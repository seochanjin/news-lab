import os
import re

import requests
from bs4 import BeautifulSoup
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

HEADERS = {
    "User-Agent": "NewsLabBot/0.1 (+https://api.dev-scj.site)"
}

SKIP_TEXT_PREFIXES = (
    "The first StrictlyVC",
    "Get Disrupt Early Bird",
)


def normalize_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    article_tag = soup.find("article")

    if article_tag:
        paragraphs = article_tag.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    texts = []

    for paragraph in paragraphs:
        text = normalize_text(paragraph.get_text(" ", strip=True))

        if len(text) < 40:
            continue

        if text.startswith(SKIP_TEXT_PREFIXES):
            continue

        texts.append(text)

    raw_text = "\n\n".join(texts)
    return raw_text.strip()


def create_extraction_run(connection):
    query = text("""
        insert into extraction_runs (status)
        values ('running')
        returning id
    """)

    return connection.execute(query).scalar_one()


def finish_extraction_run(connection, run_id, status, success_count, failed_count, error_message=None):
    query = text("""
        update extraction_runs
        set
            finished_at = now(),
            status = :status,
            success_count = :success_count,
            failed_count = :failed_count,
            error_message = :error_message
        where id = :run_id
    """)

    connection.execute(
        query,
        {
            "run_id": run_id,
            "status": status,
            "success_count": success_count,
            "failed_count": failed_count,
            "error_message": error_message,
        },
    )


def get_target_articles(connection, limit: int):
    query = text("""
        select
            a.id,
            a.title,
            a.url,
            s.name as source
        from articles a
        left join sources s on s.id = a.source_id
        left join raw_articles r on r.article_id = a.id
        where r.id is null
          and a.url is not null
          and a.url not like 'https://example.com/%'
        order by a.published_at desc nulls last, a.id desc
        limit :limit
    """)

    return connection.execute(query, {"limit": limit}).mappings().all()


def save_raw_article_success(connection, article_id: int, raw_text: str):
    query = text("""
        insert into raw_articles (
            article_id,
            raw_text,
            extraction_status,
            error_message,
            extracted_at
        )
        values (
            :article_id,
            :raw_text,
            'success',
            null,
            now()
        )
        on conflict (article_id) do update
        set
            raw_text = excluded.raw_text,
            extraction_status = 'success',
            error_message = null,
            extracted_at = now()
    """)

    connection.execute(
        query,
        {
            "article_id": article_id,
            "raw_text": raw_text,
        },
    )


def save_raw_article_failed(connection, article_id: int, error_message: str):
    query = text("""
        insert into raw_articles (
            article_id,
            raw_text,
            extraction_status,
            error_message,
            extracted_at
        )
        values (
            :article_id,
            null,
            'failed',
            :error_message,
            now()
        )
        on conflict (article_id) do update
        set
            extraction_status = 'failed',
            error_message = excluded.error_message,
            extracted_at = now()
    """)

    connection.execute(
        query,
        {
            "article_id": article_id,
            "error_message": error_message[:1000],
        },
    )


def fetch_article_text(url: str) -> str:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()

    raw_text = extract_text_from_html(response.text)

    if len(raw_text) < 300:
        raise ValueError("extracted text is too short")

    return raw_text


def extract(limit: int = 5):
    success_count = 0
    failed_count = 0

    with engine.begin() as connection:
        run_id = create_extraction_run(connection)

    print(f"extraction run started: {run_id}")

    try:
        with engine.begin() as connection:
            articles = get_target_articles(connection, limit)

        print(f"target articles: {len(articles)}")

        for article in articles:
            article_id = article["id"]
            title = article["title"]
            url = article["url"]

            print(f"extracting article_id={article_id}: {title}")

            try:
                raw_text = fetch_article_text(url)

                with engine.begin() as connection:
                    save_raw_article_success(
                        connection=connection,
                        article_id=article_id,
                        raw_text=raw_text,
                    )

                success_count += 1
                print(f"success article_id={article_id}, length={len(raw_text)}")

            except Exception as error:
                with engine.begin() as connection:
                    save_raw_article_failed(
                        connection=connection,
                        article_id=article_id,
                        error_message=str(error),
                    )

                failed_count += 1
                print(f"failed article_id={article_id}: {error}")

        with engine.begin() as connection:
            finish_extraction_run(
                connection=connection,
                run_id=run_id,
                status="success",
                success_count=success_count,
                failed_count=failed_count,
            )

        print("done")
        print(f"success: {success_count}")
        print(f"failed: {failed_count}")

    except Exception as error:
        with engine.begin() as connection:
            finish_extraction_run(
                connection=connection,
                run_id=run_id,
                status="failed",
                success_count=success_count,
                failed_count=failed_count,
                error_message=str(error),
            )

        print("failed")
        print(f"success: {success_count}")
        print(f"failed: {failed_count}")
        print(f"error: {error}")

        raise


if __name__ == "__main__":
    extract()
