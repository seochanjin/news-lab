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
from scripts.agent_workflow.review_context import ReviewContext, build_review_context
from scripts.agent_workflow.review_unit_status import build_initial_review_unit_status
from scripts.agent_workflow.runner import (
    REVIEW_ACTIVE_ENV,
    build_agent_argv,
    classify_failure,
    run_agent,
)
from scripts.agent_workflow.state import load_state
from tests.test_agent_review_validation import complete_review
from tests.test_agent_workflow_state import make_repo


def fake_executable(path: Path, body: str) -> Path:
    """지정 본문을 실행하는 테스트용 Python executable을 만들고 경로를 반환한다."""

    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def complete_unit_response(unit_identifier: str = "UNIT-01") -> str:
    """Runner 통합 검증에 필요한 전체 UNIT Review 응답을 반환한다."""

    return f"""## UNIT Review: {unit_identifier}
### Review Scope
선택 UNIT 검토
### Requirement Coverage
충족
### Previous UNIT Contract Regression
- 없음
### Code Quality / Maintainability
양호
### Scope Control
범위 내
### Verification Evidence
테스트 확인
### Problems Found
- 없음
### Required Fixes Before Next UNIT
- 없음
### Verdict
- PASS
"""


def review_context(repo: Path) -> ReviewContext:
    """임시 repository의 첫 완료 UNIT을 대상으로 ReviewContext를 생성한다."""

    state = load_state(repo)
    return build_review_context(
        repo=repo,
        branch=state.branch,
        task=state.task,
        review_status=build_initial_review_unit_status(state.task),
        review_path=state.paths.review,
        verification_path=state.paths.verification,
    )


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

    def test_agy_print_argv_uses_sandbox_and_timeout(self) -> None:
        """agy adapter가 실제 CLI 계약대로 prompt를 --print 바로 뒤에 전달하는지 검증한다."""

        command = AgentCommand("Antigravity", "/tmp/agy", "agy-print")
        argv, stdin_text = build_agent_argv(
            command,
            Path("/tmp/repo"),
            "review prompt",
            45,
        )
        self.assertEqual(
            argv,
            [
                "/tmp/agy",
                "--print",
                "review prompt",
                "--sandbox",
                "--print-timeout",
                "45s",
            ],
        )
        self.assertIsNone(stdin_text)

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
                2,
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

    def test_successful_process_ignores_failure_markers(self) -> None:
        """정상 종료의 stdout·stderr 실패 marker를 failure category로 오분류하지 않는다."""

        cases = (
            ("The unsupported client issue was resolved.", ""),
            ("", "Authentication failed earlier; the user is now authenticated."),
            ("This no longer requires a TTY.", ""),
        )
        for stdout, stderr in cases:
            with self.subTest(stdout=stdout, stderr=stderr):
                self.assertIsNone(
                    classify_failure(
                        exit_code=0,
                        timed_out=False,
                        stdout=stdout,
                        stderr=stderr,
                    )
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
            self.assertEqual(data["review_file_validation"], "not_evaluated")
            self.assertFalse(data["review_completed"])

    def test_successful_review_validates_and_appends_response(self) -> None:
        """정상 Review stdout을 검증해 로그와 Review 파일에 append하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-antigravity",
                f"print({complete_unit_response()!r})\n",
            )
            context = review_context(repo)
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "valid-review",
                review_context=context,
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIsNone(result.failure_category)
            self.assertEqual(result.review_file_validation, "completed")
            self.assertIn(
                "## UNIT Review: UNIT-01",
                (
                    repo
                    / ".agent-runs"
                    / "valid-review"
                    / "response.md"
                ).read_text(encoding="utf-8"),
            )
            self.assertTrue(result.review_completed)
            self.assertFalse(result.manual_fallback_required)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            self.assertIn(
                "## UNIT Review: UNIT-01",
                review.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "- [x] UNIT-01: 완료",
                review.read_text(encoding="utf-8"),
            )

    def test_review_subprocess_receives_recursion_guard_environment(self) -> None:
        """Review Agent 하위 process에 재귀 실행 차단 환경변수가 전달된다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            executable = fake_executable(
                root / "fake-antigravity",
                "import os\n"
                f"assert os.environ[{REVIEW_ACTIVE_ENV!r}] == '1'\n"
                f"print({complete_unit_response()!r})\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "guard-env",
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 0)

    def test_execution_attempt_response_has_dedicated_failure_and_preserves_review(
        self,
    ) -> None:
        """실제 실패 문구를 전용 오류로 분류하고 writer 호출 없이 Review bytes를 보존한다."""

        attempted = (
            "I am running `scripts/agent_run.sh antigravity-review --yes` in the\n"
            "background to automatically run the Antigravity review process for "
            "the first\npending unit. I will wait for it to complete.\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
            before = review.read_bytes()
            executable = fake_executable(
                root / "attempted-execution",
                f"print({attempted!r})\n",
            )
            log_dir = repo / ".agent-runs" / "attempted-execution"
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=log_dir,
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(
                result.failure_category,
                "review_agent_attempted_execution",
            )
            self.assertIn("detected_phrase=i am running", result.review_file_validation)
            self.assertIn(
                "expected_heading=## UNIT Review: UNIT-01",
                result.review_file_validation,
            )
            self.assertIn("response.md", result.review_file_validation)
            self.assertIn("review_file_changed=no", result.review_file_validation)
            self.assertEqual(review.read_bytes(), before)

    def test_execution_intent_phrases_are_rejected(self) -> None:
        """실행·대기 의도 문구별로 전용 오류와 Review bytes 보존을 검증한다."""

        responses = {
            "i-will-run": "I will run `scripts/agent_run.sh antigravity-review` now.\n",
            "i-will-wait": "I will wait for it to complete.\n",
            "background": "The process is in the background.\n",
        }
        for name, response in responses.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                repo = make_repo(root)
                review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
                review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
                before = review.read_bytes()
                executable = fake_executable(
                    root / name,
                    f"print({response!r})\n",
                )
                result = run_agent(
                    load_state(repo),
                    "antigravity-review",
                    AgentCommand("Antigravity", str(executable), "test"),
                    "prompt",
                    5,
                    log_directory=repo / ".agent-runs" / name,
                    review_context=review_context(repo),
                )
                self.assertEqual(result.exit_code, 1)
                self.assertEqual(
                    result.failure_category,
                    "review_agent_attempted_execution",
                )
                self.assertFalse(result.review_completed)
                self.assertEqual(review.read_bytes(), before)

    def test_review_body_can_mention_antigravity_command_path(self) -> None:
        """정상 Review 본문이 검토 대상 명령 경로를 언급해도 실행 시도로 보지 않는다."""

        response = """## UNIT Review: UNIT-01
### Review Scope
- `scripts/agent_run.sh antigravity-review` 자동 실행 하네스 검증
### Requirement Coverage
자동 실행 경로 구현 완료
### Previous UNIT Contract Regression
- 없음
### Code Quality / Maintainability
양호
### Scope Control
범위 내
### Verification Evidence
pytest 324 passed, unittest 324 passed
### Problems Found
- 없음
### Required Fixes Before Next UNIT
- 없음
### Verdict
- PASS
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
            executable = fake_executable(
                root / "command-path-in-review",
                f"print({response!r})\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "command-path-in-review",
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 0)

    def test_review_body_can_quote_previous_execution_attempt_response(self) -> None:
        """Expected heading 뒤 Review 본문에 과거 실행 시도 문구가 있어도 허용한다."""

        response = """## UNIT Review: UNIT-01
### Review Scope
과거 실패 응답 인용: I am running `scripts/agent_run.sh antigravity-review`.
### Requirement Coverage
자동 실행 경로 구현 완료
### Previous UNIT Contract Regression
- 없음
### Code Quality / Maintainability
양호
### Scope Control
범위 내
### Verification Evidence
pytest 324 passed, unittest 324 passed
### Problems Found
- 없음
### Required Fixes Before Next UNIT
- 없음
### Verdict
- PASS
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            executable = fake_executable(
                root / "quoted-attempt-in-review",
                f"print({response!r})\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "quoted-attempt-in-review",
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 0)
            self.assertIsNone(result.failure_category)
            self.assertEqual(result.review_file_validation, "completed")
            self.assertTrue(result.review_completed)
            updated = review.read_text(encoding="utf-8")
            self.assertIn("`scripts/agent_run.sh antigravity-review`", updated)
            self.assertIn("- [x] UNIT-01: 완료", updated)

    def test_sandbox_user_request_response_is_rejected_and_preserves_review(self) -> None:
        """--sandbox가 prompt로 전달됐던 실제 실패 응답을 회귀 fixture로 검증한다."""

        actual_failure = "<USER_REQUEST>\n--sandbox\n</USER_REQUEST>\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
            before = review.read_bytes()
            executable = fake_executable(
                root / "sandbox-user-request",
                f"print({actual_failure!r})\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "sandbox-user-request",
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(result.failure_category, "review_response_invalid")
            self.assertFalse(result.review_completed)
            self.assertEqual(review.read_bytes(), before)

    def test_invalid_stdout_fails_without_review_file_write(self) -> None:
        """Process가 성공해도 잘못된 stdout이면 Review 파일을 만들지 않는다."""

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
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(result.failure_category, "review_response_invalid")
            self.assertFalse(result.review_completed)
            self.assertFalse(
                (repo / "docs" / "reviews" / "feature-example-antigravity.md").exists()
            )

    def test_invalid_response_does_not_rewrite_existing_review_file(self) -> None:
        """응답 검증 실패가 기존 Review 파일 내용을 변경하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text(complete_review(), encoding="utf-8")
            original = review.read_text(encoding="utf-8")
            no_change = fake_executable(root / "no-change", "print('done')\n")
            unchanged = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(no_change), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "unchanged-review",
                review_context=review_context(repo),
            )
            self.assertEqual(unchanged.failure_category, "review_response_invalid")
            self.assertEqual(review.read_text(encoding="utf-8"), original)

    def test_restores_review_file_modified_directly_by_agent(self) -> None:
        """Agent의 직접 Review 파일 변경을 복구하고 writer 성공으로 오인하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = make_repo(root)
            review = repo / "docs" / "reviews" / "feature-example-antigravity.md"
            review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
            before = review.read_bytes()
            executable = fake_executable(
                root / "file-writer",
                "from pathlib import Path\n"
                "Path('docs/reviews/feature-example-antigravity.md').write_text("
                "'# Rewritten\\n', encoding='utf-8')\n"
                f"print({complete_unit_response()!r})\n",
            )
            result = run_agent(
                load_state(repo),
                "antigravity-review",
                AgentCommand("Antigravity", str(executable), "test"),
                "prompt",
                5,
                log_directory=repo / ".agent-runs" / "direct-write",
                review_context=review_context(repo),
            )
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(
                result.failure_category,
                "review_file_modified_by_agent",
            )
            self.assertEqual(review.read_bytes(), before)

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
