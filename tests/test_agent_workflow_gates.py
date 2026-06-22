"""Agent action 실행 전 workflow gate의 차단과 허용 조건을 검증한다.

임시 repository 상태만 사용하고 Agent executable 확인은 비활성화하여 실제
Codex, Gemini 또는 Antigravity를 실행하지 않는다.
"""

from pathlib import Path
import tempfile
import unittest

from scripts.agent_workflow.gates import GateError, validate_action
from scripts.agent_workflow.state import load_state
from tests.test_agent_workflow_state import make_repo


class WorkflowGateTests(unittest.TestCase):
    """Branch, Task, Approved Fixes와 Verification 관련 gate 회귀를 검증한다."""

    def test_master_blocks_codex_fix(self) -> None:
        """master branch에서 승인 Fix action이 차단되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory), branch="master")
            with self.assertRaises(GateError):
                validate_action(load_state(repo), "codex-fix", require_agent=False)

    def test_missing_task_is_reported(self) -> None:
        """현재 branch의 Task 문서가 없으면 상태 구성이 실패하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            (repo / "docs" / "tasks" / "feature-example.md").unlink()
            with self.assertRaises(FileNotFoundError):
                load_state(repo)

    def test_general_task_allows_codex_implement_without_agent_check(self) -> None:
        """필수 section이 있는 일반 Task가 구현 gate를 통과하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            task = repo / "docs" / "tasks" / "feature-example.md"
            task.write_text(
                "# Task: gate\n\n## Scope\n\n범위\n\n## Do not change\n\n없음\n\n"
                "## Test commands\n\n테스트\n\n## Acceptance criteria\n\n기준\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                validate_action(load_state(repo), "codex-implement", require_agent=False)
            )

    def test_unit_mode_rejects_general_task(self) -> None:
        """UNIT이 `없음`인 Task에서 UNIT action을 요청하면 차단되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            task = repo / "docs" / "tasks" / "feature-example.md"
            task.write_text(
                "# Task: gate\n\n## Scope\n\n범위\n\n## Do not change\n\n없음\n\n"
                "## Test commands\n\n테스트\n\n## Acceptance criteria\n\n기준\n"
                "\n## Implementation Units\n\n없음\n",
                encoding="utf-8",
            )
            with self.assertRaises(GateError):
                validate_action(
                    load_state(repo), "codex-implement-unit", require_agent=False
                )

    def test_fix_requires_approved_item(self) -> None:
        """Approved Fixes section이 비어 있으면 Fix action이 차단되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            fixes = repo / "docs" / "fixes" / "feature-example-approved-fixes.md"
            fixes.write_text("# Fixes\n\n## Approved Fixes\n\n", encoding="utf-8")
            with self.assertRaises(GateError):
                validate_action(load_state(repo), "codex-fix", require_agent=False)

    def test_review_rejects_explicit_failed_verification(self) -> None:
        """명시적 verification 실패가 남아 있으면 Review가 차단되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text(
                "# Verification\n\n## Verification Status\n\nfailed\n",
                encoding="utf-8",
            )
            with self.assertRaises(GateError):
                validate_action(
                    load_state(repo), "antigravity-review", require_agent=False
                )
