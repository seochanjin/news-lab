# Approved Fixes: Daily Topic Pipeline 연계 Home Cache Prewarming 및 TTL 정책 정합화

## Approved Fixes

Claude Code 독립 리뷰 결과는 `APPROVE WITH MINOR FIXES`다. Blocker와 Major는 없으며, 현재 브랜치를 막을 수준의 기능 결함이나 외부 API 계약 위반은 발견되지 않았다. 아래 항목만 현재 브랜치에서 반영한다.

### FIX-01: 3-day router의 미사용 상수 제거

- 대상: `app/routers/three_day_topics.py`
- `HOME_TOPICS_LIMIT = 10`은 Home payload 생성 책임이 공통 module로 이동한 뒤 사용되지 않는다.
- 해당 상수를 제거해 실제 limit 정의 위치가 `app/home_topics_payload.py`임을 명확히 한다.
- 동작 변경과 별도 테스트 추가는 필요하지 않다.

### FIX-02: Weekly CronJob TTL의 API manifest 교차 검증 추가

- 대상: `tests/test_weekly_topic_pipeline_cronjob_manifest.py`
- Weekly CronJob의 `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS`가 단순히 `691200`인지 확인하는 것에 더해, API Deployment의 같은 환경변수 값과 일치하는지 검증한다.
- 3-day manifest test와 동일한 검증 패턴을 사용한다.
- Production manifest 값 자체는 변경하지 않는다.

### FIX-03: 3-day와 Weekly prewarm의 Redis SET 실패 회귀 테스트 추가

- 대상:
  - `tests/test_run_three_day_topic_pipeline.py`
  - `tests/test_run_weekly_topic_pipeline.py`
- Daily Pipeline의 기존 실패 client 테스트 패턴을 참고한다.
- 최소한 다음 Redis SET 계층 실패를 직접 검증한다.
  - connection error
  - timeout
  - SET/SETEX error
- Redis 오류가 성공한 Pipeline 결과를 실패로 바꾸지 않는지 확인한다.
- warning 로그에 credential 또는 전체 `REDIS_URL`이 포함되지 않는지 확인한다.
- 테스트를 위해 Production 코드를 불필요하게 변경하지 않는다.

### FIX-04: 3-day API 테스트 fixture의 실제 저장 상태 정합화

- 대상: `tests/test_three_day_topics_api.py`
- `three_day_topic_row()` fixture의 `status="ready"`를 실제 3-day Pipeline 저장 상태인 `status="draft"`로 변경한다.
- Home query가 Topic status를 필터하지 않는 현재 외부 동작은 변경하지 않는다.
- 테스트 fixture와 실제 저장 모델의 의미만 정합화한다.

### FIX-05: 잘못된 `REDIS_URL`의 cache 비활성화 경로 테스트 추가

- 대상은 현재 Cache factory 테스트 구조를 조사한 뒤 결정한다.
- malformed 또는 unsupported `REDIS_URL`이 애플리케이션과 Pipeline을 실패시키지 않고 Cache disabled 상태로 처리되는지 한 개의 집중 테스트로 검증한다.
- 동일 경로를 이미 충분히 검증하는 테스트가 존재하면 중복 추가하지 않고 Verification에 근거를 기록한다.

## Rejected or Deferred Suggestions

### DEFER-01: `next(iter(PUBLISHABLE_TOPIC_STATUSES))`를 즉시 `IN` query로 변경

- 현재 `PUBLISHABLE_TOPIC_STATUSES`는 `frozenset({"ready"})`로 단일 상태만 가진다.
- 현재 동작 결함은 없으며, 다중 publishable status 요구사항도 없다.
- 지금 `IN` query 또는 별도 동적 bind 구성을 추가하면 현재 Task 범위를 넘어선다.
- 추후 publishable status가 2개 이상으로 확장될 때 SQL과 테스트를 함께 변경한다.
- 현재 브랜치에는 assert도 추가하지 않는다. module import 시점의 강제 실패보다 실제 요구사항 변경 시 명시적으로 구현하는 편을 우선한다.

### DEFER-02: Production DB의 3-day status 조회

- `SELECT DISTINCT status FROM three_day_topics` 확인은 코드 수정이 아니라 운영 검증 항목이다.
- 운영 DB 조회는 사람 승인 후 필요한 경우 별도로 수행한다.
- 이번 로컬 Fix 적용의 완료 조건에는 포함하지 않는다.

### DEFER-03: Redis 주소 변경 시 `lru_cache` 초기화 자동화

- 현재 Deployment 환경변수 변경은 Pod 재기동을 수반하므로 실제 운영 결함으로 확인되지 않았다.
- runtime에서 Redis 설정을 동적으로 바꾸는 요구사항이 없으므로 Cache factory 구조는 유지한다.
- Pod 재기동 필요 사항은 Runbook 또는 운영 검증에서만 확인한다.

### REJECT-01: 별도 기능 PR로 분리

- 승인한 수정은 모두 현재 Home Cache 구현의 dead code, manifest test와 fail-open 회귀 테스트 보완이다.
- 변경량이 작고 현재 Task의 검증 신뢰도를 직접 높이므로 같은 브랜치에서 반영한다.

## Applied Changes

- [x] FIX-01: `app/routers/three_day_topics.py`에서 payload 공통화 뒤 남은
  미사용 `HOME_TOPICS_LIMIT` 상수를 제거했다. 실제 limit 정의는
  `app/home_topics_payload.py`에만 유지된다.
- [x] FIX-02: `tests/test_weekly_topic_pipeline_cronjob_manifest.py`에서 Weekly
  CronJob TTL `691200`을 확인하고 API Deployment의 같은 환경변수 값과도
  일치하는지 교차 검증한다. Production manifest 값은 변경하지 않았다.
- [x] FIX-03: `tests/test_run_three_day_topic_pipeline.py`와
  `tests/test_run_weekly_topic_pipeline.py`에 Redis connection, timeout과 SETEX
  실패의 fail-open 회귀 테스트를 추가했다. Pipeline 성공 흐름이 예외로 바뀌지
  않고 warning 로그에 credential과 전체 `REDIS_URL`이 포함되지 않음을 검증한다.
- [x] FIX-04: `tests/test_three_day_topics_api.py`의 공통 fixture status를 실제
  3-day Pipeline 저장 상태인 `draft`로 변경했다. Home query와 외부 동작은
  변경하지 않았다.
- [x] FIX-05: `tests/test_topics_api.py`의 기존 malformed 및 unsupported
  `REDIS_URL` 테스트가 cache disabled 상태, PostgreSQL fallback과 애플리케이션
  예외 미전파를 이미 검증함을 확인했다. 중복 테스트는 추가하지 않았다.

새로운 기능, API, DB schema, Pipeline schedule, Redis key 또는 TTL은 변경하지
않는다.

`DEFER-01`부터 `DEFER-03`, `REJECT-01`과 그 밖의 승인되지 않은 review suggestion은
적용하지 않았다.

## Verification Required

### Targeted tests

```bash
PYTHONPATH=. pytest -q \
  tests/test_three_day_topics_api.py \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Cache factory 테스트 파일을 확인한 뒤 malformed `REDIS_URL` 관련 테스트도 함께 실행한다.

### Home Cache 관련 선택 테스트

```bash
PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"
```

### 전체 테스트

```bash
PYTHONPATH=. pytest -q
```

### Kubernetes YAML parse

```bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

### 정적 및 범위 검증

```bash
git diff --check
```

```bash
git diff --name-only -- db migrations frontend
```

기대 결과: DB migration과 Frontend 변경 없음.

### 문서 확인

- `docs/pr/feat-home-cache-prewarm.md`와 `docs/devlog/feat-home-cache-prewarm.md`가 Daily·3-day·Weekly 최종 범위를 반영하는지 읽기 전용으로 확인한다.
- 운영 검증을 실행하지 않았으면 `passed` 근거에 운영 결과를 포함하지 않는다.
- Verification에는 승인된 Fix의 적용 파일, targeted test, 전체 test와 정적 검증 결과만 추가한다.
