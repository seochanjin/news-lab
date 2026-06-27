"""7일 Topic Summary 후보 기사 원문을 재사용하거나 지연 추출한다.

선정 단계가 만든 주간 Topic의 관련 기사 안에서 기존 원문을 먼저 조회하고,
execute 모드에서는 원문이 없는 Summary 후보 기사만 extractor에 전달한다. 한
Topic의 extractor 예외는 기사별 실패로 기록하고 다음 Topic 처리를 계속한다.
Summary 생성과 DB 저장은 이 모듈의 책임이 아니며, 최종 Summary 입력 단계에서
원문이 없는 후보는 같은 Topic의 다음 관련 기사 원문으로 대체될 수 있다.
"""

import logging

from .models import (
    WeeklyPipelineContext,
    WeeklyRawAcquisitionResult,
    WeeklyTopicSelectionResult,
)


ELIGIBLE_EXTRACTION_STATUSES = frozenset({"not_extracted", "pending"})
LOGGER = logging.getLogger(__name__)


def acquire_weekly_topic_raw_texts(
    topic_result: WeeklyTopicSelectionResult,
    raw_states,
    raw_texts,
    *,
    pipeline_context: WeeklyPipelineContext,
    execute: bool,
    extraction_limit: int,
    extraction_executor=None,
    raw_text_loader=None,
) -> WeeklyRawAcquisitionResult:
    """주간 Summary 후보 원문을 조회하고 필요한 경우 Topic별로 지연 추출한다.

    기존 원문 조회는 선택 Topic의 관련 기사 전체로 제한해 후보 원문 확보 실패 시
    다음 순위 기사를 대체 근거로 사용할 수 있게 한다. Extractor 호출은 원문이
    없는 Summary 후보 기사에만 수행하며, execute 모드에서는 executor와 loader를
    모두 주입해야 한다.
    """

    if not 1 <= extraction_limit <= 5:
        raise ValueError("extraction_limit must be between 1 and 5")
    related_ids = topic_result.related_article_ids
    summary_ids = set(topic_result.summary_article_ids)
    LOGGER.info(
        "weekly raw acquisition start: week_start=%s week_end=%s "
        "related_article_count=%d summary_article_count=%d",
        pipeline_context.week_start.isoformat(),
        pipeline_context.week_end.isoformat(),
        len(related_ids),
        len(summary_ids),
    )
    article_raw_texts = _selected_raw_texts(raw_texts, related_ids)
    if raw_text_loader is not None and related_ids:
        article_raw_texts = _selected_raw_texts(
            raw_text_loader(related_ids),
            related_ids,
        )

    extraction_results = []
    if execute:
        if extraction_executor is None or raw_text_loader is None:
            raise ValueError(
                "execute mode requires extraction_executor and raw_text_loader"
            )
        for topic in topic_result.selected_topics:
            target_ids = _topic_extraction_target_ids(
                topic,
                summary_ids=summary_ids,
                article_raw_texts=article_raw_texts,
                raw_states=raw_states,
            )
            for offset in range(0, len(target_ids), extraction_limit):
                batch = target_ids[offset : offset + extraction_limit]
                try:
                    extraction_results.extend(
                        extraction_executor(batch, limit=extraction_limit)
                    )
                except Exception as error:
                    LOGGER.warning(
                        "weekly raw extraction failed: "
                        "topic_candidate_id=%s article_ids=%s error=%s",
                        topic["topic_candidate_id"],
                        batch,
                        _safe_error(error),
                    )
                    extraction_results.extend(
                        {
                            "article_id": article_id,
                            "status": "failed",
                            "error_message": _safe_error(error),
                        }
                        for article_id in batch
                    )
        if related_ids:
            article_raw_texts = _selected_raw_texts(
                raw_text_loader(related_ids),
                related_ids,
            )

    extracted_ids = _successful_extracted_ids(
        extraction_results,
        article_raw_texts,
    )
    failed_ids = list(
        dict.fromkeys(
            int(result["article_id"])
            for result in extraction_results
            if result.get("status") == "failed"
        )
    )
    reused_ids = [
        article_id
        for article_id in related_ids
        if article_id not in extracted_ids
        and (article_raw_texts.get(article_id) or "").strip()
    ]
    missing_ids = [
        article_id
        for article_id in topic_result.summary_article_ids
        if not (article_raw_texts.get(article_id) or "").strip()
    ]
    return WeeklyRawAcquisitionResult(
        article_raw_texts=article_raw_texts,
        reused_article_ids=reused_ids,
        extracted_article_ids=extracted_ids,
        failed_article_ids=failed_ids,
        missing_article_ids=missing_ids,
        extraction_results=extraction_results,
    )


def _selected_raw_texts(raw_texts, selected_ids) -> dict[int, str]:
    """선택 기사 중 비어 있지 않은 원문만 ID mapping으로 반환한다."""

    return {
        article_id: raw_texts[article_id]
        for article_id in selected_ids
        if (raw_texts.get(article_id) or "").strip()
    }


def _topic_extraction_target_ids(
    topic,
    *,
    summary_ids,
    article_raw_texts,
    raw_states,
) -> list[int]:
    """한 Topic의 Summary 후보 중 원문이 없고 재시도 가능한 ID만 반환한다."""

    target_ids = []
    for article in topic["articles"]:
        article_id = int(article["id"])
        if article_id not in summary_ids:
            continue
        if (article_raw_texts.get(article_id) or "").strip():
            continue
        raw_state = raw_states.get(article_id)
        if raw_state is None:
            status = "not_extracted"
        elif raw_state.get("has_raw_text"):
            status = "already_extracted"
        else:
            status = str(raw_state.get("extraction_status") or "pending").casefold()
        if status in ELIGIBLE_EXTRACTION_STATUSES:
            target_ids.append(article_id)
    return target_ids


def _successful_extracted_ids(extraction_results, raw_texts) -> list[int]:
    """Extractor 성공 결과 중 재조회한 원문이 실제 존재하는 기사 ID를 반환한다."""

    return list(
        dict.fromkeys(
            int(result["article_id"])
            for result in extraction_results
            if result.get("status") == "success"
            and (raw_texts.get(int(result["article_id"])) or "").strip()
        )
    )


def _safe_error(error: Exception) -> str:
    """로그와 실패 결과에 기록할 예외를 공백 정규화와 길이 제한 후 반환한다."""

    message = " ".join(str(error).split())
    if len(message) > 200:
        message = message[:197] + "..."
    return f"{type(error).__name__}: {message}" if message else type(error).__name__
