# Daily·3-day·Weekly Home Cache Prewarming 및 TTL 정책 정합화

## 작업 목적

NewsLab 홈 화면은 Daily, 3-day, Weekly Home API를 함께 조회한다. 세 데이터의
생성 주기에 맞춰 Redis cache 수명주기를 정리하고, 각 Pipeline이 PostgreSQL 저장을
성공한 직후 대응 Home payload를 미리 저장해 첫 사용자 요청의 cold miss 비용을
줄이는 것이 목적이다.

PostgreSQL은 계속 source of truth로 두고 Redis는 삭제 가능한 성능 최적화 계층으로
유지한다. Cache 장애가 API 응답이나 이미 성공한 Pipeline 결과를 실패로 바꾸지
않는 것도 완료 조건에 포함했다.

## 기존 문제

- `/topics/home`은 cache-aside만 사용했고 기본 TTL이 60초여서 하루 단위 데이터
  갱신 주기와 맞지 않았다.
- Cache key가 없거나 만료되면 첫 사용자 요청이 PostgreSQL 조회와 Redis 저장을
  함께 부담했다.
- 초기 prewarm 범위는 Daily Pipeline과 `/topics/home`만 연결했다. 실제 홈은
  3-day와 Weekly API도 함께 사용하므로 홈 전체 cache 생명주기는 정합하지 않았다.
- 3-day와 Weekly Home API는 PostgreSQL을 직접 조회했고, 대응 cache key와
  Pipeline prewarm 경로가 없었다.
- Router와 Pipeline이 각자 payload 생성 SQL을 가지면 외부 response schema가
  내부 경로에 따라 달라질 위험이 있었다.

## 변경 내용

- Home payload 생성과 cache-aside/prewarm 조립을 `app/home_topics_payload.py`로
  분리했다.
- 세 Home API가 독립된 Redis key와 payload validator를 사용하도록
  `HomeTopicsCache`를 확장했다.
  - Daily: `topics:home:v1`, TTL `108000`초
  - 3-day: `three-day-topics:home:v1`, TTL `108000`초
  - Weekly: `weekly-topics:home:v1`, TTL `691200`초
- `/three-day-topics/home`과 `/weekly-topics/home`에 cache-aside와 PostgreSQL
  fallback을 추가했다.
- Daily, 3-day, Weekly Pipeline이 자신의 DB 저장 성공 경계 이후 대응 key를
  prewarm하도록 연결했다.
- Redis 미설정, malformed URL, connection/timeout/SETEX 오류와 손상 payload를
  fail-open으로 처리했다.
- API Deployment와 세 CronJob에 Redis URL, API별 TTL과 timeout 설정을 맞췄다.
- Architecture, cache design과 CronJob runbook을 세 API와 세 Pipeline 기준으로
  갱신했다.
- 승인된 FIX-01~05를 반영했다. 승인되지 않은 suggestion과 Deferred/Rejected
  항목은 적용하지 않았다.

## 구현 상세

### API 조회 경로

세 Home API는 같은 cache-aside 순서를 사용한다.

```text
Redis GET
├─ hit: cached payload 반환
└─ miss/bypass: PostgreSQL 조회
                 → Redis SETEX 시도
                 → 기존 response schema 반환
```

API별 validator는 key에 맞지 않는 payload나 손상된 JSON을 hit로 인정하지 않는다.
Cache hit에서는 PostgreSQL connection을 열지 않고, miss나 Redis 오류에서는 공통
payload builder가 PostgreSQL source of truth를 읽는다.

### Pipeline prewarm 경계

- Daily는 execute 결과의 `db_write_performed=True`에서만 prewarm한다.
- 3-day와 Weekly는 execute 모드에서 `saved_topic_count >= 1`이고 run 종료가
  성공한 뒤 prewarm한다.
- Dry-run, no-write와 publishable 결과 미생성에서는 Redis와 PostgreSQL prewarm
  조회를 건너뛴다.
- Prewarm은 commit이 끝난 뒤 새 read connection으로 API와 같은 payload builder를
  호출한다. Redis 실패로 기존 DB transaction을 rollback하지 않는다.

### 실패와 관측

Redis GET/SETEX, timeout, URL parsing, JSON decode와 payload validation 실패는
cache bypass로 격리한다. 로그의 `event=hit|miss|store|prewarm|bypass`와
`operation=store|prewarm`으로 API 저장과 Pipeline prewarm을 구분한다. 오류
로그에는 예외 클래스만 남기고 credential이나 전체 `REDIS_URL`은 기록하지 않는다.

### 승인 fix 반영

- 3-day router의 공통화 이후 남은 미사용 limit 상수를 제거했다.
- Weekly CronJob TTL이 API Deployment 값과 일치하는지 manifest test에 추가했다.
- 3-day와 Weekly prewarm에서 connection, timeout, SETEX 실패가 Pipeline 성공을
  바꾸지 않는 회귀 테스트를 추가했다.
- 3-day API fixture status를 실제 Pipeline 저장 상태인 `draft`로 맞췄다.
- 기존 malformed/unsupported `REDIS_URL` 테스트가 cache disabled와 PostgreSQL
  fallback을 이미 검증해 중복 테스트는 추가하지 않았다.

## 대안 검토

### Cache-aside와 짧은 TTL만 유지

구현은 단순하지만 데이터 갱신이 없어도 반복 만료가 발생하고, 사용자 요청이
cache 재생성 비용을 부담한다. Pipeline이 데이터 생성 시점을 이미 알고 있다는
점을 활용하지 못한다.

### 세 API를 단일 `home:all:*` key 또는 신규 통합 endpoint로 합치기

한 번의 조회로 홈 데이터를 제공할 수 있지만 세 데이터의 갱신 주기와 실패 경계를
결합한다. 외부 API와 frontend 계약 변경도 필요해 현재 backend task 범위를 넘는다.

### Pipeline 성공 후 key 삭제만 수행

오래된 payload는 제거할 수 있지만 다음 사용자 요청이 여전히 cold miss를 부담한다.
이번 목표인 사용자 요청 전 cache 준비를 충족하지 못한다.

### Router와 각 Pipeline에 payload SQL을 각각 유지

초기 변경량은 작지만 schema와 정렬 조건이 쉽게 분기한다. API miss와 prewarm이
같은 결과를 보장하기 어려워 공통 builder가 더 적합하다.

### Redis 실패를 Pipeline 실패로 처리

Cache 상태를 강하게 보장할 수 있지만 성능 최적화 계층의 장애가 성공한 PostgreSQL
저장을 실패로 바꾸게 된다. PostgreSQL source of truth 원칙과 맞지 않는다.

## 선택한 접근과 근거

- API별 key를 유지해 Daily, 3-day, Weekly의 갱신 주기와 payload schema를 독립시켰다.
- 최신성은 짧은 TTL이 아니라 Pipeline 성공 시 overwrite로 관리한다. TTL은 Pipeline
  지연을 흡수하고 오래된 key의 영구 잔류를 막는 안전장치로만 사용한다.
- API miss와 Pipeline prewarm이 동일한 payload builder를 사용하게 해 외부 response
  schema와 정렬 조건의 단일 책임 지점을 만들었다.
- Prewarm을 DB commit과 run 종료 뒤에 배치해 rollback 의미를 바꾸지 않았다.
- Redis 경로를 fail-open으로 유지해 cache 장애와 핵심 데이터 생성 성공을 분리했다.
- 기존 cache client, serializer와 logging 구조를 확장해 범용 invalidation framework나
  별도 관리자 API를 만들지 않았다.

## 트레이드오프

- Pipeline이 실패하거나 prewarm이 bypass되면 긴 TTL 동안 이전 payload가 남을 수
  있다. API는 정상 응답하지만 최신성 확인은 Pipeline 상태와 cache 로그를 함께
  봐야 한다.
- 각 Pipeline 성공 뒤 Home payload를 다시 읽으므로 PostgreSQL read가 한 번
  추가된다. 대신 첫 사용자 요청의 read와 cache 저장을 미리 수행한다.
- Fail-open은 가용성을 높이지만 Redis 장애가 Pipeline exit status에 드러나지
  않는다. `prewarm`/`bypass` 로그와 운영 key/TTL 확인이 필요하다.
- API별 key와 TTL 환경변수는 결합도를 낮추는 대신 Deployment와 세 CronJob의
  설정 항목을 늘린다. Manifest 교차 검증으로 값 불일치 위험을 줄였다.
- Cache stampede 방지, stale-while-revalidate, persistence와 분산락은 다루지 않았다.
  현재 규모와 task 목표에는 필요한 복잡도가 아니며 별도 요구가 생기면 평가한다.

## 테스트

Verification 문서에 기록된 실제 결과는 다음과 같다.

- 승인 fix targeted test:
  `PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
  - `41 passed, 8 subtests passed`
- Home Cache 선택 테스트:
  `PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"`
  - `137 passed, 308 deselected, 32 subtests passed`
- 세 cache 통합 테스트:
  `PYTHONPATH=. pytest -q tests/test_home_cache_integration.py`
  - `1 passed`
- 전체 테스트: `PYTHONPATH=. pytest -q`
  - `445 passed, 91 subtests passed`
- K8s YAML parse:
  - top-level Kubernetes YAML 전체 parse 통과
- 정적 및 범위 검증:
  - `git diff --check` 통과
  - `git diff --name-only -- db migrations frontend` 출력 없음

## 운영 반영

Status: `pending / human-required`

- PR merge, Argo CD Manual Sync와 K3s rollout을 수행하지 않았다.
- 수동 Daily·3-day·Weekly Pipeline Job과 production API curl을 실행하지 않았다.
- Pipeline 실행 전후 Redis `EXISTS`/`TTL`과 첫 Home API 요청 후 TTL 감소를 확인하지
  않았다.
- 사람이 제공한 rollout, Pipeline, Redis 또는 curl verification log는 없다.
- 운영 반영은 `docs/runbooks/cronjobs.md`의 human-controlled 절차에 따라 수행하고,
  실제 결과가 제공된 뒤 Verification 문서에 기록해야 한다.

## README 업데이트 판단

README 업데이트는 필요하지 않다.

- 신규 endpoint, request parameter와 response schema가 없다.
- 사용자-facing 설치나 로컬 실행 절차를 변경하지 않았다.
- Cache key/TTL, Pipeline 성공 경계와 운영 검증은 README보다 Architecture, design,
  CronJob runbook이 적절한 책임 위치다.

## 확인 결과

- 로컬 Verification 상태는 `passed`다.
- 세 Home API의 hit, miss/store, Redis 오류와 손상 payload fallback을 확인했다.
- 세 Pipeline의 성공 후 prewarm과 dry-run/no-write skip을 확인했다.
- Redis connection, timeout과 SETEX 오류가 Pipeline 성공을 바꾸지 않고 credential과
  전체 URL을 로그에 노출하지 않음을 확인했다.
- 세 cache key, TTL과 validator가 서로 충돌하지 않음을 확인했다.
- API Deployment와 세 CronJob의 Redis 설정 및 YAML 문법을 확인했다.
- 외부 API 계약, DB schema, migration, Supabase 운영 데이터와 frontend는 변경하지
  않았다.
- Production deployment와 production verification은 `pending`이다.

## 이번 단계의 의미

Cache 최신성의 기준을 요청 시점의 짧은 TTL 만료에서 데이터 생성 시점의 명시적
overwrite로 옮겼다. 이로써 API read path와 batch write path가 동일한 payload
계약을 공유하면서도 PostgreSQL source of truth와 Redis fail-open 경계를 유지한다.

기능 추가뿐 아니라 commit 이후 실행 순서, cache 장애 격리, 민감정보 없는 로그,
manifest 설정 정합성과 운영 검증 경계까지 하나의 작업 단위로 검증했다.

## 포트폴리오용 요약

- FastAPI와 PostgreSQL 기반 뉴스 backend에서 Daily·3-day·Weekly Home API의 Redis
  cache-aside와 Pipeline prewarming을 설계·구현했다.
- 데이터 생성 transaction 이후 동일 payload builder로 API별 Redis key를
  overwrite하고, Redis 장애 시 PostgreSQL fallback을 유지하는 fail-open 구조를
  적용했다.
- API/Pipeline/manifest 단위 테스트와 통합 회귀 테스트를 보강해 전체
  `445 passed, 91 subtests passed`를 확인했으며, K8s 운영 반영은 사람 승인 단계로
  분리했다.

## 다음 단계 후보

- `pending / human-required`: Argo CD diff에서 API Deployment와 세 CronJob의
  Redis 환경변수 변경만 포함됐는지 확인한다.
- `pending / human-required`: Manual Sync 후 각 Pipeline 실행만으로 사용자 요청 전
  대응 key가 생성되는지 확인한다.
- `pending / human-required`: Daily·3-day TTL이 약 `108000`, Weekly TTL이 약
  `691200`인지 확인하고 첫 Home API 요청 뒤 TTL이 감소하는지 확인한다.
- `pending / human-required`: `/health`와 세 Home API의 production response schema를
  확인한다.
- 후속 요구가 생기면 publishable status 다중화에 맞춰 Weekly query의 `IN` 조건과
  테스트를 함께 설계한다.
- Runtime에서 Redis 설정을 동적으로 변경해야 하는 요구가 생기면 cache factory의
  `lru_cache` 수명주기와 재초기화 정책을 별도 task로 검토한다.
