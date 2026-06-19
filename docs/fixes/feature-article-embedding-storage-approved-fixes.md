# Approved Fixes: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Approved Fixes

해당 사항 없음.

Antigravity 최초 review와 재검토 결과, 현재 구현에서 PR 전에 반드시 수정해야 하는 결함은 발견되지 않았다.

실제 Supabase 환경에서 다음 핵심 동작도 확인했다.

```text
소량 article 조회
→ embedding 생성
→ article_embeddings 저장
→ 동일 batch 재실행
→ 기존 embedding 재사용
```

실행 결과:

```json
{
  "dry_run": true,
  "selected": 3,
  "created": 0,
  "updated": 0,
  "reused": 0,
  "failed": 0
}
```

```json
{
  "dry_run": false,
  "selected": 3,
  "created": 3,
  "updated": 0,
  "reused": 0,
  "failed": 0,
  "failures": []
}
```

```json
{
  "dry_run": false,
  "selected": 3,
  "created": 0,
  "updated": 0,
  "reused": 3,
  "failed": 0,
  "failures": []
}
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

이번 작업에서는 새 dependency 또는 자동 `.env` 로더를 추가하지 않는다.

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

## Applied Changes

추가 수정 사항 없음.

기존 구현에서 다음이 완료되었다.

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

운영 환경에서 다음 E2E를 추가 확인했다.

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

동일 입력에 대해 중복 row 생성 또는 embedding 재호출 없이 재사용되는 핵심 MVP 동작을 확인했다.

## Verification Required

### 1. Verification 문서에 운영 E2E 결과 추가

`docs/verification/feature-article-embedding-storage.md`에 다음 내용을 추가한다.

````md
## Production E2E Verification

### 환경변수 로드

```bash
source .venv/bin/activate
set -a
source .env
set +a
```
````

환경변수 값 자체는 출력하거나 문서에 기록하지 않았다.

### Read-only dry-run

```bash
python scripts/embed_articles.py --limit 3 --dry-run
```

결과:

```json
{
  "dry_run": true,
  "selected": 3,
  "created": 0,
  "updated": 0,
  "reused": 0,
  "failed": 0
}
```

상태: 통과

확인 내용:

- Supabase DB 연결 성공
- 처리 대상 기사 3건 선택
- embedding provider 호출 없음
- DB insert/update 없음

### 최초 embedding 생성

```bash
python scripts/embed_articles.py --limit 3
```

결과:

```json
{
  "dry_run": false,
  "selected": 3,
  "created": 3,
  "updated": 0,
  "reused": 0,
  "failed": 0,
  "failures": []
}
```

상태: 통과

확인 내용:

- 기사 3건 선택
- embedding 3건 생성
- `article_embeddings`에 신규 저장
- 실패 없음

### 동일 batch 재실행

```bash
python scripts/embed_articles.py --limit 3
```

결과:

```json
{
  "dry_run": false,
  "selected": 3,
  "created": 0,
  "updated": 0,
  "reused": 3,
  "failed": 0,
  "failures": []
}
```

상태: 통과

확인 내용:

- 동일 기사 3건 선택
- 신규 생성 없음
- 갱신 없음
- 기존 embedding 3건 재사용
- 실패 없음

동일한 article, provider, model, source text type 및 source text hash에 대해 기존 embedding이 재사용됨을 확인했다.

````

### 2. DB row 확인

Supabase SQL Editor에서 다음을 확인한다.

```sql
select
    article_id,
    provider,
    model,
    dimension,
    source_text_type,
    source_text_hash,
    created_at,
    updated_at
from article_embeddings
order by id desc
limit 10;
````

확인 기준:

- 실행 대상 article 3건의 row 존재
- `provider = 'openai'`
- `model = 'text-embedding-3-small'`
- `dimension = 1536`
- `source_text_type = 'title_summary'`
- `source_text_hash`가 비어 있지 않음

### 3. 실제 vector dimension 확인

```sql
select
    article_id,
    vector_dims(embedding) as actual_dimension,
    dimension as recorded_dimension
from article_embeddings
order by id desc
limit 10;
```

확인 기준:

```text
actual_dimension = 1536
recorded_dimension = 1536
```

### 4. 중복 row 확인

```sql
select
    article_id,
    provider,
    model,
    source_text_type,
    count(*) as row_count
from article_embeddings
group by
    article_id,
    provider,
    model,
    source_text_type
having count(*) > 1;
```

기대 결과:

```text
0 rows
```

### 5. Cosine similarity 확인

구현된 내부 similarity 조회 경로 또는 검증 SQL을 사용해 결과를 확인한다.

확인 기준:

- 같은 provider만 비교
- 같은 model만 비교
- 같은 dimension만 비교
- 같은 source text type만 비교
- 자기 자신은 similarity가 1에 가깝게 반환
- 결과가 cosine similarity 내림차순으로 정렬

### 6. 최종 회귀 검증

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

확인 기준:

- Compile 통과
- 전체 test 통과
- whitespace 오류 없음
- 변경 범위가 task와 문서 범위에 한정됨
- secret 또는 `.env`가 Git 변경에 포함되지 않음

### 7. 최종 상태

다음 조건을 만족하면 PR 진행 가능하다.

- Supabase migration 적용 완료
- dry-run 성공
- 최초 3건 생성 성공
- 동일 batch 재실행 시 3건 재사용
- 실패 0건
- DB row 및 dimension 확인
- 중복 row 없음
- cosine similarity 조회 확인
- 전체 회귀 테스트 통과
