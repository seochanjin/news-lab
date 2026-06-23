# Antigravity CLI review adapter 전환 및 실패 상태 개선

## 작업 내용

- Gemini CLI 설치를 Antigravity 자동 review 실행 가능 근거로 사용하던 기존 adapter 탐지를 제거했다.
- Agent 표시 이름, adapter, 실행 파일 후보와 자동 실행 지원 여부를 별도 상태로 관리하도록 workflow 계약을 변경했다.
- 현재 검증 수준에서는 Antigravity 자동 실행을 비활성화하고 기존 두 단계 수동 review prompt 흐름을 안내하도록 했다.
- Agent process 실패와 review 파일 미완성을 구분하는 failure category와 실행 기록을 추가했다.
- review 파일의 존재 여부가 아니라 필수 section, 실제 본문과 Verdict를 검증해 완료 상태를 판정하도록 했다.
- workflow 상태 출력과 다음 단계 판정을 보강해 실패하거나 미완성인 review에서 fix 또는 PR 단계로 진행하지 않도록 했다.
- 자동·수동 review 차이, 실패 복구, 완료 조건과 backend·frontend 공통 적용 기준을 관련 workflow 문서에 반영했다.

## 주요 변경 사항

### Antigravity adapter 탐지

- PATH의 `gemini`를 Antigravity adapter로 선택하지 않는다.
- `agy`와 `AGENT_ANTIGRAVITY_BIN`은 실행 파일 후보로만 탐지한다.
- 실행 파일이 있어도 비대화형 prompt, 인증, permission, 파일 작성과 종료 상태 계약이 검증되지 않았으면 `automatic_review_unavailable`로 판정한다.
- 실행 파일을 찾지 못하면 `executable_missing`으로 판정한다.
- 자동 실행 미지원 상태에서는 subprocess와 `.agent-runs` 로그를 만들지 않고 다음 수동 흐름을 안내한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

Codex implement와 `codex-fix` adapter의 기존 실행 의미는 유지했다.

### 실행 실패와 기록

다음 failure category를 구분한다.

- `executable_missing`
- `automatic_review_unavailable`
- `unsupported_client`
- `authentication_failed`
- `noninteractive_unsupported`
- `timeout`
- `nonzero_exit`
- `review_file_missing`
- `review_file_unchanged`
- `review_file_validation_failed`

실행 결과에는 표시 Agent, adapter, 실행 파일, 자동 실행 지원 여부, exit code, timeout, failure category, 수동 fallback 필요 여부, review 파일 검증 결과, 완료 판정과 다음 action을 기록한다.

`UNSUPPORTED_CLIENT`는 일반 실패와 구분하고 같은 client를 성공으로 간주하지 않으며 수동 review로 전환한다.

### Review 파일 완료 검증

신규 `review_validation.py`가 최초 review와 최신 Re-review를 읽기 전용으로 검증한다.

다음 상태는 완료로 처리하지 않는다.

- 파일 없음 또는 빈 파일
- heading만 있는 초기 템플릿
- 필수 section 누락
- 실제 review 본문 없음
- Verdict 누락
- 허용되지 않은 Verdict

허용 Verdict는 다음 세 값이다.

- `APPROVED`
- `APPROVED WITH NOTES`
- `CHANGES REQUIRED`

자동 review는 process 성공과 review 파일 생성 또는 변경, 구조 검증을 모두 통과해야 완료된다. 수동 review는 자동 실행 기록이 없어도 같은 파일 검증을 통과하면 완료될 수 있다.

### Workflow 상태와 문서

- `agent_next_step.sh status`가 review 검증 상태, 자동 실행 상태, 실행 실패, 수동 review 필요 여부와 다음 action을 출력한다.
- 자동 실행 실패 또는 미완성 review에서는 `codex-fix`나 PR 초안을 다음 action으로 제안하지 않는다.
- 다음 문서를 현재 동작에 맞게 갱신했다.
  - `docs/agent/backend-workflow.md`
  - `docs/agent/antigravity-review.md`
  - `docs/agent/usage-guide.md`
  - `docs/agent/verification-gates.md`
- `docs/tasks/main.md`가 현재 branch Task를 가리키도록 갱신했다.

Approved Fixes 문서에는 적용 승인된 항목이 없으며, `agy` 자동 adapter 활성화는 비대화형 실행 계약이 확인되지 않아 deferred 상태다.

## 추가/변경된 API

없음.

- FastAPI endpoint 변경 없음
- Request·response schema 변경 없음
- NewsLab application 기능 변경 없음

이번 변경은 repository 내부 Agent workflow CLI와 상태 판정에만 적용된다.

## DB 변경 사항

없음.

- DB schema 및 migration 변경 없음
- Supabase SQL 실행 없음
- application data write 없음

## README 영향

README는 변경하지 않았다.

이번 변경은 application 설치·실행 방법이나 사용자-facing 기능이 아니라 Agent review workflow의 내부 실행·검증 계약 변경이다. 상세 사용법과 복구 절차는 `docs/agent/` 문서에 반영하는 것이 적절하다고 판단했다.

## 테스트

`docs/verification/fix-antigravity-cli-review-adapter.md`에 기록된 실제 결과:

- Agent workflow 집중 테스트
  - 44개 테스트와 8개 subtest 통과
- Review 검증 전용 테스트
  - 6개 테스트와 5개 subtest 통과
- Agent workflow 전체 회귀
  - 49개 테스트와 12개 subtest 통과
- 전체 `pytest`
  - 222 passed
- 전체 `unittest`
  - 222 tests, OK
- `python -m compileall app scripts tests`
  - 통과
- `git diff --check`
  - 통과
- application router, Daily Topic pipeline, DB migration, K3s manifest, dependency와 `app/main.py` 변경 검사
  - diff 없음
- `scripts/agent_run.sh antigravity-review --preview`
  - adapter `agy`
  - 자동 실행 지원 `no`
  - failure category `automatic_review_unavailable`
  - 수동 fallback 필요 `yes`
  - Agent process와 실행 로그는 생성되지 않음
- `scripts/agent_next_step.sh status`
  - Verification `passed`
  - review `template only`
  - 자동 review `unavailable`
  - 수동 review 필요 `yes`
  - 다음 action `antigravity-review-write`

검증 과정에서 다음 실패도 기록했다.

- 최초 미추적 파일 whitespace 검사 command는 zsh의 특수 변수 `path`를 loop 변수로 사용해 exit code 127로 실패했다.
  - 변수명을 `file_name`으로 변경한 재실행은 통과했다.
- sandbox 내부 `agy models`와 `agy --print` 조사 실행은 filesystem/network 제약으로 exit code 1이었다.
  - 인증, 정상 응답, review 파일 작성 계약을 확인할 근거로 사용하지 않았다.
  - 실제 review prompt는 실행하지 않았다.

## 확인 결과

- Gemini CLI만 설치된 환경을 Antigravity 자동 실행 가능 상태로 판정하지 않는다.
- `agy` 설치 여부와 자동 실행 지원 여부가 분리된다.
- 자동 실행 미지원 상태에서는 process를 시작하지 않고 수동 review 절차를 안내한다.
- `UNSUPPORTED_CLIENT`, 인증 실패, 비대화형 실행 미지원, timeout과 일반 non-zero exit가 구분된다.
- Agent exit code가 0이어도 review 파일이 없거나 변경되지 않았거나 검증에 실패하면 review 완료로 처리하지 않는다.
- 파일 없음, 빈 파일, 초기 템플릿, 필수 section·본문·Verdict 누락과 잘못된 Verdict가 미완성으로 판정된다.
- 세 허용 Verdict와 최신 Re-review 구조가 인식된다.
- 완성된 수동 review는 자동 실행 기록 없이 완료로 판정된다.
- 자동 review 실패 또는 미완성 상태에서 fix·PR 단계 진행이 차단된다.
- Codex implement·fix gate, Task parser와 UNIT 실행 흐름의 회귀가 없었다.
- application, API, DB, Daily Topic pipeline과 K3s 영역은 수정하지 않았다.
- 승인되어 적용된 review fix는 없다.

## 비고

- Verification 상태는 `passed`지만 현재 Antigravity review 파일은 초기 템플릿 상태다.
- 자동 Antigravity review는 지원되는 것으로 확인되지 않았으며 완료를 주장하지 않는다.
- PR 진행 전 사람이 다음 수동 review 흐름을 수행하고 review 파일의 완료 판정을 확인해야 한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh status
```

- review 결과가 fix를 요구하면 사람이 Approved Fixes에 적용 항목을 승인한 후 별도 fix 단계를 진행해야 한다.
- `agy` 자동 adapter 활성화는 사전 인증된 일반 터미널에서 비대화형 prompt, permission, stdout·stderr, exit code와 review 파일 변경 계약이 검증된 뒤 별도 Task로 다룬다.
- Git push, PR 생성·merge, production deployment, K3s rollout, production verification과 Supabase SQL은 수행하지 않았다.
