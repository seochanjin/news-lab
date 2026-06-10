import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from scripts.run_raw_extraction_targets import (
    build_execution_candidates,
    build_execution_plan,
    execute_plan,
    parse_args,
    render_execution_report,
)


def article(article_id, status, raw_status="not_extracted"):
    return {
        "id": article_id,
        "title": f"Article {article_id}",
        "source": "Source",
        "extraction_target_status": status,
        "raw_extraction_status": raw_status,
        "extraction_target_reason": f"Reason for {status}.",
    }


def target_result():
    return {
        "analysis": {"extraction_target_count": 2},
        "topic_candidates": [
            {
                "topic_candidate_id": "topic-0001",
                "articles": [
                    article(1, "target"),
                    article(2, "backup"),
                    article(3, "already_extracted", "already_extracted"),
                    article(4, "failed", "failed"),
                ],
            },
            {
                "topic_candidate_id": "topic-0002",
                "articles": [
                    article(5, "target"),
                    article(6, "skipped"),
                ],
            },
        ],
    }


def args(*, execute=False, limit=None):
    return SimpleNamespace(execute=execute, limit=limit)


class RunRawExtractionTargetsTests(unittest.TestCase):
    def test_defaults_to_dry_run(self):
        parsed = parse_args([])

        self.assertFalse(parsed.execute)
        self.assertIsNone(parsed.limit)
        self.assertFalse(parsed.use_embedding_provider)

    def test_execute_requires_limit(self):
        with self.assertRaises(SystemExit):
            parse_args(["--execute"])

    def test_limit_must_be_between_one_and_five(self):
        with self.assertRaises(SystemExit):
            parse_args(["--limit", "0"])
        with self.assertRaises(SystemExit):
            parse_args(["--limit", "6"])
        self.assertEqual(parse_args(["--limit", "5"]).limit, 5)

    def test_execution_candidates_include_only_targets_and_apply_limit(self):
        candidates = build_execution_candidates(target_result(), limit=1)

        self.assertEqual([candidate["article_id"] for candidate in candidates], [1])
        self.assertEqual(candidates[0]["topic_candidate_id"], "topic-0001")
        self.assertEqual(candidates[0]["execution_status"], "planned")

    def test_dry_run_plan_does_not_mark_write(self):
        plan = build_execution_plan(target_result(), args(limit=2))

        self.assertFalse(plan["analysis"]["execute_requested"])
        self.assertTrue(plan["analysis"]["dry_run"])
        self.assertFalse(plan["analysis"]["raw_extraction_performed"])
        self.assertFalse(plan["analysis"]["db_write_performed"])
        self.assertEqual(plan["execution_results"], [])

    def test_execute_path_calls_mock_executor_with_target_ids_only(self):
        executor = Mock(return_value=[{"article_id": 1, "status": "success"}])
        plan = build_execution_plan(target_result(), args(execute=True, limit=1))

        result = execute_plan(plan, executor=executor)

        executor.assert_called_once_with([1], limit=1)
        self.assertTrue(result["analysis"]["raw_extraction_performed"])
        self.assertTrue(result["analysis"]["db_write_performed"])
        self.assertEqual(result["execution_results"][0]["status"], "success")

    def test_execute_with_no_candidates_does_not_call_executor(self):
        executor = Mock()
        empty_result = {"analysis": {"extraction_target_count": 0}, "topic_candidates": []}
        plan = build_execution_plan(empty_result, args(execute=True, limit=1))

        result = execute_plan(plan, executor=executor)

        executor.assert_not_called()
        self.assertFalse(result["analysis"]["raw_extraction_performed"])
        self.assertFalse(result["analysis"]["db_write_performed"])

    def test_dry_run_report_contains_required_plan_fields(self):
        plan = build_execution_plan(target_result(), args(limit=1))

        report = render_execution_report(plan)

        self.assertIn("Dry-run: `true`", report)
        self.assertIn("Raw extraction performed: `false`", report)
        self.assertIn("DB write performed: `false`", report)
        self.assertIn("Article ID", report)
        self.assertIn("Topic ID", report)
        self.assertIn("Reason for target.", report)
        self.assertIn("not an approval", report)


if __name__ == "__main__":
    unittest.main()
