from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(prefix="/collector", tags=["collector"])


@router.get("/runs")
def get_crawl_runs(
    limit: int = Query(default=10, ge=1, le=50),
    connection: Connection = Depends(get_connection),
):
    query = text("""
        select
            id,
            started_at,
            finished_at,
            status,
            inserted_count,
            skipped_count,
            error_message,
            created_at
        from crawl_runs
        order by id desc
        limit :limit
    """)

    rows = connection.execute(query, {"limit": limit}).mappings().all()

    return {
        "count": len(rows),
        "runs": [dict(row) for row in rows],
    }


@router.get("/status")
def get_collector_status(
    connection: Connection = Depends(get_connection),
):
    query = text("""
        select
            id,
            started_at,
            finished_at,
            status,
            inserted_count,
            skipped_count,
            error_message,
            created_at
        from crawl_runs
        order by id desc
        limit 1
    """)

    row = connection.execute(query).mappings().first()

    if not row:
        return {
            "status": "no_runs",
            "latest_run": None,
        }

    return {
        "status": row["status"],
        "latest_run": dict(row),
    }
