from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(tags=["articles"])


@router.get("/articles")
def get_articles(
    category: str | None = None,
    source: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    connection: Connection = Depends(get_connection),
):
    where_clauses = []
    params = {
        "limit": limit,
    }

    if category:
        where_clauses.append("a.category = :category")
        params["category"] = category

    if source:
        where_clauses.append("lower(s.name) = lower(:source)")
        params["source"] = source

    where_sql = ""
    if where_clauses:
        where_sql = "where " + " and ".join(where_clauses)

    query = text(f"""
        select
            a.id,
            a.source_id,
            s.name as source,
            a.title,
            a.url,
            a.category,
            a.summary,
            a.published_at,
            a.tags,
            a.created_at
        from articles a
        left join sources s on s.id = a.source_id
        {where_sql}
        order by a.published_at desc nulls last, a.id desc
        limit :limit
    """)

    rows = connection.execute(query, params).mappings().all()

    return {
        "count": len(rows),
        "articles": [dict(row) for row in rows],
    }


@router.get("/articles/{article_id}")
def get_article(
    article_id: int,
    connection: Connection = Depends(get_connection),
):
    query = text("""
        select
            a.id,
            a.source_id,
            s.name as source,
            a.title,
            a.url,
            a.category,
            a.summary,
            a.published_at,
            a.tags,
            a.created_at
        from articles a
        left join sources s on s.id = a.source_id
        where a.id = :article_id
    """)

    row = connection.execute(
        query,
        {"article_id": article_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    return dict(row)
