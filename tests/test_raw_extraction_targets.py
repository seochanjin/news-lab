import unittest
from datetime import datetime, timedelta, timezone

from app.utils.raw_extraction_targets import (
    render_raw_extraction_target_report,
    select_raw_extraction_targets,
)


def candidate(article_id, rank, score, *, source="A", hours_old=0):
    now = datetime(2026, 6, 10, tzinfo=timezone.utc)
    return {
        "id": article_id,
        "source": source,
        "title": f"Article {article_id}",
        "published_at": now - timedelta(hours=hours_old),
        "created_at": now - timedelta(hours=hours_old),
        "representative_candidate_rank": rank,
        "candidate_score": score,
    }


def topic(topic_id, articles, *, source_count=None):
    return {
        "topic_candidate_id": topic_id,
        "article_count": len(articles),
        "source_count": source_count or len({article["source"] for article in articles}),
        "representative_candidate_count": sum(
            article["representative_candidate_rank"] is not None
            for article in articles
        ),
        "articles": articles,
    }


def result_for(topics, max_targets=1):
    return {
        "analysis": {
            "article_count": sum(item["article_count"] for item in topics),
            "topic_candidate_count": len(topics),
            "multi_article_topic_count": sum(item["article_count"] > 1 for item in topics),
            "extraction_target_count": sum(
                item["extraction_target_count"] for item in topics
            ),
            "max_targets_per_topic": max_targets,
            "similarity_threshold": 0.72,
            "embedding_provider": "deterministic",
            "embedding_model": "fake-v1",
        },
        "topic_candidates": topics,
    }


class RawExtractionTargetTests(unittest.TestCase):
    def test_selects_up_to_one_target_and_marks_remaining_candidate_backup(self):
        selected = select_raw_extraction_targets(
            [topic("topic-0001", [candidate(1, 1, 0.9), candidate(2, 2, 0.8)])],
            {},
            max_targets_per_topic=1,
        )[0]

        self.assertEqual(selected["extraction_target_count"], 1)
        self.assertEqual(
            [article["extraction_target_status"] for article in selected["articles"]],
            ["target", "backup"],
        )

    def test_max_two_selects_two_pending_candidates(self):
        selected = select_raw_extraction_targets(
            [
                topic(
                    "topic-0001",
                    [
                        candidate(1, 1, 0.9),
                        candidate(2, 2, 0.8),
                        candidate(3, 3, 0.7),
                    ],
                )
            ],
            {},
            max_targets_per_topic=2,
        )[0]

        self.assertEqual(selected["extraction_target_count"], 2)
        self.assertEqual(
            [article["extraction_target_status"] for article in selected["articles"]],
            ["target", "target", "backup"],
        )

    def test_selects_targets_by_rank_when_input_order_is_shuffled(self):
        selected = select_raw_extraction_targets(
            [
                topic(
                    "topic-0001",
                    [
                        candidate(2, 2, 0.8),
                        candidate(3, None, 0.7),
                        candidate(1, 1, 0.9),
                    ],
                )
            ],
            {},
            max_targets_per_topic=1,
        )[0]

        self.assertEqual(
            [
                (
                    article["representative_candidate_rank"],
                    article["extraction_target_status"],
                )
                for article in selected["articles"]
            ],
            [(1, "target"), (2, "backup"), (None, "skipped")],
        )

    def test_marks_existing_failed_and_non_candidate_statuses(self):
        selected = select_raw_extraction_targets(
            [
                topic(
                    "topic-0001",
                    [
                        candidate(1, 1, 0.9),
                        candidate(2, 2, 0.8),
                        candidate(3, None, 0.7),
                        candidate(4, 3, 0.6),
                    ],
                )
            ],
            {
                1: {"extraction_status": "success", "has_raw_text": True},
                2: {"extraction_status": "failed", "has_raw_text": False},
                4: {"extraction_status": "pending", "has_raw_text": False},
            },
        )[0]

        self.assertEqual(
            [article["extraction_target_status"] for article in selected["articles"]],
            ["already_extracted", "failed", "target", "skipped"],
        )

    def test_singleton_is_skipped(self):
        selected = select_raw_extraction_targets(
            [topic("topic-0001", [candidate(1, 1, 0.9)])],
            {},
        )[0]["articles"][0]

        self.assertEqual(selected["extraction_target_status"], "skipped")
        self.assertIn("Singleton", selected["extraction_target_reason"])

    def test_topic_priority_does_not_use_candidate_score(self):
        low_score_many_sources = topic(
            "topic-0002",
            [candidate(1, 1, 0.1, source="A"), candidate(2, 2, 0.1, source="B")],
            source_count=2,
        )
        high_score_one_source = topic(
            "topic-0001",
            [candidate(3, 1, 0.99), candidate(4, 2, 0.98)],
            source_count=1,
        )

        selected = select_raw_extraction_targets(
            [high_score_one_source, low_score_many_sources],
            {},
        )

        self.assertEqual(selected[0]["topic_candidate_id"], "topic-0002")

    def test_rejects_target_limits_outside_allowed_range(self):
        with self.assertRaises(ValueError):
            select_raw_extraction_targets([], {}, max_targets_per_topic=0)
        with self.assertRaises(ValueError):
            select_raw_extraction_targets([], {}, max_targets_per_topic=4)

    def test_report_explains_policy_reasons_and_read_only_status(self):
        topics = select_raw_extraction_targets(
            [topic("topic-0001", [candidate(1, 1, 0.9), candidate(2, 2, 0.8)])],
            {},
        )

        report = render_raw_extraction_target_report(result_for(topics))

        self.assertIn("DB write performed: `false`", report)
        self.assertIn("Raw extraction performed: `false`", report)
        self.assertIn("Candidate score is not used to prioritize topics", report)
        self.assertIn("Article 1 (target)", report)
        self.assertIn("Article 2 (backup)", report)
        self.assertIn("검증용", report)
        self.assertIn("승인 목록이 아니다", report)
        self.assertIn("human-approved", report)

    def test_report_warns_when_comparing_multiple_targets(self):
        topics = select_raw_extraction_targets(
            [topic("topic-0001", [candidate(1, 1, 0.9), candidate(2, 2, 0.8)])],
            {},
            max_targets_per_topic=2,
        )

        report = render_raw_extraction_target_report(result_for(topics, max_targets=2))

        self.assertIn("comparison/비교용", report)
        self.assertIn("실행 승인을 의미하지 않는다", report)


if __name__ == "__main__":
    unittest.main()
