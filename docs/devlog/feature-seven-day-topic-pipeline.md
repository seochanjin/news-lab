# 최근 7일 기사·토픽 파이프라인 확장

## 작업 목적

직전 완료 주간의 기사와 기존 `article_embeddings`를 이용해 Daily Topic, 3일
Topic과 독립적인 7일 Topic 결과를 생성하고 API로 제공한다.

이번 작업의 핵심 목표는 월요일 00:00부터 다음 월요일 00:00 미만까지의 완료된
calendar week를 한 번의 실행 context로 고정하고, 해당 주간 기사를 직접
재클러스터링해 주간 흐름을 설명하는 Topic을 만드는 것이다.

## 기존 문제

기존 Daily Topic은 일 단위 결과이고 3일 Topic은 rolling 72시간 결과다. 따라서
월요일부터 일요일까지의 완료 주간 흐름을 별도 기준으로 조회하거나 재처리할 수
없었다.

Daily 또는 3일 Topic 결과를 다시 집계하면 원래 pipeline의 API contract, 저장
데이터 의미, 실행 window가 섞일 수 있다. 특히 Weekly Topic은 완료 주간,
최소 기사 5개, 최소 source 2개, Summary 근거 최대 5개라는 별도 정책이 필요해
기존 테이블을 그대로 쓰기 어렵다.

## 변경 내용

- Weekly 전용 DB schema로 `weekly_topic_runs`, `weekly_topics`,
  `weekly_topic_articles`를 추가했다.
- 저장된 `article_embeddings`를 read-only로 재사용하는 공통 후보 조회 helper를
  추가하고, 기존 3일 Topic 후보 stage도 이 helper를 사용하도록 정리했다.
- `app/services/weekly_topic_pipeline/`에 완료 주간 context, 후보 조회,
  재클러스터링, Topic 선정, 원문 확보, 주간 Summary 생성, idempotent 저장 흐름을
  추가했다.
- `/weekly-topics`, `/weekly-topics/home`, `/weekly-topics/{topic_id}` read API를
  추가하고 FastAPI router에 등록했다.
- `scripts/run_weekly_topic_pipeline.py`와
  `k8s/news-weekly-topic-pipeline-cronjob.yaml`을 추가했다.
- README, Architecture index, pipeline architecture, Runbook index, CronJob
  runbook, Weekly design 문서를 갱신했다.

## 구현 상세

Weekly context는 pipeline 시작 시 한 번 계산한다. 기본 실행은 `Asia/Seoul` 기준
실행 시점보다 앞선 가장 최근 완료 주간을 선택하고, 명시 재처리는
`--week-start YYYY-MM-DD` 형식의 월요일만 허용한다. 모든 stage와 저장 row는 같은
`week_start`, `week_end`, `window_start`, `window_end`를 사용한다.

후보 조회는 기사 시각을 `coalesce(published_at, created_at)` 기준으로 판단한다.
Weekly pipeline은 기존 `article_embeddings`만 조회하며 신규 embedding provider
호출이나 embedding insert/update를 수행하지 않는다. 누락, metadata 불일치,
stale hash, invalid vector는 실행 실패가 아니라 기사 단위 제외와 누락 통계로
처리한다.

Topic 선정은 저장 embedding을 이용해 완료 주간 기준으로 다시 clustering한다.
기사 수 5개 이상, source 수 2개 이상인 군집만 Weekly Topic 후보로 유지하고,
대표 기사와 관련 기사, Summary 근거 기사를 결정론적으로 선정한다. Summary 근거
기사는 대표 기사를 포함하고 URL·정규화 제목 중복을 피하며 가능한 source 다양성을
우선해 Topic당 최대 5개까지 선택한다.

원문 확보는 관련 기사 범위의 저장 원문을 먼저 조회하고, 원문이 없는 Summary
후보 기사에 한해 지연 추출을 수행한다. 특정 Topic의 원문 확보나 Summary provider
호출이 실패해도 다른 Topic 처리를 계속한다. 일부 Topic만 성공하면 성공 부분집합을
저장하고 run 상태를 `partial_success`로 남긴다.

저장은 3일 Topic에서 검증된 구조를 따른다. run 생성과 결과 교체 transaction을
분리하고, 결과 교체는 동일 `window_start`, `window_end` advisory transaction
lock 안에서 기존 결과 삭제와 신규 Topic·기사 관계 삽입을 함께 수행한다. 모든
Topic이 실패하면 결과 교체를 호출하지 않아 기존 성공 결과를 보존하고, 정상적으로
선정 Topic이 없는 경우는 빈 결과로 window를 원자 교체할 수 있다.

## 대안 검토

대안 A는 Weekly 전용 테이블을 추가하는 방식이다.

- `weekly_topic_runs`
- `weekly_topics`
- `weekly_topic_articles`

이 방식은 Daily와 3일 Topic의 기존 DB/API 계약을 건드리지 않고 Weekly 고유 정책을
독립적으로 표현할 수 있다. 대신 기간별 repository와 테이블이 늘어난다.

대안 B는 `period_topics`, `period_topic_articles`, `period_topic_runs` 같은 범용
기간 Topic 구조로 일반화하는 방식이다. 장기적으로는 기간 추가 비용을 줄일 수
있지만 기존 3일 Topic migration, repository, API, 운영 데이터를 함께 바꾸거나
이관해야 한다.

이번 task의 `Do not change` 범위는 기존 Daily/3일 Topic schema와 API contract를
깨지 않는 것이다. 따라서 대안 B는 범위와 운영 위험이 커서 선택하지 않았다.

## 선택한 접근과 근거

선택한 접근은 대안 A, 즉 Weekly 전용 테이블과 3일 Topic의 검증된 실행·저장
패턴을 조합하는 방식이다.

근거는 다음과 같다.

- Weekly Topic은 완료된 calendar week를 다루므로 rolling 72시간인 3일 Topic과
  실행 식별자가 다르다.
- Weekly Topic은 `week_start`, `week_end`, `--week-start`, 최소 source 수,
  Summary 근거 최대 5개 같은 별도 계약이 필요하다.
- 기존 Daily/3일 Topic API와 저장 데이터를 변경하지 않아 회귀 위험을 줄일 수
  있다.
- 3일 Topic의 run 이력, advisory lock 기반 원자 교체, Topic별 실패 격리,
  대표·Summary 근거 기사 flag 구조는 Weekly에도 그대로 유효하다.
- 저장 embedding만 재사용하므로 Weekly pipeline은 embedding 비용과 provider
  의존성을 추가하지 않는다.

## 트레이드오프

- 전용 테이블을 선택해 schema와 repository 수는 늘어났다. 대신 기존 운영 데이터
  이관 없이 Weekly 정책을 독립적으로 검증하고 롤백 판단도 단순하게 유지했다.
- 공통 후보 조회 helper를 도입해 3일 Topic stage에도 작은 변경이 들어갔다. 대신
  `article_embeddings` 호환성 검증과 누락 통계 계약을 기간 pipeline 간 일관되게
  유지할 수 있게 됐다.
- Weekly pipeline은 embedding을 새로 만들지 않는다. 따라서 embedding 누락 기사는
  Topic 후보에서 제외된다. 이는 주간 coverage를 일부 낮출 수 있지만, Daily
  pipeline의 embedding 저장 결과를 재사용한다는 task 요구와 운영 비용 통제에
  맞는 선택이다.
- 모든 Topic 실패 시 기존 결과를 보존한다. 실패한 실행이 최신 데이터를 비우지
  않는 장점이 있지만, 운영자는 run 상태와 기존 결과의 생성 시점을 함께 확인해야
  한다.
- CronJob과 DB migration은 문서와 manifest까지 준비했지만 실제 production 반영은
  사람이 수행해야 한다. 자동화 범위는 줄지만 production-impacting command 통제를
  유지한다.

## 테스트

테스트 결과의 source of truth는
`docs/verification/feature-seven-day-topic-pipeline.md`다.

- `python -m pytest`
  - 398 tests passed in 14.27s.
- `python -m unittest discover -s tests`
  - 398 tests ran in 13.863s, OK.
- `python -m compileall app scripts tests`
  - passed.
- `git diff --check`
  - passed.
- Daily 회귀 테스트:
  - `python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v`
  - 23 tests passed.
- 3일 Topic 회귀 테스트:
  - `python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`
  - 33 tests passed, 6 subtests passed.
- Weekly 실행·pipeline 집중 테스트:
  - `python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py -v`
  - 28 tests passed, 6 subtests passed.
- Weekly API와 CronJob manifest 테스트:
  - `python -m pytest tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`
  - 9 tests passed.

과거 중간 실패는 verification 문서에 기록된 뒤 수정·재실행으로 통과했다. Review
파일은 fix 승인 또는 verification 통과 근거로 사용하지 않았다.

## 운영 반영

운영 반영은 pending이다.

Agent는 production DB migration, Supabase SQL, K3s apply, K3s rollout, 수동 Job
실행, production API curl verification을 수행하지 않았다. 사람이 제공한 rollout
log나 production curl verification log도 없다.

사람이 수행해야 할 항목은 다음과 같다.

- `db/migrations/008_create_weekly_topic_tables.sql` review와 Supabase 또는
  production DB 적용
- 적용 후 `weekly_topic_runs`, `weekly_topics`, `weekly_topic_articles` table,
  constraint, index 확인
- `k8s/news-weekly-topic-pipeline-cronjob.yaml` client/server dry-run
- K3s manifest apply와 CronJob 상태 확인
- 수동 Job 생성 후 log, `weekly_topic_runs`, 저장 결과 확인
- `/weekly-topics`, `/weekly-topics/home`, `/weekly-topics/{topic_id}` production
  API 확인
- 다음 월요일 `00:30 Asia/Seoul` scheduled Job 확인

## README 업데이트 판단

README 업데이트는 필요했고 실제로 반영했다.

판단 근거는 이번 변경이 새 pipeline, API, 실행 script, CronJob, 설계 문서를
추가하기 때문이다. repository 진입 문서에서 Weekly API, dry-run 실행 예시,
상세 설계 문서 위치를 찾을 수 있어야 하므로 README에 해당 내용을 추가했다.

## 확인 결과

- `docs/verification/feature-seven-day-topic-pipeline.md` 기준 verification status는
  `passed`다.
- `docs/fixes/feature-seven-day-topic-pipeline-approved-fixes.md`에는 적용할 승인
  fix 항목이 없다.
- Daily Topic service, runner, CronJob manifest에는 tracked diff가 없다.
- 3일 Topic runner와 CronJob manifest에는 tracked diff가 없고, 후보 stage만 공통
  helper 사용으로 변경됐다.
- Weekly runner는 신규 embedding provider flag를 제공하지 않는다.
- Weekly CronJob은 기존 image, `DATABASE_URL`, `OPENAI_SUMMARY_API_KEY`, 보안
  설정 패턴을 재사용하고 `OPENAI_EMBEDDING_API_KEY`를 주입하지 않는다.
- `kubectl apply --dry-run=client -f k8s/news-weekly-topic-pipeline-cronjob.yaml`는
  현재 지침상 Agent가 실행하지 않았고, manifest 구조는 pytest로 검증했다.
- PR merge, production deployment, K3s rollout 완료는 주장하지 않는다.

## 이번 단계의 의미

Daily Topic과 rolling 72시간 Topic에 이어 완료 주간 기준의 Topic 생성 흐름이
backend 내부에서 독립된 제품 단위로 추가됐다. 데이터 저장, pipeline 실행,
read API, CronJob, 운영 문서, 검증 문서가 함께 준비되어 local acceptance 기준을
충족했다.

운영 관점에서는 기존 Daily/3일 Topic 계약을 건드리지 않고 새로운 기간 단위
Topic을 추가하는 패턴을 확립했다. 이후 월간 Topic 같은 기간 확장이 필요할 때도
전용 정책과 공통 helper를 조합하는 방식의 기준점으로 사용할 수 있다.

## 포트폴리오용 요약

NewsLab backend에 완료 주간 기준 7일 Topic pipeline을 설계·구현했다. 기존
Daily/3일 Topic 결과를 재집계하지 않고 저장된 article embedding을 직접
재사용해 주간 단위로 재클러스터링하며, 최소 기사 수와 source 다양성 조건을
적용해 주간 주요 이슈를 생성한다.

DB는 `weekly_topic_runs`, `weekly_topics`, `weekly_topic_articles`로 분리했고,
advisory lock 기반 원자 교체와 Topic별 실패 격리를 적용했다. FastAPI 목록·홈·상세
API, dry-run 기본 CLI, 매주 월요일 00:30 K3s CronJob manifest, architecture/runbook
문서와 테스트를 함께 정리했다. 전체 local test suite는 `398 passed`로 검증했다.

## 다음 단계 후보

- 사람이 production DB migration과 K3s manifest를 적용한 뒤 실제 run log와 API
  확인 결과를 verification 문서에 추가한다.
- 첫 수동 Job과 다음 월요일 scheduled Job의 `weekly_topic_runs` 통계를 비교해
  후보 수, embedding 누락 수, 저장 Topic 수가 기대 범위인지 확인한다.
- 운영 데이터가 쌓인 뒤 Weekly Summary 품질을 샘플링해 prompt 개선이나 source
  다양성 정책 조정이 필요한지 별도 task로 검토한다.
- 기간 Topic이 더 늘어날 가능성이 커지면 `period_topics` 일반화의 비용과 이관
  전략을 별도 architecture decision으로 검토한다.
