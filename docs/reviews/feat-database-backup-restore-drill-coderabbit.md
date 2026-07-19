# CodeRabbit Review: Supabase PostgreSQL 논리 Backup 및 격리 Restore 훈련

## Review Summary

CodeRabbit은 애플리케이션 코드나 Production DB 변경 문제를 발견하지 않았다. 발견된 문제는 모두 문서의 검증 정책과 실제 수행 evidence 사이의 일관성에 관한 것이다.

1. Task 문서가 SHA-256 digest 값 자체를 Verification에 기록하도록 요구하지만, Runbook과 실제 Verification은 보안·sanitization 정책에 따라 실제 hash 값을 기록하지 않는다고 명시한다.
2. Index와 constraint는 개수만 비교했는데 일부 문서가 구조 자체가 일치한 것처럼 표현한다. 동일한 개수만으로 이름, 대상 column, 조건과 정의까지 같다고 증명할 수 없다.

Pre-merge check 5개는 통과했지만, 아래 두 review thread는 수정 전까지 미해결 상태다.

## Problems Found

### 1. Checksum 기록 정책 불일치

- Severity: Major
- 대상: `docs/tasks/feat-database-backup-restore-drill.md`
- 관련 정책: `docs/runbooks/database-backup-restore.md`, `docs/verification/feat-database-backup-restore-drill.md`

Task에는 Verification에 `SHA-256 digest`를 기록한다고 작성돼 있다. 반면 Runbook은 실제 checksum hash를 기록하지 않는다고 명시하고, Verification도 checksum 생성·재검증 성공 여부만 기록했다.

현재 상태에서는 같은 작업 안에서 다음 두 정책이 충돌한다.

- Task: digest 값 기록 요구
- Runbook·Verification: 실제 digest 값 미기록

실제 수행 방식은 credential·hash를 문서와 Notion에 남기지 않는 정책이므로, Task의 요구사항을 수정하는 것이 맞다.

### 2. Index·constraint 개수 일치를 구조 일치로 과장

- Severity: Major
- 대상:
  - `docs/verification/feat-database-backup-restore-drill.md`
  - `docs/devlog/feat-database-backup-restore-drill.md`
  - `docs/pr/feat-database-backup-restore-drill.md`

현재 검증은 다음 aggregate count가 Production과 Restore에서 같음을 확인했다.

- Index: 45개
- Constraint: 83개
- Primary key: 14개
- Foreign key: 11개
- Unique: 11개
- Check: 47개

그러나 개수가 같아도 object 이름, 대상 table·column, index expression, partial predicate, constraint definition이 다를 수 있다. 따라서 현재 evidence로 증명한 것은 `구조적 동일성`이 아니라 `개수 일치(count parity)`다.

Restore가 실패했다는 의미는 아니다. 다만 문서의 주장 범위가 실제 검증 범위보다 넓다.

## Required Fixes Before PR

### Fix 1. SHA-256 digest 값 기록 요구 제거

`docs/tasks/feat-database-backup-restore-drill.md`에서 다음 의미로 수정한다.

- 기존 의미: archive basename, 크기, 소요 시간과 SHA-256 digest 값을 기록
- 수정 의미: archive basename, 크기, 소요 시간, checksum 생성·재검증 성공 여부를 기록
- 실제 SHA-256 hash 값은 Git, Notion, chat, ticket과 Verification에 기록하지 않음

Runbook과 Verification의 기존 sanitization 정책은 유지한다.

### Fix 2. Index·constraint 표현을 count parity로 제한

이번 Restore 환경은 이미 cleanup됐으므로, Production과 Restore의 exact catalog definition 비교를 새로 수행하지 않는다. 현재 evidence에 맞춰 다음 세 문서의 표현만 최소 수정한다.

- Verification: `index와 constraint가 일치`가 아니라 `index·constraint 유형별 개수가 Production baseline과 일치`로 표현
- Devlog: `Table 14, sequence 14, index 45, constraint 83: 일치`를 `object count parity 확인`으로 제한
- PR 문서: `constraint/index 정합성 확인` 또는 구조 일치로 해석될 문구를 `개수 기준 parity 확인`으로 제한

Row count, sequence value, FK orphan, pgvector dimension과 representative query는 실제로 수행한 상세 검증 결과이므로 기존 passed evidence를 유지한다.

## Optional Improvements

- 다음 Backup/Restore drill에서는 Production과 Restore의 index·constraint identity를 비교한다.
- Index는 schema, table, index name과 `pg_get_indexdef()` 결과를 정규화해 비교한다.
- Constraint는 table, constraint name, type과 `pg_get_constraintdef()` 결과를 정규화해 비교한다.
- 민감한 data value는 출력하지 않고 catalog definition만 비교한다.
- Exact definition 비교를 도입한 경우에만 `구조 일치` 또는 `structural equivalence` 표현을 사용한다.
- 장기적으로 Backup 보존 기간, 재검증 주기와 폐기 기준을 별도 운영 정책으로 분리한다.

## Suggested Test Commands

수정은 문서 표현 변경만 수행하며 Production DB, Local Restore DB와 Docker resource에는 다시 접근하지 않는다.

```bash
scripts/agent_next_step.sh status

git diff --check

git diff -- \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md \
  docs/devlog/feat-database-backup-restore-drill.md \
  docs/pr/feat-database-backup-restore-drill.md

rg -n \
  'SHA-256 digest|checksum hash|index.*일치|constraint.*일치|구조.*일치|structural equivalence|count parity' \
  docs/tasks/feat-database-backup-restore-drill.md \
  docs/verification/feat-database-backup-restore-drill.md \
  docs/devlog/feat-database-backup-restore-drill.md \
  docs/pr/feat-database-backup-restore-drill.md \
  docs/runbooks/database-backup-restore.md
```

확인 기준:

- Task가 실제 checksum hash 값 기록을 요구하지 않음
- Runbook과 Verification의 `hash not recorded` 정책과 충돌하지 않음
- Index·constraint 결과가 count parity로 한정됨
- 기존 human-operated Backup·Restore·cleanup evidence는 변경되지 않음
- Application code, migration, manifest와 dependency 변경 없음

## Risk Notes

- Checksum hash 기록 정책을 그대로 두면 향후 작업자가 실제 digest 값을 Git·Notion·chat에 남길 수 있어 sanitization 경계가 깨질 수 있다.
- Aggregate count를 구조 일치로 표현하면 잘못된 index definition이나 constraint target을 놓치고도 복구 검증이 완전하다고 오해할 수 있다.
- 이번 finding은 Restore 실패를 의미하지 않는다. 현재 검증은 row count, object count, sequence, FK orphan, pgvector와 대표 query 수준에서 성공했다.
- 최소 수정은 실제 evidence에 맞춰 표현을 좁히는 것이다. Exact catalog 비교는 Restore 환경을 다시 만들지 않는 한 이번 PR의 필수 수정으로 확대하지 않는다.
- 수정 후 CodeRabbit thread 2건을 해결하고 PR을 merge한다.
