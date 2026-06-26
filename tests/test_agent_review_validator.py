"""Antigravity UNIT Review stdout의 구조와 선택 대상 일치 검증을 확인한다.

UNIT·통합 Review fixture로 필수 heading, section, Verdict와 finding ID를
검증하며 실제 Review 파일, Git repository 또는 외부 Agent를 변경하지 않는다.
"""

import unittest

from scripts.agent_workflow.review_context import ReviewTarget
from scripts.agent_workflow.review_evidence import (
    ApprovedFix,
    ApprovedFixesSnapshot,
    ReviewEvidence,
    ReviewHistorySnapshot,
    VerificationSnapshot,
    VerificationTestResult,
)
from scripts.agent_workflow.review_response import (
    ReviewResponseError,
    validate_review_response,
)
from scripts.agent_workflow.task_parser import TaskUnit


def target(*, integration: bool = False) -> ReviewTarget:
    """Validator 테스트용 UNIT 또는 통합 Review 대상을 반환한다."""

    unit = TaskUnit("UNIT-08" if integration else "UNIT-05", "응답 검증", True)
    return ReviewTarget(
        unit=unit,
        mode="integration" if integration else "unit",
        position=8 if integration else 5,
        total_units=8,
    )


def unit_response(
    *,
    heading: str = "## UNIT Review: UNIT-05",
    verdict: str = "PASS",
    problems: str = "없음",
) -> str:
    """모든 필수 section을 가진 UNIT Review 응답을 생성한다."""

    return f"""{heading}
### Review Scope
UNIT-05 변경만 검토함
### Requirement Coverage
충족
### Previous UNIT Contract Regression
없음
### Code Quality / Maintainability
양호
### Scope Control
범위 내
### Verification Evidence
집중 테스트 확인
### Problems Found
{problems}
### Required Fixes Before Next UNIT
없음
### Verdict
{verdict}
"""


def integration_response() -> str:
    """모든 필수 section을 가진 마지막 UNIT 통합 Review 응답을 생성한다."""

    return """## Integration Review: UNIT-08
### Review Scope
전체 Task 검토
### Acceptance Criteria Coverage
충족
### Cross-UNIT Contract Review
계약 일치
### Code Quality / Maintainability
양호
### Security / Operational Risk
추가 위험 없음
### Scope Control
범위 내
### Verification Evidence
전체 검증 확인
### Documentation Review
문서 일치
### Problems Found
없음
### Required Fixes Before PR
없음
### Verdict
PASS
"""


def re_review_target() -> ReviewTarget:
    """다음 번호가 3인 Re-review validator 대상을 반환한다."""

    return ReviewTarget(
        unit=TaskUnit("UNIT-08", "전체 회귀", True),
        mode="re-review",
        position=8,
        total_units=8,
        re_review_number=3,
    )


def general_target() -> ReviewTarget:
    """일반 Task Review validator 대상을 반환한다."""

    return ReviewTarget(
        unit=TaskUnit("TASK", "일반 검토", True),
        mode="general",
        position=1,
        total_units=1,
    )


def re_review_evidence() -> ReviewEvidence:
    """FIX-01~17과 pending human-verification FIX-09 current-state를 반환한다."""

    return ReviewEvidence(
        approved_fixes=ApprovedFixesSnapshot(
            fixes=(
                tuple(
                    ApprovedFix(f"FIX-{number:02d}", f"승인 수정 {number}", "applied")
                    for number in range(1, 9)
                )
                + (
                    ApprovedFix(
                        "FIX-09",
                        "외부 Re-review 검증",
                        "approved",
                        "human-verification",
                    ),
                )
                + tuple(
                    ApprovedFix(f"FIX-{number:02d}", f"승인 수정 {number}", "applied")
                    for number in range(10, 18)
                )
            )
        ),
        verification=VerificationSnapshot(
            status="passed",
            latest_tests=(
                VerificationTestResult("pytest", 265, 1),
                VerificationTestResult("unittest", 265, 2),
            ),
        ),
        review_history=ReviewHistorySnapshot((1, 2), 3),
    )


def re_review_response(
    *,
    heading: str = "## Re-review 3",
    fixes: str | None = None,
    verification: str = "현재 최종 전체 테스트는 265 passed입니다.",
) -> str:
    """필수 section과 현재-state evidence를 가진 Re-review 응답을 생성한다."""

    fixes_body = fixes or "\n".join(
        (
            f"- FIX-{number:02d}: 적용 확인"
            if number != 9
            else "- FIX-09: human-verification pending이며 이번 Re-review PASS 후 완료 대상"
        )
        for number in range(1, 18)
    )
    return f"""{heading}
### Existing Problems Status
기존 문제 해결 확인
### Approved Fixes Verification
{fixes_body}
### Verification Evidence
{verification}
### New Problems Found
없음
### Required Fixes Before PR
없음
### Verdict
PASS
"""


def general_response() -> str:
    """일반 Review 필수 section을 모두 가진 응답을 생성한다."""

    return """## General Review
### Review Summary
전체 변경 검토
### Requirement Coverage
충족
### Code Quality / Maintainability
양호
### Security Review
추가 위험 없음
### Operational Risk
운영 위험 없음
### Scope Control
범위 내
### Verification Review
검증 확인
### Documentation Review
문서 일치
### Problems Found
없음
### Required Fixes Before PR
없음
### Optional Improvements
없음
### Suggested Test Commands
python -m pytest
### Verdict
PASS
"""


class ReviewResponseValidatorTests(unittest.TestCase):
    """UNIT Review 응답의 성공과 주요 거부 조건을 검증한다."""

    def test_accepts_complete_unit_response(self) -> None:
        """선택 UNIT의 전체 section과 PASS를 가진 응답을 정규화한다."""

        response = validate_review_response(unit_response(), target())
        self.assertEqual(response.verdict, "PASS")
        self.assertTrue(response.fingerprint)
        self.assertTrue(response.markdown.startswith("## UNIT Review: UNIT-05"))

    def test_accepts_single_markdown_bullet_scalar_sections(self) -> None:
        """실제 Antigravity의 `- 없음`, `- PASS` 단일 bullet 응답을 승인한다."""

        response = validate_review_response(
            unit_response(
                verdict="- PASS",
                problems="- 없음",
            ).replace(
                "### Previous UNIT Contract Regression\n없음\n",
                "### Previous UNIT Contract Regression\n- 없음\n",
            ).replace(
                "### Required Fixes Before Next UNIT\n없음\n",
                "### Required Fixes Before Next UNIT\n- 없음\n",
            ),
            target(),
        )
        self.assertEqual(response.verdict, "PASS")

    def test_accepts_allowed_scalar_trailing_punctuation(self) -> None:
        """`없음.`과 `PASS.`처럼 허용된 단일 scalar 종결부호만 정규화한다."""

        response = validate_review_response(
            unit_response(
                verdict="- PASS.",
                problems="- 없음.",
            ).replace(
                "### Previous UNIT Contract Regression\n없음\n",
                "### Previous UNIT Contract Regression\n- 없음。\n",
            ).replace(
                "### Required Fixes Before Next UNIT\n없음\n",
                "### Required Fixes Before Next UNIT\n- 없음.\n",
            ),
            target(),
        )
        self.assertEqual(response.verdict, "PASS")

    def test_rejects_wrong_unit_heading_without_file_effects(self) -> None:
        """다른 UNIT heading을 선택 대상 응답으로 승인하지 않는다."""

        with self.assertRaisesRegex(ReviewResponseError, "heading"):
            validate_review_response(
                unit_response(heading="## UNIT Review: UNIT-04"),
                target(),
            )

    def test_rejects_missing_or_empty_required_section(self) -> None:
        """응답 잘림으로 필수 section이 없거나 본문이 비면 실패하는지 검증한다."""

        missing = unit_response().replace(
            "### Scope Control\n범위 내\n",
            "",
        )
        empty = unit_response().replace(
            "### Verification Evidence\n집중 테스트 확인\n",
            "### Verification Evidence\n",
        )
        for response in (missing, empty):
            with self.subTest(response=response):
                with self.assertRaises(ReviewResponseError):
                    validate_review_response(response, target())

    def test_rejects_invalid_verdict_and_finding_identifier(self) -> None:
        """허용되지 않은 Verdict와 다른 UNIT finding ID를 각각 거부한다."""

        cases = (
            unit_response(verdict="APPROVED"),
            unit_response(verdict="- MAYBE"),
            unit_response(verdict="- MAYBE."),
            unit_response(problems="- [ ] REVIEW-UNIT-04-01: 잘못된 대상"),
        )
        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(ReviewResponseError):
                    validate_review_response(response, target())

    def test_rejects_problem_text_written_as_plain_bullet(self) -> None:
        """문제가 있으면 `- 없음`이 아닌 REVIEW checklist 형식을 요구한다."""

        cases = (
            "- 문제가 있습니다.",
            "- 현재 문제가 없는 것으로 보입니다.",
        )
        for problems in cases:
            with self.subTest(problems=problems):
                with self.assertRaisesRegex(ReviewResponseError, "REVIEW-<UNIT>-NN"):
                    validate_review_response(
                        unit_response(problems=problems),
                        target(),
                    )

    def test_accepts_selected_unit_finding_identifier(self) -> None:
        """선택 UNIT의 두 자리 finding 번호가 있는 문제 section을 승인한다."""

        response = validate_review_response(
            unit_response(
                verdict="CHANGES REQUIRED",
                problems="- [ ] REVIEW-UNIT-05-01: writer 보완 필요",
            ),
            target(),
        )
        self.assertEqual(response.verdict, "CHANGES REQUIRED")

    def test_accepts_complete_integration_response(self) -> None:
        """마지막 UNIT의 통합 heading과 전용 section 계약을 승인한다."""

        response = validate_review_response(integration_response(), target(integration=True))
        self.assertEqual(response.verdict, "PASS")
        self.assertIn("## Integration Review: UNIT-08", response.markdown)

    def test_accepts_re_review_matching_current_state(self) -> None:
        """계산된 번호, 모든 FIX ID와 최신 265 passed가 일치하는 Re-review를 승인한다."""

        response = validate_review_response(
            re_review_response(),
            re_review_target(),
            re_review_evidence(),
        )
        self.assertEqual(response.verdict, "PASS")

    def test_accepts_general_review_response(self) -> None:
        """일반 Task Review heading과 section 계약을 승인한다."""

        response = validate_review_response(general_response(), general_target())

        self.assertEqual(response.verdict, "PASS")
        self.assertTrue(response.markdown.startswith("## General Review"))

    def test_rejects_stale_re_review_number_and_current_state(self) -> None:
        """과거 번호·FIX 없음·261 passed를 현재 Re-review 결론으로 기록하지 않는다."""

        cases = (
            re_review_response(heading="## Re-review 2"),
            re_review_response(fixes="승인된 수정 항목이 없습니다."),
            re_review_response(
                verification="현재 최종 전체 테스트는 261 passed입니다."
            ),
        )
        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(ReviewResponseError):
                    validate_review_response(
                        response,
                        re_review_target(),
                        re_review_evidence(),
                    )

    def test_rejects_re_review_fix_range_without_individual_ids(self) -> None:
        """FIX 범위 표현만으로 개별 FIX 검증을 대체하지 못하게 한다."""

        with self.assertRaisesRegex(ReviewResponseError, "누락"):
            validate_review_response(
                re_review_response(fixes="- FIX-01 ~ FIX-17: 모두 적용 완료"),
                re_review_target(),
                re_review_evidence(),
            )

    def test_rejects_pending_human_verification_as_completed(self) -> None:
        """pending human-verification FIX를 구현 완료처럼 표현하면 실패한다."""

        fixes = "\n".join(
            f"- FIX-{number:02d}: 적용 확인" for number in range(1, 18)
        )
        with self.assertRaisesRegex(ReviewResponseError, "human-verification"):
            validate_review_response(
                re_review_response(fixes=fixes),
                re_review_target(),
                re_review_evidence(),
            )


if __name__ == "__main__":
    unittest.main()
