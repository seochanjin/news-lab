import unittest
from unittest.mock import patch

from app.utils.article_embeddings import (
    DeterministicHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    build_embedding_input,
)


class ArticleEmbeddingTests(unittest.TestCase):
    def test_build_embedding_input_includes_expected_fields(self):
        result = build_embedding_input(
            title="AI  Startup",
            summary="New model",
            source="Tech Source",
            source_category="tech",
            rule_category="ai",
        )

        self.assertIn("title: ai startup", result)
        self.assertIn("summary: new model", result)
        self.assertIn("source: tech source", result)
        self.assertIn("source_category: tech", result)
        self.assertIn("rule_category: ai", result)

    def test_hash_embeddings_are_deterministic(self):
        provider = DeterministicHashEmbeddingProvider(dimensions=16)

        first = provider.embed(["same input"])[0]
        second = provider.embed(["same input"])[0]

        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)

    @patch("app.utils.article_embeddings.requests.post")
    def test_openai_provider_orders_response_embeddings(self, post):
        post.return_value.json.return_value = {
            "data": [
                {"index": 1, "embedding": [0.0, 1.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ]
        }

        result = OpenAIEmbeddingProvider(api_key="test-key").embed(["a", "b"])

        self.assertEqual(result, [[1.0, 0.0], [0.0, 1.0]])
        post.assert_called_once()

    @patch("app.utils.article_embeddings.requests.post")
    def test_openai_provider_skips_request_for_empty_input(self, post):
        result = OpenAIEmbeddingProvider(api_key="test-key").embed([])

        self.assertEqual(result, [])
        post.assert_not_called()

    @patch("app.utils.article_embeddings.requests.post")
    def test_openai_provider_rejects_missing_response_embedding(self, post):
        post.return_value.json.return_value = {
            "data": [{"index": 0, "embedding": [1.0, 0.0]}]
        }

        with self.assertRaisesRegex(RuntimeError, "response count mismatch"):
            OpenAIEmbeddingProvider(api_key="test-key").embed(["a", "b"])

    @patch("app.utils.article_embeddings.requests.post")
    def test_openai_provider_rejects_extra_response_embedding(self, post):
        post.return_value.json.return_value = {
            "data": [
                {"index": 0, "embedding": [1.0, 0.0]},
                {"index": 1, "embedding": [0.0, 1.0]},
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "response count mismatch"):
            OpenAIEmbeddingProvider(api_key="test-key").embed(["a"])


if __name__ == "__main__":
    unittest.main()
