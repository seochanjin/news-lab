"""NewsLab Task Markdown과 Implementation Units를 해석한다.

Task 파일 경로를 입력받아 제목, section, UNIT 상태를 구조화된 데이터로
반환한다. 형식이 모호하거나 완료 순서가 안전하지 않으면 TaskParseError를
발생시키며 파일을 변경하거나 subprocess를 실행하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
UNIT_RE = re.compile(r"^-\s+\[([ xX])\]\s+(UNIT-\d+):\s+(.+?)\s*$")


class TaskParseError(ValueError):
    """Task Markdown을 안전하고 일관되게 해석할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class TaskUnit:
    """Task에 선언된 UNIT 하나의 식별자, 설명과 완료 상태를 보관한다."""

    identifier: str
    title: str
    completed: bool


@dataclass(frozen=True)
class TaskDocument:
    """파싱된 Task의 경로, 제목, section과 선택적 UNIT 목록을 보관한다."""

    path: Path
    title: str
    sections: dict[str, str]
    implementation_units: tuple[TaskUnit, ...] | None

    @property
    def execution_mode(self) -> str:
        """UNIT 목록 존재 여부에 따라 `unit` 또는 `general` mode를 반환한다."""

        return "unit" if self.implementation_units else "general"

    @property
    def current_unit(self) -> TaskUnit | None:
        """첫 번째 미완료 UNIT을 반환하고 UNIT이 없거나 모두 완료되면 None을 반환한다."""

        if not self.implementation_units:
            return None
        return next((unit for unit in self.implementation_units if not unit.completed), None)

    @property
    def completed_unit_count(self) -> int:
        """완료 표시된 UNIT 수를 반환한다."""

        return sum(unit.completed for unit in self.implementation_units or ())

    @property
    def pending_unit_count(self) -> int:
        """아직 완료되지 않은 UNIT 수를 반환한다."""

        return sum(not unit.completed for unit in self.implementation_units or ())


def _split_sections(text: str) -> tuple[str, dict[str, str]]:
    """Task Markdown을 제목과 2단계 heading별 본문으로 분리한다.

    fenced code block 안의 heading은 예시로 간주해 section으로 처리하지 않는다.
    제목이 없으면 TaskParseError를 발생시키며 입력 문자열은 변경하지 않는다.
    """

    lines = text.splitlines()
    title = ""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    in_fence = False

    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            if current is not None:
                sections[current].append(line)
            continue
        if not title and line.startswith("# "):
            title = line[2:].strip()
        match = None if in_fence else SECTION_RE.match(line)
        if match:
            current = match.group(1).strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)

    if not title:
        raise TaskParseError("Task 제목을 찾을 수 없습니다.")
    if title.startswith("Task:"):
        title = title.removeprefix("Task:").strip()
    return title, {name: "\n".join(body).strip() for name, body in sections.items()}


def _parse_units(body: str) -> tuple[TaskUnit, ...] | None:
    """Implementation Units 본문을 검증하고 순서가 보존된 UNIT 목록으로 변환한다.

    `없음`이면 None을 반환한다. 혼합 형식, 중복 식별자, 역순 완료 또는 잘못된
    checklist가 있으면 TaskParseError를 발생시킨다.
    """

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        raise TaskParseError("Implementation Units section이 비어 있습니다.")

    has_none = any(line == "없음" for line in lines)
    unit_lines = [line for line in lines if UNIT_RE.match(line)]
    if has_none and unit_lines:
        raise TaskParseError("Implementation Units에 '없음'과 UNIT checklist가 함께 있습니다.")
    if has_none:
        if lines != ["없음"]:
            raise TaskParseError("Implementation Units의 '없음' 외에 해석할 수 없는 내용이 있습니다.")
        return None
    if len(unit_lines) != len(lines):
        raise TaskParseError("UNIT 형식은 '- [ ] UNIT-NN: 설명'이어야 합니다.")

    units: list[TaskUnit] = []
    identifiers: set[str] = set()
    incomplete_seen = False
    for line in lines:
        match = UNIT_RE.match(line)
        assert match is not None
        completed = match.group(1).lower() == "x"
        identifier = match.group(2)
        if identifier in identifiers:
            raise TaskParseError(f"중복 UNIT identifier입니다: {identifier}")
        if completed and incomplete_seen:
            raise TaskParseError("완료된 UNIT 뒤에 앞선 미완료 UNIT이 있어 완료 순서가 비정상적입니다.")
        if not completed:
            incomplete_seen = True
        identifiers.add(identifier)
        units.append(TaskUnit(identifier, match.group(3).strip(), completed))
    return tuple(units)


def parse_task(path: str | Path) -> TaskDocument:
    """UTF-8 Task 파일을 읽어 TaskDocument로 반환한다.

    파일 읽기만 수행하며 내용을 변경하지 않는다. 파일이 없으면 FileNotFoundError,
    Markdown 형식이 안전하지 않으면 TaskParseError가 발생할 수 있다.
    """

    task_path = Path(path)
    title, sections = _split_sections(task_path.read_text(encoding="utf-8"))
    units = None
    if "Implementation Units" in sections:
        units = _parse_units(sections["Implementation Units"])
    return TaskDocument(task_path, title, sections, units)
