# Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## 작업 내용

- Production Supabase PostgreSQL을 변경하지 않는 read-only logical Backup을
  생성하고 checksum과 custom archive 구조를 검증했다.
- Production과 분리된 Local PostgreSQL 17·pgvector 0.8.0 Docker 환경에 archive를
  Restore하고 schema, data, constraint, index, sequence와 vector 정합성을
  확인했다.
- 검증이 끝난 임시 Restore container·volume·credential·log를 정리하고, 검증된
  Backup과 checksum은 Repository 밖에 permission 600으로 보존했다.
- 반복 가능한 수동 Backup·Restore·검증·cleanup 절차를 전용 Runbook으로 작성하고
  Runbook index에 연결했다.

## 주요 변경 사항

- UNIT-01 baseline
  - Production PostgreSQL 17.6과 PostgreSQL Docker client 17.10의 major 호환성을
    확인했다.
  - Direct connection 5432는 local Docker 환경에서 주소 해석에 실패했으며,
    Shared Pooler session mode 5432 연결을 최종 Backup 경로로 사용했다.
  - `public`의 application table·data·sequence·constraint·index만 Backup 대상으로
    확정하고 `extensions`와 Supabase 관리 schema는 제외했다.
- Backup과 archive
  - `public` schema를 owner·ACL 없이 PostgreSQL custom archive로 생성했다.
  - Archive non-empty, SHA-256과 `pg_restore --list`를 검증했으며 table
    definition·data와 sequence definition·value가 각각 14개임을 확인했다.
- 격리 Restore
  - `pgvector/pgvector:0.8.0-pg17` 기반 PostgreSQL 17.6 환경을 loopback에만
    노출하고 `extensions.vector`를 먼저 준비했다.
  - `pg_restore --exit-on-error --single-transaction --no-owner --no-acl`로
    Restore했다.
- 정합성 검증
  - 14개 table과 총 12,330개 row가 Production baseline과 일치했다.
  - Table 14개, sequence 14개, index 45개, constraint 83개와 constraint 유형별
    개수가 일치했다.
  - Sequence 14개가 source `last_value`와 일치하고 모두 table `MAX(id)`를
    포함하며, foreign key 11개의 orphan은 0건이다.
  - pgvector 0.8.0, `extensions.vector(1536)`, NULL 0건, dimension mismatch 0건과
    대표 관계 query 6개를 확인했다.
- 최종 정리
  - Restore container·volume·Local DB data·password file·Restore log와 listener를
    제거했다.
  - Backup archive와 checksum은 최종 checksum 검증을 통과한 상태로 Repository
    밖에 보존하고 재사용 가능한 pgvector image는 유지했다.
- 문서
  - `docs/runbooks/database-backup-restore.md`에 human-controlled 실행 경계,
    중단 조건, sanitized evidence와 cleanup 정책을 기록했다.
  - `docs/RUNBOOK.md`에서 전용 Runbook으로 이동할 수 있게 연결했다.

## 추가/변경된 API

없음.

- FastAPI endpoint, request/response schema와 인증 정책을 변경하지 않았다.
- Application 실행 계약과 `/metrics`를 포함한 API surface 변경이 없다.

## DB 변경 사항

Production DB 변경은 없다.

- Production에서는 read-only catalog 조회와 logical Backup만 수행했다.
- Schema, migration, table, constraint, index와 Production data를 변경하지 않았다.
- Restore는 Production과 분리된 일회성 Local Docker volume에서만 수행했으며,
  검증 후 container·volume과 Local Restore data를 제거했다.

## README 영향

README 변경은 필요하지 않다.

- 이번 변경은 application 사용법이나 API 계약이 아니라 운영자용 수동
  Backup/Restore 훈련 절차다.
- 운영 진입점인 `docs/RUNBOOK.md`와 전용 database Backup/Restore Runbook에 절차를
  배치해 기존 문서 구조 안에서 발견할 수 있도록 했다.

## 테스트

- `PYTHONPATH=. pytest -q`
  - 최신 실행 결과: `445 passed, 91 subtests passed in 15.29s`
- `scripts/agent_next_step.sh status`
  - Current unit: none
  - Completed units: 6
  - Pending units: 0
  - Verification: `passed`
- Runbook 문서 검사
  - 전용 Runbook 존재 확인: passed
  - Runbook index → 전용 Runbook link: passed
  - 전용 Runbook → index link: passed
- 정적 검사
  - `git diff --check`: 출력 없음
  - Task·Verification·Runbook whitespace 검사: passed
  - Connection URI, credential, private key, checksum hash와 container ID pattern:
    match 없음

## 확인 결과

- 사람이 Production read-only baseline, Backup, 격리 Restore, Local read-only
  정합성 검증과 cleanup을 직접 수행했고 sanitized evidence를 제공했다.
- Production `public` custom archive는 27초에 생성됐고 크기는 28,679,777 bytes다.
  Non-empty, checksum과 archive list 검증이 모두 통과했다.
- Local Restore는 PostgreSQL 17.6·pgvector 0.8.0에서 성공했다. 기록된 Restore
  duration 0초는 정수 초 측정에서 1초 미만일 수 있으며, exit success, error scan,
  table·sequence 개수와 vector type 결과로 성공을 확인했다.
- Source/Restore row count 14개와 total 12,330, object·constraint count,
  sequence·FK·pgvector 및 대표 query 검증이 모두 통과했다.
- Cleanup 후 Restore container·volume·Local DB data·password file·Restore log와
  local listener가 제거됐고 Production DB와 다른 Local DB는 변경되지 않았다.
- Backup과 checksum은 최종 checksum 검증 및 permission 600 상태로 Repository
  밖에 보존한다. 실제 checksum hash와 credential은 문서에 기록하지 않았다.
- Verification Status는 `passed`이며 Pending Verification은 없다.

## 비고

- Host PATH에서 `pg_dump`, `psql`, `pg_restore`를 찾지 못한 초기 실패와 Direct
  connection 주소 해석 실패는 historical evidence로 보존했다. PostgreSQL 17
  Docker client와 Shared Pooler session mode 검증으로 blocker를 해소했다.
- Approved Fixes 문서에는 승인·적용된 finding이 없다. Review artifact를 test나
  Verification 통과 근거로 사용하지 않았다.
- Backup archive, checksum, raw archive list, password와 Restore log는 Repository에
  추가하지 않았다. 실제 host, user, project reference, connection URI, 기사 본문,
  summary, URL과 embedding 값도 기록하지 않았다.
- 정기 Backup 자동화, PITR, Object Storage lifecycle, K3s resource와 Production
  Restore는 이번 범위에 포함하지 않았다.
- PR merge, git push, Production deployment와 K3s rollout 완료를 주장하지 않는다.
