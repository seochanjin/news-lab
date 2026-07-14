"""Topics API의 response schema와 Home cache-aside 동작을 검증한다.

가짜 DB connection을 사용해 SQL 호출과 응답 조립만 확인하며 실제 DB나
Production API에는 접근하지 않는다. Home cache 검증도 fake Redis client로
hit, miss, TTL, Redis 오류와 손상 payload fallback만 재현한다.
"""

import os
import unittest
from contextlib import nullcontext
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)

from app.home_topics_cache import (
    DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS,
    HOME_TOPICS_CACHE_KEY,
    HomeTopicsCache,
    get_home_topics_cache,
)
from app.home_topics_payload import (
    fetch_home_topics_from_database,
    get_home_topics_payload,
)
from app.routers.topics import (
    get_topic,
    get_topics,
)
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


class FakeRedisClient:
    """Home Topics cache 테스트에 필요한 Redis get/setex와 TTL 동작을 흉내 낸다."""

    def __init__(self):
        """저장소와 현재 시간을 초기화한다."""

        self.values = {}
        self.now = 0.0
        self.get_error = None
        self.set_error = None
        self.set_calls = []

    def get(self, key):
        """만료 시간을 반영해 저장된 문자열 payload를 반환한다."""

        if self.get_error:
            raise self.get_error
        entry = self.values.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at <= self.now:
            self.values.pop(key, None)
            return None
        return value

    def setex(self, key, ttl_seconds, value):
        """TTL과 payload를 기록하거나 설정된 오류를 발생시킨다."""

        if self.set_error:
            raise self.set_error
        self.set_calls.append((key, ttl_seconds, value))
        self.values[key] = (value, self.now + ttl_seconds)

    def advance(self, seconds):
        """테스트에서 TTL 만료를 재현하기 위해 현재 시간을 이동한다."""

        self.now += seconds


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

        result = fetch_home_topics_from_database(connection=connection)

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

        result = fetch_home_topics_from_database(connection=connection)

        self.assertIsNone(result["topic_date"])
        self.assertEqual(result["items"], [])

    def test_home_topics_cache_miss_reads_database_and_stores_payload(self):
        """Cache miss에서 PostgreSQL 조회 후 기본 30시간 TTL 저장이 실행되는지 검증한다."""

        client = FakeRedisClient()
        cache = HomeTopicsCache(client=client)
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)
        self.assertEqual(client.set_calls[0][0], HOME_TOPICS_CACHE_KEY)
        self.assertEqual(client.set_calls[0][1], 108000)

    def test_home_topics_cache_default_ttl_is_thirty_hours(self):
        """환경변수 override가 없을 때 Home cache 기본 TTL이 30시간인지 고정한다."""

        client = FakeRedisClient()
        cache = HomeTopicsCache(client=client)

        self.assertEqual(cache.ttl_seconds, DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS)
        self.assertEqual(DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS, 108000)

    def test_home_topics_cache_hit_skips_database_connection(self):
        """Cache hit이면 DB connection factory를 호출하지 않아 반복 조회 부하를 막는다."""

        client = FakeRedisClient()
        cached_payload = {
            "generated_at": "2026-07-13T00:00:00Z",
            "topic_date": "2026-07-13",
            "items": [
                {
                    "id": 1,
                    "topic_date": "2026-07-13",
                    "title_ko": "제목",
                    "summary_ko": "요약",
                    "keywords": ["키워드"],
                    "source_count": 4,
                    "article_count": 5,
                }
            ],
        }
        cache = HomeTopicsCache(client=client, ttl_seconds=60)
        cache.set(cached_payload)

        def fail_connection_factory():
            """Cache hit 회귀 검증을 위해 호출되면 실패한다."""

            raise AssertionError("DB connection should not be opened on cache hit")

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=fail_connection_factory,
        )

        self.assertEqual(result, cached_payload)

    def test_home_topics_cache_ttl_expiry_reads_database_again(self):
        """TTL이 지난 cached payload는 miss로 처리되어 PostgreSQL을 다시 조회한다."""

        client = FakeRedisClient()
        cache = HomeTopicsCache(client=client, ttl_seconds=1)
        first_connection = FakeConnection([FakeResult(rows=[home_topic_row()])])
        second_connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(first_connection),
        )
        client.advance(2)
        get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(second_connection),
        )

        self.assertEqual(len(first_connection.calls), 1)
        self.assertEqual(len(second_connection.calls), 1)
        self.assertEqual(len(client.set_calls), 2)

    def test_home_topics_cache_get_failure_falls_back_to_database(self):
        """Redis GET timeout이 API 실패로 번지지 않고 PostgreSQL fallback으로 복구된다."""

        client = FakeRedisClient()
        client.get_error = TimeoutError("redis get timeout")
        cache = HomeTopicsCache(client=client, ttl_seconds=60)
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)

    def test_home_topics_cache_connection_failure_falls_back_to_database(self):
        """Redis connection 오류도 bypass로 기록되고 PostgreSQL 조회 결과를 반환한다."""

        client = FakeRedisClient()
        client.get_error = OSError("connection refused")
        cache = HomeTopicsCache(client=client, ttl_seconds=60)
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)

    def test_home_topics_cache_set_failure_keeps_response_successful(self):
        """Redis SET 실패가 PostgreSQL 조회 성공 응답을 실패시키지 않는지 확인한다."""

        client = FakeRedisClient()
        client.set_error = TimeoutError("redis set timeout")
        cache = HomeTopicsCache(client=client, ttl_seconds=60)
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)

    def test_home_topics_corrupt_cache_payload_falls_back_to_database(self):
        """손상된 cache payload를 폐기하고 PostgreSQL 재조회로 응답 schema를 복구한다."""

        client = FakeRedisClient()
        client.values[HOME_TOPICS_CACHE_KEY] = ("not-json", 60)
        cache = HomeTopicsCache(client=client, ttl_seconds=60)
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)

    def test_home_topics_malformed_redis_url_falls_back_to_database(self):
        """Malformed Redis URL이 dependency 생성 실패 대신 PostgreSQL fallback을 유도한다."""

        get_home_topics_cache.cache_clear()
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])
        redis_url = "redis://:secret-token@[bad-host"

        with patch.dict(os.environ, {"REDIS_URL": redis_url}):
            with patch("app.home_topics_cache.Redis") as redis_class:
                redis_class.from_url.side_effect = ValueError("invalid url")
                with self.assertLogs("app.home_topics_cache", level="WARNING") as logs:
                    cache = get_home_topics_cache()

        self.assertFalse(cache.enabled)
        self.assertIsNone(cache.client)
        self.assertIn("reason=invalid_redis_url", "\n".join(logs.output))
        self.assertNotIn("secret-token", "\n".join(logs.output))
        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)
        get_home_topics_cache.cache_clear()

    def test_home_topics_unsupported_redis_url_scheme_disables_cache(self):
        """지원하지 않는 Redis URL scheme도 비활성 cache로 처리해 DB 조회를 유지한다."""

        get_home_topics_cache.cache_clear()
        connection = FakeConnection([FakeResult(rows=[home_topic_row()])])

        with patch.dict(os.environ, {"REDIS_URL": "http://redis.example/cache"}):
            with patch("app.home_topics_cache.Redis") as redis_class:
                redis_class.from_url.side_effect = ValueError("unsupported scheme")
                cache = get_home_topics_cache()

        result = get_home_topics_payload(
            cache=cache,
            connection_factory=lambda: nullcontext(connection),
        )

        self.assertFalse(cache.enabled)
        self.assertIsNone(cache.client)
        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(len(connection.calls), 1)
        get_home_topics_cache.cache_clear()

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
