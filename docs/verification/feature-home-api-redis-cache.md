# Verification: Home API 부하 측정 및 Redis Cache 적용

## Verification Status

passed

- UNIT-01부터 UNIT-08까지 모두 완료했다.
- Production Redis 적용, 적용 후 부하 테스트, 장애·복구 검증을 완료했다.
- 최종 로컬 전체 test, Kubernetes YAML parse, `git diff --check`가 모두 통과했다.
- 운영 상태는 Argo CD `Synced / Healthy`, Backend 2/2 Ready, Redis 1/1 Ready, restart 0으로 확인했다.

## Verification Scope

- `/topics/home` Redis cache-aside 구현과 fail-open 동작
- Cache hit, miss, store, bypass 구분 가능성
- Redis 미설정, 설정 오류, 연결 오류 시 PostgreSQL fallback
- Kubernetes manifest 문법과 immutable image 정책 확인
- Redis 적용 전·후 동일 조건 Production 부하 측정
- Redis 장애·복구 end-to-end 검증
- Argo CD Manual Sync와 운영 상태 확인
- 문서와 checklist 동기화

## Environment

- 실행일: 2026-07-13
- 구현 branch: `feature/home-api-redis-cache`
- 운영 검증 branch: `test/home-api-redis-cache-verification`
- 대상 endpoint: `https://api.dev-scj.site/topics/home`
- Health endpoint: `https://api.dev-scj.site/health`
- 적용 Backend image: `seocj/news-api:6c988f8540ae873901d6182d66eeb351b767e160`
- Argo CD sync revision: `209fa378546c54ecf808919c0c8c687aa2f20174`
- Backend replica: 2
- Redis image: `redis:7.2-alpine`
- Redis replica: 1
- Redis Service: `news-redis`, ClusterIP, `6379/TCP`
- Cache key: `topics:home:v1`
- Cache TTL: 60초
- Redis timeout: 0.05초
- k6: `v2.1.0 (commit/devel, go1.26.4, darwin/arm64)`
- Fixed-VU duration: 30초
- 각 iteration sleep: 1초

## Local Test and Static Verification

### Immutable image assertion

```bash
rg -n 'seocj/news-api:latest' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result:

- 출력 없음
- exit code 1
- stale `latest` expectation 제거 확인

```bash
rg -n \
  'assertRegex|[0-9a-f].*40|news-api' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result:

- `^seocj/news-api:[0-9a-f]{40}$` 형식 검증
- 각 CronJob image와 Backend Deployment image 정합성 검증
- 특정 현재 SHA를 test에 하드코딩하지 않음

### Targeted test

```bash
PYTHONPATH=. pytest -q \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result: `10 passed in 0.04s`

```bash
PYTHONPATH=. pytest -q tests/test_topics_api.py
```

Result: `15 passed in 0.39s`

포함 범위:

- cache miss, hit, TTL 만료
- Redis GET timeout, connection 오류, SET 실패
- 손상된 payload fallback
- malformed `REDIS_URL`
- unsupported Redis URL scheme
- 잘못된 URL에서 disabled cache 전환과 PostgreSQL fallback
- warning log에 credential 미포함
- 기존 response schema 유지

```bash
PYTHONPATH=. pytest -q tests/test_home_api_redis_k8s_manifest.py
```

Result: `4 passed in 0.02s`

### 전체 test

마지막 구현·리뷰 수정 기준:

```bash
PYTHONPATH=. pytest -q
```

Result: `422 passed, 78 subtests passed in 15.92s`

Notes:

- 기준 commit `15c686ef` 별도 worktree에서는 `406 passed, 3 failed, 78 subtests passed`였다.
- 세 실패는 stale `seocj/news-api:latest` assertion이었다.
- Round 2의 malformed/unsupported Redis URL fallback test 2건을 포함한다.
- 운영 검증과 문서 수정 이후 최종 전체 suite를 재실행했으며 실패 0건이었다.

### YAML and diff

```bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

Result:

- `k8s/cluster-issuer.yaml` parse 통과
- `k8s/news-api.yaml` parse 통과
- 네 CronJob manifest parse 통과
- `k8s/redis.yaml` parse 통과

```bash
git diff --check
```

Result: no output

```bash
git diff --name-only -- db migrations frontend
```

Result: no output

DB migration과 frontend 변경은 없다.

## UNIT-02 Redis 적용 전 Production Baseline

### Ramp test

부하 조건:

- 1 → 10 → 25 → 50 → 100 → 0 VU
- 각 stage 30초
- 총 실행 시간 약 3분

| Metric                 | Value                       |
| ---------------------- | --------------------------- |
| ---                    | ---:                        |
| Requests               | 3,280                       |
| RPS                    | 18.075                      |
| Average                | 694.14ms                    |
| p50                    | 547.61ms                    |
| p95                    | 1.17s                       |
| p99                    | 1.36s                       |
| Max                    | 1.97s                       |
| HTTP failures          | 1 / 3,280                   |
| Error rate             | 0.03%                       |
| Completed iterations   | 3,280                       |
| Interrupted iterations | 0                           |
| Threshold              | `http_req_failed < 1%` 통과 |

### Fixed-VU Baseline

| VU   | Duration | Requests | RPS   | Average  | p50      | p95      | p99      | Error rate |
| ---- | -------- | -------- | ----- | -------- | -------- | -------- | -------- | ---------- |
| ---: | ---:     | ---:     | ---:  | ---:     | ---:     | ---:     | ---:     | ---:       |
| 1    | 30s      | 19       | 0.63  | 562.52ms | 533.19ms | 764.68ms | 769.29ms | 0%         |
| 10   | 30s      | 194      | 6.15  | 552.55ms | 516.40ms | 685.31ms | 701.10ms | 0%         |
| 25   | 30s      | 438      | 13.87 | 717.63ms | 519.78ms | 1.51s    | 1.97s    | 0%         |
| 50   | 30s      | 938      | 29.07 | 604.51ms | 516.53ms | 1.35s    | 1.77s    | 0%         |
| 100  | 30s      | 1,310    | 40.50 | 1.31s    | 1.22s    | 2.20s    | 3.25s    | 0%         |

All stages:

- response schema check 100% 통과
- HTTP failure 0건
- interrupted iteration 0건
- Backend Pod 2/2 Ready
- Backend restart 0
- `/health` 정상

### Baseline resource snapshots

| VU   | Pod 1 CPU | Pod 2 CPU | Pod 1 Memory | Pod 2 Memory |
| ---- | --------- | --------- | ------------ | ------------ |
| ---: | ---:      | ---:      | ---:         | ---:         |
| 1    | 2m        | 2m        | 65Mi         | 65Mi         |
| 10   | 17m       | 18m       | 65Mi         | 65Mi         |
| 25   | 44m       | 47m       | 66Mi         | 66Mi         |
| 50   | 79m       | 81m       | 67Mi         | 67Mi         |
| 100  | 63m       | 29m       | 69Mi         | 70Mi         |

위 값은 각 테스트 종료 직후 snapshot이며 peak 값이 아니다.

## UNIT-06 K3s 운영 반영

### Argo CD diff

예상 변경만 확인했다.

- `news-api` image:
  - Before: `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
  - After: `seocj/news-api:6c988f8540ae873901d6182d66eeb351b767e160`
- `news-api` 환경변수 추가:
  - `REDIS_URL=redis://news-redis:6379/0`
  - `HOME_TOPICS_CACHE_TTL_SECONDS=60`
  - `REDIS_TIMEOUT_SECONDS=0.05`
- 신규 `Deployment/news-redis`
- 신규 `Service/news-redis`
- 네 CronJob image를 새 immutable Backend image로 갱신
- Service, Ingress, Secret 삭제 없음
- Prune 대상 없음

### Manual Sync

```bash
argocd app sync news-api \
  --server localhost:8080 \
  --insecure
```

Result:

- Operation phase: `Succeeded`
- Sync status: `Synced`
- Sync revision: `209fa378546c54ecf808919c0c8c687aa2f20174`

### Rollout

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl rollout status deployment/news-redis \
  -n default \
  --timeout=180s
```

Result: `deployment "news-redis" successfully rolled out`

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl rollout status deployment/news-api \
  -n default \
  --timeout=300s
```

Result: `deployment "news-api" successfully rolled out`

### Runtime state

- `news-api`: 2/2 Ready
- `news-redis`: 1/1 Ready
- `news-api` Pod 2개: Running, restart 0
- `news-redis` Pod 1개: Running, restart 0
- `news-redis` Service: ClusterIP, `6379/TCP`
- 모든 Pod가 `arm-worker-node`에 배치됨
- `/health`: HTTP 200, `status=ok`
- `/topics/home`: HTTP 200, 기존 schema 유지

### Cache connection and TTL

첫 요청 후 Redis key를 직접 확인했다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl exec \
  -n default \
  deployment/news-redis \
  -- redis-cli EXISTS topics:home:v1
```

Result: `1`

요청 직후 TTL은 `59`, 후속 요청 뒤 TTL은 `41`이었다. TTL이 다시 60으로 초기화되지 않고 감소해 기존 cache hit을 확인했다.

운영 Backend 로그에서 `home_topics_cache event=` 문자열은 확인되지 않았다. 기능 검증은 Redis key 존재와 TTL 감소를 직접 확인하는 방식으로 대체했다. 로그 가시성은 별도 observability 개선 후보로 남긴다.

### Final Argo state after deployment

```
NAME       SYNC     HEALTH    REVISION
news-api   Synced   Healthy   209fa378546c54ecf808919c0c8c687aa2f20174
```

UNIT-06 Status: passed

## UNIT-07 Redis 적용 후 Fixed-VU Test

### Test command

각 VU 단계에서 동일한 스크립트와 endpoint를 사용했다.

```bash
k6 run \
  --summary-trend-stats='avg,min,med,p(90),p(95),p(99),max' \
  -e BASE_URL=https://api.dev-scj.site \
  -e VUS=<1|10|25|50|100> \
  -e DURATION=30s \
  load-tests/topics-home-fixed.js
```

각 단계 전에 60초 TTL 만료를 확인해 cold-cache 시작 조건을 유지했다.

### After results

| VU   | Duration | Requests | RPS   | Average  | p50     | p95      | p99      | Error rate |
| ---- | -------- | -------- | ----- | -------- | ------- | -------- | -------- | ---------- |
| ---: | ---:     | ---:     | ---:  | ---:     | ---:    | ---:     | ---:     | ---:       |
| 1    | 30s      | 29       | 0.94  | 42.96ms  | 19.14ms | 35.65ms  | 518.84ms | 0%         |
| 10   | 30s      | 273      | 8.82  | 82.96ms  | 18.18ms | 33.27ms  | 2.00s    | 0%         |
| 25   | 30s      | 635      | 20.68 | 71.30ms  | 20.29ms | 93.07ms  | 1.59s    | 0%         |
| 50   | 30s      | 1,359    | 43.88 | 97.45ms  | 22.46ms | 266.14ms | 2.12s    | 0%         |
| 100  | 30s      | 2,683    | 86.59 | 110.57ms | 26.05ms | 412.41ms | 2.25s    | 0%         |

All stages:

- response schema check 100% 통과
- HTTP failure 0건
- interrupted iteration 0건
- Backend Pod 2/2 Ready
- Redis Pod 1/1 Ready
- 모든 Pod restart 0
- `/health` 정상

### Before and After comparison

| VU   | RPS Before → After | Average Before → After | p50 Before → After | p95 Before → After | p99 Before → After  |
| ---- | ------------------ | ---------------------- | ------------------ | ------------------ | ------------------- |
| ---: | ---                | ---                    | ---                | ---                | ---                 |
| 1    | 0.63 → 0.94        | 562.52ms → 42.96ms     | 533.19ms → 19.14ms | 764.68ms → 35.65ms | 769.29ms → 518.84ms |
| 10   | 6.15 → 8.82        | 552.55ms → 82.96ms     | 516.40ms → 18.18ms | 685.31ms → 33.27ms | 701.10ms → 2.00s    |
| 25   | 13.87 → 20.68      | 717.63ms → 71.30ms     | 519.78ms → 20.29ms | 1.51s → 93.07ms    | 1.97s → 1.59s       |
| 50   | 29.07 → 43.88      | 604.51ms → 97.45ms     | 516.53ms → 22.46ms | 1.35s → 266.14ms   | 1.77s → 2.12s       |
| 100  | 40.50 → 86.59      | 1.31s → 110.57ms       | 1.22s → 26.05ms    | 2.20s → 412.41ms   | 3.25s → 2.25s       |

### Performance interpretation

- 100 VU에서 RPS는 `40.50 → 86.59`로 약 113.8% 증가했다.
- 100 VU 평균 응답시간은 `1.31s → 110.57ms`로 약 91.6% 감소했다.
- 100 VU p50은 `1.22s → 26.05ms`로 약 97.9% 감소했다.
- 100 VU p95는 `2.20s → 412.41ms`로 약 81.3% 감소했다.
- 100 VU p99는 `3.25s → 2.25s`로 약 30.8% 감소했다.
- 50 VU에서 100 VU로 VU를 두 배로 늘렸을 때 RPS 증가율은 Before 약 39%, After 약 97%였다.
- Redis 적용 전 50~100 VU 구간에서 보였던 포화 징후가 이번 테스트 범위에서는 크게 완화됐다.
- 10 VU와 50 VU의 p99는 Before보다 높았다. 각 테스트를 cold-cache 상태에서 시작했기 때문에 일부 긴 요청이 포함됐을 가능성이 있으나, 요청별 trace와 DB 지표가 없으므로 원인을 단정하지 않는다.
- 모든 단계에서 HTTP 오류와 Pod restart는 0건이었다.

### After resource snapshots

| VU   | API Pod 1 CPU | API Pod 2 CPU | API Pod 1 Memory | API Pod 2 Memory | Redis CPU | Redis Memory |
| ---- | ------------- | ------------- | ---------------- | ---------------- | --------- | ------------ |
| ---: | ---:          | ---:          | ---:             | ---:             | ---:      | ---:         |
| 1    | 1m            | 2m            | 63Mi             | 63Mi             | 2m        | 3Mi          |
| 10   | 12m           | 11m           | 65Mi             | 65Mi             | 3m        | 3Mi          |
| 25   | 31m           | 26m           | 67Mi             | 67Mi             | 4m        | 3Mi          |
| 50   | 49m           | 38m           | 69Mi             | 68Mi             | 6m        | 3Mi          |
| 100  | 2m            | 2m            | 70Mi             | 70Mi             | 2m        | 3Mi          |

위 값은 테스트 종료 직후 snapshot이며 peak CPU 또는 peak memory가 아니다. 100 VU CPU가 낮게 표시된 것은 측정 시점 차이의 영향을 받는다.

UNIT-07 Status: passed

## UNIT-08 Redis 장애·복구 Verification

### Pre-outage state

- `news-api`: 2/2 Ready
- `news-redis`: desired 1, ready 1, available 1
- `topics:home:v1`: `EXISTS=1`
- `/health`: HTTP 200

### Redis outage injection

사람이 승인하고 직접 실행했다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl scale deployment/news-redis \
  -n default \
  --replicas=0
```

Result:

- `news-redis` Deployment: 0/0
- Redis Pod: 없음
- `news-api`: 2/2 Running, restart 0

### Fail-open result

```bash
curl -sS \
  -o /tmp/topics-home-redis-down.json \
  -w 'http_code=%{http_code} time_total=%{time_total}s\n' \
  https://api.dev-scj.site/topics/home
```

Result:

```
http_code=200 time_total=0.846616s
```

Response validation:

```
generated_at: True
topic_date: 2026-07-13
items: 10
```

Redis Pod가 없는 상태에서도 `/topics/home`은 PostgreSQL fallback을 통해 HTTP 200과 기존 response schema를 유지했다.

### Redis recovery

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl scale deployment/news-redis \
  -n default \
  --replicas=1
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl rollout status deployment/news-redis \
  -n default \
  --timeout=180s
```

Result:

- Redis rollout 성공
- `news-redis`: 1/1 Ready
- 새 Redis Pod: Running, restart 0
- Backend Pod 2개: Running, restart 0

Persistence가 비활성화돼 있으므로 복구 직후 cache key는 없었다.

```
EXISTS topics:home:v1 = 0
```

### Recovery miss, store, hit

복구 후 첫 요청:

```
http_code=200
time_total=0.770431s
TTL=60
```

빈 Redis에서 PostgreSQL 조회 후 cache 저장과 TTL 설정을 확인했다.

수동 단계 사이에 key가 다시 만료된 뒤 실행한 요청:

```
http_code=200
time_total=0.930226s
TTL=60
```

TTL이 60으로 재설정돼 새로운 miss/store가 발생했음을 확인했다.

바로 이어서 실행한 후속 요청:

```
http_code=200
time_total=0.049407s
TTL=54
```

응답시간이 약 49ms로 감소했고 TTL이 초기화되지 않고 감소해 cache hit을 확인했다.

### Final operational state

```
news-api Deployment: 2/2
news-redis Deployment: 1/1
news-api Pod 2개: Running, restart 0
news-redis Pod 1개: Running, restart 0
Argo CD: Synced / Healthy
Argo revision: 209fa378546c54ecf808919c0c8c687aa2f20174
/health: status=ok
```

UNIT-08 Production outage and recovery verification: passed

## Results

### Cache implementation

- Cache key: `topics:home:v1`
- TTL: 60초
- Redis timeout: 0.05초
- Redis 미설정 환경: disabled cache 상태로 application import 가능
- Cache hit: DB connection factory 미호출 test 통과
- Cache miss: PostgreSQL 조회 후 Redis 저장 test 통과
- Redis GET, SET, connection, timeout 오류: PostgreSQL fallback test 통과
- malformed 또는 unsupported Redis URL: disabled cache 전환 후 PostgreSQL fallback test 통과
- 손상된 payload: decode 실패 후 PostgreSQL fallback test 통과
- 운영 Redis key 생성, TTL, hit 확인
- 운영 Redis 중단 시 fail-open 확인
- 운영 Redis 복구 후 miss → store → hit 확인

### Operational conclusion

- Redis는 `/topics/home`의 반복 조회 지연과 DB 접근을 줄이는 cache-aside 계층으로 정상 동작한다.
- Redis가 중단돼도 API는 PostgreSQL fallback으로 HTTP 200을 유지한다.
- Redis 적용 후 모든 fixed-VU 단계에서 오류율 0%를 유지했다.
- 100 VU 처리량은 40.50 RPS에서 86.59 RPS로 증가했다.
- 평균, p50, p95 지연은 전 VU 구간에서 크게 감소했다.
- 소수의 cold-cache tail latency가 남았으며 p99 원인 분석에는 요청 trace와 DB 지표가 추가로 필요하다.
- 운영 cache event 로그가 현재 수집 로그에서 보이지 않아 key와 TTL을 직접 확인했다. 로그 가시성 개선은 후속 작업 후보다.

## Task Checklist State to Sync

```markdown
- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [x] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [x] UNIT-05: Unit/Integration Test
- [x] UNIT-06: K3s와 운영 설정 반영
- [x] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [x] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
```

UNIT-08의 Production 장애·복구 검증은 완료했다. 아래 최종 로컬 검증과 문서 동기화가 끝난 뒤 `[x]`로 변경한다.

## Final Verification Pending

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

```bash
git diff --check
```

```bash
git status --short
```

완료 조건:

- 전체 test 실패 0건
- 모든 K8s YAML parse 통과
- `git diff --check` exit code 0
- Task와 Verification 문서 상태 동기화
- UNIT-08 `[x]`
- Verification Status를 `passed`로 변경

## Evidence Notes

- Production Baseline, Redis 적용 후 k6, Argo CD Manual Sync, Redis scale down/up은 사람이 승인하고 직접 실행했다.
- Agent는 Production mutation을 실행하지 않았다.
- Ramp 결과는 전체 구간 집계값이고 Before/After 비교의 기준은 fixed-VU 결과다.
- `.agent-runs/home-api-redis-after/` 로그는 로컬 실행 증거이며 저장소 커밋 대상이 아니다.
- Resource 값은 테스트 종료 직후 snapshot이며 peak 관측값이 아니다.
- PostgreSQL connection 또는 query 수치는 별도로 수집하지 않아 DB 부하 감소량을 정량적으로 단정하지 않는다.

## Final Technical Verification

### Full test suite

```bash
PYTHONPATH=. pytest -q
```

Result:

```
422 passed, 78 subtests passed in 15.92s
```

Status: passed

검증 범위:

- `/topics/home` cache hit, miss, TTL 만료
- Redis GET timeout, connection 오류, SET 실패
- malformed 및 unsupported `REDIS_URL` fail-open
- 손상된 cache payload fallback
- 기존 response schema 유지
- Kubernetes Redis manifest 및 Backend Redis 환경변수
- 기존 topic pipeline과 CronJob manifest 회귀 test

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

Result:

```
ok k8s/cluster-issuer.yaml
ok k8s/news-api.yaml
ok k8s/news-daily-topic-pipeline-cronjob.yaml
ok k8s/news-rss-collector-cronjob.yaml
ok k8s/news-three-day-topic-pipeline-cronjob.yaml
ok k8s/news-weekly-topic-pipeline-cronjob.yaml
ok k8s/redis.yaml
```

Status: passed

### Diff validation

```bash
git diff --check
```

Result: no output

Status: passed

공백 오류, trailing whitespace, conflict marker는 확인되지 않았다.

### Final production state

- Argo CD: `Synced / Healthy`
- Sync revision: `209fa378546c54ecf808919c0c8c687aa2f20174`
- Backend image: `seocj/news-api:6c988f8540ae873901d6182d66eeb351b767e160`
- `news-api`: 2/2 Ready, restart 0
- `news-redis`: 1/1 Ready, restart 0
- `/health`: HTTP 200, `status=ok`
- Redis 중단 중 `/topics/home`: HTTP 200, items 10
- Redis 복구 후: `EXISTS=0 → miss/store TTL 60 → hit 49ms, TTL 54`

## Final Decision

Verification Status: `passed`

Redis cache-aside 적용 전·후 성능 비교, K3s 운영 반영, Redis 장애 시 PostgreSQL fail-open, Redis 복구 후 cache 재생성, 전체 회귀 test와 manifest 정적 검증을 모두 완료했다.

현재 확인된 제한:

- Backend 운영 로그에서 `home_topics_cache event=`가 노출되지 않아 hit/miss/store/bypass의 로그 기반 확인은 수행하지 못했다.
- 기능 동작은 Redis key 존재, TTL 변화, 응답 시간, 장애 중 HTTP 200으로 검증했다.
- CPU와 Memory 값은 각 부하 테스트 종료 직후 snapshot이며 peak 값이 아니다.
- PostgreSQL query 수와 connection 수를 직접 수집하지 않아 DB 부하 감소량을 정량화하지 않았다.
- Cold-cache 동시 요청에서 p99 tail latency가 남아 있으며 cache stampede 가능성은 별도 개선 후보다.
