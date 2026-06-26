"""다음 UNIT Review 대상 선택과 구조화된 Context 생성을 검증한다.

임시 Task와 mock Git 출력만 사용해 구현·Review 상태 대조, 마지막 UNIT 통합
mode, 상태 모순 차단, Task 계약과 제한된 diff 전달을 확인한다.
실제 Git repository, workflow 문서 또는 외부 Agent subprocess는 변경하지 않는다.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workflow.review_context import (
    ReviewContextError,
    build_review_context,
    select_next_review_target,
    select_final_review_target,
)
from scripts.agent_workflow.review_evidence import (
    ApprovedFix,
    ApprovedFixesSnapshot,
    ReviewEvidence,
    ReviewHistorySnapshot,
    VerificationSnapshot,
)
from scripts.agent_workflow.review_unit_status import ReviewUnit, ReviewUnitStatus
from scripts.agent_workflow.task_parser import parse_task


def write_task(root: Path, units: str) -> Path:
    """Context 필드 검증에 필요한 section과 UNIT을 가진 임시 Task를 생성한다."""

    path = root / "docs" / "tasks" / "task.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Task: Context 자동화\n\n"
        "## Scope\n\n선택 UNIT 관련 변경을 검토한다.\n\n"
        "## Do not change\n\nApplication과 DB를 변경하지 않는다.\n\n"
        "## Test commands\n\n`python -m pytest tests/test_agent_review_context.py`\n\n"
        "## Acceptance criteria\n\n다음 Review UNIT을 자동 선택한다.\n\n"
        "## Implementation Units\n\n"
        f"{units}\n",
        encoding="utf-8",
    )
    return path


def status(*items: tuple[str, str, bool]) -> ReviewUnitStatus:
    """테스트가 지정한 UNIT 목록으로 파일 쓰기 없는 Review 상태를 만든다."""

    return ReviewUnitStatus(
        units=tuple(
            ReviewUnit(identifier=identifier, title=title, reviewed=reviewed)
            for identifier, title, reviewed in items
        ),
        created=False,
    )


class ReviewTargetTests(unittest.TestCase):
    """Task 구현 상태와 Review 통과 상태의 조합별 대상 선택을 검증한다."""

    def test_selects_first_completed_unreviewed_unit(self) -> None:
        """앞선 Review 완료 UNIT을 건너뛰고 첫 구현 완료 미검토 UNIT을 선택한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: Parser\n"
                    "- [x] UNIT-02: Status\n"
                    "- [ ] UNIT-03: Context",
                )
            )
            target = select_next_review_target(
                task,
                status(
                    ("UNIT-01", "Parser", True),
                    ("UNIT-02", "Status", False),
                    ("UNIT-03", "Context", False),
                ),
            )
        self.assertEqual(target.unit.identifier, "UNIT-02")
        self.assertEqual(target.mode, "unit")
        self.assertEqual((target.position, target.total_units), (2, 3))

    def test_unit_action_keeps_last_unit_as_unit_review(self) -> None:
        """UNIT 전용 action은 마지막 UNIT도 통합으로 전환하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: Parser\n- [x] UNIT-02: Integration",
                )
            )
            target = select_next_review_target(
                task,
                status(
                    ("UNIT-01", "Parser", True),
                    ("UNIT-02", "Integration", False),
                ),
            )
        self.assertEqual(target.unit.identifier, "UNIT-02")
        self.assertEqual(target.mode, "unit")

    def test_rejects_reviewed_incomplete_unit(self) -> None:
        """Task 미완료 UNIT의 Review 완료 표시를 현재 상태 모순으로 거부한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: Parser\n- [ ] UNIT-02: Context",
                )
            )
            review_status = status(
                ("UNIT-01", "Parser", True),
                ("UNIT-02", "Context", True),
            )
            with self.assertRaisesRegex(ReviewContextError, "미완료 Task UNIT"):
                select_next_review_target(task, review_status)

    def test_rejects_out_of_order_review_completion(self) -> None:
        """앞 UNIT을 건너뛴 Review 완료 상태를 순서 모순으로 거부한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: Parser\n- [x] UNIT-02: Context",
                )
            )
            review_status = status(
                ("UNIT-01", "Parser", False),
                ("UNIT-02", "Context", True),
            )
            with self.assertRaisesRegex(ReviewContextError, "순서를 건너뛰었습니다"):
                select_next_review_target(task, review_status)

    def test_final_action_selects_integration_after_all_unit_reviews(self) -> None:
        """모든 UNIT Review 완료 뒤 최종 action이 Integration Review를 선택한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(root, "- [x] UNIT-01: Parser\n- [x] UNIT-02: Integration")
            )
            review = root / "review.md"
            evidence = ReviewEvidence(
                approved_fixes=ApprovedFixesSnapshot(fixes=()),
                verification=VerificationSnapshot(status="passed", latest_tests=()),
                review_history=ReviewHistorySnapshot((), 1),
            )
            target = select_final_review_target(
                task,
                status(
                    ("UNIT-01", "Parser", True),
                    ("UNIT-02", "Integration", True),
                ),
                evidence,
                review,
            )

        self.assertEqual(target.mode, "integration")
        self.assertEqual(target.unit.identifier, "UNIT-02")

    def test_final_action_rejects_pending_unit_review(self) -> None:
        """미검토 UNIT이 있으면 최종 action 대신 UNIT 전용 action을 요구한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(root, "- [x] UNIT-01: Parser\n- [x] UNIT-02: Integration")
            )
            evidence = ReviewEvidence(
                approved_fixes=ApprovedFixesSnapshot(fixes=()),
                verification=VerificationSnapshot(status="passed", latest_tests=()),
                review_history=ReviewHistorySnapshot((), 1),
            )
            with self.assertRaisesRegex(ReviewContextError, "antigravity-review-unit"):
                select_final_review_target(
                    task,
                    status(
                        ("UNIT-01", "Parser", True),
                        ("UNIT-02", "Integration", False),
                    ),
                    evidence,
                    root / "review.md",
                )

    def test_final_action_allows_re_review_with_only_human_verification_pending(self) -> None:
        """사람 검증 FIX만 pending이면 구현 FIX 적용 완료로 Re-review를 허용한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: Integration"))
            review = root / "review.md"
            review.write_text("## Integration Review: UNIT-01\n\n기록\n", encoding="utf-8")
            evidence = ReviewEvidence(
                approved_fixes=ApprovedFixesSnapshot(
                    fixes=(
                        ApprovedFix("FIX-01", "구현 수정", "applied"),
                        ApprovedFix(
                            "FIX-02",
                            "외부 실행 확인",
                            "approved",
                            "human-verification",
                        ),
                    )
                ),
                verification=VerificationSnapshot(status="passed", latest_tests=()),
                review_history=ReviewHistorySnapshot((1,), 2),
            )
            target = select_final_review_target(
                task,
                status(("UNIT-01", "Integration", True)),
                evidence,
                review,
            )

        self.assertEqual(target.mode, "re-review")
        self.assertEqual(target.re_review_number, 2)

    def test_final_action_blocks_pending_implementation_fix(self) -> None:
        """미적용 구현 FIX가 있으면 Re-review 진입을 차단한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: Integration"))
            review = root / "review.md"
            review.write_text("## Integration Review: UNIT-01\n\n기록\n", encoding="utf-8")
            evidence = ReviewEvidence(
                approved_fixes=ApprovedFixesSnapshot(
                    fixes=(ApprovedFix("FIX-01", "구현 수정", "approved"),)
                ),
                verification=VerificationSnapshot(status="passed", latest_tests=()),
                review_history=ReviewHistorySnapshot((), 1),
            )
            with self.assertRaisesRegex(ReviewContextError, "미적용 구현"):
                select_final_review_target(
                    task,
                    status(("UNIT-01", "Integration", True)),
                    evidence,
                    review,
                )

    @patch("scripts.agent_workflow.review_context.run_git")
    def test_selects_re_review_after_all_units_and_applied_fixes(
        self, run_git_mock
    ) -> None:
        """FIX 9개·최신 265 결과와 Re-review 2 이력에서 Re-review 3을 선택한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(root, "- [x] UNIT-01: Parser\n- [x] UNIT-02: 통합")
            )
            fixes = root / "fixes.md"
            fixes.write_text(
                "## Approved Fixes\n\n"
                + "\n".join(
                    f"- [x] FIX-{number:02d}: 적용 완료 {number}"
                    for number in range(1, 10)
                )
                + "\n",
                encoding="utf-8",
            )
            verification = root / "verification.md"
            verification.write_text(
                "## Verification Status\n\npassed\n\n"
                "### 1. 과거 전체 회귀\n\n"
                "Command:\n\n```bash\npython -m pytest\n```\n\n"
                "Result:\n\n- 261 passed\n\nStatus: passed\n\n"
                "### 2. 최신 전체 회귀\n\n"
                "Command:\n\n```bash\npython -m pytest\n```\n\n"
                "Result:\n\n- 265 passed\n\nStatus: passed\n",
                encoding="utf-8",
            )
            review = root / "review.md"
            review.write_text(
                "## Integration Review: UNIT-02\n\n기록\n\n"
                "## Re-review 1\n\n기록\n\n## Re-review 2\n\n기록\n",
                encoding="utf-8",
            )
            run_git_mock.side_effect = ["", "", ""]

            context = build_review_context(
                repo=root,
                branch="fix/context",
                task=task,
                review_status=status(
                    ("UNIT-01", "Parser", True),
                    ("UNIT-02", "통합", True),
                ),
                review_path=review,
                verification_path=verification,
                approved_fixes_path=fixes,
                action="antigravity-review",
            )

        self.assertEqual(context.target.mode, "re-review")
        self.assertEqual(context.target.re_review_number, 3)
        self.assertEqual(len(context.evidence.approved_fixes.applied), 9)
        self.assertEqual(context.evidence.verification.latest_passed_counts, (265,))


class ReviewContextBuilderTests(unittest.TestCase):
    """선택 대상과 repository evidence가 Context에 보존되는지 검증한다."""

    @patch("scripts.agent_workflow.review_context.run_git")
    def test_builds_structured_context_without_writing_files(self, run_git_mock) -> None:
        """Task 계약, 선행 UNIT, 최신 evidence와 Git 변경을 구조화해 반환한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(
                    root,
                    "- [x] UNIT-01: Parser 계약\n"
                    "- [x] UNIT-02: Context 생성\n"
                    "- [ ] UNIT-03: Prompt 생성",
                )
            )
            verification = root / "docs" / "verification" / "task.md"
            verification.parent.mkdir(parents=True)
            verification.write_text(
                "## Verification Status\n\npending\n\n62 passed\n",
                encoding="utf-8",
            )
            review = root / "docs" / "reviews" / "task-antigravity.md"
            run_git_mock.side_effect = [
                " M scripts/agent_workflow/review_context.py\n"
                "?? tests/test_agent_review_context.py",
                "diff --git a/file b/file\n+context\n",
                "",
            ]

            context = build_review_context(
                repo=root,
                branch="fix/context",
                task=task,
                review_status=status(
                    ("UNIT-01", "Parser 계약", True),
                    ("UNIT-02", "Context 생성", False),
                    ("UNIT-03", "Prompt 생성", False),
                ),
                review_path=review,
                verification_path=verification,
            )

        self.assertEqual(context.target.unit.identifier, "UNIT-02")
        self.assertEqual(
            [(unit.identifier, unit.title) for unit in context.previous_units],
            [("UNIT-01", "Parser 계약")],
        )
        self.assertEqual(
            context.changed_files,
            (
                "scripts/agent_workflow/review_context.py",
                "tests/test_agent_review_context.py",
            ),
        )
        self.assertIn("Application과 DB를 변경하지 않는다.", context.do_not_change)
        self.assertEqual(context.evidence.verification.status, "pending")
        self.assertIn("+context", context.git_diff)
        run_git_mock.assert_any_call(root.resolve(), "status", "--porcelain")
        run_git_mock.assert_any_call(
            root.resolve(), "diff", "--no-ext-diff", "HEAD", "--"
        )
        run_git_mock.assert_any_call(
            root.resolve(), "ls-files", "--others", "--exclude-standard"
        )

    @patch("scripts.agent_workflow.review_context.run_git")
    def test_includes_safe_untracked_text_and_omits_sensitive_content(
        self, run_git_mock
    ) -> None:
        """신규 text 구현은 diff에 넣고 민감 경로의 값은 노출하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: Context 생성"))
            review_status = status(("UNIT-01", "Context 생성", False))
            source = root / "new_module.py"
            source.write_text('"""새 모듈."""\n', encoding="utf-8")
            secret = root / ".env.local"
            secret.write_text("TOKEN=노출금지\n", encoding="utf-8")
            run_git_mock.side_effect = [
                "?? new_module.py\n?? .env.local",
                "",
                "new_module.py\n.env.local",
            ]

            context = build_review_context(
                repo=root,
                branch="fix/context",
                task=task,
                review_status=review_status,
                review_path=root / "review.md",
                verification_path=root / "verification.md",
            )

        self.assertIn("+++ b/new_module.py", context.git_diff)
        self.assertIn('+\u0022\u0022\u0022새 모듈.\u0022\u0022\u0022', context.git_diff)
        self.assertIn(".env.local (sensitive path)", context.git_diff)
        self.assertNotIn("TOKEN=노출금지", context.git_diff)

    @patch("scripts.agent_workflow.review_context.run_git")
    def test_excludes_document_diff_and_truncates_large_source_diff(
        self, run_git_mock
    ) -> None:
        """문서 전체 diff를 제외하고 큰 구현 diff에 파일별 상한을 적용한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: Context 생성"))
            large_body = "+" + ("x" * 20_000)
            run_git_mock.side_effect = [
                " M docs/task.md\n M scripts/review.py",
                "diff --git a/docs/task.md b/docs/task.md\n+문서 원문\n"
                "diff --git a/scripts/review.py b/scripts/review.py\n"
                f"{large_body}\n",
                "",
            ]

            context = build_review_context(
                repo=root,
                branch="fix/context",
                task=task,
                review_status=status(("UNIT-01", "Context 생성", False)),
                review_path=root / "review.md",
                verification_path=root / "verification.md",
            )

        self.assertNotIn("문서 원문", context.git_diff)
        self.assertIn("scripts/review.py", context.git_diff)
        self.assertIn("diff truncated by review context limit", context.git_diff)


if __name__ == "__main__":
    unittest.main()
