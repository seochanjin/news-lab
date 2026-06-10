import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.generate_topic_summary_report import generate, parse_args


class GenerateTopicSummaryReportTests(unittest.TestCase):
    def test_defaults_are_deterministic_and_bounded(self):
        with patch.dict(os.environ, {}, clear=True):
            args = parse_args([])

        self.assertFalse(args.use_summary_provider)
        self.assertEqual(args.summary_model, "gpt-5-nano")
        self.assertEqual(args.max_topics, 3)
        self.assertEqual(args.max_articles_per_topic, 2)

    @patch.dict(os.environ, {}, clear=True)
    def test_provider_requires_api_key(self):
        with self.assertRaises(SystemExit):
            parse_args(["--use-summary-provider"])

    def test_provider_models_support_nano_and_mini(self):
        with patch.dict(os.environ, {"OPENAI_SUMMARY_MODEL": "gpt-5-mini"}):
            self.assertEqual(parse_args([]).summary_model, "gpt-5-mini")
        with patch.dict(
            os.environ,
            {"OPENAI_SUMMARY_MODEL": "other", "OPENAI_SUMMARY_API_KEY": "test"},
        ):
            with self.assertRaises(SystemExit):
                parse_args(["--use-summary-provider"])

    def test_limits_are_validated(self):
        with self.assertRaises(SystemExit):
            parse_args(["--max-topics", "11"])
        with self.assertRaises(SystemExit):
            parse_args(["--max-articles-per-topic", "4"])
        with self.assertRaises(SystemExit):
            parse_args(["--max-raw-chars-per-article", "5001"])

    @patch("app.utils.topic_summary.requests.post")
    def test_default_generation_does_not_call_provider(self, post):
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": 1,
                "source": "Source",
                "title": "AI 정책 변화",
                "summary": "인공지능 정책 관련 기사",
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            }
        ]
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="published",
            similarity_threshold=0.72,
            max_topics=1,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
            use_summary_provider=False,
        )

        result = generate(rows, {1: "원문 내용"}, args)

        self.assertEqual(result["analysis"]["provider"], "deterministic")
        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertFalse(result["analysis"]["raw_extraction_performed"])
        post.assert_not_called()

    def test_generate_uses_injected_mock_provider(self):
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": 1,
                "source": "Source",
                "title": "AI 정책 변화",
                "summary": "인공지능 정책 관련 기사",
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            }
        ]
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="published",
            similarity_threshold=0.72,
            max_topics=1,
            max_articles_per_topic=1,
            max_raw_chars_per_article=100,
            use_summary_provider=True,
        )
        provider = Mock(provider="mock", model="mock-v1")
        provider.summarize.return_value = {
            "title_ko": "제목",
            "summary_ko": "요약",
            "key_points": ["핵심"],
            "keywords": ["키워드"],
            "confidence": 0.9,
        }

        result = generate(rows, {1: "원문 내용"}, args, summary_provider=provider)

        provider.summarize.assert_called_once()
        self.assertEqual(result["topic_summaries"][0]["provider"], "mock")


if __name__ == "__main__":
    unittest.main()
