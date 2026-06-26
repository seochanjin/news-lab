"""Approved Fixes 문서의 canonical checklist를 검증하고 필요할 때 생성한다.

`codex-fix` 실행 전에 `## Approved Fixes` 범위의 checklist와 상세
`### FIX-NN: 제목` heading을 비교한다. 상세 heading만 있으면 동일한 ID와
제목의 unchecked checklist를 section 시작에 원자적으로 삽입한다. 기존 체크
상태와 상세 설명은 보존하며, 모호한 ID·제목·번호 구조에서는 파일을 변경하지
않고 오류를 반환한다. Agent 실행이나 다른 workflow 문서 변경은 담당하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tempfile


SECTION_HEADING = "## Approved Fixes"
CHECKLIST_RE = re.compile(r"^-\s+\[([ xX])\]\s+(FIX-(\d+)):\s+(.+?)\s*$")
DETAIL_RE = re.compile(r"^###\s+(FIX-(\d+)):\s+(.+?)\s*$")
FIX_LIKE_HEADING_RE = re.compile(r"^###\s+FIX(?:\b|-)", flags=re.IGNORECASE)


class ApprovedFixesNormalizationError(ValueError):
    """Approved Fixes 구조가 모호해 안전하게 정규화할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class ApprovedFixEntry:
    """문서에서 읽은 FIX ID, 번호, 제목과 선택적 체크 상태를 보관한다."""

    identifier: str
    number: int
    title: str
    checked: bool | None


@dataclass(frozen=True)
class ApprovedFixesNormalizationResult:
    """정규화 수행 여부와 canonical Approved Fixes 항목을 반환한다."""

    created: bool
    fixes: tuple[ApprovedFixEntry, ...]


def _approved_section_bounds(lines: list[str]) -> tuple[int, int]:
    """fenced code 밖의 Approved Fixes section 본문 시작·종료 index를 반환한다."""

    in_fence = False
    start: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped == SECTION_HEADING:
            if start is not None:
                raise ApprovedFixesNormalizationError(
                    "Approved Fixes section이 중복되었습니다."
                )
            start = index + 1
            continue
        if start is not None and line.startswith("## "):
            return start, index
    if start is None:
        raise ApprovedFixesNormalizationError("Approved Fixes section이 없습니다.")
    return start, len(lines)


def _validate_identifiers(
    entries: list[ApprovedFixEntry],
    *,
    source: str,
) -> None:
    """FIX ID 중복과 1부터 이어지는 번호 누락을 검증한다."""

    identifiers = [entry.identifier for entry in entries]
    if len(set(identifiers)) != len(identifiers):
        duplicate = next(
            identifier
            for identifier in identifiers
            if identifiers.count(identifier) > 1
        )
        raise ApprovedFixesNormalizationError(
            f"{source}의 FIX ID가 중복되었습니다: {duplicate}"
        )
    numbers = [entry.number for entry in entries]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        raise ApprovedFixesNormalizationError(
            f"{source}의 FIX 번호가 1부터 순서대로 이어지지 않습니다: {numbers}"
        )


def _parse_entries(
    lines: list[str],
    start: int,
    end: int,
) -> tuple[list[ApprovedFixEntry], list[ApprovedFixEntry]]:
    """Approved Fixes 본문에서 checklist와 상세 heading을 분리해 파싱한다."""

    checklist: list[ApprovedFixEntry] = []
    details: list[ApprovedFixEntry] = []
    in_fence = False
    for line in lines[start:end]:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        checklist_match = CHECKLIST_RE.match(stripped)
        if checklist_match:
            checklist.append(
                ApprovedFixEntry(
                    identifier=checklist_match.group(2),
                    number=int(checklist_match.group(3)),
                    title=checklist_match.group(4).strip(),
                    checked=checklist_match.group(1).lower() == "x",
                )
            )
            continue
        detail_match = DETAIL_RE.match(stripped)
        if detail_match:
            details.append(
                ApprovedFixEntry(
                    identifier=detail_match.group(1),
                    number=int(detail_match.group(2)),
                    title=detail_match.group(3).strip(),
                    checked=None,
                )
            )
            continue
        if FIX_LIKE_HEADING_RE.match(stripped):
            raise ApprovedFixesNormalizationError(
                f"번호 또는 제목 형식이 잘못된 FIX heading입니다: {stripped}"
            )
    return checklist, details


def _write_atomic(path: Path, text: str) -> None:
    """같은 directory의 임시 파일을 교체해 정규화 결과를 원자적으로 기록한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def normalize_approved_fixes(path: str | Path) -> ApprovedFixesNormalizationResult:
    """Approved Fixes checklist를 검증하고 상세 heading만 있으면 생성한다.

    기존 checklist가 있으면 체크 상태를 포함한 원문을 보존하고, 상세 heading도
    존재할 때 ID·제목·순서가 정확히 같은지 검증한다. checklist 없이 유효한 상세
    heading이 있으면 unchecked checklist를 `## Approved Fixes` 바로 아래에
    삽입한다. 승인 항목을 추론할 근거가 없거나 구조가 모호하면 파일을 변경하기
    전에 ApprovedFixesNormalizationError를 발생시킨다.
    """

    document = Path(path)
    if not document.exists():
        raise ApprovedFixesNormalizationError(
            f"Approved Fixes 문서가 없습니다: {document}"
        )
    original = document.read_text(encoding="utf-8")
    lines = original.splitlines()
    start, end = _approved_section_bounds(lines)
    checklist, details = _parse_entries(lines, start, end)

    if checklist:
        _validate_identifiers(checklist, source="Approved Fixes checklist")
        if details:
            _validate_identifiers(details, source="Approved Fixes 상세 heading")
            checklist_contract = [
                (entry.identifier, entry.title) for entry in checklist
            ]
            detail_contract = [(entry.identifier, entry.title) for entry in details]
            if checklist_contract != detail_contract:
                raise ApprovedFixesNormalizationError(
                    "Approved Fixes checklist와 상세 heading의 ID·제목·순서가 다릅니다."
                )
        return ApprovedFixesNormalizationResult(
            created=False,
            fixes=tuple(checklist),
        )

    if not details:
        raise ApprovedFixesNormalizationError(
            "Approved Fixes에 checklist 또는 상세 FIX heading이 없습니다."
        )

    _validate_identifiers(details, source="Approved Fixes 상세 heading")
    checklist_lines = [
        f"- [ ] {entry.identifier}: {entry.title}" for entry in details
    ]
    content_start = start
    while content_start < end and not lines[content_start].strip():
        content_start += 1
    insertion = ["", *checklist_lines, ""]
    normalized_lines = [*lines[:start], *insertion, *lines[content_start:]]
    normalized = "\n".join(normalized_lines)
    if original.endswith("\n"):
        normalized += "\n"
    _write_atomic(document, normalized)
    generated = tuple(
        ApprovedFixEntry(
            identifier=entry.identifier,
            number=entry.number,
            title=entry.title,
            checked=False,
        )
        for entry in details
    )
    return ApprovedFixesNormalizationResult(created=True, fixes=generated)
