import os
import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)

from app.routers.topics import get_topic, get_topics
from app.main import app


class FakeResult:
    def __init__(self, *, scalar=None, rows=None, first=None):
        self.scalar = scalar
        self.rows = rows or []
        self.first_row = first

    def scalar_one(self):
        return self.scalar

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.first_row


class FakeConnection:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def execute(self, query, params):
        self.calls.append((str(query), params))
        return self.results.pop(0)


def topic_row():
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "topic_date": date.today(),
        "topic_candidate_id": "topic-0001",
        "title_ko": "제목",
        "summary_ko": "요약",
        "key_points": ["핵심"],
        "keywords": ["키워드"],
        "confidence": 0.8,
        "source_count": 1,
        "article_count": 1,
        "provider": "deterministic",
        "model": "deterministic-summary-v1",
        "status": "draft",
        "summary_input_hash": "hash",
        "created_at": now,
        "updated_at": now,
    }


class TopicsApiTests(unittest.TestCase):
    def test_topics_routes_are_registered(self):
        paths = {route.path for route in app.routes}

        self.assertIn("/topics", paths)
        self.assertIn("/topics/{topic_id}", paths)

    def test_topic_list_returns_pagination_and_bound_filters(self):
        connection = FakeConnection(
            [FakeResult(scalar=3), FakeResult(rows=[topic_row()])]
        )

        result = get_topics(
            page=1,
            page_size=2,
            status="draft",
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 30),
            keyword="AI",
            connection=connection,
        )

        self.assertEqual(result["total"], 3)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(connection.calls[0][1]["status"], "draft")
        self.assertEqual(connection.calls[0][1]["keyword"], "%AI%")
        self.assertIn(":date_from", connection.calls[0][0])

    def test_topic_detail_returns_related_article_without_raw_text(self):
        connection = FakeConnection(
            [
                FakeResult(first=topic_row()),
                FakeResult(
                    rows=[
                        {
                            "article_id": 10,
                            "title": "Article",
                            "url": "https://example.com/article",
                            "source": "Source",
                            "published_at": datetime.now(timezone.utc),
                            "role": "representative",
                            "similarity_score": None,
                        }
                    ]
                ),
            ]
        )

        result = get_topic(1, connection=connection)

        self.assertEqual(result["articles"][0]["article_id"], 10)
        self.assertNotIn("raw_text", result)
        self.assertNotIn("raw_text", result["articles"][0])
        self.assertNotIn("raw_articles", connection.calls[1][0])

    def test_missing_topic_returns_404(self):
        connection = FakeConnection([FakeResult(first=None)])

        with self.assertRaises(HTTPException) as context:
            get_topic(999, connection=connection)

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
