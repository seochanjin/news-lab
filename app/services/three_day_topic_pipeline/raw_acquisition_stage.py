"""3일 Topic의 Summary 근거 기사에 한해 원문을 재사용하거나 지연 추출한다.

선정 단계가 정한 Summary 기사 ID만 저장 원문 조회와 extractor 호출 대상으로
사용한다. Topic별 extractor 예외와 기사별 실패를 격리해 다른 Topic 처리를
계속하며, Summary 생성이나 DB 결과 교체는 담당하지 않는다.
"""

import logging

from .models import (
    ThreeDayPipelineContext,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicSelectionResult,
)


ELIGIBLE_EXTRACTION_STATUSES = frozenset({"not_extracted", "pending"})
LOGGER = logging.getLogger(__name__)


def acquire_three_day_topic_raw_texts(
    topic_result: ThreeDayTopicSelectionResult,
    raw_states,
    raw_texts,
    *,
    pipeline_context: ThreeDayPipelineContext,
    execute: bool,
    extraction_limit: int,
    extraction_executor=None,
    raw_text_loader=None,
) -> ThreeDayRawAcquisitionResult:
    """선택된 Summary 근거 기사만 조회하고 필요한 원문을 Topic별로 추출한다.

    저장 원문을 먼저 조회한 뒤 execute 모드에서 원문이 없고 재시도 가능한
    기사만 extractor에 전달한다. 한 Topic의 extractor 호출이 예외를 내도 다음
    Topic을 계속하며, 추출 뒤 선택 기사만 다시 조회해 최종 원문 mapping을 만든다.
    """

    if not 1 <= extraction_limit <= 5:
        raise ValueError("extraction_limit must be between 1 and 5")
    selected_ids = topic_result.summary_article_ids
    LOGGER.info(
        "three-day raw acquisition start: window_start=%s window_end=%s "
        "summary_article_count=%d",
        pipeline_context.window_start.isoformat(),
        pipeline_context.window_end.isoformat(),
        len(selected_ids),
    )
    article_raw_texts = _selected_raw_texts(raw_texts, selected_ids)
    if raw_text_loader is not None and selected_ids:
        article_raw_texts = _selected_raw_texts(
            raw_text_loader(selected_ids),
            selected_ids,
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
                selected_ids=set(selected_ids),
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
                        "three-day raw extraction failed: "
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
        if selected_ids:
            article_raw_texts = _selected_raw_texts(
                raw_text_loader(selected_ids),
                selected_ids,
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
        for article_id in selected_ids
        if article_id not in extracted_ids
        and (article_raw_texts.get(article_id) or "").strip()
    ]
    missing_ids = [
        article_id
        for article_id in selected_ids
        if not (article_raw_texts.get(article_id) or "").strip()
    ]
    return ThreeDayRawAcquisitionResult(
        article_raw_texts=article_raw_texts,
        reused_article_ids=reused_ids,
        extracted_article_ids=extracted_ids,
        failed_article_ids=failed_ids,
        missing_article_ids=missing_ids,
        extraction_results=extraction_results,
    )


def _selected_raw_texts(raw_texts, selected_ids) -> dict[int, str]:
    """선택 기사 중 비어 있지 않은 원문만 ID 순서와 무관한 mapping으로 반환한다."""

    return {
        article_id: raw_texts[article_id]
        for article_id in selected_ids
        if (raw_texts.get(article_id) or "").strip()
    }


def _topic_extraction_target_ids(
    topic,
    *,
    selected_ids,
    article_raw_texts,
    raw_states,
) -> list[int]:
    """한 Topic의 Summary 기사 중 원문이 없고 재시도 가능한 ID만 반환한다."""

    target_ids = []
    for article in topic["articles"]:
        article_id = int(article["id"])
        if article_id not in selected_ids:
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
