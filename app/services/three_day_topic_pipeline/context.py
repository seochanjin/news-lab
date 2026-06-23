"""3일 Topic pipeline 전체가 공유하는 서울 기준 72시간 context를 생성한다.

실행 시작 시각 또는 명시적으로 주입한 window 종료 시각을 UTC absolute instant로
정규화하고, 후보 조회부터 저장까지 전달할 단일 context를 반환한다. DB 조회,
파일 쓰기, subprocess 실행은 수행하지 않는다.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import ThreeDayPipelineContext


BUSINESS_TIMEZONE = "Asia/Seoul"
WINDOW_HOURS = 72


def resolve_three_day_pipeline_context(
    *,
    started_at_utc: datetime | None = None,
    window_end: datetime | None = None,
    business_timezone: str = BUSINESS_TIMEZONE,
) -> ThreeDayPipelineContext:
    """한 실행에서 재사용할 기준일과 `[start, end)` 72시간 범위를 결정한다.

    `started_at_utc`와 `window_end`는 timezone-aware 값만 허용한다. `window_end`가
    주입되면 재현 실행 범위로 사용하고, 없으면 실행 시작 instant를 종료 경계로
    사용한다. 모든 absolute 시각은 UTC로 정규화하며 서울 local 표현과 기준일도
    함께 보관한다.
    """

    started_at = started_at_utc or datetime.now(timezone.utc)
    _require_aware(started_at, "started_at_utc")
    started_at = started_at.astimezone(timezone.utc)

    resolved_window_end = window_end or started_at
    _require_aware(resolved_window_end, "window_end")
    resolved_window_end = resolved_window_end.astimezone(timezone.utc)
    resolved_window_start = resolved_window_end - timedelta(hours=WINDOW_HOURS)

    timezone_info = ZoneInfo(business_timezone)
    started_at_local = started_at.astimezone(timezone_info)
    window_end_local = resolved_window_end.astimezone(timezone_info)
    return ThreeDayPipelineContext(
        reference_date=window_end_local.date(),
        business_timezone=business_timezone,
        started_at_utc=started_at,
        started_at_local=started_at_local,
        window_start=resolved_window_start,
        window_end=resolved_window_end,
        window_hours=WINDOW_HOURS,
        window_source="explicit_window_end" if window_end is not None else "started_at",
    )


def _require_aware(value: datetime, field_name: str) -> None:
    """입력 시각이 timezone-aware absolute instant인지 확인한다."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
