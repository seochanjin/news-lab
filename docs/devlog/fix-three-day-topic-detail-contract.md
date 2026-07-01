# 3일 Topic 상세 API key_points 응답 계약 수정

## 작업 목적

Production DB의 `three_day_topics.key_points`에는 핵심 포인트가 정상 저장되어
있지만, `GET /three-day-topics/{topic_id}` 상세 API 응답에서 해당 필드가 누락되는
문제를 수정한다.

이번 작업의 목표는 3일 Topic 생성 pipeline, DB schema, 저장 로직을 바꾸지 않고
상세 API read 계약만 보강하는 것이다.

## 기존 문제

- 운영 확인 결과 `three_day_topics.id = 38`에는 `key_points`가 9개 저장되어
  있었다.
- 하지만 상세 API 응답에는 `key_points` 필드가 포함되지 않아 Frontend가 핵심
  포인트가 없는 것으로 처리할 수 있었다.
- 조사 결과 `app/routers/three_day_topics.py`의 상세 topic SELECT가 `key_points`를
  조회하지 않았다.
- Three-day Topic router는 SQLAlchemy mapping row를 `dict(row)`로 변환한 뒤
  `articles`만 추가해 반환하므로, SELECT에 없는 field는 응답에 포함될 수 없었다.
- 기존 API test는 상세 응답의 articles 정렬과 role flag를 검증했지만
  `key_points` 계약은 검증하지 않았다.

## 변경 내용

- `GET /three-day-topics/{topic_id}` 상세 SELECT에 `key_points`를 추가했다.
- 상세 payload 조립 전에 `key_points`가 `NULL`이면 `[]`로 정규화했다.
- DB에 저장된 배열이나 빈 배열은 list 응답으로 유지한다.
- Three-day Topic 상세 API contract test에 다음 케이스를 추가했다.
  - `key_points` 값이 있는 경우
  - `key_points`가 `NULL`인 경우
  - `key_points`가 빈 배열인 경우
- 기존 상세 `articles` 배열 구조와 `rank`, `article_id` 정렬 검증은 유지했다.
- Three-day Topic 목록 API와 home API는 변경하지 않았다.
- Daily/Weekly Topic API와 pipeline은 변경하지 않았다.

## 구현 상세

- 수정 파일:
  - `app/routers/three_day_topics.py`
  - `tests/test_three_day_topics_api.py`
  - `docs/tasks/main.md`
  - branch별 workflow 문서: task, verification, review, fix, PR, devlog
- API router는 별도 response schema 없이 SQLAlchemy mapping row를 dict로 변환해
  반환하는 구조였다.
- 상세 query의 topic SELECT column 목록에 `key_points`를 추가했다.
- row를 `topic = dict(row)`로 변환한 뒤 `topic["key_points"] =
  topic.get("key_points") or []`를 적용했다.
- 이 정규화는 DB 값이 `NULL`인 경우 `[]`를 반환하고, 저장된 배열의 순서는
  변경하지 않는다.
- 테스트 fixture에는 상세 API용 `detail_topic_row()`를 추가해 `key_points` 값을
  명시적으로 주입할 수 있게 했다.
- Python 문서화 정책에 따라 새 테스트 helper와 추가 테스트에는 실제 역할과 검증
  목적을 설명하는 한글 docstring을 작성했다.

## 대안 검토

- 대안 1: Three-day Topic pipeline 또는 저장 로직 수정
  - 채택하지 않았다. Task와 DB 확인 결과 `key_points`는 이미 저장되어 있었고,
    문제는 API read 경로의 SELECT 누락이었다.
- 대안 2: DB migration 또는 backfill 추가
  - 채택하지 않았다. schema와 기존 데이터가 정상이며, task에서도 DB 변경을
    명시적으로 제외했다.
- 대안 3: 목록 API와 home API에도 `key_points` 추가
  - 채택하지 않았다. 이번 task는 상세 API 계약만 수정하며, 목록/home API 계약은
    변경하지 않는 것이 요구사항이었다.
- 대안 4: 기간별 Topic 공통 response schema를 새로 만들기
  - 채택하지 않았다. 현재 문제는 한 endpoint의 field 누락이므로 대규모 공통화는
    변경 범위를 키우고 review 부담을 늘린다.

## 선택한 접근과 근거

상세 API의 SELECT와 응답 조립만 최소 수정하는 방식을 선택했다.

근거:

- Architecture 문서상 Three-day Topic detail은 `three_day_topic_articles`를
  `rank`, `article_id` 순서로 반환하는 read API이며, request/response 계약의
  source of truth는 router 구현이다.
- Database 문서상 `three_day_topics`는 현재 활성 72시간 Topic 결과와 Summary
  metadata를 저장하는 table이고, 이번 문제의 `key_points`는 이미 저장된 데이터다.
- Task는 Three-day Topic 생성 pipeline, DB schema, 기존 데이터, Daily/Weekly API,
  frontend repository 변경을 금지했다.
- Weekly Topic 상세 API는 같은 반환 패턴에서 `key_points`를 SELECT하고 있어,
  Three-day Topic 상세 API도 상세 SELECT 보강이 가장 작은 수정 범위였다.

## 트레이드오프

- 장점:
  - DB와 pipeline을 건드리지 않고 API 계약 누락만 수정한다.
  - 기존 `articles` 반환 구조와 정렬을 유지한다.
  - 목록/home API 계약을 그대로 유지해 frontend 영향 범위를 제한한다.
- 단점:
  - router가 dict payload를 직접 조립하는 현재 구조는 response model이 없어
    field 누락을 타입 수준에서 막지 못한다.
  - `topic.get("key_points") or []`는 현재 계약에는 충분하지만, 나중에 더 엄격한
    JSON 타입 검증이 필요하면 별도 schema 또는 validator 도입을 검토해야 한다.
- 보류한 개선:
  - 기간별 Topic 공통 schema 도입
  - 상세 API response model 정리
  - Frontend 상세 페이지의 기간 및 관련 기사 표시 수정

## 테스트

실제 테스트와 검증 결과의 source of truth는
`docs/verification/fix-three-day-topic-detail-contract.md`다.

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

참고:

- `rg -n "response_model|BaseModel|articles|keywords" app/routers app/schemas app/services tests`
  는 `app/schemas` 경로가 없어 실패했다.
- 이 실패는 현재 저장소 구조와 task 예시 경로의 차이 때문이며, 이후 실제 존재
  경로 기준으로 재확인했다.

## 운영 반영

- 수행하지 않았다.
- PR merge 완료를 주장하지 않는다.
- Production deployment 완료를 주장하지 않는다.
- K3s rollout 완료를 주장하지 않는다.
- Production API curl verification 완료를 주장하지 않는다.
- Human-provided rollout 또는 curl verification log는 제공되지 않았다.

운영 반영 후 사람이 확인할 항목:

- 배포된 API image 또는 rollout 상태
- `GET /three-day-topics/38` 응답에 `key_points`가 포함되는지
- `key_points` 길이가 운영 DB에 저장된 값과 일치하는지
- 기존 `articles` 배열 길이와 정렬이 유지되는지

## README 업데이트 판단

README 업데이트는 필요하지 않다.

판단 근거:

- 이번 변경은 기존 endpoint의 누락 field를 복구하는 API 계약 보강이다.
- 설치 방법, 실행 방법, 환경 변수, dependency, DB migration, 배포 절차가
  변경되지 않았다.
- Architecture와 Runbook의 운영 원칙도 변경되지 않았다.

## 확인 결과

- Three-day Topic 상세 API 응답에 `key_points: list[str]`가 항상 포함되도록
  local contract test로 확인했다.
- DB 값이 `NULL`이면 `[]`로 반환된다.
- DB 값이 빈 배열이면 `[]`로 반환된다.
- 저장된 배열 값은 list 그대로 반환하므로 DB 저장 순서를 변경하지 않는다.
- 기존 상세 `articles` 배열 구조와 정렬 검증은 유지됐다.
- Three-day Topic 목록 API와 home API는 변경하지 않았다.
- Daily/Weekly Topic API와 pipeline은 변경하지 않았다.
- DB migration, dependency, Kubernetes manifest, Dockerfile, GitHub Actions 관련
  diff가 없음을 확인했다.
- `docs/fixes/fix-three-day-topic-detail-contract-approved-fixes.md`에는 적용할
  Approved Fixes가 없어 review fix 적용은 없었다.

## 이번 단계의 의미

Backend 상세 API 계약 누락은 로컬 회귀 테스트 기준으로 해소됐다.

Production DB의 `id = 38` 데이터처럼 이미 저장된 `key_points`는 운영 반영 후
상세 API에서 반환될 수 있는 계약이 완성됐다. 다만 실제 production 응답 확인은
rollout과 curl verification log가 제공된 뒤에만 완료로 볼 수 있다.

## 포트폴리오용 요약

NewsLab의 3일 Topic 상세 API에서 DB에는 저장되어 있으나 응답에서 누락되던
`key_points` 필드를 복구했다. 원인을 pipeline이나 DB 문제가 아니라 상세 SELECT
누락으로 좁히고, API 계약을 `list[str]`로 고정하면서 `NULL`과 빈 배열 케이스를
테스트로 보강했다. 관련 Three-day, Daily, Weekly 회귀 테스트와 전체 테스트를
통과시켜 작은 변경 범위 안에서 사용자-visible API 결함을 해결했다.

## 다음 단계 후보

- 운영 반영 후 human operator가 production API 응답의 `key_points` 개수와
  `articles` 배열을 확인한다.
- Frontend 상세 페이지에서 Three-day/Weekly 기간 표시와 관련 기사 표시 문제를
  별도 task로 수정한다.
- 필요하면 Three-day Topic 상세 API에 response model 또는 contract schema를
  도입해 future field 누락을 더 이른 단계에서 잡는다.
- PR review에서 승인된 fix가 생기면
  `docs/fixes/fix-three-day-topic-detail-contract-approved-fixes.md`에 기록한 뒤
  별도 fix 단계에서 적용한다.
