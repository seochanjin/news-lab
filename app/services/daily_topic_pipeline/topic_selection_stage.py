"""Embedding 기사들을 clustering하고 Daily topic 선택 결과를 구성한다.

기존 grouping과 대표 후보 정렬을 호출해 선택 topic과 reference topic을 나누고,
다음 단계가 사용할 관련 기사와 Summary 기사 ID 계약을 만든다. 원문 조회,
Summary provider 호출, DB 저장은 수행하지 않는다.
"""

import logging

from app.services.topic_pipeline import (
    attach_article_urls,
    selected_topic_article_ids,
    summary_topic_article_ids,
    topic_selection_key,
)
from app.utils.topic_grouping import group_articles
from app.utils.topic_representatives import select_topic_representatives

from .models import EmbeddingStageResult, PipelineContext, TopicSelectionResult


MIN_CLUSTERING_ARTICLES = 2
LOGGER = logging.getLogger(__name__)


def cluster_and_select_topics(
    embedding_result: EmbeddingStageResult,
    args,
    *,
    pipeline_context: PipelineContext,
):
    """Embedding 결과를 clustering하고 주요 topic과 대표·관련 기사를 선택한다.

    기존 similarity threshold, 대표 기사 선정, topic 정렬과 최대 개수 정책을
    그대로 적용한다. 정상 vector가 두 건 미만이면 후속 처리를 위한 topic을
    만들지 않고 빈 선택 결과를 반환한다. 원문 조회나 provider 호출, DB 저장은
    수행하지 않는다.
    """

    LOGGER.info(
        "topic selection stage start: pipeline_date=%s",
        pipeline_context.pipeline_date,
    )
    clustering_articles = embedding_result.articles
    embeddings = embedding_result.embeddings
    LOGGER.info(
        "topic candidate generation start: article_count=%d",
        len(clustering_articles),
    )
    if len(clustering_articles) < MIN_CLUSTERING_ARTICLES:
        LOGGER.warning(
            "topic candidate generation skipped: clustering_input_count=%d "
            "minimum=%d",
            len(clustering_articles),
            MIN_CLUSTERING_ARTICLES,
        )
        grouped = []
    else:
        grouped = group_articles(
            clustering_articles,
            embeddings,
            similarity_threshold=args.similarity_threshold,
        )
    representatives = select_topic_representatives(
        grouped,
        max_candidates_per_topic=getattr(
            args,
            "max_related_articles_per_topic",
            args.max_articles_per_topic,
        ),
    )
    attach_article_urls(representatives, clustering_articles)
    ordered_topics = sorted(representatives, key=topic_selection_key)
    LOGGER.info(
        "topic candidate generation end: candidate_count=%d",
        len(ordered_topics),
    )
    selected_topics = ordered_topics[: args.max_topics]
    reference_topics = ordered_topics[
        args.max_topics : args.max_topics + args.max_reference_topics
    ]
    related_article_ids = selected_topic_article_ids(selected_topics)
    summary_article_ids = summary_topic_article_ids(
        selected_topics,
        maximum=getattr(
            args,
            "max_summary_articles_per_topic",
            args.max_articles_per_topic,
        ),
    )
    representative_article_ids = [
        article["id"]
        for topic in selected_topics
        for article in topic["articles"]
        if article.get("representative_candidate_rank") == 1
    ]
    LOGGER.info("selected topic count: %d", len(selected_topics))
    return TopicSelectionResult(
        selected_topics=selected_topics,
        reference_topics=reference_topics,
        representative_article_ids=list(dict.fromkeys(representative_article_ids)),
        related_article_ids=related_article_ids,
        summary_article_ids=summary_article_ids,
        cluster_count=len(grouped),
        selected_topic_count=len(selected_topics),
        topic_candidate_count=len(ordered_topics),
    )


def public_topic(topic):
    selected = [
        article
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    ]
    return {
        "topic_candidate_id": topic["topic_candidate_id"],
        "article_count": topic["article_count"],
        "source_count": topic["source_count"],
        "selected_article_ids": [article["id"] for article in selected],
        "similarity_scores": {
            article["id"]: article.get("similarity_to_seed") for article in selected
        },
        "articles": [
            {
                "role": (
                    "representative"
                    if article.get("representative_candidate_rank") == 1
                    else "supporting"
                ),
                "article_id": article["id"],
                "similarity_score": article.get("similarity_to_seed"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "title": article.get("title"),
                "url": article.get("url"),
            }
            for article in selected
        ],
    }
