# Verification: 다중 RSS source 수집 및 DB 저장 MVP

## Verification Scope

- Local code and collector verification for `feature/rss-source-db-ingest`.
- Local API read-only verification through `http://127.0.0.1:8000`.
- No production rollout, K8s apply/rollout, git push/merge, or Supabase SQL migration execution was performed.

## Commands Run

```bash
git status --short --branch
sed -n '1,240p' AGENTS.md
sed -n '1,260p' docs/RUNBOOK.md
sed -n '1,260p' docs/prompts/codex-implement.md
sed -n '1,320p' docs/tasks/feature-rss-source-db-ingest.md
sed -n '1,220p' docs/ARCHITECTURE.md
rg --files app scripts db docs | sort
sed -n '1,320p' scripts/collect_rss.py
sed -n '1,280p' scripts/extract_raw_articles.py
sed -n '1,220p' app/main.py
sed -n '1,260p' app/routers/sources.py
sed -n '1,320p' app/routers/articles.py
sed -n '1,320p' app/routers/collector.py
sed -n '1,220p' app/database.py
sed -n '1,220p' db/migrations/001_add_feed_url_to_sources.sql
sed -n '1,220p' db/migrations/002_create_crawl_runs.sql
sed -n '1,220p' db/migrations/003_create_raw_articles.sql
rg -n "create table.*sources|alter table sources|sources \(|insert into sources|trust_level|country|language|feed_url|category" .
git grep -n "extract(limit\|get_target_articles\|limit :limit\|extraction_status\|r.id is null" scripts/extract_raw_articles.py app db
.venv/bin/python -m py_compile scripts/collect_rss.py app/config/rss_sources.py
git status --short
git diff --stat
git diff --check
git grep -n "limit\|status\|raw\|extract" scripts/extract_raw_articles.py app db
git diff -- k8s
git diff -- app scripts db
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\.env"
pytest
python scripts/collect_rss.py
.venv/bin/python -m pip show feedparser
.venv/bin/python scripts/collect_rss.py
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/sources
curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
curl http://127.0.0.1:8000/collector/status
curl "http://127.0.0.1:8000/collector/runs?limit=5"
pkill -f "uvicorn app.main:app"
curl http://127.0.0.1:8000/health
```

## Results

- `git status --short --branch`: current branch was `feature/rss-source-db-ingest`.
- `.venv/bin/python -m py_compile scripts/collect_rss.py app/config/rss_sources.py`: exit code `0`.
- `git diff --check`: exit code `0`.
- `git diff -- k8s`: no output; K8s manifests were not modified.
- `git diff -- app scripts db`: tracked diff showed collector code changes; DB migrations were not modified. New `app/config/` files appeared in `git status --short` as untracked files.
- `git grep ...extract...`: confirmed `scripts/extract_raw_articles.py` has `extract(limit: int = 5)`, selects only articles with no `raw_articles` row, and orders by latest article metadata before `limit :limit`.
- Security grep: matched existing safe references, GitHub secret expressions, documented command strings, and Python `engine.begin()` false positives. No secret value was found in the changes.
- `pytest`: failed with `zsh:1: command not found: pytest`; automated tests are not available in this environment.
- `python scripts/collect_rss.py`: failed before collector execution because the non-venv Python did not have `feedparser`.
- `.venv/bin/python scripts/collect_rss.py` initial sandbox run: failed resolving the configured Supabase host due restricted DNS/network.
- `.venv/bin/python scripts/collect_rss.py` approved network run: exit code `0`; crawl run `11` completed successfully.

Collector run `11` source counts:

| Source | Parsed | Inserted | Skipped | Errors |
| --- | ---: | ---: | ---: | ---: |
| TechCrunch | 20 | 1 | 19 | 0 |
| Ars Technica | 20 | 20 | 0 | 0 |
| Wired | 30 | 30 | 0 | 0 |
| Hacker News | 30 | 30 | 0 | 0 |
| BBC World | 25 | 24 | 1 | 0 |
| The Guardian World | 30 | 30 | 0 | 0 |
| Al Jazeera | 25 | 25 | 0 | 0 |
| DW English | 30 | 30 | 0 | 0 |

Aggregate collector result:

- `inserted_count`: `190`
- `skipped_count`: `20`
- `error_count`: `0`
- Source result supports the 27th-round target of roughly 100-300 article metadata rows per daily run.

Local API read-only checks:

- `/health`: returned `{"status":"ok","service":"news-api",...}`.
- `/sources`: returned `count: 10`; eight registry sources were enabled and existing `The Verge` / `Reuters` rows remained disabled.
- `/articles?page=1&page_size=20`: returned `count: 20`, `total: 273`, `has_next: true`; page included multiple sources such as The Guardian World, Wired, BBC World, and Al Jazeera.
- `/collector/status`: returned latest run `id: 11`, `status: success`, `inserted_count: 190`, `skipped_count: 20`.
- `/collector/runs?limit=5`: returned latest five runs with run `11` first.
- Final `curl http://127.0.0.1:8000/health` after `pkill`: failed to connect, confirming the local verification server was stopped.

## Manual or Production Verification

- Not performed.
- No production curl verification was run.
- No Kubernetes apply, rollout, restart, Docker build/push, git push, git merge, or Supabase SQL migration execution was performed.

## Pending Verification

- Human operator may decide separately whether to build/push an image, roll out K3s, run the production CronJob, or perform production read-only verification.
- Automated tests remain pending because `pytest` is not installed/configured in this local environment.

## Evidence Notes

- The collector writes source rows and article metadata to the configured Supabase database when run locally.
- Source metadata fields `country`, `language`, and `trust_level` are defined in the code registry. They are only written to `sources` if matching DB columns already exist; no schema migration was added or executed.
- Raw extractor risk note: current extractor default limit is `5`, and `get_target_articles()` only selects articles where no `raw_articles` row exists. Source growth increases backlog potential but does not increase one extractor run beyond five target articles unless the limit or invocation changes.

## Approved Fix Verification: Architecture CronJob Status

Commands run for approved fixes:

```bash
git status --short --branch
sed -n '1,240p' AGENTS.md
sed -n '1,260p' docs/prompts/codex-implement.md
sed -n '1,360p' docs/fixes/feature-rss-source-db-ingest-approved-fixes.md
sed -n '1,320p' docs/tasks/feature-rss-source-db-ingest.md
sed -n '1,360p' docs/verification/feature-rss-source-db-ingest.md
grep -n "raw extractor\|raw article\|CronJob\|news-raw-extractor\|news-rss-collector" docs/ARCHITECTURE.md
sed -n '1,340p' docs/ARCHITECTURE.md
git status --short
git diff --stat
git diff --check
git diff -- docs/ARCHITECTURE.md
git diff -- k8s
git diff -- app scripts db
```

Approved fix result:

- `docs/ARCHITECTURE.md` was updated to document `news-rss-collector` as the K3s RSS collector CronJob, scheduled daily at 03:00 Asia/Seoul with command `python scripts/collect_rss.py`.
- `docs/ARCHITECTURE.md` was updated to document `news-raw-extractor` as the K3s raw extractor CronJob, scheduled daily at 03:30 Asia/Seoul with command `python scripts/extract_raw_articles.py`.
- `Raw article extraction CronJob` was removed from the `Not Yet Implemented` list.
- `docs/fixes/feature-rss-source-db-ingest-approved-fixes.md` was updated to record the applied approved fix.

Validation results:

- `git diff --check`: exit code `0`.
- `git diff -- docs/ARCHITECTURE.md`: showed only the approved CronJob status/schedule/command documentation changes.
- `git diff -- k8s`: no output.
- `git diff -- app scripts db`: still showed the prior collector implementation diff from the main task; no additional app, script, or DB changes were made for this approved documentation fix.
- `grep -n ... docs/ARCHITECTURE.md`: confirmed `news-rss-collector`, `news-raw-extractor`, and both CronJob commands are present.

No production-impacting commands were run for the approved fix.
