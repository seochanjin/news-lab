# CodeRabbit Review: 다중 RSS source 수집 및 DB 저장 MVP

## Review Summary

CodeRabbit review identified several issues in the multi-RSS source ingestion MVP.

The implementation direction is generally valid, but two runtime issues should be fixed before PR:

1. `RSS_MAX_ENTRIES_PER_SOURCE` is parsed with direct `int(...)` casting, so invalid or non-positive environment values can crash the collector or produce unexpected slicing behavior.
2. Collector inserted/skipped counters are updated inside a source transaction. If a later entry fails and the transaction rolls back, the database writes are rolled back but the Python counters may remain incremented, making `crawl_runs` and logs inaccurate.

The remaining findings are documentation quality and review hygiene issues:

- Local absolute file URI links should be replaced with repository-relative paths or plain repository paths.
- Data-writing commands such as `scripts/collect_rss.py` should not appear as default verification commands in review documentation.
- Repetitive approved-fix bullet wording should be cleaned up for readability.

## Problems Found

### 1. Local absolute file links in review documentation

Some markdown links use local absolute paths such as:

```text
docs/tasks/feature-rss-source-db-ingest.md
```

These links only work on the local machine and do not work for GitHub reviewers or other contributors. They also unnecessarily expose the local user path.

Expected direction:

- Replace local file URI links with repository-relative paths.
- Alternatively, use plain repository paths such as `docs/tasks/feature-rss-source-db-ingest.md`.

### 2. Data-writing collector command listed as default verification

The review document includes a command similar to:

```bash
.venv/bin/python scripts/collect_rss.py
```

This script writes data to the database. It should not be listed as a default verification command unless explicitly approved by the human operator.

Expected direction:

- Remove data-writing commands from default review/test command lists.
- If the collector script is mentioned, clearly label it as data-writing and human-approved only.
- Prefer read-only or non-mutating verification commands in review documentation.

### 3. Repetitive approved-fix bullet wording

Some verification or approved-fix bullets repeat the same opening phrase, reducing scanability.

Expected direction:

- Rephrase repetitive bullets.
- Group related architecture documentation changes under one bullet when possible.

### 4. `RSS_MAX_ENTRIES_PER_SOURCE` is not validated

Current code parses the environment variable directly:

```python
MAX_ENTRIES_PER_SOURCE = int(os.getenv("RSS_MAX_ENTRIES_PER_SOURCE", "30"))
```

This can fail or behave unexpectedly:

- `RSS_MAX_ENTRIES_PER_SOURCE=abc` causes a `ValueError`.
- `RSS_MAX_ENTRIES_PER_SOURCE=0` or a negative value can produce unexpected slicing behavior.

Expected direction:

- Add safe parsing for positive integer environment values.
- Invalid or non-positive values should either fall back to the default with a warning or fail in a controlled way.
- For CronJob stability, fallback with a clear warning is preferred.

### 5. Collector counters can over-report when a source transaction rolls back

Inside each source transaction, `inserted_count`, `skipped_count`, and `source_result` counters are updated before the transaction has successfully committed.

If an earlier entry increments a counter and a later entry raises an exception, the source transaction rolls back. In that case, the database changes are not committed, but the Python counters may still show inserted/skipped rows.

Expected direction:

- Use local per-source counters inside the transaction.
- Add those local counters to global counters only after the `with engine.begin()` block completes successfully.
- Keep the existing source-level transaction behavior unless there is a clear reason to change it.

## Required Fixes Before PR

- Replace local absolute file URI links with repository-relative paths or plain repository paths.
- Remove data-writing commands from default review verification command lists.
- Add validation for `RSS_MAX_ENTRIES_PER_SOURCE`.
- Fix inserted/skipped counter updates so they are reflected only after successful source transaction commit.
- Update `docs/fixes/feature-rss-source-db-ingest-approved-fixes.md` to record the approved fixes.
- Update `docs/verification/feature-rss-source-db-ingest.md` after rerunning verification.

## Optional Improvements

- Clean up repetitive approved-fix bullet wording for readability.
- Add a short note in review/verification docs that `scripts/collect_rss.py` and `scripts/extract_raw_articles.py` are data-writing scripts and require explicit human approval before execution.
- Consider adding a small unit-level test for environment variable parsing if the project already has a lightweight test structure. If not, keep this as a future improvement.

## Suggested Test Commands

Use non-mutating verification commands by default:

```bash
git diff --check
python -m compileall app scripts
```

Security scans:

```bash
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|kubeconfig|client-key-data|client-certificate-data|token:"
git grep -n -i -E "API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|ACCESS_KEY|AWS_|OCI_|SUPABASE|DATABASE_URL|DB_PASSWORD|OPENAI_API_KEY|GEMINI_API_KEY|ANTHROPIC_API_KEY"
```

Optional human-approved data-writing verification only when explicitly intended:

```bash
.venv/bin/python scripts/collect_rss.py
```

The collector command above is data-writing and should not be treated as a default safe verification command.

## Risk Notes

- The counter bug can make `crawl_runs.inserted_count` and `crawl_runs.skipped_count` inaccurate when a source transaction rolls back.
- Invalid `RSS_MAX_ENTRIES_PER_SOURCE` values can break the collector CronJob at startup.
- Running collector scripts during review can write to the configured database. This must remain a human-controlled operation.
- Local absolute paths in committed documentation reduce portability and expose local machine structure.
