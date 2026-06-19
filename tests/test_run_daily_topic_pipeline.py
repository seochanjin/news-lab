import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.utils.article_embedding_storage import EmbeddingResult
from app.utils.topic_summary import DeterministicSummaryProvider
from scripts.run_daily_topic_pipeline import (
    _topic_selection_key,
    acquire_pipeline_embeddings,
    build_pipeline,
    parse_args,
    render_report,
)


class FakeEmbeddingProvider:
    model = "fake-embedding-v1"

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


class SequenceEmbeddingProvider:
    model = "fake-sequence-embedding-v1"

    def __init__(self, embeddings):
        self.embeddings = embeddings

    def embed(self, texts):
        return self.embeddings


def rows():
    now = datetime.now(timezone.utc)
    return [
        {
            "id": article_id,
            "source": source,
            "title": f"AI topic article {article_id}",
            "summary": "Detailed artificial intelligence policy update.",
            "url": f"https://example.com/{article_id}",
            "source_category": "tech",
            "published_at": now,
            "created_at": now,
            "analysis_time": now,
        }
        for article_id, source in ((1, "A"), (2, "B"))
    ]


def args(
    *,
    execute=False,
    max_topics=5,
    max_reference_topics=10,
    use_embedding_provider=False,
):
    return SimpleNamespace(
        execute=execute,
        window_hours=24,
        time_basis="published",
        max_articles=100,
        effective_max_articles=100,
        similarity_threshold=0.78,
        max_topics=max_topics,
        max_reference_topics=max_reference_topics,
        max_articles_per_topic=3,
        max_raw_chars_per_article=3000,
        extraction_limit=5,
        use_embedding_provider=use_embedding_provider,
        use_summary_provider=False,
        summary_model="gpt-5-nano",
    )


class RunDailyTopicPipelineTests(unittest.TestCase):
    def test_defaults_to_safe_dry_run(self):
        parsed = parse_args([])

        self.assertEqual(parsed.window_hours, 24)
        self.assertFalse(parsed.execute)
        self.assertFalse(parsed.use_embedding_provider)
        self.assertFalse(parsed.use_summary_provider)
        self.assertEqual(parsed.summary_model, "gpt-5-nano")
        self.assertEqual(parsed.max_reference_topics, 10)
        self.assertEqual(parse_args(["--max-reference-topics", "0"]).max_reference_topics, 0)
        with self.assertRaises(SystemExit):
            parse_args(["--max-reference-topics", "11"])

    @patch("scripts.run_daily_topic_pipeline.load_dotenv")
    def test_provider_flags_require_keys(self, load_dotenv):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                parse_args(["--use-embedding-provider"])
            with self.assertRaises(SystemExit):
                parse_args(["--use-summary-provider"])

    @patch("scripts.run_daily_topic_pipeline.load_dotenv")
    def test_embedding_provider_supports_bounded_daily_article_limit(self, load_dotenv):
        with patch.dict(
            os.environ,
            {"OPENAI_EMBEDDING_API_KEY": "test"},
            clear=True,
        ):
            self.assertEqual(
                parse_args(
                    ["--use-embedding-provider", "--max-articles", "300"]
                ).max_articles,
                300,
            )
            with self.assertRaises(SystemExit):
                parse_args(
                    ["--use-embedding-provider", "--max-articles", "301"]
                )

    def test_topic_order_prioritizes_article_count_then_source_count(self):
        now = datetime.now(timezone.utc)
        topics = [
            {
                "topic_candidate_id": "topic-smaller",
                "article_count": 2,
                "source_count": 2,
                "articles": [],
            },
            {
                "topic_candidate_id": "topic-fewer-sources",
                "article_count": 3,
                "source_count": 1,
                "articles": [{"published_at": now}],
            },
            {
                "topic_candidate_id": "topic-more-sources",
                "article_count": 3,
                "source_count": 2,
                "articles": [{"published_at": now}],
            },
        ]

        ordered = sorted(topics, key=_topic_selection_key)

        self.assertEqual(
            [topic["topic_candidate_id"] for topic in ordered],
            ["topic-more-sources", "topic-fewer-sources", "topic-smaller"],
        )

    def test_dry_run_builds_memory_only_plan_without_execution(self):
        result = build_pipeline(
            rows(),
            {},
            {1: "raw text one", 2: "raw text two"},
            args(),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
        )

        self.assertTrue(result["analysis"]["dry_run"])
        self.assertFalse(result["analysis"]["raw_extraction_performed"])
        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertEqual(result["analysis"]["topic_candidate_count"], 1)
        self.assertEqual(result["analysis"]["selected_article_ids"], [1, 2])
        saved_articles = result["save_plan"]["topics"][0]["articles"]
        self.assertEqual(saved_articles[0]["similarity_score"], 1.0)
        self.assertEqual(saved_articles[0]["role"], "representative")
        self.assertEqual(saved_articles[1]["role"], "supporting")

    def test_execute_uses_injected_extraction_loader_and_save(self):
        extraction_executor = Mock(
            return_value=[
                {"article_id": 1, "status": "success"},
                {"article_id": 2, "status": "failed"},
            ]
        )
        raw_text_loader = Mock(return_value={1: "new raw text"})

        def save_executor(plan):
            plan["analysis"]["db_write_performed"] = True
            return plan

        result = build_pipeline(
            rows(),
            {},
            {},
            args(execute=True),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
            save_executor=save_executor,
        )

        extraction_executor.assert_called_once_with([1, 2], limit=5)
        raw_text_loader.assert_called_once()
        self.assertTrue(result["analysis"]["raw_extraction_performed"])
        self.assertEqual(result["analysis"]["raw_extraction_success_count"], 1)
        self.assertEqual(result["analysis"]["raw_extraction_failed_count"], 1)
        self.assertTrue(result["analysis"]["db_write_performed"])
        self.assertTrue(result["save_plan"]["analysis"]["raw_extraction_performed"])

    def test_reference_topics_do_not_enter_extraction_summary_or_save(self):
        input_rows = rows() + [
            {
                **rows()[0],
                "id": article_id,
                "source": source,
                "title": f"Other topic article {article_id}",
                "url": f"https://example.com/{article_id}",
            }
            for article_id, source in ((3, "C"), (4, "D"), (5, "E"))
        ]
        extraction_executor = Mock(return_value=[])
        raw_text_loader = Mock(return_value={3: "three", 4: "four", 5: "five"})
        save_executor = Mock(side_effect=lambda plan: plan)

        result = build_pipeline(
            input_rows,
            {},
            {article_id: f"raw text {article_id}" for article_id in range(1, 6)},
            args(execute=True, max_topics=1, max_reference_topics=1),
            embedding_provider=SequenceEmbeddingProvider(
                [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]
            ),
            summary_provider=DeterministicSummaryProvider(),
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
            save_executor=save_executor,
        )

        self.assertEqual(result["analysis"]["selected_topic_count"], 1)
        self.assertEqual(result["analysis"]["reference_topic_count"], 1)
        self.assertEqual(result["topics"][0]["article_count"], 3)
        self.assertEqual(result["reference_topics"][0]["article_count"], 2)
        extraction_executor.assert_called_once_with([3, 4, 5], limit=5)
        raw_text_loader.assert_called_once_with([3, 4, 5])
        self.assertEqual(len(result["topic_summaries"]), 1)
        self.assertEqual(len(result["save_plan"]["topics"]), 1)
        self.assertNotEqual(
            result["topic_summaries"][0]["topic_candidate_id"],
            result["reference_topics"][0]["topic_candidate_id"],
        )
        report = render_report(result)
        self.assertIn("#### Reference Articles", report)
        self.assertIn("AI topic article 1", report)
        self.assertNotIn("raw text 1", report)

    def test_report_contains_required_pipeline_fields(self):
        result = build_pipeline(
            rows(),
            {},
            {1: "raw text one", 2: "raw text two"},
            args(),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
        )

        report = render_report(result)

        self.assertIn("Window hours: 24", report)
        self.assertIn("Candidate articles: 2", report)
        self.assertIn("Embedding created/updated/reused/failed: 2 / 0 / 0 / 0", report)
        self.assertIn("Clustering input count: 2", report)
        self.assertIn("Pipeline elapsed seconds", report)
        self.assertIn("Selected article IDs", report)
        self.assertIn("Similarity scores", report)
        self.assertIn("Raw extraction success/failure", report)
        self.assertIn("DB write performed: `false`", report)
        self.assertIn("Topic ordering: `article_count desc, source_count desc", report)
        self.assertIn("#### Selected Articles", report)
        self.assertIn("representative", report)
        self.assertIn("https://example.com/1", report)
        self.assertIn("#### Generated Summary", report)
        self.assertIn("## Reference Candidates", report)
        self.assertNotIn("raw text one", report)

    def test_stored_embeddings_preserve_article_vector_order_and_stats(self):
        input_rows = rows() + [
            {
                **rows()[0],
                "id": 3,
                "source": "C",
                "title": "AI topic article 3",
                "url": "https://example.com/3",
            },
            {
                **rows()[0],
                "id": 4,
                "source": "D",
                "title": "AI topic article 4",
                "url": "https://example.com/4",
            }
        ]
        provider = FakeEmbeddingProvider()
        results = {
            1: EmbeddingResult(1, "reused", "hash-1", (1.0, 0.0)),
            2: RuntimeError("provider unavailable"),
            3: EmbeddingResult(3, "created", "hash-3", (1.0, 0.0)),
            4: EmbeddingResult(4, "updated", "hash-4", (1.0, 0.0)),
        }

        def acquire(article):
            result = results[article["id"]]
            if isinstance(result, Exception):
                raise result
            return result

        result = build_pipeline(
            input_rows,
            {},
            {1: "one", 3: "three"},
            args(use_embedding_provider=True),
            embedding_provider=provider,
            embedding_acquirer=acquire,
            summary_provider=DeterministicSummaryProvider(),
        )

        self.assertEqual(provider.calls, [])
        self.assertEqual(result["analysis"]["candidate_articles"], 4)
        self.assertEqual(result["analysis"]["embedding_created"], 1)
        self.assertEqual(result["analysis"]["embedding_updated"], 1)
        self.assertEqual(result["analysis"]["embedding_reused"], 1)
        self.assertEqual(result["analysis"]["embedding_failed"], 1)
        self.assertEqual(result["analysis"]["clustering_input_count"], 3)
        self.assertEqual(
            [article["article_id"] for article in result["topics"][0]["articles"]],
            [1, 3, 4],
        )
        self.assertEqual(
            result["embedding_failures"],
            [{"article_id": 2, "error": "RuntimeError: provider unavailable"}],
        )

    def test_dimension_failure_excludes_article_and_skips_clustering_below_minimum(self):
        save_executor = Mock()

        def acquire(article):
            if article["id"] == 1:
                return EmbeddingResult(1, "reused", "hash-1", (1.0, 0.0))
            raise ValueError("stored embedding dimension mismatch")

        result = build_pipeline(
            rows(),
            {},
            {},
            args(execute=True, use_embedding_provider=True),
            embedding_provider=FakeEmbeddingProvider(),
            embedding_acquirer=acquire,
            summary_provider=DeterministicSummaryProvider(),
            save_executor=save_executor,
        )

        self.assertEqual(result["analysis"]["embedding_reused"], 1)
        self.assertEqual(result["analysis"]["embedding_failed"], 1)
        self.assertEqual(result["analysis"]["clustering_input_count"], 1)
        self.assertEqual(result["analysis"]["topic_count"], 0)
        self.assertEqual(result["topics"], [])
        self.assertEqual(result["topic_summaries"], [])
        self.assertFalse(result["analysis"]["db_write_performed"])
        save_executor.assert_not_called()

    def test_invalid_acquirer_result_type_fails_fast(self):
        with self.assertRaisesRegex(
            TypeError,
            "embedding acquirer returned an invalid result",
        ):
            acquire_pipeline_embeddings(
                [{"id": 1}],
                FakeEmbeddingProvider(),
                embedding_acquirer=lambda article: None,
            )

    def test_invalid_acquirer_status_fails_fast(self):
        with self.assertRaisesRegex(ValueError, "unsupported embedding status"):
            acquire_pipeline_embeddings(
                [{"id": 1}],
                FakeEmbeddingProvider(),
                embedding_acquirer=lambda article: EmbeddingResult(
                    article["id"],
                    "failed",
                    "hash-1",
                    (1.0, 0.0),
                ),
            )

    def test_missing_acquirer_vector_fails_fast(self):
        with self.assertRaisesRegex(
            ValueError,
            "embedding result does not include a vector",
        ):
            acquire_pipeline_embeddings(
                [{"id": 1}],
                FakeEmbeddingProvider(),
                embedding_acquirer=lambda article: EmbeddingResult(
                    article["id"],
                    "reused",
                    "hash-1",
                    None,
                ),
            )


if __name__ == "__main__":
    unittest.main()
