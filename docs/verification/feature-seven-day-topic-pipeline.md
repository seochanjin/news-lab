# Verification: 최근 7일 기사·토픽 파이프라인 확장

## Verification Status

passed

## Verification Scope

UNIT-01: 기존 Daily·3일 Topic·embedding 구조 분석 및 7일 Topic DB·실행 계약
확정.

UNIT-02: UNIT-01 설계 결과 기반 7일 Topic migration과 repository 구현.

UNIT-03: 직전 완료 주간 후보 조회 및 기존 article embedding 재사용 구현.

UNIT-04: 7일 Topic 재클러스터링, 최소 기사·출처 조건, 대표·관련·Summary 근거
기사 선정 구현.

UNIT-05: 선택 기사 원문 확보, 주간 요약 생성, Topic별 실패 격리와 idempotent
window 결과 저장 연결 구현.

UNIT-06: 7일 Topic 목록·홈·상세 API 구현.

UNIT-07: 7일 Topic CronJob manifest와 실행 진입점 구현.

UNIT-08: 전체 회귀 검증, 운영 수동 절차, README와 architecture/runbook/design 문서
정리.

## Commands Run

Command:
`pwd && git branch --show-current && git status --short`

Result:
현재 작업 경로는 `/Users/seochanjin/workspace/NewsLab/news-lab`, branch는
`feature/seven-day-topic-pipeline`이다. 작업 전 상태에는 기존 미추적 task,
verification, PR, devlog, review, fixes 문서와 `docs/tasks/main.md` 수정이
있었다.

Status: passed

Command:
`rg -n "three_day_topics|three_day_topic_articles|three_day_topic_runs" db/migrations app scripts tests`

Result:
`db/migrations/007_create_three_day_topic_tables.sql`,
`app/services/three_day_topic_pipeline/repository.py`,
`app/services/three_day_topic_pipeline/topic_selection_stage.py`,
`app/services/three_day_topic_pipeline/summary_persistence_stage.py`,
`app/routers/three_day_topics.py`, 3일 Topic 관련 tests에서 기존 3일 Topic
테이블, repository, API, 테스트 계약을 확인했다.

Status: passed

Command:
`rg -n "three-day-topics|three_day_topics" app tests docs`

Result:
`app/main.py`, `app/routers/three_day_topics.py`,
`tests/test_three_day_topics_api.py`, architecture/runbook/design 문서에서 기존
3일 Topic route 등록, API route 순서, 운영 문서 참조를 확인했다.

Status: passed

Command:
`python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`

Result:
33 tests passed, 6 subtests passed in 0.49s.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_pipeline.py -v`

Result:
첫 실행은 새 UNIT-05 원문 확보 테스트 fixture가 상태 없는 Summary 후보를
`not_extracted` 재시도 가능 기사로 취급하는 stage 정책과 맞지 않아
`test_raw_acquisition_reuses_extracts_and_keeps_fallback_related_text`에서 실패했다.
테스트 fixture를 실제 정책에 맞게 조정한 뒤 같은 명령을 재실행해 19 tests
passed, 6 subtests passed in 0.13s.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_repository.py tests/test_weekly_topic_pipeline.py -v`

Result:
30 tests passed, 6 subtests passed in 0.13s. Weekly repository의 원자적 결과 교체
계약과 UNIT-05의 선택 기사 원문 조회, Summary 후보 지연 추출, fallback 원문 사용,
주간 prompt/provider adapter, Topic별 실패 격리, 부분 성공 저장, 전체 실패 시 기존
window 결과 보존, 정상 빈 결과 교체를 함께 확인했다.

Status: passed

Command:
`python -m compileall app/services/weekly_topic_pipeline tests/test_weekly_topic_pipeline.py`

Result:
Weekly pipeline package와 `tests/test_weekly_topic_pipeline.py` compile 성공.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py -v`

Result:
24 tests passed, 6 subtests passed in 0.15s. 공통 후보 helper 전환 이후 3일 Topic
실행 진입점, 후보 조회, 선정, 원문 확보와 Summary stage 회귀를 확인했다.

Status: passed

Command:
`python -m pytest tests/test_daily_topic_article_selection.py tests/test_daily_topic_pipeline_configuration.py -v`

Result:
11 tests passed in 0.12s. `app.services.topic_pipeline` package export 변경 이후
Daily Topic의 공통 selection helper import와 기사 선정 계약 회귀를 확인했다.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_pipeline.py tests/test_three_day_topic_pipeline.py -v`

Result:
첫 실행은 `app.services.topic_pipeline.__init__`가 기존 selection helper를 export하지
않아 `tests/test_three_day_topic_pipeline.py` collection 중
`ImportError: cannot import name 'attach_article_urls'`로 실패했다. 공통 package
export를 복원한 뒤 같은 명령을 재실행해 24 tests passed, 12 subtests passed in
0.13s.

Status: passed

Command:
`python -m compileall app/services/topic_pipeline app/services/weekly_topic_pipeline app/services/three_day_topic_pipeline tests/test_weekly_topic_pipeline.py`

Result:
공통 후보 helper, Weekly context/candidate/model, 3일 후보 stage와 Weekly 테스트
compile 성공.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_repository.py tests/test_weekly_topic_pipeline.py -v`

Result:
19 tests passed, 6 subtests passed in 0.12s. Weekly repository 계약과 UNIT-03의
직전 완료 주간 context, 명시 `week_start`, 후보 조회 window, 기존
`article_embeddings` read-only 재사용, embedding 누락 사유 통계를 함께 확인했다.

Status: passed

Command:
`rg -n "weekly_candidates|load_weekly_candidates|resolve_weekly_pipeline_context|WeeklyCandidateStageResult|WeeklyPipelineContext|article_embeddings|coalesce\\(a\\.published_at" app/services tests docs/tasks/feature-seven-day-topic-pipeline.md docs/verification/feature-seven-day-topic-pipeline.md`

Result:
`app/services/weekly_topic_pipeline/context.py`,
`app/services/weekly_topic_pipeline/candidate_stage.py`,
`app/services/weekly_topic_pipeline/models.py`,
`app/services/topic_pipeline/candidate_stage.py`,
`tests/test_weekly_topic_pipeline.py`에서 Weekly context와 후보 조회 구현 및 테스트를
확인했다. 공통 후보 helper는 `coalesce(a.published_at, a.created_at)` window와
`article_embeddings` read-only 조회를 사용한다.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_repository.py -v`

Result:
11 tests passed in 0.07s. Weekly migration 정적 검사, run 생성·종료 transaction,
window advisory lock, 기존 결과 삭제와 신규 Topic·기사 관계 삽입 순서, 빈 결과
교체, insert 실패 rollback, 주간 시작일·최소 기사 수·최소 source 수·Summary
근거 최대 5개 검증을 확인했다.

Status: passed

Command:
`python -m compileall app/services/weekly_topic_pipeline tests/test_weekly_topic_repository.py`

Result:
`app/services/weekly_topic_pipeline/__init__.py`,
`app/services/weekly_topic_pipeline/models.py`,
`app/services/weekly_topic_pipeline/repository.py`,
`tests/test_weekly_topic_repository.py` compile 성공.

Status: passed

Command:
`rg -n "weekly_topics|weekly_topic_articles|weekly_topic_runs" db/migrations app tests`

Result:
`db/migrations/008_create_weekly_topic_tables.sql`,
`app/services/weekly_topic_pipeline/repository.py`,
`tests/test_weekly_topic_repository.py`에서 Weekly 전용 table, query와 검증 항목을
확인했다.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_pipeline.py -v`

Result:
13 tests passed, 6 subtests passed in 0.15s. Weekly context, 후보 조회와 함께
UNIT-04의 재클러스터링, 최소 기사 5개·source 2개 필터, 대표·관련 기사 선정,
source 다양성을 반영한 Summary 근거 최대 5개 선정과 중복 URL·제목 제외를
확인했다.

Status: passed

Command:
`python -m compileall app/services/weekly_topic_pipeline tests/test_weekly_topic_pipeline.py`

Result:
Weekly pipeline package와 `tests/test_weekly_topic_pipeline.py` compile 성공.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_repository.py tests/test_weekly_topic_pipeline.py -v`

Result:
24 tests passed, 6 subtests passed in 0.12s. Weekly repository 계약과 UNIT-04
선정 stage 계약을 함께 확인했다.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`python -m pytest tests/test_weekly_topics_api.py -v`

Result:
6 tests passed in 0.29s. Weekly API의 archive filter bind, pagination, 최신
publishable 주간 home card, 빈 home payload, 상세 관련 기사 rank/role flag,
404 응답과 `/weekly-topics/home` route가 동적 `/{topic_id}`보다 먼저 등록되는
계약을 확인했다.

Status: passed

Command:
`rg -n "weekly-topics|weekly_topics" app tests docs/tasks/feature-seven-day-topic-pipeline.md docs/design/weekly-topic-pipeline.md`

Result:
`app/main.py`, `app/routers/weekly_topics.py`, `tests/test_weekly_topics_api.py`,
Weekly pipeline service, task와 design 문서에서 Weekly API route, table, test
참조를 확인했다.

Status: passed

Command:
`python -m pytest tests/test_weekly_topics_api.py tests/test_three_day_topics_api.py -v`

Result:
12 tests passed in 0.22s. Weekly API 추가와 `app/main.py` route 등록 이후 Weekly
목록·홈·상세 API와 기존 3일 Topic 목록·홈·상세 API 계약 회귀를 함께 확인했다.

Status: passed

Command:
`python -m compileall app/routers/weekly_topics.py app/main.py tests/test_weekly_topics_api.py`

Result:
`tests/test_weekly_topics_api.py` compile 성공. `app/routers/weekly_topics.py`와
`app/main.py`는 이미 최신 bytecode 상태로 오류 없이 완료됐다.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`git diff --name-only`

Result:
Tracked diff에는 `app/main.py`,
`app/services/three_day_topic_pipeline/candidate_stage.py`,
`app/services/topic_pipeline/__init__.py`, `docs/ARCHITECTURE.md`,
`docs/tasks/main.md`가 표시됐다. UNIT-06에서 직접 수정한 tracked file은
`app/main.py`이며, task와 verification 문서는 현재 branch의 기존 미추적 file
상태다.

Status: passed

Command:
`git status --short`

Result:
작업트리에는 UNIT-06에서 수정한 `app/main.py`와 새
`app/routers/weekly_topics.py`, `tests/test_weekly_topics_api.py`가 포함되어 있다.
그 밖에 이전 UNIT에서 생성·수정된 Weekly pipeline, migration, design, task,
verification, PR/devlog/review/fixes 문서와 기존 tracked 변경이 함께 남아 있다.

Status: passed

Command:
`python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`

Result:
12 tests passed in 0.17s. Weekly 실행 진입점의 dry-run 기본값, `--week-start`
월요일 검증, execute provider/key 조건, embedding provider flag 부재, context
전달, execute stage 호출, 후보 조회 connection 반환, run completion 변환과
CronJob manifest의 월요일 00:30 Asia/Seoul schedule, 전용 command, Secret·보안
설정을 확인했다.

Status: passed

Command:
`python -m compileall scripts/run_weekly_topic_pipeline.py tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline_cronjob_manifest.py`

Result:
`scripts/run_weekly_topic_pipeline.py`,
`tests/test_run_weekly_topic_pipeline.py`,
`tests/test_weekly_topic_pipeline_cronjob_manifest.py` compile 성공.

Status: passed

Command:
`python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py -v`

Result:
28 tests passed, 6 subtests passed in 0.16s. Weekly 실행 진입점과 기존 Weekly
context, 후보 조회, 재클러스터링, 원문 확보, Summary persistence 계약을 함께
확인했다.

Status: passed

Command:
`python -m pytest tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`

Result:
3 tests passed in 0.02s. Weekly CronJob manifest의 schedule, command, 기존 image,
DATABASE_URL·OPENAI_SUMMARY_API_KEY Secret 재사용, embedding key 미사용, pod
security/resource/tmp volume 설정을 확인했다.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`rg -n "run_weekly_topic_pipeline|news-weekly-topic-pipeline|weekly-topic-pipeline-cronjob|--week-start|30 0 \\* \\* 1" scripts k8s tests docs/tasks/feature-seven-day-topic-pipeline.md docs/verification/feature-seven-day-topic-pipeline.md`

Result:
`scripts/run_weekly_topic_pipeline.py`,
`k8s/news-weekly-topic-pipeline-cronjob.yaml`,
`tests/test_run_weekly_topic_pipeline.py`,
`tests/test_weekly_topic_pipeline_cronjob_manifest.py`, task와 verification 문서에서
Weekly 실행 진입점, CronJob 이름, manifest test, `--week-start` 계약과
`30 0 * * 1` schedule 참조를 확인했다.

Status: passed

Command:
`kubectl apply --dry-run=client -f k8s/news-weekly-topic-pipeline-cronjob.yaml`

Result:
실행하지 않았다. 현재 AGENTS/common 규칙과 forbidden commands가 `kubectl apply`
실행을 금지하므로 client-side dry-run도 Agent가 수행하지 않았다. 로컬 YAML
구조는 `tests/test_weekly_topic_pipeline_cronjob_manifest.py`로 검증했다.

Status: skipped

Command:
`python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v`

Result:
23 tests passed in 0.21s. Daily Topic 실행 진입점과 CronJob manifest 회귀를
확인했다.

Status: passed

Command:
`python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`

Result:
33 tests passed, 6 subtests passed in 0.41s. 기존 3일 Topic 실행 진입점, pipeline,
API와 CronJob manifest 회귀를 확인했다.

Status: passed

Command:
`python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py -v`

Result:
28 tests passed, 6 subtests passed in 0.20s. Weekly 실행 진입점과 Weekly pipeline
context, 후보 조회, 선정, 원문 확보, Summary persistence 계약을 확인했다.

Status: passed

Command:
`python -m pytest tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`

Result:
9 tests passed in 0.34s. Weekly API와 Weekly CronJob manifest 계약을 확인했다.

Status: passed

Command:
`python -m pytest`

Result:
398 tests passed in 14.27s.

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
398 tests ran in 13.863s, OK. 일부 CLI validation 테스트가 의도한 argparse error와
stage failure log를 출력했지만 전체 unittest 결과는 OK였다.

Status: passed

Command:
`python -m compileall app scripts tests`

Result:
`app`, `scripts`, `tests` compile 성공.

Status: passed

Command:
`git diff --check`

Result:
No whitespace errors.

Status: passed

Command:
`git diff --stat`

Result:
Tracked diff에는 `README.md`, `app/main.py`,
`app/services/three_day_topic_pipeline/candidate_stage.py`,
`app/services/topic_pipeline/__init__.py`, `docs/ARCHITECTURE.md`,
`docs/RUNBOOK.md`, `docs/architecture/pipeline.md`,
`docs/runbooks/cronjobs.md`, `docs/tasks/main.md`가 표시됐다. UNIT-08에서 추가로
수정한 tracked file은 README와 architecture/runbook/design 문서다. Weekly 신규
파일과 branch별 workflow 문서는 미추적 상태이므로 이 stat에는 포함되지 않았다.

Status: passed

Command:
`git diff --name-only`

Result:
Tracked diff file은 `README.md`, `app/main.py`,
`app/services/three_day_topic_pipeline/candidate_stage.py`,
`app/services/topic_pipeline/__init__.py`, `docs/ARCHITECTURE.md`,
`docs/RUNBOOK.md`, `docs/architecture/pipeline.md`,
`docs/runbooks/cronjobs.md`, `docs/tasks/main.md`다.

Status: passed

Command:
`git diff -- app/services/daily_topic_pipeline scripts/run_daily_topic_pipeline.py k8s/news-daily-topic-pipeline-cronjob.yaml`

Result:
출력 없음. Daily Topic pipeline service, 실행 script, CronJob manifest에는 tracked
diff가 없다.

Status: passed

Command:
`git diff -- app/services/three_day_topic_pipeline scripts/run_three_day_topic_pipeline.py k8s/news-three-day-topic-pipeline-cronjob.yaml`

Result:
`app/services/three_day_topic_pipeline/candidate_stage.py`가 공통 후보 helper를
사용하도록 변경된 diff만 표시됐다. 기존 3일 Topic 실행 script와 CronJob manifest
diff는 없다.

Status: passed

Command:
`rg -n "weekly-topics|weekly_topics|run_weekly_topic_pipeline|news-weekly-topic-pipeline|008_create_weekly_topic_tables|7일 Topic|Weekly topic" README.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture/pipeline.md docs/runbooks/cronjobs.md docs/design/weekly-topic-pipeline.md`

Result:
README, Architecture index, Runbook index, pipeline architecture, CronJob runbook,
Weekly design 문서에서 Weekly API, table, migration, runner, CronJob과 운영 수동
절차 참조를 확인했다.

Status: passed

## Results

- 3일 Topic은 `three_day_topic_runs`, `three_day_topics`,
  `three_day_topic_articles` 세 테이블로 run 이력, 활성 결과, 기사 관계를
  분리한다.
- 3일 Topic 저장소는 run 생성/종료 transaction과 결과 교체 transaction을
  분리하며, 결과 교체는 window advisory lock 안에서 삭제와 삽입을 원자적으로
  수행한다.
- 3일 Topic 후보 조회는 `coalesce(published_at, created_at)` 기준 window와
  기존 `article_embeddings` 호환 row만 사용한다.
- Daily Topic 저장 구조는 실행 window 감사와 부분 성공 상태가 없어 Weekly
  설계 기준으로는 3일 Topic 구조를 따르는 것이 적합하다.
- Weekly DB·실행 계약은 `docs/design/weekly-topic-pipeline.md`에 확정했다.
- `db/migrations/008_create_weekly_topic_tables.sql`을 추가해
  `weekly_topic_runs`, `weekly_topics`, `weekly_topic_articles` 전용 테이블,
  FK, unique, count check와 조회 index를 정의했다.
- `app/services/weekly_topic_pipeline/`에 run 시작·종료 model, Topic·기사 관계
  model과 `WeeklyTopicRepository`를 추가했다.
- Weekly repository는 3일 Topic과 같은 run 이력 분리, advisory lock 기반
  window 결과 교체, insert 실패 시 rollback, 빈 결과 교체 계약을 따른다.
- Weekly model은 월요일 시작 완료 주간, 정확한 7일 window, 최소 기사 5개,
  최소 source 2개, Summary 근거 최대 5개와 대표 기사 1건을 저장 전에 검증한다.
- 공통 `app/services/topic_pipeline/candidate_stage.py`를 추가해
  `coalesce(published_at, created_at)` 기준 window 후보 조회와 저장
  `article_embeddings` metadata/hash/vector 검증을 공통화했다.
- 기존 3일 후보 stage는 공통 helper를 사용하도록 전환했고, 3일 후보·선정·요약
  테스트로 기존 동작 회귀를 확인했다.
- `resolve_weekly_pipeline_context`는 인자가 없을 때 Asia/Seoul 기준 실행 시점보다
  앞선 가장 최근 완료 주간을 선택하고, 명시 `week_start`는 월요일만 허용한다.
- `load_weekly_candidates`는 Weekly context의 동일 `window_start`, `window_end`를
  사용해 후보를 조회하고, 기존 embedding이 없거나 metadata/hash/vector가 맞지
  않는 기사는 실패 대신 누락 사유 통계로 제외한다.
- `cluster_and_select_weekly_topics`를 추가해 저장 embedding 후보를 완료 주간
  기준으로 직접 재클러스터링하고 Daily 또는 3일 Topic 저장 결과를 입력으로
  사용하지 않도록 했다.
- Weekly 선정 stage는 기본 threshold 인자를 검증하고, 정상 embedding 5건 미만은
  빈 결과로 처리하며, 기사 수 5개 이상·source 수 2개 이상인 군집만 Topic 후보로
  유지한다.
- 관련 기사는 기존 대표 후보 점수 순서로 제한하고, Summary 근거 기사는 대표
  기사를 포함하면서 URL·정규화 제목 중복을 제외하고 가능한 새 source를 우선해
  Topic당 최대 5개까지 결정론적으로 선정한다.
- `acquire_weekly_topic_raw_texts`를 추가해 선택 Topic의 관련 기사 원문을 먼저
  조회하고, 원문이 없는 Summary 후보 기사에 한해 지연 추출을 수행한다.
- 주간 원문 확보 단계는 extractor 예외를 기사별 실패로 기록하고 다음 Topic
  처리를 계속하며, 관련 기사 원문을 함께 보관해 Summary 후보 원문 확보 실패 시
  같은 Topic의 다음 순위 기사 원문을 대체 근거로 사용할 수 있게 했다.
- `weekly-flow-v1` prompt version과 `WeeklyOpenAISummaryProvider`를 추가해 지난
  월요일부터 일요일까지의 변화, 반복 쟁점, 여러 출처의 공통 내용과 불확실성을
  설명하는 주간 전용 Summary prompt를 사용한다.
- `summarize_and_persist_weekly_topics`는 Topic별 원문 부족과 provider 실패를
  격리하고, 성공 Topic이 있으면 성공 부분집합만 repository의 window 교체
  transaction에 전달해 `partial_success`로 기록할 수 있게 했다.
- 모든 Topic이 실패한 실행은 repository 교체를 호출하지 않아 기존 성공 window
  결과를 보존하고, 정상 빈 선정 결과는 빈 결과로 window를 원자 교체한다.
- `app/routers/weekly_topics.py`를 추가해 `/weekly-topics`,
  `/weekly-topics/home`, `/weekly-topics/{topic_id}` read API를 제공하고,
  `app/main.py`에 Weekly router를 등록했다.
- Weekly API는 `week_start`, `week_end`, `window_start`, `window_end`,
  `article_count`, `source_count`, `keywords`, `status`를 포함한 목록·상세
  payload를 반환하고, 상세에서는 `weekly_topic_articles.rank` 순서의 전체 관련
  기사와 `is_representative`, `is_summary_evidence`를 노출한다.
- `/weekly-topics/home`은 성공 또는 부분 성공 run이 만든 최신 완료 주간 window의
  card payload를 반환하며, 정적 `/home` route는 동적 `/{topic_id}` route보다 먼저
  등록된다.
- `scripts/run_weekly_topic_pipeline.py`를 추가해 기본 dry-run, 명시
  `--week-start` 월요일 재처리, execute provider/key 조건, read-only 후보 조회,
  Weekly 선정·원문 확보·Summary 저장 orchestration, run 생성·종료 기록을 제공한다.
- Weekly 실행 진입점은 신규 embedding provider flag를 제공하지 않고 기존
  `article_embeddings` 재사용 계약을 유지한다.
- `k8s/news-weekly-topic-pipeline-cronjob.yaml`을 추가해 매주 월요일 00:30
  `Asia/Seoul`에 전용 runner를 `--execute --use-summary-provider`로 실행하도록
  정의했다.
- Weekly CronJob은 기존 image, `DATABASE_URL`, `OPENAI_SUMMARY_API_KEY`,
  node selector, `/tmp` emptyDir, resource와 securityContext 패턴을 3일 Topic
  CronJob과 맞추며 `OPENAI_EMBEDDING_API_KEY`를 주입하지 않는다.
- README에 Weekly API, dry-run 실행 예시와 설계 문서 링크를 추가했다.
- Architecture index와 pipeline 세부 문서에 Weekly Topic pipeline, CronJob,
  read API와 운영 절차 참조를 추가했다.
- Runbook index와 CronJob runbook에 Weekly 최초 반영 순서, migration 적용 후
  확인 기준, K3s dry-run/apply, 수동 Job, log/API 확인과 idempotency 확인 절차를
  human-controlled 작업으로 기록했다.
- Weekly design 문서의 migration 상태 문구를 실제 추가된
  `db/migrations/008_create_weekly_topic_tables.sql` 기준으로 정리했다.

## Manual or Production Verification

없음. UNIT-01부터 UNIT-08까지 production DB, K3s, Supabase SQL, production API
curl을 실행하지 않았다. `008_create_weekly_topic_tables.sql`의 실제 Supabase 또는
production DB 적용과 `k8s/news-weekly-topic-pipeline-cronjob.yaml`의 K3s
client/server dry-run, apply, 수동 Job, scheduled Job 및 운영 API 확인은 사람이
수행해야 한다.

## Pending Verification

- `kubectl apply --dry-run=client -f k8s/news-weekly-topic-pipeline-cronjob.yaml`는
  현재 지침상 Agent가 실행하지 않았으며, 사람이 수행해야 한다.
- `KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server -f k8s/news-weekly-topic-pipeline-cronjob.yaml`,
  실제 K3s apply, 수동 Job 생성, production log/API 확인은 사람이 수행해야 한다.
- Supabase 또는 production DB migration 적용과 적용 후 table/constraint/index
  확인은 사람이 수행해야 한다.

## Evidence Notes

- `docs/design/weekly-topic-pipeline.md`를 추가해 DB 테이블 수, naming, 주간
  식별 정보, unique 기준, 기사 관계, 대표·요약 근거 표현, run 상태,
  foreign key, index, 재실행 교체 정책, rollback/복구 방침을 기록했다.
- UNIT-02에서 Weekly migration, 저장 model, repository와 repository 테스트를
  추가했다.
- UNIT-03에서 Weekly context, 후보 조회 stage, 공통 후보 조회 helper와 Weekly
  후보 테스트를 추가했다.
- UNIT-04에서 Weekly 재클러스터링·기사 선정 stage와 Weekly 선정 테스트를
  추가했다.
- UNIT-05에서 Weekly 원문 확보 stage, 주간 Summary persistence stage와
  Topic별 실패 격리·idempotent 저장 연결 테스트를 추가했다.
- UNIT-06에서 `app/routers/weekly_topics.py`와 `tests/test_weekly_topics_api.py`를
  추가하고 `app/main.py`에 Weekly API router를 등록했다.
- UNIT-07에서 `scripts/run_weekly_topic_pipeline.py`,
  `k8s/news-weekly-topic-pipeline-cronjob.yaml`,
  `tests/test_run_weekly_topic_pipeline.py`,
  `tests/test_weekly_topic_pipeline_cronjob_manifest.py`를 추가했다.
- UNIT-08에서 README, Architecture index, pipeline architecture, Runbook index,
  CronJob runbook과 Weekly design 문서를 Weekly 운영 수동 절차와 전체 회귀 검증
  결과에 맞게 갱신했다.
- `docs/tasks/feature-seven-day-topic-pipeline.md`의 UNIT-01 조사 결과와
  UNIT-02, UNIT-03, UNIT-04, UNIT-05, UNIT-06, UNIT-07, UNIT-08 checklist를
  갱신했다.
