import unittest
from datetime import datetime, timezone

from app.utils.topic_grouping import cosine_similarity, group_articles


def article(article_id, importance, category="tech", source="Source"):
    now = datetime(2026, 6, 9, tzinfo=timezone.utc)
    return {
        "id": article_id,
        "source": source,
        "title": f"Article {article_id}",
        "source_category": category,
        "rule_category": category,
        "topic_category": category,
        "detected_language": "en",
        "importance_score": importance,
        "published_at": now,
        "created_at": now,
    }


class TopicGroupingTests(unittest.TestCase):
    def test_cosine_similarity(self):
        self.assertEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_cosine_similarity_rejects_mismatched_dimensions(self):
        with self.assertRaisesRegex(ValueError, "dimensions must match"):
            cosine_similarity([1.0], [1.0, 0.0])

    def test_greedy_grouping_uses_importance_seed_and_similarity_threshold(self):
        articles = [
            article(1, 3, source="A"),
            article(2, 10, source="B"),
            article(3, 1, category="world", source="C"),
        ]
        embeddings = [
            [0.9, 0.1],
            [1.0, 0.0],
            [0.0, 1.0],
        ]

        groups = group_articles(articles, embeddings, similarity_threshold=0.8)

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["representative_article"]["id"], 2)
        self.assertEqual(groups[0]["article_count"], 2)
        self.assertEqual(groups[0]["source_count"], 2)
        self.assertEqual(groups[0]["category_distribution"], {"tech": 2})
        self.assertGreater(groups[0]["average_similarity"], 0.9)
        self.assertEqual(groups[1]["representative_article"]["id"], 3)


if __name__ == "__main__":
    unittest.main()
