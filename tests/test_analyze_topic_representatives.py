import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from scripts.analyze_topic_representatives import analyze, parse_args


class FakeEmbeddingProvider:
    model = "fake-fixture-v1"

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class AnalyzeTopicRepresentativesTests(unittest.TestCase):
    @patch("scripts.analyze_topic_representatives.load_dotenv")
    def test_parse_args_loads_dotenv_before_validation(self, load_dotenv):
        parse_args([])

        load_dotenv.assert_called_once_with()

    def test_defaults_match_candidate_policy(self):
        args = parse_args([])

        self.assertEqual(args.similarity_threshold, 0.70)
        self.assertEqual(args.max_candidates_per_topic, 3)
        self.assertFalse(args.include_singletons)
        self.assertTrue(args.dry_run)

    def test_parse_args_accepts_include_singletons(self):
        args = parse_args(["--include-singletons"])

        self.assertTrue(args.include_singletons)

    @patch("scripts.analyze_topic_representatives.load_dotenv")
    def test_provider_requires_explicit_limit_and_key(self, load_dotenv):
        with patch.dict(os.environ, {"OPENAI_EMBEDDING_API_KEY": "test"}, clear=False):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider"])

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider", "--max-articles", "10"])

    @patch("app.utils.article_embeddings.requests.post")
    def test_analyze_is_deterministic_and_read_only(self, post):
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
            similarity_threshold=0.7,
            max_candidates_per_topic=3,
            use_embedding_provider=False,
        )

        result = analyze(rows, args, provider=FakeEmbeddingProvider())

        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertEqual(result["analysis"]["topic_candidate_count"], 1)
        self.assertEqual(result["analysis"]["representative_candidate_count"], 2)
        self.assertEqual(result["analysis"]["embedding_provider"], "deterministic")
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
