import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from scripts.analyze_article_classification import analyze


class AnalyzeArticleClassificationTests(unittest.TestCase):
    def test_reports_counts_mismatches_and_importance_candidates(self):
        now = datetime.now(timezone.utc)
        articles = [
            {
                "id": 1,
                "source_id": 10,
                "source": "BBC World",
                "title": "Breaking AI chatbot update",
                "summary": "Artificial intelligence market news",
                "source_category": "world",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            },
            {
                "id": 2,
                "source_id": 20,
                "source": "TechCrunch",
                "title": "Local notes",
                "summary": None,
                "source_category": "tech",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            },
        ]
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="published",
            max_examples=5,
        )

        result = analyze(articles, args)

        self.assertEqual(result["analysis"]["article_count"], 2)
        self.assertEqual(result["analysis"]["source_rule_category_mismatch_count"], 1)
        self.assertEqual(result["source_category_counts"], {"tech": 1, "world": 1})
        self.assertEqual(result["rule_category_counts"], {"ai": 1, "unknown": 1})
        self.assertEqual(result["language_counts"], {"en": 2})
        self.assertGreater(result["importance_score_summary"]["maximum"], 0)
        self.assertGreater(result["importance_score_summary"]["nonzero_count"], 0)
        self.assertEqual(
            result["source_rule_category_mismatch_examples"][0]["id"],
            1,
        )
        self.assertEqual(result["top_importance_candidates"][0]["id"], 1)

    def test_respects_example_limit(self):
        now = datetime.now(timezone.utc)
        articles = [
            {
                "id": 1,
                "source_id": 10,
                "source": "BBC World",
                "title": "AI update",
                "summary": None,
                "source_category": "world",
                "published_at": now,
                "created_at": now,
                "analysis_time": now,
            }
        ]
        args = SimpleNamespace(
            all=True,
            window_hours=24,
            time_basis="created",
            max_examples=0,
        )

        result = analyze(articles, args)

        self.assertEqual(result["analysis"]["source_rule_category_mismatch_count"], 1)
        self.assertEqual(result["source_rule_category_mismatch_examples"], [])
        self.assertEqual(result["top_importance_candidates"], [])


if __name__ == "__main__":
    unittest.main()
