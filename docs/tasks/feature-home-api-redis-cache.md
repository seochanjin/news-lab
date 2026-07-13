# Task: Home API 부하 측정 및 Redis Cache 적용

## Goal

`GET /topics/home`의 현재 응답 성능과 반복 조회 부하를 먼저 측정한 뒤, PostgreSQL을 source of truth로 유지하는 Redis Cache-aside 구조를 적용한다.

Redis는 성능 최적화 계층으로만 사용하며, Redis 장애 시 요청을 실패시키지 않고 PostgreSQL 직접 조회로 전환하는 fail-open 정책을 적용한다.

Redis 적용 전후를 동일한 부하 조건으로 비교해 다음 지표를 기록한다.

- p50, p95, p99 응답 시간
- 처리량(RPS)
- 오류율
- Backend Pod CPU와 Memory
- 가능한 범위의 PostgreSQL connection 및 query 부하
- Cache hit, miss, bypass 비율

최종적으로 첫 화면 조회 성능을 개선하면서도 Redis 장애가 서비스 장애로 이어지지 않는 구조를 검증한다.

```
/topics/home 현재 구조 조사
→ Redis 적용 전 Baseline 부하 측정
→ Cache-aside와 fail-open 정책 설계
→ Redis 적용
→ 동일 조건 Before/After 비교
→ Redis 중단·복구 시 PostgreSQL fallback 검증
```

이번 Task의 핵심 완료 기준은 단순히 Redis를 추가하는 것이 아니라, 측정 결과를 근거로 Cache를 적용하고 성능 개선과 장애 격리를 실제로 검증하는 것이다.

## Scope

- 현재 `/topics/home`의 Route, Service, Repository, SQL 실행 경로를 조사한다.
- 응답 데이터의 생성 주기와 변경 주기를 확인해 Cache 적용 적합성을 판단한다.
- 현재 Backend Deployment replica, resource requests/limits, Pod CPU/Memory 상태를 확인한다.
- Redis 적용 전 Baseline 부하 테스트를 수행한다.
- 부하 단계별 p50, p95, p99, RPS, 오류율을 기록한다.
- 가능하면 같은 시간대의 Backend Pod CPU/Memory와 DB connection/query 상태를 함께 기록한다.
- `/topics/home`에 Cache-aside 패턴을 적용한다.
- 초기 Cache key는 `topics:home:v1`을 기준으로 하되 실제 응답 계약과 무효화 조건을 조사한 뒤 확정한다.
- 초기 TTL은 60초 후보로 두고 데이터 갱신 주기와 stale 허용 범위를 근거로 최종 결정한다.
- Cache hit 시 PostgreSQL을 조회하지 않고 cached response를 반환한다.
- Cache miss 시 PostgreSQL을 조회한 뒤 응답을 Redis에 저장한다.
- Redis GET, SET, connection, timeout 오류가 발생해도 PostgreSQL 직접 조회로 정상 응답한다.
- Redis 오류와 Cache hit/miss/bypass를 로그 또는 기존 metrics 체계에서 구분 가능하게 한다.
- 잘못된 Cache payload는 폐기하고 PostgreSQL 재조회로 복구한다.
- Redis 적용 후 Baseline과 동일한 조건으로 부하 테스트를 다시 수행한다.
- Redis 정상, 중단, 복구 시나리오를 검증한다.
- K3s 운영 반영은 사람 승인 후 수행하고 Argo CD Manual Sync 정책을 유지한다.
- Architecture, Runbook, Verification, PR, devlog에 최종 결과와 실제 수치를 기록한다.

## Do not change

- `/topics/home`의 외부 response schema와 의미
- 다른 Topic, Article, Search API의 Cache 적용
- Topic grouping, summary, embedding, extraction pipeline logic
- Daily, 3-day, Weekly CronJob schedule과 command
- PostgreSQL schema, table, column, index, constraint
- Supabase 운영 데이터
- Frontend repository와 UI
- Backend business logic 중 Cache와 무관한 영역
- Argo CD Manual Sync 정책
- automated sync, automatic prune, automatic self-heal
- HPA와 replica 자동 확장
- Redis Cluster, Sentinel, sharding, persistence 고도화
- CDN과 edge cache
- Rate limiting
- AI Agent workflow와 harness
- production Secret 값의 문서 또는 로그 노출
- 사람이 승인해야 하는 다음 작업의 자동 실행
  - PR merge
  - `kubectl apply/delete/patch/edit/rollout`
  - Argo CD Sync
  - Secret 변경
  - production 부하 테스트
  - Redis 중단 및 장애 주입

## Expected files

작업 중 실제 repository 구조를 확인한 뒤 최소 범위로 수정한다.

예상 Backend 파일:

```
app/api/*topics*.py
app/services/*topic*.py
app/repositories/*topic*.py
app/core/config.py
app/core/redis.py 또는 동등한 Redis client 모듈
requirements.txt
```

예상 Test 파일:

```
tests/api/*topics_home*.py
tests/services/*cache*.py
```

예상 K3s/운영 파일:

```
k8s/news-api.yaml
k8s/redis.yaml 또는 동등한 Redis Deployment/Service manifest
k8s/argocd/*
```

예상 부하 테스트 파일:

```
load-tests/topics-home.js
scripts/load_test_topics_home.*
```

예상 문서 파일:

```
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/design/home-api-redis-cache.md
docs/tasks/feature-home-api-redis-cache.md
docs/reviews/feature-home-api-redis-cache-coderabbit.md
docs/fixes/feature-home-api-redis-cache-approved-fixes.md
docs/verification/feature-home-api-redis-cache.md
docs/pr/feature-home-api-redis-cache.md
docs/devlog/feature-home-api-redis-cache.md
```

실제 파일명과 책임 구조가 다르면 기존 구조를 우선한다. 같은 목적의 Redis client, config, metrics 모듈을 중복 생성하지 않는다.

구현 전에 다음 항목을 조사한다.

- `/topics/home`의 실제 Route, Service, Repository와 SQL 경로
- 응답 데이터 생성 주기와 stale 허용 범위
- 기존 Redis dependency, config, local 실행 지원 여부
- Backend replica와 resource requests/limits
- 현재 metrics와 로그에서 확인 가능한 항목
- 운영 Redis 배치 후보와 node resource 여유
- 기존 Argo CD Application이 관리하는 manifest 범위
- 부하 테스트 도구와 production 실행 승인 경계

## DB changes

원칙적으로 없음.

- migration file 추가 없음
- table, column, index, constraint 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음

Baseline 조사에서 DB query 자체가 병목으로 확인되더라도 이번 Task에서는 schema/index 변경을 즉시 포함하지 않는다. Redis 적용 전후 결과와 별도로 기록하고, index나 query 개선이 필요하면 후속 Task로 분리한다.

## API changes

외부 API 계약 변경 없음.

- endpoint path 유지: `GET /topics/home`
- request parameter 변경 없음
- response schema 변경 없음
- 인증과 권한 정책 변경 없음
- Cache hit 여부를 외부 response body에 추가하지 않음

내부 동작만 다음과 같이 변경한다.

```
Request
→ Redis GET
  ├─ HIT: cached response 반환
  └─ MISS: PostgreSQL 조회
           → Redis SET with TTL
           → response 반환
```

Redis 오류 시:

```
Redis timeout / connection / payload error
→ Cache bypass 기록
→ PostgreSQL 직접 조회
→ 기존 response schema로 정상 응답
```

## Test commands

### 현재 구조 조사

```bash
rg -n "topics/home|home_topics|topics_home|Redis|redis" app tests k8s requirements.txt
```

```bash
rg -n "replicas:|resources:|requests:|limits:|image:" k8s/news-api.yaml
```

### 변경 범위 확인

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

### Unit / Integration Test

실제 프로젝트 test command를 확인한 뒤 해당 명령을 사용한다.

```bash
pytest -q
```

Cache 관련 최소 검증 항목:

- Cache miss 시 PostgreSQL 조회 후 Cache 저장
- Cache hit 시 PostgreSQL 미호출
- TTL 만료 후 PostgreSQL 재조회
- Redis connection 실패 시 PostgreSQL fallback
- Redis GET 실패 시 PostgreSQL fallback
- Redis SET 실패 시 응답 정상 유지
- Redis timeout 시 PostgreSQL fallback
- 손상된 Cache payload 발견 시 폐기 후 PostgreSQL 재조회
- 기존 `/topics/home` response schema 유지
- Redis 미설정 환경에서도 애플리케이션 기동 가능 여부 또는 명시적 설정 실패 정책 확인

### Baseline / After 부하 테스트

부하 테스트 도구와 script는 UNIT-01에서 확정한다. `k6`를 사용할 경우 기본 실행 예시는 다음과 같다.

```bash
k6 run load-tests/topics-home.js
```

동시 사용자 단계 예시:

```
1 → 10 → 25 → 50 → 100
```

각 단계에서 기록할 값:

- p50
- p95
- p99
- RPS
- error rate
- 테스트 duration
- Backend Pod CPU/Memory
- 가능한 범위의 DB connection/query 상태

Production endpoint에 대한 부하 테스트는 사람 승인 없이 실행하지 않는다. 먼저 로컬 또는 제한된 검증 환경에서 수행한다.

### Local Redis 확인

실제 로컬 실행 방식을 조사한 뒤 Docker Compose 또는 단일 Container를 사용한다.

```bash
redis-cli ping
```

기대 결과:

```
PONG
```

### K8s Manifest 확인

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

기대 결과: 금지 영역의 신규 변경 없음.

### 운영 확인

다음 작업은 사람이 승인한 뒤 실행하고 결과를 Verification에 기록한다.

```
Argo CD OutOfSync와 diff 확인
→ Manual Sync
→ Redis Deployment/Service 상태 확인
→ Backend rollout 확인
→ /health 확인
→ /topics/home 정상 응답 확인
→ Cache hit/miss 확인
```

모든 `kubectl` 명령은 다음 prefix를 사용한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl ...
```

Redis 장애 검증은 사람이 승인한 환경에서만 수행한다.

```
정상 상태에서 Cache HIT 확인
→ Redis 중단
→ /topics/home이 PostgreSQL fallback으로 정상 응답하는지 확인
→ Redis 복구
→ MISS 후 재저장
→ 이후 HIT 확인
```

## Acceptance criteria

- Redis 적용 전 `/topics/home` Baseline 부하 테스트 결과가 기록돼 있다.
- Baseline에는 p50, p95, p99, RPS, 오류율과 테스트 조건이 포함된다.
- 가능한 범위에서 Backend Pod CPU/Memory와 DB 부하가 함께 기록된다.
- Cache 적용 여부가 추측이 아니라 Baseline과 조회 구조 분석을 근거로 결정된다.
- `/topics/home`에 Cache-aside 패턴이 적용된다.
- Cache key naming과 TTL 선택 근거가 문서화된다.
- PostgreSQL이 source of truth로 유지된다.
- Cache hit 시 PostgreSQL 조회가 발생하지 않음을 테스트로 확인한다.
- Cache miss 시 PostgreSQL 조회 후 Cache 저장이 수행된다.
- Redis GET/SET/connection/timeout 오류가 API 실패로 전파되지 않는다.
- Redis 장애 시 PostgreSQL fallback으로 기존 response schema의 정상 응답을 유지한다.
- 손상된 Cache payload를 감지하고 PostgreSQL 재조회로 복구한다.
- Cache hit, miss, bypass를 로그 또는 metrics에서 구분할 수 있다.
- Redis 적용 전후를 같은 부하 조건으로 비교한다.
- 개선되지 않은 지표가 있으면 성공으로 과장하지 않고 원인을 기록한다.
- Redis 중단과 복구 후 `/topics/home`의 연속 동작을 검증한다.
- K3s 반영 후 Backend rollout, Redis 상태, `/health`, `/topics/home`이 정상이다.
- Argo CD Manual Sync와 사람 승인 경계가 유지된다.
- API, DB schema, Frontend, AI pipeline, CronJob schedule에 회귀가 없다.
- HPA는 이번 Task에 포함하지 않는다.
- Architecture, Runbook, Verification, PR, devlog에 실제 결과와 트레이드오프가 기록된다.
- 실행하지 않은 production 검증은 통과로 기록하지 않는다.

## Notes

- Redis는 source of truth가 아니라 삭제 가능한 성능 최적화 계층이다.
- 기본 장애 정책은 fail-open이다. Redis 장애 시 성능은 저하될 수 있지만 서비스는 PostgreSQL 직접 조회로 계속 동작해야 한다.
- 초기 Cache key 후보는 `topics:home:v1`, TTL 후보는 60초다. 둘 다 조사와 측정 결과를 근거로 확정한다.
- Cache stampede 가능성을 조사하되, 현재 규모에서 필요성이 입증되지 않으면 distributed lock이나 stale-while-revalidate는 도입하지 않는다.
- Redis persistence는 이번 Task의 핵심 요구가 아니다. Cache 데이터는 재생성 가능해야 한다.
- 운영 Redis를 Raspberry Pi Worker에 배치할지 Oracle Cloud Worker에 배치할지는 node reliability, network path, resource 여유를 확인한 뒤 결정한다.
- `news-api` Pod와 Redis의 resource requests/limits는 추측값으로 확정하지 않고 초기값과 근거를 기록한다.
- HPA는 Redis 적용 후에도 API CPU 또는 처리량 한계가 확인될 때 후속 Task로 진행한다.
- 최종 성과는 단순히 Redis를 추가했다는 사실이 아니라, 측정 → 병목 판단 → Cache 적용 → Before/After 비교 → 장애 복구 검증까지 연결하는 것이다.

## Implementation Units

- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [x] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [x] UNIT-05: Unit/Integration Test
- [x] UNIT-06: K3s와 운영 설정 반영
- [x] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [x] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
