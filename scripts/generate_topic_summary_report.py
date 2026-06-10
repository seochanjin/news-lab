import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import bindparam, create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.article_embeddings import DeterministicHashEmbeddingProvider
from app.utils.topic_grouping import group_articles
from app.utils.topic_representatives import select_topic_representatives
from app.utils.topic_summary import (
    DEFAULT_SUMMARY_MODEL,
    SUPPORTED_SUMMARY_MODELS,
    DeterministicSummaryProvider,
    OpenAISummaryProvider,
    build_topic_summary_inputs,
    render_topic_summary_report,
    summarize_topic_inputs,
)
from scripts.analyze_topic_groups import (
    DEFAULT_MAX_ARTICLES,
    DEFAULT_SIMILARITY_THRESHOLD,
    SUPPORTED_WINDOWS,
    get_articles,
    prepare_articles,
)


DEFAULT_MAX_TOPICS = 3
DEFAULT_MAX_ARTICLES_PER_TOPIC = 2
DEFAULT_MAX_RAW_CHARS_PER_ARTICLE = 3000
MAX_TOPICS = 10
MAX_ARTICLES_PER_TOPIC = 3
MAX_RAW_CHARS_PER_ARTICLE = 5000
RAW_TEXT_QUERY = text("""
    select article_id, raw_text
    from raw_articles
    where article_id in :article_ids
      and raw_text is not null
      and length(raw_text) > 0
""").bindparams(bindparam("article_ids", expanding=True))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only raw text topic summary report generator.",
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
    parser.add_argument("--max-articles", type=int, default=DEFAULT_MAX_ARTICLES)
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    parser.add_argument("--max-topics", type=int, default=DEFAULT_MAX_TOPICS)
    parser.add_argument(
        "--max-articles-per-topic",
        type=int,
        default=DEFAULT_MAX_ARTICLES_PER_TOPIC,
    )
    parser.add_argument(
        "--max-raw-chars-per-article",
        type=int,
        default=DEFAULT_MAX_RAW_CHARS_PER_ARTICLE,
    )
    parser.add_argument("--use-summary-provider", action="store_true")
    parser.add_argument("--report-path", type=Path)
    args = parser.parse_args(argv)

    if args.max_articles <= 0:
        parser.error("--max-articles must be greater than zero")
    if not 0 <= args.similarity_threshold <= 1:
        parser.error("--similarity-threshold must be between zero and one")
    _validate_limit(parser, args.max_topics, "--max-topics", MAX_TOPICS)
    _validate_limit(
        parser,
        args.max_articles_per_topic,
        "--max-articles-per-topic",
        MAX_ARTICLES_PER_TOPIC,
    )
    _validate_limit(
        parser,
        args.max_raw_chars_per_article,
        "--max-raw-chars-per-article",
        MAX_RAW_CHARS_PER_ARTICLE,
    )

    args.summary_model = os.getenv("OPENAI_SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL)
    if args.use_summary_provider:
        if args.summary_model not in SUPPORTED_SUMMARY_MODELS:
            parser.error(
                "OPENAI_SUMMARY_MODEL must be one of: "
                + ", ".join(sorted(SUPPORTED_SUMMARY_MODELS))
            )
        if not os.getenv("OPENAI_SUMMARY_API_KEY"):
            parser.error("--use-summary-provider requires OPENAI_SUMMARY_API_KEY")

    args.effective_max_articles = args.max_articles
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


def get_raw_texts(connection, article_ids):
    article_ids = list(article_ids)
    if not article_ids:
        return {}
    rows = connection.execute(
        RAW_TEXT_QUERY,
        {"article_ids": article_ids},
    ).mappings()
    return {row["article_id"]: row["raw_text"] for row in rows}


def create_summary_provider(args):
    if not args.use_summary_provider:
        return DeterministicSummaryProvider()
    return OpenAISummaryProvider(
        api_key=os.environ["OPENAI_SUMMARY_API_KEY"],
        model=args.summary_model,
    )


def generate(rows, raw_texts, args, *, summary_provider=None):
    articles = prepare_articles(rows)
    embedding_provider = DeterministicHashEmbeddingProvider()
    embeddings = embedding_provider.embed(
        [article["embedding_input"] for article in articles]
    )
    topics = group_articles(
        articles,
        embeddings,
        similarity_threshold=args.similarity_threshold,
    )
    topic_candidates = select_topic_representatives(
        topics,
        max_candidates_per_topic=args.max_articles_per_topic,
    )
    summary_inputs = build_topic_summary_inputs(
        topic_candidates,
        raw_texts,
        max_topics=args.max_topics,
        max_articles_per_topic=args.max_articles_per_topic,
        max_raw_chars_per_article=args.max_raw_chars_per_article,
    )
    provider = summary_provider or create_summary_provider(args)
    summaries = summarize_topic_inputs(summary_inputs, provider)
    return {
        "analysis": {
            "time_basis": args.time_basis,
            "window_hours": None if args.all else args.window_hours,
            "article_count": len(articles),
            "topic_count": len(summaries),
            "summarized_topic_count": sum(
                summary["status"] == "ready" for summary in summaries
            ),
            "insufficient_raw_text_topic_count": sum(
                summary["status"] == "insufficient_raw_text"
                for summary in summaries
            ),
            "similarity_threshold": args.similarity_threshold,
            "max_topics": args.max_topics,
            "max_articles_per_topic": args.max_articles_per_topic,
            "max_raw_chars_per_article": args.max_raw_chars_per_article,
            "provider": provider.provider,
            "model": provider.model,
            "summary_provider_enabled": args.use_summary_provider,
            "db_write_performed": False,
            "raw_extraction_performed": False,
        },
        "topic_summaries": summaries,
    }


def main():
    args = parse_args()
    engine = create_database_engine()
    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        rows = get_articles(connection, args)
        raw_texts = get_raw_texts(connection, (row["id"] for row in rows))

    result = generate(rows, raw_texts, args)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(
            render_topic_summary_report(result),
            encoding="utf-8",
        )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def _validate_limit(parser, value, name, maximum):
    if not 1 <= value <= maximum:
        parser.error(f"{name} must be between 1 and {maximum}")


if __name__ == "__main__":
    main()
