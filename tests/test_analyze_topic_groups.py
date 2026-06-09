import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from scripts.analyze_topic_groups import analyze, get_articles, parse_args


class FakeEmbeddingProvider:
    model = "fake-fixture-v1"

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeMappingResult:
    def mappings(self):
        return self

    def all(self):
        return []


class FakeConnection:
    def __init__(self):
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query = query
        self.params = params
        return FakeMappingResult()


class AnalyzeTopicGroupsTests(unittest.TestCase):
    def test_get_articles_uses_bound_window_and_limit_parameters(self):
        connection = FakeConnection()
        args = SimpleNamespace(
            all=False,
            window_hours=72,
            time_basis="published",
            effective_max_articles=150,
        )

        get_articles(connection, args)

        self.assertIn(":window_hours", str(connection.query))
        self.assertIn("limit :max_articles", str(connection.query))
        self.assertEqual(
            connection.params,
            {"window_hours": 72, "max_articles": 150},
        )

    def test_get_articles_rejects_unsupported_time_basis(self):
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="unexpected",
            effective_max_articles=10,
        )

        with self.assertRaisesRegex(ValueError, "unsupported time_basis"):
            get_articles(FakeConnection(), args)

    def test_provider_requires_explicit_max_articles(self):
        with patch.dict(os.environ, {"OPENAI_EMBEDDING_API_KEY": "test"}, clear=False):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider"])

    def test_provider_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider", "--max-articles", "10"])

    def test_provider_rejects_excessive_max_articles(self):
        with patch.dict(os.environ, {"OPENAI_EMBEDDING_API_KEY": "test"}, clear=False):
            with self.assertRaises(SystemExit):
                parse_args(
                    ["--use-embedding-provider", "--max-articles", "201"]
                )

    @patch("app.utils.article_embeddings.requests.post")
    def test_analyze_uses_fake_embeddings_without_external_api(self, post):
        now = datetime.now(timezone.utc)
        rows = [
            {
                "id": 1,
                "source": "TechCrunch",
                "title": "AI startup update",
                "summary": "New artificial intelligence model",
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            },
            {
                "id": 2,
                "source": "BBC World",
                "title": "AI policy update",
                "summary": "Government discusses artificial intelligence",
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
            effective_max_articles=10,
            similarity_threshold=0.8,
            use_embedding_provider=False,
        )

        result = analyze(rows, args, provider=FakeEmbeddingProvider())

        self.assertTrue(result["analysis"]["dry_run"])
        self.assertFalse(result["analysis"]["embedding_provider_enabled"])
        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertEqual(result["analysis"]["article_count"], 2)
        self.assertEqual(result["analysis"]["topic_candidate_count"], 1)
        self.assertEqual(result["topic_candidates"][0]["article_count"], 2)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
