# NewsLab Architecture

## Overview

NewsLab is a FastAPI-based news processing service deployed on a K3s cluster.

The project collects RSS articles, stores article metadata in PostgreSQL/Supabase, extracts raw article text, and exposes the data through FastAPI APIs.

This project is intended to be operated and evolved over time, not just built once.

## Components

### Agent workflow artifacts

NewsLab uses file-based artifacts to coordinate implementation, review, approved fixes, and verification across agents.

Main workflow directories:

- `docs/tasks/` - task specifications
- `docs/reviews/` - Antigravity, CodeRabbit, and other review outputs
- `docs/fixes/` - human-approved review fixes that were applied or deferred
- `docs/verification/` - actual commands run, results, skipped checks, and human-provided verification logs
- `docs/pr/` - PR drafts
- `docs/devlog/` - worklog drafts

PR and devlog drafts should be based on `docs/verification/` for test and verification claims.

### FastAPI API server

Serves read APIs for article data, collector status, and raw article extraction results.

Main router files:

- `app/routers/articles.py`
- `app/routers/sources.py`
- `app/routers/collector.py`
- `app/routers/raw_articles.py`
- `app/routers/health.py`
- `app/routers/version.py`
- `app/routers/extractor.py`

### PostgreSQL / Supabase database

Stores source metadata, collected article metadata, RSS collection run history, and extracted raw article text.

Current tables:

- `sources`
- `articles`
- `crawl_runs`
- `raw_articles`
- `extraction_runs`

### RSS collector

Script:

- `scripts/collect_rss.py`

Purpose:

- Reads enabled RSS sources from `sources`
- Fetches RSS feed entries
- Inserts new articles into `articles`
- Records execution results in `crawl_runs`

Execution:

- Runs manually in local development
- Runs automatically in K3s through RSS collector CronJob

### Raw article extractor

Script:

- `scripts/extract_raw_articles.py`

Purpose:

- Reads article URLs from `articles`
- Fetches article HTML
- Extracts article-like text using BeautifulSoup
- Stores extraction result in `raw_articles`

Execution:

- Currently manual
- Not yet automated as a K3s CronJob

### K3s deployment

The FastAPI application is containerized and deployed to a K3s cluster running on Oracle Cloud A1 nodes.

Kubernetes manifests are stored under:

- `k8s/`

Kubernetes apply, rollout, secret changes, and production verification are human-controlled operations.

### Tailscale remote operation path

Tailscale is used to access Oracle K3s nodes through a private network.

The kubeconfig still uses:

```text
https://127.0.0.1:6443
```

The local Kubernetes API access is done through an SSH tunnel over Tailscale.

## Data Flow

### RSS collection flow

```text
RSS feed
→ scripts/collect_rss.py
→ articles table
→ crawl_runs table
→ /articles API
→ /collector/status API
→ /collector/runs API
```

### Raw article extraction flow

```text
articles.url
→ scripts/extract_raw_articles.py
→ article HTML
→ BeautifulSoup extraction
→ raw_articles table
→ /raw-articles API
```

### Raw article extractor run history flow

```text
scripts/extract_raw_articles.py
→ extraction_runs table
→ /extractor/status API
→ /extractor/runs API
```

## Database Tables

### sources

Stores news source metadata and feed configuration.

### articles

Stores collected article metadata.

Main data:

- `source_id`
- `title`
- `url`
- `category`
- `summary`
- `published_at`
- `tags`

### crawl_runs

Stores RSS collector execution history.

Main data:

- `started_at`
- `finished_at`
- `status`
- `inserted_count`
- `skipped_count`
- `error_message`

### raw_articles

Stores extracted raw article text.

Main data:

- `article_id`
- `raw_text`
- `extraction_status`
- `error_message`
- `extracted_at`

### extraction_runs

Stores raw article extractor execution history.

Main data:

- `started_at`
- `finished_at`
- `status`
- `success_count`
- `failed_count`
- `error_message`

## APIs

### Basic APIs

- `GET /`
- `GET /health`
- `GET /version`

### Source APIs

- `GET /sources`

### Article APIs

- `GET /articles`
- `GET /articles/{article_id}`

Supported query parameters include:

- `page`
- `page_size`
- `source`
- `category`
- `keyword`

### Collector APIs

- `GET /collector/status`
- `GET /collector/runs`
- `GET /collector/runs?status=success`
- `GET /collector/runs?status=failed`

### Raw Article APIs

- `GET /raw-articles`
- `GET /raw-articles?status=success`
- `GET /raw-articles?status=failed`
- `GET /raw-articles/{article_id}`

### Extractor APIs

- `GET /extractor/status`
- `GET /extractor/runs`
- `GET /extractor/runs?status=running`
- `GET /extractor/runs?status=success`
- `GET /extractor/runs?status=failed`

## Current Manual Operations

The following operations are intentionally manual:

- Supabase SQL migration execution
- PR merge
- K3s rollout / restart
- Kubernetes manifest apply
- Secret creation or update
- Production verification
- OCI security rule changes

## Not Yet Implemented

The following are not implemented yet:

- Automated tests
- Lint / formatter setup
- Raw article extraction CronJob
- Article summarization
- Keyword extraction
- Embedding / RAG search
- Frontend UI
- Prometheus / Grafana monitoring
- Backup automation
