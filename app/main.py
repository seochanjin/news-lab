from fastapi import FastAPI

from app.routers import (
    articles,
    collector,
    extractor,
    health,
    raw_articles,
    sources,
    topics,
    version,
)

app = FastAPI(
    title="NewsLab API",
    description="Personal news processing API running on K3s",
    version="0.2.0",
)

app.include_router(health.router)
app.include_router(version.router)
app.include_router(sources.router)
app.include_router(articles.router)
app.include_router(collector.router)
app.include_router(extractor.router)
app.include_router(raw_articles.router)
app.include_router(topics.router)

@app.get("/")
def root():
    return {
        "service": "news-api",
        "project": "NewsLab",
        "message": "NewsLab API is running",
        "docs": "/docs",
        "health": "/health",
        "version": "/version",
        "articles": "/articles",
        "raw_articles": "/raw-articles",
        "topics": "/topics",
        "extractor": "/extractor/status",
    }
