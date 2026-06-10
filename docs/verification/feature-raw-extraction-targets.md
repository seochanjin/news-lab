# Verification: Topic 대표 후보 기반 raw extraction 대상 선정

## Verification Scope

- Raw extraction target policy helper and report rendering
- Read-only CLI, raw extraction state query, and provider safety gate
- Deterministic max-targets-per-topic 1 and 2 reports
- Focused/full unit tests, static scope, and credential-pattern checks

## Commands Run

```bash
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests docs
.venv/bin/python -m py_compile app/utils/topic_grouping.py app/utils/topic_representatives.py app/utils/raw_extraction_targets.py scripts/analyze_raw_extraction_targets.py
.venv/bin/python -m unittest tests.test_topic_grouping tests.test_topic_representatives tests.test_raw_extraction_targets tests.test_analyze_raw_extraction_targets -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_raw_extraction_targets.py --help
.venv/bin/python scripts/analyze_raw_extraction_targets.py --window-hours 24 --max-articles 100 --similarity-threshold 0.72 --max-candidates-per-topic 3 --max-targets-per-topic 1 --report-path docs/reports/feature-raw-extraction-targets.md --dry-run
.venv/bin/python scripts/analyze_raw_extraction_targets.py --window-hours 24 --max-articles 100 --similarity-threshold 0.72 --max-candidates-per-topic 3 --max-targets-per-topic 2 --report-path docs/reports/feature-raw-extraction-targets-max2.md --dry-run
pytest
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
rg -n "Target status counts|\\| (target|backup|skipped|already_extracted|failed) \\|" docs/reports/feature-raw-extraction-targets*.md
```

## Results

- Python compile: passed.
- Focused unittest: `21 passed`.
- Full unittest discovery: `65 passed`.
- CLI help: passed.
- Default deterministic report (`max_targets_per_topic=1`): passed.
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article/report detail topics: 2
  - extraction targets: 2
  - each multi-article topic selected at most one target
  - DB write performed: false
  - raw extraction performed: false
- Comparison deterministic report (`max_targets_per_topic=2`): passed.
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article/report detail topics: 2
  - extraction targets: 4
  - each multi-article topic selected at most two targets
  - DB write performed: false
  - raw extraction performed: false
- Both reports used `deterministic-hash-v1`; no OpenAI provider call was made.
- The first two report attempts failed before DB access because sandbox DNS could
  not resolve the database host. The identical read-only commands were rerun
  with network approval and passed.
- Report content check: passed. Target, backup, skipped, rank, candidate score,
  raw status, and decision reason are present.
- Already-extracted and failed status branches passed unit tests. The current
  report sample did not contain those states among multi-article topic
  candidates.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Security checks matched existing safe references, documented command text,
  environment-variable names, test-only values, and `engine.begin()` false
  positives. No credential value was found.
- `pytest`: not run because the executable is not installed (`command not
  found`).

## Manual or Production Verification

- Production verification was not run.
- Actual raw extraction was not run.
- Real OpenAI embedding provider was not called.
- No Supabase SQL, migration, Kubernetes command, rollout, deployment, push, or
  merge was run.

## Pending Verification

- Human review of target suitability, topic ordering, and whether one or two
  targets per topic is preferable remains pending.
- Real-provider comparison is optional and requires explicit human approval.
- PR merge, rollout, deployment, actual extraction, summary generation, and
  production verification remain manual/future work.

## Evidence Notes

- Default report: `docs/reports/feature-raw-extraction-targets.md`
- Max-two comparison report:
  `docs/reports/feature-raw-extraction-targets-max2.md`
- The CLI queries `articles`, `sources`, and selected `raw_articles` state
  inside a read-only transaction and prints JSON output.

## Approved Fix Verification

### Commands Run

```bash
git status --short --branch
git diff --stat
git diff --check
.venv/bin/python -m py_compile app/utils/topic_grouping.py app/utils/topic_representatives.py app/utils/raw_extraction_targets.py scripts/analyze_raw_extraction_targets.py
.venv/bin/python -m unittest tests.test_raw_extraction_targets tests.test_analyze_raw_extraction_targets -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_raw_extraction_targets.py --help
.venv/bin/python scripts/analyze_raw_extraction_targets.py --window-hours 24 --max-articles 100 --similarity-threshold 0.72 --max-candidates-per-topic 3 --max-targets-per-topic 1 --report-path docs/reports/feature-raw-extraction-targets.md --dry-run
.venv/bin/python scripts/analyze_raw_extraction_targets.py --window-hours 24 --max-articles 100 --similarity-threshold 0.72 --max-candidates-per-topic 3 --max-targets-per-topic 2 --report-path docs/reports/feature-raw-extraction-targets-max2.md --dry-run
rg -n "검증용|승인 목록|comparison|비교용|human-approved|deterministic-hash-v1" docs/reports/feature-raw-extraction-targets*.md
git diff -- k8s
git diff -- app scripts db tests docs
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
pytest
git status --short -- .env k8s db app/routers frontend scripts/extract_raw_articles.py app/utils/topic_grouping.py app/utils/topic_representatives.py scripts/analyze_topic_representatives.py
```

### Results

- Python compile after approved fixes: passed.
- Approved-fix focused unittest:
  - Initial run: `1 failed, 12 passed`. Existing status test still expected the
    pre-fix input order.
  - After updating that expectation to the approved rank-first order:
    `13 passed`.
- Full unittest after approved fixes: `67 passed`.
- Shuffled rank test passed: rank 1 became `target`, rank 2 became `backup`,
  and the rankless article became `skipped`.
- CLI help: passed.
- Default deterministic report regeneration: passed.
  - extraction targets: 2
  - deterministic verification/non-approval/human-approved provider warning:
    present
  - DB write performed: false
  - raw extraction performed: false
- Max2 deterministic report regeneration: passed.
  - extraction targets: 4
  - deterministic warning and comparison/non-approval warning: present
  - DB write performed: false
  - raw extraction performed: false
- Warning grep: passed.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Explicit protected-scope status check: no changes to `.env`, K8s, DB,
  routers, frontend, raw extractor, grouping/scoring, or representative CLI.
- Security checks matched existing safe references, command text,
  environment-variable names, test-only values, and existing false positives.
  No credential value was found.
- `pytest`: not run because the executable is not installed (`command not
  found`).

### Safety Notes

- Real OpenAI embedding provider was not called.
- Actual raw extraction and DB write were not run.
- Production verification, Supabase SQL, Kubernetes commands, rollout,
  deployment, push, and merge were not run.
