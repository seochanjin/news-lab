SOURCES = [
    {
        "id": 1,
        "name": "TechCrunch",
        "type": "tech",
        "url": "https://techcrunch.com",
        "enabled": True,
    },
    {
        "id": 2,
        "name": "The Verge",
        "type": "tech",
        "url": "https://www.theverge.com",
        "enabled": True,
    },
    {
        "id": 3,
        "name": "Reuters",
        "type": "global",
        "url": "https://www.reuters.com",
        "enabled": False,
    },
]

ARTICLES = [
    {
        "id": 1,
        "title": "AI infrastructure demand continues to grow",
        "source": "TechCrunch",
        "category": "ai",
        "summary": "AI 서비스 확산으로 GPU, 데이터센터, 클라우드 인프라 수요가 증가하고 있다.",
        "url": "https://example.com/articles/1",
        "published_at": "2026-05-28T09:00:00Z",
        "tags": ["ai", "cloud", "infrastructure"],
    },
    {
        "id": 2,
        "title": "Kubernetes adoption expands in small teams",
        "source": "The Verge",
        "category": "devops",
        "summary": "소규모 팀과 개인 프로젝트에서도 Kubernetes와 경량 배포판 활용이 늘고 있다.",
        "url": "https://example.com/articles/2",
        "published_at": "2026-05-28T10:00:00Z",
        "tags": ["kubernetes", "k3s", "devops"],
    },
    {
        "id": 3,
        "title": "Cloud cost optimization becomes a key topic",
        "source": "Reuters",
        "category": "cloud",
        "summary": "기업들이 클라우드 비용 최적화와 인프라 효율화를 중요한 운영 과제로 보고 있다.",
        "url": "https://example.com/articles/3",
        "published_at": "2026-05-28T11:00:00Z",
        "tags": ["cloud", "cost", "ops"],
    },
]
