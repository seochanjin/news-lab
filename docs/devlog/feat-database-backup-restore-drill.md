# Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## 작업 목적

Production Supabase PostgreSQL을 변경하지 않고 `public` application schema의
logical Backup을 만든 뒤, Production과 분리된 PostgreSQL 17·pgvector 0.8.0
환경에 실제 Restore해 복구 가능성을 확인하는 것이 목적이었다.

이번 단계의 완료 기준은 Backup 파일 생성 자체가 아니었다. Archive 무결성,
격리 Restore, schema·data·constraint·index·sequence·vector 정합성, 대표 관계
query와 임시 환경 cleanup까지 한 번의 수동 복구 흐름으로 검증하는 데 초점을
맞췄다.

## 기존 문제

- Repository migration만으로는 Production 전체 schema를 재구성할 수 없었다.
  `sources`와 `articles`의 초기 schema는 Repository 밖에서 시작했기 때문에 실제
  Production catalog baseline이 필요했다.
- Agent 환경의 Host PATH에는 `pg_dump`, `psql`, `pg_restore`가 없어 client/server
  major 호환성을 바로 확인할 수 없었다.
- Direct connection 5432는 local Docker 환경에서 endpoint 주소를 해석하지 못해
  Backup 경로로 사용할 수 없었다.
- `vector` extension은 `extensions` schema에 있지만 application table은 `public`에
  있어, 관리 schema 전체를 dump하지 않으면서 pgvector 의존성을 복원하는 순서를
  명시해야 했다.
- Backup이 존재해도 실제로 다른 환경에 Restore하고 row·관계·sequence·vector를
  검증하지 않으면 복구 가능성을 증명할 수 없었다.
- Credential, checksum hash, 기사 본문과 embedding 값을 기록하지 않으면서도
  audit 가능한 evidence를 남기는 경계가 필요했다.

## 변경 내용

- Production PostgreSQL 17.6과 PostgreSQL Docker client 17.10의 major 호환성을
  확인했다.
- Shared Pooler session mode 5432를 read-only Backup 경로로 확정했다.
- Backup 범위를 `public`의 table·data·sequence·constraint·index로 제한하고,
  `extensions` 및 Supabase 관리 schema는 제외했다.
- `public` custom archive를 owner·ACL 없이 생성하고 non-empty, SHA-256과 archive
  list를 검증했다.
- PostgreSQL 17.6·pgvector 0.8.0 일회성 Docker 환경에 archive를 Restore했다.
- 14개 table, object·constraint, sequence, FK orphan, pgvector와 대표 관계 query를
  Production baseline과 비교했다.
- Restore container·volume·Local DB data·password file·Restore log와 listener를
  정리했다.
- Backup과 checksum은 최종 checksum 검증 및 permission 600 상태로 Repository
  밖에 보존했다.
- 전용 [Database Backup/Restore Runbook](../runbooks/database-backup-restore.md)을
  만들고 [Runbook index](../RUNBOOK.md)에 연결했다.

## 구현 상세

### Baseline과 Backup 계약

Production application table은 14개, sequence 14개, index 45개, constraint 83개로
확인됐다. Constraint는 primary key 14개, foreign key 11개, unique 11개, check
47개이며 모든 application table에 primary key가 있었다.

Backup은 PostgreSQL custom archive, `--schema=public`, `--no-owner`, `--no-acl`을
계약으로 정했다. Production credential은 Repository 밖의 `pg_service.conf`와
`pgpass`로 분리하고 command argument나 connection URI에 풀어 쓰지 않았다.

### 격리 Restore

Restore image는 `pgvector/pgvector:0.8.0-pg17`을 사용했다. Host exposure는
loopback으로 제한하고, archive가 `public` schema를 생성할 수 있도록 기본
`public`을 제거한 뒤 `extensions` schema와 vector 0.8.0을 먼저 준비했다.

Restore는 owner·ACL을 제외하고 `--exit-on-error --single-transaction`으로
실행했다. 첫 SQL error에서 중단하고 전체 transaction을 rollback할 수 있는
경계를 택해 일부 object만 복구된 상태를 성공으로 오인하지 않게 했다.

### 정합성 검증과 cleanup

Local Restore 검증 SQL은 `BEGIN READ ONLY`와 `ROLLBACK` 경계에서 실행했다.
기사 본문, summary, URL과 embedding 값 대신 row count, boolean, object count와
관계 집계만 evidence로 남겼다.

검증이 끝난 container, volume, Local Restore DB data, local password file,
Restore log와 listener는 사람이 제거했다. Backup과 checksum은 검증된 복구
artifact로 Repository 밖에 보존하고, Production data나 credential을 포함하지
않는 pgvector image는 재사용 가능하므로 유지했다.

## 대안 검토

### Direct connection과 Session Pooler

- Direct connection 5432를 우선 검토했지만 local Docker에서 주소 해석에
  실패했다.
- Transaction Pooler 6543은 `pg_dump` 경로로 사용하지 않았다.
- PostgreSQL server와 database를 확인한 Shared Pooler session mode 5432를
  선택했다.

### 전체 schema dump와 `public` 선택 dump

- 전체 schema dump는 Supabase 관리 object와 extension 소유권·권한을 불필요하게
  포함할 수 있다.
- `public`만 dump하고 pgvector를 Restore 전에 별도로 준비하는 접근을 선택했다.

### Plain SQL과 custom archive

- Plain SQL은 사람이 읽기 쉽지만 archive 목록 검사와 선택 Restore에 불리하다.
- Custom archive는 `pg_restore --list`, 압축과 Restore option을 지원해 이번
  drill에 더 적합했다.

### Production Restore와 격리 Restore

- Production Restore는 실제 data와 schema를 변경할 위험이 있어 제외했다.
- Loopback-only Local Docker environment를 사용해 복구 가능성을 Production과
  분리해 검증했다.

### Backup 삭제와 보존

- Cleanup 시 Backup까지 삭제하는 선택지도 있었지만, 최종 checksum 검증을 통과한
  artifact를 후속 복구 참고용으로 남기는 정책을 선택했다.
- 보존 위치는 Repository 밖이며 archive와 checksum은 permission 600으로
  제한했다.

## 선택한 접근과 근거

- 검증된 PostgreSQL 17 client를 사용해 server major보다 낮은 client로 인한 dump
  호환성 위험을 피했다.
- Application 책임 범위인 `public`만 archive에 담고 pgvector는 명시적 Restore
  사전 조건으로 분리해 Supabase 관리 영역과 경계를 유지했다.
- `--exit-on-error --single-transaction`으로 partial Restore를 성공으로 처리하지
  않는 fail-fast 경계를 만들었다.
- Production baseline과 Local Restore 결과를 table별 row, object, sequence,
  orphan과 vector 계약으로 비교해 단순 접속 성공보다 강한 복구 evidence를
  확보했다.
- 실제 값 대신 aggregate와 상태만 기록해 운영 evidence와 credential·개인 데이터
  보호를 함께 만족시켰다.
- 수동 실행 순서와 중단 조건을 Runbook으로 분리해 같은 훈련을 다시 수행할 수
  있게 했다.

## 트레이드오프

- `public` 선택 dump는 Supabase 관리 schema를 복구하지 않는다. 대신 이번 범위인
  NewsLab application data와 pgvector 의존성을 명확히 분리한다.
- Session Pooler는 Direct endpoint보다 한 계층이 추가되지만, 실제 operator
  환경에서 검증된 session 연결 경로를 제공했다.
- Custom archive는 `pg_restore` 도구가 필요하고 사람이 바로 읽기 어렵지만,
  archive 구조 검사와 fail-fast Restore 제어가 가능하다.
- 수동 drill은 한 시점의 복구 가능성은 증명하지만 정기 Backup이나 지속적인 RPO,
  RTO를 보장하지 않는다.
- Backup 보존은 재검증에 유용하지만 별도 lifecycle·암호화·접근 통제 정책이
  필요하다. 이번 작업에서는 Repository 밖 permission 600 보존까지만 결정했다.
- Restore duration은 정수 초 측정에서 0초로 기록됐다. 재실행으로 시간을 정밀하게
  측정하지 않고 exit success, error scan과 복구 결과를 성공 근거로 사용했다.

## 테스트

- Repository test
  - `PYTHONPATH=. pytest -q`
  - 최신 결과: `445 passed, 91 subtests passed in 15.29s`
- Workflow 상태
  - `scripts/agent_next_step.sh status`
  - Completed units: 6
  - Pending units: 0
  - Verification: `passed`
- Archive와 Restore
  - Backup non-empty, SHA-256과 `pg_restore --list`: passed
  - Table definition·data와 sequence definition·value: 각각 14개
  - `pg_restore --exit-on-error --single-transaction`: passed
  - Restore log error scan: passed
- 정합성
  - 14개 table row count와 total 12,330: 일치
  - Table 14, sequence 14, index 45, constraint 83: 일치
  - Sequence 14개 source value 일치 및 `last_value >= MAX(id)`: passed
  - Foreign key 11개의 orphan: 0
  - pgvector 0.8.0, `extensions.vector(1536)`, NULL 0, dimension mismatch 0
  - 대표 관계 query 6개: passed
- 문서와 scope
  - Runbook index 왕복 link: passed
  - `git diff --check`와 대상 문서 whitespace 검사: passed
  - Credential, connection URI, checksum hash와 container ID pattern: match 없음

## 운영 반영

Production application 배포나 K3s rollout을 수행한 작업은 아니다.

사람이 Production에 read-only로 연결해 baseline과 logical Backup을 확인했고,
Production schema·data·Supabase 설정은 변경하지 않았다. Restore와 정합성 검증은
Production과 분리된 Local Docker environment에서 수행했다.

최종 cleanup으로 Restore container·volume·Local DB data·password file·log와
listener를 제거했다. Backup과 checksum은 최종 checksum 검증을 통과한 상태로
Repository 밖에 보존한다. PR commit, push, merge는 완료로 주장하지 않는다.

## README 업데이트 판단

README는 변경하지 않았다.

이번 작업은 API 사용법, local application 실행이나 사용자 기능이 아니라 운영자용
수동 복구 절차다. 따라서 README보다 `docs/RUNBOOK.md`와 전용 database
Backup/Restore Runbook에 두는 편이 기존 문서 책임과 맞다.

## 확인 결과

- Production PostgreSQL 17.6과 Docker client 17.10의 major 호환성을 확인했다.
- Direct connection 실패 후 Shared Pooler session mode 5432로 blocker를 해소했다.
- `public` custom archive는 27초에 생성됐고 크기는 28,679,777 bytes이며 checksum과
  archive list 검증을 통과했다.
- PostgreSQL 17.6·pgvector 0.8.0 격리 Restore와 구조 검증이 통과했다.
- Production/Restore row count, object·constraint, sequence, FK, vector와 대표
  query 결과가 모두 일치했다.
- Cleanup 후 임시 Restore resource와 local credential·log·listener가 제거됐다.
- Backup과 checksum은 permission 600으로 Repository 밖에 보존한다.
- Verification Status는 `passed`이고 Pending Verification은 없다.

## 이번 단계의 의미

Backup 파일이 있다는 사실과 실제 복구 가능성 사이의 간극을 줄였다. 이번 작업은
Production을 변경하지 않으면서도 `Backup 생성 → archive 검증 → 격리 Restore →
정합성 검증 → cleanup` 전체 흐름을 실제 evidence로 연결했다.

또한 Supabase 관리 schema와 NewsLab application schema의 책임을 분리하고,
pgvector처럼 schema 밖 dependency가 있는 경우의 Restore 순서를 명시했다. 이를
통해 장애 시 즉흥적인 command 조합이 아니라 검토 가능한 Runbook과 중단 기준을
사용할 수 있게 됐다.

## 포트폴리오용 요약

Production Supabase PostgreSQL 17의 `public` schema를 custom logical archive로
Backup하고, PostgreSQL 17·pgvector 0.8.0 격리 환경에 fail-fast single-transaction
Restore하는 재해복구 훈련을 설계·검증했다. 14개 table과 총 12,330개 row,
45개 index, 83개 constraint, 14개 sequence, FK orphan 0건, 1536차원 vector와
대표 관계 query를 비교해 복구 정합성을 확인했다. Credential과 데이터 본문은
evidence에서 제외하고, 임시 환경 cleanup 및 검증 artifact 보존 정책까지
Runbook으로 남겼다.

## 다음 단계 후보

- PR review와 merge 여부는 사람이 결정한다. 현재 PR merge 완료를 주장하지 않는다.
- 정기 Backup 자동화, Object Storage 보존과 lifecycle 정책은 별도 task로 검토할 수
  있다.
- 암호화된 Backup 저장, 접근 권한 audit와 보존 기간을 별도 운영 정책으로 정의할
  수 있다.
- 반복 Restore drill과 RPO·RTO 측정을 정기 운영 개선 과제로 검토할 수 있다.
- Direct endpoint의 IPv6/DNS 접근 문제는 Backup 경로 변경과 분리된 네트워크
  후속 조사 후보로 남길 수 있다.
- Approved Fixes에는 승인된 항목이 없으며 Review artifact를 Verification 근거로
  사용하지 않았다.
