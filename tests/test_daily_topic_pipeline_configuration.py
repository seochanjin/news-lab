"""Daily topic pipeline의 기사 상한 설정과 단계 결과 집합 계약을 검증한다.

테스트는 CLI 파싱과 메모리 내 dataclass 생성만 수행하며 provider, DB,
Kubernetes 같은 외부 시스템을 호출하거나 상태를 변경하지 않는다.
"""

import unittest

from app.services.daily_topic_pipeline.models import TopicSelectionResult
from scripts.run_daily_topic_pipeline import parse_args


class DailyTopicPipelineConfigurationTests(unittest.TestCase):
    """관련 기사와 Summary 기사 상한의 기본값·호환성·검증 규칙을 확인한다."""

    def test_defaults_separate_related_and_summary_article_limits(self):
        """신규 CLI 기본값이 관련 기사 20건과 Summary 기사 3건으로 분리된다."""

        args = parse_args([])

        self.assertEqual(args.max_related_articles_per_topic, 20)
        self.assertEqual(args.max_summary_articles_per_topic, 3)
        self.assertEqual(args.max_articles_per_topic, 3)

    def test_rejects_summary_limit_greater_than_related_limit(self):
        """Summary 상한이 관련 기사 상한보다 크면 pipeline 실행 전에 차단한다."""

        with self.assertRaises(SystemExit):
            parse_args(
                [
                    "--max-related-articles-per-topic",
                    "2",
                    "--max-summary-articles-per-topic",
                    "3",
                ]
            )

    def test_deprecated_alias_preserves_previous_single_limit_semantics(self):
        """기존 alias 단독 사용 시 두 상한에 같은 값을 적용해 호환성을 유지한다."""

        args = parse_args(["--max-articles-per-topic", "2"])

        self.assertEqual(args.max_related_articles_per_topic, 2)
        self.assertEqual(args.max_summary_articles_per_topic, 2)
        self.assertEqual(args.max_articles_per_topic, 2)

    def test_rejects_deprecated_alias_mixed_with_new_limits(self):
        """기존 alias와 신규 상한을 혼용한 모호한 설정을 명시적으로 거부한다."""

        with self.assertRaises(SystemExit):
            parse_args(
                [
                    "--max-articles-per-topic",
                    "2",
                    "--max-related-articles-per-topic",
                    "20",
                ]
            )


class TopicSelectionResultTests(unittest.TestCase):
    """단계 결과가 관련 기사와 Summary 기사 집합을 독립적으로 보관하는지 검증한다."""

    def test_accepts_summary_articles_as_related_article_subset(self):
        """대표 기사를 포함한 Summary 기사 부분집합은 정상 결과로 생성된다."""

        result = self._result(
            representative_article_ids=[1],
            related_article_ids=[1, 2, 3],
            summary_article_ids=[1, 2],
        )

        self.assertEqual(result.related_article_ids, [1, 2, 3])
        self.assertEqual(result.summary_article_ids, [1, 2])
        self.assertEqual(result.selected_article_ids, [1, 2])

    def test_rejects_summary_article_outside_related_articles(self):
        """관련 기사에 없는 Summary 기사 ID가 있으면 단계 경계에서 차단한다."""

        with self.assertRaisesRegex(
            ValueError,
            "summary articles must be a subset of related articles",
        ):
            self._result(
                representative_article_ids=[1],
                related_article_ids=[1, 2],
                summary_article_ids=[1, 3],
            )

    def test_rejects_representative_missing_from_summary_articles(self):
        """특별한 실패 상태가 없는 결과에서 대표 기사가 Summary 집합에 없으면 거부한다."""

        with self.assertRaisesRegex(
            ValueError,
            "representative articles must be included in summary articles",
        ):
            self._result(
                representative_article_ids=[1],
                related_article_ids=[1, 2],
                summary_article_ids=[2],
            )

    @staticmethod
    def _result(
        *,
        representative_article_ids,
        related_article_ids,
        summary_article_ids,
    ):
        """집합 계약 테스트에 필요한 최소 TopicSelectionResult를 생성한다."""

        return TopicSelectionResult(
            selected_topics=[],
            reference_topics=[],
            representative_article_ids=representative_article_ids,
            related_article_ids=related_article_ids,
            summary_article_ids=summary_article_ids,
            cluster_count=0,
            selected_topic_count=0,
            topic_candidate_count=0,
        )


if __name__ == "__main__":
    unittest.main()
