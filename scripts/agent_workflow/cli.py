"""NewsLab Agent 실행 하네스의 command-line interface를 제공한다.

사용자 인자를 해석해 status, prompt-only, preview 또는 실제 Agent 실행 흐름을
조정한다. 실제 실행 시 runner를 통해 로그를 쓰고 subprocess를 실행하지만,
preview와 status는 Agent 실행이나 로그 생성을 수행하지 않는다.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from .approved_fixes import (
    ApprovedFixesNormalizationError,
    normalize_approved_fixes,
)
from .gates import AgentCommand, GateError, gate_message, validate_action
from .prompt_builder import build_prompt
from .review_context import ReviewContext, build_review_context
from .review_prompt import build_review_prompt, expected_review_heading
from .review_unit_status import (
    ReviewUnitStatus,
    ReviewUnitStatusError,
    build_initial_review_unit_status,
    parse_review_unit_status,
)
from .runner import planned_log_directory, run_agent
from .state import format_status, load_state, run_git
from .task_parser import TaskParseError


ACTIONS = (
    "codex-implement",
    "codex-implement-unit",
    "antigravity-review-unit",
    "antigravity-review",
    "codex-fix",
)
REVIEW_ACTIONS = {"antigravity-review-unit", "antigravity-review"}
DEFAULT_TIMEOUT = 1200
MAX_REVIEW_PROMPT_BYTES = 100_000


def build_parser() -> argparse.ArgumentParser:
    """지원 action과 공통 option이 등록된 ArgumentParser를 반환한다."""

    parser = argparse.ArgumentParser(description="NewsLab Agent 직접 실행 하네스")
    parser.add_argument("action", choices=(*ACTIONS, "status"))
    parser.add_argument("--preview", action="store_true", help="실행 정보와 prompt만 확인")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Antigravity Review mode, Context와 prompt만 확인",
    )
    parser.add_argument("--yes", action="store_true", help="대화형 확인 생략")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="초 단위 timeout")
    parser.add_argument("--prompt-only", action="store_true", help=argparse.SUPPRESS)
    return parser


def preview_text(
    state: "WorkflowState",
    action: str,
    command: AgentCommand,
    log_dir: Path,
    timeout: int,
) -> str:
    """실행 전 Agent adapter, 지원 상태, branch, 로그와 timeout 정보를 반환한다."""

    unit = state.task.current_unit
    current_unit = (
        f"{unit.identifier}: {unit.title}"
        if action == "codex-implement-unit" and unit
        else "없음"
    )
    mode = "unit" if action == "codex-implement-unit" else "general"
    return "\n".join(
        [
            f"Action: {action}",
            f"Target Agent: {command.agent}",
            f"Adapter: {command.adapter}",
            f"Executable: {command.executable or 'not found'}",
            "Automatic execution supported: "
            f"{'yes' if command.automatic_execution_supported else 'no'}",
            f"Failure category: {command.failure_category or 'none'}",
            "Manual fallback required: "
            f"{'yes' if command.manual_fallback_required else 'no'}",
            f"Current branch: {state.branch}",
            f"Task path: {state.paths.task.relative_to(state.repo)}",
            f"Execution mode: {mode}",
            f"Current UNIT: {current_unit}",
            f"Log directory: {log_dir.relative_to(state.repo)}",
            f"Timeout: {timeout}초",
        ]
    )


def _review_status_for_prompt(state: "WorkflowState") -> ReviewUnitStatus | None:
    """Review UNIT 상태를 읽거나 파일 쓰기 없이 초기 unchecked 상태를 만든다."""

    if state.task.execution_mode != "unit":
        return None
    try:
        return parse_review_unit_status(state.task, state.paths.review)
    except ReviewUnitStatusError as error:
        if state.paths.review.exists():
            text = state.paths.review.read_text(encoding="utf-8")
            if "## Unit Review Status" in text:
                raise error
        return build_initial_review_unit_status(state.task)


def _build_antigravity_prompt(
    state: "WorkflowState", action: str
) -> tuple[ReviewContext, str]:
    """현재 branch의 Review 대상, Context와 Antigravity prompt를 구성한다."""

    review_status = _review_status_for_prompt(state)
    context = build_review_context(
        repo=state.repo,
        branch=state.branch,
        task=state.task,
        review_status=review_status,
        review_path=state.paths.review,
        verification_path=state.paths.verification,
        approved_fixes_path=state.paths.approved_fixes,
        action=action,
    )
    return context, build_review_prompt(context)


def _review_prompt_summary(context: ReviewContext, prompt: str) -> str:
    """외부 실행 전 확인할 Review 대상, prompt 크기와 evidence 요약을 반환한다."""

    diff_file_count = sum(
        line.startswith(("diff --git ", "diff --untracked "))
        for line in context.git_diff.splitlines()
    )
    latest_by_kind = {
        result.kind: result.passed_count
        for result in context.evidence.verification.latest_tests
    }
    reasons = {
        "unit": "구현 완료됐지만 Review를 통과하지 않은 UNIT을 선택했습니다.",
        "integration": "모든 UNIT Review가 완료됐고 Integration Review가 없습니다.",
        "re-review": "Integration Review 이후 적용된 구현 FIX와 최신 Verification을 검토합니다.",
        "general": "Implementation Units가 없는 일반 Task입니다.",
    }
    return "\n".join(
        [
            f"Action: {context.action}",
            f"Resolved review mode: {context.target.mode}",
            f"Mode selection reason: {reasons.get(context.target.mode, 'unknown')}",
            "Target UNIT: "
            f"{context.target.unit.identifier}: {context.target.unit.title}",
            f"Expected heading: {expected_review_heading(context)}",
            f"Prompt lines: {len(prompt.splitlines())}",
            f"Prompt characters: {len(prompt)}",
            f"Prompt bytes: {len(prompt.encode('utf-8'))}",
            f"Diff files: {diff_file_count}",
            "Approved fixes: "
            f"{len(context.evidence.approved_fixes.re_review_items)}",
            f"Latest pytest passed: {latest_by_kind.get('pytest', 'none')}",
            f"Latest unittest passed: {latest_by_kind.get('unittest', 'none')}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    """CLI action을 처리하고 shell에 전달할 종료 코드를 반환한다.

    실제 실행은 사용자 확인 또는 --yes가 필요하다. Gate나 입력 오류는 한글로
    stderr에 출력하고 2를 반환하며 예외를 외부로 전파하지 않는다.
    """

    args = build_parser().parse_args(argv)
    if args.timeout <= 0:
        print("오류: timeout은 1초 이상이어야 합니다.", file=sys.stderr)
        return 2
    try:
        if (
            args.action in REVIEW_ACTIONS
            and os.environ.get("NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE") == "1"
        ):
            raise GateError(
                "활성 Antigravity Review 하위 process에서는 재귀 실행할 수 없습니다."
            )
        cwd = Path.cwd()
        if args.action in {"codex-implement", "codex-implement-unit", "codex-fix"}:
            root = Path(run_git(cwd, "rev-parse", "--show-toplevel"))
            branch = run_git(root, "branch", "--show-current")
            if branch in {"main", "master"}:
                raise GateError(
                    f"{branch} branch에서는 구현 또는 Fix를 실행할 수 없습니다."
                )
            if args.action == "codex-fix":
                safe_branch = branch.replace("/", "-")
                normalization = normalize_approved_fixes(
                    root
                    / "docs"
                    / "fixes"
                    / f"{safe_branch}-approved-fixes.md"
                )
                if normalization.created:
                    identifiers = [fix.identifier for fix in normalization.fixes]
                    print(
                        "Approved Fixes checklist가 없어 상세 FIX Heading "
                        f"{len(identifiers)}개에서 생성했습니다."
                    )
                    print(f"- {identifiers[0]} ~ {identifiers[-1]}")
                pending_count = sum(
                    fix.checked is False for fix in normalization.fixes
                )
                print(f"Approved fixes pending: {pending_count}")
        state = load_state(cwd)
        if args.action == "status":
            print(format_status(state))
            return 0
        dry_run = args.dry_run or args.preview
        command = validate_action(
            state,
            args.action,
            require_agent=not args.prompt_only and not args.dry_run,
            env=dict(os.environ),
        )
        review_context = None
        if args.action in REVIEW_ACTIONS:
            review_context, prompt = _build_antigravity_prompt(state, args.action)
            prompt_bytes = len(prompt.encode("utf-8"))
            if prompt_bytes > MAX_REVIEW_PROMPT_BYTES:
                raise GateError(
                    "Antigravity Review prompt가 실행 상한을 초과했습니다: "
                    f"{prompt_bytes} > {MAX_REVIEW_PROMPT_BYTES} bytes"
                )
        else:
            if args.dry_run:
                raise ValueError(
                    "--dry-run은 antigravity-review 계열 action에서만 지원합니다."
                )
            prompt = build_prompt(state, args.action)
        if args.prompt_only:
            print(prompt)
            return 0
        if args.dry_run:
            assert review_context is not None
            print(_review_prompt_summary(review_context, prompt))
            if review_context.target.re_review_number is not None:
                print(
                    "Next Re-review: "
                    f"{review_context.target.re_review_number}"
                )
            print("\n--- Prompt ---\n")
            print(prompt)
            return 0
        assert command is not None
        log_dir = planned_log_directory(state, args.action)
        print(preview_text(state, args.action, command, log_dir, args.timeout))
        if review_context is not None:
            print(_review_prompt_summary(review_context, prompt))
        if args.action == "codex-implement" and state.task.execution_mode == "unit":
            print("경고: UNIT Task를 일반 모드로 실행하므로 Task 전체가 대상입니다.")
        if args.preview:
            print("\n--- Prompt ---\n")
            print(prompt)
            return 0
        if not command.automatic_execution_supported:
            print("\n자동 Antigravity review를 실행할 수 없습니다.", file=sys.stderr)
            if command.failure_category == "executable_missing":
                print("원인: 확인된 Antigravity CLI 실행 파일을 찾지 못했습니다.", file=sys.stderr)
            else:
                print(
                    "원인: 현재 환경에서 비대화형 Antigravity review 계약이 검증되지 않았습니다.",
                    file=sys.stderr,
                )
            print(
                f"수동 review 요청: {command.next_action}",
                file=sys.stderr,
            )
            print(
                "review 파일 작성 prompt: "
                "scripts/agent_next_step.sh antigravity-review-write",
                file=sys.stderr,
            )
            return 2
        if not args.yes:
            if not sys.stdin.isatty():
                print("오류: 비대화형 실행에서는 --yes가 필요합니다.", file=sys.stderr)
                return 2
            answer = input("\nAgent를 실행할까요? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                print("실행을 취소했습니다.")
                return 1
        result = run_agent(
            state,
            args.action,
            command,
            prompt,
            args.timeout,
            log_directory=log_dir,
            review_context=review_context,
        )
        print(f"\nAgent 종료 코드: {result.exit_code}")
        print(f"Timeout: {'yes' if result.timed_out else 'no'}")
        print(f"Failure category: {result.failure_category or 'none'}")
        print(
            "Manual fallback required: "
            f"{'yes' if result.manual_fallback_required else 'no'}"
        )
        print(f"Review file validation: {result.review_file_validation}")
        print(f"Review completed: {'yes' if result.review_completed else 'no'}")
        if result.failure_category == "unsupported_client":
            print(
                "지원되지 않는 client입니다. "
                "scripts/agent_next_step.sh antigravity-review로 수동 review를 진행하세요."
            )
        print(f"실행 시간: {result.duration_seconds}초")
        print(f"로그 위치: {result.log_directory}")
        print("Agent 종료만으로 Task 또는 Verification 완료를 판단하지 않습니다.")
        if result.exit_code == 0 and result.failure_category is not None:
            return 1
        return result.exit_code
    except (
        ApprovedFixesNormalizationError,
        GateError,
        TaskParseError,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        print(f"오류: {gate_message(error)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
