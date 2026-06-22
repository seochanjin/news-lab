"""Task Markdown과 Implementation Units parser의 안전 동작을 검증한다.

임시 Task 파일을 사용해 일반·UNIT mode 판정과 잘못된 형식 차단을 확인하며,
실제 repository 문서나 외부 Agent를 변경·실행하지 않는다.
"""

from pathlib import Path
import tempfile
import unittest

from scripts.agent_workflow.task_parser import TaskParseError, parse_task


def write_task(tmp_path: Path, units: str | None) -> Path:
    """테스트용 Task Markdown을 임시 경로에 쓰고 생성 경로를 반환한다."""

    suffix = "" if units is None else f"\n## Implementation Units\n\n{units}\n"
    path = tmp_path / "task.md"
    path.write_text(
        "# Task: parser\n\n## Goal\n\n목표\n\n## Scope\n\n범위\n" + suffix,
        encoding="utf-8",
    )
    return path


class TaskParserTests(unittest.TestCase):
    """Task parser의 mode 판정과 형식 검증 회귀를 확인한다."""

    def test_missing_units_section_is_general_mode(self) -> None:
        """기존 Task처럼 UNIT section이 없어도 일반 mode로 호환되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(write_task(Path(directory), None))
        self.assertEqual(task.execution_mode, "general")
        self.assertIsNone(task.current_unit)

    def test_none_units_section_is_general_mode(self) -> None:
        """Implementation Units가 `없음`이면 일반 mode가 되는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(write_task(Path(directory), "없음"))
        self.assertEqual(task.execution_mode, "general")

    def test_ignores_units_heading_inside_fenced_example(self) -> None:
        """코드 예시 안의 UNIT heading을 실제 section으로 오인하지 않는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "task.md"
            path.write_text(
                "# Task: fenced\n\n## Goal\n\n```markdown\n"
                "## Implementation Units\n\n없음\n```\n\n## Scope\n\n범위\n",
                encoding="utf-8",
            )
            task = parse_task(path)
        self.assertEqual(task.execution_mode, "general")

    def test_selects_first_incomplete_unit(self) -> None:
        """완료 순서를 유지하며 첫 번째 미완료 UNIT을 선택하는지 검증한다."""

        with tempfile.TemporaryDirectory() as directory:
            task = parse_task(
                write_task(
                    Path(directory),
                    "- [x] UNIT-01: 완료\n- [ ] UNIT-02: 현재\n- [ ] UNIT-03: 다음",
                )
            )
        self.assertEqual(task.execution_mode, "unit")
        self.assertIsNotNone(task.current_unit)
        self.assertEqual(task.current_unit.identifier, "UNIT-02")
        self.assertEqual(task.completed_unit_count, 1)
        self.assertEqual(task.pending_unit_count, 2)

    def test_rejects_unsafe_unit_formats(self) -> None:
        """혼합, 비정형, 역순 완료와 빈 UNIT section을 차단하는지 검증한다."""

        cases = [
            "없음\n- [ ] UNIT-01: 충돌",
            "- [ ] 잘못된 형식",
            "- [ ] UNIT-01: 미완료\n- [x] UNIT-02: 순서 오류",
            "",
        ]
        for units in cases:
            with self.subTest(units=units), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(TaskParseError):
                    parse_task(write_task(Path(directory), units))


if __name__ == "__main__":
    unittest.main()
