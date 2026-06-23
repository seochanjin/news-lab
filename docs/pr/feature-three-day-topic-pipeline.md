# 3일 Topic pipeline·저장·API·CronJob 구축

## 작업 내용

- 최근 72시간 기사를 기존 Daily Topic 결과가 아닌 원본 기사와 저장된 `article_embeddings`로 직접 재클러스터링하는 3일 Topic pipeline을 추가했다.
- 3일 Topic 전용 저장 구조와 실행 이력을 추가하고 동일 window 재실행 시 결과를 원자적으로 교체하도록 했다.
- 3일 Topic archive, home, detail read API를 추가했다.
- Daily Topic 실행 이후 별도로 동작하는 3일 Topic CLI와 K3s CronJob manifest를 추가했다.
- pipeline 설계, migration 적용, CronJob 운영과 production 확인 절차를 README, Architecture, Runbook과 전용 설계 문서에 반영했다.

## 주요 변경 사항

### 72시간 실행 범위와 후보 조회

- `Asia/Seoul` 기준으로 `window_end`를 한 번 결정하고 `[window_start, window_end)` 72시간 범위를 모든 단계에 전달한다.
- 기사 시간은 `coalesce(published_at, created_at)` 기준으로 조회한다.
- CLI의 명시적 `--window-end`는 timezone-aware ISO 8601 값만 허용한다.
- 후보 기사의 현재 title/summary source hash, embedding metadata와 vector 차원을 검증한다.
- 호환되는 기존 `article_embeddings`만 사용하며 embedding provider 호출이나 insert/update를 수행하지 않는다.
- embedding이 없거나 오래됐거나 metadata·vector가 호환되지 않는 기사는 제외하고 `missing_embedding_count`에 기록한다.

### 재클러스터링과 기사 선정

- 저장 embedding을 사용해 3일 window 기사 자체를 다시 clustering한다.
- 최대 후보 기사, 최대 Topic, similarity threshold, 관련 기사와 Summary 근거 기사 상한을 3일 pipeline 설정으로 독립 관리한다.
- 대표 기사, 관련 기사와 Summary 근거 기사 집합의 포함 관계를 보장한다.
- 관련 기사 순위, source 다양성, URL과 정규화 제목 중복 제거를 사용해 Summary 근거 기사를 결정론적으로 선택한다.
- 기간에 독립적인 기사 선정 helper를 `app/services/topic_pipeline/selection.py`로 공통화했다.
- Daily Topic은 공통 helper를 호출하도록 내부 구현만 변경했으며 외부 결과 모델, 실행 CLI와 CronJob 계약은 유지했다.

### 원문 확보와 3일 Summary

- Summary 근거 기사만 저장 원문 재사용과 지연 추출 대상으로 사용한다.
- 기사 단위 원문 확보 실패와 Topic 단위 Summary 실패를 격리해 다른 Topic 처리를 계속한다.
- 최근 72시간 동안의 변화와 진행 상황을 설명하는 `three-day-flow-v1` prompt와 strict schema를 사용한다.
- 기사 시각과 bounded raw text를 포함한 versioned Summary input hash를 생성한다.
- 실제 provider 입력에 사용된 기사만 `is_summary_evidence=true`로 저장한다.

### 저장과 idempotency

- 실행 이력 생성·종료 transaction과 결과 교체 transaction을 분리했다.
- provider 및 원문 작업이 끝난 뒤 advisory transaction lock을 획득하고 동일 window의 기존 결과 삭제와 신규 결과 삽입을 한 transaction에서 수행한다.
- 일부 Topic만 성공하면 성공 부분집합으로 교체하고 run 상태를 `partial_success`로 기록한다.
- 모든 Topic이 실패하면 기존 성공 결과를 보존하고 run을 `failed`로 종료한다.
- 동일 window 결과는 교체하되 `three_day_topic_runs` 실행 감사 이력은 보존한다.
- 빈 성공 결과 교체를 허용하며 저장 도중 실패하면 전체 결과 교체를 rollback한다.

### 실행 진입점과 CronJob

- `scripts/run_three_day_topic_pipeline.py`를 추가했다.
- 기본 모드는 dry-run이며 `--execute`에서만 저장과 필요한 원문 추출을 수행한다.
- execute 모드는 Summary provider 설정과 key를 요구하며 embedding provider option은 제공하지 않는다.
- 단계별 후보, embedding, 누락, cluster, Topic 저장·실패 수로 run 종료 상태를 기록한다.
- `news-three-day-topic-pipeline` CronJob을 추가했다.
  - Schedule: `05:00 Asia/Seoul`
  - 기존 Daily Topic 이후 실행
  - `concurrencyPolicy: Forbid`
  - 기존 image, Secret reference와 runtime pattern 재사용
  - history, resource, deadline과 job 안전 설정 포함

### 문서

- `README.md`에 3일 Topic API와 로컬 실행 진입점을 추가했다.
- Architecture index와 pipeline, database, backend API, K3s runtime 문서를 갱신했다.
- Runbook index와 CronJob, database check, routine check 절차를 갱신했다.
- `docs/design/three-day-topic-pipeline.md`에 시간 범위, 단계 경계, 저장 원자성, idempotency와 운영 판단 기준을 기록했다.

Approved Fixes 문서에는 승인되어 적용된 항목이 없다.

## 추가/변경된 API

다음 read API를 추가했다.

### `GET /three-day-topics`

3일 Topic archive 목록을 pagination과 filter로 조회한다.

- Query parameter
  - `page`
  - `page_size`
  - `reference_date`
  - `date_from`
  - `date_to`
  - `keyword`
  - `status`
- Response
  - `page`
  - `page_size`
  - `total`
  - `has_next`
  - `items`
- Topic 정렬
  - `reference_date`
  - `window_end`
  - `id`
  - 최신순

### `GET /three-day-topics/home`

성공 또는 부분 성공한 최신 window 하나의 경량 Topic card payload를 반환한다.

- 전체 pagination count와 관련 기사 join을 수행하지 않는다.
- 결과가 없으면 `reference_date`, `window_start`, `window_end`가 `null`이고 `items`가 빈 정상 응답을 반환한다.
- 정적 `/home` route를 동적 `/{topic_id}`보다 먼저 등록했다.

### `GET /three-day-topics/{topic_id}`

단일 Topic과 연결 기사를 반환한다.

- 대표 기사와 Summary 근거 여부 제공
- `rank`, `article_id` 순서로 기사 정렬
- 존재하지 않는 Topic은 기존 API style의 404 반환

기존 `/topics`, `/topics/home`, `/topics/{topic_id}` endpoint와 response contract는 변경하지 않았다.

## DB 변경 사항

Migration 파일을 추가했다.

- `db/migrations/007_create_three_day_topic_tables.sql`

추가 table:

### `three_day_topics`

- 3일 window와 Topic 결과 저장
- `reference_date`, `window_start`, `window_end`
- 제목, 요약, keywords와 기사·source 집계
- provider, model, prompt version과 Summary input hash
- status와 생성·수정 시각
- 최신 window 조회 및 중복 방지를 위한 constraint와 index 포함

### `three_day_topic_articles`

- Topic과 기존 `articles` 관계 저장
- rank, similarity, 대표 기사 여부와 Summary 근거 여부 저장
- `UNIQUE (three_day_topic_id, article_id)`로 중복 관계 방지

### `three_day_topic_runs`

- 실행 window, 상태와 단계별 count 저장
- `running`, `success`, `partial_success`, `failed` 상태 기록
- 오류 요약과 시작·종료 시각 보존

기존 `topics`, `topic_articles`, `article_embeddings`와 기사 데이터 schema는 변경하지 않았다.

Migration SQL은 생성만 했으며 Supabase 또는 production DB에 적용하지 않았다.

## README 영향

README를 변경했다.

- 3일 Topic API endpoint 안내 추가
- 3일 Topic pipeline 로컬 dry-run 진입점 추가
- 전용 migration과 사람이 수행해야 하는 운영 반영 경계 안내

신규 pipeline과 API가 repository의 주요 실행·조회 진입점에 해당하므로 Architecture와 Runbook만이 아니라 README에도 최소 사용 정보를 반영했다.

## 테스트

`docs/verification/feature-three-day-topic-pipeline.md`에 기록된 실제 최종 결과:

- 3일 pipeline과 실행 진입점 집중 테스트
  - 20 passed
- 3일 Topic API 테스트
  - 6 passed
- 3일 CronJob manifest 테스트
  - 3 passed
- 기존 Daily 실행·CronJob 회귀
  - 23 passed
- 전체 `pytest`
  - 261 passed in 8.94s
- 전체 `unittest`
  - 261 tests in 6.604s, OK
- `python -m compileall app scripts tests`
  - 통과
- `git diff --check`
  - 통과
- 전용 table, API route와 CronJob 이름·schedule 문서 일관성 검색
  - 통과
- 기존 Daily 실행 script와 CronJob manifest
  - diff 없음

검증 과정에서 발견된 실패와 해결도 verification에 보존했다.

- UNIT-02 repository 초기 테스트에서 1건 실패
  - repository 계약 수정 후 migration 회귀 포함 11건 통과
- UNIT-04 정적 검사에서 Daily selection 파일 끝의 불필요한 빈 줄 발견
  - 빈 줄 제거 후 compileall과 diff 검사 통과
- UNIT-07 최초 실행 진입점 집중 테스트에서 CLI 계약 불일치 발견
  - 수정 후 3일 실행·stage 20건과 Daily 회귀 23건 통과

테스트는 가짜 SQLAlchemy engine/connection, 메모리 vector, mock extractor·HTTP와 로컬 YAML parsing을 사용했다. 실제 DB write, embedding·Summary provider, 원문 추출과 Kubernetes command는 실행하지 않았다.

## 확인 결과

- 서울 기준 동일한 72시간 window가 pipeline 전체에서 유지된다.
- 기존 저장 embedding만 사용하며 누락 embedding은 실행 실패 대신 통계로 분리된다.
- 최근 72시간 기사를 Daily 결과와 독립적으로 재클러스터링한다.
- 대표 기사, Summary 근거 기사와 관련 기사 집합 계약이 유지된다.
- Summary 근거 기사에만 원문 확보와 provider 입력을 수행한다.
- Topic별 실패를 격리하고 성공 부분집합을 저장할 수 있다.
- 동일 window 재실행은 중복 누적 없이 transaction으로 원자 교체된다.
- 전부 실패하면 기존 성공 결과를 먼저 삭제하지 않는다.
- archive, home, detail API와 빈 응답·404·route 순서가 검증됐다.
- 기존 Daily Topic의 외부 CLI, CronJob manifest와 `/topics` API 계약은 유지된다.
- DB migration, production API와 K3s 운영 검증은 수행되지 않았다.

## 비고

- 현재 working tree의 일반 `git diff`는 비어 있으며, PR 변경 범위는 `main...HEAD` 기준 41개 파일이다.
- 다음 작업은 사람이 수행해야 한다.
  - `007_create_three_day_topic_tables.sql` migration 검토 및 Supabase 적용
  - 적용 전후 schema, constraint와 index 확인
  - Kubernetes client/server-side manifest dry-run
  - K3s manifest apply와 필요 시 rollout 판단
  - 수동 Job 실행과 run log·DB 결과 확인
  - production `/three-day-topics`, `/home`, detail API 확인
- `kubectl apply --dry-run=client`도 현재 금지 규칙에 따라 실행하지 않았으며 로컬 manifest 테스트로만 검증했다.
- 7일 Topic pipeline과 frontend 변경은 이번 범위에 포함하지 않았다.
- Git push, PR merge, production deployment, K3s rollout과 production verification 완료를 주장하지 않는다.
