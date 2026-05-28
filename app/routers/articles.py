from fastapi import APIRouter, HTTPException, Query
from app.data import ARTICLES

router = APIRouter(tags=["articles"])

@router.get("/articles")
def get_articles(
    category: str | None = None,
    source: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
):
    results = ARTICLES

    if category:
        results = [
            article for article in results
            if article["category"].lower() == category.lower()
        ]

    if source:
        results = [
            article for article in results
            if article["source"].lower() == source.lower()
        ]

    return {
        "count": len(results[:limit]),
        "articles": results[:limit],
    }

@router.get("/articles/{article_id}")
def get_article(article_id: int):
    for article in ARTICLES:
        if article["id"] == article_id:
            return article

    raise HTTPException(status_code=404, detail="Article not found")
