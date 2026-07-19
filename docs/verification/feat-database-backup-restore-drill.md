# Verification: Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## Verification Status

passed

## Verification Scope

- UNIT-01의 Repository 구조, DB 연결 설정 주입 경로, migration 기반 schema 기대값,
  로컬 PostgreSQL client 가용성과 artifact Git 경계를 조사했다.
- UNIT-02의 `public` custom archive 대상, Production credential 주입,
  Repository 밖 artifact 수명, PostgreSQL 17·pgvector 0.8.0 격리 Restore
  순서와 중단 조건을 확정했다.
- Repository 정적 조사는 Agent가 수행했다.
- Production SQL Editor 조회와 PostgreSQL 17 Docker client 연결 테스트는 사람이
  직접 수행했다. Agent는 제공된 sanitized evidence만 문서에 반영했다.
- UNIT-03 Production logical Backup과 archive 무결성 검증도 사람이 직접
  수행했다. Agent는 제공된 sanitized evidence만 기록했다.
- UNIT-04 Local PostgreSQL 17·pgvector 격리 Restore도 사람이 직접 수행했다.
  Agent는 제공된 sanitized evidence만 기록했다.
- UNIT-05 Local Restore 정합성 검증을 사람이 직접 수행했다. 모든 SQL은 Local
  Restore DB의 read-only transaction과 explicit rollback 경계에서 실행됐다.
- UNIT-06의 반복 가능한 Backup·Restore·검증·cleanup 절차를 전용 Runbook에
  문서화하고 Runbook index에 연결했다.
- UNIT-06 human-controlled cleanup을 사람이 직접 수행해 임시 Restore environment,
  local credential과 Restore log를 제거했다.
- Backup과 checksum은 검증된 artifact로 Repository 밖에 보존한다.
- Agent는 사람이 제공한 sanitized evidence만 기록했다.
- Agent는 Production DB 연결·query, Backup, Restore, Docker resource 작업과
  Local DB query, filesystem cleanup, Backup·checksum·password file·Restore log
  접근을 수행하지 않았다.

## Commands Run

### Branch와 working tree

Command:

```bash
git branch --show-current
git status --short
```

Result:

- Branch: `feat/database-backup-restore-drill`
- 기존 수정/미추적 문서가 있음을 확인했다. UNIT-01에서는 Task와 Verification
  두 문서만 수정 대상으로 삼았다.

Status: passed

### Repository 연결 및 schema 계약 조사

Command:

```bash
rg -l 'DATABASE_URL' app scripts k8s --glob '*.py' --glob '*.yaml' | sort
rg -n -i \
  '^(create|alter)[[:space:]]+(table|view|materialized view|sequence|index)|add constraint|references|create extension|vector\(' \
  db/migrations/*.sql
```

Result:

- `app/database.py`와 DB 접근 script가 `DATABASE_URL`을 사용한다.
- K3s manifest는 `news-api-secret`의 `DATABASE_URL` key를 API와 네 개 scheduled
  workload에 같은 이름으로 주입한다.
- Repository migration은 12개 application table과 관련 constraint/index를
  정의한다. Architecture가 기록한 초기 `sources`, `articles`를 합치면 기대
  application table은 14개다.
- `vector`는 `extensions` schema에 생성되고 embedding column은
  `vector(1536)`으로 선언되어 있다.
- Secret 값, `.env`와 connection string은 조회하지 않았다.

Status: passed

### Local PostgreSQL client 확인

Command:

```bash
command -v pg_dump && pg_dump --version
command -v psql && psql --version
command -v pg_restore && pg_restore --version
```

Result:

- 세 executable 모두 현재 Agent 환경의 `PATH`에서 발견되지 않았다.
- 따라서 client major 확인과 Production server major 비교는 수행할 수 없다.

Status: failed

Notes:

- 이 실패 시점에는 호환 client를 준비한 사람의 재검증이 필요했다.
- 아래 human-operated 검증에서 Docker client/server major 호환성을 확인해 현재
  상태는 passed다.

### Human-operated PostgreSQL client와 Production baseline 검증

사람이 수행한 Production read-only 조사와 local Docker 연결 검증의 sanitized
결과를 기록한다. 실제 host, user, project reference, password와 connection
string은 제공받거나 기록하지 않았다.

Result:

- Production server: PostgreSQL 17.6, major 17, database `postgres`
- Docker image: `postgres:17`
- Docker client: `pg_dump` 17.10, `psql` 17.10, `pg_restore` 17.10
- Client/server major compatibility: passed
- `Direct connection / 5432`: failed
  - local Docker 환경에서 Direct endpoint를 주소로 해석할 수 없었다.
- `Shared Pooler session mode / 5432`: connection test passed
  - server 17.6과 database `postgres`를 확인했다.
- `Transaction Pooler / 6543`: not used

Schema와 extension baseline:

- 존재 schema: `public`, `extensions`
- `supabase_migrations`: schema 자체가 존재하지 않음
- `pgvector`: 0.8.0, extension schema `extensions`
- embedding column: `public.article_embeddings.embedding`, `vector(1536)`

Backup 범위 결정:

- 포함: `public` schema의 table, data, sequence, constraint와 index
- 제외: `extensions` schema 전체, Supabase 관리 schema,
  존재하지 않는 `supabase_migrations`, owner와 ACL
- Restore 사전 조건: PostgreSQL major 17, `extensions` schema, `pgvector` 0.8.0,
  `public` schema Restore 전 vector extension 준비

Production object baseline:

- Application tables: 14
- Sequences: 14
- Indexes: 45
- Constraints: 83
  - Primary key: 14
  - Foreign key: 11
  - Unique: 11
  - Check: 47
- 모든 14개 application table에 primary key가 존재한다.

Source row count baseline:

| table | source_rows |
| --- | ---: |
| article_embeddings | 4042 |
| articles | 6372 |
| crawl_runs | 51 |
| extraction_runs | 154 |
| raw_articles | 469 |
| sources | 10 |
| three_day_topic_articles | 604 |
| three_day_topic_runs | 27 |
| three_day_topics | 123 |
| topic_articles | 268 |
| topics | 87 |
| weekly_topic_articles | 102 |
| weekly_topic_runs | 6 |
| weekly_topics | 15 |

Total source rows: 12330

Sequence baseline:

| sequence | last_value |
| --- | ---: |
| article_embeddings_id_seq | 4042 |
| articles_id_seq | 8872 |
| crawl_runs_id_seq | 51 |
| extraction_runs_id_seq | 154 |
| raw_articles_id_seq | 474 |
| sources_id_seq | 10 |
| three_day_topic_articles_id_seq | 604 |
| three_day_topic_runs_id_seq | 27 |
| three_day_topics_id_seq | 123 |
| topic_articles_id_seq | 305 |
| topics_id_seq | 101 |
| weekly_topic_articles_id_seq | 145 |
| weekly_topic_runs_id_seq | 6 |
| weekly_topics_id_seq | 23 |

향후 Restore sequence 검증 기준:

- Production과 Restore의 sequence `last_value`를 비교한다.
- Restore sequence `last_value`가 Restore table `MAX(id)`보다 작지 않은지
  확인한다.
- sequence `last_value`와 row count 일치는 완료 조건으로 사용하지 않는다.
  삭제된 row 또는 실패·rollback된 INSERT로 sequence gap이 생길 수 있다.

Status: passed

Notes:

- Host PATH에서 PostgreSQL client를 찾지 못한 과거 실패는 그대로 유지한다.
  PostgreSQL 17 Docker client를 대안으로 검증해 UNIT-01 blocker를 해소했다.
- Production server/catalog baseline, source row count, constraint/index/sequence와
  Backup connection path baseline은 모두 passed다.
- 실제 logical Backup과 Restore는 수행하지 않았다.

### Backup artifact Git 경계 조사

Command:

```bash
sed -n '1,240p' .gitignore
git check-ignore -v drill.backup drill.dump drill.backup.sha256
```

Result:

- `.env`, virtual environment와 Agent 실행 log 등은 제외된다.
- `*.backup`, `*.dump`와 checksum은 ignore pattern에 포함되지 않는다.
- `git check-ignore`는 세 가상 경로 모두 match하지 않아 exit 1을 반환했다.
- Task의 통제는 archive와 파생 artifact를 Repository 밖에만 생성하는 것이다.

Status: passed

### Repository test

Command:

```bash
PYTHONPATH=. pytest -q
```

Result:

- `445 passed, 91 subtests passed in 15.80s`

Status: passed

### Workflow 문서 상태 검사

Command:

```bash
scripts/agent_next_step.sh status
```

Result:

- 첫 실행은 UNIT 아래의 중첩 checkbox를 별도 UNIT 형식으로 해석해
  `Task 파싱 오류`로 실패했다.
- 중첩 checkbox를 UNIT-01 세부 상태 표로 변경한 뒤 재실행은 exit 0이었다.
- 재실행 결과 current unit은 UNIT-01, completed unit은 0, pending unit은 6,
  Verification은 `pending`으로 표시됐다.

Status: passed

Notes:

- 실패 원인에 맞춰 Task 형식만 수정했으며 UNIT-01 완료 상태는 변경하지 않았다.

### UNIT-01 완료 후 workflow 상태 검사

Command:

```bash
scripts/agent_next_step.sh status
```

Result:

- Current unit: UNIT-02
- Completed units: 1
- Pending units: 5
- Verification: `pending`

Status: passed

Notes:

- Parser가 UNIT-01만 완료하고 UNIT-02~06을 pending으로 인식한다.
- 상태 확인만 수행했으며 UNIT-02 작업은 시작하지 않았다.

### 문서 정적 검사와 민감정보 pattern 검사

Command:

```bash
git diff --check
task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"
rg -l \
  '(postgres(ql)?://[^[:space:]]+|password[=:][^[:space:]]+|SUPABASE_DB_PASSWORD)' \
  docs scripts . \
  --glob '!*.backup' \
  --glob '!*.dump' || true
```

Result:

- Tracked diff와 두 untracked 대상 문서에서 whitespace 오류가 없었다.
- Repository 전체 pattern 검사는 기존 문서들과 현재 Task 파일명을 반환했다.
  출력은 파일명으로 제한했다.
- 현재 Task/Verification만 대상으로 재확인했을 때 Task의 검사 command에 적힌
  `SUPABASE_DB_PASSWORD` pattern 한 곳만 탐지됐고 실제 credential 값은 없었다.

Status: passed

### UNIT-01 evidence 반영 후 최종 문서 검사

Command:

```bash
git diff --check
git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md
git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md
git status --short

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
rg -n "$uri_pattern|$authority_pattern|$key_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md
```

Result:

- `git diff --check`: exit 0, 출력 없음
- 두 `git diff --no-index --check`: 각 exit 1, 출력 없음
  - `/dev/null`과 새 문서의 내용 차이 때문에 exit 1이며 whitespace 진단은 없다.
- `git status --short`: 문서 파일만 표시되고 application code, DB schema,
  migration과 dependency 변경은 없다.
- Sensitive value pattern: 출력 없음
- 첫 재검사는 문서에 기록된 검사 pattern 자체를 self-match했다. Pattern 조각을
  변수로 분리한 뒤 재실행해 실제 value pattern이 없음을 확인했다.
- 작업 시작 전에 존재한 다른 문서 변경과 미추적 파일은 수정하지 않았다.

Status: passed

Notes:

- 이번 갱신은 Task와 Verification 두 문서로 제한했다.
- pytest는 application code 변경이 없어 다시 실행하지 않았다. 기존
  `445 passed, 91 subtests passed in 15.80s` evidence만 유지한다.

### UNIT-02 Repository·database 설계 입력 조사

Command:

```bash
sed -n '1,280p' docs/runbooks/database-check.md
sed -n '1,280p' docs/architecture/database.md
sed -n '1,220p' db/migrations/006_create_article_embeddings.sql
rg -n \
  'pg_dump|pg_restore|pgvector/pgvector|PGSERVICE|PGPASSFILE|backup|restore' \
  docs scripts .gitignore \
  --glob '!docs/tasks/feat-database-backup-restore-drill.md' \
  --glob '!docs/verification/feat-database-backup-restore-drill.md'
```

Result:

- Database architecture와 runbook은 credential 값 기록 금지, migration
  human-control과 `vector(1536)` 중단 기준을 재확인했다.
- Migration은 `vector` extension을 `extensions` schema에 생성하고
  `article_embeddings.embedding` type을 `vector(1536)`으로 정의한다.
- 기존 database runbook에는 이 drill의 logical Backup/Restore 절차가 없다.
  UNIT-02는 Task에 설계만 기록했고 UNIT-06 Runbook 범위를 미리
  구현하지 않았다.

Status: passed

### UNIT-02 공식 문서 조사

Command:

```text
PostgreSQL 17 pg_dump, pg_restore, pg_service.conf, pgpass 공식 문서와
pgvector v0.8.0·versioned PostgreSQL 17 Docker tag를 read-only로 조회
```

Result:

- `--schema=public`은 해당 schema와 내부 object를 선택하지만 다른
  schema의 의존 object를 자동 포함하지 않음을 확인했다.
- Custom archive에서 `--no-owner`는 Restore 시점에 반복해야 실질적으로
  owner 적용을 막으며 `--no-acl`은 grant/revoke를 제외함을 확인했다.
- `pg_restore --exit-on-error`는 기본 continue-on-error를 대신해 첫 SQL
  error에서 종료하고 `--single-transaction`은 전체 Restore의 성공·rollback
  경계를 제공함을 확인했다.
- `PGSERVICEFILE`, `PGSERVICE`과 `PGPASSFILE`로 connection 설정과 password를
  CLI argument·connection URI에서 분리할 수 있음을 확인했다.
- `pgvector/pgvector:0.8.0-pg17` versioned tag가 PostgreSQL 17과
  pgvector 0.8.0 조합으로 존재함을 확인했다.

Status: passed

Notes:

- 조회한 공식 출처 link는 Task의 UNIT-02 설계 끝에 기록했다.
- Image pull·inspect는 UNIT-04 human operation으로 남겨두었고, 이 UNIT에서
  local Docker resource를 생성하지 않았다.

### UNIT-02 workflow 상태와 문서 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git diff --name-only
git status --short
task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
if rg -n "$uri_pattern|$authority_pattern|$key_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Workflow parser: UNIT-01·02 완료, UNIT-03 current, UNIT-03~06 pending,
  Verification `pending`
- `git diff --check`: exit 0, 출력 없음
- Tracked diff는 작업 시작 전부터 있던 `docs/tasks/main.md`만
  표시했고, `git status --short`는 Task·Verification을 포함한 기존
  문서 수정·미추적 상태만 표시했다. Application code, migration,
  manifest와 dependency 변경은 없었다.
- 두 untracked 문서의 `git diff --no-index --check`: 내용 차이 exit 1,
  whitespace 진단 없음
- Sensitive value pattern: match 없음

Status: passed

Notes:

- Parser가 UNIT-02만 추가로 완료했고 후속 UNIT은 pending으로 인식한다.
- UNIT-03은 parser의 다음 대상일 뿐 실제 Backup을 시작하지 않았다.
- Application code, DB migration, manifest와 dependency 변경이 없어 pytest는
  UNIT-02에서 재실행하지 않았다.

### UNIT-03 Production logical Backup 및 archive 검증

Status: passed

- Operator: human
- Connection: Shared Pooler session mode / 5432
- PostgreSQL client: 17.10
- Production server: 17.6
- Backup schema: `public`
- Format: custom archive
- Owner and ACL: excluded
- `pg_dump`: passed
- Duration: 27 seconds
- Archive:
  `~/backups/newslab/newslab-public-20260719-014233.backup`
- Size: 28,679,777 bytes
- Non-empty archive: passed
- SHA-256 generation: passed
- Initial SHA-256 verification: passed
- Permission 변경 후 SHA-256 verification: passed
- Checksum file:
  `newslab-public-20260719-014233.backup.sha256`
- 실제 SHA-256 hash value: not recorded
- `pg_restore --list`: passed
- Non-empty archive list: passed
- Table definitions: 14
- Table data entries: 14
- Sequence definitions: 14
- Sequence value entries: 14
- Expected public tables: all 14 present
- Missing expected tables: none
- `extensions` schema objects: not included
- Temporary `pg_service.conf`: removed
- Temporary `pgpass`: removed
- Temporary archive list: removed
- `/tmp/newslab-backup.*` temporary directory: none remaining
- Backup permission: 600 (`-rw-------`)
- Checksum permission: 600 (`-rw-------`)
- Backup and checksum retained outside Repository for UNIT-04 and UNIT-05

Execution summary:

- PostgreSQL 17 Docker client로 Session Pooler 연결을 확인한 뒤 `public` schema를
  owner·ACL 없이 custom archive로 생성했다.
- Non-empty 검사, SHA-256 생성·검증과 `pg_restore --list`를 수행했다.
- Archive의 table definition·data와 sequence definition·value를 각각 14개로
  확인하고 예상 public table 전체 존재 및 `extensions` schema 제외를 확인했다.
- 임시 credential과 archive list를 정리하고 두 보존 artifact에 permission 600을
  적용한 뒤 checksum을 다시 검증했다.

Notes:

- Backup은 Production read-only logical dump였고 Production schema·data를
  변경하지 않았다.
- `vector` extension은 archive에 포함하지 않았으며 UNIT-04 Restore 전에 별도로
  준비하는 UNIT-02 설계를 유지한다.
- Agent는 Backup command를 재실행하거나 archive·checksum 내용을 읽지 않았다.
- Restore는 수행하지 않았다.

### UNIT-03 workflow 상태와 문서 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git diff --name-only
git status --short

task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
if rg -n "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Workflow parser: UNIT-01~03 완료, UNIT-04 current, completed 3,
  pending 3, Verification `pending`
- `git diff --check`: exit 0, 출력 없음
- `git diff --stat`과 `git diff --name-only`: 작업 시작 전부터 있던 tracked
  `docs/tasks/main.md`만 표시
- `git status --short`: Task·Verification을 포함한 기존 문서 수정·미추적 상태만
  표시하고 application code, migration, manifest와 dependency 변경 없음
- 두 untracked 대상 문서 whitespace check: passed
- Sensitive value and SHA-256 hash pattern: match 없음

Status: passed

Notes:

- Task와 Verification 두 문서만 수정했고 기존 다른 문서 변경은 보존했다.
- Application code 변경이 없어 pytest는 재실행하지 않았다. 기존
  `445 passed, 91 subtests passed in 15.80s` evidence만 유지한다.
- UNIT-04 Restore와 Backup·checksum artifact 접근은 수행하지 않았다.

### UNIT-04 Local PostgreSQL 17·pgvector 격리 Restore

Status: passed

- Operator: human
- Backup checksum preflight: passed
- Backup archive:
  `~/backups/newslab/newslab-public-20260719-014233.backup`
- Existing container·volume name conflict: none
- Local port 55432 listener conflict: none
- Restore image: `pgvector/pgvector:0.8.0-pg17`
- Image pull: passed
- PostgreSQL: 17.6
- Restore container logical name: `newslab-restore-drill`
- Restore volume logical name: `newslab-restore-drill-data`
- Restore database: `newslab_restore`
- Network binding: loopback only
- Host binding: `127.0.0.1:55432`
- Container database port: 5432
- Container readiness: passed on first attempt
- Container restart count after Restore: 0
- Container status after Restore: running
- Local password: randomly generated and not recorded
- Local password file: Repository 밖에 유지, permission 600
- Pre-Restore database creation: passed
- Pre-Restore default `public` schema removal: passed
- Pre-Restore `public` schema count: 0
- `extensions` schema preparation: passed
- pgvector:
  - version: 0.8.0
  - schema: `extensions`
- `pg_restore` options:
  - `--no-owner`
  - `--no-acl`
  - `--exit-on-error`
  - `--single-transaction`
  - `--verbose`
- `pg_restore` status: passed
- Restore duration output: 0 seconds
  - zsh `SECONDS`의 정수 초 측정에서 1초 미만일 수 있다.
  - Duration 확인을 위해 Restore를 재실행하지 않았다.
- Restore log error scan: passed
  - error, fatal, panic pattern 없음
- Restored public base tables: 14
- Restored public sequences: 14
- Embedding type: `extensions.vector(1536)`
- Container and volume retained for UNIT-05
- Backup, checksum, local password file and Restore log retained for UNIT-05

Result interpretation:

- PostgreSQL 17.6과 pgvector 0.8.0의 격리 환경에서 Production과 분리된
  `newslab_restore` database를 준비했다.
- Archive가 `public` schema를 생성하므로 Restore 전에 기본 `public`을 제거하고
  `extensions.vector`를 먼저 준비했다.
- `--exit-on-error --single-transaction` 경계에서 Restore가 성공했고 log error
  scan, table·sequence 개수, pgvector와 embedding type 확인이 모두 통과했다.
- Production의 `vector(1536)`과 Local Restore의 `extensions.vector(1536)`은 같은
  pgvector type이며 Local 출력이 extension schema를 명시한 것이다.
- Duration 0초는 정수 초 측정 결과이며 성공 evidence와 모순되지 않는다.

Notes:

- Image digest, container ID, local password, password file 내용, checksum hash와
  Restore log 내용은 기록하지 않았다.
- Agent는 Docker 명령, Restore, Local DB query와 artifact 접근을 수행하지 않았다.
- UNIT-05를 위해 container, volume, database와 필요한 artifact를 그대로 유지한다.
- Cleanup은 수행하지 않았다.

### UNIT-04 workflow 상태와 문서 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git diff --name-only
git status --short

task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
container_id_pattern='[0-9a-f]{''64}'
if rg -n \
  "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern|$container_id_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Workflow parser: UNIT-01~04 완료, UNIT-05 current, completed 4,
  pending 2, Verification `pending`
- `git diff --check`: exit 0, 출력 없음
- `git diff --stat`과 `git diff --name-only`: 작업 시작 전부터 있던 tracked
  `docs/tasks/main.md`만 표시
- `git status --short`: Task·Verification을 포함한 기존 문서 수정·미추적 상태만
  표시하고 application code, migration, manifest와 dependency 변경 없음
- 두 untracked 대상 문서 whitespace check: passed
- Sensitive value, checksum hash and container ID pattern: match 없음

Status: passed

Notes:

- Task와 Verification 두 문서만 수정했고 기존 다른 문서 변경은 보존했다.
- Application code 변경이 없어 pytest는 재실행하지 않았다. 기존
  `445 passed, 91 subtests passed in 15.80s` evidence만 유지한다.
- UNIT-05 query와 UNIT-06 cleanup은 수행하지 않았다.

### UNIT-05 정합성 검증 설계 조사

Command:

```bash
rg -n "UNIT-05|Acceptance criteria|대표|orphan|sequence|vector|row count|검증 SQL|Local Restore" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md
rg -n -i "references|create extension|vector\\(" db/migrations/*.sql
sed -n '1,220p' docs/architecture/database.md
```

Result:

- UNIT-01에서 source row count 14개, constraint 유형별 개수, index 45개,
  sequence 14개의 `last_value`, pgvector 0.8.0과 `vector(1536)` baseline을 이미
  확보했음을 확인했다.
- Migration과 Database architecture에서 11개 foreign key 관계를 확인했다.
  `sources`와 `articles`의 초기 schema는 Repository 밖에서 시작했으므로
  `articles.source_id → sources.id` 관계는 UNIT-01 Production catalog baseline을
  기준으로 포함했다.
- 대표 query에 필요한 `sources.enabled`, `articles.source_id`·`published_at`,
  `raw_articles.extraction_status`, 세 Topic 계열과 embedding metadata column의
  사용 계약을 확인했다.
- Task에 Local Restore 전용 read-only transaction으로 row count, FK orphan,
  constraint/index, sequence, vector와 대표 query 5개를 검증하는 human-controlled
  절차와 중단 기준을 추가했다.
- 기사 본문, summary, URL, embedding 값과 credential을 출력하는 query는 포함하지
  않았다.

Status: passed

Notes:

- Agent는 Docker command와 Local 또는 Production DB query를 실행하지 않았다.
- 실제 UNIT-05 정합성 결과가 아니며, 아래 human-operated 실행 evidence가
  제공되기 전에는 UNIT-05 checklist와 관련 Acceptance criteria를 완료 처리하지
  않는다.

### UNIT-05 검증 절차 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check

task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

rg -n \
  "UNIT05_|begin read only|rollback;|extensions\\.vector_dims|\\[ \\] UNIT-05" \
  docs/tasks/feat-database-backup-restore-drill.md

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
if rg -n \
  "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi

git diff --stat
git diff --name-only
git status --short
```

Result:

- Workflow parser는 UNIT-05를 current로, completed unit 4개와 pending unit 2개,
  Verification `pending`으로 표시했다.
- Tracked diff와 두 untracked 대상 문서의 whitespace 검사는 모두 통과했다.
- UNIT-05 SQL에 read-only transaction 시작, 7개 section marker, 명시적 rollback,
  schema-qualified `extensions.vector_dims`와 미완료 UNIT-05 checklist가 있음을
  확인했다.
- 대상 문서에서 connection URI, 5432 authority, private key와 64자리 hash pattern
  match가 없었다.
- `git diff --stat`과 `git diff --name-only`에는 작업 시작 전부터 수정된 tracked
  `docs/tasks/main.md`만 표시됐다. `git status --short`에는 Task·Verification을
  포함한 기존 untracked 문서가 표시됐고 application code, migration, manifest와
  dependency 변경은 없었다.

Status: passed

Notes:

- PostgreSQL client가 Agent 환경에 없고 Local DB query가 금지돼 SQL 실행 검증은
  사람이 수행해야 한다.
- UNIT-05 checklist는 실제 Local Restore query evidence가 없으므로 미완료다.

### UNIT-05 Local Restore 정합성 검증

Status: passed

- Operator: human
- Target container: `newslab-restore-drill`
- Target database: `newslab_restore`
- Query mode: read-only transaction, explicit rollback
- Production connection: not used
- Container status: running
- Network binding: loopback only, `127.0.0.1:55432 -> 5432`
- Container restart count: 0
- Local database access: passed

Row count:

| table | expected | actual | match |
| --- | ---: | ---: | --- |
| article_embeddings | 4042 | 4042 | passed |
| articles | 6372 | 6372 | passed |
| crawl_runs | 51 | 51 | passed |
| extraction_runs | 154 | 154 | passed |
| raw_articles | 469 | 469 | passed |
| sources | 10 | 10 | passed |
| three_day_topic_articles | 604 | 604 | passed |
| three_day_topic_runs | 27 | 27 | passed |
| three_day_topics | 123 | 123 | passed |
| topic_articles | 268 | 268 | passed |
| topics | 87 | 87 | passed |
| weekly_topic_articles | 102 | 102 | passed |
| weekly_topic_runs | 6 | 6 | passed |
| weekly_topics | 15 | 15 | passed |

- Expected total rows: 12330
- Actual total rows: 12330
- All 14 table row counts: passed

Object and constraint count:

| object | expected | actual | match |
| --- | ---: | ---: | --- |
| Public base tables | 14 | 14 | passed |
| Public sequences | 14 | 14 | passed |
| Public indexes | 45 | 45 | passed |
| Public constraints | 83 | 83 | passed |
| Primary key | 14 | 14 | passed |
| Foreign key | 11 | 11 | passed |
| Unique | 11 | 11 | passed |
| Check | 47 | 47 | passed |

Sequence:

- 14개 모두 Production expected `last_value`와 일치했다.
- 14개 모두 Restore `last_value >= MAX(id)`를 충족했다.
- Missing sequence, expected mismatch와 MAX(id) 미포함 sequence: 없음
- `articles_id_seq`: expected/restored 8872, table `MAX(id)` 8863
  - 이 gap은 정상이며 삭제 또는 실패·rollback된 INSERT로 발생할 수 있다.
  - Sequence `last_value`와 row count 일치는 완료 조건이 아니다.

Foreign key:

- Public foreign key relation 11개를 검사했다.
- 모든 relation의 orphan count: 0
- Total orphan rows: 0
- Foreign key orphan verification: passed

pgvector:

- Extension: `vector` 0.8.0
- Extension schema: `extensions`
- Embedding column: `public.article_embeddings.embedding`
- Embedding type: `extensions.vector(1536)`
- Nullable: `NO`
- NULL embedding rows: 0
- Non-NULL dimension mismatch rows: 0
- Production의 `vector(1536)`과 schema-qualified Local type은 같은 pgvector
  type이다.

Representative read-only queries:

| query | joined_rows | parent_rows | result |
| --- | ---: | ---: | --- |
| sources_to_articles | 6372 | 10 | passed |
| articles_to_raw_articles | 469 | 469 | passed |
| articles_to_embeddings | 4042 | 4042 | passed |
| topics_to_articles | 268 | 87 | passed |
| three_day_topics_to_articles | 604 | 123 | passed |
| weekly_topics_to_articles | 102 | 15 | passed |

- Expected/actual joined row counts: all matched
- Representative read-only query verification: 6 passed

Final Local Restore state:

- Container remains running with loopback-only binding and restart count 0.
- Container, volume, Restore DB, Backup, checksum, local password file and Restore log
  remain unchanged for UNIT-06.
- Production DB connection and Local Restore resource changes: none

Notes:

- 기사 본문, summary, URL과 embedding value는 출력하거나 기록하지 않았다.
- Local password, password file 내용, connection URI, checksum hash, image digest,
  container ID와 Restore log 내용은 기록하지 않았다.
- Agent는 Docker, Local DB와 보존 artifact에 접근하지 않았다.
- UNIT-06 cleanup은 수행하지 않았다.

### UNIT-05 workflow 상태와 문서 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git diff --name-only
git status --short

task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
container_id_pattern='[0-9a-f]{''64}'
if rg -n \
  "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern|$container_id_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Workflow parser: UNIT-01~05 완료, UNIT-06 current, completed 5,
  pending 1, Verification `pending`
- `git diff --check`: exit 0, 출력 없음
- `git diff --stat`과 `git diff --name-only`: 작업 시작 전부터 있던 tracked
  `docs/tasks/main.md`만 표시
- `git status --short`: Task·Verification을 포함한 기존 문서 수정·미추적 상태만
  표시하고 application code, migration, manifest와 dependency 변경 없음
- 두 untracked 대상 문서 whitespace check: passed
- Sensitive value, checksum hash and container ID pattern: match 없음

Status: passed

Notes:

- Task와 Verification 두 문서만 수정했고 기존 다른 문서 변경은 보존했다.
- Application code 변경이 없어 pytest는 재실행하지 않았다. 기존
  `445 passed, 91 subtests passed in 15.80s` evidence만 유지한다.
- UNIT-06 문서화와 cleanup은 수행하지 않았다.

### UNIT-06 Runbook 문서화와 Repository 검증

Command:

```bash
PYTHONPATH=. pytest -q

scripts/agent_next_step.sh status

test -f docs/runbooks/database-backup-restore.md
rg -nF \
  '[Database logical Backup과 격리 Restore 훈련](runbooks/database-backup-restore.md)' \
  docs/RUNBOOK.md
rg -nF \
  '[Runbook index로 돌아가기](../RUNBOOK.md)' \
  docs/runbooks/database-backup-restore.md

git diff --check
git diff --stat
git diff --name-only
git status --short

for document_path in \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md \
  docs/runbooks/database-backup-restore.md; do
  document_check_output=$(git diff --no-index --check /dev/null \
    "$document_path" 2>&1 || true)
  test -z "$document_check_output"
done

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
container_id_pattern='[0-9a-f]{''64}'
if rg -l \
  "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern|$container_id_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md \
  docs/RUNBOOK.md \
  docs/runbooks/database-backup-restore.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Repository test: `445 passed, 91 subtests passed in 15.29s`
- Workflow parser: UNIT-01~05 완료, UNIT-06 current, completed 5,
  pending 1, Verification `pending`
- 전용 Runbook file과 index→Runbook, Runbook→index 상대 link: passed
- `git diff --check`: exit 0, 출력 없음
- Tracked diff는 이번 UNIT의 `docs/RUNBOOK.md`와 작업 시작 전부터 있던
  `docs/tasks/main.md`만 표시했다.
- `git status --short`에서 새 Runbook·Task·Verification과 기존 미추적 workflow
  문서를 확인했다. Application code, migration, manifest와 dependency 변경은
  없다.
- 세 untracked 대상 문서 whitespace check: passed
- Sensitive value, checksum hash and container ID pattern: match 없음

Status: passed

Notes:

- 기존 `database-check`와 책임을 섞지 않고 Task가 허용한 전용 Runbook 한 개만
  추가했다.
- Runbook은 human-controlled Backup·Restore·cleanup 경계, 중단 조건, artifact
  최종 보존·삭제 선택과 sanitized evidence 항목을 기록한다.
- Agent는 Docker resource와 artifact를 조회하거나 삭제하지 않았다. 실제 cleanup
  evidence가 없어 UNIT-06과 전체 Verification은 아직 완료하지 않는다.

### UNIT-06 Human-controlled cleanup과 Backup 최종 상태

Status: passed

- Operator: human
- Cleanup 전 Restore container `newslab-restore-drill`: running
- Cleanup 전 binding: `127.0.0.1:55432 -> 5432`
- Cleanup 전 Restore volume `newslab-restore-drill-data`: present
- Cleanup 전 local password file and Restore log: present
- Restore container removal: passed
- Restore volume removal: passed
- Local Restore DB data removal: passed through volume removal
- Local password file removal: passed
- Restore log removal: passed
- Port 55432 listener removal: passed
- Empty Restore-only secret directory cleanup: attempted after file removal
- Production resource changes: none
- Other Local database changes: none

Cleanup 후 상태:

- `newslab-restore-drill` container: absent
- `newslab-restore-drill-data` volume: absent
- `newslab_restore` data: removed with dedicated volume
- Local Restore password file: absent
- Restore log: absent
- `127.0.0.1:55432` listener: absent

Backup final state:

- Backup: retained outside Repository
- Checksum: retained outside Repository
- Backup basename: `newslab-public-20260719-014233.backup`
- Checksum basename: `newslab-public-20260719-014233.backup.sha256`
- Final checksum verification: passed
- Backup permission: 600
- Checksum permission: 600
- Backup size: 28,679,777 bytes
- Actual checksum hash: not recorded
- macOS `-rw-------@`는 permission 600과 extended attribute 존재를 의미하며
  permission 문제로 판단하지 않는다.

Docker image:

- `pgvector/pgvector:0.8.0-pg17`: retained
- Reusable image는 Production data나 credential을 포함한 임시 volume이 아니므로
  제거를 UNIT-06 완료 조건으로 사용하지 않았다.

Notes:

- Runbook 문서화와 human-controlled cleanup이 모두 완료됐다.
- Backup과 checksum은 Restore drill을 통과한 검증 artifact로 Repository 밖에
  보존한다.
- Container ID, password, checksum hash와 Restore log 내용은 기록하지 않았다.
- Agent는 Docker command, filesystem cleanup, checksum 검증과 artifact 접근을
  수행하지 않았다.
- Cleanup 이후 Production DB 접속이나 변경은 없었다.

### UNIT-06 최종 workflow 상태와 문서 정적 검사

Command:

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git diff --name-only
git status --short

task_check_output=$(git diff --no-index --check /dev/null \
  docs/tasks/feat-database-backup-restore-drill.md 2>&1 || true)
verification_check_output=$(git diff --no-index --check /dev/null \
  docs/verification/feat-database-backup-restore-drill.md 2>&1 || true)
test -z "$task_check_output"
test -z "$verification_check_output"

uri_pattern='postgres''(ql)?://'
key_pattern='-----BEGIN ''(RSA |OPENSSH |EC )?PRIVATE KEY-----'
authority_pattern='@[^[:space:]]+:''5432'
hash_pattern='[0-9a-fA-F]{''64}'
container_id_pattern='[0-9a-f]{''64}'
if rg -n \
  "$uri_pattern|$authority_pattern|$key_pattern|$hash_pattern|$container_id_pattern" \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md; then
  exit 1
else
  test "$?" -eq 1
fi
```

Result:

- Workflow parser: current unit none, completed 6, pending 0,
  Verification `passed`
- `git diff --check`: exit 0, 출력 없음
- `git diff --stat`과 `git diff --name-only`: 이미 UNIT-06에서 작성·검증된
  `docs/RUNBOOK.md`와 작업 시작 전부터 있던 `docs/tasks/main.md`만 표시
- `git status --short`: Runbook·Task·Verification을 포함한 기존 문서
  수정·미추적 상태만 표시하고 application code, migration, manifest와 dependency
  변경 없음
- 두 untracked 대상 문서 whitespace check: passed
- Sensitive value, checksum hash and container ID pattern: match 없음

Status: passed

Notes:

- 이번 cleanup evidence 반영은 Task와 Verification 두 문서로 제한했다.
- pytest는 재실행하지 않았으며 UNIT-06 Runbook 단계의 기존
  `445 passed, 91 subtests passed in 15.29s` 결과를 유지한다.
- Agent는 Docker, filesystem, DB와 보존 artifact에 접근하지 않았다.

## Results

- Repository에서 확인 가능한 연결 계약, application object 기대 목록, vector
  type/dimension 기대값과 artifact 경계를 Task의 UNIT-01 baseline에 기록했다.
- 사람이 제공한 sanitized evidence에서 Production catalog와 Repository 기대
  구조가 application table 14개 기준으로 일치함을 확인했다.
- `public`을 Backup 대상으로 확정했다. `extensions` schema 전체는 제외하고
  `pgvector` 0.8.0을 Restore 사전 조건으로 준비한다.
- `supabase_migrations`는 Production에 존재하지 않아 Backup에서 제외한다.
- PostgreSQL client/server major, Backup 연결 경로와 schema·object·row count·
  sequence baseline blocker가 모두 해소돼 UNIT-01은 passed다.
- UNIT-02에서 `public` custom archive, service·pass file credential 주입,
  Repository 밖 artifact 경계와 archive 수명을 확정했다.
- Restore는 `pgvector/pgvector:0.8.0-pg17`, loopback bind, local password
  file, `extensions.vector` 사전 생성, 빈 `public`, single-transaction·
  exit-on-error 순서로 확정했다.
- 사람이 Production `public` schema의 custom logical Backup을 성공적으로
  생성했고 non-empty archive와 SHA-256 무결성을 확인했다.
- Archive에는 public table definition·data와 sequence definition·value가 각각
  14개 존재하며 예상 table 누락과 `extensions` schema object 포함이 없다.
- 임시 credential·archive list를 정리하고 Backup·checksum permission 600 및
  permission 변경 후 checksum 재검증을 완료해 UNIT-03 blocker를 해소했다.
- Local PostgreSQL 17.6·pgvector 0.8.0 환경과 Production에서 분리된 Docker
  container·volume의 `newslab_restore` database 준비에 성공했다.
- Port는 `127.0.0.1:55432` loopback에만 bind하고 Restore 전에 기본 `public`을
  제거한 뒤 `extensions.vector`를 준비했다.
- `pg_restore --exit-on-error --single-transaction`과 log error scan이 통과했고
  public table 14개, sequence 14개 및 `extensions.vector(1536)`을 확인했다.
- Restore 후 container restart count는 0이고 running 상태를 유지해 UNIT-04
  blocker를 해소했다.
- Production baseline과 Restore의 14개 table row count 및 total 12330이 모두
  일치하고 public object·constraint 유형별 count도 일치했다.
- Sequence 14개의 expected value와 `last_value >= MAX(id)`가 통과했으며 foreign
  key 11개의 orphan count는 모두 0이다.
- pgvector version·schema·dimension·NULL 정책이 일치하고 대표 read-only 관계
  query 6개가 통과했다.
- Container는 running, loopback-only, restart count 0 상태를 유지해 UNIT-05
  blocker를 해소했다.
- 전용 Database Backup/Restore Runbook을 추가하고 Runbook index에서 접근할 수
  있게 했다. Human-controlled 작업, 중단 기준과 최종 cleanup 확인 절차를 한 곳에
  기록했다.
- 사람이 Restore container·volume과 그 안의 Local Restore DB data, local password
  file, Restore log 및 port 55432 listener를 제거했다.
- Backup과 checksum은 final checksum 검증을 통과한 permission 600 artifact로
  Repository 밖에 보존하고 reusable pgvector image는 유지했다.
- Cleanup 과정에서 Production DB와 다른 Local database는 변경하지 않았고
  UNIT-06 blocker를 해소했다.
- UNIT-01~06이 모두 완료됐으며 전체 Verification Status는 `passed`다.

## Manual or Production Verification

UNIT-01 human verification: passed

- Production server/catalog, source row count, constraint/index/sequence baseline과
  Shared Pooler session mode 5432 연결을 사람이 확인했다.
- 실제 host, user, project reference, password와 전체 connection string은 기록하지
  않았다.

UNIT-03 human verification: passed

- 사람이 Production read-only logical Backup, checksum과 archive 구조 검증 및
  임시 credential 정리를 완료했다.
- Backup과 checksum은 Repository 밖에 permission 600으로 유지한다.

UNIT-04 human verification: passed

- 사람이 Local PostgreSQL 17.6·pgvector 0.8.0 격리 환경을 준비하고 fail-fast·
  single-transaction Restore와 최소 구조 확인을 완료했다.
- Container, volume, database와 필요한 artifact는 UNIT-05를 위해 유지한다.

UNIT-05 human verification: passed

- 사람이 Local Restore DB에서 read-only transaction과 rollback 경계로 row count,
  object, sequence, FK, pgvector와 대표 query 정합성을 확인했다.
- Production DB에는 재접속하지 않았고 Local Restore resource는 변경하지 않았다.

UNIT-06 human verification: passed

- 최소 Runbook 문서화와 human-controlled cleanup을 완료했다.
- Restore container·volume·Local DB data, password file, Restore log와 listener
  제거를 확인했다.
- Backup과 checksum은 Repository 밖에 permission 600으로 보존한다.

## Pending Verification

None.

## Evidence Notes

- UNIT-01 Production SQL Editor 조회와 Docker 연결 테스트는 사람이 수행했고,
  Agent는 sanitized 결과만 기록했다.
- Host PATH의 PostgreSQL client 미탐지 실패와 Docker client 대안 검증을 모두
  보존했다.
- 기사 본문, summary, URL 목록, embedding 값, 실제 host·user·project reference,
  password와 connection string은 기록하지 않았다.
- 기존 `445 passed, 91 subtests passed in 15.80s`는 이전 UNIT-01 evidence이고,
  UNIT-06 Runbook 단계의 최신 결과는 `445 passed, 91 subtests passed in 15.29s`다.
  이번 cleanup evidence 반영에서는 pytest를 다시 실행하지 않았다.
- Approved Fixes 문서는 비어 있어 review output을 구현 근거로 사용하지 않았다.
- UNIT-02에서 Production query, Backup, image pull, container·volume 생성,
  Restore와 cleanup을 실행하지 않았다.
- UNIT-03 Backup과 checksum은 UNIT-04·05를 위해 Repository 밖에 유지한다.
- 실제 credential과 SHA-256 hash value는 기록하지 않았다.
- Agent는 Backup content를 열거나 읽거나 검사하지 않았고 checksum을 재계산하지
  않았다.
- Local Restore는 Production DB와 분리된 Docker environment에서 사람이
  수행했고 외부 노출 없이 loopback binding만 사용했다.
- Backup mount는 read-only였고 `pg_restore`는 owner·ACL을 제외한 single
  transaction으로 수행됐다.
- Local password 값과 Restore log 내용은 기록하지 않았다.
- Container, volume, database, local password file과 Restore log는 UNIT-06 cleanup
  전까지 유지했고 이후 사람이 제거했다.
- Backup과 checksum은 cleanup하지 않고 Repository 밖에 유지한다.
- Agent는 Restore를 재실행하거나 Local DB를 조회하지 않았다.
- UNIT-05 query는 Local Restore DB에서만 실행됐고 Production DB에 재접속하지
  않았다.
- 모든 UNIT-05 SQL은 read-only transaction과 rollback으로 수행됐다.
- 기사 본문, URL, summary와 embedding value는 출력하거나 기록하지 않았다.
- Agent는 Local DB나 Docker resource에 접근하지 않았다.
- UNIT-06 cleanup은 사람이 직접 수행했고 Agent는 Docker 또는 filesystem cleanup을
  실행하지 않았다.
- `newslab-restore-drill` container, `newslab-restore-drill-data` volume과
  `newslab_restore` data는 제거됐다.
- Local Restore password file, Restore log와 port listener도 제거됐다.
- Final checksum verification은 통과했고 Backup과 checksum은 Repository 밖에
  유지한다.
- 실제 password, checksum hash와 log 내용은 기록하지 않았다.
- `pgvector/pgvector:0.8.0-pg17` image는 cleanup 대상이 아니므로 유지했다.
- Cleanup 이후 Production DB 접속이나 변경은 없었다.
