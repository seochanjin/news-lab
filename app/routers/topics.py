from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(prefix="/topics", tags=["topics"])
HOME_TOPICS_LIMIT = 10


@router.get("")
def get_topics(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    keyword: str | None = None,
    connection: Connection = Depends(get_connection),
):
    where_clauses = []
    params = {"limit": page_size, "offset": (page - 1) * page_size}
    if status:
        where_clauses.append("status = :status")
        params["status"] = status
    if date_from:
        where_clauses.append("topic_date >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_clauses.append("topic_date <= :date_to")
        params["date_to"] = date_to
    if keyword:
        where_clauses.append(
            "(title_ko ilike :keyword or summary_ko ilike :keyword "
            "or keywords::text ilike :keyword)"
        )
        params["keyword"] = f"%{keyword}%"

    where_sql = "where " + " and ".join(where_clauses) if where_clauses else ""
    total = connection.execute(
        text(f"select count(*) from topics {where_sql}"),
        params,
    ).scalar_one()
    rows = connection.execute(
        text(f"""
            select
                id, topic_date, title_ko, summary_ko, keywords,
                source_count, article_count, provider, model, status,
                created_at, updated_at
            from topics
            {where_sql}
            order by topic_date desc, id desc
            limit :limit offset :offset
        """),
        params,
    ).mappings().all()
    items = [dict(row) for row in rows]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": page * page_size < total,
    }


@router.get("/home")
def get_home_topics(
    connection: Connection = Depends(get_connection),
):
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


@router.get("/{topic_id}")
def get_topic(
    topic_id: int,
    connection: Connection = Depends(get_connection),
):
    row = connection.execute(
        text("""
            select
                id, topic_date, topic_candidate_id, title_ko, summary_ko,
                key_points, keywords, confidence, source_count, article_count,
                provider, model, status, summary_input_hash, created_at, updated_at
            from topics
            where id = :topic_id
        """),
        {"topic_id": topic_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Topic not found")

    article_rows = connection.execute(
        text("""
            select
                ta.article_id, a.title, a.url, s.name as source, a.published_at,
                ta.role, ta.similarity_score
            from topic_articles ta
            join articles a on a.id = ta.article_id
            left join sources s on s.id = a.source_id
            where ta.topic_id = :topic_id
            order by ta.id
        """),
        {"topic_id": topic_id},
    ).mappings().all()
    return {**dict(row), "articles": [dict(article) for article in article_rows]}
