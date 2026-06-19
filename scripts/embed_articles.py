"""Create or reuse stored article embeddings in small batches."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping

from sqlalchemy import bindparam, create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.article_embedding_storage import (
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_SOURCE_TEXT_TYPE,
    get_model_dimension,
    store_article_embedding,
)
from app.utils.article_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    OpenAIEmbeddingProvider,
)


DEFAULT_LIMIT = 10
MAX_LIMIT = 100

SELECT_ARTICLES_QUERY = text("""
    select id, title, summary
    from articles
    where (
        :use_article_ids = false
        or id in :article_ids
    )
    order by created_at desc nulls last, id desc
    limit :limit
""").bindparams(bindparam("article_ids", expanding=True))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Store or reuse pgvector embeddings for a small article batch.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum selected articles (default: {DEFAULT_LIMIT}, max: {MAX_LIMIT}).",
    )
    parser.add_argument(
        "--article-id",
        action="append",
        type=int,
        dest="article_ids",
        help="Select a specific article ID. May be repeated.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Select articles without calling the provider or writing embeddings.",
    )
    args = parser.parse_args(argv)
    if args.limit <= 0:
        parser.error("--limit must be greater than zero")
    if args.limit > MAX_LIMIT:
        parser.error(f"--limit cannot exceed {MAX_LIMIT}")
    return args


def create_database_engine():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


def select_articles(connection, *, limit: int, article_ids: list[int] | None):
    selected_ids = article_ids or []
    return (
        connection.execute(
            SELECT_ARTICLES_QUERY,
            {
                "use_article_ids": bool(selected_ids),
                "article_ids": selected_ids,
                "limit": limit,
            },
        )
        .mappings()
        .all()
    )


def process_selected_articles(
    rows,
    process_article: Callable[[Mapping[str, object]], str],
) -> tuple[dict[str, int], list[dict[str, object]]]:
    summary = {
        "selected": len(rows),
        "created": 0,
        "updated": 0,
        "reused": 0,
        "failed": 0,
    }
    failures = []
    for row in rows:
        try:
            status = process_article(row)
            if status not in {"created", "updated", "reused"}:
                raise ValueError(f"unsupported embedding status: {status}")
            summary[status] += 1
        except Exception as error:  # Batch processing continues per article.
            summary["failed"] += 1
            failures.append(
                {
                    "article_id": row.get("id"),
                    "error": str(error),
                }
            )
    return summary, failures


def _create_provider() -> OpenAIEmbeddingProvider:
    api_key = os.getenv("OPENAI_EMBEDDING_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_EMBEDDING_API_KEY environment variable is not set")
    model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    get_model_dimension(model)
    return OpenAIEmbeddingProvider(api_key=api_key, model=model)


def main(argv=None):
    args = parse_args(argv)
    engine = create_database_engine()
    with engine.connect() as connection:
        rows = select_articles(
            connection,
            limit=args.limit,
            article_ids=args.article_ids,
        )

    if args.dry_run:
        summary = {
            "selected": len(rows),
            "created": 0,
            "updated": 0,
            "reused": 0,
            "failed": 0,
        }
        print(json.dumps({"dry_run": True, **summary}, ensure_ascii=False))
        return 0

    embedding_provider = _create_provider()
    expected_dimension = get_model_dimension(embedding_provider.model)

    def process_article(row):
        with engine.begin() as connection:
            return store_article_embedding(
                connection,
                article=row,
                embedding_provider=embedding_provider,
                provider=DEFAULT_EMBEDDING_PROVIDER,
                source_text_type=DEFAULT_SOURCE_TEXT_TYPE,
                expected_dimension=expected_dimension,
            ).status

    summary, failures = process_selected_articles(rows, process_article)
    print(
        json.dumps(
            {"dry_run": False, **summary, "failures": failures},
            ensure_ascii=False,
        )
    )
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
