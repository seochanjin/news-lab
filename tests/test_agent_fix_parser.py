"""Approved Fixes checklist 정규화와 `codex-fix` 진입 계약을 검증한다.

임시 Markdown 문서와 임시 Git repository만 사용한다. 상세 FIX heading에서
unchecked checklist를 생성하는 성공 경로, 기존 체크 상태 보존, ID·제목·번호
오류 시 무변경 실패와 CLI gate 연결을 검증하며 외부 Codex나 production
자원은 실행하지 않는다.
"""

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workflow.approved_fixes import (
    ApprovedFixesNormalizationError,
    normalize_approved_fixes,
)
from scripts.agent_workflow.cli import main
from scripts.agent_workflow.review_evidence import parse_approved_fixes
from tests.test_agent_workflow_state import make_repo


class ApprovedFixesNormalizerTests(unittest.TestCase):
    """Approved Fixes canonical checklist 생성과 거부 조건을 검증한다."""

    def test_creates_unchecked_checklist_from_detail_headings(self) -> None:
        """상세 heading 두 개를 같은 ID·제목의 unchecked checklist로 생성한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "# Fixes\n\n"
                "## Approved Fixes\n\n"
                "### FIX-01: 첫 번째 수정\n\n설명\n\n"
                "### FIX-02: 두 번째 수정\n\n설명\n\n"
                "## Applied Changes\n\n없음.\n",
                encoding="utf-8",
            )
            result = normalize_approved_fixes(path)
            text = path.read_text(encoding="utf-8")
            snapshot = parse_approved_fixes(path)

        self.assertTrue(result.created)
        self.assertEqual(
            [fix.identifier for fix in result.fixes],
            ["FIX-01", "FIX-02"],
        )
        self.assertIn(
            "## Approved Fixes\n\n"
            "- [ ] FIX-01: 첫 번째 수정\n"
            "- [ ] FIX-02: 두 번째 수정\n\n"
            "### FIX-01: 첫 번째 수정",
            text,
        )
        self.assertIn("### FIX-02: 두 번째 수정\n\n설명", text)
        self.assertEqual(
            [fix.identifier for fix in snapshot.actionable],
            ["FIX-01", "FIX-02"],
        )

    def test_preserves_existing_checked_state_and_details(self) -> None:
        """일치하는 기존 checklist의 `[x]` 상태와 상세 설명을 변경하지 않는다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            original = (
                "## Approved Fixes\n\n"
                "- [x] FIX-01: 적용 완료\n"
                "- [ ] FIX-02: 적용 대기\n\n"
                "### FIX-01: 적용 완료\n\n첫 설명\n\n"
                "### FIX-02: 적용 대기\n\n둘째 설명\n"
            )
            path.write_text(original, encoding="utf-8")
            result = normalize_approved_fixes(path)

            self.assertFalse(result.created)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual([fix.checked for fix in result.fixes], [True, False])

    def test_accepts_legacy_checklist_without_detail_headings(self) -> None:
        """기존 checklist-only 승인 문서를 재작성하지 않고 호환 처리한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            original = "## Approved Fixes\n\n- [ ] FIX-01: 승인 항목\n"
            path.write_text(original, encoding="utf-8")
            result = normalize_approved_fixes(path)

            self.assertFalse(result.created)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_rejects_mismatch_duplicate_missing_and_unnumbered_without_write(self) -> None:
        """모호한 ID·제목·번호 구조를 모두 원본 bytes 보존 실패로 처리한다."""

        cases = {
            "mismatch": (
                "## Approved Fixes\n\n"
                "- [ ] FIX-01: 체크 제목\n\n"
                "### FIX-01: 다른 제목\n"
            ),
            "duplicate": (
                "## Approved Fixes\n\n"
                "### FIX-01: 첫 항목\n\n"
                "### FIX-01: 중복 항목\n"
            ),
            "missing": (
                "## Approved Fixes\n\n"
                "### FIX-01: 첫 항목\n\n"
                "### FIX-03: 누락 뒤 항목\n"
            ),
            "unnumbered": "## Approved Fixes\n\n### FIX: 번호 없음\n",
            "prose_only": "## Approved Fixes\n\n승인된 수정 설명만 있음.\n",
        }
        for name, original in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "fixes.md"
                path.write_text(original, encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaises(ApprovedFixesNormalizationError):
                    normalize_approved_fixes(path)
                self.assertEqual(path.read_bytes(), before)

    def test_codex_fix_normalizes_before_loading_workflow_state(self) -> None:
        """CLI가 상세 heading을 정규화한 뒤 기존 codex-fix gate를 통과한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            fixes = repo / "docs" / "fixes" / "feature-example-approved-fixes.md"
            fixes.write_text(
                "## Approved Fixes\n\n"
                "### FIX-01: 첫 수정\n\n설명\n\n"
                "### FIX-02: 둘째 수정\n\n설명\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with (
                patch("pathlib.Path.cwd", return_value=repo),
                patch(
                    "scripts.agent_workflow.gates.shutil.which",
                    return_value="/tmp/codex",
                ),
                redirect_stdout(output),
            ):
                exit_code = main(["codex-fix", "--preview"])

            self.assertEqual(exit_code, 0)
            self.assertIn("상세 FIX Heading 2개에서 생성", output.getvalue())
            self.assertIn("Approved fixes pending: 2", output.getvalue())
            text = fixes.read_text(encoding="utf-8")
            self.assertIn("- [ ] FIX-01: 첫 수정", text)
            self.assertIn("- [ ] FIX-02: 둘째 수정", text)

    def test_codex_fix_reports_normalization_error_without_agent_lookup(self) -> None:
        """CLI가 불일치 문서를 수정하거나 Agent를 탐지하기 전에 non-zero로 종료한다."""

        with tempfile.TemporaryDirectory() as directory:
            repo = make_repo(Path(directory))
            fixes = repo / "docs" / "fixes" / "feature-example-approved-fixes.md"
            original = (
                "## Approved Fixes\n\n"
                "- [ ] FIX-01: 체크 제목\n\n"
                "### FIX-01: 다른 제목\n"
            )
            fixes.write_text(original, encoding="utf-8")
            error = io.StringIO()
            with (
                patch("pathlib.Path.cwd", return_value=repo),
                patch(
                    "scripts.agent_workflow.gates.shutil.which",
                    side_effect=AssertionError("Agent lookup must not run"),
                ),
                redirect_stderr(error),
            ):
                exit_code = main(["codex-fix", "--preview"])

            self.assertEqual(exit_code, 2)
            self.assertIn("ID·제목·순서가 다릅니다", error.getvalue())
            self.assertEqual(fixes.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
