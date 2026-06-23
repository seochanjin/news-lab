"""Summary 근거 기사로 요약을 만들고 관련 기사 전체의 저장 계획을 구성한다.

원문이 확보된 Summary 기사만 provider 입력으로 전달하고, 생성된 Topic에는
선정 단계의 관련 기사 전체를 기존 순서와 대표 기사 역할로 연결한다. 실제 DB
transaction 실행은 주입된 save executor에 위임하며 provider 실패는 Topic별로
격리한다.
"""

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
    """Summary 기사로 요약을 만들고 관련 기사 전체의 저장 계획을 처리한다.

    Topic별 summary provider 예외는 해당 topic에 한정해 격리한다. 원문이 없는
    topic은 기존 save-plan 정책에 따라 skip한다. Execute 모드에서 저장 후보가
    있으면 주입된 save executor를 호출하며, 공통 `pipeline_date`를 모든
    `topics.topic_date` 값에 사용한다.

    Returns:
        생성·저장·skip·실패 통계와 save plan을 포함한 `TopicSaveResult`.
    """

    LOGGER.info(
        "summary/save stage start: pipeline_date=%s related_article_count=%d "
        "summary_article_count=%d",
        pipeline_context.pipeline_date,
        len(topic_result.related_article_ids),
        len(topic_result.summary_article_ids),
    )
    provider = summary_provider or create_summary_provider(args)
    summary_topics = _summary_article_topics(topic_result)
    summary_inputs = build_topic_summary_inputs(
        summary_topics,
        raw_result.article_raw_texts,
        max_topics=args.max_topics,
        max_articles_per_topic=getattr(
            args,
            "max_summary_articles_per_topic",
            args.max_articles_per_topic,
        ),
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
    _apply_related_articles(save_plan, topic_result.selected_topics)
    save_plan["analysis"]["related_article_count"] = sum(
        len(topic["articles"]) for topic in save_plan["topics"]
    )
    save_plan["analysis"]["summary_article_count"] = sum(
        summary["article_count"]
        for summary in summaries
        if summary["status"] == "ready"
    )
    save_plan["analysis"]["raw_extraction_performed"] = bool(
        raw_result.extraction_results
    )
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


def _summary_article_topics(topic_result):
    """선택 Topic 구조에서 Summary 근거 기사만 남긴 provider 입력용 복사본을 만든다."""

    summary_ids = set(topic_result.summary_article_ids)
    return [
        {
            **{key: value for key, value in topic.items() if key != "articles"},
            "articles": [
                article
                for article in topic["articles"]
                if article["id"] in summary_ids
            ],
        }
        for topic in topic_result.selected_topics
    ]


def _apply_related_articles(save_plan, topics):
    """저장 후보 Topic의 기사 관계와 집계값을 관련 기사 전체 기준으로 교체한다.

    Summary 생성에 성공해 저장 후보가 된 Topic만 대상으로 한다. 선정 단계의
    기사 순서를 rank로 유지하고 article ID 중복은 최초 관계만 보존한다.
    """

    topics_by_candidate_id = {
        topic["topic_candidate_id"]: topic for topic in topics
    }
    for topic in save_plan["topics"]:
        selected_topic = topics_by_candidate_id[topic["topic_candidate_id"]]
        related_articles = []
        seen_article_ids = set()
        for article in selected_topic["articles"]:
            if article.get("representative_candidate_rank") is None:
                continue
            if article["id"] in seen_article_ids:
                continue
            seen_article_ids.add(article["id"])
            related_articles.append(
                {
                    "article_id": article["id"],
                    "role": (
                        "representative"
                        if article.get("representative_candidate_rank") == 1
                        else "supporting"
                    ),
                    "similarity_score": article.get("similarity_to_seed"),
                }
            )
        topic["articles"] = related_articles
        topic["article_count"] = len(related_articles)
        topic["source_count"] = len(
            {
                article.get("source")
                for article in selected_topic["articles"]
                if article["id"] in seen_article_ids and article.get("source")
            }
        )
