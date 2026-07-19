# Task: Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## Goal

Production Supabase PostgreSQL을 변경하지 않고 논리 Backup을 생성한 뒤, Mac 로컬의 격리된 PostgreSQL + pgvector 환경에 실제 Restore하여 복구 가능성을 검증한다.

이번 작업은 정기 Backup 시스템 구축이 아니라 다음 수동 복구 흐름을 한 번 끝까지 수행하는 훈련이다.

```
Production Supabase PostgreSQL
→ read-only logical backup
→ checksum 및 archive 목록 검증
→ Mac 로컬 Docker PostgreSQL + pgvector
→ isolated restore
→ schema·data·constraint·index·sequence·vector 검증
→ 임시 restore 환경 정리
```

핵심 완료 기준은 Backup 생성 자체가 아니라, 별도의 격리 환경에서 실제 Restore가 성공하고 주요 구조와 데이터 정합성을 확인하는 것이다.

## Scope

### UNIT-01에서 먼저 확정할 baseline

- `pg_dump --version`과 Production PostgreSQL server major를 가장 먼저 비교
- client major가 server major보다 낮지 않은지 확인
- NewsLab DB 연결 설정의 주입 경로 확인
- 실제 credential 값은 조회·출력하지 않고 Secret 이름과 환경변수 계약만 확인
- `pg_dump`에 사용할 연결 경로를 명시적으로 확정
  - 우선 검토: direct connection, port `5432`
  - Direct IPv6 연결이 불가능한 경우: Shared Pooler session mode, port `5432`
  - 제외: Transaction Pooler, port `6543`
- `public`, extension schema와 `supabase_migrations`를 조사
- 각 schema를 Backup 대상에 포함하거나 제외할지 근거와 함께 기록
- NewsLab이 사용하는 table, view, sequence, constraint와 index 확인
- `vector` extension version·설치 schema와 embedding column type·dimension 확인
- table별 source row count baseline 확보
- 복구 후 실행할 대표 read-only query 3~5개 선정
- Backup artifact가 Git에 포함되지 않도록 `.gitignore`와 작업 경계 확인

### Logical Backup

- Production과 호환되는 `pg_dump` client 사용
- custom archive format 사용
- Backup 대상 schema와 object 범위는 UNIT-01 결과로 확정
- 격리 Restore에 불필요한 owner와 ACL은 제외
- Backup 파일은 Repository 밖의 로컬 디렉터리에 생성
- Backup 파일 크기, 소요 시간과 SHA-256 checksum 기록
- `pg_restore --list`로 archive를 읽을 수 있는지 확인
- Production에는 read-only 연결만 수행

### 격리 Restore

- Mac 로컬 Docker 사용
- Production과 동일한 PostgreSQL major의 pgvector image 사용
- `127.0.0.1`에만 노출되는 임시 restore database 구성
- Production credential과 분리된 로컬 전용 credential 사용
- extension과 schema 준비 순서는 UNIT-01·02 결과로 확정
- `pg_restore --exit-on-error`를 사용해 일부 object 실패를 놓치지 않음
- K3s, PV, PVC와 Production workload는 사용하지 않음

### Restore 검증

- Backup 대상 전체 table의 source/restore row count 비교
- primary key, foreign key, unique constraint와 index 확인
- foreign key orphan 0건 확인
- sequence 존재와 정합성 확인
- `vector` extension, 설치 schema, embedding column type과 dimension 확인
- 대표 read-only query 3~5개 실행
- 실제 기사 본문, summary, embedding 값과 credential은 evidence에 기록하지 않음

### 정리 및 기록

- Task에는 설계 결정과 범위만 유지
- Verification에는 실행 명령의 sanitized 형태, 결과, 소요 시간과 실패·수정 이력 기록
- 기존 Runbook에 자연스럽게 포함하기 어렵다면 Backup/Restore Runbook 한 개만 추가
- 임시 Docker container, volume과 `/tmp` artifact 정리
- Backup 파일과 checksum의 최종 보존 또는 삭제 상태 명시

## Do not change

- Production DB schema, table, column, constraint와 index
- Production 데이터의 `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`
- Production에서 `CREATE`, `ALTER`, `DROP`
- Production DB로의 Restore
- Supabase 프로젝트 설정, 관리형 Backup 정책과 요금제
- PITR 설정
- FastAPI application code
- Pipeline business logic
- DB migration과 Supabase SQL
- API request/response schema와 인증 정책
- Redis와 Home Cache 설정
- CronJob schedule, command, retry와 timezone
- K3s Deployment, StatefulSet, Job와 CronJob
- K3s PV, PVC와 StorageClass
- Monitoring, Grafana, Prometheus와 Alertmanager 설정
- 정기 Backup 자동화
- Object Storage와 Backup lifecycle 정책
- GitHub Actions 또는 외부 scheduler
- Production Secret 조회·디코딩·변경
- DB password, 전체 connection string와 Backup 데이터의 Repository·Notion 기록
- Agent의 Production write query 실행
- Agent의 Production Backup·Restore 명령 실행
- Agent의 Docker container·volume 생성 및 삭제
- Agent의 git push와 PR merge

Production 연결, Backup 생성, Docker Restore와 임시 환경 정리는 사람이 명령과 diff를 검토한 뒤 직접 수행한다. Agent는 Repository 조사, 명령 설계, sanitized evidence 정리와 문서화만 담당한다.

## Expected files

필수 문서는 다음 두 개로 제한한다.

```
docs/tasks/feat-database-backup-restore-drill.md
docs/verification/feat-database-backup-restore-drill.md
```

기존 운영 문서에 자연스럽게 포함하기 어렵다면 다음 Runbook 한 개만 추가한다.

```
docs/runbooks/database-backup-restore.md
```

다음 문서는 실제 필요가 생긴 경우에만 작성한다.

- PR 문서: Repository workflow가 명시적으로 요구하는 경우
- Review 문서: 실제 Review 결과가 존재하는 경우
- Approved Fixes 문서: 승인된 수정 사항이 실제로 존재하는 경우

다음 placeholder 문서는 기본 생성 대상이 아니다.

```
docs/design/database-backup-restore-drill.md
docs/devlog/feat-database-backup-restore-drill.md
빈 Antigravity Review
빈 CodeRabbit Review
빈 Approved Fixes
```

Backup 파일, checksum과 raw archive 목록은 Repository에 추가하지 않는다.

## DB changes

없음.

- Production schema 변경 없음
- migration 추가 없음
- Production 데이터 변경 없음
- Restore는 Mac 로컬의 격리된 임시 database에만 수행
- 로컬 restore database와 Docker volume은 Production resource가 아님

## API changes

없음.

- FastAPI endpoint 변경 없음
- request/response schema 변경 없음
- 인증·권한 정책 변경 없음
- application 실행 계약 변경 없음
- Restore 검증은 read-only SQL 중심으로 수행

## Test commands

실제 command는 UNIT-01 baseline 결과에 따라 PostgreSQL major, 연결 경로, schema와 image tag를 확정한 뒤 작성한다. Credential은 command history, process argument, log, 문서와 Git diff에 남기지 않는다.

### Client와 server major 확인

```bash
pg_dump --version
psql <SAFE_CONNECTION_ARGS> -X -v ON_ERROR_STOP=1 \
  -c 'SHOW server_version;'
```

완료 조건:

```
pg_dump client major >= Production server major
```

### Connection path 확인

사람이 다음 중 하나를 선택하고 Verification에 host 전체가 아닌 mode와 port만 기록한다.

```
Direct connection / 5432
Shared Pooler session mode / 5432
```

Transaction Pooler `6543`은 사용하지 않는다.

### Production read-only baseline

```bash
psql <SAFE_CONNECTION_ARGS> -X -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_setting('server_version');
SELECT current_database();

SELECT extname, extversion, n.nspname AS extension_schema
FROM pg_extension e
JOIN pg_namespace n ON n.oid = e.extnamespace
ORDER BY extname;

SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
SQL
```

Table별 row count, constraint, index, sequence와 vector dimension query는 실제 schema 조사 후 작성한다. 데이터 본문은 출력하지 않는다.

### Logical Backup

Production 접속 parameter와 password는 UNIT-02의 read-only bind mount
`pg_service.conf`·`pgpass`로만 주입한다. `<SAFE_DUMP_CONNECTION_ARGS>`를
CLI connection argument로 풀어 쓰지 않는다.

```bash
PGSERVICE=newslab_backup \
PGSERVICEFILE=<MOUNTED_SERVICE_FILE> \
PGPASSFILE=<MOUNTED_PASSFILE> \
pg_dump \
  --format=custom \
  --no-owner \
  --no-acl \
  --schema=public \
  --file=<REPOSITORY_OUTSIDE_BACKUP_PATH>
```

### Archive 검증

```bash
test -s <BACKUP_PATH>
pg_restore --list <BACKUP_PATH> > <TEMP_LIST_PATH>
shasum -a 256 <BACKUP_PATH> > <CHECKSUM_PATH>
```

### Local Restore

```bash
docker run -d \
  --name <RESTORE_CONTAINER> \
  --mount type=volume,src=<RESTORE_VOLUME>,dst=/var/lib/postgresql/data \
  --mount type=bind,src=<LOCAL_PASSWORD_FILE>,dst=/run/secrets/local_password,readonly \
  --mount type=bind,src=<ARTIFACT_DIRECTORY>,dst=/backup,readonly \
  -e POSTGRES_DB=<LOCAL_DB> \
  -e POSTGRES_USER=<LOCAL_USER> \
  -e POSTGRES_PASSWORD_FILE=/run/secrets/local_password \
  -p 127.0.0.1:<LOCAL_PORT>:5432 \
  pgvector/pgvector:0.8.0-pg17

docker exec <RESTORE_CONTAINER> pg_restore \
  --single-transaction \
  --exit-on-error \
  --no-owner \
  --no-acl \
  --username=<LOCAL_USER> \
  --dbname=<LOCAL_DB> \
  /backup/<ARCHIVE_NAME>.dump
```

### 정합성 검증

실제 schema를 기준으로 다음 검증 SQL을 작성한다.

```
전체 대상 table source/restore row count
foreign key orphan count
constraint와 index 목록
sequence 목록과 현재값
vector extension version·schema
embedding column type·dimension
대표 read-only query 3~5개
```

### Repository와 민감정보 검사

```bash
PYTHONPATH=. pytest -q
git diff --check
git status --short

rg -n \
  '(postgres(ql)?://[^[:space:]]+|password[=:][^[:space:]]+|SUPABASE_DB_PASSWORD)' \
  docs scripts . \
  --glob '!*.backup' \
  --glob '!*.dump' || true
```

탐지 결과에 실제 값이 포함될 가능성이 있으면 내용을 복사하지 않고 파일 위치만 확인해 제거한다.

### 임시 환경 정리

```bash
docker rm -f <RESTORE_CONTAINER>
docker volume rm <RESTORE_VOLUME>
rm -f <TEMP_LIST_PATH>
```

## Acceptance criteria

- [x] Production write 없이 logical Backup을 생성하고 checksum 및 `pg_restore --list` 검증을 통과한다.
- [x] Production과 동일한 PostgreSQL major 및 pgvector를 사용하는 격리된 로컬 환경에 `pg_restore --exit-on-error`로 Restore한다.
- [x] Backup 대상 전체 table의 source/restore row count가 일치하고 foreign key orphan이 0건이다.
- [x] `vector` extension, 설치 schema, embedding column type과 dimension이 복구 전후 일치한다.
- [x] 대표 read-only query 3~5개가 Restore DB에서 정상 실행된다.
- [x] Credential과 데이터 본문을 기록하지 않고 임시 container, volume, credential artifact와 불필요한 임시 파일을 정리한다.

## Notes

- 이번 작업은 한 번의 수동 Backup/Restore 훈련이다.
- 정기 Backup, K3s CronJob, PV/PVC, Object Storage, 보존 정책과 성공·실패 Alert는 구현하지 않는다.
- `public` schema를 사전에 Backup 대상으로 가정하지 않는다.
- `public`, extension schema와 `supabase_migrations`의 포함·제외 여부를 UNIT-01에서 명시적으로 결정한다.
- `pg_dump` client/server major 비교를 UNIT-01의 첫 검증으로 수행한다.
- Backup 연결 경로를 UNIT-01에서 확정하지 못하면 UNIT-03으로 진행하지 않는다.
- Direct connection의 IPv6 접근이 불가능하면 session mode 5432를 검토하되 transaction mode 6543은 사용하지 않는다.
- 실제 기사 본문, summary, URL 목록, embedding vector와 credential은 evidence에 복사하지 않는다.
- Checklist의 핵심 완료 기준은 Acceptance criteria 6개다. 세부 검증 결과는 Verification evidence로 기록한다.
- 안전성이나 복구 가능성 증명에 기여하지 않는 중복 문서는 만들지 않는다.

## UNIT-01 baseline

### Repository 연결 계약과 작업 경계

- Application과 DB 접근 script는 `DATABASE_URL` 환경변수를 사용한다.
- K3s의 API, RSS collector, Daily·3-day·Weekly Topic workload는 Kubernetes
  Secret `news-api-secret`의 `DATABASE_URL` key를 같은 이름의 환경변수로
  주입한다. Secret 값은 조회하거나 Backup 작업에 복사하지 않는다.
- Local 개발 환경에서는 `app/database.py`가 `.env`를 읽을 수 있지만 `.env`는
  Git ignore 대상이며, Backup operator credential 전달 경로로 문서화하지 않는다.
- Backup operator는 Production Secret과 독립적으로 준비한
  `<SAFE_CONNECTION_ARGS>`를 사용한다. 전체 host, user, database와 password는
  command argument, shell history, process 목록, log와 문서에 남기지 않는다.
- Backup archive, checksum과 raw `pg_restore --list` 결과는 Repository 밖의
  operator 전용 directory에 둔다. 현재 `.gitignore`는 `*.backup`, `*.dump`를
  무시하지 않으므로 Repository 내부 생성 금지가 주된 통제다.

### Client/server major와 연결 경로

- 2026-07-19 Agent 환경에는 `pg_dump`, `psql`, `pg_restore` executable이 없어
  host PATH 기반 local client major를 확인하지 못했다.
- 사람이 `postgres:17` Docker image에서 `pg_dump`, `psql`, `pg_restore` 17.10을
  확인했고 Production PostgreSQL 17.6과 major 17 호환성을 검증했다.
- `Direct connection / 5432`는 local Docker 환경에서 endpoint 주소를 해석하지
  못해 실패했다. `Shared Pooler session mode / 5432` 연결은 성공해 Backup 연결
  경로로 확정했으며 `Transaction Pooler / 6543`은 사용하지 않는다.
- 전체 host, user, project reference, password와 connection string은 기록하지
  않는다.

### Repository schema baseline과 Backup 범위 판단

Repository 자료는 Production의 완전한 schema source of truth가 아니다.
특히 `sources`, `articles`의 초기 정의와 Production에서 추가된 object는 아래
operator query로 확인해야 한다.

| Schema | UNIT-01 판단 | 근거와 확인 사항 |
| --- | --- | --- |
| `public` | 포함 | Application table·data·sequence·constraint·index를 Backup 대상으로 확정했다. |
| `extensions` | 제외 | Schema 전체를 archive에서 제외하고 Restore 전에 `pgvector` 0.8.0을 준비한다. |
| `supabase_migrations` | 제외 | Production에 schema가 존재하지 않는다. |

Repository migration과 architecture 문서가 식별하는 `public` table은 다음 14개다.

```text
sources
articles
crawl_runs
raw_articles
extraction_runs
topics
topic_articles
article_embeddings
three_day_topic_runs
three_day_topics
three_day_topic_articles
weekly_topic_runs
weekly_topics
weekly_topic_articles
```

Migration은 위 table 중 `sources`, `articles`를 제외한 12개 table에 `bigserial`
primary key를 선언하고 이에 딸린 sequence를 예상한다. Foreign key, unique/check
constraint와 명시적 B-tree index도 정의한다. 사람의 Production catalog 조회에서
application table 14개, sequence 14개, index 45개와 constraint 83개가 확인됐고
모든 application table에 primary key가 있다.
`db/migrations/006_create_article_embeddings.sql`의 기대 계약은 `vector` extension을
`extensions` schema에 설치하고 `public.article_embeddings.embedding`을
`vector(1536)`으로 정의하는 것이다. Production도 `pgvector` 0.8.0,
`extensions` schema와 `vector(1536)` type으로 이 계약과 일치한다.

### Human-required read-only baseline

Operator는 선택한 5432 연결 경로에서 다음 조회를 수행하고 민감정보나 데이터
본문 없이 결과를 Verification에 제공한다.

```sql
select current_setting('server_version') as server_version;

select n.nspname as schema_name
from pg_namespace n
where n.nspname in ('public', 'extensions', 'supabase_migrations')
order by n.nspname;

select e.extname, e.extversion, n.nspname as extension_schema
from pg_extension e
join pg_namespace n on n.oid = e.extnamespace
order by e.extname;

select n.nspname as schema_name,
       c.relname as relation_name,
       c.relkind
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname in ('public', 'extensions', 'supabase_migrations')
  and c.relkind in ('r', 'p', 'v', 'm', 'S')
order by n.nspname, c.relkind, c.relname;

select n.nspname as schema_name,
       c.relname as table_name,
       con.conname,
       con.contype,
       con.convalidated,
       pg_get_constraintdef(con.oid) as definition
from pg_constraint con
join pg_class c on c.oid = con.conrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
order by c.relname, con.conname;

select schemaname, tablename, indexname, indexdef
from pg_indexes
where schemaname = 'public'
order by tablename, indexname;

select n.nspname as table_schema,
       c.relname as table_name,
       a.attname as column_name,
       format_type(a.atttypid, a.atttypmod) as formatted_type
from pg_attribute a
join pg_class c on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname = 'article_embeddings'
  and a.attname = 'embedding'
  and not a.attisdropped;
```

전체 `public` base table의 count는 table 이름과 숫자만 출력하도록 다음 psql
query로 수집한다.

```sql
select format(
  'select %L as table_name, count(*) as row_count from %I.%I;',
  tablename,
  schemaname,
  tablename
)
from pg_tables
where schemaname = 'public'
order by tablename
\gexec
```

Restore 전후 비교할 대표 read-only query는 다음 5개로 정한다. 결과 evidence에는
aggregate 숫자와 상태값만 기록하고 기사 본문, summary, URL 또는 vector 값은
기록하지 않는다.

1. 활성 source 수와 전체 article 수
2. source별 article 수와 최신 `published_at` 시각
3. `raw_articles.extraction_status`별 건수
4. Daily·3-day·Weekly Topic별 결과 및 연결 article 건수
5. provider, model, dimension별 `article_embeddings` 건수와 전체 article 대비
   embedding 보유 article 수

UNIT-01 세부 상태:

| 작업 | 상태 |
| --- | --- |
| Repository DB 설정 주입 경로와 credential 계약 조사 | 완료 |
| Repository schema·migration·vector 기대 baseline 조사 | 완료 |
| Backup artifact의 Git 경계와 대표 read-only query 선정 | 완료 |
| `pg_dump` client major와 Production server major 비교 | 완료 |
| Production 연결 mode와 port 확정 | 완료 |
| Production schema/object·extension·table별 row count baseline 확보 | 완료 |

## UNIT-02 Backup/Restore 설계

UNIT-02는 사람이 UNIT-03·04의 명령을 검토하고 실행하기 전에
Backup 대상, archive format, credential·artifact 경계와 격리 Restore 순서를
확정한다. 아래 명령은 모두 human-controlled 예정 명령이며 UNIT-02에서는
실행하지 않는다.

### Backup 대상과 archive 계약

| 항목 | 확정값 | 근거 |
| --- | --- | --- |
| Connection | Shared Pooler session mode, port `5432` | UNIT-01에서 PostgreSQL 17.6 연결을 확인했다. Transaction Pooler `6543`은 제외한다. |
| Client | `postgres:17` image의 PostgreSQL 17 client | 검증된 client 17.10은 server major 17보다 낮지 않다. |
| Schema | `--schema=public` | 14개 application table의 schema, data, sequence, constraint와 index를 포함한다. |
| Exclusion | `extensions`, Supabase 관리 schema, `supabase_migrations` | `vector`는 Restore 전에 준비하고 `supabase_migrations`는 Production에 없다. Schema 선택 dump는 다른 schema를 포함하지 않는다. |
| Format | `--format=custom` | `pg_restore --list`, 선택 Restore와 archive 압축을 지원한다. |
| Ownership/ACL | dump와 Restore 둘 다 `--no-owner --no-acl` | 로컬 role에 Production owner·grant를 재현하지 않는다. Custom archive에서 owner 적용 제외는 Restore 옵션이 실질적인 통제이다. |
| Consistency | 단일 `pg_dump`, 병렬 job 없음 | `pg_dump`의 일관된 snapshot을 사용하고 이번 수동 drill에서 복잡도를 늘리지 않는다. |

`--schema=public`은 다른 schema의 의존 object를 자동 포함하지 않으므로
`extensions.vector`를 Restore 전에 먼저 생성한다. Large object는 UNIT-01
Production catalog에서 application Backup 대상으로 식별되지 않았고 schema
선택 dump에도 기본 포함되지 않으므로 대상이 아니다.

UNIT-03 operator가 검토할 sanitized dump 형태는 다음과 같다.

```bash
docker run --rm \
  --mount type=bind,src=<PRODUCTION_SERVICE_FILE>,dst=/run/secrets/pg_service.conf,readonly \
  --mount type=bind,src=<PRODUCTION_PASSFILE>,dst=/run/secrets/pgpass,readonly \
  --mount type=bind,src=<ARTIFACT_DIRECTORY>,dst=/backup \
  --env PGSERVICE=newslab_backup \
  --env PGSERVICEFILE=/run/secrets/pg_service.conf \
  --env PGPASSFILE=/run/secrets/pgpass \
  postgres:17 \
  pg_dump \
    --format=custom \
    --schema=public \
    --no-owner \
    --no-acl \
    --file=/backup/<ARCHIVE_NAME>.dump
```

### Production credential 경계

- Production 접속 정보는 Repository 밖의 operator 전용 credential
  directory에 `pg_service.conf`와 `pgpass`로 분리한다. Directory는
  mode `0700`, 두 file은 mode `0600`을 확인한다.
- `pg_service.conf`에는 service name `newslab_backup`, session pooler host,
  port `5432`, database, user, `sslmode=require`를 두고 `pgpass`에는 이와
  일치하는 password entry를 둔다. 실제 값은 문서, shell history,
  command argument, process 목록과 Verification에 기록하지 않는다.
- `PGPASSWORD`, connection URI, `--password`, interactive password prompt와
  Kubernetes `news-api-secret` 조회·decode를 사용하지 않는다.
- Credential directory를 archive directory와 분리하고 Docker에 read-only
  bind mount한다. UNIT-03 Production read-only baseline과 dump가 끝나면 두
  credential file을 삭제하고 directory를 제거한 결과를 기록한다.

### Backup artifact 경계와 수명

- Archive directory는 Repository root의 하위가 아닌 operator 전용 임시
  directory로 생성하고 mode `0700`을 적용한다. 생성 후
  `git -C <REPOSITORY_ROOT> check-ignore` 결과에 의존하지 않고 경로
  자체가 Repository 밖임을 확인한다.
- `<ARCHIVE_NAME>.dump`, `<ARCHIVE_NAME>.dump.sha256`,
  `<ARCHIVE_NAME>.list`는 같은 directory에 둔다. Archive와 raw list는
  Production data·object metadata artifact로 간주해 Git, Notion, chat,
  ticket에 첨부하지 않는다.
- Verification에는 archive basename, byte size, elapsed time, SHA-256 digest,
  `pg_restore --list` exit status와 entry count만 기록한다. Raw list와
  archive 내용은 복사하지 않는다.
- Archive와 checksum은 UNIT-04·05가 완료될 때까지 유지한다.
  UNIT-06에서 최종 보존 경로와 권한 또는 삭제 결과를 확정하며,
  UNIT-02에서 미리 삭제하지 않는다.

Archive 검증은 다음 순서로 중단 조건을 두고 수행한다.

```bash
test -s <BACKUP_PATH>
pg_restore --list <BACKUP_PATH> > <TEMP_LIST_PATH>
shasum -a 256 <BACKUP_PATH> > <CHECKSUM_PATH>
shasum -a 256 -c <CHECKSUM_PATH>
```

Empty archive, `pg_restore --list` non-zero, checksum 생성·재검증 실패 중
하나라도 발생하면 UNIT-04로 진행하지 않는다.

### 격리 Restore 환경과 순서

| 항목 | 확정값 |
| --- | --- |
| Image | `pgvector/pgvector:0.8.0-pg17` versioned tag. Pull 후 resolved image digest를 Verification에 기록한다. |
| Network | `-p 127.0.0.1:<LOCAL_PORT>:5432`; 모든 interface bind를 금지한다. |
| Storage | 이 drill 전용 named volume 하나. K3s PV·PVC와 host Production data를 mount하지 않는다. |
| Credential | Production과 다른 local user·database·random password. `POSTGRES_PASSWORD_FILE`에 Repository 밖 `0600` file을 read-only mount한다. |
| Archive mount | Archive directory를 Restore container에 read-only mount한다. |
| Failure atomicity | `pg_restore --single-transaction --exit-on-error`; 일부 object만 남은 Restore를 성공으로 판정하지 않는다. |

UNIT-04 operator는 다음 순서를 바꾸지 않는다.

1. 전용 container·volume·local credential file 이름이 기존 resource와
   충돌하지 않음을 확인한다.
2. Versioned image로 container를 생성하고 `127.0.0.1`에만 port를
   publish한 뒤 `pg_isready`를 확인한다.
3. PostgreSQL server major가 17임을 확인한다.
4. 초기 database의 `public` schema를 비우기 위해 해당 일회성
   local database에서만 `drop schema public cascade`를 실행한다.
   즉시 `extensions` schema를 생성하고
   `create extension vector with schema extensions version '0.8.0'`을 실행한다.
5. `vector` version·schema가 각각 `0.8.0`, `extensions`임을 확인하고
   `public` application relation이 없음을 확인한다.
6. Archive의 SHA-256을 다시 확인한 뒤 다음 형태로 Restore한다.

```bash
docker exec <RESTORE_CONTAINER> \
  pg_restore \
    --single-transaction \
    --exit-on-error \
    --no-owner \
    --no-acl \
    --username=<LOCAL_USER> \
    --dbname=<LOCAL_DB> \
    /backup/<ARCHIVE_NAME>.dump
```

7. Restore exit status 0인 경우에만 UNIT-05 정합성 검증을 시작한다.

`public` schema drop은 새로 생성한 일회성 local database의 archive
Restore 전 빈 상태를 만들기 위한 human-controlled 명령이다. Database,
container, volume 식별자 중 하나라도 예정값과 다르거나 Production
연결 설정이 보이면 즉시 중단한다. Restore 실패 시 single transaction의
rollback을 확인하고, 불명확한 상태에서 덮어쓰거나 `--clean`으로
재시도하지 않는다. 사람이 일회성 container·volume을 정리하고
새 환경에서 원인을 수정한 뒤 다시 시작한다.

PostgreSQL 17의 schema 선택 dump, connection service file, password file와
fail-fast Restore 동작은 공식
[`pg_dump`](https://www.postgresql.org/docs/17/app-pgdump.html),
[`pg_restore`](https://www.postgresql.org/docs/17/app-pgrestore.html),
[`pg_service.conf`](https://www.postgresql.org/docs/17/libpq-pgservice.html),
[`pgpass`](https://www.postgresql.org/docs/17/libpq-pgpass.html) 문서를 기준으로
했다. pgvector 0.8.0의 PostgreSQL 17 image 계약은
[`pgvector` v0.8.0](https://github.com/pgvector/pgvector/tree/v0.8.0)과 versioned
Docker tag를 확인했다.

## UNIT-05 정합성 검증 절차

UNIT-05는 UNIT-04에서 유지한 격리 Restore database만 조회한다. 아래 명령은
human-controlled read-only 검증이며 Agent는 Docker command나 Local DB query를
실행하지 않는다. Operator는 container와 database가 UNIT-04의 논리 이름과
일치하고 container가 `127.0.0.1:55432`에만 bind된 상태인지 먼저 확인한다.
식별자가 다르거나 Production 연결 설정이 보이면 실행하지 않는다.

```bash
docker exec -i <RESTORE_CONTAINER> \
  psql \
    --username=<LOCAL_USER> \
    --dbname=<LOCAL_DB> \
    -X \
    -v ON_ERROR_STOP=1 <<'SQL'
\pset pager off
begin read only;

\echo 'UNIT05_ROW_COUNTS'
with restored(table_name, restored_rows) as (
  values
    ('article_embeddings', (select count(*) from public.article_embeddings)),
    ('articles', (select count(*) from public.articles)),
    ('crawl_runs', (select count(*) from public.crawl_runs)),
    ('extraction_runs', (select count(*) from public.extraction_runs)),
    ('raw_articles', (select count(*) from public.raw_articles)),
    ('sources', (select count(*) from public.sources)),
    ('three_day_topic_articles', (select count(*) from public.three_day_topic_articles)),
    ('three_day_topic_runs', (select count(*) from public.three_day_topic_runs)),
    ('three_day_topics', (select count(*) from public.three_day_topics)),
    ('topic_articles', (select count(*) from public.topic_articles)),
    ('topics', (select count(*) from public.topics)),
    ('weekly_topic_articles', (select count(*) from public.weekly_topic_articles)),
    ('weekly_topic_runs', (select count(*) from public.weekly_topic_runs)),
    ('weekly_topics', (select count(*) from public.weekly_topics))
), expected(table_name, source_rows) as (
  values
    ('article_embeddings', 4042::bigint),
    ('articles', 6372::bigint),
    ('crawl_runs', 51::bigint),
    ('extraction_runs', 154::bigint),
    ('raw_articles', 469::bigint),
    ('sources', 10::bigint),
    ('three_day_topic_articles', 604::bigint),
    ('three_day_topic_runs', 27::bigint),
    ('three_day_topics', 123::bigint),
    ('topic_articles', 268::bigint),
    ('topics', 87::bigint),
    ('weekly_topic_articles', 102::bigint),
    ('weekly_topic_runs', 6::bigint),
    ('weekly_topics', 15::bigint)
)
select e.table_name,
       e.source_rows,
       r.restored_rows,
       e.source_rows = r.restored_rows as matches
from expected e
join restored r using (table_name)
order by e.table_name;

with restored(restored_rows) as (
  values
    ((select count(*) from public.article_embeddings)),
    ((select count(*) from public.articles)),
    ((select count(*) from public.crawl_runs)),
    ((select count(*) from public.extraction_runs)),
    ((select count(*) from public.raw_articles)),
    ((select count(*) from public.sources)),
    ((select count(*) from public.three_day_topic_articles)),
    ((select count(*) from public.three_day_topic_runs)),
    ((select count(*) from public.three_day_topics)),
    ((select count(*) from public.topic_articles)),
    ((select count(*) from public.topics)),
    ((select count(*) from public.weekly_topic_articles)),
    ((select count(*) from public.weekly_topic_runs)),
    ((select count(*) from public.weekly_topics))
)
select 12330::bigint as source_total_rows,
       sum(restored_rows)::bigint as restored_total_rows,
       sum(restored_rows) = 12330 as matches
from restored;

\echo 'UNIT05_FOREIGN_KEY_ORPHANS'
with orphan_counts(relationship, orphan_rows) as (
  values
    ('articles.source_id -> sources.id',
      (select count(*) from public.articles c
       where c.source_id is not null and not exists (
         select 1 from public.sources p where p.id = c.source_id))),
    ('raw_articles.article_id -> articles.id',
      (select count(*) from public.raw_articles c
       where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ('topic_articles.topic_id -> topics.id',
      (select count(*) from public.topic_articles c
       where not exists (select 1 from public.topics p where p.id = c.topic_id))),
    ('topic_articles.article_id -> articles.id',
      (select count(*) from public.topic_articles c
       where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ('article_embeddings.article_id -> articles.id',
      (select count(*) from public.article_embeddings c
       where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ('three_day_topics.run_id -> three_day_topic_runs.id',
      (select count(*) from public.three_day_topics c
       where not exists (select 1 from public.three_day_topic_runs p where p.id = c.run_id))),
    ('three_day_topic_articles.three_day_topic_id -> three_day_topics.id',
      (select count(*) from public.three_day_topic_articles c
       where not exists (select 1 from public.three_day_topics p
                         where p.id = c.three_day_topic_id))),
    ('three_day_topic_articles.article_id -> articles.id',
      (select count(*) from public.three_day_topic_articles c
       where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ('weekly_topics.run_id -> weekly_topic_runs.id',
      (select count(*) from public.weekly_topics c
       where not exists (select 1 from public.weekly_topic_runs p where p.id = c.run_id))),
    ('weekly_topic_articles.weekly_topic_id -> weekly_topics.id',
      (select count(*) from public.weekly_topic_articles c
       where not exists (select 1 from public.weekly_topics p
                         where p.id = c.weekly_topic_id))),
    ('weekly_topic_articles.article_id -> articles.id',
      (select count(*) from public.weekly_topic_articles c
       where not exists (select 1 from public.articles p where p.id = c.article_id)))
)
select relationship, orphan_rows
from orphan_counts
order by relationship;

with orphan_counts(orphan_rows) as (
  values
    ((select count(*) from public.articles c where c.source_id is not null
      and not exists (select 1 from public.sources p where p.id = c.source_id))),
    ((select count(*) from public.raw_articles c
      where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ((select count(*) from public.topic_articles c
      where not exists (select 1 from public.topics p where p.id = c.topic_id))),
    ((select count(*) from public.topic_articles c
      where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ((select count(*) from public.article_embeddings c
      where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ((select count(*) from public.three_day_topics c
      where not exists (select 1 from public.three_day_topic_runs p where p.id = c.run_id))),
    ((select count(*) from public.three_day_topic_articles c
      where not exists (select 1 from public.three_day_topics p
                        where p.id = c.three_day_topic_id))),
    ((select count(*) from public.three_day_topic_articles c
      where not exists (select 1 from public.articles p where p.id = c.article_id))),
    ((select count(*) from public.weekly_topics c
      where not exists (select 1 from public.weekly_topic_runs p where p.id = c.run_id))),
    ((select count(*) from public.weekly_topic_articles c
      where not exists (select 1 from public.weekly_topics p
                        where p.id = c.weekly_topic_id))),
    ((select count(*) from public.weekly_topic_articles c
      where not exists (select 1 from public.articles p where p.id = c.article_id)))
)
select count(*) as checked_foreign_keys,
       sum(orphan_rows)::bigint as total_orphan_rows,
       sum(orphan_rows) = 0 as passed
from orphan_counts;

\echo 'UNIT05_CONSTRAINTS_AND_INDEXES'
select case con.contype
         when 'p' then 'primary_key'
         when 'f' then 'foreign_key'
         when 'u' then 'unique'
         when 'c' then 'check'
       end as constraint_type,
       count(*) as restored_count,
       count(*) filter (where not con.convalidated) as not_validated_count
from pg_constraint con
join pg_class c on c.oid = con.conrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and con.contype in ('p', 'f', 'u', 'c')
group by con.contype
order by constraint_type;

select count(*) as restored_index_count,
       count(*) filter (where not i.indisvalid) as invalid_index_count,
       count(*) filter (where not i.indisready) as not_ready_index_count,
       count(*) = 45
         and count(*) filter (where not i.indisvalid or not i.indisready) = 0
         as passed
from pg_index i
join pg_class c on c.oid = i.indrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public';

select c.relname as table_name,
       count(i.indexrelid) as index_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_index i on i.indrelid = c.oid
where n.nspname = 'public'
  and c.relkind in ('r', 'p')
group by c.relname
order by c.relname;

\echo 'UNIT05_SEQUENCES'
with sequence_state(table_name, sequence_name, source_last_value,
                    restored_last_value, max_id) as (
  values
    ('article_embeddings', 'article_embeddings_id_seq', 4042::bigint,
      (select last_value from public.article_embeddings_id_seq),
      (select max(id) from public.article_embeddings)),
    ('articles', 'articles_id_seq', 8872::bigint,
      (select last_value from public.articles_id_seq),
      (select max(id) from public.articles)),
    ('crawl_runs', 'crawl_runs_id_seq', 51::bigint,
      (select last_value from public.crawl_runs_id_seq),
      (select max(id) from public.crawl_runs)),
    ('extraction_runs', 'extraction_runs_id_seq', 154::bigint,
      (select last_value from public.extraction_runs_id_seq),
      (select max(id) from public.extraction_runs)),
    ('raw_articles', 'raw_articles_id_seq', 474::bigint,
      (select last_value from public.raw_articles_id_seq),
      (select max(id) from public.raw_articles)),
    ('sources', 'sources_id_seq', 10::bigint,
      (select last_value from public.sources_id_seq),
      (select max(id) from public.sources)),
    ('three_day_topic_articles', 'three_day_topic_articles_id_seq', 604::bigint,
      (select last_value from public.three_day_topic_articles_id_seq),
      (select max(id) from public.three_day_topic_articles)),
    ('three_day_topic_runs', 'three_day_topic_runs_id_seq', 27::bigint,
      (select last_value from public.three_day_topic_runs_id_seq),
      (select max(id) from public.three_day_topic_runs)),
    ('three_day_topics', 'three_day_topics_id_seq', 123::bigint,
      (select last_value from public.three_day_topics_id_seq),
      (select max(id) from public.three_day_topics)),
    ('topic_articles', 'topic_articles_id_seq', 305::bigint,
      (select last_value from public.topic_articles_id_seq),
      (select max(id) from public.topic_articles)),
    ('topics', 'topics_id_seq', 101::bigint,
      (select last_value from public.topics_id_seq),
      (select max(id) from public.topics)),
    ('weekly_topic_articles', 'weekly_topic_articles_id_seq', 145::bigint,
      (select last_value from public.weekly_topic_articles_id_seq),
      (select max(id) from public.weekly_topic_articles)),
    ('weekly_topic_runs', 'weekly_topic_runs_id_seq', 6::bigint,
      (select last_value from public.weekly_topic_runs_id_seq),
      (select max(id) from public.weekly_topic_runs)),
    ('weekly_topics', 'weekly_topics_id_seq', 23::bigint,
      (select last_value from public.weekly_topics_id_seq),
      (select max(id) from public.weekly_topics))
)
select table_name,
       sequence_name,
       source_last_value,
       restored_last_value,
       max_id,
       restored_last_value = source_last_value as source_matches,
       restored_last_value >= coalesce(max_id, restored_last_value) as covers_max_id
from sequence_state
order by table_name;

\echo 'UNIT05_VECTOR'
select e.extversion as vector_version,
       n.nspname as extension_schema,
       e.extversion = '0.8.0' and n.nspname = 'extensions' as passed
from pg_extension e
join pg_namespace n on n.oid = e.extnamespace
where e.extname = 'vector';

select format_type(a.atttypid, a.atttypmod) as embedding_type,
       count(*) as embedding_rows,
       count(*) filter (where ae.dimension <> 1536) as invalid_dimension_column_rows,
       count(*) filter (where extensions.vector_dims(ae.embedding) <> 1536) as invalid_vector_rows,
       format_type(a.atttypid, a.atttypmod) = 'extensions.vector(1536)'
         and count(*) filter (where ae.dimension <> 1536) = 0
         and count(*) filter (where extensions.vector_dims(ae.embedding) <> 1536) = 0
         as passed
from pg_attribute a
join pg_class c on c.oid = a.attrelid
join pg_namespace n on n.oid = c.relnamespace
cross join public.article_embeddings ae
where n.nspname = 'public'
  and c.relname = 'article_embeddings'
  and a.attname = 'embedding'
  and not a.attisdropped
group by a.atttypid, a.atttypmod;

\echo 'UNIT05_REPRESENTATIVE_QUERY_1_SOURCE_AND_ARTICLE_TOTALS'
select (select count(*) from public.sources where enabled) as active_source_count,
       (select count(*) from public.articles) as article_count;

\echo 'UNIT05_REPRESENTATIVE_QUERY_2_ARTICLES_PER_SOURCE'
select s.id as source_id,
       count(a.id) as article_count,
       max(a.published_at) as latest_published_at
from public.sources s
left join public.articles a on a.source_id = s.id
group by s.id
order by s.id;

\echo 'UNIT05_REPRESENTATIVE_QUERY_3_EXTRACTION_STATUS'
select extraction_status, count(*) as row_count
from public.raw_articles
group by extraction_status
order by extraction_status;

\echo 'UNIT05_REPRESENTATIVE_QUERY_4_TOPIC_AND_LINK_COUNTS'
select topic_kind, topic_count, linked_article_count
from (
  select 'daily'::text as topic_kind,
         (select count(*) from public.topics) as topic_count,
         (select count(*) from public.topic_articles) as linked_article_count
  union all
  select 'three_day',
         (select count(*) from public.three_day_topics),
         (select count(*) from public.three_day_topic_articles)
  union all
  select 'weekly',
         (select count(*) from public.weekly_topics),
         (select count(*) from public.weekly_topic_articles)
) counts
order by topic_kind;

\echo 'UNIT05_REPRESENTATIVE_QUERY_5_EMBEDDING_COVERAGE'
select provider,
       model,
       dimension,
       count(*) as embedding_count,
       count(distinct article_id) as embedded_article_count,
       (select count(*) from public.articles) as total_article_count
from public.article_embeddings
group by provider, model, dimension
order by provider, model, dimension;

rollback;
SQL
```

완료 판정은 다음을 모두 만족해야 한다.

- 14개 table의 source/Restore row count와 전체 12,330건이 모두 일치한다.
- catalog의 primary key 14개, foreign key 11개, unique 11개, check 47개가
  모두 validated 상태이고, 11개 FK의 orphan 합계가 0건이다.
- `public` index가 45개이고 invalid 또는 not-ready index가 0개다.
- 14개 sequence의 Restore `last_value`가 source baseline과 일치하고 각 table의
  `MAX(id)`보다 작지 않다. Sequence와 row count의 단순 일치는 요구하지 않는다.
- `vector` 0.8.0이 `extensions` schema에 있고 embedding type, 선언 dimension과
  실제 vector dimension이 모두 1536이다.
- 대표 query 5개가 오류 없이 실행되고 기사 본문, summary, URL과 embedding 값을
  출력하지 않는다.

Operator가 Verification에 제공할 sanitized evidence는 각 section의 aggregate
숫자, boolean 결과와 상태값으로 제한한다. 전체 query output, source name,
article timestamp, provider/model 값은 raw evidence에만 두고 Repository 문서나
chat에 복사하지 않는다. 하나라도 불일치하거나 query가 non-zero로 종료되면
UNIT-05를 완료하지 않고 container·volume과 artifact를 유지한 채 원인과 실패
section만 기록한다. Restore를 덮어쓰거나 Production에서 보정 query를 실행하지
않는다.

## Implementation Units

- [x] UNIT-01: Repository 구조, `pg_dump` client/server major, 연결 경로와 schema baseline 조사
- [x] UNIT-02: Backup 대상·format·credential·artifact 경계와 Restore 설계 확정
- [x] UNIT-03: 사람이 Production logical Backup 생성 및 checksum·archive 무결성 검증
- [x] UNIT-04: 사람이 Local pgvector Restore 환경 구성 및 `--exit-on-error` Restore 수행
- [x] UNIT-05: Row count·FK·index·sequence·vector와 대표 query 정합성 검증
- [x] UNIT-06: Verification·Runbook 최소 문서화와 임시 환경 최종 정리
