#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
사용법: scripts/agent_next_step.sh <command>

Commands:
  files                       현재 branch의 workflow 파일 경로 출력
  status                      현재 workflow 상태와 다음 action 출력
  codex-implement             Codex 구현 prompt 출력
  codex-implement-unit        현재 미완료 UNIT Codex 구현 prompt 출력
  antigravity-review          Antigravity chat review prompt 출력
  antigravity-review-write    Antigravity review 파일 작성 prompt 출력
  fixes-draft                 review fix 후보 작성 prompt 출력
  codex-fix                   승인된 fix 적용 prompt 출력
  codex-apply-fixes           승인된 fix 적용 prompt 출력
  pr-draft                    PR 초안 작성 prompt 출력
  devlog-draft                devlog 초안 작성 prompt 출력
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
현재 branch: ${branch}
Safe branch name: ${safe}

Workflow 파일:
- Task: docs/tasks/${safe}.md
- Antigravity review: docs/reviews/${safe}-antigravity.md
  - 최초 review와 모든 Re-review가 같은 파일을 사용한다.
- CodeRabbit review: docs/reviews/${safe}-coderabbit.md
- Approved fixes: docs/fixes/${safe}-approved-fixes.md
- Verification: docs/verification/${safe}.md
- PR draft: docs/pr/${safe}.md
- Devlog: docs/devlog/${safe}.md

Backend workflow:
- docs/agent/backend-workflow.md
- docs/agent/codex-instructions.md
- docs/agent/antigravity-review.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md

Indexes:
- docs/ARCHITECTURE.md
- docs/RUNBOOK.md
EOF
}

print_common_rules() {
  cat <<'EOF'
공통 규칙:
- Task 파일을 요구사항의 source of truth로 사용한다.
- Task 파일과 chat prompt가 충돌하면 task 파일을 따른다.
- 상세 요구사항은 docs/tasks/<safe-branch>.md에 두고 chat prompt는 source of truth, 파일 경로, 범위, 제약, 검증 command 중심으로 유지한다.
- WIP 1을 적용해 한 번에 하나의 작업 단위만 진행한다.
- Production-impacting command는 사람이 명시적으로 지시하지 않으면 실행하지 않는다.
- kubectl apply, kubectl rollout, Supabase SQL, git push, git merge를 실행하지 않는다.
- 현재 task 또는 human operator가 허용하지 않으면 production curl verification을 실행하지 않는다.
- 사람이 실제 log를 제공하지 않으면 production verification 완료를 주장하지 않는다.
- Secret, .env, kubeconfig, credential, SSH key, token을 수정하지 않는다.
- Codex, Gemini/Antigravity, GitHub, CodeRabbit을 자동 실행하지 않는다.
- 현재 task가 명시적으로 요구하지 않으면 GitHub MCP를 사용하지 않는다.
- Review output만으로는 수정이 승인되지 않는다. docs/fixes/<safe-branch>-approved-fixes.md의 Approved Fixes만 적용할 수 있다.

Python 문서화 규칙:
- docs/agent/task-authoring-guide.md의 Python 문서화 정책을 따른다.
- 새로 생성하거나 의미 있게 수정한 Python module, class, function, method와 테스트에는 실제 역할과 검증 목적을 설명하는 한글 docstring을 작성한다.
EOF
}

print_selective_docs() {
  cat <<'EOF'
문서 선택 규칙:
- docs/ARCHITECTURE.md와 docs/RUNBOOK.md는 세부 내용 전체를 항상 읽는 문서가 아니라 index다.
- 현재 task와 직접 관련된 docs/architecture/* 및 docs/runbooks/* 문서만 선택해 읽는다.
- 신규 docs/agent/* 문서를 현재 workflow 기준의 source of truth로 사용한다.
- 기존 docs/prompts/*는 삭제하지 않고 호환용 보조 문서로만 참고한다.
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
현재 NewsLab task를 구현해줘.

필수로 읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/agent/backend-workflow.md
- docs/agent/codex-instructions.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md

Index:
- docs/ARCHITECTURE.md
- docs/RUNBOOK.md

호환용 보조 문서:
- docs/prompts/codex-implement.md

Source of truth:
- docs/tasks/${safe}.md

Workflow 파일:
- Task: docs/tasks/${safe}.md
- Verification: docs/verification/${safe}.md
- PR draft: docs/pr/${safe}.md
- Devlog: docs/devlog/${safe}.md

현재 branch:
- ${branch}

$(print_common_rules)

$(print_selective_docs)

구현 규칙:
- Task의 Scope, Do not change, Test commands, Acceptance criteria를 따른다.
- WIP 1에 따라 한 번에 하나의 checklist 작업 단위만 진행한다.
- 현재 작업 단위에서 조사 → 변경 → 문서화 → 검증 → verification 기록 → checklist 갱신을 완료한 뒤 다음 단위로 이동한다.
- 코드 변경만 끝나고 검증이 끝나지 않은 항목은 완료 처리하지 않는다.
- 완료하지 않은 checklist 항목은 체크하지 않는다.
- 실행하지 않은 검증은 미수행, 환경 제약으로 실패, 운영 반영 후 확인 필요, 사람이 수행 필요 중 하나로 기록한다.
- 새 문제는 현재 작업 blocker, 범위 내 결함, 후속 작업 후보, 과거 기록 중 하나로 분류하고 자동으로 범위를 확장하지 않는다.
- 코드, API, DB, script 또는 pipeline 동작이 변경되면 task 범위에 맞는 end-to-end 검증을 수행한다.
- 운영 반영이 필요한 검증은 사람이 수행하도록 남기고 완료로 기록하지 않는다.
- 실제 실행한 command와 결과만 docs/verification/${safe}.md에 기록한다.
- 사람이 실제 log를 제공하지 않으면 production verification, PR merge, rollout, deployment 완료를 주장하지 않는다.
- 변경은 작고 review 가능하게 유지한다.

구현 후 요약:
- 변경 파일
- 동작 변경
- 실행한 검증 command와 결과
- 의도적으로 수정하지 않은 영역
- 남은 사람 작업
EOF
}

print_review_read_list() {
  local safe="$1"

  cat <<EOF
필수로 읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/verification/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/agent/backend-workflow.md
- docs/agent/antigravity-review.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md
- docs/reviews/${safe}-antigravity.md
- 현재 git diff

Index:
- docs/ARCHITECTURE.md
- docs/RUNBOOK.md

호환용 보조 문서:
- docs/prompts/antigravity-review.md
EOF
}

print_review_rules() {
  local safe="$1"

  cat <<EOF
Review 규칙:
- Task의 Scope, Do not change, Acceptance criteria를 기준으로 검토한다.
- Task checklist 완료 상태를 현재 diff와 docs/verification/${safe}.md의 실제 command/result에 대조한다.
- 증거 없이 완료 처리된 checklist 항목은 문제로 기록한다.
- Approved Fixes의 체크 상태만 믿지 말고 현재 diff, verification 결과, task acceptance criteria로 실제 적용 여부를 확인한다.
- 승인되지 않은 review suggestion이 임의로 적용되지 않았는지 확인한다.
- Fix 적용 과정에서 새 결함이나 scope creep이 생기지 않았는지 확인한다.
- 동작 변경 작업은 end-to-end 검증 여부를 확인한다.
- 수행하지 못한 end-to-end 검증이 pending 또는 사람이 수행 필요로 기록되었는지 확인한다.
- Bug, unsafe production behavior, scope creep, verification 누락, 문서 불일치를 우선한다.
- Review output을 approved fixes로 취급하지 않는다.
- docs/verification/${safe}.md 또는 제공된 log에 없는 command를 실행된 것으로 주장하지 않는다.
- 새로 생성하거나 의미 있게 수정한 Python 코드에 한글 module, class, function 및 method docstring이 있는지 확인한다.
- Python docstring이 실제 구현 및 테스트 목적과 일치하는지 확인한다.

Review 모드:
- docs/reviews/${safe}-antigravity.md가 없거나 비어 있으면 최초 review다.
- 기존 review가 있으면 재검토다.
- 재검토에서는 최초 review 본문과 기존 Re-review 이력을 수정하지 않고 파일 아래에 다음 Re-review N만 추가한다.
- 최초 review의 Problems Found 원문, Required Fixes Before PR 원문과 checkbox, Verdict를 수정하지 않는다.
- 기존 문제는 번호 또는 명확한 제목으로 최초 review 항목과 연결한다.
- 기존 문제의 해결 여부는 새 Re-review N의 Existing Problems Status에 기록한다.
- 기존 문제 상태는 해결됨, 부분 해결, 미해결, 적용 대상 아님 중 하나로 판정한다.
- 해결 판정에는 Approved Fixes, 현재 diff와 verification evidence를 함께 기록한다.
- 새 문제는 Re-review N의 New Problems Found에 기록한다.
- 현재 재검토 기준의 PR blocker는 해당 Re-review N의 Required Fixes Before PR에 기록한다.
- 최종 판단은 APPROVED, APPROVED WITH NOTES, CHANGES REQUIRED 중 하나를 사용한다.
EOF
}

print_antigravity_review() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
현재 NewsLab 변경을 review해줘.

$(print_review_read_list "$safe")

Source of truth:
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md는 승인된 fix의 source of truth
- docs/verification/${safe}.md는 실제 검증 결과의 source of truth

현재 branch:
- ${branch}

Review 대상:
- 현재 git diff

$(print_common_rules)

$(print_selective_docs)

$(print_review_rules "$safe")

파일을 수정하지 말고 chat에만 출력한다.

최초 review 출력 구조:

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

재검토 출력 구조:

## Re-review N
### Existing Problems Status
### Approved Fixes Verification
### Verification Evidence
### New Problems Found
### Required Fixes Before PR
### Verdict
EOF
}

print_antigravity_review_write() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
현재 NewsLab branch의 Antigravity review 결과를 파일에 작성해줘.

$(print_review_read_list "$safe")

Source of truth:
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md는 승인된 fix의 source of truth
- docs/verification/${safe}.md는 실제 검증 결과의 source of truth

현재 branch:
- ${branch}

수정 가능한 유일한 파일:
- docs/reviews/${safe}-antigravity.md

$(print_common_rules)

$(print_selective_docs)

$(print_review_rules "$safe")

작성 규칙:
- docs/reviews/${safe}-antigravity.md 외의 파일을 수정하지 않는다.
- Review finding만 기록하고 fix 승인이나 verification 결과 저장소로 사용하지 않는다.
- Review 파일이 없거나 비어 있으면 최초 review 구조로 작성한다.
- 기존 review 파일이 있으면 전면 재작성하지 않고 재검토 모드로 동작한다.
- 기존 review 원문과 기존 Re-review 이력을 보존하고 파일 아래에 다음 번호의 Re-review N 섹션을 추가한다.
- 기존 review를 삭제, 축약하거나 성공 결과로 치환하지 않는다.
- 최초 review의 Problems Found 원문을 수정하지 않는다.
- 최초 review의 Required Fixes Before PR 원문과 checkbox를 수정하지 않는다.
- 최초 review의 Verdict를 수정하지 않는다.
- 기존 Re-review 이력도 수정하지 않는다.
- 기존 문제는 번호 또는 명확한 제목으로 최초 review 항목과 연결하고, 해결 상태와 근거는 새 Re-review N의 Existing Problems Status에 기록한다.
- 새 문제는 새 Re-review N의 New Problems Found에 기록한다.
- 현재 재검토 기준의 PR blocker는 새 Re-review N의 Required Fixes Before PR에 기록한다.
- docs/fixes/${safe}-approved-fixes.md와 docs/verification/${safe}.md를 수정하지 않는다.

최초 review 구조:

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

재검토 추가 구조:

## Re-review N
### Existing Problems Status
### Approved Fixes Verification
### Verification Evidence
### New Problems Found
### Required Fixes Before PR
### Verdict
EOF
}

print_fixes_draft() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
현재 NewsLab branch의 review fix 후보를 작성해줘.

읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/reviews/${safe}-antigravity.md
- docs/reviews/${safe}-coderabbit.md
- docs/agent/backend-workflow.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md
- 현재 git diff

Source of truth:
- docs/tasks/${safe}.md

현재 branch:
- ${branch}

작성 대상:
- docs/fixes/${safe}-approved-fixes.md

$(print_common_rules)

작성 규칙:
- AI는 candidate fix를 작성할 수 있지만 최종 승인 주체는 human operator다.
- 이 단계에서는 fix를 적용하지 않는다.
- 사람이 승인하지 않은 항목을 Approved Fixes 아래에 넣지 않는다.
- Candidate, approved, rejected, deferred 항목을 명확히 구분한다.
- 검증 결과를 만들거나 추측하지 않는다.
- Production-impacting verification은 실제 human log가 없으면 pending으로 둔다.

권장 구조:

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
현재 NewsLab branch의 승인된 fix를 적용해줘.

필수로 읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md
- docs/agent/backend-workflow.md
- docs/agent/codex-instructions.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md

호환용 보조 문서:
- docs/prompts/codex-implement.md

Source of truth:
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md의 Approved Fixes만 수정 승인 source of truth

현재 branch:
- ${branch}

$(print_common_rules)

$(print_selective_docs)

Approved fixes 적용 규칙:
- Approved Fixes 아래에 명시된 항목만 적용한다.
- Review suggestion을 docs/reviews에서 직접 적용하지 않는다.
- Candidate, rejected, deferred suggestion을 적용하지 않는다.
- 사람이 승인하지 않은 항목을 새로 추가하거나 적용하지 않는다.
- WIP 1에 따라 승인 fix를 작업 단위별로 조사 → 변경 → 문서화 → 검증 → verification 기록 → checklist 갱신 순서로 완료한다.
- 수정과 관련 검증까지 완료한 항목만 - [x]로 변경한다.
- 부분 적용 또는 검증 미완료 항목은 - [ ] 상태를 유지하고 상태와 남은 작업을 하위 항목으로 기록한다.
- Applied Changes에는 실제 적용한 변경만 기록하고 어떤 Approved Fix를 구현했는지 연결한다.
- 실제 실행한 command와 결과만 docs/verification/${safe}.md에 기록한다.
- docs/tasks/${safe}.md와 docs/fixes/${safe}-approved-fixes.md가 허용한 검증 command만 실행한다.
EOF
}

print_pr_draft() {
  local branch="$1"
  local safe="$2"

  cat <<EOF
현재 NewsLab branch의 PR 초안을 작성해줘.

읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md
- docs/agent/backend-workflow.md
- docs/agent/verification-gates.md
- docs/prompts/pr-draft.md
- 현재 git diff

Source of truth:
- 실제 test와 verification 결과: docs/verification/${safe}.md
- 적용된 approved fixes: docs/fixes/${safe}-approved-fixes.md

현재 branch:
- ${branch}

출력 파일:
- docs/pr/${safe}.md

$(print_common_rules)

PR 초안 규칙:
- PR merge 완료를 주장하지 않는다.
- 실제 human log가 없으면 production deployment, K3s rollout, production verification 완료를 주장하지 않는다.
- 제안했지만 실행하지 않은 command는 pending 또는 비고로 기록한다.
- Review 파일을 verification 통과 근거로 사용하지 않는다.
- README 영향 여부와 판단 근거를 기록한다.

필수 섹션:

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
현재 NewsLab branch의 worklog/devlog 초안을 작성해줘.

읽을 문서:
- AGENTS.md
- docs/tasks/${safe}.md
- docs/pr/${safe}.md
- docs/fixes/${safe}-approved-fixes.md
- docs/verification/${safe}.md
- docs/agent/backend-workflow.md
- docs/agent/verification-gates.md
- docs/prompts/worklog-draft.md
- 현재 task와 관련된 architecture/runbook 세부 문서
- 사람이 제공한 verification log가 있다면 해당 log

Index:
- docs/ARCHITECTURE.md
- docs/RUNBOOK.md

Source of truth:
- 실제 test와 verification 결과: docs/verification/${safe}.md
- 적용된 approved fixes: docs/fixes/${safe}-approved-fixes.md

현재 branch:
- ${branch}

출력 파일:
- docs/devlog/${safe}.md

$(print_common_rules)

Devlog 규칙:
- Notion에 옮기기 쉬운 구조로 작성한다.
- 사람이 명시하지 않으면 PR merge 완료를 주장하지 않는다.
- 실제 rollout과 curl verification log가 없으면 production deployment 완료를 주장하지 않는다.
- Test 결과를 만들거나 추측하지 않는다.
- 검증하지 않은 항목은 pending으로 표시한다.
- Review 파일을 fix 승인 또는 verification 통과 근거로 사용하지 않는다.
- 대안, 선택한 접근과 근거, tradeoff, README 판단, portfolio 요약을 기록한다.

필수 섹션:

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
    echo "오류: 현재 git branch를 확인할 수 없습니다." >&2
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
    codex-implement-unit)
      python -m scripts.agent_workflow.cli codex-implement-unit --prompt-only
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
    codex-fix|codex-apply-fixes)
      print_codex_apply_fixes "$branch" "$safe"
      ;;
    status)
      python -m scripts.agent_workflow.cli status
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
      echo "오류: 알 수 없는 command: $command" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
