"""3일 Topic 실행 진입점의 CLI 안전성, 단계 조정과 cache hook을 검증한다.

가짜 stage 결과와 mock dependency만 사용해 dry-run 기본값, embedding provider
옵션 부재, 공통 context 전달, 실행 통계, run 종료 변환과 Redis SETEX fail-open을
확인한다. 실제 DB, Redis, 원문 추출, 외부 Summary API와 파일 쓰기는 수행하지
않는다.
"""

import os
import unittest
from contextlib import nullcontext
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.home_topics_cache import HomeTopicsCache, THREE_DAY_HOME_TOPICS_CACHE_KEY
from app.services.three_day_topic_pipeline import (
    ThreeDayCandidateStageResult,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicProcessingResult,
    ThreeDayTopicSelectionResult,
    resolve_three_day_pipeline_context,
)
from scripts.run_three_day_topic_pipeline import (
    _completion_from_analysis,
    _prewarm_three_day_home_topics_cache_after_success,
    build_pipeline,
    load_candidates_for_context,
    parse_args,
)


def _args(*, execute=False):
    """Pipeline 조정 테스트에 필요한 검증 완료 CLI namespace를 만든다."""

    return SimpleNamespace(
        execute=execute,
        max_articles=500,
        similarity_threshold=0.70,
        max_topics=5,
        max_related_articles_per_topic=20,
        max_summary_articles_per_topic=3,
        max_raw_chars_per_article=3000,
        extraction_limit=5,
    )


class FakeRedisSetClient:
    """3일 prewarm 테스트에서 Redis SETEX 성공과 실패만 재현한다."""

    def __init__(self, *, set_error=None):
        """SETEX 호출 기록과 선택적 오류를 초기화한다."""

        self.set_error = set_error
        self.set_calls = []

    def setex(self, key, ttl_seconds, value):
        """SETEX 호출을 기록하거나 지정된 Redis 계층 오류를 발생시킨다."""

        if self.set_error:
            raise self.set_error
        self.set_calls.append((key, ttl_seconds, value))


class RunThreeDayTopicPipelineTests(unittest.TestCase):
    """3일 전용 CLI와 pipeline orchestration의 회귀를 검증한다."""

    @patch("scripts.run_three_day_topic_pipeline.load_dotenv")
    def test_defaults_to_dry_run_without_embedding_provider_option(self, load_dotenv):
        """기본 실행은 dry-run이고 embedding 생성 flag가 노출되지 않는지 확인한다."""

        parsed = parse_args([])

        self.assertEqual(parsed.window_hours, 72)
        self.assertEqual(parsed.max_articles, 500)
        self.assertFalse(parsed.execute)
        self.assertFalse(parsed.use_summary_provider)
        with self.assertRaises(SystemExit):
            parse_args(["--use-embedding-provider"])

    @patch("scripts.run_three_day_topic_pipeline.load_dotenv")
    def test_execute_requires_summary_provider_and_key(self, load_dotenv):
        """DB 교체 실행이 deterministic Summary로 저장되는 구성을 차단한다."""

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                parse_args(["--execute"])
            with self.assertRaises(SystemExit):
                parse_args(["--execute", "--use-summary-provider"])
        with patch.dict(
            os.environ,
            {"OPENAI_SUMMARY_API_KEY": "test"},
            clear=True,
        ):
            parsed = parse_args(["--execute", "--use-summary-provider"])
        self.assertTrue(parsed.execute)

    @patch("scripts.run_three_day_topic_pipeline.load_dotenv")
    def test_dry_run_allows_summary_provider_flag_without_api_key(self, load_dotenv):
        """Dry-run은 provider flag가 있어도 외부 API key를 요구하지 않는지 확인한다."""

        with patch.dict(os.environ, {}, clear=True):
            parsed = parse_args(["--use-summary-provider"])

        self.assertFalse(parsed.execute)
        self.assertTrue(parsed.use_summary_provider)

    @patch("scripts.run_three_day_topic_pipeline.load_dotenv")
    def test_window_end_accepts_timezone_and_rejects_naive_value(self, load_dotenv):
        """재현 실행 종료 경계가 timezone-aware ISO 8601만 허용하는지 확인한다."""

        parsed = parse_args(["--window-end", "2026-06-23T05:00:00+09:00"])

        self.assertEqual(
            parsed.window_end,
            datetime(
                2026,
                6,
                23,
                5,
                tzinfo=timezone(timedelta(hours=9)),
            ),
        )
        with self.assertRaises(SystemExit):
            parse_args(["--window-end", "2026-06-23T05:00:00"])

    @patch("scripts.run_three_day_topic_pipeline.summarize_and_persist_three_day_topics")
    @patch("scripts.run_three_day_topic_pipeline.acquire_three_day_topic_raw_texts")
    @patch("scripts.run_three_day_topic_pipeline.cluster_and_select_three_day_topics")
    def test_build_pipeline_passes_one_context_and_reports_stage_counts(
        self,
        select_topics,
        acquire_raw,
        summarize,
    ):
        """선정 stage가 같은 context를 받고 dry-run 부수 효과가 차단되는지 확인한다."""

        context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc)
        )
        candidate_result = ThreeDayCandidateStageResult(
            articles_with_embeddings=[({"id": 1}, (1.0, 0.0))],
            missing_embeddings=[{"article_id": 2, "reason": "missing_row"}],
        )
        topic_result = ThreeDayTopicSelectionResult(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[],
            summary_article_ids=[],
            cluster_count=0,
            topic_candidate_count=0,
        )
        raw_result = ThreeDayRawAcquisitionResult(
            article_raw_texts={},
            reused_article_ids=[],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        processing_result = ThreeDayTopicProcessingResult(
            topics=[],
            generated_topic_count=0,
            saved_topic_count=0,
            failed_topic_count=0,
            saved_topic_ids=[],
            failures=[],
            run_status="success",
        )
        select_topics.return_value = topic_result
        acquire_raw.return_value = raw_result
        summarize.return_value = processing_result
        raw_state_loader = Mock(return_value={})
        summary_provider = Mock()

        result = build_pipeline(
            candidate_result,
            _args(),
            pipeline_context=context,
            summary_provider=summary_provider,
            raw_state_loader=raw_state_loader,
        )

        self.assertIs(
            select_topics.call_args.kwargs["pipeline_context"],
            context,
        )
        acquire_raw.assert_not_called()
        summarize.assert_not_called()
        raw_state_loader.assert_not_called()
        summary_provider.summarize.assert_not_called()
        self.assertEqual(result["analysis"]["candidate_count"], 2)
        self.assertEqual(result["analysis"]["embedding_count"], 1)
        self.assertEqual(result["analysis"]["missing_embedding_count"], 1)
        self.assertEqual(result["analysis"]["run_status"], "success")
        self.assertIsNone(result["analysis"]["run_id"])

    @patch("scripts.run_three_day_topic_pipeline.summarize_and_persist_three_day_topics")
    @patch("scripts.run_three_day_topic_pipeline.acquire_three_day_topic_raw_texts")
    @patch("scripts.run_three_day_topic_pipeline.cluster_and_select_three_day_topics")
    def test_execute_mode_calls_raw_summary_and_repository_stages(
        self,
        select_topics,
        acquire_raw,
        summarize,
    ):
        """Execute 모드에서만 원문 확보와 Summary 저장 stage가 호출되는지 검증한다."""

        context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc)
        )
        candidate_result = ThreeDayCandidateStageResult(
            articles_with_embeddings=[({"id": 1}, (1.0, 0.0))],
            missing_embeddings=[],
        )
        topic_result = ThreeDayTopicSelectionResult(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[1],
            summary_article_ids=[1],
            cluster_count=0,
            topic_candidate_count=0,
        )
        raw_result = ThreeDayRawAcquisitionResult(
            article_raw_texts={},
            reused_article_ids=[],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        processing_result = ThreeDayTopicProcessingResult(
            topics=[],
            generated_topic_count=0,
            saved_topic_count=0,
            failed_topic_count=0,
            saved_topic_ids=[],
            failures=[],
            run_status="success",
        )
        select_topics.return_value = topic_result
        acquire_raw.return_value = raw_result
        summarize.return_value = processing_result
        raw_state_loader = Mock(return_value={1: {"has_raw_text": False}})
        repository = Mock()

        build_pipeline(
            candidate_result,
            _args(execute=True),
            pipeline_context=context,
            summary_provider=Mock(),
            repository=repository,
            run_id=10,
            raw_state_loader=raw_state_loader,
        )

        raw_state_loader.assert_called_once_with([1])
        acquire_raw.assert_called_once()
        summarize.assert_called_once()
        self.assertIs(summarize.call_args.kwargs["repository"], repository)

    @patch("scripts.run_three_day_topic_pipeline.load_three_day_candidates")
    def test_candidate_connection_is_closed_before_downstream_processing(
        self,
        load_candidates,
    ):
        """후보 조회 connection이 materialize 후 반환되는 구조를 검증한다."""

        context = resolve_three_day_pipeline_context(
            started_at_utc=datetime(2026, 6, 23, 3, tzinfo=timezone.utc)
        )
        expected = ThreeDayCandidateStageResult([], [])
        load_candidates.return_value = expected
        engine = _RecordingEngine()

        result = load_candidates_for_context(
            engine,
            _args(),
            pipeline_context=context,
        )

        self.assertIs(result, expected)
        self.assertEqual(engine.events, ["connect", "execute", "close"])
        self.assertTrue(engine.connection.closed)

    def test_completion_uses_actual_analysis_counts(self):
        """Run 종료 model이 pipeline 결과의 실제 count와 상태를 보존하는지 확인한다."""

        analysis = {
            "run_status": "partial_success",
            "candidate_count": 10,
            "embedding_count": 8,
            "missing_embedding_count": 2,
            "cluster_count": 4,
            "selected_topic_count": 3,
            "saved_topic_count": 2,
            "failed_topic_count": 1,
        }

        completion = _completion_from_analysis(analysis)

        self.assertEqual(completion.status, "partial_success")
        self.assertEqual(completion.candidate_count, 10)
        self.assertEqual(completion.saved_topic_count, 2)
        self.assertEqual(completion.failed_topic_count, 1)

    def test_execute_saved_topics_prewarm_reads_three_day_home_payload(self):
        """3일 Topic 저장 성공 결과에서 Home payload를 조회해 prewarm 저장한다."""

        row = {
            "id": 31,
            "reference_date": date(2026, 7, 14),
            "window_start": datetime(2026, 7, 11, tzinfo=timezone.utc),
            "window_end": datetime(2026, 7, 14, tzinfo=timezone.utc),
            "title_ko": "3일 이슈",
            "summary_ko": "3일 요약",
            "keywords": ["정책"],
            "source_count": 4,
            "article_count": 5,
        }
        query_result = Mock()
        query_result.mappings.return_value.all.return_value = [row]
        connection = Mock()
        connection.execute.return_value = query_result
        engine = SimpleNamespace(connect=lambda: nullcontext(connection))
        cache = Mock()

        _prewarm_three_day_home_topics_cache_after_success(
            engine,
            {"analysis": {"saved_topic_count": 1}},
            _args(execute=True),
            cache=cache,
        )

        cache.set.assert_called_once()
        payload = cache.set.call_args.args[0]
        self.assertEqual(cache.set.call_args.kwargs["operation"], "prewarm")
        self.assertEqual(payload["items"], [row])
        self.assertEqual(payload["reference_date"], date(2026, 7, 14))
        self.assertIn("generated_at", payload)
        self.assertEqual(connection.execute.call_args.args[1], {"limit": 10})

    def test_dry_run_and_no_publishable_result_skip_three_day_prewarm(self):
        """Dry-run 또는 저장된 publishable Topic이 없으면 prewarm을 호출하지 않는다."""

        engine = Mock()
        cache = Mock()

        _prewarm_three_day_home_topics_cache_after_success(
            engine,
            {"analysis": {"saved_topic_count": 1}},
            _args(execute=False),
            cache=cache,
        )
        _prewarm_three_day_home_topics_cache_after_success(
            engine,
            {"analysis": {"saved_topic_count": 0}},
            _args(execute=True),
            cache=cache,
        )

        engine.connect.assert_not_called()
        cache.set.assert_not_called()

    def test_three_day_prewarm_failure_does_not_fail_pipeline(self):
        """3일 prewarm 조회 실패가 pipeline 성공 결과를 예외로 바꾸지 않는다."""

        secret_text = "redis://:secret-token@redis:6379/0"
        engine = SimpleNamespace(connect=Mock(side_effect=RuntimeError(secret_text)))

        with self.assertLogs("scripts.run_three_day_topic_pipeline", level="WARNING") as logs:
            _prewarm_three_day_home_topics_cache_after_success(
                engine,
                {"analysis": {"saved_topic_count": 1}},
                _args(execute=True),
                cache=Mock(),
            )

        rendered_logs = "\n".join(logs.output)
        self.assertIn("operation=prewarm key=three-day error=RuntimeError", rendered_logs)
        self.assertNotIn("secret-token", rendered_logs)

    def test_three_day_prewarm_disabled_redis_logs_bypass_without_failure(self):
        """Redis 미설정 상태의 3일 prewarm bypass가 pipeline 성공 흐름을 유지한다."""

        row = {
            "id": 31,
            "reference_date": date(2026, 7, 14),
            "window_start": datetime(2026, 7, 11, tzinfo=timezone.utc),
            "window_end": datetime(2026, 7, 14, tzinfo=timezone.utc),
            "title_ko": "3일 이슈",
            "summary_ko": "3일 요약",
            "keywords": ["정책"],
            "source_count": 4,
            "article_count": 5,
        }
        query_result = Mock()
        query_result.mappings.return_value.all.return_value = [row]
        connection = Mock()
        connection.execute.return_value = query_result
        engine = SimpleNamespace(connect=lambda: nullcontext(connection))
        cache = HomeTopicsCache(
            client=None,
            key=THREE_DAY_HOME_TOPICS_CACHE_KEY,
            enabled=False,
        )

        with self.assertLogs("app.home_topics_cache", level="INFO") as logs:
            _prewarm_three_day_home_topics_cache_after_success(
                engine,
                {"analysis": {"saved_topic_count": 1}},
                _args(execute=True),
                cache=cache,
            )

        self.assertIn(
            "event=bypass operation=prewarm reason=disabled",
            "\n".join(logs.output),
        )

    def test_three_day_prewarm_redis_set_failures_are_fail_open(self):
        """Redis connection, timeout, SETEX 실패가 3일 Pipeline 성공을 바꾸지 않는다."""

        row = {
            "id": 31,
            "reference_date": date(2026, 7, 14),
            "window_start": datetime(2026, 7, 11, tzinfo=timezone.utc),
            "window_end": datetime(2026, 7, 14, tzinfo=timezone.utc),
            "title_ko": "3일 이슈",
            "summary_ko": "3일 요약",
            "keywords": ["정책"],
            "source_count": 4,
            "article_count": 5,
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
                    key=THREE_DAY_HOME_TOPICS_CACHE_KEY,
                    ttl_seconds=108000,
                )

                with self.assertLogs("app.home_topics_cache", level="WARNING") as logs:
                    _prewarm_three_day_home_topics_cache_after_success(
                        engine,
                        {"analysis": {"saved_topic_count": 1}},
                        _args(execute=True),
                        cache=cache,
                    )

                rendered_logs = "\n".join(logs.output)
                self.assertIn(
                    f"event=bypass operation=prewarm error={error.__class__.__name__}",
                    rendered_logs,
                )
                self.assertNotIn("secret-token", rendered_logs)
                self.assertNotIn(secret_text, rendered_logs)

class _RecordingConnection:
    """후보 조회 connection 반환 시점을 기록하는 테스트용 connection이다."""

    def __init__(self, engine):
        """부모 engine과 close 여부를 보관한다."""

        self.engine = engine
        self.closed = False

    def __enter__(self):
        """Context manager 진입 시 자기 자신을 반환한다."""

        return self

    def __exit__(self, exc_type, exc, tb):
        """Context manager 종료 시 close 기록을 남긴다."""

        self.closed = True
        self.engine.events.append("close")

    def execute(self, *_args, **_kwargs):
        """read-only 설정 SQL 실행을 기록한다."""

        self.engine.events.append("execute")


class _RecordingEngine:
    """후보 조회 helper가 connection scope를 좁히는지 확인하는 가짜 engine이다."""

    def __init__(self):
        """이벤트 목록과 마지막 connection을 초기화한다."""

        self.events = []
        self.connection = None

    def connect(self):
        """새 connection을 만들고 connect 이벤트를 기록한다."""

        self.events.append("connect")
        self.connection = _RecordingConnection(self)
        return self.connection


if __name__ == "__main__":
    unittest.main()
