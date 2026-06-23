# CodeRabbit Review: Antigravity CLI review adapter 전환 및 실패 상태 개선

## Review Summary

CodeRabbit은 failure category 문서 정합성, subprocess 실패 분류 조건, workflow 복구 정책 및 type annotation import를 검토했다.

검토 결과 다음 두 항목은 실제 수정이 필요한 것으로 판단한다.

1. `classify_failure()`가 process 성공 여부를 확인하기 전에 stdout·stderr marker를 검사하여, exit code 0인 정상 실행을 실패로 오분류할 수 있다.
2. workflow 문서의 failure category 목록에서 `unsupported_client` 대소문자가 구현과 일치하지 않고, pre-flight 단계에서 사용하는 `automatic_review_unavailable`이 누락되어 있다.

반면 retry 강제, 인증 실패 후 재시도 차단, 과거 자동 review 실패를 근거로 한 영구적인 `codex-fix` 차단은 현재 Task의 요구사항이 아니며 수동 review fallback 설계와 충돌할 수 있다. `WorkflowState` type annotation은 postponed annotation 또는 문자열 annotation으로 runtime 안전성이 확보되어 있으므로 필수 수정으로 분류하지 않는다.

## Problems Found

### 1. 성공한 process가 stdout·stderr 문구 때문에 실패로 오분류될 수 있음

`runner.py`의 failure 분류 로직은 현재 stdout과 stderr를 먼저 결합하여 다음 marker를 검사한다.

- `unsupported_client`
- 인증 실패 관련 문구
- 비대화형 실행 미지원 문구

이 검사가 `exit_code != 0` 조건보다 먼저 수행되면, exit code 0으로 정상 완료된 review 출력에 다음과 같은 일반 문장이 포함된 경우 실패로 오분류될 수 있다.

```text
The unsupported client issue was resolved.
The user is now authenticated.
```

정상 process는 review 파일 검증 단계로 넘기고, stdout·stderr 기반 실패 marker는 timeout 또는 non-zero exit 상태에서만 해석해야 한다.

Severity: Major

### 2. 문서의 failure category가 구현과 일치하지 않음

문서에서 `UNSUPPORTED_CLIENT`를 failure category처럼 대문자로 표기한 부분이 있으나 실제 내부 category는 다음 소문자 값이다.

```text
unsupported_client
```

또한 executable은 존재하지만 자동 실행 지원 검증이 완료되지 않은 pre-flight 상태에서 사용하는 다음 category가 문서 목록에 누락되어 있다.

```text
automatic_review_unavailable
```

문서의 failure category 목록을 구현과 동일하게 정리해야 한다.

Severity: Minor

### 3. 복구 절차를 gate에서 강제해야 한다는 제안은 현재 계약과 일치하지 않음

CodeRabbit은 다음 내용을 문제로 제시했다.

- `authentication_failed` 후 재시도 금지를 코드로 강제하지 않음
- retry 정책이 구현되어 있지 않음
- review execution이 한 번 실패했다면 `codex-fix`를 차단해야 함

그러나 현재 workflow의 목적은 자동 재시도 엔진을 구현하는 것이 아니라 실패 원인을 분류하고 안전한 수동 review fallback을 제공하는 것이다.

또한 자동 review 실행이 실패했더라도 이후 사용자가 수동 review 파일을 완성하고 Approved Fixes를 승인했다면 다음 단계로 진행할 수 있어야 한다. 과거 `review_execution_status=failed`만을 근거로 계속 차단하면 수동 fallback을 통한 복구가 불가능해진다.

따라서 다음 현재 조건을 유지하는 것이 적절하다.

- 자동 실행 실패 후 review가 여전히 미완성이면 `codex-fix`와 PR 진행 차단
- 수동 review가 검증을 통과하고 Approved Fixes가 승인되면 진행 허용
- 실패 category에 따른 자동 retry 또는 영구 retry 차단은 별도 후속 범위

Severity: Not accepted as a defect

### 4. `WorkflowState` import 제안은 필수 수정이 아님

`cli.py`의 `WorkflowState`가 문자열 annotation 또는 postponed annotation으로 사용되고 있다면 runtime에서 직접 import하지 않아도 안전하다.

정적 type checker 설정에서 실제 unresolved-name 오류가 확인되지 않은 상태에서 import를 추가하는 것은 선택적 개선이다. 순환 import 가능성이나 runtime dependency 증가 여부를 함께 검토해야 한다.

Severity: Optional

## Required Fixes Before PR

- [ ] `classify_failure()`가 stdout·stderr marker를 검사하기 전에 timeout과 process exit code를 기준으로 성공·실패를 구분하도록 수정한다.
- [ ] exit code 0인 정상 실행은 marker 문구가 포함되어 있어도 failure category로 오분류하지 않는 회귀 테스트를 추가한다.
- [ ] workflow 문서에서 failure category를 실제 구현 값인 `unsupported_client`로 통일한다.
- [ ] workflow 문서의 failure category 목록에 `automatic_review_unavailable`을 추가한다.
- [ ] 수정 후 agent workflow 집중 테스트와 전체 회귀 테스트를 다시 수행한다.

## Optional Improvements

- `WorkflowState` annotation import는 실제 type checker 오류가 확인될 경우 `TYPE_CHECKING` block을 사용하는 방식으로 추가할 수 있다.
- 실패 category별 자동 retry 또는 retry 금지 정책은 별도의 workflow 정책 Task로 검토할 수 있다.
- failure category 문자열을 여러 모듈에서 직접 작성하고 있다면 향후 enum 또는 상수 모듈로 통합할 수 있다.

## Suggested Test Commands

```bash
python -m pytest \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

```bash
python -m pytest tests/test_agent_review_validation.py -v
```

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

```bash
python -m compileall app scripts tests
```

```bash
git diff --check
```

```bash
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

## Risk Notes

- failure marker 검사를 무조건 제거하면 실제 non-zero 실행의 세부 failure category가 모두 `nonzero_exit`로 축소될 수 있다. marker 검사는 유지하되 timeout 또는 non-zero exit 상태에서만 수행해야 한다.
- 과거 자동 실행 실패만으로 이후 workflow를 영구 차단하면 수동 review fallback으로 복구할 수 없으므로 현재 review 파일 완료 상태와 Approved Fixes 상태를 최종 진행 기준으로 유지해야 한다.
- 문서의 `UNSUPPORTED_CLIENT`는 외부 Gemini 오류의 `reasonCode`를 인용할 때는 대문자를 유지할 수 있다. 다만 내부 failure category를 설명하는 위치에서는 `unsupported_client`로 구분해서 작성해야 한다.

## Verdict

**CHANGES REQUIRED**
