# Embedding 기반 topic grouping MVP

## 작업 내용

- Multi-source article metadata를 대상으로 topic 후보를 생성하는 embedding
  topic grouping MVP를 추가했습니다.
- title, RSS summary, source name, source/rule category 후보를 embedding
  입력으로 구성합니다.
- embedding provider interface, cosine similarity, importance 우선
  seed-based greedy clustering을 분리해 구현했습니다.
- 현재 DB article을 read-only로 조회하고 topic 후보를 JSON으로 출력하는
  `scripts/analyze_topic_groups.py`를 추가했습니다.
- 기본 실행은 실제 embedding API를 호출하지 않는 deterministic local
  embedding과 dry-run 방식입니다.

## 주요 변경 사항

- `app/utils/article_embeddings.py`
  - embedding 입력 text 생성 helper 추가
  - provider protocol, deterministic hash provider, OpenAI embedding
    provider 분리
  - provider 호출 전 예상 token 수 계산 지원
- `app/utils/topic_grouping.py`
  - cosine similarity helper 추가
  - importance score를 seed와 대표 기사 선정에 반영하는 greedy clustering
    추가
  - topic별 article/source 수, category/language 분포, 대표 기사,
    average similarity, max importance article 출력
- `scripts/analyze_topic_groups.py`
  - published 기준과 created 기준 분석 지원
  - 24h/72h/168h/all window와 max article limit 지원
  - SQLAlchemy 고정 `text()` query와 bind parameter를 사용한 read-only
    article 조회
  - topic candidate JSON dry-run 출력
- 실제 provider 호출 안전 조건:
  - `--use-embedding-provider` 명시 필요
  - `OPENAI_EMBEDDING_API_KEY` 필요
  - 명시적 `--max-articles` 필요
  - 200건 초과 요청 거부
  - 호출 전 예상 article 수, token 수, 비용 출력
- 외부 API를 호출하지 않는 helper, provider 안전 조건, grouping 분석
  테스트를 추가했습니다.

## 추가/변경된 API

- 추가되거나 변경된 FastAPI API는 없습니다.
- 기존 API 응답 구조를 변경하지 않았습니다.
- Topic 후보 결과는 API가 아닌 `scripts/analyze_topic_groups.py`의 JSON
  출력으로 확인합니다.
- `/topics`, `/topics/{topic_id}`는 후속 검토 대상이며 이번 PR에 포함하지
  않았습니다.

## DB 변경 사항

- DB schema 변경 및 migration 파일 추가는 없습니다.
- Supabase SQL을 실행하지 않았고 article/source/topic/embedding row를
  생성하거나 수정하지 않았습니다.
- 분석 script는 `set transaction read only` 후 SELECT만 수행합니다.
- 후속 차수에서 검토할 후보 구조:
  `article_embeddings`, `topics`, `topic_articles`, `topic_runs`,
  `topic_grouping_runs`

## README 영향

- README 변경은 필요하지 않습니다.
- 이번 변경은 내부 helper와 수동 read-only 분석 script 추가이며, 기존
  API 사용법, 서비스 실행 방법, K3s 운영 절차를 변경하지 않습니다.
- Topic API 또는 운영 batch/CronJob이 추가되는 후속 차수에서 README와
  Runbook 업데이트를 검토합니다.

## 테스트

- Python compile: 통과
- `.venv/bin/python -m unittest discover -s tests -v`: 전체 33개 테스트
  통과
- 테스트는 deterministic fake/hash embedding과 mocked HTTP response를
  사용했으며 외부 API를 호출하지 않았습니다.
- CLI help: 통과
- API key 없는 provider 실행이 DB 접근 전에 명확히 실패함을 확인
- Provider 사용 시 명시적 `--max-articles`가 필요하고 200건 초과를
  거부함을 단위 테스트로 확인
- `git diff --check` 및 신규 untracked 파일 whitespace 검사: 통과
- `git diff -- k8s`: 변경 없음
- security grep: credential 값 없음
- `pytest`: `.venv/bin/pytest`가 설치되어 있지 않아 pending
- 상세 실행 기록은
  `docs/verification/feature-embedding-topic-grouping.md`를 참조합니다.

## 확인 결과

- 기본 threshold 0.72와 `deterministic-hash-v1`을 사용한 read-only
  dry-run 결과:
  - published 24h, 최대 100건: topic 후보 98개, multi-article 후보 2개
  - published 72h, 최대 150건: topic 후보 141개, multi-article 후보 4개
  - published 168h, 최대 200건: topic 후보 186개, multi-article 후보 4개
  - published all, 최대 200건: topic 후보 186개, multi-article 후보 4개
  - created 24h, 최대 100건: topic 후보 97개, multi-article 후보 3개
- 모든 dry-run에서 `embedding_provider_enabled: false`,
  `db_write_performed: false`를 확인했습니다.
- Local deterministic hash 결과는 pipeline과 출력 구조 검증 결과이며,
  실제 semantic embedding 품질 검증 결과는 아닙니다.
- 실제 OpenAI embedding provider 호출은 수행하지 않았습니다.

## 비고

- Human operator가 승인해 적용한 review fix는 없습니다.
- OpenAI embedding provider batching/chunking 제안은 이번 MVP의 200건
  상한과 범위를 고려해 deferred 상태입니다.
- Topic summary, key points, LLM keyword 생성, API, frontend, DB 저장,
  CronJob 자동화는 구현하지 않았습니다.
- 실제 provider 비교, multi-article 후보 human review, threshold/model별
  semantic 품질 검증은 pending입니다.
- DB migration, production deployment, K3s rollout, production
  verification, push, merge는 수행하지 않았습니다.
