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
- 동일 conflict key의 동시 insert 경쟁을 처리하는 atomic upsert 적용
- 소량 batch script와 상태 집계 구현
- 같은 embedding 계약으로 제한한 cosine similarity query 구현
- architecture와 human-controlled database runbook 갱신
- migration 적용 전·후 확인 SQL, 중단 기준과 복구 방향 문서화
- migration test의 현재 작업 디렉터리 의존 제거
- Approved fixes 문서의 Markdown fence 구조 수정

## 구현 상세

실제 repository query를 기준으로 article ID는 bigint, RSS 요약은
`articles.summary`, DB driver는 SQLAlchemy와 psycopg3로 확인했다.

초기 계약은 기존 provider 기본값인 `text-embedding-3-small`, provider
`openai`, dimension 1536, source type `title_summary`다. 입력은 letter case를
보존하고 연속 공백과 줄바꿈만 한 칸으로 정규화한다.

DB row는 article/provider/model/source type 조합마다 하나를 유지한다. 같은
hash는 provider 호출 전에 `reused`를 반환한다. 신규 또는 변경 입력은
`INSERT ... ON CONFLICT DO UPDATE`로 저장하며 실제 insert면 `created`,
기존 row 또는 insert race의 conflict면 `updated`를 반환한다. Provider vector
길이가 1536과 다르면 SQL write 전에 실패한다.

Conflict target은 migration의 unique constraint와 동일한
`(article_id, provider, model, source_text_type)`다. Conflict 시 embedding,
dimension, source text hash와 updated timestamp를 최신 결과로 갱신한다.
PostgreSQL `RETURNING (xmax = 0) AS inserted` 결과를 사용해 insert와 update
상태를 구분한다.

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

Migration test는 `Path(__file__).resolve()`에서 repository root를 계산해
migration 절대 경로를 구성한다. Repository root 외부에서 test를 실행해도
현재 작업 디렉터리에 의존하지 않는다.

## 대안 검토

- 별도 vector DB: 운영 구성과 데이터 일관성 부담이 커 이번 MVP에서 제외했다.
- 기사별 embedding 이력 table: 최신 성공 vector 재사용이 목표라 제외했다.
- 매 변경마다 새 row: 조회와 정리 복잡도가 증가해 같은 계약의 row update를
  선택했다.
- `SELECT → INSERT` 유지: 단일 실행에서는 단순하지만 동시 worker가 같은 key를
  처리하면 unique constraint race로 한 작업이 실패할 수 있어 atomic upsert로
  변경했다.
- 분산 락 또는 advisory lock: embedding API 중복 호출까지 막을 수 있지만
  수동 소량 MVP에는 범위가 크므로 DB unique race만 upsert로 해결했다.
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

기존 row 조회는 hash 동일 fast path를 위해 유지하되 저장은 단일 atomic
upsert로 통합했다. 이 구조는 일반적인 동일 hash 재실행에서는 provider를
호출하지 않으면서, 두 worker가 동시에 row 없음으로 판단한 경우에도 두 번째
write가 unique violation으로 실패하지 않게 한다.

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
- Atomic upsert는 DB unique constraint race를 해결하지만 동시에 시작한
  worker의 embedding API 중복 호출까지 방지하지는 않는다.
- `xmax` 기반 insert/update 판정은 PostgreSQL 동작에 의존하므로 다른 DB로
  이전할 경우 상태 판정 방식을 재검토해야 한다.

## 테스트

실제 결과는 verification 문서를 source of truth로 사용한다.

- `python -m compileall app scripts tests`: 통과
- 초기 관련 표준 `unittest`: 20 tests 통과
- Atomic upsert 관련 `unittest`: 17 tests 통과
- `python -m unittest discover -s tests`: 승인 fix 적용 후 전체 137 tests 통과
- `python scripts/embed_articles.py --help`: 통과
- `git diff --check`: 통과
- `pytest`: agent 환경에 executable/module이 없어 실패
- Agent 환경의 dry-run: `DATABASE_URL`이 없어 provider 호출과 DB write 전에
  중단
- 별도 PostgreSQL/pgvector test DB에서 unique constraint와 cascade delete:
  환경 제약으로 미수행
- Migration test: repository root와 `/tmp` 작업 디렉터리에서 각각 통과
- Approved fixes Markdown: standalone 3-backtick fence 20개가 10쌍으로 대응

사람이 제공한 Supabase verification log:

- Read-only dry-run: 기사 3건 선택, provider 호출과 DB write 없음
- 최초 실제 실행: `selected=3`, `created=3`, `failed=0`
- 동일 batch 재실행: `selected=3`, `reused=3`, `created=0`, `updated=0`,
  `failed=0`
- 저장 vector 3건: 실제 차원과 기록된 dimension 모두 1536
- Cosine similarity: 기준 article 자신이 similarity 1.0으로 첫 번째 반환,
  나머지 결과는 더 낮은 값으로 내림차순 정렬

위 Supabase E2E 결과는 atomic upsert 승인 fix 적용 전에 수집된 결과다.
Upsert 적용 후 `python scripts/embed_articles.py --limit 3` 운영 회귀는 DB
write와 credential 환경이 필요해 Codex가 실행하지 않았으며 pending이다.

## 운영 반영

사람이 제공한 verification log 기준으로 최초 구현의 Supabase pgvector 저장과
소량 batch E2E는 확인됐다.

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
확인됐다.

이후 승인 fix로 저장 SQL을 atomic upsert로 변경했다. 변경 후 로컬 회귀
137 tests는 통과했지만 운영 재사용 E2E는 다시 실행하지 않았다. 따라서
atomic upsert 버전의 운영 회귀는 사람이 수행해야 하는 pending 항목이다.

이 작업은 API application 배포 변경이 아니며 K3s manifest, CronJob, rollout과
production curl verification은 수행하지 않았다. Production deployment 또는
K3s rollout 완료로 기록하지 않는다.

## README 업데이트 판단

README는 변경하지 않았다. Public API나 일반 사용자 시작 절차가 바뀌지 않았고,
내부 storage 설계와 운영 절차는 architecture/database, architecture/pipeline,
database runbook에 기록하는 편이 현재 문서 구조에 맞다.

## 확인 결과

로컬 단위 테스트에서 정규화/hash, provider 미호출 reuse, insert/update,
model별 row, dimension mismatch 차단, batch 집계, dry-run provider 미호출,
호환 embedding만 대상으로 하는 cosine SQL을 확인했다.

Approved Fix 적용 후 atomic `ON CONFLICT DO UPDATE` SQL, migration unique key와
동일한 conflict target, conflict 시 정상 `updated` 반환, bind parameter
전달과 기존 reuse/dimension validation 회귀를 확인했다. Migration test는
repository root와 `/tmp`에서 모두 통과했다.

사람이 제공한 실제 Supabase log에서는 최초 3건 생성과 동일 batch 3건 재사용,
1536차원 저장, cosine similarity 정렬을 확인했다. 동일 입력에서 중복
embedding을 생성하지 않는 핵심 MVP 흐름은 검증됐다.

운영 article의 제목이나 요약을 변경하는 update 검증은 데이터 변경 위험 때문에
수행하지 않았다. 이 경로는 fake provider 단위 테스트로 검증했으며 별도 test
fixture 기반 DB 통합 검증은 pending이다.

승인된 수정 3건은 모두 적용했다.

- 저장 경로 atomic upsert 전환
- Approved fixes Markdown fence 수정
- Migration test 경로 독립성 확보

Atomic upsert 적용 후 운영 E2E 재실행과 Antigravity 재검토는 pending이다.
`.env` 자동 로드, ANN index, provider batch/bulk 처리, 실행 이력 table, ORM
전환과 embedding API 중복 호출 방지용 분산 제어는 deferred 상태다.

## 이번 단계의 의미

기사 embedding을 일회성 계산 결과가 아니라 source content와 model 계약에
연결된 재사용 가능한 backend 자산으로 관리할 기반을 추가했다.

특히 저장 자체뿐 아니라 입력 변경 감지, API 재호출 방지, dimension 계약,
호환 vector만 대상으로 하는 similarity 조회까지 하나의 검증 가능한 흐름으로
정리했다. Daily topic pipeline에 연결하기 전에 저장 계층의 비용·일관성
위험을 독립적으로 줄인 단계다.

후속 승인 fix에서는 데이터 중복 방지에 그치지 않고 동시 insert가 batch
failure로 이어지는 application-level race를 atomic upsert로 보완했다. 테스트
경로와 workflow 문서 구조도 실행 위치와 Markdown renderer에 덜 취약하게
정리했다.

## 포트폴리오용 요약

PostgreSQL pgvector와 SHA-256 content fingerprint를 사용해 기사 embedding의
idempotent create/update/reuse 흐름을 구현했다. Provider 경계, dimension
validation, bind parameter SQL, dry-run batch와 cosine similarity 조회를 함께
설계했다. 실제 Supabase에서 최초 3건 생성, 동일 batch 3건 재사용, 1536차원
vector와 cosine similarity를 확인했다. 이후 atomic upsert를 적용해 동일
conflict key의 동시 insert가 unique constraint failure로 이어지지 않도록
보완하고, 전체 137 tests로 회귀를 검증했다.

## 다음 단계 후보

- 별도 test PostgreSQL에서 unique constraint와 cascade delete 통합 검증
- 별도 test fixture에서 source hash 변경에 따른 DB update 통합 검증
- Atomic upsert 적용 후 소량 운영 재사용 E2E 재검증
- Approved Fix 1~3에 대한 Antigravity 재검토
- 데이터 규모와 latency를 근거로 ANN index 필요성 평가
- 처리량 증가 시 OpenAI batch embedding, bulk upsert와 retry/reconciliation
  검토
- scheduled pipeline 전환 시 `embedding_runs`와 실패 재처리 정책 검토
- 여러 script의 설정 로딩이 중복될 경우 공통 configuration loader 검토
- Daily topic pipeline 연결은 별도 task로 검토
- Human final diff 확인 후 push와 PR 진행
