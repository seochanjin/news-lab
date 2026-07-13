# Verification: Home API 부하 측정 및 Redis Cache 적용

## Verification Status

pending

- UNIT-02 Redis 적용 전 Baseline 부하 테스트는 완료했다.
- UNIT-06 K3s 운영 설정 manifest와 문서 반영은 완료했다.
- UNIT-07 Redis 적용 후 동일 조건 비교, UNIT-08 장애·복구 검증과 최종 문서화가 남아 있으므로 전체 Verification은 아직 `pending`이다.

## Verification Scope

- `/topics/home` Redis cache-aside 구현과 fail-open 동작
- Cache hit, miss, store, bypass 구분 가능성
- Redis 미설정 및 Redis 오류 시 PostgreSQL fallback
- Kubernetes manifest 문법과 immutable image 정책 확인
- Redis 적용 전 Production Baseline 부하 측정
- 문서와 checklist 동기화
- Production 배포, Redis 적용 후 부하 테스트, Redis 장애·복구 주입은 사람이 수행

## Environment

- 실행일: 2026-07-13
- Branch: `feature/home-api-redis-cache`
- 대상 endpoint: `https://api.dev-scj.site/topics/home`
- Health endpoint: `https://api.dev-scj.site/health`
- Backend image: `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- Backend replica: 2
- Backend Pod: 2/2 Ready, restart 0
- Redis 적용 상태: 운영 manifest 반영 준비 완료, Production 미적용
- k6: `v2.1.0 (commit/devel, go1.26.4, darwin/arm64)`
- 각 고정 VU 테스트 duration: 30초
- 각 iteration sleep: 1초

## Commands Run

### Immutable image assertion 정리

```bash
rg -n 'seocj/news-api:latest' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result:

- 출력 없음
- exit code 1

Status: passed

Notes: 세 CronJob manifest test에서 stale `latest` image 기대값이 제거됐다.

```bash
rg -n \
  'assertRegex|[0-9a-f].*40|news-api' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result:

- 세 test 파일 모두 `k8s/news-api.yaml`의 Backend Deployment image를 읽는다.
- `^seocj/news-api:[0-9a-f]{40}$` 형식을 검증한다.
- Backend workload image 정합성과 `news-api-secret` 검증을 유지한다.

Status: passed

### Targeted 및 전체 test

```bash
PYTHONPATH=. pytest -q \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

Result: `10 passed in 0.04s`

Status: passed

```bash
PYTHONPATH=. pytest -q tests/test_topics_api.py
```

Result: `13 passed in 0.27s`

Status: passed

Notes: cache miss, hit, TTL 만료, Redis GET timeout, connection 오류, SET 실패, 손상 payload fallback, 기존 response schema 유지를 포함한다.

```bash
PYTHONPATH=. pytest -q tests/test_home_api_redis_k8s_manifest.py
```

Result: `4 passed in 0.02s`

Status: passed

Notes: `news-api` Redis env, `news-redis` Deployment/Service, Argo CD Manual Sync 경계를 로컬 YAML 파싱으로 확인했다.

```bash
PYTHONPATH=. pytest -q
```

Result: `420 passed, 78 subtests passed in 15.00s`

Status: passed

Notes:

- 기준 commit `15c686ef` 별도 worktree에서는 `406 passed, 3 failed, 78 subtests passed`였다.
- 세 실패는 stale `seocj/news-api:latest` assertion이었다.
- Fix와 UNIT-06 manifest test 추가 이후 전체 suite는 0 failed다.

### YAML, diff, 범위 확인

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
- 4개 CronJob manifest parse 통과
- `k8s/redis.yaml` parse 통과

Status: passed

```bash
rg -n "seocj/news-api:latest|generated resource.*7|7개|일곱 resource|Backend resource 7" \
  docs/architecture/k3s-runtime.md \
  docs/architecture/argocd-manual-sync-design.md \
  docs/runbooks/argocd-manual-sync-plan.md \
  docs/RUNBOOK.md
```

Result:

- `docs/architecture/k3s-runtime.md`, `docs/RUNBOOK.md`의 현재 운영 기준에서는 출력 없음
- `docs/architecture/argocd-manual-sync-design.md`, `docs/runbooks/argocd-manual-sync-plan.md`의 과거 baseline section에만 `latest`와 최초 Argo CD resource 7개 기록이 남아 있음

Status: passed

Notes: 현재 Redis 반영 후 Argo CD generated resource 기준은 `news-api`, `news-redis`, 네 CronJob을 포함한 9개로 문서화했다. Historical baseline 기록은 당시 상태 보존 목적이라 수정하지 않았다.

```bash
git diff --check
```

Result: no output

Status: passed

```bash
git diff --name-only -- db migrations frontend
```

Result: no output

Status: passed

Notes: DB migration과 frontend 변경이 없다.

### Production Redis 미적용 상태 확인

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get deploy news-api \
  -n default \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Result:

```
seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get deploy news-api \
  -n default \
  -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}{"\n"}{end}' \
  | grep -i redis || true
```

Result: no output

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get secret news-api-secret \
  -n default \
  -o go-template='{{range $key, $value := .data}}{{printf "%s\n" $key}}{{end}}' \
  | grep -i redis || true
```

Result: no output

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get deployment,service \
  -n default \
  | grep -i redis || true
```

Result: no output

Status: passed

Notes: 현재 Production은 Redis 미적용 상태이므로 Redis 적용 전 Baseline 대상으로 사용했다.

### Remote DB 안전성 확인

```bash
REDIS_URL= python - <<'PY'
from dotenv import load_dotenv
from urllib.parse import urlparse
import os
load_dotenv(dotenv_path='.env')
url = os.getenv('DATABASE_URL')
if not url:
    print('database_url=missing')
    raise SystemExit(1)
host = urlparse(url).hostname or ''
print('database_target=local' if host in {'localhost', '127.0.0.1', '::1'} else 'database_target=nonlocal')
PY
```

Result: `database_target=nonlocal`

Status: passed

Notes: local FastAPI를 실행해도 remote Supabase PostgreSQL을 사용하므로 local HTTP endpoint를 안전한 local DB 부하 테스트 대상으로 취급하지 않았다. Production 테스트는 사람이 승인하고 직접 실행했다.

## UNIT-02 Redis 적용 전 Production Baseline

### Ramp test

부하 조건:

- 1 → 10 → 25 → 50 → 100 → 0 VU
- 각 stage 30초
- 총 실행 시간 약 3분

Result:

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

Notes:

- `status is 200`과 `has home payload`가 동일 실패 응답에서 각각 한 번 실패했다.
- 전체 ramp 안정성 확인에는 유효하지만 단계별 비교를 위해 고정 VU 테스트를 추가 수행했다.

### Fixed-VU script validation

초기 생성 파일은 line 4의 invalid character 때문에 parse 실패했고 실제 부하는 발생하지 않았다. 파일을 ASCII 내용으로 다시 생성한 뒤 검증했다.

```bash
k6 inspect load-tests/topics-home-fixed.js
```

Result:

- `vus: 1`
- `duration: 30s`
- `http_req_failed: rate<0.01`
- parse error 없음

Status: passed

Smoke test:

```bash
k6 run \
  --summary-trend-stats='avg,min,med,p(90),p(95),p(99),max' \
  -e BASE_URL="$BASE_URL" \
  -e VUS=1 \
  -e DURATION=10s \
  load-tests/topics-home-fixed.js
```

Result:

- Requests: 4
- p50: 574.98ms
- p95: 723.5ms
- p99: 738.1ms
- Error rate: 0%

Status: passed

Notes: smoke test는 동작 확인용이며 최종 Baseline 표에는 포함하지 않았다.

### Fixed-VU Baseline results

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
- Backend Pod restart 0
- `/health` 정상

### Resource snapshots after each stage

| VU   | Pod 1 CPU | Pod 2 CPU | Pod 1 Memory | Pod 2 Memory |
| ---- | --------- | --------- | ------------ | ------------ |
| ---: | ---:      | ---:      | ---:         | ---:         |
| 1    | 2m        | 2m        | 65Mi         | 65Mi         |
| 10   | 17m       | 18m       | 65Mi         | 65Mi         |
| 25   | 44m       | 47m       | 66Mi         | 66Mi         |
| 50   | 79m       | 81m       | 67Mi         | 67Mi         |
| 100  | 63m       | 29m       | 69Mi         | 70Mi         |

Notes:

- 위 값은 각 테스트 종료 직후의 snapshot이며 peak CPU 또는 peak memory가 아니다.
- 100 VU CPU가 50 VU보다 낮은 것은 테스트 종료 후 측정 시점 차이의 영향을 받는다.

### Operational health after Baseline

```bash
curl -fsS https://api.dev-scj.site/health
```

Result:

```json
{
  "status": "ok",
  "service": "news-api",
  "hostname": "news-api-5755fd5b99-g9wxc"
}
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get pods -n default \
  -o custom-columns='NAME:.metadata.name,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,NODE:.spec.nodeName' \
  | grep news-api
```

Result:

- `news-api-5755fd5b99-dzflf`: Ready true, restart 0
- `news-api-5755fd5b99-g9wxc`: Ready true, restart 0

Status: passed

## Results

### Cache implementation

- Cache key: `topics:home:v1`
- TTL: 60초
- Redis timeout 기본값: 0.05초
- Redis 미설정 환경: cache disabled 상태로 application import 가능
- Cache hit: DB connection factory를 호출하지 않는 test 통과
- Cache miss: PostgreSQL 조회 후 `SETEX` 저장 test 통과
- Redis GET, SET, connection, timeout 오류: PostgreSQL fallback test 통과
- 손상된 cache payload: decode 실패 후 PostgreSQL fallback test 통과
- Cache event: `home_topics_cache event=hit|miss|store|bypass`
- K8s YAML parse: 통과

### UNIT-06 K3s 운영 설정

- `k8s/news-api.yaml`에 `REDIS_URL=redis://news-redis:6379/0`,
  `HOME_TOPICS_CACHE_TTL_SECONDS=60`, `REDIS_TIMEOUT_SECONDS=0.05`가 추가됐다.
- `k8s/redis.yaml`은 `news-redis` Deployment/Service를 추가한다.
- Redis는 `replicas: 1`, `workload: app` node selector, request `50m/64Mi`,
  limit `250m/128Mi`, `maxmemory 96mb`, `allkeys-lru`로 설정했다.
- Redis persistence는 `--save ""`, `--appendonly no`로 비활성화했다.
- Argo CD `news-api` Application은 `k8s` top-level manifest를 읽으므로 Redis
  Deployment/Service가 generated resource에 포함된다.
- Argo CD `spec.syncPolicy`는 없으며 Manual Sync 경계를 유지한다.
- Architecture와 Runbook은 Redis 운영 반영, 사람 승인 경계, 장애 검증 절차를
  설명한다.
- Production Argo CD Sync, K3s object 생성, rollout, `/health`, `/topics/home`,
  운영 cache log 확인은 실행하지 않았다.

### Baseline interpretation

- 1~50 VU에서 p50은 약 516~533ms 범위를 유지했다.
- 50 VU에서 29.07 RPS, 100 VU에서 40.50 RPS로 처리량 증가는 약 39%에 그쳤다.
- 100 VU에서는 p50 1.22초, p95 2.20초, p99 3.25초로 지연이 크게 증가했다.
- Redis 적용 전 `/topics/home`은 50~100 VU 구간에서 포화 징후를 보인다.
- DB query 또는 connection이 병목일 가능성은 있으나 DB 측 지표를 수집하지 않았으므로 원인을 단정하지 않는다.
- 성능 저하는 있었지만 HTTP 오류, Pod restart, Ready 상실은 발생하지 않았다.

## Task Checklist State to Sync

```
- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [x] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [x] UNIT-05: Unit/Integration Test
- [x] UNIT-06: K3s와 운영 설정 반영
- [ ] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [ ] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
```

## Manual or Production Verification

UNIT-06 완료 후 사람이 승인하고 수행해야 한다.

- Argo CD OutOfSync와 diff 확인
- Argo CD Manual Sync
- `news-redis` Deployment와 Service 상태 확인
- Backend rollout 확인
- `/health` 정상 응답 확인
- `/topics/home` 정상 응답 확인
- Cache miss, store, hit 로그 확인
- Backend Pod CPU와 Memory 관측
- PostgreSQL connection 또는 query 부하 관측 가능한 범위 확인

UNIT-07에서 수행한다.

- Redis 적용 후 동일한 fixed VU 1, 10, 25, 50, 100 조건 재측정
- Before와 After의 Requests, RPS, Average, p50, p95, p99, Error rate 비교
- cache hit 이후 DB query 감소 여부를 가능한 범위에서 확인

UNIT-08에서 수행한다.

- Redis 중단 후 PostgreSQL fail-open 정상 응답 확인
- Redis 복구 후 miss → store → hit 흐름 확인
- 최종 pytest, YAML parse, diff check
- Verification Status 최종 갱신

## Pending Verification

- Redis K3s 배포와 Argo CD Manual Sync
- Redis 적용 후 동일 조건 부하 테스트 수치
- Before와 After 성능 비교
- Cache hit, miss, store, bypass 운영 로그
- 테스트 중 peak Backend CPU와 Memory
- PostgreSQL connection 또는 query 부하
- Redis 장애·복구 end-to-end
- 전체 작업 완료 후 최종 Verification Status 갱신

## Evidence Notes

- Production Baseline 부하 테스트는 사람이 승인하고 직접 실행했다.
- Agent는 production k6 실행, Redis 장애 주입, Argo CD sync, `kubectl apply/delete/patch/edit/rollout`, Supabase SQL, DB migration, `git push`, `git merge`를 실행하지 않았다.
- 초기 fixed-VU script parse 실패에서는 실제 부하가 발생하지 않았으며 해당 빈 로그는 최종 결과에서 제외했다.
- Ramp 결과는 전체 구간 집계값이고, 성능 비교의 기준값은 fixed-VU 결과다.
- `load-tests/topics-home-fixed.js`는 UNIT-07의 Redis 적용 후 동일 조건 측정에 재사용한다.
