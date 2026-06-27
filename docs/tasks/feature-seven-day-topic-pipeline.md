# Task: 최근 7일 기사·토픽 파이프라인 확장

## Goal

기존 Daily Topic pipeline과 3일 Topic 운영 구조를 유지하면서, 직전 완료 주간인
월요일부터 일요일까지 수집된 기사와 기존 `article_embeddings` 데이터를
활용해 7일 단위 주요 이슈를 생성하는 별도 Weekly Topic pipeline을 구축한다.

7일 Topic은 Daily Topic이나 3일 Topic 결과를 다시 집계하는 방식이 아니라,
직전 7일 기사 후보를 직접 조회하고 이미 저장된 article embedding을 재사용해
주간 단위로 다시 clustering한다.

선정된 7일 Topic은 기존 `topics`, `topic_articles` 및
`three_day_topics`, `three_day_topic_articles`와 분리된 전용 테이블에 저장한다.

목록·상세·홈 API와 K3s CronJob을 추가해 Daily 및 3일 Topic과 독립적으로
조회하고 실행할 수 있어야 한다.

이번 작업의 최종 흐름은 다음과 같다.

```text
기존 Daily Topic pipeline
→ 기사 embedding 저장 유지

매주 월요일 실행
→ 직전 월요일~일요일 기사 조회
→ 기존 article_embeddings 재사용
→ 7일 기준 재클러스터링
→ 최소 기사 수·출처 수 조건 적용
→ 주간 Topic 후보 선정
→ 관련 기사 전체 기록
→ 요약 근거 기사 최대 5개 선정
→ selected 기사 원문 확보
→ 지난주 흐름 요약 생성
→ weekly_topics 계열 테이블 저장
→ 7일 Topic API 제공
→ 전용 CronJob 정기 실행
```

기본 정책은 다음과 같다.

```text
timezone: Asia/Seoul
처리 범위: 직전 월요일 00:00 이상 ~ 현재 월요일 00:00 미만
similarity threshold: 0.70
minimum cluster size: 5
minimum source count: 2
summary evidence article count: 최대 5
기본 실행 시각: 매주 월요일 00:30 Asia/Seoul
```

## Scope

- 직전 완료 주간의 기사 후보를 조회하는 7일 Topic 전용 실행 컨텍스트를 추가한다.
- 주간 범위는 `Asia/Seoul` 기준 월요일 00:00부터 다음 월요일 00:00 미만으로 계산한다.
- 표시용 날짜 범위는 `week_start` 월요일부터 `week_end` 일요일까지다.
- 실행 과정 전체에서 동일한 `week_start`, `week_end`, `window_start`,
  `window_end`를 사용하도록 컨텍스트를 한 번만 결정해 주입한다.
- 인자가 없는 기본 실행에서는 실행 시점보다 앞선 가장 최근의 완료된 주간을
  처리한다.
- 특정 주간을 재처리할 수 있도록 명시적인 `--week-start` 인자를 지원한다.
- `--week-start`는 `YYYY-MM-DD` 형식의 월요일이어야 한다.
- 기사 시간 기준은 기존 기사 데이터 구조를 검토해 `published_at`을 우선
  사용하고, 필요한 경우 기존 후보 조회 정책과 일치하는 fallback을 적용한다.
- 기존 `article_embeddings`에 저장된 embedding만 사용한다.
- 7일 Topic pipeline에서는 신규 embedding provider 호출을 수행하지 않는다.
- embedding이 없는 기사는 전체 실행 실패로 만들지 않고 후보에서 제외한다.
- embedding 누락 기사 수를 실행 결과와 로그에 기록한다.
- 직전 주간 기사 embedding을 이용해 7일 기준으로 다시 clustering한다.
- Daily Topic이나 3일 Topic의 저장 결과를 군집 입력으로 사용하지 않는다.
- 기존 Daily 및 3일 Topic의 clustering, 대표 기사 선정, 관련 기사 선정 로직을
  가능한 범위에서 재사용하거나 공통 처리 계층으로 추출한다.
- 공통화 시 기존 Daily 및 3일 Topic의 입력·출력·설정·통계 의미와 테스트
  계약을 유지한다.
- 7일 Topic의 최대 후보 기사 수, 최대 Topic 수, clustering threshold,
  최소 군집 기사 수, 최소 source 수, 관련 기사 수와 요약 근거 기사 수를
  독립적인 설정으로 관리한다.
- 기본 clustering threshold는 `0.70`으로 한다.
- 기사 수가 5개 이상인 군집만 주간 Topic 후보로 유지한다.
- 서로 다른 source가 2개 이상인 군집만 주간 Topic 후보로 유지한다.
- source 수는 동일 source의 반복 기사만으로 주요 Topic이 생성되는 것을
  완화하기 위한 조건이다.
- 군집별 centroid 또는 기존 대표성 점수를 기준으로 관련 기사를 정렬한다.
- 요약 근거 기사는 유사도가 높은 기사를 우선하되 동일 source에 편중되지
  않도록 최대 5개를 선택한다.
- 랜덤 선택은 사용하지 않는다.
- 동일 점수에서는 article ID, 발행 시각 또는 기존의 안정적인 tie-breaker를
  사용해 결정론적인 결과를 만든다.
- 관련 기사 전체와 요약에 실제 사용한 근거 기사를 분리해 저장한다.
- Topic으로 선정된 기사에 대해서만 기존 원문을 우선 조회한다.
- 원문이 없는 요약 후보 기사에 한해서 지연 원문 추출을 수행한다.
- 요약 후보 원문 확보 실패 시 동일 군집의 다음 순위 기사로 대체한다.
- 7일 흐름에 맞는 별도 summary prompt 또는 prompt version을 사용한다.
- 주간 요약은 단일 시점 사건 설명보다 지난 월요일부터 일요일까지의 변화,
  진행 상황, 반복해서 등장한 쟁점과 여러 출처의 공통 내용을 설명해야 한다.
- Topic 하나의 원문 확보 또는 요약이 실패해도 다른 Topic 처리는 계속하는
  실패 격리 정책을 적용한다.
- 7일 Topic 전용 저장 구조와 실행 이력 구조를 추가한다.
- 동일한 절대 `window_start`, `window_end` 범위로 재실행할 때 중복 데이터가
  누적되지 않도록 idempotency 정책을 적용한다.
- `week_start`는 표시와 조회용 주간 식별 정보이며, 결과 교체의 최종 고유
  기준은 절대 `window_start`, `window_end` 또는 결정론적 Topic key로 한다.
- 기존 성공 결과를 먼저 삭제한 뒤 pipeline 중간 실패로 결과가 사라지지
  않도록 저장·교체 순서를 설계한다.
- 7일 Topic 목록·상세·홈 API를 추가한다.
- 7일 Topic pipeline을 정기 실행하는 K3s CronJob manifest를 추가한다.
- CronJob은 일요일 전체 기사가 수집된 이후인 매주 월요일 00:30
  `Asia/Seoul`에 실행한다.
- CronJob은 기존 Secret, ConfigMap, image와 실행 환경을 가능한 범위에서
  재사용한다.
- 로컬 단위 테스트, 전체 회귀 테스트, migration 및 manifest 검증과 수동
  실행 절차를 문서화한다.
- 실제 DB migration 적용, K3s apply, 수동 Job 실행과 운영 API 확인은 사람이
  수행할 수 있도록 명령과 확인 기준만 제공한다.
- README와 Architecture, Runbook, verification, PR, devlog 문서를 작업
  결과에 맞게 갱신한다.
- 설계 대안, 선택 근거와 트레이드오프를 문서에 기록한다.

## Do not change

- 기존 Daily Topic pipeline의 운영 의미와 실행 결과를 변경하지 않는다.
- 기존 `scripts/run_daily_topic_pipeline.py`의 외부 실행 계약을 깨지 않는다.
- 기존 `app/services/daily_topic_pipeline/`의 public 함수·결과 모델·통계
  의미를 불필요하게 변경하지 않는다.
- 기존 3일 Topic pipeline의 최근 72시간 처리 계약을 변경하지 않는다.
- 기존 `scripts/run_three_day_topic_pipeline.py`의 외부 실행 계약을 깨지 않는다.
- 기존 `app/services/three_day_topic_pipeline/`의 public 함수·결과 모델·통계
  의미를 불필요하게 변경하지 않는다.
- 기존 `topics` 테이블 구조와 저장 데이터를 7일 Topic 용도로 사용하지 않는다.
- 기존 `topic_articles` 테이블 구조와 저장 데이터를 7일 Topic 용도로 사용하지 않는다.
- 기존 `three_day_topics` 테이블 구조와 저장 데이터를 7일 Topic 용도로
  사용하지 않는다.
- 기존 `three_day_topic_articles`와 `three_day_topic_runs`를 7일 Topic
  용도로 사용하지 않는다.
- 기존 `topics`, `topic_articles`, `three_day_topics`,
  `three_day_topic_articles`, `article_embeddings`, `article_texts`,
  `article_summaries` 데이터를 삭제하거나 변환하지 않는다.
- 기존 `/topics`, `/topics/{topic_id}`, `/topics/home` API contract를
  변경하지 않는다.
- 기존 `/three-day-topics`, `/three-day-topics/home`,
  `/three-day-topics/{topic_id}` API contract를 변경하지 않는다.
- 기존 Daily Topic CronJob schedule, command와 argument를 변경하지 않는다.
- 기존 3일 Topic CronJob schedule, command와 argument를 변경하지 않는다.
- 기존 RSS 수집 및 기사 저장 흐름을 변경하지 않는다.
- 기존 embedding 생성 정책이나 embedding model을 변경하지 않는다.
- 7일 Topic pipeline에서 embedding API를 새로 호출하지 않는다.
- frontend 저장소와 화면을 변경하지 않는다.
- Redis, cache server, snapshot file과 별도 message queue를 도입하지 않는다.
- production Secret 값을 변경하지 않는다.
- GitHub Actions의 image build/push 정책을 변경하지 않는다.
- 실제 migration 적용, Supabase SQL 실행, K3s apply, rollout, CronJob 실행과
  production 배포를 Agent가 수행하지 않는다.
- 기존 application SQL 전반의 interpolation 또는 query construction
  리팩터링을 이번 작업에 포함하지 않는다.
- 기간별 Topic 테이블을 하나의 범용 테이블로 통합하는 대규모 schema
  리팩터링을 이번 작업에 포함하지 않는다.

## Expected files

실제 저장소 구조와 기존 3일 Topic 구현을 먼저 조사한 뒤 필요한 파일만
추가·수정한다.

예상 신규 파일:

```text
db/migrations/*_create_weekly_topic_tables.sql

scripts/run_weekly_topic_pipeline.py

app/services/weekly_topic_pipeline/
app/routers/weekly_topics.py

k8s/news-weekly-topic-pipeline-cronjob.yaml

tests/test_run_weekly_topic_pipeline.py
tests/test_weekly_topic_pipeline.py
tests/test_weekly_topics_api.py
tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

공통 로직 추출이 필요할 경우 예상 수정 파일:

```text
app/services/daily_topic_pipeline/*
app/services/three_day_topic_pipeline/*
app/services/topic_pipeline/*
app/routers/__init__.py
app/main.py
```

정확한 파일명, package 구조, model 위치와 repository 계층은 기존 3일 Topic
구현을 우선 기준으로 결정한다.

다음 항목을 구현 전에 조사한다.

- 3일 Topic migration과 실제 테이블 구조
- 3일 Topic SQLAlchemy model 또는 DB row mapping
- 3일 Topic repository와 transaction 경계
- Topic 중복 방지 및 재실행 정책
- Topic과 기사 관계 저장 방식
- 대표 기사와 요약 근거 기사 구분 방식
- 실행 이력과 통계 저장 방식
- 목록·홈·상세 API가 조회하는 컬럼
- 기존 index, unique constraint와 foreign key 정책
- migration naming convention
- 테스트에서 사용하는 DB fixture와 schema 검증 방식

Daily 또는 3일 Topic 코드를 Weekly Topic 디렉터리로 단순 복사하지 않는다.

3일 Topic 구조를 그대로 재사용할 수 있는 경우 naming과 계약을 최대한
일치시킨다. 주간 기능에 필요하지 않은 컬럼을 관성적으로 복제하지 않고,
주간 고유 요구사항이 있는 경우에만 별도 컬럼이나 제약을 추가한다.

예상 문서 파일:

```text
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/design/weekly-topic-pipeline.md
docs/tasks/<current-task>.md
docs/verification/<current-task>.md
docs/reviews/<current-task>-antigravity.md
docs/reviews/<current-task>-coderabbit.md
docs/fixes/<current-task>-approved-fixes.md
docs/pr/<current-task>.md
docs/devlog/<current-task>.md
```

## DB changes

7일 Topic은 기존 Daily 및 3일 Topic 결과와 구분해 저장해야 한다.

다만 구체적인 테이블, 컬럼, 제약과 index는 현재 Task에서 미리 확정하지 않고
기존 3일 Topic 저장 구조를 분석한 뒤 결정한다.

### 설계 원칙

- 기존 Daily Topic 테이블의 의미를 변경하지 않는다.
- 기존 3일 Topic 테이블의 의미를 변경하지 않는다.
- 7일 Topic 데이터를 3일 Topic 테이블에 억지로 저장하지 않는다.
- 3일 Topic의 검증된 저장·조회·재실행 계약은 가능한 범위에서 재사용한다.
- 주간 범위와 주간 조회에 필요한 차이만 별도로 설계한다.
- 동일 주간 재실행 시 결과가 중복 누적되지 않아야 한다.
- pipeline 실패 때문에 기존 성공 결과가 먼저 제거되지 않아야 한다.
- Topic별 실패와 전체 run 상태를 구분할 수 있어야 한다.
- 전체 관련 기사와 요약 근거 기사를 구분할 수 있어야 한다.
- 실제 production migration은 Agent가 수행하지 않는다.

### UNIT-01 조사 결과로 확정할 항목

다음 항목은 기존 3일 Topic 구현을 분석한 뒤 설계 문서와 Task에 확정해
기록한다.

1. 7일 Topic 전용 테이블이 몇 개 필요한지
2. 테이블과 컬럼 naming
3. 주간 식별 정보
   - `week_start`
   - `week_end`
   - `window_start`
   - `window_end`
     중 실제로 저장할 값
4. Topic 고유 식별 및 중복 방지 기준
5. Topic과 기사 관계 저장 방식
6. 대표 기사와 요약 근거 기사 표현 방식
7. 실행 이력과 단계별 통계 컬럼
8. `success`, `partial_success`, `failed` 상태 표현 방식
9. foreign key와 삭제 정책
10. 목록·홈·상세 API에 필요한 index
11. 동일 주간 재실행의 upsert 또는 교체 정책
12. migration rollback 또는 복구 절차

### UNIT-01 확정 결과

기존 Daily, 3일 Topic, embedding 구조를 조사한 결과 7일 Topic은 대안 A인 전용
Weekly 테이블 구조로 구현한다. 확정 설계는
[7일 Topic 저장·실행 설계](../design/weekly-topic-pipeline.md)를 source로
사용한다.

UNIT-01에서 확정한 항목은 다음과 같다.

1. 7일 Topic 전용 테이블은 `weekly_topic_runs`, `weekly_topics`,
   `weekly_topic_articles` 세 개를 사용한다.
2. `weekly_topic_runs`는 모든 실행 이력과 단계별 통계를 저장하고,
   `weekly_topics`는 현재 활성 주간 Topic 결과를 저장하며,
   `weekly_topic_articles`는 관련 기사 전체와 대표·요약 근거 기사 역할을
   저장한다.
3. 주간 식별 정보는 `week_start`, `week_end`, `window_start`, `window_end`를
   모두 저장한다. 결과 교체와 중복 방지의 최종 기준은 absolute
   `window_start`, `window_end`다.
4. Topic 고유 식별과 중복 방지는
   `unique (window_start, window_end, topic_candidate_id)`로 수행한다.
5. Topic과 기사 관계는 `weekly_topic_articles.weekly_topic_id`와
   `article_id`, `rank`, `similarity`로 표현한다.
6. 대표 기사와 요약 근거 기사는 `is_representative`,
   `is_summary_evidence` boolean으로 구분한다.
7. 실행 이력은 3일 Topic과 같은 count 컬럼을 사용하되 주간 식별 컬럼을
   `reference_date` 대신 `week_start`, `week_end`로 둔다.
8. 실행 상태는 `running`, `success`, `partial_success`, `failed`를 사용한다.
9. `weekly_topics.run_id`는 `weekly_topic_runs(id) on delete restrict`,
   `weekly_topic_articles.weekly_topic_id`는
   `weekly_topics(id) on delete cascade`, `article_id`는
   `articles(id) on delete cascade`를 사용한다.
10. 목록·홈·상세 API를 위해 run window/status, topic archive/status/run_id,
    topic article rank/article_id index를 둔다.
11. 동일 주간 재실행은 run row를 새로 추가하고, advisory transaction lock
    안에서 기존 window Topic set을 삭제 후 신규 결과를 삽입하는 원자 교체
    정책을 사용한다.
12. migration rollback 또는 복구는 후속 Runbook에서 human-controlled 작업으로
    기록한다. 신규 Weekly 테이블 초기 rollback은 article 관계, topic, run
    순서의 제거가 가능하지만 Agent는 production SQL을 실행하지 않는다.

3일 Topic과 다르게 설계한 항목은 완료된 calendar week를 표현하기 위한
`week_start`, `week_end`, `--week-start` 실행 계약과 최소 기사 수 5개, 최소
source 수 2개, Summary 근거 기사 최대 5개 정책이다. 그 외 DB transaction,
idempotency, 실행 상태, 대표·요약 근거 기사 표현과 API route 구조는 3일 Topic의
검증된 계약을 따른다.

### 우선 검토할 대안

#### 대안 A: 3일 Topic 구조를 기준으로 Weekly 전용 테이블 생성

예:

```text
weekly_topics
weekly_topic_articles
weekly_topic_runs
```

장점:

- Daily와 3일 Topic 계약에 영향이 적다.
- 주간 정책을 독립적으로 변경하기 쉽다.
- 기존 3일 repository와 API 구조를 참고하기 쉽다.

단점:

- 기간별 테이블과 repository가 늘어난다.
- 공통 로직이 중복될 가능성이 있다.

#### 대안 B: 기존 기간 Topic 구조를 일반화

예:

```text
period_topics
period_topic_articles
period_topic_runs
```

장점:

- 3일과 7일 Topic의 공통 저장 구조를 재사용할 수 있다.
- 기간이 추가될 때 테이블 증가를 줄일 수 있다.

단점:

- 기존 3일 Topic migration과 API를 변경해야 할 수 있다.
- 이번 작업 범위를 넘어서는 schema migration과 데이터 이전이 필요할 수 있다.
- 기존 운영 데이터와 API 회귀 위험이 크다.

이번 작업에서는 기존 3일 Topic 운영 계약을 깨지 않는 것을 우선한다.

따라서 조사 결과 특별한 근거가 없다면 대안 A를 우선하되, 테이블 컬럼과
제약은 3일 Topic 구현을 확인한 뒤 확정한다.

### Migration 적용 정책

- Migration SQL은 기존 repository convention에 맞게 작성한다.
- 기존 3일 Topic migration 파일을 수정하지 않는다.
- 기존 데이터를 이동하거나 변환하지 않는다.
- Migration 파일은 자동 테스트와 정적 검증까지만 수행한다.
- 실제 Supabase 또는 production DB 적용은 사람이 수행한다.
- 실제 적용 전 server 또는 DB 환경에서 별도 검토할 명령과 확인 기준을
  Runbook에 기록한다.

## Test commands

UNIT별 구현에서는 해당 범위의 집중 테스트를 먼저 실행하고, 모든 UNIT 완료 후
Daily·3일 Topic 회귀 테스트와 전체 테스트를 실행한다.

UNIT-01은 조사와 설계 확정이 중심이므로 기존 3일 Topic 구조와 테스트 계약을
확인한다.

```bash
rg -n \
  "three_day_topics|three_day_topic_articles|three_day_topic_runs" \
  db/migrations app scripts tests
```

```bash
rg -n \
  "three-day-topics|three_day_topics" \
  app tests docs
```

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

7일 Topic pipeline 집중 테스트:

```bash
python -m pytest \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_weekly_topic_pipeline.py \
  -v
```

7일 Topic API 테스트:

```bash
python -m pytest \
  tests/test_weekly_topics_api.py \
  -v
```

7일 Topic CronJob manifest 테스트:

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

Daily Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

3일 Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

전체 회귀 테스트:

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

Compile 검증:

```bash
python -m compileall app scripts tests
```

Whitespace 검증:

```bash
git diff --check
```

기존 Daily 및 3일 Topic 변경 범위 확인:

```bash
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

```bash
git diff -- \
  app/services/three_day_topic_pipeline \
  scripts/run_three_day_topic_pipeline.py \
  k8s/news-three-day-topic-pipeline-cronjob.yaml
```

UNIT-01에서 DB 설계가 확정되고 실제 migration 경로가 결정된 후 다음 검색어와
파일 경로를 구현 결과에 맞게 구체화한다.

```bash
rg -n \
  "weekly_topics|weekly_topic_articles|weekly_topic_runs" \
  db/migrations app scripts tests
```

API route 확인:

```bash
rg -n \
  "weekly-topics|weekly_topics" \
  app tests docs
```

CronJob manifest가 구현된 후 client-side dry-run을 실행한다.

```bash
kubectl apply --dry-run=client \
  -f k8s/news-weekly-topic-pipeline-cronjob.yaml
```

K3s server-side dry-run과 실제 적용은 사람이 수행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-weekly-topic-pipeline-cronjob.yaml
```

Verification 문서에는 실제 실행한 명령과 실제 결과만 기록한다.

아직 생성되지 않은 테스트 파일이나 manifest를 대상으로 한 명령은 구현 전
실행한 것처럼 기록하지 않는다. UNIT-01 조사 결과로 파일명이나 DB 구조가
달라진 경우 실제 구현 경로에 맞게 이 section을 갱신한다.

## Acceptance criteria

- 기존 Daily Topic pipeline과 CronJob이 변경 전과 동일하게 동작한다.
- 기존 3일 Topic pipeline과 CronJob이 변경 전과 동일하게 동작한다.
- 기존 Daily 및 3일 Topic DB schema와 API contract가 변경되지 않는다.
- UNIT-01에서 기존 3일 Topic migration, model, repository, transaction,
  idempotency와 API 조회 구조를 조사한다.
- 조사 결과를 기반으로 7일 Topic DB 설계가 확정된다.
- 선택한 DB 설계의 대안, 선택 근거와 트레이드오프가 기록된다.
- 3일 Topic 구조와 다르게 설계한 항목은 차이와 이유가 문서화된다.
- 불필요한 컬럼이나 table을 사전에 하드코딩하지 않는다.
- 7일 Topic 데이터는 기존 Daily 및 3일 Topic 데이터와 구분된다.
- 동일한 주간 재실행으로 결과가 중복 누적되지 않는다.
- pipeline 실패 시 기존 성공 결과가 불완전하게 삭제되지 않는다.
- 관련 기사와 요약 근거 기사를 구분해 저장할 수 있다.
- 실행 이력과 실패 통계를 저장할 수 있다.
- 실제 production migration은 수행하지 않는다.

- 7일 Topic pipeline이 직전 완료 주간 기사 후보를 명시적인 시간 범위로 조회한다.
- `Asia/Seoul` 기준 월요일 00:00 이상부터 다음 월요일 00:00 미만까지 처리한다.
- pipeline 전체 단계가 동일한 주간 범위를 사용한다.
- 기본 실행은 가장 최근 완료 주간을 선택한다.
- 명시적인 `--week-start` 재처리를 지원한다.
- 기존 `article_embeddings`만 재사용하고 신규 embedding API를 호출하지 않는다.
- embedding이 없는 기사는 제외되고 누락 통계가 기록된다.
- Daily 또는 3일 Topic 결과를 재집계하지 않는다.
- 기본 clustering threshold는 `0.70`이다.
- 기사 수 5개 미만 군집은 제외된다.
- 서로 다른 source가 2개 미만인 군집은 제외된다.
- 요약 근거 기사는 최대 5개다.
- 기사 선택은 결정론적이며 랜덤을 사용하지 않는다.
- centroid 유사도와 source 다양성을 반영한다.
- 원문 확보 실패 시 다음 순위 기사로 대체한다.
- Topic 하나의 실패가 다른 Topic 처리를 중단시키지 않는다.
- Weekly 전용 summary prompt 또는 prompt version을 사용한다.
- 목록·홈·상세 API를 제공한다.
- 정적 `/home` route가 동적 route에 가려지지 않는다.
- Weekly CronJob manifest를 제공한다.
- 실제 K3s apply와 production 실행은 수행하지 않는다.
- Weekly 집중 테스트, Daily 및 3일 Topic 회귀 테스트가 통과한다.
- 전체 pytest, unittest, compileall과 `git diff --check`가 통과한다.
- Verification에는 실제 실행한 명령과 결과만 기록한다.

## Notes

### DB 설계 확정 시점

이 Task에 기록된 DB 이름과 구조는 구현 전 확정안이 아니다.

UNIT-01에서 현재 3일 Topic 구조를 조사한 뒤 다음 순서로 결정한다.

```text
3일 Topic migration·model·repository 분석
→ 기존 계약 중 재사용 가능한 부분 식별
→ Weekly 고유 요구사항 식별
→ DB 대안 비교
→ 선택 근거 기록
→ migration 구현
```

3일 Topic과 Weekly Topic의 저장 요구가 사실상 동일하다면 naming만 Weekly로
분리하고 구조를 맞춘다.

주간 범위, 조회 방식 또는 idempotency 때문에 다른 구조가 필요하면 해당
차이만 추가한다.

기존 3일 Topic을 범용 기간 테이블로 리팩터링하는 작업은 기존 데이터 migration과
API 변경이 필요할 수 있으므로 이번 작업의 기본 범위에 포함하지 않는다.

### Weekly 고유 요구사항

DB 설계 시 최소한 다음 주간 특성을 고려한다.

- rolling 168시간이 아닌 완료된 calendar week
- 월요일부터 일요일까지의 표시 범위
- 동일 주간 수동 재처리
- 최소 기사 수와 최소 source 수
- 요약 근거 기사 최대 5개
- 주간 흐름 전용 summary prompt
- 최신 완료 주간 home 조회
- 매주 월요일 CronJob 실행

### 3일 Topic과의 관계

3일 Topic은 최근 72시간 rolling window를 사용한다.

Weekly Topic은 완료된 월요일~일요일 calendar week를 사용한다.

두 pipeline은 기사와 기존 embedding을 공유하지만 저장 결과를 서로
재집계하지 않는다.

## Implementation Units

- [x] UNIT-01: 기존 Daily·3일 Topic·embedding 구조 분석 및 7일 Topic DB·실행 계약 확정
- [x] UNIT-02: UNIT-01 설계 결과 기반 7일 Topic migration과 repository 구현
- [x] UNIT-03: 직전 완료 주간 후보 조회 및 기존 article embedding 재사용 구현
- [x] UNIT-04: 7일 Topic 재클러스터링·최소 기사/출처 조건·대표/관련/요약 근거 기사 선정 구현
- [x] UNIT-05: 선택 기사 원문 확보·주간 요약 생성·실패 격리·idempotent 저장 구현
- [x] UNIT-06: 7일 Topic 목록·홈·상세 API 구현
- [x] UNIT-07: 7일 Topic CronJob manifest와 실행 진입점 구현
- [x] UNIT-08: 전체 회귀 검증·운영 수동 절차·README 및 설계 문서 정리
