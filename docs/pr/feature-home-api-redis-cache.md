# Home API 부하 측정 및 Redis Cache 적용

## 작업 내용

`GET /topics/home`에 Redis cache-aside를 적용해 반복 조회 시 PostgreSQL 조회를
건너뛸 수 있도록 했다. PostgreSQL은 계속 source of truth로 유지하며, Redis
미설정·연결 실패·GET/SET timeout·payload 손상은 요청 실패로 전파하지 않고
PostgreSQL fallback으로 처리한다.

이번 PR은 Redis 적용 전 production baseline 수치를 기록하고, Redis 운영 manifest
반영 준비와 로컬 검증까지 포함한다. Argo CD Manual Sync, Redis 적용 후 부하
테스트, Redis 장애·복구 검증은 아직 수행하지 않았다.

## 주요 변경 사항

- `app/home_topics_cache.py`를 추가해 `/topics/home` 전용 Redis cache-aside 계층을
  분리했다.
  - cache key: `topics:home:v1`
  - TTL 기본값: 60초
  - Redis timeout 기본값: 0.05초
  - log event: `hit`, `miss`, `store`, `bypass`
- `app/routers/topics.py`에서 `/topics/home` payload 생성 경로를 분리했다.
  - cache hit 시 DB connection factory를 호출하지 않는다.
  - cache miss 또는 bypass 시 기존 SQL 조회 후 Redis `SETEX` 저장을 시도한다.
- `requirements.txt`에 `redis` dependency를 추가했다.
- `k8s/news-api.yaml`에 `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS`,
  `REDIS_TIMEOUT_SECONDS` env를 추가했다.
- `k8s/redis.yaml`에 ephemeral `news-redis` Deployment/Service를 추가했다.
  - Redis persistence 비활성화
  - `maxmemory 96mb`, `allkeys-lru`
  - request `50m/64Mi`, limit `250m/128Mi`
- `load-tests/topics-home.js`, `load-tests/topics-home-fixed.js`로 `/topics/home`
  ramp 및 fixed-VU 부하 테스트 스크립트를 추가했다.
- CronJob manifest image test의 stale `seocj/news-api:latest` 기대값을 제거하고
  immutable full Git SHA 형식 및 Backend Deployment image 정합성을 검증하도록
  수정했다.
- Architecture, Runbook, design, task, fix, verification, devlog 문서를 현재
  작업 상태와 pending 운영 검증 기준에 맞게 갱신했다.

## 추가/변경된 API

- 외부 API 계약 변경 없음.
- 기존 endpoint 유지: `GET /topics/home`
- request parameter, 인증/권한 정책, response body schema 변경 없음.
- cache hit 여부를 response body에 추가하지 않는다.
- 내부 동작만 Redis cache-aside로 변경된다.

## DB 변경 사항

- DB migration 없음.
- PostgreSQL table, column, index, constraint 변경 없음.
- Supabase SQL 실행 없음.
- 운영 데이터 수정 없음.

## README 영향

README 변경은 필요하지 않다고 판단했다. 사용자에게 노출되는 API path, request,
response schema가 바뀌지 않았고, 운영 절차와 Redis 반영 조건은 Architecture,
Runbook, design, verification 문서에 기록했다.

## 테스트

- `PYTHONPATH=. pytest -q tests/test_topics_api.py`
  - `15 passed in 0.39s`
- `PYTHONPATH=. pytest -q tests/test_home_api_redis_k8s_manifest.py`
  - `4 passed in 0.02s`
- `PYTHONPATH=. pytest -q tests/test_daily_topic_pipeline_cronjob_manifest.py tests/test_three_day_topic_pipeline_cronjob_manifest.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
  - `10 passed in 0.04s`
- `PYTHONPATH=. pytest -q`
  - `422 passed, 78 subtests passed in 15.10s`
- `ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
  - `k8s/*.yaml` parse 통과
- `rg -n 'seocj/news-api:latest' tests/test_daily_topic_pipeline_cronjob_manifest.py tests/test_three_day_topic_pipeline_cronjob_manifest.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
  - CronJob manifest test 파일에서 출력 없음
- `k6 inspect load-tests/topics-home-fixed.js`
  - parse error 없음
- `git diff --check`
  - 통과
- `git diff --name-only -- db migrations frontend`
  - 출력 없음

## 확인 결과

- Cache miss 후 PostgreSQL 조회와 Redis 저장 검증 완료
- Cache hit 시 PostgreSQL 조회 미호출 검증 완료
- TTL 만료 후 재조회 검증 완료
- Redis GET/SET/connection/timeout 오류 fallback 검증 완료
- malformed/unsupported Redis URL fallback 검증 완료
- 손상 payload fallback 검증 완료
- 기존 `/topics/home` response schema 유지 검증 완료
- K3s Redis manifest와 Argo CD Manual Sync 경계 로컬 검증 완료
- Production Redis 미적용 상태를 확인한 뒤 Redis 적용 전 baseline을 측정했다.
- Redis 적용 전 fixed-VU baseline:

| VU | Duration | Requests | RPS | Average | p50 | p95 | p99 | Error rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 30s | 19 | 0.63 | 562.52ms | 533.19ms | 764.68ms | 769.29ms | 0% |
| 10 | 30s | 194 | 6.15 | 552.55ms | 516.40ms | 685.31ms | 701.10ms | 0% |
| 25 | 30s | 438 | 13.87 | 717.63ms | 519.78ms | 1.51s | 1.97s | 0% |
| 50 | 30s | 938 | 29.07 | 604.51ms | 516.53ms | 1.35s | 1.77s | 0% |
| 100 | 30s | 1,310 | 40.50 | 1.31s | 1.22s | 2.20s | 3.25s | 0% |

- Baseline 중 Backend Pod는 2/2 Ready, restart 0, `/health` 정상으로 기록됐다.
- 100 VU에서 p50 1.22초, p95 2.20초, p99 3.25초로 지연 증가가 확인됐다.

## 비고

- PR merge 완료를 주장하지 않는다.
- Production Redis 배포, Argo CD Manual Sync, K3s rollout은 아직 완료되지 않았다.
- Redis 적용 후 동일 조건 부하 테스트와 Before/After 비교는 pending이다.
- 운영 cache hit/miss/store/bypass 로그 확인은 pending이다.
- Redis 중단·복구 및 PostgreSQL fail-open 운영 검증은 pending이다.
- Verification Status는 아직 `pending`이다. UNIT-07과 UNIT-08 완료 후 최종
  상태를 갱신해야 한다.
