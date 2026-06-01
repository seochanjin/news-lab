from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(tags=["articles"])


@router.get("/articles")
def get_articles(
    category: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    connection: Connection = Depends(get_connection),
):
    where_clauses = []
    params = {
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }

    if category:
        where_clauses.append("a.category = :category")
        params["category"] = category

    if source:
        where_clauses.append("lower(s.name) = lower(:source)")
        params["source"] = source

    if keyword:
        where_clauses.append("""
            (
                a.title ilike :keyword
                or a.summary ilike :keyword
                or a.category ilike :keyword
                or s.name ilike :keyword
            )
        """)
        params["keyword"] = f"%{keyword}%"

    where_sql = ""
    if where_clauses:
        where_sql = "where " + " and ".join(where_clauses)

    count_query = text(f"""
        select
            count(*) as total
        from articles a
        left join sources s on s.id = a.source_id
        {where_sql}
    """)

    total = connection.execute(count_query, params).scalar_one()

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
        offset :offset
    """)

    rows = connection.execute(query, params).mappings().all()
    articles = [dict(row) for row in rows]

    return {
        "page": page,
        "page_size": page_size,
        "count": len(articles),
        "total": total,
        "has_next": page * page_size < total,
        "articles": articles,
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