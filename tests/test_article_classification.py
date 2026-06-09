import unittest
from datetime import datetime, timedelta, timezone

from app.utils.article_classification import (
    calculate_importance_signals,
    classify_article,
    classify_rule_category,
    count_keyword_matches,
    detect_language,
)


class CategoryClassificationTests(unittest.TestCase):
    def test_title_matches_are_weighted_above_summary_matches(self):
        category, scores = classify_rule_category(
            "AI startup releases chatbot",
            "The election result is discussed.",
        )

        self.assertEqual(category, "ai")
        self.assertGreater(scores["ai"], scores["politics"])

    def test_keyword_matching_uses_word_boundaries(self):
        self.assertEqual(count_keyword_matches("Daily update", ("ai",)), 0)
        self.assertEqual(count_keyword_matches("AI update", ("ai",)), 1)

    def test_no_category_match_returns_unknown(self):
        category, scores = classify_rule_category("Local notes", None)

        self.assertEqual(category, "unknown")
        self.assertTrue(all(score == 0 for score in scores.values()))


class LanguageDetectionTests(unittest.TestCase):
    def test_detects_non_latin_script(self):
        language, basis = detect_language("기술 뉴스", "새로운 서비스 출시")

        self.assertEqual(language, "ko")
        self.assertEqual(basis, "detected")

    def test_uses_source_language_for_short_uncertain_text(self):
        language, basis = detect_language("Brief", None, "en-US")

        self.assertEqual(language, "en")
        self.assertEqual(basis, "source_fallback")

    def test_returns_unknown_without_detection_or_fallback(self):
        language, basis = detect_language("123", None, None)

        self.assertEqual(language, "unknown")
        self.assertEqual(basis, "unknown")


class ImportanceSignalTests(unittest.TestCase):
    def test_calculates_transparent_importance_components(self):
        now = datetime(2026, 6, 9, tzinfo=timezone.utc)
        signals = calculate_importance_signals(
            title="Breaking: AI market update",
            summary="Cybersecurity and stock market news",
            source_category="world",
            article_time=now - timedelta(hours=2),
            reference_time=now,
        )

        self.assertGreater(signals["title_keyword_count"], 0)
        self.assertGreater(signals["summary_keyword_count"], 0)
        self.assertGreater(signals["breaking_keyword_count"], 0)
        self.assertGreater(signals["high_impact_keyword_count"], 0)
        self.assertEqual(signals["source_category_points"], 1)
        self.assertEqual(signals["recency_points"], 3)
        self.assertGreater(signals["score"], 0)

    def test_source_category_remains_separate_from_rule_category(self):
        result = classify_article(
            title="AI chatbot startup raises funds",
            summary=None,
            source_category="world",
            source_language="en",
            article_time=None,
        )

        self.assertEqual(result["base_category"], "world")
        self.assertEqual(result["rule_category"], "ai")


if __name__ == "__main__":
    unittest.main()
