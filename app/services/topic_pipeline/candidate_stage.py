"""기사 window 후보와 기존 article embedding을 read-only로 결합한다.

기간별 Topic pipeline이 주입한 명시적 `[window_start, window_end)` 범위와 기사
상한을 기준으로 후보를 조회한 뒤, 저장된 `article_embeddings` row의 metadata,
source hash와 vector 차원을 검증한다. 유효한 vector만 caller가 지정한 결과
model로 반환하며 embedding provider 호출이나 DB 쓰기는 수행하지 않는다.
"""

import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

from sqlalchemy import text

from app.utils.article_embedding_storage import (
    DEFAULT_EMBEDDING_DIMENSION,
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_SOURCE_TEXT_TYPE,
    build_article_embedding_input,
    hash_source_text,
    pgvector_to_vector,
)
from app.utils.article_embeddings import DEFAULT_EMBEDDING_MODEL
from scripts.analyze_topic_groups import prepare_articles


T = TypeVar("T")

CANDIDATE_QUERY = text("""
select
    a.id,
    s.name as source,
    a.title,
    a.url,
    a.summary,
    a.category as source_category,
    a.published_at,
    a.created_at,
    coalesce(a.published_at, a.created_at) as analysis_time
from articles a
left join sources s on s.id = a.source_id
where coalesce(a.published_at, a.created_at) >= :window_start
  and coalesce(a.published_at, a.created_at) < :window_end
order by coalesce(a.published_at, a.created_at) desc, a.id desc
limit :max_articles
""")

EMBEDDING_QUERY = text("""
select
    id,
    article_id,
    provider,
    model,
    dimension,
    source_text_type,
    source_text_hash,
    embedding::text as embedding,
    updated_at
from article_embeddings
where article_id = any(:article_ids)
order by article_id asc, updated_at desc, id desc
""")

MISSING_ROW = "missing_row"
STALE_HASH = "stale_hash"
INCOMPATIBLE_METADATA = "incompatible_metadata"
INVALID_VECTOR = "invalid_vector"


def load_stored_embedding_candidates(
    connection,
    *,
    window_start,
    window_end,
    max_articles: int,
    result_factory: Callable[[list[tuple[dict, tuple[float, ...]]], list[dict]], T],
    provider: str = DEFAULT_EMBEDDING_PROVIDER,
    model: str = DEFAULT_EMBEDDING_MODEL,
    dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    source_text_type: str = DEFAULT_SOURCE_TEXT_TYPE,
) -> T:
    """Window 후보를 조회하고 호환되는 저장 embedding만 결과 model로 감싼다.

    Args:
        connection: SQLAlchemy 호환 read connection.
        window_start/window_end: 후보 조회에 사용할 timezone-aware 반열림 범위.
        max_articles: 결정론적 정렬 뒤 조회할 최대 기사 수.
        result_factory: 검증된 기사·vector 목록과 누락 목록을 받을 결과 생성자.
        provider/model/dimension/source_text_type: 허용할 저장 embedding 계약.

    Returns:
        `result_factory`가 만든 기간별 후보 stage 결과.

    Raises:
        ValueError: 기사 상한이나 embedding metadata 설정이 유효하지 않은 경우.
    """

    _validate_settings(
        max_articles=max_articles,
        provider=provider,
        model=model,
        dimension=dimension,
        source_text_type=source_text_type,
    )
    rows = list(
        connection.execute(
            CANDIDATE_QUERY,
            {
                "window_start": window_start,
                "window_end": window_end,
                "max_articles": max_articles,
            },
        )
        .mappings()
        .all()
    )
    articles = prepare_articles(rows)
    embedding_rows = _load_embedding_rows(
        connection,
        [int(article["id"]) for article in articles],
    )
    matched, missing = _match_stored_embeddings(
        articles,
        embedding_rows,
        provider=provider,
        model=model,
        dimension=dimension,
        source_text_type=source_text_type,
    )
    return result_factory(matched, missing)


def _validate_settings(
    *,
    max_articles: int,
    provider: str,
    model: str,
    dimension: int,
    source_text_type: str,
) -> None:
    """후보 상한과 호환 embedding metadata가 비어 있거나 잘못되지 않게 한다."""

    if max_articles < 1:
        raise ValueError("max_articles must be positive")
    if dimension < 1:
        raise ValueError("dimension must be positive")
    for field_name, value in (
        ("provider", provider),
        ("model", model),
        ("source_text_type", source_text_type),
    ):
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must not be blank")


def _load_embedding_rows(connection, article_ids: list[int]) -> list[Mapping]:
    """후보 기사들의 저장 embedding row를 한 번에 조회한다."""

    if not article_ids:
        return []
    return list(
        connection.execute(
            EMBEDDING_QUERY,
            {"article_ids": article_ids},
        )
        .mappings()
        .all()
    )


def _match_stored_embeddings(
    articles: Sequence[dict],
    embedding_rows: Sequence[Mapping],
    *,
    provider: str,
    model: str,
    dimension: int,
    source_text_type: str,
) -> tuple[list[tuple[dict, tuple[float, ...]]], list[dict]]:
    """기사 순서를 유지하며 저장 row를 검증하고 누락 사유를 분류한다."""

    rows_by_article: dict[int, list[Mapping]] = defaultdict(list)
    for row in embedding_rows:
        rows_by_article[int(row["article_id"])].append(row)

    matched = []
    missing = []
    for article in articles:
        article_id = int(article["id"])
        article_rows = rows_by_article.get(article_id, [])
        compatible = _find_compatible_row(
            article_rows,
            provider=provider,
            model=model,
            dimension=dimension,
            source_text_type=source_text_type,
        )
        if compatible is None:
            reason = MISSING_ROW if not article_rows else INCOMPATIBLE_METADATA
            missing.append({"article_id": article_id, "reason": reason})
            continue

        source_text = build_article_embedding_input(
            title=article.get("title"),
            summary=article.get("summary"),
        )
        if compatible["source_text_hash"] != hash_source_text(source_text):
            missing.append({"article_id": article_id, "reason": STALE_HASH})
            continue

        vector = _validated_vector(compatible["embedding"], dimension)
        if vector is None:
            missing.append({"article_id": article_id, "reason": INVALID_VECTOR})
            continue
        matched.append((article, vector))

    return matched, missing


def _find_compatible_row(
    rows: Sequence[Mapping],
    *,
    provider: str,
    model: str,
    dimension: int,
    source_text_type: str,
) -> Mapping | None:
    """요구 metadata가 모두 일치하는 최신 저장 row를 반환한다."""

    return next(
        (
            row
            for row in rows
            if row["provider"] == provider
            and row["model"] == model
            and int(row["dimension"]) == dimension
            and row["source_text_type"] == source_text_type
        ),
        None,
    )


def _validated_vector(value: object, dimension: int) -> tuple[float, ...] | None:
    """pgvector text를 유한한 고정 차원 tuple로 변환하며 오류는 누락으로 처리한다."""

    try:
        vector = pgvector_to_vector(str(value))
    except (TypeError, ValueError):
        return None
    if len(vector) != dimension or any(not math.isfinite(item) for item in vector):
        return None
    return vector

