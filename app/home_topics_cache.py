"""Home Topics API 응답을 Redis에 저장하고 조회하는 cache-aside 계층이다.

이 모듈은 PostgreSQL에서 만들어진 `/topics/home` 응답 payload를 짧은 TTL로
Redis에 보관한다. Redis는 source of truth가 아니므로 읽기, 쓰기, 연결, timeout,
payload decode 오류가 발생하면 예외를 요청 처리 경로로 전파하지 않고 호출자가
PostgreSQL 조회를 계속할 수 있도록 cache miss 형태로 반환한다.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - dependency 설치 전 local import 보호
    Redis = None
    RedisError = Exception

from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

HOME_TOPICS_CACHE_KEY = "topics:home:v1"
DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS = 60
DEFAULT_REDIS_TIMEOUT_SECONDS = 0.05


@dataclass
class HomeTopicsCache:
    """`/topics/home` payload 전용 Redis cache 동작을 캡슐화한다.

    `client`가 없으면 cache가 비활성화된 상태로 동작한다. 모든 Redis 예외와
    payload decode 실패는 로그에 남기고 `None`을 반환해 PostgreSQL fallback을
    유도한다.
    """

    client: Any | None
    key: str = HOME_TOPICS_CACHE_KEY
    ttl_seconds: int = DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS
    enabled: bool = True

    def get(self) -> dict[str, Any] | None:
        """Cache hit payload를 반환하거나 miss/bypass 상황에서는 `None`을 반환한다."""

        if not self.enabled or self.client is None:
            logger.info("home_topics_cache event=bypass reason=disabled")
            return None

        try:
            cached = self.client.get(self.key)
        except (RedisError, TimeoutError, OSError) as exc:
            logger.warning(
                "home_topics_cache event=bypass operation=get error=%s",
                exc.__class__.__name__,
            )
            return None

        if cached is None:
            logger.info("home_topics_cache event=miss key=%s", self.key)
            return None

        try:
            payload = json.loads(cached)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "home_topics_cache event=bypass operation=decode error=%s",
                exc.__class__.__name__,
            )
            return None

        if not _is_valid_home_topics_payload(payload):
            logger.warning("home_topics_cache event=bypass operation=validate")
            return None

        logger.info("home_topics_cache event=hit key=%s", self.key)
        return payload

    def set(self, payload: dict[str, Any]) -> None:
        """응답 payload를 JSON으로 변환해 Redis에 저장하며 실패해도 요청을 유지한다."""

        if not self.enabled or self.client is None:
            logger.info("home_topics_cache event=bypass reason=disabled")
            return

        try:
            encoded = json.dumps(jsonable_encoder(payload), ensure_ascii=False)
            self.client.setex(self.key, self.ttl_seconds, encoded)
        except (RedisError, TimeoutError, OSError, TypeError, ValueError) as exc:
            logger.warning(
                "home_topics_cache event=bypass operation=set error=%s",
                exc.__class__.__name__,
            )
            return

        logger.info(
            "home_topics_cache event=store key=%s ttl_seconds=%s",
            self.key,
            self.ttl_seconds,
        )


def _is_valid_home_topics_payload(payload: Any) -> bool:
    """Cache payload가 `/topics/home` 응답에 필요한 최소 구조를 갖췄는지 검사한다."""

    if not isinstance(payload, dict):
        return False
    if "generated_at" not in payload or "topic_date" not in payload:
        return False
    items = payload.get("items")
    if not isinstance(items, list):
        return False

    required_item_keys = {
        "id",
        "topic_date",
        "title_ko",
        "summary_ko",
        "keywords",
        "source_count",
        "article_count",
    }
    return all(isinstance(item, dict) and required_item_keys <= set(item) for item in items)


def _int_from_env(name: str, default: int) -> int:
    """환경 변수의 양의 정수 값을 읽고 잘못된 값이면 기본값을 반환한다."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning("home_topics_cache invalid_int_env name=%s", name)
        return default
    return value if value > 0 else default


def _float_from_env(name: str, default: float) -> float:
    """환경 변수의 양의 실수 값을 읽고 잘못된 값이면 기본값을 반환한다."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning("home_topics_cache invalid_float_env name=%s", name)
        return default
    return value if value > 0 else default


@lru_cache(maxsize=1)
def get_home_topics_cache() -> HomeTopicsCache:
    """환경 설정을 바탕으로 `/topics/home` Redis cache client를 한 번만 생성한다."""

    redis_url = os.getenv("REDIS_URL")
    ttl_seconds = _int_from_env(
        "HOME_TOPICS_CACHE_TTL_SECONDS",
        DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS,
    )

    if not redis_url:
        return HomeTopicsCache(client=None, ttl_seconds=ttl_seconds, enabled=False)

    if Redis is None:
        logger.warning("home_topics_cache event=bypass reason=redis_dependency_missing")
        return HomeTopicsCache(client=None, ttl_seconds=ttl_seconds, enabled=False)

    timeout_seconds = _float_from_env(
        "REDIS_TIMEOUT_SECONDS",
        DEFAULT_REDIS_TIMEOUT_SECONDS,
    )
    try:
        client = Redis.from_url(
            redis_url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
            decode_responses=True,
        )
    except ValueError:
        logger.warning("home_topics_cache event=bypass reason=invalid_redis_url")
        return HomeTopicsCache(client=None, ttl_seconds=ttl_seconds, enabled=False)
    return HomeTopicsCache(client=client, ttl_seconds=ttl_seconds)
