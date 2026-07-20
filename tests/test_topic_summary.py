"""Daily Topic Summary 입력, provider 응답과 prompt 안전 계약을 검증한다.

외부 HTTP는 mock으로 대체하고 DB 쓰기 없이 입력 제한, JSON 응답 검증, 원문 비노출,
날짜·기간을 제외한 제목 지시문을 확인한다.
"""

import json
import unittest
from unittest.mock import patch

from app.utils.topic_summary import (
    DeterministicSummaryProvider,
    OpenAISummaryProvider,
    build_topic_summary_inputs,
    parse_provider_response,
    render_topic_summary_report,
    summarize_topic_inputs,
)


def topic(topic_id, articles):
    """테스트용 Topic candidate와 기사 목록을 구성한다."""

    return {"topic_candidate_id": topic_id, "articles": articles}


def article(article_id, title, source):
    """Summary 입력에 필요한 최소 기사 dictionary를 반환한다."""

    return {"id": article_id, "title": title, "source": source}


class TopicSummaryTests(unittest.TestCase):
    """Daily Summary 생성 helper와 provider adapter의 회귀를 검증한다."""

    def test_build_inputs_uses_only_raw_text_and_applies_limits(self):
        inputs = build_topic_summary_inputs(
            [
                topic(
                    "topic-0001",
                    [article(1, "First", "A"), article(2, "Second", "B")],
                )
            ],
            {1: "abcdef", 2: ""},
            max_topics=1,
            max_articles_per_topic=2,
            max_raw_chars_per_article=3,
        )

        self.assertEqual(inputs[0]["status"], "ready")
        self.assertEqual(inputs[0]["article_count"], 1)
        self.assertEqual(inputs[0]["used_articles"][0]["raw_text"], "abc")
        self.assertEqual(inputs[0]["used_articles"][0]["raw_text_length"], 6)

    def test_topic_without_raw_text_is_insufficient(self):
        inputs = build_topic_summary_inputs(
            [topic("topic-0001", [article(1, "First", "A")])],
            {},
            max_topics=1,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
        )

        summaries = summarize_topic_inputs(inputs, DeterministicSummaryProvider())

        self.assertEqual(summaries[0]["status"], "insufficient_raw_text")
        self.assertIsNone(summaries[0]["summary_ko"])

    def test_ready_topic_outside_initial_window_is_prioritized(self):
        inputs = build_topic_summary_inputs(
            [
                topic("topic-0001", [article(1, "First", "A")]),
                topic("topic-0002", [article(2, "Second", "B")]),
                topic("topic-0003", [article(3, "Ready", "C")]),
            ],
            {3: "available raw text"},
            max_topics=2,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
        )

        self.assertEqual(inputs[0]["topic_candidate_id"], "topic-0003")
        self.assertEqual(inputs[0]["status"], "ready")
        self.assertEqual(inputs[1]["status"], "insufficient_raw_text")

    def test_ready_topics_sort_by_article_and_source_count_before_limit(self):
        inputs = build_topic_summary_inputs(
            [
                topic("topic-0001", [article(1, "One", "A")]),
                topic(
                    "topic-0002",
                    [article(2, "Two", "A"), article(3, "Three", "B")],
                ),
                topic("topic-0003", [article(4, "Four", "C")]),
            ],
            {1: "raw 1", 2: "raw 2", 3: "raw 3", 4: "raw 4"},
            max_topics=2,
            max_articles_per_topic=2,
            max_raw_chars_per_article=100,
        )

        self.assertEqual(
            [topic_input["topic_candidate_id"] for topic_input in inputs],
            ["topic-0002", "topic-0001"],
        )

    def test_deterministic_summary_contains_required_fields(self):
        inputs = build_topic_summary_inputs(
            [topic("topic-0001", [article(1, "AI 정책 변화", "Source")])],
            {1: "정부가 인공지능 정책 변경을 발표했다."},
            max_topics=1,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
        )

        summary = summarize_topic_inputs(inputs, DeterministicSummaryProvider())[0]

        for field in (
            "title_ko",
            "summary_ko",
            "key_points",
            "keywords",
            "confidence",
            "source_count",
            "article_count",
            "used_articles",
            "provider",
            "model",
        ):
            self.assertIn(field, summary)
        self.assertEqual(summary["provider"], "deterministic")
        self.assertNotIn("raw_text", summary["used_articles"][0])
        self.assertIn("AI 정책 변화", summary["key_points"][0])

    def test_public_summary_and_report_do_not_expose_raw_text_content(self):
        raw_text = "PRIVATE_RAW_TEXT_SHOULD_NOT_APPEAR"
        inputs = build_topic_summary_inputs(
            [topic("topic-0001", [article(1, "Public title", "Source")])],
            {1: raw_text},
            max_topics=1,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
        )
        summary = summarize_topic_inputs(inputs, DeterministicSummaryProvider())[0]
        result = {
            "analysis": {
                "provider": "deterministic",
                "model": "deterministic-summary-v1",
                "topic_count": 1,
                "summarized_topic_count": 1,
                "insufficient_raw_text_topic_count": 0,
            },
            "topic_summaries": [summary],
        }

        self.assertNotIn(raw_text, json.dumps(result))
        self.assertNotIn(raw_text, render_topic_summary_report(result))
        self.assertNotIn("raw_text", summary["used_articles"][0])

    def test_parse_provider_response_supports_responses_output(self):
        parsed = parse_provider_response(
            {
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    '{"title_ko":"제목","summary_ko":"요약",'
                                    '"key_points":["핵심"],"keywords":["키워드"],'
                                    '"confidence":0.8}'
                                ),
                            }
                        ]
                    }
                ]
            }
        )

        self.assertEqual(parsed["title_ko"], "제목")
        self.assertEqual(parsed["confidence"], 0.8)

    def test_parse_provider_response_rejects_non_object_json(self):
        for output_text in ('["summary"]', '"summary"', "null"):
            with self.subTest(output_text=output_text):
                with self.assertRaises(ValueError):
                    parse_provider_response({"output_text": output_text})

    def test_parse_provider_response_rejects_non_finite_confidence(self):
        for confidence in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    parse_provider_response(
                        {
                            "output_text": (
                                '{"title_ko":"제목","summary_ko":"요약",'
                                '"key_points":[],"keywords":[],'
                                f'"confidence":{confidence}' + "}"
                            )
                        }
                    )

    def test_parse_provider_response_rejects_out_of_range_confidence(self):
        for confidence in (-0.1, 1.1):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    parse_provider_response(
                        {
                            "output_text": json.dumps(
                                {
                                    "title_ko": "제목",
                                    "summary_ko": "요약",
                                    "key_points": [],
                                    "keywords": [],
                                    "confidence": confidence,
                                }
                            )
                        }
                    )

    def test_parse_provider_response_rejects_non_string_list_item(self):
        with self.assertRaises(ValueError):
            parse_provider_response(
                {
                    "output_text": json.dumps(
                        {
                            "title_ko": "제목",
                            "summary_ko": "요약",
                            "key_points": ["핵심", 1],
                            "keywords": ["키워드"],
                            "confidence": 0.8,
                        }
                    )
                }
            )

    def test_parse_provider_response_rejects_non_string_text_field(self):
        with self.assertRaises(ValueError):
            parse_provider_response(
                {
                    "output_text": json.dumps(
                        {
                            "title_ko": ["제목"],
                            "summary_ko": "요약",
                            "key_points": [],
                            "keywords": [],
                            "confidence": 0.8,
                        }
                    )
                }
            )

    @patch("app.utils.topic_summary.requests.post")
    def test_openai_provider_parses_mock_response(self, post):
        """OpenAI adapter가 제목 제외 계약을 보내고 mock JSON 응답을 parse한다."""

        post.return_value.json.return_value = {
            "output_text": (
                '{"title_ko":"제목","summary_ko":"요약",'
                '"key_points":[],"keywords":[],"confidence":0.7}'
            )
        }

        result = OpenAISummaryProvider(api_key="test", model="gpt-5-mini").summarize(
            {"used_articles": []}
        )

        self.assertEqual(result["summary_ko"], "요약")
        post.assert_called_once()
        prompt = post.call_args.kwargs["json"]["input"]
        self.assertIn(
            "제목에는 날짜, 연도, 월, 일, 요일, 기간과 시간 범위를 포함하지 않는다.",
            prompt,
        )
        self.assertIn("제목은 뉴스 내용과 핵심 주제만 표현한다.", prompt)

    def test_report_contains_safety_and_used_article_fields(self):
        summary = {
            "topic_candidate_id": "topic-0001",
            "status": "ready",
            "title_ko": "제목",
            "summary_ko": "요약",
            "key_points": ["핵심"],
            "keywords": ["키워드"],
            "confidence": 0.7,
            "source_count": 1,
            "article_count": 1,
            "used_articles": [
                {
                    "article_id": 1,
                    "title": "Article",
                    "source": "Source",
                    "raw_text_length": 100,
                    "raw_text": "PRIVATE_REPORT_RAW_TEXT",
                }
            ],
            "provider": "deterministic",
            "model": "deterministic-summary-v1",
        }
        report = render_topic_summary_report(
            {
                "analysis": {
                    "provider": "deterministic",
                    "model": "deterministic-summary-v1",
                    "topic_count": 1,
                    "summarized_topic_count": 1,
                    "insufficient_raw_text_topic_count": 0,
                },
                "topic_summaries": [summary],
            }
        )

        self.assertIn("Raw Text Length", report)
        self.assertIn("DB write performed: `false`", report)
        self.assertIn("Raw extraction performed: `false`", report)
        self.assertNotIn("PRIVATE_REPORT_RAW_TEXT", report)


if __name__ == "__main__":
    unittest.main()
