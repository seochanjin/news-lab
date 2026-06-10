import unittest
from datetime import datetime, timedelta, timezone

from app.utils.topic_representatives import (
    render_representative_report,
    select_topic_representatives,
)


def article(
    article_id,
    *,
    source,
    importance,
    similarity,
    seed=False,
    hours_old=0,
    summary="Detailed summary " * 20,
):
    now = datetime(2026, 6, 10, tzinfo=timezone.utc)
    return {
        "id": article_id,
        "source": source,
        "title": f"Detailed article title {article_id}",
        "summary": summary,
        "source_category": "tech",
        "rule_category": "ai",
        "topic_category": "ai",
        "detected_language": "en",
        "importance_score": importance,
        "similarity_to_seed": similarity,
        "is_topic_seed": seed,
        "published_at": now - timedelta(hours=hours_old),
        "created_at": now - timedelta(hours=hours_old),
    }


def topic(articles):
    return {
        "topic_candidate_id": "topic-0001",
        "article_count": len(articles),
        "source_count": len({item["source"] for item in articles}),
        "category_distribution": {"ai": len(articles)},
        "language_distribution": {"en": len(articles)},
        "representative_article": articles[0],
        "average_similarity": 0.9,
        "max_importance_article": articles[0],
        "articles": articles,
    }


def result_for(topics):
    return {
        "analysis": {
            "article_count": sum(item["article_count"] for item in topics),
            "topic_candidate_count": len(topics),
            "multi_article_topic_count": sum(
                item["article_count"] > 1 for item in topics
            ),
            "representative_candidate_count": sum(
                item["representative_candidate_count"] for item in topics
            ),
            "similarity_threshold": 0.7,
            "embedding_provider": "deterministic",
            "embedding_model": "fake-v1",
        },
        "topic_candidates": topics,
    }


class TopicRepresentativeTests(unittest.TestCase):
    def test_selects_at_most_requested_candidates_and_marks_non_selected(self):
        result = select_topic_representatives(
            [
                topic(
                    [
                        article(1, source="A", importance=20, similarity=1.0, seed=True),
                        article(2, source="B", importance=10, similarity=0.95),
                        article(3, source="C", importance=8, similarity=0.9),
                    ]
                )
            ],
            max_candidates_per_topic=2,
        )[0]

        self.assertEqual(result["representative_candidate_count"], 2)
        self.assertEqual(len(result["representative_candidates"]), 2)
        self.assertEqual(sum(item["selected"] for item in result["articles"]), 2)
        self.assertIsNone(result["articles"][-1]["representative_candidate_rank"])

    def test_source_diversity_can_promote_a_different_source(self):
        result = select_topic_representatives(
            [
                topic(
                    [
                        article(1, source="A", importance=20, similarity=1.0, seed=True),
                        article(2, source="A", importance=15, similarity=0.99),
                        article(3, source="B", importance=15, similarity=0.99),
                    ]
                )
            ],
            max_candidates_per_topic=2,
        )[0]

        self.assertEqual(
            [item["source"] for item in result["representative_candidates"]],
            ["A", "B"],
        )

    def test_score_contains_all_required_components_and_reason(self):
        result = select_topic_representatives(
            [topic([article(1, source="A", importance=10, similarity=1.0, seed=True)])]
        )[0]["representative_candidates"][0]

        self.assertEqual(
            set(result["candidate_score_components"]),
            {
                "importance",
                "topic_seed",
                "similarity",
                "source_diversity",
                "information",
                "recency",
                "category",
            },
        )
        self.assertIn("Selected for", result["selection_reason"])
        self.assertEqual(result["human_review_status"], "Pending")

    def test_report_distinguishes_selected_and_non_selected_articles(self):
        topics = select_topic_representatives(
            [
                topic(
                    [
                        article(1, source="A", importance=20, similarity=1.0, seed=True),
                        article(2, source="B", importance=5, similarity=0.8),
                    ]
                )
            ],
            max_candidates_per_topic=1,
        )
        report = render_representative_report(result_for(topics))

        self.assertIn("| yes | 1 |", report)
        self.assertIn("| no |  |", report)
        self.assertIn("components:", report)
        self.assertIn("selection reason:", report)

    def test_report_excludes_singleton_details_by_default(self):
        singleton = select_topic_representatives(
            [topic([article(1, source="A", importance=10, similarity=1.0, seed=True)])]
        )[0]
        multi_article = select_topic_representatives(
            [
                {
                    **topic(
                        [
                            article(2, source="B", importance=10, similarity=1.0, seed=True),
                            article(3, source="C", importance=8, similarity=0.9),
                        ]
                    ),
                    "topic_candidate_id": "topic-0002",
                }
            ]
        )[0]

        report = render_representative_report(result_for([singleton, multi_article]))

        self.assertNotIn("### topic-0001", report)
        self.assertIn("### topic-0002", report)
        self.assertIn("Singleton topic count: 1", report)
        self.assertIn("Report detail topic count: 1", report)

    def test_report_can_include_singleton_details(self):
        topics = select_topic_representatives(
            [topic([article(1, source="A", importance=10, similarity=1.0, seed=True)])]
        )

        report = render_representative_report(
            result_for(topics),
            include_singletons=True,
        )

        self.assertIn("### topic-0001", report)
        self.assertIn("Singleton topic details included: `True`", report)

    def test_report_explains_recency_time_and_score_scope(self):
        item = article(1, source="A", importance=10, similarity=1.0, seed=True)
        item["published_at"] = None
        topics = select_topic_representatives([topic([item])])

        report = render_representative_report(
            result_for(topics),
            include_singletons=True,
        )

        self.assertIn("Created At", report)
        self.assertIn("Recency Time Source", report)
        self.assertIn("`created_at`", report)
        self.assertIn("within the same topic", report)
        self.assertIn("must not be used as an importance score across topics", report)
        self.assertIn("separate follow-up policy", report)


if __name__ == "__main__":
    unittest.main()
