import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.topic_grouping import group_articles
from app.utils.topic_representatives import (
    render_representative_report,
    select_topic_representatives,
)
from scripts.analyze_topic_groups import (
    DEFAULT_MAX_ARTICLES,
    MAX_PROVIDER_ARTICLES,
    SUPPORTED_WINDOWS,
    build_provider_estimate,
    create_database_engine,
    create_embedding_provider,
    get_articles,
    prepare_articles,
)


DEFAULT_SIMILARITY_THRESHOLD = 0.70
DEFAULT_MAX_CANDIDATES_PER_TOPIC = 3


def parse_args(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Read-only topic representative candidate analysis.",
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
    parser.add_argument("--max-articles", type=int, default=None)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument(
        "--max-candidates-per-topic",
        type=int,
        default=DEFAULT_MAX_CANDIDATES_PER_TOPIC,
    )
    parser.add_argument("--report-path", type=Path)
    parser.add_argument(
        "--include-singletons",
        action="store_true",
        help="Include singleton topic details in the markdown report.",
    )
    parser.add_argument("--use-embedding-provider", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Read-only analysis mode (always enabled).",
    )
    args = parser.parse_args(argv)

    if args.max_articles is not None and args.max_articles <= 0:
        parser.error("--max-articles must be greater than zero")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    if args.max_candidates_per_topic <= 0:
        parser.error("--max-candidates-per-topic must be greater than zero")
    if args.use_embedding_provider:
        import os

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


def analyze(rows, args, provider=None):
    articles = prepare_articles(rows)
    embedding_provider = provider or create_embedding_provider(args)
    texts = [article["embedding_input"] for article in articles]
    embeddings = embedding_provider.embed(texts)
    topics = group_articles(
        articles,
        embeddings,
        similarity_threshold=args.similarity_threshold,
    )
    topic_candidates = select_topic_representatives(
        topics,
        max_candidates_per_topic=args.max_candidates_per_topic,
    )
    representative_count = sum(
        topic["representative_candidate_count"] for topic in topic_candidates
    )
    return {
        "analysis": {
            "dry_run": True,
            "time_basis": args.time_basis,
            "window_hours": None if args.all else args.window_hours,
            "max_articles": args.effective_max_articles,
            "article_count": len(articles),
            "topic_candidate_count": len(topic_candidates),
            "multi_article_topic_count": sum(
                topic["article_count"] > 1 for topic in topic_candidates
            ),
            "representative_candidate_count": representative_count,
            "similarity_threshold": args.similarity_threshold,
            "max_candidates_per_topic": args.max_candidates_per_topic,
            "embedding_provider": (
                "openai" if args.use_embedding_provider else "deterministic"
            ),
            "embedding_model": embedding_provider.model,
            "embedding_provider_enabled": args.use_embedding_provider,
            "db_write_performed": False,
        },
        "provider_call_estimate": (
            build_provider_estimate(texts, embedding_provider.model)
            if args.use_embedding_provider
            else None
        ),
        "topic_candidates": topic_candidates,
    }


def main():
    args = parse_args()
    engine = create_database_engine()
    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        rows = get_articles(connection, args)

    result = analyze(rows, args)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(
            render_representative_report(
                result,
                include_singletons=args.include_singletons,
            ),
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
