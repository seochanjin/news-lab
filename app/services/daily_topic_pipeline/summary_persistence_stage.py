"""Topic summary generation and persistence planning stage."""

import logging

from app.utils.topic_summary import (
    build_topic_summary_inputs,
    summarize_topic_inputs,
)
from scripts.generate_topic_summary_report import create_summary_provider
from scripts.save_topic_summaries import build_save_plan

from .errors import safe_error
from .models import (
    PipelineContext,
    RawAcquisitionResult,
    TopicSaveResult,
    TopicSelectionResult,
)


LOGGER = logging.getLogger(__name__)


def summarize_and_save_topics(
    topic_result: TopicSelectionResult,
    raw_result: RawAcquisitionResult,
    args,
    *,
    pipeline_context: PipelineContext,
    summary_provider=None,
    save_executor=None,
):
    """Selected topic의 원문으로 summary를 만들고 topic 저장 계획을 처리한다.

    Topic별 summary provider 예외는 해당 topic에 한정해 격리한다. 원문이 없는
    topic은 기존 save-plan 정책에 따라 skip한다. Execute 모드에서 저장 후보가
    있으면 주입된 save executor를 호출하며, 공통 `pipeline_date`를 모든
    `topics.topic_date` 값에 사용한다.

    Returns:
        생성·저장·skip·실패 통계와 save plan을 포함한 `TopicSaveResult`.
    """

    LOGGER.info(
        "summary/save stage start: pipeline_date=%s",
        pipeline_context.pipeline_date,
    )
    provider = summary_provider or create_summary_provider(args)
    summary_inputs = build_topic_summary_inputs(
        topic_result.selected_topics,
        raw_result.article_raw_texts,
        max_topics=args.max_topics,
        max_articles_per_topic=args.max_articles_per_topic,
        max_raw_chars_per_article=args.max_raw_chars_per_article,
    )
    LOGGER.info(
        "summary provider start: provider=%s model=%s topic_count=%d",
        provider.provider,
        provider.model,
        len(summary_inputs),
    )
    summaries = []
    failures = []
    for summary_input in summary_inputs:
        try:
            summaries.extend(summarize_topic_inputs([summary_input], provider))
        except Exception as error:
            failure = {
                "topic_candidate_id": summary_input["topic_candidate_id"],
                "error": safe_error(error),
            }
            failures.append(failure)
            LOGGER.warning(
                "topic summary failed: topic_candidate_id=%s error=%s",
                failure["topic_candidate_id"],
                failure["error"],
            )
    LOGGER.info(
        "summary provider end: provider=%s model=%s summary_count=%d",
        provider.provider,
        provider.model,
        len(summaries),
    )
    generation_result = {
        "analysis": {"provider": provider.provider, "model": provider.model},
        "topic_summaries": summaries,
    }
    save_plan = build_save_plan(
        generation_result,
        args,
        topic_date=pipeline_context.pipeline_date,
    )
    save_plan["analysis"]["raw_extraction_performed"] = bool(
        raw_result.extraction_results
    )
    _apply_similarity_scores(save_plan, topic_result.selected_topics)
    if args.execute and save_plan["topics"]:
        if save_executor is None:
            raise ValueError("execute mode requires save_executor")
        LOGGER.info("DB write start: topic_count=%d", len(save_plan["topics"]))
        save_plan = save_executor(save_plan)
        LOGGER.info(
            "DB write end: saved_topic_count=%d",
            save_plan["analysis"]["saved_topic_count"],
        )
    return TopicSaveResult(
        summaries=summaries,
        save_plan=save_plan,
        generated_topic_count=sum(
            summary["status"] == "ready" for summary in summaries
        ),
        saved_topic_count=save_plan["analysis"]["saved_topic_count"],
        skipped_topic_count=save_plan["analysis"]["skipped_topic_count"],
        failed_topic_count=len(failures),
        saved_topic_ids=[
            topic["topic_id"]
            for topic in save_plan["topics"]
            if topic["topic_id"] is not None
        ],
        failures=failures,
    )


def _apply_similarity_scores(save_plan, topics):
    metadata_by_article = {
        article["id"]: {
            "role": (
                "representative"
                if article.get("representative_candidate_rank") == 1
                else "supporting"
            ),
            "similarity_score": article.get("similarity_to_seed"),
        }
        for topic in topics
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    }
    for topic in save_plan["topics"]:
        for article in topic["articles"]:
            metadata = metadata_by_article.get(article["article_id"], {})
            article.update(metadata)
