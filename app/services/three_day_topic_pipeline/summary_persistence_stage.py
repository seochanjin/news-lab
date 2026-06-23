"""3일 흐름 Summary를 Topic별로 생성하고 성공 결과를 window 단위로 저장한다.

Summary 입력은 원문이 확보된 근거 기사와 기사 시각을 포함하며
`three-day-flow-v1` prompt 계약으로 hash를 계산한다. Provider 실패와 원문
부족은 Topic별로 격리하고, 성공 부분집합 또는 정상 빈 결과만 repository의
원자적 교체 transaction에 전달한다.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone

import requests

from app.utils.topic_summary import (
    DEFAULT_SUMMARY_MODEL,
    SUPPORTED_SUMMARY_MODELS,
    parse_provider_response,
)

from .models import (
    ThreeDayPipelineContext,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicArticleRecord,
    ThreeDayTopicProcessingResult,
    ThreeDayTopicRecord,
    ThreeDayTopicSelectionResult,
)


PROMPT_VERSION = "three-day-flow-v1"
LOGGER = logging.getLogger(__name__)


class ThreeDayOpenAISummaryProvider:
    """OpenAI Responses API에 3일 흐름 전용 prompt와 JSON schema를 전달한다."""

    provider = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, *, api_key: str, model: str = DEFAULT_SUMMARY_MODEL) -> None:
        """API key와 지원 Summary model을 검증해 provider 설정을 보관한다."""

        if not api_key:
            raise ValueError("api_key is required")
        if model not in SUPPORTED_SUMMARY_MODELS:
            raise ValueError(f"unsupported summary model: {model}")
        self.api_key = api_key
        self.model = model

    def summarize(self, topic_input: dict) -> dict:
        """한 Topic 입력을 3일 prompt로 호출하고 검증된 Summary 객체를 반환한다."""

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": build_three_day_summary_prompt(topic_input),
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "three_day_topic_summary",
                        "strict": True,
                        "schema": _summary_schema(),
                    }
                },
            },
            timeout=90,
        )
        response.raise_for_status()
        return parse_provider_response(response.json())


def summarize_and_persist_three_day_topics(
    topic_result: ThreeDayTopicSelectionResult,
    raw_result: ThreeDayRawAcquisitionResult,
    *,
    pipeline_context: ThreeDayPipelineContext,
    summary_provider,
    repository,
    run_id: int,
    execute: bool,
    max_raw_chars_per_article: int,
) -> ThreeDayTopicProcessingResult:
    """Topic별 3일 Summary를 만들고 저장 가능한 결과만 원자적으로 교체한다.

    원문이 없거나 대표 기사 원문이 없는 Topic과 provider 예외는 실패 목록에
    남기고 다음 Topic을 계속한다. Execute 모드에서는 성공 Topic이 있거나
    선택 Topic 자체가 없는 정상 빈 실행일 때만 동일 window 결과를 교체한다.
    """

    if max_raw_chars_per_article < 1:
        raise ValueError("max_raw_chars_per_article must be positive")
    if execute and repository is None:
        raise ValueError("execute mode requires repository")
    topics = []
    failures = []
    for topic in topic_result.selected_topics:
        try:
            summary_input = build_three_day_summary_input(
                topic,
                raw_result.article_raw_texts,
                max_raw_chars_per_article=max_raw_chars_per_article,
            )
            _validate_summary_input(summary_input)
            summary = summary_provider.summarize(summary_input)
            topics.append(
                _build_topic_record(
                    topic,
                    summary_input,
                    summary,
                    pipeline_context=pipeline_context,
                    provider=summary_provider.provider,
                    model=summary_provider.model,
                )
            )
        except Exception as error:
            failure = {
                "topic_candidate_id": topic["topic_candidate_id"],
                "error": _safe_error(error),
            }
            failures.append(failure)
            LOGGER.warning(
                "three-day topic processing failed: topic_candidate_id=%s error=%s",
                failure["topic_candidate_id"],
                failure["error"],
            )

    run_status = _run_status(topics, failures)
    saved_topic_ids = []
    should_replace = bool(topics) or not topic_result.selected_topics
    if execute and should_replace:
        saved_topic_ids = repository.replace_window_topics(
            run_id=run_id,
            window_start=pipeline_context.window_start,
            window_end=pipeline_context.window_end,
            topics=topics,
        )
    return ThreeDayTopicProcessingResult(
        topics=topics,
        generated_topic_count=len(topics),
        saved_topic_count=len(saved_topic_ids),
        failed_topic_count=len(failures),
        saved_topic_ids=saved_topic_ids,
        failures=failures,
        run_status=run_status,
    )


def build_three_day_summary_input(
    topic,
    raw_texts,
    *,
    max_raw_chars_per_article: int,
) -> dict:
    """한 Topic에서 원문이 있는 Summary 근거 기사의 시간순 입력을 구성한다."""

    used_articles = []
    for article in topic["articles"]:
        raw_text = (raw_texts.get(int(article["id"])) or "").strip()
        if not raw_text:
            continue
        analysis_time = article.get("published_at") or article.get("analysis_time")
        used_articles.append(
            {
                "article_id": int(article["id"]),
                "title": article.get("title"),
                "source": article.get("source"),
                "analysis_time": _isoformat_utc(analysis_time),
                "raw_text": raw_text[:max_raw_chars_per_article],
            }
        )
    used_articles.sort(
        key=lambda article: (
            article["analysis_time"] or "",
            article["article_id"],
        )
    )
    representative_ids = [
        int(article["id"])
        for article in topic["articles"]
        if article.get("representative_candidate_rank") == 1
    ]
    return {
        "topic_candidate_id": topic["topic_candidate_id"],
        "prompt_version": PROMPT_VERSION,
        "representative_article_id": (
            representative_ids[0] if representative_ids else None
        ),
        "instruction": (
            "최근 72시간 동안 사건이 어떻게 변했는지 시간 흐름, 진행 상황, "
            "여러 출처가 공통으로 확인한 사실과 남은 불확실성을 구분해 "
            "한국어로 요약한다."
        ),
        "used_articles": used_articles,
    }


def build_three_day_summary_input_hash(summary_input: dict) -> str:
    """Prompt version, 기사 시각과 bounded 원문을 포함한 결정론적 hash를 만든다."""

    payload = {
        "prompt_version": summary_input["prompt_version"],
        "used_articles": sorted(
            summary_input["used_articles"],
            key=lambda article: (
                article["article_id"],
                article["analysis_time"] or "",
                article["raw_text"],
            ),
        ),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_three_day_summary_prompt(summary_input: dict) -> str:
    """OpenAI 계열 provider에 전달할 3일 흐름 전용 한국어 prompt를 반환한다."""

    return (
        "아래 기사 원문만 근거로 3일 뉴스 흐름을 작성하세요. "
        "단일 시점 설명에 머물지 말고 시간 순서의 변화와 진행 상황을 설명하고, "
        "여러 출처가 공통으로 확인한 내용과 불확실한 내용을 구분하세요. "
        "근거에 없는 사실은 추가하지 마세요.\n"
        + json.dumps(summary_input, ensure_ascii=False)
    )


def _validate_summary_input(summary_input: dict) -> None:
    """대표 기사 원문을 포함한 최소 한 건의 실제 Summary 근거가 있는지 확인한다."""

    used_ids = {
        int(article["article_id"]) for article in summary_input["used_articles"]
    }
    if not used_ids:
        raise ValueError("insufficient raw text")
    representative_id = summary_input.get("representative_article_id")
    if representative_id is None:
        raise ValueError("representative article is required")
    representative_id = int(representative_id)
    if representative_id not in used_ids:
        raise ValueError("representative article raw text is required")


def _build_topic_record(
    topic,
    summary_input,
    summary,
    *,
    pipeline_context,
    provider,
    model,
) -> ThreeDayTopicRecord:
    """Provider 출력과 선정 기사 역할을 repository용 불변 record로 변환한다."""

    used_ids = {
        int(article["article_id"]) for article in summary_input["used_articles"]
    }
    related_articles = [
        article
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    ]
    related_articles.sort(
        key=lambda article: (
            article["representative_candidate_rank"],
            article["id"],
        )
    )
    records = [
        ThreeDayTopicArticleRecord(
            article_id=int(article["id"]),
            rank=rank,
            similarity=article.get("similarity_to_seed"),
            is_representative=article.get("representative_candidate_rank") == 1,
            is_summary_evidence=int(article["id"]) in used_ids,
        )
        for rank, article in enumerate(related_articles, start=1)
    ]
    return ThreeDayTopicRecord(
        topic_candidate_id=topic["topic_candidate_id"],
        reference_date=pipeline_context.reference_date,
        window_start=pipeline_context.window_start,
        window_end=pipeline_context.window_end,
        title_ko=summary["title_ko"],
        summary_ko=summary["summary_ko"],
        key_points=list(summary["key_points"]),
        keywords=list(summary["keywords"]),
        confidence=float(summary["confidence"]),
        source_count=len(
            {
                article.get("source")
                for article in related_articles
                if article.get("source")
            }
        ),
        status="draft",
        provider=provider,
        model=model,
        prompt_version=PROMPT_VERSION,
        summary_input_hash=build_three_day_summary_input_hash(summary_input),
        articles=records,
    )


def _run_status(topics, failures) -> str:
    """성공·실패 Topic 조합을 run 최종 상태 계약으로 변환한다."""

    if topics and failures:
        return "partial_success"
    if failures:
        return "failed"
    return "success"


def _isoformat_utc(value) -> str | None:
    """기사 시각을 hash와 prompt에 안정적인 UTC ISO 8601 문자열로 변환한다."""

    if value is None:
        return None
    if not isinstance(value, datetime):
        return str(value)
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _safe_error(error: Exception) -> str:
    """Topic 실패에 기록할 예외를 공백 정규화와 길이 제한 후 반환한다."""

    message = " ".join(str(error).split())
    if len(message) > 200:
        message = message[:197] + "..."
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


def _summary_schema() -> dict:
    """Responses API strict output에 사용할 3일 Topic Summary JSON schema를 반환한다."""

    return {
        "type": "object",
        "properties": {
            "title_ko": {"type": "string"},
            "summary_ko": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
        },
        "required": [
            "title_ko",
            "summary_ko",
            "key_points",
            "keywords",
            "confidence",
        ],
        "additionalProperties": False,
    }
