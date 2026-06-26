"""Re-review 판단에 필요한 현재 workflow evidence를 구조적으로 파싱한다.

Approved Fixes의 FIX 식별자와 적용·승인·보류·거절 상태, Verification의 최신
성공한 전체 테스트 수, 기존 Review History의 Re-review 번호를 읽어 하나의
불변 snapshot으로 반환한다. Markdown 문서를 읽기만 하며 Review mode 선택,
모델 응답 작성 또는 workflow 파일 변경은 담당하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


FIX_RE = re.compile(
    r"^(?:-\s+\[([ xX])\]\s+|#{3,4}\s+)(FIX-\d+)(?::|\.|\s)+(.+?)\s*$"
)
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
RE_REVIEW_RE = re.compile(r"^Re-review\s+(\d+)$", flags=re.IGNORECASE)
PASSED_COUNT_RE = re.compile(
    r"(?:\b(\d+)\s+passed\b|(\d+)개(?:의)?\s+테스트가\s+모두\s+통과)",
    re.IGNORECASE,
)


class ReviewEvidenceError(ValueError):
    """workflow evidence 문서를 모호함 없이 파싱할 수 없음을 나타낸다."""


@dataclass(frozen=True)
class ApprovedFix:
    """Approved Fixes 문서의 FIX 식별자, 제목, 상태와 분류를 보관한다.

    `category`는 Re-review 진입 조건에서 코드·문서 수정 FIX와 사람 검증 항목을
    분리하는 데 사용한다. 기존 문서에 분류가 없으면 구현 FIX로 취급한다.
    """

    identifier: str
    title: str
    status: str
    category: str = "implementation-fix"


@dataclass(frozen=True)
class ApprovedFixesSnapshot:
    """중복 검증이 끝난 Approved Fixes 항목과 상태별 조회 결과를 보관한다."""

    fixes: tuple[ApprovedFix, ...]

    @property
    def re_review_items(self) -> tuple[ApprovedFix, ...]:
        """Re-review 출력에서 개별 검증해야 하는 현재 승인 FIX를 반환한다."""

        return tuple(fix for fix in self.fixes if fix.status in {"approved", "applied"})

    @property
    def actionable(self) -> tuple[ApprovedFix, ...]:
        """Re-review 대상인 구현 FIX의 승인 또는 적용 상태 항목을 반환한다."""

        return tuple(
            fix
            for fix in self.fixes
            if fix.category == "implementation-fix"
            and fix.status in {"approved", "applied"}
        )

    @property
    def applied(self) -> tuple[ApprovedFix, ...]:
        """체크 완료되어 적용된 구현 FIX만 원문 순서로 반환한다."""

        return tuple(
            fix
            for fix in self.fixes
            if fix.category == "implementation-fix" and fix.status == "applied"
        )

    @property
    def pending_implementation(self) -> tuple[ApprovedFix, ...]:
        """Re-review를 차단해야 하는 미적용 구현 FIX를 반환한다."""

        return tuple(
            fix
            for fix in self.fixes
            if fix.category == "implementation-fix" and fix.status == "approved"
        )

    @property
    def pending_human_verification(self) -> tuple[ApprovedFix, ...]:
        """Re-review를 차단하지 않는 미완료 사람 검증 FIX를 반환한다."""

        return tuple(
            fix
            for fix in self.fixes
            if fix.category == "human-verification" and fix.status == "approved"
        )


@dataclass(frozen=True)
class VerificationTestResult:
    """성공한 Verification command의 종류, 테스트 수와 문서 내 순서를 보관한다."""

    kind: str
    passed_count: int
    sequence: int


@dataclass(frozen=True)
class VerificationSnapshot:
    """Verification 현재 상태와 종류별 최신 성공한 전체 테스트 결과를 보관한다."""

    status: str
    latest_tests: tuple[VerificationTestResult, ...]

    @property
    def latest_passed_counts(self) -> tuple[int, ...]:
        """중복을 제거한 최신 전체 테스트 수를 문서 순서대로 반환한다."""

        return tuple(dict.fromkeys(result.passed_count for result in self.latest_tests))


@dataclass(frozen=True)
class ReviewHistorySnapshot:
    """기존 Re-review 번호와 다음에 사용할 결정론적 번호를 보관한다."""

    re_review_numbers: tuple[int, ...]
    next_re_review_number: int


@dataclass(frozen=True)
class ReviewEvidence:
    """Approved Fixes, Verification과 Review History의 현재 snapshot을 묶는다."""

    approved_fixes: ApprovedFixesSnapshot
    verification: VerificationSnapshot
    review_history: ReviewHistorySnapshot


def _section_name(line: str) -> str | None:
    """Markdown heading이면 section 이름을 반환하고 일반 본문이면 None을 반환한다."""

    match = HEADING_RE.match(line.strip())
    return match.group(2).strip() if match else None


def parse_approved_fixes(path: str | Path) -> ApprovedFixesSnapshot:
    """Approved Fixes 문서에서 FIX ID와 적용·승인·보류·거절 상태를 파싱한다.

    `Approved Fixes` section의 checked 항목은 `applied`, unchecked 항목은
    `approved`로 분류한다. `Rejected or Deferred Suggestions` 아래 FIX heading은
    heading 문구에 따라 `rejected` 또는 `deferred`로 분류한다. 중복 FIX ID는
    현재 상태가 모호하므로 ReviewEvidenceError를 발생시킨다.
    """

    document = Path(path)
    if not document.exists() or not document.read_text(encoding="utf-8").strip():
        return ApprovedFixesSnapshot(fixes=())

    text = document.read_text(encoding="utf-8")
    category_by_identifier = _parse_fix_categories(text)
    fixes: list[ApprovedFix] = []
    fixes_by_identifier: dict[str, ApprovedFix] = {}
    current_section = ""
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = _section_name(line)
        if heading and line.startswith("## "):
            current_section = heading
            continue
        match = FIX_RE.match(stripped)
        if not match:
            continue
        identifier = match.group(2)
        title = match.group(3).strip()
        checkbox = match.group(1)
        section_lower = current_section.lower()
        if "rejected" in section_lower:
            lowered = stripped.lower()
            status = "rejected" if "rejected" in lowered or "거절" in stripped else "deferred"
        elif current_section == "Approved Fixes":
            status = "applied" if checkbox and checkbox.lower() == "x" else "approved"
        else:
            continue
        existing = fixes_by_identifier.get(identifier)
        if existing:
            if (
                current_section == "Approved Fixes"
                and checkbox is None
                and existing.title == title
                and existing.status in {"approved", "applied"}
            ):
                continue
            raise ReviewEvidenceError(
                f"Approved Fixes의 FIX ID가 중복되었습니다: {identifier}"
            )
        fix = ApprovedFix(
            identifier=identifier,
            title=title,
            status=status,
            category=category_by_identifier.get(identifier, "implementation-fix"),
        )
        fixes.append(fix)
        fixes_by_identifier[identifier] = fix
    return ApprovedFixesSnapshot(fixes=tuple(fixes))


def _parse_fix_categories(text: str) -> dict[str, str]:
    """FIX 상세 heading 아래의 `분류:` 값을 FIX ID별 category로 반환한다."""

    categories: dict[str, str] = {}
    current_identifier: str | None = None
    category_pending_for: str | None = None
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and category_pending_for is None:
            continue
        detail = re.match(r"^###\s+(FIX-\d+)(?::|\.|\s)+", stripped)
        if detail:
            current_identifier = detail.group(1)
            category_pending_for = None
            continue
        if stripped.startswith("### "):
            current_identifier = None
            category_pending_for = None
            continue
        if category_pending_for is not None:
            if not stripped:
                continue
            if stripped in {"implementation-fix", "human-verification"}:
                categories[category_pending_for] = stripped
            category_pending_for = None
            continue
        if current_identifier is None:
            continue
        if stripped.startswith("분류:") or stripped.lower().startswith("category:"):
            value = stripped.partition(":")[2].strip()
            if value in {"implementation-fix", "human-verification"}:
                categories[current_identifier] = value
            elif not value:
                category_pending_for = current_identifier
    return categories


def _verification_status(lines: list[str]) -> str:
    """fenced code 밖 Verification Status section의 현재 값을 반환한다."""

    in_fence = False
    in_status = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            in_status = stripped == "## Verification Status"
            continue
        if in_status and stripped:
            lowered = stripped.lower()
            return lowered if lowered in {"pending", "passed", "failed"} else "present"
    return "present"


def _command_records(lines: list[str]) -> tuple[tuple[str, str, str], ...]:
    """Verification의 Command, Result, Status block을 문서 순서대로 반환한다."""

    records: list[tuple[str, str, str]] = []
    command: list[str] = []
    result: list[str] = []
    status = ""
    field: str | None = None
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if field == "command":
                command.append(line)
            elif field == "result":
                result.append(line)
            in_fence = not in_fence
            continue
        if not in_fence and stripped == "Command:":
            if command:
                records.append(("\n".join(command), "\n".join(result), status))
            command, result, status = [], [], ""
            field = "command"
            continue
        if not in_fence and stripped == "Result:" and command:
            field = "result"
            continue
        if not in_fence and stripped.startswith("Status:") and command:
            status = stripped.partition(":")[2].strip().lower()
            field = None
            records.append(("\n".join(command), "\n".join(result), status))
            command, result, status = [], [], ""
            continue
        if field == "command":
            command.append(line)
        elif field == "result":
            result.append(line)
    if command:
        records.append(("\n".join(command), "\n".join(result), status))
    return tuple(records)


def parse_verification(path: str | Path) -> VerificationSnapshot:
    """Verification에서 현재 상태와 종류별 최신 성공한 전체 테스트 수를 파싱한다.

    `python -m pytest` 전체 실행과 `python -m unittest discover` 전체 실행만
    최종 회귀 수치로 취급한다. 같은 종류가 여러 번 기록됐으면 문서에서 마지막
    `Status: passed` record를 사용해 과거 중간 결과를 최신 결과와 구분한다.
    """

    document = Path(path)
    if not document.exists() or not document.read_text(encoding="utf-8").strip():
        return VerificationSnapshot(status="missing", latest_tests=())
    lines = document.read_text(encoding="utf-8").splitlines()
    latest: dict[str, VerificationTestResult] = {}
    for sequence, (command, result, status) in enumerate(_command_records(lines), start=1):
        if status != "passed":
            continue
        normalized = " ".join(
            line.strip()
            for line in command.splitlines()
            if line.strip() and not line.strip().startswith("```")
        )
        if re.search(r"\bpython\s+-m\s+pytest\s*$", normalized):
            kind = "pytest"
        elif re.search(r"\bpython\s+-m\s+unittest\s+discover(?:\s+-s\s+tests)?\s*$", normalized):
            kind = "unittest"
        else:
            continue
        counts = [
            int(first or second)
            for first, second in PASSED_COUNT_RE.findall(result)
        ]
        if counts:
            latest[kind] = VerificationTestResult(
                kind=kind,
                passed_count=counts[-1],
                sequence=sequence,
            )
    return VerificationSnapshot(
        status=_verification_status(lines),
        latest_tests=tuple(sorted(latest.values(), key=lambda item: item.sequence)),
    )


def parse_review_history(path: str | Path) -> ReviewHistorySnapshot:
    """Review 파일의 fenced code 밖 Re-review heading을 읽어 다음 번호를 계산한다."""

    document = Path(path)
    if not document.exists() or not document.read_text(encoding="utf-8").strip():
        return ReviewHistorySnapshot(re_review_numbers=(), next_re_review_number=1)
    numbers: list[int] = []
    in_fence = False
    for line in document.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line.startswith("## "):
            continue
        match = RE_REVIEW_RE.match(line[3:].strip())
        if match:
            numbers.append(int(match.group(1)))
    if len(numbers) != len(set(numbers)):
        raise ReviewEvidenceError("Review History의 Re-review 번호가 중복되었습니다.")
    return ReviewHistorySnapshot(
        re_review_numbers=tuple(numbers),
        next_re_review_number=max(numbers, default=0) + 1,
    )


def build_review_evidence(
    *,
    approved_fixes_path: str | Path,
    verification_path: str | Path,
    review_path: str | Path,
) -> ReviewEvidence:
    """세 workflow 문서를 읽어 Re-review current-state snapshot을 생성한다."""

    return ReviewEvidence(
        approved_fixes=parse_approved_fixes(approved_fixes_path),
        verification=parse_verification(verification_path),
        review_history=parse_review_history(review_path),
    )
