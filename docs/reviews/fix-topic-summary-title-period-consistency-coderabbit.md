# CodeRabbit Review: Topic Summary 제목·기간 정합성 수정

## Review Summary

PR #66에 대해 CodeRabbit은 **actionable comment 1개**를 남겼다. 등급은 `Major`, 작업 규모는 `Heavy lift`로 분류됐다.

핵심 finding은 3-day·Weekly period 계산 함수가 저장 metadata 불일치 시 `ValueError`를 발생시키도록 설계됐지만, API와 Home payload 경계에서 이를 처리하지 않아 **단일 비정상 row가 전체 endpoint의 500 오류로 확장될 수 있다**는 것이다.

현재 사람이 수행한 Production read-only analyzer에서는 3-day 132건과 Weekly 20건의 period 계산이 모두 성공했으므로 현재 데이터 손상이 확인된 것은 아니다. 하지만 새 코드가 기존 `dict(row)` 직렬화 경로를 검증 함수 호출로 대체하면서, 향후 잘못된 metadata가 유입될 경우 availability가 낮아지는 회귀 가능성이 생겼다.

CodeRabbit이 직접 지적한 call site는 다음 4곳이다.

- `app/home_topics_payload.py`: 3-day Home payload 생성
- `app/home_topics_payload.py`: Weekly Home payload 생성
- `app/routers/weekly_topics.py`: Weekly archive list
- `app/routers/weekly_topics.py`: Weekly detail

추가 검토 결과, 동일한 `ValueError`가 발생할 수 있는 대칭 경로가 다음 2곳 더 존재한다.

- `app/routers/three_day_topics.py`: 3-day archive list
- `app/routers/three_day_topics.py`: 3-day detail

따라서 핵심 finding은 유효하며, 수정은 DB나 period 계약을 완화하는 방식이 아니라 **응답 경계에서 오류를 명시적으로 처리하는 최소 변경**으로 진행하는 것이 적절하다.

## Fix Application Status

- FIX-01~04의 승인 코드·테스트 변경을 현재 branch에 적용했다.
- 3-day·Weekly Home/list는 invalid period row만 warning 후 제외하고 valid row를
  유지한다. Detail은 내부 값을 노출하지 않는 고정 detail의 HTTP 500을 반환한다.
- Warning에는 topic type과 row ID만 포함하고 title, window와 exception 원문은
  기록하지 않는다.
- Targeted API·Home 회귀: `40 passed, 14 subtests passed in 0.31s`
- Topic Summary 전체 targeted suite:
  `188 passed, 68 subtests passed in 0.43s`
- 전체 Backend 회귀: `479 passed, 122 subtests passed in 14.47s`
- DB migration, dependency와 K3s manifest 변경은 없다.
- Production mutation, rollout, merge와 CodeRabbit thread resolve는 수행하지 않았다.
  Thread 상태 확인과 resolve는 수정 commit·CI 확인 후 사람이 수행해야 한다.

## Problems Found

### 1. Home payload에서 비정상 period row 하나가 전체 Home API를 실패시킬 수 있음

대상:

- `app/home_topics_payload.py`
- `fetch_three_day_home_topics_from_database()`
- `fetch_weekly_home_topics_from_database()`

현재 동작:

```python
items = [
    with_three_day_topic_period(with_sanitized_topic_title(row))
    for row in rows
]
```

또는 Weekly equivalent를 사용한다.

문제:

- `with_three_day_topic_period()`와 `with_weekly_topic_period()`는 window duration, timezone, 기준 날짜가 계약과 다르면 `ValueError`를 발생시킨다.
- list comprehension 내부에서 예외가 발생하면 정상 row가 함께 있어도 Home payload 전체가 실패한다.
- Home cache miss 또는 stale cache 재생성 시 DB fallback 경로가 500으로 종료될 수 있다.

영향:

- 단일 비정상 row가 `/three-day-topics/home` 또는 `/weekly-topics/home` 전체 장애로 확대될 수 있다.
- 기존 Home cache가 무효화된 직후 문제가 노출될 가능성이 있다.

수정 방향:

- row별로 period 계산을 시도한다.
- `ValueError`가 발생한 row는 warning log를 남기고 제외한다.
- log에는 dataset과 row ID만 포함하고 title, window 값, credential은 기록하지 않는다.
- 유효한 row는 정상 반환한다.

### 2. Archive list에서 비정상 row 하나가 전체 페이지를 실패시킬 수 있음

대상:

- CodeRabbit 직접 지적: `app/routers/weekly_topics.py`
- 동일 위험 확인: `app/routers/three_day_topics.py`

현재 동작:

```python
"items": [
    with_weekly_topic_period(with_sanitized_topic_title(row))
    for row in rows
]
```

문제:

- 한 row의 metadata가 계약을 위반하면 해당 페이지의 정상 row까지 반환하지 못한다.
- archive endpoint는 여러 row를 반환하므로 하나의 데이터 품질 문제를 전체 요청 실패로 확장할 필요가 없다.

수정 방향:

- 3-day·Weekly list 모두 row별 try/except를 적용한다.
- 비정상 row는 warning log 후 제외한다.
- pagination의 `total`은 DB 전체 건수를 유지하므로 `items` 수가 `page_size`보다 작을 수 있음을 테스트와 문서에서 허용한다.

### 3. Detail endpoint에서 period 불일치가 구조화되지 않은 500으로 노출됨

대상:

- CodeRabbit 직접 지적: `app/routers/weekly_topics.py`
- 동일 위험 확인: `app/routers/three_day_topics.py`

현재 동작:

```python
topic = with_weekly_topic_period(with_sanitized_topic_title(row))
```

문제:

- `ValueError`가 그대로 전파되어 framework 기본 500으로 처리된다.
- 장애 원인이 DB 조회 실패인지, period metadata 불일치인지 API 계약상 구분되지 않는다.

수정 방향:

- detail에서는 row를 건너뛸 수 없으므로 `ValueError`를 잡는다.
- 명확하고 고정된 `HTTPException(status_code=500, detail="Topic period data inconsistent")` 형태로 변환한다.
- 내부 warning/error log에는 topic 종류와 row ID만 남긴다.

### 4. 현재 테스트는 invalid metadata가 API 경계에서 어떻게 처리되는지 보장하지 않음

대상:

- `tests/test_three_day_topics_api.py`
- `tests/test_weekly_topics_api.py`
- `tests/test_home_cache_integration.py` 또는 Home payload 관련 테스트

현재 상태:

- period 계산 함수 자체의 invalid metadata 거부는 검증한다.
- 정상 list/detail/Home 응답과 cache 하위 호환도 검증한다.
- 그러나 invalid row가 섞였을 때 list/Home이 정상 row를 유지하고 detail이 명시적 500을 반환하는지는 검증하지 않는다.

수정 방향:

- Home: invalid row를 제외하고 valid row를 반환하는 테스트
- List: invalid row를 제외하고 valid row를 반환하는 테스트
- Detail: invalid metadata를 명시적 500으로 변환하는 테스트
- 3-day와 Weekly 양쪽에 대칭 테스트 추가

## Required Fixes Before PR

### FIX-01. 3-day·Weekly Home payload를 row 단위로 안전하게 직렬화

파일:

- `app/home_topics_payload.py`

필수 변경:

- 두 Home payload 함수의 list comprehension을 명시적 loop로 변경
- period 계산 `ValueError`를 row별로 catch
- invalid row는 warning log 후 skip
- 정상 row와 기존 top-level period field 계약 유지

완료 기준:

- invalid row 하나가 있어도 valid Home item은 반환됨
- 모든 row가 invalid여도 구조화된 empty payload를 반환하고 unhandled exception이 발생하지 않음
- title, window 원문, credential을 log하지 않음

### FIX-02. 3-day·Weekly archive list의 invalid row 격리

파일:

- `app/routers/three_day_topics.py`
- `app/routers/weekly_topics.py`

필수 변경:

- period 변환을 row별로 수행
- `ValueError` 발생 row는 warning log 후 제외
- 기존 pagination field와 기존 response field 유지

완료 기준:

- invalid row가 포함돼도 endpoint status는 200
- valid row는 정상 반환
- invalid row는 응답에서 제외

### FIX-03. 3-day·Weekly detail의 period 불일치를 명시적 HTTP 500으로 변환

파일:

- `app/routers/three_day_topics.py`
- `app/routers/weekly_topics.py`

필수 변경:

- 단일 row period 변환을 try/except로 감싼다.
- `ValueError`를 안정적인 `HTTPException(status_code=500)`으로 변환한다.
- detail message에는 credential, title, window 값과 내부 exception 문자열을 포함하지 않는다.

완료 기준:

- invalid metadata detail 요청이 구조화된 500 response를 반환
- 정상 detail 응답은 기존 field와 period field를 유지

### FIX-04. invalid metadata 경계 테스트 추가

파일:

- `tests/test_three_day_topics_api.py`
- `tests/test_weekly_topics_api.py`
- `tests/test_home_cache_integration.py` 또는 관련 Home payload 테스트

필수 case:

- 3-day Home valid+invalid 혼합 row
- Weekly Home valid+invalid 혼합 row
- 3-day list valid+invalid 혼합 row
- Weekly list valid+invalid 혼합 row
- 3-day detail invalid metadata → 명시적 500
- Weekly detail invalid metadata → 명시적 500

### FIX-05. Review·Approved Fixes artifact 갱신

파일:

- `docs/reviews/fix-topic-summary-title-period-consistency-coderabbit.md`
- `docs/fixes/fix-topic-summary-title-period-consistency-approved-fixes.md`

필수 변경:

- PR #66의 실제 actionable finding과 승인 범위를 지정 format에 맞게 기록
- 수정 전에는 `Applied Changes`를 미적용 상태로 유지
- 수정 후 실제 변경 파일과 검증 결과로 갱신

## Optional Improvements

### 1. 공통 safe serialization helper 도입

3-day·Weekly, Home·router에서 비슷한 try/except가 반복될 수 있다. 다만 이번 PR은 최종 정합성 수정이므로 별도 abstraction이 코드량을 줄이는 것이 명확할 때만 적용한다. 새로운 framework-level abstraction이나 전역 exception 정책으로 확대하지 않는다.

### 2. 구조화된 log event 명칭 통일

예:

```
period_serialization event=skip_invalid_period topic_type=weekly topic_id=<id>
```

운영자가 로그에서 원인을 구분하는 데 도움이 된다. 단, title, window metadata와 exception 원문은 기록하지 않는다.

### 3. CodeRabbit thread resolve

수정 커밋과 테스트 결과를 확인한 뒤 PR #66의 unresolved inline thread를 resolve한다.

### 4. CodeRabbit Finishing Touches 자동 생성 기능은 사용하지 않음

자동 unit-test 생성이나 stacked PR 생성은 일반 제안이다. 이번 finding은 직접 targeted test를 추가하는 것으로 충분하다.

## Suggested Test Commands

### Targeted regression

```bash
PYTHONPATH=. pytest -q \
  tests/test_topic_period.py \
  tests/test_three_day_topics_api.py \
  tests/test_weekly_topics_api.py \
  tests/test_home_cache_integration.py
```

### 기존 Topic Summary 관련 suite

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

### 전체 Backend 회귀

```bash
PYTHONPATH=. pytest -q
```

### 변경 범위와 금지 영역 확인

```bash
git diff --check
git status --short
git diff --stat
git diff --name-only

git diff --name-only -- \
  db/migrations \
  requirements.txt \
  k8s
```

기대 결과:

- DB migration, dependency, K3s manifest 변경 없음
- Topic period API 경계, 관련 테스트와 review/fix 문서만 변경

## Risk Notes

- validator에서 `ValueError`를 제거하거나 검증 조건을 완화하지 않는다. 저장 metadata 불일치를 감지하는 계약은 유지해야 한다.
- invalid period를 `created_at`, title 문자열 또는 임의 기본 날짜로 보정하지 않는다.
- list/Home에서는 availability를 위해 invalid row를 제외하되, warning log로 관찰 가능성을 유지한다.
- detail에서는 다른 row로 대체하거나 404로 위장하지 않는다. 저장된 row는 존재하지만 period metadata가 불일치하므로 명시적 500이 적절하다.
- row skip으로 인해 `total`과 현재 page의 `items` 길이가 일치하지 않을 수 있다. 이번 수정에서 count query나 pagination 구조를 재설계하지 않는다.
- 현재 Production analyzer에서 invalid period가 0건이었다는 evidence는 유지한다. 이 수정은 현재 데이터 복구가 아니라 방어적 availability 보강이다.
- DB schema·data migration, 기존 row update, Pipeline 재실행, CronJob 변경, Redis flush, Secret 변경과 Production mutation은 수행하지 않는다.
- CodeRabbit의 finding은 Weekly 중심으로 제시됐지만 동일한 예외 경로가 있는 3-day list/detail도 대칭적으로 처리해야 일관된 API 계약을 유지할 수 있다.
