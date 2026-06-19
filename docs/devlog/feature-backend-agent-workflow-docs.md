# backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## 작업 목적

NewsLab backend task에서 agent가 매번 긴 architecture와 runbook 전체를 읽는
비용을 줄이고, 구현·review·검증의 완료 조건을 일관되게 만드는 것이
목적이었다.

이번 작업에서는 현재 운영 기준과 과거 작업 기록을 분리하고, Codex와
Antigravity가 task에 필요한 context만 선택해 읽을 수 있는 문서 구조를
만들었다. 동시에 다음 원칙을 backend workflow의 기준으로 고정했다.

```text
WIP 1
= 한 번에 하나의 작업 단위만 진행한다.

작업 단위 완료
= 조사 → 변경 → 문서화 → 검증 → verification 기록 → checklist 갱신
```

완전 자동화된 agent harness를 구현하는 작업은 아니며, 향후 자동 gate를
추가하기 전에 문서 기반 workflow와 source of truth를 정리하는 단계다.

## 기존 문제

- `docs/ARCHITECTURE.md`에 component, data flow, table, API, 운영 경계가 한
  파일에 혼재했다.
- `docs/RUNBOOK.md`에 routine check, local command, 배포, domain/TLS,
  CronJob, agent workflow, Git workflow가 누적되어 1,000줄을 넘었다.
- 현재 운영 기준과 과거 작업 이력·검증 기록의 책임이 명확히 분리되지 않았다.
- Codex 구현과 Antigravity review가 먼저 읽어야 할 문서와 역할별 context가
  분산되어 있었다.
- 코드 변경, 문서화, 검증, checklist 갱신 중 일부만 끝난 상태에서도 작업이
  완료된 것으로 해석될 수 있었다.
- Review 결과와 사람이 승인한 fix, 실제 verification 결과의 source of truth가
  prompt에서 충분히 강제되지 않았다.
- `scripts/agent_next_step.sh`가 기존 통합 문서와 영문 prompt를 기준으로
  동작해 새 문서 구조와 맞지 않았다.
- 최초 Antigravity review의 정책 문서는 `Problems Found`를 요구했지만 chat
  review prompt는 `Existing Problems Status`와 `New Problems Found`를
  최상위 heading으로 사용해 출력 계약이 일치하지 않았다.
- 기존 review 원문을 보존한다는 규칙과 해결된 required fix의 checkbox를
  수정한다는 규칙이 함께 존재해 review 이력의 불변성 기준이 모호했다.

## 변경 내용

- `AGENTS.md`를 task-first 읽기 순서와 핵심 안전 규칙 중심으로 한국어화했다.
- `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`를 짧은 index 문서로 변경했다.
- Architecture를 API, database, pipeline, K3s runtime, domain/TLS 책임으로
  분리했다.
- Runbook을 routine check, backend deploy, CronJob, database/local check,
  troubleshooting 책임으로 분리했다.
- Backend agent workflow를 공통 workflow, Codex, Antigravity, verification,
  forbidden command 문서로 분리했다.
- WIP 1과 작업 단위 완료 조건, 새 문제 분류 기준을 정의했다.
- 작업 전 상태, 단위 완료, 전체 diff, end-to-end, 고위험 중단의 Gate 1~5를
  정의했다.
- Production-impacting command와 human-controlled verification 경계를
  문서화했다.
- `scripts/agent_next_step.sh`의 help와 8개 prompt 출력을 한국어화하고 신규
  `docs/agent/*` 구조에 맞췄다.
- Codex prompt에 checklist 완료 조건과 end-to-end 검증 원칙을 반영했다.
- Antigravity prompt가 task checklist, Approved Fixes, current diff,
  verification evidence를 함께 검토하도록 보완했다.
- 최초 review와 재검토 결과를 하나의 Antigravity review 파일에
  `Re-review N` 형식으로 누적하도록 정리했다.
- 최초 review는 `Problems Found`를 사용하는 하나의 출력 계약으로 통일했다.
- 최초 review 본문, 문제 원문, required fix checkbox, verdict를 수정하지 않고
  새 재검토 결과만 append하는 정책으로 보완했다.

## 구현 상세

### 문서 진입점

`AGENTS.md`는 모든 세부 내용을 다시 담지 않고 다음 읽기 순서를 안내한다.

```text
현재 task
→ backend workflow
→ Codex 또는 Antigravity 역할별 지침
→ 관련 architecture/runbook 세부 문서
→ verification gate와 forbidden command
```

`docs/ARCHITECTURE.md`는 45줄, `docs/RUNBOOK.md`는 54줄의 index로 정리했다.
세부 문서에서 index 또는 인접 문서로 돌아갈 수 있도록 상대 링크를 추가했다.

### Workflow artifact

문서별 source of truth를 다음처럼 분리했다.

- 요구사항: `docs/tasks/<safe-branch>.md`
- Review finding: `docs/reviews/`
- 사람이 승인한 fix: `docs/fixes/<safe-branch>-approved-fixes.md`
- 실제 command와 결과: `docs/verification/<safe-branch>.md`
- PR draft: `docs/pr/`
- Devlog: `docs/devlog/`

Review output만으로 코드를 수정하지 않고, Approved Fixes에 명시된 항목만
적용하도록 했다.

### Helper script

`scripts/agent_next_step.sh`는 기존 command를 유지한다.

```text
files
codex-implement
antigravity-review
antigravity-review-write
fixes-draft
codex-apply-fixes
pr-draft
devlog-draft
```

Script는 agent, test, GitHub 작업을 직접 실행하지 않는다. 현재 branch에서
artifact 경로와 사람이 복사해 사용할 prompt만 출력한다.

Approved Fixes를 적용하면서 다음을 추가했다.

- `docs/agent/*`를 현재 workflow 기준 문서로 사용
- Architecture와 Runbook은 index로 안내
- Task 관련 세부 문서만 선택적으로 읽기
- WIP 1과 checklist 완료 규칙
- 미수행·환경 제약 실패·운영 반영 후 확인 필요·사람 수행 필요 상태
- Approved Fixes와 verification evidence 대조
- 단일 review 파일의 최초 review와 `Re-review N` 누적 규칙

최초 review와 재검토의 schema는 명시적으로 분리했다.

```text
최초 review
→ Problems Found
→ Required Fixes Before PR
→ Verdict

Re-review N
→ Existing Problems Status
→ Approved Fixes Verification
→ Verification Evidence
→ New Problems Found
→ Required Fixes Before PR
→ Verdict
```

`antigravity-review`와 `antigravity-review-write`가 동일한 최초 review 구조를
출력하도록 맞췄다. `Existing Problems Status`와 `New Problems Found`는
`Re-review N` 내부에서만 사용한다.

재검토는 append-only 방식으로 정의했다.

- 최초 review의 `Problems Found` 원문을 수정하지 않는다.
- 최초 `Required Fixes Before PR` 원문과 checkbox를 수정하지 않는다.
- 최초 `Verdict`와 기존 `Re-review` 이력을 수정하지 않는다.
- 기존 문제는 번호 또는 명확한 제목으로 최초 항목과 연결한다.
- 해결 상태와 근거는 새 `Existing Problems Status`에 기록한다.
- 해결 근거는 Approved Fixes, current diff, verification evidence를 함께
  사용한다.
- 현재 시점의 새 문제와 PR blocker는 새 재검토 섹션에만 기록한다.

Script 재작성 직후 executable bit가 제거되어 직접 실행이
`permission denied`로 실패했다. 이를 범위 내 결함으로 분류하고
`chmod +x scripts/agent_next_step.sh`로 mode를 복원한 뒤 동일 검증을
재실행했다.

## 대안 검토

### 대안 1. 기존 Architecture와 Runbook을 그대로 번역·정리

파일 수는 늘지 않지만 agent가 매 task마다 긴 단일 문서를 읽는 문제가
유지된다. 현재 운영 기준과 작업별 세부 정보의 책임도 다시 혼재할 가능성이
높아 제외했다.

### 대안 2. 모든 주제를 더 작은 다수의 문서로 세분화

문서당 context는 줄지만 파일 탐색 비용과 중복 링크가 늘어난다. 독립적으로
참조할 책임이 분명한 architecture 6개, runbook 5개, agent workflow 5개
문서만 생성하는 수준으로 제한했다.

### 대안 3. 즉시 자동 agent harness와 검증 script 구현

Checklist 자동 판정, forbidden file 검사, Markdown link 검사, verification
정합성 검사를 바로 자동화할 수 있다. 그러나 artifact 구조와 완료 조건이
고정되지 않은 상태에서 자동화를 먼저 추가하면 잘못된 규칙을 코드로 고착할
위험이 있어 후속 작업으로 미뤘다.

### 대안 4. 재검토 전용 command와 review 파일 추가

`antigravity-rereview` command와 별도 rereview 파일을 만들 수 있었지만 review
이력이 분산된다. 기존 command와 단일 review 파일을 유지하고 파일 존재 여부에
따라 최초 review 또는 재검토를 수행하도록 선택했다.

### 대안 5. 기존 `docs/prompts/*` 즉시 삭제

과거 workflow와 script가 참조할 가능성이 있어 삭제하지 않았다. 신규
`docs/agent/*`를 현재 기준으로 사용하고 기존 prompt는 호환용 보조 문서로
유지했다.

### 대안 6. 최초 review checkbox를 해결 상태에 맞게 직접 수정

기존 required fix를 체크하면 현재 상태를 한눈에 볼 수 있지만, 최초 review가
당시 판단을 보존하는 감사 기록 역할을 하지 못한다. 최초 review는 immutable
history로 유지하고 해결 상태를 새 `Re-review N`에 기록하는 방식을 선택했다.

### 대안 7. Review schema 자동 검사 script 즉시 추가

별도 `scripts/check_review_contract.sh`를 추가할 수 있었지만 이번 task는
workflow 기준 문서와 helper prompt 정렬이 범위다. 기존 read-only `rg`와
prompt 출력 검증으로 계약을 확인하고 자동 검사는 후속 후보로 남겼다.

## 선택한 접근과 근거

선택한 접근은 `짧은 index + 단일 책임 세부 문서 + task 중심 읽기 순서`다.

이 구조를 선택한 이유는 다음과 같다.

- Agent가 현재 task에 필요한 context만 선택할 수 있다.
- 현재 운영 기준과 과거 task/review/verification 기록을 분리할 수 있다.
- Codex와 Antigravity의 역할과 입력 문서를 명시적으로 구분할 수 있다.
- WIP 1과 verification gate를 사람과 agent가 같은 문서에서 확인할 수 있다.
- 향후 자동화 script가 검사해야 할 artifact와 완료 조건을 먼저 고정할 수 있다.
- 기존 helper command와 prompt 호환성을 유지하면서 점진적으로 전환할 수 있다.
- 최초 review를 불변 기록으로 유지해 review 당시 판단과 이후 해결 상태를
  분리해서 추적할 수 있다.
- 최초 review와 재검토의 heading 계약을 분리해 agent별 출력 편차를 줄일 수
  있다.

## 트레이드오프

- 전체 Markdown 파일 수는 증가했다.
  - Index와 상호 링크를 제공하고 동일한 상세 절차를 여러 문서에 복사하지 않는
    방식으로 탐색 비용을 제한했다.
- `docs/agent/*`와 기존 `docs/prompts/*`가 당분간 공존한다.
  - 즉시 삭제에 따른 호환성 위험을 피하는 대신 일부 중복을 허용했다.
- Checklist와 verification 정합성은 아직 사람이 확인한다.
  - 자동 판정 오류를 피했지만 반복 검토 비용은 남아 있다.
- 단일 review 파일은 이력 추적에 유리하지만 시간이 지나면 파일이 길어질 수
  있다.
  - `Re-review N` 구조로 회차를 구분하고 별도 파일 난립을 피하는 쪽을
    선택했다.
- Append-only review는 과거 기록의 무결성을 높이지만 최신 해결 상태를
  확인하려면 파일의 마지막 재검토 섹션까지 읽어야 한다.
  - 최초 기록 수정 대신 이력 추적 가능성을 우선했다.
- Review schema 검증은 현재 shell output과 `rg`에 의존한다.
  - 별도 자동 검사 script를 추가하지 않아 scope는 작게 유지했지만 수동 검증
    비용은 남아 있다.
- 이번 작업은 application 기능을 개선하지 않는다.
  - 대신 이후 기능 task에서 context와 검증 누락을 줄이는 기반을 만든다.

## 테스트

실제 command와 결과의 source of truth는
`docs/verification/feature-backend-agent-workflow-docs.md`다.

- `git diff --check`: 통과
- Markdown 상대 링크 검사:
  - 19개 Markdown file 검사
  - broken link 0개
- 문서 구조와 운영 기준 검색:
  - WIP 1과 Gate 1~5 확인
  - 고위험 command 문맥 확인
  - CronJob schedule, API host, Kubernetes resource 명칭 충돌 없음
- 민감정보 pattern 검사:
  - 실제 credential 값 없음
  - 환경 변수명, Secret reference, test placeholder, 정책 문구만 확인
- `scripts/agent_next_step.sh`:
  - `bash -n` 통과
  - executable mode `100755` 유지
  - 기존 8개 command 정상 출력
  - 별도 rereview command 또는 artifact path 없음
  - 핵심 prompt 5개 출력 검증, 총 346줄, 모두 exit code 0
- Approved Fixes 적용 후 Antigravity 재검토:
  - 최초 review 원문 유지
  - 동일 review 파일에 `Re-review 1` 추가
  - 최종 verdict `APPROVED`
- Approved Fix 9·10:
  - `bash -n scripts/agent_next_step.sh` 통과
  - `antigravity-review`와 `antigravity-review-write` 출력에서
    `Problems Found`, `Required Fixes Before PR`, `Verdict` 확인
  - 최초 review 최상위 `Existing Problems Status`,
    `New Problems Found` 없음
  - Append-only 재검토 구조와 최초 review 원문·checkbox·verdict 수정 금지
    규칙 확인
  - Script와 `docs/agent/antigravity-review.md`의 출력 계약 일치
  - 기존 helper command 회귀 검증 통과
  - 실제 credential 값 없음

검증 과정에서 executable bit 문제로 직접 실행이 한 차례 실패했으며, mode 복원
후 동일 command를 재실행해 통과했다. 실패 이력과 수정 결과를 verification
문서에 모두 기록했다.

Fix 9·10 적용 후 실제 Antigravity `Re-review N` append는 실행하지 않았다.
Agent를 자동 실행하지 않는 경계를 유지했으며 사람이 수행할 pending
verification으로 남겼다.

## 운영 반영

운영 반영은 수행하지 않았다.

- Kubernetes manifest apply 미수행
- K3s rollout/restart 미수행
- Supabase SQL과 migration 미수행
- DB write script 미수행
- Production API curl verification 미수행
- Git push와 merge 미수행

이번 변경은 local documentation과 prompt helper 동작에 한정된다. Production
deployment와 production verification은 이 task의 범위 밖이다.

## README 업데이트 판단

README는 수정하지 않았다.

이번 작업은 사용자 기능, 설치 방법, 공개 API contract를 변경하지 않는다.
변경된 내용은 backend 내부 agent-assisted development workflow와 운영 문서
탐색 구조이므로 `AGENTS.md`, `docs/agent/`, architecture/runbook index가 더
적절한 source of truth라고 판단했다.

## 확인 결과

- Architecture와 Runbook이 짧은 index와 책임별 세부 문서로 분리됐다.
- Agent가 매번 1,000줄 이상의 단일 runbook 전체를 읽을 필요가 줄었다.
- Codex와 Antigravity의 필수 입력, 역할, 수정 권한이 구분됐다.
- WIP 1과 작업 단위 완료 조건이 문서와 helper prompt에 반영됐다.
- Task checklist와 Approved Fixes checklist가 실제 완료 상태에 맞게
  갱신됐다.
- Review finding, approved fix, verification 결과가 서로 다른 source of
  truth로 관리된다.
- 최초 review와 재검토의 출력 구조가 구분되고 helper script와 policy 문서가
  동일한 계약을 사용한다.
- 최초 review는 불변 기록으로 유지되고 해결 상태는 append된 재검토 섹션에서
  추적된다.
- Backend source, DB/migration, Kubernetes manifest, Dockerfile, GitHub
  Actions, frontend는 변경하지 않았다.

현재 working tree의 CodeRabbit review 변경은 Fix 9·10 승인 근거로 사람이
제공한 review artifact이며 이번 적용 과정에서는 수정하지 않았다.

PR 생성과 merge는 아직 완료되지 않았으며 사람이 수행해야 한다.

## 이번 단계의 의미

이 작업의 핵심은 문서 줄 수 자체가 아니라 agent가 무엇을 어떤 순서로 읽고,
언제 작업 단위를 완료로 판단하는지를 명시한 것이다.

현재 단계는 자동화된 agent harness가 아니다. 다만 task, approved fixes,
verification, review, PR, devlog의 책임을 분리하고 Gate 1~5를 정의함으로써
향후 자동 검사 도입 시 필요한 기준을 먼저 만들었다.

추가로 최초 review를 immutable history로 취급하고 이후 해결 상태를
append-only 재검토에 남기는 기준을 확정했다. 이는 단순 prompt 형식 통일을
넘어 review 판단의 시점별 근거를 보존하는 변경이다.

기능 개발 관점에서는 직접적인 API 변화가 없지만, 이후 embedding과 daily
pipeline 작업에서 context 낭비, scope creep, 검증 누락을 줄일 수 있는
engineering process 기반을 마련했다.

## 포트폴리오용 요약

장기간 운영되는 FastAPI/K3s backend 프로젝트에서 agent-assisted development
workflow를 재설계했다.

1,000줄 이상으로 비대해진 architecture/runbook을 index와 단일 책임 문서로
분리하고, task → 구현 → review → approved fixes → verification → PR/devlog로
이어지는 artifact 기반 workflow를 정의했다. 또한 WIP 1과 5단계 verification
gate를 도입해 코드 변경뿐 아니라 문서화, 검증, checklist 갱신까지 완료해야
다음 작업으로 이동하도록 했다.

Prompt helper는 기존 command 호환성을 유지하면서 한국어화했고, Codex와
Antigravity가 task, diff, approved fixes, verification evidence를 기준으로
작업하도록 보완했다. 이 과정에서 실행 권한 회귀를 실제 검증으로 발견하고
복구 후 재검증했으며, 실패 이력도 verification 문서에 남겼다.

이후 review schema 불일치를 수정해 최초 review는 `Problems Found`, 재검토는
`Existing Problems Status`와 `New Problems Found`를 사용하도록 계약을
분리했다. 최초 review의 문제·checkbox·verdict는 수정하지 않고 이후 해결
상태만 append하도록 해 review history의 감사 가능성을 높였다.

결과적으로 기능 자동화보다 먼저 운영 안전성, 검증 무결성, review 이력 보존을
강화한 engineering decision documentation을 구축했다.

## 다음 단계 후보

기능 개발:

- 55차: embedding 저장 구조 검토 및 재사용 설계
- 56차: article embedding 저장/재사용 MVP 구현
- 57차: daily pipeline 분리 설계
- 58차: daily pipeline 분리 구현

Workflow 자동화 후보:

- `scripts/check_agent_task.sh`
- `scripts/check_docs_links.sh`
- `scripts/check_forbidden_changes.sh`
- `scripts/check_task_checklist.sh`
- `scripts/check_verification_commands.sh`
- `scripts/check_review_contract.sh`

문서 정리 후보:

- 신규 `docs/agent/*` 적용이 안정화된 뒤 기존 `docs/prompts/*` 중복 제거 검토
- 단일 Antigravity review 파일이 장기적으로 비대해질 경우 archive 기준 검토

Pending:

- 사람이 PR 생성 및 merge
- Fix 9·10 적용 후 실제 Antigravity `Re-review N` append와 최종 판단
- 다음 실제 backend task에서 새 읽기 순서와 WIP 1 gate 운영성 확인
