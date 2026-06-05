#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/agent_next_step.sh <command>

Commands:
  files
  codex-implement
  antigravity-review
  antigravity-review-write
  fixes-draft
  codex-apply-fixes
  pr-draft
  devlog-draft
USAGE
}

branch_name() {
  git branch --show-current
}

safe_name() {
  printf '%s' "$1" | tr '/' '-'
}

print_context() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Branch: ${branch}
Safe branch name: ${safe}

Workflow files:
- Task: docs/tasks/${safe}.md
- Antigravity review: docs/reviews/${safe}-antigravity.md
- CodeRabbit review: docs/reviews/${safe}-coderabbit.md
- Approved fixes: docs/fixes/${safe}-approved-fixes.md
- Verification: docs/verification/${safe}.md
- PR draft: docs/pr/${safe}.md
- Devlog: docs/devlog/${safe}.md
EOF
}

print_common_rules() {
  cat <<'EOF'
Common rules:
- Use the task file as the source of truth.
- If the task file and this chat prompt conflict, follow the task file.
- Keep detailed requirements in docs/tasks/<safe-branch>.md; keep chat prompts focused on source of truth, file paths, scope, constraints, and validation commands.
- Do not run production-impacting commands unless the human explicitly instructs it.
- Do not run kubectl apply, kubectl rollout, Supabase SQL, git push, or git merge.
- Do not run production curl verification unless the current task or human operator explicitly allows read-only checks.
- Do not claim production verification is complete unless the human provides actual logs.
- Do not modify secrets, .env, kubeconfig, credentials, SSH keys, or tokens.
- Do not automatically run Codex, Gemini/Antigravity, GitHub, or CodeRabbit.
- Do not use GitHub MCP unless the current task explicitly requires it.
- Review output alone is not approval to modify code. Only human-approved fixes recorded in docs/fixes/<safe-branch>-approved-fixes.md may be applied.
EOF
}

print_files() {
  local branch="$1"
  local safe="$2"

  print_context "$branch" "$safe"
}

print_codex_implement() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
AGENTS.md, docs/RUNBOOK.md, docs/prompts/codex-implement.md, docs/tasks/${safe}.md를 읽고 구현해줘.

Source of truth:
- docs/tasks/${safe}.md

Workflow files:
- Task: docs/tasks/${safe}.md
- Verification: docs/verification/${safe}.md
- PR draft: docs/pr/${safe}.md
- Devlog: docs/devlog/${safe}.md

Current branch:
- ${branch}

$(print_common_rules)

Implementation rules:
- Follow the Scope, Do not change, Test commands, and Acceptance criteria in docs/tasks/${safe}.md.
- Record only commands actually run and their results in docs/verification/${safe}.md.
- Do not claim production verification, PR merge, rollout, or deployment is complete unless the human provides actual logs.
- Keep changes small and reviewable.

After implementation, summarize:
- Changed files.
- Behavior changes.
- Verification commands run and results.
- Areas intentionally not modified.
- Remaining manual work.
EOF
}

print_antigravity_review() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Review the current NewsLab changes.

Read:
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/prompts/antigravity-review.md
- docs/tasks/${safe}.md
- Current git diff

Source of truth:
- docs/tasks/${safe}.md

Current branch:
- ${branch}

Review target:
- Current git diff

$(print_common_rules)

Review rules:
- Do not modify files.
- Review against the task Scope, Do not change, and Acceptance criteria.
- Prioritize bugs, unsafe production behavior, scope creep, missing verification, and documentation mismatch.
- Do not treat review output as approved fixes.
- Do not claim a command was executed unless it is recorded in docs/verification/${safe}.md or shown in the provided logs.

Review focus:
- Requirement coverage against docs/tasks/${safe}.md.
- Code quality and maintainability.
- Security risks, including secret exposure, unsafe permissions, and unnecessary privileges.
- Operational safety and human-controlled operation boundaries.
- Scope control and unexpected file changes.
- Verification integrity: completed checks must match actually-run commands.
- Documentation consistency and future readability.

Output in chat only using:

## Review Summary

## Requirement Coverage

## Code Quality / Maintainability

## Security Review

## Operational Risk

## Scope Control

## Verification Review

## Documentation Review

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Verdict
EOF
}

print_antigravity_review_write() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Write the Gemini/Antigravity review result for the current NewsLab branch.

Read:
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/prompts/antigravity-review.md
- docs/tasks/${safe}.md
- Current git diff

Source of truth:
- docs/tasks/${safe}.md

Current branch:
- ${branch}

Only writable file:
- docs/reviews/${safe}-antigravity.md

$(print_common_rules)

Write rules:
- Do not modify any file except docs/reviews/${safe}-antigravity.md.
- Save review findings only.
- Do not record applied fixes in docs/reviews/${safe}-antigravity.md.
- Do not record verification results in docs/reviews/${safe}-antigravity.md.
- Do not treat review output as approved fixes.
- Do not claim a command was executed unless it is recorded in docs/verification/${safe}.md or shown in the provided logs.

Review focus:
- Requirement coverage against docs/tasks/${safe}.md.
- Code quality and maintainability.
- Security risks, including secret exposure, unsafe permissions, and unnecessary privileges.
- Operational safety and human-controlled operation boundaries.
- Scope control and unexpected file changes.
- Verification integrity: completed checks must match actually-run commands.
- Documentation consistency and future readability.

Use this structure:

## Review Summary

## Requirement Coverage

## Code Quality / Maintainability

## Security Review

## Operational Risk

## Scope Control

## Verification Review

## Documentation Review

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Verdict
EOF
}

print_fixes_draft() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Draft candidate fixes for the current NewsLab branch.

Read:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/reviews/${safe}-antigravity.md
- docs/reviews/${safe}-coderabbit.md
- Current git diff

Source of truth:
- docs/tasks/${safe}.md

Current branch:
- ${branch}

Fix decision draft output:
- docs/fixes/${safe}-approved-fixes.md

Important:
- This file may contain candidate fixes, but only items explicitly placed under Approved Fixes by the human operator are approved.

$(print_common_rules)

Fix drafting rules:
- AI may draft candidate fixes, but the human operator is the final approval authority.
- Review output alone is not approval to modify code.
- Do not apply fixes in this step.
- Separate approved, rejected, and deferred suggestions clearly.
- If the human has not approved a fix, mark it as candidate or pending approval, not approved.
- Do not invent verification results.
- Production-impacting verification must remain pending unless the human provides actual logs.

Suggested structure:

## Candidate Fixes Pending Human Approval

## Approved Fixes

## Rejected or Deferred Suggestions

## Applied Changes

## Verification Required
EOF
}

print_codex_apply_fixes() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Apply approved fixes for the current NewsLab branch.

Read:
- AGENTS.md
- docs/prompts/codex-implement.md
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md

Source of truth:
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md for approved fixes only

Current branch:
- ${branch}

$(print_common_rules)

Apply-fixes rules:
- Apply only fixes explicitly listed under approved fixes in docs/fixes/${safe}-approved-fixes.md.
- Do not apply review suggestions directly from docs/reviews.
- Review output alone is not a modification instruction.
- Do not apply candidate, rejected, or deferred suggestions.
- Update docs/fixes/${safe}-approved-fixes.md with applied changes when appropriate.
- Record only commands actually run and their results in docs/verification/${safe}.md.
- Run only validation commands allowed by docs/tasks/${safe}.md and docs/fixes/${safe}-approved-fixes.md.
EOF
}

print_pr_draft() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Create the PR draft for the current NewsLab branch.

Read:
- AGENTS.md
- docs/prompts/pr-draft.md
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md
- Current git diff

Source of truth:
- docs/verification/${safe}.md for tests and verification results
- docs/fixes/${safe}-approved-fixes.md for approved fixes that were applied

Current branch:
- ${branch}

Output file:
- docs/pr/${safe}.md

$(print_common_rules)

PR draft rules:
- Do not claim PR merge is complete.
- Do not claim production deployment, K3s rollout, or production verification is complete unless the human provides actual logs.
- If a command is suggested but not run, write it as pending or notes, not completed.
- Do not use review files as proof that verification passed.
- Mention README impact when relevant. If README changes are not needed, state that briefly.

Required sections:

## 작업 내용

## 주요 변경 사항

## 추가/변경된 API

## DB 변경 사항

## README 영향

## 테스트

## 확인 결과

## 비고
EOF
}

print_devlog_draft() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
Create the worklog/devlog draft for the current NewsLab branch.

Read:
- AGENTS.md
- docs/ARCHITECTURE.md
- docs/prompts/worklog-draft.md
- docs/tasks/${safe}.md
- docs/pr/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md
- Human-provided verification logs, if any

Source of truth:
- docs/verification/${safe}.md for actual test and verification results
- docs/fixes/${safe}-approved-fixes.md for approved fixes that were applied

Current branch:
- ${branch}

Output file:
- docs/devlog/${safe}.md

$(print_common_rules)

Devlog rules:
- Make the worklog suitable for Notion.
- Do not claim PR merge is complete unless the human explicitly says it was merged.
- Do not claim production deployment is complete unless the human provides rollout and curl verification logs.
- Do not invent test results.
- If something was not verified, mark it as pending.
- Do not use raw review files as proof that fixes were approved or verification passed.
- Record alternatives considered, chosen approach and rationale, tradeoffs, README update decision, and portfolio-facing summary.

Required sections:

## 작업 목적

## 기존 문제

## 변경 내용

## 구현 상세

## 대안 검토

## 선택한 접근과 근거

## 트레이드오프

## 테스트

## 운영 반영

## README 업데이트 판단

## 확인 결과

## 이번 단계의 의미

## 포트폴리오용 요약

## 다음 단계 후보
EOF
}

main() {
  if [ $# -ne 1 ]; then
    usage
    exit 1
  fi

  local command="$1"
  local branch
  branch=$(branch_name)

  if [ -z "$branch" ]; then
    echo "Error: could not determine current git branch." >&2
    exit 1
  fi

  local safe
  safe=$(safe_name "$branch")

  case "$command" in
    files)
      print_files "$branch" "$safe"
      ;;
    codex-implement)
      print_codex_implement "$branch" "$safe"
      ;;
    antigravity-review)
      print_antigravity_review "$branch" "$safe"
      ;;
    antigravity-review-write)
      print_antigravity_review_write "$branch" "$safe"
      ;;
    fixes-draft)
      print_fixes_draft "$branch" "$safe"
      ;;
    codex-apply-fixes)
      print_codex_apply_fixes "$branch" "$safe"
      ;;
    pr-draft)
      print_pr_draft "$branch" "$safe"
      ;;
    devlog-draft)
      print_devlog_draft "$branch" "$safe"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Error: unknown command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
