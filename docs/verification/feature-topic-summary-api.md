# Verification: Topic summary DB 저장 및 조회 API MVP

## Verification Scope

이번 검증 범위는 다음과 같다.

- `topics`, `topic_articles` migration SQL 구조와 constraint 확인
- topic summary save CLI의 기본 dry-run, save plan, mocked execute path 확인
- `summary_input_hash`의 deterministic/raw-input-sensitive 동작 확인
- `/topics`, `/topics/{topic_id}` pagination/detail/404/raw text 미노출 확인
- 기존 테스트 회귀, scope, security 확인
- human-approved Supabase migration 적용 확인
- human-approved limited save execute 확인
- local API 조회 확인

## Commands Run

### Python compile

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py app/routers/topics.py app/main.py
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py
```

### Unit tests

```bash
.venv/bin/python -m unittest tests.test_topic_summary_migration tests.test_save_topic_summaries tests.test_topics_api -v
.venv/bin/python -m unittest tests.test_topic_summary tests.test_generate_topic_summary_report tests.test_topic_summary_migration tests.test_save_topic_summaries tests.test_topics_api -v
.venv/bin/python -m unittest discover -s tests -v
```

### Save CLI

```bash
.venv/bin/python scripts/save_topic_summaries.py --help
.venv/bin/python scripts/save_topic_summaries.py --window-hours 24 --max-topics 3 --max-articles-per-topic 2 --max-raw-chars-per-article 3000 --report-path docs/reports/feature-topic-summary-api-save-dry-run.md
```

### Git / scope / formatting checks

```bash
git status --short --branch
git diff --stat
git diff --check
git diff --check -- app/main.py app/routers/topics.py app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py db/migrations/005_create_topics_tables.sql tests/test_topic_summary_migration.py tests/test_save_topic_summaries.py tests/test_topics_api.py
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
git diff -- app scripts db tests docs
git status --short -- app/routers app/main.py app/utils scripts db tests k8s .github frontend Dockerfile docs/reports docs/verification/feature-topic-summary-api.md
rg -n '[[:blank:]]+$' app/routers/topics.py app/main.py app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py db/migrations/005_create_topics_tables.sql tests/test_topic_summary_migration.py tests/test_save_topic_summaries.py tests/test_topics_api.py docs/verification/feature-topic-summary-api.md
```

### Security checks

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

## Initial Implementation Verification Results

초기 구현 직후 검증 결과는 다음과 같다.

- Python compile: passed.
- Initial new-test run: passed, 9 tests.
- Focused summary/save/API test run: passed, 30 tests.
- Full unittest discovery: passed, 105 tests.
- Save CLI help: passed.
  - bounded summary generation options and `--execute` are displayed.
- Save dry-run report command: failed before DB access because `DATABASE_URL` is not set in the current process environment.
  - No report was generated at this stage.
  - This was later completed in human-approved Supabase verification.
- `git diff --check`: passed.
- Explicit trailing-whitespace scan of changed implementation/test/verification files: no matches.
- Migration test confirms both tables, foreign keys, unique constraints, and key indexes are present in the SQL file.
- Save tests confirm:
  - default dry-run
  - no write marking without execute
  - stable input hash
  - raw-input-sensitive hash changes
  - report safety fields
  - mocked execute persistence path
- Topic API tests confirm:
  - route registration
  - pagination/filter bind parameters
  - detail article metadata
  - 404 behavior
  - raw text omission
- K8s, GitHub Actions, frontend, and Dockerfile scope checks: no changes.
- Security checks matched existing safe references, environment-variable names, test-only values, and documented command strings.
- No credential value was found in the implementation changes.

## Initial Codex Verification: Manual or Production Verification

이 섹션은 Codex 구현 직후의 초기 검증 상태를 기록한 것이다.  
이후 human-approved verification 결과는 아래 별도 섹션에 추가했다.

- Codex 구현 직후 기준으로 manual/production verification은 수행하지 않았다.
- Supabase migration SQL was not executed by Codex.
- No save command with `--execute` was run by Codex.
- No DB write, raw extraction, provider call, manual SQL, production curl, deployment, rollout, git push, or git merge was performed by Codex.

## Evidence Notes

- Save CLI는 기본적으로 read-only transaction을 연다.
- Save CLI의 write transaction은 `--execute`가 명시된 경우에만 접근 가능하다.
- 초기 execute persistence path는 fake connection으로만 테스트했다.
- `summary_input_hash`는 내부적으로 bounded summary input을 기반으로 계산한다.
- raw text는 report나 API response에 포함하지 않는다.
- Topic detail API는 기존 article/source metadata를 join하지만 `raw_articles.raw_text`는 조회하거나 반환하지 않는다.

## Approved Fix Verification

### Context

초기 Antigravity review에서 다음 문제가 발견되었다.

- migration SQL은 `unique (summary_input_hash, provider, model)`을 사용함
- save CLI의 upsert query는 `on conflict (summary_input_hash)`를 사용함
- PostgreSQL에서 `ON CONFLICT` target은 실제 unique constraint와 일치해야 하므로, 이 상태에서는 실제 `--execute` 저장 시 런타임 오류가 발생할 수 있음
- migration unit test도 기존 단일 unique constraint 기준을 기대하고 있어 테스트가 깨질 수 있음

Approved fix 적용 후 검증을 수행했다.

### Commands Run

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py app/routers/topics.py app/main.py
.venv/bin/python -m unittest tests.test_topic_summary_migration tests.test_save_topic_summaries tests.test_topics_api -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/save_topic_summaries.py --help
```

```bash
git diff --check
git diff --check -- scripts/save_topic_summaries.py tests/test_topic_summary_migration.py tests/test_save_topic_summaries.py docs/verification/feature-topic-summary-api.md docs/fixes/feature-topic-summary-api-approved-fixes.md
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
git status --short --branch
git diff --stat
git diff -- scripts/save_topic_summaries.py tests/test_topic_summary_migration.py tests/test_save_topic_summaries.py docs/fixes/feature-topic-summary-api-approved-fixes.md
rg -n "unique \(summary_input_hash, provider, model\)|on conflict \(summary_input_hash, provider, model\)" db/migrations/005_create_topics_tables.sql scripts/save_topic_summaries.py tests/test_topic_summary_migration.py tests/test_save_topic_summaries.py
```

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

### Results

- Python compile: passed.
- Focused migration/save/topics API tests: passed, 11 tests.
- Full unittest discovery: passed, 106 tests.
- Save CLI help: passed.
- `git diff --check` and targeted diff check: passed.
- `UPSERT_TOPIC_QUERY` now uses:
  - `on conflict (summary_input_hash, provider, model)`
- Migration SQL continues to use:
  - `unique (summary_input_hash, provider, model)`
- Migration unit test now expects the composite unique constraint.
- A lightweight save CLI unit test confirms the upsert conflict target uses the same composite columns.
- K8s, GitHub Actions, frontend, and Dockerfile scope checks: no changes.
- Security checks matched existing safe references, environment-variable names, test-only values, and documented command strings.
- No credential value was found in the approved-fix changes.
- The dry-run report command was not rerun during Codex approved-fix verification because real-DB dry-run verification required `DATABASE_URL` and human-applied migration.
- No Supabase SQL, manual SQL, save CLI `--execute`, real DB write, raw extraction, provider call, production curl, deployment, rollout, git push, or git merge was performed by Codex.

## Human Supabase Migration Verification

### Commands / SQL Run

- Supabase SQL Editor에서 `db/migrations/005_create_topics_tables.sql` 실행
- 테이블/컬럼/constraint/index 확인 SQL 실행

### Results

- `topics` table created or already existed.
- `topic_articles` table created or already existed.
- `topics` unique constraint 확인:
  - `unique (summary_input_hash, provider, model)`
- `topics.confidence` check constraint 확인:
  - `confidence >= 0 and confidence <= 1`
- `topic_articles.topic_id -> topics.id` FK 확인
- `topic_articles.article_id -> articles.id` FK 확인
- expected indexes 확인

### Safety

- Supabase SQL은 human operator가 수동 실행했다.
- 이 단계에서는 save CLI `--execute`를 실행하지 않았다.
- raw extraction, provider call, deployment, rollout은 수행하지 않았다.

## Human-approved Supabase Save Verification

### Commands Run

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-api-save-dry-run.md
```

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 1 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --execute \
  --report-path docs/reports/feature-topic-summary-api-save-execute.md
```

### Dry-run Results

- Save CLI dry-run succeeded after Supabase migration was applied and `DATABASE_URL` was explicitly available.
- Dry-run report result:
  - Dry-run: `true`
  - Execute requested: `false`
  - DB write performed: `false`
  - Raw extraction performed: `false`
  - Provider/model: `deterministic` / `deterministic-summary-v1`
  - Topic count: 3
  - Save candidate count: 2
  - Saved topic count: 0
  - Skipped topic count: 1
  - Linked article count: 0
- Planned save candidates:
  - `topic-0033`
  - `topic-0034`
- Skipped topic:
  - `topic-0001`: `insufficient_raw_text`

### Execute Results

- Human-approved limited execute was run with `--max-topics 1`.
- Save report result:
  - Dry-run: `false`
  - Execute requested: `true`
  - DB write performed: `true`
  - Raw extraction performed: `false`
  - Provider/model: `deterministic` / `deterministic-summary-v1`
  - Topic count: 1
  - Save candidate count: 1
  - Saved topic count: 1
  - Skipped topic count: 0
  - Linked article count: 1
- Saved topic:
  - `topic-0033`: `saved`, `topic_id=1`, `articles=1`

### Supabase Table Checks

- Supabase `topics` check:
  - `id=1`
  - `topic_candidate_id=topic-0033`
  - `provider=deterministic`
  - `model=deterministic-summary-v1`
  - `status=draft`
  - `article_count=1`
  - `source_count=1`
- Supabase `topic_articles` check:
  - `topic_id=1`
  - `article_id=889`
  - `role=representative`

### Safety

- Raw extraction was not run.
- Provider call was not run.
- K3s rollout was not run.
- Deployment was not performed.
- Git push/merge was not performed.

## Human-approved Local API Verification

### Commands Run

```bash
curl "http://127.0.0.1:8000/health"
curl "http://127.0.0.1:8000/topics?page=1&page_size=10"
curl "http://127.0.0.1:8000/topics/1"
```

### Results

- `/health` returned 정상 응답:
  - `status=ok`
  - `service=news-api`
- `/topics?page=1&page_size=10` returned one saved topic:
  - `id=1`
  - `topic_date=2026-06-11`
  - `provider=deterministic`
  - `model=deterministic-summary-v1`
  - `status=draft`
  - `article_count=1`
  - `source_count=1`
  - `has_next=false`
- `/topics/1` returned topic detail:
  - `id=1`
  - `topic_candidate_id=topic-0033`
  - `article_id=889`
  - `source=BBC World`
  - `role=representative`
  - `similarity_score=null`
- `/topics` and `/topics/1` responses did not include `raw_text`.

### Safety

- Local API verification only.
- Production API verification was not performed.
- K3s rollout was not performed.
- Deployment was not performed.
- Git push/merge was not performed.

## Final Pending Verification

남은 검증 항목은 다음과 같다.

- Production deployment, K3s rollout, and production verification.
- Production HTTP verification of `/topics` and `/topics/{topic_id}` after deployment.
- Optional provider-based save verification remains deferred.

## Approved Hash and Transaction Fix Verification

### Commands Run

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/save_topic_summaries.py tests/test_save_topic_summaries.py
.venv/bin/python -m unittest tests.test_save_topic_summaries -v
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py scripts/save_topic_summaries.py app/routers/topics.py app/main.py
.venv/bin/python -m unittest tests.test_topic_summary_migration tests.test_save_topic_summaries tests.test_topics_api tests.test_topic_summary -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/save_topic_summaries.py --help
git diff --check
git diff --check -- app/utils/topic_summary.py scripts/save_topic_summaries.py tests/test_topic_summary.py tests/test_save_topic_summaries.py tests/test_topic_summary_migration.py docs/verification/feature-topic-summary-api.md docs/fixes/feature-topic-summary-api-approved-fixes.md
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

### Results

- Initial changed-file Python compile: passed.
- Initial save-focused test run: failed, 8 tests run with 2 errors because the new fake connection did not accept parameter-less `execute()` calls.
  - The test helper signature was corrected to match SQLAlchemy connection usage.
- Approved-fix focused tests: passed, 27 tests.
- Full unittest discovery: passed, 108 tests.
- Full requested Python compile: passed.
- Save CLI help: passed; dry-run default and explicit `--execute` option remain available.
- `summary_input_hash` tests confirm:
  - equivalent article/raw_text sets produce the same hash regardless of order;
  - changing raw_text changes the hash;
  - changing article_id changes the hash.
- Transaction-boundary tests confirm:
  - generation and save plan creation complete before the write transaction opens;
  - only `execute_save_plan()` runs inside the write transaction;
  - dry-run does not open a write transaction or call `execute_save_plan()`.
- `git diff --check`: failed because `docs/reviews/feature-topic-summary-api-coderabbit.md` contains pre-existing trailing whitespace in the human-provided review artifact.
- Initial targeted `git diff --check`: failed because the human-provided approved-fixes document also contained trailing whitespace; those allowed-file formatting issues were removed while recording applied changes.
- Final targeted `git diff --check` for implementation, tests, fixes, and verification files: passed.
- Scope checks for `k8s`, `.github`, `frontend`, and `Dockerfile`: no changes.
- Security grep checks matched existing safe references, test-only values, documented commands, and `engine.begin()` false positives. No credential value was found in the approved-fix changes.

### Safety

- Supabase SQL and manual SQL were not executed.
- `scripts/save_topic_summaries.py --execute` was not run.
- No real DB write, raw extraction, provider call, production curl verification, deployment, rollout, git push, or git merge was performed.
