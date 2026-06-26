"""Approved Fixes, 최신 Verification과 Review History parser 계약을 검증한다.

임시 Markdown 문서만 사용해 FIX 상태, 과거 테스트 수와 최신 전체 회귀 수치의
구분, 다음 Re-review 번호 계산을 확인한다. 실제 workflow 문서, Git repository,
외부 Agent 또는 production 자원은 변경하지 않는다.
"""

from pathlib import Path
import tempfile
import unittest

from scripts.agent_workflow.review_evidence import (
    ReviewEvidenceError,
    build_review_evidence,
    parse_approved_fixes,
    parse_review_history,
    parse_verification,
)


class ReviewEvidenceParserTests(unittest.TestCase):
    """Re-review current-state를 구성하는 세 parser의 성공과 거부 조건을 검증한다."""

    def test_parses_applied_approved_and_rejected_fix_states(self) -> None:
        """FIX checklist와 거절 section의 상태를 ID·제목과 함께 보존한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "# Approved Fixes\n\n"
                "## Approved Fixes\n\n"
                "- [x] FIX-01: 적용 완료\n"
                "- [ ] FIX-02: 승인 후 미적용\n\n"
                "## Rejected or Deferred Suggestions\n\n"
                "### FIX-03. Rejected: 범위 밖 제안\n",
                encoding="utf-8",
            )
            snapshot = parse_approved_fixes(path)

        self.assertEqual(
            [(fix.identifier, fix.status) for fix in snapshot.fixes],
            [
                ("FIX-01", "applied"),
                ("FIX-02", "approved"),
                ("FIX-03", "rejected"),
            ],
        )
        self.assertEqual(
            [fix.identifier for fix in snapshot.actionable],
            ["FIX-01", "FIX-02"],
        )

    def test_rejects_duplicate_fix_identifiers(self) -> None:
        """동일 FIX ID가 여러 상태로 기록된 모호한 문서를 거부한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "## Approved Fixes\n\n"
                "- [x] FIX-01: 첫 기록\n"
                "- [ ] FIX-01: 중복 기록\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ReviewEvidenceError, "중복"):
                parse_approved_fixes(path)

    def test_ignores_matching_detail_headings_after_canonical_checklist(self) -> None:
        """checklist와 같은 상세 heading을 중복 FIX가 아닌 설명 계약으로 처리한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "## Approved Fixes\n\n"
                "- [x] FIX-01: 적용 완료\n"
                "- [ ] FIX-02: 적용 대기\n\n"
                "### FIX-01: 적용 완료\n\n설명\n\n"
                "### FIX-02: 적용 대기\n\n설명\n",
                encoding="utf-8",
            )
            snapshot = parse_approved_fixes(path)

        self.assertEqual(
            [(fix.identifier, fix.status) for fix in snapshot.fixes],
            [("FIX-01", "applied"), ("FIX-02", "approved")],
        )

    def test_classifies_human_verification_fix_separately(self) -> None:
        """상세 설명의 분류가 human-verification이면 Re-review 차단 대상에서 제외한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "## Approved Fixes\n\n"
                "- [x] FIX-01: 구현 수정\n"
                "- [ ] FIX-02: 외부 실행 확인\n\n"
                "### FIX-01: 구현 수정\n\n분류: implementation-fix\n\n"
                "### FIX-02: 외부 실행 확인\n\n분류: human-verification\n",
                encoding="utf-8",
            )
            snapshot = parse_approved_fixes(path)

        self.assertEqual(
            [(fix.identifier, fix.category) for fix in snapshot.fixes],
            [("FIX-01", "implementation-fix"), ("FIX-02", "human-verification")],
        )
        self.assertEqual([fix.identifier for fix in snapshot.actionable], ["FIX-01"])
        self.assertEqual(
            [fix.identifier for fix in snapshot.re_review_items],
            ["FIX-01", "FIX-02"],
        )
        self.assertEqual(
            [fix.identifier for fix in snapshot.pending_human_verification],
            ["FIX-02"],
        )

    def test_classifies_category_value_in_following_fenced_block(self) -> None:
        """`분류:` 다음 fenced block의 category 값을 현재 FIX에 연결한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixes.md"
            path.write_text(
                "## Approved Fixes\n\n"
                "- [ ] FIX-01: 외부 검증\n\n"
                "### FIX-01: 외부 검증\n\n"
                "분류:\n\n"
                "```text\n"
                "human-verification\n"
                "```\n",
                encoding="utf-8",
            )
            snapshot = parse_approved_fixes(path)

        self.assertEqual(
            [fix.identifier for fix in snapshot.pending_human_verification],
            ["FIX-01"],
        )

    def test_selects_latest_successful_full_test_counts(self) -> None:
        """과거 261 수치 뒤의 최신 pytest·unittest 265 수치를 선택한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verification.md"
            path.write_text(
                "## Verification Status\n\npassed\n\n"
                "### 1. 과거 전체 회귀\n\n"
                "Command:\n\n```bash\npython -m pytest\n```\n\n"
                "Result:\n\n- 261 passed\n\nStatus: passed\n\n"
                "### 2. 최신 pytest\n\n"
                "Command:\n\n```bash\npython -m pytest\n```\n\n"
                "Result:\n\n- 265개 테스트가 모두 통과했다.\n\nStatus: passed\n\n"
                "### 3. 최신 unittest\n\n"
                "Command:\n\n```bash\npython -m unittest discover -s tests\n```\n\n"
                "Result:\n\n- 265 passed\n\nStatus: passed\n",
                encoding="utf-8",
            )
            snapshot = parse_verification(path)

        self.assertEqual(snapshot.status, "passed")
        self.assertEqual(
            [(result.kind, result.passed_count) for result in snapshot.latest_tests],
            [("pytest", 265), ("unittest", 265)],
        )
        self.assertEqual(snapshot.latest_passed_counts, (265,))

    def test_calculates_next_re_review_number_outside_fences(self) -> None:
        """코드 예시 heading을 무시하고 실제 Re-review 최대 번호 다음 값을 반환한다."""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.md"
            path.write_text(
                "# Review\n\n"
                "```markdown\n## Re-review 99\n```\n\n"
                "## Re-review 1\n\n기록\n\n"
                "## Re-review 2\n\n기록\n",
                encoding="utf-8",
            )
            snapshot = parse_review_history(path)

        self.assertEqual(snapshot.re_review_numbers, (1, 2))
        self.assertEqual(snapshot.next_re_review_number, 3)

    def test_builds_real_failure_case_snapshot(self) -> None:
        """실제 FIX 9개·265 passed와 기록된 Re-review 3 다음 번호를 확인한다."""

        root = Path(__file__).resolve().parents[1]
        snapshot = build_review_evidence(
            approved_fixes_path=(
                root / "docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md"
            ),
            verification_path=(
                root / "docs/verification/feature-three-day-topic-pipeline.md"
            ),
            review_path=(
                root / "docs/reviews/feature-three-day-topic-pipeline-antigravity.md"
            ),
        )

        self.assertEqual(len(snapshot.approved_fixes.applied), 9)
        self.assertEqual(snapshot.verification.latest_passed_counts, (265,))
        self.assertEqual(snapshot.review_history.next_re_review_number, 4)


if __name__ == "__main__":
    unittest.main()
