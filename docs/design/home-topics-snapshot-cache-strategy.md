# Home Topics Snapshot and Cache Strategy

## Context

The frontend home page currently needs only a small set of topic card fields,
but the general `/topics` archive API returns pagination metadata and additional
topic metadata. Production timing observed before this change placed
`/topics?page=1&page_size=10` around 0.7 to 1.0 seconds, with an average near
0.87 seconds over 10 samples.

This change adds `GET /topics/home` as a read-only MVP. It is not the final
snapshot/cache implementation.

## Current MVP

`GET /topics/home` reads directly from `topics` and returns at most 10 items:

- `id`
- `topic_date`
- `title_ko`
- `summary_ko`
- `keywords`
- `article_count`
- `source_count`

Response metadata:

- `generated_at`
- `topic_date`

The endpoint intentionally excludes:

- provider/model/status/debug fields
- pagination metadata
- total count query
- connected article details
- representative article detail
- raw article content

## Existing API Differences

`GET /topics` remains the archive API. It supports filters, page/page_size, a
total count query, and returns provider/model/status/timestamps.

`GET /topics/{id}` remains the detail API. It reads a single topic and joins
`topic_articles`, `articles`, and `sources` to return connected articles.

`GET /topics/home` is a small home payload API. It does not call the existing
archive handler as a wrapper, so it avoids the archive count query and avoids
detail joins.

## Cache and Snapshot Options

### 1. Next.js fetch revalidate

This can reduce frontend request frequency with minimal backend work. It still
depends on the backend endpoint when the revalidation window expires, and it is
not a durable source of truth.

### 2. FastAPI in-memory TTL cache

This is simple and avoids an external dependency. It is per-process, lost on
restart, and inconsistent across multiple replicas unless cache warming or
sticky behavior is added. It can be useful as a short MVP if `/topics/home`
still performs too slowly.

### 3. Redis cache

Redis can serve the latest home payload quickly across API replicas. Redis is
not the goal by itself; it is only useful if it removes user-request-time DB
lookup or payload assembly from the home path. It requires operational setup,
failure handling, and a fallback.

### 4. DB snapshot table

A table such as `home_topic_snapshots` could store generated payload JSON:

```text
home_topic_snapshots
- id
- snapshot_date
- generated_at
- payload jsonb
- source_pipeline_run_id
- status
- created_at
```

This provides history and a durable fallback. It adds schema and retention
decisions, so it is deferred.

### 5. Static JSON

The daily pipeline could publish a static JSON artifact for the frontend to
read. This can be very fast, but it introduces artifact hosting, invalidation,
and freshness concerns.

### 6. Redis plus DB snapshot fallback

The pipeline writes the latest payload to Redis and also stores a DB snapshot.
API reads Redis first and falls back to the latest valid DB snapshot. This is a
strong long-term option when the home payload becomes stable.

### 7. CronJob cache warming and frontend revalidate

After the Daily Topic Pipeline completes, it can generate the home payload,
write the cache/snapshot, and optionally trigger frontend revalidation or cache
warming. This matches the target direction: precompute after the pipeline,
instead of computing during a user request.

## Recommended Sequence

1. 46th change: add `/topics/home` MVP and measure local/API behavior.
2. 47th change: switch the frontend home screen to `/topics/home` and check
   loading behavior.
3. If `/topics/home` is still too slow, make the 47th change a cache/snapshot
   MVP instead and move the frontend switch to the 48th change.
4. 48th change: implement home payload cache/snapshot refresh after the Daily
   Topic Pipeline.
5. 49th change or later: resume embedding storage design.

## Principle

Redis, snapshots, and revalidation are implementation options. The goal is that
the home page does not ask users to wait for repeated heavy database lookup or
payload assembly when the Daily Topic Pipeline can precompute the payload once.
