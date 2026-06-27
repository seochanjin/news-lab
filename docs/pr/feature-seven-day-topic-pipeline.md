# 최근 7일 기사·토픽 파이프라인 확장

## 작업 내용

- 기존 Daily Topic과 3일 Topic 운영 계약을 유지하면서, 직전 완료 주간
  월요일-일요일 기사와 저장된 `article_embeddings`를 재사용하는 Weekly Topic
  pipeline을 추가한다.
- Weekly 전용 DB 테이블, repository, pipeline stage, API, 실행 script와 K3s
  CronJob manifest를 추가한다.
- README, Architecture, Runbook, Weekly 설계 문서에 운영 계약과 사람이 수행할
  production 적용·검증 절차를 기록한다.

## 주요 변경 사항

- `app/services/topic_pipeline/candidate_stage.py`를 추가해 저장된
  `article_embeddings` 기반 후보 조회 helper를 공통화하고, 기존 3일 Topic 후보
  stage가 이를 사용하도록 변경했다.
- `app/services/weekly_topic_pipeline/`에 Weekly context 계산, 후보 조회,
  재클러스터링, 최소 기사 수·source 수 필터, 대표·관련·Summary 근거 기사 선정,
  원문 확보, 주간 Summary 생성, Topic별 실패 격리와 idempotent 저장 흐름을
  추가했다.
- `scripts/run_weekly_topic_pipeline.py`를 추가해 기본 dry-run, `--week-start`
  월요일 재처리, `--execute --use-summary-provider` 실행 흐름과 run completion
  기록을 제공한다.
- `k8s/news-weekly-topic-pipeline-cronjob.yaml`을 추가해 매주 월요일 00:30
  `Asia/Seoul`에 Weekly Topic pipeline을 실행하도록 정의했다.
- `docs/design/weekly-topic-pipeline.md`, README, Architecture/Runbook 문서를
  Weekly Topic 설계와 human-controlled 운영 절차에 맞게 갱신했다.

## 추가/변경된 API

- `GET /weekly-topics`
  - Weekly Topic 목록을 조회한다.
  - `week_start`, `week_end`, `window_start`, `window_end`, `article_count`,
    `source_count`, `keywords`, `status`를 포함한다.
- `GET /weekly-topics/home`
  - 성공 또는 부분 성공 run이 만든 최신 완료 주간의 home card payload를
    반환한다.
- `GET /weekly-topics/{topic_id}`
  - Weekly Topic 상세와 `weekly_topic_articles.rank` 순서의 관련 기사,
    `is_representative`, `is_summary_evidence` flag를 반환한다.
- 기존 `/topics`, `/topics/{topic_id}`, `/topics/home` 및
  `/three-day-topics`, `/three-day-topics/home`, `/three-day-topics/{topic_id}`
  API contract는 변경하지 않는다.

## DB 변경 사항

- `db/migrations/008_create_weekly_topic_tables.sql`을 추가했다.
- 신규 테이블:
  - `weekly_topic_runs`
  - `weekly_topics`
  - `weekly_topic_articles`
- Weekly Topic 결과는 기존 `topics`, `topic_articles`,
  `three_day_topics`, `three_day_topic_articles`, `three_day_topic_runs`와 분리해
  저장한다.
- repository는 window advisory lock 안에서 기존 window 결과 삭제와 신규 결과
  삽입을 원자적으로 수행한다. 전체 Topic 실패 시 결과 교체를 호출하지 않아 기존
  성공 결과를 보존하고, 정상 빈 결과는 빈 결과로 window를 교체한다.
- 실제 Supabase 또는 production DB migration 적용과 적용 후 table/constraint/index
  확인은 사람이 수행해야 하며, 이 PR 작성 과정에서는 실행하지 않았다.

## README 영향

- README를 갱신했다.
- Weekly API, dry-run 실행 예시, Weekly 설계 문서 링크를 추가했다.
- 판단 근거: 이번 변경은 새 pipeline, API, 실행 script, CronJob과 운영 문서를
  추가하므로 repository 진입 문서에서 사용자가 기능 위치와 로컬 실행 방법을
  찾을 수 있어야 한다.

## 테스트

- `python -m pytest`
  - 398 tests passed in 14.27s.
- `python -m unittest discover -s tests`
  - 398 tests ran, OK.
- `python -m compileall app scripts tests`
  - passed.
- `git diff --check`
  - passed.
- Daily 회귀:
  - `python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v`
  - 23 tests passed.
- 3일 Topic 회귀:
  - `python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`
  - 33 tests passed, 6 subtests passed.
- Weekly 집중 검증:
  - `python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py -v`
  - 28 tests passed, 6 subtests passed.
  - `python -m pytest tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`
  - 9 tests passed.

## 확인 결과

- `docs/verification/feature-seven-day-topic-pipeline.md` 기준 전체 verification
  status는 `passed`다.
- Daily Topic service, runner와 CronJob manifest에는 tracked diff가 없다.
- 3일 Topic runner와 CronJob manifest에는 tracked diff가 없고, 후보 stage만 공통
  helper 사용으로 변경됐다.
- Weekly runner는 신규 embedding provider flag를 제공하지 않고 기존
  `article_embeddings` 재사용 계약을 유지한다.
- Weekly CronJob은 기존 image, `DATABASE_URL`, `OPENAI_SUMMARY_API_KEY`, 보안
  설정 패턴을 재사용하며 `OPENAI_EMBEDDING_API_KEY`를 주입하지 않는다.
- `kubectl apply --dry-run=client -f k8s/news-weekly-topic-pipeline-cronjob.yaml`는
  현재 지침상 Agent가 실행하지 않았고, manifest 구조는 pytest로 검증했다.

## 비고

- Approved fixes source인
  `docs/fixes/feature-seven-day-topic-pipeline-approved-fixes.md`에는 적용할 승인
  fix 항목이 없다.
- PR merge, production deployment, K3s rollout 완료를 주장하지 않는다.
- Agent는 `git push`, `git merge`, Supabase SQL, production migration,
  `kubectl apply`, rollout, production API curl을 실행하지 않았다.
- K3s client/server dry-run, 실제 apply, 수동 Job 생성, production log/API 확인,
  Supabase 또는 production DB migration 적용과 적용 후 검증은 사람이 수행해야
  한다.
