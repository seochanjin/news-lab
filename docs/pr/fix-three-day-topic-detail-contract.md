# 3일 Topic 상세 API key_points 응답 계약 수정

## 작업 내용

- `GET /three-day-topics/{topic_id}` 상세 API가 `three_day_topics.key_points`를
  조회하도록 수정했다.
- 상세 응답에서 `key_points`가 `NULL`인 경우 빈 배열 `[]`로 정규화했다.
- Three-day Topic 상세 API contract test에 `key_points` 값 있음, `NULL`, 빈 배열
  케이스를 추가했다.
- 기존 Three-day Topic 목록/home API, Daily/Weekly Topic API와 pipeline 계약은
  변경하지 않았다.

## 주요 변경 사항

- `app/routers/three_day_topics.py`
  - 상세 topic SELECT에 `key_points` 추가
  - 반환 payload 조립 전 `key_points` 기본값을 `[]`로 보정
- `tests/test_three_day_topics_api.py`
  - 상세 fixture에 `key_points` 지원 추가
  - 기존 articles 정렬/role flag 검증을 유지하면서 `key_points` 계약 검증 추가
- `docs/tasks/main.md`
  - 현재 task pointer를 `fix-three-day-topic-detail-contract.md`로 갱신
- Workflow 문서
  - branch별 task, verification, review, fix, PR, devlog 문서를 현재 작업 결과에
    맞게 작성 또는 갱신

## 추가/변경된 API

- 변경 endpoint: `GET /three-day-topics/{topic_id}`
- 상세 응답에 `key_points` 필드를 항상 포함한다.
- `key_points` 타입은 `list[str]`이다.
- DB 값이 존재하면 저장된 배열 순서를 유지해 반환한다.
- DB 값이 `NULL`이면 `[]`를 반환한다.
- DB 값이 빈 배열이면 `[]`를 반환한다.
- 변경하지 않은 API:
  - `GET /three-day-topics`
  - `GET /three-day-topics/home`
  - `GET /weekly-topics`
  - `GET /weekly-topics/home`
  - `GET /weekly-topics/{topic_id}`
  - `GET /topics`
  - `GET /topics/home`
  - `GET /topics/{topic_id}`

## DB 변경 사항

- DB migration 추가 없음.
- `three_day_topics`, `three_day_topic_articles`, `three_day_topic_runs` schema 변경
  없음.
- 기존 DB 데이터 수정, backfill, Supabase SQL 실행 없음.
- dependency 변경 없음.

## README 영향

- README 변경은 필요하지 않다.
- 판단 근거: 이번 변경은 기존 Three-day Topic 상세 API의 누락 필드 보강과
  contract test 추가이며, 설치 방법, 실행 방법, 환경 변수, 배포 절차, 운영
  runbook을 바꾸지 않는다.

## 테스트

- `python -m pytest tests/test_three_day_topics_api.py -v`
  - 8개 테스트 통과
- `python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`
  - 35개 테스트와 6개 subtest 통과
- `python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v`
  - 23개 테스트 통과
- `python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`
  - 44개 테스트와 13개 subtest 통과
- `python -m pytest`
  - 409개 테스트 통과
- `python -m unittest discover -s tests`
  - 409개 테스트 통과, `OK`
- `python -m compileall app scripts tests`
  - 통과
- `git diff --check`
  - 통과

## 확인 결과

- 누락 지점은 `app/routers/three_day_topics.py`의 Three-day Topic 상세 SELECT가
  `key_points`를 조회하지 않는 부분이었다.
- 상세 router는 SQLAlchemy mapping row를 `dict(row)`로 변환해 반환하므로,
  SELECT에 없는 `key_points`는 응답에 포함될 수 없었다.
- 상세 SELECT에 `key_points`를 추가하고, row 변환 후 `topic["key_points"] =
  topic.get("key_points") or []`로 정규화했다.
- 기존 `articles` 배열 구조와 정렬 검증은 유지했다.
- Three-day Topic 목록 API와 home API는 변경하지 않았다.
- Daily/Weekly Topic API와 pipeline은 변경하지 않았다.
- DB migration, dependency, Kubernetes manifest, Dockerfile, GitHub Actions 변경은
  없다.
- Production DB 조회, production API curl, K3s rollout, deploy는 수행하지 않았다.
- `docs/fixes/fix-three-day-topic-detail-contract-approved-fixes.md`에는 적용할
  Approved Fixes가 기록되어 있지 않아 review fix 적용은 없었다.

## 비고

- Frontend 상세 페이지의 기간 및 관련 기사 표시 문제는 이번 Backend task 범위가
  아니며 후속 작업 대상이다.
- PR merge 완료, production deployment 완료, K3s rollout 완료, production
  verification 완료를 주장하지 않는다.
