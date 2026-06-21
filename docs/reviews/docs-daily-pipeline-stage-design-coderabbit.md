# CodeRabbit Review: Daily topic pipeline 분리 설계

## Review Summary

CodeRabbit 리뷰에서 `resolve_pipeline_context()`가 timezone 정보가 없는 naive `started_at_utc`를 UTC로 자동 해석하는 문제가 발견됐다.

현재 구현:

```python
if started_at_utc.tzinfo is None:
    started_at_utc = started_at_utc.replace(tzinfo=timezone.utc)
```

이 처리는 입력값이 실제 UTC라는 사실을 검증하지 않고 timezone 정보만 덧붙인다.

호출자가 Asia/Seoul 로컬 시각을 naive `datetime`으로 전달한 경우에도 오류가 발생하지 않으며, 잘못된 UTC 시각으로 해석되어 `pipeline_date`와 최종 `topics.topic_date`가 달라질 수 있다.

이번 작업은 UTC/KST 날짜 경계 문제를 수정하고 하나의 공통 `pipeline_date`를 사용하도록 만드는 작업이므로, 해당 입력은 암묵적으로 보정하지 않고 명시적으로 검증해야 한다.

---

## Problems Found

### 1. Naive `started_at_utc`를 UTC로 조용히 해석함

대상:

```text
app/services/daily_topic_pipeline/context.py
```

문제 코드:

```python
if started_at_utc.tzinfo is None:
    started_at_utc = started_at_utc.replace(tzinfo=timezone.utc)
```

`datetime.replace(tzinfo=timezone.utc)`는 시각을 UTC로 변환하지 않는다.

기존 wall-clock 값을 그대로 유지한 채 UTC라는 의미만 부여한다.

예를 들어 호출자가 다음 값을 Asia/Seoul 로컬 시각 의미로 전달할 수 있다.

```text
2026-06-21 04:00:00
```

현재 구현은 이를 다음으로 해석한다.

```text
2026-06-21 04:00:00 UTC
```

그러나 실제 의도가 KST였다면 올바른 UTC instant는 다음이다.

```text
2026-06-20 19:00:00 UTC
```

두 값은 9시간 차이가 나며, 날짜 경계 부근에서는 다음 데이터가 잘못될 수 있다.

- `started_at_utc`
- `started_at_local`
- `pipeline_date`
- `save_plan.topic_date`
- `topics.topic_date`

이 값은 최종 DB에 저장되므로 데이터 정합성 위험이 있다.

심각도:

```text
Major
```

분류:

```text
입력 검증 누락
Timezone 정합성
DB 저장 날짜 오류 가능성
```

---

## Required Fixes Before PR

### 1. Naive datetime 입력 거부

`started_at_utc`는 timezone-aware `datetime`만 허용한다.

권장 구현:

```python
if started_at_utc.tzinfo is None:
    raise ValueError(
        "started_at_utc must be timezone-aware and represent an absolute instant"
    )

started_at_utc = started_at_utc.astimezone(timezone.utc)
```

정확한 예외 타입과 메시지는 프로젝트의 기존 validation 규칙에 맞게 조정할 수 있다.

요구사항:

- naive `datetime`에 UTC를 자동 부착하지 않는다.
- timezone-aware 입력만 허용한다.
- UTC가 아닌 aware 입력은 UTC로 정규화한다.
- 입력 오류는 pipeline context 생성 시점에서 fail-fast 처리한다.
- 잘못된 context로 후속 stage 또는 topic 저장을 실행하지 않는다.

### 2. Timezone 입력 테스트 추가

최소 다음 테스트를 추가한다.

#### Naive 입력 거부

```python
started_at_utc = datetime(2026, 6, 21, 4, 0, 0)
```

예상 결과:

```text
ValueError 또는 프로젝트에서 정의한 validation exception
```

#### UTC 입력 정상 처리

```python
started_at_utc = datetime(
    2026,
    6,
    20,
    19,
    0,
    0,
    tzinfo=timezone.utc,
)
```

예상 결과:

```text
pipeline_date = 2026-06-21
business_timezone = Asia/Seoul
```

#### UTC 외 aware 입력 정규화

예:

```python
started_at = datetime(
    2026,
    6,
    21,
    4,
    0,
    0,
    tzinfo=ZoneInfo("Asia/Seoul"),
)
```

예상 결과:

```text
started_at_utc = 2026-06-20 19:00:00+00:00
pipeline_date = 2026-06-21
```

#### 후속 저장 차단

잘못된 naive 입력이 전달되면 다음 작업이 실행되지 않아야 한다.

- embedding 단계
- clustering 단계
- raw acquisition 단계
- summary provider 호출
- topic 저장

---

## Optional Improvements

### 1. 인자 이름 또는 타입 계약 강화

`started_at_utc`라는 이름만으로 UTC 입력을 기대하고 있지만 Python `datetime` 타입 자체는 timezone-aware 여부를 강제하지 않는다.

다음 방법을 후속으로 검토할 수 있다.

- 함수 docstring에 timezone-aware 필수 계약 명시
- 별도의 UTC datetime validation helper 사용
- type checker용 aware datetime 타입 도입
- CLI 또는 외부 입력 단계에서 UTC 변환 완료 후 context 함수 호출

이번 PR에서는 명시적 runtime validation과 테스트 추가만으로 충분하다.

### 2. 날짜 입력 함수의 단일 진입점 유지

`pipeline_date`와 관련된 datetime 정규화가 다른 stage나 helper에 중복되지 않도록 `resolve_pipeline_context()`를 단일 진입점으로 유지한다.

각 stage에서는 전달받은 `PipelineContext.pipeline_date`만 사용한다.

---

## Suggested Test Commands

관련 pipeline 테스트:

```bash
python -m unittest tests.test_run_daily_topic_pipeline
```

관련 회귀 테스트:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

전체 회귀:

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
```

Import 및 diff 확인:

```bash
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
git diff --check
git status --short --branch
```

변경 금지 영역:

```bash
git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  requirements.txt
```

---

## Risk Notes

- 이 문제는 예외나 장애를 즉시 발생시키지 않고 정상 실행처럼 보일 수 있다.
- 잘못 계산된 날짜가 DB에 저장된 뒤에야 발견될 가능성이 있다.
- 특히 UTC와 Asia/Seoul의 날짜가 달라지는 00:00~08:59 KST 실행에서 영향이 크다.
- 현재 Daily topic pipeline은 04:00 Asia/Seoul에 실행되므로 날짜 경계 영향을 직접 받을 수 있다.
- naive 입력을 허용해야 하는 기존 호출자가 있다면 수정 후 즉시 실패할 수 있으므로 전체 호출 위치를 검색해야 한다.

호출 위치 확인:

```bash
rg -n "resolve_pipeline_context|started_at_utc" app scripts tests
```

모든 호출자가 timezone-aware 값을 전달하는지 확인해야 한다.

---

## Verdict

```text
CHANGES REQUESTED
```

Naive `started_at_utc`를 UTC로 자동 해석하는 동작은 잘못된 `pipeline_date`와 `topic_date`를 저장할 수 있다.

PR 전 다음 수정이 필요하다.

- naive datetime 입력 거부
- timezone-aware 입력의 UTC 정규화
- 날짜 경계 및 잘못된 입력 테스트 추가
- 후속 stage와 DB 저장 차단 확인
