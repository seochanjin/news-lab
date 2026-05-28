from fastapi import APIRouter
from app.data import SOURCES

router = APIRouter(tags=["sources"])

@router.get("/sources")
def get_sources():
    return {
        "count": len(SOURCES),
        "sources": SOURCES,
    }
