# Home API 부하 측정 및 Redis Cache 적용

## 작업 목적

`GET /topics/home`은 첫 화면에서 반복 호출되는 read API다. 이번 작업의 목적은
PostgreSQL을 source of truth로 유지하면서 Redis cache-aside를 추가해 반복 조회
부하를 줄이고, Redis 장애가 API 장애로 번지지 않는 fail-open 구조를 만드는
것이다.

단순히 Redis를 추가하는 것이 아니라 Redis 적용 전 baseline을 측정하고, 이후
동일 조건으로 비교할 수 있는 검증 기준을 남기는 것도 목표에 포함했다.

## 기존 문제

`/topics/home`은 home card payload를 만들기 위해 매 요청마다 PostgreSQL의
`topics` table을 조회했다. SQL 자체는 archive/detail API보다 가볍지만, 운영
Backend replica 2개에서 반복 조회가 늘어나면 DB connection과 query 부하가
계속 누적되는 구조였다.

기존에는 다음 기준도 정리되어 있지 않았다.

- Redis 적용 전 `/topics/home` production baseline 수치
- cache hit, miss, store, bypass를 구분하는 운영 로그 기준
- Redis 장애 또는 손상 payload 발생 시 API가 어떤 방식으로 복구되는지
- Redis 운영 manifest가 Argo CD Manual Sync 경계를 유지하는지
- CronJob manifest test의 image 기대값이 immutable full Git SHA 정책과 맞는지

## 변경 내용

- `/topics/home` 전용 Redis cache-aside 계층 `app/home_topics_cache.py`를 추가했다.
- `/topics/home` route를 cache orchestration과 DB payload 생성 helper로 분리했다.
- Redis 미설정, dependency 부재, connection 오류, GET/SET timeout, 손상 payload를
  모두 PostgreSQL fallback으로 처리했다.
- cache key `topics:home:v1`, TTL 60초, Redis timeout 0.05초를 초기값으로 정했다.
- cache 상태를 response body가 아니라
  `home_topics_cache event=hit|miss|store|bypass` 로그로 구분하게 했다.
- `requirements.txt`에 `redis` dependency를 추가했다.
- `k8s/news-api.yaml`에 Redis 관련 env를 추가했다.
- `k8s/redis.yaml`에 ephemeral `news-redis` Deployment/Service를 추가했다.
- `/topics/home` ramp/fixed-VU k6 부하 테스트 스크립트를 추가했다.
- Redis 적용 전 production baseline을 기록했다.
- CronJob manifest test의 stale `seocj/news-api:latest` assertion을 immutable full
  Git SHA 형식과 Backend Deployment image 일치 검증으로 바꿨다.
- Architecture, Runbook, design, PR, verification, fix 문서를 현재 상태와 pending
  검증 기준에 맞게 갱신했다.

## 구현 상세

`HomeTopicsCache`는 Redis client, cache key, TTL, enabled 상태를 보관한다. cache가
비활성화되어 있거나 Redis 작업 중 예외가 발생하면 `None`을 반환해 호출자가
PostgreSQL 조회를 계속하게 한다. `set()` 실패도 요청 실패로 전파하지 않는다.

`get_home_topics_payload()`는 다음 흐름을 담당한다.

```text
cache.get()
  ├─ payload 존재: cached payload 반환
  └─ None: PostgreSQL 조회
          → cache.set(payload)
          → payload 반환
```

Cache payload는 최소 구조만 검증한다.

- top-level `generated_at`, `topic_date`, `items`
- item별 `id`, `topic_date`, `title_ko`, `summary_ko`, `keywords`,
  `source_count`, `article_count`

Kubernetes 쪽에서는 `news-api`가 `redis://news-redis:6379/0`을 사용하게 했고,
Redis는 persistence 없이 bounded resource로 실행한다. Cache 데이터는 재생성
가능하므로 `--save ""`, `--appendonly no`, `maxmemory 96mb`, `allkeys-lru`로
설정했다.

Argo CD `news-api` Application은 `k8s` top-level manifest를 읽고 Manual Sync를
유지한다. Redis 추가 후 기대 generated resource는 `news-api`, `news-redis`, 네
CronJob을 포함한 9개다. 운영 object 생성과 Sync는 사람이 수행해야 한다.

## 대안 검토

- Process-local cache: replica 간 cache가 공유되지 않아 운영 replica 2개 구조에서
  반복 조회 부하 감소 효과가 제한적이다.
- PostgreSQL materialized view 또는 snapshot table: source of truth와 DB schema에
  영향을 주며 이번 task의 DB 변경 없음 원칙을 벗어난다.
- CDN 또는 edge cache: API 내부의 DB fallback과 Redis 장애 격리 검증보다 범위가
  커진다.
- Redis Cluster/Sentinel/persistence: 현재 요구는 삭제 가능한 성능 최적화 계층이므로
  고가용성과 persistence 고도화는 이번 범위에서 제외했다.
- Distributed lock 또는 stale-while-revalidate: cache stampede 완화에는 유효하지만
  현재 규모와 검증 범위에서는 복잡도 대비 필요성이 입증되지 않았다.
- CronJob manifest test를 `latest`로 되돌리기: immutable image GitOps 정책을
  위반하므로 거절했다.

## 선택한 접근과 근거

Redis cache-aside를 선택했다. PostgreSQL을 source of truth로 유지하면서도 cache
hit 시 DB connection factory 자체를 호출하지 않아 반복 조회 부하를 줄일 수 있기
때문이다.

TTL은 60초로 정했다. Daily Topic Pipeline이 home payload의 주된 갱신 주기이므로
초 단위 강한 일관성이 필요하지 않고, 운영자가 새 결과를 확인할 때 stale window를
짧게 유지할 수 있는 초기값이다.

Redis failure policy는 fail-open으로 정했다. Redis는 성능 계층일 뿐이므로 Redis
장애가 `/topics/home` 장애로 이어지면 안 된다. 따라서 GET, SET, timeout,
connection, decode, validate 실패를 모두 bypass로 기록하고 PostgreSQL 조회로
복구한다.

운영 반영은 Argo CD Manual Sync 기준을 유지했다. Auto sync, prune, self-heal은
추가하지 않았고, object 생성과 rollout은 사람 승인 뒤 수행하도록 남겼다.

## 트레이드오프

- 60초 TTL 동안 최신 topic 반영이 최대 60초 늦게 보일 수 있다.
- Redis 장애 시 API는 정상 응답하지만 DB 직접 조회로 돌아가므로 성능은 저하될 수
  있다.
- SET 실패를 사용자 요청 실패로 만들지 않기 때문에 cache 저장 실패는 로그 관측에
  의존한다.
- Redis persistence를 비활성화해 운영이 단순해졌지만, Redis restart 후 cache는
  비어 있는 상태로 시작한다.
- cache payload 검증은 최소 schema 검증이다. 완전한 business validation은
  PostgreSQL payload 생성 로직에 맡긴다.
- Production baseline은 사람이 승인하고 직접 실행한 결과를 기록했지만, Redis 적용
  후 비교와 장애 주입은 아직 pending이다.
- Backend Pod CPU/Memory는 각 단계 종료 직후 snapshot이므로 peak 사용량으로
  해석하면 안 된다.

## 테스트

실제 결과는 `docs/verification/feature-home-api-redis-cache.md`를 source of truth로
사용했다.

- `PYTHONPATH=. pytest -q tests/test_topics_api.py`
  - `13 passed in 0.27s`
  - cache miss, hit, TTL 만료, Redis GET timeout, connection 오류, SET 실패,
    손상 payload fallback, 기존 response schema 유지 검증 포함
- `PYTHONPATH=. pytest -q tests/test_home_api_redis_k8s_manifest.py`
  - `4 passed in 0.02s`
  - `news-api` Redis env, `news-redis` Deployment/Service, Argo CD Manual Sync
    경계 검증
- `PYTHONPATH=. pytest -q tests/test_daily_topic_pipeline_cronjob_manifest.py tests/test_three_day_topic_pipeline_cronjob_manifest.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
  - `10 passed in 0.04s`
  - CronJob image assertion을 immutable full Git SHA 정책으로 검증
- `PYTHONPATH=. pytest -q`
  - `420 passed, 78 subtests passed in 15.00s`
- `ruby -e '...'`
  - `k8s/*.yaml` parse 통과
- `rg -n 'seocj/news-api:latest' ...`
  - CronJob manifest test 파일에서 출력 없음
- `k6 inspect load-tests/topics-home-fixed.js`
  - parse error 없음
- `git diff --check`
  - 통과
- `git diff --name-only -- db migrations frontend`
  - 출력 없음

기준 commit `15c686ef`의 별도 worktree에서는
`406 passed, 3 failed, 78 subtests passed`였고, 세 실패는 모두 stale
`seocj/news-api:latest` assertion으로 확인됐다. 이번 fix 이후 전체 suite는
`0 failed`다.

## 운영 반영

완료된 것:

- Redis 적용 전 production baseline 측정
- Production Redis 미적용 상태 확인
- K3s Redis manifest 로컬 YAML parse
- Argo CD Manual Sync 경계를 로컬 manifest test와 문서로 확인

아직 완료되지 않은 것:

- PR merge
- Argo CD OutOfSync와 diff 확인
- Argo CD Manual Sync
- `news-redis` Deployment/Service 생성 확인
- Backend rollout 확인
- Redis 적용 후 `/health`, `/topics/home` production 확인
- 운영 cache miss, store, hit, bypass 로그 확인
- Redis 중단·복구 장애 검증

Production-impacting command는 실행하지 않았다. Agent는 production k6 실행,
Redis 장애 주입, Argo CD sync, `kubectl apply/delete/patch/edit/rollout`,
Supabase SQL, DB migration, `git push`, `git merge`를 실행하지 않았다.

## README 업데이트 판단

README 변경은 필요하지 않다고 판단했다. 외부 API path, request parameter,
response schema가 바뀌지 않았고, 사용자가 직접 알아야 하는 endpoint 계약도
변경되지 않았다.

운영자가 알아야 하는 Redis cache 정책, Argo CD Manual Sync 경계, 장애 검증 절차는
Architecture, Runbook, design, verification 문서에 기록했다. 따라서 README에
중복 요약을 추가하기보다 운영 문서의 source of truth를 유지하는 쪽을 선택했다.

## 확인 결과

Redis 적용 전 fixed-VU baseline:

| VU | Duration | Requests | RPS | Average | p50 | p95 | p99 | Error rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 30s | 19 | 0.63 | 562.52ms | 533.19ms | 764.68ms | 769.29ms | 0% |
| 10 | 30s | 194 | 6.15 | 552.55ms | 516.40ms | 685.31ms | 701.10ms | 0% |
| 25 | 30s | 438 | 13.87 | 717.63ms | 519.78ms | 1.51s | 1.97s | 0% |
| 50 | 30s | 938 | 29.07 | 604.51ms | 516.53ms | 1.35s | 1.77s | 0% |
| 100 | 30s | 1,310 | 40.50 | 1.31s | 1.22s | 2.20s | 3.25s | 0% |

Baseline 해석:

- 1~50 VU에서 p50은 약 516~533ms 범위를 유지했다.
- 50 VU에서 29.07 RPS, 100 VU에서 40.50 RPS로 처리량 증가는 약 39%였다.
- 100 VU에서는 p50 1.22초, p95 2.20초, p99 3.25초로 지연이 크게 증가했다.
- Redis 적용 전 `/topics/home`은 50~100 VU 구간에서 포화 징후를 보인다.
- DB query 또는 connection이 병목일 가능성은 있지만 DB 측 지표를 수집하지
  않았으므로 원인은 단정하지 않는다.
- 성능 저하는 있었지만 HTTP 오류, Pod restart, Ready 상실은 발생하지 않았다.

Resource snapshot은 각 fixed-VU 테스트 종료 직후 기준이다.

| VU | Pod 1 CPU | Pod 2 CPU | Pod 1 Memory | Pod 2 Memory |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 2m | 2m | 65Mi | 65Mi |
| 10 | 17m | 18m | 65Mi | 65Mi |
| 25 | 44m | 47m | 66Mi | 66Mi |
| 50 | 79m | 81m | 67Mi | 67Mi |
| 100 | 63m | 29m | 69Mi | 70Mi |

## 이번 단계의 의미

이번 단계에서 `/topics/home`은 Redis가 있으면 반복 조회를 cache로 흡수하고,
Redis가 없거나 실패하면 PostgreSQL로 복구하는 구조를 갖췄다. 동시에 Redis 적용
전 baseline을 남겨 이후 적용 후 성능 개선 여부를 같은 조건으로 비교할 수 있게
됐다.

운영 관점에서는 Redis를 source of truth가 아닌 삭제 가능한 성능 계층으로
제한했고, GitOps/Argo CD Manual Sync 경계를 유지했다. 이 때문에 아직 production
적용 완료는 아니지만, 적용 전 검토와 승인에 필요한 코드, manifest, 문서, 테스트
근거는 준비됐다.

## 포트폴리오용 요약

NewsLab의 첫 화면 API인 `GET /topics/home`에 Redis cache-aside를 적용했다.
PostgreSQL을 source of truth로 유지하고 Redis 장애, timeout, 손상 payload를 모두
fail-open fallback으로 처리해 API 안정성을 우선했다. Production baseline에서는
100 VU에서 p95 2.20초, p99 3.25초까지 지연이 증가하는 포화 징후를 확인했고,
이후 Redis 적용 후 비교를 위한 k6 fixed-VU 측정 기준을 마련했다. K3s manifest와
Argo CD Manual Sync 경계를 문서화하고, unit/integration test와 YAML parse를
포함해 `420 passed, 78 subtests passed`로 검증했다.

## 다음 단계 후보

- Argo CD diff에서 Redis Deployment/Service와 `news-api` Redis env 변경만 포함되는지
  확인한다.
- 사람이 승인한 운영 창에서 Argo CD Manual Sync를 수행한다.
- `news-redis` Deployment/Service와 Backend rollout 상태를 확인한다.
- `/health`, `/topics/home` production 응답을 확인한다.
- cache miss → store → hit 로그를 확인한다.
- Redis 적용 후 fixed-VU 1, 10, 25, 50, 100 조건으로 동일 부하 테스트를 수행한다.
- Before/After RPS, average, p50, p95, p99, error rate를 비교한다.
- 가능한 범위에서 PostgreSQL connection/query 부하 변화를 확인한다.
- Redis 중단 후 PostgreSQL fallback 정상 응답을 검증한다.
- Redis 복구 후 miss → store → hit 흐름을 다시 확인한다.
- UNIT-07, UNIT-08 완료 후 Verification Status를 최종 갱신한다.
