import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.utils.url_normalization import make_title_hash, normalize_title, normalize_url


SUPPORTED_WINDOWS = (24, 72, 168)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read-only duplicate candidate analysis for stored articles.",
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
        "--max-groups",
        type=int,
        default=20,
        help="Maximum groups to print per candidate type (default: 20).",
    )
    args = parser.parse_args()

    if args.max_groups < 0:
        parser.error("--max-groups must be zero or greater")

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
            a.url,
            a.published_at,
            a.created_at
        from articles a
        left join sources s on s.id = a.source_id
        {where_sql}
        order by {timestamp_expression} desc nulls last, a.id desc
    """)

    return connection.execute(query, params).mappings().all()


def build_candidate_groups(articles, key_name):
    groups = defaultdict(list)

    for article in articles:
        key = article[key_name]
        if key:
            groups[key].append(article)

    return [group for group in groups.values() if len(group) > 1]


def serialize_article(article):
    return {
        "id": article["id"],
        "source_id": article["source_id"],
        "source": article["source"],
        "title": article["title"],
        "url": article["url"],
        "published_at": article["published_at"],
        "created_at": article["created_at"],
    }


def serialize_groups(groups, key_name, max_groups):
    sorted_groups = sorted(
        groups,
        key=lambda group: (-len(group), min(article["id"] for article in group)),
    )

    return [
        {
            key_name: group[0][key_name],
            "article_count": len(group),
            "articles": [serialize_article(article) for article in group],
        }
        for group in sorted_groups[:max_groups]
    ]


def analyze(articles, args):
    analyzed_articles = []
    invalid_url_count = 0
    missing_title_count = 0

    for row in articles:
        article = dict(row)
        article["normalized_url"] = normalize_url(article["url"])
        article["normalized_title"] = normalize_title(article["title"])
        article["title_hash"] = make_title_hash(article["title"])

        if article["normalized_url"] is None:
            invalid_url_count += 1
        if article["normalized_title"] is None:
            missing_title_count += 1

        analyzed_articles.append(article)

    url_groups = build_candidate_groups(analyzed_articles, "normalized_url")
    title_groups = build_candidate_groups(analyzed_articles, "title_hash")

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
            "invalid_or_missing_url_count": invalid_url_count,
            "invalid_or_missing_title_count": missing_title_count,
            "normalized_url_candidate_group_count": len(url_groups),
            "normalized_url_candidate_article_count": sum(map(len, url_groups)),
            "title_hash_candidate_group_count": len(title_groups),
            "title_hash_candidate_article_count": sum(map(len, title_groups)),
            "printed_group_limit_per_type": args.max_groups,
        },
        "normalized_url_candidates": serialize_groups(
            url_groups,
            "normalized_url",
            args.max_groups,
        ),
        "title_hash_candidates": serialize_groups(
            title_groups,
            "title_hash",
            args.max_groups,
        ),
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
