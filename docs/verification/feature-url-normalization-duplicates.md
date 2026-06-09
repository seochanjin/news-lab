# Verification: URL 정규화와 중복 후보 분석 MVP

## Verification Scope

- URL/title normalization helper behavior
- duplicate analysis grouping behavior
- Python syntax/compile checks
- current DB read-only analysis for published and collection time bases
- forbidden-scope change checks

## Commands Run

```bash
.venv/bin/python -m unittest tests/test_url_normalization.py -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/url_normalization.py scripts/analyze_article_duplicates.py tests/test_url_normalization.py tests/test_analyze_article_duplicates.py
.venv/bin/python scripts/analyze_article_duplicates.py --help
.venv/bin/pytest
git diff --check
git diff --stat
git status --short
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

The following read-only commands were first attempted in the sandbox and
failed before a DB connection was established because DNS resolution was
blocked:

```bash
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 24 --max-groups 0
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 72 --max-groups 0
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 168 --max-groups 0
.venv/bin/python scripts/analyze_article_duplicates.py --all --max-groups 0
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 24 --time-basis created --max-groups 0
```

The same five commands were then run successfully with approved network
access. `--max-groups 0` prevented article titles and URLs from being printed.

## Results

- Unit tests: 9 passed.
- Python compile: passed.
- CLI help: passed; documented 24h/72h/168h, all, published/created, and output
  group-limit options.
- `pytest`: pending because `.venv/bin/pytest` is not installed.
- `git diff --check`: passed.
- Published-time analysis (`coalesce(published_at, created_at)`):
  - 24h: 180 articles, 0 normalized URL candidate groups, 0 title hash groups.
  - 72h: 254 articles, 0 normalized URL candidate groups, 0 title hash groups.
  - 168h: 347 articles, 0 normalized URL candidate groups, 1 title hash group
    containing 2 articles.
  - all: 376 articles, 0 normalized URL candidate groups, 2 title hash groups
    containing 4 articles.
- Collection-time analysis (`created_at`):
  - 24h: 293 articles, 0 normalized URL candidate groups, 0 title hash groups.
- Every successful DB analysis reported 0 invalid/missing URLs and 0
  invalid/missing titles.
- `git diff -- k8s` returned no changes.
- Security grep matched existing safe GitHub secret expressions, documentation,
  command text, and secret object names. No credential value was found.
- No DB migration was added or executed.

## Manual or Production Verification

- Not performed.
- No production API curl, Kubernetes command, rollout, deployment, merge, or
  push was run.

## Pending Verification

- Human review of the two all-time title-hash candidate groups before defining
  a duplicate-linking policy.
- Re-run the dry-run after additional multi-source collection data accumulates.
- API checks were not run because this task does not change API behavior.

## Evidence Notes

- The analysis script executes `set transaction read only` before its SELECT.
- Candidate counts are dry-run evidence only; no article rows were updated.
- `git diff` does not display the new untracked implementation files until
  they are staged, so `git status --short` is the source of truth for the
  current file list.
