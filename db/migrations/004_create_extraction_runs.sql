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
