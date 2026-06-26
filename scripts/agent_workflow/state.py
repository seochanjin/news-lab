"""현재 Git branch와 workflow 문서 상태를 읽어 실행 상태를 구성한다.

Repository 경로를 입력받아 branch별 Task와 Verification, Review, Approved
Fixes 경로 및 요약 상태를 반환한다. 읽기 전용 Git subprocess와 파일 읽기를
수행하지만 workflow 파일을 변경하거나 Agent를 실행하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess

from .review_validation import ReviewValidation, validate_review_file
from .task_parser import TaskDocument, parse_task


def safe_branch_name(branch: str) -> str:
    """branch 이름의 slash를 dash로 바꿔 workflow 파일용 safe name을 반환한다."""

    return branch.replace("/", "-")


def run_git(repo: Path, *args: str) -> str:
    """지정 repository에서 읽기 목적 Git 명령을 실행하고 stdout을 반환한다.

    명령 실패 시 subprocess.CalledProcessError를 전달하며 shell은 사용하지 않는다.
    """

    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@dataclass(frozen=True)
class WorkflowPaths:
    """현재 branch에 대응하는 workflow 문서 경로 묶음을 보관한다."""

    task: Path
    verification: Path
    review: Path
    approved_fixes: Path
    main_pointer: Path


@dataclass(frozen=True)
class WorkflowState:
    """현재 repository의 Task 구조와 workflow 진행 상태를 표현한다.

    상태 판정 결과만 보관하며 생성 자체로 추가 subprocess나 파일 변경을
    수행하지 않는다.
    """

    repo: Path
    branch: str
    safe_branch: str
    paths: WorkflowPaths
    task: TaskDocument
    has_changes: bool
    verification_status: str
    review_status: str
    review_validation: str
    review_verdict: str | None
    automatic_review_status: str
    review_execution_status: str
    review_failure_category: str | None
    review_failure_started_at: str | None
    manual_review_required: bool
    approved_fixes_status: str

    @property
    def suggested_action(self) -> str:
        """Verification, Approved Fixes, Review와 UNIT 상태로 다음 단계를 제안한다.

        Review가 이미 존재하는데 Verification이 failed 또는 pending이면 실행
        action 대신 `resolve-verification`을 반환해 먼저 검증 문제를 해결하도록
        안내한다.
        """

        if self.review_execution_status == "failed":
            return "antigravity-review"
        if self.review_status == "completed" and self.approved_fixes_status == "approved":
            return "codex-fix"
        if (
            self.verification_status in {"failed", "pending"}
            and self.review_status == "completed"
        ):
            return "resolve-verification"
        if (
            self.verification_status == "passed"
            and self.review_status == "completed"
            and self.approved_fixes_status == "applied"
        ):
            return "pr-draft"
        if self.verification_status == "passed" and self.review_status == "completed":
            return (
                "fixes-draft"
                if self.review_verdict == "CHANGES REQUIRED"
                else "pr-draft"
            )
        if self.review_status == "not started":
            return (
                "codex-implement-unit"
                if self.task.execution_mode == "unit" and self.task.current_unit
                else "codex-implement"
            )
        if self.review_status in {"template only", "incomplete"}:
            return "antigravity-review-write"
        return "antigravity-review"


def _document_status(path: Path, section: str | None = None) -> str:
    """문서 또는 특정 section의 존재와 checklist 상태를 간단한 문자열로 반환한다."""

    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return "not started"
    text = path.read_text(encoding="utf-8")
    if section:
        match = re.search(
            rf"^##\s+{re.escape(section)}\s*$\n(.*?)(?=^##\s|\Z)",
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not match or not match.group(1).strip():
            return "none"
        body = match.group(1)
        if re.search(r"^-\s+\[ \]\s+\S", body, flags=re.MULTILINE):
            return "approved"
        if re.search(r"^-\s+\[[xX]\]\s+\S", body, flags=re.MULTILINE):
            return "applied"
        return "none"
    return "present"


def _verification_status(path: Path) -> str:
    """Verification Status section만 읽어 현재 검증 상태를 반환한다.

    문서가 없으면 missing, 문서는 있지만 명시적 section이 없거나 지원하지 않는
    값이면 present를 반환한다. fenced code block과 과거 command별 Status 문구는
    현재 상태 판정에서 제외하며 파일을 변경하지 않는다.
    """

    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return "missing"

    lines = path.read_text(encoding="utf-8").splitlines()
    in_fence = False
    in_status_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            in_status_section = stripped == "## Verification Status"
            continue
        if in_status_section and stripped:
            status = stripped.lower()
            return status if status in {"passed", "failed", "pending"} else "present"
    return "present"


def _review_status(validation: ReviewValidation) -> str:
    """세부 review 검증 결과를 workflow의 사용자-facing 상태로 축약한다."""

    if validation.status in {"not_started", "empty"}:
        return "not started"
    if validation.status == "template_only":
        return "template only"
    if validation.completed:
        return "completed"
    return "incomplete"


def _latest_review_run(repo: Path, safe_branch: str) -> dict[str, object] | None:
    """현재 branch의 최신 Antigravity 실행 result JSON을 읽어 반환한다.

    로그가 없거나 JSON이 손상된 실행은 상태 판정 근거로 사용하지 않는다. 로그를
    생성·수정하지 않으며 민감한 stdout·stderr 내용은 읽지 않는다.
    """

    run_root = repo / ".agent-runs" / safe_branch
    if not run_root.exists():
        return None
    result_paths = sorted(
        [
            *run_root.glob("*-antigravity-review/result.json"),
            *run_root.glob("*-antigravity-review-unit/result.json"),
        ],
        key=lambda path: path.parent.name,
        reverse=True,
    )
    for path in result_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def load_state(repo: str | Path = ".") -> WorkflowState:
    """Repository와 현재 branch를 조사해 WorkflowState를 생성한다.

    Git 조회와 UTF-8 문서 읽기를 수행한다. branch나 Task가 없거나 Task 형식이
    잘못되면 ValueError, FileNotFoundError 또는 TaskParseError가 발생할 수 있다.
    """

    root = Path(run_git(Path(repo), "rev-parse", "--show-toplevel")).resolve()
    branch = run_git(root, "branch", "--show-current")
    if not branch:
        raise ValueError("현재 git branch를 확인할 수 없습니다.")
    safe = safe_branch_name(branch)
    paths = WorkflowPaths(
        task=root / "docs" / "tasks" / f"{safe}.md",
        verification=root / "docs" / "verification" / f"{safe}.md",
        review=root / "docs" / "reviews" / f"{safe}-antigravity.md",
        approved_fixes=root / "docs" / "fixes" / f"{safe}-approved-fixes.md",
        main_pointer=root / "docs" / "tasks" / "main.md",
    )
    if not paths.task.exists():
        raise FileNotFoundError(f"현재 branch의 Task 문서가 없습니다: {paths.task}")
    review_validation = validate_review_file(paths.review)
    latest_review_run = _latest_review_run(root, safe)
    automatic_review_status = "unavailable"
    review_execution_status = "not started"
    review_failure_category = None
    review_failure_started_at = None
    if latest_review_run:
        automatic_review_status = (
            "available"
            if latest_review_run.get("automatic_execution_supported") is True
            else "unavailable"
        )
        review_failure_category_value = latest_review_run.get("failure_category")
        if isinstance(review_failure_category_value, str):
            review_failure_category = review_failure_category_value
        started_at_value = latest_review_run.get("started_at")
        if isinstance(started_at_value, str):
            review_failure_started_at = started_at_value
        if review_failure_category or latest_review_run.get("exit_code") not in {0, None}:
            review_execution_status = "failed"
        elif latest_review_run.get("review_completed") is True:
            review_execution_status = "completed"
        else:
            review_execution_status = "incomplete"
    review_status = _review_status(review_validation)
    return WorkflowState(
        repo=root,
        branch=branch,
        safe_branch=safe,
        paths=paths,
        task=parse_task(paths.task),
        has_changes=bool(run_git(root, "status", "--porcelain")),
        verification_status=_verification_status(paths.verification),
        review_status=review_status,
        review_validation=review_validation.status,
        review_verdict=review_validation.verdict,
        automatic_review_status=automatic_review_status,
        review_execution_status=review_execution_status,
        review_failure_category=review_failure_category,
        review_failure_started_at=(
            review_failure_started_at if review_execution_status == "failed" else None
        ),
        manual_review_required=(
            review_execution_status == "failed"
            or (
                review_status != "completed"
                and (
                    automatic_review_status == "unavailable"
                    or review_execution_status == "failed"
                )
            )
        ),
        approved_fixes_status=_document_status(paths.approved_fixes, "Approved Fixes"),
    )


def main_pointer_matches(state: WorkflowState) -> bool:
    """docs/tasks/main.md의 실제 Markdown link가 현재 Task를 가리키는지 판정한다.

    Symlink는 해석된 대상 경로를 비교한다. 일반 Markdown 파일은 fenced code
    block 밖의 link target만 추출하고 pointer 문서 기준으로 정규화해 현재 Task
    경로와 정확히 같은 경우에만 True를 반환한다.
    """

    pointer = state.paths.main_pointer
    if not pointer.exists():
        return False
    if pointer.is_symlink():
        return pointer.resolve() == state.paths.task.resolve()

    in_fence = False
    targets: list[str] = []
    for line in pointer.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        targets.extend(re.findall(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)", line))

    expected = state.paths.task.resolve()
    for target in targets:
        if target.startswith(("#", "http://", "https://", "file://")):
            continue
        normalized = (pointer.parent / target).resolve()
        if normalized == expected:
            return True
    return False


def format_status(state: WorkflowState) -> str:
    """WorkflowState를 사람이 읽을 수 있는 상태 출력 문자열로 변환한다."""

    lines = [
        "Task:",
        f"- {state.task.title}",
        "",
        "Branch:",
        f"- {state.branch}",
        "",
        "Execution mode:",
        f"- {state.task.execution_mode}",
    ]
    if state.task.execution_mode == "unit":
        unit = state.task.current_unit
        lines.extend(
            [
                "",
                "Current unit:",
                f"- {unit.identifier}: {unit.title}" if unit else "- none",
                "",
                "Completed units:",
                f"- {state.task.completed_unit_count}",
                "",
                "Pending units:",
                f"- {state.task.pending_unit_count}",
            ]
        )
    lines.extend(
        [
            "",
            "Verification:",
            f"- {state.verification_status}",
            "",
            "Review:",
            f"- {state.review_status}",
            "",
            "Review validation:",
            f"- {state.review_validation}",
            "",
            "Automatic review:",
            f"- {state.automatic_review_status}",
            "",
            "Review execution:",
            f"- {state.review_execution_status}",
            "",
            "Manual review required:",
            f"- {'yes' if state.manual_review_required else 'no'}",
            "",
            "Approved fixes:",
            f"- {state.approved_fixes_status}",
            "",
            "Suggested next action:",
            f"- {state.suggested_action}",
        ]
    )
    if state.suggested_action == "resolve-verification":
        lines.extend(
            [
                "",
                "Action required:",
                "- 먼저 검증 문제를 해결하고 실제 결과를 Verification에 기록하세요.",
            ]
        )
    elif state.manual_review_required:
        lines.extend(
            [
                "",
                "Action required:",
                "- scripts/agent_next_step.sh antigravity-review",
                "- scripts/agent_next_step.sh antigravity-review-write",
            ]
        )
    if state.review_failure_category:
        lines.extend(
            [
                "",
                "Review failure category:",
                f"- {state.review_failure_category}",
            ]
        )
    if state.review_failure_started_at:
        lines.extend(
            [
                "",
                "Latest review failure started at:",
                f"- {state.review_failure_started_at}",
                "",
                "Review recovery action:",
                "- scripts/agent_run.sh antigravity-review",
            ]
        )
    return "\n".join(lines)
