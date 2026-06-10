# Verification: Raw text 기반 topic summary report MVP

## Verification Scope

- deterministic/mock summary 기본 동작과 raw-text-only input 구성 확인
- `insufficient_raw_text` 처리와 report safety fields 확인
- summary provider opt-in guard, model 선택, response parsing을 unit test/mock으로 확인
- DB write, raw extraction, provider 호출 없이 변경 범위 확인

## Commands Run

```bash
git status --short --branch
git diff --stat
git diff --check
```

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py
.venv/bin/python -m unittest tests.test_topic_summary tests.test_generate_topic_summary_report -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/generate_topic_summary_report.py --help
```

```bash
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

```bash
git diff -- k8s
git diff -- app scripts db tests docs
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github .env
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
pytest
```

## Results

- Python compile: passed.
- Focused unittest: passed, 12 tests.
- Full unittest: passed, 87 tests.
- CLI help: passed.
- `git diff --check`: passed.
- Deterministic actual-data report: failed before DB access because
  `DATABASE_URL` was not set in the current process environment.
- The new CLI did not load or read `.env` to obtain `DATABASE_URL`.
- `git diff -- k8s`: no changes.
- Protected-scope status check: no changes to API routers, DB, K8s, frontend,
  Dockerfile, GitHub workflows, or `.env`.
- Security checks matched existing safe references, environment variable names,
  test-only values, documented command strings, and existing false positives.
  No credential value was found in the implementation changes.
- `pytest`: not run; command is not installed (`command not found`).

## Manual or Production Verification

- None.
- No provider test command was run.
- No OpenAI/LLM provider call was made.
- No raw extraction or raw extraction execute command was run.
- No DB write, migration, manual SQL, production curl, deployment, or rollout
  was run.

## Pending Verification

- Generate `docs/reports/feature-topic-summary-report-deterministic.md` in an
  approved environment where `DATABASE_URL` is explicitly available.
- Human-approved `gpt-5-nano` provider report.
- Optional human-approved `gpt-5-mini` comparison report.
- `pytest` remains pending because it is not installed.

## Evidence Notes

- Provider behavior was verified only with unit tests and mocked HTTP responses.
- The default path uses deterministic embeddings and deterministic summaries.
- Raw text is used as summary input, but raw text content is omitted from final
  JSON/markdown output; used article metadata and raw text length are retained.
- Missing raw text produces `insufficient_raw_text`; extraction is never invoked.

## Approved Fix 1 Verification

### Commands Run

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py
.venv/bin/python -m unittest tests.test_topic_summary tests.test_generate_topic_summary_report -v
.venv/bin/python -m unittest discover -s tests -v
```

```bash
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

```bash
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github .env
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

### Results

- Python compile: passed.
- Focused unittest: passed, 15 tests.
- Full unittest: passed, 90 tests.
- New tests confirm:
  - a ready topic outside the initial `max_topics` window is prioritized;
  - ready topics sort by used article count and source count before limit;
  - an insufficient topic remains when it fits within `max_topics`;
  - public summary JSON and markdown do not expose the raw text test marker.
- `git diff --check`: passed.
- K8s/protected scope: no changes.
- Security checks: existing safe references and test-only values only; no
  credential value found.
- Deterministic report regeneration: failed before DB access because
  `DATABASE_URL` is not set in the current process environment.
- The existing deterministic report was not overwritten and still records
  `summarized_topic_count=0`; therefore `summarized_topic_count >= 1` is not yet
  verified against actual data.
- No raw extraction, raw extraction execute command, DB write, provider call,
  migration, manual SQL, production verification, deployment, or rollout was
  performed.

### Human-approved actual-data rerun after Approved Fix 1

```bash
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

Result:

- Deterministic report regeneration: passed after `DATABASE_URL` was made available in the current shell environment.
- Report generated: `docs/reports/feature-topic-summary-report-deterministic.md`.
- Topic count: 3.
- Summarized topic count: 3.
- Insufficient raw text topic count: 0.
- Provider/model: `deterministic` / `deterministic-summary-v1`.
- Used articles:
  - article_id=574, source=TechCrunch, raw_text_length=1904
  - article_id=684, source=BBC World, raw_text_length=3553
  - article_id=675, source=BBC World, raw_text_length=5203
- `db_write_performed=false`.
- `raw_extraction_performed=false`.
- Provider call performed: false.
- Raw extraction was not run during this rerun.
- Raw text content was not exposed in the markdown report; only metadata and raw text length were shown.

## Human-approved Provider Verification

### gpt-5-nano provider test

Command:

```bash
OPENAI_SUMMARY_MODEL=gpt-5-nano \
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 1 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --use-summary-provider \
  --report-path docs/reports/feature-topic-summary-report-provider-nano.md
```

Result:

- Provider report generation: passed.
- Provider/model: `openai` / `gpt-5-nano`.
- Topic count: 1.
- Summarized topic count: 1.
- Insufficient raw text topic count: 0.
- Used article:
  - article_id=574
  - source=TechCrunch
  - raw_text_length=1904
- `db_write_performed=false`.
- `raw_extraction_performed=false`.
- Provider output was written to markdown report only.
- No topic summary DB write was performed.
- No API, K8s, CronJob, deployment, or rollout was performed.

### gpt-5-mini provider comparison test

Command:

```bash
OPENAI_SUMMARY_MODEL=gpt-5-mini \
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 1 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --use-summary-provider \
  --report-path docs/reports/feature-topic-summary-report-provider-mini.md
```

Result:

- Provider comparison report generation: passed.
- Provider/model: `openai` / `gpt-5-mini`.
- Topic count: 1.
- Summarized topic count: 1.
- Insufficient raw text topic count: 0.
- Used article:
  - article_id=574
  - source=TechCrunch
  - raw_text_length=1904
- `db_write_performed=false`.
- `raw_extraction_performed=false`.
- Provider output was written to markdown report only.
- No topic summary DB write was performed.
- No API, K8s, CronJob, deployment, or rollout was performed.

### Provider comparison notes

- `gpt-5-nano` produced a usable low-cost MVP summary.
- `gpt-5-mini` produced a more natural and specific Korean summary.
- Initial operating recommendation:
  - default model candidate: `gpt-5-nano`
  - comparison model: `gpt-5-mini`
  - automatic fallback/retry policy: not implemented in this task
  - before DB/API promotion, additional factuality and quality checks are required
- Factuality check is still required before promoting provider output to user-facing DB/API output.

## Approved Fix 2 Verification

### Commands Run

```bash
.venv/bin/python -m py_compile app/utils/topic_summary.py scripts/generate_topic_summary_report.py
.venv/bin/python -m unittest tests.test_topic_summary tests.test_generate_topic_summary_report -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/generate_topic_summary_report.py --window-hours 24 --max-topics 3 --max-articles-per-topic 2 --max-raw-chars-per-article 3000 --report-path docs/reports/feature-topic-summary-report-deterministic.md
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github .env
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" -- app scripts tests docs ':!docs/reviews/feature-topic-summary-report-antigravity.md' ':!docs/reviews/feature-topic-summary-report-coderabbit.md'
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs -g '!docs/reviews/feature-topic-summary-report-antigravity.md' -g '!docs/reviews/feature-topic-summary-report-coderabbit.md'
```

### Results

- Python compile: passed.
- Focused unittest: passed, 20 tests.
- Full unittest: passed, 95 tests.
- New tests confirm invalid provider payloads raise controlled `ValueError` for
  non-object JSON, invalid text/list types, non-finite confidence, and
  confidence outside `0~1`.
- Deterministic report regeneration: failed before DB access because
  `DATABASE_URL` is not set in the current process environment. The existing
  human-approved actual-data report was not overwritten.
- `git diff --check`: failed only on pre-existing, unrelated trailing
  whitespace in `docs/reviews/feature-topic-summary-report-coderabbit.md`.
  Review files were intentionally not modified.
- K8s/protected scope: no changes.
- Security checks matched existing safe references, environment-variable names,
  test-only values, and documented command strings; no credential value was
  found in the approved-fix changes.
- No raw extraction, raw extraction execute command, DB write, provider call,
  migration, manual SQL, production verification, deployment, or rollout was
  performed.
