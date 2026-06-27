# Approved Fixes: 최근 7일 기사·토픽 파이프라인 확장

## Approved Fixes

- [x] FIX-01: Weekly Home API의 publishable Topic 상태 필터 보강
  - `/weekly-topics/home`은 성공 또는 부분 성공 run에 속한다는 조건만으로 Topic을 공개하지 않는다.
  - 최신 window를 선택하는 `latest_window` CTE에서 개별 `weekly_topics.status`가 publish 가능한 상태인지 확인한다.
  - 실제 card 목록을 조회하는 본 query에서도 동일한 Topic status 조건을 적용한다.
  - publish 가능한 상태의 source of truth는 기존 repository, Weekly 저장 계약과 API 테스트를 확인해 통일한다.
  - 성공 또는 부분 성공 run 안에 `draft`, `failed` 또는 기타 비공개 Topic이 섞여 있어도 홈 응답에서 제외되어야 한다.
  - 최신 run이지만 publish 가능한 Topic이 하나도 없는 window는 `/home`의 최신 공개 window로 선택하지 않는다.
  - 정적 `/weekly-topics/home` route가 동적 `/{topic_id}` route보다 먼저 등록되는 기존 계약은 유지한다.
  - 기존 목록·상세 API contract는 변경하지 않는다.
  - publishable Topic만 포함되는 정상 응답, 비공개 Topic 제외, publish 가능한 결과가 없는 빈 응답 테스트를 추가한다.

- [x] FIX-02: Weekly window의 Asia/Seoul 자정 경계 검증 강화
  - `window_start`는 `Asia/Seoul` 기준 월요일 `00:00:00`이어야 한다.
  - `window_end`는 `Asia/Seoul` 기준 다음 월요일 `00:00:00`이어야 한다.
  - 날짜만 일치하고 시간이 정오 또는 임의 시각인 shifted 7-day window는 거부한다.
  - `week_start`는 `window_start`의 서울 기준 날짜와 일치해야 한다.
  - `week_end`는 `week_start + 6일`이어야 한다.
  - `window_end`의 서울 기준 날짜는 `week_start + 7일`이어야 한다.
  - timezone-aware datetime의 UTC offset 변환 후에도 서울 기준 자정 여부를 검사한다.
  - hour, minute, second와 microsecond가 모두 0인지 확인한다.
  - 정상적인 서울 월요일 자정 window와 명시적인 `--week-start` 실행 계약은 유지한다.
  - 월요일 12:00 KST부터 다음 월요일 12:00 KST까지의 잘못된 window가 `ValueError`로 거부되는 테스트를 추가한다.
  - UTC로 표현된 정상 서울 자정 범위가 통과하는 테스트를 유지하거나 추가한다.

- [x] FIX-03: Raw acquisition 상태 bucket 상호 배타성 검증
  - 다음 상태 목록 내부의 중복뿐 아니라 목록 간 교집합도 거부한다.
    - `reused_article_ids`
    - `extracted_article_ids`
    - `failed_article_ids`
    - `missing_article_ids`
  - 하나의 article ID가 둘 이상의 상태 bucket에 동시에 존재할 수 없도록 한다.
  - `article_raw_texts`에 원문이 존재하는 article은 `failed_article_ids` 또는 `missing_article_ids`에 존재할 수 없다.
  - `reused_article_ids`와 `extracted_article_ids`에 포함된 article은 유효한 원문 map entry를 가져야 한다.
  - article ID 양수 검증과 각 목록 내부 중복 검증은 유지한다.
  - 정상 상태 조합, reused/failed 중복, extracted/missing 중복, raw text와 missing 상태 모순을 테스트한다.
  - 통계와 Summary 입력이 동일한 article 처리 상태를 표현하도록 결과 model 계약을 명확히 한다.

- [x] FIX-04: 최종 run status와 저장·실패 Topic count 정합성 검증
  - Weekly pipeline의 최종 결과 model에서 `run_status`, `saved_topic_count`,
    `failed_topic_count`, 생성 Topic과 failure 목록의 관계를 함께 검증한다.
  - `success` 상태에서는 실패 Topic이 존재할 수 없다.
  - `partial_success` 상태에서는 저장된 Topic과 실패 Topic이 각각 1개 이상 존재해야 한다.
  - `failed` 상태에서는 저장된 Topic이 존재할 수 없다.
  - 선택 Topic이 없는 정상 빈 결과를 성공으로 취급하는 기존 정책은 명시적으로 허용한다.
  - 모든 Topic이 실패한 경우 기존 성공 window 결과를 보존하고 최종 상태가 `failed`가 되는 기존 계약을 유지한다.
  - 일부 Topic만 성공한 경우 성공 부분집합만 저장하고 최종 상태가 `partial_success`가 되는 계약을 유지한다.
  - 동일한 상태/count 검증이 적용되어야 하는 다른 Weekly 최종 결과 model에도 공통 또는 동일한 검증을 반영한다.
  - `success + failure`, `failed + saved`, 저장이나 실패 중 한쪽이 없는
    `partial_success`가 모두 거부되는 테스트를 추가한다.
  - 정상 성공, 정상 부분 성공, 전체 실패와 정상 빈 결과 테스트를 유지한다.

- [x] FIX-05: Raw text loader 결과와 기존 원문 병합
  - `raw_acquisition_stage.py`에서 인자로 전달된 기존 `raw_texts`를 loader 결과로 통째로 덮어쓰지 않는다.
  - 기존 원문 map과 `raw_text_loader()` 결과를 article ID 기준으로 병합한다.
  - loader가 일부 article만 반환하거나 빈 결과를 반환해도 기존에 제공된 유효 원문은 보존한다.
  - 동일 article ID가 양쪽에 존재할 때 어느 원문을 우선할지 명확히 결정한다.
  - DB 또는 loader의 최신 값을 우선한다면 병합 순서와 이유를 코드와 테스트에서 고정한다.
  - 인자로 전달된 기존 원문을 우선한다면 해당 정책을 docstring 또는 설계 문서에 기록한다.
  - CodeRabbit가 지적한 동일 패턴의 다른 분기에도 같은 병합 정책을 적용한다.
  - 기존 원문만 존재하는 경우, loader 원문만 존재하는 경우, 양쪽 모두 존재하는 경우, partial loader와 빈 loader를 테스트한다.
  - 원문 확보 실패 시 다음 순위 관련 기사로 대체하는 기존 계약은 유지한다.

- [x] FIX-06: Weekly JSONB 컬럼의 배열 타입 DB 제약 추가
  - `weekly_topics.key_points`는 JSON array만 저장할 수 있어야 한다.
  - `weekly_topics.keywords`는 JSON array만 저장할 수 있어야 한다.
  - `db/migrations/008_create_weekly_topic_tables.sql`에 `jsonb_typeof()` CHECK를 추가한다.
  - 기본값 `'[]'::jsonb`는 유지한다.
  - object, string, number, boolean 또는 null 형태의 JSONB 값이 schema 계약을 우회하지 못하도록 한다.
  - repository model과 API가 해당 필드를 list로 취급하는 기존 계약을 유지한다.
  - migration 정적 테스트에서 두 JSONB CHECK가 존재하는지 검증한다.
  - 실제 production migration은 Agent가 적용하지 않는다.

- [x] FIX-07: Weekly Topic 최소 기사·출처 수 DB 제약 강화
  - `weekly_topics.article_count`는 Weekly Topic 최소 기사 수인 5 이상이어야 한다.
  - `weekly_topics.source_count`는 최소 서로 다른 source 수인 2 이상이어야 한다.
  - `source_count`는 `article_count`보다 클 수 없다.
  - 기존 application model의 검증과 DB schema가 동일한 계약을 갖도록 한다.
  - repository가 완성된 publishable Topic만 저장하는 현재 구조를 확인한 뒤 CHECK를 추가한다.
  - 불완전한 draft row를 먼저 저장하는 경로가 있다면 status별 제약이 필요한지 검토하고 실제 저장 흐름과 일치하도록 설계한다.
  - migration 정적 테스트에서 최소 기사 수, 최소 source 수와 두 count의 상대 관계 CHECK를 검증한다.
  - 기존 최소 기사 5개, 최소 source 2개 clustering 필터 테스트를 유지한다.
  - 실제 production migration은 Agent가 적용하지 않는다.

- [x] FIX-08: Weekly Topic 기사 rank와 역할 DB 제약 강화
  - 동일한 `weekly_topic_id` 안에서 `rank`가 중복되지 않도록 UNIQUE 제약을 추가한다.
  - 기존 `(weekly_topic_id, article_id)` UNIQUE 제약은 유지한다.
  - 대표 기사인 row는 반드시 Summary 근거 기사여야 한다.
  - `is_representative = true`이면서 `is_summary_evidence = false`인 모순 상태를 CHECK로 거부한다.
  - 상세 API가 `rank` 기준으로 안정적인 순서를 반환하는 기존 계약을 유지한다.
  - 대표 기사 정확히 1개와 Summary 근거 최대 5개처럼 row 집합 전체를 검사해야 하는 제약은 repository/model 검증으로 유지한다.
  - 단순 CHECK나 UNIQUE로 안정적으로 표현하기 어려운 집합 단위 제약을 무리하게 trigger로 구현하지 않는다.
  - migration 정적 테스트에서 `(weekly_topic_id, rank)` UNIQUE와 대표/근거 역할 CHECK를 검증한다.
  - repository model의 unique rank, 대표 기사와 Summary evidence 검증 테스트를 유지한다.
  - 실제 production migration은 Agent가 적용하지 않는다.

- [x] FIX-09: Weekly Topic status와 DB·API publish 계약 명확화
  - `weekly_topics.status`의 실제 허용값과 publish 가능한 상태를 repository와 API 기준으로 확인한다.
  - migration 기본값 `draft`와 repository insert에서 명시하는 status가 일치하는지 확인한다.
  - Topic status에 제한된 상태 집합이 존재한다면 DB CHECK를 추가한다.
  - `/weekly-topics/home`과 archive/detail API가 어떤 status를 공개하는지 문서화한다.
  - 성공 또는 부분 성공 run status와 개별 Topic publish status를 혼동하지 않도록 한다.
  - repository가 status를 항상 명시적으로 insert하는지 테스트로 확인한다.
  - 공개 가능한 status와 비공개 status가 API 테스트에서 구분되도록 한다.
  - 기존 3일 Topic status 계약과 다르게 설계한 경우 그 이유를 Weekly 설계 문서에 기록한다.

- [x] FIX-10: Task 문서 오타와 관련 문구 정리
  - `docs/tasks/feature-seven-day-topic-pipeline.md`에서 `시용 날짜 범위`를
    `표시용 날짜 범위`로 수정한다.
  - 이미 수정된 경우 실제 staged diff와 branch 파일을 확인하고 추가 변경하지 않는다.
  - 동일 문서와 Weekly 관련 문서에서 `시용`, 잘못된 날짜 범위 표현이나 유사 오타가 남아 있지 않은지 검색한다.
  - `week_start`는 월요일, `week_end`는 일요일 표시 날짜라는 표현을 유지한다.
  - 절대 처리 범위는 `window_start` 이상, `window_end` 미만임을 문서에서 일관되게 유지한다.

- [x] FIX-11: Weekly CronJob service account token 자동 mount 비활성화
  - Weekly Job은 Kubernetes API를 직접 호출하지 않으므로 Pod에 service account token을 mount하지 않는다.
  - Job template의 Pod spec에 `automountServiceAccountToken: false`를 추가한다.
  - 기존 `restartPolicy: Never`를 유지한다.
  - 기존 Secret, image, command, timezone, resource와 `/tmp` volume 설정을 변경하지 않는다.
  - 기존 `allowPrivilegeEscalation: false`, capability drop과
    `seccompProfile: RuntimeDefault` 설정을 유지한다.
  - manifest 테스트에서 `automountServiceAccountToken`이 명시적으로 `false`인지 확인한다.
  - `runAsNonRoot`와 `readOnlyRootFilesystem`은 image runtime 호환성을 확인하지 않고 즉시 추가하지 않는다.
  - Weekly image hardening이 필요한 경우 별도 작업으로 기록하되, 이번 Fix에서는 token mount 비활성화를 적용한다.

- [x] FIX-12: Weekly migration과 서비스 model 계약의 추가 정합성 검토
  - CodeRabbit가 직접 지적한 schema 제약을 적용한 뒤 migration, model, repository와 API 계약을 다시 비교한다.
  - `similarity` 값의 실제 범위가 `-1~1`인지 `0~1`인지 구현을 확인하고 명확한 범위가 있다면 DB CHECK 추가 여부를 결정한다.
  - `week_start`, `week_end`, `window_start`, `window_end`의 정확한 달력 주간 관계를 DB에서도 안전하게 표현할 수 있는지 검토한다.
  - timezone에 의존하는 복잡한 DB CHECK를 무리하게 추가하지 않고 application model 검증과 책임을 구분한다.
  - `finished_at >= started_at`과 같은 run 시간 관계 제약이 기존 3일 Topic과 달라질 필요가 있는지 검토한다.
  - 대표 기사 정확히 1개와 Summary 근거 최대 5개는 repository/model 검증으로 계속 보호한다.
  - 이번 작업 범위를 넘어서는 trigger, 범용 기간 Topic schema 통합이나 기존 3일 Topic migration 변경은 수행하지 않는다.
  - 추가 적용하거나 보류한 항목과 근거를 설계 문서와 PR 문서에 기록한다.

## Rejected or Deferred Suggestions

### Deferred: 검증 없이 `runAsNonRoot: true` 즉시 적용

현재 Docker image의 최종 `USER`, 실행 UID/GID와 runtime writable path를 별도로
검증하지 않고 `runAsNonRoot: true`를 적용하면 Weekly CronJob이 시작되지 않을 수
있다.

이번 Fix에서는 Kubernetes API를 사용하지 않는 workload에 대해 안전하게 적용할
수 있는 `automountServiceAccountToken: false`만 반영한다.

Image가 non-root 실행을 지원하는지 확인하고 Dockerfile 또는 전체 workload image
정책을 함께 변경해야 한다면 별도 container hardening 작업으로 진행한다.

### Deferred: 검증 없이 `readOnlyRootFilesystem: true` 즉시 적용

Weekly pipeline은 Python runtime, 원문 추출 library 또는 임시 파일 처리 과정에서
filesystem write가 필요할 수 있다.

현재 `/tmp` `emptyDir`가 존재하더라도 모든 쓰기 경로가 `/tmp`로 한정되는지
확인되지 않았다.

필요한 writable path와 image 동작을 검증한 뒤 API, Daily, 3일, Weekly workload를
포함하는 별도 image hardening 작업에서 적용한다.

### Deferred: 대표 기사 정확히 1개를 DB trigger로 강제

대표 기사 정확히 1개라는 제약은 여러 row를 함께 검사해야 하므로 단순 CHECK
constraint로 표현할 수 없다.

이번 Fix에서는 다음을 적용한다.

- 대표 기사는 Summary evidence여야 한다는 row-level CHECK
- Topic 내 rank UNIQUE
- repository/model에서 대표 기사 정확히 1개 검증
- 관련 회귀 테스트

이를 위해 별도 trigger를 추가하면 저장 transaction과 migration 복잡도가
과도하게 증가하므로 이번 작업에서는 보류한다.

### Deferred: Summary 근거 기사 최대 5개를 DB trigger로 강제

Topic당 Summary evidence 최대 5개라는 제약도 여러 row의 집계를 필요로 한다.

현재 repository/model에서 저장 전에 검증하고 테스트로 보호하므로 이번
migration에는 trigger를 추가하지 않는다.

### Deferred: 기존 3일 Topic migration에 동일 제약 역반영

Weekly migration에 추가하는 다음 제약을 기존 3일 Topic 테이블에도 즉시
추가하지 않는다.

- JSONB array CHECK
- 최소 기사·source 수 CHECK
- Topic 내 rank UNIQUE
- 대표 기사와 Summary evidence 관계 CHECK
- Topic status CHECK

기존 운영 DB와 3일 Topic contract에 영향을 줄 수 있으므로 별도 schema hardening
작업에서 실제 데이터 검사를 거쳐 진행한다.

### Rejected: 성공 run이면 모든 개별 Topic을 무조건 공개

Run의 `success` 또는 `partial_success`는 전체 실행 상태다.

개별 Topic의 publish 가능 여부를 대신하지 않으므로 Public Home API는 run
status와 Topic status를 모두 검사해야 한다.

### Rejected: Raw text loader 결과로 기존 원문 map 전체 교체

loader가 partial 또는 stale 결과를 반환할 수 있으므로 이미 확보된 유효 원문을
버리는 방식은 허용하지 않는다.

기존 원문과 loader 결과를 명시적인 우선순위에 따라 병합한다.

### Rejected: 날짜만 같으면 유효한 Weekly window로 허용

Weekly Topic은 rolling 168시간이 아니라 서울 기준 완료된 calendar week다.

따라서 월요일 정오부터 다음 월요일 정오까지와 같은 shifted window는 날짜 차이가
7일이어도 허용하지 않는다.

### Rejected: Application model 검증만 믿고 DB 제약을 추가하지 않음

Weekly migration은 아직 production DB에 적용되지 않았으며, 현재가 schema
계약을 강화하기 가장 안전한 시점이다.

단순하고 명확하게 표현할 수 있는 JSON type, 최소 count, rank와 역할 관계는
DB에서도 강제한다.

## Applied Changes

- `/weekly-topics/home`의 최신 공개 window 선택과 card query에 publishable Topic
  status인 `ready` 필터를 추가했다.
- 서울 기준 월요일 자정부터 다음 월요일 자정까지의 정확한 Weekly window를
  model에서 검증한다.
- Raw acquisition의 reused, extracted, failed, missing 상태를 상호 배타적으로
  검증하고 원문 map과 상태 목록의 모순을 차단한다.
- Weekly 최종 결과의 `success`, `partial_success`, `failed` 상태와
  saved/failed count 관계를 검증한다.
- 기존 raw text와 loader 결과를 병합하여 partial loader 응답으로 기존 원문이
  유실되지 않게 했다. 동일 article ID가 양쪽에 있으면 loader 재조회 값을 최신
  원문으로 우선한다.
- Weekly migration에 JSON array, 최소 기사·source 수, source/article 관계,
  Topic 내 rank UNIQUE, 대표/Summary evidence 역할 CHECK, Topic status CHECK,
  similarity 범위와 단순 날짜/run 시간 관계 CHECK를 추가했다.
- Weekly Topic status의 허용값과 publishable 상태 계약을 확인해 DB, repository,
  API와 문서에 일관되게 반영했다. Repository는 완성된 Topic을 `ready`로 저장하고
  `/weekly-topics/home`은 `ready`만 공개한다.
- Task 문서의 `시용` 오타는 이미 `표시용`으로 수정된 상태임을 검색으로 확인했고,
  Weekly 날짜 범위 문구는 설계·PR·devlog 문서에 맞춰 정리했다.
- Weekly CronJob에 `automountServiceAccountToken: false`를 추가했다.
- 관련 집중 테스트, 기존 Daily·3일 Topic 회귀 테스트, 전체 pytest/unittest,
  compileall과 `git diff --check`를 통과했다.
- Verification에는 실제 실행한 명령과 실제 결과만 기록했다.
- 실제 production migration, K3s apply와 운영 API 검증은 수행하지 않는다.

## Verification Required

### Weekly Home API 상태 필터 검증

```bash
python -m pytest \
  tests/test_weekly_topics_api.py \
  -v
```

확인 항목:

- 성공 run의 publishable Topic만 홈 card에 포함
- 부분 성공 run의 publishable Topic만 포함
- `draft`, `failed` 또는 비공개 상태 Topic 제외
- 최신 run에 공개 가능한 Topic이 없으면 이전 publishable window 선택 또는
  기존 빈 응답 정책 적용
- 공개 가능한 window가 없으면 정상 빈 응답
- `/weekly-topics/home` 정적 route 순서 유지
- 목록·상세 API 회귀 없음

### Weekly Context 및 Window 검증

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline.py \
  tests/test_run_weekly_topic_pipeline.py \
  -v
```

확인 항목:

- 서울 기준 월요일 00:00 시작
- 서울 기준 다음 월요일 00:00 종료
- `week_end = week_start + 6일`
- 정오부터 정오까지의 shifted window 거부
- UTC로 표현된 정상 KST 자정 window 허용
- 명시적인 `--week-start` 월요일 검증 유지
- 기본 실행이 가장 최근 완료 주간을 선택

### Raw acquisition 및 Summary 결과 검증

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline.py \
  -v
```

확인 항목:

- reused, extracted, failed, missing bucket 상호 배타성
- raw text와 failed/missing 상태 모순 거부
- reused/extracted article의 원문 존재
- 기존 raw text와 partial loader 결과 병합
- loader가 빈 결과를 반환해도 기존 원문 보존
- 원문 실패 시 다음 순위 관련 기사 fallback 유지
- Topic별 실패 격리 유지

### Run status 및 Count 정합성 검증

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  -v
```

확인 항목:

- `success`에서 실패 Topic 없음
- `partial_success`에서 저장·실패 Topic 각각 존재
- `failed`에서 저장 Topic 없음
- 정상 빈 결과의 성공 처리
- 모든 Topic 실패 시 기존 성공 window 결과 보존
- 일부 성공 시 성공 부분집합 저장
- count와 결과 목록 크기 일치
- 모순된 상태가 `ValueError`로 거부

### Migration 및 Repository 검증

```bash
python -m pytest \
  tests/test_weekly_topic_repository.py \
  -v
```

확인 항목:

- `key_points`, `keywords` JSON array CHECK
- `article_count >= 5`
- `source_count >= 2`
- `source_count <= article_count`
- `(weekly_topic_id, rank)` UNIQUE
- 대표 기사는 Summary evidence여야 한다는 CHECK
- Topic status CHECK를 적용한 경우 허용 상태 검증
- 기존 window advisory lock
- 기존 결과 삭제와 신규 결과 삽입 원자성
- insert 실패 rollback
- 정상 빈 결과 교체
- 동일 window 재실행 idempotency

Migration 정적 검색:

```bash
rg -n \
  "jsonb_typeof|article_count|source_count|weekly_topic_id, rank|is_representative|status" \
  db/migrations/008_create_weekly_topic_tables.sql \
  tests/test_weekly_topic_repository.py
```

### CronJob manifest 검증

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

확인 항목:

- `automountServiceAccountToken: false`
- 월요일 00:30 `Asia/Seoul` schedule 유지
- 전용 Weekly runner와 argument 유지
- `DATABASE_URL`, Summary API key Secret 유지
- embedding API key 미주입
- `restartPolicy: Never`
- `/tmp` `emptyDir`와 volume mount 유지
- `allowPrivilegeEscalation: false`
- capability drop 유지
- `RuntimeDefault` seccomp 유지
- resource와 deadline 설정 유지

### Weekly 전체 집중 테스트

```bash
python -m pytest \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  tests/test_weekly_topics_api.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

### 기존 Daily Topic 회귀

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_daily_topic_pipeline_configuration.py \
  -v
```

확인 항목:

- Daily Topic 실행 진입점과 CronJob 계약 유지
- 공통 candidate/selection helper 변경에 따른 회귀 없음
- Daily Topic 기사 선정과 정렬 결과 유지

### 기존 3일 Topic 회귀

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

확인 항목:

- 최근 72시간 rolling window 계약 유지
- 공통 candidate helper 사용 후 후보 조회 결과 유지
- 기존 3일 Topic 저장, Summary, API와 CronJob 계약 유지
- 기존 3일 Topic migration 변경 없음

### 전체 회귀

```bash
python -m pytest
python -m unittest discover -s tests
python -m compileall app scripts tests
git diff --check
```

### 문서 정합성

```bash
rg -n \
  "시용 날짜|표시용 날짜|draft|publishable|weekly-topics/home|Asia/Seoul|00:00" \
  docs README.md \
  app/routers/weekly_topics.py \
  app/services/weekly_topic_pipeline
```

확인 항목:

- `시용 날짜` 오타 없음
- Weekly 표시 범위와 절대 window 설명 일치
- Topic publishable status 설명 일치
- Home API가 run status와 Topic status를 모두 확인한다고 문서화
- 서울 기준 월요일 자정 경계 설명 일치

### Git 및 변경 범위 확인

```bash
git diff --check
git diff --stat
git status --short
```

기존 Daily와 3일 Topic의 금지 영역 또는 불필요한 schema 변경이 없는지 확인한다.

```bash
git diff -- \
  db/migrations/007_create_three_day_topic_tables.sql \
  scripts/run_daily_topic_pipeline.py \
  scripts/run_three_day_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml \
  k8s/news-three-day-topic-pipeline-cronjob.yaml
```

### Kubernetes client-side dry-run

사람이 실행한다.

```bash
kubectl apply --dry-run=client \
  -f k8s/news-weekly-topic-pipeline-cronjob.yaml
```

기대 결과:

```text
cronjob.batch/news-weekly-topic-pipeline created (dry run)
```

### Kubernetes server-side dry-run

사람이 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-weekly-topic-pipeline-cronjob.yaml
```

### Production 수동 검증

다음 작업은 Agent가 수행하지 않는다.

- `008_create_weekly_topic_tables.sql` Supabase 또는 production DB 적용
- 적용 후 table, CHECK, UNIQUE와 index 확인
- K3s CronJob apply
- 수동 Weekly Job 생성
- Pod log와 run 상태 확인
- 실제 Weekly Topic 생성 및 저장 확인
- `/weekly-topics`, `/weekly-topics/home`,
  `/weekly-topics/{topic_id}` 운영 API 확인
- 동일 주간 재실행 idempotency 확인
