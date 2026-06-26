# Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## 작업 내용

현재 branch의 Task, Review, Approved Fixes, Verification과 Git diff를
하네스가 구조적으로 읽어 Antigravity Review 대상을 자동 결정하도록
개선했다. 사용자는 긴 Review prompt를 직접 작성하지 않고 다음 명령으로
UNIT Review, Integration Review, Re-review 흐름을 실행할 수 있다.

```bash
scripts/agent_run.sh antigravity-review-unit
scripts/agent_run.sh antigravity-review
```

## 주요 변경 사항

- Task의 `Implementation Units`를 파싱하고, branch별 Antigravity Review 파일에
  `Unit Review Status`를 자동 생성·검증한다.
- `antigravity-review-unit` action을 추가해 구현 완료됐지만 Review 미통과인
  다음 UNIT 하나만 선택한다.
- `antigravity-review` action은 UNIT Review로 전환하지 않고 Integration Review,
  Summary recovery, Re-review 또는 일반 Review만 선택하도록 분리했다.
- Review Context와 Prompt를 자동 생성하고, `agy --print <prompt> --sandbox`
  기반 비대화형 실행 경로를 추가했다.
- Antigravity 응답의 heading, 필수 section, Verdict, finding ID, 대상 UNIT,
  Re-review 번호, Approved Fixes와 최신 Verification 수치 모순을 검증한다.
- 검증된 Review section만 append하고, `PASS`일 때만 Review Status를 완료한다.
  실패, 응답 잘림, 중복, Agent의 Review 파일 직접 변경 시 기존 bytes를 보존한다.
- Approved Fixes의 FIX ID, 제목, 체크 상태와 `human-verification` 분류를
  파싱하고, Re-review Prompt에서 모든 FIX ID를 개별 검증하도록 강화했다.
- 재귀 실행 guard와 명령 실행 시도 응답 차단을 추가했다.
- Agent workflow 문서, Antigravity review 지침, 사용 가이드와 verification gate를
  새 action 및 상태 전이 계약에 맞게 갱신했다.
- 관련 테스트를 추가·확장했다.

적용된 approved fixes는
`docs/fixes/fix-antigravity-review-automation-approved-fixes.md` 기준
FIX-01부터 FIX-17까지다.

현재 working tree의 `git diff`는 비어 있으며, PR 범위는 `main...HEAD` 기준
Agent workflow 코드, 테스트, workflow 문서와 task/review/verification 산출물이다.

## 추가/변경된 API

- FastAPI route, request/response schema, public backend API 변경 없음.
- 내부 Agent CLI 변경:
  - 추가: `scripts/agent_run.sh antigravity-review-unit`
  - 유지·의미 변경: `scripts/agent_run.sh antigravity-review`
  - 두 action 모두 `--dry-run`으로 mode, target, expected heading, prompt 크기,
    diff 파일 수, FIX와 최신 테스트 snapshot을 확인할 수 있다.

## DB 변경 사항

없음. DB migration, schema, table, constraint, index와 운영 데이터 변경은 없다.
`git diff -- app db k8s requirements.txt` 결과도 출력 없음으로 기록됐다.

## README 영향

README 변경은 없다. 이번 변경은 backend application 사용법이 아니라 내부
Agent workflow 계약과 실행 방식 변경이므로 `docs/agent/antigravity-review.md`,
`docs/agent/backend-workflow.md`, `docs/agent/usage-guide.md`,
`docs/agent/verification-gates.md`를 갱신하는 것으로 충분하다고 판단했다.

## 테스트

Source of truth:
`docs/verification/fix-antigravity-review-automation.md`

- `python -m pytest tests/test_agent_*.py -v`
  - 최종 결과: 130개 Agent workflow 테스트와 41개 subtest 통과
- `python -m pytest`
  - 최종 결과: 전체 Repository pytest 339 passed
- `python -m unittest discover -s tests`
  - 최종 결과: 전체 unittest 339 passed
  - argparse 오류 메시지와 provider 실패 log는 테스트가 의도적으로 검증하는
    출력이며 최종 결과는 `OK`
- `python -m compileall scripts tests`
  - 결과: 통과
- `bash -n scripts/agent_run.sh scripts/agent_next_step.sh`
  - 결과: 통과
- `git diff --check`
  - 결과: 출력 없음
- `git diff -- app db k8s requirements.txt`
  - 결과: 출력 없음
- `scripts/agent_run.sh antigravity-review --dry-run`
  - 결과: `re-review` mode와 `## Re-review 1` heading 선택
  - FIX-01부터 FIX-17까지 Prompt에 개별 출력 골격으로 포함
  - FIX-09는 `approved, human-verification` 및 pending 완료 조건 골격으로 표시
  - dry-run이므로 외부 Agent와 Writer는 실행하지 않음

## 확인 결과

- UNIT-01부터 UNIT-08까지 실제 외부 Antigravity Review가 모두 `PASS`로
  검증됐고 Review History append 및 Review Status 갱신이 완료됐다.
- Integration Review가 `PASS`한 뒤 상단 Review Summary placeholder가
  Integration Review 근거로 갱신됐다.
- 최종 Re-review에서 `antigravity-review`가 `re-review` mode와
  `## Re-review 1`을 선택했다.
- Re-review에서 Approved Fixes FIX-01부터 FIX-17까지 개별 검증됐다.
- FIX-09는 `human-verification pending` 상태로 정확히 검토됐다.
- 최신 pytest와 unittest는 각각 339개 통과로 반영됐다.
- Re-review Verdict는 `PASS`였고, Review 응답 검증과 Review History append가
  완료됐다.
- Application, DB, K3s manifest, dependency 영역 변경은 없다.

## 비고

- PR merge 완료를 주장하지 않는다.
- Production deployment, K3s rollout, production verification은 수행하지 않았고
  완료로 주장하지 않는다.
- GitHub MCP, git push, git merge, kubectl apply/rollout, Supabase SQL은
  실행하지 않았다.
- Review 파일은 검증 근거가 아니라 Review 이력으로만 사용했다. 테스트와
  검증 결과는 verification 문서를 기준으로 작성했다.
