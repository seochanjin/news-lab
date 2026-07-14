# Home API Redis Cache

## Decision

`GET /topics/home`, `GET /three-day-topics/home`과 `GET /weekly-topics/home`은
Redis cache-aside를 사용하고, 대응 Pipeline 성공 후 같은 payload를 Redis에 미리
저장한다.

PostgreSQL은 계속 source of truth다. Redis는 반복 조회 부하를 줄이는 삭제 가능한
성능 최적화 계층이며, Redis 장애나 손상된 payload는 API 실패가 아니라
PostgreSQL 직접 조회로 복구한다.

## Current Read Path

현재 home payload는 `app/home_topics_payload.py`에서 Daily `topics`, 3-day
`three_day_topics`와 Weekly `weekly_topics` 계열을 직접 조회해 최대 10개의 card
field를 반환한다. Home API cache miss와 대응 Pipeline prewarm은 같은 payload
builder를 사용한다.

```text
GET /topics/home
→ Redis GET topics:home:v1
  ├─ hit: cached payload 반환
  └─ miss/bypass: topics table 조회
                   → Redis SETEX
                   → payload 반환

GET /three-day-topics/home
→ Redis GET three-day-topics:home:v1
  ├─ hit: cached payload 반환
  └─ miss/bypass: 최신 publishable 72시간 window 조회
                   → Redis SETEX
                   → payload 반환

GET /weekly-topics/home
→ Redis GET weekly-topics:home:v1
  ├─ hit: cached payload 반환
  └─ miss/bypass: 최신 publishable 주간 window 조회
                   → Redis SETEX
                   → payload 반환
```

조회 SQL은 Home card table만 읽으며 `count(*)`, article relation join, archive
metadata field를 사용하지 않는다.

Pipeline prewarm 경로:

```text
Daily Topic Pipeline
→ PostgreSQL 저장 transaction commit 성공
→ Home payload 재조회
→ Redis SETEX topics:home:v1 108000

3-day Topic Pipeline
→ 최신 72시간 window 교체 transaction 성공
→ run status success/partial_success 종료 성공
→ 3-day Home payload 재조회
→ Redis SETEX three-day-topics:home:v1 108000

Weekly Topic Pipeline
→ 최신 주간 window 교체 transaction 성공
→ run status success/partial_success 종료 성공
→ Weekly Home payload 재조회
→ Redis SETEX weekly-topics:home:v1 691200
```

Dry-run, 저장할 publishable topic이 없는 성공 실행, Redis 미설정과 Redis SET
실패는 pipeline 실패로 전파하지 않는다.

## Cache Policy

- Daily key: `topics:home:v1`
- 3-day key: `three-day-topics:home:v1`
- Weekly key: `weekly-topics:home:v1`
- Daily/3-day TTL: 108,000초(30시간)
- Weekly TTL: 691,200초(8일)
- Redis URL: `REDIS_URL`
- Daily TTL override: `HOME_TOPICS_CACHE_TTL_SECONDS`
- 3-day TTL override: `THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS`
- Weekly TTL override: `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS`
- Redis connect/read timeout: `REDIS_TIMEOUT_SECONDS`, 기본 0.05초

Daily와 3-day Pipeline은 하루 단위, Weekly Pipeline은 주 단위로 새 topic set을
생성하는 구조라 home payload는 초 단위 강한 일관성이 필요하지 않다. 30시간 TTL은
하루 한 번 실행되는 Pipeline의 시작과 완료 지연을 흡수하고, Weekly 8일 TTL은 주간
Pipeline 지연 시 stale key가 영구 잔류하지 않게 하는 안전장치다. 최신성은 TTL
만료가 아니라 Pipeline 성공 후 대응 key를 overwrite하는 방식으로 관리한다.

## Failure Policy

다음 상황은 cache bypass로 처리한다.

- Redis 미설정
- Redis dependency 미설치
- Redis connection 오류
- Redis GET/SET timeout 또는 오류
- JSON decode 실패
- 대응 Home API 최소 schema를 만족하지 않는 payload

Cache hit, miss, store, prewarm, bypass는 `home_topics_cache event=...` 로그로
구분한다. 외부 response body에는 cache 상태를 추가하지 않는다.

## Kubernetes

`k8s/redis.yaml`은 `news-redis` Deployment/Service를 추가한다. Cache data는
재생성 가능하므로 persistence를 사용하지 않고 Redis `appendonly`와 snapshot save를
비활성화한다.

초기 resource 값:

- Redis request: `50m`, `64Mi`
- Redis limit: `250m`, `128Mi`
- Redis maxmemory: `96mb`, policy `allkeys-lru`

`news-api`, `news-daily-topic-pipeline`, `news-three-day-topic-pipeline`,
`news-weekly-topic-pipeline`은 `REDIS_URL=redis://news-redis:6379/0`과
`REDIS_TIMEOUT_SECONDS=0.05`를 사용한다. Daily는
`HOME_TOPICS_CACHE_TTL_SECONDS=108000`, 3-day는
`THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS=108000`, Weekly는
`WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS=691200`을 사용한다.
운영 반영은 manifest merge 후 Argo CD Manual Sync로 사람이 수행한다.

## Verification Boundary

Agent가 수행 가능한 검증:

- unit/integration test
- k8s YAML parse
- local 또는 제한된 환경의 load test
- Redis disabled/failure fallback test

사람이 수행해야 하는 검증:

- 사용자 요청 전 각 Pipeline 실행만으로 대응 key가 생성되는지 확인
- Pipeline 직후 Daily/3-day TTL은 약 108,000초, Weekly TTL은 약 691,200초이고
  첫 Home API 요청 후 TTL이 감소하는지 확인
- K3s apply 또는 Argo CD Manual Sync
- Redis pod 중단·복구 장애 주입
- production pod CPU/Memory와 DB connection/query 관측
