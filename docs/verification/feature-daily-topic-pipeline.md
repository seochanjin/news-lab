# Verification: 수동 daily topic pipeline MVP

## Verification Scope

- 수동 recent-24-hour daily topic pipeline orchestration 확인
- 기본 dry-run, provider safety gate, mocked execute path 확인
- embedding/topic candidate memory-only 처리와 save plan 확인
- selected article raw extraction 경계와 similarity score 전달 확인
- selected/reference topic report 품질 확인
- provider 기반 0.70 / 0.72 dry-run 비교 확인
- human-approved 0.70 execute 및 production `/topics` read 확인
- 기존 전체 test suite 회귀 확인
- raw extractor CronJob suspend 절차 문서화 확인

## Commands Run

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest tests.test_run_daily_topic_pipeline -v
git diff --check -- scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/RUNBOOK.md

python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest tests.test_run_daily_topic_pipeline tests.test_save_topic_summaries -v
git diff --check -- scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/RUNBOOK.md

python -m unittest discover -s tests -v
git diff --check
git status --short --branch
git diff --stat
git diff -- db k8s .github frontend Dockerfile app app/routers

git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" -- scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/RUNBOOK.md docs/verification/feature-daily-topic-pipeline.md docs/tasks/feature-daily-topic-pipeline.md

rg -n '[[:blank:]]+$' scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/verification/feature-daily-topic-pipeline.md docs/RUNBOOK.md

rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/verification/feature-daily-topic-pipeline.md docs/RUNBOOK.md

rg -n "raw_text|execute|engine.begin|extract_selected_article_ids|execute_save_plan|similarity_score|representative|supporting" scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py
```

## Results

- Required Python compile: passed.
- Initial daily pipeline focused tests: passed, 5 tests.
- Final focused daily pipeline/save tests: passed, 14 tests.
- Full unittest discovery: passed, 114 tests.
- `git diff --check`: passed.
- Pipeline tests confirm:
  - default mode is dry-run;
  - input window is fixed to recent 24 hours;
  - provider flags require their API key gates;
  - embedding provider daily limit supports up to 300 articles;
  - dry-run builds grouping, extraction target, summary, and save plans without extraction or DB write;
  - mocked execute path calls only injected extraction/load/save boundaries;
  - representative/supporting roles and similarity scores are preserved in `topic_articles` save plan entries;
  - report contains required pipeline counts, selected IDs, similarity scores, extraction counts, provider/model, and DB write state.
- Scope check: no changes to DB migrations, K8s manifests, GitHub Actions, frontend, Dockerfile, application utilities, or API routers.
- Explicit trailing-whitespace scan: no matches.
- Security grep matched safe RUNBOOK secret references, environment-variable names, documented commands, test-only values, and `engine.begin()`. No credential value was found in the changed files.
- Execution-boundary scan confirmed that actual extraction and `execute_save_plan()` are reachable only through the explicit execute path.
- `docs/RUNBOOK.md` documents the human-controlled `news-raw-extractor` CronJob suspend and verification commands.

## Approved Fix Verification

### Commands Run

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest tests.test_run_daily_topic_pipeline -v
git diff --check -- scripts/run_daily_topic_pipeline.py tests/test_run_daily_topic_pipeline.py docs/RUNBOOK.md docs/tasks/feature-daily-topic-pipeline.md

python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest tests.test_run_daily_topic_pipeline -v
python -m unittest tests.test_save_topic_summaries -v
python -m unittest discover -s tests -v
git diff --check
git diff -- db k8s .github frontend Dockerfile app app/routers
git diff --stat
git status --short --branch

python -m py_compile scripts/run_daily_topic_pipeline.py scripts/analyze_topic_groups.py
python -m unittest tests.test_run_daily_topic_pipeline tests.test_analyze_topic_groups tests.test_save_topic_summaries -v

rg -n '[[:blank:]]+$' scripts/run_daily_topic_pipeline.py scripts/analyze_topic_groups.py tests/test_run_daily_topic_pipeline.py tests/test_analyze_topic_groups.py docs/RUNBOOK.md docs/tasks/feature-daily-topic-pipeline.md docs/fixes/feature-daily-topic-pipeline-approved-fixes.md docs/verification/feature-daily-topic-pipeline.md
```

### Results

- Initial focused pipeline test: failed, 1 of 8 tests.
  - The report URL assertion exposed that the shared read-only article query did not select `a.url`.
  - Added `a.url` to the existing read-only query projections; no DB write or API response shape changed.
- Final focused pipeline tests: passed, 8 tests.
- Save topic summary tests: passed, 8 tests.
- Combined pipeline/analyze/save focused tests: passed, 25 tests.
- Full unittest discovery after the initial approved-fix implementation: passed, 116 tests.
- Final required validation rerun after URL query/test updates:
  - pipeline tests passed, 8 tests;
  - save tests passed, 8 tests;
  - full unittest discovery passed, 116 tests;
  - `git diff --check` passed.
- Python compile checks: passed.
- `git diff --check` and targeted diff check: passed.
- Scope diff for DB, K8s, GitHub Actions, frontend, Dockerfile, app, and API routers: empty.
- Explicit whitespace scan found only existing trailing whitespace in task and approved-fixes prose; no Python or RUNBOOK match was reported.
- Tests confirm:
  - selected topic ordering prioritizes article_count and source_count;
  - reference candidates do not enter extraction/summary/save paths;
  - article metadata and generated summaries appear in the report;
  - raw_text content is absent from report output.

## Manual or Production Verification

### Human-approved provider dry-run: 0.70

Command:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-070.md
```

Result summary:

- Dry-run: `true`
- Execute requested: `false`
- Window hours: 24
- Article count: 115
- Topic candidate count: 105
- Selected topic count: 3
- Reference topic count: 10
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `false`
- DB write performed: `false`

Selected topics:

```text
topic-0001: article_count=6, source_count=4
topic-0054: article_count=2, source_count=2
topic-0038: article_count=2, source_count=2
```

Observation:

- 0.70 groups the Middle East/Iran topic more broadly.
- This is acceptable for the intended homepage wording of “오늘의 주요 이슈” rather than strict duplicate-story grouping.
- Reference Candidates were reported only for human review and were not extraction, summary, or save targets.
- Some single-article reference candidates were included in the report; this is report-only noise and not a blocking issue for the current task.

### Human-approved provider dry-run: 0.72

Command:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.72 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-072.md
```

Result summary:

- Dry-run: `true`
- Execute requested: `false`
- Window hours: 24
- Article count: 115
- Topic candidate count: 107
- Selected topic count: 3
- Reference topic count: 10
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `false`
- DB write performed: `false`

Selected topics:

```text
topic-0001: article_count=4, source_count=3
topic-0056: article_count=2, source_count=2
topic-0039: article_count=2, source_count=2
```

Observation:

- 0.72 produces a narrower Middle East/Iran topic than 0.70.
- 0.72 still selects three multi-article topics.
- 0.72 is safer if the product wording emphasizes “같은 사건 기사 묶음”.
- 0.70 is acceptable if the product wording emphasizes “오늘의 주요 이슈”.

### Production read check before execute

Command:

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/<topic_id>"
```

Result:

- `/topics` returned only the previously saved deterministic topic:

```text
id=1
provider=deterministic
model=deterministic-summary-v1
article_count=1
source_count=1
```

- `/topics/<topic_id>` failed because `<topic_id>` was used literally instead of an integer topic id.

Interpretation:

- Provider dry-runs did not write to DB because `--execute` was not used.
- It is expected that production `/topics` still shows only the previously saved deterministic row.
- A real topic detail check must use an integer id, for example `/topics/1` or a new id returned after `--execute`.

### Human-approved execute: 0.70

Command:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --execute \
  --report-path docs/reports/feature-daily-topic-pipeline-execute-070.md
```

Result summary:

- Dry-run: `false`
- Execute requested: `true`
- Window hours: 24
- Article count: 114
- Topic candidate count: 104
- Selected topic count: 3
- Reference topic count: 10
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `true`
- Raw extraction success/failure: 3 / 2
- DB write performed: `true`

Selected topics:

```text
topic-0001: article_count=6, source_count=4, status=ready
topic-0054: article_count=2, source_count=2, status=ready
topic-0038: article_count=2, source_count=2, status=insufficient_raw_text
```

Observation:

- `topic-0001` and `topic-0054` produced provider-based summaries.
- `topic-0038` remained `insufficient_raw_text`.
- raw extraction was attempted only in the explicit `--execute` path.
- DB write occurred only in the explicit `--execute` path.
- No DB migration or schema change was performed.

### Production read after execute

Command:

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/2"
curl -sS "https://api.dev-scj.site/topics/3"
curl -sS "https://api.dev-scj.site/topics/2" | grep -i raw_text
curl -sS "https://api.dev-scj.site/topics/3" | grep -i raw_text
curl -sS -i "https://api.dev-scj.site/topics/999999999"
```

Result:

- `/topics` returned new `openai` / `gpt-5-nano` rows:
  - `id=2`, `provider=openai`, `model=gpt-5-nano`, `article_count=3`, `source_count=3`
  - `id=3`, `provider=openai`, `model=gpt-5-nano`, `article_count=1`, `source_count=1`
- Existing deterministic topic `id=1` remained.
- `/topics/2` returned the provider summary for the Middle East/Iran topic.
- `/topics/3` returned the provider summary for the Johannesburg mass shooting topic.
- `grep -i raw_text` against `/topics/2` and `/topics/3` returned no output.
- `/topics/999999999` returned:

```text
HTTP/2 404
{"detail":"Topic not found"}
```

Observation:

- Provider-based summaries are now saved and readable through the existing production `/topics` API.
- raw_text is not exposed through the topic detail API.
- `id=3` was originally a multi-article candidate, but only one raw-text-backed article was saved in the final topic result.
- `id=3` summary contained minor Korean quality issues such as `동нуть` and mixed English/Korean phrase `남성 and 3명의 여성`.
- These are not blockers for the pipeline MVP, but should be recorded as provider quality observations before frontend exposure.

## Pending Verification

- Human decision on whether to suspend the existing `news-raw-extractor` CronJob.
- CronJob automation is deferred to the next task.
- Frontend exposure and UI quality review are deferred to a later task.

## Evidence Notes

- Provider dry-run was executed for 0.70 and 0.72.
- Human-approved `--execute` was executed once with threshold 0.70.
- Real raw extraction was performed only during the explicit `--execute` run.
- Real DB write was performed only during the explicit `--execute` run.
- No Supabase SQL or migration was executed.
- No kubectl command, deployment, rollout, git push, or git merge was performed.
- Production curl after execute confirmed provider summaries through `/topics`.
- raw_text was not exposed by production topic detail responses.
