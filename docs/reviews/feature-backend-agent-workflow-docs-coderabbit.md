# CodeRabbit Review: backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## Review Summary

CodeRabbit review에서 `scripts/agent_next_step.sh`의 Antigravity review 출력 계약과 재검토 보존 규칙에 관한 두 가지 문제를 확인했다.

첫 번째 문제는 최초 Antigravity chat review가 `Existing Problems Status`와 `New Problems Found`를 출력하도록 변경되었지만, agent policy에서는 최초 review에 `Problems Found`를 사용하도록 정의하고 있다는 점이다.

이 불일치로 인해 Antigravity chat 출력, review file 작성 prompt와 policy 문서 사이에 서로 다른 review 형식이 사용될 수 있다.

두 번째 문제는 재검토 과정에서 기존 review 내용을 보존하라고 규정하면서도 기존 `Required Fixes Before PR` checkbox를 해결 시 체크하도록 지시한다는 점이다.

기존 checkbox를 수정하면 최초 review가 불변 이력으로 유지되지 않으므로, 해결 상태는 기존 review를 수정하지 않고 `Re-review N` 섹션에 별도로 기록해야 한다.

두 문제 모두 workflow 기능 전체를 변경하지 않고 출력 계약과 기록 보존 규칙을 정렬하는 방식으로 수정할 수 있다.

## Problems Found

### CR-1. Antigravity chat review 출력 제목과 policy contract 불일치

- 심각도: Major
- 유형: Review output contract drift
- 대상:
  - `scripts/agent_next_step.sh`
  - `docs/agent/antigravity-review.md`

현재 `print_antigravity_review`가 다음 제목을 출력하도록 구성되어 있다.

```md
## Existing Problems Status

## New Problems Found
```

그러나 policy contract는 최초 review 형식에 다음 제목을 요구한다.

```md
## Problems Found
```

`Existing Problems Status`와 `New Problems Found`는 기존 review를 토대로 수행하는 재검토에 적합한 제목이며 최초 review의 출력 구조로 사용하면 안 된다.

이 상태에서는 도구별 또는 검토 회차별 review format이 달라질 수 있고, review 파일 갱신 로직이 최초 review인지 재검토인지 안정적으로 판단하기 어려워진다.

#### 승인 수정 방향

- 최초 review에는 `Problems Found`를 사용한다.
- `Existing Problems Status`와 `New Problems Found`는 `Re-review N` 내부에서만 사용한다.
- chat review와 write review가 같은 최초 review 계약을 사용하도록 한다.
- policy 문서와 helper script의 출력 구조를 일치시킨다.

### CR-2. 재검토 기록 보존 규칙의 내부 모순

- 심각도: Minor
- 유형: Review history integrity
- 대상:
  - `scripts/agent_next_step.sh`
  - `docs/agent/antigravity-review.md`
  - approved fixes의 재검토 규칙

현재 재검토 규칙에는 다음 두 요구가 함께 존재한다.

```text
기존 review 원문과 기존 Re-review 이력을 보존한다.
기존 Required Fixes Before PR은 실제 해결된 경우 체크한다.
```

기존 `Required Fixes Before PR` checkbox를 체크하면 최초 review를 수정하게 되므로 두 요구를 동시에 만족할 수 없다.

#### 승인 수정 방향

- 최초 review 전체를 불변 기록으로 유지한다.
- 최초 `Problems Found`, `Required Fixes Before PR` checkbox와 `Verdict`를 수정하지 않는다.
- 기존 문제의 해결 여부는 `Re-review N`의 `Existing Problems Status`에서 새 checklist로 기록한다.
- 새 문제와 현재 PR blocker도 해당 재검토 섹션에 기록한다.

## Required Fixes Before PR

- [ ] CR-1: 최초 Antigravity review의 출력 구조를 policy contract와 일치시킨다.
  - 최초 review에 `Problems Found`를 사용한다.
  - `Existing Problems Status`와 `New Problems Found`는 재검토에서만 사용한다.
  - chat review와 write review의 출력 계약을 통일한다.

- [ ] CR-2: 재검토 기록을 append-only 방식으로 변경한다.
  - 최초 review의 원문, checkbox와 verdict를 수정하지 않는다.
  - 해결 상태를 `Re-review N`의 별도 checklist로 기록한다.
  - 기존 문제, 신규 문제와 현재 blocker를 재검토 섹션에서 구분한다.

완료 여부는 Codex가 fixes checklist를 체크한 것만으로 판정하지 않는다.

다음 근거를 함께 확인해야 한다.

```text
Approved Fixes checklist
실제 script 및 policy diff
verification command 결과
Antigravity 재검토 결과
```

## Optional Improvements

### Review schema 자동 검사

Review prompt의 heading contract를 shell 또는 Python script로 검사할 수 있다.

예:

```text
scripts/check_review_contract.sh
```

검사 후보:

- 최초 review 필수 heading 존재
- 최초 review에 재검토 전용 heading이 없는지 확인
- `Re-review N` 필수 heading 확인
- 최초 review 수정 금지 규칙 존재 여부 확인

이번 작업에서는 자동 검사 script를 추가하지 않고 기존 read-only 검증 command로 확인한다.

### 구조화된 review 문제 ID

향후 review 문제에 다음 형식의 ID를 부여하면 최초 review와 재검토를 연결하기 쉬워진다.

```text
AG-1
AG-2
CR-1
CR-2
```

현재 작업에서는 CodeRabbit 지적에 `CR-1`, `CR-2`를 사용해 문서상 연결한다.

## Suggested Test Commands

### Shell 문법

```bash
bash -n scripts/agent_next_step.sh
```

### 최초 review prompt 확인

```bash
scripts/agent_next_step.sh antigravity-review \
  > /tmp/agent-next-antigravity-review.txt

scripts/agent_next_step.sh antigravity-review-write \
  > /tmp/agent-next-antigravity-review-write.txt
```

```bash
rg -n \
  '^## Problems Found$|^## Existing Problems Status$|^## New Problems Found$|^## Required Fixes Before PR$|^## Verdict$' \
  /tmp/agent-next-antigravity-review.txt \
  /tmp/agent-next-antigravity-review-write.txt
```

기대 결과:

```text
Problems Found 존재
Required Fixes Before PR 존재
Verdict 존재
최초 출력에 Existing Problems Status 없음
최초 출력에 New Problems Found 없음
```

### 재검토 규칙 확인

```bash
rg -n \
  'Re-review N|Existing Problems Status|Approved Fixes Verification|Verification Evidence|New Problems Found|checkbox.*수정하지|Verdict.*수정하지|원문.*보존' \
  scripts/agent_next_step.sh \
  docs/agent/antigravity-review.md
```

### Diff 형식 및 범위

```bash
git diff --check
git diff --name-only
git diff --stat
```

### 최종 Antigravity 재검토

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

확인 항목:

- 기존 review 원문이 유지된다.
- 다음 `Re-review N` 섹션만 추가된다.
- CR-1과 CR-2 해결 상태가 별도 checklist로 기록된다.
- Approved Fixes와 verification evidence가 대조된다.
- 새 문제와 scope creep 여부가 확인된다.

## Risk Notes

이번 문제는 backend application, DB 또는 production infrastructure에 영향을 주는 실행 결함은 아니다.

주요 위험은 workflow 기록의 신뢰성과 review 도구 간 형식 불일치다.

CR-1을 수정하지 않으면 다음 문제가 발생할 수 있다.

```text
Antigravity chat과 review file의 heading 불일치
최초 review와 재검토 구조 구분 실패
후속 parser 또는 자동 검사 도입 시 계약 충돌
검토자마다 다른 review format 생성
```

CR-2를 수정하지 않으면 다음 문제가 발생할 수 있다.

```text
최초 review의 당시 상태가 사라짐
checkbox 변경으로 review 이력 해석이 어려워짐
어떤 재검토에서 문제가 해결됐는지 추적하기 어려움
최초 verdict와 수정 후 verdict가 혼재
```

두 수정은 기존 review workflow를 제거하지 않고, 최초 review를 immutable record로 유지하면서 재검토만 append하는 방식으로 해결한다.

수정 범위는 helper script와 관련 workflow 문서에 한정해야 하며 backend application, DB, Kubernetes, Docker와 frontend 변경은 포함하지 않는다.
