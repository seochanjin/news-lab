# Verification: Raw extraction target 기반 제한 실행 CLI

## Verification Scope

- 기본 dry-run 실행 계획 생성과 read-only DB 조회 확인
- `target` 상태 article만 실행 후보에 포함되는지 확인
- execute/limit guard와 opt-in extractor 연결을 unit test/mocks로 확인
- 기존 raw extractor 기본 진입점, API, DB schema, K8s, CronJob 변경 여부 확인
- 실제 raw extraction, DB write, provider 호출은 검증 범위에서 제외

## Commands Run

```bash
git status --short --branch
git diff --stat
git diff --check
```

```bash
.venv/bin/python -m py_compile app/utils/raw_extraction_targets.py scripts/analyze_raw_extraction_targets.py scripts/run_raw_extraction_targets.py
.venv/bin/python -m unittest tests.test_raw_extraction_targets tests.test_analyze_raw_extraction_targets tests.test_run_raw_extraction_targets -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_raw_extraction_targets.py --help
```

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 6
```

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 2 \
  --report-path docs/reports/feature-raw-extraction-target-runner-dry-run.md
```

```bash
git diff -- k8s
git diff -- app scripts db tests docs
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
pytest
```

## Results

- `py_compile`: passed.
- Focused unittest: passed, 21 tests.
- Full unittest: passed, 75 tests.
- CLI help: passed.
- Limit validation: passed; `--limit 6` exited with code 2 and
  `--limit must be between 1 and 5`.
- Dry-run report:
  - First sandboxed attempt failed before DB access because external DNS was unavailable.
  - Read-only rerun passed and generated
    `docs/reports/feature-raw-extraction-target-runner-dry-run.md`.
  - 100 articles were analyzed and 2 `target` candidates were planned.
  - Report records `dry_run=true`, `execute_requested=false`,
    `raw_extraction_performed=false`, and `db_write_performed=false`.
- `git diff --check`: passed.
- `git diff -- k8s`: no changes.
- Protected-scope status check: no changes to API routers, DB, K8s, frontend,
  Dockerfile, or GitHub workflow files.
- Security checks matched existing safe references, documented command strings,
  environment-variable names, test values, and `engine.begin()` false positives.
  No credential value was found in the implementation changes.
- `pytest`: not run; command is not installed (`command not found`).

## Manual or Production Verification

- None.
- No production curl, deployment, rollout, migration, or manual SQL was run.
- No actual raw extraction was run.
- No DB write to `raw_articles` or `extraction_runs` was performed.
- No OpenAI, embedding, summary, or other LLM provider was called.

## Pending Verification

- Human review and explicit approval before any limited execute-mode run.
- Execute-mode verification against real articles is pending and human-controlled.
- `pytest` remains pending because it is not installed.

## Evidence Notes

- No shell command containing `--execute` was run. The execute guard was verified
  only through parser unit tests, and the execute integration was verified only
  with a mock executor.
- The existing `scripts/extract_raw_articles.py` default `extract()` entrypoint
  and invocation semantics remain unchanged. The new selected-ID path is opt-in.
- The generated dry-run report is an execution plan, not execution approval.
