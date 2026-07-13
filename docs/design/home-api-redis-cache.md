# Home API Redis Cache

## Decision

`GET /topics/home`은 Redis cache-aside를 사용한다.

PostgreSQL은 계속 source of truth다. Redis는 반복 조회 부하를 줄이는 삭제 가능한
성능 최적화 계층이며, Redis 장애나 손상된 payload는 API 실패가 아니라
PostgreSQL 직접 조회로 복구한다.

## Current Read Path

현재 home payload는 `app/routers/topics.py`에서 `topics` table을 직접 조회해
최대 10개의 card field를 반환한다.

```text
GET /topics/home
→ Redis GET topics:home:v1
  ├─ hit: cached payload 반환
  └─ miss/bypass: topics table 조회
                   → Redis SETEX
                   → payload 반환
```

조회 SQL은 `topics`만 읽으며 `count(*)`, `topic_articles` join, archive metadata
field를 사용하지 않는다.

## Cache Policy

- Key: `topics:home:v1`
- TTL: 60초
- Redis URL: `REDIS_URL`
- TTL override: `HOME_TOPICS_CACHE_TTL_SECONDS`
- Redis connect/read timeout: `REDIS_TIMEOUT_SECONDS`, 기본 0.05초

Daily Topic Pipeline이 새 topic set을 생성하는 구조라 home payload는 초 단위 강한
일관성이 필요하지 않다. 60초 TTL은 첫 화면 반복 조회 부하를 줄이면서 운영자가
pipeline 결과 반영을 확인할 때 stale window를 짧게 유지하는 초기값이다.

## Failure Policy

다음 상황은 cache bypass로 처리한다.

- Redis 미설정
- Redis dependency 미설치
- Redis connection 오류
- Redis GET/SET timeout 또는 오류
- JSON decode 실패
- `/topics/home` 최소 schema를 만족하지 않는 payload

Cache hit, miss, store, bypass는 `home_topics_cache event=...` 로그로 구분한다.
외부 response body에는 cache 상태를 추가하지 않는다.

## Kubernetes

`k8s/redis.yaml`은 `news-redis` Deployment/Service를 추가한다. Cache data는
재생성 가능하므로 persistence를 사용하지 않고 Redis `appendonly`와 snapshot save를
비활성화한다.

초기 resource 값:

- Redis request: `50m`, `64Mi`
- Redis limit: `250m`, `128Mi`
- Redis maxmemory: `96mb`, policy `allkeys-lru`

`news-api`는 `REDIS_URL=redis://news-redis:6379/0`을 사용한다. 운영 반영은
manifest merge 후 Argo CD Manual Sync로 사람이 수행한다.

## Verification Boundary

Agent가 수행 가능한 검증:

- unit/integration test
- k8s YAML parse
- local 또는 제한된 환경의 load test
- Redis disabled/failure fallback test

사람이 수행해야 하는 검증:

- production endpoint 부하 테스트
- K3s apply 또는 Argo CD Manual Sync
- Redis pod 중단·복구 장애 주입
- production pod CPU/Memory와 DB connection/query 관측
