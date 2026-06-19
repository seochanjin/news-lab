# Backend Agent Workflow

[AGENTS.md로 돌아가기](../../AGENTS.md)

이 문서는 NewsLab backend의 문서 기반 agent-assisted development workflow를
정의한다. 자동 task runner나 hook 기반 harness가 아니다.

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
