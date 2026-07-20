"""Daily Topic Summary 저장 계획과 transaction adapter 계약을 검증한다.

가짜 connection을 사용해 실제 DB 쓰기 없이 dry-run, upsert parameter, 기사 관계,
저장 전 제목 sanitizer와 fallback 적용을 확인한다.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.save_topic_summaries import (
    UPSERT_TOPIC_QUERY,
    build_save_plan,
    execute_save_plan,
    parse_args,
    render_save_report,
    run_save,
)
from app.utils.topic_summary import build_summary_input_hash


def summary(topic_id="topic-0001", status="ready"):
    """저장 가능 상태 또는 원문 부족 상태의 Summary fixture를 만든다."""

    return {
        "topic_candidate_id": topic_id,
        "status": status,
        "title_ko": "제목" if status == "ready" else None,
        "summary_ko": "요약" if status == "ready" else None,
        "key_points": ["핵심"] if status == "ready" else [],
        "keywords": ["키워드"] if status == "ready" else [],
        "confidence": 0.8 if status == "ready" else 0.0,
        "source_count": 1 if status == "ready" else 0,
        "article_count": 1 if status == "ready" else 0,
        "provider": "deterministic",
        "model": "deterministic-summary-v1",
        "summary_input_hash": "stable-hash",
        "used_articles": (
            [
                {
                    "article_id": 10,
                    "title": "Article",
                    "source": "Source",
                    "raw_text_length": 100,
                }
            ]
            if status == "ready"
            else []
        ),
    }


def generation_result():
    """저장 대상 한 건과 skip 대상 한 건을 포함한 생성 결과를 반환한다."""

    return {
        "analysis": {
            "provider": "deterministic",
            "model": "deterministic-summary-v1",
        },
        "topic_summaries": [summary(), summary("topic-0002", "insufficient_raw_text")],
    }


class ScalarResult:
    """SQLAlchemy scalar result의 테스트용 최소 동작을 제공한다."""

    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class FakeConnection:
    """실행 query와 parameter를 기록하고 고정 Topic ID를 반환한다."""

    def __init__(self):
        self.calls = []

    def execute(self, query, params=None):
        self.calls.append((str(query), params))
        if "returning id" in str(query).lower():
            return ScalarResult(42)
        return ScalarResult(None)


class RecordingContext:
    """가짜 connection context 진입·종료 순서를 기록한다."""

    def __init__(self, events, name):
        self.events = events
        self.name = name
        self.connection = FakeConnection()

    def __enter__(self):
        self.events.append(f"{self.name}_enter")
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        self.events.append(f"{self.name}_exit")


class RecordingEngine:
    """read와 write context를 분리해 transaction 순서를 검증한다."""

    def __init__(self, events):
        self.events = events

    def connect(self):
        return RecordingContext(self.events, "read")

    def begin(self):
        return RecordingContext(self.events, "write")


class SaveTopicSummariesTests(unittest.TestCase):
    """Daily Summary 저장 계획과 실행 경계의 회귀를 검증한다."""

    def test_upsert_conflict_target_matches_composite_unique_constraint(self):
        query = " ".join(str(UPSERT_TOPIC_QUERY).lower().split())

        self.assertIn(
            "on conflict (summary_input_hash, provider, model) do update set",
            query,
        )

    def test_defaults_to_dry_run(self):
        args = parse_args([])

        self.assertFalse(args.execute)
        self.assertFalse(args.use_summary_provider)
        self.assertEqual(args.max_topics, 3)

    def test_build_save_plan_does_not_mark_db_write(self):
        plan = build_save_plan(generation_result(), SimpleNamespace(execute=False))

        self.assertTrue(plan["analysis"]["dry_run"])
        self.assertFalse(plan["analysis"]["execute_requested"])
        self.assertFalse(plan["analysis"]["db_write_performed"])
        self.assertFalse(plan["analysis"]["raw_extraction_performed"])
        self.assertEqual(plan["analysis"]["save_candidate_count"], 1)
        self.assertEqual(plan["analysis"]["skipped_topic_count"], 1)
        self.assertEqual(plan["topics"][0]["articles"][0]["article_id"], 10)

    def test_build_save_plan_sanitizes_title_and_uses_article_fallback(self):
        """날짜뿐인 provider 제목과 기간 keyword 대신 대표 기사 제목을 저장한다."""

        result = generation_result()
        ready = result["topic_summaries"][0]
        ready["title_ko"] = "(월~일)"
        ready["keywords"] = ["최근 3일"]
        ready["used_articles"][0]["title"] = "2026-07-12 AI 반도체 투자"

        plan = build_save_plan(result, SimpleNamespace(execute=False))

        self.assertEqual(plan["topics"][0]["title_ko"], "AI 반도체 투자")

    def test_summary_input_hash_is_order_insensitive_and_input_sensitive(self):
        first = {
            "used_articles": [
                {"article_id": 1, "raw_text": "first"},
                {"article_id": 2, "raw_text": "second"},
            ]
        }
        reordered = {
            "used_articles": [
                {"article_id": 2, "raw_text": "second"},
                {"article_id": 1, "raw_text": "first"},
            ]
        }
        changed_raw_text = {
            "used_articles": [
                {"article_id": 1, "raw_text": "changed"},
                {"article_id": 2, "raw_text": "second"},
            ]
        }
        changed_article_id = {
            "used_articles": [
                {"article_id": 3, "raw_text": "first"},
                {"article_id": 2, "raw_text": "second"},
            ]
        }

        self.assertEqual(
            build_summary_input_hash(first),
            build_summary_input_hash(reordered),
        )
        self.assertNotEqual(
            build_summary_input_hash(first),
            build_summary_input_hash(changed_raw_text),
        )
        self.assertNotEqual(
            build_summary_input_hash(first),
            build_summary_input_hash(changed_article_id),
        )

    def test_execute_generation_and_plan_happen_before_write_transaction(self):
        events = []
        engine = RecordingEngine(events)
        args = SimpleNamespace(execute=True)

        with (
            patch(
                "scripts.save_topic_summaries._generate_with_connection",
                side_effect=lambda connection, args: (
                    events.append("generate"),
                    generation_result(),
                )[1],
            ),
            patch(
                "scripts.save_topic_summaries.build_save_plan",
                side_effect=lambda result, args: (
                    events.append("build_plan"),
                    {"plan": True},
                )[1],
            ),
            patch(
                "scripts.save_topic_summaries.execute_save_plan",
                side_effect=lambda plan, connection: (
                    events.append("execute_save_plan"),
                    plan,
                )[1],
            ),
        ):
            result = run_save(engine, args)

        self.assertEqual(result, {"plan": True})
        self.assertEqual(
            events,
            [
                "read_enter",
                "generate",
                "read_exit",
                "build_plan",
                "write_enter",
                "execute_save_plan",
                "write_exit",
            ],
        )

    def test_dry_run_does_not_open_write_transaction(self):
        events = []
        engine = RecordingEngine(events)
        args = SimpleNamespace(execute=False)

        with (
            patch(
                "scripts.save_topic_summaries._generate_with_connection",
                return_value=generation_result(),
            ),
            patch(
                "scripts.save_topic_summaries.execute_save_plan"
            ) as execute_save_plan_mock,
        ):
            result = run_save(engine, args)

        self.assertFalse(result["analysis"]["db_write_performed"])
        self.assertNotIn("write_enter", events)
        execute_save_plan_mock.assert_not_called()

    def test_execute_save_plan_uses_injected_connection(self):
        connection = FakeConnection()
        plan = build_save_plan(generation_result(), SimpleNamespace(execute=True))

        result = execute_save_plan(plan, connection)

        self.assertTrue(result["analysis"]["db_write_performed"])
        self.assertEqual(result["analysis"]["saved_topic_count"], 1)
        self.assertEqual(result["analysis"]["linked_article_count"], 1)
        self.assertEqual(result["topics"][0]["topic_id"], 42)
        self.assertEqual(result["topics"][0]["save_status"], "saved")
        self.assertEqual(len(connection.calls), 3)

    def test_save_report_contains_required_safety_fields(self):
        plan = build_save_plan(generation_result(), SimpleNamespace(execute=False))

        report = render_save_report(plan)

        self.assertIn("Dry-run: `true`", report)
        self.assertIn("Execute requested: `false`", report)
        self.assertIn("DB write performed: `false`", report)
        self.assertIn("Raw extraction performed: `false`", report)
        self.assertIn("insufficient_raw_text", report)


if __name__ == "__main__":
    unittest.main()
