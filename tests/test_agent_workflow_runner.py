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
from scripts.agent_workflow.runner import classify_failure, run_agent
from scripts.agent_workflow.state import load_state
from tests.test_agent_review_validation import complete_review
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
            self.assertEqual(data["adapter"], "stdin")
            self.assertTrue(data["automatic_execution_supported"])
            self.assertIsNone(data["failure_category"])

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
            self.assertEqual(result.failure_category, "nonzero_exit")

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
            self.assertEqual(result.failure_category, "timeout")
            self.assertTrue(result.manual_fallback_required)
            self.assertIn("started", (log_dir / "stdout.log").read_text())

    def test_external_log_directory_uses_absolute_path(self) -> None:
        """Repository 밖 로그 경로를 절대 경로로 저장하고 실행 결과를 보존한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-agent", "print('external log')\n"
            )
            external_root = root / "external-logs"
            log_dir = external_root / "run"
            result = run_agent(
                load_state(repo),
                "codex-implement",
                AgentCommand("Fake Codex", str(executable), "stdin"),
                "prompt",
                5,
                log_directory=log_dir,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.log_directory, str(log_dir.resolve()))
            data = json.loads((log_dir / "result.json").read_text())
            self.assertEqual(data["log_directory"], str(log_dir.resolve()))

    def test_classifies_known_antigravity_failures(self) -> None:
        """지원 client, 인증과 비대화형 실행 오류가 별도 category로 분류되는지 검증한다."""

        cases = (
            ("reasonCode: UNSUPPORTED_CLIENT", "unsupported_client"),
            ("Authentication required. Login required.", "authentication_failed"),
            ("This command requires a TTY.", "noninteractive_unsupported"),
        )
        for stderr, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    classify_failure(
                        exit_code=1,
                        timed_out=False,
                        stdout="",
                        stderr=stderr,
                    ),
                    expected,
                )

    def test_unsupported_client_result_recommends_manual_review(self) -> None:
        """UNSUPPORTED_CLIENT 실행 기록에 수동 fallback과 다음 action이 남는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-antigravity",
                "import sys\n"
                "print('reasonCode: UNSUPPORTED_CLIENT', file=sys.stderr)\n"
                "sys.exit(1)\n",
            )
            log_dir = repo / ".agent-runs" / "unsupported-client"
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=log_dir,
            )
            self.assertEqual(result.failure_category, "unsupported_client")
            self.assertTrue(result.manual_fallback_required)
            self.assertEqual(
                result.next_action,
                "scripts/agent_next_step.sh antigravity-review",
            )
            data = json.loads((log_dir / "result.json").read_text())
            self.assertEqual(data["review_file_validation"], "not_started")
            self.assertFalse(data["review_completed"])

    def test_successful_review_requires_new_valid_review_file(self) -> None:
        """exit code 0과 새 유효 review 파일을 함께 만족해야 완료로 기록한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review_text = repr(complete_review())
            executable = fake_executable(
                root / "fake-antigravity",
                "from pathlib import Path\n"
                f"Path('docs/reviews/feature-example-antigravity.md').write_text({review_text}, "
                "encoding='utf-8')\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "valid-review",
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIsNone(result.failure_category)
            self.assertEqual(result.review_file_validation, "completed")
            self.assertTrue(result.review_completed)
            self.assertFalse(result.manual_fallback_required)

    def test_successful_process_without_review_file_is_failure(self) -> None:
        """exit code 0이어도 review 파일이 생성되지 않으면 실패로 분류한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(root / "fake-antigravity", "print('done')\n")
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "missing-review",
            )
            self.assertEqual(result.failure_category, "review_file_missing")
            self.assertFalse(result.review_completed)

    def test_unchanged_or_invalid_review_file_is_failure(self) -> None:
        """기존 파일 미변경과 변경 후 검증 실패를 별도 failure category로 기록한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text(complete_review(), encoding="utf-8")
            no_change = fake_executable(root / "no-change", "print('done')\n")
            unchanged = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(no_change), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "unchanged-review",
            )
            self.assertEqual(unchanged.failure_category, "review_file_unchanged")

            invalid = fake_executable(
                root / "invalid",
                "from pathlib import Path\n"
                "Path('docs/reviews/feature-example-antigravity.md').write_text("
                "'# Review\\n\\n## Verdict\\n\\nPASS\\n', encoding='utf-8')\n",
            )
            invalid_result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(invalid), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "invalid-review",
            )
            self.assertEqual(
                invalid_result.failure_category,
                "review_file_validation_failed",
            )
            self.assertFalse(invalid_result.review_completed)

    def test_automatic_execution_unavailable_does_not_create_logs(self) -> None:
        """자동 실행 미지원 command가 process와 실행 로그를 만들지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            log_dir = repo / ".agent-runs" / "unavailable"
            command = AgentCommand(
                "Antigravity",
                None,
                "agy",
                automatic_execution_supported=False,
                failure_category="executable_missing",
                manual_fallback_required=True,
            )
            with self.assertRaises(ValueError):
                run_agent(
                    load_state(repo),
                    "antigravity-review",
                    command,
                    "prompt",
                    5,
                    log_directory=log_dir,
                )
            self.assertFalse(log_dir.exists())
