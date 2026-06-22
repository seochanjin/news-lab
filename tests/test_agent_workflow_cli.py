"""Agent workflow CLI의 읽기 전용 status, preview와 branch gate를 검증한다.

임시 repository와 가짜 executable을 사용하며 preview가 실제 Agent 실행이나
로그 파일 생성을 일으키지 않는지 확인한다.
"""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workflow.cli import main
from tests.test_agent_workflow_state import make_repo


class WorkflowCliTests(unittest.TestCase):
    """사용자-facing CLI action의 안전한 제어 흐름을 검증한다."""

    def test_status_is_read_only(self) -> None:
        """status 실행 전후 repository 파일 내용이 동일한지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            before = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file() and ".git" not in path.parts
            }
            output = io.StringIO()
            with patch("pathlib.Path.cwd", return_value=repo), redirect_stdout(output):
                exit_code = main(["status"])
            after = {
                path.relative_to(repo): path.read_bytes()
                for path in repo.rglob("*")
                if path.is_file() and ".git" not in path.parts
            }
            self.assertEqual(exit_code, 0)
            self.assertEqual(before, after)
            self.assertIn("Suggested next action:", output.getvalue())

    def test_preview_does_not_run_fake_agent_or_create_logs(self) -> None:
        """preview가 가짜 Agent를 실행하거나 `.agent-runs`를 만들지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            task = repo / "docs" / "tasks" / "feature-example.md"
            task.write_text(
                "# Task: preview\n\n## Scope\n\n범위\n\n## Do not change\n\n없음\n\n"
                "## Test commands\n\n테스트\n\n## Acceptance criteria\n\n기준\n",
                encoding="utf-8",
            )
            marker = root / "executed"
            executable = root / "fake-codex"
            executable.write_text(
                f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8"
            )
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            output = io.StringIO()
            env = {**os.environ, "AGENT_CODEX_BIN": str(executable)}
            with (
                patch("pathlib.Path.cwd", return_value=repo),
                patch.dict(os.environ, env, clear=True),
                redirect_stdout(output),
            ):
                exit_code = main(["codex-implement", "--preview"])
            self.assertEqual(exit_code, 0)
            self.assertFalse(marker.exists())
            self.assertFalse((repo / ".agent-runs").exists())
            self.assertIn("Target Agent: Codex", output.getvalue())

    def test_main_branch_implementation_is_blocked(self) -> None:
        """main branch 구현 요청이 Task parsing 전에 차단되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory), branch="main")
            error = io.StringIO()
            with (
                patch("pathlib.Path.cwd", return_value=repo),
                redirect_stderr(error),
            ):
                exit_code = main(["codex-implement", "--preview"])
            self.assertEqual(exit_code, 2)
            self.assertIn("main branch", error.getvalue())
