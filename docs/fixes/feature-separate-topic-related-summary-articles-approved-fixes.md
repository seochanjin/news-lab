# Approved Fixes: Topic 관련 기사 보존과 Summary 근거 기사 분리

## Approved Fixes

- [x] URL과 제목의 중복 비교 정규화 로직을 분리한다.
  - 제목은 공백을 정규화하고 대소문자를 무시한다.
  - URL은 앞뒤 공백만 제거하고 path와 query의 대소문자를 보존한다.
  - 대소문자가 다른 URL을 서로 다른 기사로 유지하는 회귀 테스트를 추가한다.

## Rejected or Deferred Suggestions

- 없음

## Applied Changes

- `topic_selection_stage.py`에서 URL과 제목의 중복 비교 정규화 함수를
  분리했다.
- URL은 앞뒤 공백만 제거해 path와 query의 대소문자를 보존한다.
- 제목은 기존처럼 연속 공백을 정규화하고 대소문자를 무시한다.
- path와 query 대소문자가 다른 URL 두 건이 모두 Summary 근거 기사로
  선택되는 회귀 테스트를 추가했다.

## Verification Required

- 관련 기사 및 Summary 근거 기사 선정 테스트
- Daily topic pipeline 관련 회귀 테스트
- `python -m compileall app scripts tests`
- `git diff --check`
