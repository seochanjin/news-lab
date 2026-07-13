# Approved Fixes: Home API 부하 측정 및 Redis Cache 적용

## Approved Fixes

이 문서는 기존 수정 이력을 삭제하지 않고 Review Round별로 누적 관리한다.

- Review Round 1은 Task 70의 immutable image 정책과 CronJob manifest test 사이의 정합성을 복구한 완료 이력이다.
- Review Round 2는 CodeRabbit이 추가로 발견한 Redis fail-open 결함과 문서 품질 문제를 다룬다.
- Production 배포, Argo CD Manual Sync, Redis 장애 주입은 이 fix 문서의 자동 실행 범위에 포함하지 않는다.

## Review Round 1 — Immutable Image 정합성 복구

### Background

Redis 변경 전 기준 commit `15c686ef`의 별도 worktree에서도 동일한 세 CronJob manifest test가 실패했다.

````
406 passed
3 failed
78 subtests passed
````

세 실패는 모두 실제 manifest가 `seocj/news-api:<40자리 full Git SHA>`를 사용하는 반면, test가 `seocj/news-api:latest`를 고정 기대해서 발생했다. 따라서 Redis 구현으로 생긴 회귀가 아니라 immutable image 전환 이후 남아 있던 stale test expectation으로 확정했다.

### Completed Fixes

- [x] FIX-01: Daily Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-02: Three-day Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-03: Weekly Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-04: 특정 현재 SHA를 하드코딩하지 않고 full Git SHA 형식과 workload image 정합성을 검증
- [x] FIX-05: Task의 Implementation Units를 parser 호환 형식으로 정리
- [x] FIX-06: Verification에 기준 worktree 재현 결과와 fix 이후 전체 test 결과를 반영

기존 assertion:

````python
self.assertEqual(self.container["image"], "seocj/news-api:latest")
````

수정 원칙:

````python
self.assertRegex(
    self.container["image"],
    r"^seocj/news-api:[0-9a-f]{40}$",
)
````

각 CronJob image는 `k8s/news-api.yaml`의 Backend Deployment image와 일치하는지도 검증한다. 현재 SHA 값 자체는 test에 하드코딩하지 않는다.

### Applied Changes

- FIX-01~FIX-03: 세 CronJob manifest test의 image assertion을 `seocj/news-api:latest` 고정 기대값에서 `^seocj/news-api:[0-9a-f]{40}$` full Git SHA 형식 검증으로 변경했다.
- FIX-04: 세 CronJob image가 `k8s/news-api.yaml`의 Backend Deployment image와 일치하는지 검증하도록 했다.
- FIX-05: `docs/tasks/feature-home-api-redis-cache.md`의 `Implementation Units`를 하위 bullet 없는 parser 호환 checklist 형식으로 정리했다.
- FIX-06: `docs/verification/feature-home-api-redis-cache.md`에 기준 worktree 재현 결과와 fix 이후 대상 test 및 전체 test 결과를 기록했다.

### Round 1 Verification

기존 stale expectation 제거:

````bash
rg -n 'seocj/news-api:latest' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
````

기대 결과: 출력 없음.

Immutable image assertion 확인:

````bash
rg -n \
  'assertRegex|[0-9a-f].*40|news-api' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
````

대상 test:

````bash
PYTHONPATH=. pytest -q \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
````

전체 test:

````bash
PYTHONPATH=. pytest -q
````

Round 1 완료 당시 기준:

- 대상 test 실패 0건
- 전체 suite 실패 0건
- 기존 Redis cache 관련 test 포함 전체 suite 통과

## Review Round 2 — Redis Fail-open 및 문서 품질 수정

### Review Summary

CodeRabbit이 제기한 항목은 Major 1건과 Minor 문서 항목들이다.

- Major는 잘못된 `REDIS_URL`이 `/topics/home` 전체를 HTTP 500으로 만들 수 있는 fail-open 위반이다.
- Minor는 재현 불가능한 축약 명령, Markdown lint, 문서 상태 불일치, 문장 표현 문제다.
- Major와 회귀 test가 통과하기 전에는 PR을 병합하지 않는다.

### Approved Fixes

- [x] FIX-07: 잘못된 `REDIS_URL`에서도 PostgreSQL fallback이 유지되도록 Redis client 생성 예외 처리
- [x] FIX-08: malformed URL과 unsupported Redis URL scheme에 대한 회귀 test 추가
- [x] FIX-09: Devlog의 축약된 검증 명령을 실제 실행 가능한 전체 명령으로 교체
- [x] FIX-10: PR 문서의 축약된 검증 명령을 실제 실행 가능한 전체 명령으로 교체
- [x] FIX-11: Approved Fixes 문서의 UNIT-05 상태와 완료 서술을 현재 상태에 맞게 동기화
- [x] FIX-12: Task와 Approved Fixes의 언어 없는 fenced code block에 language identifier 추가
- [x] FIX-13: Verification의 문장 표현과 언어 없는 fenced code block 수정
- [x] FIX-14: 전체 test, Markdown fence 검사, placeholder 검사, diff 검증 후 문서 상태 갱신

### Applied Changes

- FIX-07: `Redis.from_url(...)`의 `ValueError`를 처리해 invalid Redis URL을
  disabled cache로 전환하고 PostgreSQL fallback을 유지했다. URL 값이나 credential은
  로그에 남기지 않는다.
- FIX-08: malformed `REDIS_URL`과 unsupported Redis URL scheme에서 cache dependency
  생성이 예외를 전파하지 않고 DB fallback을 수행하는 회귀 test를 추가했다.
- FIX-09~FIX-10: PR과 devlog의 축약된 `ruby -e '...'`, `rg ...` 검증 명령을 실제
  실행 가능한 전체 명령으로 교체했다.
- FIX-11: Round 2 문서의 authoritative Implementation Units snapshot을 UNIT-02,
  UNIT-05 완료와 UNIT-06 미완료 상태로 정리했다.
- FIX-12~FIX-13: task, approved fixes, verification 문서의 Markdown fence를 검사
  command에 맞춰 정리하고 verification 문장 표현을 `실패 0건`으로 수정했다.
- FIX-14: targeted test, K3s manifest test, CronJob immutable image test, 전체
  suite, YAML parse, Markdown fence check, placeholder check, task parser check,
  diff check와 변경 파일 확인 결과를 verification에 기록했다.

## FIX-07 — Redis Client 생성 Fail-open 보장

### Problem

현재 `app/home_topics_cache.py`는 `REDIS_URL`이 존재하면 다음 client를 즉시 생성한다.

````python
client = Redis.from_url(
    redis_url,
    socket_connect_timeout=timeout_seconds,
    socket_timeout=timeout_seconds,
    decode_responses=True,
)
````

`Redis.from_url(...)`은 malformed URL 또는 지원하지 않는 scheme에서 `ValueError`를 발생시킬 수 있다. 이 예외가 dependency 생성 단계에서 전파되면 cache miss로 처리되지 않고 `/topics/home` 요청이 HTTP 500으로 종료된다.

````
잘못된 REDIS_URL
→ Redis client 생성 실패
→ Cache 조회 전에 예외 전파
→ PostgreSQL fallback 미실행
→ /topics/home HTTP 500
````

이는 Cache 장애나 설정 오류가 서비스 장애로 이어지지 않아야 한다는 fail-open 원칙을 위반한다.

### Approved Direction

- `Redis.from_url(...)` 호출을 예상 가능한 URL 파싱·설정 예외로부터 보호한다.
- malformed URL에서도 application startup 또는 request dependency 생성이 실패하지 않아야 한다.
- 기존 disabled-cache 또는 no-op cache 경로를 우선 재사용한다.
- 로그에는 `event=bypass` 또는 명확한 configuration warning을 남긴다.
- URL 전체, password, credential은 로그에 출력하지 않는다.
- 우선 `ValueError`처럼 예상 가능한 설정 예외만 처리한다.
- 무관한 programming error까지 숨기는 광범위한 `except Exception`은 사용하지 않는다.

예시 방향:

````python
try:
    client = Redis.from_url(
        redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
        decode_responses=True,
    )
except ValueError:
    logger.warning(
        "home_topics_cache event=bypass reason=invalid_redis_url"
    )
    return HomeTopicsCache.disabled(ttl_seconds=ttl_seconds)

return HomeTopicsCache(client=client, ttl_seconds=ttl_seconds)
````

실제 disabled-cache 생성 방식은 현재 `HomeTopicsCache` API와 factory 구조에 맞춘다. 존재하지 않는 API를 문서 예시 그대로 임의 추가하지 않는다.

## FIX-08 — Regression Test

최소한 다음 경우를 검증한다.

- malformed `REDIS_URL`에서 cache dependency 생성이 예외를 전파하지 않는다.
- unsupported Redis URL scheme에서 cache가 비활성화된다.
- 잘못된 URL 상태에서도 `/topics/home`이 PostgreSQL fallback으로 기존 response schema와 HTTP 200을 유지한다.
- Redis client factory가 실패한 경우 DB connection factory가 호출된다.
- warning 또는 bypass 로그에 Redis credential이 포함되지 않는다.

Test는 기존 `tests/test_topics_api.py` 또는 현재 cache factory test 구조를 따른다. 기존 구조로 표현하기 어려운 경우에만 최소 범위의 신규 test 파일을 추가한다.

## FIX-09, FIX-10 — Reproducible Verification Commands

Devlog와 PR 문서의 다음 표현은 실제 실행할 수 없는 placeholder다.

````
ruby -e '...'
rg -n 'seocj/news-api:latest' ...
````

다음 전체 명령으로 교체한다.

Kubernetes YAML parse:

````bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
````

Stale `latest` assertion 확인:

````bash
rg -n 'seocj/news-api:latest' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
````

기대 결과: 출력 없음, exit code 1.

문서에서 명령을 축약해야 하는 경우 실행 가능한 명령처럼 쓰지 않고 `축약 예시`라고 명시한다.

## FIX-11 — UNIT 상태 동기화

기존 Approved Fixes 문서에는 Round 1 당시 snapshot이 남아 있어 UNIT-02와 UNIT-05가 미완료로 표시됐다. 현재 authoritative state는 다음과 같다.

````markdown
## Implementation Units

- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [x] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [x] UNIT-05: Unit/Integration Test
- [ ] UNIT-06: K3s와 운영 설정 반영
- [ ] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [ ] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
````

UNIT-06은 manifest, test, Runbook 준비가 끝났더라도 Production Argo CD Manual Sync와 운영 검증 전까지 미완료로 유지한다.

## FIX-12, FIX-13 — Markdown Lint와 문장 정리

언어가 없는 fenced code block에는 내용에 맞는 identifier를 추가한다.

- Shell command: `bash`
- Python source: `python`
- JSON output: `json`
- Checklist 또는 Markdown 예시: `markdown`
- 일반 출력, 경로 목록, 흐름도: `text`

적용 대상:

````
docs/tasks/feature-home-api-redis-cache.md
docs/fixes/feature-home-api-redis-cache-approved-fixes.md
docs/verification/feature-home-api-redis-cache.md
````

Verification의 다음 표현도 수정한다.

기존:

````
Fix와 UNIT-06 manifest test 추가 이후 전체 suite는 0 failed다.
````

수정:

````
Fix와 UNIT-06 manifest test 추가 이후 전체 suite는 실패 0건이다.
````

## Rejected or Deferred Suggestions

### Rejected

- **CronJob manifest를 다시 `latest`로 되돌리기**: immutable full Git SHA 정책을 위반하므로 거절한다.
- **현재 SHA를 test에 직접 하드코딩하기**: 다음 manifest image 갱신에서 동일 문제가 재발하므로 거절한다.
- **세 CronJob 실패를 Redis 구현 회귀로 분류하기**: 기준 commit에서도 동일하게 재현됐으므로 거절한다.
- **Redis URL 오류를 그대로 HTTP 500으로 반환하기**: Cache fail-open 원칙을 위반하므로 거절한다.
- **`except Exception`으로 모든 오류를 무조건 숨기기**: 예상 가능한 설정 예외만 처리해야 하므로 거절한다.
- **잘못된 URL 문자열이나 credential을 로그에 출력하기**: secret 노출 위험 때문에 거절한다.
- **검증 명령 placeholder를 그대로 유지하기**: 제3자가 재실행할 수 없으므로 거절한다.
- **UNIT-06을 Production 검증 전에 완료 처리하기**: 저장소 준비와 운영 적용을 구분해야 하므로 거절한다.

### Deferred

- Production Argo CD Manual Sync
- `kubectl apply/delete/patch/edit/rollout`
- Redis 장애 주입
- Production Redis 적용 후 부하 테스트
- Supabase SQL 또는 DB migration
- Git push 또는 merge

위 작업은 사람이 승인하고 직접 수행한다.

## Allowed Change Scope

````
app/home_topics_cache.py
tests/test_topics_api.py
tests/test_home_topics_cache.py
docs/devlog/feature-home-api-redis-cache.md
docs/pr/feature-home-api-redis-cache.md
docs/tasks/feature-home-api-redis-cache.md
docs/fixes/feature-home-api-redis-cache-approved-fixes.md
docs/verification/feature-home-api-redis-cache.md
````

`tests/test_home_topics_cache.py`가 현재 repository에 없다면 기존 test 파일을 우선 사용한다. 신규 test 파일은 기존 구조로 표현하기 어려운 경우에만 추가한다.

다음 영역은 변경하지 않는다.

````
k8s/
load-tests/
requirements.txt
db/
migrations/
frontend/
.github/workflows/
scripts/
docker-compose.yml
````

## Verification Required

### Cache Targeted Test

````bash
PYTHONPATH=. pytest -q tests/test_topics_api.py
````

Cache factory 전용 test 파일을 추가했다면 해당 파일도 함께 실행한다.

### K3s Manifest Test

````bash
PYTHONPATH=. pytest -q tests/test_home_api_redis_k8s_manifest.py
````

### CronJob Immutable Image Test

````bash
PYTHONPATH=. pytest -q \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
````

### Full Test Suite

````bash
PYTHONPATH=. pytest -q
````

기대 결과:

- 실패 0건
- 기존 Redis hit, miss, timeout, connection error, malformed payload fallback test 유지
- malformed 또는 unsupported Redis URL fallback test 추가 통과
- 실제 passed 및 subtests 수를 Verification에 기록

### YAML Parse

````bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
````

### Markdown Code Fence Check

````bash
python - <<'PY'
from pathlib import Path

paths = [
    Path("docs/tasks/feature-home-api-redis-cache.md"),
    Path("docs/fixes/feature-home-api-redis-cache-approved-fixes.md"),
    Path("docs/verification/feature-home-api-redis-cache.md"),
]

for path in paths:
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if line.strip() == "```":
            print(f"{path}:{number}: language identifier missing")
PY
````

기대 결과: 출력 없음.

### Placeholder Check

````bash
rg -n "ruby -e '\.\.\.'|rg .*\.\.\." \
  docs/devlog/feature-home-api-redis-cache.md \
  docs/pr/feature-home-api-redis-cache.md
````

기대 결과: 출력 없음.

### Task Parser Check

````bash
awk '
  /^## Implementation Units/ { in_units=1; next }
  in_units && /^## / { in_units=0 }
  in_units && NF { print }
' docs/tasks/feature-home-api-redis-cache.md
````

기대 결과:

````
- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [x] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [x] UNIT-05: Unit/Integration Test
- [ ] UNIT-06: K3s와 운영 설정 반영
- [ ] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [ ] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
````

### Static and Scope Checks

````bash
git diff --check
````

````bash
git diff --name-only
````

Production command, Argo CD Sync, `kubectl apply/delete/patch/edit/rollout`, Redis 장애 주입, Supabase SQL, DB migration, `git push`, `git merge`는 실행하지 않는다.

## Completion Rule

- 기존 FIX-01~FIX-06은 완료 이력으로 유지하며 다시 미완료로 되돌리지 않는다.
- 신규 FIX-07~FIX-14는 실제 수정과 검증이 끝난 경우에만 `[x]`로 변경한다.
- Major인 FIX-07과 FIX-08이 통과하기 전에는 PR을 병합하지 않는다.
- UNIT-06은 Production Argo CD Manual Sync와 운영 검증 완료 전까지 `[ ]`로 유지한다.
