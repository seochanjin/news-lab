"""선택한 Agent subprocess를 실행하고 실행 증거를 로컬 로그로 보존한다.

WorkflowState, Agent command, prompt와 timeout을 입력받아 process를 실행하고
prompt, stdout, stderr, result JSON 및 RunResult를 생성한다. 실행 결과에서
지원되지 않는 client, 인증, 비대화형 실행, timeout과 일반 non-zero 실패를
분류한다. Task, Verification 또는 review 문서는 자동으로 변경하지 않는다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from .gates import AgentCommand
from .review_validation import validate_review_file
from .state import WorkflowState


@dataclass(frozen=True)
class RunResult:
    """Agent 실행의 adapter, 실패 분류, 종료 상태와 로그 위치를 보관한다."""

    action: str
    agent: str
    adapter: str
    executable: str | None
    automatic_execution_supported: bool
    branch: str
    task_path: str
    execution_mode: str
    current_unit: str | None
    exit_code: int
    duration_seconds: float
    timed_out: bool
    failure_category: str | None
    manual_fallback_required: bool
    review_file_validation: str
    review_completed: bool
    next_action: str | None
    log_directory: str
    started_at: str


def planned_log_directory(state: WorkflowState, action: str, now: datetime | None = None) -> Path:
    """현재 시각과 action으로 아직 생성하지 않은 실행 로그 경로를 계산한다."""

    timestamp = (now or datetime.now()).strftime("%Y%m%dT%H%M%S%f")
    return state.repo / ".agent-runs" / state.safe_branch / f"{timestamp}-{action}"


def build_agent_argv(
    command: AgentCommand, repo: Path, prompt: str
) -> tuple[list[str], str | None]:
    """Agent adapter에 맞는 인자 배열과 선택적 stdin prompt를 반환한다.

    shell 문자열을 만들지 않으며 subprocess를 실행하지 않는다.
    """

    if not command.automatic_execution_supported or not command.executable:
        raise ValueError("자동 실행이 지원되지 않는 Agent command입니다.")
    if command.adapter == "codex":
        return [command.executable, "exec", "-C", str(repo), "-"], prompt
    return [command.executable], prompt


def classify_failure(
    *, exit_code: int, timed_out: bool, stdout: str, stderr: str
) -> str | None:
    """Process 결과를 workflow가 사용하는 failure category로 변환한다.

    timeout을 최우선으로 처리하고 stdout과 stderr의 진단 문구에서 지원되지
    않는 client, 인증 실패와 비대화형 실행 미지원을 판별한다. 알려진 패턴이
    없는 비정상 종료는 `nonzero_exit`, 정상 종료는 None을 반환한다.
    """

    if timed_out:
        return "timeout"
    combined = f"{stdout}\n{stderr}".lower()
    if "unsupported_client" in combined or "unsupported client" in combined:
        return "unsupported_client"
    authentication_markers = (
        "authentication failed",
        "authentication required",
        "not authenticated",
        "unauthorized",
        "login required",
        "invalid credential",
    )
    if any(marker in combined for marker in authentication_markers):
        return "authentication_failed"
    noninteractive_markers = (
        "non-interactive mode is not supported",
        "noninteractive mode is not supported",
        "requires an interactive terminal",
        "requires a tty",
    )
    if any(marker in combined for marker in noninteractive_markers):
        return "noninteractive_unsupported"
    if exit_code != 0:
        return "nonzero_exit"
    return None


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    """Timeout된 subprocess group에 SIGTERM 후 필요하면 SIGKILL을 전송한다."""

    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _serialized_log_directory(log_dir: Path, repo: Path) -> str:
    """로그 경로를 repository 내부 상대 경로 또는 외부 절대 경로로 직렬화한다.

    경로가 repository 밖에 있어도 relative_to 예외를 외부로 전파하지 않아
    Agent 실행 결과 저장이 실패하지 않게 한다. 파일을 생성하거나 변경하지 않는다.
    """

    normalized_log = log_dir.resolve()
    normalized_repo = repo.resolve()
    try:
        return str(normalized_log.relative_to(normalized_repo))
    except ValueError:
        return str(normalized_log)


def run_agent(
    state: WorkflowState,
    action: str,
    command: AgentCommand,
    prompt: str,
    timeout: int,
    *,
    log_directory: Path | None = None,
) -> RunResult:
    """Agent를 실행하고 prompt, 출력과 결과 metadata를 로그 디렉터리에 저장한다.

    로그 경로가 이미 존재하면 FileExistsError가 발생할 수 있다. 자동 실행
    미지원 command는 로그 디렉터리를 만들기 전에 ValueError로 차단한다.
    Timeout은 process group을 종료하고 exit code 124로 기록하며, 비정상 종료
    코드는 그대로 보존한다.
    """

    if not command.automatic_execution_supported or not command.executable:
        raise ValueError("자동 실행이 지원되지 않아 Agent process를 시작하지 않습니다.")

    is_review = action == "antigravity-review"
    review_before = (
        state.paths.review.read_bytes() if is_review and state.paths.review.exists() else None
    )
    log_dir = log_directory or planned_log_directory(state, action)
    log_dir.mkdir(parents=True, exist_ok=False)
    (log_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    argv, stdin_text = build_agent_argv(command, state.repo, prompt)
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=state.repo,
        stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=stdin_text, timeout=timeout)
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
        stdout, stderr = process.communicate()
        exit_code = 124

    duration = round(time.monotonic() - started, 3)
    (log_dir / "stdout.log").write_text(stdout or "", encoding="utf-8")
    (log_dir / "stderr.log").write_text(stderr or "", encoding="utf-8")
    failure_category = classify_failure(
        exit_code=exit_code,
        timed_out=timed_out,
        stdout=stdout or "",
        stderr=stderr or "",
    )
    review_file_validation = "not_evaluated"
    review_completed = False
    if is_review:
        validation = validate_review_file(state.paths.review)
        review_file_validation = validation.status
        review_after = (
            state.paths.review.read_bytes() if state.paths.review.exists() else None
        )
        if failure_category is None:
            if review_after is None:
                failure_category = "review_file_missing"
            elif review_after == review_before:
                failure_category = "review_file_unchanged"
            elif not validation.completed:
                failure_category = "review_file_validation_failed"
            else:
                review_completed = True
    manual_fallback_required = is_review and not review_completed
    next_action = (
        "scripts/agent_next_step.sh antigravity-review"
        if manual_fallback_required
        else None
    )
    unit = state.task.current_unit
    result = RunResult(
        action=action,
        agent=command.agent,
        adapter=command.adapter,
        executable=command.executable,
        automatic_execution_supported=command.automatic_execution_supported,
        branch=state.branch,
        task_path=str(state.paths.task.relative_to(state.repo)),
        execution_mode="unit" if action == "codex-implement-unit" else "general",
        current_unit=f"{unit.identifier}: {unit.title}" if unit and action == "codex-implement-unit" else None,
        exit_code=exit_code,
        duration_seconds=duration,
        timed_out=timed_out,
        failure_category=failure_category,
        manual_fallback_required=manual_fallback_required,
        review_file_validation=review_file_validation,
        review_completed=review_completed,
        next_action=next_action,
        log_directory=_serialized_log_directory(log_dir, state.repo),
        started_at=started_at.isoformat(),
    )
    (log_dir / "result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
