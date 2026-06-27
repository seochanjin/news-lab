"""NewsLab FastAPI application을 생성하고 domain별 read router를 등록한다.

이 모듈은 application import 시 router 구성을 확정한다. Pipeline 실행이나 DB
schema 변경은 담당하지 않으며 각 요청의 DB 처리는 개별 router dependency에
위임한다.
"""

from fastapi import FastAPI

from app.routers import (
    articles,
    collector,
    extractor,
    health,
    raw_articles,
    sources,
    three_day_topics,
    topics,
    version,
    weekly_topics,
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
app.include_router(three_day_topics.router)
app.include_router(weekly_topics.router)


@app.get("/")
def root():
    """서비스 식별 정보와 기존 주요 endpoint 경로를 반환한다."""

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
        "weekly_topics": "/weekly-topics",
        "extractor": "/extractor/status",
    }
