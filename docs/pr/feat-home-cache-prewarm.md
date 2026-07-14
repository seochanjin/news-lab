# Daily·3-day·Weekly Home Cache Prewarming 및 TTL 정책 정합화

## 작업 내용

- 홈 화면이 함께 조회하는 Daily, 3-day, Weekly Home API의 Redis cache 정책을
  각 데이터 생성 Pipeline의 갱신 주기에 맞췄다.
- Home API cache miss와 Pipeline prewarm이 같은 PostgreSQL payload builder를
  사용하도록 `app/home_topics_payload.py`로 payload 생성 책임을 분리했다.
- 각 Pipeline의 DB 저장 transaction과 run 종료가 성공한 뒤 대응 Redis key를
  overwrite하도록 연결했다. PostgreSQL은 계속 source of truth로 유지한다.
- Redis 미설정, 잘못된 URL, connection/timeout/SETEX 오류, 손상 payload는 API와
  Pipeline 실패로 전파하지 않고 PostgreSQL fallback 또는 cache bypass로 처리한다.

## 주요 변경 사항

- `HomeTopicsCache`가 API별 key, TTL 환경변수와 payload validator를 사용하도록
  확장했다.
  - Daily: `topics:home:v1`, `108000`초
  - 3-day: `three-day-topics:home:v1`, `108000`초
  - Weekly: `weekly-topics:home:v1`, `691200`초
- Cache 동작을 `hit`, `miss`, `store`, `prewarm`, `bypass` 로그로 구분하고,
  오류 로그에는 credential이나 전체 `REDIS_URL`을 남기지 않는다.
- Daily Pipeline은 execute 결과의 `db_write_performed=True`일 때, 3-day와 Weekly
  Pipeline은 `saved_topic_count >= 1`이고 run 종료가 성공한 뒤 각각 prewarm한다.
  Dry-run과 no-write/no-publishable-result에서는 prewarm을 건너뛴다.
- API Deployment와 Daily·3-day·Weekly CronJob에 동일한 Redis URL, 대응 TTL과
  timeout 설정을 전달했다. Pipeline schedule과 실행 command는 변경하지 않았다.
- Architecture, cache design과 CronJob runbook을 세 Home API와 세 Pipeline 기준으로
  갱신하고, 운영 prewarm 확인 절차를 human-controlled 단계로 문서화했다.
- 세 cache의 key, TTL과 validator 분리, API cache-aside, Pipeline prewarm,
  manifest 설정과 Redis fail-open 동작을 단위·통합 테스트로 보강했다.
- 승인된 FIX-01~05를 반영했다. 3-day router의 미사용 상수 제거, Weekly TTL
  manifest 교차 검증, 3-day/Weekly SETEX 실패 회귀 테스트와 3-day fixture 상태
  정합화를 적용했다. 기존 malformed/unsupported `REDIS_URL` 테스트가 충분해
  중복 테스트는 추가하지 않았다.

## 추가/변경된 API

- 신규 endpoint는 없다.
- 기존 endpoint의 path, request parameter, response schema, HTTP status 정책은
  변경하지 않았다.
  - `GET /topics/home`
  - `GET /three-day-topics/home`
  - `GET /weekly-topics/home`
- 내부적으로 `/three-day-topics/home`과 `/weekly-topics/home`에 Redis
  cache-aside를 추가했고, 세 endpoint 모두 cache miss 또는 Redis 오류 시 기존
  PostgreSQL payload를 반환한다.
- Cache 상태를 response body나 header에 추가하지 않았다.

## DB 변경 사항

- PostgreSQL schema, table, column, index와 constraint 변경 없음.
- DB migration과 Supabase SQL 추가 없음.
- 기존 Pipeline transaction과 commit 의미는 변경하지 않았다.
- Prewarm은 성공한 DB transaction 이후 별도 read connection으로 payload를
  조회하며, Redis 오류로 이미 완료된 DB 저장을 rollback하지 않는다.

## README 영향

- README 변경은 필요하지 않다. 사용자-facing 설치·실행 방법이나 공개 API 계약이
  바뀌지 않았기 때문이다.
- 구현 및 운영 정책 변경은 책임에 맞게 `docs/architecture/backend-api.md`,
  `docs/design/home-api-redis-cache.md`, `docs/runbooks/cronjobs.md`에 반영했다.

## 테스트

- 승인 fix targeted test:
  `PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
  - 결과: `41 passed, 8 subtests passed`
- Home Cache 선택 테스트:
  `PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"`
  - 결과: `137 passed, 308 deselected, 32 subtests passed`
- 전체 테스트: `PYTHONPATH=. pytest -q`
  - 결과: `445 passed, 91 subtests passed`
- 세 cache 통합 테스트: `PYTHONPATH=. pytest -q tests/test_home_cache_integration.py`
  - 결과: `1 passed`
- Kubernetes YAML parse:
  `ruby -e 'require "yaml"; Dir["k8s/*.yaml"].sort.each { |path| YAML.load_stream(File.read(path)); puts "ok #{path}" }'`
  - 결과: top-level K8s YAML 전체 parse 통과
- 정적 및 범위 검증:
  - `git diff --check`: whitespace 오류 없음
  - `git diff --name-only -- db migrations frontend`: 출력 없음

## 확인 결과

- Verification 상태는 `passed`다.
- 세 Home API의 cache hit, miss/store, Redis 오류와 손상 payload의 PostgreSQL
  fallback을 로컬 테스트로 확인했다.
- 세 Pipeline의 저장 성공 후 prewarm과 dry-run/no-write skip을 확인했다.
- Redis connection, timeout과 SETEX 오류가 성공한 Pipeline 결과를 실패로 바꾸지
  않고 warning 로그에 credential과 전체 URL을 노출하지 않음을 확인했다.
- Daily·3-day·Weekly cache가 서로 다른 key와 validator를 사용하고, TTL이 각각
  `108000`, `108000`, `691200`초임을 확인했다.
- API Deployment와 세 CronJob의 Redis 설정 정합성 및 K8s YAML parse를 확인했다.
- DB migration, Supabase 운영 데이터와 frontend 변경은 없다.

## 비고

- Redis는 삭제 가능한 성능 최적화 계층이며 최신성은 TTL 만료가 아니라 각
  Pipeline 성공 시 대응 key overwrite로 관리한다.
- PR merge, Argo CD Manual Sync, K3s rollout, 수동 Pipeline Job, Redis key/TTL 및
  production Home API 검증은 수행하지 않았다.
- 운영 반영과 검증은 `docs/runbooks/cronjobs.md` 절차에 따라 사람이 수행하고,
  실제 credential 없는 결과가 제공된 뒤 Verification에 기록해야 한다.
- Deferred/Rejected suggestion과 승인되지 않은 review suggestion은 적용하지 않았다.
