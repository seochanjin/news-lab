"""검증된 UNIT Review section과 Verdict 기반 status 반영 계약을 검증한다.

임시 Review 파일에서 신규 status 생성, 기존 이력 보존, 중복 거부와 검증 실패
미변경을 확인한다. PASS만 선택 UNIT을 완료 처리하고 다른 Verdict는 status를
유지하는지 검증한다. 마지막 Integration Review PASS가 빈 상단 요약 placeholder를
갱신하고 기존 내용은 덮어쓰지 않는지도 확인한다. 외부 Agent, 실제 repository와
production 자원은 사용하지 않는다.
"""

from pathlib import Path
import tempfile
import unittest

from scripts.agent_workflow.review_response import (
    ReviewResponseError,
    append_review_response,
    validate_review_response,
)
from scripts.agent_workflow.review_context import ReviewTarget
from scripts.agent_workflow.task_parser import TaskUnit, parse_task
from tests.test_agent_review_validator import (
    integration_response,
    re_review_evidence,
    re_review_response,
    re_review_target,
    target,
    unit_response,
)


def write_task(root: Path) -> Path:
    """Writer 테스트용 완료 UNIT 두 개가 있는 Task 파일을 생성한다."""

    path = root / "task.md"
    path.write_text(
        "# Task: Writer\n\n"
        "## Implementation Units\n\n"
        "- [x] UNIT-05: 응답 검증\n"
        "- [x] UNIT-06: 상태 갱신\n",
        encoding="utf-8",
    )
    return path


def write_integration_task(root: Path) -> Path:
    """Integration Review 요약 갱신 테스트용 마지막 UNIT Task를 생성한다."""

    path = root / "integration-task.md"
    path.write_text(
        "# Task: Writer 통합\n\n"
        "## Test commands\n\n"
        "```bash\n"
        "python -m pytest tests/test_agent_*.py -v\n"
        "```\n\n"
        "## Implementation Units\n\n"
        "- [x] UNIT-07: 선행 구현\n"
        "- [x] UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신\n",
        encoding="utf-8",
    )
    return path


def review_with_empty_summary() -> str:
    """FIX-15 canonical 상단 placeholder를 가진 Review 문서를 반환한다."""

    return (
        "# Existing Review\n\n"
        "## Unit Review Status\n\n"
        "- [x] UNIT-07: 선행 구현\n"
        "- [ ] UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신\n\n"
        "## Review Summary\n\n"
        "## Problems Found\n\n"
        "## Required Fixes Before PR\n\n"
        "## Optional Improvements\n\n"
        "## Suggested Test Commands\n\n"
        "## Risk Notes\n\n"
        "## UNIT Review: UNIT-07\n\n"
        "과거 기록\n"
    )


def integration_target() -> ReviewTarget:
    """Writer 통합 테스트용 마지막 UNIT Review 대상을 반환한다."""

    unit = TaskUnit(
        "UNIT-08",
        "전체 Agent Workflow 회귀 테스트와 문서 갱신",
        True,
    )
    return ReviewTarget(unit=unit, mode="integration", position=2, total_units=2)


class ReviewResponseWriterTests(unittest.TestCase):
    """Review 이력 보존과 실패 시 무변경 동작을 검증한다."""

    def test_creates_status_and_appends_validated_section(self) -> None:
        """파일이 없을 때 Task status와 검증된 section을 함께 생성한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            response = validate_review_response(unit_response(), target())
            append_review_response(task, review, response, target())
            text = review.read_text(encoding="utf-8")
        self.assertIn("- [x] UNIT-05: 응답 검증", text)
        self.assertIn("- [ ] UNIT-06: 상태 갱신", text)
        self.assertIn("## UNIT Review: UNIT-05", text)

    def test_preserves_existing_history_and_appends_at_end(self) -> None:
        """기존 이력을 보존하며 PASS status 변경과 새 section을 함께 반영한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            history = (
                "# Existing Review\n\n"
                "## Unit Review Status\n\n"
                "- [ ] UNIT-05: 응답 검증\n"
                "- [ ] UNIT-06: 상태 갱신\n\n"
                "## Historical Note\n\n보존할 기록\n"
            )
            review.write_text(history, encoding="utf-8")
            response = validate_review_response(unit_response(), target())
            append_review_response(task, review, response, target())
            updated = review.read_text(encoding="utf-8")
        self.assertIn("- [x] UNIT-05: 응답 검증", updated)
        self.assertIn("## Historical Note\n\n보존할 기록", updated)
        self.assertTrue(updated.rstrip().endswith("PASS"))

    def test_duplicate_section_is_rejected_without_modification(self) -> None:
        """동일 fingerprint의 section을 다시 append하지 않고 원문을 유지한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            response = validate_review_response(unit_response(), target())
            append_review_response(task, review, response, target())
            before = review.read_bytes()
            with self.assertRaisesRegex(ReviewResponseError, "이미 기록"):
                append_review_response(task, review, response, target())
            self.assertEqual(review.read_bytes(), before)

    def test_non_pass_verdicts_keep_selected_unit_unchecked(self) -> None:
        """CHANGES REQUIRED와 BLOCKED가 선택 UNIT status를 완료 처리하지 않음을 검증한다."""

        for verdict in ("CHANGES REQUIRED", "BLOCKED"):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                task = parse_task(write_task(root))
                review = root / "review.md"
                response = validate_review_response(
                    unit_response(verdict=verdict),
                    target(),
                )
                append_review_response(task, review, response, target())
                text = review.read_text(encoding="utf-8")
                self.assertIn("- [ ] UNIT-05: 응답 검증", text)
                self.assertIn(f"### Verdict\n{verdict}", text)

    def test_pass_updates_only_selected_unit(self) -> None:
        """PASS가 선택 UNIT 하나만 체크하고 뒤 UNIT 상태를 보존하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            response = validate_review_response(unit_response(), target())
            append_review_response(task, review, response, target())
            text = review.read_text(encoding="utf-8")
        self.assertIn("- [x] UNIT-05: 응답 검증", text)
        self.assertIn("- [ ] UNIT-06: 상태 갱신", text)

    def test_target_mismatch_leaves_existing_file_unchanged(self) -> None:
        """Task와 다른 선택 UNIT이면 status와 Review 이력을 모두 변경하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            review.write_text("# Existing Review\n\n보존\n", encoding="utf-8")
            before = review.read_bytes()
            mismatched = target()
            mismatched = type(mismatched)(
                unit=type(mismatched.unit)("UNIT-05", "다른 제목", True),
                mode=mismatched.mode,
                position=mismatched.position,
                total_units=mismatched.total_units,
            )
            response = validate_review_response(unit_response(), mismatched)
            with self.assertRaisesRegex(ReviewResponseError, "Task 완료 상태"):
                append_review_response(task, review, response, mismatched)
            self.assertEqual(review.read_bytes(), before)

    def test_validation_failure_leaves_existing_file_unchanged(self) -> None:
        """잘린 stdout이 validator에서 실패하면 writer 호출 전 기존 파일이 유지된다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            review.write_text("# Existing Review\n\n과거 기록\n", encoding="utf-8")
            before = review.read_bytes()
            with self.assertRaises(ReviewResponseError):
                response = validate_review_response(
                    "## UNIT Review: UNIT-05\n### Verdict\nPASS\n",
                    target(),
                )
                append_review_response(task, review, response, target())
            self.assertEqual(review.read_bytes(), before)

    def test_re_review_appends_without_rechecking_completed_unit(self) -> None:
        """모든 UNIT status가 완료된 Re-review는 checklist를 바꾸지 않고 append한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_task(root))
            review = root / "review.md"
            review.write_text(
                "# Existing Review\n\n"
                "## Unit Review Status\n\n"
                "- [x] UNIT-05: 응답 검증\n"
                "- [x] UNIT-06: 상태 갱신\n\n"
                "## Re-review 1\n\n과거 기록\n\n"
                "## Re-review 2\n\n과거 기록\n",
                encoding="utf-8",
            )
            target_value = re_review_target()
            target_value = type(target_value)(
                unit=type(target_value.unit)("UNIT-06", "상태 갱신", True),
                mode="re-review",
                position=2,
                total_units=2,
                re_review_number=3,
            )
            response = validate_review_response(
                re_review_response(),
                target_value,
                re_review_evidence(),
            )
            append_review_response(task, review, response, target_value)
            text = review.read_text(encoding="utf-8")

        self.assertEqual(text.count("- [x] UNIT-06: 상태 갱신"), 1)
        self.assertTrue(text.rstrip().endswith("PASS"))

    def test_integration_pass_updates_empty_top_summary_once(self) -> None:
        """UNIT-08 통합 PASS가 빈 상단 요약과 status와 history를 한 번에 갱신한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_integration_task(root))
            review = root / "review.md"
            review.write_text(review_with_empty_summary(), encoding="utf-8")
            integration_target_value = integration_target()
            response = validate_review_response(
                integration_response(),
                integration_target_value,
            )
            append_review_response(task, review, response, integration_target_value)
            text = review.read_text(encoding="utf-8")

        self.assertIn(
            "- [x] UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신",
            text,
        )
        self.assertIn("Writer 통합 작업의 UNIT Review와 최종 Integration Review를 완료했다.", text)
        self.assertIn("## Problems Found\n\n- 없음", text)
        self.assertIn("python -m pytest tests/test_agent_*.py -v", text)
        self.assertIn("## UNIT Review: UNIT-07\n\n과거 기록", text)
        self.assertTrue(text.rstrip().endswith("PASS"))

    def test_integration_summary_does_not_overwrite_existing_top_content(self) -> None:
        """상단 placeholder에 내용이 있으면 Integration Review append 전체를 중단한다."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = parse_task(write_integration_task(root))
            review = root / "review.md"
            review.write_text(
                review_with_empty_summary().replace(
                    "## Review Summary\n\n",
                    "## Review Summary\n\n이미 작성된 요약\n\n",
                ),
                encoding="utf-8",
            )
            before = review.read_bytes()
            integration_target_value = integration_target()
            response = validate_review_response(
                integration_response(),
                integration_target_value,
            )
            with self.assertRaisesRegex(ReviewResponseError, "기존 내용"):
                append_review_response(task, review, response, integration_target_value)
            self.assertEqual(review.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
