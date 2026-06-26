# Backend Agent Workflow

[AGENTS.md로 돌아가기](../../AGENTS.md)

이 문서는 NewsLab backend의 문서 기반 agent-assisted development workflow를
정의한다. Prompt-only 흐름과 선택적인 로컬 Agent 실행 하네스를 함께 지원하며,
hook이나 production automation은 포함하지 않는다.

## Source of truth

1. 요구사항: `docs/tasks/<safe-branch>.md`
2. 승인된 review fix: `docs/fixes/<safe-branch>-approved-fixes.md`
3. 실제 검증 결과: `docs/verification/<safe-branch>.md`
4. PR draft: `docs/pr/<safe-branch>.md`
5. Devlog: `docs/devlog/<safe-branch>.md`

Chat prompt나 review output은 task 또는 approved fixes를 대체하지 않는다.

## 읽기 순서

1. `AGENTS.md`
2. 현재 task file
3. 이 문서
4. 역할별 문서
5. Task에 직접 필요한 architecture/runbook 세부 문서
6. Verification gate와 forbidden command

매 작업마다 전체 architecture와 전체 runbook을 읽는 대신 index에서 필요한
문서만 선택한다.

## WIP 1

한 번에 하나의 작업 단위만 진행한다.

```text
1. 관련 문서와 코드 위치 조사
2. 현재 작업 단위 변경
3. 필요한 문서 작성 또는 갱신
4. 정적 검증 및 test 실행
5. verification에 command와 결과 기록
6. task checklist 갱신
7. 완료 조건 확인
8. 다음 작업 단위로 이동
```

조사, 변경, 문서화, 검증, checklist 갱신 중 하나라도 남아 있으면 현재 작업
단위는 완료가 아니다.

## 새 문제 분류

- `blocker`: 현재 완료를 막아 우선 해결 또는 사람 판단이 필요하다.
- `현재 범위의 결함`: task acceptance criteria를 충족하려면 수정해야 한다.
- `후속 작업 후보`: 현재 목표 없이도 별도 task로 처리할 수 있다.
- `과거 기록`: 현재 운영 기준을 바꾸지 않는 historical evidence다.

후속 작업 후보 때문에 현재 scope를 자동 확장하지 않는다.

## Checklist

모든 backend task는 checklist를 포함한다. Agent는 실제 완료한 항목만 체크한다.
완료하지 않은 항목은 다음 상태를 명시한다.

- 미수행
- 환경 제약으로 실패
- 운영 반영 후 확인 필요
- 사람이 수행 필요

## 역할

- Codex는 task 범위의 구현과 허용된 검증을 수행한다.
- Antigravity는 변경을 수정하지 않고 requirement, code, security, operation,
  scope, verification, documentation 관점에서 review한다.
- Human operator는 review fix 승인, merge, production-impacting command와
  production verification을 담당한다.

세부 역할은 [Codex 지침](codex-instructions.md)과
[Antigravity review](antigravity-review.md)를 따른다.

## 실행 진입점

- Prompt-only: `scripts/agent_next_step.sh <action>`
- 직접 실행: `scripts/agent_run.sh <action>`
- 상태 확인: `scripts/agent_next_step.sh status`

직접 실행 하네스는 실행 전 gate, subprocess timeout, 로컬 로그 저장까지만
담당한다. Agent 종료 코드 0은 Task 완료나 verification 통과를 의미하지 않는다.
상세 사용법은 [Agent workflow 사용 가이드](usage-guide.md), Task 형식은
[Task 작성 가이드](task-authoring-guide.md)를 따른다.

## Antigravity review 실행 원칙

UNIT Task의 Antigravity review는 Task의 구현 완료 checklist와 Review 파일의
`Unit Review Status`를 분리해 관리한다. UNIT Review와 최종 Review는 action을
분리한다.

- `antigravity-review-unit`: 구현 완료됐지만 Review 미통과인 가장 앞선 UNIT 하나
- `antigravity-review`: 모든 UNIT Review 완료 후 Integration Review, Re-review 또는 일반 Review

`scripts/agent_run.sh antigravity-review-unit --dry-run`과
`scripts/agent_run.sh antigravity-review --dry-run`은 선택 mode, 대상 UNIT,
예상 heading, prompt 크기, 제한 diff 파일 수, FIX와 최신 전체 테스트 snapshot
및 생성 prompt를 파일 쓰기 없이 출력한다. 최종 action은 UNIT Review 대상으로
자동 전환하지 않고 `antigravity-review-unit` 사용을 요구한다.
기본 실행은 검증된 `agy --print --sandbox` adapter를 사용하며 Agent에는 파일
수정이 아니라 새 Review section 하나만 stdout으로 반환하게 한다.

하네스는 응답의 heading, 필수 section, Verdict, finding ID, 선택 UNIT과
Re-review 번호 및 current-state evidence를 검증한다. 검증된 section만 branch별
Review 파일에 append하고 UNIT/Integration Review의 `PASS`일 때만 해당 UNIT의
Review Status를 완료한다.
`CHANGES REQUIRED`와 `BLOCKED`는 미완료 상태를 유지한다. Agent가 Review 파일을
직접 수정하거나 응답 검증에 실패하면 실행 전 파일을 보존하고 실패한다.
하위 process에는 재귀 실행 차단 환경을 전달하며 명령 실행 또는 대기 의도가
포함된 응답은 `review_agent_attempted_execution`으로 별도 실패 처리한다.

`agy` 실행 파일이 없거나 자동 실행이 실패한 경우 다음 prompt-only 흐름을
fallback으로 사용할 수 있다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

첫 명령은 review 요청 prompt를, 둘째 명령은 결과를 branch별 review 파일에
작성하는 prompt를 출력한다. 수동 review도 [Antigravity review 지침의 구조와
Verdict](antigravity-review.md)를 충족해야 완료로 판정한다.
