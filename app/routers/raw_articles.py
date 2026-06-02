from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(prefix="/raw-articles", tags=["raw_articles"])


@router.get("")
def get_raw_articles(
    status: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    connection: Connection = Depends(get_connection),
):
    where_clauses = []
    params = {
        "limit": limit,
    }

    if status:
        where_clauses.append("r.extraction_status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "where " + " and ".join(where_clauses)

    query = text(f"""
        select
            r.id,
            r.article_id,
            a.title,
            a.url,
            s.name as source,
            r.extraction_status,
            length(r.raw_text) as text_length,
            left(r.raw_text, 300) as preview,
            r.error_message,
            r.extracted_at,
            r.created_at
        from raw_articles r
        left join articles a on a.id = r.article_id
        left join sources s on s.id = a.source_id
        {where_sql}
        order by r.id desc
        limit :limit
    """)

    rows = connection.execute(query, params).mappings().all()

    return {
        "count": len(rows),
        "raw_articles": [dict(row) for row in rows],
    }


@router.get("/{article_id}")
def get_raw_article(
    article_id: int,
    connection: Connection = Depends(get_connection),
):
    query = text("""
        select
            r.id,
            r.article_id,
            a.title,
            a.url,
            s.name as source,
            r.extraction_status,
            length(r.raw_text) as text_length,
            left(r.raw_text, 500) as preview,
            r.error_message,
            r.extracted_at,
            r.created_at
        from raw_articles r
        left join articles a on a.id = r.article_id
        left join sources s on s.id = a.source_id
        where r.article_id = :article_id
    """)

    row = connection.execute(
        query,
        {"article_id": article_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Raw article not found")

    return dict(row)
