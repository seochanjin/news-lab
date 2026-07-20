"""3일·Weekly Topic의 저장된 기간 metadata를 API 날짜 범위로 변환한다.

Topic row에 이미 저장된 Pipeline window와 기준 날짜를 입력받아 KST 기준
``[period_start, period_end)`` 날짜를 계산하고 서로의 일치 여부를 검증한다.
제목, ``created_at`` 또는 새 DB field에는 의존하지 않으며 DB 접근과 파일 쓰기
같은 부수 효과도 수행하지 않는다.
"""

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


BUSINESS_TIMEZONE = ZoneInfo("Asia/Seoul")
THREE_DAY_WINDOW = timedelta(days=3)
WEEKLY_WINDOW = timedelta(days=7)


def calculate_three_day_topic_period(
    *,
    reference_date: date,
    window_start: datetime,
    window_end: datetime,
) -> tuple[date, date]:
    """정확한 72시간 window를 KST 3일 날짜 범위로 계산한다.

    ``period_start``는 window 시작 instant의 KST 날짜이고 ``period_end``는
    window 종료 경계 instant의 KST 날짜다. 기본 Pipeline처럼 경계가 자정이
    아니어도 72시간 계약과 ``reference_date``가 일치하면 같은 세 날짜 범위를
    반환한다. 입력이 timezone-aware가 아니거나 저장 metadata가 Pipeline 계약과
    다르면 ``ValueError``를 발생시킨다.
    """

    _require_date(reference_date, "reference_date")
    _validate_aware_window(window_start, window_end, THREE_DAY_WINDOW, "three-day")
    period_start = window_start.astimezone(BUSINESS_TIMEZONE).date()
    period_end = window_end.astimezone(BUSINESS_TIMEZONE).date()
    if period_end != reference_date:
        raise ValueError(
            "reference_date must match the Asia/Seoul date of window_end"
        )
    if period_end - period_start != THREE_DAY_WINDOW:
        raise ValueError("three-day KST period must span exactly 3 dates")
    return period_start, period_end


def calculate_weekly_topic_period(
    *,
    week_start: date,
    week_end: date,
    window_start: datetime,
    window_end: datetime,
) -> tuple[date, date]:
    """완료된 월요일~일요일 window를 KST end-exclusive 날짜 범위로 계산한다.

    저장된 ``week_start``와 포함 마지막 날짜인 ``week_end``를 기존 정확한 7일
    Pipeline window와 대조한다. 모든 값이 일치하면 월요일과 다음 월요일을
    반환하고, 불일치하거나 timezone 정보가 없으면 ``ValueError``를 발생시킨다.
    """

    _require_date(week_start, "week_start")
    _require_date(week_end, "week_end")
    _validate_aware_window(window_start, window_end, WEEKLY_WINDOW, "weekly")
    period_end = week_end + timedelta(days=1)
    if week_start.weekday() != 0:
        raise ValueError("week_start must be a Monday")
    if period_end - week_start != WEEKLY_WINDOW:
        raise ValueError("weekly period must span exactly 7 dates")

    local_start = window_start.astimezone(BUSINESS_TIMEZONE)
    local_end = window_end.astimezone(BUSINESS_TIMEZONE)
    if local_start.date() != week_start or local_end.date() != period_end:
        raise ValueError("weekly dates must match the Asia/Seoul window boundaries")
    if local_start.timetz().replace(tzinfo=None) != datetime.min.time():
        raise ValueError("weekly window_start must be Asia/Seoul midnight")
    if local_end.timetz().replace(tzinfo=None) != datetime.min.time():
        raise ValueError("weekly window_end must be Asia/Seoul midnight")
    return week_start, period_end


def with_three_day_topic_period(row: Mapping[str, object]) -> dict:
    """3일 Topic mapping을 복사하고 계산된 두 period field를 추가한다."""

    item = dict(row)
    period_start, period_end = calculate_three_day_topic_period(
        reference_date=item["reference_date"],
        window_start=item["window_start"],
        window_end=item["window_end"],
    )
    item["period_start"] = period_start
    item["period_end"] = period_end
    return item


def with_weekly_topic_period(row: Mapping[str, object]) -> dict:
    """Weekly Topic mapping을 복사하고 계산된 두 period field를 추가한다."""

    item = dict(row)
    period_start, period_end = calculate_weekly_topic_period(
        week_start=item["week_start"],
        week_end=item["week_end"],
        window_start=item["window_start"],
        window_end=item["window_end"],
    )
    item["period_start"] = period_start
    item["period_end"] = period_end
    return item


def _validate_aware_window(
    window_start: datetime,
    window_end: datetime,
    expected_duration: timedelta,
    period_name: str,
) -> None:
    """두 경계가 timezone-aware이고 순서와 예상 길이를 지키는지 검증한다."""

    _require_aware_datetime(window_start, "window_start")
    _require_aware_datetime(window_end, "window_end")
    if window_start >= window_end:
        raise ValueError("window_start must be earlier than window_end")
    if window_end - window_start != expected_duration:
        raise ValueError(f"{period_name} window has an invalid duration")


def _require_aware_datetime(value: object, field_name: str) -> None:
    """값이 absolute instant를 나타내는 timezone-aware datetime인지 확인한다."""

    if not isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _require_date(value: object, field_name: str) -> None:
    """값이 datetime이 아닌 순수 date인지 확인한다."""

    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"{field_name} must be a date")
