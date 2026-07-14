"""Home API 응답 payload를 생성하고 cache-aside 흐름을 조립한다.

이 모듈은 Home API와 각 Topic Pipeline이 공유해야 하는 PostgreSQL 조회와 응답
payload 생성 책임을 router에서 분리한다. 입력은 SQLAlchemy connection과
HomeTopicsCache이며, 출력은 기존 Home API response schema와 같은 dict다. Redis
저장은 전달받은 cache 객체에 위임하고, 파일 쓰기나 subprocess 실행 같은 부수
효과는 수행하지 않는다.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import ContextManager

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.home_topics_cache import HomeTopicsCache
from app.services.weekly_topic_pipeline import PUBLISHABLE_TOPIC_STATUSES

HOME_TOPICS_LIMIT = 10


def get_home_topics_payload(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """Cache hit payload를 반환하고 miss이면 DB payload 생성 후 cache 저장을 시도한다."""

    cached_payload = cache.get()
    if cached_payload is not None:
        return cached_payload

    with connection_factory() as connection:
        payload = fetch_home_topics_from_database(connection)
    cache.set(payload)
    return payload


def prewarm_home_topics_cache(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """PostgreSQL payload를 다시 조회해 Home Redis cache를 pipeline prewarm으로 덮어쓴다.

    Home API cache miss와 동일한 `fetch_home_topics_from_database()` builder를
    사용하지만 Redis GET은 수행하지 않는다. 따라서 Daily Pipeline 성공 직후
    기존 `topics:home:v1` key를 최신 payload로 overwrite하는 데 사용한다.
    Redis 저장 실패는 `HomeTopicsCache`의 fail-open 정책에 맡긴다.
    """

    with connection_factory() as connection:
        payload = fetch_home_topics_from_database(connection)
    cache.set(payload, operation="prewarm")
    return payload


def get_three_day_home_topics_payload(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """3일 Home cache hit를 반환하고 miss이면 DB payload 생성 후 cache 저장을 시도한다."""

    cached_payload = cache.get()
    if cached_payload is not None:
        return cached_payload

    with connection_factory() as connection:
        payload = fetch_three_day_home_topics_from_database(connection)
    cache.set(payload)
    return payload


def prewarm_three_day_home_topics_cache(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """3일 Home payload를 PostgreSQL에서 다시 조회해 Redis cache를 덮어쓴다.

    `/three-day-topics/home` cache miss와 동일한
    `fetch_three_day_home_topics_from_database()` builder를 사용한다. Redis 저장
    실패는 cache 계층의 fail-open 정책에 맡기며 pipeline 성공 여부를 바꾸지
    않는다.
    """

    with connection_factory() as connection:
        payload = fetch_three_day_home_topics_from_database(connection)
    cache.set(payload, operation="prewarm")
    return payload


def get_weekly_home_topics_payload(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """Weekly Home cache hit를 반환하고 miss이면 DB payload 생성 후 cache 저장을 시도한다."""

    cached_payload = cache.get()
    if cached_payload is not None:
        return cached_payload

    with connection_factory() as connection:
        payload = fetch_weekly_home_topics_from_database(connection)
    cache.set(payload)
    return payload


def prewarm_weekly_home_topics_cache(
    *,
    cache: HomeTopicsCache,
    connection_factory: Callable[[], ContextManager[Connection]],
):
    """Weekly Home payload를 PostgreSQL에서 다시 조회해 Redis cache를 덮어쓴다.

    `/weekly-topics/home` cache miss와 동일한
    `fetch_weekly_home_topics_from_database()` builder를 사용한다. Redis 저장
    실패는 cache 계층의 fail-open 정책에 맡기며 pipeline 성공 여부를 바꾸지
    않는다.
    """

    with connection_factory() as connection:
        payload = fetch_weekly_home_topics_from_database(connection)
    cache.set(payload, operation="prewarm")
    return payload


def fetch_home_topics_from_database(connection: Connection):
    """PostgreSQL source of truth에서 Home topic card 응답 payload를 생성한다."""

    rows = connection.execute(
        text("""
            select
                id, topic_date, title_ko, summary_ko, keywords,
                source_count, article_count
            from topics
            order by topic_date desc, article_count desc, source_count desc, id desc
            limit :limit
        """),
        {"limit": HOME_TOPICS_LIMIT},
    ).mappings().all()
    items = [dict(row) for row in rows]
    return {
        "generated_at": datetime.now(timezone.utc),
        "topic_date": items[0]["topic_date"] if items else None,
        "items": items,
    }


def fetch_three_day_home_topics_from_database(connection: Connection):
    """PostgreSQL source of truth에서 3일 Home topic card payload를 생성한다."""

    rows = connection.execute(
        text("""
            with latest_window as (
                select t.window_start, t.window_end
                from three_day_topics t
                join three_day_topic_runs r on r.id = t.run_id
                where r.status in ('success', 'partial_success')
                order by t.window_end desc, t.window_start desc, t.id desc
                limit 1
            )
            select
                t.id,
                t.reference_date,
                t.window_start,
                t.window_end,
                t.title_ko,
                t.summary_ko,
                t.keywords,
                t.article_count,
                t.source_count
            from three_day_topics t
            join latest_window w
              on w.window_start = t.window_start
             and w.window_end = t.window_end
            order by
                t.article_count desc,
                t.source_count desc,
                t.id desc
            limit :limit
        """),
        {"limit": HOME_TOPICS_LIMIT},
    ).mappings().all()
    items = [dict(row) for row in rows]
    latest = items[0] if items else None

    return {
        "generated_at": datetime.now(timezone.utc),
        "reference_date": latest["reference_date"] if latest else None,
        "window_start": latest["window_start"] if latest else None,
        "window_end": latest["window_end"] if latest else None,
        "items": items,
    }


def fetch_weekly_home_topics_from_database(connection: Connection):
    """PostgreSQL source of truth에서 Weekly Home topic card payload를 생성한다."""

    rows = connection.execute(
        text("""
            with latest_window as (
                select t.window_start, t.window_end
                from weekly_topics t
                join weekly_topic_runs r on r.id = t.run_id
                where r.status in ('success', 'partial_success')
                  and t.status = :publishable_status
                order by t.window_end desc, t.window_start desc, t.id desc
                limit 1
            )
            select
                t.id,
                t.week_start,
                t.week_end,
                t.window_start,
                t.window_end,
                t.title_ko,
                t.summary_ko,
                t.keywords,
                t.article_count,
                t.source_count
            from weekly_topics t
            join latest_window w
              on w.window_start = t.window_start
             and w.window_end = t.window_end
            where t.status = :publishable_status
            order by
                t.article_count desc,
                t.source_count desc,
                t.id desc
            limit :limit
        """),
        {
            "limit": HOME_TOPICS_LIMIT,
            "publishable_status": next(iter(PUBLISHABLE_TOPIC_STATUSES)),
        },
    ).mappings().all()
    items = [dict(row) for row in rows]
    latest = items[0] if items else None

    return {
        "generated_at": datetime.now(timezone.utc),
        "week_start": latest["week_start"] if latest else None,
        "week_end": latest["week_end"] if latest else None,
        "window_start": latest["window_start"] if latest else None,
        "window_end": latest["window_end"] if latest else None,
        "items": items,
    }
