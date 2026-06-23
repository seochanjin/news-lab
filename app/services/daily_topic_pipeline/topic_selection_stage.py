"""Embedding 기사들을 clustering하고 Daily topic 선택 결과를 구성한다.

기존 grouping과 대표 후보 정렬을 호출해 선택 topic과 reference topic을 나누고,
다음 단계가 사용할 관련 기사와 Summary 기사 ID 계약을 만든다. 원문 조회,
Summary provider 호출, DB 저장은 수행하지 않는다.
"""

import logging
from datetime import timezone

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
    _attach_report_metadata(representatives, clustering_articles)
    ordered_topics = sorted(representatives, key=topic_selection_key)
    LOGGER.info(
        "topic candidate generation end: candidate_count=%d",
        len(ordered_topics),
    )
    selected_topics = ordered_topics[: args.max_topics]
    reference_topics = ordered_topics[
        args.max_topics : args.max_topics + args.max_reference_topics
    ]
    related_article_ids = _selected_topic_article_ids(selected_topics)
    summary_article_ids = _summary_topic_article_ids(
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


def topic_selection_key(topic):
    selected = [
        article
        for article in topic["articles"]
        if article.get("representative_candidate_rank") is not None
    ]
    similarities = [
        float(article["similarity_to_seed"])
        for article in selected
        if article.get("similarity_to_seed") is not None
    ]
    average_similarity = (
        sum(similarities) / len(similarities) if similarities else 0.0
    )
    latest = max(
        (
            value
            for article in topic["articles"]
            if (
                value := _as_utc(
                    article.get("published_at") or article.get("created_at")
                )
            )
            is not None
        ),
        default=None,
    )
    latest_timestamp = latest.timestamp() if latest else float("-inf")
    return (
        -topic["article_count"],
        -topic["source_count"],
        -average_similarity,
        -latest_timestamp,
        topic["topic_candidate_id"],
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


def _attach_report_metadata(topics, articles):
    url_by_article_id = {
        article["id"]: article.get("url")
        for article in articles
    }
    for topic in topics:
        for article in topic["articles"]:
            article["url"] = url_by_article_id.get(article["id"])


def _selected_topic_article_ids(topics):
    """선택 topic별 관련 기사 순서를 유지하면서 중복 없는 ID 목록을 반환한다."""

    return list(
        dict.fromkeys(
            article["id"]
            for topic in topics
            for article in topic["articles"]
            if article.get("representative_candidate_rank") is not None
        )
    )


def _summary_topic_article_ids(topics, *, maximum):
    """관련 기사 순위에서 대표 기사와 중복 제거 정책을 지켜 Summary ID를 고른다.

    기존 대표 후보 순위에는 관련도, 중요도, source 다양성과 결정론적 ID
    tie-breaker가 반영되어 있다. Topic별로 그 순서를 유지하되 동일 URL 또는
    공백·대소문자를 정규화한 제목이 같은 기사는 제외하고 설정 상한까지만
    선택한다.
    """

    selected_ids = []
    for topic in topics:
        selected_ids.extend(_summary_article_ids_for_topic(topic, maximum=maximum))
    return list(dict.fromkeys(selected_ids))


def _summary_article_ids_for_topic(topic, *, maximum):
    """단일 topic의 관련 기사 중 Summary 근거 기사 ID를 결정론적으로 선택한다."""

    selected_ids = []
    seen_urls = set()
    seen_titles = set()
    related_articles = sorted(
        (
            article
            for article in topic["articles"]
            if article.get("representative_candidate_rank") is not None
        ),
        key=lambda article: (
            article["representative_candidate_rank"],
            article["id"],
        ),
    )
    for article in related_articles:
        normalized_url = _normalize_duplicate_url(article.get("url"))
        normalized_title = _normalize_duplicate_title(article.get("title"))
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        selected_ids.append(article["id"])
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        if len(selected_ids) >= maximum:
            break
    return selected_ids


def _normalize_duplicate_url(value):
    """URL 중복 비교를 위해 앞뒤 공백만 제거하고 원래 대소문자를 보존한다."""

    return str(value or "").strip()


def _normalize_duplicate_title(value):
    """제목 중복 비교를 위해 공백을 정규화하고 대소문자를 무시한다."""

    return " ".join(str(value or "").split()).casefold()


def _as_utc(value):
    """날짜 값을 UTC aware datetime으로 정규화한다."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
