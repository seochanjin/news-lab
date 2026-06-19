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

각 command에 실제 실행 여부와 결과를 남긴다.

```text
Command:
Result:
Status: passed | failed | skipped | human-required
Notes:
```

PR과 devlog는 이 기록을 근거로 작성한다.
