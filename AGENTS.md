# AGENTS.md

## Project

This repository is NewsLab, a long-running news processing and K3s operation project.

NewsLab collects RSS articles, stores article metadata, extracts raw article text, and serves the data through FastAPI APIs. The system is deployed on a K3s cluster running on Oracle Cloud A1 nodes.

## Human-controlled steps

The following actions must be performed manually by the human:

- PR merge
- GitHub main branch merge decisions
- Supabase SQL migration execution
- Kubernetes manifest apply
- K3s rollout / restart
- Production verification
- Secret creation or update
- OCI security rule changes
- DNS / domain / TLS changes

Agents must not perform these actions unless explicitly instructed.

## Safety Rules

- Do not push directly to main.
- Do not run git push unless explicitly asked.
- Do not run git merge unless explicitly asked.
- Do not run kubectl apply unless explicitly asked.
- Do not run kubectl rollout unless explicitly asked.
- Do not modify secrets, .env files, kubeconfig files, SSH keys, DockerHub tokens, or Supabase credentials.
- Do not modify Kubernetes manifests unless the task explicitly asks for it.
- Do not delete files without explaining why.
- Keep changes small and reviewable.

## Code Style

- Use FastAPI routers under app/routers.
- Register new routers in app/main.py.
- Prefer SQLAlchemy text() with raw SQL for database queries.
- Use bind parameters, not string interpolation, for user-provided values.
- When adding DB schema changes, add a SQL file under db/migrations.
- When adding dependencies, update requirements.txt.
- Avoid large refactors unless explicitly requested.

## Current Architecture

- FastAPI API server
- PostgreSQL / Supabase database
- SQLAlchemy text() queries
- RSS collector script: scripts/collect_rss.py
- Raw article extractor script: scripts/extract_raw_articles.py
- K3s deployment on Oracle Cloud A1
- RSS collector CronJob
- Tailscale-based remote operation path

## Main API Areas

- /articles
- /sources
- /collector/status
- /collector/runs
- /raw-articles
- /health
- /version

## Commands

Run API locally:

```bash
uvicorn app.main:app --reload
```

## Common checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/articles
curl http://127.0.0.1:8000/collector/status
curl http://127.0.0.1:8000/raw-articles
```

Run RSS collector manually:

```bash
python scripts/collect_rss.py
```

Run raw article extractor manually:

```bash
python scripts/extract_raw_articles.py
```

## Workflow

Before editing code:

1. Inspect relevant files.
2. Explain the current structure.
3. Propose a plan.
4. Keep the scope limited.

After editing code:

1. Summarize changed files.
2. Summarize behavior changes.
3. Provide exact test commands.
4. Mention risks and follow-up work.
5. Do not push or merge unless explicitly asked.

## Data and Migration Safety

- Do not execute migration SQL against Supabase. Only create migration files under `db/migrations`.
- Do not run data-writing scripts such as `scripts/collect_rss.py` or `scripts/extract_raw_articles.py` unless explicitly asked.
- Before running any script that writes to the database, explain what data it will create or update.
- Read-only API checks with `curl` are allowed.

## Test Status

Automated tests and lint are not fully configured yet.

If a task requires tests:

- Do not pretend tests already exist.
- Propose the test setup first.
- Prefer clear manual verification commands until automated tests are introduced.

## Documentation Outputs

When asked to prepare PR or worklog drafts:

- PR drafts should be written under `docs/pr/`.
- Worklog drafts should be written under `docs/devlog/`.
- Architecture decisions should be written under `docs/adr/`.
- Do not claim production deployment is complete unless the human provides verification logs.
- Do not claim PR merge is complete unless the human explicitly says it was merged.
