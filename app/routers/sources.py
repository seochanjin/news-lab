from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(tags=["sources"])


@router.get("/sources")
def get_sources(connection: Connection = Depends(get_connection)):
    query = text("""
        select
            id,
            name,
            type,
            url,
            enabled,
            created_at
        from sources
        order by id
    """)

    rows = connection.execute(query).mappings().all()

    return {
        "count": len(rows),
        "sources": [dict(row) for row in rows],
    }
