from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.database import get_connection

router = APIRouter(prefix="/extractor", tags=["extractor"])

ExtractionRunStatus = Literal["running", "success", "failed"]


@router.get("/runs")
def get_extraction_runs(
    status: ExtractionRunStatus | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    connection: Connection = Depends(get_connection),
):
    where_clauses = []
    params = {
        "limit": limit,
    }

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "where " + " and ".join(where_clauses)

    query = text(f"""
        select
            id,
            started_at,
            finished_at,
            status,
            success_count,
            failed_count,
            error_message,
            created_at
        from extraction_runs
        {where_sql}
        order by id desc
        limit :limit
    """)

    rows = connection.execute(query, params).mappings().all()

    return {
        "count": len(rows),
        "runs": [dict(row) for row in rows],
    }


@router.get("/status")
def get_extractor_status(
    connection: Connection = Depends(get_connection),
):
    query = text("""
        select
            id,
            started_at,
            finished_at,
            status,
            success_count,
            failed_count,
            error_message,
            created_at
        from extraction_runs
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
