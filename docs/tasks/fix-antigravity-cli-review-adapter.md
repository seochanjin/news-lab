# Task: Antigravity CLI review adapter 전환 및 실패 상태 개선

## Goal

현재 `scripts/agent_run.sh antigravity-review`는 `gemini` 실행 파일을 `Gemini/Antigravity` agent로 탐지해 실행한다.

하지만 현재 로컬 환경의 Gemini CLI는 다음 오류로 실행되지 않는다.

```text
IneligibleTierError
reasonCode: UNSUPPORTED_CLIENT
This client is no longer supported for Gemini Code Assist for individuals.
```

이번 작업의 목표는 Antigravity review 실행 가능 여부를 실제 환경과 지원 방식에 따라 판정하고, 자동 실행이 불가능한 경우 안전한 수동 review 흐름으로 전환하는 것이다.

또한 review 파일이 존재하거나 초기 템플릿만 생성된 상태를 review 완료로 오인하지 않도록 review 검증과 다음 단계 판정을 강화한다.

완료 후에는 다음 상태를 명확히 구분할 수 있어야 한다.

- 자동 Antigravity review 실행 가능
- 자동 review 실행 불가
- 수동 review 필요
- review 실행 실패
- review 파일 미완성
- review 완료
- Approved Fixes 처리 필요
- PR 초안 작성 가능

## Scope

### Antigravity 실행 방식 조사

- 현재 `gemini` adapter의 탐지, 실행 및 상태 판정 흐름을 확인한다.
- 현재 환경에서 실제로 사용할 수 있는 Antigravity 실행 또는 연동 방식을 조사한다.
- 실행 파일명, 설치 여부 확인 방식, 비대화형 실행 지원 여부를 확인한다.
- prompt 전달 방식, 인증 방식, exit code 및 stdout·stderr 처리 방식을 확인한다.
- shell script에서 자동 호출할 수 있는지 확인한다.
- 확인되지 않은 명령이나 option을 추측하여 구현하지 않는다.
- 자동 실행 지원 여부와 선택한 접근을 Verification에 기록한다.

### Agent 탐지와 adapter 계약 개선

- agent 표시 이름과 실제 실행 adapter를 분리한다.
- `gemini` 실행 파일이 존재한다는 이유만으로 Antigravity 자동 실행 가능 상태로 판정하지 않는다.
- 자동 실행 가능 여부를 명시적인 상태로 표현한다.
- 자동 실행이 가능한 경우 실제로 확인된 Antigravity 실행 방식만 사용한다.
- 자동 실행이 불가능한 경우 수동 review 필요 상태를 반환한다.
- Codex adapter 실행 경로는 기존 동작을 유지한다.

### Review 실행 실패 분류

다음 실패 유형을 구분한다.

- 실행 파일 미설치
- 지원되지 않는 client
- 인증 실패
- 비대화형 실행 미지원
- timeout
- non-zero exit
- review 파일 미생성
- review 파일 미변경
- review 파일 검증 실패

`UNSUPPORTED_CLIENT` 오류는 별도 failure category로 분류하고, 수동 review 절차를 안내한다.

### Review 파일 완료 검증

review 파일 존재 여부와 review 완료 여부를 분리한다.

다음 상태는 완료된 review로 처리하지 않는다.

- 파일이 없음
- 빈 파일
- 초기 템플릿만 존재
- 필수 section 누락
- 실제 review 본문 없음
- Verdict 누락
- 허용되지 않은 Verdict 사용

허용 Verdict는 다음과 같다.

- `APPROVED`
- `APPROVED WITH NOTES`
- `CHANGES REQUIRED`

자동 review는 agent 실행 결과와 review 파일 검증을 모두 통과해야 완료로 판정한다.

수동 review는 자동 실행 기록이 없어도 review 파일 검증을 통과하면 완료로 판정할 수 있다.

### Workflow 상태 및 다음 단계 개선

`agent_next_step.sh status`와 관련 state logic에서 다음 상태를 구분한다.

- review not started
- review template only
- automatic review unavailable
- manual review required
- review execution failed
- review incomplete
- review completed

자동 실행 실패 후 빈 review 파일만 존재하는 상태에서 `codex-fix` 또는 PR 초안 단계로 진행하지 않도록 한다.

현재 상태와 함께 사용자가 수행할 다음 명령을 출력한다.

### 수동 review fallback 유지

다음 기존 흐름을 유지한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

역할은 다음과 같이 구분한다.

- `antigravity-review`
  - review 요청 prompt 출력
- `antigravity-review-write`
  - review 결과를 지정된 review 파일에 작성하게 하는 prompt 출력
- `scripts/agent_run.sh antigravity-review`
  - 자동 실행이 지원되는 경우에만 agent 실행
  - 지원되지 않으면 수동 review 필요 상태와 안내 출력

### 실행 기록 개선

Antigravity review 실행 결과에 다음 정보를 기록한다.

- agent 표시 이름
- adapter 종류
- 실행 파일
- 자동 실행 지원 여부
- exit code
- timeout 여부
- failure category
- 수동 fallback 필요 여부
- review 파일 검증 결과
- review 완료 판정
- 다음 권장 action

민감한 인증 정보는 실행 기록에 포함하지 않는다.

### 문서 동기화

다음 내용을 agent workflow 문서에 반영한다.

- Antigravity 자동 실행 지원 조건
- 자동 review와 수동 review의 차이
- Gemini CLI `UNSUPPORTED_CLIENT` 오류 처리
- 수동 review 절차
- review 완료 판정 기준
- 허용 Verdict
- 실패 후 복구 절차
- backend와 frontend 저장소에 동일한 기준을 적용하는 방법

## Do not change

- NewsLab application 기능
- Daily Topic pipeline
- 기사 수집, embedding, clustering 및 Summary 처리
- FastAPI router와 API schema
- DB schema와 migration
- K3s manifest와 CronJob
- GitHub Actions와 배포 workflow
- Codex implement 및 `codex-fix`의 기존 실행 의미
- review finding의 승인 및 적용 정책
- 기존 task의 review 파일 내용
- frontend application 코드

기존 Gemini CLI 오류를 무시하거나 성공으로 처리하지 않는다.

review 파일 존재만으로 review 완료를 판정하지 않는다.

자동 review가 지원되는 것으로 확인되지 않은 상태에서 가상의 Antigravity 명령이나 option을 추가하지 않는다.

## Expected files

예상 변경 범위:

```text
scripts/agent_workflow/gates.py
scripts/agent_workflow/runner.py
scripts/agent_workflow/state.py
scripts/agent_workflow/cli.py
scripts/agent_workflow/prompt_builder.py
scripts/agent_run.sh
scripts/agent_next_step.sh
```

책임 분리를 위해 필요한 경우 다음과 같은 모듈을 추가할 수 있다.

```text
scripts/agent_workflow/review_validation.py
scripts/agent_workflow/agent_detection.py
```

예상 테스트 범위:

```text
tests/test_agent_workflow_gates.py
tests/test_agent_workflow_runner.py
tests/test_agent_workflow_state.py
tests/test_agent_workflow_cli.py
tests/test_agent_task_parser.py
```

필요한 경우 다음과 같은 전용 테스트를 추가할 수 있다.

```text
tests/test_agent_review_validation.py
tests/test_antigravity_adapter.py
```

예상 문서 범위:

```text
AGENTS.md
docs/agent/backend-workflow.md
docs/agent/antigravity-review.md
docs/agent/usage-guide.md
docs/agent/verification-gates.md
docs/agent/forbidden-commands.md
```

`docs/prompts/*`는 현재 workflow와 불일치하는 내용이 있을 때만 호환용 문서로 수정한다.

현재 branch용 task, verification, review, fixes, PR 및 devlog 문서를 갱신한다.

## DB changes

없음.

## API changes

없음.

## Test commands

Agent workflow 집중 검증:

```bash
python -m pytest \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

전용 테스트가 추가된 경우:

```bash
python -m pytest \
  tests/test_agent_review_validation.py \
  tests/test_antigravity_adapter.py \
  -v
```

Agent workflow 전체 회귀:

```bash
python -m pytest \
  tests/test_agent_task_parser.py \
  tests/test_agent_workflow_cli.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  -v
```

전체 회귀:

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

문법 및 diff 검증:

```bash
python -m compileall app scripts tests
```

```bash
git diff --check
```

변경 금지 영역 확인:

```bash
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Preview 확인:

```bash
scripts/agent_run.sh antigravity-review --preview
```

다음 상태를 자동화 테스트 또는 임시 repository fixture로 검증한다.

- Antigravity 실행 파일이 없는 상태
- Gemini CLI만 설치된 상태
- `UNSUPPORTED_CLIENT` 오류
- 인증 실패
- timeout
- non-zero exit
- review 파일 미생성
- review 파일 초기 템플릿 유지
- Verdict 누락
- 잘못된 Verdict
- 정상 수동 review 파일
- 정상 자동 review 결과

실제 외부 Antigravity 실행은 조사 결과 자동 실행이 지원되고 현재 환경에서 실행 가능하다고 확인된 경우에만 수행한다.

## Acceptance criteria

- [x] 현재 Gemini CLI가 Antigravity 자동 review 실행 도구로 잘못 판정되지 않는다.
- [x] Antigravity 자동 실행 지원 여부를 명시적으로 판정한다.
- [x] 확인되지 않은 Antigravity 명령이나 option을 사용하지 않는다.
- [x] 자동 실행이 불가능하면 수동 review 필요 상태를 반환한다.
- [x] `UNSUPPORTED_CLIENT`를 별도의 failure category로 판정한다.
- [x] `UNSUPPORTED_CLIENT` 발생 시 원인과 수동 review 절차를 안내한다.
- [x] 실행 파일 미설치, 인증 실패, timeout 및 non-zero exit를 구분한다.
- [x] agent 실행 실패를 review 완료로 판정하지 않는다.
- [x] review 파일 존재 여부와 review 완료 여부를 구분한다.
- [x] 빈 review 파일을 완료로 판정하지 않는다.
- [x] 초기 review 템플릿을 완료로 판정하지 않는다.
- [x] 필수 section이 없는 review를 완료로 판정하지 않는다.
- [x] 실제 review 본문이 없는 파일을 완료로 판정하지 않는다.
- [x] Verdict가 없는 review를 완료로 판정하지 않는다.
- [x] 허용되지 않은 Verdict를 완료로 판정하지 않는다.
- [x] `APPROVED` Verdict를 인식한다.
- [x] `APPROVED WITH NOTES` Verdict를 인식한다.
- [x] `CHANGES REQUIRED` Verdict를 인식한다.
- [x] 완성된 수동 review 파일을 정상 완료로 판정한다.
- [x] 자동 review 실패 후 fix 또는 PR 단계로 잘못 진행하지 않는다.
- [x] `agent_next_step.sh status`가 review 상태와 다음 action을 출력한다.
- [x] 기존 `antigravity-review` prompt 출력 흐름이 유지된다.
- [x] 기존 `antigravity-review-write` 수동 흐름이 유지된다.
- [x] review finding을 Approved Fixes로 자동 등록하지 않는다.
- [x] 실행 기록에 adapter와 failure category가 포함된다.
- [x] 실행 기록에 수동 fallback 필요 여부가 포함된다.
- [x] 실행 기록에 review 파일 검증 결과가 포함된다.
- [x] Codex implement 흐름에 회귀가 없다.
- [x] `codex-fix` 흐름에 회귀가 없다.
- [x] task parser와 UNIT 실행 흐름에 회귀가 없다.
- [x] agent workflow 집중 테스트가 통과한다.
- [x] 전체 pytest가 통과한다.
- [x] 전체 unittest가 통과한다.
- [x] compileall이 통과한다.
- [x] `git diff --check`가 통과한다.
- [x] application, DB, API 및 K3s 변경이 없다.
- [x] Antigravity 자동 및 수동 review 절차가 문서화된다.
- [x] 실제 외부 실행을 하지 않은 경우 자동 review 성공을 주장하지 않는다.

## Notes

현재 확인된 실행 흐름:

```text
antigravity-review action
→ gates.py가 gemini 실행 파일 탐지
→ agent 이름을 Gemini/Antigravity로 지정
→ runner.py가 gemini adapter 실행
→ 인증 단계에서 UNSUPPORTED_CLIENT 발생
→ exit code 1
```

현재 확인된 오류:

```text
IneligibleTierError
reasonCode: UNSUPPORTED_CLIENT
tierName: Gemini Code Assist for individuals
```

이번 작업은 Antigravity 자동 실행 구현을 완료 상태로 미리 가정하지 않는다.

조사 결과에 따라 다음 중 하나를 선택한다.

1. 공식적으로 지원되고 자동화 가능한 Antigravity 실행 방식으로 adapter 전환
2. 자동 실행을 비활성화하고 명시적인 수동 review workflow 제공

### UNIT-01 조사 결과와 adapter 계약

2026-06-23 로컬 환경에서 확인한 실행 파일은 다음과 같다.

- `antigravity`: 설치되지 않음
- `gemini`: `/opt/homebrew/bin/gemini`, version `0.45.0`
- `agy`: `~/.local/bin/agy`, version `1.0.9`

`agy --help`는 `--print`/`--prompt` 단일 prompt 비대화형 실행,
`--print-timeout`, `--sandbox`를 명시한다. 반면 현재 sandbox에서는
`~/.gemini/antigravity-cli/log` 기록과 loopback listener 생성이 차단되어
`agy models`와 단일 prompt 실행이 exit code 1로 종료됐다. 따라서 인증 상태,
실제 review 파일 작성, 정상 종료 시 stdout·stderr 계약은 아직 확인되지 않았다.

후속 UNIT에서 적용할 adapter 계약은 다음과 같다.

- 사용자 표시 이름은 `Antigravity`, adapter 식별자는 실제 실행 방식과 분리한다.
- 기본 Antigravity 실행 후보는 `agy`이며 `gemini`를 자동 fallback으로 사용하지
  않는다.
- `gemini` 실행 파일 존재 여부는 Antigravity 자동 실행 지원 근거가 아니다.
- `agy` 자동 실행은 설치만으로 활성화하지 않는다. 확인된 headless 인자,
  사전 인증된 사용자 session, 비대화형 permission 처리, review 파일 작성과
  exit/output 동작이 모두 검증된 경우에만 지원 상태로 판정한다.
- 현재 repository 기준 기본 판정은 `automatic review unavailable`과
  `manual review required`다.
- 자동 실행이 검증되기 전에는 가상의 option, credential 전달 방식 또는
  성공 판정을 추가하지 않는다.
- 인증 정보는 command argument, 실행 로그와 workflow 문서에 기록하지 않는다.
- 실행 결과는 최소한 adapter, executable, 자동 실행 지원 여부, exit code,
  timeout, failure category와 manual fallback 필요 여부를 보존한다.
- 외부 process exit code 0만으로 review 완료를 판정하지 않고, 후속 UNIT의
  review 파일 검증을 함께 통과해야 한다.

우선순위는 다음과 같다.

```text
잘못된 자동 실행 판정 제거
→ 실제 지원 방식 확인
→ 실패 상태 분류
→ 수동 fallback 보장
→ review 완료 판정 강화
```

이번 작업 완료 후 최근 72시간 및 168시간 기사 embedding을 재사용하는 Period Topic pipeline 작업을 진행한다.

## Implementation Units

- [x] UNIT-01: Antigravity 실행 방식 조사 및 adapter 계약 정의
- [x] UNIT-02: Agent 탐지·실행 adapter와 실패 분류 개선
- [x] UNIT-03: Review 파일 검증 및 workflow 상태 판정 강화
- [x] UNIT-04: 수동 fallback·문서 동기화 및 전체 회귀 검증
