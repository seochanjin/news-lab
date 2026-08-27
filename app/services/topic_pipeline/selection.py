"""기간별 Topic pipeline이 공유하는 결정론적 기사 선정 정책을 정의한다.

Clustering과 대표 후보 점수 계산이 끝난 Topic을 정렬하고, 관련 기사 순서를
유지한 ID 목록과 URL·제목 중복을 제거한 Summary 근거 기사 부분집합을 만든다.
입력 dict에 URL metadata를 보강하는 것 외에는 외부 상태를 변경하지 않으며
provider 호출, 원문 조회와 DB 쓰기는 담당하지 않는다.
"""

from datetime import datetime, timezone
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


def pick_summary_representative_article_id(topic_articles, used_articles):
    """Summary 근거로 실제 사용된 기사 중에서 대표 기사를 고른다.

    개념이 둘로 나뉜다.

    - clustering 대표(``representative_candidate_rank`` 1)는 기사 유사도로 정해진다.
      원문 확보 여부와 무관하다.
    - Summary 대표는 요약의 근거가 되므로 원문이 반드시 있어야 한다.

    기존 구현은 후자에 전자를 그대로 사용했다. 그 결과 rank 1 기사의 원문 추출이
    실패하면 같은 Topic의 다른 근거 기사에 원문이 남아 있어도 Topic 전체가 폐기됐다.
    실제로 폐기 원인의 대부분은 본문이 없는 영상 포스트가 rank 1로 선정된 경우였다.
    영상 포스트에는 뽑을 본문이 없으므로 추출은 앞으로도 계속 실패한다.

    따라서 rank 순서를 존중하되 ``used_articles``에 포함된 첫 기사를 선택한다.

    ``used_articles``가 비어 있으면 None을 반환한다. 이때는 근거가 하나도 없으므로
    호출부의 검증이 Topic을 실패로 처리한다. 근거 없이 요약하지 않는다는 계약은
    그대로 유지된다.
    """

    used_ids = set()
    for article in used_articles:
        used_ids.add(int(article["article_id"]))

    if not used_ids:
        return None

    ranked_articles = []
    for article in topic_articles:
        if article.get("representative_candidate_rank") is None:
            continue
        ranked_articles.append(article)

    ranked_articles.sort(
        key=lambda article: (
            article["representative_candidate_rank"],
            article["id"],
        )
    )

    for article in ranked_articles:
        article_id = int(article["id"])
        if article_id in used_ids:
            return article_id

    # rank가 없는 기사만 원문을 갖고 있는 경우다. used_articles는 호출부에서
    # 이미 시간순으로 정렬되므로 가장 이른 기사를 대표로 사용한다.
    return int(used_articles[0]["article_id"])


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


def _as_utc(value: datetime | None) -> datetime | None:
    """날짜 값을 Topic 간 최신성 비교에 사용할 UTC aware datetime으로 바꾼다."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
