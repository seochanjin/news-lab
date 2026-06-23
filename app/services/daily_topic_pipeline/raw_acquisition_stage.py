"""Summary 근거 기사에 한해 저장 원문을 재사용하거나 신규 추출한다.

Topic 선정 결과의 관련 기사 전체는 보존하되 원문 조회와 extractor 호출 대상은
`summary_article_ids`로 제한한다. 이 모듈은 Summary 생성이나 Topic 저장을
수행하지 않으며 기사별 추출 실패를 결과 통계로 격리한다.
"""

import logging

from app.utils.raw_extraction_targets import select_raw_extraction_targets

from .models import PipelineContext, RawAcquisitionResult, TopicSelectionResult


LOGGER = logging.getLogger(__name__)


def acquire_selected_article_raw_texts(
    topic_result: TopicSelectionResult,
    raw_states,
    raw_texts,
    args,
    *,
    pipeline_context: PipelineContext,
    extraction_executor=None,
    raw_text_loader=None,
):
    """선택된 Summary 근거 기사에 한해 summary용 원문을 확보한다.

    기존 `raw_articles` 원문을 우선 재사용하고 execute 모드에서는 원문이 없는
    extraction target만 extractor에 전달한다. 추출 후 Summary 기사만 다시
    조회해 재사용 원문과 합친다. 단일 기사 실패는 failed/missing 통계로
    격리하며 원문이 확보된 다른 topic의 summary 진행을 막지 않는다.

    Returns:
        원문 mapping과 reused, extracted, failed, missing article ID를 포함한
        `RawAcquisitionResult`.
    """

    LOGGER.info(
        "raw acquisition stage start: pipeline_date=%s",
        pipeline_context.pipeline_date,
    )
    summary_topics = _summary_article_topics(topic_result)
    target_topics = select_raw_extraction_targets(
        summary_topics,
        raw_states,
        max_targets_per_topic=getattr(
            args,
            "max_summary_articles_per_topic",
            args.max_articles_per_topic,
        ),
    )
    extraction_target_ids = _extraction_target_ids(target_topics)
    selected_article_ids = topic_result.selected_article_ids
    article_raw_texts = {
        article_id: raw_texts[article_id]
        for article_id in selected_article_ids
        if (raw_texts.get(article_id) or "").strip()
    }
    extraction_results = []
    if args.execute and extraction_target_ids:
        LOGGER.info(
            "raw extraction start: article_count=%d article_ids=%s",
            len(extraction_target_ids),
            extraction_target_ids,
        )
        if extraction_executor is None or raw_text_loader is None:
            raise ValueError(
                "execute mode requires extraction_executor and raw_text_loader"
            )
        extraction_results = extraction_executor(
            extraction_target_ids,
            limit=args.extraction_limit,
        )
        # Reload only selected articles so newly extracted text can join reused text.
        article_raw_texts = raw_text_loader(selected_article_ids)
        LOGGER.info(
            "raw extraction end: requested_count=%d result_count=%d article_ids=%s",
            len(extraction_target_ids),
            len(extraction_results),
            extraction_target_ids,
        )
    elif raw_text_loader is not None and selected_article_ids:
        article_raw_texts = raw_text_loader(selected_article_ids)

    extracted_article_ids = [
        result["article_id"]
        for result in extraction_results
        if result["status"] == "success"
        and (article_raw_texts.get(result["article_id"]) or "").strip()
    ]
    failed_article_ids = [
        result["article_id"]
        for result in extraction_results
        if result["status"] == "failed"
    ]
    reused_article_ids = [
        article_id
        for article_id in selected_article_ids
        if article_id not in extracted_article_ids
        and (article_raw_texts.get(article_id) or "").strip()
    ]
    missing_article_ids = [
        article_id
        for article_id in selected_article_ids
        if not (article_raw_texts.get(article_id) or "").strip()
    ]
    summary_ready_topics = [
        topic
        for topic in target_topics
        if any(
            (article_raw_texts.get(article["id"]) or "").strip()
            for article in topic["articles"]
        )
    ]
    return RawAcquisitionResult(
        article_raw_texts=article_raw_texts,
        reused_article_ids=reused_article_ids,
        extracted_article_ids=extracted_article_ids,
        failed_article_ids=failed_article_ids,
        missing_article_ids=missing_article_ids,
        summary_ready_topics=summary_ready_topics,
        extraction_results=extraction_results,
    )


def _extraction_target_ids(topics):
    """Raw target로 판정된 Summary 기사 ID를 topic 순서대로 반환한다."""

    ids = []
    for topic in topics:
        for article in topic["articles"]:
            if article["extraction_target_status"] == "target":
                ids.append(article["id"])
    return ids


def _summary_article_topics(topic_result):
    """선택 topic 구조를 유지하면서 Summary 근거 기사만 포함한 복사본을 만든다."""

    summary_ids = set(topic_result.summary_article_ids)
    return [
        {
            **{key: value for key, value in topic.items() if key != "articles"},
            "articles": [
                article for article in topic["articles"] if article["id"] in summary_ids
            ],
        }
        for topic in topic_result.selected_topics
    ]
