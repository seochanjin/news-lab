"""임시 Git repository에서 workflow 상태 판정과 status 출력을 검증한다.

테스트 fixture는 로컬 임시 경로에 Git repository와 workflow 문서를 만들며
실제 NewsLab repository, network 또는 외부 Agent에는 영향을 주지 않는다.
"""

from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.agent_workflow.state import (
    format_status,
    load_state,
    main_pointer_matches,
    safe_branch_name,
)
from tests.test_agent_review_validation import complete_review


def git(repo: Path, *args: str) -> None:
    """임시 fixture repository에서 테스트 준비용 Git 명령을 실행한다."""

    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(tmp_path: Path, branch: str = "feature/example") -> Path:
    """필수 workflow 문서를 갖춘 임시 Git repository를 생성해 반환한다."""

    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "seed").write_text("seed", encoding="utf-8")
    git(repo, "add", "seed")
    git(repo, "commit", "-m", "seed")
    current = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current != branch:
        git(repo, "switch", "-c", branch)
    safe = safe_branch_name(branch)
    (repo / "docs" / "tasks").mkdir(parents=True)
    (repo / "docs" / "verification").mkdir(parents=True)
    (repo / "docs" / "reviews").mkdir(parents=True)
    (repo / "docs" / "fixes").mkdir(parents=True)
    (repo / "docs" / "agent").mkdir(parents=True)
    (repo / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    for name in (
        "backend-workflow.md",
        "verification-gates.md",
        "forbidden-commands.md",
        "codex-instructions.md",
        "antigravity-review.md",
    ):
        (repo / "docs" / "agent" / name).write_text(f"# {name}\n", encoding="utf-8")
    (repo / "docs" / "tasks" / f"{safe}.md").write_text(
        "# Task: 상태 테스트\n\n## Goal\n\n테스트\n\n## Scope\n\n범위\n\n"
        "## Do not change\n\n없음\n\n## Test commands\n\n테스트\n\n"
        "## Acceptance criteria\n\n기준\n\n## Implementation Units\n\n"
        "- [x] UNIT-01: 완료\n- [ ] UNIT-02: 현재\n",
        encoding="utf-8",
    )
    (repo / "docs" / "tasks" / "main.md").write_text(
        f"[current]({safe}.md)\n", encoding="utf-8"
    )
    return repo


class WorkflowStateTests(unittest.TestCase):
    """현재 branch의 Task 경로, UNIT 상태와 main pointer 판정을 검증한다."""

    def test_loads_branch_paths_and_status(self) -> None:
        """UNIT Task 상태와 사람이 읽는 status 문자열이 일치하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            state = load_state(make_repo(Path(directory)))
            self.assertEqual(state.branch, "feature/example")
            self.assertIsNotNone(state.task.current_unit)
            self.assertEqual(state.task.current_unit.identifier, "UNIT-02")
            self.assertTrue(main_pointer_matches(state))
            output = format_status(state)
        self.assertIn("Execution mode:\n- unit", output)
        self.assertIn("UNIT-02: 현재", output)

    def test_main_pointer_must_reference_current_task(self) -> None:
        """main.md가 다른 Task를 가리키면 pointer gate가 실패하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            (repo / "docs" / "tasks" / "main.md").write_text(
                "[wrong](other.md)\n", encoding="utf-8"
            )
            self.assertFalse(main_pointer_matches(load_state(repo)))

    def test_main_pointer_accepts_exact_markdown_link_target(self) -> None:
        """현재 Task의 정확한 Markdown link target만 정상 pointer로 인정한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            self.assertTrue(main_pointer_matches(load_state(repo)))

    def test_main_pointer_rejects_task_name_in_plain_text(self) -> None:
        """본문 설명에 Task 파일명만 있어도 pointer로 오인하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            (repo / "docs" / "tasks" / "main.md").write_text(
                "현재 파일은 feature-example.md를 설명한다.\n", encoding="utf-8"
            )
            self.assertFalse(main_pointer_matches(load_state(repo)))

    def test_main_pointer_rejects_task_link_in_code_example(self) -> None:
        """fenced code 예시 안의 정상 Task link를 실제 pointer로 인정하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            (repo / "docs" / "tasks" / "main.md").write_text(
                "```markdown\n[current](feature-example.md)\n```\n",
                encoding="utf-8",
            )
            self.assertFalse(main_pointer_matches(load_state(repo)))

    def test_historical_failed_text_does_not_mark_verification_failed(self) -> None:
        """과거 Status: failed 설명이 현재 Verification 실패로 오인되지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text(
                "# Verification\n\n과거 `Status: failed` 기록은 이후 검증으로 superseded되었다.\n",
                encoding="utf-8",
            )
            self.assertEqual(load_state(repo).verification_status, "present")

    def test_failed_example_in_code_fence_is_ignored(self) -> None:
        """예제 code block의 status: failed가 현재 상태에 영향을 주지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text(
                "# Verification\n\n```text\nstatus: failed\n```\n",
                encoding="utf-8",
            )
            self.assertEqual(load_state(repo).verification_status, "present")

    def test_explicit_verification_status_values(self) -> None:
        """passed, failed와 pending 명시 상태를 각각 그대로 판정하는지 검증한다."""

        for expected in ("passed", "failed", "pending"):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                repo = make_repo(Path(directory))
                verification = repo / "docs" / "verification" / "feature-example.md"
                verification.write_text(
                    f"# Verification\n\n## Verification Status\n\n{expected}\n",
                    encoding="utf-8",
                )
                self.assertEqual(load_state(repo).verification_status, expected)

    def test_verification_without_status_section_is_present(self) -> None:
        """기존 Verification 문서에 상태 section이 없으면 present로 호환되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text("# Verification\n\n기존 기록\n", encoding="utf-8")
            self.assertEqual(load_state(repo).verification_status, "present")

    def test_missing_verification_is_reported(self) -> None:
        """Verification 문서가 없으면 missing 상태로 판정하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            self.assertEqual(load_state(repo).verification_status, "missing")

    def test_passed_reviewed_applied_state_suggests_pr_draft(self) -> None:
        """검증·Review·Fix 적용이 끝난 상태에서 PR 초안을 권장하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            safe = "feature-example"
            (repo / "docs" / "verification" / f"{safe}.md").write_text(
                "# Verification\n\n## Verification Status\n\npassed\n",
                encoding="utf-8",
            )
            (repo / "docs" / "reviews" / f"{safe}-antigravity.md").write_text(
                complete_review(), encoding="utf-8"
            )
            (repo / "docs" / "fixes" / f"{safe}-approved-fixes.md").write_text(
                "# Fixes\n\n## Approved Fixes\n\n- [x] FIX-01\n", encoding="utf-8"
            )
            self.assertEqual(load_state(repo).suggested_action, "pr-draft")

    def test_failed_reviewed_state_requires_verification_resolution(self) -> None:
        """Review 후 Verification 실패 상태에서는 재Review 대신 검증 해결을 안내한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            safe = "feature-example"
            (repo / "docs" / "verification" / f"{safe}.md").write_text(
                "# Verification\n\n## Verification Status\n\nfailed\n",
                encoding="utf-8",
            )
            (repo / "docs" / "reviews" / f"{safe}-antigravity.md").write_text(
                complete_review("CHANGES REQUIRED"), encoding="utf-8"
            )
            state = load_state(repo)
            self.assertEqual(state.suggested_action, "resolve-verification")
            self.assertIn("먼저 검증 문제를 해결", format_status(state))

    def test_pending_reviewed_state_requires_verification_resolution(self) -> None:
        """Review 후 Verification pending 상태에서는 실행 가능한 해결 안내를 출력한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            safe = "feature-example"
            (repo / "docs" / "verification" / f"{safe}.md").write_text(
                "# Verification\n\n## Verification Status\n\npending\n",
                encoding="utf-8",
            )
            (repo / "docs" / "reviews" / f"{safe}-antigravity.md").write_text(
                complete_review(), encoding="utf-8"
            )
            self.assertEqual(load_state(repo).suggested_action, "resolve-verification")

    def test_template_review_requires_manual_write_without_advancing(self) -> None:
        """초기 템플릿을 review 완료로 오인하지 않고 수동 작성 action을 제안한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text(
                "# Review\n\n## Review Summary\n\n## Problems Found\n\n## Verdict\n",
                encoding="utf-8",
            )
            state = load_state(repo)
            output = format_status(state)
            self.assertEqual(state.review_status, "template only")
            self.assertTrue(state.manual_review_required)
            self.assertEqual(state.suggested_action, "antigravity-review-write")
            self.assertIn("Automatic review:\n- unavailable", output)
            self.assertIn("Manual review required:\n- yes", output)

    def test_completed_manual_review_can_reach_pr_draft(self) -> None:
        """자동 실행 기록 없이도 유효한 수동 review가 완료로 판정되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            safe = "feature-example"
            (repo / "docs" / "verification" / f"{safe}.md").write_text(
                "# Verification\n\n## Verification Status\n\npassed\n",
                encoding="utf-8",
            )
            (repo / "docs" / "reviews" / f"{safe}-antigravity.md").write_text(
                complete_review(), encoding="utf-8"
            )
            state = load_state(repo)
            self.assertEqual(state.review_status, "completed")
            self.assertFalse(state.manual_review_required)
            self.assertEqual(state.suggested_action, "pr-draft")

    def test_failed_automatic_review_log_blocks_fix_and_pr_progression(self) -> None:
        """자동 review 실패와 미완성 파일 상태에서 fix 또는 PR을 제안하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            safe = "feature-example"
            review = repo / "docs" / "reviews" / f"{safe}-antigravity.md"
            review.write_text("# Review\n\n## Review Summary\n", encoding="utf-8")
            log_dir = (
                repo
                / ".agent-runs"
                / safe
                / "20260623T120000-antigravity-review"
            )
            log_dir.mkdir(parents=True)
            (log_dir / "result.json").write_text(
                '{"automatic_execution_supported": true, "exit_code": 1, '
                '"failure_category": "unsupported_client", '
                '"review_completed": false}\n',
                encoding="utf-8",
            )
            state = load_state(repo)
            self.assertEqual(state.review_execution_status, "failed")
            self.assertEqual(state.review_failure_category, "unsupported_client")
            self.assertNotIn(state.suggested_action, {"codex-fix", "pr-draft"})


if __name__ == "__main__":
    unittest.main()
