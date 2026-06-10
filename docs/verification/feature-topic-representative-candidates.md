# Verification: Topic 대표 기사 후보 선정 MVP

## Verification Scope

- Representative candidate scoring/ranking helper
- Read-only representative analysis CLI and provider opt-in gate
- Deterministic 0.70 and 0.72 markdown reports
- Existing and new unit tests
- Static scope and credential-pattern checks

## Commands Run

```bash
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
.venv/bin/python -m py_compile app/utils/topic_grouping.py app/utils/topic_representatives.py scripts/analyze_topic_representatives.py
.venv/bin/python -m py_compile app/utils/topic_representatives.py scripts/analyze_topic_representatives.py
.venv/bin/python -m unittest tests.test_topic_grouping tests.test_topic_representatives tests.test_analyze_topic_representatives -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_representatives.py --help
.venv/bin/python scripts/analyze_topic_representatives.py --window-hours 24 --max-articles 100 --similarity-threshold 0.70 --max-candidates-per-topic 3 --report-path docs/reports/feature-topic-representative-candidates-deterministic.md --dry-run
.venv/bin/python scripts/analyze_topic_representatives.py --window-hours 24 --max-articles 100 --similarity-threshold 0.72 --max-candidates-per-topic 3 --report-path docs/reports/feature-topic-representative-candidates-deterministic-threshold-072.md --dry-run
.venv/bin/python scripts/analyze_topic_representatives.py --window-hours 24 --max-articles 100 --similarity-threshold 0.70 --max-candidates-per-topic 3 --include-singletons --report-path docs/reports/feature-topic-representative-candidates-deterministic-with-singletons.md --dry-run
pytest
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

## Results

- Python compile checks: passed.
- Focused unit tests after approved fixes: 15 passed.
- Full unittest discovery after approved fixes: 54 passed.
  - An initial run had one failure because the new key-missing test allowed
    `load_dotenv()` to restore the local environment. The test was isolated
    with a mock and subsequent full runs passed.
- CLI help: passed.
- Default deterministic report at threshold `0.70`: passed.
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics: 3
  - representative candidates: 100
  - provider/model: deterministic / deterministic-hash-v1
  - DB write performed: false
  - singleton topics: 93
  - report detail topics: 3
  - singleton details included: false
- Conservative deterministic report at threshold `0.72`: passed.
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics: 2
  - representative candidates: 99
  - provider/model: deterministic / deterministic-hash-v1
  - DB write performed: false
  - singleton topics: 94
  - report detail topics: 2
  - singleton details included: false
- Deterministic report with `--include-singletons`: passed.
  - topic candidates: 96
  - report detail topics: 96
  - singleton details included: true
- Fix 4 report artifact preservation: passed.
  - deterministic reports were generated only at `-deterministic` paths
  - OpenAI provider report paths were not used by deterministic commands
  - no command with `--use-embedding-provider` was run
- Report content checks: passed.
  - default reports only contain multi-article topic details
  - reports display published time, created time, and recency time source
  - reports explain that candidate score is for within-topic comparison only
  - reports state that overall raw extraction priority needs a follow-up policy
- The first report attempts failed before any query or transaction because
  sandbox DNS could not resolve the database host. The same read-only commands
  were rerun after network approval and passed.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Security checks matched existing safe references, documented command text,
  provider environment-variable names, test-only values, and
  `engine.begin()` false positives. No credential value was found.
- `pytest`: not run because the executable is not installed (`command not
  found`).

## Manual or Production Verification

- Production verification was not run.
- Real OpenAI embedding provider was not called.
- `--use-embedding-provider` performs a real OpenAI embedding API call and may
  incur cost; it was intentionally not run.
- No Supabase SQL, migration, raw extraction, Kubernetes command, rollout,
  deployment, push, or merge was run.

## Pending Verification

- Human review of representative candidate suitability, source diversity, and
  candidate count remains pending.
- Real-provider comparison remains optional and requires explicit human
  approval.
- PR merge, rollout, deployment, and production verification remain manual.

## Evidence Notes

- Deterministic threshold `0.70` report:
  `docs/reports/feature-topic-representative-candidates-deterministic.md`
- Deterministic threshold `0.72` report:
  `docs/reports/feature-topic-representative-candidates-deterministic-threshold-072.md`
- Deterministic singleton-inclusive report:
  `docs/reports/feature-topic-representative-candidates-deterministic-with-singletons.md`
- OpenAI provider report paths are reserved for human-approved provider runs:
  `docs/reports/feature-topic-representative-candidates.md` and
  `docs/reports/feature-topic-representative-candidates-threshold-072.md`
- Reports include candidate rank, selected status, article/source/category
  fields, candidate score/components, selection reason, and pending human
  review status.
