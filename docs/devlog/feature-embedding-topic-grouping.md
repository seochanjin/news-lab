# Embedding 기반 topic grouping MVP

## 작업 목적

Multi-source article metadata와 29차 lightweight classification/importance
signal을 입력으로 사용해, 의미 기반 topic 후보 grouping 파이프라인의
구조와 출력 형식을 검증한다.

이번 단계는 최종 topic feed가 아니라 read-only MVP다. 실제 embedding
provider 호출은 기본적으로 차단하고, deterministic local embedding으로
조회·분류·clustering·JSON 출력 경로를 먼저 검증했다.

## 기존 문제

- 유사한 기사를 source가 달라도 하나의 topic 후보로 묶는 분석 도구가
  없었다.
- embedding 입력, provider 호출, similarity 계산, clustering 책임이
  분리되어 있지 않았다.
- 실제 provider 비용을 발생시키기 전에 입력 수와 안전 조건을 검증할
  경계가 없었다.
- topic 저장 구조와 API를 결정하기 전에 실제 후보 수와 grouping 품질을
  확인할 read-only 경로가 없었다.

## 변경 내용

- `app/utils/article_embeddings.py`
  - title, RSS summary, source, source/rule category 기반 embedding 입력 생성
  - provider protocol, deterministic hash provider, OpenAI provider 분리
  - 예상 token 수 계산
- `app/utils/topic_grouping.py`
  - cosine similarity helper
  - importance 우선 seed-based greedy clustering
  - topic별 article/source 수, category/language 분포, representative,
    average similarity, max importance article 출력
- `scripts/analyze_topic_groups.py`
  - published/created 및 24h/72h/168h/all read-only 조회
  - max article limit과 similarity threshold 지원
  - 기본 local deterministic embedding 및 JSON dry-run 출력
  - real provider 호출 전 opt-in, key, 명시 limit, 최대 200건 조건 강제
- 외부 API를 호출하지 않는 단위 테스트 추가

DB schema, API, frontend, collector/extractor, K8s manifest는 변경하지
않았다.

## 구현 상세

- 기본 제품 기준은 `coalesce(published_at, created_at)`이며 운영 분석용
  `created_at` 기준도 지원한다.
- SQL은 published/created와 window/all 조합별 고정 `text()` template을
  선택하고 `window_hours`, `max_articles`를 bind parameter로 전달한다.
- 29차 classification helper를 재사용해 `rule_category`,
  `detected_language`, `importance_score`를 계산한다.
- Representative article과 greedy seed는 importance score 내림차순,
  article id 오름차순으로 결정한다.
- 기본 local provider는 normalized token feature hashing을 사용한다.
  반복 가능한 pipeline 검증용이며 semantic 품질 증거로 사용하지 않는다.
- 실제 OpenAI provider는 `--use-embedding-provider`,
  `OPENAI_EMBEDDING_API_KEY`, 명시적 `--max-articles`가 모두 필요하며,
  200건 초과 요청을 거부한다.
- 실제 provider 호출 전 예상 article 수, token 수, 비용을 stdout에
  출력하도록 구성했다.

## 대안 검토

- **처음부터 실제 OpenAI embedding provider로만 분석**
  - semantic grouping 품질을 바로 확인할 수 있지만 API key, 비용,
    네트워크 상태에 테스트와 기본 실행이 의존한다. 기본 경로에서는
    deterministic local embedding을 사용하고 실제 provider는 명시적
    opt-in으로 분리했다.
- **DB에 embedding과 topic을 즉시 저장**
  - 반복 분석과 API 연동에는 유리하지만 model, input format, threshold가
    안정화되기 전에 schema와 stale 결과 관리 정책을 고정하게 된다.
    이번 단계에서는 read-only JSON dry-run만 구현했다.
- **Seed-based greedy clustering 대신 계층적 clustering 또는 DB vector
  search 사용**
  - 복잡한 topic 구조와 대규모 데이터에는 유리하지만 추가 dependency,
    vector extension, parameter 설계가 필요하다. MVP에서는 동작을
    설명하기 쉬운 greedy 방식을 선택했다.
- **Source category만 사용해 topic grouping**
  - 구현은 단순하지만 같은 category 안의 서로 다른 사건을 구분하지
    못한다. Title, summary, source, source/rule category를 embedding
    입력으로 사용했다.
- **OpenAI provider batching/chunking 즉시 구현**
  - 운영 규모 확장에는 필요하지만 현재 실제 provider 호출 상한이
    200건이며 human-approved fix가 아니다. 이번 PR에는 적용하지 않고
    deferred 상태로 유지했다.
- **Topic summary와 frontend를 함께 구현**
  - 사용자 기능을 빠르게 만들 수 있지만 grouping 품질 확인 전 LLM 비용,
    API 계약, UI 의존성이 추가된다. 이번 범위에서 제외했다.

## 선택한 접근과 근거

- Embedding input 생성, provider 호출, cosine similarity, clustering을
  별도 helper로 분리했다. Provider나 clustering 전략을 교체할 때 DB 조회
  및 JSON 출력 경로를 유지하기 위해서다.
- 기본 실행은 deterministic hash embedding을 선택했다. Semantic 품질을
  대신하지는 않지만 외부 API 없이 pipeline, safety gate, 출력 구조를
  반복 검증할 수 있다.
- 실제 provider는 opt-in, API key, 명시 article limit, 최대 200건 조건을
  모두 요구한다. 비용이 발생하는 호출을 기본 실행이나 테스트에서
  우발적으로 수행하지 않기 위해서다.
- Greedy seed 순서는 29차 importance score를 사용했다. 중요도가 높은
  article을 topic 대표 후보로 우선 검토하면서 기존 classification signal을
  재사용할 수 있다.
- DB write보다 read-only dry-run을 먼저 선택했다. 실제 provider와
  threshold 품질을 검토한 후 저장 구조와 API 계약을 결정하기 위해서다.
- 제품 흐름 분석은 published time과 created fallback을 사용하고, 운영
  관점 분석은 created time을 별도로 지원했다.

## 트레이드오프

- Deterministic hash embedding은 빠르고 반복 가능하지만 의미적 유사도를
  충분히 표현하지 못한다. 현재 결과는 pipeline 검증이며 semantic 품질
  검증이 아니다.
- Seed-based greedy clustering은 구현과 결과 설명이 단순하지만 seed
  순서와 threshold에 민감하고 topic 간 전역 최적화를 보장하지 않는다.
- Embedding을 매 실행마다 계산하므로 실제 provider를 반복 사용하면 비용과
  latency가 증가한다. 후속 단계에서 input hash 기반 cache가 필요하다.
- 현재 OpenAI provider는 최대 200건을 한 HTTP 요청으로 처리한다. 상한을
  늘리거나 운영 자동화할 경우 batching, retry, partial failure 정책이
  필요하다.
- 고정 SQL query template은 일부 query 중복이 있지만 dynamic SQL fragment
  없이 허용되는 조회 경로와 bind parameter를 명확히 검토할 수 있다.
- Topic 결과를 DB에 저장하지 않아 비교 이력이나 API 조회에는 사용할 수
  없지만, schema를 조기에 확정하지 않고 실험할 수 있다.

## 테스트

- Python compile 통과
- 전체 unittest 33개 통과
- 테스트는 fake/hash embedding과 mocked HTTP response만 사용했으며 외부
  API를 호출하지 않았다.
- CLI help와 provider 안전 조건 검증 통과
- published 24h/72h/168h/all 및 created 24h read-only local embedding
  dry-run 통과
- `git diff --check`, 신규 파일 whitespace, K8s 범위, security grep 통과
- `pytest`는 `.venv/bin/pytest` 미설치로 pending
- 실제 명령과 상세 결과는
  `docs/verification/feature-embedding-topic-grouping.md`를 참조한다.

## 운영 반영

- 운영 반영 없음.
- 실제 OpenAI embedding API를 호출하지 않았다.
- DB migration, Supabase SQL, article/source/topic row write를 수행하지
  않았다.
- API, frontend, K8s manifest, CronJob schedule을 변경하지 않았다.
- rollout, production verification, push, merge를 수행하지 않았다.

## README 업데이트 판단

README는 변경하지 않았다.

이번 변경은 내부 helper와 수동 read-only 분석 script를 추가하며 기존
FastAPI API, 서비스 실행 방법, K3s 운영 절차를 변경하지 않는다. 실제
provider 운영 정책, topic API, DB 저장, batch/CronJob 자동화가 도입되는
후속 단계에서 README와 Runbook에 사용법과 운영 조건을 추가하는 것이
적절하다.

## 확인 결과

- 기본 threshold 0.72의 deterministic local embedding dry-run 결과:
  - published 24h, 최대 100건: topic 후보 98개, multi-article 후보 2개
  - published 72h, 최대 150건: topic 후보 141개, multi-article 후보 4개
  - published 168h, 최대 200건: topic 후보 186개, multi-article 후보 4개
  - published all, 최대 200건: topic 후보 186개, multi-article 후보 4개
  - created 24h, 최대 100건: topic 후보 97개, multi-article 후보 3개
- 단일 기사 후보가 대부분이므로 local hash 결과만으로 threshold나
  semantic grouping 품질을 확정할 수 없다.
- 모든 dry-run은 `embedding_provider_enabled: false`,
  `db_write_performed: false`로 확인됐다.
- API key가 없는 provider 실행은 DB 접근 전에 명확한 error로 종료됐다.
- Human operator가 승인해 적용한 review fix는 없다.
- Provider batching/chunking 제안은 deferred 상태이며 이번 PR에 적용하지
  않았다.
- 실제 OpenAI embedding provider 호출과 semantic grouping 품질 검증은
  pending이다.

## 이번 단계의 의미

Embedding provider와 clustering 로직을 분리하고, 실제 비용이나 DB write
없이 topic 후보 생성 파이프라인을 끝까지 검증했다. 향후 실제 semantic
embedding을 소량 비교할 때 호출 조건, 입력 형식, 대표 기사 선정, JSON
출력 기준을 재사용할 수 있다.

또한 `article_embeddings`, `topics`, `topic_articles`, topic run history
구조를 즉시 추가하지 않고 후보로 남겨, 실제 grouping 품질과 운영 요구를
먼저 확인한 뒤 migration을 설계할 수 있게 했다.

## 포트폴리오용 요약

Multi-source RSS article metadata를 대상으로 embedding topic grouping MVP를
설계하고 구현했다. Title, RSS summary, source, source/rule category를
embedding 입력으로 구성하고, provider interface, cosine similarity,
importance 기반 seed selection, greedy clustering을 분리했다.

실제 비용이 발생하는 provider 호출은 opt-in, API key, 명시 article limit,
최대 200건 조건으로 보호하고, 기본 deterministic local embedding과
read-only JSON dry-run으로 pipeline을 검증했다. 전체 33개 unittest와
published/created 기준 다섯 가지 read-only 분석을 통과했으며, DB schema,
API, K8s, production 환경을 변경하지 않고 후속 semantic 품질 검증을 위한
기반을 마련했다.

## 다음 단계 후보

- Human operator가 multi-article 후보를 검토해 threshold와 grouping
  적합성을 판단한다.
- 명시적으로 승인된 경우에만 작은 article limit으로 실제 embedding
  provider 결과를 local hash 결과와 비교한다.
- 모델·threshold별 precision/recall 평가 기준을 정의한다.
- embedding cache와 input hash 전략을 검토한다.
- Provider 상한 또는 운영 규모를 늘릴 때 batching/chunking, retry,
  partial failure 정책을 설계한다.
- 검증 결과가 충분할 때만 `article_embeddings`, `topics`,
  `topic_articles`, `topic_runs` 또는 `topic_grouping_runs` migration을
  별도 승인 차수에서 검토한다.
- Topic summary, API, frontend, CronJob, production rollout은 후속 범위로
  유지한다.
