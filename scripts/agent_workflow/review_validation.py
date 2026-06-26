"""Antigravity review Markdown의 구조와 완료 조건을 검증한다.

Review 파일 경로를 입력받아 파일 존재, 템플릿 잔존, 필수 section, 실제
review 본문과 허용 Verdict를 판정한다. 자동 실행과 수동 fallback 모두 같은
Verdict 계약을 사용하며 파일을 수정하거나 Agent subprocess를 실행하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


ALLOWED_VERDICTS = ("PASS", "CHANGES REQUIRED", "BLOCKED")
INITIAL_REQUIRED_SECTIONS = (
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
REREVIEW_REQUIRED_SECTIONS = (
    "Existing Problems Status",
    "Approved Fixes Verification",
    "Verification Evidence",
    "New Problems Found",
    "Required Fixes Before PR",
    "Verdict",
)
HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
REREVIEW_RE = re.compile(r"^Re-review\s+(\d+)$", flags=re.IGNORECASE)


@dataclass(frozen=True)
class ReviewValidation:
    """Review 파일의 검증 상태, Verdict와 누락 section을 보관한다."""

    status: str
    completed: bool
    verdict: str | None = None
    missing_sections: tuple[str, ...] = ()


def _sections(text: str) -> list[tuple[int, str, str]]:
    """fenced code block 밖의 2·3단계 heading과 본문을 순서대로 반환한다."""

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
        if match:
            headings.append((len(match.group(1)), match.group(2).strip(), index))

    sections: list[tuple[int, str, str]] = []
    for position, (level, name, start) in enumerate(headings):
        end = headings[position + 1][2] if position + 1 < len(headings) else len(lines)
        sections.append((level, name, "\n".join(lines[start + 1 : end]).strip()))
    return sections


def _normalized_verdict(body: str) -> str | None:
    """Verdict 본문에서 Markdown 강조를 제거한 현행 허용 Verdict 하나를 반환한다."""

    for line in body.splitlines():
        candidate = line.strip().lstrip("- ").strip()
        if candidate.startswith("**"):
            candidate = candidate[2:]
        candidate_upper = candidate.upper()
        for verdict in sorted(ALLOWED_VERDICTS, key=len, reverse=True):
            if not candidate_upper.startswith(verdict):
                continue
            remainder = candidate[len(verdict) :]
            if remainder.startswith("**"):
                remainder = remainder[2:]
            remainder = remainder.strip()
            if not remainder or remainder.startswith((":", "(", "-", "—")):
                return verdict
    return None


def _has_review_body(sections: dict[str, str], verdict_heading: str = "Verdict") -> bool:
    """Verdict 외 section 중 하나 이상에 실질적인 본문이 있는지 판정한다."""

    return any(body.strip() for name, body in sections.items() if name != verdict_heading)


def validate_review_file(path: str | Path) -> ReviewValidation:
    """Review 파일이 workflow 완료 조건을 충족하는지 읽기 전용으로 판정한다.

    파일이 없거나 비어 있으면 각각 `not_started`, `empty`를 반환한다. heading만
    있는 초기 파일은 `template_only`, 구조나 본문 또는 Verdict가 부족하면
    구체적인 미완성 상태를 반환한다. 모든 조건을 만족하면 `completed`와 정규화된
    Verdict를 반환한다.
    """

    review_path = Path(path)
    if not review_path.exists():
        return ReviewValidation("not_started", False)
    text = review_path.read_text(encoding="utf-8")
    if not text.strip():
        return ReviewValidation("empty", False)

    parsed = _sections(text)
    if not parsed or not any(body for _, _, body in parsed):
        return ReviewValidation("template_only", False)

    initial_sections = {
        name: body for level, name, body in parsed if level == 2 and not REREVIEW_RE.match(name)
    }
    missing_initial = tuple(
        name for name in INITIAL_REQUIRED_SECTIONS if name not in initial_sections
    )
    if missing_initial:
        return ReviewValidation(
            "missing_sections",
            False,
            missing_sections=missing_initial,
        )
    if not _has_review_body(initial_sections):
        return ReviewValidation("no_review_body", False)

    review_sections = initial_sections
    required_sections = INITIAL_REQUIRED_SECTIONS
    rereview_positions = [
        index
        for index, (level, name, _) in enumerate(parsed)
        if level == 2 and REREVIEW_RE.match(name)
    ]
    if rereview_positions:
        start = rereview_positions[-1]
        review_sections = {}
        for level, name, body in parsed[start + 1 :]:
            if level == 2:
                break
            if level == 3:
                review_sections[name] = body
        required_sections = REREVIEW_REQUIRED_SECTIONS
        missing_rereview = tuple(
            name for name in required_sections if name not in review_sections
        )
        if missing_rereview:
            return ReviewValidation(
                "missing_sections",
                False,
                missing_sections=missing_rereview,
            )
        if not _has_review_body(review_sections):
            return ReviewValidation("no_review_body", False)

    verdict_body = review_sections.get("Verdict", "")
    if not verdict_body.strip():
        return ReviewValidation("missing_verdict", False)
    verdict = _normalized_verdict(verdict_body)
    if verdict is None:
        return ReviewValidation("invalid_verdict", False)
    return ReviewValidation("completed", True, verdict=verdict)
