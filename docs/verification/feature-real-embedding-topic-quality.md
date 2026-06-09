# Verification: 실제 embedding 기반 topic 품질 검증

## Verification Scope

- Threshold comparison and singleton/multi-article topic metrics
- Human-reviewable markdown report generation
- Real-provider safety gates and deterministic baseline comparison path
- Published 24h read-only deterministic baseline
- Compile, unit test, CLI, static scope, and security checks

## Commands Run

```bash
.venv/bin/python -m py_compile app/utils/topic_quality.py scripts/analyze_topic_groups.py tests/test_topic_quality.py tests/test_analyze_topic_groups.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_groups.py --help
env -u OPENAI_EMBEDDING_API_KEY .venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 50 --use-embedding-provider --thresholds 0.65,0.70,0.72,0.75,0.80 --dry-run
.venv/bin/pytest
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs/reports/feature-real-embedding-topic-quality.md docs/verification/feature-real-embedding-topic-quality.md docs/devlog/feature-real-embedding-topic-quality.md
```

The following read-only deterministic baseline command was run without
`--use-embedding-provider`:

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --thresholds 0.65,0.70,0.72,0.75,0.80 --report-path docs/reports/feature-real-embedding-topic-quality.md --dry-run
```

The first sandbox attempt failed before DB connection because DNS resolution
was blocked. The same command succeeded with approved network access.

## Results

- Python compile passed.
- Final full unittest suite passed: 41 tests.
- Tests used fake/deterministic embeddings and mocked provider behavior; no
  external API was called.
- CLI help passed and includes `--thresholds` and `--report-path`.
- Provider execution without `OPENAI_EMBEDDING_API_KEY` failed before DB
  access with a clear error.
- Tests confirmed that provider-mode analysis includes a deterministic hash
  baseline comparison without making an external request.
- `pytest` is pending because `.venv/bin/pytest` is not installed.
- `git diff --check` passed.
- `git diff -- k8s` returned no changes.
- Security grep matched existing safe references, environment variable names,
  provider plumbing, test placeholders, and article text containing the word
  `tokens`; no credential value was found.
- Published 24h deterministic baseline succeeded read-only:
  - Requested maximum: 100 articles
  - Retrieved: 70 articles
  - Embedding model: `deterministic-hash-v1`
  - Provider enabled: `false`
  - DB write performed: `false`
- Threshold summary:
  - 0.65: 65 topic candidates, 5 multi-article candidates, singleton ratio
    0.9231
  - 0.70: 68 topic candidates, 2 multi-article candidates, singleton ratio
    0.9706
  - 0.72: 68 topic candidates, 2 multi-article candidates, singleton ratio
    0.9706
  - 0.75: 69 topic candidates, 1 multi-article candidate, singleton ratio
    0.9855
  - 0.80: 70 topic candidates, 0 multi-article candidates, singleton ratio
    1.0
- The markdown report was generated at
  `docs/reports/feature-real-embedding-topic-quality.md`.
- The report contains threshold summaries, multi-article topic details,
  article title/source/category/rule category/importance/published time/
  similarity, and human review status `Pending`.
- Deterministic baseline includes unrelated over-grouping candidates and is
  not semantic quality evidence.

## Manual or Production Verification

- Not performed.
- No real OpenAI embedding provider call was made because no explicit human
  approval for a billable provider run was provided.
- No production API curl, Kubernetes command, rollout, deployment, DB write,
  Supabase SQL, raw extraction, push, or merge was run.

## Pending Verification

- Explicit human approval for a bounded 50-100 article real OpenAI embedding
  provider run.
- Real-provider article count, token estimate, estimated cost, model, and
  threshold results.
- Deterministic hash versus real OpenAI embedding result comparison.
- Human review of same-event grouping, over-grouping, representative article,
  and recommended threshold.
- `pytest` pending until the runner is installed.
- Production verification pending; no human-provided logs are available.

## Evidence Notes

- The existing provider safety gates remain required:
  `--use-embedding-provider`, `OPENAI_EMBEDDING_API_KEY`, explicit
  `--max-articles`, and a maximum of 200 articles.
- Provider call estimates are printed before a real provider call.
- One embedding set is reused across all requested thresholds.
- When real provider mode is used, the same article set is also evaluated with
  deterministic hash embeddings for baseline comparison.
- The analysis script executes `set transaction read only`; no DB write path
  was added.
- Semantic grouping quality and recommended threshold remain human-review
  decisions.

## Real Provider Verification

A bounded real OpenAI embedding provider run was performed with explicit human approval.

- Model: `text-embedding-3-small`
- Article count: 68
- Time basis: `published`
- Window hours: 24
- Estimated tokens: 5896
- Estimated cost USD: 0.000118
- DB write performed: `false`
- Recommended threshold candidate: 0.70
- Conservative fallback threshold: 0.72

## Approved Fix 1 Verification

Applied fix:

- `parse_args()` now calls `load_dotenv()` before argument and provider safety
  validation.
- The provider safety gates remain unchanged.
- No `.env` file or secret value was modified or printed.

Commands actually run after the approved fix:

```bash
.venv/bin/python -m py_compile scripts/analyze_topic_groups.py tests/test_analyze_topic_groups.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_groups.py --help
git diff -- .env
git status --short -- .env
git diff --check
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

Results:

- Python compile: passed.
- Final full unittest suite: 42 tests passed.
- CLI help: passed; existing options were preserved.
- Mock-based test confirmed `parse_args()` calls `load_dotenv()` before
  validation.
- Mock-based key-missing test confirmed provider validation still fails
  clearly when no key is loaded.
- `git diff -- .env`: no changes.
- `git status --short -- .env`: no changes.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Security grep matched existing safe references, environment variable names,
  and test placeholders; no credential value was found.
- The real provider command from `Verification Required` was not rerun because
  it can make a billable external API call. The existing human-approved real
  provider verification above remains the source of truth.
- No DB write/migration, API/frontend/K8s/CronJob/raw extraction change,
  production command, push, or merge was performed.
