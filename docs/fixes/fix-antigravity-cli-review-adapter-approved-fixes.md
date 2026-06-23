# Approved Fixes: Antigravity CLI review adapter 전환 및 실패 상태 개선

## Approved Fixes

- [x] FIX-01: 성공한 process의 failure marker 오분류 방지
- [x] FIX-02: Failure category 문서 정합성 수정

## Rejected or Deferred Suggestions

### Rejected: 과거 자동 review 실행 실패를 근거로 한 영구적인 `codex-fix` 차단

자동 review가 실패했더라도 이후 사용자가 수동 review를 완료하고 review 파일 검증을 통과했으며 Approved Fixes를 승인했다면 workflow는 복구될 수 있어야 한다.

따라서 다음 현재 정책을 유지한다.

- review가 미완성이면 `codex-fix` 및 PR 진행 차단
- 수동 review가 완료되고 Approved Fixes가 승인되면 진행 허용
- 과거 자동 실행 실패 상태만으로 이후 단계를 영구 차단하지 않음

### Deferred: Failure category별 retry 정책 강제

현재 Task는 retry engine 구현이 아니라 실패 분류, 수동 fallback 및 review 완료 검증을 범위로 한다.

다음 항목은 별도 workflow 정책 작업으로 보류한다.

- 인증 실패 후 자동 재시도 금지
- timeout 자동 재시도
- retry 횟수 및 backoff
- failure category별 재실행 허용 정책
- 반복 실패 상태 보존

### Deferred: `WorkflowState` type-checking import 추가

현재 annotation은 runtime에서 안전하게 처리되며 실제 type checker 실패가 확인되지 않았다.

향후 정적 type checker를 workflow 검증에 추가하고 unresolved-name 오류가 확인되면 다음 형태를 검토한다.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state import WorkflowState
```

### Deferred: `agy` 자동 review adapter 활성화

현재 로컬 환경에서 다음 비대화형 단일 prompt를 실행했으나 정상 응답을 받지 못했다.

```bash
agy --print \
  --print-timeout 60s \
  "파일을 수정하지 말고 OK만 출력해."
```

실행 결과:

```text
Error: timed out waiting for response
```

현재 상태에서는 다음 항목이 확인되지 않았다.

- 사전 인증된 `agy` session의 정상 동작
- 비대화형 단일 prompt의 exit code 0 완료
- stdout 응답 반환
- 지정 review 파일 수정
- permission prompt 없는 headless 실행
- 정상 실패와 인증 실패의 구분

따라서 이번 Task에서는 `automatic_review_unavailable` 상태와 수동 review fallback을 유지한다.

자동 review 활성화는 다음 조건이 별도 작업에서 검증된 뒤 진행한다.

1. 일반 터미널에서 `agy --print` 단일 prompt가 exit code 0으로 완료된다.
2. 지정된 임시 파일만 수정할 수 있다.
3. 비대화형 실행 중 사용자 입력이나 permission prompt가 발생하지 않는다.
4. stdout, stderr와 exit code 계약을 확인한다.
5. review 파일 변경 범위와 완료 검증을 하네스 테스트로 보장한다.

## Applied Changes

- FIX-01: `classify_failure()`가 timeout을 우선 처리한 뒤 exit code 0을 즉시
  성공으로 반환하도록 변경했다. 실패 marker는 non-zero process에서만
  해석하며, 정상 출력에 `unsupported client`, 인증 또는 TTY 관련 문구가
  포함되어도 실패로 오분류하지 않는 회귀 테스트를 추가했다.
- FIX-02: workflow 문서에서 외부 Gemini `reasonCode: UNSUPPORTED_CLIENT`와
  내부 `unsupported_client` category를 구분했다. failure category 목록에
  pre-flight 상태인 `automatic_review_unavailable`을 포함하고 실제 구현의
  소문자 category 값을 명시했다.

## Verification Required

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
