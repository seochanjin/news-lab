# Task: 홈 Topics 경량 API 설계 및 MVP

## Goal

홈(`/`) 첫 화면이 매 요청마다 범용 `/topics` API와 불필요한 pagination/집계 응답을 기다리지 않도록, 홈 전용 Topics 경량 API를 설계하고 MVP로 구현한다.

현재 프론트 구조는 다음처럼 정리되어 있다.

```text
/          → 오늘의 주요 이슈 중심
/topics    → 전체 주요 이슈 아카이브
/search    → 주요 이슈 + 원문 통합 검색
/articles  → 원문 모음 전용 페이지
```

45차에서 홈의 원문 기사 preview와 Articles API 조회를 제거했지만, 홈은 여전히 주요 이슈를 표시하기 위해 `/topics?page=1&page_size=10` 응답을 기다린다.

운영 API 간단 측정 결과 `/topics?page=1&page_size=10` 응답은 약 0.7~1.0초 범위로 관찰되었다.

```text
/topics?page=1&page_size=10: 1.004652s
/topics?page=1&page_size=50: 0.902372s
/topics/7: 0.793147s

/topics?page=1&page_size=10 10회 반복:
1. 0.965516s
2. 0.881402s
3. 0.709049s
4. 0.793458s
5. 0.897315s
6. 0.868379s
7. 0.927151s
8. 0.897393s
9. 0.813286s
10. 0.996598s

평균 약 0.87s
```

이 응답 시간이 API 자체로 심각하게 느린 수준은 아니지만, 홈 첫 화면에서는 사용자가 loading을 체감하기에 충분하다.

이번 작업의 목표는 Redis, DB snapshot, static generation까지 한 번에 구현하는 것이 아니다. 먼저 홈에서 필요한 최소 payload만 반환하는 read-only API를 추가해 다음을 확인한다.

```text
- 홈이 범용 /topics API를 그대로 사용하는 것이 적절한가?
- 홈 전용 lightweight API로 payload와 쿼리 부담을 줄일 수 있는가?
- 추후 Daily Topic Pipeline 완료 시점에 home payload snapshot/cache를 갱신하는 구조로 확장 가능한가?
```

최종적으로 지향하는 방향은 다음이다.

```text
Daily Topic Pipeline 완료
→ 오늘의 주요 이슈 payload 생성
→ 홈에서 바로 쓸 수 있는 snapshot/cache 갱신
→ 사용자는 매 요청마다 무거운 DB 조회/조합을 기다리지 않고 빠르게 홈을 받음
```

이번 차수에서는 그 전 단계로 다음을 구현한다.

```text
GET /topics/home
```

이 API는 홈 첫 화면에 필요한 주요 이슈 card용 필드만 반환한다.

## Scope

### 1. 현재 Topics API 구조 분석

다음 API 구현을 분석한다.

```text
GET /topics
GET /topics/{id}
```

확인할 항목:

```text
- route handler 위치
- service/repository/query 구조
- topics 목록 조회 방식
- topic_articles join 여부
- article_count/source_count 계산 방식
- total count query 여부
- pagination 처리 방식
- 정렬 기준
- response payload 필드
- 홈에서 실제로 필요한 필드와 불필요한 필드
```

분석 결과는 verification 또는 design note에 기록한다.

### 2. 운영 API 응답 시간 측정 문서화

이미 측정한 결과를 verification 문서에 기록한다.  
필요하면 read-only curl을 추가로 수행한다.

기본 측정 대상:

```text
/topics?page=1&page_size=10
/topics?page=1&page_size=50
/topics/{id}
```

측정 command 후보:

```bash
curl -sS -o /dev/null -w 'topics page_size=10: %{time_total}s\n' \
  'https://api.dev-scj.site/topics?page=1&page_size=10'

curl -sS -o /dev/null -w 'topics page_size=50: %{time_total}s\n' \
  'https://api.dev-scj.site/topics?page=1&page_size=50'

curl -sS -o /dev/null -w 'topic detail: %{time_total}s\n' \
  'https://api.dev-scj.site/topics/7'

for i in {1..10}; do
  curl -sS -o /dev/null -w "$i %{time_total}s\n" \
    'https://api.dev-scj.site/topics?page=1&page_size=10'
done
```

기록할 항목:

```text
- 최소 응답 시간
- 최대 응답 시간
- 평균 또는 대략적인 범위
- page_size 변화에 따른 차이
- detail API와 list API의 차이
- 홈 첫 화면에서 체감 loading으로 이어질 가능성
```

### 3. 홈 전용 API 추가

신규 read-only endpoint를 추가한다.

```text
GET /topics/home
```

역할:

```text
홈 첫 화면에 필요한 주요 이슈 목록을 경량 payload로 반환한다.
```

요구사항:

- 기존 `/topics`와 `/topics/{id}` API는 유지한다.
- 기존 response schema를 깨지 않는다.
- 신규 API는 홈 전용으로 작고 예측 가능한 payload를 반환한다.
- DB schema 변경 없이 구현한다.
- Redis/cache/snapshot 저장소는 이번 차수에서 구현하지 않는다.
- 운영 DB에 write하지 않는다.

### 4. `/topics/home` response schema 정의

후보 response:

```json
{
  "generated_at": "2026-06-16T04:05:00+09:00",
  "topic_date": "2026-06-16",
  "items": [
    {
      "id": 12,
      "topic_date": "2026-06-16",
      "title_ko": "...",
      "summary_ko": "...",
      "keywords": ["..."],
      "article_count": 7,
      "source_count": 3
    }
  ]
}
```

필드 요구사항:

```text
- id
- topic_date
- title_ko
- summary_ko
- keywords
- article_count
- source_count
```

선택 필드 후보:

```text
- generated_at
- total
- has_next
- source
```

기본 방향:

```text
홈 화면에 필요 없는 필드는 제외한다.
```

제외 후보:

```text
- provider
- model
- confidence
- similarity_score
- status가 사용자에게 필요 없다면 제외
- connected articles
- representative article detail
- debug/report field
```

### 5. 쿼리와 payload 최소화

`/topics/home`은 기존 `/topics`를 단순히 wrapper로 호출하는 것보다, 홈에 필요한 최소 데이터만 조회하는 구조가 바람직하다.

확인할 항목:

```text
- total count query가 필요한가?
- pagination metadata가 필요한가?
- topic detail용 join이 필요한가?
- connected article 목록이 필요한가?
- source_count/article_count는 이미 topics에 저장되어 있는가?
- 없으면 계산 비용이 과한가?
```

MVP에서는 구현 리스크를 낮추기 위해 기존 query/helper를 재사용할 수 있다.  
다만 문서에는 이후 최적화 지점을 남긴다.

### 6. API 문서/아키텍처 반영

다음 문서를 필요 범위만큼 갱신한다.

```text
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

기록할 내용:

```text
- /topics/home API 역할
- /topics와 /topics/home의 차이
- 홈 첫 화면 최적화 목적
- cache/snapshot은 후속 작업임
```

README는 설치/실행/dependency/API contract 공개 문서 변경이 필요할 때만 수정한다.

### 7. 후속 cache/snapshot 전략 기록

이번 차수에서 Redis, DB snapshot, static JSON, Next.js revalidate를 구현하지는 않는다.  
다만 `/topics/home`을 후속 cache/snapshot 구조로 확장하는 전략은 문서에 남긴다.

비교 후보:

```text
1. Next.js fetch revalidate
2. FastAPI in-memory TTL cache
3. Redis cache
4. DB snapshot table
5. Static JSON
6. Redis + DB snapshot fallback
7. CronJob 완료 후 frontend revalidate/cache warming
```

특히 다음 관점을 정리한다.

```text
- Redis 자체가 목적이 아니다.
- 목적은 홈 첫 화면에서 사용자 요청 시점의 무거운 조회/조합을 줄이는 것이다.
- Daily Topic Pipeline 완료 시점에 home payload를 사전 생성하는 구조가 장기 목표다.
```

### 8. 후속 차수 제안

이번 차수 이후 후보를 문서화한다.

후속 후보:

```text
47차: 프론트 홈 /topics/home 전환 및 로딩 확인
48차: Home Topics cache/snapshot 갱신 MVP
49차: embedding 저장 구조 검토
```

또는 `/topics/home` 자체 응답이 충분히 빠르지 않으면:

```text
47차: /topics/home cache/snapshot MVP
48차: 프론트 홈 /topics/home 전환
```

## Do not change

이번 작업은 read-only API 추가와 설계 문서 중심이다. 다음 항목을 변경하지 않는다.

```text
- DB schema
- Supabase SQL
- K3s manifest
- Dockerfile
- GitHub Actions
- production infrastructure
- frontend code
- frontend route
- secret
- .env
- .env.*
```

기존 API에서 변경하지 않을 항목:

```text
- GET /topics
- GET /topics/{id}
- 기존 response schema
- 기존 query parameter
- 기존 topic pipeline
- 기존 CronJob
```

금지 작업:

```text
- git push
- git merge
- production deploy command
- kubectl apply/delete/patch/rollout
- helm upgrade
- Supabase SQL migration
- DB write
- Redis 설치
- K3s 리소스 생성/수정
- CronJob manifest 변경
- production-impacting command
```

허용 작업:

```text
- backend code read
- 신규 read-only route 구현
- API schema/model 추가
- 문서 작성
- read-only API curl 측정
- local test
- local lint/typecheck/compile
- read-only git diff/status 확인
```

## Expected files

예상 변경 파일:

```text
app 또는 src 내부 topics router/service/schema 관련 파일
docs/tasks/feature-home-topics-snapshot-design.md
docs/verification/feature-home-topics-snapshot-design.md
docs/reviews/feature-home-topics-snapshot-design-antigravity.md
docs/reviews/feature-home-topics-snapshot-design-coderabbit.md
docs/fixes/feature-home-topics-snapshot-design-approved-fixes.md
docs/pr/feature-home-topics-snapshot-design.md
docs/devlog/feature-home-topics-snapshot-design.md
docs/design/home-topics-snapshot-cache-strategy.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

실제 backend 구조를 먼저 확인하고 최소 파일만 변경한다.

필수 산출물 후보:

```text
- /topics/home route 구현
- /topics/home response schema/model
- docs/verification/feature-home-topics-snapshot-design.md
- docs/design/home-topics-snapshot-cache-strategy.md
```

`docs/ARCHITECTURE.md`는 신규 API 역할을 설명하기 위해 수정한다.  
`docs/RUNBOOK.md`는 운영 API 측정 command 또는 새 endpoint 확인 command를 남길 때만 수정한다.  
README는 설치/실행/dependency가 변경되지 않으면 수정하지 않는다.

## DB changes

이번 차수에서는 DB 변경을 수행하지 않는다.

금지:

```text
- table 생성
- column 추가
- index 추가
- migration 작성/실행
- Supabase SQL 실행
- data backfill
- write query
```

다만 설계 문서에서는 후속 DB snapshot table 후보를 검토할 수 있다.

DB snapshot 후보 예시:

```text
home_topic_snapshots
- id
- snapshot_date
- generated_at
- payload jsonb
- source_pipeline_run_id
- status
- created_at
```

이는 후속 설계 후보일 뿐이며 이번 차수에서 구현하지 않는다.

검토할 항목:

```text
- DB snapshot이 필요한 이유
- Redis와의 역할 분리
- snapshot history 보관 기간
- cache miss 시 fallback 용도
- payload jsonb 저장의 장단점
```

## API changes

이번 차수에서는 신규 read-only API를 추가한다.

추가 API:

```text
GET /topics/home
```

목적:

```text
홈 첫 화면에 필요한 Topics 경량 payload 제공
```

후보 response:

```json
{
  "generated_at": "2026-06-16T04:05:00+09:00",
  "topic_date": "2026-06-16",
  "items": [
    {
      "id": 12,
      "topic_date": "2026-06-16",
      "title_ko": "...",
      "summary_ko": "...",
      "keywords": ["..."],
      "article_count": 7,
      "source_count": 3
    }
  ]
}
```

검토할 항목:

```text
- endpoint naming
- response fields
- generated_at 기준
- topic_date 기준
- empty response 형태
- error response 형태
- 기존 /topics와의 역할 분리
```

변경하지 않는 API:

```text
GET /topics
GET /topics/{id}
GET /articles
기타 기존 API
```

## Test commands

실제 backend project 구조와 package/test command를 먼저 확인한다.

기본 검증 후보:

```bash
git diff --check
git diff --name-only
git status --short --branch
```

코드 검색 후보:

```bash
rg -n "topics|topic_articles|source_count|article_count|/topics|Topic" app src scripts docs
rg -n "daily-topic-pipeline|run_daily_topic_pipeline|news-daily-topic-pipeline" .
rg -n "Redis|cache|snapshot|revalidate|home topics|topics/home" docs app src scripts
```

Python 검증 후보:

```bash
python -m compileall .
pytest
```

단, `pytest`가 외부 DB write 또는 infra 변경을 유발할 수 있으면 실행하지 않는다.  
실행하지 않은 command는 verification 문서에 명확히 기록한다.

로컬 API 검증 후보:

```bash
uvicorn app.main:app --reload
```

또는 프로젝트의 기존 실행 방식 확인 후 사용한다.

신규 endpoint 확인 후보:

```bash
curl -sS 'http://127.0.0.1:8000/topics/home' | python -m json.tool
curl -sS -o /dev/null -w 'topics home local: %{time_total}s\n' \
  'http://127.0.0.1:8000/topics/home'
```

운영 API read-only 측정 후보:

```bash
curl -sS -o /dev/null -w 'topics page_size=10: %{time_total}s\n' \
  'https://api.dev-scj.site/topics?page=1&page_size=10'

curl -sS -o /dev/null -w 'topics page_size=50: %{time_total}s\n' \
  'https://api.dev-scj.site/topics?page=1&page_size=50'

curl -sS -o /dev/null -w 'topic detail: %{time_total}s\n' \
  'https://api.dev-scj.site/topics/7'
```

신규 `/topics/home` 운영 검증은 배포 전에는 수행하지 않는다.  
배포 전 verification에는 local 또는 code-level 검증만 기록한다.

Shell script syntax 검증 후보:

```bash
bash -n scripts/new_agent_task.sh
bash -n scripts/agent_next_step.sh
```

Credential scan:

```bash
git grep -n -i -E 'API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|BEGIN|\.env' -- ':!package-lock.json'
```

검증 결과는 다음 파일에 기록한다.

```text
docs/verification/feature-home-topics-snapshot-design.md
```

## Acceptance criteria

완료 조건:

```text
- 현재 /topics, /topics/{id} API 구조가 분석되어 있다.
- 운영 API 응답 시간 측정 결과가 verification에 기록되어 있다.
- GET /topics/home read-only API가 추가되어 있다.
- /topics/home은 홈 첫 화면에 필요한 최소 Topics payload를 반환한다.
- 기존 /topics, /topics/{id} API 동작과 schema가 깨지지 않는다.
- DB schema가 변경되지 않았다.
- Supabase SQL이 실행되지 않았다.
- Redis, DB snapshot, CronJob 갱신은 이번 차수에서 구현하지 않았다.
- cache/snapshot/revalidate 후보와 후속 전략이 문서화되어 있다.
- 47차 후속 작업 후보가 제시되어 있다.
- backend compile/test 또는 가능한 검증 command가 통과했다.
- 실행한 검증 command와 결과가 verification 문서에 기록되어 있다.
- K3s, Docker, production infra, secret, .env, .env.*가 변경되지 않았다.
- production deploy 또는 production verification 완료를 주장하지 않는다.
```

## Notes

이번 작업은 프론트 로딩 문제를 백엔드/데이터 제공 구조 관점에서 해결하기 위한 첫 구현 차수다.

중요한 판단:

```text
Redis 자체가 목적이 아니다.
목적은 홈 첫 화면에서 사용자 요청 시점의 무거운 조회/조합을 줄이는 것이다.
```

즉, 장기적으로는 다음 구조로 가야 한다.

```text
사용자 요청 시점에 계산 ❌
Daily Topic Pipeline 완료 시점에 홈 payload 사전 생성 ⭕
```

이번 차수의 위치:

```text
46차: 홈 Topics 경량 API 설계 및 MVP
47차: 프론트 홈 /topics/home 전환 및 로딩 확인
48차: Home Topics cache/snapshot 갱신 MVP
49차 이후: embedding 저장 구조 검토로 복귀
```

장기적으로 가능한 이상적인 흐름:

```text
Daily Topic Pipeline CronJob
→ topics 저장
→ home topics payload 생성
→ Redis 최신 payload 저장
→ 선택적으로 DB snapshot 저장
→ 선택적으로 Next.js revalidate 호출
→ 선택적으로 cache warming
→ 사용자는 정적 페이지에 가까운 홈 화면을 받음
```

기존 장기 계획과의 관계:

```text
Embedding 저장 구조
Daily pipeline 단계 분리
3일/7일 topic window
Topic continuation / related topics
대표 이미지 수집/표시
```

위 작업들은 여전히 중요하다.  
다만 홈 첫 화면이 느리면 사용자 경험이 크게 나빠지므로, Topics API 제공 구조와 홈 payload 전략을 먼저 정리한다.

프론트 dev 환경의 Turbopack ChunkLoadError는 별도 known issue다.  
이번 백엔드 작업에서는 해결하지 않는다.

도메인 변경(`newslab.site`)은 이번 작업 범위에 포함하지 않는다.  
프론트 배포와 도메인 연결은 별도 차수에서 다룬다.
