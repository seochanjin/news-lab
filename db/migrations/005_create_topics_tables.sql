create table if not exists topics (
    id bigserial primary key,
    topic_date date not null,
    topic_candidate_id text not null,
    title_ko text not null,
    summary_ko text not null,
    key_points jsonb not null default '[]'::jsonb,
    keywords jsonb not null default '[]'::jsonb,
    confidence double precision not null check (confidence >= 0 and confidence <= 1),
    provider text not null,
    model text not null,
    status text not null default 'draft',
    source_count integer not null default 0,
    article_count integer not null default 0,
    summary_input_hash text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (summary_input_hash, provider, model)
);

create table if not exists topic_articles (
    id bigserial primary key,
    topic_id bigint not null references topics(id) on delete cascade,
    article_id bigint not null references articles(id) on delete cascade,
    role text not null default 'representative',
    similarity_score double precision,
    created_at timestamptz not null default now(),
    unique (topic_id, article_id)
);

create index if not exists idx_topics_topic_date on topics (topic_date desc);
create index if not exists idx_topics_status on topics (status);
create index if not exists idx_topics_created_at on topics (created_at desc);
create index if not exists idx_topic_articles_topic_id on topic_articles (topic_id);
create index if not exists idx_topic_articles_article_id on topic_articles (article_id);
