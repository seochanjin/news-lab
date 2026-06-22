"""선택한 Agent subprocess를 실행하고 실행 증거를 로컬 로그로 보존한다.

WorkflowState, Agent command, prompt와 timeout을 입력받아 process를 실행하고
prompt, stdout, stderr, result JSON 및 RunResult를 생성한다. Timeout 시 process
group을 종료하지만 Task나 Verification 문서를 자동으로 변경하지 않는다.
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
from .state import WorkflowState


@dataclass(frozen=True)
class RunResult:
    """Agent 실행의 action, 대상, 종료 상태, 시간과 로그 위치를 보관한다."""

    action: str
    agent: str
    branch: str
    task_path: str
    execution_mode: str
    current_unit: str | None
    exit_code: int
    duration_seconds: float
    timed_out: bool
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

    if command.adapter == "codex":
        return [command.executable, "exec", "-C", str(repo), "-"], prompt
    if command.adapter == "gemini":
        return [
            command.executable,
            "--prompt",
            prompt,
            "--approval-mode",
            "auto_edit",
        ], None
    return [command.executable], prompt


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

    로그 경로가 이미 존재하면 FileExistsError가 발생할 수 있다. Timeout은
    process group을 종료하고 exit code 124로 기록하며, 비정상 종료 코드는
    그대로 보존한다.
    """

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
    unit = state.task.current_unit
    result = RunResult(
        action=action,
        agent=command.agent,
        branch=state.branch,
        task_path=str(state.paths.task.relative_to(state.repo)),
        execution_mode="unit" if action == "codex-implement-unit" else "general",
        current_unit=f"{unit.identifier}: {unit.title}" if unit and action == "codex-implement-unit" else None,
        exit_code=exit_code,
        duration_seconds=duration,
        timed_out=timed_out,
        log_directory=_serialized_log_directory(log_dir, state.repo),
        started_at=started_at.isoformat(),
    )
    (log_dir / "result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result
