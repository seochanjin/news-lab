"""Daily Topic Pipeline의 stage 조립, 실행 조건과 후속 cache hook을 검증한다.

테스트는 fake provider, fake DB connection, mock executor를 사용해 실제 DB,
Redis, OpenAI API, production workload에 접근하지 않는다. Execute 모드의 저장
성공 이후 Home cache prewarm이 commit 경계 뒤에서 동작하는지도 local mock으로
회귀 검증한다.
"""

import os
import unittest
from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.home_topics_cache import HomeTopicsCache
from app.utils.article_embedding_storage import EmbeddingResult
from app.utils.topic_summary import DeterministicSummaryProvider
from scripts.run_daily_topic_pipeline import (
    _prewarm_home_topics_cache_after_success,
    _topic_selection_key,
    acquire_pipeline_embeddings,
    build_pipeline,
    parse_args,
    render_report,
    resolve_pipeline_context,
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


class FailFirstSummaryProvider(DeterministicSummaryProvider):
    """첫 summary 생성만 실패시켜 topic 단위 실패 격리를 재현한다."""

    def __init__(self):
        """호출 횟수를 초기화해 첫 호출 실패를 제어한다."""

        self.call_count = 0

    def summarize(self, topic_input):
        """첫 호출에서는 예외를 내고 이후에는 deterministic summary를 반환한다."""

        self.call_count += 1
        if self.call_count == 1:
            raise RuntimeError("summary provider unavailable")
        return super().summarize(topic_input)


class FakeRedisSetClient:
    """Pipeline prewarm 테스트에서 Redis SETEX 성공과 실패만 재현한다."""

    def __init__(self, *, set_error=None):
        """SETEX 호출 기록과 선택적 오류를 초기화한다."""

        self.set_error = set_error
        self.set_calls = []

    def setex(self, key, ttl_seconds, value):
        """SETEX 호출을 기록하거나 지정된 Redis 계층 오류를 발생시킨다."""

        if self.set_error:
            raise self.set_error
        self.set_calls.append((key, ttl_seconds, value))


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

    def test_pipeline_date_uses_asia_seoul_date_at_utc_boundary(self):
        context = resolve_pipeline_context(
            started_at_utc=datetime(2026, 6, 20, 19, 0, tzinfo=timezone.utc)
        )

        result = build_pipeline(
            rows(),
            {},
            {1: "raw text one", 2: "raw text two"},
            args(),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
            pipeline_context=context,
        )

        self.assertEqual(context.pipeline_date, date(2026, 6, 21))
        self.assertEqual(context.business_timezone, "Asia/Seoul")
        self.assertEqual(result["analysis"]["pipeline_date"], date(2026, 6, 21))
        self.assertEqual(result["analysis"]["pipeline_date_source"], "started_at_local")
        self.assertEqual(
            {topic["topic_date"] for topic in result["save_plan"]["topics"]},
            {date(2026, 6, 21)},
        )

    def test_pipeline_context_rejects_naive_started_at_before_save(self):
        save_executor = Mock()

        with self.assertRaisesRegex(
            ValueError,
            "started_at_utc must be timezone-aware",
        ):
            context = resolve_pipeline_context(
                started_at_utc=datetime(2026, 6, 21, 4, 0)
            )
            build_pipeline(
                rows(),
                {},
                {1: "raw text one", 2: "raw text two"},
                args(execute=True),
                embedding_provider=FakeEmbeddingProvider(),
                summary_provider=DeterministicSummaryProvider(),
                save_executor=save_executor,
                pipeline_context=context,
            )

        save_executor.assert_not_called()

    def test_pipeline_context_normalizes_timezone_aware_offset_to_utc(self):
        seoul_timezone = timezone(timedelta(hours=9))

        context = resolve_pipeline_context(
            started_at_utc=datetime(
                2026,
                6,
                21,
                4,
                0,
                tzinfo=seoul_timezone,
            )
        )

        self.assertEqual(
            context.started_at_utc,
            datetime(2026, 6, 20, 19, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(context.started_at_local.utcoffset(), timedelta(hours=9))
        self.assertEqual(context.pipeline_date, date(2026, 6, 21))

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
        self.assertEqual(result["analysis"]["raw_extracted_count"], 1)
        self.assertEqual(result["analysis"]["raw_failed_count"], 1)
        self.assertEqual(result["analysis"]["raw_missing_count"], 1)
        self.assertTrue(result["analysis"]["db_write_performed"])
        self.assertTrue(result["save_plan"]["analysis"]["raw_extraction_performed"])

    def test_raw_stage_reuses_existing_text_and_extracts_only_missing_selected_article(self):
        extraction_executor = Mock(
            return_value=[{"article_id": 2, "status": "success"}]
        )
        raw_text_loader = Mock(
            return_value={1: "stored raw text", 2: "new raw text"}
        )

        result = build_pipeline(
            rows(),
            {
                1: {
                    "has_raw_text": True,
                    "extraction_status": "success",
                },
                2: {
                    "has_raw_text": False,
                    "extraction_status": "pending",
                },
            },
            {},
            args(execute=True),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
            extraction_executor=extraction_executor,
            raw_text_loader=raw_text_loader,
            save_executor=lambda plan: plan,
        )

        extraction_executor.assert_called_once_with([2], limit=5)
        raw_text_loader.assert_called_once_with([1, 2])
        self.assertEqual(result["analysis"]["selected_article_count"], 2)
        self.assertEqual(result["analysis"]["raw_reused_count"], 1)
        self.assertEqual(result["analysis"]["raw_extracted_count"], 1)
        self.assertEqual(result["analysis"]["raw_failed_count"], 0)
        self.assertEqual(result["analysis"]["raw_missing_count"], 0)

    def test_dry_run_loads_raw_text_only_after_selected_articles_are_known(self):
        raw_text_loader = Mock(return_value={1: "one", 2: "two"})

        result = build_pipeline(
            rows(),
            {},
            {},
            args(),
            embedding_provider=FakeEmbeddingProvider(),
            summary_provider=DeterministicSummaryProvider(),
            raw_text_loader=raw_text_loader,
        )

        raw_text_loader.assert_called_once_with([1, 2])
        self.assertEqual(result["analysis"]["raw_reused_count"], 2)
        self.assertEqual(result["analysis"]["raw_extracted_count"], 0)

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

    def test_summary_failure_is_isolated_to_one_topic(self):
        input_rows = rows() + [
            {
                **rows()[0],
                "id": article_id,
                "source": source,
                "title": f"Other topic article {article_id}",
                "url": f"https://example.com/{article_id}",
            }
            for article_id, source in ((3, "C"), (4, "D"))
        ]

        result = build_pipeline(
            input_rows,
            {},
            {
                1: "one",
                2: "two",
                3: "three",
                4: "four",
            },
            args(max_topics=2),
            embedding_provider=SequenceEmbeddingProvider(
                [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]
            ),
            summary_provider=FailFirstSummaryProvider(),
        )

        self.assertEqual(result["analysis"]["selected_topic_count"], 2)
        self.assertEqual(result["analysis"]["generated_topic_count"], 1)
        self.assertEqual(result["analysis"]["failed_topic_count"], 1)
        self.assertEqual(len(result["topic_summaries"]), 1)
        self.assertEqual(len(result["topic_failures"]), 1)
        self.assertEqual(len(result["save_plan"]["topics"]), 1)

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

    def test_execute_db_write_success_prewarm_reads_home_payload(self):
        """DB write가 완료된 execute 결과에서 Home payload를 조회해 prewarm 저장한다."""

        row = {
            "id": 1,
            "topic_date": date(2026, 7, 14),
            "title_ko": "제목",
            "summary_ko": "요약",
            "keywords": ["키워드"],
            "source_count": 2,
            "article_count": 3,
        }
        query_result = Mock()
        query_result.mappings.return_value.all.return_value = [row]
        connection = Mock()
        connection.execute.return_value = query_result
        engine = SimpleNamespace(connect=lambda: nullcontext(connection))
        cache = Mock()

        _prewarm_home_topics_cache_after_success(
            engine,
            {"analysis": {"db_write_performed": True}},
            args(execute=True),
            cache=cache,
        )

        cache.set.assert_called_once()
        payload = cache.set.call_args.args[0]
        self.assertEqual(cache.set.call_args.kwargs["operation"], "prewarm")
        self.assertEqual(payload["items"], [row])
        self.assertEqual(payload["topic_date"], date(2026, 7, 14))
        self.assertIn("generated_at", payload)
        self.assertEqual(connection.execute.call_args.args[1], {"limit": 10})

    def test_dry_run_and_no_db_write_skip_home_cache_prewarm(self):
        """Dry-run 또는 실제 DB 저장이 없던 성공 결과에서는 prewarm을 호출하지 않는다."""

        engine = Mock()
        cache = Mock()

        _prewarm_home_topics_cache_after_success(
            engine,
            {"analysis": {"db_write_performed": True}},
            args(execute=False),
            cache=cache,
        )
        _prewarm_home_topics_cache_after_success(
            engine,
            {"analysis": {"db_write_performed": False}},
            args(execute=True),
            cache=cache,
        )

        engine.connect.assert_not_called()
        cache.set.assert_not_called()

    def test_home_cache_prewarm_failure_does_not_fail_pipeline(self):
        """Prewarm 조회나 저장 준비 실패가 pipeline 성공 결과를 예외로 바꾸지 않는다."""

        secret_text = "redis://:secret-token@redis:6379/0"
        engine = SimpleNamespace(
            connect=Mock(side_effect=RuntimeError(secret_text)),
        )

        with self.assertLogs("scripts.run_daily_topic_pipeline", level="WARNING") as logs:
            _prewarm_home_topics_cache_after_success(
                engine,
                {"analysis": {"db_write_performed": True}},
                args(execute=True),
                cache=Mock(),
            )

        rendered_logs = "\n".join(logs.output)
        self.assertIn("operation=prewarm error=RuntimeError", rendered_logs)
        self.assertNotIn("secret-token", rendered_logs)

    def test_home_cache_prewarm_disabled_redis_logs_bypass_without_failure(self):
        """Redis 미설정 상태의 prewarm bypass가 pipeline 성공 흐름을 유지하는지 검증한다."""

        row = {
            "id": 1,
            "topic_date": date(2026, 7, 14),
            "title_ko": "제목",
            "summary_ko": "요약",
            "keywords": ["키워드"],
            "source_count": 2,
            "article_count": 3,
        }
        query_result = Mock()
        query_result.mappings.return_value.all.return_value = [row]
        connection = Mock()
        connection.execute.return_value = query_result
        engine = SimpleNamespace(connect=lambda: nullcontext(connection))
        cache = HomeTopicsCache(client=None, enabled=False)

        with self.assertLogs("app.home_topics_cache", level="INFO") as logs:
            _prewarm_home_topics_cache_after_success(
                engine,
                {"analysis": {"db_write_performed": True}},
                args(execute=True),
                cache=cache,
            )

        self.assertIn(
            "event=bypass operation=prewarm reason=disabled",
            "\n".join(logs.output),
        )

    def test_home_cache_prewarm_redis_set_failures_are_fail_open(self):
        """Redis connection, timeout, SET 직렬화 실패가 prewarm 예외로 전파되지 않는다."""

        row = {
            "id": 1,
            "topic_date": date(2026, 7, 14),
            "title_ko": "제목",
            "summary_ko": "요약",
            "keywords": ["키워드"],
            "source_count": 2,
            "article_count": 3,
        }
        query_result = Mock()
        query_result.mappings.return_value.all.return_value = [row]
        connection = Mock()
        connection.execute.return_value = query_result
        engine = SimpleNamespace(connect=lambda: nullcontext(connection))
        secret_text = "redis://:secret-token@redis:6379/0"

        for error in (
            OSError(secret_text),
            TimeoutError(secret_text),
            ValueError(secret_text),
        ):
            with self.subTest(error=error.__class__.__name__):
                cache = HomeTopicsCache(
                    client=FakeRedisSetClient(set_error=error),
                    ttl_seconds=108000,
                )

                with self.assertLogs("app.home_topics_cache", level="WARNING") as logs:
                    _prewarm_home_topics_cache_after_success(
                        engine,
                        {"analysis": {"db_write_performed": True}},
                        args(execute=True),
                        cache=cache,
                    )

                rendered_logs = "\n".join(logs.output)
                self.assertIn(
                    f"event=bypass operation=prewarm error={error.__class__.__name__}",
                    rendered_logs,
                )
                self.assertNotIn("secret-token", rendered_logs)
                self.assertNotIn(secret_text, rendered_logs)


if __name__ == "__main__":
    unittest.main()
