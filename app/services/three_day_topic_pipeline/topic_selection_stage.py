"""저장 embedding 후보를 72시간 기준으로 재클러스터링하고 기사를 선정한다.

Daily Topic 결과 table을 읽지 않고 UNIT-03의 기사·embedding 대응 결과를 직접
사용한다. 공통 grouping, 대표 후보 점수, Topic 정렬과 Summary 중복 제거 정책을
재사용하되 Topic 수와 관련·Summary 기사 상한은 3일 전용 인자로 받는다.
원문 조회, Summary provider 호출과 DB 쓰기는 수행하지 않는다.
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

from .models import (
    ThreeDayCandidateStageResult,
    ThreeDayPipelineContext,
    ThreeDayTopicSelectionResult,
)


MIN_CLUSTERING_ARTICLES = 2
LOGGER = logging.getLogger(__name__)


def cluster_and_select_three_day_topics(
    candidate_result: ThreeDayCandidateStageResult,
    *,
    pipeline_context: ThreeDayPipelineContext,
    similarity_threshold: float,
    max_topics: int,
    max_related_articles_per_topic: int,
    max_summary_articles_per_topic: int,
) -> ThreeDayTopicSelectionResult:
    """3일 후보를 clustering하고 대표·관련·Summary 근거 기사 집합을 만든다.

    정상 embedding이 두 건 미만이면 오류 대신 빈 결과를 반환한다. 대표 기사는
    관련 기사와 Summary 근거 기사에 모두 포함되며 Summary 집합은 URL과 정규화
    제목 중복을 제외한다.
    """

    _validate_selection_settings(
        similarity_threshold=similarity_threshold,
        max_topics=max_topics,
        max_related_articles_per_topic=max_related_articles_per_topic,
        max_summary_articles_per_topic=max_summary_articles_per_topic,
    )
    articles = candidate_result.articles
    embeddings = candidate_result.embeddings
    LOGGER.info(
        "three-day topic selection start: window_start=%s window_end=%s "
        "clustering_input_count=%d",
        pipeline_context.window_start.isoformat(),
        pipeline_context.window_end.isoformat(),
        len(articles),
    )
    if len(articles) < MIN_CLUSTERING_ARTICLES:
        LOGGER.warning(
            "three-day clustering skipped: clustering_input_count=%d minimum=%d",
            len(articles),
            MIN_CLUSTERING_ARTICLES,
        )
        grouped = []
    else:
        grouped = group_articles(
            articles,
            embeddings,
            similarity_threshold=similarity_threshold,
        )

    candidates = select_topic_representatives(
        grouped,
        max_candidates_per_topic=max_related_articles_per_topic,
    )
    attach_article_urls(candidates, articles)
    ordered_topics = sorted(candidates, key=topic_selection_key)
    selected_topics = ordered_topics[:max_topics]
    related_article_ids = selected_topic_article_ids(selected_topics)
    summary_article_ids = summary_topic_article_ids(
        selected_topics,
        maximum=max_summary_articles_per_topic,
    )
    representative_article_ids = list(
        dict.fromkeys(
            int(article["id"])
            for topic in selected_topics
            for article in topic["articles"]
            if article.get("representative_candidate_rank") == 1
        )
    )
    result = ThreeDayTopicSelectionResult(
        selected_topics=selected_topics,
        representative_article_ids=representative_article_ids,
        related_article_ids=related_article_ids,
        summary_article_ids=summary_article_ids,
        cluster_count=len(grouped),
        topic_candidate_count=len(ordered_topics),
    )
    LOGGER.info(
        "three-day topic selection end: cluster_count=%d candidate_count=%d "
        "selected_topic_count=%d related_article_count=%d "
        "summary_article_count=%d",
        result.cluster_count,
        result.topic_candidate_count,
        result.selected_topic_count,
        len(result.related_article_ids),
        len(result.summary_article_ids),
    )
    return result


def _validate_selection_settings(
    *,
    similarity_threshold: float,
    max_topics: int,
    max_related_articles_per_topic: int,
    max_summary_articles_per_topic: int,
) -> None:
    """3일 전용 threshold와 기사·Topic 상한의 유효 범위를 검증한다."""

    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between zero and one")
    if max_topics < 1:
        raise ValueError("max_topics must be positive")
    if max_related_articles_per_topic < 1:
        raise ValueError("max_related_articles_per_topic must be positive")
    if max_summary_articles_per_topic < 1:
        raise ValueError("max_summary_articles_per_topic must be positive")
    if max_summary_articles_per_topic > max_related_articles_per_topic:
        raise ValueError(
            "max_summary_articles_per_topic cannot exceed "
            "max_related_articles_per_topic"
        )
