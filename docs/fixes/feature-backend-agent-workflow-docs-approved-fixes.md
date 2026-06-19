# Approved Fixes: backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## Approved Fixes

### 1. `scripts/agent_next_step.sh`를 신규 backend agent workflow 문서 구조와 정렬

- [x] `codex-implement`가 다음 문서를 필수로 읽도록 수정한다.
  - `AGENTS.md`
  - `docs/tasks/<safe-branch>.md`
  - `docs/agent/backend-workflow.md`
  - `docs/agent/codex-instructions.md`
  - `docs/agent/verification-gates.md`
  - `docs/agent/forbidden-commands.md`

- [x] `antigravity-review`와 `antigravity-review-write`가 다음 문서를 필수로 읽도록 수정한다.
  - `AGENTS.md`
  - `docs/tasks/<safe-branch>.md`
  - `docs/verification/<safe-branch>.md`
  - `docs/fixes/<safe-branch>-approved-fixes.md`
  - `docs/agent/backend-workflow.md`
  - `docs/agent/antigravity-review.md`
  - `docs/agent/verification-gates.md`
  - `docs/agent/forbidden-commands.md`
  - 기존 `docs/reviews/<safe-branch>-antigravity.md`
  - 현재 `git diff`

- [x] `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`는 전체 내용을 항상 읽는 필수 문서가 아니라 index 문서로 안내한다.

- [x] 현재 task와 직접 관련된 `docs/architecture/*`, `docs/runbooks/*` 문서만 선택적으로 읽도록 prompt에 명시한다.

- [x] 기존 `docs/prompts/*` 문서를 삭제하지 않는다.
  - 신규 `docs/agent/*` 문서를 현재 기준 source of truth로 사용한다.
  - 기존 `docs/prompts/*`는 호환용 보조 문서로 유지한다.
  - 중복 제거 여부는 후속 작업으로 남긴다.

### 2. `scripts/agent_next_step.sh`의 내부 설명과 생성 prompt를 한국어화

- [x] `usage()`의 command 설명을 한국어로 변경한다.
- [x] workflow file 설명을 한국어로 변경한다.
- [x] 공통 규칙을 한국어로 변경한다.
- [x] Codex 구현 prompt를 한국어로 변경한다.
- [x] Antigravity review prompt를 한국어로 변경한다.
- [x] review file 작성 prompt를 한국어로 변경한다.
- [x] fixes draft prompt를 한국어로 변경한다.
- [x] approved fixes 적용 prompt를 한국어로 변경한다.
- [x] PR 초안 prompt를 한국어로 변경한다.
- [x] devlog 초안 prompt를 한국어로 변경한다.
- [x] 오류 메시지와 안내 문구를 한국어로 변경한다.

다음 항목은 원문 표기를 유지할 수 있다.

```text
Codex
Antigravity
CodeRabbit
WIP 1
source of truth
branch
git diff
Markdown
API
DB
Kubernetes
Docker
command 이름
파일 경로
shell command
```

### 3. Codex 구현 prompt에 WIP 1과 checklist 완료 규칙 반영

- [x] `WIP 1` 원칙을 공통 규칙 또는 구현 규칙에 포함한다.
- [x] 한 번에 하나의 checklist 작업 단위만 진행하도록 명시한다.
- [x] 현재 작업 단위의 다음 절차를 완료한 뒤 다음 단위로 이동하도록 명시한다.

```text
조사
→ 변경
→ 문서화
→ 검증
→ verification 기록
→ checklist 갱신
```

- [x] 완료하지 않은 checklist 항목은 체크하지 않도록 명시한다.
- [x] 코드 변경만 끝나고 검증이 끝나지 않은 항목은 완료 처리하지 않도록 명시한다.
- [x] 실행하지 않은 검증은 다음 중 하나로 기록하도록 명시한다.
  - 미수행
  - 환경 제약으로 실패
  - 운영 반영 후 확인 필요
  - 사람이 수행 필요

- [x] 새로 발견된 문제는 다음 중 하나로 분류하도록 명시한다.
  - 현재 작업 blocker
  - 범위 내 결함
  - 후속 작업 후보
  - 과거 기록

- [x] 코드, API, DB, script 또는 pipeline 동작이 변경되면 task 범위에 맞는 end-to-end 검증을 수행하도록 명시한다.
- [x] 운영 반영이 필요한 검증은 사람이 수행하도록 남기고 완료로 기록하지 않도록 명시한다.

### 4. `Approved Fixes` checklist를 Codex가 적용 결과에 맞게 갱신

- [x] `codex-apply-fixes`는 `Approved Fixes` 아래에 명시된 항목만 적용하도록 유지한다.
- [x] Codex는 사람이 승인하지 않은 항목을 추가하거나 적용하지 않는다.
- [x] 수정과 관련 검증까지 완료한 항목만 `- [x]`로 변경한다.
- [x] 부분 적용 또는 검증 미완료 항목은 `- [ ]` 상태를 유지한다.
- [x] 부분 적용된 항목에는 상태와 남은 작업을 하위 항목으로 기록한다.

예:

```md
- [ ] Antigravity review 재검토 규칙 반영
  - 상태: 부분 적용
  - 남은 작업: 기존 review 파일 보존 및 재검토 append 동작 확인
```

- [x] `Applied Changes`에는 실제로 적용한 변경만 기록한다.
- [x] `Applied Changes`의 각 항목은 어떤 Approved Fix를 구현했는지 연결해 기록한다.
- [x] 실제 실행한 command와 결과는 `docs/verification/<safe-branch>.md`에 기록한다.

### 5. Antigravity review가 fixes 적용 여부와 verification 근거를 검토하도록 보완

- [x] Antigravity review는 task의 checklist 완료 상태를 실제 diff와 verification 기록에 대조한다.
- [x] 증거 없이 완료 처리된 checklist 항목이 있으면 문제로 기록한다.
- [x] `Approved Fixes`에서 체크된 항목이 실제로 적용되었는지 확인한다.
- [x] `Approved Fixes`의 체크 상태만으로 해결됐다고 판단하지 않는다.
- [x] 다음 자료를 함께 확인하도록 한다.
  - Approved Fixes checklist
  - 현재 diff
  - verification command와 결과
  - task acceptance criteria

- [x] 승인되지 않은 review suggestion이 임의로 적용되지 않았는지 확인한다.
- [x] fix 적용 과정에서 새로운 결함이나 scope creep이 발생하지 않았는지 확인한다.
- [x] 동작 변경 작업에서 end-to-end 검증이 수행되었는지 확인한다.
- [x] 수행하지 못한 end-to-end 검증이 pending 또는 사람이 수행 필요로 기록되었는지 확인한다.

### 6. 최초 리뷰와 재검토 결과를 하나의 review 파일에 누적

Antigravity review 파일은 하나만 사용한다.

```text
docs/reviews/<safe-branch>-antigravity.md
```

별도의 `-rereview.md` 파일은 만들지 않는다.

- [x] 최초 review가 없는 경우 기존 review 구조로 최초 검토 내용을 작성한다.
- [x] 기존 review 파일이 있는 경우 기존 내용을 삭제하거나 새 내용으로 교체하지 않는다.
- [x] 재검토 시 기존 review의 원문과 기존 `Re-review` 이력을 유지한다.
- [x] 재검토 결과는 같은 파일 아래쪽에 새로운 회차로 추가한다.

```md
## Re-review 1

## Re-review 2
```

- [x] 재검토 회차 번호는 기존 review 파일의 `Re-review` 섹션을 확인해 다음 번호를 사용한다.
- [x] 재검토 시 기존 review에서 발견된 문제의 해결 여부를 확인한다.
- [x] 기존 문제의 상태는 다음 중 하나로 판정한다.
  - 해결됨
  - 부분 해결
  - 미해결
  - 적용 대상 아님

- [x] 기존 문제 원문은 삭제하거나 의미를 변경하지 않는다.
- [x] 기존 문제의 상태를 확인할 때 해결 근거를 재검토 섹션에 기록한다.
- [x] 기존 `Required Fixes Before PR` 항목은 실제 해결이 확인된 경우에만 체크한다.
- [x] 새로운 문제가 발견되면 기존 문제와 구분해 재검토 섹션에 추가한다.
- [x] 재검토 후 현재 상태를 기준으로 최종 판단을 다시 기록한다.

사용 가능한 최종 판단:

```text
APPROVED
APPROVED WITH NOTES
CHANGES REQUIRED
```

### 7. `antigravity-review-write`의 단일 review file 갱신 규칙 반영

- [x] `antigravity-review-write`의 writable file은 계속 다음 하나로 유지한다.

```text
docs/reviews/<safe-branch>-antigravity.md
```

- [x] 파일이 없거나 비어 있으면 최초 review를 작성한다.
- [x] 파일이 이미 존재하면 재검토 모드로 동작하도록 prompt에 명시한다.
- [x] 재검토 모드에서는 기존 파일을 전면 재작성하지 않도록 명시한다.
- [x] 기존 review 내용을 보존하고 파일 아래에 `Re-review N` 섹션을 추가하도록 명시한다.
- [x] 기존 review를 삭제, 축약, 성공 결과로 치환하지 않도록 명시한다.
- [x] review 파일은 review 결과만 기록하며 fixes 승인 문서로 사용하지 않는다.
- [x] 수정 승인 여부는 `docs/fixes/<safe-branch>-approved-fixes.md`만 기준으로 한다.

### 8. `agent_next_step.sh`의 workflow file 안내 보완

- [x] `files` command 출력에 다음 현재 기준 문서를 추가한다.

```text
Backend workflow:
- docs/agent/backend-workflow.md
- docs/agent/codex-instructions.md
- docs/agent/antigravity-review.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md

Indexes:
- docs/ARCHITECTURE.md
- docs/RUNBOOK.md
```

- [x] Antigravity review는 최초 검토와 재검토 모두 동일한 review 파일을 사용한다고 안내한다.
- [x] 별도의 rereview artifact 경로는 추가하지 않는다.

## Rejected or Deferred Suggestions

### 1. 별도 Antigravity rereview 파일 생성

Rejected.

다음과 같은 별도 파일은 만들지 않는다.

```text
docs/reviews/<safe-branch>-antigravity-rereview.md
```

최초 review와 재검토 결과는 하나의 review 파일에서 이력으로 관리한다.

### 2. 별도의 `antigravity-rereview`, `antigravity-rereview-write` command 추가

Deferred.

현재는 기존 command를 유지한다.

```text
antigravity-review
antigravity-review-write
```

기존 review 파일이 있는지에 따라 최초 검토 또는 재검토를 수행하도록 prompt를 개선한다.

향후 단일 command 방식이 혼란을 일으키는 경우 별도 command 도입을 다시 검토한다.

### 3. Checklist 자동 파싱 및 자동 완료 판정

Deferred.

예:

```text
scripts/check_task_checklist.sh
```

현재는 Codex가 task 및 fixes checklist를 갱신하고 Antigravity가 diff와 verification을 근거로 독립 검토한다.

자동 판정은 verification artifact 구조화 이후 별도 작업에서 검토한다.

### 4. 검증 command 자동 실행

Deferred.

`scripts/agent_next_step.sh`는 prompt와 artifact 경로를 출력하는 역할을 유지한다.

다음 자동 실행 기능은 이번 범위에 포함하지 않는다.

```text
test command 실행
Markdown link 검사
forbidden file 검사
task checklist 검사
verification command/result 정합성 검사
```

### 5. Codex, Antigravity 또는 CodeRabbit 직접 실행

Rejected.

현재 script는 외부 agent나 GitHub 작업을 자동 실행하지 않는다.

사람이 생성된 prompt를 확인한 뒤 직접 실행하는 경계를 유지한다.

### 6. Git hook 또는 pre-commit 도입

Deferred.

Repository 전체 개발 환경에 영향을 줄 수 있으므로 별도 작업으로 분리한다.

### 7. 기존 `docs/prompts/*` 즉시 삭제

Deferred.

현재 다른 script 또는 과거 workflow가 참조할 가능성이 있으므로 유지한다.

신규 `docs/agent/*`를 현재 기준으로 사용하고, 중복 제거는 별도 후속 작업에서 검토한다.

## Applied Changes

- Approved Fix 1 적용
  - `codex-implement`, `antigravity-review`, `antigravity-review-write`가 신규
    `docs/agent/*` 기준 문서를 읽도록 변경했다.
  - Architecture와 Runbook은 index로 안내하고 관련 세부 문서만 선택하도록
    변경했다.

- Approved Fix 2 적용
  - `usage()`, workflow file 안내, 공통 규칙, 모든 생성 prompt와 오류 메시지를
    한국어로 변경했다.

- Approved Fix 3 적용
  - WIP 1, 작업 단위 완료 순서, checklist 갱신, 문제 분류, end-to-end 및
    human-controlled verification 규칙을 추가했다.

- Approved Fix 4 적용
  - `codex-apply-fixes`에 승인 항목만 적용하고 검증 완료 항목만 체크하며
    `Applied Changes`와 verification을 실제 결과로 갱신하는 규칙을 추가했다.

- Approved Fix 5 적용
  - Antigravity가 task checklist, Approved Fixes, diff, verification,
    acceptance criteria를 함께 대조하도록 보완했다.

- Approved Fix 6~7 적용
  - 최초 review와 재검토를 동일 review 파일에 누적하고 기존 원문과 이력을
    보존하도록 review prompt와 agent 지침을 변경했다.

- Approved Fix 8 적용
  - `files` 출력에 backend workflow 문서와 architecture/runbook index를
    추가하고 단일 review 파일 사용을 안내했다.

- 검증 중 수정
  - Script 재작성 직후 executable bit가 사라져 직접 실행이 실패한 것을
    확인했고 `chmod +x scripts/agent_next_step.sh`로 복원한 뒤 재검증했다.

## Verification Required

### 1. Shell 문법 검사

```bash
bash -n scripts/agent_next_step.sh
```

기대 결과:

```text
exit code 0
```

### 2. 도움말 확인

```bash
scripts/agent_next_step.sh --help
```

확인 항목:

- 기존 command가 모두 유지된다.
- 별도의 rereview command가 추가되지 않았다.
- command 설명이 한국어로 출력된다.

### 3. Workflow 파일 안내 확인

```bash
scripts/agent_next_step.sh files
```

확인 항목:

- task
- Antigravity review
- CodeRabbit review
- approved fixes
- verification
- PR draft
- devlog
- 신규 `docs/agent/*`
- architecture/runbook index

Antigravity 최초 review와 재검토가 동일한 review 파일을 사용한다고 안내해야 한다.

### 4. Codex 구현 prompt 확인

```bash
scripts/agent_next_step.sh codex-implement
```

확인 항목:

- task가 source of truth로 표시된다.
- 신규 `docs/agent/*` 문서를 읽는다.
- Architecture와 Runbook이 index로 설명된다.
- task 관련 세부 문서만 선택적으로 읽도록 안내한다.
- WIP 1이 포함된다.
- 조사, 변경, 문서화, 검증, verification 기록, checklist 갱신 후 다음 작업으로 이동하도록 안내한다.
- 완료하지 않은 checklist를 체크하지 않도록 안내한다.
- end-to-end 검증 및 human-controlled verification 원칙이 포함된다.
- 출력 설명이 한국어로 작성되어 있다.

### 5. Antigravity review prompt 확인

```bash
scripts/agent_next_step.sh antigravity-review
```

확인 항목:

- task, fixes, verification, 기존 review, current diff를 확인하도록 안내한다.
- 최초 review가 없으면 최초 검토를 수행하도록 안내한다.
- 기존 review가 있으면 재검토하도록 안내한다.
- checklist와 verification evidence를 대조한다.
- Approved Fixes 적용 여부를 확인한다.
- 승인되지 않은 suggestion의 임의 적용 여부를 확인한다.
- 기존 문제 해결과 신규 문제를 구분한다.
- 파일을 수정하지 않고 chat에만 출력하도록 유지한다.

### 6. Antigravity review write prompt 확인

```bash
scripts/agent_next_step.sh antigravity-review-write
```

확인 항목:

- writable file은 `docs/reviews/<safe-branch>-antigravity.md` 하나뿐이다.
- 기존 review가 없으면 최초 review를 작성한다.
- 기존 review가 있으면 내용을 보존하고 `Re-review N`을 추가한다.
- 기존 문제 원문과 이전 재검토 이력을 삭제하지 않는다.
- 해결이 확인된 기존 required fix만 체크한다.
- 새 문제를 별도로 기록한다.
- fixes 파일을 수정하지 않는다.
- verification 파일을 수정하지 않는다.
- 출력 설명이 한국어로 작성되어 있다.

### 7. Approved fixes 적용 prompt 확인

```bash
scripts/agent_next_step.sh codex-apply-fixes
```

확인 항목:

- `Approved Fixes`의 항목만 적용하도록 안내한다.
- 수정과 검증이 완료된 항목만 `- [x]` 처리하도록 안내한다.
- 부분 적용 또는 검증 미완료 항목은 체크하지 않도록 안내한다.
- `Applied Changes`를 실제 결과에 맞게 갱신하도록 안내한다.
- 실제 command 결과를 verification 문서에 기록하도록 안내한다.

### 8. 기존 command 회귀 확인

```bash
scripts/agent_next_step.sh fixes-draft
scripts/agent_next_step.sh pr-draft
scripts/agent_next_step.sh devlog-draft
```

확인 항목:

- 각 command가 정상적으로 prompt를 출력한다.
- branch safe name 기반 경로가 유지된다.
- 공통 고위험 명령 제한이 유지된다.
- 출력 문구가 한국어 기준이다.
- 기존 역할이 제거되지 않았다.

### 9. 단일 review 파일 보존 방식 확인

기존 review 파일의 checksum 또는 복사본을 확보한다.

```bash
cp \
  docs/reviews/feature-backend-agent-workflow-docs-antigravity.md \
  /tmp/feature-backend-agent-workflow-docs-antigravity.before.md
```

재검토 결과 작성 후 다음을 확인한다.

```bash
test -f docs/reviews/feature-backend-agent-workflow-docs-antigravity.md

diff -u \
  /tmp/feature-backend-agent-workflow-docs-antigravity.before.md \
  docs/reviews/feature-backend-agent-workflow-docs-antigravity.md
```

확인 기준:

- 기존 review 내용이 삭제되지 않았다.
- 기존 문제와 verdict 원문이 임의로 치환되지 않았다.
- 파일 아래에 `Re-review 1` 섹션이 추가되었다.
- 기존 문제의 해결 여부와 Approved Fixes 적용 결과가 기록되었다.
- 새로운 문제가 있다면 별도로 기록되었다.

실제 Antigravity file write를 아직 수행하지 않았다면 이 검증은 `재검토 후 사람이 확인 필요`로 기록한다.

### 10. 변경 범위 확인

```bash
git diff --name-only
git diff --stat
git diff --check
```

확인 기준:

- 변경이 승인된 script와 문서 범위에 한정된다.
- backend application source 변경이 없다.
- DB 및 migration 변경이 없다.
- K3s manifest 변경이 없다.
- Dockerfile 변경이 없다.
- GitHub Actions workflow 변경이 없다.
- frontend 변경이 없다.
- `git diff --check`가 통과한다.

### 11. 민감정보 확인

```bash
git grep -n -i -E \
  'API_KEY|TOKEN|PASSWORD|PRIVATE KEY|BEGIN PRIVATE|DATABASE_URL=|SECRET=' \
  -- \
  scripts/agent_next_step.sh \
  docs/agent \
  docs/fixes/feature-backend-agent-workflow-docs-approved-fixes.md
```

확인 기준:

- 실제 credential 값이 없다.
- 정책 문구와 환경 변수명만 존재한다.

### 12. 최종 Antigravity 재검토

Codex가 승인 수정 적용과 verification 기록을 완료한 뒤 기존 command로 Antigravity review를 다시 수행한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

최종 확인 항목:

- 최초 review 내용 보존
- Approved Fixes checklist와 실제 diff 일치
- 체크된 fix의 verification 근거 존재
- 기존 문제의 해결 여부
- 새로 발생한 문제 여부
- scope 위반 여부
- 추가 필수 수정 여부
- PR 제출 가능 여부
