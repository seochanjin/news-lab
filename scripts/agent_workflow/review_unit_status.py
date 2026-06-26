"""Task UNIT 목록과 Antigravity Review 상태 checklist를 동기화한다.

TaskDocument의 Implementation Units를 기준으로 Review 파일의
`Unit Review Status` section을 파싱하고, section이 없을 때만 결정론적으로
생성한다. 기존 checklist와 Review 이력은 보존하며 Task와 식별자·제목·순서가
다르면 예외를 발생시켜 파일을 수정하지 않는다. Agent subprocess 실행이나
Review 응답 검증은 담당하지 않으며, 검증된 PASS Verdict를 받은 선택 UNIT의
체크 상태를 메모리 문자열에서 갱신하는 기능만 제공한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .task_parser import TaskDocument


HEADING_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$")
STATUS_UNIT_RE = re.compile(r"^-\s+\[([ xX])\]\s+(UNIT-\d+):\s+(.+?)\s*$")
STATUS_HEADING = "Unit Review Status"


class ReviewUnitStatusError(ValueError):
    """Review UNIT 상태를 안전하게 생성하거나 해석할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class ReviewUnit:
    """Review checklist에 기록된 UNIT 식별자, 원문 제목과 통과 상태를 보관한다."""

    identifier: str
    title: str
    reviewed: bool


@dataclass(frozen=True)
class ReviewUnitStatus:
    """Task와 대조가 끝난 Review UNIT 목록과 section 생성 여부를 보관한다."""

    units: tuple[ReviewUnit, ...]
    created: bool


def build_initial_review_unit_status(task: TaskDocument) -> ReviewUnitStatus:
    """Task UNIT 전체를 Review 미통과 상태로 구성해 반환한다.

    Review 파일이 아직 없거나 status section 생성 전인 dry-run에서 사용한다.
    Task의 식별자, 제목과 순서를 그대로 보존하며 파일을 생성하거나 수정하지 않는다.
    """

    if not task.implementation_units:
        raise ReviewUnitStatusError("Implementation Units가 없는 Task입니다.")
    return ReviewUnitStatus(
        units=tuple(
            ReviewUnit(
                identifier=unit.identifier,
                title=unit.title,
                reviewed=False,
            )
            for unit in task.implementation_units
        ),
        created=False,
    )


def _find_status_section(text: str) -> tuple[int, int] | None:
    """fenced code block 밖의 Unit Review Status 본문 line 범위를 반환한다.

    같은 heading이 둘 이상이면 상태 source가 모호하므로
    ReviewUnitStatusError를 발생시킨다.
    """

    lines = text.splitlines()
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))

    matches: list[tuple[int, int]] = []
    for position, (index, level, name) in enumerate(headings):
        if level != 2 or name != STATUS_HEADING:
            continue
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        matches.append((index + 1, end))
    if len(matches) > 1:
        raise ReviewUnitStatusError("Unit Review Status section이 중복되어 있습니다.")
    return matches[0] if matches else None


def _parse_status_units(body_lines: list[str]) -> tuple[ReviewUnit, ...]:
    """Review status 본문을 순서가 보존된 UNIT 목록으로 변환한다."""

    content = [line.strip() for line in body_lines if line.strip()]
    if not content:
        raise ReviewUnitStatusError("Unit Review Status section이 비어 있습니다.")
    units: list[ReviewUnit] = []
    identifiers: set[str] = set()
    for line in content:
        match = STATUS_UNIT_RE.match(line)
        if not match:
            raise ReviewUnitStatusError(
                "Review UNIT 형식은 '- [ ] UNIT-NN: 설명'이어야 합니다."
            )
        identifier = match.group(2)
        if identifier in identifiers:
            raise ReviewUnitStatusError(f"중복 Review UNIT identifier입니다: {identifier}")
        identifiers.add(identifier)
        units.append(
            ReviewUnit(
                identifier=identifier,
                title=match.group(3).strip(),
                reviewed=match.group(1).lower() == "x",
            )
        )
    return tuple(units)


def _validate_against_task(
    task: TaskDocument, review_units: tuple[ReviewUnit, ...]
) -> None:
    """Review UNIT 식별자·제목·순서가 Task 원문과 정확히 같은지 검증한다."""

    task_units = task.implementation_units
    if not task_units:
        raise ReviewUnitStatusError("Implementation Units가 없는 Task입니다.")
    expected = tuple((unit.identifier, unit.title) for unit in task_units)
    actual = tuple((unit.identifier, unit.title) for unit in review_units)
    if actual != expected:
        raise ReviewUnitStatusError(
            "Unit Review Status가 Task의 UNIT 식별자, 제목 또는 순서와 다릅니다."
        )


def parse_review_unit_status(
    task: TaskDocument, review_path: str | Path
) -> ReviewUnitStatus:
    """기존 Review 파일의 Unit Review Status를 읽고 Task와 대조한다.

    파일 또는 status section이 없으면 ReviewUnitStatusError를 발생시킨다.
    성공 시 기존 체크 상태를 그대로 반환하며 파일을 변경하지 않는다.
    """

    path = Path(review_path)
    if not path.exists():
        raise ReviewUnitStatusError(f"Review 파일이 없습니다: {path}")
    text = path.read_text(encoding="utf-8")
    section = _find_status_section(text)
    if section is None:
        raise ReviewUnitStatusError("Unit Review Status section이 없습니다.")
    lines = text.splitlines()
    units = _parse_status_units(lines[section[0] : section[1]])
    _validate_against_task(task, units)
    return ReviewUnitStatus(units=units, created=False)


def _status_markdown(task: TaskDocument) -> str:
    """Task UNIT 제목을 변경하지 않은 unchecked Review checklist를 생성한다."""

    if not task.implementation_units:
        raise ReviewUnitStatusError("Implementation Units가 없는 Task입니다.")
    checklist = "\n".join(
        f"- [ ] {unit.identifier}: {unit.title}" for unit in task.implementation_units
    )
    return f"## {STATUS_HEADING}\n\n{checklist}"


def _insert_status(text: str, status_markdown: str) -> str:
    """첫 2단계 section 앞에 status를 삽입하고 제목·preamble·이력을 보존한다."""

    lines = text.splitlines()
    title_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("# ") and not line.startswith("## ")
        ),
        None,
    )
    if title_index is None:
        raise ReviewUnitStatusError("Review 파일의 1단계 제목을 찾을 수 없습니다.")

    insert_index = len(lines)
    in_fence = False
    for index in range(title_index + 1, len(lines)):
        line = lines[index]
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 2:
            insert_index = index
            break

    before = "\n".join(lines[:insert_index]).rstrip()
    after = "\n".join(lines[insert_index:]).strip("\n")
    result = f"{before}\n\n{status_markdown}"
    if after:
        result += f"\n\n{after}"
    return result + "\n"


def ensure_review_unit_status(
    task: TaskDocument, review_path: str | Path
) -> ReviewUnitStatus:
    """Review 파일에 Task 기반 Unit Review Status가 존재하도록 보장한다.

    파일이 없으면 branch Review 제목과 unchecked checklist를 생성한다. 기존
    파일에 section이 없으면 1단계 제목 바로 뒤에 삽입한다. 이미 section이
    있으면 Task와 대조만 수행하고 체크 상태와 Review 이력을 변경하지 않는다.
    """

    path = Path(review_path)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if original and _find_status_section(original) is not None:
        return parse_review_unit_status(task, path)
    updated = render_review_with_unit_status(task, original)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(updated, encoding="utf-8")
    parsed = parse_review_unit_status(task, path)
    return ReviewUnitStatus(units=parsed.units, created=True)


def render_review_with_unit_status(task: TaskDocument, original: str) -> str:
    """기존 Review 이력을 보존해 Task 기반 Unit Review Status 문자열을 반환한다.

    입력이 비어 있으면 branch Review 제목과 unchecked checklist를 만든다.
    기존 status가 있으면 Task와 식별자·제목·순서를 대조한 원문을 그대로
    반환하고, 없으면 기존 1단계 제목과 이력 앞에 status를 삽입한다. 파일은
    변경하지 않는다.
    """

    status_markdown = _status_markdown(task)
    if not original:
        return f"# Antigravity Review: {task.title}\n\n{status_markdown}\n"
    section = _find_status_section(original)
    if section is not None:
        lines = original.splitlines()
        units = _parse_status_units(lines[section[0] : section[1]])
        _validate_against_task(task, units)
        return original if original.endswith("\n") else original + "\n"
    return _insert_status(original, status_markdown)


def render_review_with_passed_unit(
    task: TaskDocument,
    original: str,
    unit_identifier: str,
) -> str:
    """선택 UNIT의 Review Status만 통과 상태로 바꾼 전체 문자열을 반환한다.

    Review 파일이 없거나 status section이 없으면 먼저 Task 기준 checklist를
    구성한다. 대상 UNIT이 Task와 status에 정확히 한 번 존재하고 아직 미통과인
    경우에만 `[ ]`를 `[x]`로 변경한다. 이미 통과했거나 알 수 없는 UNIT이면
    ReviewUnitStatusError를 발생시키며 파일은 직접 변경하지 않는다.
    """

    base = render_review_with_unit_status(task, original)
    section = _find_status_section(base)
    if section is None:
        raise ReviewUnitStatusError("Unit Review Status section을 생성하지 못했습니다.")

    lines = base.splitlines()
    units = _parse_status_units(lines[section[0] : section[1]])
    _validate_against_task(task, units)
    matching_units = [unit for unit in units if unit.identifier == unit_identifier]
    if len(matching_units) != 1:
        raise ReviewUnitStatusError(
            f"Review Status에서 선택 UNIT을 찾을 수 없습니다: {unit_identifier}"
        )
    unit = matching_units[0]
    if unit.reviewed:
        raise ReviewUnitStatusError(
            f"이미 Review를 통과한 UNIT입니다: {unit_identifier}"
        )
    matching_lines = [
        index
        for index in range(section[0], section[1])
        if (
            (match := STATUS_UNIT_RE.match(lines[index].strip()))
            and match.group(2) == unit_identifier
        )
    ]
    if len(matching_lines) != 1:
        raise ReviewUnitStatusError(
            f"Review Status의 선택 UNIT line이 모호합니다: {unit_identifier}"
        )
    lines[matching_lines[0]] = f"- [x] {unit.identifier}: {unit.title}"
    return "\n".join(lines) + "\n"
