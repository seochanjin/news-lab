create extension if not exists vector
with schema extensions;

create table if not exists article_embeddings (
    id bigserial primary key,
    article_id bigint not null references articles(id) on delete cascade,
    embedding vector(1536) not null,
    provider text not null,
    model text not null,
    dimension integer not null check (dimension = 1536),
    source_text_type text not null,
    source_text_hash text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (article_id, provider, model, source_text_type)
);

create index if not exists idx_article_embeddings_lookup
on article_embeddings (provider, model, dimension, source_text_type);
