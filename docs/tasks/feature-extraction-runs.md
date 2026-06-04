# Task: 본문 추출 실행 이력 저장

## Goal

Store raw article extraction execution history in the database and expose it through FastAPI APIs.

The RSS collector already stores execution history in `crawl_runs`. The raw article extractor currently stores per-article extraction results in `raw_articles`, but it does not store execution-level history.

Add execution-level tracking for `scripts/extract_raw_articles.py`.

## Scope

- Add a migration SQL file for `extraction_runs`.
- Update `scripts/extract_raw_articles.py` to create an execution run record.
- Store:
  - started_at
  - finished_at
  - status
  - success_count
  - failed_count
  - error_message
- Add a new FastAPI router for extractor status/runs.
- Register the new router in `app/main.py`.
- Add read APIs:
  - `GET /extractor/status`
  - `GET /extractor/runs`
  - `GET /extractor/runs?status=success`
  - `GET /extractor/runs?status=failed`

## Do not change

- Do not change RSS collector behavior.
- Do not modify K3s manifests.
- Do not run kubectl commands.
- Do not execute Supabase SQL.
- Do not run data-writing scripts unless explicitly approved by the human.
- Do not modify `.env`, kubeconfig, secrets, or credentials.
- Do not add automated CronJob for raw article extraction in this task.

## Expected files

Likely files:

- `db/migrations/004_create_extraction_runs.sql`
- `scripts/extract_raw_articles.py`
- `app/routers/extractor.py`
- `app/main.py`
- `docs/pr/feature-extraction-runs.md`
- `docs/devlog/feature-extraction-runs.md`

## DB changes

Create `extraction_runs` table.

Suggested schema:

```sql
create table if not exists extraction_runs (
    id bigserial primary key,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'running',
    success_count integer not null default 0,
    failed_count integer not null default 0,
    error_message text,
    created_at timestamptz not null default now()
);
```

## API changes

Add:

```text
GET /extractor/status
GET /extractor/runs
GET /extractor/runs?status=success
GET /extractor/runs?status=failed
```

## Test commands

Do not run migration SQL automatically.

After the human executes the migration manually, suggested local checks:

```bash
python scripts/extract_raw_articles.py

curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/extractor/runs
curl "http://127.0.0.1:8000/extractor/runs?status=success"
curl "http://127.0.0.1:8000/extractor/runs?status=failed"
```

## Acceptance criteria

- `extraction_runs` migration SQL exists.
- `extract_raw_articles.py` creates a run record.
- Successful extraction run stores `status=success`.
- Failed extraction run stores `status=failed` and `error_message`.
- `success_count` and `failed_count` are stored.
- `/extractor/status` returns the latest extraction run.
- `/extractor/runs` returns recent extraction runs.
- status filter works.
- No K3s manifests are changed.
- No production commands are executed by the agent.

## Notes

The implementation should follow the same pattern used by RSS collector execution history in `crawl_runs`, but keep the extractor history separate as `extraction_runs`.
