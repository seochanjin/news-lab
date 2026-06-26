# Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## 작업 목적

Antigravity Review를 수동 prompt 작성 중심에서 branch workflow artifact 기반
자동 실행 흐름으로 전환한다.

목표는 `scripts/agent_run.sh antigravity-review-unit`과
`scripts/agent_run.sh antigravity-review`가 현재 branch의 Task, Review,
Approved Fixes, Verification과 Git diff를 읽고 다음 Review 대상을 결정하도록
만드는 것이다. Re-review에서는 과거 Review 문구가 최신 상태를 덮어쓰지 못하게
Approved Fixes와 최신 Verification evidence를 하네스가 직접 검증한다.

## 기존 문제

- 사용자가 Antigravity Review용 긴 prompt를 직접 만들고 복사해야 했다.
- 기존 Review History의 과거 결론, FIX 상태, 테스트 수가 Re-review에서 현재
  상태처럼 해석될 위험이 있었다.
- Task의 구현 완료 체크박스와 Review 통과 상태가 분리되어 있지 않았다.
- Review Agent가 Review 파일 전체를 직접 수정하는 흐름은 append-only 보존과
  중복 방지에 약했다.
- Agent가 명령 실행 또는 background 대기 응답을 반환했을 때 이를 Review
  실패로 분류하는 guard가 부족했다.
- `antigravity-review` 하나가 UNIT Review, Integration Review, Re-review를 모두
  자동 선택해 사용자 관점의 명령 의미가 불명확했다.

## 변경 내용

- Task의 `Implementation Units` 파서와 Review 파일의 `Unit Review Status`
  자동 생성 및 검증을 추가했다.
- `antigravity-review-unit` action을 추가해 구현 완료됐지만 Review 미통과인
  UNIT 하나만 검토하도록 했다.
- `antigravity-review` action은 UNIT Review를 실행하지 않고 Integration Review,
  Summary recovery, Re-review 또는 일반 Review만 선택하도록 분리했다.
- Review Context, Prompt, Evidence, Response Validator, Append-only Writer를
  추가했다.
- `agy --print <prompt> --sandbox --print-timeout <초>s` 기반 비대화형
  Antigravity adapter를 검증된 실행 경로로 사용했다.
- Approved Fixes의 FIX ID, 제목, 체크 상태와 `human-verification` 분류를
  파싱하고, Re-review Prompt와 Validator가 모든 현재 FIX ID를 개별 검증하게
  했다.
- Agent의 재귀 실행과 명령 실행 시도 응답을 차단했다.
- Agent workflow 문서, Antigravity review 지침, 사용 가이드, verification gate를
  새 action과 상태 전이 계약에 맞게 갱신했다.
- 관련 테스트를 추가하고 기존 Agent workflow 테스트를 확장했다.

적용된 approved fixes는
`docs/fixes/fix-antigravity-review-automation-approved-fixes.md` 기준
FIX-01부터 FIX-17까지다.

## 구현 상세

- `scripts/agent_workflow/review_unit_status.py`
  - Task UNIT 목록을 기준으로 Review Status section을 생성한다.
  - 기존 Review Status가 Task의 UNIT ID, 제목, 순서와 다르면 파일을 변경하지
    않고 실패한다.
  - `PASS`인 경우에만 선택 UNIT을 `[x]`로 갱신한다.
- `scripts/agent_workflow/review_context.py`
  - action별 Review mode와 target UNIT을 선택한다.
  - 민감 경로, binary, 대용량 파일을 제외하고 제한된 Git diff를 Context에
    포함한다.
- `scripts/agent_workflow/review_evidence.py`
  - Approved Fixes, Verification, Review History에서 Re-review current-state
    evidence를 구조화한다.
  - 다음 Re-review 번호와 최신 pytest/unittest 통과 수를 계산한다.
- `scripts/agent_workflow/review_prompt.py`
  - 예상 heading을 prompt 상단과 하단에 반복하고, Shell, Agent, 테스트, Script
    실행 금지 계약을 명시한다.
  - Re-review에서는 모든 FIX ID별 출력 골격을 포함한다.
- `scripts/agent_workflow/review_response.py`
  - UNIT, Integration, Re-review, General Review 응답의 heading, section,
    Verdict, finding ID와 current-state 모순을 검증한다.
  - 검증된 section만 Review History에 append하고, Integration Review `PASS` 후
    상단 Summary placeholder를 갱신한다.
- `scripts/agent_workflow/runner.py`, `cli.py`, `gates.py`
  - action 분리, dry-run, prompt 크기 요약, 재귀 guard, failure category,
    review 파일 직접 변경 복구를 연결했다.
- 테스트
  - parser, context, evidence, prompt, validator, writer, runner, CLI, gate
    단위 회귀를 추가했다.

## 대안 검토

- 기존 prompt-only 흐름 유지
  - 장점: 구현량이 적고 기존 수동 절차를 그대로 유지할 수 있다.
  - 단점: 긴 prompt 작성 부담과 과거 Review 상태 오해 문제를 해결하지 못한다.
- Antigravity가 Review 파일 전체를 직접 수정하게 하기
  - 장점: writer 구현이 단순하다.
  - 단점: 기존 History 보존, 중복 방지, 실패 시 bytes 보존을 신뢰하기 어렵다.
- `antigravity-review` 단일 action 유지
  - 장점: 사용자 command 수가 적다.
  - 단점: UNIT Review와 최종 Review의 gate가 섞이고 Re-review 진입 조건이
    불명확하다.
- Gemini CLI fallback 사용
  - 장점: 실행 가능한 client 후보가 늘어난다.
  - 단점: Antigravity adapter 계약과 다르고 `UNSUPPORTED_CLIENT` 실패를 성공처럼
    오인할 위험이 있다.

## 선택한 접근과 근거

- UNIT Review와 최종 Review action을 분리했다.
  - 구현 직후 국소 Review는 `antigravity-review-unit`, 전체 통합과 Re-review는
    `antigravity-review`로 의미를 고정했다.
- 모델이 아니라 하네스가 current-state를 계산하게 했다.
  - 다음 UNIT, 다음 Re-review 번호, FIX 상태, 최신 테스트 수는 구조화 parser로
    결정하고 모델 출력은 그 값과 대조한다.
- Agent에는 새 Review section 하나만 stdout으로 반환하게 했다.
  - Review 파일 반영은 검증된 writer가 맡아 append-only와 bytes 보존 계약을
    지킨다.
- 자동 실행 실패 시 기존 prompt-only fallback을 유지했다.
  - `agy` 미설치, 인증 실패, timeout, 응답 검증 실패에서도 사람이 기존 방식으로
    이어갈 수 있다.

## 트레이드오프

- 구조화 parser와 validator가 늘어나 workflow 코드가 복잡해졌다.
  - 대신 Review 결과가 최신 Task, Approved Fixes, Verification과 모순되는 경우
    파일을 변경하지 않고 실패할 수 있게 됐다.
- Prompt가 더 엄격해졌다.
  - 일부 자연스러운 Review 응답은 실패할 수 있지만, PR gate 전에 상태 왜곡을
    막는 쪽을 선택했다.
- `antigravity-review-unit`과 `antigravity-review`로 command가 두 개가 됐다.
  - 사용자에게는 action 선택이 하나 늘지만, 각 command의 의미와 gate가 명확해졌다.
- 실제 `agy`에는 Shell, Tool 완전 비활성화 option이 없어 prompt 제한, sandbox,
  재귀 guard, 실행 시도 validator, 파일 복구를 조합했다.

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
  - FIX-01부터 FIX-17까지 Prompt에 개별 출력 골격 포함
  - FIX-09는 `approved, human-verification` 및 pending 완료 조건 골격으로 표시
  - dry-run이므로 외부 Agent와 Writer는 실행하지 않음

## 운영 반영

- 이번 변경은 내부 Agent workflow와 문서 변경이다.
- FastAPI application, DB schema, migration, K3s manifest, dependency 변경은
  없다.
- Production deployment, K3s rollout, production curl verification은 수행하지
  않았다.
- 운영 반영이 필요하다면 PR merge 이후 사람이 판단한다. 이 devlog는 merge나
  production 반영 완료를 주장하지 않는다.

## README 업데이트 판단

README 업데이트는 필요하지 않다고 판단했다.

근거:

- 변경 범위가 backend application 사용법이 아니라 내부 Agent workflow 계약이다.
- 사용자-facing API, DB, deployment 절차 변경이 없다.
- 관련 사용법과 gate는 `docs/agent/antigravity-review.md`,
  `docs/agent/backend-workflow.md`, `docs/agent/usage-guide.md`,
  `docs/agent/verification-gates.md`에 기록했다.

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
- Application, DB, K3s manifest, dependency 영역 변경은 없었다.

## 이번 단계의 의미

Review workflow가 사람의 prompt 작성 능력과 모델의 과거 기록 해석에 덜
의존하게 됐다. Task, Approved Fixes, Verification을 하네스가 직접 읽고
검증하므로 PR 전 Review gate의 재현성과 실패 진단이 좋아졌다.

또한 UNIT 단위 구현과 Review Status를 분리해 WIP 1 흐름에 맞는 작은 검토 단위를
만들었다. 마지막 통합 Review와 승인 Fix 이후 Re-review도 같은 Review 파일에
누적하면서 기존 History는 보존한다.

## 포트폴리오용 요약

NewsLab backend의 Agent-assisted development workflow에서 Antigravity Review를
자동화했다. Task의 Implementation Units, Approved Fixes, Verification과 Git
diff를 구조적으로 파싱해 다음 Review mode를 결정하고, `agy --print --sandbox`
응답을 검증한 뒤 append-only로 Review History에 반영한다. Re-review에서는 모든
FIX ID와 최신 테스트 evidence를 대조해 과거 Review 상태가 현재 검증 결과로
오인되는 문제를 방지했다.

## 다음 단계 후보

- PR 생성, push, merge 여부는 사람이 결정한다.
- merge 후 production-impacting 작업이 필요하다고 판단되면 사람이 별도
  verification log와 함께 수행한다.
- 다른 repository에도 같은 workflow를 적용할 경우 저장소별 artifact 경로와
  adapter 계약을 점검한다.
- 이후 실제 운영 중 자동 Review 실패 category가 반복되면 failure category별
  troubleshooting 예시를 `docs/agent/usage-guide.md`에 보강한다.
