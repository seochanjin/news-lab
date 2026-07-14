"""저장된 7일 Topic의 archive, home card와 상세 조회 API를 제공한다.

이 router는 `weekly_topics` 계열 테이블과 기존 기사 metadata를 읽기만 한다.
Weekly pipeline 실행, run 오류 노출, 원문 조회와 DB 쓰기는 담당하지 않으며
모든 사용자 입력은 SQLAlchemy bind parameter로 query에 전달한다.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import engine, get_connection
from app.home_topics_cache import HomeTopicsCache, get_weekly_home_topics_cache
from app.home_topics_payload import get_weekly_home_topics_payload

router = APIRouter(prefix="/weekly-topics", tags=["weekly_topics"])


@router.get("")
def get_weekly_topics(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    week_start: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    keyword: str | None = None,
    status: str | None = None,
    connection: Connection = Depends(get_connection),
):
    """조건에 맞는 7일 Topic archive를 최신순 pagination으로 반환한다."""

    where_clauses = []
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    if week_start:
        where_clauses.append("t.week_start = :week_start")
        params["week_start"] = week_start
    if date_from:
        where_clauses.append("t.week_start >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("t.week_start <= :date_to")
        params["date_to"] = date_to
    if keyword:
        where_clauses.append(
            "(t.title_ko ilike :keyword or t.summary_ko ilike :keyword "
            "or t.keywords::text ilike :keyword)"
        )
        params["keyword"] = f"%{keyword}%"
    if status:
        where_clauses.append("t.status = :status")
        params["status"] = status

    where_sql = "where " + " and ".join(where_clauses) if where_clauses else ""
    total = connection.execute(
        text(f"select count(*) from weekly_topics t {where_sql}"),
        params,
    ).scalar_one()
    rows = connection.execute(
        text(f"""
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
                t.source_count,
                t.status,
                t.created_at,
                t.updated_at
            from weekly_topics t
            {where_sql}
            order by t.week_start desc, t.window_end desc, t.id desc
            limit :limit offset :offset
        """),
        params,
    ).mappings().all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": page * page_size < total,
        "items": [dict(row) for row in rows],
    }


@router.get("/home")
def get_weekly_home_topics(
    cache: HomeTopicsCache = Depends(get_weekly_home_topics_cache),
):
    """성공 또는 부분 성공한 최신 완료 주간의 publishable card를 반환한다."""

    return get_weekly_home_topics_payload(
        cache=cache,
        connection_factory=engine.connect,
    )


@router.get("/{topic_id}")
def get_weekly_topic(
    topic_id: int,
    connection: Connection = Depends(get_connection),
):
    """단일 7일 Topic과 순위가 지정된 관련 기사 전체를 반환한다."""

    row = connection.execute(
        text("""
            select
                id,
                week_start,
                week_end,
                window_start,
                window_end,
                title_ko,
                summary_ko,
                key_points,
                keywords,
                confidence,
                article_count,
                source_count,
                status,
                provider,
                model,
                prompt_version,
                summary_input_hash,
                created_at,
                updated_at
            from weekly_topics
            where id = :topic_id
        """),
        {"topic_id": topic_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Weekly topic not found")

    article_rows = connection.execute(
        text("""
            select
                ta.article_id,
                a.title,
                a.url,
                a.published_at,
                s.name as source,
                ta.rank,
                ta.similarity,
                ta.is_representative,
                ta.is_summary_evidence
            from weekly_topic_articles ta
            join articles a on a.id = ta.article_id
            left join sources s on s.id = a.source_id
            where ta.weekly_topic_id = :topic_id
            order by ta.rank asc, ta.article_id asc
        """),
        {"topic_id": topic_id},
    ).mappings().all()

    return {**dict(row), "articles": [dict(article) for article in article_rows]}
