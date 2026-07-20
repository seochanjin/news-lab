"""Topic 제목 sanitizer와 deterministic fallback 계약을 검증한다.

DB나 외부 provider를 호출하지 않고 날짜·기간 제거, 내용 숫자 보존, 길이와
잔존 pattern 검증, keyword·대표 기사 제목 fallback 순서를 확인한다.
"""

import unittest

from app.utils.topic_title import (
    MAX_TOPIC_TITLE_LENGTH,
    has_forbidden_topic_title_pattern,
    is_valid_topic_title,
    sanitize_topic_title,
    topic_title_requires_fallback,
    with_sanitized_topic_title,
)


class TopicTitleSanitizerTests(unittest.TestCase):
    """공통 제목 신뢰 경계의 정제·검증·fallback 회귀를 검증한다."""

    def test_normal_title_is_preserved_after_basic_whitespace_normalization(self):
        """날짜가 없는 정상 제목은 내용 변경 없이 공백만 정규화한다."""

        self.assertEqual(
            sanitize_topic_title("  AI   반도체 투자 경쟁  "),
            "AI 반도체 투자 경쟁",
        )

    def test_period_and_date_patterns_are_removed(self):
        """상대 기간, 숫자 날짜, 요일 범위와 괄호형 기간을 제목에서 제거한다."""

        cases = {
            "3일차 기록: AI 반도체 경쟁": "기록 AI 반도체 경쟁",
            "최근 3일 AI 반도체 경쟁": "AI 반도체 경쟁",
            "72시간 기록 - AI 반도체 경쟁": "기록 AI 반도체 경쟁",
            "7월 12일~7월 15일 AI 반도체 경쟁": "AI 반도체 경쟁",
            "2026-07-12 AI 반도체 경쟁": "AI 반도체 경쟁",
            "2026.07.12 AI 반도체 경쟁": "AI 반도체 경쟁",
            "2026 AI 반도체 경쟁": "AI 반도체 경쟁",
            "7월 AI 반도체 경쟁": "AI 반도체 경쟁",
            "(월~일) 주간 AI 반도체 경쟁": "AI 반도체 경쟁",
            "(월요일~일요일) AI 반도체 경쟁": "AI 반도체 경쟁",
            "월요일의 AI 반도체 경쟁": "AI 반도체 경쟁",
        }

        for raw_title, expected in cases.items():
            with self.subTest(raw_title=raw_title):
                result = sanitize_topic_title(raw_title)
                self.assertEqual(result, expected)
                self.assertFalse(has_forbidden_topic_title_pattern(result))

    def test_content_numbers_are_preserved(self):
        """기간 단위가 아닌 기업 수와 제품명 숫자는 삭제하지 않는다."""

        for title in (
            "AI 3대 기업과 GPT-5 경쟁",
            "1주택 정책과 3년물 국채",
            "유통기간 단축과 주간지 개편",
        ):
            with self.subTest(title=title):
                self.assertEqual(sanitize_topic_title(title), title)

    def test_empty_result_uses_keyword_then_representative_article_fallback(self):
        """정제 후 빈 제목은 keyword를 우선하고 없으면 대표 기사 제목을 사용한다."""

        self.assertEqual(
            sanitize_topic_title(
                "(월요일~일요일)",
                keywords=["AI 반도체 투자", "정책"],
                article_titles=["대표 기사"],
            ),
            "AI 반도체 투자",
        )
        self.assertEqual(
            sanitize_topic_title(
                "2026-07-12",
                keywords=["최근 3일"],
                article_titles=["2026.07.12 로봇 산업 재편"],
            ),
            "로봇 산업 재편",
        )

    def test_meaningless_period_remainder_uses_fallback(self):
        """기간 제거 후 `기록`·`요약`만 남으면 내용 keyword로 대체한다."""

        for title in ("3일차 기록", "72시간 요약"):
            with self.subTest(title=title):
                self.assertEqual(
                    sanitize_topic_title(title, keywords=["반도체 공급망 재편"]),
                    "반도체 공급망 재편",
                )

    def test_invalid_or_overlong_title_uses_deterministic_fallback(self):
        """구두점뿐인 값과 허용 길이 초과 값은 반복 호출에도 같은 fallback을 쓴다."""

        candidates = ["---", "가" * (MAX_TOPIC_TITLE_LENGTH + 1)]
        for candidate in candidates:
            with self.subTest(candidate_length=len(candidate)):
                first = sanitize_topic_title(candidate, keywords=["핵심 정책 변화"])
                second = sanitize_topic_title(candidate, keywords=["핵심 정책 변화"])
                self.assertEqual(first, "핵심 정책 변화")
                self.assertEqual(first, second)
                self.assertTrue(is_valid_topic_title(first))

    def test_validation_rejects_residual_period_pattern(self):
        """sanitizer를 거치지 않은 요일·기간 잔존 제목을 validation이 거부한다."""

        for title in ("AI 정책 월요일", "최근 3일 AI 정책", "2026-07-12 AI 정책"):
            with self.subTest(title=title):
                self.assertFalse(is_valid_topic_title(title))

    def test_read_time_row_sanitize_uses_keywords_without_mutating_input(self):
        """기존 DB row 제목은 keyword fallback으로 복사 정제하고 원본은 보존한다."""

        row = {
            "id": 31,
            "title_ko": "(월요일~일요일)",
            "keywords": ["반도체 공급망", "정책"],
        }

        result = with_sanitized_topic_title(row)

        self.assertEqual(result["title_ko"], "반도체 공급망")
        self.assertEqual(row["title_ko"], "(월요일~일요일)")
        self.assertTrue(topic_title_requires_fallback(row["title_ko"]))

    def test_read_time_row_sanitize_ignores_invalid_keyword_container(self):
        """기존 keywords metadata가 문자열이어도 문자 단위 fallback 없이 안전 처리한다."""

        result = with_sanitized_topic_title(
            {"title_ko": "2026-07-12", "keywords": "날짜 keyword"}
        )

        self.assertEqual(result["title_ko"], "주요 뉴스 이슈")


if __name__ == "__main__":
    unittest.main()
