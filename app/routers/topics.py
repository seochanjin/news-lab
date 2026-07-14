"""Topic archive, home card, detail API를 제공하는 FastAPI router다.

`/topics/home`은 PostgreSQL을 source of truth로 유지하되 Redis cache-aside를
사용해 반복 조회 시 DB query를 건너뛴다. Redis 장애나 cache payload 오류는
요청 실패로 전파하지 않고 PostgreSQL 직접 조회로 복구한다. Home payload 생성
책임은 API와 pipeline이 공유할 수 있도록 `app.home_topics_payload`에 둔다.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import engine, get_connection
from app.home_topics_cache import HomeTopicsCache, get_home_topics_cache
from app.home_topics_payload import get_home_topics_payload

router = APIRouter(prefix="/topics", tags=["topics"])


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
    cache: HomeTopicsCache = Depends(get_home_topics_cache),
):
    """Home 화면용 topic card payload를 cache-aside 정책으로 반환한다."""

    return get_home_topics_payload(cache=cache, connection_factory=engine.connect)


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
