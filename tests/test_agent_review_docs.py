"""Antigravity Review workflow 문서의 현재 계약 정합성을 검증한다.

문서 파일만 읽어서 UNIT Review와 최종 Review action 분리, 허용 Verdict 목록,
수동 fallback 계약과 보조 review artifact의 채움 상태를 확인한다. 외부 Agent,
Git subprocess 또는 workflow 파일 쓰기는 수행하지 않는다.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERDICTS = ("PASS", "CHANGES REQUIRED", "BLOCKED")
OLD_VERDICTS = ("APPROVED", "APPROVED WITH NOTES")


class ReviewDocsTests(unittest.TestCase):
    """Review 관련 문서가 현재 action과 Verdict 계약을 설명하는지 검증한다."""

    def read_doc(self, relative_path: str) -> str:
        """Repository 기준 상대 경로의 문서를 UTF-8 text로 읽어 반환한다."""

        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_review_guides_use_current_verdict_contract(self) -> None:
        """핵심 Review 문서가 PASS/CHANGES REQUIRED/BLOCKED만 계약으로 설명한다."""

        for relative_path in (
            "docs/agent/antigravity-review.md",
            "docs/agent/usage-guide.md",
            "docs/agent/backend-workflow.md",
            "docs/prompts/antigravity-review.md",
        ):
            with self.subTest(path=relative_path):
                text = self.read_doc(relative_path)
                for verdict in CURRENT_VERDICTS:
                    self.assertIn(verdict, text)
                for verdict in OLD_VERDICTS:
                    self.assertNotIn(verdict, text)

    def test_unit_and_final_review_actions_are_documented_as_separate(self) -> None:
        """UNIT action과 최종 action이 서로 전환되지 않는 계약을 문서에서 확인한다."""

        text = "\n".join(
            self.read_doc(path)
            for path in (
                "docs/tasks/fix-antigravity-review-automation.md",
                "docs/agent/usage-guide.md",
                "docs/agent/verification-gates.md",
            )
        )
        self.assertIn("antigravity-review-unit", text)
        self.assertIn("antigravity-review", text)
        self.assertIn("별도", text)
        self.assertNotIn("마지막 UNIT은 전체 통합 Review를 수행한다", text)
        self.assertNotIn("마지막 UNIT의 PASS는 전체 통합\nReview 통과를 뜻한다", text)

    def test_current_coderabbit_artifact_has_review_sections(self) -> None:
        """현재 브랜치 CodeRabbit artifact의 빈 section이 실제 요약으로 채워졌는지 검증한다."""

        text = self.read_doc("docs/reviews/fix-antigravity-review-automation-coderabbit.md")
        for heading in (
            "## Review Summary",
            "## Problems Found",
            "## Required Fixes Before PR",
            "## Optional Improvements",
            "## Suggested Test Commands",
            "## Risk Notes",
        ):
            with self.subTest(heading=heading):
                start = text.index(heading) + len(heading)
                next_heading = text.find("\n## ", start)
                body = text[start: next_heading if next_heading != -1 else len(text)]
                self.assertTrue(body.strip())


if __name__ == "__main__":
    unittest.main()
