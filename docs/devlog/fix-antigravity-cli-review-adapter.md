# Antigravity CLI review adapter 전환 및 실패 상태 개선

## 작업 목적

Antigravity review 실행 가능 여부를 단순한 실행 파일 존재가 아니라 실제로 검증된 비대화형 실행 계약에 따라 판정한다.

현재 Gemini CLI에서 발생하는 `UNSUPPORTED_CLIENT` 오류를 성공 가능 상태로 취급하지 않고, 자동 review를 안전하게 중단한 뒤 수동 review로 전환한다. 동시에 review 파일이 존재하거나 초기 템플릿만 생성된 상태를 완료로 오인하지 않도록 파일 구조와 Verdict를 검증한다.

완료 후 workflow가 다음 상태를 구분하는 것을 목표로 했다.

- 자동 review 실행 가능 또는 미지원
- 수동 review 필요
- review process 실행 실패
- review 파일 미완성 또는 완료
- Approved Fixes 처리 필요
- PR 초안 작성 가능

## 기존 문제

기존 workflow는 PATH에서 `gemini`를 발견하면 이를 `Gemini/Antigravity`로 표시하고 `--prompt`, `--approval-mode auto_edit` 옵션으로 실행했다. 그러나 설치된 Gemini CLI는 개인 사용자 환경에서 `UNSUPPORTED_CLIENT` 오류를 반환해 실제 Antigravity review adapter로 사용할 수 없었다.

실행 파일 탐지와 자동 실행 지원 여부가 결합되어 있어 다음 문제가 있었다.

- Gemini CLI 설치만으로 Antigravity 자동 review가 가능한 것처럼 보였다.
- Agent 종료 코드와 review 파일 존재가 실제 review 완료보다 강한 신호로 취급될 수 있었다.
- 빈 파일, 초기 템플릿, 누락된 section이나 Verdict가 있는 파일을 명확히 분류하지 못했다.
- 자동 실행 실패 이후 수동 review 전환 방법과 다음 workflow action이 불명확했다.
- 실행 실패와 review 파일 실패가 하나의 일반 오류로 섞여 원인별 복구가 어려웠다.
- 자동 실행 실패 후에도 fix 또는 PR 단계로 잘못 진행할 여지가 있었다.

## 변경 내용

- Agent 표시 이름, adapter, 실행 파일 후보와 자동 실행 지원 여부를 분리했다.
- PATH의 `gemini`를 Antigravity fallback으로 선택하지 않도록 변경했다.
- `agy`와 `AGENT_ANTIGRAVITY_BIN`은 설치 후보로 탐지하되 자동 실행 지원을 의미하지 않도록 했다.
- 현재 검증 수준에서는 `automatic_review_unavailable`과 `manual review required`를 반환한다.
- 자동 실행 미지원 상태에서는 subprocess와 실행 로그를 생성하지 않는다.
- `UNSUPPORTED_CLIENT`, 인증 실패, 비대화형 실행 미지원, timeout, non-zero exit를 별도 category로 분류했다.
- review 파일 미생성, 미변경, 구조 검증 실패를 process 실패와 별도로 기록한다.
- 최초 review와 최신 Re-review의 필수 section, 실제 본문과 Verdict를 검사하는 전용 모듈을 추가했다.
- workflow status가 review 검증, 자동 실행, 실행 실패와 수동 fallback 상태를 출력하도록 확장했다.
- 미완성 review 또는 자동 실행 실패 상태에서 `codex-fix`와 PR 단계를 제안하지 않도록 했다.
- 자동·수동 review 절차와 실패 복구 기준을 workflow 문서에 동기화했다.
- Python module, class, function과 테스트에 실제 역할과 검증 목적을 설명하는 한글 docstring을 반영했다.

## 구현 상세

### Agent 탐지 계약

`AgentCommand`는 다음 정보를 별도로 보관한다.

- 사용자에게 표시할 Agent 이름
- adapter 종류
- 실행 파일 후보
- 자동 실행 지원 여부
- 사전 failure category
- 수동 fallback 필요 여부
- 다음 권장 action

Codex action은 기존처럼 검증된 Codex CLI 실행 경로를 사용한다. Antigravity action은 `agy`만 후보로 탐지하며 Gemini CLI를 fallback으로 사용하지 않는다.

`agy`가 설치되어 있어도 다음 계약이 모두 확인되지 않았으므로 자동 실행을 활성화하지 않았다.

- 비대화형 단일 prompt의 정상 종료
- 사전 인증된 session 사용
- 사용자 입력 없는 permission 처리
- 지정 review 파일만 수정
- 성공과 실패의 exit code
- stdout·stderr 위치와 내용

실행 후보가 있으면 `automatic_review_unavailable`, 없거나 잘못 설정되면 `executable_missing`으로 판정한다.

### 자동 실행 차단과 수동 fallback

자동 실행이 지원되지 않는 Antigravity command는 runner 진입 전에 차단된다. 따라서 외부 Agent process나 `.agent-runs` 로그를 만들지 않는다.

CLI는 다음 수동 흐름을 안내한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

첫 명령은 review 요청 prompt를 출력하고, 두 번째 명령은 review 결과를 branch별 review 파일에 작성하기 위한 prompt를 출력한다.

### 실행 실패 분류

실행 가능한 테스트 adapter의 stdout, stderr, exit code와 timeout 상태에서 다음 category를 분류한다.

- `unsupported_client`
- `authentication_failed`
- `noninteractive_unsupported`
- `timeout`
- `nonzero_exit`

Review process가 성공해도 파일 결과가 계약을 충족하지 않으면 다음 category를 사용한다.

- `review_file_missing`
- `review_file_unchanged`
- `review_file_validation_failed`

실행 기록에는 Agent, adapter, executable, 자동 실행 지원, exit code, timeout, failure category, manual fallback, review 검증 결과, 완료 여부와 다음 action을 저장한다. 상태 판정 과정에서는 credential이나 stdout·stderr 본문을 노출하지 않는다.

### Review 파일 검증

신규 `review_validation.py`는 파일을 수정하지 않고 Markdown 구조를 검사한다.

최초 review는 다음 항목을 확인한다.

- 필수 2단계 section 전체
- Verdict 외 section의 실제 review 본문
- Verdict section
- 허용 Verdict

Re-review가 있으면 가장 최신 `Re-review N`의 필수 3단계 section과 Verdict가 최종 상태를 결정한다. fenced code block 안의 heading은 구조로 인식하지 않는다.

허용 Verdict는 다음 세 값으로 제한한다.

- `APPROVED`
- `APPROVED WITH NOTES`
- `CHANGES REQUIRED`

Markdown 강조와 Verdict 뒤의 설명은 허용하지만 `PASS`, `APPROVED MAYBE`처럼 임의로 확장한 값은 거부한다.

검증 결과는 파일 없음, 빈 파일, 템플릿, section 누락, 실제 본문 없음, Verdict 누락, 잘못된 Verdict와 완료 상태로 구분된다.

### 자동 review와 수동 review의 완료 조건

자동 review는 다음 조건을 모두 충족해야 한다.

1. Agent process 성공
2. review 파일 신규 생성 또는 실제 변경
3. review 파일 구조 검증 통과

수동 review는 자동 실행 기록이 없어도 동일한 파일 검증을 통과하면 완료로 판정한다. 자동 실행 실패 로그가 있더라도 이후 수동으로 완성된 review 파일은 정상 workflow 완료 근거가 될 수 있다.

### Workflow 상태와 다음 action

`agent_next_step.sh status`는 다음 정보를 구분해 출력한다.

- Verification 상태
- review 상태와 상세 검증 상태
- 자동 review 지원 여부
- 최신 review 실행 상태
- failure category
- 수동 review 필요 여부
- Approved Fixes 상태
- 다음 권장 action

Review가 `template only` 또는 `incomplete`이면 `antigravity-review-write`를 제안한다. Verification이 통과하고 review가 완성된 경우에만 Verdict와 Approved Fixes 상태에 따라 fixes 또는 PR 단계로 진행한다.

## 대안 검토

### 기존 Gemini CLI adapter 유지

기존 코드 변경은 최소화할 수 있지만 현재 client가 `UNSUPPORTED_CLIENT`를 반환한다. 설치와 help option 확인만으로 실제 review 성공을 보장할 수 없어 제외했다.

### `agy`를 즉시 자동 adapter로 활성화

설치된 `agy` 1.0.9는 `--print`, `--prompt`, `--print-timeout` 옵션을 제공했다. 그러나 현재 sandbox에서는 log 디렉터리 기록과 listener bind 제약으로 language server 시작 전에 종료됐다.

사전 인증, 정상 prompt 응답, permission, review 파일 수정 범위와 exit/output 계약을 확인하지 못했으므로 자동 활성화를 deferred로 남겼다.

### 실행 파일이 없을 때만 수동 fallback

설치된 실행 파일이 동작하지 않거나 headless 계약이 불명확한 경우를 처리하지 못한다. 설치 여부와 자동 지원 상태를 분리하는 현재 방식을 선택했다.

### Review 파일 존재만 확인

구현은 단순하지만 초기 템플릿과 미완성 파일을 완료로 오인한다. 필수 구조와 실제 본문, Verdict까지 검증하도록 했다.

### 자동 review 실행 기록이 있는 경우만 완료 인정

자동 adapter를 사용할 수 없는 현재 환경에서는 정상적인 수동 review도 영원히 완료되지 않는다. 자동 review와 수동 review의 완료 조건을 분리하되 동일한 파일 품질 기준을 적용했다.

### Review validator를 state나 runner 내부에 직접 구현

파일 구조 검증이 실행과 상태 로직에 중복되고 테스트하기 어려워진다. 읽기 전용 전용 모듈로 분리해 runner와 state가 같은 판정 결과를 공유하도록 했다.

## 선택한 접근과 근거

“실행 파일 탐지”, “자동 실행 지원”, “process 결과”, “review 파일 품질”을 서로 다른 상태로 모델링했다.

이 접근을 선택한 이유는 다음과 같다.

- 설치된 도구를 실행 가능한 adapter로 성급하게 간주하지 않는다.
- 확인되지 않은 command나 option을 production workflow 계약으로 만들지 않는다.
- 외부 Agent 실패와 review 문서 실패를 독립적으로 진단할 수 있다.
- 수동 review fallback을 유지하면서 자동 review와 같은 품질 기준을 적용할 수 있다.
- 미완성 결과에서 fix나 PR로 넘어가는 잘못된 상태 전이를 차단한다.
- Codex adapter와 application 기능을 변경하지 않고 review workflow에만 범위를 제한할 수 있다.
- backend와 frontend 저장소에 동일한 상태 계약을 적용할 수 있다.

## 트레이드오프

- `agy`가 설치되어 있어도 자동 review는 사용할 수 없다. 안전성을 위해 편의성을 보류했다.
- 수동 review에는 prompt 복사와 결과 작성이라는 사람 작업이 필요하다.
- Markdown section 이름이 workflow 계약이 되므로 review 형식 변경 시 validator와 문서를 함께 수정해야 한다.
- 단순한 파일 존재 검사보다 validator가 복잡하지만 잘못된 완료 판정 위험을 줄인다.
- failure classification은 알려진 stderr marker에 의존하므로 새로운 CLI 오류 형식은 일반 `nonzero_exit`로 분류될 수 있다.
- `AGENT_ANTIGRAVITY_BIN`을 지정해도 현재는 자동 실행을 활성화하지 않는다. 향후 검증된 adapter가 생기면 명시적으로 계약과 테스트를 변경해야 한다.
- 수동 review 완료는 process 실행 증적 없이 파일 검증만으로 인정한다. 대신 필수 구조, 본문과 Verdict를 엄격히 검사한다.
- 현재 branch의 review 파일이 템플릿 상태이므로 구현 검증이 통과했어도 review workflow 자체는 완료되지 않았다.

## 테스트

실제 결과의 source of truth는 `docs/verification/fix-antigravity-cli-review-adapter.md`다.

최종 검증 결과:

- Agent workflow 집중 검증
  - 44개 테스트와 8개 subtest 통과
- Review validator 전용 검증
  - 6개 테스트와 5개 subtest 통과
- Agent workflow 전체 회귀
  - 49개 테스트와 12개 subtest 통과
- Verdict parser 보완 후 최종 집중 검증
  - 50개 테스트와 13개 subtest 통과
- 전체 `pytest`
  - 222 passed
- 전체 `unittest`
  - 222 tests, OK
- `python -m compileall app scripts tests`
  - 통과
- `git diff --check`
  - 통과
- application router, Daily Topic pipeline, DB migration, K3s manifest, dependency와 `app/main.py`
  - diff 없음

실제 상태 확인:

- `scripts/agent_run.sh antigravity-review --preview`
  - 표시 Agent: `Antigravity`
  - adapter: `agy`
  - 자동 실행 지원: `no`
  - failure category: `automatic_review_unavailable`
  - 수동 fallback 필요: `yes`
  - Agent process와 실행 로그 생성 없음
- `scripts/agent_next_step.sh status`
  - Verification: `passed`
  - review: `template only`
  - 자동 review: `unavailable`
  - 수동 review 필요: `yes`
  - 다음 action: `antigravity-review-write`

검증 과정의 실패도 보존했다.

- 미추적 파일 whitespace 검사에서 zsh 특수 배열 변수 `path`를 loop 변수로 사용해 exit code 127이 발생했다.
  - 변수명을 `file_name`으로 바꿔 재실행했고 통과했다.
- sandbox 안에서 실행한 `agy models`와 제한된 단일 prompt 조사는 exit code 1이었다.
  - sandbox의 log 경로 쓰기와 listener bind 제약으로 language server 시작 전에 종료됐다.
  - 자동 review 성공, 인증 실패 또는 정상 output 계약의 증거로 사용하지 않았다.
  - 실제 review prompt는 실행하지 않았다.
- 초기 단계 preview는 Verification이 `pending`이어서 기존 gate가 exit code 2로 차단했다.
  - 후속 구현과 Verification 완료 뒤 preview에서 자동 실행 미지원과 수동 fallback 상태를 확인했다.

전체 `unittest` 출력의 argparse 오류와 provider 실패 문구는 기존 실패 경로 테스트의 예상 출력이며 최종 결과는 `OK`였다.

## 운영 반영

NewsLab production application에 대한 운영 반영은 없다.

- FastAPI 및 application 기능 변경 없음
- DB schema와 migration 변경 없음
- Kubernetes manifest와 CronJob 변경 없음
- 배포 workflow 변경 없음
- Supabase SQL 실행 없음
- production curl verification 없음
- K3s apply, rollout 또는 restart 없음

Agent workflow 관점에서 다음 작업은 pending이다.

- 수동 Antigravity review 작성
- review 파일 완료 상태 재확인
- review finding이 있는 경우 사람의 Approved Fixes 승인
- 필요 시 승인된 fix 적용과 재검증
- Git commit, push, PR 생성과 merge

자동 `agy` adapter 활성화는 사전 인증된 일반 터미널에서 실행 계약이 검증되기 전까지 pending이 아니라 별도 후속 작업 후보로 유지한다.

## README 업데이트 판단

README는 수정하지 않았다.

이번 변경은 NewsLab application의 설치, API, 실행 방법이나 운영 배포 절차가 아니라 repository 내부 Agent review workflow의 실행·검증 계약이다. 따라서 다음 세부 문서에 반영하는 것이 적절하다고 판단했다.

- `docs/agent/backend-workflow.md`: 자동 실행 지원 판정과 수동 fallback
- `docs/agent/antigravity-review.md`: review 완료 조건, Verdict와 복구 절차
- `docs/agent/usage-guide.md`: 실행 방법, failure category와 다른 저장소 적용 기준
- `docs/agent/verification-gates.md`: process와 파일 검증을 결합한 review gate

Architecture와 production runbook의 application 흐름은 변경되지 않아 별도 세부 문서 수정이 필요하지 않았다.

## 확인 결과

- Gemini CLI는 더 이상 Antigravity 자동 adapter로 선택되지 않는다.
- `agy` 설치 여부와 자동 실행 지원 여부가 분리된다.
- 자동 실행 미지원 상태에서는 외부 process와 실행 로그를 만들지 않는다.
- `UNSUPPORTED_CLIENT`, 인증 실패, 비대화형 미지원, timeout과 일반 non-zero exit가 구분된다.
- review 파일 없음, 미변경과 구조 검증 실패가 별도 category로 기록된다.
- 빈 파일, 초기 템플릿, section·본문·Verdict 누락과 잘못된 Verdict를 완료로 처리하지 않는다.
- 세 허용 Verdict와 최신 Re-review 구조를 검증한다.
- Agent가 exit code 0으로 끝나도 유효한 review 파일이 없으면 실패한다.
- 완성된 수동 review는 자동 실행 기록 없이 완료될 수 있다.
- 자동 review 실패와 미완성 review에서 fix·PR 단계 진행이 차단된다.
- Codex implement, `codex-fix`, Task parser와 UNIT 실행 흐름에 회귀가 없었다.
- application, API, DB, Daily Topic pipeline과 K3s 영역은 수정하지 않았다.
- Approved Fixes에 승인된 적용 항목은 없다.
- `agy` 자동 review adapter 활성화는 deferred 상태다.
- 현재 Antigravity review 파일은 템플릿 상태이며 review 완료를 주장하지 않는다.

## 이번 단계의 의미

Agent workflow의 성공 조건을 “CLI가 존재하고 종료됐다”에서 “지원된 adapter가 실행되고 검증 가능한 review 결과를 남겼다”로 강화했다.

외부 Agent 도구의 설치 상태, 인증이나 client 지원이 변해도 workflow가 이를 성공으로 추측하지 않는다. 자동 실행이 불가능한 경우에는 사람 작업으로 명확히 전환하고, 동일한 문서 품질 기준으로 완료 여부를 판정한다.

이 구조는 외부 도구 장애가 review 승인, fix 적용과 PR 준비 상태로 전파되는 것을 차단한다. 또한 자동화와 수동 절차를 동일한 상태 모델에서 관리할 수 있는 기반이 된다.

## 포트폴리오용 요약

외부 AI review CLI의 실행 파일 탐지와 실제 자동 실행 지원 여부를 분리한 안전한 workflow adapter를 설계했다. 지원되지 않는 Gemini client와 미검증 `agy` 실행을 성공으로 간주하지 않고 수동 fallback으로 전환했으며, process 실패와 review 문서 실패를 10개 category로 구분했다. 최초 review와 최신 Re-review의 필수 구조, 본문, 허용 Verdict를 검증하는 읽기 전용 parser를 추가하고 미완성 결과에서 fix·PR 단계 진행을 차단했다. 전체 222건 회귀 테스트와 workflow 상태 검증을 통해 기존 Codex 실행과 application 영역에 회귀가 없음을 확인했다.

## 다음 단계 후보

- 사람이 다음 prompt-only 흐름으로 Antigravity review를 완료한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh status
```

- Review Verdict가 `CHANGES REQUIRED`이면 사람이 적용할 항목만 Approved Fixes에 승인한다.
- 승인된 fix가 생기면 해당 항목만 적용하고 허용된 검증을 다시 수행한다.
- 사전 인증된 일반 터미널에서 `agy --print`의 정상 exit code, stdout·stderr, permission과 지정 파일 수정 범위를 별도 Task로 검증한다.
- 검증된 `agy` 계약이 확보되면 자동 adapter 활성화와 실행 기록 회귀 테스트를 별도 Task에서 구현한다.
- frontend 저장소에도 동일한 표시 Agent·adapter·지원 상태·review 파일 검증 계약을 적용한다.
