"""Antigravity UNIT Review 응답을 검증하고 Review 이력에 안전하게 누적한다.

모델 stdout과 선택된 ReviewTarget을 입력받아 heading, 필수 section, 본문,
Verdict와 finding 식별자를 검증한다. 검증된 section만 기존 Review 파일 끝에
append하며, 기존 이력과 Unit Review Status를 메모리에서 보존한 뒤 임시 파일의
원자적 교체로 반영한다. PASS Verdict이면 선택 UNIT의 Review Status도 같은
쓰기에서 완료 처리한다. Re-review에서는 Approved Fixes, 최신 Verification과
계산된 다음 번호를 모델 출력과 대조해 과거 상태가 현재 결론으로 기록되는 것을
차단한다. 마지막 UNIT Integration Review가 PASS이면 비어 있는 상단 Review
요약 placeholder만 검증된 section 내용으로 함께 갱신한다.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import tempfile

from .review_context import ReviewTarget
from .review_evidence import ReviewEvidence
from .review_unit_status import (
    ReviewUnitStatusError,
    render_review_with_passed_unit,
    render_review_with_unit_status,
)
from .task_parser import TaskDocument


UNIT_REQUIRED_SECTIONS = (
    "Review Scope",
    "Requirement Coverage",
    "Previous UNIT Contract Regression",
    "Code Quality / Maintainability",
    "Scope Control",
    "Verification Evidence",
    "Problems Found",
    "Required Fixes Before Next UNIT",
    "Verdict",
)
INTEGRATION_REQUIRED_SECTIONS = (
    "Review Scope",
    "Acceptance Criteria Coverage",
    "Cross-UNIT Contract Review",
    "Code Quality / Maintainability",
    "Security / Operational Risk",
    "Scope Control",
    "Verification Evidence",
    "Documentation Review",
    "Problems Found",
    "Required Fixes Before PR",
    "Verdict",
)
RE_REVIEW_REQUIRED_SECTIONS = (
    "Existing Problems Status",
    "Approved Fixes Verification",
    "Verification Evidence",
    "New Problems Found",
    "Required Fixes Before PR",
    "Verdict",
)
GENERAL_REQUIRED_SECTIONS = (
    "Review Summary",
    "Requirement Coverage",
    "Code Quality / Maintainability",
    "Security Review",
    "Operational Risk",
    "Scope Control",
    "Verification Review",
    "Documentation Review",
    "Problems Found",
    "Required Fixes Before PR",
    "Optional Improvements",
    "Suggested Test Commands",
    "Verdict",
)
ALLOWED_VERDICTS = ("PASS", "CHANGES REQUIRED", "BLOCKED")
ALLOWED_SCALAR_TRAILING_PUNCTUATION = (".", "。")
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
TOP_SUMMARY_SECTIONS = (
    "Review Summary",
    "Problems Found",
    "Required Fixes Before PR",
    "Optional Improvements",
    "Suggested Test Commands",
    "Risk Notes",
)


class ReviewResponseError(ValueError):
    """Review 응답을 검증하거나 안전하게 append할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class ReviewResponse:
    """검증된 Review section, Verdict와 중복 판정용 fingerprint를 보관한다."""

    markdown: str
    verdict: str
    fingerprint: str


def _expected_heading(target: ReviewTarget) -> str:
    """선택 mode와 UNIT에 대응하는 정확한 2단계 heading을 반환한다."""

    label = "Integration Review" if target.mode == "integration" else "UNIT Review"
    if target.mode == "re-review":
        if target.re_review_number is None:
            raise ReviewResponseError("Re-review target에 다음 번호가 없습니다.")
        return f"Re-review {target.re_review_number}"
    if target.mode == "general":
        return "General Review"
    return f"{label}: {target.unit.identifier}"


def _required_sections(target: ReviewTarget) -> tuple[str, ...]:
    """선택 mode에 필요한 3단계 section 이름과 순서를 반환한다."""

    if target.mode == "integration":
        return INTEGRATION_REQUIRED_SECTIONS
    if target.mode == "unit":
        return UNIT_REQUIRED_SECTIONS
    if target.mode == "re-review":
        return RE_REVIEW_REQUIRED_SECTIONS
    if target.mode == "general":
        return GENERAL_REQUIRED_SECTIONS
    raise ReviewResponseError(f"지원하지 않는 Review mode입니다: {target.mode}")


def _normalize_markdown(text: str) -> str:
    """줄 끝 공백과 외곽 공백을 제거해 안정적인 section 문자열을 반환한다."""

    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _parse_sections(markdown: str) -> tuple[str, dict[str, str]]:
    """단일 2단계 heading과 순서가 보존된 3단계 section 본문을 파싱한다."""

    lines = markdown.splitlines()
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            headings.append((len(match.group(1)), match.group(2).strip(), index))
    if in_fence:
        raise ReviewResponseError("Review 응답의 code fence가 닫히지 않았습니다.")

    level_two = [(name, index) for level, name, index in headings if level == 2]
    if len(level_two) != 1 or level_two[0][1] != 0:
        raise ReviewResponseError("Review 응답은 첫 줄의 단일 2단계 heading만 허용합니다.")

    sections: dict[str, str] = {}
    for position, (level, name, start) in enumerate(headings):
        if level != 3:
            continue
        if name in sections:
            raise ReviewResponseError(f"Review section이 중복되었습니다: {name}")
        end = headings[position + 1][2] if position + 1 < len(headings) else len(lines)
        sections[name] = "\n".join(lines[start + 1 : end]).strip()
    return level_two[0][0], sections


def _parse_verdict(body: str) -> str:
    """Verdict 본문이 허용 값 하나인지 검증해 정규화된 값을 반환한다."""

    candidate = _normalize_single_scalar(body)
    if candidate.startswith("**") and candidate.endswith("**"):
        candidate = candidate[2:-2].strip()
    verdict = candidate.upper()
    if verdict not in ALLOWED_VERDICTS:
        raise ReviewResponseError(
            "Verdict는 PASS, CHANGES REQUIRED, BLOCKED 중 하나여야 합니다."
        )
    return verdict


def _normalize_single_scalar(body: str) -> str:
    """한 줄 scalar 또는 한 줄 Markdown bullet scalar의 값을 반환한다.

    Antigravity가 `없음`이나 `PASS`처럼 단일 값으로 써야 하는 section을
    `- 없음`, `- PASS` 형태로 반환하거나 허용된 종결부호 하나를 붙인 경우만
    동일 의미로 취급한다. 여러 줄 목록이나 임의의 복합 Markdown은 원문을
    유지해 기존 검증에서 실패하게 한다.
    """

    lines = [line.strip() for line in body.strip().splitlines() if line.strip()]
    if len(lines) != 1:
        return body.strip()
    line = lines[0]
    if line.startswith("- "):
        line = line[2:].strip()
    if line.endswith(ALLOWED_SCALAR_TRAILING_PUNCTUATION):
        line = line[:-1].strip()
    return line


def _validate_findings(sections: dict[str, str], unit_identifier: str) -> None:
    """Problems Found의 finding 식별자가 선택 UNIT 형식을 따르는지 검증한다."""

    finding_section = (
        "New Problems Found" if "New Problems Found" in sections else "Problems Found"
    )
    body = sections[finding_section].strip()
    expected = re.compile(
        rf"^-\s+\[ \]\s+REVIEW-{re.escape(unit_identifier)}-\d{{2}}:\s+\S.+$"
    )
    finding_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip().startswith("- [ ] REVIEW-")
    ]
    malformed = [
        line.strip()
        for section_body in sections.values()
        for line in section_body.splitlines()
        if "REVIEW-" in line and not expected.match(line.strip())
    ]
    if malformed:
        raise ReviewResponseError(
            f"Review finding 식별자가 선택 UNIT 형식과 다릅니다: {malformed[0]}"
        )
    normalized_body = _normalize_single_scalar(body)
    if normalized_body not in {"없음", "None", "NONE"} and not finding_lines:
        raise ReviewResponseError(
            "Problems Found에 문제가 있으면 REVIEW-<UNIT>-NN checklist가 필요합니다."
        )


def _validate_re_review_evidence(
    sections: dict[str, str],
    evidence: ReviewEvidence,
) -> None:
    """Re-review 본문이 현재 FIX와 최신 전체 테스트 snapshot에 모순되는지 검증한다."""

    fixes = evidence.approved_fixes.re_review_items
    fixes_body = sections["Approved Fixes Verification"]
    no_fix_phrases = (
        "승인된 수정 항목이 없습니다",
        "승인된 수정 항목이 없",
        "검증할 내역이 없습니다",
        "approved fixes 없음",
        "no approved fixes",
    )
    if fixes and any(phrase.lower() in fixes_body.lower() for phrase in no_fix_phrases):
        raise ReviewResponseError("현재 Approved Fixes가 존재하는데 없다고 작성했습니다.")
    if fixes:
        missing = tuple(fix.identifier for fix in fixes if fix.identifier not in fixes_body)
        if missing:
            raise ReviewResponseError(
                "Approved Fixes Verification에 현재 FIX ID가 누락되었습니다: "
                + ", ".join(missing)
            )
        for fix in evidence.approved_fixes.pending_human_verification:
            matching_lines = [
                line
                for line in fixes_body.splitlines()
                if fix.identifier in line
            ]
            combined = "\n".join(matching_lines)
            if not matching_lines:
                continue
            has_pending = re.search(
                r"pending|미완료|대기",
                combined,
                flags=re.IGNORECASE,
            )
            has_category = (
                "human-verification" in combined
                or "사람 검증" in combined
                or "수동 검증" in combined
            )
            if not has_pending or not has_category:
                raise ReviewResponseError(
                    "pending human-verification FIX가 현재 상태와 다르게 작성되었습니다: "
                    f"{fix.identifier}"
                )

    latest_counts = evidence.verification.latest_passed_counts
    verification_body = sections["Verification Evidence"]
    if latest_counts and not all(
        re.search(rf"\b{count}\s*(?:passed|개)", verification_body, flags=re.IGNORECASE)
        for count in latest_counts
    ):
        raise ReviewResponseError(
            "Verification Evidence가 최신 전체 테스트 수를 포함하지 않습니다: "
            + ", ".join(str(count) for count in latest_counts)
        )
    stale_current_lines = [
        line
        for line in verification_body.splitlines()
        if re.search(r"현재|최신|최종|current|latest|final", line, flags=re.IGNORECASE)
        and any(
            int(count) not in latest_counts
            for count in re.findall(r"\b(\d+)\s+(?:passed|개)", line, flags=re.IGNORECASE)
        )
    ]
    if stale_current_lines:
        raise ReviewResponseError("Verification Evidence가 과거 테스트 수를 현재 결과로 작성했습니다.")


def validate_review_response(
    response: str,
    target: ReviewTarget,
    evidence: ReviewEvidence | None = None,
) -> ReviewResponse:
    """모델 stdout이 선택된 UNIT Review 출력 계약을 충족하는지 검증한다.

    응답이 비어 있거나 preamble, 잘못된 heading, 누락·추가·빈 section, 잘못된
    Verdict 또는 finding ID를 포함하면 ReviewResponseError를 발생시킨다.
    파일을 읽거나 변경하지 않는다.
    """

    markdown = _normalize_markdown(response)
    if not markdown:
        raise ReviewResponseError("Antigravity Review 응답이 비어 있습니다.")
    heading, sections = _parse_sections(markdown)
    expected_heading = _expected_heading(target)
    if heading != expected_heading:
        raise ReviewResponseError(
            f"Review heading이 선택 대상과 다릅니다: expected '{expected_heading}'"
        )

    required = _required_sections(target)
    actual = tuple(sections)
    if actual != required:
        missing = tuple(name for name in required if name not in sections)
        unexpected = tuple(name for name in actual if name not in required)
        details = []
        if missing:
            details.append(f"누락: {', '.join(missing)}")
        if unexpected:
            details.append(f"추가: {', '.join(unexpected)}")
        if not details:
            details.append("section 순서가 출력 계약과 다름")
        raise ReviewResponseError("Review section 구조가 올바르지 않습니다. " + "; ".join(details))

    empty = tuple(name for name in required if not sections[name].strip())
    if empty:
        raise ReviewResponseError(
            f"Review section 본문이 비어 있습니다: {', '.join(empty)}"
        )
    verdict = _parse_verdict(sections["Verdict"])
    _validate_findings(sections, target.unit.identifier)
    if target.mode == "re-review":
        if evidence is None:
            raise ReviewResponseError("Re-review current-state evidence가 없습니다.")
        _validate_re_review_evidence(sections, evidence)
    fingerprint = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return ReviewResponse(markdown=markdown, verdict=verdict, fingerprint=fingerprint)


def _atomic_write(path: Path, text: str) -> None:
    """같은 directory의 임시 파일을 교체해 기존 파일의 부분 쓰기를 방지한다."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _find_top_section_ranges(text: str) -> dict[str, tuple[int, int]]:
    """Review 파일 상단의 canonical summary section 본문 범위를 찾는다.

    Unit Review와 Integration Review 이력에 있는 동명 section은 제외하고, 첫
    Review history heading 이전에 위치한 2단계 section만 대상으로 삼는다. 모든
    placeholder가 하나씩 존재해야 하며 중복되거나 누락되면 자동 요약 갱신을
    중단할 수 있도록 ReviewResponseError를 발생시킨다.
    """

    lines = text.splitlines()
    headings: list[tuple[int, str, int]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match and match.group(1) == "##":
            headings.append((index, match.group(2).strip(), len(match.group(1))))

    history_start = len(lines)
    history_prefixes = ("UNIT Review:", "Integration Review:", "Re-review ")
    for index, name, _level in headings:
        if name.startswith(history_prefixes):
            history_start = index
            break

    ranges: dict[str, tuple[int, int]] = {}
    for position, (index, name, _level) in enumerate(headings):
        if index >= history_start or name not in TOP_SUMMARY_SECTIONS:
            continue
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        end = min(end, history_start)
        if name in ranges:
            raise ReviewResponseError(f"상단 Review 요약 section이 중복되었습니다: {name}")
        ranges[name] = (index + 1, end)

    missing = [name for name in TOP_SUMMARY_SECTIONS if name not in ranges]
    if missing:
        raise ReviewResponseError(
            "상단 Review 요약 placeholder가 없습니다: " + ", ".join(missing)
        )
    return ranges


def _require_empty_top_placeholders(
    lines: list[str], ranges: dict[str, tuple[int, int]]
) -> None:
    """상단 summary placeholder가 비어 있는지 검증한다.

    사람이 이미 작성했거나 이전 자동 갱신이 완료된 내용을 덮어쓰지 않기 위해
    공백 외 본문이 하나라도 있으면 실패시킨다.
    """

    non_empty = [
        name
        for name, (start, end) in ranges.items()
        if any(line.strip() for line in lines[start:end])
    ]
    if non_empty:
        raise ReviewResponseError(
            "상단 Review 요약 section에 기존 내용이 있어 자동 갱신하지 않습니다: "
            + ", ".join(non_empty)
        )


def _section_as_bullets(body: str) -> str:
    """Integration Review 본문을 상단 요약용 Markdown bullet 목록으로 변환한다."""

    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return "- 없음"
    if all(line.startswith("- ") for line in lines):
        return "\n".join(lines)
    return "\n".join(f"- {line}" for line in lines)


def _task_test_commands(task: TaskDocument) -> str:
    """Task의 Test commands section을 Suggested Test Commands 본문으로 반환한다."""

    commands = task.sections.get("Test commands", "").strip()
    return commands or "- Verification 문서의 최신 검증 명령을 확인한다."


def _integration_top_summary(
    task: TaskDocument,
    response: ReviewResponse,
    sections: dict[str, str],
) -> dict[str, str]:
    """검증된 Integration Review section에서 상단 summary 본문을 생성한다."""

    problems = _normalize_single_scalar(sections["Problems Found"])
    required = _normalize_single_scalar(sections["Required Fixes Before PR"])
    problem_body = "- 없음" if problems in {"없음", "None", "NONE"} else sections["Problems Found"].strip()
    required_body = (
        "- 없음"
        if required in {"없음", "None", "NONE"}
        else sections["Required Fixes Before PR"].strip()
    )
    summary = (
        f"{task.title} 작업의 UNIT Review와 최종 Integration Review를 완료했다.\n\n"
        f"- 최종 Verdict: {response.verdict}\n"
        f"- Acceptance Criteria: {sections['Acceptance Criteria Coverage'].strip()}\n"
        f"- Cross-UNIT Contract: {sections['Cross-UNIT Contract Review'].strip()}\n"
        f"- Verification Evidence: {sections['Verification Evidence'].strip()}"
    )
    risk_notes = _section_as_bullets(sections["Security / Operational Risk"])
    return {
        "Review Summary": summary,
        "Problems Found": problem_body,
        "Required Fixes Before PR": required_body,
        "Optional Improvements": "- 없음",
        "Suggested Test Commands": _task_test_commands(task),
        "Risk Notes": risk_notes,
    }


def _render_integration_summary(
    task: TaskDocument,
    base: str,
    response: ReviewResponse,
    target: ReviewTarget,
) -> str:
    """UNIT-08 Integration Review PASS 이후 비어 있는 상단 요약을 갱신한다.

    마지막 UNIT의 Integration Review가 PASS인 경우에만 동작한다. Review history는
    변경하지 않고 canonical 상단 placeholder section의 빈 본문만 교체한다.
    기존 내용이 있거나 placeholder 구조가 불완전하면 파일을 수정하지 않도록
    예외를 발생시킨다.
    """

    if (
        target.mode != "integration"
        or response.verdict != "PASS"
        or target.position != target.total_units
    ):
        return base
    if (
        not task.implementation_units
        or target.unit.identifier != task.implementation_units[-1].identifier
    ):
        raise ReviewResponseError("Integration Review 대상이 마지막 UNIT이 아닙니다.")

    _heading, sections = _parse_sections(response.markdown)
    replacements = _integration_top_summary(task, response, sections)
    lines = base.splitlines()
    ranges = _find_top_section_ranges(base)
    _require_empty_top_placeholders(lines, ranges)

    updated = list(lines)
    for name in reversed(TOP_SUMMARY_SECTIONS):
        start, end = ranges[name]
        body = replacements[name].strip().splitlines()
        updated[start:end] = [""] + body + [""]
    return "\n".join(updated).rstrip() + "\n"


def append_review_response(
    task: TaskDocument,
    review_path: str | Path,
    response: ReviewResponse,
    target: ReviewTarget,
) -> None:
    """검증된 Review section과 Verdict 기반 status를 원자적으로 반영한다.

    기존 Review 파일이 없거나 Unit Review Status가 없으면 Task 기준 checklist를
    최종 문자열에 포함한다. 동일한 정규화 section이 이미 있으면 중복으로
    거부한다. PASS이면 선택 UNIT만 `[x]`로 바꾸고 CHANGES REQUIRED 또는
    BLOCKED이면 모든 체크 상태를 유지한다. 모든 검증과 최종 문자열 구성이
    끝난 뒤에만 원자적으로 교체한다.
    """

    path = Path(review_path)
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if target.mode == "general":
        normalized_original = _normalize_markdown(original)
        if response.markdown in normalized_original:
            raise ReviewResponseError("동일한 Review section이 이미 기록되어 있습니다.")
        prefix = original.rstrip() if original.strip() else f"# Antigravity Review: {task.title}"
        _atomic_write(path, f"{prefix}\n\n{response.markdown}\n")
        return
    base = render_review_with_unit_status(task, original)
    task_matches = [
        unit
        for unit in task.implementation_units
        if unit.identifier == target.unit.identifier
        and unit.title == target.unit.title
    ]
    if len(task_matches) != 1 or not target.unit.completed:
        raise ReviewResponseError("선택 Review UNIT이 현재 Task 완료 상태와 다릅니다.")
    normalized_base = _normalize_markdown(base)
    if response.markdown in normalized_base:
        raise ReviewResponseError("동일한 Review section이 이미 기록되어 있습니다.")
    if response.verdict == "PASS" and target.mode != "re-review":
        try:
            base = render_review_with_passed_unit(
                task,
                base,
                target.unit.identifier,
            )
        except ReviewUnitStatusError as error:
            raise ReviewResponseError(str(error)) from error
    base = _render_integration_summary(task, base, response, target)
    updated = f"{base.rstrip()}\n\n{response.markdown}\n"
    _atomic_write(path, updated)
