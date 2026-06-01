create table if not exists crawl_runs (
    id bigserial primary key,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'running',
    inserted_count integer not null default 0,
    skipped_count integer not null default 0,
    error_message text,
    created_at timestamptz not null default now()
);
