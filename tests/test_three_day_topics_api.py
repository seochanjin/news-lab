"""3일 Topic 목록·홈·상세 API의 SQL bind와 응답 계약을 검증한다.

가짜 SQLAlchemy connection으로 read query와 payload 조립만 확인하며 실제 DB,
pipeline, migration 또는 Production API에는 접근하지 않는다.
"""

import os
import unittest
from datetime import date, datetime, timezone

from fastapi import HTTPException


os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)

from app.main import app
from app.routers.three_day_topics import (
    get_three_day_home_topics,
    get_three_day_topic,
    get_three_day_topics,
)


class FakeResult:
    """Router가 사용하는 SQLAlchemy result의 최소 조회 interface를 제공한다."""

    def __init__(self, *, scalar=None, rows=None, first=None):
        """단일 scalar, 다중 row와 첫 row 반환값을 보관한다."""

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
    """실행된 SQL과 parameter를 기록하고 준비된 결과를 순서대로 반환한다."""

    def __init__(self, results):
        """각 execute 호출에 대응하는 가짜 result 목록을 초기화한다."""

        self.results = list(results)
        self.calls = []

    def execute(self, query, params):
        """SQL 문자열과 bind parameter를 기록한 뒤 다음 result를 반환한다."""

        self.calls.append((str(query), params))
        return self.results.pop(0)


def three_day_topic_row():
    """목록과 상세 응답에 사용할 3일 Topic 가짜 row를 만든다."""

    now = datetime.now(timezone.utc)
    return {
        "id": 31,
        "reference_date": date(2026, 6, 23),
        "window_start": datetime(2026, 6, 20, tzinfo=timezone.utc),
        "window_end": datetime(2026, 6, 23, tzinfo=timezone.utc),
        "title_ko": "3일 이슈",
        "summary_ko": "3일 동안의 변화",
        "keywords": ["정책", "시장"],
        "article_count": 5,
        "source_count": 4,
        "status": "ready",
        "provider": "openai",
        "model": "summary-model",
        "prompt_version": "three-day-flow-v1",
        "created_at": now,
        "updated_at": now,
    }


def home_topic_row():
    """상세 row에서 home card에 허용된 field만 추출한다."""

    row = three_day_topic_row()
    return {
        key: row[key]
        for key in (
            "id",
            "reference_date",
            "window_start",
            "window_end",
            "title_ko",
            "summary_ko",
            "keywords",
            "article_count",
            "source_count",
        )
    }


def detail_topic_row(key_points=None):
    """상세 API 응답에 필요한 key_points field를 포함한 가짜 row를 만든다."""

    row = three_day_topic_row()
    row["key_points"] = key_points
    return row


class ThreeDayTopicsApiTests(unittest.TestCase):
    """3일 Topic route 순서, filter, 빈 응답, 상세 기사 역할을 검증한다."""

    def test_routes_are_registered_with_home_before_dynamic_detail(self):
        """정적 home route가 동적 topic ID route보다 먼저 등록되는지 확인한다."""

        paths = [route.path for route in app.routes]

        self.assertIn("/three-day-topics", paths)
        self.assertIn("/three-day-topics/home", paths)
        self.assertIn("/three-day-topics/{topic_id}", paths)
        self.assertLess(
            paths.index("/three-day-topics/home"),
            paths.index("/three-day-topics/{topic_id}"),
        )

    def test_archive_returns_pagination_and_bound_filters(self):
        """Archive가 모든 지원 filter를 bind하고 최신순 page를 반환하는지 확인한다."""

        connection = FakeConnection(
            [FakeResult(scalar=3), FakeResult(rows=[three_day_topic_row()])]
        )

        result = get_three_day_topics(
            page=1,
            page_size=2,
            reference_date=date(2026, 6, 23),
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 30),
            keyword="시장",
            status="ready",
            connection=connection,
        )

        self.assertEqual(result["total"], 3)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["items"][0]["id"], 31)
        count_sql, params = connection.calls[0]
        self.assertEqual(params["reference_date"], date(2026, 6, 23))
        self.assertEqual(params["keyword"], "%시장%")
        self.assertEqual(params["status"], "ready")
        self.assertIn(":date_from", count_sql)
        self.assertNotIn("2026-06-23", count_sql)
        self.assertIn(
            "order by t.reference_date desc, t.window_end desc, t.id desc",
            connection.calls[1][0].lower(),
        )

    def test_home_returns_latest_publishable_window_cards_only(self):
        """Home이 최신 publishable window의 경량 card와 공통 window를 반환하는지 확인한다."""

        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_three_day_home_topics(connection=connection)

        item = result["items"][0]
        self.assertEqual(result["reference_date"], item["reference_date"])
        self.assertEqual(result["window_start"], item["window_start"])
        self.assertEqual(result["window_end"], item["window_end"])
        self.assertIn("generated_at", result)
        self.assertEqual(connection.calls[0][1]["limit"], 10)
        sql = connection.calls[0][0].lower()
        self.assertIn("latest_window", sql)
        self.assertIn("'success', 'partial_success'", sql)
        self.assertNotIn("count(*)", sql)
        self.assertNotIn("three_day_topic_articles", sql)
        self.assertNotIn("provider", sql)
        self.assertNotIn("model", sql)

    def test_home_empty_response_uses_null_window_metadata(self):
        """Publishable Topic이 없을 때 정상 빈 payload를 반환하는지 확인한다."""

        connection = FakeConnection([FakeResult(rows=[])])

        result = get_three_day_home_topics(connection=connection)

        self.assertIsNone(result["reference_date"])
        self.assertIsNone(result["window_start"])
        self.assertIsNone(result["window_end"])
        self.assertEqual(result["items"], [])

    def test_detail_returns_articles_in_rank_order_with_role_flags(self):
        """상세가 대표·Summary 근거 flag를 포함해 관련 기사를 순위순 반환하는지 확인한다."""

        published_at = datetime.now(timezone.utc)
        articles = [
            {
                "article_id": 101,
                "title": "대표 기사",
                "url": "https://example.com/representative",
                "published_at": published_at,
                "source": "Source A",
                "rank": 1,
                "similarity": 1.0,
                "is_representative": True,
                "is_summary_evidence": True,
            },
            {
                "article_id": 102,
                "title": "관련 기사",
                "url": "https://example.com/related",
                "published_at": published_at,
                "source": "Source B",
                "rank": 2,
                "similarity": 0.91,
                "is_representative": False,
                "is_summary_evidence": False,
            },
        ]
        connection = FakeConnection(
            [
                FakeResult(
                    first=detail_topic_row(
                        ["첫 번째 핵심 포인트", "두 번째 핵심 포인트"]
                    )
                ),
                FakeResult(rows=articles),
            ]
        )

        result = get_three_day_topic(31, connection=connection)

        self.assertEqual(result["article_count"], 5)
        self.assertEqual(result["source_count"], 4)
        self.assertEqual(
            result["key_points"],
            ["첫 번째 핵심 포인트", "두 번째 핵심 포인트"],
        )
        self.assertIn("key_points", connection.calls[0][0].lower())
        self.assertEqual(
            [article["article_id"] for article in result["articles"]],
            [101, 102],
        )
        self.assertTrue(result["articles"][0]["is_representative"])
        self.assertTrue(result["articles"][0]["is_summary_evidence"])
        self.assertFalse(result["articles"][1]["is_summary_evidence"])
        self.assertIn(
            "order by ta.rank asc, ta.article_id asc",
            connection.calls[1][0].lower(),
        )
        self.assertNotIn("raw_articles", connection.calls[1][0].lower())

    def test_detail_returns_empty_key_points_when_database_value_is_null(self):
        """상세 row의 key_points가 NULL이면 항상 빈 배열로 응답하는지 확인한다."""

        connection = FakeConnection(
            [
                FakeResult(first=detail_topic_row(key_points=None)),
                FakeResult(rows=[]),
            ]
        )

        result = get_three_day_topic(31, connection=connection)

        self.assertEqual(result["key_points"], [])
        self.assertEqual(result["articles"], [])

    def test_detail_preserves_empty_key_points_array(self):
        """상세 row의 key_points가 빈 배열이면 빈 배열 계약을 유지하는지 확인한다."""

        connection = FakeConnection(
            [
                FakeResult(first=detail_topic_row(key_points=[])),
                FakeResult(rows=[]),
            ]
        )

        result = get_three_day_topic(31, connection=connection)

        self.assertEqual(result["key_points"], [])
        self.assertIsInstance(result["key_points"], list)

    def test_missing_topic_returns_404(self):
        """존재하지 않는 3일 Topic 요청이 404를 반환하는지 확인한다."""

        connection = FakeConnection([FakeResult(first=None)])

        with self.assertRaises(HTTPException) as context:
            get_three_day_topic(999, connection=connection)

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Three-day topic not found")


if __name__ == "__main__":
    unittest.main()
