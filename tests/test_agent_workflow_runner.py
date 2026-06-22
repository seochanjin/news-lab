"""가짜 executable로 Agent runner의 실행 결과와 로그 보존을 검증한다.

정상 종료, 비정상 종료와 timeout을 임시 subprocess로 재현하며 실제 Codex,
Gemini 또는 Antigravity CLI는 호출하지 않는다.
"""

import json
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.agent_workflow.gates import AgentCommand
from scripts.agent_workflow.runner import run_agent
from scripts.agent_workflow.state import load_state
from tests.test_agent_workflow_state import make_repo


def fake_executable(path: Path, body: str) -> Path:
    """지정 본문을 실행하는 테스트용 Python executable을 만들고 경로를 반환한다."""

    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class WorkflowRunnerTests(unittest.TestCase):
    """Runner의 종료 코드, timeout과 실행 증거 저장 동작을 검증한다."""

    def test_saves_stdout_stderr_and_result(self) -> None:
        """정상 실행의 prompt, stdout, stderr와 result JSON이 저장되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-agent",
                "import sys\n"
                "prompt = sys.stdin.read()\n"
                "print('OUT:' + prompt[:4])\n"
                "print('ERR', file=sys.stderr)\n",
            )
            log_dir = repo / ".agent-runs" / "test-run"
            result = run_agent(
                load_state(repo),
                "codex-implement",
                AgentCommand("Fake Codex", str(executable), "stdin"),
                "prompt",
                5,
                log_directory=log_dir,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(result.timed_out)
            self.assertIn("OUT:prom", (log_dir / "stdout.log").read_text())
            self.assertIn("ERR", (log_dir / "stderr.log").read_text())
            data = json.loads((log_dir / "result.json").read_text())
            self.assertEqual(data["exit_code"], 0)
            self.assertFalse(data["timed_out"])

    def test_preserves_nonzero_exit(self) -> None:
        """Agent의 비정상 종료 코드를 성공으로 바꾸지 않고 보존하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-agent", "import sys\nsys.exit(7)\n"
            )
            result = run_agent(
                load_state(repo),
                "codex-implement",
                AgentCommand("Fake Codex", str(executable), "stdin"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "nonzero",
            )
            self.assertEqual(result.exit_code, 7)

    def test_timeout_returns_124_and_keeps_logs(self) -> None:
        """Timeout 시 exit code 124와 timeout 전 stdout이 보존되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-agent",
                "import time\nprint('started', flush=True)\ntime.sleep(10)\n",
            )
            log_dir = repo / ".agent-runs" / "timeout"
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Fake Antigravity", str(executable), "stdin"),
                "prompt",
                1,
                log_directory=log_dir,
            )
            self.assertEqual(result.exit_code, 124)
            self.assertTrue(result.timed_out)
            self.assertIn("started", (log_dir / "stdout.log").read_text())
