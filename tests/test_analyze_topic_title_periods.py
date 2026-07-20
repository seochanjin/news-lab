"""기존 Topic 전수 점검 도구의 무기록 집계와 read-only SQL을 검증한다.

가짜 Topic row와 connection만 사용하며 실제 PostgreSQL, Production API, 파일 쓰기
또는 DB 변경은 수행하지 않는다. 제목 원문 없는 count와 기간 실패 판정을 확인한다.
"""

import unittest
from datetime import date, datetime, timezone

from scripts.analyze_topic_title_periods import (
    analyze_existing_topics,
    has_blocking_findings,
    load_existing_topic_rows,
)


class FakeResult:
    """Analyzer가 사용하는 mapping result chain과 row 목록을 제공한다."""

    def __init__(self, rows):
        """단일 query가 반환할 가짜 row를 보관한다."""

        self.rows = rows

    def mappings(self):
        """SQLAlchemy mapping chain을 흉내 내기 위해 자기 자신을 반환한다."""

        return self

    def all(self):
        """보관한 row를 query 결과로 반환한다."""

        return self.rows


class FakeConnection:
    """실행 SQL을 기록하고 query 순서에 맞는 결과를 반환한다."""

    def __init__(self, results):
        """Read-only 설정을 포함한 네 execute 결과를 초기화한다."""

        self.results = list(results)
        self.calls = []

    def execute(self, query):
        """SQL을 기록하고 준비된 다음 결과를 반환한다."""

        self.calls.append(str(query))
        return self.results.pop(0)


def valid_rows():
    """정제 변경·fallback·유지와 정상 period를 함께 포함한 fixture를 만든다."""

    return {
        "topics": [
            {
                "id": 1,
                "title_ko": "2026-07-12 AI 반도체 경쟁",
                "keywords": ["반도체"],
            }
        ],
        "three_day_topics": [
            {
                "id": 31,
                "title_ko": "(월요일~일요일)",
                "keywords": ["정책 변화"],
                "reference_date": date(2026, 7, 14),
                "window_start": datetime(2026, 7, 10, 20, tzinfo=timezone.utc),
                "window_end": datetime(2026, 7, 13, 20, tzinfo=timezone.utc),
            }
        ],
        "weekly_topics": [
            {
                "id": 71,
                "title_ko": "시장 공급 변화",
                "keywords": ["시장"],
                "week_start": date(2026, 7, 6),
                "week_end": date(2026, 7, 12),
                "window_start": datetime(2026, 7, 5, 15, tzinfo=timezone.utc),
                "window_end": datetime(2026, 7, 12, 15, tzinfo=timezone.utc),
            }
        ],
    }


class AnalyzeTopicTitlePeriodsTests(unittest.TestCase):
    """전수 점검 count, 실패 verdict와 transaction 설정을 검증한다."""

    def test_aggregates_sanitized_counts_without_exposing_row_values(self):
        """정상 fixture는 요구된 모든 count를 만들고 원문이나 row ID를 노출하지 않는다."""

        result = analyze_existing_topics(valid_rows(), source="sanitized_fixture")

        self.assertEqual(result["totals"]["row_count"], 3)
        self.assertEqual(result["totals"]["sanitize_changed_count"], 2)
        self.assertEqual(result["totals"]["sanitize_unchanged_count"], 1)
        self.assertEqual(result["totals"]["fallback_required_count"], 1)
        self.assertEqual(result["totals"]["period_calculation_success_count"], 2)
        self.assertFalse(has_blocking_findings(result))
        self.assertFalse(result["analysis"]["title_values_exposed"])
        self.assertNotIn("2026-07-12 AI 반도체 경쟁", repr(result))
        self.assertNotIn("rows", result)
        self.assertNotIn("examples", result)

    def test_invalid_period_is_counted_as_calculation_failure(self):
        """기존 window 계약이 깨진 row는 추정하지 않고 period 실패로 집계한다."""

        rows = valid_rows()
        rows["three_day_topics"][0]["window_start"] = datetime(
            2026, 7, 11, 20, tzinfo=timezone.utc
        )

        result = analyze_existing_topics(rows, source="sanitized_fixture")

        self.assertEqual(result["totals"]["period_calculation_failure_count"], 1)
        self.assertTrue(has_blocking_findings(result))

    def test_database_loader_sets_read_only_before_all_selects(self):
        """전체 table 조회보다 먼저 transaction read-only가 실행되고 write SQL은 없다."""

        connection = FakeConnection(
            [FakeResult([]), FakeResult([]), FakeResult([]), FakeResult([])]
        )

        result = load_existing_topic_rows(connection)

        self.assertEqual(connection.calls[0].strip().lower(), "set transaction read only")
        self.assertEqual(set(result), {"topics", "three_day_topics", "weekly_topics"})
        self.assertEqual(len(connection.calls), 4)
        self.assertTrue(
            all(
                call.strip().lower().startswith(("set transaction read only", "select"))
                for call in connection.calls
            )
        )


if __name__ == "__main__":
    unittest.main()
