"""7일 Topic migration과 repository의 원자적 저장 계약을 검증한다.

실제 PostgreSQL이나 production data를 사용하지 않고 migration SQL 정적 검사와
가짜 engine transaction 기록으로 run 이력 분리, advisory lock, 삭제·삽입 순서,
빈 결과 교체 및 저장 전 주간 불변식 검증을 확인한다.
"""

import unittest
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.weekly_topic_pipeline import (
    WeeklyTopicArticleRecord,
    WeeklyTopicRecord,
    WeeklyTopicRepository,
    WeeklyTopicRunCompletion,
    WeeklyTopicRunStart,
)


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "db"
    / "migrations"
    / "008_create_weekly_topic_tables.sql"
)
BUSINESS_TIMEZONE = ZoneInfo("Asia/Seoul")


class FakeResult:
    """Repository가 사용하는 scalar ID와 update rowcount를 반환한다."""

    def __init__(self, *, scalar=None, rowcount=1):
        """한 SQL 실행의 scalar와 영향 row 수를 보관한다."""

        self._scalar = scalar
        self.rowcount = rowcount

    def scalar_one(self):
        """INSERT ... RETURNING 결과로 설정된 단일 값을 반환한다."""

        return self._scalar


class RecordingConnection:
    """실행 SQL과 bind parameter를 순서대로 기록하는 가짜 connection이다."""

    def __init__(self, engine):
        """ID 할당 상태를 공유할 가짜 engine을 보관한다."""

        self.engine = engine

    def execute(self, statement, parameters=None):
        """SQL 문자열과 parameter를 기록하고 query 종류에 맞는 결과를 반환한다."""

        sql = " ".join(str(statement).split())
        self.engine.events.append(("execute", sql, parameters or {}))
        if self.engine.fail_on_sql and self.engine.fail_on_sql in sql.lower():
            raise RuntimeError("simulated insert failure")
        if "returning id" in sql.lower():
            value = self.engine.next_id
            self.engine.next_id += 1
            return FakeResult(scalar=value)
        return FakeResult(rowcount=self.engine.finish_rowcount)


class RecordingEngine:
    """Transaction 경계와 SQL 실행 순서를 기록하는 가짜 SQLAlchemy engine이다."""

    def __init__(self):
        """기록 목록, 반환 ID와 update rowcount 기본값을 초기화한다."""

        self.events = []
        self.next_id = 200
        self.finish_rowcount = 1
        self.fail_on_sql = None

    @contextmanager
    def begin(self):
        """begin·commit 경계를 기록하고 예외 시 rollback을 기록한다."""

        self.events.append(("begin",))
        try:
            yield RecordingConnection(self)
        except Exception:
            self.events.append(("rollback",))
            raise
        else:
            self.events.append(("commit",))


class WeeklyTopicMigrationTests(unittest.TestCase):
    """전용 table, 관계, idempotency와 조회 index가 migration에 있는지 검증한다."""

    def test_migration_defines_tables_constraints_and_indexes(self):
        """세 table과 핵심 FK·unique·status·rank·window 제약을 확인한다."""

        sql = MIGRATION.read_text(encoding="utf-8").lower()

        self.assertIn("create table if not exists weekly_topic_runs", sql)
        self.assertIn("create table if not exists weekly_topics", sql)
        self.assertIn("create table if not exists weekly_topic_articles", sql)
        self.assertIn("week_start date not null", sql)
        self.assertIn("week_end date not null", sql)
        self.assertIn(
            "unique (window_start, window_end, topic_candidate_id)",
            sql,
        )
        self.assertIn("unique (weekly_topic_id, article_id)", sql)
        self.assertIn("references weekly_topic_runs(id) on delete restrict", sql)
        self.assertIn("references weekly_topics(id) on delete cascade", sql)
        self.assertIn("references articles(id) on delete cascade", sql)
        self.assertIn("check (rank >= 1)", sql)
        self.assertIn("check (week_start <= week_end)", sql)
        self.assertIn("check (window_start < window_end)", sql)
        self.assertIn(
            "check (candidate_count = embedding_count + missing_embedding_count)",
            sql,
        )
        self.assertIn("check (saved_topic_count <= selected_topic_count)", sql)
        self.assertIn("'partial_success'", sql)
        self.assertIn("idx_weekly_topics_archive", sql)
        self.assertIn("idx_weekly_topic_articles_topic_rank", sql)

    def test_run_history_does_not_make_window_unique(self):
        """동일 window 재실행 이력을 막는 unique가 run table에 없음을 확인한다."""

        sql = MIGRATION.read_text(encoding="utf-8").lower()
        run_sql = sql.split(
            "create table if not exists weekly_topics",
            maxsplit=1,
        )[0]

        self.assertNotIn("unique (window_start, window_end)", run_sql)


class WeeklyTopicRepositoryTests(unittest.TestCase):
    """가짜 transaction으로 실행 이력과 window 결과 교체 순서를 검증한다."""

    def setUp(self):
        """고정 주간 window, 가짜 engine과 repository를 준비한다."""

        self.week_start = date(2026, 6, 15)
        self.week_end = date(2026, 6, 21)
        self.window_start = datetime(
            2026,
            6,
            15,
            0,
            tzinfo=BUSINESS_TIMEZONE,
        )
        self.window_end = self.window_start + timedelta(days=7)
        self.engine = RecordingEngine()
        self.repository = WeeklyTopicRepository(self.engine)

    def test_run_start_and_completion_use_separate_transactions(self):
        """Run 생성과 종료가 각각 commit되고 최종 통계가 bind되는지 확인한다."""

        run_id = self.repository.create_run(
            WeeklyTopicRunStart(
                week_start=self.week_start,
                week_end=self.week_end,
                window_start=self.window_start,
                window_end=self.window_end,
                started_at=self.window_end,
            )
        )
        self.repository.finish_run(
            run_id,
            WeeklyTopicRunCompletion(
                status="partial_success",
                candidate_count=8,
                embedding_count=6,
                missing_embedding_count=2,
                cluster_count=3,
                selected_topic_count=2,
                saved_topic_count=1,
                failed_topic_count=1,
                finished_at=self.window_end + timedelta(minutes=2),
            ),
        )

        self.assertEqual(run_id, 200)
        self.assertEqual(
            [event[0] for event in self.engine.events],
            ["begin", "execute", "commit", "begin", "execute", "commit"],
        )
        create_parameters = self.engine.events[1][2]
        finish_parameters = self.engine.events[4][2]
        self.assertEqual(create_parameters["week_start"], self.week_start)
        self.assertEqual(finish_parameters["status"], "partial_success")
        self.assertEqual(finish_parameters["missing_embedding_count"], 2)
        self.assertEqual(finish_parameters["saved_topic_count"], 1)

    def test_replace_window_locks_deletes_and_inserts_in_one_transaction(self):
        """Lock과 기존 삭제 뒤 Topic·기사 관계가 한 transaction에 저장되는지 확인한다."""

        topic_ids = self.repository.replace_window_topics(
            run_id=9,
            window_start=self.window_start,
            window_end=self.window_end,
            topics=[self._topic()],
        )

        self.assertEqual(topic_ids, [200])
        sql_events = [
            event[1].lower() for event in self.engine.events if event[0] == "execute"
        ]
        self.assertIn("pg_advisory_xact_lock", sql_events[0])
        self.assertTrue(sql_events[1].startswith("delete from weekly_topics"))
        self.assertTrue(sql_events[2].startswith("insert into weekly_topics"))
        self.assertTrue(
            sql_events[3].startswith("insert into weekly_topic_articles")
        )
        self.assertTrue(
            sql_events[7].startswith("insert into weekly_topic_articles")
        )
        self.assertEqual(self.engine.events[0], ("begin",))
        self.assertEqual(self.engine.events[-1], ("commit",))
        topic_parameters = self.engine.events[3][2]
        self.assertEqual(topic_parameters["article_count"], 5)
        self.assertEqual(topic_parameters["source_count"], 3)
        self.assertEqual(topic_parameters["prompt_version"], "weekly-flow-v1")

    def test_empty_result_still_locks_and_deletes_existing_window(self):
        """정상 빈 결과가 lock·delete 후 commit되어 기존 결과를 비우는지 확인한다."""

        topic_ids = self.repository.replace_window_topics(
            run_id=9,
            window_start=self.window_start,
            window_end=self.window_end,
            topics=[],
        )

        self.assertEqual(topic_ids, [])
        sql_events = [
            event[1].lower() for event in self.engine.events if event[0] == "execute"
        ]
        self.assertEqual(len(sql_events), 2)
        self.assertIn("pg_advisory_xact_lock", sql_events[0])
        self.assertTrue(sql_events[1].startswith("delete from weekly_topics"))
        self.assertEqual(self.engine.events[-1], ("commit",))

    def test_insert_failure_rolls_back_delete_and_new_results_together(self):
        """신규 Topic insert 실패 시 기존 삭제와 신규 저장 transaction이 rollback된다."""

        self.engine.fail_on_sql = "insert into weekly_topics"

        with self.assertRaisesRegex(RuntimeError, "simulated insert failure"):
            self.repository.replace_window_topics(
                run_id=9,
                window_start=self.window_start,
                window_end=self.window_end,
                topics=[self._topic()],
            )

        self.assertEqual(self.engine.events[-1], ("rollback",))
        self.assertNotIn(("commit",), self.engine.events)

    def test_invalid_topic_is_rejected_before_transaction(self):
        """대표 기사가 Summary 근거가 아니면 DB transaction을 시작하지 않는다."""

        with self.assertRaisesRegex(
            ValueError,
            "representative article must be summary evidence",
        ):
            self._topic(representative_is_evidence=False)

        self.assertEqual(self.engine.events, [])

    def test_topic_rejects_too_few_articles_or_sources(self):
        """Weekly 최소 기사 수 5개와 최소 source 수 2개를 저장 전에 검증한다."""

        with self.assertRaisesRegex(
            ValueError,
            "weekly topic must have at least 5 articles",
        ):
            self._topic(article_count=4)

        with self.assertRaisesRegex(
            ValueError,
            "weekly topic must have at least 2 sources",
        ):
            self._topic(source_count=1)

        self.assertEqual(self.engine.events, [])

    def test_topic_rejects_too_many_summary_evidence_articles(self):
        """Summary 근거 기사가 5개를 초과하면 저장 전에 차단한다."""

        with self.assertRaisesRegex(
            ValueError,
            "at most 5 summary evidence",
        ):
            self._topic(article_count=6, summary_evidence_count=6)

        self.assertEqual(self.engine.events, [])

    def test_run_rejects_non_monday_week_start(self):
        """주간 시작일이 월요일이 아니면 run을 생성하지 않는다."""

        with self.assertRaisesRegex(
            ValueError,
            "week_start must be a Monday",
        ):
            WeeklyTopicRunStart(
                week_start=date(2026, 6, 16),
                week_end=date(2026, 6, 22),
                window_start=self.window_start,
                window_end=self.window_end,
                started_at=self.window_end,
            )

        self.assertEqual(self.engine.events, [])

    def test_completion_rejects_inconsistent_embedding_counts(self):
        """후보 수 관계가 맞지 않는 종료 통계가 DB에 기록되지 않게 한다."""

        with self.assertRaisesRegex(
            ValueError,
            "candidate_count must equal",
        ):
            WeeklyTopicRunCompletion(
                status="success",
                candidate_count=3,
                embedding_count=1,
                missing_embedding_count=1,
            )

        self.assertEqual(self.engine.events, [])

    def _topic(
        self,
        *,
        representative_is_evidence=True,
        article_count=5,
        source_count=3,
        summary_evidence_count=5,
    ):
        """고정 주간 window와 대표·지원 기사 관계를 가진 저장 Topic을 만든다."""

        return WeeklyTopicRecord(
            topic_candidate_id="cluster-1",
            week_start=self.week_start,
            week_end=self.week_end,
            window_start=self.window_start,
            window_end=self.window_end,
            title_ko="주간 주요 이슈",
            summary_ko="지난 월요일부터 일요일까지의 변화 흐름을 요약한다.",
            key_points=["초반 변화", "주중 진행", "주말 쟁점"],
            keywords=["정책", "시장"],
            confidence=0.8,
            source_count=source_count,
            status="ready",
            provider="deterministic",
            model="deterministic-v1",
            prompt_version="weekly-flow-v1",
            summary_input_hash="hash-1",
            articles=[
                WeeklyTopicArticleRecord(
                    article_id=100 + index,
                    rank=index,
                    similarity=1.0 - (index * 0.01),
                    is_representative=index == 1,
                    is_summary_evidence=(
                        representative_is_evidence
                        if index == 1
                        else index <= summary_evidence_count
                    ),
                )
                for index in range(1, article_count + 1)
            ],
        )


if __name__ == "__main__":
    unittest.main()
