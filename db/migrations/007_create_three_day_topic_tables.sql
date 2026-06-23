create table if not exists three_day_topic_runs (
    id bigserial primary key,
    reference_date date not null,
    window_start timestamptz not null,
    window_end timestamptz not null,
    status text not null default 'running'
        check (status in ('running', 'success', 'partial_success', 'failed')),
    candidate_count integer not null default 0 check (candidate_count >= 0),
    embedding_count integer not null default 0 check (embedding_count >= 0),
    missing_embedding_count integer not null default 0
        check (missing_embedding_count >= 0),
    cluster_count integer not null default 0 check (cluster_count >= 0),
    selected_topic_count integer not null default 0
        check (selected_topic_count >= 0),
    saved_topic_count integer not null default 0 check (saved_topic_count >= 0),
    failed_topic_count integer not null default 0 check (failed_topic_count >= 0),
    error_message text,
    started_at timestamptz not null,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    check (window_start < window_end),
    check (candidate_count = embedding_count + missing_embedding_count),
    check (saved_topic_count <= selected_topic_count)
);

create table if not exists three_day_topics (
    id bigserial primary key,
    run_id bigint not null references three_day_topic_runs(id) on delete restrict,
    reference_date date not null,
    window_start timestamptz not null,
    window_end timestamptz not null,
    topic_candidate_id text not null,
    title_ko text not null,
    summary_ko text not null,
    key_points jsonb not null default '[]'::jsonb,
    keywords jsonb not null default '[]'::jsonb,
    confidence double precision not null
        check (confidence >= 0 and confidence <= 1),
    article_count integer not null default 0 check (article_count >= 0),
    source_count integer not null default 0 check (source_count >= 0),
    status text not null default 'ready',
    provider text not null,
    model text not null,
    prompt_version text not null,
    summary_input_hash text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (window_start < window_end),
    unique (window_start, window_end, topic_candidate_id)
);

create table if not exists three_day_topic_articles (
    id bigserial primary key,
    three_day_topic_id bigint not null
        references three_day_topics(id) on delete cascade,
    article_id bigint not null references articles(id) on delete cascade,
    rank integer not null check (rank >= 1),
    similarity double precision,
    is_representative boolean not null default false,
    is_summary_evidence boolean not null default false,
    created_at timestamptz not null default now(),
    unique (three_day_topic_id, article_id)
);

create index if not exists idx_three_day_topic_runs_window
on three_day_topic_runs (window_end desc, window_start desc, id desc);

create index if not exists idx_three_day_topic_runs_status
on three_day_topic_runs (status, started_at desc);

create index if not exists idx_three_day_topics_archive
on three_day_topics (reference_date desc, window_end desc, id desc);

create index if not exists idx_three_day_topics_status
on three_day_topics (status, reference_date desc, window_end desc);

create index if not exists idx_three_day_topics_run_id
on three_day_topics (run_id);

create index if not exists idx_three_day_topic_articles_topic_rank
on three_day_topic_articles (three_day_topic_id, rank, article_id);

create index if not exists idx_three_day_topic_articles_article_id
on three_day_topic_articles (article_id);
