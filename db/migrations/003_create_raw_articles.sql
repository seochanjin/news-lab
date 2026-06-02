create table if not exists raw_articles (
    id bigserial primary key,
    article_id bigint not null references articles(id) on delete cascade,
    raw_text text,
    extraction_status text not null default 'pending',
    error_message text,
    extracted_at timestamptz,
    created_at timestamptz not null default now(),
    unique (article_id)
);
