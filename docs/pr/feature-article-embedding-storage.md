# Supabase pgvector 기반 article embedding 저장·재사용 MVP

## 작업 내용

- 기사 제목과 RSS 요약을 기반으로 OpenAI embedding을 생성해 Supabase
  PostgreSQL pgvector에 저장하는 MVP를 구현했다.
- 정규화된 입력의 SHA-256 hash를 비교해 동일 입력은 기존 embedding을
  재사용하고, 입력 변경 시 기존 row를 갱신하도록 했다.
- 소량 기사 처리용 batch script와 stored vector cosine similarity 내부 조회
  경로를 추가했다.
- Database/pipeline architecture와 migration 적용·검증 runbook을 갱신했다.

## 주요 변경 사항

- `articles.title`과 `articles.summary`의 연속 공백·줄바꿈을 정규화하고 UTF-8
  SHA-256 source text hash를 생성한다.
- 기존 `EmbeddingProvider` 경계를 재사용해 fake provider 기반 테스트가
  가능하며, OpenAI provider 호출과 DB 저장 판정을 분리했다.
- 같은 article, provider, model, source text type의 row가 없으면 `created`,
  hash가 변경되면 `updated`, hash가 같으면 provider 호출 없이 `reused`를
  반환한다.
- `text-embedding-3-small`의 1536차원 vector만 저장하며 dimension 불일치는
  DB write 전에 중단한다.
- 신규 runtime SQL은 SQLAlchemy `text()`와 bind parameter를 사용한다.
- `scripts/embed_articles.py`에 `--limit`, 반복 가능한 `--article-id`,
  `--dry-run`을 추가하고 `selected`, `created`, `updated`, `reused`,
  `failed` 집계를 출력한다.
- `--dry-run`은 article selection만 수행하고 embedding provider와 DB write를
  호출하지 않는다.
- cosine similarity 조회는 같은 provider, model, dimension, source text
  type으로 비교 대상을 제한한다.
- Approved Fixes에 추가 코드 수정 항목은 없었다.

## 추가/변경된 API

- Public FastAPI endpoint와 기존 API contract 변경 없음
- Similarity search는 `find_similar_article_embeddings()` 내부 함수로만 제공
- Daily topic pipeline에는 연결하지 않음

## DB 변경 사항

- `db/migrations/006_create_article_embeddings.sql` 추가
- Supabase `vector` extension 활성화
- `article_embeddings` table 추가
  - `articles(id)` bigint foreign key와 `ON DELETE CASCADE`
  - `embedding vector(1536)`
  - provider, model, dimension, source text type/hash, timestamp
  - `(article_id, provider, model, source_text_type)` unique constraint
- provider/model/dimension/source type 조회용 일반 index 추가
- HNSW 또는 IVFFlat ANN index는 범위에서 제외
- 별도 `embedding_runs` table은 추가하지 않음
- 사람이 제공한 verification log 기준 실제 Supabase에 저장된 3개 vector의
  차원은 모두 1536으로 확인됨

## README 영향

README 변경 없음.

Public API나 일반 사용자 실행 흐름은 바뀌지 않았다. 이번 변경은 backend 내부
storage와 human-controlled batch 운영 절차이므로
`docs/architecture/database.md`, `docs/architecture/pipeline.md`,
`docs/runbooks/database-check.md`에 설계와 실행 경계를 기록했다.

## 테스트

- `python -m compileall app scripts tests`
  - 통과
- `python -m unittest tests.test_embed_articles tests.test_article_embedding_storage tests.test_article_embedding_migration tests.test_article_embeddings`
  - 관련 20 tests 통과
- `python -m unittest discover -s tests`
  - 전체 136 tests 통과
- `python scripts/embed_articles.py --help`
  - 통과
- `git diff --check`
  - 통과
- `pytest -q tests/test_article_embedding_storage.py tests/test_article_embedding_migration.py tests/test_article_embeddings.py`
  - 현재 환경에 `pytest` executable이 없어 실패
- `.venv/bin/python -m pytest ...`
  - `.venv`에 pytest module이 없어 실패
- agent 환경의 `python scripts/embed_articles.py --limit 3 --dry-run`
  - `DATABASE_URL`이 없어 provider 호출과 DB write 전에 중단
- 별도 PostgreSQL/pgvector test DB 통합 테스트
  - 환경 제약으로 미수행

## 확인 결과

- 단위 테스트로 입력 정규화, 동일 입력 hash, 입력 변경 hash, 요약 없음,
  provider 미호출 reuse, insert/update, model/source type 분리, dimension 차단,
  batch 집계, dry-run provider/write 미호출과 cosine query 조건을 확인했다.
- 사람이 제공한 Supabase verification log 기준:
  - dry-run에서 기사 3건 선택, write 없음
  - 최초 실행에서 `created=3`, `failed=0`
  - 동일 batch 재실행에서 `reused=3`, `created=0`, `updated=0`, `failed=0`
  - 저장 vector 3건의 실제 차원과 기록 dimension이 모두 1536
  - pgvector `<=>` cosine similarity query가 내림차순 결과를 반환
- 운영 article의 제목이나 요약을 변경하는 update 검증은 수행하지 않았다.
- 별도 test DB의 unique constraint와 cascade delete 통합 검증은 미수행이다.

## 비고

- PR merge, git push와 main branch merge는 수행하지 않았다.
- K3s manifest, CronJob, rollout과 deployment는 변경하거나 수행하지 않았다.
- Secret, `.env`, kubeconfig와 credential 값은 코드나 문서에 기록하지 않았다.
- `.env` 자동 로드, ANN index, provider batch 호출, bulk upsert,
  `embedding_runs` table과 ORM 전환은 Approved Fixes에서 deferred로 유지했다.
- Production deployment 또는 K3s rollout 완료를 주장하지 않는다.
