# Approved Fixes: Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## Approved Fixes

- [x] FIX-01: SHA-256 evidence 정책 통일
- [x] FIX-02: Index·constraint 검증 표현을 count parity로 한정

### FIX-01: SHA-256 evidence 정책 통일

- 대상: `docs/tasks/feat-database-backup-restore-drill.md`
- 문제: Task는 Verification에 실제 SHA-256 digest 값을 기록하도록 요구하지만, Runbook과 Verification은 실제 hash 값을 기록하지 않는 sanitized evidence 정책을 사용한다.
- 승인한 수정:
  - 실제 SHA-256 digest 값 기록 요구를 제거한다.
  - checksum 생성 성공 여부와 재검증 성공 여부만 기록하도록 변경한다.
  - 실제 hash 값은 Repository, Notion, PR, Verification에 기록하지 않는다는 정책을 유지한다.
- 수정 이유: 민감정보 최소화 정책과 문서 간 계약을 일치시키기 위해서다.

### FIX-02: Index·constraint 검증 표현을 count parity로 한정

- 대상:
  - `docs/verification/feat-database-backup-restore-drill.md`
  - `docs/devlog/feat-database-backup-restore-drill.md`
  - `docs/pr/feat-database-backup-restore-drill.md`
- 문제: 실제 검증은 index·constraint의 전체 개수와 유형별 개수를 비교했지만, 일부 문서는 이를 구조 또는 정의가 완전히 일치한 것처럼 표현할 수 있다.
- 승인한 수정:
  - `index·constraint 일치`, `구조 일치`와 같이 identity-level equivalence로 읽힐 수 있는 표현을 제거한다.
  - `index·constraint 개수 일치`, `constraint 유형별 count parity 확인`, `aggregate object count parity`로 표현을 좁힌다.
  - Table row count, sequence value, FK orphan, pgvector type·dimension처럼 실제 identity 또는 값 비교를 수행한 항목은 기존 표현을 유지한다.
- 수정 이유: 수행한 검증 범위를 초과해 복구 구조의 완전한 동일성을 주장하지 않도록 하기 위해서다.

## Rejected or Deferred Suggestions

### Exact index·constraint definition 비교 — 이번 PR에서는 보류

- CodeRabbit이 제안한 또 다른 해결책은 Production과 Restore의 index 이름, 대상 column, predicate, constraint definition을 정확히 비교하는 것이다.
- 이번 훈련에서 확보한 evidence는 aggregate count와 constraint 유형별 count이며, 임시 Restore environment는 UNIT-06에서 이미 정리했다.
- 정확한 catalog identity 비교를 추가하려면 Restore 환경을 다시 생성하고 DB catalog query를 재수행해야 한다.
- 문서 표현을 count parity로 정확히 한정하면 현재 evidence와 주장이 일치하므로, 이번 PR에서는 환경 재생성과 추가 DB 검증을 수행하지 않는다.
- 향후 복구 검증 수준을 강화하는 별도 작업에서 definition-level comparison을 검토한다.

### CodeRabbit의 unit test 생성 제안 — 적용하지 않음

- 이번 PR은 application code, migration, API와 business logic을 변경하지 않는 문서·운영 훈련 기록이다.
- 새 unit test 생성은 두 finding의 해결과 직접 관련이 없으므로 적용하지 않는다.

## Applied Changes

현재 상태: 적용 및 정적 검증 완료

승인된 수정은 다음 문서에 최소 변경으로 반영한다.

- FIX-01 — `docs/tasks/feat-database-backup-restore-drill.md`
  - SHA-256 digest 실제 값 기록 요구 제거
  - checksum 생성·재검증 성공 상태만 기록하도록 수정
- FIX-02 — `docs/verification/feat-database-backup-restore-drill.md`
  - index·constraint 결과를 count-only 또는 count parity로 명시
- FIX-02 — `docs/devlog/feat-database-backup-restore-drill.md`
  - 구조 일치로 해석될 수 있는 표현을 유형별 개수 일치로 축소
- FIX-02 — `docs/pr/feat-database-backup-restore-drill.md`
  - PR 요약의 검증 범위를 aggregate count parity로 한정
- FIX-01·FIX-02 적용 결과와 문서 정적 검증 기록
  - 본 승인 결정과 적용 결과를 기록

검증 결과:

- Task, Runbook과 Verification의 SHA-256 hash 비기록 정책: passed
- Checksum 생성·최초 검증·권한 변경 후 재검증 성공 evidence 유지: passed
- Verification, Devlog와 PR의 aggregate count parity 표현: passed
- Identity-level index·constraint equivalence 주장 부재: passed
- 변경 문서 whitespace와 `git diff --check`: passed
- Connection URI, credential, private key, SHA-256 hash value와 container ID
  pattern: match 없음
- Application code 변경이 없어 pytest는 재실행하지 않았다. 기존
  `445 passed, 91 subtests passed in 15.29s` evidence를 유지한다.
- Production, Local DB, Docker와 Backup·checksum artifact 작업: 수행하지 않음
- CodeRabbit review thread 확인은 push 이후 사람 또는 별도 review 단계에서
  수행해야 하므로 이번 적용 범위에서는 미수행

다음 항목은 변경하지 않는다.

- Production DB
- Local Restore DB와 Docker resource
- Backup archive와 checksum
- Runbook의 hash 비기록 정책
- Application code, migration, manifest, dependency
- 이미 통과한 row count, sequence, FK orphan, pgvector와 대표 query evidence

## Verification Required

수정 후 다음을 확인한다.

1. 정책 일관성
   - Task, Runbook, Verification 모두 실제 SHA-256 hash 값을 기록하지 않는 정책으로 일치해야 한다.
   - checksum 생성과 재검증의 성공 여부는 계속 evidence로 남아야 한다.
2. 표현 정확성
   - Verification, Devlog와 PR 문서에서 index·constraint 검증이 count parity임을 명시해야 한다.
   - exact definition, identity-level structural equivalence를 수행했다고 주장하는 문구가 없어야 한다.
3. 문서 검사
   - `git diff --check`
   - 변경 문서 whitespace 검사
   - connection URI, credential, private key, SHA-256 hash value와 container ID pattern 검사
4. 범위 확인
   - 변경 파일이 승인된 문서로 제한돼야 한다.
   - Production 접속, Local DB query, Docker 재생성, Backup·checksum 접근을 수행하지 않아야 한다.
5. Workflow 확인
   - Approved Fixes 문서에 FIX-01·FIX-02의 적용 상태와 검증 결과를 기록한다.
   - 수정 push 후 CodeRabbit의 두 review thread가 현재 diff 기준으로 해소됐는지 확인한다.

Application code 변경이 없으므로 이 수정만을 이유로 새로운 기능 test를 추가할 필요는 없다. 기존 Repository test evidence는 유지하고, 문서 정적 검사와 review thread 해소 여부를 핵심 검증으로 사용한다.
