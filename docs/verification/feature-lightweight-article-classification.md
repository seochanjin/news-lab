# Verification: Lightweight article classification MVP

## Verification Scope

- Deterministic category, language, and importance helper behavior
- Read-only classification analysis aggregation
- 24h/72h/168h/all published-time analysis and 24h created-time analysis
- Python compile, CLI, static scope, and security checks

## Commands Run

```bash
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py tests/test_article_classification.py tests/test_analyze_article_classification.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_article_classification.py --help
.venv/bin/pytest
git diff --check
git status --short --branch
git diff --stat
git diff -- k8s
git diff -- app scripts db tests
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app/utils/article_classification.py scripts/analyze_article_classification.py tests/test_article_classification.py tests/test_analyze_article_classification.py docs/verification/feature-lightweight-article-classification.md docs/pr/feature-lightweight-article-classification.md docs/devlog/feature-lightweight-article-classification.md
```

An additional `git diff --no-index --check` loop was run for the new untracked
implementation and workflow files. Its first attempt failed because `status`
is a read-only zsh variable; the corrected loop used `rc` and passed.

The following read-only DB commands were run with `--max-examples 0` so article
titles and candidate details were not printed:

```bash
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 168 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --all --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --time-basis created --max-examples 0
```

## Results

- Initial compile and unit-test run failed because a keyword regex f-string
  contained a backslash expression. The regex fragment was moved outside the
  f-string.
- After the fix, Python compile passed and the full unit test suite passed:
  19 tests.
- CLI help passed and documented 24h/72h/168h/all, published/created, and
  example-limit options.
- `pytest` is pending because `.venv/bin/pytest` is not installed.
- `git diff --check` passed.
- The corrected untracked-file whitespace check passed.
- Initial sandbox DB attempts failed before connection because DNS resolution
  was blocked.
- The first approved-network query failed read-only because the current
  `sources` table does not have a `language` column. The script was changed to
  use source name plus the repository `RSS_SOURCES` registry for language
  fallback, without a schema change.
- Final approved-network read-only analysis succeeded:
  - Published 24h: 169 articles, 51 source/rule category mismatches, importance
    maximum 30 and average 5.25.
  - Published 72h: 253 articles, 70 mismatches, importance maximum 30 and
    average 4.69.
  - Published 168h: 347 articles, 102 mismatches, importance maximum 30 and
    average 4.07.
  - Published all: 376 articles, 112 mismatches, importance maximum 30 and
    average 4.0.
  - Created 24h: 293 articles, 76 mismatches, importance maximum 30 and
    average 4.81.
- All-time source categories: `tech` 208, `world` 165, `ai` 1, `unknown` 2.
- All-time rule categories: `unknown` 224, `ai` 42, `politics` 37, `world` 27,
  `business` 15, `tech` 15, `sports` 7, `security` 6, `climate` 3.
- All-time languages: `en` 373 and `ko` 3; all 376 were script-detected.
- `git diff -- k8s` returned no changes.
- Repository security grep matched existing safe references and documentation.
  The new implementation/workflow file search returned no matches, and no
  credential value was found.
- No DB migration was added or executed, and no DB rows were updated.

## Manual or Production Verification

- Not performed.
- No production API curl, Kubernetes command, rollout, deployment, merge, or
  push was run.

## Pending Verification

- Human review of source/rule category mismatch examples and top importance
  candidates before using signals for topic grouping or ranking.
- Re-run after more multi-source data accumulates and tune keyword weights.
- `pytest` is pending until the runner is installed.
- API checks were not run because this task does not change API behavior.

## Evidence Notes

- The analysis script executes `set transaction read only` before SELECT.
- Source category remains the base category; rule category is a separate
  candidate signal and does not overwrite article data.
- Importance score is explicitly marked as not being a final ranking.
- New implementation files are untracked, so `git status --short` is the
  source of truth for their current file list.
- No human-provided production verification logs were available.

## Approved Fix 1 Verification

Applied fix:

- Replaced `get_articles()` SQL fragment interpolation with four fixed
  SQLAlchemy `text()` query templates.
- Kept `window_hours` as a bind parameter.
- Added `ValueError` handling for unsupported `time_basis`.
- Added focused query-selection and invalid-input tests.

Commands actually run after the approved fix:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py tests/test_article_classification.py
.venv/bin/python scripts/analyze_article_classification.py --help
git status --short
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
rg -n "text\\(f|timestamp_expression|where_sql|ARTICLE_QUERIES|window_hours" scripts/analyze_article_classification.py tests/test_analyze_article_classification.py
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 168 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --all --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --time-basis created --max-examples 0
```

Results:

- Full unit test suite: 21 tests passed.
- Python compile: passed.
- CLI help: passed; existing options were preserved.
- `git diff --check`: passed.
- `get_articles()` no longer contains `text(f"""...""")`,
  `timestamp_expression`, or `where_sql`.
- Fixed query selection and bound `window_hours` behavior passed focused tests.
- Unsupported `time_basis` raises `ValueError`.
- Security grep matched existing safe references/documentation; no credential
  value was found.
- `git diff -- k8s` returned no changes.
- All five approved-fix DB dry-runs succeeded read-only.
- All-time result remained 376 articles, 112 mismatches, rule category counts
  unchanged, and languages `en` 373 / `ko` 3.
- The all-time importance average changed from 4.0 to 3.99 because recency is
  based on execution time; this is not a classification rule change.
- No DB write, migration, API change, K8s change, production command, push, or
  merge was performed.
