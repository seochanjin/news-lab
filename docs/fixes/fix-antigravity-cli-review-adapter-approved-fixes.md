# Approved Fixes: Antigravity CLI review adapter 전환 및 실패 상태 개선

## Approved Fixes

없음.

## Rejected or Deferred Suggestions

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

없음.

## Verification Required

없음.
