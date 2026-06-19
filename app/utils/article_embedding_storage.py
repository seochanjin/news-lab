"""Store and reuse article embeddings in PostgreSQL with pgvector."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Sequence

from sqlalchemy import text

from app.utils.article_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingProvider,
)


DEFAULT_EMBEDDING_PROVIDER = "openai"
DEFAULT_EMBEDDING_DIMENSION = 1536
DEFAULT_SOURCE_TEXT_TYPE = "title_summary"
SUPPORTED_MODEL_DIMENSIONS = {
    DEFAULT_EMBEDDING_MODEL: DEFAULT_EMBEDDING_DIMENSION,
}

FIND_EMBEDDING_QUERY = text("""
    select id, source_text_hash
    from article_embeddings
    where article_id = :article_id
      and provider = :provider
      and model = :model
      and source_text_type = :source_text_type
""")

UPSERT_EMBEDDING_QUERY = text("""
    insert into article_embeddings (
        article_id,
        embedding,
        provider,
        model,
        dimension,
        source_text_type,
        source_text_hash
    )
    values (
        :article_id,
        cast(:embedding as vector),
        :provider,
        :model,
        :dimension,
        :source_text_type,
        :source_text_hash
    )
    on conflict (article_id, provider, model, source_text_type)
    do update set
        embedding = excluded.embedding,
        dimension = excluded.dimension,
        source_text_hash = excluded.source_text_hash,
        updated_at = now()
    returning (xmax = 0) as inserted
""")

SIMILAR_EMBEDDINGS_QUERY = text("""
    select
        article_id,
        1 - (embedding <=> cast(:embedding as vector)) as similarity
    from article_embeddings
    where provider = :provider
      and model = :model
      and dimension = :dimension
      and source_text_type = :source_text_type
      and (:exclude_article_id is null or article_id <> :exclude_article_id)
    order by embedding <=> cast(:embedding as vector)
    limit :limit
""")


@dataclass(frozen=True)
class EmbeddingResult:
    article_id: int
    status: str
    source_text_hash: str


def normalize_source_text(value: str | None) -> str:
    """Collapse whitespace while preserving the original letter case."""

    return " ".join((value or "").split())


def build_article_embedding_input(
    *,
    title: str | None,
    summary: str | None,
) -> str:
    fields = (
        ("title", normalize_source_text(title)),
        ("summary", normalize_source_text(summary)),
    )
    return "\n".join(f"{name}: {value}" for name, value in fields if value)


def hash_source_text(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def get_model_dimension(model: str) -> int:
    try:
        return SUPPORTED_MODEL_DIMENSIONS[model]
    except KeyError as error:
        raise ValueError(f"unsupported embedding model: {model}") from error


def vector_to_pgvector(vector: Sequence[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


def _existing_embedding(
    connection,
    *,
    article_id: int,
    provider: str,
    model: str,
    source_text_type: str,
) -> Mapping[str, object] | None:
    return (
        connection.execute(
            FIND_EMBEDDING_QUERY,
            {
                "article_id": article_id,
                "provider": provider,
                "model": model,
                "source_text_type": source_text_type,
            },
        )
        .mappings()
        .first()
    )


def store_article_embedding(
    connection,
    *,
    article: Mapping[str, object],
    embedding_provider: EmbeddingProvider,
    provider: str = DEFAULT_EMBEDDING_PROVIDER,
    source_text_type: str = DEFAULT_SOURCE_TEXT_TYPE,
    expected_dimension: int | None = None,
) -> EmbeddingResult:
    article_id = int(article["id"])
    source_text = build_article_embedding_input(
        title=article.get("title"),
        summary=article.get("summary"),
    )
    if not source_text:
        raise ValueError(f"article {article_id} has no embedding source text")

    source_text_hash = hash_source_text(source_text)
    existing = _existing_embedding(
        connection,
        article_id=article_id,
        provider=provider,
        model=embedding_provider.model,
        source_text_type=source_text_type,
    )
    if existing and existing["source_text_hash"] == source_text_hash:
        return EmbeddingResult(article_id, "reused", source_text_hash)

    dimension = expected_dimension or get_model_dimension(embedding_provider.model)
    embeddings = embedding_provider.embed([source_text])
    if len(embeddings) != 1:
        raise ValueError(
            f"embedding response count mismatch: expected 1, got {len(embeddings)}"
        )
    embedding = embeddings[0]
    if len(embedding) != dimension:
        raise ValueError(
            "embedding dimension mismatch: "
            f"expected {dimension}, got {len(embedding)}"
        )

    params = {
        "article_id": article_id,
        "embedding": vector_to_pgvector(embedding),
        "provider": provider,
        "model": embedding_provider.model,
        "dimension": dimension,
        "source_text_type": source_text_type,
        "source_text_hash": source_text_hash,
    }
    upsert_result = (
        connection.execute(UPSERT_EMBEDDING_QUERY, params).mappings().first()
    )
    if upsert_result is None:
        raise RuntimeError("embedding upsert did not return a result")
    status = "created" if upsert_result["inserted"] else "updated"

    return EmbeddingResult(article_id, status, source_text_hash)


def find_similar_article_embeddings(
    connection,
    *,
    embedding: Sequence[float],
    provider: str,
    model: str,
    dimension: int,
    source_text_type: str,
    limit: int = 5,
    exclude_article_id: int | None = None,
) -> list[Mapping[str, object]]:
    if len(embedding) != dimension:
        raise ValueError(
            "query embedding dimension mismatch: "
            f"expected {dimension}, got {len(embedding)}"
        )
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    return list(
        connection.execute(
            SIMILAR_EMBEDDINGS_QUERY,
            {
                "embedding": vector_to_pgvector(embedding),
                "provider": provider,
                "model": model,
                "dimension": dimension,
                "source_text_type": source_text_type,
                "exclude_article_id": exclude_article_id,
                "limit": limit,
            },
        )
        .mappings()
        .all()
    )
