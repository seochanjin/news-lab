"""세 Home API Redis cache 계약을 한 번에 묶어 회귀 검증한다.

이 테스트는 실제 Redis, PostgreSQL, Production API에 접근하지 않는다. 하나의
가짜 Redis client에 Daily, 3-day, Weekly Home payload를 함께 저장해 key 충돌,
TTL 정책, payload validator 분리가 유지되는지 확인한다.
"""

import json
import unittest

from app.home_topics_cache import (
    DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS,
    DEFAULT_THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS,
    DEFAULT_WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS,
    HOME_TOPICS_CACHE_KEY,
    THREE_DAY_HOME_TOPICS_CACHE_KEY,
    WEEKLY_HOME_TOPICS_CACHE_KEY,
    HomeTopicsCache,
)


class SharedFakeRedisClient:
    """통합 cache 테스트에서 여러 Redis key의 저장값과 TTL을 함께 기록한다."""

    def __init__(self):
        """빈 저장소와 Redis SETEX 호출 기록을 초기화한다."""

        self.values = {}
        self.set_calls = []

    def get(self, key):
        """저장된 JSON 문자열 payload를 key 기준으로 반환한다."""

        entry = self.values.get(key)
        if entry is None:
            return None
        return entry["value"]

    def setex(self, key, ttl_seconds, value):
        """Redis SETEX 호출의 key, TTL, payload를 기록한다."""

        self.set_calls.append((key, ttl_seconds, value))
        self.values[key] = {
            "ttl_seconds": ttl_seconds,
            "value": value,
        }


def daily_payload():
    """Daily Home API schema와 같은 가짜 payload를 반환한다."""

    return {
        "generated_at": "2026-07-14T00:00:00Z",
        "topic_date": "2026-07-14",
        "items": [
            {
                "id": 1,
                "topic_date": "2026-07-14",
                "title_ko": "오늘의 이슈",
                "summary_ko": "일간 요약",
                "keywords": ["경제"],
                "source_count": 3,
                "article_count": 5,
            }
        ],
    }


def three_day_payload():
    """3-day Home API schema와 같은 가짜 payload를 반환한다."""

    return {
        "generated_at": "2026-07-14T00:00:00Z",
        "reference_date": "2026-07-14",
        "window_start": "2026-07-11T00:00:00Z",
        "window_end": "2026-07-14T00:00:00Z",
        "items": [
            {
                "id": 31,
                "reference_date": "2026-07-14",
                "window_start": "2026-07-11T00:00:00Z",
                "window_end": "2026-07-14T00:00:00Z",
                "title_ko": "3일 이슈",
                "summary_ko": "3일 요약",
                "keywords": ["정책"],
                "source_count": 4,
                "article_count": 7,
            }
        ],
    }


def weekly_payload():
    """Weekly Home API schema와 같은 가짜 payload를 반환한다."""

    return {
        "generated_at": "2026-07-14T00:00:00Z",
        "week_start": "2026-07-06",
        "week_end": "2026-07-12",
        "window_start": "2026-07-05T15:00:00Z",
        "window_end": "2026-07-12T15:00:00Z",
        "items": [
            {
                "id": 71,
                "week_start": "2026-07-06",
                "week_end": "2026-07-12",
                "window_start": "2026-07-05T15:00:00Z",
                "window_end": "2026-07-12T15:00:00Z",
                "title_ko": "주간 이슈",
                "summary_ko": "주간 요약",
                "keywords": ["시장"],
                "source_count": 5,
                "article_count": 12,
            }
        ],
    }


class HomeCacheIntegrationTests(unittest.TestCase):
    """Daily, 3-day, Weekly cache가 서로 독립된 운영 계약을 갖는지 검증한다."""

    def test_three_home_caches_use_distinct_keys_ttls_and_validators(self):
        """세 Home payload가 한 Redis client에서 key와 TTL을 섞지 않는지 확인한다."""

        client = SharedFakeRedisClient()
        caches = [
            HomeTopicsCache(
                client=client,
                key=HOME_TOPICS_CACHE_KEY,
                ttl_seconds=DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS,
            ),
            HomeTopicsCache(
                client=client,
                key=THREE_DAY_HOME_TOPICS_CACHE_KEY,
                ttl_seconds=DEFAULT_THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS,
            ),
            HomeTopicsCache(
                client=client,
                key=WEEKLY_HOME_TOPICS_CACHE_KEY,
                ttl_seconds=DEFAULT_WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS,
            ),
        ]
        payloads = [daily_payload(), three_day_payload(), weekly_payload()]

        for cache, payload in zip(caches, payloads, strict=True):
            cache.set(payload, operation="prewarm")

        self.assertEqual(
            {call[0] for call in client.set_calls},
            {
                HOME_TOPICS_CACHE_KEY,
                THREE_DAY_HOME_TOPICS_CACHE_KEY,
                WEEKLY_HOME_TOPICS_CACHE_KEY,
            },
        )
        self.assertEqual(
            client.values[HOME_TOPICS_CACHE_KEY]["ttl_seconds"],
            108000,
        )
        self.assertEqual(
            client.values[THREE_DAY_HOME_TOPICS_CACHE_KEY]["ttl_seconds"],
            108000,
        )
        self.assertEqual(
            client.values[WEEKLY_HOME_TOPICS_CACHE_KEY]["ttl_seconds"],
            691200,
        )
        self.assertEqual(caches[0].get(), payloads[0])
        self.assertEqual(caches[1].get(), payloads[1])
        self.assertEqual(caches[2].get(), payloads[2])

        client.values[THREE_DAY_HOME_TOPICS_CACHE_KEY]["value"] = json.dumps(
            daily_payload()
        )

        self.assertIsNone(caches[1].get())


if __name__ == "__main__":
    unittest.main()
