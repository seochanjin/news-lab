# CodeRabbit Review: Daily Topic Pipeline 연계 Home Cache Prewarming 및 TTL 정책 정합화

## Review Summary

- 대상 PR: `seochanjin/news-lab#58`
- CodeRabbit 상태: `COMMENTED`
- Pre-merge checks: 5개 통과
- Actionable comments: 8건
- Nitpick comments: 5건
- Blocker 또는 Major 결함은 발견되지 않았다.
- 핵심 구현인 Daily·3-day·Weekly Home Cache key/TTL 분리, cache-aside, PostgreSQL fallback, Pipeline prewarm, fail-open과 manifest 배치는 정상으로 평가됐다.
- 이번 리뷰의 주요 지적은 운영 Runbook, Verification/PR 문서 정합성, 비어 있는 review artifact와 일부 중복 코드 정리다.

## Problems Found

### 1. FIX-05 검증 설명이 현재 상태와 맞지 않음

- 파일: `docs/fixes/feat-home-cache-prewarm-approved-fixes.md`
- 문제: malformed `REDIS_URL` 관련 기존 테스트가 이미 확인됐고 중복 테스트를 추가하지 않았는데, 문서에는 여전히 해당 테스트를 조사하거나 실행해야 하는 것처럼 남아 있다.
- 영향: 완료된 검증과 남은 작업의 경계가 불명확해진다.

### 2. PR 문서의 Verification 상태가 로컬 검증과 운영 검증을 충분히 구분하지 않음

- 파일: `docs/pr/feat-home-cache-prewarm.md`
- 문제: `passed`가 로컬 검증 결과임을 명확히 하지 않으면 운영 반영과 Redis key/TTL 확인까지 완료된 것으로 오해될 수 있다.
- 영향: 실제 미수행인 production verification이 완료된 것처럼 읽힐 위험이 있다.

### 3. Review artifact가 빈 placeholder 상태임

- 파일:
  - `docs/reviews/feat-home-cache-prewarm-antigravity.md`
  - `docs/reviews/feat-home-cache-prewarm-coderabbit.md`
- 문제: Review Summary, Findings, Required Fixes, Suggested Tests와 Risk Notes가 비어 있다.
- 영향: 어떤 리뷰가 수행됐고 어떤 지적을 반영·보류했는지 audit trail이 남지 않는다.

### 4. Argo CD diff checklist에 API Deployment의 일부 Redis 설정이 빠져 있음

- 파일: `docs/runbooks/cronjobs.md`
- 누락 항목:
  - `REDIS_URL`
  - `REDIS_TIMEOUT_SECONDS`
  - `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS="691200"`
- 문제: 실제 manifest 변경 범위와 Runbook의 예상 diff 목록이 완전히 일치하지 않는다.
- 영향: 운영자가 정상 변경을 누락으로 판단하거나, 반대로 의도하지 않은 변경을 놓칠 수 있다.

### 5. 수동 검증 Job 이름이 고정돼 재실행 시 충돌할 수 있음

- 파일: `docs/runbooks/cronjobs.md`
- 문제: 동일한 이름으로 `kubectl create job`을 다시 실행하면 `AlreadyExists`가 발생한다.
- 영향: Runbook을 두 번째 실행할 때 검증이 중단될 수 있다.
- 수정 방향: Job 이름에 고유한 run identifier를 포함하거나, 증거 보존 후 완료 Job을 사람이 명시적으로 정리하도록 작성한다.

### 6. Daily Pipeline의 Cache 생성 조건이 실제 코드와 다름

- 파일: `docs/runbooks/cronjobs.md`
- 문제: Daily 검증 기준이 Pipeline 실행 결과와 관계없이 `EXISTS topics:home:v1 = 1`을 요구한다. 실제 구현은 `db_write_performed=True`일 때만 prewarm한다.
- 영향: 정상적인 no-write 실행을 실패로 오판할 수 있다.
- 수정 방향: Daily Cache 존재 확인은 `db_write_performed=True`인 실행에만 필수로 한다.

### 7. Task 문서의 전체 테스트 수치가 오래됨

- 파일: `docs/tasks/feat-home-cache-prewarm.md`
- 문제: 일부 위치에 `443 passed, 85 subtests passed`가 남아 있지만 승인 Fix 반영 후 최종 결과는 `445 passed, 91 subtests passed`다.
- 영향: 최종 검증 기록 간 수치가 불일치한다.

### 8. Verification의 테스트 결과 snapshot 설명이 부정확함

- 파일: `docs/verification/feat-home-cache-prewarm.md`
- 문제: `443 passed, 85 subtests passed`가 남아 있는 문서를 설명하면서 `docs/devlog/feat-home-cache-prewarm.md`까지 포함하지만, devlog에는 이미 최종 `445 passed, 91 subtests passed`가 기록돼 있다.
- 영향: 어떤 문서가 stale 상태인지 잘못 기록된다.

## Required Fixes Before PR

PR은 이미 생성됐으므로 아래 항목은 **Merge 전에 반영할 필수 문서 수정**으로 처리한다.

1. `docs/fixes/feat-home-cache-prewarm-approved-fixes.md`
   - FIX-05에 기존 malformed/unsupported `REDIS_URL` 테스트가 이미 검증됐음을 기록한다.
   - 중복 테스트는 추가하지 않았고 추가 조사도 필요 없다는 상태로 정리한다.
2. `docs/pr/feat-home-cache-prewarm.md`
   - `local verification passed`를 명시한다.
   - Production rollout, Argo CD Manual Sync, Redis key/TTL과 Home API 운영 검증은 `pending`, `human-required`로 분리한다.
3. Review artifact 정리
   - `docs/reviews/feat-home-cache-prewarm-coderabbit.md`에는 이번 리뷰 결과를 작성한다.
   - `docs/reviews/feat-home-cache-prewarm-antigravity.md`는 실제 리뷰 내용이 없다면 빈 placeholder를 유지하지 말고 제거하거나, 리뷰 미수행 상태와 사유를 명확히 기록한다.
4. `docs/runbooks/cronjobs.md`
   - Argo CD diff checklist에 API Deployment의 `REDIS_URL`, `REDIS_TIMEOUT_SECONDS`, Weekly TTL을 추가한다.
   - Daily·3-day·Weekly 수동 Job 이름을 재실행 가능한 고유 이름으로 변경한다.
   - Daily Cache `EXISTS` 검증은 `db_write_performed=True`일 때만 요구하도록 수정한다.
5. 테스트 수치 정합화
   - `docs/tasks/feat-home-cache-prewarm.md`의 stale 수치를 `445 passed, 91 subtests passed`로 갱신하거나 historical baseline이라고 명시한다.
   - `docs/verification/feat-home-cache-prewarm.md`에서 실제로 이전 수치가 남은 문서만 정확히 지목한다.

## Optional Improvements

다음은 기능 결함이 아니라 유지보수성 개선 제안이다. 이번 PR 범위를 키울 수 있으므로 보류 가능하다.

### 공통 Fake Redis test helper 추출

- `tests/test_three_day_topics_api.py`와 `tests/test_weekly_topics_api.py`의 `FakeRedisClient` 중복 제거
- Daily·3-day·Weekly Pipeline test의 `FakeRedisSetClient` 중복 제거
- 공통 `tests/fakes.py` 또는 기존 fixture module로 이동

### Payload validator 공통 helper 추출

- 파일: `app/home_topics_cache.py`
- 세 validator가 반복하는 dict, items list, required key 검사 로직을 private helper로 공통화
- 현재 동작은 정상이며, 리팩터링 과정에서 validator 경계가 약해질 수 있으므로 이번 PR에서는 보류 가능

### Cache-aside와 prewarm private helper 공통화

- 파일: `app/home_topics_payload.py`
- Daily·3-day·Weekly의 get/prewarm 함수가 같은 구조를 반복함
- 공통 `_cache_aside()`와 `_prewarm()` helper를 둘 수 있으나 현재 기능 문제는 없음

### Daily Pipeline prewarm 호출 구조 통일

- `scripts/run_daily_topic_pipeline.py`의 prewarm 호출 위치가 3-day·Weekly와 구조적으로 다르지만 helper 내부에서 예외를 모두 격리하므로 기능 문제는 없다.
- 변경 불필요. 향후 예외 처리 범위를 좁힐 때만 재검토한다.

## Suggested Test Commands

필수 수정이 문서에만 제한되면 다음 검증으로 충분하다.

```bash
git diff --check
```

```bash
rg -n "443 passed|85 subtests|445 passed|91 subtests" \
  docs/tasks/feat-home-cache-prewarm.md \
  docs/verification/feat-home-cache-prewarm.md \
  docs/pr/feat-home-cache-prewarm.md \
  docs/devlog/feat-home-cache-prewarm.md
```

```bash
rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|AlreadyExists|db_write_performed" \
  docs/runbooks/cronjobs.md
```

```bash
rg -n "Review Summary|Problems Found|Required Fixes Before PR|Suggested Test Commands|Risk Notes" \
  docs/reviews/feat-home-cache-prewarm-coderabbit.md
```

선택적 Python 리팩터링까지 반영할 경우 추가 실행한다.

```bash
PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"
```

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

## Risk Notes

- Blocker와 Major 이슈는 없다. 현재 코드의 Cache key, TTL, validator routing, cache-aside, Pipeline commit 이후 prewarm과 fail-open 계약은 정상으로 평가됐다.
- 가장 실제적인 위험은 코드보다 운영 Runbook의 조건 불일치다. 고정 Job 이름은 재검증을 막을 수 있고, Daily no-write 실행에서 Cache 존재를 무조건 요구하면 정상 실행을 실패로 판단하게 된다.
- PR 문서와 Verification에서 `passed`의 범위를 로컬 검증으로 제한하지 않으면 production verification까지 완료된 것으로 오해될 수 있다.
- 빈 review artifact는 실행 결과에는 영향을 주지 않지만 프로젝트의 리뷰 기록과 승인 근거를 약화한다.
- 중복 코드 리팩터링 제안은 모두 낮은 우선순위다. 이번 PR에서 무리하게 반영하면 검증된 Cache 동작에 불필요한 회귀 위험을 추가할 수 있다.
- 운영 Merge 이후에도 Argo CD Manual Sync와 세 Cache key/TTL 검증은 사람이 직접 수행해야 하며, 실제 운영 결과가 제공되기 전에는 production verification을 완료로 기록하지 않는다.
