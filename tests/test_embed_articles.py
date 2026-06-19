import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from scripts.embed_articles import (
    main,
    parse_args,
    process_selected_articles,
    select_articles,
)


class FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeResult(self.rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeEngine:
    def __init__(self, rows):
        self.connection = FakeConnection(rows)

    def connect(self):
        return self.connection


class EmbedArticlesScriptTests(unittest.TestCase):
    def test_parse_args_supports_required_options(self):
        args = parse_args(
            ["--limit", "3", "--article-id", "10", "--article-id", "11", "--dry-run"]
        )

        self.assertEqual(args.limit, 3)
        self.assertEqual(args.article_ids, [10, 11])
        self.assertTrue(args.dry_run)

    def test_select_articles_uses_bound_filters(self):
        rows = [{"id": 10, "title": "Article", "summary": None}]
        connection = FakeConnection(rows)

        result = select_articles(connection, limit=3, article_ids=[10])

        self.assertEqual(result, rows)
        sql, params = connection.calls[0]
        self.assertIn("select id, title, summary", sql)
        self.assertEqual(params["article_ids"], [10])
        self.assertEqual(params["limit"], 3)
        self.assertTrue(params["use_article_ids"])

    def test_batch_aggregates_statuses_and_failures(self):
        rows = [{"id": number} for number in range(1, 6)]
        statuses = iter(["created", "updated", "reused"])

        def process(row):
            if row["id"] >= 4:
                raise RuntimeError("provider failed")
            return next(statuses)

        summary, failures = process_selected_articles(rows, process)

        self.assertEqual(
            summary,
            {
                "selected": 5,
                "created": 1,
                "updated": 1,
                "reused": 1,
                "failed": 2,
            },
        )
        self.assertEqual([failure["article_id"] for failure in failures], [4, 5])

    @patch("scripts.embed_articles._create_provider")
    @patch("scripts.embed_articles.create_database_engine")
    def test_dry_run_skips_provider_and_writes(self, create_engine, create_provider):
        engine = FakeEngine([{"id": 1, "title": "Article", "summary": None}])
        create_engine.return_value = engine
        output = StringIO()

        with redirect_stdout(output):
            exit_code = main(["--limit", "3", "--dry-run"])

        self.assertEqual(exit_code, 0)
        self.assertIn('"dry_run": true', output.getvalue())
        self.assertIn('"selected": 1', output.getvalue())
        create_provider.assert_not_called()
        self.assertEqual(len(engine.connection.calls), 1)


if __name__ == "__main__":
    unittest.main()
