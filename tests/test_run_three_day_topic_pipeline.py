"""3일 Topic 실행 진입점의 CLI 안전성과 단계 조정 계약을 검증한다.

가짜 stage 결과와 mock dependency만 사용해 dry-run 기본값, embedding provider
옵션 부재, 공통 context 전달, 실행 통계와 run 종료 변환을 확인한다. 실제 DB,
원문 추출, 외부 Summary API와 파일 쓰기는 수행하지 않는다.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.three_day_topic_pipeline import (
    ThreeDayCandidateStageResult,
    ThreeDayRawAcquisitionResult,
    ThreeDayTopicProcessingResult,
    ThreeDayTopicSelectionResult,
    resolve_three_day_pipeline_context,
)
from scripts.run_three_day_topic_pipeline import (
    _completion_from_analysis,
    build_pipeline,
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
    @patch("scripts.run_three_day_topic_pipeline.load_three_day_candidates")
    def test_build_pipeline_passes_one_context_and_reports_stage_counts(
        self,
        load_candidates,
        select_topics,
        acquire_raw,
        summarize,
    ):
        """모든 stage가 같은 context를 받고 실행 계약 통계가 합쳐지는지 확인한다."""

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
        load_candidates.return_value = candidate_result
        select_topics.return_value = topic_result
        acquire_raw.return_value = raw_result
        summarize.return_value = processing_result
        raw_state_loader = Mock(return_value={})

        result = build_pipeline(
            Mock(),
            _args(),
            pipeline_context=context,
            summary_provider=Mock(),
            raw_state_loader=raw_state_loader,
        )

        self.assertIs(
            load_candidates.call_args.kwargs["pipeline_context"],
            context,
        )
        self.assertIs(
            select_topics.call_args.kwargs["pipeline_context"],
            context,
        )
        self.assertIs(
            acquire_raw.call_args.kwargs["pipeline_context"],
            context,
        )
        self.assertIs(
            summarize.call_args.kwargs["pipeline_context"],
            context,
        )
        raw_state_loader.assert_called_once_with([])
        self.assertEqual(result["analysis"]["candidate_count"], 2)
        self.assertEqual(result["analysis"]["embedding_count"], 1)
        self.assertEqual(result["analysis"]["missing_embedding_count"], 1)
        self.assertEqual(result["analysis"]["run_status"], "success")
        self.assertIsNone(result["analysis"]["run_id"])

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


if __name__ == "__main__":
    unittest.main()
