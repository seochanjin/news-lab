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

Antigravity review는 실행 파일 존재와 자동 실행 지원을 분리한다. 검증된
비대화형 adapter가 없으면 직접 실행을 차단하고 prompt-only 수동 review를
안내한다. Gemini CLI의 `UNSUPPORTED_CLIENT`, 인증 실패, 비대화형 실행 미지원,
timeout과 일반 non-zero exit는 성공으로 처리하지 않는다.

자동 review 완료에는 process 성공뿐 아니라 review 파일 생성 또는 변경과 구조
검증 통과가 필요하다. 수동 review는 실행 기록 없이도 파일 검증을 통과하면
완료될 수 있다. 파일 없음, 빈 파일, 초기 템플릿, 필수 section·본문·Verdict
누락과 허용되지 않은 Verdict는 미완성으로 유지하며 fix 또는 PR gate를 열지
않는다.
