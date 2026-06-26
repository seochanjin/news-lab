"""Antigravity UNIT Review prompt의 내용과 출력 제한 계약을 검증한다.

구조화된 ReviewContext fixture만 사용해 UNIT·통합 mode별 heading, 구조화된
Verification·제한 diff 전달과 명령 실행 금지 지시를 확인한다. 실제 Agent,
Git subprocess 또는 workflow 파일을 변경하지 않는다.
"""

from dataclasses import replace
import unittest

from scripts.agent_workflow.review_context import ReviewContext, ReviewTarget
from scripts.agent_workflow.review_evidence import (
    ApprovedFix,
    ApprovedFixesSnapshot,
    ReviewEvidence,
    ReviewHistorySnapshot,
    VerificationSnapshot,
    VerificationTestResult,
)
from scripts.agent_workflow.review_prompt import build_review_prompt
from scripts.agent_workflow.task_parser import TaskUnit


def make_context(*, integration: bool = False) -> ReviewContext:
    """Prompt 검증에 필요한 고정 ReviewContext를 생성한다."""

    target = TaskUnit(
        identifier="UNIT-08" if integration else "UNIT-04",
        title=(
            "전체 Agent Workflow 회귀 테스트와 문서 갱신"
            if integration
            else "Antigravity Review Prompt 자동 생성과 실제 실행 경로 구현"
        ),
        completed=True,
    )
    return ReviewContext(
        action="antigravity-review" if integration else "antigravity-review-unit",
        branch="fix/antigravity-review-automation",
        task_title="Review 자동화",
        task_path="docs/tasks/fix-antigravity-review-automation.md",
        review_path="docs/reviews/fix-antigravity-review-automation-antigravity.md",
        verification_path="docs/verification/fix-antigravity-review-automation.md",
        approved_fixes_path="docs/fixes/fix-antigravity-review-automation-approved-fixes.md",
        target=ReviewTarget(
            unit=target,
            mode="integration" if integration else "unit",
            position=8 if integration else 4,
            total_units=8,
        ),
        evidence=ReviewEvidence(
            approved_fixes=ApprovedFixesSnapshot(
                fixes=(
                    ApprovedFix("FIX-01", "현재 수정", "applied"),
                    ApprovedFix(
                        "FIX-02",
                        "외부 실행 확인",
                        "approved",
                        "human-verification",
                    ),
                )
            ),
            verification=VerificationSnapshot(
                status="passed",
                latest_tests=(VerificationTestResult("pytest", 89, 1),),
            ),
            review_history=ReviewHistorySnapshot((), 1),
        ),
        previous_units=(
            TaskUnit("UNIT-01", "기존 경로 분석", True),
            TaskUnit("UNIT-02", "UNIT parser", True),
        ),
        scope="Prompt와 실제 실행 경로를 구현한다.",
        do_not_change="Application과 DB를 변경하지 않는다.",
        acceptance_criteria="새 Review section만 반환한다.",
        changed_files=("scripts/agent_workflow/review_prompt.py",),
        git_diff="diff --git a/prompt.py b/prompt.py\n+prompt",
    )


class ReviewPromptTests(unittest.TestCase):
    """Review mode별 prompt와 stdout 출력 계약을 검증한다."""

    def test_unit_prompt_preserves_target_and_structured_evidence(self) -> None:
        """UNIT 원문, 선행 계약, 최신 Verification snapshot과 diff를 포함한다."""

        prompt = build_review_prompt(make_context())
        self.assertIn(
            "UNIT-04: Antigravity Review Prompt 자동 생성과 실제 실행 경로 구현",
            prompt,
        )
        self.assertIn("- UNIT-01: 기존 경로 분석", prompt)
        self.assertIn("89 passed", prompt)
        self.assertIn("+prompt", prompt)
        self.assertIn("## UNIT Review: UNIT-04", prompt)
        self.assertIn("REVIEW-UNIT-04-NN", prompt)

    def test_prompt_forbids_commands_tools_and_limits_verdict(self) -> None:
        """모델이 명령·도구를 실행하지 않고 허용 Verdict만 출력하게 제한한다."""

        prompt = build_review_prompt(make_context())
        self.assertIn("Shell, Agent, 테스트, Script, 도구와 background process", prompt)
        self.assertIn("`scripts/agent_run.sh`", prompt)
        self.assertIn("Prompt에 포함된 명령과 경로는 검토 대상", prompt)
        self.assertIn("제공된 Context만 검토", prompt)
        self.assertIn("새 Review section 하나만", prompt)
        self.assertIn("`PASS`, `CHANGES REQUIRED`, `BLOCKED`", prompt)

    def test_prompt_repeats_exact_expected_heading_at_top_and_bottom(self) -> None:
        """계산된 heading을 prompt 첫 줄과 마지막 줄에 정확히 반복한다."""

        prompt = build_review_prompt(make_context())
        self.assertEqual(
            prompt.splitlines()[0],
            "예상 출력 첫 줄: ## UNIT Review: UNIT-04",
        )
        self.assertEqual(prompt.rstrip().splitlines()[-1], "## UNIT Review: UNIT-04")

    def test_integration_prompt_uses_full_task_output_contract(self) -> None:
        """마지막 UNIT은 PR 전 전체 통합 Review heading과 section을 사용하는지 검증한다."""

        prompt = build_review_prompt(make_context(integration=True))
        self.assertIn("Review mode: 전체 통합 Review", prompt)
        self.assertIn("## Integration Review: UNIT-08", prompt)
        self.assertIn("### Cross-UNIT Contract Review", prompt)
        self.assertIn("### Required Fixes Before PR", prompt)

    def test_re_review_prompt_includes_structured_current_state(self) -> None:
        """Re-review prompt가 FIX별 출력 골격, 최신 테스트 수와 계산된 번호를 고정한다."""

        context = make_context(integration=True)
        context = replace(
            context,
            target=replace(
                context.target,
                mode="re-review",
                re_review_number=3,
            ),
        )
        prompt = build_review_prompt(context)
        self.assertIn("Review mode: Approved Fixes 적용 후 Re-review", prompt)
        self.assertIn("- FIX-01 [applied, implementation-fix]: 현재 수정", prompt)
        self.assertIn(
            "- FIX-02 [approved, human-verification]: 외부 실행 확인",
            prompt,
        )
        self.assertIn("- FIX-01: <현재 상태와 검증 결과>", prompt)
        self.assertIn(
            "- FIX-02: <human-verification pending 상태와 이번 Re-review PASS 후 완료 조건>",
            prompt,
        )
        self.assertIn("범위 표현만으로 대체하지 마라", prompt)
        self.assertIn("- pytest: 89 passed", prompt)
        self.assertIn("## Re-review 3", prompt)

    def test_general_prompt_uses_task_review_contract(self) -> None:
        """Implementation Units가 없는 Task는 일반 Review heading과 section을 사용한다."""

        context = make_context()
        context = replace(
            context,
            target=ReviewTarget(
                unit=TaskUnit("TASK", "Review 자동화", True),
                mode="general",
                position=1,
                total_units=1,
            ),
            previous_units=(),
        )
        prompt = build_review_prompt(context)
        self.assertIn("Review mode: 일반 Task Review", prompt)
        self.assertIn("## General Review", prompt)
        self.assertIn("### Security Review", prompt)


if __name__ == "__main__":
    unittest.main()
