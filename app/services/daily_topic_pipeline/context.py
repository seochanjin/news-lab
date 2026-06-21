"""Shared execution context for the daily topic pipeline."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .models import PipelineContext


BUSINESS_TIMEZONE = "Asia/Seoul"


def resolve_pipeline_context(
    *,
    started_at_utc=None,
    business_timezone=BUSINESS_TIMEZONE,
):
    """Pipeline 시작 시각을 기준으로 공유 실행 context를 한 번 생성한다.

    `started_at_utc`는 absolute instant를 표현하는 timezone-aware datetime만
    허용한다. 입력 시각은 UTC로 정규화한 뒤 기본 `Asia/Seoul` 업무 시간대로
    변환한다. 반환된 `pipeline_date`를 모든 stage와 topic 저장에 전달해 자정
    경계에서도 서로 다른 날짜가 계산되지 않게 한다.
    """

    started_at_utc = started_at_utc or datetime.now(timezone.utc)
    if started_at_utc.tzinfo is None:
        raise ValueError(
            "started_at_utc must be timezone-aware and represent "
            "an absolute instant"
        )
    started_at_utc = started_at_utc.astimezone(timezone.utc)

    # Resolve the business date once so every stage and DB save uses one date.
    started_at_local = started_at_utc.astimezone(ZoneInfo(business_timezone))
    return PipelineContext(
        pipeline_date=started_at_local.date(),
        business_timezone=business_timezone,
        started_at_utc=started_at_utc,
        started_at_local=started_at_local,
        pipeline_date_source="started_at_local",
    )
