"""Agent action 실행 전에 필요한 안전 조건을 검사한다.

WorkflowState와 action을 입력받아 branch, Task section, workflow 문서,
Approved Fixes와 Agent CLI 가용성을 검증한다. Agent 표시 이름, 실제 adapter,
실행 파일과 자동 실행 지원 상태를 분리해 반환하지만 Agent subprocess나 파일
변경은 직접 수행하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from .state import WorkflowState, main_pointer_matches
from .task_parser import TaskParseError


class GateError(RuntimeError):
    """요청한 Agent action이 안전 조건을 충족하지 못했음을 나타낸다."""


@dataclass(frozen=True)
class AgentCommand:
    """실행 대상 Agent의 표시 정보와 자동 실행 가능 상태를 보관한다.

    executable은 설치된 후보 경로이며 자동 실행 지원을 뜻하지 않는다.
    automatic_execution_supported가 거짓이면 runner가 subprocess를 시작해서는
    안 되며, failure_category와 next_action은 수동 fallback 안내에 사용한다.
    """

    agent: str
    executable: str | None
    adapter: str
    automatic_execution_supported: bool = True
    failure_category: str | None = None
    manual_fallback_required: bool = False
    next_action: str | None = None


REQUIRED_TASK_SECTIONS = ("Scope", "Do not change", "Test commands", "Acceptance criteria")
REVIEW_ACTIONS = {"antigravity-review-unit", "antigravity-review"}


def _configured_executable(value: str, label: str) -> str:
    """환경변수의 binary 경로 또는 command 이름을 안전하게 검증한다.

    Slash가 포함된 값은 실행 가능한 일반 파일인지 확인하고 command 이름은
    PATH에서 검색한다. 검증 실패 시 환경변수 값을 노출하지 않는 GateError를
    발생시키며 executable을 실행하지 않는다.
    """

    if "/" in value:
        candidate = Path(value).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    else:
        resolved = shutil.which(value)
        if resolved and Path(resolved).is_file() and os.access(resolved, os.X_OK):
            return resolved
    raise GateError(f"{label}에 지정된 Agent binary가 존재하지 않거나 실행할 수 없습니다.")


def resolve_agent(action: str, env: dict[str, str] | None = None) -> AgentCommand:
    """Action과 환경 설정에 맞는 Agent executable 및 지원 상태를 찾는다.

    Codex는 기존처럼 설치된 CLI를 요구한다. Antigravity는 비대화형 `--print`
    계약을 제공하는 `agy`만 탐지하고 PATH의 `gemini`를 fallback으로 사용하지
    않는다. 실행 가능한 agy가 있으면 sandbox 단일 prompt adapter를 활성화한다.
    """

    env = env or {}
    if action.startswith("codex-"):
        configured = env.get("AGENT_CODEX_BIN")
        executable = (
            _configured_executable(configured, "AGENT_CODEX_BIN")
            if configured
            else shutil.which("codex")
        )
        if not executable:
            raise GateError(
                "Codex CLI를 찾을 수 없습니다. PATH 또는 AGENT_CODEX_BIN을 확인하세요."
            )
        return AgentCommand("Codex", executable, "codex")

    configured = env.get("AGENT_ANTIGRAVITY_BIN")
    if configured:
        try:
            executable = _configured_executable(configured, "AGENT_ANTIGRAVITY_BIN")
        except GateError:
            executable = None
    else:
        executable = shutil.which("agy")

    if executable:
        return AgentCommand(
            agent="Antigravity",
            executable=executable,
            adapter="agy-print",
        )
    return AgentCommand(
        agent="Antigravity",
        executable=None,
        adapter="agy-print",
        automatic_execution_supported=False,
        failure_category="executable_missing",
        manual_fallback_required=True,
        next_action="scripts/agent_next_step.sh antigravity-review",
    )


def _require_file(path: Path, label: str) -> None:
    """필수 파일이 존재하는지 확인하고 없으면 label을 포함한 GateError를 발생시킨다."""

    if not path.exists():
        raise GateError(f"{label} 문서가 없습니다: {path}")


def validate_action(
    state: WorkflowState,
    action: str,
    *,
    require_agent: bool = True,
    env: dict[str, str] | None = None,
) -> AgentCommand | None:
    """요청 action의 workflow gate를 검사한다.

    require_agent가 참이면 AgentCommand를 반환하고 거짓이면 문서·상태 gate만
    검사해 None을 반환한다. 조건 불충족 시 GateError를 발생시키며 파일을
    변경하거나 Agent를 실행하지 않는다.
    """

    if not main_pointer_matches(state):
        raise GateError("docs/tasks/main.md가 현재 branch의 Task를 가리키지 않습니다.")

    required_docs = [
        state.repo / "AGENTS.md",
        state.repo / "docs" / "agent" / "backend-workflow.md",
        state.repo / "docs" / "agent" / "verification-gates.md",
        state.repo / "docs" / "agent" / "forbidden-commands.md",
    ]
    if action.startswith("codex-"):
        required_docs.append(state.repo / "docs" / "agent" / "codex-instructions.md")
    if action in REVIEW_ACTIONS:
        required_docs.append(state.repo / "docs" / "agent" / "antigravity-review.md")
    for path in required_docs:
        _require_file(path, "필수 workflow")

    missing = [name for name in REQUIRED_TASK_SECTIONS if name not in state.task.sections]
    if missing:
        raise GateError(f"Task 필수 section이 없습니다: {', '.join(missing)}")

    if action in {"codex-implement", "codex-implement-unit", "codex-fix"}:
        if state.branch in {"main", "master"}:
            raise GateError(f"{state.branch} branch에서는 구현 또는 Fix를 실행할 수 없습니다.")

    if action == "codex-implement":
        if state.approved_fixes_status == "approved":
            raise GateError("Approved Fixes 적용 대상이 있어 codex-fix를 사용해야 합니다.")

    if action == "codex-implement-unit":
        if state.task.execution_mode != "unit":
            raise GateError(
                "현재 Task는 UNIT 모드가 아닙니다. Implementation Units checklist를 작성하거나 "
                "codex-implement를 사용하세요."
            )
        if state.task.current_unit is None:
            raise GateError("모든 Implementation Unit이 완료되었습니다.")

    if action == "codex-fix":
        _require_file(state.paths.approved_fixes, "Approved Fixes")
        if state.approved_fixes_status != "approved":
            raise GateError("Approved Fixes section에 실제 승인 항목이 없습니다.")

    if action in REVIEW_ACTIONS:
        _require_file(state.paths.verification, "Verification")
        if not state.has_changes:
            raise GateError("Review할 구현 변경사항이 없습니다.")
        if state.verification_status == "failed":
            raise GateError(
                "Verification이 failed 상태여서 review 실행을 차단합니다. "
                "먼저 검증 문제를 해결하고 실제 결과를 기록하세요."
            )
        if action == "antigravity-review-unit":
            if state.task.execution_mode != "unit":
                raise GateError(
                    "UNIT Review 전용 action은 Implementation Units가 있는 Task에서만 "
                    "사용할 수 있습니다."
                )
        if state.verification_status == "pending" and action != "antigravity-review-unit":
            raise GateError(
                "최종 Review의 Verification이 pending 상태여서 review 실행을 차단합니다. "
                "먼저 검증을 완료하고 실제 결과를 기록하세요."
            )

    if require_agent:
        return resolve_agent(action, env)
    return None


def gate_message(error: Exception) -> str:
    """Gate 또는 Task parser 예외를 사용자가 이해할 수 있는 한글 메시지로 변환한다."""

    if isinstance(error, TaskParseError):
        return f"Task 파싱 오류: {error}"
    return str(error)
