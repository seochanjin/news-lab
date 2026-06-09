import unittest
from types import SimpleNamespace

from scripts.analyze_article_duplicates import analyze


class AnalyzeArticleDuplicatesTests(unittest.TestCase):
    def test_reports_url_and_title_hash_candidate_groups(self):
        articles = [
            {
                "id": 1,
                "source_id": 10,
                "source": "First",
                "title": "Same story!",
                "url": "https://example.com/story?utm_source=rss",
                "published_at": None,
                "created_at": "2026-06-09T00:00:00Z",
            },
            {
                "id": 2,
                "source_id": 20,
                "source": "Second",
                "title": "same story",
                "url": "https://example.com/story/",
                "published_at": "2026-06-09T01:00:00Z",
                "created_at": "2026-06-09T01:30:00Z",
            },
        ]
        args = SimpleNamespace(
            all=False,
            window_hours=24,
            time_basis="published",
            max_groups=20,
        )

        result = analyze(articles, args)

        self.assertEqual(result["analysis"]["article_count"], 2)
        self.assertEqual(
            result["analysis"]["normalized_url_candidate_group_count"],
            1,
        )
        self.assertEqual(result["analysis"]["title_hash_candidate_group_count"], 1)
        self.assertEqual(
            result["normalized_url_candidates"][0]["article_count"],
            2,
        )
        self.assertEqual(result["title_hash_candidates"][0]["article_count"], 2)

    def test_respects_printed_group_limit(self):
        articles = [
            {
                "id": article_id,
                "source_id": 1,
                "source": "Source",
                "title": "Repeated",
                "url": "https://example.com/repeated",
                "published_at": None,
                "created_at": "2026-06-09T00:00:00Z",
            }
            for article_id in (1, 2)
        ]
        args = SimpleNamespace(
            all=True,
            window_hours=24,
            time_basis="created",
            max_groups=0,
        )

        result = analyze(articles, args)

        self.assertEqual(result["analysis"]["normalized_url_candidate_group_count"], 1)
        self.assertEqual(result["normalized_url_candidates"], [])
        self.assertEqual(result["title_hash_candidates"], [])


if __name__ == "__main__":
    unittest.main()
