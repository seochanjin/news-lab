"""7일 Topic pipeline 전체가 공유하는 서울 기준 완료 주간 context를 생성한다.

실행 시작 시각 또는 명시적인 `week_start`를 바탕으로 월요일 00:00 이상부터 다음
월요일 00:00 미만까지의 단일 주간 window를 결정한다. 반환된 context는 후보
조회부터 저장까지 같은 범위를 주입하기 위한 값 객체이며 DB 조회, 파일 쓰기,
subprocess 실행은 수행하지 않는다.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import (
    BUSINESS_TIMEZONE_NAME,
    WEEKLY_WINDOW,
    WeeklyPipelineContext,
)


def resolve_weekly_pipeline_context(
    *,
    started_at_utc: datetime | None = None,
    week_start: date | None = None,
    business_timezone: str = BUSINESS_TIMEZONE_NAME,
) -> WeeklyPipelineContext:
    """한 실행에서 재사용할 완료 주간 날짜와 `[start, end)` 7일 범위를 결정한다.

    `started_at_utc`는 timezone-aware 값만 허용한다. `week_start`가 주입되면
    명시 재처리 범위로 사용하고, 없으면 실행 시점보다 앞선 가장 최근 완료된
    서울 기준 월요일-일요일 주간을 선택한다. Absolute 시각은 UTC로 정규화한다.
    """

    started_at = started_at_utc or datetime.now(timezone.utc)
    _require_aware(started_at, "started_at_utc")
    started_at = started_at.astimezone(timezone.utc)

    timezone_info = ZoneInfo(business_timezone)
    started_at_local = started_at.astimezone(timezone_info)
    resolved_week_start = week_start or _previous_completed_week_start(
        started_at_local
    )
    if resolved_week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")

    resolved_week_end = resolved_week_start + timedelta(days=6)
    window_start_local = datetime.combine(
        resolved_week_start,
        time.min,
        tzinfo=timezone_info,
    )
    window_end_local = window_start_local + WEEKLY_WINDOW

    return WeeklyPipelineContext(
        week_start=resolved_week_start,
        week_end=resolved_week_end,
        business_timezone=business_timezone,
        started_at_utc=started_at,
        started_at_local=started_at_local,
        window_start=window_start_local.astimezone(timezone.utc),
        window_end=window_end_local.astimezone(timezone.utc),
        window_days=7,
        window_source="explicit_week_start" if week_start is not None else "started_at",
    )


def _previous_completed_week_start(started_at_local: datetime) -> date:
    """실행 시각보다 앞선 가장 최근 완료 주간의 월요일 날짜를 반환한다."""

    current_week_start = started_at_local.date() - timedelta(
        days=started_at_local.weekday()
    )
    return current_week_start - timedelta(days=7)


def _require_aware(value: datetime, field_name: str) -> None:
    """입력 시각이 timezone-aware absolute instant인지 확인한다."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")

