"""기간별 Topic pipeline이 공유하는 결정론적 기사 선정 정책을 정의한다.

Clustering과 대표 후보 점수 계산이 끝난 Topic을 정렬하고, 관련 기사 순서를
유지한 ID 목록과 URL·제목 중복을 제거한 Summary 근거 기사 부분집합을 만든다.
입력 dict에 URL metadata를 보강하는 것 외에는 외부 상태를 변경하지 않으며
provider 호출, 원문 조회와 DB 쓰기는 담당하지 않는다.
"""

from datetime import timezone
from typing import Any


def topic_selection_key(topic: dict[str, Any]) -> tuple:
    """Topic 규모, 출처 수, 평균 유사도와 최신 시각 순의 정렬 key를 반환한다."""

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


def attach_article_urls(
    topics: list[dict[str, Any]],
    articles: list[dict[str, Any]],
) -> None:
    """Grouping 직렬화에서 제외된 원본 URL을 기사 ID 기준으로 Topic에 보강한다."""

    url_by_article_id = {
        article["id"]: article.get("url")
        for article in articles
    }
    for topic in topics:
        for article in topic["articles"]:
            article["url"] = url_by_article_id.get(article["id"])


def selected_topic_article_ids(topics: list[dict[str, Any]]) -> list[int]:
    """Topic별 관련 기사 순서를 유지하면서 중복 없는 ID 목록을 반환한다."""

    return list(
        dict.fromkeys(
            int(article["id"])
            for topic in topics
            for article in topic["articles"]
            if article.get("representative_candidate_rank") is not None
        )
    )


def summary_topic_article_ids(
    topics: list[dict[str, Any]],
    *,
    maximum: int,
) -> list[int]:
    """대표 기사를 포함하고 URL·제목 중복을 제거한 Summary 근거 ID를 반환한다."""

    if maximum < 1:
        raise ValueError("maximum must be positive")
    selected_ids = []
    for topic in topics:
        selected_ids.extend(_summary_article_ids_for_topic(topic, maximum=maximum))
    return list(dict.fromkeys(selected_ids))


def _summary_article_ids_for_topic(
    topic: dict[str, Any],
    *,
    maximum: int,
) -> list[int]:
    """단일 Topic의 관련 기사 순위에서 중복 없는 Summary 근거 기사를 선택한다."""

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
        selected_ids.append(int(article["id"]))
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        if len(selected_ids) >= maximum:
            break
    return selected_ids


def _normalize_duplicate_url(value: object) -> str:
    """URL 중복 비교를 위해 앞뒤 공백만 제거하고 path 대소문자는 보존한다."""

    return str(value or "").strip()


def _normalize_duplicate_title(value: object) -> str:
    """제목 중복 비교를 위해 공백을 정규화하고 대소문자를 무시한다."""

    return " ".join(str(value or "").split()).casefold()


def _as_utc(value):
    """날짜 값을 Topic 간 최신성 비교에 사용할 UTC aware datetime으로 바꾼다."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
