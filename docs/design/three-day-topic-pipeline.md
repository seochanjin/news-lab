# 3일 Topic Pipeline 저장·실행 계약

## 문서 목적

이 문서는 `feature/three-day-topic-pipeline`의 설계와 구현 결과를 함께
정리한다. 기존 Daily Topic과 article embedding 구현을 기준으로 3일 Topic의
시간 범위, 입력, 단계 경계, 저장 원자성, 실행 상태와 재사용 범위를 고정하고,
UNIT-02부터 UNIT-07에서 구현된 실제 경로를 기록한다.

Migration과 CronJob manifest는 repository에만 추가했다. Production DB 적용,
K3s object 생성·변경과 운영 검증은 사람이 수행한다.

## 조사한 현재 구조

### Daily Topic 실행 계약

현재 진입점은 `scripts/run_daily_topic_pipeline.py`이며 다음 네 단계를 한
`PipelineContext`로 조정한다.

```text
최근 기사 조회
→ embedding 생성·갱신·재사용
→ clustering 및 대표/관련/Summary 기사 선정
→ Summary 기사 원문 확보
→ Summary 생성 및 topics/topic_articles 저장
```

현재 context는 실행 시작 시 `Asia/Seoul` 기준 `pipeline_date`를 한 번 계산한다.
그러나 기사 조회 SQL은 DB의 `now()`와 `window_hours`를 사용하므로 명시적인
`window_start`, `window_end`를 단계 전체에 전달하지 않는다. 3일 Topic은 이
부분을 그대로 재사용하지 않는다.

Daily 저장은 `summary_input_hash`, provider, model 기준 upsert 후 해당 Topic의
`topic_articles`를 교체한다. 이 계약은 개별 Summary 입력의 중복 저장은 막지만
동일한 72시간 window 전체를 하나의 결과 세대로 교체하는 계약은 제공하지
않는다.

### Article embedding 저장 계약

`article_embeddings`는 다음 key별 최신 embedding 한 건을 유지한다.

```text
article_id + provider + model + source_text_type
```

현재 기본 호환 조건은 다음과 같다.

```text
provider = openai
model = text-embedding-3-small
dimension = 1536
source_text_type = title_summary
```

`source_text_hash`는 공백을 정규화한 article title과 summary의 SHA-256 값이다.
Daily Topic은 hash가 같으면 vector를 재사용하고, 없거나 달라지면 embedding
provider를 호출해 생성 또는 갱신한다.

3일 Topic은 provider 호출을 허용하지 않는다. 따라서 저장 row가 없거나 호환
조건이 다르거나 현재 title/summary로 계산한 hash와 다르면 해당 기사를
clustering 입력에서 제외해야 한다.

### 재사용 가능한 처리

다음 로직은 DB table이나 Daily 날짜 의미에 직접 의존하지 않아 재사용 후보로
본다.

- `app.utils.topic_grouping.group_articles`
- `app.utils.topic_representatives.select_topic_representatives`
- 대표 기사 우선의 관련 기사 정렬
- URL과 정규화 제목 중복을 제거하는 Summary 근거 기사 선정 정책
- 선택 기사에 한정한 raw text 재사용 및 지연 추출
- Topic별 Summary provider 실패 격리 패턴

다음 로직은 3일 계약에 그대로 재사용하지 않는다.

- embedding 생성·갱신을 포함하는 Daily `embedding_stage`
- DB `now()`로 상대 범위를 계산하는 기존 후보 조회
- 기존 `topics`, `topic_articles` save plan과 upsert query
- 단일 시점 Topic 설명을 전제로 한 기존 Summary prompt
- Daily CLI의 provider flag와 24시간 전용 argument 계약

공통화는 순수 처리 로직에 한정한다. Daily public 함수, 결과 통계, CLI argument,
CronJob command와 저장 의미는 유지한다.

## 3일 실행 context 계약

### 시간 해석

`ThreeDayPipelineContext`는 pipeline 시작 시 한 번 생성하고 모든 단계에 같은
instance를 전달한다.

필수 값:

```text
reference_date
business_timezone
started_at_utc
started_at_local
window_start
window_end
window_hours
window_source
```

정책:

1. `business_timezone` 기본값은 `Asia/Seoul`이다.
2. 기본 `window_end`는 실행 시작 absolute instant다.
3. 재현 실행을 위해 timezone-aware ISO 8601 `window_end`를 명시적으로 주입할
   수 있어야 한다. naive datetime은 거부한다.
4. 주입된 값은 UTC absolute instant로 정규화하되 서울 local 표현도 context에
   보관한다.
5. `window_start = window_end - 72 hours`다.
6. 후보 범위는 `[window_start, window_end)` 반개구간이다.
7. `reference_date`는 `window_end`의 `Asia/Seoul` 날짜다.
8. candidate 조회, 로그, run row, Topic row와 재실행 key는 모두 context의 같은
   `window_start`, `window_end`를 사용한다.

반개구간은 인접 실행 경계의 기사가 양쪽 window에 동시에 포함되는 모호성을
없앤다. 서울은 현재 DST를 사용하지 않지만 계산은 timezone-aware datetime으로
유지한다.

### 기사 시간 기준

현재 분석 도구와 Daily 후보 조회의 published 기준을 유지한다.

```sql
coalesce(a.published_at, a.created_at)
```

이를 `analysis_time`으로 사용한다. 즉 `published_at`이 있으면 우선하고, 없으면
수집 시각인 `created_at`을 fallback으로 사용한다. 정렬은
`analysis_time desc, article_id desc`로 결정론적으로 수행하고, 최대 후보 기사
상한은 3일 전용 설정으로 적용한다.

## 후보 및 embedding 조회 계약

후보 조회는 개념적으로 두 집합을 구분한다.

1. window와 최대 기사 수를 적용한 전체 article 후보
2. 그 후보 중 호환되고 최신인 저장 embedding이 있는 clustering 입력

필수 필드는 다음과 같다.

```text
article:
  id, source, title, url, summary, source_category,
  published_at, created_at, analysis_time

embedding:
  provider, model, dimension, source_text_type,
  source_text_hash, embedding
```

저장 embedding 사용 조건:

```text
article_id 일치
provider/model/dimension/source_text_type이 3일 설정과 일치
저장 source_text_hash가 현재 title/summary 입력 hash와 일치
vector dimension이 설정값과 일치
```

위 조건을 충족하지 않는 기사는 pipeline 실패가 아니라 누락이다. 신규 embedding
provider 호출, embedding insert와 embedding update는 금지한다.

통계 관계:

```text
candidate_count = embedding_count + missing_embedding_count
clustering_input_count = embedding_count
```

로그에는 전체 누락 수와 가능한 범위에서 `missing_row`, `stale_hash`,
`incompatible_metadata`, `invalid_vector`의 안전한 분류를 남긴다. credential,
embedding vector 전체와 기사 원문은 기록하지 않는다.

## Pipeline 단계 계약

```text
context 확정 및 run 시작 기록
→ 후보와 저장 embedding 조회
→ 72시간 기준 clustering
→ 대표/관련/Summary 근거 기사 선정
→ Summary 근거 기사 원문 확보
→ 3일 흐름 Summary 생성
→ window 결과 원자적 교체
→ run 종료 상태와 통계 기록
```

### Candidate stage

- context의 window만 사용한다.
- Daily Topic 결과 table을 읽지 않는다.
- `article_embeddings`를 read-only로 조회한다.
- embedding 누락은 기사 단위로 제외하고 통계에 반영한다.
- 정상 vector가 2건 미만이면 빈 clustering 결과로 진행한다.

### Topic selection stage

- `group_articles`와 대표 기사 선정의 순수 로직을 재사용하는 것을 우선한다.
- 최대 후보 기사 수, threshold, 최대 Topic 수, 관련 기사 수와 Summary 기사
  수는 모두 3일 전용 설정으로 둔다.
- 대표 기사는 관련 기사에 포함되고 Summary 근거 기사에도 포함된다.
- Summary 근거 기사는 관련 기사의 부분집합이다.
- 초기 정렬은 Daily와 같은 다음 순서를 출발점으로 사용한다.

```text
article_count desc
source_count desc
average similarity desc
latest analysis_time desc
deterministic candidate id asc
```

72시간 시간 흐름을 반영하는 추가 점수는 실제 데이터 검증 없이 UNIT-01에서
도입하지 않는다. 별도 정책을 추가할 경우 3일 설정과 테스트로 Daily와 분리한다.

### Raw acquisition stage

- 관련 기사 전체가 아니라 Summary 근거 기사만 조회·추출 대상이다.
- 저장된 `raw_articles.raw_text`를 우선 재사용한다.
- execute 모드에서 원문이 없는 Summary 근거 기사만 지연 추출한다.
- 기사 하나의 추출 실패는 다른 기사와 Topic 처리를 중단하지 않는다.
- Topic에 사용할 수 있는 원문이 하나도 없으면 그 Topic은 저장 후보에서
  제외되고 Topic 실패 또는 skip 통계에 반영된다.

### Summary stage

- 3일 전용 prompt와 명시적 `prompt_version`을 사용한다.
- 초기 prompt version은 `three-day-flow-v1`로 정의한다.
- 입력에 기사별 `published_at` 또는 fallback `analysis_time`, source, title,
  bounded raw text를 포함한다.
- 출력은 사건의 단일 상태보다 72시간의 변화, 진행 순서, 여러 출처가 공통으로
  확인한 내용과 불확실성을 설명해야 한다.
- Topic별 provider 예외를 격리하고 나머지 Topic을 계속 처리한다.
- `summary_input_hash`는 사용 article ID, bounded raw text와 시간 metadata를
  결정론적으로 정렬한 payload에 `prompt_version`을 포함해 계산한다.

### Persistence stage

provider 호출과 raw extraction은 DB 결과 교체 transaction 밖에서 모두 끝낸다.
그 후 동일 window 결과는 한 transaction에서 다음 순서로 교체한다.

```text
window 단위 transaction/advisory lock 획득
→ 기존 window의 three_day_topics 삭제
→ 신규 three_day_topics 삽입
→ 신규 three_day_topic_articles 삽입
→ commit
```

중간 insert가 실패하면 transaction 전체를 rollback하므로 기존 성공 결과가
유지된다. 기존 결과를 먼저 commit한 delete로 제거해서는 안 된다.

선택된 Topic 중 일부의 원문 확보 또는 Summary가 실패해도 성공 Topic 처리는
계속한다. 하나 이상의 Topic이 성공하면 성공한 부분집합을 위 transaction으로
교체하고 run을 `partial_success`로 기록한다. 성공 Topic이 하나도 없고
Topic 실패가 있으면 결과를 교체하지 않고 run을 `failed`로 기록한다.

후보 또는 cluster가 정상적으로 0건인 실행은 오류가 아니다. `success` run으로
기록하고 동일 window의 기존 Topic을 빈 결과로 교체할 수 있다. 이 정책은
재실행 결과가 현재 입력 상태를 반영하게 한다.

## 저장 schema 계약

실제 SQL은 UNIT-02에서 작성한다. 최소 column은 Task를 따르며 아래 제약을
추가 기준으로 사용한다.

### `three_day_topic_runs`

한 실행 시도마다 row 하나를 먼저 생성한다. 동일 window 재실행 이력을 보존해야
하므로 window에 unique constraint를 두지 않는다.

상태:

```text
running
success
partial_success
failed
```

종료 계약:

- 시작 시 `running`, `started_at`과 context 값을 기록한다.
- 정상 종료 시 모든 count, `finished_at`, 최종 status를 기록한다.
- stage 공통 실패 시 짧고 민감정보가 없는 `error_message`와 `failed`를 기록한다.
- run 이력 기록 transaction과 결과 교체 transaction은 분리한다.
- process 강제 종료로 남은 `running` 판정과 정리는 후속 운영 정책으로 남긴다.

### `three_day_topics`

필수 column은 Task의 정의를 따른다. 한 window에 여러 Topic이 존재하므로
`window_start`, `window_end`만 unique로 만들지 않는다.

권장 추가 column:

```text
topic_candidate_id
run_id
key_points
confidence
```

제약:

```text
window_start < window_end
reference_date = Asia/Seoul 기준 window_end 날짜는 application 계약으로 검증
unique (window_start, window_end, topic_candidate_id)
```

`run_id`는 어떤 실행이 현재 결과를 생성했는지 추적하기 위한
`three_day_topic_runs` foreign key다. 결과 교체 시 과거 Topic row는 삭제되지만
run 이력은 보존한다.

### `three_day_topic_articles`

필수 관계:

```text
unique (three_day_topic_id, article_id)
rank >= 1
대표 기사 1건
is_summary_evidence=true이면 관련 기사 row에 포함
대표 기사도 is_summary_evidence=true
```

DB constraint만으로 부분집합과 대표 기사 1건을 모두 표현하기보다 save plan
검증과 테스트로 먼저 보장하고, 기본 unique/check/foreign key를 migration에
둔다. 관계 조회 순서는 `rank asc, article_id asc`다.

## Idempotency 및 동시 실행

- 동일 `window_start`, `window_end` 재실행은 이전 Topic set을 원자적으로
  교체하므로 활성 결과가 중복 누적되지 않는다.
- `reference_date`만 같은 서로 다른 window는 허용한다. 실제 identity는 absolute
  `window_start`, `window_end`다.
- CronJob은 `concurrencyPolicy: Forbid`를 사용한다.
- 수동 실행과 CronJob 경합까지 막기 위해 persistence transaction에서 window
  기반 PostgreSQL advisory transaction lock을 사용한다.
- Topic insert는 `(window_start, window_end, topic_candidate_id)` unique
  constraint로 방어한다.
- 재실행마다 run row는 추가된다. 이는 결과 중복이 아니라 실행 감사 이력이다.

## CLI 및 실행 결과 계약

후속 진입점 `scripts/run_three_day_topic_pipeline.py`는 Daily script와 분리한다.
기본은 dry-run이며 DB 결과 교체와 지연 원문 추출은 `--execute`가 있을 때만
허용한다.

필수 3일 전용 설정:

```text
--window-end
--max-articles
--similarity-threshold
--max-topics
--max-related-articles-per-topic
--max-summary-articles-per-topic
--max-raw-chars-per-article
--summary-model
--execute
```

`--window-hours`를 노출한다면 값은 72로 고정한다. embedding provider를 켜는
option은 제공하지 않는다.

실행 결과와 안전한 로그의 최소 통계:

```text
reference_date
window_start
window_end
candidate_count
embedding_count
missing_embedding_count
clustering_input_count
cluster_count
selected_topic_count
related_article_count
summary_article_count
raw_reused_count
raw_extracted_count
raw_failed_count
raw_missing_count
saved_topic_count
failed_topic_count
run_status
run_id
pipeline_elapsed_seconds
```

## API read 계약에 미치는 영향

API는 `three_day_topics` 계열만 읽고 기존 `/topics`를 변경하지 않는다.

- archive는 `reference_date desc, window_end desc, id desc`로 정렬한다.
- home은 최신 publishable window 하나의 Topic만 반환한다.
- detail 관련 기사는 `rank asc, article_id asc`로 반환한다.
- `partial_success` 결과도 publishable하며 각 Topic의 `status`는 저장 가능한
  결과 상태를 나타낸다.
- run 이력과 오류는 현재 Task의 공개 API 범위가 아니며 Topic API payload에
  노출하지 않는다.

## 검토한 대안과 선택 근거

### Daily Topic 결과 재집계

거부한다. 1일 Topic 선정에서 탈락한 기사와 cluster 관계를 복원할 수 없고 Task의
직접 재클러스터링 요구를 위반한다.

### 3일 pipeline에서 누락 embedding 생성

거부한다. 실행 비용과 실패 의미가 Daily embedding 생성 정책과 결합되고
“기존 embedding만 사용” 계약을 위반한다. 누락은 명시적으로 집계한다.

### DB `now() - interval '72 hour'`

거부한다. 단계별 query 시각이 달라지고 재현 실행이 어렵다. application에서
한 번 만든 bound parameter를 모든 query와 저장에 사용한다.

### 기존 Topic을 먼저 삭제한 뒤 처리

거부한다. provider 또는 insert 실패 시 기존 성공 결과가 사라진다. 외부 작업을
먼저 끝내고 짧은 교체 transaction을 사용한다.

### 결과 generation을 계속 누적하고 API에서 최신 run만 선택

현재는 선택하지 않는다. rollback은 단순하지만 동일 window 결과가 계속
누적되고 retention과 publishable generation 관리가 추가된다. 실행 감사는
`three_day_topic_runs`에 보존하고 활성 Topic set만 교체한다.

### Daily stage package 전체 복사

거부한다. 정책 drift와 수정 중복이 커진다. 순수 clustering/선정 helper를
재사용하거나 필요한 최소 공통 계층만 추출한다.

## UNIT-02 구현 결과

`db/migrations/007_create_three_day_topic_tables.sql`에 전용 실행 이력, Topic,
기사 관계 table과 조회 index를 추가했다. Migration은 repository에만
추가했으며 Supabase 또는 production DB에는 적용하지 않았다.

저장 계층은 다음 파일로 분리했다.

```text
app/services/three_day_topic_pipeline/models.py
app/services/three_day_topic_pipeline/repository.py
```

Model은 DB transaction 전에 다음 계약을 검증한다.

- timezone-aware인 정확한 72시간 window
- `window_end`의 `Asia/Seoul` 날짜와 일치하는 `reference_date`
- `candidate_count = embedding_count + missing_embedding_count`
- 관련 기사 ID와 rank 중복 금지 및 1부터 연속된 rank
- Topic별 대표 기사 정확히 1건
- 대표 기사의 Summary 근거 기사 포함

Repository는 engine을 주입받고 세 종류의 write를 제공한다.

```text
create_run
→ running 이력을 별도 transaction으로 commit

replace_window_topics
→ window advisory transaction lock
→ 기존 window Topic 삭제
→ 신규 Topic 및 기사 관계 삽입
→ 한 transaction으로 commit 또는 rollback

finish_run
→ running 이력을 최종 status와 count로 별도 transaction에서 종료
```

빈 Topic 결과도 `replace_window_topics`에서 lock과 delete를 수행해 정상적인 빈
세대로 교체한다. 신규 insert 실패 시 기존 delete와 신규 insert가 함께
rollback된다. Candidate 조회, clustering, Summary 생성과 repository 호출
orchestration은 UNIT-03 이후 범위로 남겼다.

## UNIT-03 구현 결과

`ThreeDayPipelineContext`가 실행 시작 시 서울 기준일과 UTC의 정확한 72시간
반개구간을 한 번 확정한다. Candidate stage는 이 범위를 bind parameter로
사용해 `coalesce(published_at, created_at)` 기준 기사를 조회한다.

`article_embeddings`는 read-only로 조회하며 provider, model, dimension,
source type, 현재 title/summary hash와 vector 유효성이 모두 맞는 row만
clustering 입력으로 재사용한다. 누락과 불일치는 `missing_row`,
`incompatible_metadata`, `stale_hash`, `invalid_vector`로 분류하고 provider
호출이나 embedding 저장은 수행하지 않는다.

## UNIT-04 구현 결과

3일 전용 선정 단계는 다음 파일에 구현했다.

```text
app/services/three_day_topic_pipeline/topic_selection_stage.py
```

입력은 UNIT-03의 `ThreeDayCandidateStageResult`이며 Daily Topic table이나 결과를
조회하지 않는다. 정상 embedding이 두 건 이상이면 기존
`group_articles`와 `select_topic_representatives`를 호출하고, 두 건 미만이면
오류 없이 빈 선정 결과를 반환한다.

다음 정책은 기간에 독립적인 순수 처리이므로 공통 package로 추출했다.

```text
app/services/topic_pipeline/selection.py
```

- Topic 정렬: 기사 수, 출처 수, 평균 유사도, 최신 기사 시각, candidate ID
- grouping 결과에 원본 URL 보강
- 관련 기사 순서를 유지한 중복 없는 ID 수집
- 대표 후보 순위 기반 Summary 근거 기사 선정
- 동일 URL 또는 정규화 제목 중복 제외

Daily stage도 같은 helper를 사용하도록 내부 호출만 변경했다. Daily public 함수,
결과 model, 설정 fallback, Reference Topic과 실행 script 계약은 유지한다.

3일 단계의 `similarity_threshold`, 최대 Topic 수, Topic별 관련 기사 수와 Summary
근거 기사 수는 명시적인 3일 전용 인자로 받는다. Summary 상한이 관련 기사
상한보다 큰 설정은 부분집합 계약을 위반하므로 실행 전에 거부한다.

`ThreeDayTopicSelectionResult`는 선택 Topic과 함께 다음 집합 관계를 검증한다.

```text
대표 기사 ⊆ Summary 근거 기사 ⊆ 관련 기사
```

원문 조회, Summary provider 호출, `ThreeDayTopicArticleRecord` 변환과 DB 결과
교체는 UNIT-05 범위로 남겼다.

## UNIT-05 구현 결과

선정된 Summary 근거 기사만 원문 단계에 전달한다. 저장 원문을 먼저 조회하고,
execute 모드에서는 원문이 없으며 이전 실패 상태가 아닌 기사만 Topic별 최대
5건 batch로 지연 추출한다. 한 Topic의 extractor 호출 예외와 기사별 실패는
결과에 남기고 다른 Topic을 계속 처리한다.

3일 Summary 입력은 다음 값을 포함한다.

```text
topic_candidate_id
prompt_version = three-day-flow-v1
representative_article_id
article_id, title, source, analysis_time, bounded raw_text
```

`ThreeDayOpenAISummaryProvider`는 단일 시점 설명 대신 72시간의 시간 순서, 진행
상황, 여러 출처의 공통 사실과 불확실성을 구분하도록 요구하는 전용 prompt와
strict JSON schema를 Responses API에 전달한다. `summary_input_hash`는 prompt
version, 기사 ID, UTC 기사 시각과 bounded 원문을 정렬한 payload로 계산한다.

저장 시 관련 기사 전체를 rank 순서로 연결하되 실제 원문이 provider 입력에
포함된 기사만 `is_summary_evidence=true`로 기록한다. 대표 기사는 설계 계약상
Summary 근거여야 하므로 대표 기사 원문이 끝내 없으면 해당 Topic을 실패로
격리한다.

저장 정책은 다음과 같다.

- 일부 Topic 성공: 성공 부분집합을 한 번의 `replace_window_topics`로 교체하고
  `partial_success`
- 선택 Topic 전부 실패: repository 교체를 호출하지 않아 기존 성공 결과를
  보존하고 `failed`
- 선택 Topic이 없는 정상 실행: 빈 목록으로 window를 교체하고 `success`
- dry-run: Summary와 저장 record만 메모리에서 만들고 DB 교체를 수행하지 않음

## UNIT-07 실행 진입점과 CronJob 구현 결과

전용 진입점은 `scripts/run_three_day_topic_pipeline.py`로 분리했다. 기본은
dry-run이며 다음 조건을 적용한다.

- `--window-end`가 없으면 실행 시작 instant를 72시간 종료 경계로 사용한다.
- `--window-end`는 timezone-aware ISO 8601 값만 허용한다.
- `--window-hours`는 호환성과 명시성을 위해 노출하되 `72`만 허용한다.
- article embedding provider option은 제공하지 않고 저장된
  `article_embeddings`만 후보 stage에서 조회한다.
- `--execute`는 `--use-summary-provider`와 `OPENAI_SUMMARY_API_KEY`가 함께
  있을 때만 허용한다.
- dry-run은 실제 DB 후보와 저장 원문을 읽을 수 있지만 run 이력, 원문 추출과
  Topic 결과 교체를 수행하지 않는다.
- execute는 `running` run을 먼저 생성하고 성공 시 실제 stage count로
  종료한다. 처리 중 예외는 안전한 오류 문자열과 `failed` 상태로 종료한 뒤
  process 실패를 유지한다.

CronJob은 `k8s/news-three-day-topic-pipeline-cronjob.yaml`에 추가했다.
`news-daily-topic-pipeline`의 `04:00 Asia/Seoul` 실행 이후인 매일
`05:00 Asia/Seoul`에 독립 실행한다. 초기 운영 인자는 다음과 같다.

```text
max_articles = 500
similarity_threshold = 0.70
max_topics = 5
max_related_articles_per_topic = 20
max_summary_articles_per_topic = 3
max_raw_chars_per_article = 3000
```

Manifest는 기존 `seocj/news-api:latest`, `news-api-secret`, app workload
node selector와 security/resource pattern을 재사용한다. 신규 embedding을
생성하지 않으므로 `OPENAI_EMBEDDING_API_KEY`는 주입하지 않고
`DATABASE_URL`, `OPENAI_SUMMARY_API_KEY`만 참조한다.

Job 안전 설정은 다음과 같다.

```text
concurrencyPolicy = Forbid
successfulJobsHistoryLimit = 3
failedJobsHistoryLimit = 3
activeDeadlineSeconds = 1800
backoffLimit = 1
restartPolicy = Never
```

Manifest apply와 실제 Job 실행은 수행하지 않았으며 human-controlled operation으로
남긴다.

## 후속 UNIT 경계

- UNIT-02: schema와 원자적 repository 계약 구현 완료. DB 적용은 사람 수행
- UNIT-03: context, candidate query, 저장 embedding 검증과 누락 통계 구현 완료
- UNIT-04: 재클러스터링 및 대표/관련/Summary 근거 기사 선정 구현 완료
- UNIT-05: 원문, 3일 prompt, 실패 격리와 결과 교체 구현 완료
- UNIT-06: archive, home, detail API와 route 등록 구현 완료
- UNIT-07: 전용 실행 script와 CronJob manifest 구현 완료
- UNIT-08: 전체 회귀 검증, Architecture/Runbook/README와 운영 수동 절차 정리

## UNIT-08 문서화 결과

- README에 3일 Topic API, dry-run 진입점과 문서 링크를 추가했다.
- Architecture index와 pipeline, database, API 문서에 72시간 입력부터 전용
  저장·조회까지의 책임을 반영했다.
- Runbook에 migration 적용 전후 확인, client/server dry-run, CronJob 적용,
  수동 Job, 실행 통계, API 확인, suspend와 rollback 판단 절차를 추가했다.
- 운영 command는 사람 통제 작업으로 구분했으며 실제 migration, Kubernetes
  apply, 수동 Job과 production API 확인은 수행하지 않았다.

전체 로컬 회귀 검증과 최종 상태는
`docs/verification/feature-three-day-topic-pipeline.md`를 source of truth로
사용한다.
