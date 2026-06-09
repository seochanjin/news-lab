import unittest
from datetime import datetime, timezone

from app.utils.topic_quality import (
    compare_thresholds,
    parse_thresholds,
    render_markdown_report,
)


def article(article_id, importance, source):
    now = datetime(2026, 6, 9, tzinfo=timezone.utc)
    return {
        "id": article_id,
        "source": source,
        "title": f"Article {article_id}",
        "source_category": "tech",
        "rule_category": "ai",
        "topic_category": "ai",
        "detected_language": "en",
        "importance_score": importance,
        "published_at": now,
        "created_at": now,
    }


class TopicQualityTests(unittest.TestCase):
    def test_parse_thresholds_deduplicates_and_validates(self):
        self.assertEqual(parse_thresholds("0.65, 0.70,0.65"), (0.65, 0.7))

        with self.assertRaisesRegex(ValueError, "between zero and one"):
            parse_thresholds("1.1")

    def test_compare_thresholds_reports_singleton_ratio(self):
        articles = [article(1, 10, "A"), article(2, 5, "B"), article(3, 1, "C")]
        embeddings = [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]]

        comparisons = compare_thresholds(articles, embeddings, (0.7, 0.99))

        self.assertEqual(comparisons[0]["multi_article_topic_candidate_count"], 1)
        self.assertEqual(comparisons[0]["singleton_topic_count"], 1)
        self.assertEqual(comparisons[1]["multi_article_topic_candidate_count"], 0)
        self.assertEqual(comparisons[1]["singleton_topic_ratio"], 1.0)

    def test_markdown_report_contains_review_fields_and_articles(self):
        comparisons = compare_thresholds(
            [article(1, 10, "A"), article(2, 5, "B")],
            [[1.0, 0.0], [1.0, 0.0]],
            (0.72,),
        )
        result = {
            "analysis": {
                "embedding_model": "fake-v1",
                "embedding_provider_enabled": True,
                "article_count": 2,
                "time_basis": "published",
                "window_hours": 24,
            },
            "provider_call_estimate": {
                "estimated_tokens": 10,
                "estimated_cost_usd": 0.000001,
            },
            "threshold_comparison": comparisons,
            "deterministic_hash_comparison": None,
        }

        report = render_markdown_report(result)

        self.assertIn("Human review: **Pending**", report)
        self.assertIn("Threshold 0.72", report)
        self.assertIn("Article 1", report)
        self.assertIn("Similarity", report)


if __name__ == "__main__":
    unittest.main()
