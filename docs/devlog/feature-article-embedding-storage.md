# Supabase pgvector 기반 article embedding 저장·재사용 MVP

## 작업 목적

기사별 embedding을 Supabase PostgreSQL에 저장하고, 입력이 변하지 않은 경우
외부 embedding API를 다시 호출하지 않는 저장·재사용 경로를 만든다.

초기 범위는 기사 제목과 RSS 요약을 사용하는 소량 batch MVP다. Public API나
daily topic pipeline에 바로 연결하지 않고, 저장 계약과 idempotent reuse
동작을 먼저 독립적으로 검증하는 것을 목표로 했다.

## 기존 문제

기존 topic 분석은 실행 시점에 embedding을 생성하지만 기사 단위 vector를
지속적으로 저장하거나 source 변경을 hash로 판정하는 구조가 없었다. 따라서
반복 분석 시 동일 입력에 provider 비용이 다시 발생할 수 있고, 저장 vector를
DB에서 cosine similarity로 검증할 경로도 없었다.

또한 기사와 embedding의 관계, model·dimension·입력 유형 같은 생성 계약을
DB에 보존하는 구조가 없어 다음 실행에서 기존 결과를 안전하게 재사용할 기준이
없었다.

## 변경 내용

- pgvector extension과 `article_embeddings` migration 추가
- 제목·RSS 요약 정규화와 SHA-256 source hash 구현
- provider 경계와 DB lookup/insert/update/reuse 로직 분리
- 소량 batch script와 상태 집계 구현
- 같은 embedding 계약으로 제한한 cosine similarity query 구현
- architecture와 human-controlled database runbook 갱신
- migration 적용 전·후 확인 SQL, 중단 기준과 복구 방향 문서화

## 구현 상세

실제 repository query를 기준으로 article ID는 bigint, RSS 요약은
`articles.summary`, DB driver는 SQLAlchemy와 psycopg3로 확인했다.

초기 계약은 기존 provider 기본값인 `text-embedding-3-small`, provider
`openai`, dimension 1536, source type `title_summary`다. 입력은 letter case를
보존하고 연속 공백과 줄바꿈만 한 칸으로 정규화한다.

DB row는 article/provider/model/source type 조합마다 하나를 유지한다. 같은
hash는 `reused`, row가 없으면 `created`, hash가 변경되면 `updated`를 반환한다.
Provider vector 길이가 1536과 다르면 SQL write 전에 실패한다.

Python pgvector adapter dependency는 추가하지 않았다. Vector를 pgvector text
형식으로 직렬화해 bind parameter로 전달하고 SQL에서 `vector`로 cast한다.

Migration은 `vector` extension과 `article_embeddings` table을 생성한다.
`articles(id)`에는 `ON DELETE CASCADE` foreign key를 두고,
`(article_id, provider, model, source_text_type)` unique constraint로 같은 생성
계약의 최신 성공 row 하나만 유지한다. HNSW/IVFFlat index는 추가하지 않았다.

Batch script는 기본 10건, 최대 100건으로 처리량을 제한한다. `--article-id`는
반복 지정할 수 있고, `--dry-run`은 article selection만 수행해 provider 호출과
DB write를 건너뛴다. 실제 처리에서는 각 article을 독립 transaction으로
처리하고 생성·갱신·재사용·실패 수를 JSON으로 출력한다.

Cosine similarity 조회는 pgvector `<=>` operator를 사용한다. 비교 대상은 같은
provider, model, dimension, source text type으로 제한해 서로 다른 embedding
공간의 vector가 섞이지 않도록 했다.

## 대안 검토

- 별도 vector DB: 운영 구성과 데이터 일관성 부담이 커 이번 MVP에서 제외했다.
- 기사별 embedding 이력 table: 최신 성공 vector 재사용이 목표라 제외했다.
- 매 변경마다 새 row: 조회와 정리 복잡도가 증가해 같은 계약의 row update를
  선택했다.
- HNSW/IVFFlat index: 데이터 규모와 latency evidence가 없어 제외했다.
- Daily topic pipeline 즉시 연결: 독립 검증 전 운영 pipeline coupling이 생겨
  제외했다.
- `pgvector` Python dependency: 타입 adapter 편의는 있지만 현재 문자열 bind와
  SQL cast로 충분해 runtime dependency를 늘리지 않았다.
- OpenAI batch embedding과 DB bulk upsert: 소량 MVP의 복잡도를 높이므로 실제
  처리량과 실행 시간이 확인된 뒤 검토하기로 했다.
- `.env` 자동 로드: script가 shell environment의 명시적 설정을 사용하도록
  유지했다. 공통 configuration loader 필요성은 여러 script에서 중복이 확인될
  때 별도 작업으로 검토한다.
- 별도 `embedding_runs` table: 현재는 script 결과와 verification 기록으로
  충분하며 scheduled pipeline으로 전환할 때 재시도·중단 탐지 요구사항과 함께
  설계하기로 했다.

## 선택한 접근과 근거

기존 raw SQL과 SQLAlchemy `text()` 패턴을 유지했다. Provider는 기존
`EmbeddingProvider` protocol과 `OpenAIEmbeddingProvider`를 재사용해 fake
client 테스트가 가능하도록 했다. Supabase PostgreSQL을 그대로 vector
store로 사용해 article foreign key와 cascade 일관성을 유지했다.

입력 내용을 직접 비교하는 대신 정규화된 source text의 SHA-256 hash를
저장했다. 이를 통해 긴 text 비교 없이 변경 여부를 판정하고, 같은 입력에서는
provider 호출 전에 빠르게 `reused`를 반환할 수 있다.

새 services/repositories 계층을 만들지 않고 기존 `app/utils` 구조에 저장
로직을 추가했다. 현재 repository 규모와 기존 구성에 맞추면서 변경 범위를
작게 유지하기 위한 선택이다.

## 트레이드오프

- `vector(1536)` 고정은 schema와 model mismatch를 조기에 차단하지만 다른
  dimension model 사용 시 새 migration 또는 저장 정책 변경이 필요하다.
- ANN index가 없어 대규모 similarity query 성능은 제한될 수 있다.
- 최신 row만 유지하므로 과거 source hash/vector 이력은 남지 않는다.
- Batch는 수동 실행이며 실행 이력 table과 scheduler가 없다.
- Vector를 문자열로 직렬화해 SQL cast하므로 Python 전용 pgvector type
  adapter의 타입 편의는 사용하지 않는다.
- 개별 article transaction은 부분 실패 격리에 유리하지만 대량 처리에서는
  batch API와 bulk upsert보다 느릴 수 있다.
- 환경 변수를 자동 로드하지 않아 실행 환경에서 명시적으로 주입해야 한다.

## 테스트

실제 결과는 verification 문서를 source of truth로 사용한다.

- `python -m compileall app scripts tests`: 통과
- 관련 표준 `unittest`: 20 tests 통과
- `python -m unittest discover -s tests`: 전체 136 tests 통과
- `python scripts/embed_articles.py --help`: 통과
- `git diff --check`: 통과
- `pytest`: agent 환경에 executable/module이 없어 실패
- Agent 환경의 dry-run: `DATABASE_URL`이 없어 provider 호출과 DB write 전에
  중단
- 별도 PostgreSQL/pgvector test DB에서 unique constraint와 cascade delete:
  환경 제약으로 미수행

사람이 제공한 Supabase verification log:

- Read-only dry-run: 기사 3건 선택, provider 호출과 DB write 없음
- 최초 실제 실행: `selected=3`, `created=3`, `failed=0`
- 동일 batch 재실행: `selected=3`, `reused=3`, `created=0`, `updated=0`,
  `failed=0`
- 저장 vector 3건: 실제 차원과 기록된 dimension 모두 1536
- Cosine similarity: 기준 article 자신이 similarity 1.0으로 첫 번째 반환,
  나머지 결과는 더 낮은 값으로 내림차순 정렬

## 운영 반영

사람이 제공한 verification log 기준으로 Supabase pgvector 저장과 소량 batch
E2E는 확인됐다.

```text
dry-run
→ 기사 3건 선택
→ write 없음

첫 실행
→ embedding 3건 생성
→ article_embeddings 저장

동일 조건 재실행
→ 신규 생성·갱신 없음
→ 기존 embedding 3건 재사용
```

저장된 vector dimension과 pgvector cosine similarity query도 실제 Supabase에서
확인됐다. 다만 이 작업은 API application 배포 변경이 아니며 K3s manifest,
CronJob, rollout과 production curl verification은 수행하지 않았다. 따라서
production deployment 또는 K3s rollout 완료로 기록하지 않는다.

## README 업데이트 판단

README는 변경하지 않았다. Public API나 일반 사용자 시작 절차가 바뀌지 않았고,
내부 storage 설계와 운영 절차는 architecture/database, architecture/pipeline,
database runbook에 기록하는 편이 현재 문서 구조에 맞다.

## 확인 결과

로컬 단위 테스트에서 정규화/hash, provider 미호출 reuse, insert/update,
model별 row, dimension mismatch 차단, batch 집계, dry-run provider 미호출,
호환 embedding만 대상으로 하는 cosine SQL을 확인했다.

사람이 제공한 실제 Supabase log에서는 최초 3건 생성과 동일 batch 3건 재사용,
1536차원 저장, cosine similarity 정렬을 확인했다. 동일 입력에서 중복
embedding을 생성하지 않는 핵심 MVP 흐름은 검증됐다.

운영 article의 제목이나 요약을 변경하는 update 검증은 데이터 변경 위험 때문에
수행하지 않았다. 이 경로는 fake provider 단위 테스트로 검증했으며 별도 test
fixture 기반 DB 통합 검증은 pending이다.

Approved Fixes에는 추가 코드 수정 항목이 없었다. `.env` 자동 로드, ANN index,
batch/bulk 처리, 실행 이력 table과 ORM 전환은 deferred 상태다.

## 이번 단계의 의미

기사 embedding을 일회성 계산 결과가 아니라 source content와 model 계약에
연결된 재사용 가능한 backend 자산으로 관리할 기반을 추가했다.

특히 저장 자체뿐 아니라 입력 변경 감지, API 재호출 방지, dimension 계약,
호환 vector만 대상으로 하는 similarity 조회까지 하나의 검증 가능한 흐름으로
정리했다. Daily topic pipeline에 연결하기 전에 저장 계층의 비용·일관성
위험을 독립적으로 줄인 단계다.

## 포트폴리오용 요약

PostgreSQL pgvector와 SHA-256 content fingerprint를 사용해 기사 embedding의
idempotent create/update/reuse 흐름을 구현했다. Provider 경계, dimension
validation, bind parameter SQL, dry-run batch와 cosine similarity 조회를 함께
설계했다. 실제 Supabase에서 최초 3건 생성, 동일 batch 3건 재사용, 1536차원
vector와 cosine similarity를 확인해 비용 제어와 저장 일관성을 검증했다.

## 다음 단계 후보

- 별도 test PostgreSQL에서 unique constraint와 cascade delete 통합 검증
- 별도 test fixture에서 source hash 변경에 따른 DB update 통합 검증
- 데이터 규모와 latency를 근거로 ANN index 필요성 평가
- 처리량 증가 시 OpenAI batch embedding, bulk upsert와 retry/reconciliation
  검토
- scheduled pipeline 전환 시 `embedding_runs`와 실패 재처리 정책 검토
- 여러 script의 설정 로딩이 중복될 경우 공통 configuration loader 검토
- Daily topic pipeline 연결은 별도 task로 검토
- Human final diff 확인 후 push와 PR 진행
