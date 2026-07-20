"""3일·Weekly Topic의 KST end-exclusive API 기간 계산 계약을 검증한다.

Timezone-aware fixture만 사용해 순수 계산과 row serialization을 확인하며 실제 DB,
Redis, Pipeline 또는 Production API에는 접근하지 않는다.
"""

import unittest
from datetime import date, datetime, timedelta, timezone

from fastapi.encoders import jsonable_encoder

from app.utils.topic_period import (
    calculate_three_day_topic_period,
    calculate_weekly_topic_period,
    with_three_day_topic_period,
)


class ThreeDayTopicPeriodTests(unittest.TestCase):
    """정확한 72시간 window의 KST 날짜 투영과 metadata 검증을 확인한다."""

    def test_non_midnight_window_uses_kst_boundary_dates(self):
        """05시 실행 window도 직전 세 KST 날짜의 end-exclusive 범위를 반환한다."""

        period = calculate_three_day_topic_period(
            reference_date=date(2026, 7, 15),
            window_start=datetime(2026, 7, 11, 20, tzinfo=timezone.utc),
            window_end=datetime(2026, 7, 14, 20, tzinfo=timezone.utc),
        )

        self.assertEqual(period, (date(2026, 7, 12), date(2026, 7, 15)))

    def test_period_ignores_title_and_created_at(self):
        """제목과 생성 시각이 달라도 같은 Pipeline metadata는 같은 기간을 만든다."""

        base_row = {
            "reference_date": date(2026, 7, 15),
            "window_start": datetime(2026, 7, 11, 20, tzinfo=timezone.utc),
            "window_end": datetime(2026, 7, 14, 20, tzinfo=timezone.utc),
        }
        first = with_three_day_topic_period(
            {
                **base_row,
                "title_ko": "7월 12일~7월 15일 반도체 경쟁",
                "created_at": datetime(2026, 7, 14, 21, tzinfo=timezone.utc),
            }
        )
        second = with_three_day_topic_period(
            {
                **base_row,
                "title_ko": "반도체 경쟁",
                "created_at": datetime(2026, 7, 15, 1, tzinfo=timezone.utc),
            }
        )

        self.assertEqual(first["period_start"], second["period_start"])
        self.assertEqual(first["period_end"], second["period_end"])
        self.assertEqual(first["title_ko"], "7월 12일~7월 15일 반도체 경쟁")

    def test_period_dates_serialize_as_iso_date_strings(self):
        """FastAPI JSON encoding에서 두 period field가 YYYY-MM-DD 문자열이 된다."""

        item = with_three_day_topic_period(
            {
                "reference_date": date(2026, 7, 15),
                "window_start": datetime(2026, 7, 11, 20, tzinfo=timezone.utc),
                "window_end": datetime(2026, 7, 14, 20, tzinfo=timezone.utc),
            }
        )

        encoded = jsonable_encoder(item)

        self.assertEqual(encoded["period_start"], "2026-07-12")
        self.assertEqual(encoded["period_end"], "2026-07-15")

    def test_invalid_window_or_reference_date_is_rejected(self):
        """72시간 길이와 KST 종료일 중 하나라도 어긋난 row를 거부한다."""

        valid_start = datetime(2026, 7, 11, 20, tzinfo=timezone.utc)
        valid_end = datetime(2026, 7, 14, 20, tzinfo=timezone.utc)
        cases = (
            {
                "reference_date": date(2026, 7, 14),
                "window_start": valid_start,
                "window_end": valid_end,
            },
            {
                "reference_date": date(2026, 7, 15),
                "window_start": valid_start,
                "window_end": valid_end + timedelta(hours=1),
            },
            {
                "reference_date": date(2026, 7, 15),
                "window_start": datetime(2026, 7, 12, 5),
                "window_end": datetime(2026, 7, 15, 5),
            },
        )

        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                calculate_three_day_topic_period(**case)


class WeeklyTopicPeriodTests(unittest.TestCase):
    """완료 주간 metadata의 다음 월요일 end-exclusive 변환을 검증한다."""

    def test_completed_week_returns_next_monday_as_period_end(self):
        """월요일~일요일 저장 계약을 `[월요일, 다음 월요일)`로 반환한다."""

        period = calculate_weekly_topic_period(
            week_start=date(2026, 7, 6),
            week_end=date(2026, 7, 12),
            window_start=datetime(2026, 7, 5, 15, tzinfo=timezone.utc),
            window_end=datetime(2026, 7, 12, 15, tzinfo=timezone.utc),
        )

        self.assertEqual(period, (date(2026, 7, 6), date(2026, 7, 13)))

    def test_misaligned_week_metadata_is_rejected(self):
        """월요일 시작, 포함 마지막 일요일과 KST 자정 window 불일치를 거부한다."""

        cases = (
            {
                "week_start": date(2026, 7, 7),
                "week_end": date(2026, 7, 13),
                "window_start": datetime(2026, 7, 6, 15, tzinfo=timezone.utc),
                "window_end": datetime(2026, 7, 13, 15, tzinfo=timezone.utc),
            },
            {
                "week_start": date(2026, 7, 6),
                "week_end": date(2026, 7, 12),
                "window_start": datetime(2026, 7, 5, 16, tzinfo=timezone.utc),
                "window_end": datetime(2026, 7, 12, 16, tzinfo=timezone.utc),
            },
        )

        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                calculate_weekly_topic_period(**case)


if __name__ == "__main__":
    unittest.main()
