import os
import sys
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config.rss_sources import RSS_SOURCES

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MAX_ENTRIES_PER_SOURCE = int(os.getenv("RSS_MAX_ENTRIES_PER_SOURCE", "30"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "prepare_threshold": None,
    },
)


def parse_published_at(entry):
    published = entry.get("published") or entry.get("updated")

    if not published:
        return None

    try:
        parsed = parsedate_to_datetime(published)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed
    except Exception:
        return None


def create_crawl_run(connection):
    query = text("""
        insert into crawl_runs (status)
        values ('running')
        returning id
    """)

    return connection.execute(query).scalar_one()


def finish_crawl_run(connection, run_id, status, inserted_count, skipped_count, error_message=None):
    query = text("""
        update crawl_runs
        set
            finished_at = now(),
            status = :status,
            inserted_count = :inserted_count,
            skipped_count = :skipped_count,
            error_message = :error_message
        where id = :run_id
    """)

    connection.execute(
        query,
        {
            "run_id": run_id,
            "status": status,
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "error_message": error_message,
        },
    )


def get_table_columns(connection, table_name):
    query = text("""
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = :table_name
    """)

    rows = connection.execute(query, {"table_name": table_name}).mappings().all()
    return {row["column_name"] for row in rows}


def sync_source_registry(connection):
    columns = get_table_columns(connection, "sources")
    supported_columns = (
        "name",
        "type",
        "url",
        "feed_url",
        "category",
        "country",
        "language",
        "enabled",
        "trust_level",
    )
    db_columns = [column for column in supported_columns if column in columns]

    if "name" not in db_columns:
        raise RuntimeError("sources.name column is required")

    synced_count = 0

    for source in RSS_SOURCES:
        values = {
            "name": source["name"],
            "type": source["category"],
            "url": source["url"],
            "feed_url": source["feed_url"],
            "category": source["category"],
            "country": source["country"],
            "language": source["language"],
            "enabled": source["enabled"],
            "trust_level": source["trust_level"],
        }

        existing_id = connection.execute(
            text("select id from sources where name = :name"),
            {"name": source["name"]},
        ).scalar()

        if existing_id:
            update_columns = [column for column in db_columns if column != "name"]

            if update_columns:
                assignments = ", ".join(
                    f"{column} = :{column}" for column in update_columns
                )
                query = text(f"""
                    update sources
                    set {assignments}
                    where id = :id
                """)
                params = {column: values[column] for column in update_columns}
                params["id"] = existing_id
                connection.execute(query, params)
        else:
            column_names = ", ".join(db_columns)
            placeholders = ", ".join(f":{column}" for column in db_columns)
            query = text(f"""
                insert into sources ({column_names})
                values ({placeholders})
            """)
            connection.execute(
                query,
                {column: values[column] for column in db_columns},
            )

        synced_count += 1

    return synced_count


def get_enabled_sources(connection):
    query = text("""
        select
            id,
            name,
            type as category,
            feed_url
        from sources
        where enabled = true
          and feed_url is not null
        order by id
    """)

    rows = connection.execute(query).mappings().all()
    registry_by_name = {source["name"]: source for source in RSS_SOURCES}

    return [
        {
            **dict(row),
            "category": (
                row["category"]
                or registry_by_name.get(row["name"], {}).get("category")
                or "general"
            ),
        }
        for row in rows
    ]


def insert_article(connection, source, entry):
    title = entry.get("title")
    url = entry.get("link")
    summary = entry.get("summary")
    published_at = parse_published_at(entry)

    if not title or not url:
        return False

    query = text("""
        insert into articles (
            source_id,
            title,
            url,
            category,
            summary,
            published_at,
            tags
        )
        values (
            :source_id,
            :title,
            :url,
            :category,
            :summary,
            :published_at,
            :tags
        )
        on conflict (url) do nothing
    """)

    result = connection.execute(
        query,
        {
            "source_id": source["id"],
            "title": title,
            "url": url,
            "category": source["category"],
            "summary": summary,
            "published_at": published_at,
            "tags": ["rss"],
        },
    )

    return result.rowcount == 1


def collect():
    inserted_count = 0
    skipped_count = 0
    error_count = 0
    source_results = []

    with engine.begin() as connection:
        run_id = create_crawl_run(connection)
        synced_count = sync_source_registry(connection)

    print(f"crawl run started: {run_id}")
    print(f"registry sources synced: {synced_count}")

    try:
        with engine.begin() as connection:
            sources = get_enabled_sources(connection)

        print(f"enabled sources: {len(sources)}")

        for source in sources:
            source_result = {
                "source": source["name"],
                "parsed_count": 0,
                "inserted_count": 0,
                "skipped_count": 0,
                "error_count": 0,
            }

            try:
                print(f"collecting: {source['name']} - {source['feed_url']}")

                feed = feedparser.parse(source["feed_url"])

                if feed.bozo:
                    print(f"feed parse warning: {feed.bozo_exception}")

                entries = feed.entries[:MAX_ENTRIES_PER_SOURCE]
                source_result["parsed_count"] = len(entries)
                print(f"entries: {len(entries)}")

                with engine.begin() as connection:
                    for entry in entries:
                        inserted = insert_article(
                            connection=connection,
                            source=source,
                            entry=entry,
                        )

                        if inserted:
                            inserted_count += 1
                            source_result["inserted_count"] += 1
                            print(f"inserted: {entry.get('title')}")
                        else:
                            skipped_count += 1
                            source_result["skipped_count"] += 1
                            print(f"skipped: {entry.get('title')}")

            except Exception as error:
                error_count += 1
                source_result["error_count"] += 1
                print(f"source failed: {source['name']}: {error}")

            source_results.append(source_result)

        with engine.begin() as connection:
            finish_crawl_run(
                connection=connection,
                run_id=run_id,
                status="success" if error_count == 0 else "partial_success",
                inserted_count=inserted_count,
                skipped_count=skipped_count,
                error_message=None if error_count == 0 else f"{error_count} source(s) failed",
            )

        print("done")
        print(f"inserted: {inserted_count}")
        print(f"skipped: {skipped_count}")
        print(f"errors: {error_count}")
        print("source results:")
        for source_result in source_results:
            print(
                f"- {source_result['source']}: "
                f"parsed={source_result['parsed_count']}, "
                f"inserted={source_result['inserted_count']}, "
                f"skipped={source_result['skipped_count']}, "
                f"errors={source_result['error_count']}"
            )

    except Exception as error:
        with engine.begin() as connection:
            finish_crawl_run(
                connection=connection,
                run_id=run_id,
                status="failed",
                inserted_count=inserted_count,
                skipped_count=skipped_count,
                error_message=str(error),
            )

        print("failed")
        print(f"inserted: {inserted_count}")
        print(f"skipped: {skipped_count}")
        print(f"error: {error}")

        raise


if __name__ == "__main__":
    collect()
