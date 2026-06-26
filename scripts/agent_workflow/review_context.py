"""다음 Antigravity UNIT Review 대상과 입력 Context를 결정론적으로 구성한다.

Task의 구현 완료 상태와 Review checklist 통과 상태를 대조해 UNIT 전용 action은
가장 앞선 미검토 완료 UNIT 하나만 선택한다. 최종 Review action은 모든 UNIT
Review가 끝난 뒤 통합 Review 또는 Re-review를 선택하며, 일반 Task는 general
Review target을 만든다. Task의 필요한 계약, Approved Fixes, 최신 Verification과
제한된 현재 Git 변경만 구조화해 반환한다. Git 조회와 문서 읽기만 수행하며
Review 파일 쓰기, prompt 생성, Agent subprocess 실행은 담당하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .review_evidence import ReviewEvidence, build_review_evidence
from .review_unit_status import ReviewUnitStatus
from .state import run_git
from .task_parser import TaskDocument, TaskUnit


class ReviewContextError(ValueError):
    """Review 대상 또는 Context를 안전하게 결정할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class ReviewTarget:
    """선택된 Review 대상, mode와 다음 Re-review 번호를 보관한다."""

    unit: TaskUnit
    mode: str
    position: int
    total_units: int
    re_review_number: int | None = None


@dataclass(frozen=True)
class ReviewContext:
    """Antigravity prompt가 사용할 현재 UNIT Review의 구조화된 입력을 보관한다."""

    action: str
    branch: str
    task_title: str
    task_path: str
    review_path: str
    verification_path: str
    approved_fixes_path: str
    target: ReviewTarget
    evidence: ReviewEvidence
    previous_units: tuple[TaskUnit, ...]
    scope: str
    do_not_change: str
    acceptance_criteria: str
    changed_files: tuple[str, ...]
    git_diff: str


SENSITIVE_FILE_NAMES = {
    ".env",
    "credentials",
    "credentials.json",
    "kubeconfig",
}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".crt", ".cer"}
SENSITIVE_PATH_MARKER = "<sensitive-path-redacted>"
MAX_UNTRACKED_TEXT_BYTES = 256_000
MAX_DIFF_FILE_CHARS = 12_000
MAX_DIFF_TOTAL_CHARS = 48_000


def select_next_review_target(
    task: TaskDocument,
    review_status: ReviewUnitStatus | None,
    evidence: ReviewEvidence | None = None,
) -> ReviewTarget:
    """기존 호환용으로 UNIT 전용 다음 Review 대상을 선택한다.

    `antigravity-review-unit`과 같은 의미로 마지막 UNIT도 `unit` mode를 유지한다.
    evidence 인자는 과거 호출자 호환을 위해 받지만 target 결정에는 사용하지 않는다.
    """

    _ = evidence
    return select_unit_review_target(task, review_status)


def _validate_review_status_order(
    task: TaskDocument, review_status: ReviewUnitStatus
) -> None:
    """Task UNIT과 Review Status의 순서, 제목과 완료 상태 모순을 검증한다."""

    task_units = task.implementation_units
    if not task_units:
        raise ReviewContextError("Implementation Units가 없는 Task입니다.")
    if len(task_units) != len(review_status.units):
        raise ReviewContextError("Task와 Review Status의 UNIT 개수가 다릅니다.")

    unchecked_seen = False
    for task_unit, review_unit in zip(task_units, review_status.units):
        if (task_unit.identifier, task_unit.title) != (
            review_unit.identifier,
            review_unit.title,
        ):
            raise ReviewContextError(
                "Task와 Review Status의 UNIT 식별자, 제목 또는 순서가 다릅니다."
            )
        if review_unit.reviewed and not task_unit.completed:
            raise ReviewContextError(
                f"미완료 Task UNIT이 Review 완료로 표시됐습니다: {task_unit.identifier}"
            )
        if review_unit.reviewed and unchecked_seen:
            raise ReviewContextError("Review 완료 상태가 UNIT 순서를 건너뛰었습니다.")
        if not review_unit.reviewed:
            unchecked_seen = True


def select_unit_review_target(
    task: TaskDocument,
    review_status: ReviewUnitStatus,
) -> ReviewTarget:
    """구현 완료됐지만 Review 미통과인 가장 앞 UNIT 하나를 `unit` mode로 선택한다."""

    _validate_review_status_order(task, review_status)
    task_units = task.implementation_units

    for index, (task_unit, review_unit) in enumerate(
        zip(task_units, review_status.units)
    ):
        if task_unit.completed and not review_unit.reviewed:
            return ReviewTarget(
                unit=task_unit,
                mode="unit",
                position=index + 1,
                total_units=len(task_units),
            )
    raise ReviewContextError("구현 완료됐지만 Review를 통과하지 않은 UNIT이 없습니다.")


def select_final_review_target(
    task: TaskDocument,
    review_status: ReviewUnitStatus | None,
    evidence: ReviewEvidence,
    review_path: str | Path,
) -> ReviewTarget:
    """최종 Review action의 integration, re-review 또는 general target을 선택한다.

    UNIT Task에서는 미검토 완료 UNIT이 남아 있으면 unit 전용 action 사용을
    요구한다. 모든 UNIT 구현과 UNIT Review가 완료된 뒤 Integration Review가
    없으면 마지막 UNIT을 통합 Review 대상으로 선택하고, Integration Review가
    있으면 적용 완료된 구현 FIX 기준으로 Re-review 번호를 계산한다. 사람이
    수행해야 하는 `human-verification` FIX만 미완료인 경우 Re-review를 허용한다.
    """

    task_units = task.implementation_units
    if not task_units:
        return ReviewTarget(
            unit=TaskUnit("TASK", task.title, True),
            mode="general",
            position=1,
            total_units=1,
        )
    if review_status is None:
        raise ReviewContextError("UNIT Task의 Review Status가 없습니다.")
    _validate_review_status_order(task, review_status)
    pending = [
        task_unit.identifier
        for task_unit, review_unit in zip(task_units, review_status.units)
        if task_unit.completed and not review_unit.reviewed
    ]
    if pending:
        raise ReviewContextError(
            "UNIT Review는 antigravity-review-unit Action을 사용하십시오."
        )
    if not all(unit.completed for unit in task_units):
        raise ReviewContextError("모든 Implementation Unit이 완료되지 않았습니다.")
    if not all(unit.reviewed for unit in review_status.units):
        raise ReviewContextError("모든 UNIT Review Status가 완료되지 않았습니다.")

    if not _has_integration_review(review_path, task_units[-1].identifier):
        return ReviewTarget(
            unit=task_units[-1],
            mode="integration",
            position=len(task_units),
            total_units=len(task_units),
        )
    pending_implementation = evidence.approved_fixes.pending_implementation
    if pending_implementation:
        identifiers = ", ".join(fix.identifier for fix in pending_implementation)
        raise ReviewContextError(
            "미적용 구현 Approved Fix가 있어 Re-review를 실행할 수 없습니다: "
            f"{identifiers}"
        )
    if evidence.approved_fixes.applied:
        return ReviewTarget(
            unit=task_units[-1],
            mode="re-review",
            position=len(task_units),
            total_units=len(task_units),
            re_review_number=evidence.review_history.next_re_review_number,
        )
    raise ReviewContextError("현재 변경사항은 이미 최신 Antigravity Review를 통과했습니다.")


def _has_integration_review(review_path: str | Path, unit_identifier: str) -> bool:
    """Review History에 대상 UNIT의 Integration Review heading이 있는지 확인한다."""

    path = Path(review_path)
    if not path.exists():
        return False
    heading = f"## Integration Review: {unit_identifier}"
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped == heading:
            return True
    return False


def _relative_path(path: Path, repo: Path) -> str:
    """Repository 내부 경로는 상대 경로로, 외부 경로는 절대 경로로 반환한다."""

    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path.resolve())


def _is_sensitive_path(path: Path) -> bool:
    """Context에 본문을 포함하면 안 되는 민감 파일명과 확장자인지 판정한다."""

    lower_parts = tuple(part.lower() for part in path.parts)
    name = path.name.lower()
    return (
        name in SENSITIVE_FILE_NAMES
        or name.startswith(".env.")
        or path.suffix.lower() in SENSITIVE_SUFFIXES
        or any(
            part in {"secret", "secrets", "credential", "credentials", ".ssh"}
            for part in lower_parts
        )
    )


def _redact_changed_file_entry(entry: str) -> str:
    """Git porcelain 변경 항목에서 민감 old/new 경로를 고정 marker로 대체한다."""

    parts = [part.strip() for part in entry.split(" -> ")]
    if any(_is_sensitive_path(Path(part)) for part in parts):
        return SENSITIVE_PATH_MARKER
    return entry


def _render_untracked_file(repo: Path, relative_name: str) -> str:
    """미추적 text 파일을 Review용 추가 diff block으로 변환한다.

    Repository 밖 경로, symlink, 민감 파일, 큰 파일과 UTF-8이 아닌 파일은
    본문을 읽지 않고 제외 사유만 반환한다.
    """

    candidate = repo / relative_name
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return f"### Untracked file omitted: {relative_name} (outside repository)"
    if candidate.is_symlink():
        return f"### Untracked file omitted: {relative_name} (symlink)"
    if _is_sensitive_path(candidate):
        return f"### Untracked file omitted: {SENSITIVE_PATH_MARKER} (sensitive path)"
    try:
        if candidate.stat().st_size > MAX_UNTRACKED_TEXT_BYTES:
            return f"### Untracked file omitted: {relative_name} (file too large)"
        text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return f"### Untracked file omitted: {relative_name} (non-text or unreadable)"
    prefixed = "\n".join(f"+{line}" for line in text.splitlines())
    if text.endswith("\n"):
        prefixed += "\n"
    return (
        f"diff --untracked a/{relative_name} b/{relative_name}\n"
        "--- /dev/null\n"
        f"+++ b/{relative_name}\n"
        f"{prefixed}"
    )


def _diff_path(block: str) -> str:
    """Git diff block의 대상 경로를 반환하고 형식이 다르면 빈 문자열을 반환한다."""

    first_line = block.splitlines()[0] if block.splitlines() else ""
    match = re.match(r"^diff --(?:git|untracked) a/(.+?) b/(.+)$", first_line)
    return match.group(2) if match else ""


def _diff_paths(block: str) -> tuple[str, ...]:
    """Git diff block의 old/new 경로를 반환하고 형식이 다르면 빈 tuple을 반환한다."""

    first_line = block.splitlines()[0] if block.splitlines() else ""
    match = re.match(r"^diff --(?:git|untracked) a/(.+?) b/(.+)$", first_line)
    return (match.group(1), match.group(2)) if match else ()


def _sensitive_diff_marker() -> str:
    """민감 파일 diff를 대체할 고정 marker block을 반환한다."""

    return (
        f"diff --git a/{SENSITIVE_PATH_MARKER} b/{SENSITIVE_PATH_MARKER}\n"
        "... sensitive path omitted from review context ..."
    )


def _limit_diff_blocks(diff_text: str) -> str:
    """문서 diff를 제외하고 파일별·전체 크기 상한을 적용한 Review diff를 반환한다."""

    blocks = re.split(r"(?=^diff --(?:git|untracked) )", diff_text, flags=re.MULTILINE)
    selected: list[str] = []
    used = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        path = _diff_path(block)
        if any(_is_sensitive_path(Path(diff_path)) for diff_path in _diff_paths(block)):
            block = _sensitive_diff_marker()
        if path.startswith("docs/"):
            continue
        if len(block) > MAX_DIFF_FILE_CHARS:
            block = (
                block[:MAX_DIFF_FILE_CHARS]
                + "\n... diff truncated by review context limit ..."
            )
        remaining = MAX_DIFF_TOTAL_CHARS - used
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining] + "\n... total diff limit reached ..."
        selected.append(block)
        used += len(block)
    return "\n\n".join(selected)


def _collect_git_diff(repo: Path) -> str:
    """Tracked·미추적 diff를 결합한 뒤 Review용 크기와 문서 제외 정책을 적용한다."""

    tracked = run_git(repo, "diff", "--no-ext-diff", "HEAD", "--")
    untracked_output = run_git(repo, "ls-files", "--others", "--exclude-standard")
    blocks = [tracked] if tracked else []
    blocks.extend(
        _render_untracked_file(repo, relative_name)
        for relative_name in untracked_output.splitlines()
        if relative_name
    )
    return _limit_diff_blocks("\n\n".join(blocks))


def build_review_context(
    *,
    repo: str | Path,
    branch: str,
    task: TaskDocument,
    review_status: ReviewUnitStatus,
    review_path: str | Path,
    verification_path: str | Path,
    approved_fixes_path: str | Path | None = None,
    action: str = "antigravity-review-unit",
) -> ReviewContext:
    """선택된 UNIT과 현재 repository evidence로 ReviewContext를 생성한다.

    `git status --porcelain`의 경로 목록과 제한된 `git diff HEAD --` 결과를
    읽는다. Approved Fixes, Verification과 Review History는 current-state
    evidence로 파싱하며 과거 Verification 원문과 Task 실행 예시는 보존하지
    않는다. Git 또는 parser 실패는 호출자에게 전달하며 파일을 수정하지 않는다.
    """

    root = Path(repo).resolve()
    fixes_path = (
        Path(approved_fixes_path)
        if approved_fixes_path is not None
        else root / "docs" / "fixes" / f"{branch.replace('/', '-')}-approved-fixes.md"
    )
    evidence = build_review_evidence(
        approved_fixes_path=fixes_path,
        verification_path=verification_path,
        review_path=review_path,
    )
    if action == "antigravity-review-unit":
        if review_status is None:
            raise ReviewContextError("UNIT Review Status가 없습니다.")
        target = select_unit_review_target(task, review_status)
    elif action == "antigravity-review":
        target = select_final_review_target(task, review_status, evidence, review_path)
    else:
        raise ReviewContextError(f"지원하지 않는 Review action입니다: {action}")
    status_output = run_git(root, "status", "--porcelain")
    changed_files = tuple(
        _redact_changed_file_entry(line[3:])
        for line in status_output.splitlines()
        if len(line) >= 4
    )
    git_diff = _collect_git_diff(root)
    task_units = task.implementation_units or ()
    return ReviewContext(
        action=action,
        branch=branch,
        task_title=task.title,
        task_path=_relative_path(task.path, root),
        review_path=_relative_path(Path(review_path), root),
        verification_path=_relative_path(Path(verification_path), root),
        approved_fixes_path=_relative_path(fixes_path, root),
        target=target,
        evidence=evidence,
        previous_units=tuple(task_units[: target.position - 1]),
        scope=task.sections.get("Scope", ""),
        do_not_change=task.sections.get("Do not change", ""),
        acceptance_criteria=task.sections.get("Acceptance criteria", ""),
        changed_files=changed_files,
        git_diff=git_diff,
    )
