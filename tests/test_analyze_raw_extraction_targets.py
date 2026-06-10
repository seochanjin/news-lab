import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from scripts.analyze_raw_extraction_targets import analyze, parse_args


class FakeEmbeddingProvider:
    model = "fake-fixture-v1"

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class AnalyzeRawExtractionTargetsTests(unittest.TestCase):
    def test_defaults_match_target_policy(self):
        args = parse_args([])

        self.assertEqual(args.similarity_threshold, 0.72)
        self.assertEqual(args.max_candidates_per_topic, 3)
        self.assertEqual(args.max_targets_per_topic, 1)
        self.assertTrue(args.dry_run)

    def test_max_targets_per_topic_accepts_only_one_to_three(self):
        self.assertEqual(parse_args(["--max-targets-per-topic", "3"]).max_targets_per_topic, 3)
        with self.assertRaises(SystemExit):
            parse_args(["--max-targets-per-topic", "0"])
        with self.assertRaises(SystemExit):
            parse_args(["--max-targets-per-topic", "4"])

    @patch("scripts.analyze_raw_extraction_targets.load_dotenv")
    def test_provider_requires_explicit_limit_and_key(self, load_dotenv):
        with patch.dict(os.environ, {"OPENAI_EMBEDDING_API_KEY": "test"}, clear=False):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider"])

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider", "--max-articles", "10"])

    @patch("app.utils.article_embeddings.requests.post")
    def test_analyze_is_deterministic_read_only_and_does_not_extract(self, post):
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": 1,
                "source": "TechCrunch",
                "title": "AI startup update",
                "summary": "A detailed artificial intelligence model update.",
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            },
            {
                "id": 2,
                "source": "BBC World",
                "title": "AI policy update",
                "summary": "Government discusses artificial intelligence policy.",
                "source_category": "world",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            },
        ]
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="published",
            effective_max_articles=100,
            similarity_threshold=0.72,
            max_candidates_per_topic=3,
            max_targets_per_topic=1,
            use_embedding_provider=False,
        )

        result = analyze(rows, {}, args, provider=FakeEmbeddingProvider())

        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertFalse(result["analysis"]["raw_extraction_performed"])
        self.assertEqual(result["analysis"]["extraction_target_count"], 1)
        self.assertEqual(result["analysis"]["embedding_provider"], "deterministic")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
