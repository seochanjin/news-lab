# Verification: Daily Topic Pipeline 연계 Home Cache Prewarming 및 TTL 정책 정합화

## Verification Status

passed

## Verification Scope

- UNIT-01: 현재 `/topics/home` cache-aside 경로, Home payload 생성 위치,
  Daily Topic Pipeline의 DB write transaction 및 commit 성공 이후 경계 조사.
- UNIT-02: Home payload 생성 로직을 router에서 공통 module로 분리하고, 기존
  `/topics/home` cache-aside 및 response schema 테스트를 유지함.
- UNIT-03: Home Cache 기본 TTL을 108000초로 변경하고 API Deployment 환경변수와
  관련 회귀 테스트를 갱신함.
- UNIT-04: Daily Topic Pipeline 성공 후 `db_write_performed`가 참인 execute
  결과에서 Home Cache prewarm을 실행하도록 hook을 추가하고, dry-run/no-write
  skip 및 prewarm 예외 격리를 단위 테스트로 검증함.
- UNIT-05: Pipeline prewarm Redis 미설정, Redis connection/timeout/SET 계층
  실패가 Pipeline 예외로 전파되지 않고, `operation=prewarm` bypass/warning
  로그에 credential과 전체 Redis URL이 포함되지 않음을 단위 테스트로 검증함.
- UNIT-06: Daily Topic Pipeline CronJob manifest에 Redis URL, Home Cache TTL
  108000초와 Redis timeout env를 추가하고 API Deployment와 같은 cache 설정을
  전달하는지 manifest test로 검증함.
- UNIT-07: 로컬 targeted test, keyword-selected test, 전체 pytest, K3s YAML
  parse, manifest 설정 검색, 문서 정합성 검색, diff/static gate를 수행하고
  Architecture, design, PR draft와 devlog draft를 현재 구현 기준으로 갱신함.
- UNIT-08: 3-day Home payload builder를 공통 module로 분리하고,
  `/three-day-topics/home` cache-aside, `three-day-topics:home:v1` prewarm,
  3-day CronJob Redis env와 관련 API/Pipeline/manifest 테스트를 추가함.
- UNIT-09: Weekly Home payload builder를 공통 module로 분리하고,
  `/weekly-topics/home` cache-aside, `weekly-topics:home:v1` prewarm,
  Weekly CronJob Redis env와 관련 API/Pipeline/manifest 테스트를 추가함.
- UNIT-10: 세 Home Cache key/TTL/validator 통합 회귀 테스트를 추가하고,
  K3s manifest, 전체 pytest, 문서 정합성과 scope diff를 최종 검증함.
- DB schema와 migration 변경은 수행하지 않음.
- Kubernetes manifest 변경은 API Deployment와 Daily·3-day·Weekly CronJob의
  Redis cache env 추가/정합화로 제한함.
- 운영 검증은 수행하지 않음.

## Commands Run

Command:
`pwd && git branch --show-current && git status --short`
Result:
- CWD: `/Users/seochanjin/workspace/NewsLab/news-lab`
- Branch: `feat/home-cache-prewarm`
- Existing working tree state included modified `docs/tasks/main.md` and untracked
  branch workflow docs including this task/verification file.
Status: passed

## UNIT-08 Implementation Verification

Command:
`pwd && git branch --show-current && git status --short`
Result:
- CWD remained `/Users/seochanjin/workspace/NewsLab/news-lab`.
- Branch remained `feat/home-cache-prewarm`.
- Working tree already contained prior UNIT-01 through UNIT-07 changes and
  untracked branch workflow artifacts before UNIT-08 implementation.
Status: passed

Command:
`sed -n '1,240p' AGENTS.md`
Result:
- Re-read project workflow, WIP 1, safety rules, workflow artifact paths and
  verification principles before UNIT-08.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read task goal, scope, do-not-change, expected files, test commands and
  acceptance criteria.
- Confirmed UNIT-08 is the only current implementation unit and UNIT-09/10 remain
  pending.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Re-read source-of-truth order, WIP 1, checklist and verification recording
  rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Re-read implementation, Python docstring, verification and completion reporting
  rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-read local verification gates and recording format.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Re-read forbidden commands, human-controlled operations and sensitive
  information rules.
Status: passed

Command:
`sed -n '1,220p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy. UNIT-08 modified existing Python modules
  and tests, so Korean module/function/test docstrings were kept or added for
  new meaningful code paths.
Status: passed

Command:
`rg -n "three-day-topics/home|three_day|ThreeDay|three-day|home_topics|HomeTopicsCache|prewarm|topics:home:v1" app scripts tests k8s docs/architecture docs/design docs/runbooks docs/tasks/feat-home-cache-prewarm.md`
Result:
- Confirmed `/three-day-topics/home` was implemented in
  `app/routers/three_day_topics.py` with direct DB query before UNIT-08.
- Confirmed Daily Home cache patterns in `app/home_topics_cache.py`,
  `app/home_topics_payload.py`, `scripts/run_daily_topic_pipeline.py` and related
  tests.
- Confirmed 3-day Pipeline entrypoint and tests are
  `scripts/run_three_day_topic_pipeline.py` and
  `tests/test_run_three_day_topic_pipeline.py`.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_cache.py`
Result:
- Read existing Daily Home cache key, TTL, serializer, validation and fail-open
  behavior before adding the 3-day key and validator.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_payload.py`
Result:
- Read shared Daily Home payload builder before adding the 3-day Home payload
  builder and prewarm helper.
Status: passed

Command:
`sed -n '1,320p' app/routers/three_day_topics.py`
Result:
- Confirmed `/three-day-topics/home` directly queried PostgreSQL before UNIT-08
  and returned `generated_at`, `reference_date`, `window_start`, `window_end` and
  `items`.
Status: passed

Command:
`sed -n '1,520p' scripts/run_three_day_topic_pipeline.py`
Result:
- Confirmed 3-day Pipeline creates a run, replaces the latest 72-hour window
  through repository transactions, finishes the run, and had no Home cache
  prewarm hook before UNIT-08.
Status: passed

Command:
`sed -n '79,170p' app/services/three_day_topic_pipeline/summary_persistence_stage.py`
Result:
- Confirmed execute mode calls `repository.replace_window_topics()` only when
  generated topics exist or an empty selected set should replace the window.
Status: passed

Command:
`sed -n '130,260p' app/services/three_day_topic_pipeline/repository.py`
Result:
- Confirmed `create_run()`, `finish_run()` and `replace_window_topics()` each use
  `engine.begin()` transactions and that `replace_window_topics()` returns saved
  topic IDs after commit.
Status: passed

Command:
`sed -n '1,220p' k8s/news-three-day-topic-pipeline-cronjob.yaml`
Result:
- Confirmed 3-day CronJob had DB and summary Secret env only before UNIT-08 and
  lacked Redis URL, 3-day TTL and Redis timeout env.
Status: passed

Command:
`python -m py_compile app/home_topics_cache.py app/home_topics_payload.py app/routers/three_day_topics.py scripts/run_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_home_api_redis_k8s_manifest.py tests/test_three_day_topic_pipeline_cronjob_manifest.py`
Result:
- 30 tests passed and 2 subtests passed in 0.45s.
Status: passed

Command:
`rg -n "topics/home|three-day-topics/home|weekly-topics/home|home_topics|HomeTopicsCache|topics:home:v1" app tests`
Result:
- Confirmed Daily and 3-day Home payload/cache references are in shared payload
  and cache modules plus router/tests.
- Confirmed Weekly Home API still uses its existing direct route and remains
  UNIT-09 scope.
Status: passed

Command:
`rg -n "run_daily_topic_pipeline|run_three_day_topic_pipeline|run_weekly_topic_pipeline|engine.begin|replace_window|CACHE_TTL|REDIS_TIMEOUT" app scripts tests k8s`
Result:
- Confirmed Daily and 3-day Pipeline cache env/tests are present.
- Confirmed Weekly Pipeline references remain present but unchanged for UNIT-09.
Status: passed

Command:
`rg --files tests | rg "topics_api|three_day|weekly|home|cache|cronjob_manifest"`
Result:
- Listed targeted API, 3-day, weekly, home, cache and CronJob manifest tests used
  for keyword-selected verification.
Status: passed

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`
Result:
- Branch remained `feat/home-cache-prewarm`.
- Working tree includes prior UNIT changes plus UNIT-08 changes in 3-day API,
  3-day Pipeline, 3-day CronJob manifest, tests and docs.
- Untracked branch workflow docs and `app/home_topics_payload.py` remain reported
  separately by `git status --short`.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm"`
Result:
- 127 tests passed, 308 tests deselected, and 24 subtests passed in 0.54s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 435 tests passed and 83 subtests passed in 15.72s.
Status: passed

Command:
`rg -n "UNIT-08 변경 결과|\\[x\\] UNIT-08|three-day-topics:home:v1|THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS|Weekly Home Cache-aside" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/architecture/backend-api.md docs/design/home-api-redis-cache.md docs/runbooks/cronjobs.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-08 result notes and checked checklist entry are present.
- Confirmed 3-day key, 3-day TTL env and UNIT-09 Weekly pending notes are present
  in task, architecture/design/runbook and PR/devlog drafts.
Status: passed

Command:
`git diff --check && git status --short`
Result:
- `git diff --check` reported no whitespace errors.
- `git status --short` showed the expected working tree with prior UNIT changes,
  UNIT-08 changes, untracked branch workflow docs and no DB/frontend tracked
  changes.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- Final re-run produced no output. DB migration and frontend paths have no tracked
  diff.
Status: passed

Command:
`Argo CD Manual Sync, kubectl apply/rollout, Redis key deletion, manual CronJob creation, production API verification`
Result:
- Not executed by Agent. These are human-controlled or production-impacting
  operations under `docs/agent/forbidden-commands.md`.
- No human-provided production logs were available in this turn.
Status: human-required

Command:
`sed -n '1,260p' AGENTS.md`
Result:
- Project workflow, WIP 1, safety rules, workflow artifact paths and verification
  principles were read.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Task goal, scope, do-not-change, expected files, test commands and early sections
  were read.
Status: passed

Command:
`sed -n '261,620p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Acceptance criteria, notes and Implementation Units were read. UNIT-01 is the
  only allowed current unit.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Source-of-truth order, WIP 1, checklist and verification recording rules were
  read.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Codex implementation, verification and completion reporting rules were read.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Verification gate and recording format were read.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Forbidden commands, human-controlled operations and sensitive information rules
  were read.
Status: passed

Command:
`sed -n '1,220p' docs/agent/task-authoring-guide.md`
Result:
- Python documentation policy was read. UNIT-01 only modified Markdown docs, so
  no Python docstring change was required.
Status: passed

Command:
`rg -n "topics/home|home_topics|topics_home|home_topics_cache|topics:home:v1" app tests`
Result:
- Located Home API route and payload builder in `app/routers/topics.py`.
- Located cache key, TTL and fail-open cache wrapper in `app/home_topics_cache.py`.
- Located existing Home cache-aside tests in `tests/test_topics_api.py`.
Status: passed

Command:
`rg -n "daily.topic|daily_topic|commit\\(|session.commit|transaction|REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS" app tests k8s`
Result:
- Located Daily pipeline modules under `app/services/daily_topic_pipeline/` and
  `scripts/run_daily_topic_pipeline.py`.
- Located `engine.begin()` based write transaction adapter in
  `app/services/daily_topic_pipeline/runtime.py`.
- Confirmed `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS`, and
  `REDIS_TIMEOUT_SECONDS` are present in `k8s/news-api.yaml` but not in
  `k8s/news-daily-topic-pipeline-cronjob.yaml`.
Status: passed

Command:
`sed -n '1,240p' app/routers/topics.py`
Result:
- Confirmed `/topics/home` delegates to `get_home_topics_payload()`.
- Confirmed miss path reads PostgreSQL through `fetch_home_topics_from_database()`
  then calls `cache.set(payload)`.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_cache.py`
Result:
- Confirmed key `topics:home:v1`, default TTL `60`, Redis timeout default `0.05`,
  and fail-open handling for disabled Redis, Redis errors, timeout, decode and
  validation errors.
Status: passed

Command:
`sed -n '1,620p' scripts/run_daily_topic_pipeline.py`
Result:
- Confirmed Daily pipeline entrypoint assembles runtime dependencies, calls
  `build_pipeline()`, and has no Home Cache prewarm step after pipeline execution.
Status: passed

Command:
`sed -n '1,240p' app/services/daily_topic_pipeline/runtime.py`
Result:
- Confirmed `create_save_executor()` runs `execute_save_plan()` inside
  `with engine.begin() as connection:`.
Status: passed

Command:
`sed -n '1,280p' app/services/daily_topic_pipeline/summary_persistence_stage.py`
Result:
- Confirmed `summarize_and_save_topics()` calls `save_executor(save_plan)` only
  when execute mode is enabled and there are topics to save.
Status: passed

Command:
`sed -n '120,260p' scripts/save_topic_summaries.py`
Result:
- Confirmed `execute_save_plan()` writes `topics` and `topic_articles` within the
  caller-provided transaction and updates saved count analysis after writes.
Status: passed

Command:
`sed -n '1,220p' k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- Confirmed Daily CronJob currently passes DB and OpenAI secret references only;
  Redis URL, Home cache TTL and Redis timeout env vars are absent.
Status: passed

Command:
`sed -n '1,140p' k8s/news-api.yaml`
Result:
- Confirmed API deployment has `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS=60`,
  and `REDIS_TIMEOUT_SECONDS=0.05`.
Status: passed

Command:
`sed -n '1,140p' k8s/argocd/news-api-application.yaml`
Result:
- Confirmed Argo CD Application source is `main` / `k8s`, with only
  `cluster-issuer.yaml` excluded.
Status: passed

Command:
`git branch --show-current`
Result:
- Branch remained `feat/home-cache-prewarm`.
Status: passed

Command:
`git status --short`
Result:
- Existing modified `docs/tasks/main.md` remained.
- Branch workflow docs including `docs/tasks/feat-home-cache-prewarm.md` and
  `docs/verification/feat-home-cache-prewarm.md` are untracked in the current
  working tree.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff only showed pre-existing `docs/tasks/main.md` change because this
  branch task and verification docs are currently untracked.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff only showed `docs/tasks/main.md`.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git ls-files --others --exclude-standard docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed both task and verification files are untracked files in this working
  tree.
Status: passed

Command:
`rg -n "UNIT-01 조사 결과|UNIT-01 only|\\[x\\] UNIT-01" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-01 investigation section, UNIT-01 verification scope and checked
  UNIT-01 checklist entry are present.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`rg --files tests | rg 'test_home_topics_cache|test_topics_api|test_run_daily_topic_pipeline|test_daily_topic_pipeline_cronjob_manifest|test_home_api_redis_k8s_manifest'`
Result:
- `tests/test_home_topics_cache.py` does not exist in the current repository.
- Related Home/API/Pipeline/manifest tests are
  `tests/test_topics_api.py`, `tests/test_run_daily_topic_pipeline.py`,
  `tests/test_home_api_redis_k8s_manifest.py`, and
  `tests/test_daily_topic_pipeline_cronjob_manifest.py`.
Status: passed

Command:
`rg -n "초기 TTL|TTL은 60|TTL 60|60초|HOME_TOPICS_CACHE_TTL_SECONDS=60|TTL: 60초|초기값이다" docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/design docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- Current output only matches devlog historical context describing the previous
  60-second TTL problem.
- No stale 60-second TTL policy wording remains in Architecture, Runbook, design
  or PR draft docs checked by this command.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff includes Home cache/API/pipeline files, architecture/design docs,
  API and Daily CronJob manifests, related tests, and existing
  `docs/tasks/main.md`.
- Untracked branch workflow docs, PR/devlog drafts and `app/home_topics_payload.py`
  are not included in `git diff --stat`.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff includes `app/home_topics_cache.py`, `app/routers/topics.py`,
  `docs/architecture/backend-api.md`, `docs/design/home-api-redis-cache.md`,
  `docs/tasks/main.md`, `k8s/news-api.yaml`,
  `k8s/news-daily-topic-pipeline-cronjob.yaml`,
  `scripts/run_daily_topic_pipeline.py`, and related test files.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_topics_api.py tests/test_run_daily_topic_pipeline.py tests/test_home_api_redis_k8s_manifest.py tests/test_daily_topic_pipeline_cronjob_manifest.py`
Result:
- 48 tests passed and 3 subtests passed in 0.43s.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or cache or daily_topic"`
Result:
- 56 tests passed, 372 tests deselected, and 3 subtests passed in 0.40s.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 428 tests passed and 81 subtests passed in 15.46s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`rg -n "REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS|108000" k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- `k8s/news-api.yaml` and `k8s/news-daily-topic-pipeline-cronjob.yaml` both
  contain `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS` value `"108000"` and
  `REDIS_TIMEOUT_SECONDS`.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`git status --short`
Result:
- Working tree shows expected branch changes in Home cache/API/pipeline files,
  architecture/design docs, API and Daily CronJob manifests, related tests and
  workflow docs.
- No production-controlled command output was produced.
Status: passed

Command:
`rg -n "UNIT-07 변경 결과|\\[x\\] UNIT-07|Current output only matches devlog|UNIT-08 production" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-07 result notes and checked checklist entry are present in the
  task file.
- Confirmed verification notes that UNIT-08 production rollout and Pipeline-based
  prewarm verification remain pending.
Status: passed

Command:
`git diff --check`
Result:
- Final re-run after UNIT-07 documentation and verification updates reported no
  whitespace errors.
Status: passed

Command:
`git status --short`
Result:
- Final visible working tree includes expected branch changes and untracked
  branch workflow artifacts.
Status: passed

Command:
`rg -n "FakeRedisSetClient|test_home_cache_prewarm_disabled_redis|test_home_cache_prewarm_redis_set_failures" tests/test_run_daily_topic_pipeline.py`
Result:
- Confirmed UNIT-05 fake Redis SETEX client and the two new prewarm fail-open
  test methods are present in `tests/test_run_daily_topic_pipeline.py`.
Status: passed

Command:
`git diff --check`
Result:
- Re-run after UNIT-05 verification record update completed with no output.
Status: passed

Command:
`sed -n '389,424p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-01 investigation notes and checklist update are present in the
  task file.
Status: passed

Command:
`sed -n '1,280p' app/routers/topics.py`
Result:
- Read the current `/topics/home` router implementation before moving the Home
  payload builder responsibility.
Status: passed

Command:
`sed -n '1,280p' app/home_topics_cache.py`
Result:
- Confirmed `HomeTopicsCache` remains the cache dependency used by the Home
  payload path.
Status: passed

Command:
`sed -n '1,360p' tests/test_topics_api.py`
Result:
- Read existing Home cache-aside tests for miss, hit, Redis failures, malformed
  payload fallback and response schema.
Status: passed

Command:
`rg -n "fetch_home_topics_from_database|get_home_topics_payload|get_home_topics\\(" app tests`
Result:
- Confirmed Home payload builder references were limited to
  `app/routers/topics.py` and `tests/test_topics_api.py` before the UNIT-02
  change.
Status: passed

Command:
`sed -n '1,150p' app/routers/topics.py`
Result:
- Confirmed router now imports `get_home_topics_payload` from
  `app.home_topics_payload` and delegates `/topics/home` to that shared module.
Status: passed

Command:
`sed -n '1,180p' app/home_topics_payload.py`
Result:
- Confirmed the new module contains Korean module/function docstrings,
  `HOME_TOPICS_LIMIT=10`, `get_home_topics_payload()` and
  `fetch_home_topics_from_database()`.
Status: passed

Command:
`rg -n "fetch_home_topics_from_database|get_home_topics_payload|HOME_TOPICS_LIMIT" app tests`
Result:
- Confirmed Home payload generation now lives in `app/home_topics_payload.py`.
- Confirmed `/topics/home` router and tests reference the shared module.
Status: passed

Command:
`python -m py_compile app/home_topics_payload.py app/routers/topics.py tests/test_topics_api.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`pytest -q tests/test_topics_api.py`
Result:
- Failed during collection with `ModuleNotFoundError: No module named 'app'`.
- This run did not execute tests because the current shell did not add the
  repository root to Python import path.
Status: failed

Command:
`rg -n "DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS|HOME_TOPICS_CACHE_TTL_SECONDS|ttl_seconds=60|\"60\"|108000" app tests k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- Confirmed `DEFAULT_HOME_TOPICS_CACHE_TTL_SECONDS = 108000` in
  `app/home_topics_cache.py`.
- Confirmed `k8s/news-api.yaml` uses `HOME_TOPICS_CACHE_TTL_SECONDS` value
  `"108000"`.
- Confirmed remaining `ttl_seconds=60` occurrences are explicit fake-cache test
  setups, not the default TTL policy.
- Confirmed Daily CronJob still has no Redis/Home cache env in UNIT-03; this is
  left for later UNIT scope.
Status: passed

Command:
`pytest -q tests/test_topics_api.py tests/test_home_api_redis_k8s_manifest.py`
Result:
- Test collection failed with `ModuleNotFoundError: No module named 'app'`
  because the shell did not include the repository root in `PYTHONPATH`.
Status: failed

Command:
`PYTHONPATH=. pytest -q tests/test_topics_api.py tests/test_home_api_redis_k8s_manifest.py`
Result:
- 20 tests passed in 0.35s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`rg -n "REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS|108000" k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- `k8s/news-api.yaml` contains `REDIS_URL`,
  `HOME_TOPICS_CACHE_TTL_SECONDS` value `"108000"` and
  `REDIS_TIMEOUT_SECONDS`.
- `k8s/news-daily-topic-pipeline-cronjob.yaml` did not match these settings in
  UNIT-03; Daily CronJob env propagation remains pending for the later manifest
  UNIT.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff showed `app/home_topics_cache.py`, `app/routers/topics.py`,
  `docs/tasks/main.md`, `k8s/news-api.yaml`,
  `tests/test_home_api_redis_k8s_manifest.py`, and `tests/test_topics_api.py`.
- The new `app/home_topics_payload.py` and branch workflow docs remain untracked,
  so they are not included in `git diff --stat`.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff showed `app/home_topics_cache.py`, `app/routers/topics.py`,
  `docs/tasks/main.md`, `k8s/news-api.yaml`,
  `tests/test_home_api_redis_k8s_manifest.py`, and `tests/test_topics_api.py`.
- Untracked files are reported separately by `git status --short`.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_topics_api.py`
Result:
- 15 tests passed in 0.39s.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or cache or daily_topic"`
Result:
- 50 tests passed and 372 tests were deselected in 0.45s.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff showed `app/routers/topics.py`, `docs/tasks/main.md`, and
  `tests/test_topics_api.py`.
- The new `app/home_topics_payload.py` and branch workflow docs are untracked,
  so they are not included in `git diff --stat`.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff showed `app/routers/topics.py`, `docs/tasks/main.md`, and
  `tests/test_topics_api.py`.
- Untracked files are reported separately by `git status --short`.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`git status --short`
Result:
- UNIT-02 code changes are `app/routers/topics.py`, `tests/test_topics_api.py`,
  and new untracked `app/home_topics_payload.py`.
- Existing pre-UNIT working tree entries remain, including modified
  `docs/tasks/main.md` and untracked branch workflow docs.
Status: passed

Command:
`rg -n "UNIT-02 변경 결과|\\[x\\] UNIT-02|UNIT-02:" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-02 result notes, UNIT-02 verification scope and checked UNIT-02
  checklist entry are present.
Status: passed

Command:
`git diff --check`
Result:
- Re-run after documentation updates; no whitespace errors were reported.
Status: passed

Command:
`git status --short`
Result:
- Final visible working tree state still includes UNIT-02 code changes
  `app/routers/topics.py`, `tests/test_topics_api.py`, untracked
  `app/home_topics_payload.py`, plus pre-existing branch workflow docs and
  modified `docs/tasks/main.md`.
Status: passed

Command:
`rg -n "Current cache key is `topics:home:v1`; current default TTL|\[x\] UNIT-03|UNIT-03 변경 결과|UNIT-04\+|Kubernetes manifest 변경" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Command failed because unescaped backticks in the double-quoted shell string
  were interpreted by `zsh` as command substitution.
- Shell reported `zsh:1: command not found: topics:home:v1`.
Status: failed

Command:
`rg -n 'Current cache key is `topics:home:v1`; current default TTL|\[x\] UNIT-03|UNIT-03 변경 결과|UNIT-04\+|Kubernetes manifest 변경' docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed `UNIT-03 변경 결과` and checked UNIT-03 checklist entry are present
  in the task file.
- Confirmed verification scope notes the limited `k8s/news-api.yaml` manifest
  change.
- Confirmed verification results now report current default TTL as `108000`.
- Confirmed pending verification starts at UNIT-04+.
Status: passed

Command:
`git diff -- docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- No output because both branch workflow docs are currently untracked files in
  this working tree.
Status: passed

Command:
`git diff --check`
Result:
- Final re-run after UNIT-03 documentation updates; no whitespace errors were
  reported.
Status: passed

Command:
`git status --short`
Result:
- Visible working tree includes UNIT-03 changes in `app/home_topics_cache.py`,
  `k8s/news-api.yaml`, `tests/test_home_api_redis_k8s_manifest.py`, and
  `tests/test_topics_api.py`.
- Existing UNIT-02 changes remain in `app/routers/topics.py`,
  `tests/test_topics_api.py`, and untracked `app/home_topics_payload.py`.
- Pre-existing workflow docs and `docs/tasks/main.md` remain present.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff showed `app/home_topics_cache.py`, `app/routers/topics.py`,
  `docs/tasks/main.md`, `k8s/news-api.yaml`,
  `tests/test_home_api_redis_k8s_manifest.py`, and `tests/test_topics_api.py`.
- Untracked files, including this task and verification document, are not shown
  by `git diff --stat`.
Status: passed

Command:
`pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/feat-home-cache-prewarm.md' -g 'docs/verification/feat-home-cache-prewarm.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'`
Result:
- CWD: `/Users/seochanjin/workspace/NewsLab/news-lab`.
- Branch: `feat/home-cache-prewarm`.
- Confirmed all required task, verification and workflow documents exist.
Status: passed

Command:
`git status --short`
Result:
- Pre-UNIT working tree contained existing changes in Home cache/API files,
  `k8s/news-api.yaml`, tests, `docs/tasks/main.md`, and untracked branch
  workflow docs.
Status: passed

Command:
`sed -n '1,260p' AGENTS.md`
Result:
- Re-read project workflow, WIP 1, safety rules, artifact paths and verification
  principles before UNIT-05.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read Task goal, scope, do-not-change, expected files, DB/API changes and
  test commands before UNIT-05.
Status: passed

Command:
`sed -n '261,620p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read acceptance criteria, notes and implementation units.
- Confirmed only UNIT-05 was in current scope for this run.
Status: passed

Command:
`sed -n '1,260p' docs/verification/feat-home-cache-prewarm.md`
Result:
- Read existing verification history and pending state through prior UNIT-04
  records.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Re-confirmed WIP 1, source-of-truth order, checklist and verification recording
  rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Re-confirmed implementation, Python docstring, verification and completion
  reporting rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-confirmed allowed verification gates and command recording format.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Re-confirmed forbidden and human-controlled production commands.
Status: passed

Command:
`sed -n '1,260p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy before modifying Python tests.
Status: passed

Command:
`rg -n "UNIT-0|fail-open|prewarm|warning|Redis|redis|HOME_TOPICS|topics:home:v1" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md app tests scripts k8s`
Result:
- Located UNIT-05 requirements in the task file.
- Located prewarm hook and logging in `scripts/run_daily_topic_pipeline.py`,
  fail-open cache behavior in `app/home_topics_cache.py`, and existing prewarm
  tests in `tests/test_run_daily_topic_pipeline.py`.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_cache.py`
Result:
- Confirmed `HomeTopicsCache.set()` logs `operation=prewarm`, catches Redis
  connection/timeout/serialization errors, and records only exception class names.
Status: passed

Command:
`sed -n '1,220p' app/home_topics_payload.py`
Result:
- Confirmed `prewarm_home_topics_cache()` reuses Home payload builder and calls
  `cache.set(payload, operation="prewarm")`.
Status: passed

Command:
`sed -n '1,760p' scripts/run_daily_topic_pipeline.py`
Result:
- Confirmed `_prewarm_home_topics_cache_after_success()` skips dry-run/no-write
  cases, catches prewarm exceptions, and logs only exception class names.
Status: passed

Command:
`sed -n '1,760p' tests/test_run_daily_topic_pipeline.py`
Result:
- Read existing Daily Pipeline and prewarm tests before adding UNIT-05 Redis
  fail-open/logging coverage.
Status: passed

Command:
`sed -n '1,460p' tests/test_topics_api.py`
Result:
- Rechecked existing Home API Redis fail-open tests for API cache-aside coverage
  and avoided duplicating unrelated API cases.
Status: passed

Command:
`python -m py_compile tests/test_run_daily_topic_pipeline.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_run_daily_topic_pipeline.py`
Result:
- 24 tests passed and 3 subtests passed in 0.22s.
- Covered UNIT-05 additions for Redis disabled prewarm bypass, Redis SET
  connection error, timeout and SET-layer failure without credential or full URL
  leakage in logs.
Status: passed

Command:
`git diff -- tests/test_run_daily_topic_pipeline.py`
Result:
- Confirmed UNIT-05 test changes add `HomeTopicsCache` and a fake SETEX client,
  then verify Redis disabled and SET failure prewarm fail-open/logging behavior.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff includes prior UNIT changes plus UNIT-05 changes in
  `tests/test_run_daily_topic_pipeline.py`.
- Untracked branch workflow docs and `app/home_topics_payload.py` remain
  untracked and are not included in `git diff --stat`.
Status: passed

Command:
`git status --short`
Result:
- Working tree includes prior UNIT changes and UNIT-05 test/doc updates.
- Existing modified `docs/tasks/main.md` and untracked branch workflow docs
  remain present.
Status: passed

Command:
`git diff --check`
Result:
- Final UNIT-05 whitespace check completed with no output.
Status: passed

Command:
`rg -n "UNIT-05 변경 결과|\\[x\\] UNIT-05|UNIT-05: Pipeline prewarm|Redis disabled|24 tests passed|3 subtests" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-05 result notes and checked checklist entry are present in the
  task file.
- Confirmed UNIT-05 verification scope and targeted test result are present in
  this verification file.
Status: passed

Command:
`git status --short`
Result:
- Final visible working tree still includes prior UNIT changes, UNIT-05 test
  changes, modified `docs/tasks/main.md`, and untracked branch workflow docs.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read Task goal, scope, do-not-change, expected files, DB/API changes and
  test commands before UNIT-04 implementation.
Status: passed

Command:
`sed -n '261,620p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read acceptance criteria, notes and implementation units.
- Confirmed only UNIT-04 was in current scope.
Status: passed

Command:
`sed -n '1,260p' docs/verification/feat-home-cache-prewarm.md`
Result:
- Read existing verification history and pending state through prior UNIT-03
  records.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Re-confirmed WIP 1, source-of-truth order, checklist and verification recording
  rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Re-confirmed implementation, Python docstring, verification and completion
  reporting rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-confirmed allowed verification gates and command recording format.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Re-confirmed forbidden and human-controlled production commands.
Status: passed

Command:
`sed -n '1,240p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy before modifying Python modules and tests.
Status: passed

Command:
`sed -n '1,320p' app/home_topics_cache.py`
Result:
- Confirmed current cache key `topics:home:v1`, default TTL `108000`, fail-open
  Redis get/set behavior and existing log structure before adding prewarm
  operation logging.
Status: passed

Command:
`sed -n '1,320p' app/home_topics_payload.py`
Result:
- Confirmed shared Home payload builder already contains
  `fetch_home_topics_from_database()` and `get_home_topics_payload()`.
Status: passed

Command:
`sed -n '1,260p' app/routers/topics.py`
Result:
- Confirmed `/topics/home` router delegates to shared
  `get_home_topics_payload()` and keeps the endpoint contract unchanged.
Status: passed

Command:
`sed -n '1,700p' scripts/run_daily_topic_pipeline.py`
Result:
- Confirmed `_run()` creates the SQLAlchemy engine, calls `build_pipeline()`,
  writes optional report output and prints JSON result.
- Confirmed there was no prewarm hook after `build_pipeline()` before UNIT-04.
Status: passed

Command:
`sed -n '1,280p' app/services/daily_topic_pipeline/runtime.py`
Result:
- Confirmed `create_save_executor()` executes the save plan inside
  `with engine.begin() as connection:`, so `_run()` code after
  `build_pipeline()` is after commit success when no exception was raised.
Status: passed

Command:
`rg -n "home_topics|prewarm|build_pipeline|run_daily_topic|create_engine|logger|logging|execute" scripts app/services/daily_topic_pipeline tests`
Result:
- Located Daily pipeline test coverage in `tests/test_run_daily_topic_pipeline.py`.
- Confirmed no existing Home prewarm helper or pipeline prewarm test existed
  before UNIT-04.
Status: passed

Command:
`sed -n '1,620p' tests/test_run_daily_topic_pipeline.py`
Result:
- Read current Daily pipeline tests before adding prewarm hook tests.
Status: passed

Command:
`sed -n '1,460p' tests/test_topics_api.py`
Result:
- Read Home payload/cache tests and fake Redis utilities before changing cache
  operation logging.
Status: passed

Command:
`python -m py_compile app/home_topics_cache.py app/home_topics_payload.py scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_run_daily_topic_pipeline.py tests/test_topics_api.py`
Result:
- 38 tests passed in 0.49s.
Status: passed

Command:
`git diff -- app/home_topics_cache.py app/home_topics_payload.py scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py`
Result:
- Reviewed UNIT-04 diff.
- Tracked diff showed `HomeTopicsCache.set(operation=...)`,
  `_prewarm_home_topics_cache_after_success()` and new Daily pipeline tests.
- `app/home_topics_payload.py` is untracked in this working tree, so it was not
  included in `git diff` output even though it now contains the new
  `prewarm_home_topics_cache()` helper.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff includes previous UNIT changes plus UNIT-04 changes in
  `scripts/run_daily_topic_pipeline.py` and `tests/test_run_daily_topic_pipeline.py`.
- Untracked files, including `app/home_topics_payload.py` and branch workflow
  docs, are not shown by `git diff --stat`.
Status: passed

Command:
`git status --short`
Result:
- Working tree includes UNIT-04 changes in `scripts/run_daily_topic_pipeline.py`
  and `tests/test_run_daily_topic_pipeline.py`.
- Existing branch changes remain in Home cache/router/tests, `k8s/news-api.yaml`,
  `docs/tasks/main.md`, and untracked workflow docs.
Status: passed

Command:
`rg -n "topics/home|home_topics|topics_home|home_topics_cache|topics:home:v1" app tests`
Result:
- Confirmed `prewarm_home_topics_cache()` exists in `app/home_topics_payload.py`.
- Confirmed `_prewarm_home_topics_cache_after_success()` is referenced by Daily
  pipeline tests.
- Confirmed cache key remains `topics:home:v1`.
Status: passed

Command:
`rg -n "daily.topic|daily_topic|commit\\(|session.commit|transaction|REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS" app tests k8s`
Result:
- Confirmed Daily pipeline runtime still uses `engine.begin()` for topic save
  transaction.
- Confirmed UNIT-04 did not add Redis env vars to
  `k8s/news-daily-topic-pipeline-cronjob.yaml`; this remains pending for later
  manifest UNIT.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or cache or daily_topic"`
Result:
- 54 tests passed and 372 tests were deselected in 0.46s.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 426 tests passed and 78 subtests passed in 15.52s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`rg -n "REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS|108000" k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- `k8s/news-api.yaml` contains `REDIS_URL`,
  `HOME_TOPICS_CACHE_TTL_SECONDS` value `"108000"` and
  `REDIS_TIMEOUT_SECONDS`.
- `k8s/news-daily-topic-pipeline-cronjob.yaml` still has no Redis/Home cache env
  settings after UNIT-04; this remains pending for UNIT-06.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff shows existing branch files plus UNIT-04
  `scripts/run_daily_topic_pipeline.py` and
  `tests/test_run_daily_topic_pipeline.py`.
- Untracked `app/home_topics_payload.py` and branch workflow docs are not listed.
Status: passed

Command:
`git status --short`
Result:
- Final pre-documentation status showed modified application/test/manifest files
  and untracked branch workflow docs.
Status: passed

Command:
`rg -n "UNIT-04 변경 결과|\\[x\\] UNIT-04|UNIT-05\\+|prewarm_home_topics_cache|_prewarm_home_topics_cache_after_success" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md app/home_topics_payload.py scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py`
Result:
- Confirmed UNIT-04 result section and checked UNIT-04 checklist entry are present
  in the task file.
- Confirmed shared prewarm helper, pipeline hook and new tests are present.
- Confirmed verification notes that UNIT-05+ remains pending.
Status: passed

Command:
`git diff --check`
Result:
- Final re-run after documentation updates; no whitespace errors were reported.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff shows existing branch changes plus UNIT-04 changes in
  `scripts/run_daily_topic_pipeline.py` and
  `tests/test_run_daily_topic_pipeline.py`.
- Untracked files, including `app/home_topics_payload.py` and branch workflow
  docs, are not included in this output.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`git status --short`
Result:
- Final visible working tree includes modified application, test and manifest
  files plus untracked branch workflow docs.
- UNIT-04 tracked changes are in `scripts/run_daily_topic_pipeline.py` and
  `tests/test_run_daily_topic_pipeline.py`; UNIT-04 also extends the currently
  untracked `app/home_topics_payload.py` shared module and branch task/
  verification docs.
Status: passed

Command:
`git diff --check`
Result:
- Re-run after appending final verification notes; no whitespace errors were
  reported.
Status: passed

Command:
`git status --short`
Result:
- Final working tree still shows the expected modified files and untracked branch
  workflow docs.
Status: passed

Command:
`sed -n '1,320p' docs/agent/verification-gates.md`
Result:
- Re-read verification gate status, command recording format and local/production
  verification separation before UNIT-06.
Status: passed

Command:
`sed -n '1,320p' docs/agent/forbidden-commands.md`
Result:
- Re-read forbidden commands, human-controlled Kubernetes operations and sensitive
  information rules before UNIT-06.
Status: passed

Command:
`sed -n '1,260p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy. UNIT-06 modified one existing Python test
  method docstring and did not create a new Python module.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_cache.py`
Result:
- Confirmed default Home Cache TTL is `108000`, key is `topics:home:v1`, Redis
  timeout default is `0.05`, and Redis errors remain fail-open.
Status: passed

Command:
`sed -n '1,260p' app/home_topics_payload.py`
Result:
- Confirmed API miss and Pipeline prewarm share the Home payload builder module.
Status: passed

Command:
`sed -n '360,760p' scripts/run_daily_topic_pipeline.py`
Result:
- Confirmed `_prewarm_home_topics_cache_after_success()` runs after
  `build_pipeline()` success and only prewarms execute results with
  `db_write_performed=True`.
Status: passed

Command:
`sed -n '1,220p' k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- Before UNIT-06 patch, Daily CronJob env contained DB and OpenAI Secret refs but
  did not pass `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS`, or
  `REDIS_TIMEOUT_SECONDS`.
Status: passed

Command:
`sed -n '1,220p' tests/test_daily_topic_pipeline_cronjob_manifest.py`
Result:
- Confirmed existing Daily CronJob manifest tests checked schedule, command,
  image, Secret refs and safety settings but not Redis cache env propagation.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_daily_topic_pipeline_cronjob_manifest.py tests/test_home_api_redis_k8s_manifest.py tests/test_run_daily_topic_pipeline.py tests/test_topics_api.py`
Result:
- 48 tests passed and 3 subtests passed in 0.38s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`rg -n "REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS|108000" k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
- Confirmed both API Deployment and Daily Topic Pipeline CronJob contain
  `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS`, `REDIS_TIMEOUT_SECONDS`, and
  TTL value `"108000"`.
Status: passed

Command:
`rg -n "topics/home|home_topics|topics_home|home_topics_cache|topics:home:v1" app tests`
Result:
- Confirmed Home payload/cache references are in `app/home_topics_payload.py`,
  `app/home_topics_cache.py`, `/topics/home` router and related tests.
Status: passed

Command:
`rg -n "daily.topic|daily_topic|commit\\(|session.commit|transaction|REDIS_URL|HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_TIMEOUT_SECONDS" app tests k8s`
Result:
- Confirmed Daily CronJob now includes Redis cache env and relevant pipeline
  transaction/cache references remain in the expected application and test files.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or cache or daily_topic"`
Result:
- 56 tests passed, 372 tests deselected, and 3 subtests passed in 0.45s.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 428 tests passed and 81 subtests passed in 15.90s.
Status: passed

Command:
`git branch --show-current && git status --short`
Result:
- Branch remained `feat/home-cache-prewarm`.
- Working tree showed expected modified application, manifest, test and workflow
  docs for this branch; branch task/verification docs remain untracked in this
  working tree.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff included Home cache/API/pipeline files, API and Daily CronJob
  manifests, related tests, and existing `docs/tasks/main.md`.
- Untracked branch workflow docs and `app/home_topics_payload.py` are not included
  in `git diff --stat`.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff included `app/home_topics_cache.py`, `app/routers/topics.py`,
  `docs/tasks/main.md`, `k8s/news-api.yaml`,
  `k8s/news-daily-topic-pipeline-cronjob.yaml`,
  `scripts/run_daily_topic_pipeline.py`, and related test files.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

## Results

- `/topics/home` is implemented in `app/routers/topics.py`.
- Current Home cache read path is `get_home_topics()` →
  `get_home_topics_payload()` → `HomeTopicsCache.get()`.
- Cache hit returns cached payload without opening a DB connection.
- Cache miss/bypass opens PostgreSQL connection, calls
  `fetch_home_topics_from_database()`, then attempts `HomeTopicsCache.set()`.
- UNIT-01 조사 당시 Home payload builder는 router code에 있었다.
- UNIT-02 이후 Home payload builder는 `app/home_topics_payload.py`에 있다.
- Current cache key is `topics:home:v1`; current default TTL is `108000`.
- Daily Topic Pipeline DB topic save is executed through
  `summarize_and_save_topics()` → injected `save_executor()` →
  `create_save_executor()` → `engine.begin()` → `execute_save_plan()`.
- Commit success boundary is after the `engine.begin()` context exits normally.
- UNIT-04 added a prewarm hook after this commit boundary and UNIT-06 verified it
  with local tests.
- UNIT-06 added Redis cache settings to the Daily CronJob manifest.
- Argo CD `news-api` Application manages the `k8s` path, so Daily CronJob manifest
  changes are in its managed resource scope.
- UNIT-02 moved Home payload generation and API cache-aside orchestration into
  `app/home_topics_payload.py`.
- `app/routers/topics.py` keeps the existing `/topics/home` endpoint and delegates
  to the shared Home payload module.
- `tests/test_topics_api.py` imports Home payload functions from the shared module,
  so future Pipeline prewarm code can use the same builder without importing a
  FastAPI router module.
- UNIT-02 did not change cache key, TTL, Redis configuration, Daily Pipeline hook,
  Kubernetes manifests, DB schema, migrations or frontend files.
- UNIT-03 changed Home Cache default TTL from `60` to `108000` seconds.
- UNIT-03 changed the API Deployment `HOME_TOPICS_CACHE_TTL_SECONDS` value from
  `"60"` to `"108000"`.
- UNIT-03 added/updated tests that lock the default 30-hour TTL and the API
  manifest TTL value.
- UNIT-03 did not change `topics:home:v1`, Redis timeout, Daily Pipeline prewarm
  hook, Daily CronJob env, DB schema, migrations or frontend files.
- UNIT-04 added `prewarm_home_topics_cache()` to `app/home_topics_payload.py` so
  Pipeline prewarm uses the same PostgreSQL payload builder as API cache miss.
- UNIT-04 added `_prewarm_home_topics_cache_after_success()` to
  `scripts/run_daily_topic_pipeline.py` and calls it immediately after
  `build_pipeline()` returns.
- UNIT-04 prewarm runs only for execute results with `db_write_performed=True`.
  Dry-run and successful no-write results log `operation=prewarm` bypass and do
  not open a Home payload DB read.
- UNIT-04 changed `HomeTopicsCache.set()` to accept `operation`, preserving the
  existing default `store` log for API miss while logging pipeline overwrite as
  `event=prewarm`.
- UNIT-04 tests verify successful prewarm payload generation, dry-run/no-write
  skip, and prewarm exception isolation without leaking a sample Redis credential
  in logs.
- UNIT-04 did not change DB schema, migrations, frontend files, Kubernetes
  manifests, Daily CronJob env, endpoint path or response schema.
- UNIT-05 tests verify Redis disabled, connection error, timeout and SET failure
  prewarm paths remain fail-open and do not log the sample credential or full
  Redis URL.
- UNIT-06 changed `k8s/news-daily-topic-pipeline-cronjob.yaml` to pass
  `REDIS_URL`, `HOME_TOPICS_CACHE_TTL_SECONDS="108000"` and
  `REDIS_TIMEOUT_SECONDS="0.05"` to the Daily Pipeline container.
- UNIT-06 updated `tests/test_daily_topic_pipeline_cronjob_manifest.py` to verify
  Daily CronJob cache env values match the API Deployment cache env values.
- UNIT-06 local verification passed targeted tests, keyword-selected tests, full
  `pytest -q`, top-level K3s YAML parse, manifest setting search,
  `git diff --check`, and DB/migration/frontend diff checks.
- UNIT-07 updated `docs/architecture/backend-api.md` and
  `docs/design/home-api-redis-cache.md` so docs describe current TTL 108,000,
  Pipeline overwrite-based freshness, shared Home payload builder and
  `event=prewarm` logging.
- UNIT-07 filled `docs/pr/feat-home-cache-prewarm.md` and
  `docs/devlog/feat-home-cache-prewarm.md` from verification evidence.
- UNIT-07 local verification passed targeted tests, keyword-selected tests, full
  `pytest -q`, top-level K3s YAML parse, manifest setting search,
  documentation consistency search, `git diff --check`, and
  DB/migration/frontend diff checks.

## Manual or Production Verification

- Not performed. UNIT-01 through UNIT-07 are local investigation/code/config/docs
  changes only.
- Production rollout, Argo CD sync, manual Job creation and Redis key inspection
  remain human-controlled and were not executed.

## Pending Verification

- UNIT-08 production rollout and Pipeline-based prewarm verification remain
  pending human-controlled execution.
- Production verification is pending human execution after later implementation
  and deployment approval.

## Evidence Notes

- No `git push`, `git merge`, `kubectl`, Helm, Docker push, Supabase SQL, DB write
  script, secret edit or production verification command was run.
- `app/home_topics_payload.py` was created with Korean module and function
  docstrings according to the Python documentation policy.

## UNIT-08 Human-Controlled Verification Preparation

Command:
`git branch --show-current && git status --short`
Result:
- Branch remained `feat/home-cache-prewarm`.
- Working tree already contained prior UNIT-01 through UNIT-07 changes and
  untracked branch workflow artifacts before UNIT-08 preparation.
Status: passed

Command:
`sed -n '1,240p' AGENTS.md`
Result:
- Re-read WIP 1, safety rules, workflow artifact paths and production
  verification rules.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read Task source of truth through Scope, Do not change, Test commands and
  early task requirements.
Status: passed

Command:
`sed -n '261,620p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read operational verification sequence, acceptance criteria, notes and
  implementation checklist.
- Confirmed UNIT-08 is the only current unit.
Status: passed

Command:
`sed -n '1,260p' docs/verification/feat-home-cache-prewarm.md`
Result:
- Re-read prior verification status and UNIT-01 through UNIT-07 evidence.
Status: passed

Command:
`sed -n '261,620p' docs/verification/feat-home-cache-prewarm.md`
Result:
- Re-read local verification history and confirmed production rollout remained
  pending.
Status: passed

Command:
`sed -n '620,1420p' docs/verification/feat-home-cache-prewarm.md`
Result:
- Re-read later verification history, Results, Manual or Production Verification,
  Pending Verification and Evidence Notes.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Re-confirmed WIP 1, checklist, verification recording and human operator
  responsibilities.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Re-confirmed Codex implementation, documentation, verification and completion
  reporting rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-confirmed production verification separation and `human-required` recording
  status.
Status: passed

Command:
`sed -n '1,300p' docs/agent/forbidden-commands.md`
Result:
- Re-confirmed `kubectl apply/delete/patch/edit/rollout`, object changes,
  manual Job creation, Secret changes and production verification are
  human-controlled.
Status: passed

Command:
`sed -n '1,220p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy. UNIT-08 preparation only changed Markdown
  docs, so no Python docstring update was required.
Status: passed

Command:
`rg -n "UNIT-08|Argo|Manual Sync|prewarm|production|운영" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md docs/RUNBOOK.md docs/ARCHITECTURE.md docs/architecture docs/runbook`
Result:
- Command failed because `docs/runbook` does not exist.
- The partial output still showed UNIT-08 pending notes and Argo CD/manual
  operation references, but the command is recorded as failed due to the invalid
  path.
Status: failed

Command:
`sed -n '1,180p' docs/pr/feat-home-cache-prewarm.md`
Result:
- Confirmed PR draft still says production rollout, Argo CD Sync, manual Job
  execution and Redis key/TTL verification were not performed.
Status: passed

Command:
`sed -n '1,180p' docs/devlog/feat-home-cache-prewarm.md`
Result:
- Confirmed devlog still records UNIT-08 production verification as
  human-controlled and pending.
Status: passed

Command:
`sed -n '1,160p' docs/RUNBOOK.md`
Result:
- Confirmed Runbook index states production-impacting commands are human-run and
  links to CronJob and Argo CD runbooks.
Status: passed

Command:
`sed -n '1,260p' docs/runbooks/argocd-manual-sync-plan.md`
Result:
- Re-read Argo CD Manual Sync boundaries and confirmed Sync and Application
  changes remain human-controlled.
Status: passed

Command:
`sed -n '1,280p' docs/runbooks/cronjobs.md`
Result:
- Read the CronJob runbook before adding the Daily Topic Pipeline Home Cache
  prewarm verification procedure.
Status: passed

Command:
`sed -n '1,140p' docs/architecture/backend-api.md`
Result:
- Confirmed Architecture already documents `topics:home:v1`, TTL `108000`,
  Pipeline overwrite freshness and `event=prewarm` logging.
Status: passed

Command:
`git diff -- docs/runbooks/argocd-manual-sync-plan.md docs/runbooks/cronjobs.md docs/RUNBOOK.md docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- No tracked diff was shown at that point because branch workflow docs are
  untracked and the Runbook patch had not yet been applied.
Status: passed

Command:
`Argo CD Manual Sync, Redis DEL, Daily Pipeline manual Job, Redis EXISTS/TTL and production /topics/home verification`
Result:
- Not executed by Agent. These are human-controlled production operations under
  `docs/agent/forbidden-commands.md`.
- No human-provided production logs were available in this turn.
Status: human-required

Result:
- Added `docs/runbooks/cronjobs.md` section
  `Daily Topic Pipeline Home Cache prewarm 검증`.
- The procedure distinguishes expected Argo CD diff scope, human-run Manual Sync
  and the Redis `EXISTS`/`TTL` checks required to prove user-request-free
  Pipeline prewarm.
- UNIT-08 checklist remains unchecked because production rollout and key/TTL
  evidence were not provided.

Command:
`rg -n "Daily Topic Pipeline Home Cache prewarm 검증|UNIT-08 준비 결과|UNIT-08 Human-Controlled|Runbook에 준비|사람 제공 운영 로그" docs/runbooks/cronjobs.md docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-08 preparation notes are present in the CronJob runbook, task,
  verification and PR draft.
- The devlog contains the same pending-production-verification wording but did
  not match this exact pattern in the returned lines.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported after UNIT-08 documentation updates.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`git status --short && git diff --stat`
Result:
- Working tree includes prior UNIT-01 through UNIT-07 application, manifest,
  test and documentation changes plus UNIT-08 `docs/runbooks/cronjobs.md`.
- Branch task, verification, PR and devlog documents remain untracked in this
  working tree, so they are not included in `git diff --stat`.
Status: passed

Command:
`rg -n "UNIT-08 Implementation Verification|435 tests passed|127 tests passed|human-required|UNIT-08 변경 결과|\\[x\\] UNIT-08" docs/verification/feat-home-cache-prewarm.md docs/tasks/feat-home-cache-prewarm.md`
Result:
- Confirmed UNIT-08 implementation verification section, local test results,
  human-required production boundary, task result notes and checked UNIT-08
  checklist entry are present.
Status: passed

Command:
`git diff --check`
Result:
- Final re-run after UNIT-08 verification updates reported no whitespace errors.
Status: passed

Command:
`git status --short`
Result:
- Final visible working tree includes prior UNIT changes, UNIT-08 changes,
  untracked branch workflow artifacts and no unexpected DB/frontend changes.
Status: passed

## UNIT-09 Implementation Verification

Command:
`pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/feat-home-cache-prewarm.md' -g 'docs/verification/feat-home-cache-prewarm.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'`
Result:
- CWD remained `/Users/seochanjin/workspace/NewsLab/news-lab`.
- Branch remained `feat/home-cache-prewarm`.
- Required workflow, task, verification and Python docstring policy documents were present.
Status: passed

Command:
`git status --short`
Result:
- Working tree already contained prior UNIT changes before UNIT-09.
- UNIT-09 was implemented without reverting those existing changes.
Status: passed

Command:
`sed -n '1,240p' AGENTS.md`
Result:
- Re-read project workflow, WIP 1, safety rules, workflow artifact paths and verification principles.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read task goal, scope, do-not-change, expected files, test commands and acceptance criteria.
- Confirmed only UNIT-09 was in scope for this turn.
Status: passed

Command:
`sed -n '1,220p' docs/agent/backend-workflow.md`
Result:
- Re-read source-of-truth order, WIP 1, checklist and verification recording rules.
Status: passed

Command:
`sed -n '1,220p' docs/agent/codex-instructions.md`
Result:
- Re-read Codex implementation, Python docstring, verification and completion reporting rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-read local verification gates and recording format.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Re-read forbidden commands, human-controlled operations and sensitive information rules.
Status: passed

Command:
`sed -n '1,240p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy. UNIT-09 modified Python modules and tests, so Korean module/function/test docstrings were kept or added for meaningful code paths.
Status: passed

Command:
`rg -n "topics/home|three-day-topics/home|weekly-topics/home|home_topics|HomeTopicsCache|topics:home:v1" app tests`
Result:
- Confirmed Weekly Home API now uses `app.home_topics_payload` and `HomeTopicsCache`.
- Confirmed `weekly-topics:home:v1` references are present in cache, payload, router and tests.
Status: passed

Command:
`rg -n "run_daily_topic_pipeline|run_three_day_topic_pipeline|run_weekly_topic_pipeline|engine.begin|replace_window|CACHE_TTL|REDIS_TIMEOUT" app scripts tests k8s`
Result:
- Confirmed Weekly Pipeline prewarm hook and `WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS` manifest/test references are present.
- Confirmed Weekly repository still uses `engine.begin()` for `replace_window_topics()`.
Status: passed

Command:
`python -m py_compile app/home_topics_cache.py app/home_topics_payload.py app/routers/weekly_topics.py scripts/run_weekly_topic_pipeline.py tests/test_weekly_topics_api.py tests/test_run_weekly_topic_pipeline.py tests/test_home_api_redis_k8s_manifest.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_weekly_topics_api.py tests/test_run_weekly_topic_pipeline.py tests/test_home_api_redis_k8s_manifest.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- 30 tests passed and 2 subtests passed in 0.36s.
Status: passed

Command:
`rg --files tests | rg "topics_api|three_day|weekly|home|cache|cronjob_manifest"`
Result:
- Listed targeted API, 3-day, weekly, home, cache and CronJob manifest tests used for keyword-selected verification.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm"`
Result:
- 134 tests passed, 308 tests deselected, and 26 subtests passed in 0.44s.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 442 tests passed and 85 subtests passed in 15.11s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`git diff --check && git diff --name-only -- db migrations frontend`
Result:
- `git diff --check` reported no whitespace errors.
- DB migration and frontend paths produced no output.
Status: passed

Command:
`rg -n "Weekly Home Cache-aside|weekly-topics:home:v1|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|Daily와 3-day|Daily/3-day|UNIT-09|\\[x\\] UNIT-09" docs/architecture/backend-api.md docs/design/home-api-redis-cache.md docs/runbooks/cronjobs.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md docs/tasks/feat-home-cache-prewarm.md`
Result:
- Confirmed Weekly key, TTL env, UNIT-09 result notes and checked checklist entry are present.
- Confirmed remaining Daily/3-day wording is historical or explicitly paired with Weekly wording where appropriate.
Status: passed

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`
Result:
- Branch remained `feat/home-cache-prewarm`.
- Working tree includes prior UNIT changes plus UNIT-09 changes in Weekly API, Weekly Pipeline, Weekly CronJob manifest, tests and docs.
- Untracked branch workflow docs and `app/home_topics_payload.py` remain reported separately by `git status --short`.
Status: passed

Command:
`Argo CD Manual Sync, kubectl apply/rollout, Redis DEL, Weekly Pipeline manual Job, Redis EXISTS/TTL and production /weekly-topics/home verification`
Result:
- Not executed by Agent. These are human-controlled or production-impacting operations under `docs/agent/forbidden-commands.md`.
- No human-provided production logs were available in this turn.
Status: human-required

## UNIT-10 Final Integration Verification

Command:
`sed -n '1,260p' AGENTS.md`
Result:
- Re-read project workflow, WIP 1, safety rules, workflow artifact paths and verification principles before UNIT-10.
Status: passed

Command:
`sed -n '1,260p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read task goal, scope, do-not-change, expected files, test commands and acceptance criteria.
Status: passed

Command:
`sed -n '261,620p' docs/tasks/feat-home-cache-prewarm.md`
Result:
- Re-read acceptance criteria, notes and Implementation Units.
- Confirmed UNIT-10 is the only current implementation unit.
Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`
Result:
- Re-read source-of-truth order, WIP 1, checklist and verification recording rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
- Re-read Codex implementation, Python docstring, verification and completion reporting rules.
Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
- Re-read local verification gates and recording format.
Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
- Re-read forbidden commands, human-controlled operations and sensitive information rules.
Status: passed

Command:
`sed -n '1,220p' docs/agent/task-authoring-guide.md`
Result:
- Re-read Python documentation policy. UNIT-10 added a Python test module with Korean module, class, helper and test docstrings.
Status: passed

Command:
`python -m py_compile tests/test_home_cache_integration.py`
Result:
- Python compilation completed with no output.
Status: passed

Command:
`PYTHONPATH=. pytest -q tests/test_home_cache_integration.py`
Result:
- 1 test passed in 0.10s.
Status: passed

Command:
`rg --files tests | rg "topics_api|three_day|weekly|home|cache|cronjob_manifest"`
Result:
- Listed targeted API, 3-day, weekly, home, cache and CronJob manifest tests.
- Confirmed the new `tests/test_home_cache_integration.py` is included in the target set.
Status: passed

Command:
`rg -n "topics/home|three-day-topics/home|weekly-topics/home|home_topics|HomeTopicsCache|topics:home:v1" app tests`
Result:
- Confirmed three Home API routes, shared payload module, cache module, three cache keys and related API/Pipeline tests are present.
Status: passed

Command:
`rg -n "run_daily_topic_pipeline|run_three_day_topic_pipeline|run_weekly_topic_pipeline|engine.begin|replace_window|CACHE_TTL|REDIS_TIMEOUT" app scripts tests k8s`
Result:
- Confirmed Daily, 3-day and Weekly Pipeline prewarm hooks and API/CronJob Redis env references are present.
- Confirmed 3-day and Weekly repository window replacement paths still use `engine.begin()`.
Status: passed

Command:
`git branch --show-current`
Result:
- Branch remained `feat/home-cache-prewarm`.
Status: passed

Command:
`git status --short`
Result:
- Working tree includes prior UNIT changes plus UNIT-10 changes in `tests/test_home_cache_integration.py`, task, verification, PR and devlog docs.
- Existing untracked branch workflow docs and generated review/fix docs remain untracked.
Status: passed

Command:
`git diff --stat`
Result:
- Tracked diff includes Home cache/API/pipeline files, architecture/design/runbook docs, K3s manifests and related tests.
- Untracked branch workflow docs, `app/home_topics_payload.py` and `tests/test_home_cache_integration.py` are not included in `git diff --stat`.
Status: passed

Command:
`git diff --name-only`
Result:
- Tracked diff is limited to expected application, script, K3s manifest, test and documentation paths for this branch.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm"`
Result:
- 135 tests passed, 308 tests deselected, and 26 subtests passed in 0.42s.
Status: passed

Command:
`PYTHONPATH=. pytest -q`
Result:
- 443 tests passed and 85 subtests passed in 15.37s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully:
  `cluster-issuer`, `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`rg -n "Daily-only|Daily only|daily-only|UNIT-10에서|UNIT-10 범위|세 Home Cache 통합 회귀 테스트.*남|final.*pending|전체 pytest|443 passed|435 passed|428 passed|K3s YAML parse|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS|HOME_TOPICS_CACHE_TTL_SECONDS" docs/architecture/backend-api.md docs/design/home-api-redis-cache.md docs/runbooks/cronjobs.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`
Result:
- Found expected TTL env references and the current `443 passed, 85 subtests passed` result.
- Remaining `Daily-only` matches are task historical notes about UNIT-01 through UNIT-07, not current behavior.
- A stale UNIT-10 pending note was found in devlog before documentation update and removed.
Status: passed

Command:
`Argo CD Manual Sync, kubectl apply/rollout, Redis DEL, manual Pipeline Jobs, Redis EXISTS/TTL and production Home API verification`
Result:
- Not executed by Agent. These are human-controlled or production-impacting operations under `docs/agent/forbidden-commands.md`.
- No human-provided production logs were available in this turn.
Status: human-required

## Approved Fix Application Verification

### FIX-01

Command:
`PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- 39 tests passed and 2 subtests passed in 0.44s after removing the unused
  3-day router limit constant.
Status: passed

### FIX-02

Command:
`PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- 39 tests passed and 2 subtests passed in 0.39s after adding the Weekly
  CronJob/API Deployment TTL cross-check.
Status: passed

### FIX-03

Command:
`PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- 41 tests passed and 8 subtests passed in 0.51s.
- The new 3-day and Weekly tests covered `OSError`, `TimeoutError` and
  `ValueError` from Redis SETEX, retained successful Pipeline flow, and verified
  warning logs omit the credential and complete Redis URL.
Status: passed

### FIX-04

Command:
`PYTHONPATH=. pytest -q tests/test_three_day_topics_api.py tests/test_run_three_day_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`
Result:
- 41 tests passed and 8 subtests passed in 0.39s after changing the shared
  3-day API fixture status from `ready` to the Pipeline's stored `draft` state.
Status: passed

### FIX-05

Command:
`PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"`
Result:
- 137 tests passed, 308 tests were deselected, and 32 subtests passed in 0.61s.
- Existing `tests/test_topics_api.py` cases cover malformed and unsupported
  `REDIS_URL`, disabled cache state and PostgreSQL fallback, so no duplicate test
  was added.
Status: passed

## Approved Fix Final Verification

Command:
`PYTHONPATH=. pytest -q`
Result:
- 445 tests passed and 91 subtests passed in 16.18s.
Status: passed

Command:
`ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'`
Result:
- Parsed all top-level Kubernetes YAML files successfully: `cluster-issuer`,
  `news-api`, Daily/three-day/weekly/RSS CronJobs and Redis.
Status: passed

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`git diff --name-only -- db migrations frontend`
Result:
- No output. DB migration and frontend paths have no tracked diff.
Status: passed

Command:
`sed -n '1,320p' docs/pr/feat-home-cache-prewarm.md` and
`sed -n '1,360p' docs/devlog/feat-home-cache-prewarm.md`
Result:
- Read-only review confirmed both drafts describe the final Daily, 3-day and
  Weekly scope and leave production verification as human-controlled work.
- Both drafts record the current final `445 passed, 91 subtests passed` result.
- The older `443 passed, 85 subtests passed` remains only in the Task as an
  explicit historical baseline and in this Verification document's historical
  command/result records; it is not a stale PR or devlog result.
Status: passed

## CodeRabbit Approved Fix Verification

### FIX-06

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
- The approved fixes document already records FIX-05 as verified by the existing
  malformed/unsupported `REDIS_URL` tests, with no duplicate test or additional
  investigation remaining. The CodeRabbit checklist item was marked complete.
Status: passed

### FIX-07

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
- The PR draft now labels local verification as passed and lists Production
  rollout, Argo CD Manual Sync, Redis key/TTL checks and Production Home API
  checks separately as `pending / human-required`.
Status: passed

### FIX-08

Command:
`rg -n "Review Summary|Problems Found|Required Fixes Before PR|Optional Improvements|Suggested Test Commands|Risk Notes|not performed" docs/reviews/feat-home-cache-prewarm-coderabbit.md docs/reviews/feat-home-cache-prewarm-antigravity.md`
Result:
- The CodeRabbit artifact contains the actual Review Summary, Problems Found,
  Required Fixes, Optional Improvements, Suggested Test Commands and Risk Notes.
- The Antigravity artifact records `not performed` and no longer contains empty
  review result headings.
Status: passed

### FIX-09

Command:
`rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|RUN_ID|db_write_performed|AlreadyExists" docs/runbooks/cronjobs.md`
Result:
- The Argo CD expected diff checklist now includes the API Deployment Redis URL,
  Redis timeout and Weekly Home Cache TTL, while retaining the existing
  Daily/3-day TTL and CronJob settings.
Status: passed

### FIX-10

Command:
`rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|RUN_ID|db_write_performed|AlreadyExists" docs/runbooks/cronjobs.md`
Result:
- Daily, 3-day and Weekly prewarm verification Jobs now use timestamp-based
  `RUN_ID` values in their names.
- The Runbook states that completed Jobs are removed only by a person after Job
  logs and Redis/API verification evidence are preserved, avoiding
  `AlreadyExists` on reruns.
Status: passed

### FIX-11

Command:
`rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|RUN_ID|db_write_performed|AlreadyExists" docs/runbooks/cronjobs.md`
Result:
- The Daily Runbook requires pre-request key existence and the prewarm TTL only
  when `db_write_performed=True`.
- Dry-run or successful no-write results may skip prewarm without being treated
  as failures, consistent with the 3-day/Weekly publishable-result condition.
Status: passed

### FIX-12

Command:
`rg -n "443 passed|85 subtests|445 passed|91 subtests" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- The Task now identifies `445 passed, 91 subtests passed` as the current final
  result.
- Its remaining `443 passed, 85 subtests passed` references are explicitly
  labeled as the historical baseline from UNIT-10 before approved fixes.
Status: passed

### FIX-13

Command:
`rg -n "443 passed|85 subtests|445 passed|91 subtests" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- The Verification document now states that PR and devlog contain the current
  `445 passed, 91 subtests passed` result.
- Older results are attributed only to the Task's explicit historical baseline
  and Verification's historical command/result records. Production verification
  remains unperformed and human-required.
Status: passed

## CodeRabbit Approved Fix Final Verification

Command:
`git diff --check`
Result:
- No whitespace errors were reported.
Status: passed

Command:
`rg -n "443 passed|85 subtests|445 passed|91 subtests" docs/tasks/feat-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md docs/pr/feat-home-cache-prewarm.md docs/devlog/feat-home-cache-prewarm.md`
Result:
- Task, PR and devlog identify `445 passed, 91 subtests passed` as the current
  final result; older Task values are labeled historical and older Verification
  values remain historical command/result evidence.
Status: passed

Command:
`rg -n "REDIS_URL|REDIS_TIMEOUT_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|RUN_ID|db_write_performed|AlreadyExists" docs/runbooks/cronjobs.md`
Result:
- Confirmed the complete API Redis diff checklist, unique Job identifiers,
  rerun guidance and conditional Daily no-write verification criteria.
Status: passed

Command:
`rg -n "Review Summary|Problems Found|Required Fixes Before PR|Optional Improvements|Suggested Test Commands|Risk Notes|not performed" docs/reviews/feat-home-cache-prewarm-coderabbit.md docs/reviews/feat-home-cache-prewarm-antigravity.md`
Result:
- Confirmed the populated CodeRabbit artifact and explicit Antigravity
  `not performed` state.
Status: passed

Command:
`git status --short`
Result:
- Modified paths are limited to approved fixes, PR, review artifacts, CronJob
  Runbook, Task and Verification documents.
Status: passed

Command:
`git diff --stat`
Result:
- The diff contains documentation changes only.
Status: passed

Command:
`git diff --name-only -- app scripts tests k8s db migrations frontend`
Result:
- No output. Application, scripts, tests, Kubernetes manifests, DB, migrations
  and frontend have no diff.
Status: passed

Command:
`PYTHONPATH=. pytest -q -k "home_topics or three_day or weekly or cache or prewarm or redis_url"`,
`PYTHONPATH=. pytest -q`, and Kubernetes YAML parse
Result:
- Not run for FIX-06 through FIX-13 because these approved changes are
  documentation-only and the Approved Fixes document requires reruns only when
  Python, tests or Kubernetes YAML change.
- The existing final result remains `445 passed, 91 subtests passed`.
Status: skipped
