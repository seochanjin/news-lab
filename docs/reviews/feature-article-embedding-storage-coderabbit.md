# CodeRabbit Review: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Review Summary

CodeRabbit review에서 총 세 가지 문제를 확인했다.

첫 번째는 article embedding 저장 과정의 `SELECT → INSERT` 흐름이 동시 실행에 취약하다는 점이다.

동일한 article, provider, model과 source text type을 두 worker가 동시에 처리하면 두 worker 모두 기존 row가 없다고 판단할 수 있다. 이후 한 worker의 insert는 성공하지만 다른 worker는 unique constraint 오류로 실패할 수 있다.

Unique constraint가 데이터 중복은 막지만, 멱등성을 의도한 batch가 실패할 수 있으므로 신규 저장 경로를 원자적 upsert로 변경해야 한다.

두 번째는 approved fixes 문서의 Markdown closing fence가 백틱 4개로 작성되어 code block 구조가 깨진 문제다.

세 번째는 migration test가 repository root를 현재 작업 디렉터리로 가정해, 다른 작업 디렉터리에서 실행하면 migration 파일을 찾지 못할 수 있다는 점이다.

## Problems Found

### CR-1. Article embedding create/update가 원자적이지 않음

- 심각도: Major
- 유형: Concurrency / Idempotency
- 대상:
  - `app/utils/article_embedding_storage.py`

현재 저장 흐름은 다음과 같다.

```text
기존 embedding SELECT
→ row가 없으면 embedding 생성
→ INSERT
```

동일한 unique key를 두 worker가 동시에 처리하면 다음 경쟁 조건이 발생할 수 있다.

```text
Worker A: SELECT → 없음
Worker B: SELECT → 없음
Worker A: INSERT 성공
Worker B: INSERT → unique constraint 실패
```

영향:

- 중복 row 자체는 unique constraint가 막는다.
- 두 번째 worker의 batch item은 실패한다.
- 병렬 batch 또는 향후 daily pipeline에서 간헐적 failure가 발생할 수 있다.
- 멱등성을 기대한 처리 흐름이 unique violation으로 깨질 수 있다.

승인 수정 방향:

- 신규 저장을 `INSERT ... ON CONFLICT DO UPDATE` 기반 upsert로 변경한다.
- conflict key는 기존 unique constraint와 동일하게 사용한다.
- conflict 시 embedding, dimension, source text hash와 updated timestamp를 갱신한다.
- 모든 runtime 값은 bind parameter로 전달한다.
- 기존 hash 동일 재사용 경로는 유지한다.

이번 수정으로 unique constraint race에 따른 batch failure를 방지한다.

단, 두 worker가 embedding API를 동시에 호출하는 것까지 완전히 방지하는 것은 별도 lock 또는 job deduplication이 필요하므로 후속 과제로 남긴다.

### CR-2. Approved fixes 문서의 Markdown closing fence 오류

- 심각도: Minor
- 유형: Documentation syntax
- 대상:
  - `docs/fixes/feature-article-embedding-storage-approved-fixes.md`

`Verification Required` 섹션의 code block closing fence가 백틱 4개로 작성되었다.

잘못된 형식:

```text

```

````

정상 형식:

```text
````

````

영향:

- 이후 Markdown 내용이 code block으로 잘못 렌더링될 수 있다.
- 문서 가독성과 review artifact 구조가 깨질 수 있다.

승인 수정 방향:

- closing fence를 백틱 3개로 수정한다.
- 같은 문서의 fenced code block 구조를 재확인한다.

### CR-3. Migration test가 현재 작업 디렉터리에 의존함

- 심각도: Minor
- 유형: Test reliability
- 대상:
  - `tests/test_article_embedding_migration.py`

현재 migration 경로:

```python
Path("db/migrations/006_create_article_embeddings.sql")
````

이 코드는 test가 repository root에서 실행된다는 가정에 의존한다.

영향:

- IDE, CI 또는 다른 작업 디렉터리에서 test 실행 시 파일을 찾지 못할 수 있다.
- 실제 migration 내용과 무관한 환경 의존적 failure가 발생한다.

승인 수정 방향:

```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "db" / "migrations" / "006_create_article_embeddings.sql"
```

Repository root와 다른 위치에서 실행해도 test가 통과하는지 검증한다.

## Required Fixes Before PR

- [ ] CR-1: Article embedding 신규 저장을 atomic upsert로 변경한다.
  - `ON CONFLICT`를 사용한다.
  - conflict target을 unique constraint와 일치시킨다.
  - unique constraint race가 batch failure로 이어지지 않도록 한다.
  - 기존 reuse 및 dimension validation 동작을 유지한다.

- [ ] CR-2: Approved fixes 문서의 잘못된 Markdown closing fence를 수정한다.
  - 백틱 4개를 3개로 변경한다.
  - 문서의 fenced code block 구조를 확인한다.

- [ ] CR-3: Migration test가 현재 작업 디렉터리에 의존하지 않도록 수정한다.
  - `__file__` 기준 경로를 사용한다.
  - repository root 외부 작업 디렉터리에서 test를 확인한다.

완료 여부는 fixes checklist만으로 판단하지 않는다.

다음 근거를 함께 확인해야 한다.

```text
Approved Fixes checklist
실제 code 및 test diff
verification command 결과
Antigravity 재검토 결과
```

## Optional Improvements

### 동시 embedding API 호출 완전 방지

Atomic upsert는 unique constraint race로 인한 DB failure를 방지하지만, 두 worker가 동시에 기존 row를 조회하면 embedding API가 중복 호출될 수 있다.

향후 daily pipeline에서 병렬 worker를 사용할 경우 다음 방식을 검토할 수 있다.

- PostgreSQL advisory lock
- processing status row
- `SELECT ... FOR UPDATE`
- queue deduplication key
- distributed lock
- embedding job의 idempotency token

현재 수동 소량 batch MVP에서는 필수 범위가 아니다.

### `.env` 자동 로드

독립 script가 `.env`를 자동으로 읽지 않으므로 실행 전에 shell environment에 변수를 주입해야 한다.

현재 명시적 환경변수 주입 방식은 정상 동작하며 필수 수정은 아니다.

공통 configuration loader가 필요해지는 시점에 별도 작업으로 검토한다.

### ANN vector index

현재 row 수에서는 exact cosine similarity로 충분하다.

실제 데이터 규모와 query latency를 측정한 후 HNSW 또는 IVFFlat 도입을 검토한다.

### Batch API 및 bulk upsert

Daily pipeline의 실제 처리량을 확인한 뒤 OpenAI batch embedding과 DB bulk write를 검토한다.

## Suggested Test Commands

### Atomic upsert 관련 테스트

```bash
python -m unittest \
  tests.test_article_embedding_storage \
  tests.test_article_embeddings
```

### Migration path 독립성

Repository root:

```bash
python -m unittest tests.test_article_embedding_migration
```

Repository root 외부:

```bash
cd /tmp
PYTHONPATH=/Users/seochanjin/workspace/NewsLab/news-lab \
python -m unittest \
  tests.test_article_embedding_migration
```

### Markdown fence 확인

```bash
rg -n '^`{3,}$' \
  docs/fixes/feature-article-embedding-storage-approved-fixes.md
```

### 전체 회귀 테스트

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

### 운영 E2E 재사용 확인

```bash
source .venv/bin/activate
set -a
source .env
set +a

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

## Risk Notes

CR-1은 현재 수동 단일 실행에서는 재현 가능성이 낮지만, 향후 CronJob 또는 병렬 worker 환경에서는 간헐적인 unique constraint failure로 이어질 수 있다.

현재 unique constraint는 데이터 무결성을 보호하지만 application 수준의 작업 성공까지 보장하지는 않는다.

Atomic upsert를 적용하면 다음 위험을 줄일 수 있다.

```text
동시 insert unique violation
부분 batch failure
재시도 시 불필요한 오류 처리
daily pipeline 병렬화 시 간헐적 실패
```

CR-2는 runtime 기능에 영향을 주지 않지만 review artifact 렌더링과 문서 구조를 깨뜨릴 수 있다.

CR-3은 repository root에서는 드러나지 않지만 CI, IDE 또는 다른 작업 디렉터리에서 test 신뢰성을 떨어뜨릴 수 있다.

수정 범위는 embedding 저장 SQL, 관련 test와 fixes 문서에 한정해야 한다.

다음 영역은 변경하지 않는다.

```text
Daily pipeline
CronJob
K3s manifest
Frontend
Public API
기존 raw SQL 전체 ORM 전환
ANN vector index
embedding_runs table
```
