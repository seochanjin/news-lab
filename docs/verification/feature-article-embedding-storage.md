# Verification: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Verification Scope

- Repository 기준 article schema와 embedding 관련 구조 조사
- pgvector migration 정적 검증
- 입력 정규화, hash, 생성·갱신·재사용, dimension 검증 단위 테스트
- 호환 조건을 적용한 cosine similarity SQL 단위 테스트

## Commands Run

Command:
`pytest -q tests/test_article_embedding_storage.py tests/test_article_embedding_migration.py tests/test_article_embeddings.py`

Result:
`pytest` executable을 찾지 못해 exit code 127로 실패했다.

Status: failed

Notes:
현재 shell과 `.venv` 모두 pytest가 설치되어 있지 않다.

Command:
`ls -l .venv/bin/pytest .venv/bin/python 2>/dev/null || true; python --version; .venv/bin/python -m pytest -q tests/test_article_embedding_storage.py tests/test_article_embedding_migration.py tests/test_article_embeddings.py`

Result:
Python 3.11.7을 확인했다. `.venv/bin/python`에는 pytest module이 없어 exit
code 1로 실패했다.

Status: failed

Notes:
Dependency 설치는 수행하지 않았다.

Command:
`python -m unittest tests.test_article_embedding_storage tests.test_article_embedding_migration tests.test_article_embeddings`

Result:
16 tests가 통과했다.

Status: passed

Notes:
정규화, hash, 요약 없음, provider 미호출 재사용, insert, update, model별 lookup,
dimension 불일치 저장 중단, cosine similarity query, migration 계약과 기존 provider
테스트를 포함한다.

Command:
`python -m unittest tests.test_embed_articles tests.test_article_embedding_storage tests.test_article_embedding_migration tests.test_article_embeddings`

Result:
20 tests가 통과했다.

Status: passed

Notes:
Batch option parsing, bind parameter article 선택, 상태 집계, dry-run provider/write
미호출 검증을 추가로 포함한다.

Command:
`python scripts/embed_articles.py --help`

Result:
`--limit`, 반복 가능한 `--article-id`, `--dry-run` option과 기본 limit 10, 최대
limit 100이 출력되었다.

Status: passed

Command:
`python scripts/embed_articles.py --limit 3 --dry-run`

Result:
`DATABASE_URL environment variable is not set`으로 exit code 1이었다.

Status: failed

Notes:
Credential이나 `.env`를 읽지 않는 현재 agent 환경에는 DB 연결 정보가 없다.
Script는 provider 호출 또는 DB write 전에 중단되었다. 실제 configured test
environment에서 read-only selection dry-run 확인이 필요하다.

Command:
`python -m compileall app scripts tests`

Result:
Exit code 0으로 완료되었다.

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
135 tests가 통과했다.

Status: passed

Notes:
기존 argument validation test의 예상 argparse error output이 포함되지만 test
runner 최종 결과는 `OK`다.

Command:
`git diff --check`

Result:
출력 없이 exit code 0이었다.

Status: passed

Notes:
Git이 추적 중인 변경 file에 whitespace error가 없음을 확인했다. 신규 untracked
file은 `git status --short --branch`로 별도 확인했다.

Command:
`git diff --name-only`

Result:
`docs/architecture/database.md`, `docs/architecture/pipeline.md`,
`docs/runbooks/database-check.md`가 출력되었다.

Status: passed

Notes:
Git command 특성상 신규 untracked file은 포함하지 않는다.

Command:
`git diff --stat`

Result:
추적 중인 architecture/runbook 3개 file에서 135 insertions, 1 deletion을
확인했다.

Status: passed

Command:
`git status --short --branch`

Result:
현재 branch가 `feature/article-embedding-storage`임을 확인했다. 구현 file,
migration, task workflow 문서와 test file은 신규 untracked 상태이며 기존
architecture/runbook 3개 file은 modified 상태다.

Status: passed

Command:
`python -m compileall app scripts tests; python -m unittest discover -s tests; git diff --check; git diff --name-only; git diff --stat; git status --short --branch`

Result:
Compileall과 diff check가 exit code 0으로 완료되었고 전체 136 tests가 통과했다.
Tracked diff는 architecture/runbook 3개 file, 신규 구현·test·workflow file은
untracked 상태로 재확인했다.

Status: passed

Command:
`rg -n '[[:blank:]]+$' <task 관련 변경 file>; git diff --check; git status --short --branch`

Result:
변경 file의 trailing whitespace 검색과 `git diff --check`는 출력 없이
완료되었다. Branch와 working tree 상태는 직전 결과와 동일했다.

Status: passed

## Results

- `articles.id`는 기존 migration의 foreign key 기준 `bigint`다.
- RSS 요약 컬럼은 기존 query 기준 `articles.summary`다.
- DB 접근은 SQLAlchemy `text()`와 psycopg3를 사용한다.
- 저장 모델은 기존 기본값 `text-embedding-3-small`, provider는 `openai`,
  dimension은 1536, source text type은 `title_summary`로 확정했다.
- 신규 runtime SQL 값은 bind parameter를 사용한다.
- migration은 HNSW/IVFFlat index를 포함하지 않는다.

## Manual or Production Verification

- Supabase migration 적용: 사람이 수행 필요
- 실제 Supabase extension, table, constraint 확인: 운영 반영 후 확인 필요
- 실제 OpenAI embedding 생성과 DB insert/update/reuse: 사람이 수행 필요

## Pending Verification

- Configured test DB를 사용한 batch read-only dry-run
- 별도 PostgreSQL/pgvector test DB 통합 테스트: 환경 제약으로 미수행

## Evidence Notes

- OpenAI 공식 embeddings guide는 `text-embedding-3-small`의 기본 vector 길이를
  1536으로 명시한다.
- Secret, `.env`, kubeconfig와 실제 credential 값은 읽거나 수정하지 않았다.

## Production pgvector Verification

### Vector dimension 확인

Supabase SQL Editor에서 저장된 embedding의 실제 차원과 기록된 dimension을 확인했다.

결과:

| article_id | actual_dimension | recorded_dimension |
| ---------: | ---------------: | -----------------: |
|       2685 |             1536 |               1536 |
|       2686 |             1536 |               1536 |
|       2687 |             1536 |               1536 |

상태: 통과

저장된 pgvector의 실제 차원과 application metadata가 모두 일치했다.

### Cosine similarity 확인

Article `2687`의 embedding을 기준 vector로 사용해 cosine similarity query를 실행했다.

결과:

| query_article_id | article_id |        similarity |
| ---------------: | ---------: | ----------------: |
|             2687 |       2687 |               1.0 |
|             2687 |       2685 | 0.294441283666331 |
|             2687 |       2686 | 0.266297983343077 |

상태: 통과

확인 내용:

- 기준 기사 자신이 첫 번째 결과로 반환됐다.
- 자기 자신의 similarity는 `1.0`이었다.
- 나머지 기사는 더 낮은 similarity로 반환됐다.
- 결과가 cosine similarity 내림차순으로 정렬됐다.
- 실제 Supabase pgvector의 `<=>` 연산이 정상 동작했다.

### Production E2E 최종 결과

- dry-run: 통과
- 최초 embedding 생성 3건: 통과
- 동일 batch 재실행 시 재사용 3건: 통과
- vector dimension 검증: 통과
- cosine similarity query: 통과
- failed: 0
