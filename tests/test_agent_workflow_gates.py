"""Agent action 실행 전 workflow gate의 차단과 허용 조건을 검증한다.

임시 repository 상태와 PATH mock만 사용해 Codex 및 Antigravity 탐지 계약을
검증하며 실제 외부 Agent를 실행하지 않는다.
"""

from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workflow.gates import GateError, resolve_agent, validate_action
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

    def test_unit_review_accepts_pending_verification(self) -> None:
        """UNIT Task는 전체 Verification pending 중에도 완료 UNIT Review를 허용한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text(
                "# Verification\n\n## Verification Status\n\npending\n",
                encoding="utf-8",
            )
            self.assertIsNone(
                validate_action(
                    load_state(repo), "antigravity-review-unit", require_agent=False
                )
            )

    def test_general_review_rejects_pending_verification(self) -> None:
        """일반 Task의 Verification pending 상태는 기존처럼 Review를 차단한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            task = repo / "docs" / "tasks" / "feature-example.md"
            task.write_text(
                "# Task: gate\n\n## Scope\n\n범위\n\n## Do not change\n\n없음\n\n"
                "## Test commands\n\n테스트\n\n## Acceptance criteria\n\n기준\n",
                encoding="utf-8",
            )
            verification = repo / "docs" / "verification" / "feature-example.md"
            verification.write_text(
                "# Verification\n\n## Verification Status\n\npending\n",
                encoding="utf-8",
            )
            with self.assertRaises(GateError):
                validate_action(
                    load_state(repo), "antigravity-review", require_agent=False
                )

    def test_configured_codex_executable_is_accepted(self) -> None:
        """실행 가능한 AGENT_CODEX_BIN 파일을 정상 Agent command로 해석한다."""

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "fake-codex"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            command = resolve_agent(
                "codex-implement", {"AGENT_CODEX_BIN": str(executable)}
            )
            self.assertEqual(command.executable, str(executable.resolve()))

    def test_configured_agent_binary_rejects_invalid_paths(self) -> None:
        """잘못된 Antigravity binary 설정을 executable 미설치 상태로 분류한다."""

        with tempfile.TemporaryDirectory() as directory:
            for value in (str(Path(directory) / "missing"), directory):
                with self.subTest(value=value):
                    command = resolve_agent(
                        "antigravity-review",
                        {"AGENT_ANTIGRAVITY_BIN": value},
                    )
                self.assertIsNone(command.executable)
                self.assertEqual(command.failure_category, "executable_missing")
                self.assertTrue(command.manual_fallback_required)

    def test_configured_agent_command_name_uses_path_lookup(self) -> None:
        """환경변수에 command 이름을 지정하면 PATH에서 실행 파일을 찾는지 검증한다."""

        command = resolve_agent("codex-implement", {"AGENT_CODEX_BIN": "sh"})
        self.assertTrue(Path(command.executable).is_file())

    def test_gemini_is_not_selected_as_antigravity_adapter(self) -> None:
        """PATH에 Gemini만 있어도 Antigravity 자동 실행 가능으로 판정하지 않는다."""

        def which(name: str) -> str | None:
            return "/tmp/gemini" if name == "gemini" else None

        with patch("scripts.agent_workflow.gates.shutil.which", side_effect=which):
            command = resolve_agent("antigravity-review")
        self.assertEqual(command.agent, "Antigravity")
        self.assertEqual(command.adapter, "agy-print")
        self.assertIsNone(command.executable)
        self.assertFalse(command.automatic_execution_supported)
        self.assertEqual(command.failure_category, "executable_missing")

    def test_agy_installation_enables_print_adapter(self) -> None:
        """설치된 agy가 sandbox 단일 prompt 자동 adapter로 선택되는지 검증한다."""

        with patch(
            "scripts.agent_workflow.gates.shutil.which",
            return_value="/tmp/agy",
        ):
            command = resolve_agent("antigravity-review")
        self.assertEqual(command.executable, "/tmp/agy")
        self.assertEqual(command.adapter, "agy-print")
        self.assertTrue(command.automatic_execution_supported)
        self.assertIsNone(command.failure_category)
        self.assertFalse(command.manual_fallback_required)
