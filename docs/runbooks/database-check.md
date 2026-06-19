# Database와 Local Read Check

[Runbook index로 돌아가기](../RUNBOOK.md)

## 원칙

- Agent는 Supabase SQL과 production migration을 실행하지 않는다.
- Credential과 `DATABASE_URL` 값을 출력하거나 기록하지 않는다.
- Collector, extractor, daily pipeline은 DB write 가능성이 있으므로 명시적 승인
  없이 실행하지 않는다.
- Read API 확인과 schema file 검토를 DB 상태 변경과 구분한다.

## Local API

환경 변수가 이미 안전하게 준비된 local environment에서 실행한다.

```bash
uvicorn app.main:app --reload
```

다른 terminal에서 read endpoint를 확인한다.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/sources
curl http://127.0.0.1:8000/articles
curl http://127.0.0.1:8000/collector/status
curl http://127.0.0.1:8000/raw-articles
curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/topics
curl http://127.0.0.1:8000/topics/home
```

Local API도 실제 configured DB를 읽을 수 있으므로 response 원문이나 민감한
application data를 verification 문서에 그대로 복사하지 않는다.

## Schema 확인

Repository에서 관리하는 변경 이력:

```bash
find db/migrations -maxdepth 1 -type f | sort
rg -n "create table|alter table|create index" db/migrations
```

Migration file 작성은 가능하지만 실행은 사람이 수행한다. 실행 전 migration
내용, 예상 변경, rollback 또는 복구 계획을 review한다.

## DB write script

다음 command는 문서 예시이며 자동 실행 대상이 아니다.

```bash
python scripts/collect_rss.py
python scripts/extract_raw_articles.py
python scripts/run_daily_topic_pipeline.py --execute
```

실행 승인을 요청할 때 생성·변경될 table과 예상 범위를 먼저 설명한다.

## Article embedding migration

`db/migrations/006_create_article_embeddings.sql` 적용은 human-controlled
operation이다. Agent는 Supabase SQL editor나 production database에서 이
migration을 실행하지 않는다.

적용 전 확인:

```sql
select id, title, summary
from articles
order by id desc
limit 1;

select extname
from pg_extension
where extname = 'vector';
```

확인 기준:

- `articles.id`가 bigint-compatible type이다.
- `articles.title`, `articles.summary`가 존재한다.
- Supabase project에서 `vector` extension 생성 권한이 있다.
- 기존 `article_embeddings` object와 이름이 충돌하지 않는다.

사람이 migration 적용 후 실행할 read-only schema 확인:

```sql
select extname
from pg_extension
where extname = 'vector';

select column_name, data_type, udt_name
from information_schema.columns
where table_schema = 'public'
  and table_name = 'article_embeddings'
order by ordinal_position;

select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.article_embeddings'::regclass
order by conname;
```

중단 기준:

- `vector` extension 생성 실패
- `articles(id)` foreign key type 불일치
- 기존 table 또는 constraint와 예상하지 않은 충돌
- embedding dimension이 1536이 아닌 schema

초기 migration이 transaction 안에서 실패하면 변경을 commit하지 않고 원인을
확인한다. 적용 후 되돌려야 할 경우, embedding data 보존 필요성을 먼저 판단한
뒤 사람이 다음 SQL을 검토하고 실행한다.

```sql
drop table if exists article_embeddings;
```

`vector` extension은 다른 object가 사용할 수 있으므로 자동 rollback 대상으로
제거하지 않는다.

## Article embedding batch 확인

다음 command는 DB read/write와 provider 호출 가능성이 있어 사람이 안전한
test 또는 production environment를 확인한 뒤 실행한다.

Read-only selection:

```bash
python scripts/embed_articles.py --limit 3 --dry-run
```

실제 소량 처리:

```bash
python scripts/embed_articles.py --limit 3
```

같은 command를 다시 실행했을 때 `reused`가 증가하고 `created`, `updated`가
증가하지 않는지 확인한다. 운영 article의 제목이나 요약을 update 검증 목적으로
수정하지 않는다. Hash 변경 update는 별도 test fixture에서 검증한다.
