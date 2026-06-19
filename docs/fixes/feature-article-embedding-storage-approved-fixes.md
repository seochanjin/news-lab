# Approved Fixes: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Approved Fixes

### 1. Article embedding 저장을 원자적 upsert로 변경

CodeRabbit review에서 현재 `SELECT → INSERT` 흐름에 동시성 경쟁 조건이 있음을 확인했다.

현재 동일한 다음 조합을 두 worker가 동시에 처리할 경우:

```text
article_id
provider
model
source_text_type
```

두 worker가 모두 기존 row가 없다고 판단한 뒤 각각 `INSERT`를 시도할 수 있다.

첫 번째 `INSERT`는 성공하지만 두 번째 `INSERT`는 unique constraint 오류로 실패해, 멱등성을 의도한 batch가 실패할 수 있다.

승인된 수정:

- [x] 신규 embedding 저장을 `INSERT ... ON CONFLICT DO UPDATE` 기반 원자적 upsert로 변경한다.
- [x] conflict target은 기존 unique constraint와 동일하게 유지한다.

```text
article_id
provider
model
source_text_type
```

- [x] conflict 발생 시 다음 값을 최신 결과로 갱신한다.
  - `embedding`
  - `dimension`
  - `source_text_hash`
  - `updated_at`
- [x] 기존 row가 없으면 `created`, race 또는 기존 row가 있으면 현재 계약에 맞는 상태를 반환한다.
- [x] unique constraint race로 batch 전체가 실패하지 않도록 한다.
- [x] 모든 runtime 값은 bind parameter를 사용한다.
- [x] vector 값을 SQL f-string으로 직접 삽입하지 않는다.
- [x] 기존 hash가 동일한 일반 경로에서는 provider 미호출 및 `reused` 동작을 유지한다.
- [x] 동시 실행에서 embedding API 중복 호출 자체를 완전히 방지하는 분산 락은 이번 범위에 포함하지 않는다.

테스트 추가 또는 보완:

- [x] 동일 conflict key에 대해 upsert SQL이 사용되는지 검증한다.
- [x] conflict 발생 시 unique constraint 예외 대신 정상 완료되는 경로를 검증한다.
- [x] hash 동일 시 기존 provider 미호출 테스트가 유지된다.
- [x] vector dimension 불일치 시 저장하지 않는 기존 검증이 유지된다.
- [x] 기존 136개 이상의 전체 회귀 테스트가 통과한다.

### 2. Approved fixes 문서의 Markdown closing fence 수정

CodeRabbit review에서 `Verification Required` 섹션의 closing fence가 백틱 4개로 작성되어 Markdown code block이 깨지는 문제를 확인했다.

승인된 수정:

- [x] 잘못된 closing fence ` ```` `를 ` ``` `로 변경한다.
- [x] 문서 내 모든 fenced code block의 opening과 closing 개수가 일치하는지 확인한다.
- [x] fixes 문서의 내용 자체는 불필요하게 재작성하지 않는다.

### 3. Migration test 경로를 현재 작업 디렉터리와 독립적으로 변경

CodeRabbit review에서 migration test가 repository root를 현재 작업 디렉터리로 가정하고 있음을 확인했다.

현재 방식:

```python
Path("db/migrations/006_create_article_embeddings.sql")
```

이 방식은 repository root가 아닌 위치에서 test를 실행하면 실패할 수 있다.

승인된 수정:

- [x] `tests/test_article_embedding_migration.py`에서 `__file__` 기준으로 repository root를 계산한다.
- [x] migration 파일 경로를 repository root에 대한 절대 경로로 구성한다.
- [x] repository root에서 실행한 기존 test가 계속 통과해야 한다.
- [x] repository root가 아닌 임시 작업 디렉터리에서도 migration test가 통과하는지 확인한다.

권장 구조:

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "db" / "migrations" / "006_create_article_embeddings.sql"
```

## Rejected or Deferred Suggestions

### 1. Batch script의 `.env` 자동 로드

Deferred.

현재 `scripts/embed_articles.py`는 `DATABASE_URL`과 embedding provider 관련 환경변수가 shell environment에 주입되어 있어야 한다.

실행 전 다음 방식으로 환경변수를 로드하면 정상 동작한다.

```bash
set -a
source .env
set +a
```

가상환경 활성화는 Python 실행 환경만 변경하며 `.env`를 자동으로 읽지 않는다.

```bash
source .venv/bin/activate
```

현재 동작은 명시적인 환경변수 주입 방식으로 정상이며, embedding 저장·재사용 MVP의 기능 결함은 아니다.

향후 다음 조건이 확인되면 공통 configuration loader 사용을 별도 작업으로 검토한다.

- 다른 독립 script도 반복적으로 `.env` 로드가 필요함
- FastAPI application과 batch script의 설정 로딩 방식이 달라짐
- 운영 CronJob에서 동일한 설정 로딩 코드가 중복됨

이번 작업에서는 새 dependency 또는 자동 `.env` loader를 추가하지 않는다.

### 2. HNSW 또는 IVFFlat vector index

Deferred.

현재는 소량 embedding 저장과 exact cosine similarity 검증 단계다.

실제 row 수와 query latency를 측정한 뒤 별도 작업에서 검토한다.

### 3. OpenAI batch embedding 및 DB bulk upsert

Deferred.

현재 script는 최대 처리량을 제한한 소량 MVP다.

Daily pipeline 적용 후 실제 처리량과 실행 시간을 측정한 뒤 다음을 검토한다.

- OpenAI batch embedding
- 병렬 API 호출
- DB bulk insert/update
- rate limit 대응
- retry 및 reconciliation

### 4. 별도 `embedding_runs` 실행 이력 table

Deferred.

현재 실행 결과는 script 출력과 verification 문서에 기록한다.

Daily pipeline 분리 시 다음 요구사항과 함께 다시 검토한다.

- 실행 시작 및 종료 상태
- 선택·생성·갱신·재사용·실패 수
- 개별 article 실패 기록
- 재시도 정책
- 중단된 실행 탐지

### 5. 기존 SQL의 ORM 전환

Deferred.

이번 작업의 신규 runtime SQL은 SQLAlchemy `text()`와 bind parameter를 사용한다.

기존 raw SQL 전체 ORM 전환과 동적 SQL 정리는 별도의 SQL refactoring 작업으로 유지한다.

### 6. 동시 실행 시 embedding API 중복 호출 완전 방지

Deferred.

이번 Approved Fix에서는 DB unique constraint race로 인해 batch가 실패하지 않도록 원자적 upsert를 적용한다.

동일 article을 여러 worker가 동시에 처리할 때 embedding API 호출 자체를 한 번만 보장하려면 다음과 같은 추가 제어가 필요할 수 있다.

- PostgreSQL advisory lock
- row-level lock
- processing state
- distributed lock
- job queue의 deduplication key

현재 수동 소량 batch MVP에서는 과도한 범위이므로 daily pipeline 병렬 실행 정책과 함께 후속 작업에서 검토한다.

## Applied Changes

적용 상태:

- Approved Fix 1
  - 상태: 적용 및 로컬 검증 완료
- Approved Fix 2
  - 상태: 적용 및 검증 완료
- Approved Fix 3
  - 상태: 적용 및 검증 완료

- Approved Fix 1 적용
  - 신규 embedding 저장과 hash 변경 갱신을 atomic upsert로 통합했다.
  - conflict target은 `(article_id, provider, model, source_text_type)`이다.
  - conflict 시 embedding, dimension, source text hash와 updated timestamp를
    갱신한다.
  - PostgreSQL `RETURNING (xmax = 0) AS inserted` 결과로 `created`와
    race/conflict의 `updated`를 구분한다.
  - 모든 runtime 값과 pgvector 문자열은 bind parameter로 전달한다.
  - hash 동일 provider 미호출 reuse와 dimension 불일치 저장 중단을 유지했다.
  - 관련 17 tests와 전체 137 tests가 통과했다.

- Approved Fix 2 적용
  - 잘못된 4-backtick closing fence가 남아 있지 않음을 확인했다.
  - standalone fenced code marker 20개가 opening/closing 10쌍으로 대응함을
    직접 확인했다.
  - 승인 checklist와 Applied Changes 외 문서 내용은 재작성하지 않았다.

- Approved Fix 3 적용
  - migration test가 `__file__`에서 repository root를 계산하도록 변경했다.
  - migration path를 repository root 기준 절대 경로로 구성했다.
  - repository root와 `/tmp` 작업 디렉터리에서 각각 test 통과를 확인했다.

기존 구현에서 완료된 내용:

- Supabase PostgreSQL의 `vector` extension 활성화
- `article_embeddings` table 생성
- `articles(id)` foreign key 및 `ON DELETE CASCADE`
- OpenAI `text-embedding-3-small` 기준 `vector(1536)` 저장
- `title_summary` 입력 텍스트 정규화
- UTF-8 SHA-256 source text hash 생성
- embedding provider 호출과 DB 저장 로직 분리
- 동일 hash에 대한 provider 미호출 및 embedding 재사용
- hash 변경 시 기존 row 갱신
- model 또는 source text type 변경 시 별도 row 저장
- vector dimension 검증
- bind parameter 기반 runtime SQL
- 소량 batch script
- `--limit`, `--article-id`, `--dry-run`
- `created`, `updated`, `reused`, `failed` 집계
- cosine similarity 조회
- architecture, pipeline, runbook 및 verification 갱신

운영 E2E 확인 결과:

```text
첫 번째 실제 실행
selected=3
created=3
updated=0
reused=0
failed=0
```

```text
동일 조건 두 번째 실행
selected=3
created=0
updated=0
reused=3
failed=0
```

Vector dimension 확인:

```text
article_id=2685 actual_dimension=1536 recorded_dimension=1536
article_id=2686 actual_dimension=1536 recorded_dimension=1536
article_id=2687 actual_dimension=1536 recorded_dimension=1536
```

Cosine similarity 확인:

```text
query_article_id=2687 article_id=2687 similarity=1.0
query_article_id=2687 article_id=2685 similarity=0.294441283666331
query_article_id=2687 article_id=2686 similarity=0.266297983343077
```

## Verification Required

### 1. Atomic upsert 관련 단위 테스트

```bash
python -m unittest \
  tests.test_article_embedding_storage \
  tests.test_article_embeddings
```

확인 기준:

- 신규 row 저장 SQL이 `ON CONFLICT`를 포함한다.
- conflict target이 unique constraint와 일치한다.
- conflict 발생 시 embedding, dimension, hash와 updated timestamp가 갱신된다.
- runtime 값이 bind parameter로 전달된다.
- hash 동일 시 provider 미호출 및 `reused` 결과가 유지된다.
- dimension 불일치 시 저장하지 않는다.

### 2. Migration test 경로 독립성 확인

Repository root에서 실행:

```bash
python -m unittest tests.test_article_embedding_migration
```

Repository root가 아닌 위치에서 실행:

```bash
cd /tmp
python \
  /Users/seochanjin/workspace/NewsLab/news-lab/tests/test_article_embedding_migration.py
```

또는 module import가 필요한 경우 repository를 `PYTHONPATH`에 지정한다.

```bash
cd /tmp
PYTHONPATH=/Users/seochanjin/workspace/NewsLab/news-lab \
python -m unittest \
  tests.test_article_embedding_migration
```

확인 기준:

- 현재 작업 디렉터리와 무관하게 migration 파일을 찾는다.
- test가 통과한다.

### 3. Markdown fence 확인

```bash
rg -n '^`{3,}$' \
  docs/fixes/feature-article-embedding-storage-approved-fixes.md
```

문서를 직접 확인해 모든 opening fence와 closing fence가 올바르게 대응하는지 검토한다.

추가로 Markdown renderer 또는 기존 문서 검사 command가 있으면 함께 사용한다.

### 4. 전체 회귀 검증

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

확인 기준:

- Python compile 통과
- 전체 test 통과
- whitespace 오류 없음
- task 범위 밖 변경 없음
- `.env` 및 실제 credential이 Git 변경에 포함되지 않음

### 5. 운영 E2E 회귀 확인

Atomic upsert 변경은 저장 SQL 경로에 영향을 주므로 소량 운영 E2E를 다시 확인한다.

환경변수 로드:

```bash
source .venv/bin/activate
set -a
source .env
set +a
```

동일 기사 재실행:

```bash
python scripts/embed_articles.py --limit 3
```

기대 결과:

```text
selected=3
created=0
updated=0
reused=3
failed=0
```

새 기사를 대상으로 생성 경로도 필요하면 `--article-id`로 아직 embedding이 없는 기사 한 건만 선택한다.

```bash
python scripts/embed_articles.py --article-id <미처리_article_id>
```

운영 article의 제목이나 요약은 검증 목적으로 수정하지 않는다.

### 6. 최종 Antigravity 재검토

Codex가 Approved Fix 1~3을 적용하고 verification을 갱신한 뒤 기존 Antigravity review 파일에 다음 `Re-review N`을 추가한다.

확인 항목:

- CodeRabbit CR-1 원자적 upsert 해결 여부
- Markdown fence 수정 여부
- migration test path 독립성
- 기존 embedding 생성·재사용 동작 회귀 없음
- 신규 scope creep 없음
- PR blocker 잔존 여부

### 7. 최종 상태

다음 조건을 모두 충족하면 PR 진행 가능하다.

- Atomic upsert 적용
- Unique constraint race로 인한 insert 실패 방지
- Markdown fence 수정
- Migration test path 독립성 확보
- 전체 회귀 테스트 통과
- 운영 재사용 E2E 통과
- Antigravity 재검토 완료
- 미해결 Required Fix 없음
