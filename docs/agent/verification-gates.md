# Backend Verification Gate

[Backend agent workflow로 돌아가기](backend-workflow.md)

## Gate 1. 작업 전 상태

- 현재 branch 확인
- Working tree 확인
- 관련 file 위치 검색
- Task scope와 acceptance criteria 확인
- 변경 금지 영역과 고위험 command 확인

예:

```bash
git status --short --branch
rg --files <관련 경로>
```

## Gate 2. 작업 단위 완료

- 현재 작업 단위 변경 완료
- 필요한 문서 갱신
- 정적 검증 또는 test 실행
- 결과와 미수행 항목을 verification에 기록
- Task checklist 갱신
- 다음 단위로 이동 가능한지 확인

실패한 검증을 숨기지 않고 원인과 영향을 기록한다.

## Gate 3. 전체 변경 범위

```bash
git diff --stat
git diff --check
git diff --name-only
```

- Scope 밖 변경이 없는지 확인한다.
- Application, DB, manifest, dependency 등 task가 금지한 영역을 확인한다.
- 현재 운영 기준 문서끼리 값이 충돌하지 않는지 확인한다.

## Gate 4. End-to-end

코드 또는 pipeline 변경은 가능한 범위에서 다음 흐름을 검증한다.

```text
입력 데이터
→ application 또는 script 처리
→ DB 저장
→ API 또는 read command 확인
```

각 단계는 다음 상태 중 하나로 기록한다.

- 로컬 검증 완료
- dry-run 완료
- 운영 검증 대기
- 사람이 수행 필요

운영 apply나 production data write가 필요한 단계는 agent가 자동 실행하지 않는다.
문서 구조 task는 index → 상대 링크 → 세부 절차 → workflow/gate 참조 흐름을
end-to-end 대상으로 삼을 수 있다.

## Gate 5. 고위험 작업 중단

고위험 command가 필요하면 자동 실행하지 않고 다음을 기록한다.

- 현재까지 완료한 작업
- 필요한 고위험 작업
- 사람이 실행할 command
- 실행 후 확인할 결과
- 실패 시 rollback 또는 troubleshooting 문서

## Verification 기록 형식

Verification 문서 상단에는 현재 전체 상태를 명시한다.

```markdown
## Verification Status

pending
```

지원 상태는 `pending`, `passed`, `failed`다. 실제 허용 검증이 모두 통과한
뒤에만 `passed`로 변경한다. 과거 실패 이력과 개별 command의 `Status:`는
보존하되 현재 전체 상태를 대신하지 않는다. 상태 section이 없는 기존 문서는
`present`, 문서가 없으면 `missing`으로 호환 처리한다.

각 command에 실제 실행 여부와 결과를 남긴다.

```text
Command:
Result:
Status: passed | failed | skipped | human-required
Notes:
```

PR과 devlog는 이 기록을 근거로 작성한다.

## 실행 하네스 gate

직접 Agent 실행 전에는 repository, branch, 현재 Task, `docs/tasks/main.md`,
필수 workflow 문서와 대상 CLI를 확인한다. 구현과 Fix는 `main` 및 `master`에서
차단한다. Codex Fix는 Approved Fixes의 실제 승인 항목을 요구하고, Review는
변경사항과 Verification 문서 및 명시적 실패 여부를 확인한다.

이 gate는 production 명령을 허용하지 않으며 Agent의 구현 품질이나 Task 완료를
자동 판정하지 않는다.

## Antigravity review gate

Antigravity UNIT Review는 Task 구현 상태와 `Unit Review Status`를 대조해
구현 완료·Review 미통과인 가장 앞선 UNIT만 선택한다. 마지막 UNIT도
`antigravity-review-unit`에서는 UNIT Review로만 처리하며, 모든 UNIT Review가
끝난 뒤 별도의 `antigravity-review` 실행에서 Integration Review를 선택한다.
Integration Review와 승인 Fix 적용이 끝난 뒤에만 Re-review를 선택한다. UNIT
Task는 전체 Verification이 `pending`이어도 완료 UNIT의 Review를 허용하지만,
명시적 `failed`와 일반 Task의 `pending`은 차단한다.

`--dry-run`은 mode, UNIT, FIX, 최신 전체 테스트 snapshot과 prompt를 파일 쓰기
없이 확인하는 gate다. 예상 heading, prompt line·byte 수와 제한 diff 파일 수도
확인하며 prompt 상한 초과는 외부 실행 전에 차단한다. 실제 실행은
`agy --print --sandbox` adapter만 사용하고 Gemini CLI를 fallback으로 사용하지
않는다. 실행 파일 없음, 인증 실패, 비대화형 실행 미지원, timeout과 non-zero
exit를 성공으로 처리하지 않는다.

자동 Review 완료에는 process 성공, 단일 stdout section의 heading·필수
section·본문·Verdict·finding ID 검증, 현재 FIX·Verification·Re-review 번호와의
모순 검사 및 append-only writer 성공이 모두 필요하다. `PASS`만 선택 UNIT의
Review Status를 완료한다. Agent 직접 파일 변경, 중복 응답 또는 validation
실패에서는 실행 전 Review 파일을 보존하고 fix 또는 PR gate를 열지 않는다.
Review subprocess의 재귀 호출과 실행·대기 의도를 나타내는 응답도 전용 gate에서
차단한다.
