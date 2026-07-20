# Approved Fixes: Topic Summary 제목·기간 정합성 수정

## Approved Fixes

- [x] FIX-01: Home payload에서 invalid period row를 격리
- [x] FIX-02: 3-day·Weekly archive list에서 invalid row를 skip
- [x] FIX-03: 3-day·Weekly detail의 period 오류를 구조화된 500으로 변환
- [x] FIX-04: Invalid metadata API 경계 테스트 추가
- [x] FIX-05: Review·Approved Fixes 문서와 PR 상태 정합화

### FIX-01. Home payload에서 invalid period row를 격리

대상:

- `app/home_topics_payload.py`
- `fetch_three_day_home_topics_from_database()`
- `fetch_weekly_home_topics_from_database()`

판정: 승인

승인 이유:

- period validator는 잘못된 저장 metadata를 감지하기 위해 의도적으로 `ValueError`를 발생시킨다.
- 현재 list comprehension에서는 한 row의 예외가 전체 Home payload를 실패시킨다.
- Home API는 여러 card를 제공하므로 invalid row를 제외하고 valid row를 유지하는 것이 availability와 데이터 정확성을 함께 보존한다.

승인 변경:

1. 두 Home 함수에서 row별로 title sanitize와 period 계산을 수행한다.
2. `ValueError` 발생 시 warning log를 남기고 해당 row만 제외한다.
3. log에는 topic type과 row ID만 포함한다.
4. 유효한 첫 row를 기준으로 기존 top-level metadata와 `period_start`, `period_end`를 구성한다.
5. 모든 row가 제외되면 기존 empty payload 형태를 유지한다.

보존 조건:

- period validation 규칙 변경 없음
- DB row 수정 없음
- Home cache key·TTL 변경 없음
- Redis flush 없음
- title, window, credential log 금지

### FIX-02. 3-day·Weekly archive list에서 invalid row를 skip

대상:

- `app/routers/three_day_topics.py`
- `app/routers/weekly_topics.py`

판정: 승인

승인 이유:

- CodeRabbit은 Weekly list를 직접 지적했다.
- 3-day list도 동일한 `with_*_topic_period()` 호출 구조를 사용해 같은 장애 가능성이 있다.
- 한 row의 데이터 품질 문제로 정상 row 전체를 반환하지 못하는 것보다, invalid row를 제외하고 warning을 남기는 것이 archive endpoint에 적합하다.

승인 변경:

- 두 list endpoint에서 row별 변환을 수행한다.
- `ValueError` row는 warning log 후 응답에서 제외한다.
- 정상 row와 pagination metadata는 기존 형식을 유지한다.

보존 조건:

- `total`, `page`, `page_size`, `has_next` 계산식 변경 없음
- invalid row를 임의 날짜로 보정하지 않음
- count query와 pagination 재설계 없음

### FIX-03. 3-day·Weekly detail의 period 오류를 구조화된 500으로 변환

대상:

- `app/routers/three_day_topics.py`
- `app/routers/weekly_topics.py`

판정: 승인

승인 이유:

- CodeRabbit은 Weekly detail의 unhandled `ValueError`를 지적했다.
- 3-day detail에도 동일한 위험이 있으므로 대칭적으로 처리해야 한다.
- 해당 Topic row는 존재하므로 404가 아니라 내부 데이터 정합성 오류를 나타내는 500이 적절하다.

승인 변경:

- period 변환을 try/except로 감싼다.
- `ValueError`를 고정된 detail message의 `HTTPException(status_code=500)`으로 변환한다.
- 내부 log에는 topic type과 row ID만 기록한다.

보존 조건:

- 내부 exception 문자열을 response에 노출하지 않음
- title, window metadata와 credential을 response/log에 노출하지 않음
- 정상 detail response field 변경 없음

### FIX-04. Invalid metadata API 경계 테스트 추가

대상:

- `tests/test_three_day_topics_api.py`
- `tests/test_weekly_topics_api.py`
- `tests/test_home_cache_integration.py` 또는 Home payload 관련 테스트

판정: 승인

승인 이유:

- 현재 period utility의 invalid 입력 거부는 테스트하지만, router와 Home payload가 예외를 안전하게 처리하는지는 보장하지 않는다.
- 이번 수정은 오류 경계의 동작 변경이므로 테스트 없이 반영하면 같은 회귀가 재발할 수 있다.

승인 테스트:

- Home valid+invalid 혼합 row에서 valid item 유지
- Archive list valid+invalid 혼합 row에서 valid item 유지
- Detail invalid metadata에서 명시적 500
- 3-day·Weekly 양쪽 대칭 검증
- 정상 response와 기존 field 회귀 검증

### FIX-05. Review·Approved Fixes 문서와 PR 상태 정합화

대상:

- `docs/reviews/fix-topic-summary-title-period-consistency-coderabbit.md`
- `docs/fixes/fix-topic-summary-title-period-consistency-approved-fixes.md`
- 필요 시 `docs/pr/fix-topic-summary-title-period-consistency.md`

판정: 승인

승인 이유:

- Repository의 review/fix artifact는 실제 CodeRabbit finding과 승인 결정을 반영해야 한다.
- 수정 전에는 `Applied Changes`를 미적용 상태로 두고, 적용 후 실제 diff와 테스트 결과로 갱신해야 한다.

## Rejected or Deferred Suggestions

### 1. Period validator를 완화하거나 `ValueError`를 제거

판정: 거절

validator는 저장된 Pipeline metadata가 기존 계약과 일치하는지 확인하는 핵심 장치다. availability 문제는 API 경계에서 처리하고 검증 자체는 유지한다.

### 2. Invalid period를 `created_at`이나 title에서 재구성

판정: 거절

이번 Task에서 날짜·기간은 LLM title에서 역산하지 않기로 고정했다. `created_at`은 insert 시각이며 period의 authoritative source가 아니다. 잘못된 metadata를 임의 값으로 숨기지 않는다.

### 3. DB schema 변경·migration·기존 row update

판정: 거절

Production analyzer 결과 period 계산 실패와 invalid period는 0건이었다. 현재 데이터 복구나 DB 변경은 필요하지 않다. 이번 수정은 API availability 방어에 한정한다.

### 4. 전역 exception handler 도입

판정: 보류

FastAPI 전역에서 모든 `ValueError`를 처리하면 unrelated validation error까지 같은 응답으로 변환될 수 있다. 이번 PR에서는 period serialization call site만 명시적으로 처리한다.

### 5. List/Home 전체를 명시적 500으로 실패

판정: 거절

여러 row 중 일부가 유효한 경우 정상 결과까지 차단할 이유가 없다. list와 Home은 invalid row를 skip하고 warning을 남긴다. 단일 detail만 구조화된 500으로 처리한다.

### 6. Invalid row 발견 시 자동 DB 수정 또는 Pipeline 재실행

판정: 거절

API read 요청이 Production write를 유발해서는 안 된다. DB 수정, Pipeline 실행, CronJob 수동 실행은 별도 human-controlled incident 대응 범위다.

### 7. CodeRabbit Finishing Touches의 stacked PR·자동 unit-test 생성

판정: 거절

현재 branch에서 최소 수정과 targeted test를 직접 반영하는 것으로 충분하다. 별도 stacked PR이나 자동 생성 테스트가 필요하지 않다.

### 8. Pagination count 재계산

판정: 보류

invalid row를 skip하면 `total`과 현재 `items` 수가 다를 수 있다. 이를 해결하려면 SQL 단계에서 period 계약을 표현하거나 count query를 변경해야 하므로 이번 최종 정합성 PR 범위를 넘는다. 현재는 warning과 row skip으로 제한한다.

## Applied Changes

현재 상태: FIX-01~05 적용 및 로컬 검증 완료

적용 완료:

- FIX-01
  - `app/home_topics_payload.py`의 3-day·Weekly Home 변환을 row별 처리로 변경했다.
  - Invalid period row는 topic type과 row ID만 warning으로 남기고 제외한다.
  - 첫 valid row가 top-level metadata를 제공하며 전부 invalid면 기존 빈 payload를
    유지한다.
  - 3-day·Weekly 혼합 row와 전부 invalid row 테스트를 추가했다.
  - 검증: `27 passed, 4 subtests passed in 0.43s`
- FIX-02
  - 3-day·Weekly archive list가 row별 period 변환을 수행하도록 변경했다.
  - Invalid row는 topic type과 row ID만 warning으로 남기고 현재 page에서 제외한다.
  - `total`, `page`, `page_size`, `has_next`는 기존 count query 계약을 유지한다.
  - 검증: `29 passed, 4 subtests passed in 0.30s`
- FIX-03
  - 3-day·Weekly detail의 invalid period `ValueError`를 고정 detail의 HTTP 500으로
    변환했다.
  - 내부 warning에는 topic type과 row ID만 남기고 원인 문자열과 metadata는
    노출하지 않는다.
  - 검증: 첫 실행의 테스트 배치 결함을 수정한 뒤
    `31 passed, 4 subtests passed in 0.29s`
- FIX-04
  - 3-day·Weekly Home valid+invalid 혼합 row, 전부 invalid row, archive list 혼합
    row와 detail HTTP 500 경계를 대칭 테스트로 고정했다.
  - 정상 period field, 기존 response field, pagination과 cache 회귀도 함께
    검증했다.
  - 검증: `40 passed, 14 subtests passed in 0.31s`
- FIX-05
  - CodeRabbit review에 실제 finding의 적용 상태와 검증 결과를 기록했다.
  - PR 초안의 변경 내용과 테스트 결과를 현재 diff에 맞게 갱신했다.
  - Approved Fixes의 Applied Changes를 실제 변경 파일과 결과에 맞게 정리했다.
  - CodeRabbit thread resolve는 commit·CI 확인 후 사람 작업으로 유지했다.

적용 대기:

- 없음. CodeRabbit thread 확인·resolve는 commit·CI 이후 사람 작업이다.

최종 검증:

- API·Home targeted: `40 passed, 14 subtests passed in 0.31s`
- Topic Summary targeted: `188 passed, 68 subtests passed in 0.43s`
- 전체 Backend: `479 passed, 122 subtests passed in 14.47s`
- Python compile, `git diff --check`, 변경 문서 whitespace: passed
- 새 diff의 connection URI, credential, private key value pattern: match 없음
- DB migration, dependency, K3s manifest diff: 없음
- Production mutation, Pipeline·CronJob 실행, Redis flush, rollout, merge와 thread
  resolve: 수행하지 않음

## Verification Required

### 1. Targeted API·Home 회귀

```bash
PYTHONPATH=. pytest -q \
  tests/test_topic_period.py \
  tests/test_three_day_topics_api.py \
  tests/test_weekly_topics_api.py \
  tests/test_home_cache_integration.py
```

완료 기준:

- invalid Home/list row는 제외되고 valid row는 유지
- invalid detail metadata는 명시적 500
- 정상 3-day·Weekly period field와 기존 response field 유지
- cache miss·재생성 동작 회귀 없음

### 2. Topic Summary 전체 targeted suite

```bash
PYTHONPATH=. pytest -q \
  tests/test_topic_title.py \
  tests/test_topic_period.py \
  tests/test_topic_summary.py \
  tests/test_save_topic_summaries.py \
  tests/test_daily_topic_summary_persistence.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  tests/test_three_day_topics_api.py \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  tests/test_weekly_topics_api.py \
  tests/test_topics_api.py \
  tests/test_home_cache_integration.py \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_analyze_topic_title_periods.py
```

### 3. 전체 Backend 회귀

```bash
PYTHONPATH=. pytest -q
```

### 4. Static·whitespace 검사

```bash
python -m compileall -q \
  app/home_topics_payload.py \
  app/routers/three_day_topics.py \
  app/routers/weekly_topics.py \
  tests/test_three_day_topics_api.py \
  tests/test_weekly_topics_api.py \
  tests/test_home_cache_integration.py

git diff --check
```

### 5. 변경 범위 확인

```bash
git status --short
git diff --stat
git diff --name-only

git diff --name-only -- \
  db/migrations \
  requirements.txt \
  k8s
```

완료 기준:

- DB migration, dependency, K3s manifest 변경 없음
- 승인된 API boundary, 테스트와 review/fix 문서 범위만 변경

### 6. 기존 Production evidence 유지

기존 사람 주도 read-only analyzer 결과를 재사용한다.

```
period calculation failure = 0
invalid period = 0
residual date pattern = 0
unhandled sanitize failure = 0
DB write performed = false
```

이번 수정은 DB data를 변경하지 않으므로 Production analyzer 재실행은 필수가 아니다.

### 7. 민감정보·Production 작업 금지 확인

확인 사항:

- `DATABASE_URL`, Secret value, title 원문과 window 값이 diff·log evidence에 없음
- DB migration과 기존 row update 없음
- Pipeline·CronJob 수동 실행 없음
- Redis flush 없음
- K3s manifest·Secret 변경 없음
- Agent의 Production rollout, merge와 thread resolve 없음

### 8. CodeRabbit thread 확인

수정 커밋과 CI 결과를 확인한 뒤 PR #66의 unresolved inline thread를 사람이 resolve한다. thread를 resolve하기 전에 현재 branch에 승인 변경과 테스트가 실제 반영됐는지 확인한다.
