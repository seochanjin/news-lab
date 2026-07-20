"""기존 Topic 제목 정제와 3일·Weekly 기간 계약을 write 없이 전수 점검한다.

설정된 PostgreSQL의 Daily·3-day·Weekly Topic row 또는 운영자가 정제한 JSON
fixture를 입력받아 제목 변경·fallback·잔존 pattern과 기간 계산 결과를 건수로만
출력한다. DB 모드에서는 transaction read-only를 query보다 먼저 설정하며 원본
제목, keyword와 row별 내용을 출력하거나 DB·fixture를 수정하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from app.utils.topic_period import (
    calculate_three_day_topic_period,
    calculate_weekly_topic_period,
)
from app.utils.topic_title import (
    has_forbidden_topic_title_pattern,
    topic_title_requires_fallback,
    with_sanitized_topic_title,
)


DATASET_NAMES = ("topics", "three_day_topics", "weekly_topics")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """DB와 sanitized fixture 중 하나의 read-only 입력 방식을 선택한다."""

    parser = argparse.ArgumentParser(
        description="Read-only audit for stored Topic titles and periods.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Read a sanitized JSON fixture instead of DATABASE_URL.",
    )
    return parser.parse_args(argv)


def create_database_engine():
    """환경의 DATABASE_URL로 기존 PostgreSQL을 읽을 SQLAlchemy engine을 만든다."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


def load_existing_topic_rows(connection) -> dict[str, list[Mapping[str, Any]]]:
    """Read-only transaction에서 세 Topic table의 검증 필드 전체를 조회한다."""

    connection.execute(text("set transaction read only"))
    topics = connection.execute(
        text("select id, title_ko, keywords from topics order by id")
    ).mappings().all()
    three_day_topics = connection.execute(
        text("""
            select id, title_ko, keywords, reference_date, window_start, window_end
            from three_day_topics
            order by id
        """)
    ).mappings().all()
    weekly_topics = connection.execute(
        text("""
            select id, title_ko, keywords, week_start, week_end,
                   window_start, window_end
            from weekly_topics
            order by id
        """)
    ).mappings().all()
    return {
        "topics": list(topics),
        "three_day_topics": list(three_day_topics),
        "weekly_topics": list(weekly_topics),
    }


def load_sanitized_fixture(path: Path) -> dict[str, list[Mapping[str, Any]]]:
    """원문을 노출하지 않는 운영자 제공 JSON fixture의 날짜형 값을 복원한다."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture root must be an object")

    rows_by_dataset: dict[str, list[Mapping[str, Any]]] = {}
    for dataset_name in DATASET_NAMES:
        rows = payload.get(dataset_name, [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"fixture {dataset_name} must be a list of objects")
        rows_by_dataset[dataset_name] = [
            _deserialize_fixture_row(dataset_name, row) for row in rows
        ]
    return rows_by_dataset


def analyze_existing_topics(
    rows_by_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    source: str,
) -> dict[str, Any]:
    """제목과 기간 검증 결과를 dataset별·전체 건수로 집계한다.

    개별 row 값은 결과에 포함하지 않는다. 제목 정제 예외와 기간 계산 예외도
    중단시키지 않고 각각 미처리 실패와 계산 실패 건수로 집계한다.
    """

    datasets = {
        dataset_name: _analyze_dataset(
            dataset_name,
            rows_by_dataset.get(dataset_name, ()),
        )
        for dataset_name in DATASET_NAMES
    }
    totals = {
        key: sum(dataset[key] for dataset in datasets.values())
        for key in (
            "row_count",
            "sanitize_changed_count",
            "sanitize_unchanged_count",
            "fallback_required_count",
            "residual_date_pattern_count",
            "unhandled_sanitize_failure_count",
            "period_calculation_success_count",
            "period_calculation_failure_count",
            "invalid_period_count",
        )
    }
    return {
        "analysis": {
            "source": source,
            "read_only": True,
            "db_write_performed": False,
            "title_values_exposed": False,
        },
        "datasets": datasets,
        "totals": totals,
    }


def has_blocking_findings(result: Mapping[str, Any]) -> bool:
    """Task의 기존 데이터 완료 조건을 위반하는 집계가 하나라도 있는지 판단한다."""

    totals = result["totals"]
    return any(
        totals[key] != 0
        for key in (
            "residual_date_pattern_count",
            "unhandled_sanitize_failure_count",
            "period_calculation_failure_count",
            "invalid_period_count",
        )
    )


def _analyze_dataset(
    dataset_name: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """단일 Topic 종류의 제목과 적용 가능한 기간 결과를 건수로 계산한다."""

    counts = {
        "row_count": len(rows),
        "sanitize_changed_count": 0,
        "sanitize_unchanged_count": 0,
        "fallback_required_count": 0,
        "residual_date_pattern_count": 0,
        "unhandled_sanitize_failure_count": 0,
        "period_calculation_success_count": 0,
        "period_calculation_failure_count": 0,
        "invalid_period_count": 0,
    }
    for row in rows:
        try:
            sanitized = with_sanitized_topic_title(row)["title_ko"]
            if sanitized == row.get("title_ko"):
                counts["sanitize_unchanged_count"] += 1
            else:
                counts["sanitize_changed_count"] += 1
            if topic_title_requires_fallback(row.get("title_ko")):
                counts["fallback_required_count"] += 1
            if has_forbidden_topic_title_pattern(sanitized):
                counts["residual_date_pattern_count"] += 1
        except (TypeError, ValueError):
            counts["unhandled_sanitize_failure_count"] += 1

        if dataset_name == "topics":
            continue
        try:
            period_start, period_end = _calculate_period(dataset_name, row)
            counts["period_calculation_success_count"] += 1
            expected_days = 3 if dataset_name == "three_day_topics" else 7
            if period_start >= period_end or (period_end - period_start).days != expected_days:
                counts["invalid_period_count"] += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            counts["period_calculation_failure_count"] += 1
    return counts


def _calculate_period(
    dataset_name: str,
    row: Mapping[str, Any],
) -> tuple[date, date]:
    """Dataset 종류에 맞는 기존 metadata 기반 period utility를 호출한다."""

    if dataset_name == "three_day_topics":
        return calculate_three_day_topic_period(
            reference_date=row["reference_date"],
            window_start=row["window_start"],
            window_end=row["window_end"],
        )
    return calculate_weekly_topic_period(
        week_start=row["week_start"],
        week_end=row["week_end"],
        window_start=row["window_start"],
        window_end=row["window_end"],
    )


def _deserialize_fixture_row(
    dataset_name: str,
    row: Mapping[str, Any],
) -> dict[str, Any]:
    """JSON fixture의 기간 문자열만 utility 입력용 date·datetime으로 변환한다."""

    item = dict(row)
    date_fields = {
        "three_day_topics": ("reference_date",),
        "weekly_topics": ("week_start", "week_end"),
    }.get(dataset_name, ())
    for field_name in date_fields:
        if field_name in item:
            item[field_name] = date.fromisoformat(item[field_name])
    for field_name in ("window_start", "window_end"):
        if field_name in item:
            item[field_name] = datetime.fromisoformat(
                item[field_name].replace("Z", "+00:00")
            )
    return item


def main(argv: Sequence[str] | None = None) -> int:
    """선택한 source를 분석해 값 없는 집계 JSON을 출력하고 위반 시 실패한다."""

    args = parse_args(argv)
    if args.fixture:
        rows_by_dataset = load_sanitized_fixture(args.fixture)
        source = "sanitized_fixture"
    else:
        engine = create_database_engine()
        with engine.connect() as connection:
            rows_by_dataset = load_existing_topic_rows(connection)
        source = "configured_database"

    result = analyze_existing_topics(rows_by_dataset, source=source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if has_blocking_findings(result) else 0


if __name__ == "__main__":
    raise SystemExit(main())
