import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.rss_sources import RSS_SOURCES
from app.utils.article_classification import classify_article


SUPPORTED_WINDOWS = (24, 72, 168)
SOURCE_LANGUAGE_BY_NAME = {
    source["name"]: source["language"]
    for source in RSS_SOURCES
    if source.get("language")
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read-only lightweight classification analysis for articles.",
    )
    window_group = parser.add_mutually_exclusive_group()
    window_group.add_argument(
        "--window-hours",
        type=int,
        choices=SUPPORTED_WINDOWS,
        default=24,
        help="Analyze articles in a supported recent window (default: 24).",
    )
    window_group.add_argument(
        "--all",
        action="store_true",
        help="Analyze all stored articles.",
    )
    parser.add_argument(
        "--time-basis",
        choices=("published", "created"),
        default="published",
        help=(
            "published uses published_at with created_at fallback; "
            "created uses collection time only (default: published)."
        ),
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="Maximum mismatch and importance examples to print (default: 5).",
    )
    args = parser.parse_args()

    if args.max_examples < 0:
        parser.error("--max-examples must be zero or greater")

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


def get_articles(connection, all_articles: bool, window_hours: int, time_basis: str):
    timestamp_expression = (
        "coalesce(a.published_at, a.created_at)"
        if time_basis == "published"
        else "a.created_at"
    )
    where_sql = ""
    params = {}

    if not all_articles:
        where_sql = (
            f"where {timestamp_expression} >= "
            "now() - (:window_hours * interval '1 hour')"
        )
        params["window_hours"] = window_hours

    query = text(f"""
        select
            a.id,
            a.source_id,
            s.name as source,
            a.title,
            a.summary,
            a.category as source_category,
            a.published_at,
            a.created_at,
            {timestamp_expression} as analysis_time
        from articles a
        left join sources s on s.id = a.source_id
        {where_sql}
        order by {timestamp_expression} desc nulls last, a.id desc
    """)

    return connection.execute(query, params).mappings().all()


def serialize_example(article):
    return {
        "id": article["id"],
        "source_id": article["source_id"],
        "source": article["source"],
        "title": article["title"],
        "source_category": article["source_category"],
        "rule_category": article["rule_category"],
        "detected_language": article["detected_language"],
        "language_basis": article["language_basis"],
        "importance_score": article["importance_score"],
        "importance_signals": article["importance_signals"],
        "published_at": article["published_at"],
        "created_at": article["created_at"],
    }


def analyze(articles, args):
    analyzed_articles = []
    source_category_counts = Counter()
    rule_category_counts = Counter()
    language_counts = Counter()
    language_basis_counts = Counter()

    for row in articles:
        article = dict(row)
        classification = classify_article(
            title=article["title"],
            summary=article["summary"],
            source_category=article["source_category"],
            source_language=SOURCE_LANGUAGE_BY_NAME.get(article["source"]),
            article_time=article["analysis_time"],
        )
        article.update(classification)
        analyzed_articles.append(article)
        source_category_counts[article["base_category"]] += 1
        rule_category_counts[article["rule_category"]] += 1
        language_counts[article["detected_language"]] += 1
        language_basis_counts[article["language_basis"]] += 1

    mismatches = [
        article
        for article in analyzed_articles
        if article["rule_category"] != "unknown"
        and article["base_category"] != article["rule_category"]
    ]
    mismatches.sort(
        key=lambda article: (
            -article["importance_score"],
            article["id"],
        )
    )
    importance_candidates = sorted(
        analyzed_articles,
        key=lambda article: (
            -article["importance_score"],
            article["id"],
        ),
    )
    importance_scores = [
        article["importance_score"]
        for article in analyzed_articles
    ]

    return {
        "analysis": {
            "mode": "all" if args.all else "window",
            "window_hours": None if args.all else args.window_hours,
            "time_basis": args.time_basis,
            "time_basis_definition": (
                "coalesce(published_at, created_at)"
                if args.time_basis == "published"
                else "created_at"
            ),
            "article_count": len(analyzed_articles),
            "source_rule_category_mismatch_count": len(mismatches),
            "printed_example_limit_per_type": args.max_examples,
            "importance_score_is_final_ranking": False,
        },
        "importance_score_summary": {
            "nonzero_count": sum(score > 0 for score in importance_scores),
            "minimum": min(importance_scores, default=0),
            "maximum": max(importance_scores, default=0),
            "average": (
                round(sum(importance_scores) / len(importance_scores), 2)
                if importance_scores
                else 0
            ),
        },
        "source_category_counts": dict(sorted(source_category_counts.items())),
        "rule_category_counts": dict(sorted(rule_category_counts.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "language_basis_counts": dict(sorted(language_basis_counts.items())),
        "source_rule_category_mismatch_examples": [
            serialize_example(article)
            for article in mismatches[: args.max_examples]
        ],
        "top_importance_candidates": [
            serialize_example(article)
            for article in importance_candidates[: args.max_examples]
        ],
    }


def main():
    args = parse_args()
    engine = create_database_engine()

    with engine.connect() as connection:
        connection.execute(text("set transaction read only"))
        articles = get_articles(
            connection=connection,
            all_articles=args.all,
            window_hours=args.window_hours,
            time_basis=args.time_basis,
        )
        result = analyze(articles, args)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
