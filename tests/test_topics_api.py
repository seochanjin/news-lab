"""Topics API가 저장된 관련 기사 전체와 기존 response schema를 반환하는지 검증한다.

가짜 DB connection을 사용해 SQL 호출과 응답 조립만 확인하며 실제 DB나
Production API에는 접근하지 않는다.
"""

import os
import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)

from app.routers.topics import get_home_topics, get_topic, get_topics
from app.main import app


class FakeResult:
    """SQLAlchemy result에서 router가 사용하는 최소 조회 interface를 제공한다."""

    def __init__(self, *, scalar=None, rows=None, first=None):
        """단일 scalar, 다중 row 또는 첫 row 반환값을 보관한다."""

        self.scalar = scalar
        self.rows = rows or []
        self.first_row = first

    def scalar_one(self):
        """Count query용 scalar 값을 반환한다."""

        return self.scalar

    def mappings(self):
        """Mapping result chain을 위해 자기 자신을 반환한다."""

        return self

    def all(self):
        """다중 row query 결과를 입력 순서대로 반환한다."""

        return self.rows

    def first(self):
        """단일 row query의 첫 결과를 반환한다."""

        return self.first_row


class FakeConnection:
    """Router SQL과 bind parameter를 기록하고 준비된 결과를 순서대로 반환한다."""

    def __init__(self, results):
        """각 execute 호출에 대응할 결과 목록을 초기화한다."""

        self.results = list(results)
        self.calls = []

    def execute(self, query, params):
        """SQL 문자열과 parameter를 기록한 뒤 다음 가짜 결과를 반환한다."""

        self.calls.append((str(query), params))
        return self.results.pop(0)


def topic_row(*, article_count=5, source_count=4):
    """관련 기사 집계값을 포함한 Topic API용 가짜 DB row를 만든다."""

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
        "source_count": source_count,
        "article_count": article_count,
        "provider": "deterministic",
        "model": "deterministic-summary-v1",
        "status": "draft",
        "summary_input_hash": "hash",
        "created_at": now,
        "updated_at": now,
    }


def home_topic_row():
    """Topic row에서 home card schema에 포함되는 field만 추출한다."""

    row = topic_row()
    return {
        key: row[key]
        for key in (
            "id",
            "topic_date",
            "title_ko",
            "summary_ko",
            "keywords",
            "source_count",
            "article_count",
        )
    }


class TopicsApiTests(unittest.TestCase):
    """Topics endpoint path, schema, 집계값과 관련 기사 순서를 회귀 검증한다."""

    def test_topics_routes_are_registered(self):
        """기존 Topics endpoint 세 개가 application에 계속 등록되는지 확인한다."""

        paths = {route.path for route in app.routes}

        self.assertIn("/topics", paths)
        self.assertIn("/topics/home", paths)
        self.assertIn("/topics/{topic_id}", paths)

    def test_topic_list_returns_pagination_and_bound_filters(self):
        """목록 API가 기존 pagination schema와 bind filter를 유지하는지 확인한다."""

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

    def test_home_topics_returns_lightweight_card_payload(self):
        """Home API가 관련 기사 전체 집계값을 기존 card schema로 반환하는지 확인한다."""

        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics(connection=connection)

        self.assertEqual(result["topic_date"], result["items"][0]["topic_date"])
        self.assertIn("generated_at", result)
        self.assertEqual(
            set(result["items"][0]),
            {
                "id",
                "topic_date",
                "title_ko",
                "summary_ko",
                "keywords",
                "source_count",
                "article_count",
            },
        )
        self.assertEqual(connection.calls[0][1]["limit"], 10)
        self.assertEqual(result["items"][0]["article_count"], 5)
        self.assertEqual(result["items"][0]["source_count"], 4)
        self.assertNotIn("count(*)", connection.calls[0][0].lower())
        self.assertNotIn("topic_articles", connection.calls[0][0])
        self.assertNotIn("provider", connection.calls[0][0])
        self.assertNotIn("model", connection.calls[0][0])

    def test_home_topics_empty_response_uses_null_topic_date(self):
        """Home 조회 결과가 없을 때 기존 빈 응답 계약을 유지하는지 확인한다."""

        connection = FakeConnection([FakeResult(rows=[])])

        result = get_home_topics(connection=connection)

        self.assertIsNone(result["topic_date"])
        self.assertEqual(result["items"], [])

    def test_topic_detail_returns_all_related_articles_in_relation_order(self):
        """상세 API가 대표 기사를 포함한 관련 기사 전체를 relation 순서로 반환하는지 확인한다."""

        published_at = datetime.now(timezone.utc)
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
                            "published_at": published_at,
                            "role": "representative",
                            "similarity_score": None,
                        },
                        {
                            "article_id": 11,
                            "title": "Article 2",
                            "url": "https://example.com/article-2",
                            "source": "Source 2",
                            "published_at": published_at,
                            "role": "supporting",
                            "similarity_score": 0.91,
                        },
                        {
                            "article_id": 12,
                            "title": "Article 3",
                            "url": "https://example.com/article-3",
                            "source": "Source 3",
                            "published_at": published_at,
                            "role": "supporting",
                            "similarity_score": 0.88,
                        },
                        {
                            "article_id": 13,
                            "title": "Article 4",
                            "url": "https://example.com/article-4",
                            "source": "Source 4",
                            "published_at": published_at,
                            "role": "supporting",
                            "similarity_score": 0.84,
                        },
                        {
                            "article_id": 14,
                            "title": "Article 5",
                            "url": "https://example.com/article-5",
                            "source": "Source",
                            "published_at": published_at,
                            "role": "supporting",
                            "similarity_score": 0.80,
                        },
                    ]
                ),
            ]
        )

        result = get_topic(1, connection=connection)

        self.assertEqual(result["article_count"], 5)
        self.assertEqual(result["source_count"], 4)
        self.assertEqual(
            [article["article_id"] for article in result["articles"]],
            [10, 11, 12, 13, 14],
        )
        self.assertEqual(result["articles"][0]["role"], "representative")
        self.assertTrue(
            all(
                article["role"] == "supporting"
                for article in result["articles"][1:]
            )
        )
        self.assertNotIn("raw_text", result)
        self.assertTrue(
            all("raw_text" not in article for article in result["articles"])
        )
        self.assertNotIn("raw_articles", connection.calls[1][0])
        self.assertIn("order by ta.id", connection.calls[1][0].lower())

    def test_missing_topic_returns_404(self):
        """존재하지 않는 Topic 요청이 기존 404 계약을 유지하는지 확인한다."""

        connection = FakeConnection([FakeResult(first=None)])

        with self.assertRaises(HTTPException) as context:
            get_topic(999, connection=connection)

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
