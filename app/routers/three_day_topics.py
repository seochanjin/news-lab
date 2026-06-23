"""저장된 3일 Topic의 archive, home card와 상세 조회 API를 제공한다.

이 router는 `three_day_topics` 계열과 기존 기사 metadata를 읽기만 한다.
Pipeline 실행, run 오류 노출, 원문 조회와 DB 쓰기는 담당하지 않으며 모든
사용자 입력은 SQLAlchemy bind parameter로 query에 전달한다.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection


router = APIRouter(prefix="/three-day-topics", tags=["three_day_topics"])
HOME_TOPICS_LIMIT = 10


@router.get("")
def get_three_day_topics(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    reference_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    keyword: str | None = None,
    status: str | None = None,
    connection: Connection = Depends(get_connection),
):
    """조건에 맞는 3일 Topic archive를 최신순 pagination으로 반환한다."""

    where_clauses = []
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    if reference_date:
        where_clauses.append("t.reference_date = :reference_date")
        params["reference_date"] = reference_date
    if date_from:
        where_clauses.append("t.reference_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("t.reference_date <= :date_to")
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
        text(f"select count(*) from three_day_topics t {where_sql}"),
        params,
    ).scalar_one()
    rows = connection.execute(
        text(f"""
            select
                t.id,
                t.reference_date,
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
            from three_day_topics t
            {where_sql}
            order by t.reference_date desc, t.window_end desc, t.id desc
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
def get_three_day_home_topics(
    connection: Connection = Depends(get_connection),
):
    """성공 또는 부분 성공한 최신 72시간 publishable window card를 반환한다."""

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


@router.get("/{topic_id}")
def get_three_day_topic(
    topic_id: int,
    connection: Connection = Depends(get_connection),
):
    """단일 3일 Topic과 순위가 지정된 관련 기사 전체를 반환한다."""

    row = connection.execute(
        text("""
            select
                id,
                reference_date,
                window_start,
                window_end,
                title_ko,
                summary_ko,
                keywords,
                article_count,
                source_count,
                status,
                provider,
                model,
                prompt_version,
                created_at,
                updated_at
            from three_day_topics
            where id = :topic_id
        """),
        {"topic_id": topic_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Three-day topic not found")

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
            from three_day_topic_articles ta
            join articles a on a.id = ta.article_id
            left join sources s on s.id = a.source_id
            where ta.three_day_topic_id = :topic_id
            order by ta.rank asc, ta.article_id asc
        """),
        {"topic_id": topic_id},
    ).mappings().all()

    return {**dict(row), "articles": [dict(article) for article in article_rows]}
