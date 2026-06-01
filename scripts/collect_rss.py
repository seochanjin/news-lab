import os
from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

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


def get_enabled_sources(connection):
    query = text("""
        select
            id,
            name,
            feed_url
        from sources
        where enabled = true
          and feed_url is not null
        order by id
    """)

    return connection.execute(query).mappings().all()


def insert_article(connection, source_id, entry):
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
            "source_id": source_id,
            "title": title,
            "url": url,
            "category": "tech",
            "summary": summary,
            "published_at": published_at,
            "tags": ["rss"],
        },
    )

    return result.rowcount == 1


def collect():
    inserted_count = 0
    skipped_count = 0

    with engine.begin() as connection:
        run_id = create_crawl_run(connection)
        print(f"crawl run started: {run_id}")

        try:
            sources = get_enabled_sources(connection)

            print(f"enabled sources: {len(sources)}")

            for source in sources:
                print(f"collecting: {source['name']} - {source['feed_url']}")

                feed = feedparser.parse(source["feed_url"])

                if feed.bozo:
                    print(f"feed parse warning: {feed.bozo_exception}")

                entries = feed.entries[:10]
                print(f"entries: {len(entries)}")

                for entry in entries:
                    inserted = insert_article(
                        connection=connection,
                        source_id=source["id"],
                        entry=entry,
                    )

                    if inserted:
                        inserted_count += 1
                        print(f"inserted: {entry.get('title')}")
                    else:
                        skipped_count += 1
                        print(f"skipped: {entry.get('title')}")

            finish_crawl_run(
                connection=connection,
                run_id=run_id,
                status="success",
                inserted_count=inserted_count,
                skipped_count=skipped_count,
            )

            print("done")
            print(f"inserted: {inserted_count}")
            print(f"skipped: {skipped_count}")

        except Exception as error:
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