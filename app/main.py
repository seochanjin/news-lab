from fastapi import FastAPI

from app.routers import articles, health, sources, version

app = FastAPI(
    title="NewsLab API",
    description="Personal news processing API running on K3s",
    version="0.2.0",
)

app.include_router(health.router)
app.include_router(version.router)
app.include_router(sources.router)
app.include_router(articles.router)

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
    }
