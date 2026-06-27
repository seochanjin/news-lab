# 7일 Topic 저장·실행 설계

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 목적

7일 Topic pipeline은 직전 완료 주간의 기사와 기존 `article_embeddings`를
사용해 월요일부터 일요일까지의 주요 이슈를 다시 clustering하고, Daily 및 3일
Topic 결과와 분리된 전용 테이블에 저장한다.

이번 설계는 기존 3일 Topic 구현을 기준으로 하되, 7일 Topic이 rolling 168시간이
아니라 완료된 calendar week를 처리한다는 차이만 별도 계약으로 둔다. 기존
`topics`, `topic_articles`, `three_day_topics`, `three_day_topic_articles`,
`three_day_topic_runs`는 변경하지 않는다.

## 기존 구조 분석

3일 Topic은 다음 구조로 구현되어 있다.

- Migration: `db/migrations/007_create_three_day_topic_tables.sql`
- 실행 context: `app/services/three_day_topic_pipeline/context.py`
- 후보 조회와 embedding 재사용:
  `app/services/three_day_topic_pipeline/candidate_stage.py`
- 재클러스터링과 기사 선정:
  `app/services/three_day_topic_pipeline/topic_selection_stage.py`
- 원문 확보와 요약 저장:
  `app/services/three_day_topic_pipeline/raw_acquisition_stage.py`,
  `app/services/three_day_topic_pipeline/summary_persistence_stage.py`
- 저장소와 transaction:
  `app/services/three_day_topic_pipeline/repository.py`
- API: `app/routers/three_day_topics.py`

3일 Topic DB는 세 테이블을 사용한다.

- `three_day_topic_runs`: 모든 실행 이력, window, 상태, 단계별 통계
- `three_day_topics`: 현재 활성 72시간 Topic 결과와 Summary metadata
- `three_day_topic_articles`: Topic별 관련 기사, 순위, 대표 기사 여부,
  Summary 근거 기사 여부

3일 저장소는 run 생성과 결과 교체 transaction을 분리한다. 결과 교체는
`window_start`, `window_end` 기반 advisory transaction lock 안에서 기존 Topic
삭제와 신규 Topic·기사 관계 삽입을 한 transaction으로 수행한다. 삽입 실패 시
삭제도 rollback되어 기존 성공 결과가 유지된다. Summary 생성에 전부 실패한
실행은 run을 `failed`로 종료하되 기존 결과를 교체하지 않는다.

Daily Topic은 `topics`, `topic_articles`에 요약 결과를 저장하지만 실행 window
감사 테이블이 없고, 동일 주간 재처리와 부분 성공 상태를 표현하기 어렵다.
따라서 Weekly 설계는 Daily 저장 구조가 아니라 3일 Topic의 run/topic/article
분리를 따른다.

## 선택한 대안

대안 A인 Weekly 전용 테이블을 선택한다.

```text
weekly_topic_runs
weekly_topics
weekly_topic_articles
```

선택 근거:

- 기존 3일 Topic API, DB, CronJob 계약을 변경하지 않는다.
- 기존 3일 Topic 데이터를 일반화 테이블로 이전할 필요가 없다.
- Weekly 고유 정책인 `week_start`, `week_end`, 완료 주간 재처리와 최소 source
  조건을 독립적으로 변경할 수 있다.
- 저장소와 API 구조는 3일 구현의 검증된 transaction과 조회 패턴을 재사용할 수
  있다.

대안 B인 `period_topics` 일반화는 이번 작업에서 선택하지 않는다. 기존 3일
Topic migration, repository, API와 운영 데이터를 함께 바꾸거나 이관해야 하며
이번 task의 Do not change 범위를 벗어난다.

## 주간 실행 context

Weekly context는 pipeline 시작 시 한 번만 결정하고 모든 단계에 주입한다.

기본 실행은 실행 시점보다 앞선 가장 최근 완료 주간을 선택한다. 예를 들어
`Asia/Seoul` 기준 2026-06-22 월요일 00:30에 실행하면 다음 범위를 처리한다.

```text
week_start: 2026-06-15
week_end:   2026-06-21
window_start: 2026-06-15 00:00:00+09:00
window_end:   2026-06-22 00:00:00+09:00
```

`--week-start YYYY-MM-DD`는 명시 재처리용 인자다. 값은 `Asia/Seoul` 기준
월요일이어야 하며, `week_end`는 `week_start + 6 days`, `window_end`는
`week_start + 7 days`로 계산한다.

저장과 중복 방지의 최종 기준은 absolute `window_start`, `window_end`다.
`week_start`, `week_end`는 표시와 주간 조회를 위한 식별 정보로 함께 저장한다.

## 후보와 embedding 계약

후보 기사는 기존 3일 후보 조회 정책처럼 기사 시각을
`coalesce(published_at, created_at)`로 판정한다. 이는 `published_at`을 우선
사용하고, 값이 없을 때 기존 후보 조회 정책과 같은 `created_at` fallback을 쓰기
위한 계약이다.

Weekly pipeline은 `article_embeddings`를 read-only로 조회한다. Provider, model,
dimension, source text type, source text hash가 현재 기사 입력과 일치하는 row만
clustering 입력으로 사용한다. 누락, metadata 불일치, stale hash, invalid vector
기사는 실행 실패로 만들지 않고 후보에서 제외하며 누락 사유와 수를 run 통계와
로그에 기록한다. Weekly pipeline은 신규 embedding provider 호출과
`article_embeddings` insert/update를 수행하지 않는다.

## 재클러스터링과 기사 선정 계약

`app/services/weekly_topic_pipeline/topic_selection_stage.py`는 후보 stage가
검증한 기사와 저장 embedding만 입력으로 받아 `group_articles`와 기존 대표 후보
점수 계산을 재사용한다. 정상 embedding이 5건 미만이면 실패 대신 빈 선정 결과를
반환한다.

Clustering 후에는 기사 수 5개 이상, 서로 다른 source 2개 이상인 군집만 Weekly
Topic 후보로 유지한다. Topic 후보 정렬은 공통 `topic_selection_key`를 사용해
기사 수, source 수, 평균 유사도와 최신성을 반영하며, 관련 기사는 대표 후보 점수
순서로 제한한다. Summary 근거 기사는 대표 기사를 포함하고 URL·정규화 제목 중복을
제외하며, 가능한 한 아직 선택되지 않은 source를 우선해 Topic당 최대 5개까지
결정론적으로 선택한다.

## 원문 확보와 주간 Summary 계약

`app/services/weekly_topic_pipeline/raw_acquisition_stage.py`는 선택된 주간 Topic의
관련 기사 범위에서 기존 원문을 먼저 조회한다. 지연 원문 추출은 원문이 없는
Summary 후보 기사에만 수행하며, 한 Topic 또는 한 batch의 extractor 실패는 기사별
실패 결과로 기록하고 다음 Topic 처리를 계속한다. Summary 입력 단계는 관련 기사
원문을 함께 보관한 결과를 사용해 원문이 끝내 확보되지 않은 Summary 후보를 같은
Topic의 다음 대표성 순위 기사 원문으로 대체할 수 있다.

`app/services/weekly_topic_pipeline/summary_persistence_stage.py`는
`weekly-flow-v1` prompt version을 사용한다. Prompt는 지난 월요일부터 일요일까지의
변화, 진행 상황, 반복해서 등장한 쟁점, 여러 출처가 공통으로 확인한 내용과
불확실성을 구분해 요약하도록 요구한다. 대표 기사 원문이 없거나 provider가 실패한
Topic은 실패로 격리하고 다른 Topic 처리를 계속한다.

저장 단계는 성공 Topic이 하나 이상 있으면 성공 부분집합만 repository의 window
교체 transaction에 전달한다. 일부 성공·일부 실패는 `partial_success`가 되고,
모든 Topic이 실패하면 repository 교체를 호출하지 않아 기존 성공 결과를 보존한다.
정상적으로 선택 Topic이 없는 실행은 빈 결과로 window를 원자 교체하고 `success`로
끝낼 수 있다.

## DB 계약

### `weekly_topic_runs`

필수 column:

```text
id bigserial primary key
week_start date not null
week_end date not null
window_start timestamptz not null
window_end timestamptz not null
status text not null default 'running'
candidate_count integer not null default 0
embedding_count integer not null default 0
missing_embedding_count integer not null default 0
cluster_count integer not null default 0
selected_topic_count integer not null default 0
saved_topic_count integer not null default 0
failed_topic_count integer not null default 0
error_message text
started_at timestamptz not null
finished_at timestamptz
created_at timestamptz not null default now()
```

상태 값:

```text
running
success
partial_success
failed
```

권장 check:

```text
week_start <= week_end
window_start < window_end
candidate_count = embedding_count + missing_embedding_count
saved_topic_count <= selected_topic_count
모든 count >= 0
```

`week_start`가 월요일이고 `week_end = week_start + 6 days`이며
`window_end = window_start + 7 days`인 계약은 application model과 테스트에서
검증한다. DB check만으로 timezone local date 계산을 과도하게 표현하지 않는다.

### `weekly_topics`

필수 column:

```text
id bigserial primary key
run_id bigint not null references weekly_topic_runs(id) on delete restrict
week_start date not null
week_end date not null
window_start timestamptz not null
window_end timestamptz not null
topic_candidate_id text not null
title_ko text not null
summary_ko text not null
key_points jsonb not null default '[]'::jsonb
keywords jsonb not null default '[]'::jsonb
confidence double precision not null
article_count integer not null default 0
source_count integer not null default 0
status text not null default 'draft'
provider text not null
model text not null
prompt_version text not null
summary_input_hash text not null
created_at timestamptz not null default now()
updated_at timestamptz not null default now()
```

권장 unique와 check:

```text
unique (window_start, window_end, topic_candidate_id)
window_start < window_end
confidence >= 0 and confidence <= 1
article_count >= 0
source_count >= 0
```

Weekly Topic 후보는 최소 5개 기사와 최소 2개 source 조건을 통과해야 하므로
application model은 저장 전 `article_count >= 5`, `source_count >= 2`를
검증한다. 빈 결과 교체를 허용해야 하므로 Topic table 자체에 window당 최소 row
수 제약은 두지 않는다.

### `weekly_topic_articles`

필수 column:

```text
id bigserial primary key
weekly_topic_id bigint not null references weekly_topics(id) on delete cascade
article_id bigint not null references articles(id) on delete cascade
rank integer not null
similarity double precision
is_representative boolean not null default false
is_summary_evidence boolean not null default false
created_at timestamptz not null default now()
```

권장 unique와 check:

```text
unique (weekly_topic_id, article_id)
rank >= 1
```

대표 기사 1건, 대표 기사의 Summary 근거 포함, Summary 근거 기사가 관련 기사
부분집합이라는 규칙은 save model과 테스트에서 검증한다. DB는 기본 관계와 중복
방어에 집중한다.

## Index

목록, 홈, 상세 API를 위해 다음 index를 둔다.

```text
idx_weekly_topic_runs_window
  on weekly_topic_runs (window_end desc, window_start desc, id desc)

idx_weekly_topic_runs_status
  on weekly_topic_runs (status, started_at desc)

idx_weekly_topics_archive
  on weekly_topics (week_start desc, window_end desc, id desc)

idx_weekly_topics_status
  on weekly_topics (status, week_start desc, window_end desc)

idx_weekly_topics_run_id
  on weekly_topics (run_id)

idx_weekly_topic_articles_topic_rank
  on weekly_topic_articles (weekly_topic_id, rank, article_id)

idx_weekly_topic_articles_article_id
  on weekly_topic_articles (article_id)
```

## Idempotency와 실패 격리

동일 `window_start`, `window_end` 재실행은 run row를 새로 추가하되 활성 Topic
set은 원자적으로 교체한다. 결과 교체 transaction은 다음 순서를 따른다.

```text
weekly window advisory transaction lock
→ 기존 weekly_topics 삭제
→ 신규 weekly_topics 삽입
→ weekly_topic_articles 삽입
```

Topic insert 실패, relation insert 실패 또는 transaction 중 예외가 발생하면
삭제와 삽입 모두 rollback되어 기존 성공 결과가 유지된다. 모든 Topic 처리에
실패한 실행은 run을 `failed`로 기록하고 기존 결과를 교체하지 않는다. 일부
Topic만 성공하면 성공 부분집합을 저장하고 run을 `partial_success`로 기록한다.
선택된 Topic이 없는 정상 실행은 빈 결과로 교체하고 `success`로 기록할 수 있다.

Advisory lock key는 UTC로 정규화한 window를 사용한다.

```text
weekly-topics:{window_start_utc}:{window_end_utc}
```

## API 계약

Weekly API는 기존 3일 Topic API와 이름만 다르게 같은 형태를 따른다.

```text
GET /weekly-topics
GET /weekly-topics/home
GET /weekly-topics/{topic_id}
```

`/weekly-topics/home`은 성공 또는 부분 성공 run이 만든 최신 완료 주간 window의
card payload를 반환한다. 정적 `/home` route는 동적 `/{topic_id}` route보다 먼저
등록한다.

목록과 상세 payload에는 `week_start`, `week_end`, `window_start`, `window_end`,
`article_count`, `source_count`, `keywords`, `status`를 포함한다. 상세 API는
`weekly_topic_articles.rank` 순서대로 전체 관련 기사를 반환하고,
`is_representative`, `is_summary_evidence`를 함께 노출한다.

## 실행 진입점과 CronJob 계약

Weekly 실행 진입점은 `scripts/run_weekly_topic_pipeline.py`다. 기본 실행은
dry-run이며 `--execute --use-summary-provider`를 함께 지정할 때만 run 이력 생성,
지연 원문 추출과 `weekly_topics` window 결과 교체를 수행한다. `--week-start`는
명시 재처리용 인자이며 `YYYY-MM-DD` 형식의 월요일만 허용한다. 인자가 없으면
실행 시점보다 앞선 가장 최근 완료 주간을 처리한다.

CronJob manifest는 `k8s/news-weekly-topic-pipeline-cronjob.yaml`에 둔다. Schedule은
`30 0 * * 1`, `timeZone: Asia/Seoul`로 매주 월요일 00:30에 실행한다. Command는
전용 runner를 사용하고 `--week-start`를 지정하지 않아 기본 완료 주간 선택 계약을
따른다. Weekly pipeline은 저장된 embedding만 재사용하므로
`OPENAI_EMBEDDING_API_KEY`를 주입하지 않고, 기존 image, `DATABASE_URL`,
`OPENAI_SUMMARY_API_KEY`, node selector, `/tmp` emptyDir와 pod security pattern을
3일 Topic CronJob과 맞춘다.

## 3일 Topic과 다른 점

- 3일 Topic은 `reference_date`와 rolling 72시간 window를 사용한다.
- Weekly Topic은 `week_start`, `week_end`와 완료된 월요일-일요일 calendar week를
  사용한다.
- Weekly Topic은 최소 기사 수 5개와 최소 source 수 2개를 Topic 후보 필터로
  적용한다.
- Weekly Summary 근거 기사는 Topic당 최대 5개이며 주간 흐름 전용 prompt
  version을 사용한다.
- CLI 재현 인자는 `--window-end`가 아니라 `--week-start`를 우선 계약으로 둔다.

그 외 run 상태, 누락 embedding 통계, 결과 교체, 대표·Summary 근거 기사 표현,
API route 순서와 transaction 경계는 3일 Topic의 검증된 구조를 따른다.

## Migration과 운영 적용

Weekly migration은 `db/migrations/008_create_weekly_topic_tables.sql` 형태로
추가한다. 기존 migration 파일은 수정하지 않는다. 실제 Supabase 또는 production
DB 적용은 사람이 수행한다.

Rollback 또는 복구는 적용 전 backup과 migration 적용 여부를 사람이 확인한 뒤
결정한다. 아직 운영 데이터가 없는 신규 Weekly 테이블의 초기 rollback은
`weekly_topic_articles`, `weekly_topics`, `weekly_topic_runs` 순서로 제거하는
방식이 가능하지만, 이 명령은 agent가 실행하지 않고 Runbook에 human-controlled
작업으로 기록한다.
