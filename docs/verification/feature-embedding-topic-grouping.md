# Verification: Embedding 기반 topic grouping MVP

## Verification Scope

- Embedding input text and provider interface
- Provider opt-in, API key, and explicit article-limit safety gates
- Cosine similarity and seed-based greedy topic grouping
- Published/created and window/all read-only analysis paths
- Static scope, compile, unit test, CLI, and security checks

## Commands Run

```bash
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py tests/test_article_embeddings.py tests/test_topic_grouping.py tests/test_analyze_topic_groups.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_groups.py --help
.venv/bin/pytest
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py tests/test_article_embeddings.py tests/test_topic_grouping.py tests/test_analyze_topic_groups.py
env -u OPENAI_EMBEDDING_API_KEY .venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 10 --use-embedding-provider --dry-run
```

The following read-only DB dry-runs used deterministic local embeddings and
did not use `--use-embedding-provider`:

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 72 --max-articles 150 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 168 --max-articles 200 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --all --max-articles 200 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --time-basis created --max-articles 100 --dry-run
```

The JSON outputs were written to temporary files and summarized with `jq`.
An additional `git diff --no-index --check` loop checked the new untracked
implementation and workflow files.

## Results

- Python compile passed.
- Final full unittest suite passed: 33 tests.
- Tests used deterministic fake/hash embeddings or a mocked HTTP response.
  No test called an external API.
- CLI help passed and documents 24h/72h/168h/all, published/created,
  `--max-articles`, similarity threshold, provider opt-in, and dry-run options.
- Provider execution without `OPENAI_EMBEDDING_API_KEY` failed before DB access
  with a clear error.
- Unit tests confirmed provider use also requires an explicit
  `--max-articles` and rejects limits above 200.
- `pytest` is pending because `.venv/bin/pytest` is not installed.
- `git diff --check` and the untracked-file whitespace check passed.
- Initial sandbox DB dry-runs failed before connection because DNS resolution
  was blocked.
- The same approved read-only dry-runs succeeded with network access:
  - Published 24h, max 100: 100 articles, 98 topic candidates, 2
    multi-article candidates.
  - Published 72h, max 150: 150 articles, 141 topic candidates, 4
    multi-article candidates.
  - Published 168h, max 200: 200 articles, 186 topic candidates, 4
    multi-article candidates.
  - Published all, max 200: 200 articles, 186 topic candidates, 4
    multi-article candidates.
  - Created 24h, max 100: 100 articles, 97 topic candidates, 3
    multi-article candidates.
- Every dry-run reported `deterministic-hash-v1`,
  `embedding_provider_enabled: false`, and `db_write_performed: false`.
- Default similarity threshold was 0.72.
- Repository security grep matched existing safe references and secret
  expressions. The new-file grep matched environment variable names, provider
  plumbing, and test placeholders only; no credential value was found.
- `git diff -- k8s` returned no changes.
- No DB migration was added or executed, and no DB rows were updated.

## Manual or Production Verification

- Not performed.
- No real OpenAI embedding provider call was made.
- No production API curl, Kubernetes command, rollout, deployment, push,
  merge, or Supabase SQL was run.

## Pending Verification

- Human review of multi-article topic candidates and threshold quality.
- Explicitly approved real embedding-provider comparison using a bounded
  article count.
- Semantic grouping quality comparison across embedding models and thresholds.
- `pytest` pending until the runner is installed.
- Production verification pending; no human-provided logs are available.

## Evidence Notes

- The analysis script executes `set transaction read only` before article
  SELECT and has no DB write path.
- Published analysis uses `coalesce(published_at, created_at)`; created analysis
  uses `created_at`.
- The local deterministic hash provider validates the pipeline and clustering
  output shape. It is not evidence of semantic embedding quality.
- Before a real provider call, the script requires
  `--use-embedding-provider`, `OPENAI_EMBEDDING_API_KEY`, and an explicit
  `--max-articles` no greater than 200, then prints an estimated article count,
  token count, and cost.
- Candidate DB structures remain documentation-only:
  `article_embeddings`, `topics`, `topic_articles`, `topic_runs`, and
  `topic_grouping_runs`.

## Approved Fix 1 Verification

Applied fix:

- Empty OpenAI embedding input now returns `[]` without an HTTP request.
- Provider response and ordered embedding counts are validated against the
  input text count.
- Missing or extra response embeddings raise a clear `RuntimeError`.

Commands actually run after the approved fix:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py
.venv/bin/python scripts/analyze_topic_groups.py --help
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py tests/test_article_embeddings.py tests/test_topic_grouping.py tests/test_analyze_topic_groups.py
```

Results:

- Final full unittest suite: 36 tests passed.
- Empty provider input returned `[]` without calling `requests.post`.
- Missing and extra response embedding tests raised `RuntimeError`.
- Existing normal response index-ordering test passed.
- Python compile: passed.
- CLI help: passed; existing options were preserved.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Security grep matched existing safe references, environment variable names,
  provider plumbing, and test placeholders; no credential value was found.
- No DB dry-run was repeated because the approved fix only changes mocked
  provider response handling.
- No real OpenAI provider call, DB write, migration, API change, K8s change,
  production command, push, or merge was performed.
