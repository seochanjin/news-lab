# Antigravity Review: 다중 RSS source 수집 및 DB 저장 MVP

## Review Summary

This review evaluates the implementation of the multi-RSS source ingestion MVP on branch `feature/rss-source-db-ingest`. The goal of this task is to expand the RSS collector from a single TechCrunch feed to a multi-source structure with 8 enabled feeds, syncing registry configurations to the Supabase database dynamically.

The implementation is highly defensive, containing separate transaction scopes for each RSS source and checking database table columns dynamically before syncing registry properties to avoid schema mismatch exceptions. Verification has been performed locally and indicates successful ingestion of 190 articles across the 8 sources, with all checked API endpoints returning expected outputs.

Overall, the branch meets all task requirements with high code quality and operational safety.

## Requirement Coverage

The code changes satisfy all scope items specified in `docs/tasks/feature-rss-source-db-ingest.md`:
- **RSS source registry**: Defined in `app/config/rss_sources.py` with 8 default enabled sources.
- **Source metadata**: Fields `name`, `feed_url`, `url`, `category`, `country`, `language`, `enabled`, and `trust_level` are fully specified.
- **Looping over enabled sources**: `scripts/collect_rss.py` correctly queries and processes each enabled source.
- **Fail-safe isolation**: Exceptions during a single feed's processing are caught, preventing total crawl failure.
- **Source-level telemetry**: Collects and logs `parsed_count`, `inserted_count`, `skipped_count`, and `error_count` per source, and stores crawl outcomes in `crawl_runs`.
- **Legacy compatibility**: Maintains TechCrunch ingestion and duplicate prevention (`on conflict (url) do nothing`).
- **Read-only validation**: Verification records query results for `/health`, `/sources`, `/articles`, `/collector/status`, and `/collector/runs`.

## Code Quality / Maintainability

- **Dynamic Schema Synchronization**: The `sync_source_registry` function queries `information_schema.columns` to check which columns exist on the `sources` table before synchronizing the registry data. This is extremely robust and prevents SQL syntax errors if fields like `trust_level` or `country` are not yet defined in the Supabase schema.
- **Transaction Granularity**: Each source is collected inside its own transaction (`with engine.begin() as connection:`), isolating failures. However, inside each source, all parsed entries are inserted in the same transaction. If a single entry insert fails (throws an exception due to a database constraint error or connection error), all successful insertions for that source's feed will be rolled back.
- **Code Cleanliness**: Imports and paths are set up cleanly, appending `sys.path` dynamically. No duplicate database engine initialization code is introduced.

## Security Review

- **No Secret Exposure**: Grep checks confirmed that no `.env` credentials, API tokens, K3s tokens, or private keys are hardcoded in the codebase or commits.
- **Safe SQL Formulation**: Queries utilize bind parameters via SQLAlchemy `text()` bindings (e.g. `:name`, `:id`, `:limit`). Dynamic column concatenation in `sync_source_registry` is safe because it only references column names validated against the database system catalogs (`information_schema.columns`).

## Operational Risk

- **Extractor Backlog Accumulation**: The default limit for `scripts/extract_raw_articles.py` is hardcoded at `5`. Since multi-source collection increases the daily collected article volume from ~20 to ~190, the extractor will run behind by ~185 articles per daily run. While this prevents CPU/network overload on production nodes, it creates a growing queue backlog of unprocessed raw articles.
- **Schema Safety**: No migrations are created or applied, ensuring zero risk to the production Supabase database.

## Scope Control

- **File modifications**: Only the expected file `scripts/collect_rss.py` is modified and the new module `app/config/rss_sources.py` is added.
- **No out-of-scope logic**: No embedding generation, summary models, keyword indexing, frontend updates, or router paths were added, in strict alignment with the "Do not change" list.

## Verification Review

- The local verification executed and logged in `docs/verification/feature-rss-source-db-ingest.md` shows:
  - Compilation checks succeeded.
  - Collector sandbox execution completed successfully (crawl run `11` inserted 190 items and skipped 20).
  - API validation calls returned correct structures.
- **Limitation**: Automated tests (using `pytest`) could not be run because `pytest` is not installed or configured in the local workspace.

## Documentation Review

- **Inconsistency**: `docs/ARCHITECTURE.md` listed the "Raw article extraction CronJob" under *Not Yet Implemented*, but the task specification `docs/tasks/feature-rss-source-db-ingest.md` explicitly lists `CronJob: news-raw-extractor` as an active K3s workload.

## Problems Found

- **Documentation Conflict**: Inconsistency between `docs/ARCHITECTURE.md` and the task file regarding the raw extractor CronJob deployment status.
- **Transaction Granularity Risk**: A database error on a single entry rolls back all parsed articles from that source's feed.

## Required Fixes Before PR

*None.* No blocking functional issues or security vulnerabilities were identified.

## Optional Improvements

1. **Transaction Isolation per Entry**: Wrap individual article insertions in sub-transactions or handle exceptions inside the feed loop so a single corrupted article does not abort the entire source collection.
2. **Resolve Documentation Conflict**: Update `docs/ARCHITECTURE.md` to reflect the correct deployment status of the `news-raw-extractor` CronJob.

## Suggested Test Commands

1. **Launch API server**:
   ```bash
   .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Verify API outputs**:
   ```bash
   curl http://127.0.0.1:8000/health
   curl http://127.0.0.1:8000/sources
   curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
   curl http://127.0.0.1:8000/collector/status
   curl "http://127.0.0.1:8000/collector/runs?limit=5"
   ```

Human-approved data-writing verification only when explicitly intended:

```bash
.venv/bin/python scripts/collect_rss.py
```

## Verdict

**PASS** (Minor documentation alignment and transaction granularity improvements recommended but optional for MVP).
