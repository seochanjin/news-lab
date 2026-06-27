"""7일 Topic 실행 진입점의 CLI 안전성과 단계 조정 계약을 검증한다.

가짜 stage 결과와 mock dependency만 사용해 dry-run 기본값, embedding provider
옵션 부재, 명시 주간 context 전달, 실행 통계와 run 종료 변환을 확인한다. 실제
DB, 원문 추출, 외부 Summary API와 파일 쓰기는 수행하지 않는다.
"""

import os
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.weekly_topic_pipeline import (
    WeeklyCandidateStageResult,
    WeeklyRawAcquisitionResult,
    WeeklyTopicProcessingResult,
    WeeklyTopicSelectionResult,
    resolve_weekly_pipeline_context,
)
from scripts.run_weekly_topic_pipeline import (
    _completion_from_analysis,
    build_pipeline,
    load_candidates_for_context,
    parse_args,
)


def _args(*, execute=False):
    """Pipeline 조정 테스트에 필요한 검증 완료 CLI namespace를 만든다."""

    return SimpleNamespace(
        execute=execute,
        max_articles=1000,
        similarity_threshold=0.70,
        max_topics=5,
        max_related_articles_per_topic=20,
        max_summary_articles_per_topic=5,
        max_raw_chars_per_article=3000,
        extraction_limit=5,
    )


class RunWeeklyTopicPipelineTests(unittest.TestCase):
    """Weekly 전용 CLI와 pipeline orchestration의 회귀를 검증한다."""

    @patch("scripts.run_weekly_topic_pipeline.load_dotenv")
    def test_defaults_to_dry_run_without_embedding_provider_option(self, load_dotenv):
        """기본 실행은 dry-run이고 embedding 생성 flag가 노출되지 않는지 확인한다."""

        parsed = parse_args([])

        self.assertEqual(parsed.max_articles, 1000)
        self.assertEqual(parsed.max_summary_articles_per_topic, 5)
        self.assertFalse(parsed.execute)
        self.assertFalse(parsed.use_summary_provider)
        with self.assertRaises(SystemExit):
            parse_args(["--use-embedding-provider"])

    @patch("scripts.run_weekly_topic_pipeline.load_dotenv")
    def test_week_start_accepts_monday_and_rejects_other_dates(self, load_dotenv):
        """명시 재처리 날짜가 YYYY-MM-DD 형식의 월요일만 허용되는지 확인한다."""

        parsed = parse_args(["--week-start", "2026-06-15"])

        self.assertEqual(parsed.week_start, date(2026, 6, 15))
        with self.assertRaises(SystemExit):
            parse_args(["--week-start", "2026-06-16"])
        with self.assertRaises(SystemExit):
            parse_args(["--week-start", "2026/06/15"])

    @patch("scripts.run_weekly_topic_pipeline.load_dotenv")
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

    @patch("scripts.run_weekly_topic_pipeline.load_dotenv")
    def test_dry_run_allows_summary_provider_flag_without_api_key(self, load_dotenv):
        """Dry-run은 provider flag가 있어도 외부 API key를 요구하지 않는지 확인한다."""

        with patch.dict(os.environ, {}, clear=True):
            parsed = parse_args(["--use-summary-provider"])

        self.assertFalse(parsed.execute)
        self.assertTrue(parsed.use_summary_provider)

    @patch("scripts.run_weekly_topic_pipeline.load_dotenv")
    def test_rejects_weekly_limit_configuration_outside_policy(self, load_dotenv):
        """Weekly 최소 관련 기사와 Summary 근거 최대값을 CLI에서 검증한다."""

        with self.assertRaises(SystemExit):
            parse_args(["--max-related-articles-per-topic", "4"])
        with self.assertRaises(SystemExit):
            parse_args(["--max-summary-articles-per-topic", "6"])
        with self.assertRaises(SystemExit):
            parse_args(
                [
                    "--max-related-articles-per-topic",
                    "5",
                    "--max-summary-articles-per-topic",
                    "6",
                ]
            )

    @patch("scripts.run_weekly_topic_pipeline.summarize_and_persist_weekly_topics")
    @patch("scripts.run_weekly_topic_pipeline.acquire_weekly_topic_raw_texts")
    @patch("scripts.run_weekly_topic_pipeline.cluster_and_select_weekly_topics")
    def test_build_pipeline_passes_one_context_and_reports_stage_counts(
        self,
        select_topics,
        acquire_raw,
        summarize,
    ):
        """선정 stage가 같은 context를 받고 dry-run 부수 효과가 차단되는지 확인한다."""

        context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 22, 1, tzinfo=timezone.utc)
        )
        candidate_result = WeeklyCandidateStageResult(
            articles_with_embeddings=[({"id": 1}, (1.0, 0.0))],
            missing_embeddings=[{"article_id": 2, "reason": "missing_row"}],
        )
        topic_result = WeeklyTopicSelectionResult(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[],
            summary_article_ids=[],
            cluster_count=0,
            topic_candidate_count=0,
        )
        raw_result = WeeklyRawAcquisitionResult(
            article_raw_texts={},
            reused_article_ids=[],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        processing_result = WeeklyTopicProcessingResult(
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
        self.assertEqual(result["analysis"]["week_start"], date(2026, 6, 15))
        self.assertEqual(result["analysis"]["candidate_count"], 2)
        self.assertEqual(result["analysis"]["embedding_count"], 1)
        self.assertEqual(result["analysis"]["missing_embedding_count"], 1)
        self.assertEqual(result["analysis"]["run_status"], "success")
        self.assertIsNone(result["analysis"]["run_id"])

    @patch("scripts.run_weekly_topic_pipeline.summarize_and_persist_weekly_topics")
    @patch("scripts.run_weekly_topic_pipeline.acquire_weekly_topic_raw_texts")
    @patch("scripts.run_weekly_topic_pipeline.cluster_and_select_weekly_topics")
    def test_execute_mode_calls_raw_summary_and_repository_stages(
        self,
        select_topics,
        acquire_raw,
        summarize,
    ):
        """Execute 모드에서만 원문 확보와 Summary 저장 stage가 호출되는지 검증한다."""

        context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 22, 1, tzinfo=timezone.utc)
        )
        candidate_result = WeeklyCandidateStageResult(
            articles_with_embeddings=[({"id": 1}, (1.0, 0.0))],
            missing_embeddings=[],
        )
        topic_result = WeeklyTopicSelectionResult(
            selected_topics=[],
            representative_article_ids=[],
            related_article_ids=[1],
            summary_article_ids=[1],
            cluster_count=0,
            topic_candidate_count=0,
        )
        raw_result = WeeklyRawAcquisitionResult(
            article_raw_texts={},
            reused_article_ids=[],
            extracted_article_ids=[],
            failed_article_ids=[],
            missing_article_ids=[],
            extraction_results=[],
        )
        processing_result = WeeklyTopicProcessingResult(
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

    @patch("scripts.run_weekly_topic_pipeline.load_weekly_candidates")
    def test_candidate_connection_is_closed_before_downstream_processing(
        self,
        load_candidates,
    ):
        """후보 조회 connection이 materialize 후 반환되는 구조를 검증한다."""

        context = resolve_weekly_pipeline_context(
            started_at_utc=datetime(2026, 6, 22, 1, tzinfo=timezone.utc)
        )
        expected = WeeklyCandidateStageResult([], [])
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
