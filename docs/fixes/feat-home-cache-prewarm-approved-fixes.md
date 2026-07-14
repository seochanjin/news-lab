# Approved Fixes: Daily Topic Pipeline 연계 Home Cache Prewarming 및 TTL 정책 정합화

## Approved Fixes

이 문서는 두 차례의 독립 리뷰 결과를 기준으로 현재 브랜치에서 반영할 수정 범위를 확정한다.

- Claude Code 독립 리뷰: `APPROVE WITH MINOR FIXES`
- CodeRabbit PR 리뷰: `COMMENTED`
- Blocker와 Major 결함 없음
- 외부 API 계약, Cache key/TTL, Pipeline transaction 이후 prewarm과 fail-open의 핵심 구현은 정상
- Merge 전에는 아래 승인 항목만 반영하고, 리팩터링성 제안은 범위 밖으로 유지한다.

### Claude Code 승인 Fix

#### FIX-01: 3-day router의 미사용 상수 제거

- 대상: `app/routers/three_day_topics.py`
- 사용되지 않는 `HOME_TOPICS_LIMIT = 10`을 제거한다.
- 실제 Home limit 정의는 `app/home_topics_payload.py`에만 유지한다.
- 동작 변경과 별도 테스트 추가는 필요하지 않다.

#### FIX-02: Weekly CronJob TTL의 API manifest 교차 검증 추가

- 대상: `tests/test_weekly_topic_pipeline_cronjob_manifest.py`
- Weekly CronJob의 `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS="691200"`을 확인한다.
- API Deployment의 같은 환경변수 값과도 일치하는지 검증한다.
- Production manifest 값은 변경하지 않는다.

#### FIX-03: 3-day와 Weekly prewarm의 Redis SET 실패 회귀 테스트 추가

- 대상:
  - `tests/test_run_three_day_topic_pipeline.py`
  - `tests/test_run_weekly_topic_pipeline.py`
- Redis connection error, timeout과 SET/SETEX 실패를 직접 검증한다.
- Redis 오류가 성공한 Pipeline을 실패시키지 않는지 확인한다.
- warning 로그에 credential과 전체 `REDIS_URL`이 포함되지 않는지 확인한다.
- 테스트를 위해 Production 코드를 불필요하게 변경하지 않는다.

#### FIX-04: 3-day API 테스트 fixture의 저장 상태 정합화

- 대상: `tests/test_three_day_topics_api.py`
- `three_day_topic_row()` fixture의 `status="ready"`를 실제 저장 상태인 `status="draft"`로 변경한다.
- Home query와 외부 동작은 변경하지 않는다.

#### FIX-05: 잘못된 `REDIS_URL` 경로의 기존 테스트 확인

- `tests/test_topics_api.py`의 기존 malformed 및 unsupported `REDIS_URL` 테스트가 다음을 이미 검증한다.
  - Cache disabled 처리
  - PostgreSQL fallback
  - 애플리케이션 예외 미전파
- 중복 테스트는 추가하지 않는다.
- 추가 조사나 별도 실행이 남은 상태로 기록하지 않는다.

### CodeRabbit 승인 Fix

아래 항목은 기능 코드 변경이 아니라 문서, Runbook과 review artifact 정합성 수정이다. Merge 전에 반영한다.

#### FIX-06: FIX-05 문서 상태를 완료 기준으로 수정

- 대상: `docs/fixes/feat-home-cache-prewarm-approved-fixes.md`
- malformed/unsupported `REDIS_URL` 테스트가 이미 검증됐음을 명시한다.
- “테스트 파일을 확인한 뒤 실행한다”는 미완료 표현을 제거한다.
- 중복 테스트를 추가하지 않았다는 근거를 남긴다.

#### FIX-07: PR Verification을 로컬과 운영으로 명확히 분리

- 대상: `docs/pr/feat-home-cache-prewarm.md`
- 상태를 `local verification passed`로 명시한다.
- 다음 항목은 `pending`, `human-required`로 분리한다.
  - Production rollout
  - Argo CD Manual Sync
  - Redis key와 TTL 확인
  - 운영 Home API 확인
- 운영 검증 미수행 설명은 유지한다.

#### FIX-08: 빈 review artifact 정리

- 대상:
  - `docs/reviews/feat-home-cache-prewarm-coderabbit.md`
  - `docs/reviews/feat-home-cache-prewarm-antigravity.md`
- CodeRabbit 문서에는 실제 리뷰 결과를 기록한다.
  - Review Summary
  - Problems Found
  - Required Fixes
  - Optional Improvements
  - Suggested Tests
  - Risk Notes
- Antigravity 리뷰를 실제로 수행하지 않았다면 빈 heading을 유지하지 않는다.
- Antigravity 문서에는 `not performed`와 사유를 명확히 기록하거나, 프로젝트 문서 규칙상 불필요하면 파일을 제거한다.
- 수행하지 않은 리뷰를 수행한 것으로 기록하지 않는다.

#### FIX-09: Argo CD diff checklist의 API Redis 설정 보완

- 대상: `docs/runbooks/cronjobs.md`
- Deployment `news-api` 예상 diff에 다음을 추가한다.
  - `REDIS_URL`
  - `REDIS_TIMEOUT_SECONDS`
  - `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS="691200"`
- 기존 Daily 및 3-day TTL 확인과 image tag 확인은 유지한다.
- Service, Ingress, Secret, HPA와 schedule은 변경 대상이 아님을 유지한다.

#### FIX-10: 수동 검증 Job 이름을 재실행 가능하게 변경

- 대상: `docs/runbooks/cronjobs.md`
- Daily·3-day·Weekly 수동 Job 이름에 고유한 run identifier를 사용한다.
- 예시:

```bash
RUN_ID=$(date +%Y%m%d%H%M%S)
```

- 생성되는 Job 이름에 `${RUN_ID}`를 포함한다.
- 완료 Job 삭제는 로그와 Redis 검증 결과를 보존한 뒤 사람이 명시적으로 수행하도록 작성한다.
- 동일 이름 재사용으로 발생하는 `AlreadyExists`를 방지한다.

#### FIX-11: Daily no-write 실행의 Cache 검증 조건 수정

- 대상: `docs/runbooks/cronjobs.md`
- Daily Pipeline의 `EXISTS topics:home:v1 = 1`은 `db_write_performed=True`일 때만 필수로 한다.
- dry-run 또는 no-write 정상 실행은 Cache가 생성되지 않아도 실패로 판단하지 않는다.
- status, 로그와 실행 결과 확인 기준은 유지한다.
- 3-day와 Weekly의 saved/publishable 결과 조건과 같은 원칙으로 정합화한다.

#### FIX-12: Task 문서의 최종 테스트 수치 갱신

- 대상: `docs/tasks/feat-home-cache-prewarm.md`
- 현재 최종 결과를 다음으로 갱신한다.
  - `445 passed`
  - `91 subtests passed`
- 과거 `443 passed, 85 subtests passed`를 유지해야 하는 위치는 `historical baseline`이라고 명시한다.
- 최종 결과와 과거 실행 결과가 혼동되지 않게 한다.

#### FIX-13: Verification의 stale snapshot 설명 수정

- 대상: `docs/verification/feat-home-cache-prewarm.md`
- `443 passed, 85 subtests passed`가 남아 있는 실제 문서만 정확히 지목한다.
- 이미 최종 `445 passed, 91 subtests passed`가 기록된 `docs/devlog/feat-home-cache-prewarm.md`를 stale 문서 목록에서 제외한다.
- 최종 검증 결과와 운영 검증 미수행 상태를 그대로 유지한다.

## Rejected or Deferred Suggestions

### DEFER-01: `next(iter(PUBLISHABLE_TOPIC_STATUSES))`를 즉시 `IN` query로 변경

- 현재 publishable status는 `ready` 하나뿐이다.
- 현재 기능 결함은 없다.
- 다중 status 요구사항이 생길 때 SQL과 테스트를 함께 변경한다.
- 이번 브랜치에는 `IN` query 또는 import 시점 assert를 추가하지 않는다.

### DEFER-02: Production DB의 3-day status 조회

- `SELECT DISTINCT status FROM three_day_topics`는 운영 검증 항목이다.
- 사람 승인 후 필요한 경우 별도로 수행한다.
- 로컬 Fix 완료 조건에는 포함하지 않는다.

### DEFER-03: Redis 주소 변경 시 `lru_cache` 초기화 자동화

- Deployment 환경변수 변경은 Pod 재기동을 수반한다.
- runtime에서 Redis 설정을 동적으로 변경하는 요구사항이 없다.
- Cache factory 구조는 유지하고 Pod 재기동 필요 사항만 운영 문서에서 확인한다.

### DEFER-04: Fake Redis test helper 공통화

- 대상 제안:
  - API test의 `FakeRedisClient`
  - 세 Pipeline test의 `FakeRedisSetClient`
- 현재 테스트 동작에는 문제가 없다.
- 공통 fixture 추출은 유지보수성 리팩터링이며 이번 PR 완료 조건이 아니다.
- 별도 테스트 정리 작업에서 처리한다.

### DEFER-05: Payload validator 공통 helper 추출

- 대상: `app/home_topics_cache.py`
- 세 validator의 중복은 존재하지만 현재 key별 schema 검증은 정상이다.
- 검증된 validator 경계를 리팩터링하면서 약화할 위험이 있으므로 이번 PR에서 변경하지 않는다.

### DEFER-06: Cache-aside와 prewarm helper 공통화

- 대상: `app/home_topics_payload.py`
- Daily·3-day·Weekly 함수 구조가 반복되지만 현재 동작은 정상이다.
- 신규 추상화는 이번 Task의 기능 완료와 직접 관련이 없으므로 보류한다.

### NOCHANGE-01: Daily Pipeline prewarm 호출 구조

- Daily 호출 위치가 3-day·Weekly와 구조적으로 다르지만 helper가 예외를 격리한다.
- fail-open 계약은 테스트로 검증됐다.
- 기능 변경을 하지 않는다.

### REJECT-01: CodeRabbit Autofix 일괄 적용

- 모든 review suggestion을 자동으로 적용하지 않는다.
- 승인된 FIX-06부터 FIX-13만 최소 변경으로 반영한다.
- Optional Improvements와 범위 밖 리팩터링은 적용하지 않는다.

### REJECT-02: 별도 기능 PR로 분리

- 승인된 항목은 현재 PR의 문서와 검증 정합성을 직접 보완한다.
- 변경량이 작으므로 같은 브랜치에서 반영한다.

## Applied Changes

### Claude Code 승인 Fix

- [x] FIX-01: 3-day router의 미사용 `HOME_TOPICS_LIMIT` 제거
- [x] FIX-02: Weekly CronJob TTL과 API Deployment TTL 교차 검증 추가
- [x] FIX-03: 3-day·Weekly Redis SETEX 실패 fail-open 테스트 추가
- [x] FIX-04: 3-day API fixture status를 `draft`로 정합화
- [x] FIX-05: 기존 malformed/unsupported `REDIS_URL` 테스트 확인, 중복 테스트 미추가

Claude 승인 Fix 적용 후 확인된 전체 테스트 결과:

```
445 passed, 91 subtests passed
```

### CodeRabbit 승인 Fix

- [x] FIX-06: 이 문서에서 FIX-05를 기존 테스트로 검증 완료된 상태로 정리하고
  중복 테스트나 추가 조사가 없음을 명시했다.
- [x] FIX-07: `docs/pr/feat-home-cache-prewarm.md`에서 local verification과
  production `pending / human-required` 항목을 분리했다.
- [x] FIX-08: `docs/reviews/feat-home-cache-prewarm-coderabbit.md`의 실제 리뷰
  결과를 유지하고 `docs/reviews/feat-home-cache-prewarm-antigravity.md`를
  `not performed` 상태로 정리했다.
- [x] FIX-09: `docs/runbooks/cronjobs.md`의 Argo CD 예상 diff에 API Redis URL,
  timeout과 Weekly TTL을 추가했다.
- [x] FIX-10: `docs/runbooks/cronjobs.md`의 세 수동 Job 이름에 `RUN_ID`를 적용하고
  증거 보존 후 사람 주도 삭제 원칙을 기록했다.
- [x] FIX-11: `docs/runbooks/cronjobs.md`의 Daily Cache 검증을
  `db_write_performed=True` 조건과 no-write 정상 경로에 맞췄다.
- [x] FIX-12: `docs/tasks/feat-home-cache-prewarm.md`의 현재 최종 결과를
  `445 passed, 91 subtests passed`로 갱신하고 이전 결과를 historical baseline으로
  구분했다.
- [x] FIX-13: `docs/verification/feat-home-cache-prewarm.md`의 stale snapshot
  설명에서 최신 PR/devlog를 제외하고 실제 과거 기록 위치만 명시했다.

FIX-06부터 FIX-13 적용 시 Python application code, K8s manifest, DB schema, API 계약, Pipeline schedule, Redis key와 TTL은 변경하지 않는다.

## Verification Required

### CodeRabbit Fix 문서 검증

```bash
git diff --check
```

```bash
rg -n "443 passed|85 subtests|445 passed|91 subtests" \
  docs/tasks/feat-home-cache-prewarm.md \
  docs/verification/feat-home-cache-prewarm.md \
  docs/pr/feat-home-cache-prewarm.md \
  docs/devlog/feat-home-cache-prewarm.md
```

```bash
rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|RUN_ID|db_write_performed|AlreadyExists" \
  docs/runbooks/cronjobs.md
```

```bash
rg -n "Review Summary|Problems Found|Required Fixes Before PR|Optional Improvements|Suggested Test Commands|Risk Notes|not performed" \
  docs/reviews/feat-home-cache-prewarm-coderabbit.md \
  docs/reviews/feat-home-cache-prewarm-antigravity.md
```

### 변경 범위 확인

```bash
git status --short
```

```bash
git diff --stat
```

```bash
git diff --name-only -- \
  app scripts tests k8s db migrations frontend
```

FIX-06부터 FIX-13만 적용했다면 위 명령에서 application, test, manifest, DB와 Frontend 변경이 없어야 한다.

### 전체 회귀 테스트 실행 조건

문서만 변경했다면 기존 최종 결과 `445 passed, 91 subtests passed`를 유지하고 전체 pytest 재실행은 필수로 요구하지 않는다.

Python, test 또는 K8s YAML이 추가로 변경된 경우에만 다음을 다시 실행한다.

```bash
PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"
```

```bash
PYTHONPATH=. pytest -q
```

```bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

### 완료 기록

- FIX-06부터 FIX-13의 실제 변경 파일을 `Applied Changes`에 체크한다.
- CodeRabbit inline conversation은 수정 근거를 확인한 뒤 resolve한다.
- 수행하지 않은 production verification은 완료로 기록하지 않는다.
- PR merge, Argo CD Manual Sync, 수동 Job 실행과 Redis key/TTL 확인은 계속 `human-required`다.
