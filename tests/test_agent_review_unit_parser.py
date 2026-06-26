"""Task UNIT parser와 Review Status 자동 생성 계약을 검증한다.

임시 Task·Review 파일만 사용해 UNIT 원문 보존, checklist 생성, 기존 이력과
체크 상태 보존, 불일치 시 무수정 실패를 확인한다. 실제 repository workflow
문서나 외부 Agent subprocess에는 영향을 주지 않는다.
"""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workflow.review_unit_status import (
    ReviewUnitStatusError,
    ensure_review_unit_status,
    parse_review_unit_status,
)
from scripts.agent_workflow.task_parser import parse_task


def write_task(tmp_path: Path, units: str) -> Path:
    """정확한 제목 보존을 확인할 UNIT Task를 임시 경로에 생성한다."""

    path = tmp_path / "task.md"
    path.write_text(
        "# Task: Review 자동화\n\n"
        "## Goal\n\n목표\n\n"
        "## Implementation Units\n\n"
        f"{units}\n",
        encoding="utf-8",
    )
    return path


class ReviewUnitParserTests(unittest.TestCase):
    """Task UNIT과 Review checklist의 생성·검증 회귀를 확인한다."""

    def test_task_parser_preserves_identifier_state_title_and_order(self) -> None:
        """Task parser가 UNIT 식별자, 구현 상태와 제목 원문 순서를 보존하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: Parser/API 계약 유지\n"
                    "- [ ] UNIT-02: Review Status 자동 생성 구현",
                )
            )
        self.assertEqual(
            [
                (unit.identifier, unit.completed, unit.title)
                for unit in task.implementation_units or ()
            ],
            [
                ("UNIT-01", True, "Parser/API 계약 유지"),
                ("UNIT-02", False, "Review Status 자동 생성 구현"),
            ],
        )

    def test_creates_review_file_from_task_units(self) -> None:
        """Review 파일이 없으면 Task 제목과 전체 unchecked status를 생성하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(
                    root,
                    "- [x] UNIT-01: 완료된 구현\n- [ ] UNIT-02: 다음 구현",
                )
            )
            review = root / "reviews" / "review.md"
            result = ensure_review_unit_status(task, review)
            text = review.read_text(encoding="utf-8")
        self.assertTrue(result.created)
        self.assertIn("# Antigravity Review: Review 자동화", text)
        self.assertIn("## Unit Review Status", text)
        self.assertIn("- [ ] UNIT-01: 완료된 구현", text)
        self.assertIn("- [ ] UNIT-02: 다음 구현", text)

    def test_inserts_status_without_rewriting_existing_review_history(self) -> None:
        """기존 Review에 status만 삽입하고 원래 section과 본문을 보존하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: 첫 구현"))
            review = root / "review.md"
            history = (
                "# Antigravity Review: 기존 제목\n\n"
                "## Review Summary\n\n기존 검토 이력\n"
            )
            review.write_text(history, encoding="utf-8")
            result = ensure_review_unit_status(task, review)
            updated = review.read_text(encoding="utf-8")
        self.assertTrue(result.created)
        self.assertIn("## Unit Review Status\n\n- [ ] UNIT-01: 첫 구현", updated)
        self.assertIn("## Review Summary\n\n기존 검토 이력", updated)

    def test_status_creation_preserves_existing_review_when_replace_fails(self) -> None:
        """원자적 replace 실패 시 기존 Review History bytes를 보존하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: 첫 구현"))
            review = root / "review.md"
            original = (
                "# Antigravity Review: 기존 제목\n\n"
                "## Review Summary\n\n기존 검토 이력\n"
            )
            review.write_text(original, encoding="utf-8")
            before = review.read_bytes()

            with patch(
                "scripts.agent_workflow.review_unit_status.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaises(OSError):
                    ensure_review_unit_status(task, review)

            self.assertEqual(review.read_bytes(), before)

    def test_preserves_existing_review_checks_and_history(self) -> None:
        """이미 생성된 status의 체크 상태와 Review 이력을 변경하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(
                write_task(
                    root,
                    "- [x] UNIT-01: 첫 구현\n- [x] UNIT-02: 두 번째 구현",
                )
            )
            review = root / "review.md"
            original = (
                "# Antigravity Review: 기존 제목\n\n"
                "## Unit Review Status\n\n"
                "- [x] UNIT-01: 첫 구현\n"
                "- [ ] UNIT-02: 두 번째 구현\n\n"
                "## UNIT Review: UNIT-01\n\n기존 이력\n"
            )
            review.write_text(original, encoding="utf-8")
            result = ensure_review_unit_status(task, review)
            current = review.read_text(encoding="utf-8")
        self.assertFalse(result.created)
        self.assertEqual(current, original)
        self.assertEqual([unit.reviewed for unit in result.units], [True, False])

    def test_rejects_mismatched_status_without_modifying_review(self) -> None:
        """Task와 제목이 다른 status를 거부하고 기존 파일을 그대로 두는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: 정확한 제목"))
            review = root / "review.md"
            original = (
                "# Antigravity Review\n\n"
                "## Unit Review Status\n\n"
                "- [ ] UNIT-01: 바뀐 제목\n\n"
                "## Review Summary\n\n보존할 이력\n"
            )
            review.write_text(original, encoding="utf-8")
            with self.assertRaises(ReviewUnitStatusError):
                ensure_review_unit_status(task, review)
            current = review.read_text(encoding="utf-8")
        self.assertEqual(current, original)

    def test_ignores_status_heading_inside_fenced_example(self) -> None:
        """코드 예시의 status heading을 실제 section으로 오인하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root, "- [x] UNIT-01: 실제 UNIT"))
            review = root / "review.md"
            review.write_text(
                "# Antigravity Review\n\n"
                "```markdown\n"
                "## Unit Review Status\n\n"
                "- [x] UNIT-99: 예시\n"
                "```\n",
                encoding="utf-8",
            )
            ensure_review_unit_status(task, review)
            parsed = parse_review_unit_status(task, review)
        self.assertEqual(
            [(unit.identifier, unit.title) for unit in parsed.units],
            [("UNIT-01", "실제 UNIT")],
        )


if __name__ == "__main__":
    unittest.main()
