"""저장 embedding 후보를 완료 주간 기준으로 재클러스터링하고 기사를 선정한다.

Weekly 후보 stage가 반환한 기사와 저장 embedding만 사용해 Daily 또는 3일 Topic
저장 결과를 읽지 않고 7일 Topic 후보를 만든다. 공통 grouping과 대표 후보 점수,
Topic 정렬 정책을 재사용하되 주간 전용 최소 기사 수, 최소 출처 수와 최대
Summary 근거 기사 수를 적용한다. 원문 조회, Summary provider 호출과 DB 쓰기는
수행하지 않는다.
"""

import logging
from typing import Any

from app.services.topic_pipeline import (
    attach_article_urls,
    selected_topic_article_ids,
    topic_selection_key,
)
from app.utils.topic_grouping import group_articles
from app.utils.topic_representatives import select_topic_representatives

from .models import (
    MAX_SUMMARY_EVIDENCE_COUNT,
    MIN_TOPIC_ARTICLE_COUNT,
    MIN_TOPIC_SOURCE_COUNT,
    WeeklyCandidateStageResult,
    WeeklyPipelineContext,
    WeeklyTopicSelectionResult,
)


LOGGER = logging.getLogger(__name__)


def cluster_and_select_weekly_topics(
    candidate_result: WeeklyCandidateStageResult,
    *,
    pipeline_context: WeeklyPipelineContext,
    similarity_threshold: float,
    max_topics: int,
    max_related_articles_per_topic: int,
    max_summary_articles_per_topic: int,
) -> WeeklyTopicSelectionResult:
    """주간 후보를 clustering하고 대표·관련·Summary 근거 기사 집합을 만든다.

    정상 embedding이 주간 최소 기사 수보다 적으면 오류 대신 빈 결과를 반환한다.
    군집은 기사 5개 이상, 서로 다른 출처 2개 이상일 때만 Topic 후보로 남기며
    Summary 근거는 대표 기사를 포함하고 출처 편중을 줄이는 결정론적 순서로 최대
    5개까지 선택한다.
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
        "weekly topic selection start: week_start=%s week_end=%s "
        "window_start=%s window_end=%s clustering_input_count=%d",
        pipeline_context.week_start.isoformat(),
        pipeline_context.week_end.isoformat(),
        pipeline_context.window_start.isoformat(),
        pipeline_context.window_end.isoformat(),
        len(articles),
    )
    if len(articles) < MIN_TOPIC_ARTICLE_COUNT:
        LOGGER.warning(
            "weekly clustering skipped: clustering_input_count=%d minimum=%d",
            len(articles),
            MIN_TOPIC_ARTICLE_COUNT,
        )
        grouped = []
    else:
        grouped = group_articles(
            articles,
            embeddings,
            similarity_threshold=similarity_threshold,
        )

    eligible_groups = [
        group
        for group in grouped
        if group["article_count"] >= MIN_TOPIC_ARTICLE_COUNT
        and group["source_count"] >= MIN_TOPIC_SOURCE_COUNT
    ]
    candidates = select_topic_representatives(
        eligible_groups,
        max_candidates_per_topic=max_related_articles_per_topic,
    )
    attach_article_urls(candidates, articles)
    ordered_topics = sorted(candidates, key=topic_selection_key)
    selected_topics = ordered_topics[:max_topics]
    related_article_ids = selected_topic_article_ids(selected_topics)
    summary_article_ids = _summary_article_ids_by_source_diversity(
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
    result = WeeklyTopicSelectionResult(
        selected_topics=selected_topics,
        representative_article_ids=representative_article_ids,
        related_article_ids=related_article_ids,
        summary_article_ids=summary_article_ids,
        cluster_count=len(grouped),
        topic_candidate_count=len(ordered_topics),
    )
    LOGGER.info(
        "weekly topic selection end: cluster_count=%d eligible_candidate_count=%d "
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
    """Weekly 전용 threshold와 기사·Topic 상한의 유효 범위를 검증한다."""

    if not 0 <= similarity_threshold <= 1:
        raise ValueError("similarity_threshold must be between zero and one")
    if max_topics < 1:
        raise ValueError("max_topics must be positive")
    if max_related_articles_per_topic < MIN_TOPIC_ARTICLE_COUNT:
        raise ValueError(
            "max_related_articles_per_topic must be at least weekly minimum"
        )
    if max_summary_articles_per_topic < 1:
        raise ValueError("max_summary_articles_per_topic must be positive")
    if max_summary_articles_per_topic > MAX_SUMMARY_EVIDENCE_COUNT:
        raise ValueError("max_summary_articles_per_topic cannot exceed 5")
    if max_summary_articles_per_topic > max_related_articles_per_topic:
        raise ValueError(
            "max_summary_articles_per_topic cannot exceed "
            "max_related_articles_per_topic"
        )


def _summary_article_ids_by_source_diversity(
    topics: list[dict[str, Any]],
    *,
    maximum: int,
) -> list[int]:
    """Topic별 대표 기사를 포함하고 출처 편중을 줄인 Summary 근거 ID를 반환한다."""

    selected_ids = []
    for topic in topics:
        selected_ids.extend(
            _summary_article_ids_for_topic_by_source_diversity(
                topic,
                maximum=maximum,
            )
        )
    return list(dict.fromkeys(selected_ids))


def _summary_article_ids_for_topic_by_source_diversity(
    topic: dict[str, Any],
    *,
    maximum: int,
) -> list[int]:
    """단일 Topic의 관련 기사에서 대표성 순서와 출처 다양성을 함께 반영한다."""

    related_articles = sorted(
        (
            article
            for article in topic["articles"]
            if article.get("representative_candidate_rank") is not None
        ),
        key=_related_article_key,
    )
    selected: list[dict[str, Any]] = []
    selected_sources: set[str] = set()
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    while len(selected) < maximum:
        winner = _next_summary_article(
            related_articles,
            selected_sources=selected_sources,
            seen_urls=seen_urls,
            seen_titles=seen_titles,
            prefer_new_source=bool(selected_sources),
        )
        if winner is None:
            winner = _next_summary_article(
                related_articles,
                selected_sources=selected_sources,
                seen_urls=seen_urls,
                seen_titles=seen_titles,
                prefer_new_source=False,
            )
        if winner is None:
            break
        selected.append(winner)
        source = str(winner.get("source") or "").strip()
        if source:
            selected_sources.add(source)
        normalized_url = _normalize_duplicate_url(winner.get("url"))
        normalized_title = _normalize_duplicate_title(winner.get("title"))
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        related_articles = [
            article for article in related_articles if article["id"] != winner["id"]
        ]

    return [int(article["id"]) for article in selected]


def _next_summary_article(
    articles: list[dict[str, Any]],
    *,
    selected_sources: set[str],
    seen_urls: set[str],
    seen_titles: set[str],
    prefer_new_source: bool,
) -> dict[str, Any] | None:
    """중복 URL·제목을 제외하고 source 선호 조건에 맞는 다음 기사를 고른다."""

    for article in articles:
        source = str(article.get("source") or "").strip()
        if prefer_new_source and source and source in selected_sources:
            continue
        normalized_url = _normalize_duplicate_url(article.get("url"))
        normalized_title = _normalize_duplicate_title(article.get("title"))
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        return article
    return None


def _related_article_key(article: dict[str, Any]) -> tuple:
    """대표성 순위, 유사도와 ID로 관련 기사 선택 순서를 고정한다."""

    return (
        article["representative_candidate_rank"],
        -float(article.get("similarity_to_seed") or 0.0),
        article["id"],
    )


def _normalize_duplicate_url(value: object) -> str:
    """URL 중복 비교를 위해 앞뒤 공백만 제거하고 path 대소문자는 보존한다."""

    return str(value or "").strip()


def _normalize_duplicate_title(value: object) -> str:
    """제목 중복 비교를 위해 공백을 정규화하고 대소문자를 무시한다."""

    return " ".join(str(value or "").split()).casefold()
