import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.rss_sources import RSS_SOURCES
from app.utils.article_classification import classify_article
from app.utils.article_embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    DeterministicHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_input,
    estimate_tokens,
)
from app.utils.topic_grouping import group_articles
from app.utils.topic_quality import (
    compare_thresholds,
    parse_thresholds,
    render_markdown_report,
    summarize_comparisons,
)


SUPPORTED_WINDOWS = (24, 72, 168)
DEFAULT_MAX_ARTICLES = 100
MAX_PROVIDER_ARTICLES = 200
DEFAULT_SIMILARITY_THRESHOLD = 0.72
DEFAULT_COST_PER_MILLION_TOKENS_USD = 0.02
SOURCE_LANGUAGE_BY_NAME = {
    source["name"]: source["language"]
    for source in RSS_SOURCES
    if source.get("language")
}

PUBLISHED_WINDOW_QUERY = text("""
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
    where coalesce(a.published_at, a.created_at) >=
        now() - (:window_hours * interval '1 hour')
    order by coalesce(a.published_at, a.created_at) desc nulls last, a.id desc
    limit :max_articles
""")

PUBLISHED_ALL_QUERY = text("""
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
    order by coalesce(a.published_at, a.created_at) desc nulls last, a.id desc
    limit :max_articles
""")

CREATED_WINDOW_QUERY = text("""
    select
        a.id,
        s.name as source,
        a.title,
        a.url,
        a.summary,
        a.category as source_category,
        a.published_at,
        a.created_at,
        a.created_at as analysis_time
    from articles a
    left join sources s on s.id = a.source_id
    where a.created_at >= now() - (:window_hours * interval '1 hour')
    order by a.created_at desc nulls last, a.id desc
    limit :max_articles
""")

CREATED_ALL_QUERY = text("""
    select
        a.id,
        s.name as source,
        a.title,
        a.url,
        a.summary,
        a.category as source_category,
        a.published_at,
        a.created_at,
        a.created_at as analysis_time
    from articles a
    left join sources s on s.id = a.source_id
    order by a.created_at desc nulls last, a.id desc
    limit :max_articles
""")

ARTICLE_QUERIES = {
    ("published", False): PUBLISHED_WINDOW_QUERY,
    ("published", True): PUBLISHED_ALL_QUERY,
    ("created", False): CREATED_WINDOW_QUERY,
    ("created", True): CREATED_ALL_QUERY,
}


def parse_args(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Read-only embedding topic grouping candidate analysis.",
    )
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument(
        "--window-hours",
        type=int,
        choices=SUPPORTED_WINDOWS,
        default=24,
    )
    window_group.add_argument("--all", action="store_true")
    parser.add_argument(
        "--time-basis",
        choices=("published", "created"),
        default="published",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=None,
        help=(
            f"Maximum articles to analyze (local default: {DEFAULT_MAX_ARTICLES}; "
            "required for provider use)."
        ),
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        help="Comma-separated thresholds for quality comparison.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="Optional markdown path for a human-reviewable quality report.",
    )
    parser.add_argument("--use-embedding-provider", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Read-only JSON analysis mode (always enabled).",
    )
    args = parser.parse_args(argv)

    if args.max_articles is not None and args.max_articles <= 0:
        parser.error("--max-articles must be greater than zero")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    if args.thresholds:
        try:
            args.quality_thresholds = parse_thresholds(args.thresholds)
        except ValueError as error:
            parser.error(str(error))
    else:
        args.quality_thresholds = (args.similarity_threshold,)
    if args.use_embedding_provider:
        if args.max_articles is None:
            parser.error(
                "--use-embedding-provider requires an explicit --max-articles limit"
            )
        if args.max_articles > MAX_PROVIDER_ARTICLES:
            parser.error(
                f"provider --max-articles cannot exceed {MAX_PROVIDER_ARTICLES}"
            )
        if not os.getenv("OPENAI_EMBEDDING_API_KEY"):
            parser.error(
                "--use-embedding-provider requires OPENAI_EMBEDDING_API_KEY"
            )

    args.effective_max_articles = args.max_articles or DEFAULT_MAX_ARTICLES
    return args


def create_database_engine():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


def get_articles(connection, args):
    try:
        query = ARTICLE_QUERIES[(args.time_basis, args.all)]
    except KeyError as error:
        raise ValueError(f"unsupported time_basis: {args.time_basis!r}") from error

    params = {"max_articles": args.effective_max_articles}
    if not args.all:
        params["window_hours"] = args.window_hours
    return connection.execute(query, params).mappings().all()


def prepare_articles(rows):
    articles = []
    for row in rows:
        article = dict(row)
        classification = classify_article(
            title=article["title"],
            summary=article["summary"],
            source_category=article["source_category"],
            source_language=SOURCE_LANGUAGE_BY_NAME.get(article["source"]),
            article_time=article["analysis_time"],
        )
        article.update(classification)
        article["topic_category"] = (
            article["rule_category"]
            if article["rule_category"] != "unknown"
            else article["base_category"]
        )
        article["embedding_input"] = build_embedding_input(
            title=article["title"],
            summary=article["summary"],
            source=article["source"],
            source_category=article["base_category"],
            rule_category=article["rule_category"],
        )
        articles.append(article)
    return articles


def create_embedding_provider(args):
    if not args.use_embedding_provider:
        return DeterministicHashEmbeddingProvider()
    return OpenAIEmbeddingProvider(
        api_key=os.environ["OPENAI_EMBEDDING_API_KEY"],
        model=os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
    )


def build_provider_estimate(texts, model):
    tokens = estimate_tokens(texts)
    cost_rate = float(
        os.getenv(
            "OPENAI_EMBEDDING_COST_PER_MILLION_TOKENS_USD",
            DEFAULT_COST_PER_MILLION_TOKENS_USD,
        )
    )
    return {
        "model": model,
        "article_count": len(texts),
        "estimated_tokens": tokens,
        "estimated_cost_usd": round(tokens / 1_000_000 * cost_rate, 6),
        "cost_rate_usd_per_million_tokens": cost_rate,
    }


def analyze(rows, args, provider=None):
    articles = prepare_articles(rows)
    embedding_provider = provider or create_embedding_provider(args)
    texts = [article["embedding_input"] for article in articles]
    provider_estimate = (
        build_provider_estimate(texts, embedding_provider.model)
        if args.use_embedding_provider
        else None
    )
    embeddings = embedding_provider.embed(texts)
    quality_thresholds = getattr(
        args,
        "quality_thresholds",
        (args.similarity_threshold,),
    )
    threshold_comparison = compare_thresholds(
        articles,
        embeddings,
        quality_thresholds,
    )
    topics = group_articles(
        articles,
        embeddings,
        similarity_threshold=args.similarity_threshold,
    )
    deterministic_hash_comparison = None
    if args.use_embedding_provider:
        local_embeddings = DeterministicHashEmbeddingProvider().embed(texts)
        deterministic_hash_comparison = summarize_comparisons(
            compare_thresholds(articles, local_embeddings, quality_thresholds)
        )
    return {
        "analysis": {
            "dry_run": True,
            "time_basis": args.time_basis,
            "window_hours": None if args.all else args.window_hours,
            "max_articles": args.effective_max_articles,
            "article_count": len(articles),
            "topic_candidate_count": len(topics),
            "similarity_threshold": args.similarity_threshold,
            "quality_thresholds": list(quality_thresholds),
            "embedding_model": embedding_provider.model,
            "embedding_provider_enabled": args.use_embedding_provider,
            "db_write_performed": False,
        },
        "provider_call_estimate": provider_estimate,
        "threshold_comparison": threshold_comparison,
        "deterministic_hash_comparison": deterministic_hash_comparison,
        "topic_candidates": topics,
    }


def main():
    args = parse_args()
    engine = create_database_engine()
    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        rows = get_articles(connection, args)

    if args.use_embedding_provider:
        articles = prepare_articles(rows)
        estimate = build_provider_estimate(
            [article["embedding_input"] for article in articles],
            os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        )
        print(json.dumps({"provider_call_estimate": estimate}, ensure_ascii=False))

    result = analyze(rows, args)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(
            render_markdown_report(result),
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
