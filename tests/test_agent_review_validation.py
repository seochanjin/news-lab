"""Antigravity review 파일의 구조와 Verdict 완료 판정을 검증한다.

임시 Markdown 파일만 사용하며 실제 repository, 외부 Agent 또는 network를
변경하지 않는다. 템플릿과 각 미완성 조건이 완료로 오인되지 않는 회귀를 막는다.
"""

from pathlib import Path
import tempfile
import unittest

from scripts.agent_workflow.review_validation import (
    ALLOWED_VERDICTS,
    INITIAL_REQUIRED_SECTIONS,
    validate_review_file,
)


def complete_review(verdict: str = "PASS") -> str:
    """필수 section과 실질 본문을 포함한 테스트용 최초 review Markdown을 반환한다."""

    parts = ["# Review"]
    for section in INITIAL_REQUIRED_SECTIONS:
        parts.extend(
            [
                "",
                f"## {section}",
                "",
                f"- **{verdict}**" if section == "Verdict" else f"{section} 검토 결과",
            ]
        )
    return "\n".join(parts) + "\n"


class ReviewValidationTests(unittest.TestCase):
    """Review 파일의 미완성 분류와 허용 Verdict 인식을 검증한다."""

    def test_missing_empty_and_template_files_are_incomplete(self) -> None:
        """파일 없음, 빈 파일과 heading-only 템플릿을 완료로 처리하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            self.assertEqual(validate_review_file(path).status, "not_started")
            path.write_text("", encoding="utf-8")
            self.assertEqual(validate_review_file(path).status, "empty")
            path.write_text(
                "# Review\n\n## Review Summary\n\n## Problems Found\n\n## Verdict\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_review_file(path).status, "template_only")

    def test_missing_section_body_and_verdict_are_incomplete(self) -> None:
        """필수 section, 실제 본문 또는 Verdict 누락을 각각 미완성으로 판정한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            path.write_text(
                complete_review().replace("## Security Review\n\nSecurity Review 검토 결과\n", ""),
                encoding="utf-8",
            )
            self.assertEqual(validate_review_file(path).status, "missing_sections")

            sections_only = complete_review()
            for section in INITIAL_REQUIRED_SECTIONS:
                if section != "Verdict":
                    sections_only = sections_only.replace(f"{section} 검토 결과", "")
            path.write_text(sections_only, encoding="utf-8")
            self.assertEqual(validate_review_file(path).status, "no_review_body")

            path.write_text(
                complete_review().replace("- **PASS**", ""),
                encoding="utf-8",
            )
            self.assertEqual(validate_review_file(path).status, "missing_verdict")

    def test_invalid_verdict_is_rejected(self) -> None:
        """예전 Verdict와 허용 Verdict를 임의 확장한 문구를 거부하는지 검증한다."""

        for verdict in ("APPROVED", "PASS MAYBE"):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "review.md"
                path.write_text(complete_review(verdict), encoding="utf-8")
                self.assertEqual(validate_review_file(path).status, "invalid_verdict")

    def test_all_allowed_verdicts_complete_manual_review(self) -> None:
        """세 허용 Verdict를 가진 완성된 수동 review가 모두 완료로 판정되는지 검증한다."""

        for verdict in ALLOWED_VERDICTS:
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "review.md"
                path.write_text(complete_review(verdict), encoding="utf-8")
                result = validate_review_file(path)
                self.assertTrue(result.completed)
                self.assertEqual(result.verdict, verdict)

    def test_allowed_verdict_can_include_markdown_and_explanation(self) -> None:
        """강조된 허용 Verdict 뒤 설명이 있는 기존 review 형식을 인식한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            path.write_text(
                complete_review().replace(
                    "- **PASS**",
                    "- **PASS** (검토 조건을 충족함)",
                ),
                encoding="utf-8",
            )
            self.assertTrue(validate_review_file(path).completed)

    def test_latest_rereview_requires_complete_structure_and_verdict(self) -> None:
        """최신 Re-review의 필수 하위 section과 Verdict가 최종 상태를 결정한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            path.write_text(
                complete_review()
                + "\n## Re-review 1\n"
                + "\n".join(
                    f"\n### {name}\n\n{name} 결과"
                    for name in (
                        "Existing Problems Status",
                        "Approved Fixes Verification",
                        "Verification Evidence",
                        "New Problems Found",
                        "Required Fixes Before PR",
                    )
                )
                + "\n\n### Verdict\n\n**CHANGES REQUIRED**\n",
                encoding="utf-8",
            )
            result = validate_review_file(path)
            self.assertTrue(result.completed)
            self.assertEqual(result.verdict, "CHANGES REQUIRED")


if __name__ == "__main__":
    unittest.main()
