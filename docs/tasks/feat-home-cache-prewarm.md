# Task: Daily Topic Pipeline 연계 Home Cache Prewarming 및 TTL 정책 정합화

## Goal

NewsLab 홈 화면이 사용하는 세 Home API의 Redis Cache 수명주기를 각 데이터 생성 Pipeline의 실제 갱신 주기와 맞춘다.

```
/topics/home
/three-day-topics/home
/weekly-topics/home
```

기존 71차에서는 `/topics/home`에 60초 Cache-aside를 적용했다. 72차 초기 구현에서는 Daily Topic Pipeline만 `/topics/home` Cache를 prewarm하도록 확장했지만, 실제 홈은 Daily·3-day·Weekly 데이터를 동시에 표시한다. 따라서 Daily만 갱신해서는 홈 전체의 Cache 생명주기가 정합하지 않다.

각 Pipeline이 자신의 DB 저장을 성공적으로 완료한 직후 대응 Home API와 동일한 payload를 Redis에 미리 저장하도록 확장한다.

```
Daily Pipeline 성공
→ topics:home:v1 overwrite

3-day Pipeline 성공
→ three-day-topics:home:v1 overwrite

Weekly Pipeline 성공
→ weekly-topics:home:v1 overwrite
```

PostgreSQL은 계속 source of truth로 유지한다. Redis 미설정, 연결 실패, timeout, payload 오류 또는 저장 실패는 API와 Pipeline 실패로 전파하지 않는 fail-open 정책을 유지한다.

## Scope

- 홈 화면이 세 Home API를 함께 조회하는 구조를 기준으로 Cache 범위를 정한다.
- 세 Home API의 payload 생성과 PostgreSQL 조회 경로를 조사한다.
- Daily, 3-day, Weekly Pipeline의 DB write transaction과 commit 성공 이후 경계를 조사한다.
- 각 Home API Cache miss와 대응 Pipeline prewarm이 동일한 payload 생성 로직을 사용하도록 공통화한다.
- 외부 response schema를 변경하지 않고 내부 payload 생성 책임만 분리한다.
- Daily Home Cache는 기존 key `topics:home:v1`, TTL `108000`초를 유지한다.
- 3-day Home Cache key는 `three-day-topics:home:v1`, TTL은 `108000`초를 기본값으로 한다.
- Weekly Home Cache key는 `weekly-topics:home:v1`, TTL은 `691200`초를 기본값으로 한다.
- 최신성은 TTL 만료가 아니라 각 Pipeline 성공 시 같은 key overwrite로 관리한다.
- Daily Topic Pipeline의 기존 prewarm 구현과 fail-open 동작을 유지한다.
- `/three-day-topics/home`과 `/weekly-topics/home`에 Cache-aside와 PostgreSQL fallback을 추가한다.
- 3-day Pipeline의 최신 window 저장 성공 이후 3-day Home Cache prewarm을 실행한다.
- Weekly Pipeline의 최신 주간 저장 성공 이후 Weekly Home Cache prewarm을 실행한다.
- dry-run, no-write, DB 저장 실패 또는 publishable 결과 미생성 시 prewarm을 실행하지 않는다.
- Redis 오류가 API 또는 Pipeline 실패로 전파되지 않도록 한다.
- Cache hit, miss, store, prewarm, bypass를 로그에서 구분할 수 있게 한다.
- API Deployment와 Daily·3-day·Weekly CronJob에 필요한 Redis URL, TTL, timeout 설정을 전달한다.
- 세 Home API와 세 Pipeline의 Unit/Integration Test를 추가한다.
- Architecture, Runbook, Verification, PR과 devlog를 세 Pipeline 기준으로 갱신한다.
- 운영 반영은 Implementation Unit과 분리된 사람 주도 검증 단계로 기록한다.

## Do not change

- `/topics/home`, `/three-day-topics/home`, `/weekly-topics/home`의 외부 계약
- Topic archive와 detail API의 외부 계약
- Topic grouping, embedding, extraction과 summary 생성 알고리즘
- Daily, 3-day, Weekly Pipeline schedule과 실행 command
- PostgreSQL schema, table, column, index와 constraint
- Supabase migration과 운영 데이터
- Frontend repository, UI, Server Component와 fetch 정책
- HPA와 replica 자동 확장
- Redis persistence, Sentinel, Cluster와 sharding
- 분산락, Cache stampede 방지와 stale-while-revalidate
- 세 Home API를 하나로 합치는 신규 endpoint
- 단일 `home:all:*` Cache key
- 범용 Cache invalidation framework와 관리자용 Cache API
- Argo CD Manual Sync 정책
- 사람이 승인해야 하는 운영 작업의 자동 실행

## Expected files

실제 repository 구조를 먼저 확인하고 기존 책임 경계를 우선한다.

예상 애플리케이션 파일:

```
app/home_topics_cache.py
app/home_topics_payload.py
app/routers/topics.py
app/routers/three_day_topics.py
app/routers/weekly_topics.py
scripts/run_daily_topic_pipeline.py
scripts/run_three_day_topic_pipeline.py
scripts/run_weekly_topic_pipeline.py
```

예상 테스트 파일:

```
tests/test_topics_api.py
tests/*three_day_topics*.py
tests/*weekly_topics*.py
tests/test_run_daily_topic_pipeline.py
tests/*run_three_day_topic_pipeline*.py
tests/*run_weekly_topic_pipeline*.py
tests/test_home_api_redis_k8s_manifest.py
tests/*cronjob_manifest*.py
```

예상 K3s 파일:

```
k8s/news-api.yaml
k8s/news-daily-topic-pipeline-cronjob.yaml
k8s/news-three-day-topic-pipeline-cronjob.yaml
k8s/news-weekly-topic-pipeline-cronjob.yaml
```

예상 문서 파일:

```
docs/architecture/backend-api.md
docs/design/home-api-redis-cache.md
docs/tasks/feat-home-cache-prewarm.md
docs/verification/feat-home-cache-prewarm.md
docs/pr/feat-home-cache-prewarm.md
docs/devlog/feat-home-cache-prewarm.md
docs/runbooks/cronjobs.md
```

동일한 Redis client, serializer, payload builder와 logging 코드를 불필요하게 중복 생성하지 않는다.

## DB changes

없음.

- migration 추가 없음
- table, column, index와 constraint 변경 없음
- 운영 데이터 수정 없음
- 기존 transaction과 commit 의미 변경 없음

Prewarm은 각 Pipeline의 DB 저장 transaction이 성공적으로 완료된 뒤 수행한다. Redis 오류 때문에 이미 성공한 DB transaction을 rollback하거나 Pipeline 전체를 실패 처리하지 않는다.

## API changes

외부 API 계약 변경 없음.

- `GET /topics/home`
- `GET /three-day-topics/home`
- `GET /weekly-topics/home`
- request parameter 변경 없음
- response schema 변경 없음
- HTTP status 정책 변경 없음
- Cache 상태를 response body나 header에 추가하지 않음

내부 동작은 다음처럼 통일한다.

```
Home API Request
→ 대응 Redis key 조회
  ├─ HIT: cached payload 반환
  └─ MISS 또는 Redis 오류
      → PostgreSQL 조회
      → Redis 저장 시도
      → 기존 response schema 반환
```

Pipeline 성공 후:

```
Daily commit 성공
→ topics:home:v1, TTL 108000

3-day commit 성공
→ three-day-topics:home:v1, TTL 108000

Weekly commit 성공
→ weekly-topics:home:v1, TTL 691200
```

## Test commands

### 구조 조사

```bash
rg -n "topics/home|three-day-topics/home|weekly-topics/home|home_topics|HomeTopicsCache|topics:home:v1" app tests
```

```bash
rg -n "run_daily_topic_pipeline|run_three_day_topic_pipeline|run_weekly_topic_pipeline|engine.begin|replace_window|CACHE_TTL|REDIS_TIMEOUT" app scripts tests k8s
```

### 변경 범위 확인

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

### Targeted Test

```bash
rg --files tests | rg "topics_api|three_day|weekly|home|cache|cronjob_manifest"
```

```bash
PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm"
```

최소 검증 항목:

- 세 Home API Cache hit 시 PostgreSQL payload builder 미호출
- Cache miss 시 PostgreSQL 조회 후 대응 Cache 저장
- Redis 오류 시 PostgreSQL fallback 유지
- 각 Pipeline DB 저장 성공 후 자신의 Home Cache prewarm 실행
- DB 저장 실패, dry-run과 no-write 결과에서 prewarm 미실행
- API miss와 Pipeline prewarm이 동일한 payload builder 사용
- Daily와 3-day TTL `108000`초
- Weekly TTL `691200`초
- 세 Cache key가 충돌하지 않음
- 세 Home API response schema 유지

### 전체 Test

```bash
PYTHONPATH=. pytest -q
```

### K8s YAML Parse

```bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

### 정적 검증

```bash
git diff --check
```

```bash
git diff --name-only -- db migrations frontend
```

기대 결과: DB migration과 Frontend 변경 없음.

## Acceptance criteria

- 홈 화면이 Daily·3-day·Weekly Home API를 함께 사용한다는 사실이 문서에 반영돼 있다.
- 세 Home API와 대응 Pipeline의 commit 성공 경계가 문서화돼 있다.
- 각 Home API Cache miss와 대응 Pipeline prewarm이 동일한 payload 생성 로직을 사용한다.
- PostgreSQL이 source of truth로 유지된다.
- Daily Cache는 `topics:home:v1`, TTL `108000`초다.
- 3-day Cache는 별도 key와 TTL `108000`초를 사용한다.
- Weekly Cache는 별도 key와 TTL `691200`초를 사용한다.
- 최신성은 각 Pipeline 성공 시 Cache overwrite로 관리된다.
- Daily 기존 구현과 회귀 테스트가 유지된다.
- 3-day와 Weekly Home API에 Cache-aside와 fallback이 적용된다.
- 3-day와 Weekly Pipeline 저장 성공 후 대응 prewarm이 실행된다.
- 실패, dry-run과 no-write에서는 prewarm이 실행되지 않는다.
- Redis 오류가 API 또는 Pipeline 실패로 전파되지 않는다.
- 손상된 Cache payload는 PostgreSQL 재조회로 복구한다.
- Cache 동작을 로그에서 구분할 수 있다.
- API Deployment와 세 CronJob에 필요한 설정이 반영된다.
- 세 Home API 외부 계약에 회귀가 없다.
- DB schema, migration과 Frontend 변경이 없다.
- 전체 pytest, K8s YAML parse와 `git diff --check`가 통과한다.
- 문서가 Daily-only 설명이 아니라 세 Home API 기준으로 정합하다.
- 실행하지 않은 운영 검증은 통과로 기록하지 않는다.

## Notes

- Redis는 source of truth가 아니라 삭제 가능한 성능 최적화 계층이다.
- 3-day 데이터가 72시간 범위를 다룬다고 TTL을 72시간으로 정하지 않는다. TTL은 Pipeline 실행 주기와 지연 여유를 기준으로 한다.
- Weekly TTL 8일도 최신성 보장 수단이 아니다. 정상 실행 시 Weekly Pipeline이 key를 overwrite하고, TTL은 오래된 key의 영구 잔류를 막는 안전장치다.
- 각 Pipeline은 자신이 생성하는 데이터의 Home Cache만 갱신한다.
- 세 API를 하나로 합치거나 Frontend를 수정하지 않는다.
- UNIT-01부터 UNIT-07까지는 Daily-only 초기 범위로 로컬 구현과 검증을 마친 상태다.
- 현재 전체 테스트 기록은 `443 passed, 85 subtests passed`다.
- Daily-only 구현은 폐기하지 않고 3-day와 Weekly 구현의 기준 패턴으로 재사용한다.
- 기존 UNIT-08 운영 준비 기록은 완료 Unit으로 취급하지 않는다.

## UNIT-08 변경 결과

- `HomeTopicsCache`는 API별 Redis key, TTL env, payload validator를 받을 수 있게
  확장했다. Daily key `topics:home:v1`와 기존 TTL `108000`초는 유지하고, 3-day key
  `three-day-topics:home:v1`와 기본 TTL `108000`초를 추가했다.
- 3-day Home payload 생성은 `app/home_topics_payload.py`의
  `fetch_three_day_home_topics_from_database()`로 분리했다.
  `/three-day-topics/home` cache miss와 3-day Pipeline prewarm은 이 builder를
  공유한다.
- `/three-day-topics/home`은 cache hit에서 PostgreSQL connection을 열지 않고,
  cache miss, Redis GET 오류, 손상 payload에서는 PostgreSQL fallback 후 Redis
  저장을 시도한다.
- `scripts/run_three_day_topic_pipeline.py`는 execute 모드에서
  `saved_topic_count >= 1`이고 run 종료가 성공한 뒤
  `three-day-topics:home:v1` prewarm을 시도한다. dry-run, publishable 결과 없음,
  prewarm 조회/저장 오류는 pipeline 실패로 전파하지 않는다.
- API Deployment와 3-day CronJob에 `THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS=108000`
  및 prewarm에 필요한 Redis env를 추가했다. Schedule과 실행 command는 변경하지
  않았다.

## UNIT-09 변경 결과

- `HomeTopicsCache`에 Weekly key `weekly-topics:home:v1`, 기본 TTL `691200`초와
  `/weekly-topics/home` payload validator를 추가했다. Daily와 3-day key/TTL은
  변경하지 않았다.
- Weekly Home payload 생성은 `app/home_topics_payload.py`의
  `fetch_weekly_home_topics_from_database()`로 분리했다.
  `/weekly-topics/home` cache miss와 Weekly Pipeline prewarm은 이 builder를
  공유한다.
- `/weekly-topics/home`은 cache hit에서 PostgreSQL connection을 열지 않고,
  cache miss, Redis GET 오류, 손상 payload에서는 PostgreSQL fallback 후 Redis
  저장을 시도한다.
- `scripts/run_weekly_topic_pipeline.py`는 execute 모드에서
  `saved_topic_count >= 1`이고 run 종료가 성공한 뒤
  `weekly-topics:home:v1` prewarm을 시도한다. dry-run, publishable 결과 없음,
  prewarm 조회/저장 오류는 pipeline 실패로 전파하지 않는다.
- API Deployment와 Weekly CronJob에 `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS=691200`
  및 prewarm에 필요한 Redis env를 추가했다. Schedule과 실행 command는 변경하지
  않았다.

## UNIT-10 변경 결과

- `tests/test_home_cache_integration.py`를 추가해 Daily, 3-day, Weekly Home Cache가
  하나의 Redis client에서도 서로 다른 key, TTL과 payload validator를 유지하는지
  회귀 검증했다.
- API Deployment와 Daily·3-day·Weekly CronJob manifest의 Redis URL, TTL, timeout
  설정을 기존 manifest tests와 K3s YAML parse로 검증했다.
- Architecture, design, runbook, PR draft와 devlog draft가 Daily-only 설명이 아니라
  세 Home API와 세 Pipeline 기준으로 정합한지 검색으로 확인했다.
- 전체 로컬 검증 결과는 `443 passed, 85 subtests passed`이며 DB migration과
  frontend 변경은 없다.

## Manual or Production Verification

Status: `human-required`

Implementation Unit 완료 후 사람이 승인하고 직접 수행한다.

- Argo CD diff에서 API Deployment와 Daily·3-day·Weekly CronJob의 의도한 변경만 확인
- Manual Sync
- Backend, Redis와 세 CronJob 상태 확인
- 각 Pipeline 실행 후 사용자 요청 전에 대응 Redis key가 생성됐는지 확인
- Daily와 3-day TTL이 약 `108000`, Weekly TTL이 약 `691200`인지 확인
- 각 Home API 첫 요청 후 TTL이 초기값으로 재설정되지 않고 감소하는지 확인
- `/health`와 세 Home API 정상 응답 확인

사람이 제공한 운영 결과만 Verification 문서에 기록한다.

## Implementation Units

- [x] UNIT-01: 현재 Daily Home Cache 경로와 Daily Pipeline commit 경계 조사
- [x] UNIT-02: Daily Home payload 생성 로직 공통화
- [x] UNIT-03: Daily Home Cache TTL 30시간 정책과 API 설정 반영
- [x] UNIT-04: Daily Topic Pipeline 성공 후 Home Cache prewarm 구현
- [x] UNIT-05: Daily prewarm Redis fail-open과 logging 검증
- [x] UNIT-06: Daily CronJob manifest와 관련 테스트 반영
- [x] UNIT-07: Daily 범위 로컬 검증과 문서화
- [x] UNIT-08: 3-day Home Cache-aside, payload 공통화와 Pipeline prewarm 구현
- [x] UNIT-09: Weekly Home Cache-aside, payload 공통화와 Pipeline prewarm 구현
- [x] UNIT-10: 세 Home Cache 통합 회귀 테스트, K3s manifest와 문서 정합성 최종 검증
