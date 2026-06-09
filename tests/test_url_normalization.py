import unittest

from app.utils.url_normalization import make_title_hash, normalize_title, normalize_url


class NormalizeUrlTests(unittest.TestCase):
    def test_removes_common_tracking_and_sorts_retained_query(self):
        url = "HTTPS://Example.COM:443/news/?b=2&utm_source=rss&a=1&fbclid=x#top"

        self.assertEqual(
            normalize_url(url),
            "https://example.com/news?a=1&b=2",
        )

    def test_removes_domain_tracking_parameter_from_subdomain(self):
        url = "https://www.wired.com/story/example/?source=RSS&edition=us"

        self.assertEqual(
            normalize_url(url),
            "https://www.wired.com/story/example?edition=us",
        )

    def test_preserves_path_case_and_non_tracking_query_values(self):
        url = "http://Example.com:8080/News/Item/?id=A%2FB&id=second"

        self.assertEqual(
            normalize_url(url),
            "http://example.com:8080/News/Item?id=A%2FB&id=second",
        )

    def test_returns_none_for_unusable_url(self):
        self.assertIsNone(normalize_url(""))
        self.assertIsNone(normalize_url("not-a-url"))
        self.assertIsNone(normalize_url("ftp://example.com/item"))
        self.assertIsNone(normalize_url("https://example.com:invalid/item"))
        self.assertIsNone(normalize_url("https://user:pass@example.com/item"))


class NormalizeTitleTests(unittest.TestCase):
    def test_normalizes_unicode_case_punctuation_and_whitespace(self):
        self.assertEqual(
            normalize_title("  AI’s Future: What’s Next?  "),
            "ai s future what s next",
        )

    def test_hash_uses_normalized_title(self):
        self.assertEqual(
            make_title_hash("Breaking: News!"),
            make_title_hash(" breaking news "),
        )

    def test_returns_none_for_missing_title(self):
        self.assertIsNone(normalize_title(None))
        self.assertIsNone(make_title_hash("  "))


if __name__ == "__main__":
    unittest.main()
