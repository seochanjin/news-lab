# Task: 3일 Topic 상세 API key_points 응답 계약 수정

## Goal

`three_day_topics.key_points`에 정상 저장된 핵심 포인트가 `GET /three-day-topics/{topic_id}` 상세 API 응답에서 누락되는 문제를 수정한다.

운영 DB 확인 결과 `three_day_topics.id = 38`에는 `key_points`가 9개 저장되어 있지만, 상세 API 응답에는 `key_points` 필드가 포함되지 않는다.

현재 확인된 흐름은 다음과 같다.

```
three_day_topics.key_points 정상 저장
→ Three-day Topic 상세 API 응답에서 key_points 누락
→ Frontend가 핵심 포인트가 없는 것으로 처리
```

따라서 이번 작업에서는 Three-day Topic 생성 pipeline이나 DB 저장 구조를 변경하지 않고, 상세 API 응답 계약과 관련 테스트만 보강한다.

Frontend의 관련 기사 및 기간 표시 문제는 별도 후속 작업에서 수정한다.

## Scope

- 현재 Three-day Topic 상세 API의 전체 응답 흐름을 조사한다.
  - Router
  - Response schema
  - Service
  - Repository 또는 query
  - DB row 및 ORM mapping
  - 응답 변환 또는 조립 코드
- DB 또는 ORM 객체에 존재하는 `key_points`가 어느 단계에서 누락되는지 확인한다.
- `GET /three-day-topics/{topic_id}` 상세 응답에 `key_points` 필드를 추가한다.
- `key_points` 응답 타입을 `list[str]`로 명시한다.
- DB에 저장된 배열 순서를 그대로 유지한다.
- DB 값이 `NULL`인 경우 빈 배열 `[]`을 반환한다.
- DB 값이 빈 배열인 경우에도 빈 배열 `[]`을 반환한다.
- 기존 Three-day Topic 상세 API의 다른 필드는 변경하지 않는다.
- 기존 `articles` 배열의 구조와 정렬을 변경하지 않는다.
- Three-day Topic 목록 API와 홈 API의 계약은 변경하지 않는다.
- 기존 API contract test를 보강하거나 필요한 테스트를 추가한다.
- 관련 집중 테스트와 전체 회귀 테스트를 실행한다.
- 작업 결과에 맞게 verification, PR, devlog 문서를 갱신한다.
- 실제 변경 파일과 테스트 결과만 문서에 기록한다.

## Do not change

- Three-day Topic 생성 prompt
- Three-day Topic prompt version
- Three-day Topic 생성 pipeline
- Three-day Topic clustering 정책
- Three-day Topic 원문 확보 정책
- Three-day Topic 요약 생성 정책
- Three-day Topic 저장 로직
- `three_day_topics` DB schema
- `three_day_topic_articles` DB schema
- `three_day_topic_runs` DB schema
- 기존 Three-day Topic 데이터
- 기존 Daily Topic API
- 기존 Daily Topic pipeline
- 기존 Weekly Topic API
- 기존 Weekly Topic pipeline
- 기존 Daily 및 Weekly Topic 응답 계약
- Frontend repository
- Frontend API type 및 화면
- DB migration
- 기존 migration 파일
- production DB 데이터
- K3s manifest
- CronJob manifest
- Dockerfile
- GitHub Actions
- dependency
- Secret
- `.env`
- `.env.*`
- 실제 Supabase SQL 실행
- production deploy
- K3s rollout
- `git push`
- PR merge
- application SQL 전반의 query construction 리팩터링
- 기간별 Topic 공통 schema를 만드는 대규모 리팩터링

## Expected files

실제 저장소 구조와 현재 Three-day Topic 구현을 먼저 조사한 뒤 필요한 파일만 수정한다.

예상 확인 또는 수정 파일:

```
app/routers/three_day_topics.py
app/schemas/three_day_topics.py
app/models/three_day_topics.py
app/repositories/three_day_topics.py
app/services/three_day_topic_pipeline/*
tests/test_three_day_topics_api.py
```

문서 파일:

```
docs/tasks/<current-task>.md
docs/verification/<current-task>.md
docs/reviews/<current-task>-antigravity.md
docs/reviews/<current-task>-coderabbit.md
docs/fixes/<current-task>-approved-fixes.md
docs/pr/<current-task>.md
docs/devlog/<current-task>.md
```

정확한 파일명은 실제 코드 구조를 우선한다.

응답 schema에 이미 `key_points`가 정의되어 있다면 동일 필드를 중복으로 추가하지 않는다.

이 경우 다음 영역을 확인한다.

- Repository query에서 `key_points`를 조회하지 않는지
- DB row mapping에서 `key_points`를 누락하는지
- Service 결과 모델에서 `key_points`를 누락하는지
- Router 응답 조립 과정에서 `key_points`를 누락하는지
- Pydantic response model 직렬화 과정에서 필드가 제외되는지
- API 테스트 fixture 또는 mock row가 `key_points`를 제공하지 않는지

Three-day Topic pipeline package는 실제 API 응답 모델이나 공통 DB mapping을 공유하는 경우에만 수정한다.

단순히 예상 파일이라는 이유로 pipeline 파일을 변경하지 않는다.

## DB changes

없음.

Production DB에서 다음 쿼리로 데이터 저장 상태를 확인했다.

```sql
SELECT
    id,
    reference_date,
    title_ko,
    key_points,
    jsonb_array_length(
        COALESCE(key_points, '[]'::jsonb)
    ) AS key_point_count
FROM three_day_topics
WHERE id = 38;
```

확인 결과:

```
id: 38
reference_date: 2026-07-01
key_points: 값 존재
key_point_count: 9
```

따라서 다음 작업은 수행하지 않는다.

- 신규 migration
- 기존 migration 수정
- DB column 추가
- DB type 변경
- production 데이터 수정
- 기존 데이터 backfill
- Three-day Topic pipeline 재실행
- Supabase SQL 실행

DB 값은 이미 정상 저장되어 있으므로 API 응답 경로만 수정한다.

## API changes

대상 endpoint:

```
GET /three-day-topics/{topic_id}
```

기존 상세 응답에 다음 필드를 추가한다.

```json
{
  "key_points": ["첫 번째 핵심 포인트", "두 번째 핵심 포인트"]
}
```

`key_points` 계약은 다음과 같다.

```
필드명: key_points
타입: list[str]
필수 여부: 상세 응답에 항상 포함
DB 값 존재: 저장된 문자열 배열 반환
DB 값 NULL: []
DB 값 빈 배열: []
순서: DB 저장 순서 유지
```

수정 후 예상 응답 형태:

```json
{
  "id": 38,
  "reference_date": "2026-07-01",
  "window_start": "2026-06-27T20:00:07.233407+00:00",
  "window_end": "2026-06-30T20:00:07.233407+00:00",
  "title_ko": "유럽 폭염 3일 흐름: 프랑스 과잉사망과 동유럽으로의 확산",
  "summary_ko": "최근 72시간 동안 유럽의 폭염이 서유럽에서 동유럽으로 확산했다.",
  "key_points": ["첫 번째 핵심 포인트", "두 번째 핵심 포인트"],
  "keywords": ["폭염", "과잉사망"],
  "article_count": 4,
  "source_count": 3,
  "status": "draft",
  "provider": "openai",
  "model": "gpt-5-nano",
  "prompt_version": "three-day-flow-v1",
  "created_at": "2026-06-30T20:03:59.216491+00:00",
  "updated_at": "2026-06-30T20:03:59.216491+00:00",
  "articles": []
}
```

다음 기존 필드는 이름, 타입과 의미를 유지한다.

```
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
status
provider
model
prompt_version
created_at
updated_at
articles
```

다음 API는 변경하지 않는다.

```
GET /three-day-topics
GET /three-day-topics/home
GET /weekly-topics
GET /weekly-topics/home
GET /weekly-topics/{topic_id}
GET /topics
GET /topics/home
GET /topics/{topic_id}
```

`articles` 배열은 다음 계약을 그대로 유지한다.

```
article_id
title
url
published_at
source
rank
similarity
is_representative
is_summary_evidence
```

기사 정렬, 대표 기사 선택 및 요약 근거 기사 표시도 변경하지 않는다.

## Test commands

구현 전 실제 코드 구조와 기존 테스트 위치를 확인한다.

```bash
rg -n \
  "ThreeDayTopic|three_day_topic|three-day-topics|key_points" \
  app tests
```

```bash
rg -n \
  "response_model|BaseModel|articles|keywords" \
  app/routers app/schemas app/services tests
```

관련 API 집중 테스트:

```bash
python -m pytest \
  tests/test_three_day_topics_api.py \
  -v
```

Three-day Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

Daily Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

Weekly Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topics_api.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

전체 pytest:

```bash
python -m pytest
```

전체 unittest:

```bash
python -m unittest discover -s tests
```

Compile 검증:

```bash
python -m compileall app scripts tests
```

변경 범위와 whitespace 확인:

```bash
git status --short
git diff --stat
git diff --check
git diff --name-only
```

금지 영역 변경 확인:

```bash
git diff -- \
  db/migrations \
  requirements.txt \
  pyproject.toml \
  poetry.lock \
  uv.lock
```

```bash
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

```bash
git diff -- \
  app/services/weekly_topic_pipeline \
  scripts/run_weekly_topic_pipeline.py \
  k8s/news-weekly-topic-pipeline-cronjob.yaml
```

```bash
git diff -- \
  k8s \
  Dockerfile \
  .github
```

변경 후 `key_points` 계약이 코드와 테스트에 반영됐는지 확인한다.

```bash
rg -n \
  "key_points" \
  app/routers \
  app/schemas \
  app/services \
  tests/test_three_day_topics_api.py
```

로컬 API를 실행할 수 있는 경우 다음 요청으로 상세 응답을 확인한다.

```bash
curl -sS \
  http://localhost:8000/three-day-topics/38 \
  | jq '{
      id,
      reference_date,
      key_point_count: (.key_points | length),
      key_points,
      article_count,
      articles_count: (.articles | length)
    }'
```

기대 형태:

```json
{
  "id": 38,
  "reference_date": "2026-07-01",
  "key_point_count": 9,
  "key_points": ["..."],
  "article_count": 4,
  "articles_count": 4
}
```

로컬 DB에 production의 `id = 38` 데이터가 존재하지 않는 경우 해당 요청 결과를 억지로 성공한 것처럼 기록하지 않는다.

이 경우 fixture 또는 테스트 DB 데이터를 사용한 API 테스트 결과만 Verification에 기록한다.

Verification 문서에는 실제로 실행한 명령과 실제 결과만 기록한다.

아직 실행하지 않은 production curl, K3s 명령 또는 배포 확인을 실행한 것처럼 기록하지 않는다.

## Acceptance criteria

- Three-day Topic 상세 API 응답에 `key_points` 필드가 항상 포함된다.
- `key_points`는 `list[str]` 타입으로 반환된다.
- DB에 저장된 핵심 포인트 배열 순서가 유지된다.
- `key_points` 값이 `NULL`이면 빈 배열 `[]`이 반환된다.
- `key_points` 값이 빈 배열이면 빈 배열 `[]`이 반환된다.
- Production DB의 `id = 38` 데이터 기준으로 핵심 포인트 9개를 반환할 수 있는 계약이 완성된다.
- 기존 Three-day Topic 상세 응답 필드가 유지된다.
- 기존 `articles` 배열 구조와 정렬이 유지된다.
- Three-day Topic 목록 API 계약이 변경되지 않는다.
- Three-day Topic 홈 API 계약이 변경되지 않는다.
- Daily Topic API와 pipeline에 회귀가 없다.
- Weekly Topic API와 pipeline에 회귀가 없다.
- Three-day Topic 생성 및 저장 pipeline이 변경되지 않는다.
- DB migration이 추가되지 않는다.
- 기존 DB 데이터와 schema가 변경되지 않는다.
- Frontend repository가 변경되지 않는다.
- API contract test가 추가되거나 보강된다.
- `key_points` 값이 있는 경우를 테스트한다.
- `key_points`가 `NULL`인 경우를 테스트한다.
- 기존 상세 필드와 `articles` 응답 회귀를 테스트한다.
- 관련 집중 테스트가 통과한다.
- Three-day Topic 회귀 테스트가 통과한다.
- 전체 pytest와 unittest가 통과한다.
- compileall과 `git diff --check`가 통과한다.
- Verification에는 실제 실행 명령과 결과만 기록된다.
- production DB 수정, K3s 변경과 production 배포는 수행하지 않는다.

## Notes

### 확인된 Production 현상

다음 요청의 응답에는 `key_points`가 없다.

```bash
curl -sS \
  https://api.newslab.ai.kr/three-day-topics/38 \
  | jq
```

응답에는 다음 정보가 정상적으로 포함되어 있다.

```
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
status
provider
model
prompt_version
created_at
updated_at
articles
```

또한 다음 값도 확인됐다.

```
article_count: 4
articles 배열 길이: 4
```

따라서 관련 기사 데이터와 상세 query 자체는 Backend API에 정상 연결되어 있다.

반면 Production DB에서는 다음 결과를 확인했다.

```
three_day_topics.id: 38
key_point_count: 9
```

따라서 이번 문제는 다음 중 하나로 판단한다.

1. 상세 response schema에서 `key_points` 누락
2. Repository 또는 row mapping에서 `key_points` 누락
3. Service 결과 모델에서 `key_points` 누락
4. Router 응답 조립 과정에서 `key_points` 누락
5. API 직렬화 과정에서 필드 제외

조사 결과 실제 누락 지점을 확인한 뒤 최소 범위만 수정한다.

### Frontend 후속 작업

Frontend에는 별도의 상세 페이지 매핑 문제가 남아 있다.

Backend API는 이미 다음 데이터를 반환한다.

Three-day Topic:

```
window_start
window_end
articles
```

Weekly Topic:

```
week_start
week_end
window_start
window_end
articles
key_points
```

하지만 현재 Frontend 상세 페이지에서는 다음 현상이 확인된다.

- Three-day Topic 기간이 `기간 정보 없음`으로 표시됨
- Weekly Topic 기간이 `기간 정보 없음`으로 표시됨
- Three-day Topic 관련 기사 4건이 화면에서는 0건으로 표시됨
- Weekly Topic 관련 기사 11건이 화면에서는 0건으로 표시됨

따라서 Backend 수정이 운영 반영된 뒤 Frontend 후속 작업에서 다음을 처리한다.

```
API articles 배열을 관련 기사 목록으로 연결
Three-day window_start, window_end 기간 표시
Weekly week_start, week_end 기간 표시
Three-day key_points 신규 API 필드 연결
```

이번 Backend 작업에는 해당 Frontend 변경을 포함하지 않는다.

### 변경 범위 원칙

이번 작업은 이미 원인이 좁혀진 API 계약 누락 수정이다.

Weekly Topic pipeline 구현처럼 DB, pipeline, CronJob과 API를 함께 설계하는 대규모 작업이 아니므로 Implementation Unit은 진행 상태를 확인하기 위한 체크리스트로만 사용한다.

UNIT마다 별도의 Agent 작업이나 리뷰를 반복하지 않는다.

한 번의 구현 흐름에서 다음 순서로 진행한다.

```
현재 계약 조사
→ 누락 지점 확인
→ 최소 수정
→ API contract test 보강
→ 관련 회귀 테스트
→ 전체 회귀 테스트
→ 문서 정리
```

Antigravity 리뷰는 모든 UNIT 구현과 검증이 끝난 뒤 전체 변경을 대상으로 한 번 수행한다.

### UNIT-02 구현 결과

- `GET /three-day-topics/{topic_id}` 상세 query가 `three_day_topics.key_points`를
  조회하도록 수정했다.
- 상세 응답 조립 시 `key_points`가 `NULL`이면 `[]`로 정규화하고, 저장된 배열이나
  빈 배열은 list 응답으로 유지한다.
- Three-day Topic 목록 API와 home API query는 변경하지 않았다.
- `tests/test_three_day_topics_api.py`에 상세 전용 fixture를 추가하고
  `key_points` 값 있음, `NULL`, 빈 배열 계약을 검증했다.
- 기존 상세 `articles` 배열 구조와 rank 정렬 검증을 유지했다.

### UNIT-03 검증 결과

- Three-day Topic API 집중 테스트와 Three-day Topic pipeline/API/CronJob 회귀
  테스트가 통과했다.
- Daily Topic pipeline/CronJob 회귀 테스트와 Weekly Topic pipeline/API/CronJob
  회귀 테스트가 통과했다.
- 전체 pytest, 전체 unittest, compileall, whitespace 및 변경 범위 gate가
  통과했다.
- DB migration, dependency, Daily/Weekly pipeline, Kubernetes manifest,
  Dockerfile, GitHub Actions 관련 diff가 없음을 확인했다.
- Production DB 조회, production API curl, K3s 변경, deploy, rollout은 수행하지
  않았다.

## Implementation Units

- [x] UNIT-01: Three-day Topic 상세 API 계약과 key_points 누락 지점 조사
- [x] UNIT-02: key_points 상세 응답 추가 및 API contract test 보강
- [x] UNIT-03: Three-day·Daily·Weekly 회귀 검증 및 작업 문서 정리
