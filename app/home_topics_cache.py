"""Home Topics API 응답을 Redis에 저장하고 조회하는 cache-aside 계층이다.

이 모듈은 PostgreSQL에서 만들어진 Daily, 3-day와 Weekly Home API 응답 payload를
Pipeline 주기보다 긴 기본 TTL로 Redis에 보관한다. Redis는 source of truth가 아니므로
읽기, 쓰기, 연결, timeout, payload decode 오류가 발생하면 예외를 요청 처리
경로로 전파하지 않고 호출자가 PostgreSQL 조회를 계속할 수 있도록 cache miss
형태로 반환한다.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - dependency 설치 전 local import 보호
    Redis = None
    RedisError = Exception

from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

HOME_TOPICS_CACHE_KEY = "topics:home:v1"
THREE_DAY_HOME_TOPICS_CACHE_KEY = "three-day-topics:home:v1"
WEEKLY_HOME_TOPICS_CACHE_KEY = "weekly-topics:home:v1"
DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS = 108000
DEFAULT_THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS = 108000
DEFAULT_WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS = 691200
DEFAULT_REDIS_TIMEOUT_SECONDS = 0.05


@dataclass
class HomeTopicsCache:
    """Home API payload별 Redis cache 동작을 캡슐화한다.

    `client`가 없으면 cache가 비활성화된 상태로 동작한다. `key`와
    `payload_validator`로 Daily, 3-day와 Weekly Home payload를 구분한다. 모든 Redis
    예외와 payload decode 실패는 로그에 남기고 `None`을 반환해 PostgreSQL
    fallback을 유도한다.
    """

    client: Any | None
    key: str = HOME_TOPICS_CACHE_KEY
    ttl_seconds: int = DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS
    enabled: bool = True
    payload_validator: Callable[[Any], bool] | None = None

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

        validator = self.payload_validator or _payload_validator_for_key(self.key)
        if not validator(payload):
            logger.warning("home_topics_cache event=bypass operation=validate")
            return None

        logger.info("home_topics_cache event=hit key=%s", self.key)
        return payload

    def set(self, payload: dict[str, Any], *, operation: str = "store") -> None:
        """응답 payload를 JSON으로 변환해 Redis에 저장하며 실패해도 호출 흐름을 유지한다.

        `operation`은 API cache-aside 저장과 pipeline prewarm 저장을 로그에서
        구분하기 위한 값이다. Redis key와 TTL 정책은 동일하게 적용한다.
        """

        if not self.enabled or self.client is None:
            logger.info(
                "home_topics_cache event=bypass operation=%s reason=disabled",
                operation,
            )
            return

        try:
            encoded = json.dumps(jsonable_encoder(payload), ensure_ascii=False)
            self.client.setex(self.key, self.ttl_seconds, encoded)
        except (RedisError, TimeoutError, OSError, TypeError, ValueError) as exc:
            logger.warning(
                "home_topics_cache event=bypass operation=%s error=%s",
                operation,
                exc.__class__.__name__,
            )
            return

        logger.info(
            "home_topics_cache event=%s key=%s ttl_seconds=%s",
            operation,
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


def _is_valid_three_day_home_topics_payload(payload: Any) -> bool:
    """Cache payload가 `/three-day-topics/home` 응답 최소 구조를 갖췄는지 검사한다."""

    if not isinstance(payload, dict):
        return False
    for key in ("generated_at", "reference_date", "window_start", "window_end"):
        if key not in payload:
            return False
    items = payload.get("items")
    if not isinstance(items, list):
        return False

    required_item_keys = {
        "id",
        "reference_date",
        "window_start",
        "window_end",
        "title_ko",
        "summary_ko",
        "keywords",
        "source_count",
        "article_count",
    }
    return all(isinstance(item, dict) and required_item_keys <= set(item) for item in items)


def _is_valid_weekly_home_topics_payload(payload: Any) -> bool:
    """Cache payload가 `/weekly-topics/home` 응답 최소 구조를 갖췄는지 검사한다."""

    if not isinstance(payload, dict):
        return False
    for key in ("generated_at", "week_start", "week_end", "window_start", "window_end"):
        if key not in payload:
            return False
    items = payload.get("items")
    if not isinstance(items, list):
        return False

    required_item_keys = {
        "id",
        "week_start",
        "week_end",
        "window_start",
        "window_end",
        "title_ko",
        "summary_ko",
        "keywords",
        "source_count",
        "article_count",
    }
    return all(isinstance(item, dict) and required_item_keys <= set(item) for item in items)


def _payload_validator_for_key(key: str) -> Callable[[Any], bool]:
    """Redis key에 맞는 Home payload validator를 반환한다."""

    if key == THREE_DAY_HOME_TOPICS_CACHE_KEY:
        return _is_valid_three_day_home_topics_payload
    if key == WEEKLY_HOME_TOPICS_CACHE_KEY:
        return _is_valid_weekly_home_topics_payload
    return _is_valid_home_topics_payload


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


def _build_home_topics_cache(
    *,
    key: str,
    ttl_env_name: str,
    default_ttl_seconds: int,
    payload_validator: Callable[[Any], bool],
) -> HomeTopicsCache:
    """공통 Redis 환경 설정으로 Home API별 cache client를 생성한다."""

    redis_url = os.getenv("REDIS_URL")
    ttl_seconds = _int_from_env(
        ttl_env_name,
        default_ttl_seconds,
    )

    if not redis_url:
        return HomeTopicsCache(
            client=None,
            key=key,
            ttl_seconds=ttl_seconds,
            enabled=False,
            payload_validator=payload_validator,
        )

    if Redis is None:
        logger.warning("home_topics_cache event=bypass reason=redis_dependency_missing")
        return HomeTopicsCache(
            client=None,
            key=key,
            ttl_seconds=ttl_seconds,
            enabled=False,
            payload_validator=payload_validator,
        )

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
        return HomeTopicsCache(
            client=None,
            key=key,
            ttl_seconds=ttl_seconds,
            enabled=False,
            payload_validator=payload_validator,
        )
    return HomeTopicsCache(
        client=client,
        key=key,
        ttl_seconds=ttl_seconds,
        payload_validator=payload_validator,
    )


@lru_cache(maxsize=1)
def get_home_topics_cache() -> HomeTopicsCache:
    """환경 설정을 바탕으로 `/topics/home` Redis cache client를 한 번만 생성한다."""

    return _build_home_topics_cache(
        key=HOME_TOPICS_CACHE_KEY,
        ttl_env_name="HOME_TOPICS_CACHE_TTL_SECONDS",
        default_ttl_seconds=DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS,
        payload_validator=_is_valid_home_topics_payload,
    )


@lru_cache(maxsize=1)
def get_three_day_home_topics_cache() -> HomeTopicsCache:
    """환경 설정을 바탕으로 `/three-day-topics/home` Redis cache client를 생성한다."""

    return _build_home_topics_cache(
        key=THREE_DAY_HOME_TOPICS_CACHE_KEY,
        ttl_env_name="THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS",
        default_ttl_seconds=DEFAULT_THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS,
        payload_validator=_is_valid_three_day_home_topics_payload,
    )


@lru_cache(maxsize=1)
def get_weekly_home_topics_cache() -> HomeTopicsCache:
    """환경 설정을 바탕으로 `/weekly-topics/home` Redis cache client를 생성한다."""

    return _build_home_topics_cache(
        key=WEEKLY_HOME_TOPICS_CACHE_KEY,
        ttl_env_name="WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS",
        default_ttl_seconds=DEFAULT_WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS,
        payload_validator=_is_valid_weekly_home_topics_payload,
    )
