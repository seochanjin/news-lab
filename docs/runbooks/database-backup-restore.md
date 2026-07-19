# Database logical Backup과 격리 Restore 훈련

[Runbook index로 돌아가기](../RUNBOOK.md)

## 목적과 통제 경계

이 Runbook은 Production Supabase PostgreSQL을 변경하지 않고 `public` application
schema의 custom logical Backup을 만든 뒤, Mac 로컬의 일회성 PostgreSQL 17과
pgvector 0.8.0 환경에 Restore하여 복구 가능성을 확인하는 수동 훈련 절차다.
정기 Backup, PITR, Object Storage, K3s resource와 Production Restore는 다루지
않는다.

Production 연결, `pg_dump`, Docker resource 생성·삭제와 artifact 삭제는 사람이
대상과 명령을 검토한 뒤 직접 수행한다. Agent는 Production Secret을 조회하거나
Production DB, Docker resource와 Backup artifact에 접근하지 않는다. 실행 결과는
credential, 전체 connection string, 데이터 본문, embedding 값과 checksum hash를
제외한 sanitized evidence로만 Verification에 기록한다.

## 사전 조건과 중단 기준

- PostgreSQL client major가 Production server major보다 낮지 않아야 한다.
- 연결은 Direct 또는 Shared Pooler session mode의 port `5432`만 사용한다.
  Transaction Pooler port `6543`은 사용하지 않는다.
- Production credential은 Repository 밖 mode `0700` directory의
  `pg_service.conf`와 `pgpass`에 두고 두 file을 mode `0600`으로 제한한다.
- Backup directory도 Repository 밖에 만들고 archive, checksum과 raw archive
  list를 Git, chat, ticket과 Notion에 첨부하지 않는다.
- Restore image는 Production과 같은 PostgreSQL major의 versioned pgvector tag를
  사용하고 host port는 `127.0.0.1`에만 bind한다.
- Production connection setting이 Local Restore 또는 cleanup 명령에 보이거나,
  예정한 container·volume·artifact의 정확한 이름을 확인할 수 없으면 중단한다.

## Backup과 archive 검증

사람이 read-only `pg_service.conf`와 `pgpass`를 container에 bind mount하고 다음
형태를 검토해 실행한다. 실제 경로와 접속 값은 shell argument에 풀어 쓰지 않는다.

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
    --file=/backup/<ARCHIVE_NAME>.backup

test -s <BACKUP_PATH>
pg_restore --list <BACKUP_PATH> > <TEMP_LIST_PATH>
shasum -a 256 <BACKUP_PATH> > <CHECKSUM_PATH>
shasum -a 256 -c <CHECKSUM_PATH>
```

Archive가 비었거나 archive list와 checksum 검증 중 하나라도 실패하면 Restore를
시작하지 않는다. Backup이 끝나면 Production credential file과 raw archive list를
삭제하고 archive와 checksum을 mode `0600`으로 제한한다.

## 격리 Restore와 검증

사람이 전용 local password file, 일회성 container·named volume과 read-only
archive mount를 사용한다. Container는 `127.0.0.1:<LOCAL_PORT>:5432`로만
노출한다. 새 local database에서 기본 `public` schema를 제거한 뒤 `extensions`
schema에 `vector` 0.8.0을 먼저 만들고 다음 형태로 Restore한다.

```bash
docker exec <RESTORE_CONTAINER> \
  pg_restore \
    --single-transaction \
    --exit-on-error \
    --no-owner \
    --no-acl \
    --username=<LOCAL_USER> \
    --dbname=<LOCAL_DB> \
    /backup/<ARCHIVE_NAME>.backup
```

Restore exit status가 0이고 log에 error가 없을 때만 다음 read-only 검증을 수행한다.

- Backup 대상 전체 table의 source/Restore row count
- primary key, foreign key, unique/check constraint와 index 수·유효 상태
- 모든 foreign key의 orphan 0건
- sequence 존재, source `last_value` 일치와 `last_value >= MAX(id)`
- `vector` version·schema와 embedding type·dimension
- 기사 본문, summary, URL과 embedding 값을 출력하지 않는 대표 query

하나라도 실패하면 불명확한 환경에 `--clean` Restore를 덮어쓰지 않는다. 원인과
실패 section만 기록하고, 사람이 기존 일회성 환경을 정리한 뒤 새 환경에서 다시
시작한다. Production에서 보정 query를 실행하지 않는다.

## 최종 정리

정합성 검증이 모두 통과한 뒤 사람이 아래 순서로 정확한 대상을 확인하고
정리한다. 명령은 예시 placeholder이며 실제 실행 전 예정한 논리 이름과 일치하는지
확인한다.

1. Container가 이 훈련 전용 이름이고 loopback에만 bind됐는지 확인한다.
2. Container를 삭제한 뒤 같은 이름의 container가 없음을 확인한다.
3. 이 훈련 전용 volume 이름을 다시 확인하고 삭제한 뒤 부재를 확인한다.
4. Local password file과 Restore log를 삭제하고 파일 부재를 확인한다.
5. `/tmp`의 이 훈련 전용 archive list와 임시 directory가 남지 않았는지 확인한다.
6. Backup과 checksum은 아래 두 정책 중 하나를 명시적으로 선택한다.
   - 보존: Repository 밖 operator 전용 경로에 두고 directory mode `0700`, 두 file
     mode `0600`, checksum 재검증 결과를 기록한다.
   - 삭제: archive와 checksum의 정확한 경로를 재확인해 삭제하고 두 파일의 부재를
     기록한다.

```bash
docker ps -a --filter name='^/<RESTORE_CONTAINER>$'
docker port <RESTORE_CONTAINER>
docker volume inspect <RESTORE_VOLUME>

docker rm -f <RESTORE_CONTAINER>
test -z "$(docker ps -aq --filter name='^/<RESTORE_CONTAINER>$')"

docker volume rm <RESTORE_VOLUME>
if docker volume inspect <RESTORE_VOLUME> >/dev/null 2>&1; then
  exit 1
fi

rm -f <LOCAL_PASSWORD_FILE> <RESTORE_LOG> <TEMP_LIST_PATH>
test ! -e <LOCAL_PASSWORD_FILE>
test ! -e <RESTORE_LOG>
test ! -e <TEMP_LIST_PATH>
```

Container 삭제로 그 안의 Restore database가 함께 제거되고, named volume 삭제로
Restore data가 최종 제거된다. 삭제 후 자동 재생성이나 운영 rollback은 없다.
Cleanup 중 일부가 실패하면 성공한 항목과 남은 정확한 논리 이름만 기록하고,
광범위한 glob이나 재귀 삭제로 우회하지 않는다.

## Verification 기록

다음 sanitized 결과만 branch Verification 문서에 기록한다.

- client/server major, connection mode와 port
- Backup byte size·소요 시간, archive list exit status·entry count와 checksum 검증
  성공 여부
- Restore image tag, PostgreSQL·pgvector version, loopback bind, Restore exit status와
  소요 시간
- table·constraint·index·sequence 수, row count 일치, orphan 합계, vector 검증과
  대표 query 성공 여부
- container·volume·local password file·Restore log·임시 파일의 최종 부재
- Backup과 checksum의 최종 보존 또는 삭제 상태

실제 host, user, project reference, password, connection string, checksum hash,
container ID, 기사 본문, summary, URL과 embedding 값은 기록하지 않는다.
