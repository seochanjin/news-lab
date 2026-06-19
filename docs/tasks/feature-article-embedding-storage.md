# Task: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Goal

Supabase PostgreSQL의 pgvector를 사용해 기사 embedding을 저장하고 재사용하는 MVP를 구현한다.

초기 embedding 입력은 기사 제목과 RSS 요약을 사용한다. 실제 요약 컬럼명은 현재 schema와 코드를 조사해 확정한다.

처리 흐름:

```text
기사 조회
→ 입력 텍스트 정규화
→ SHA-256 hash 생성
→ 기존 embedding 조회
→ hash가 같으면 재사용
→ 없거나 변경됐으면 embedding 생성
→ dimension 검증
→ article_embeddings 저장 또는 갱신
```

동일한 기사·모델·입력 유형·입력 내용에 대해서는 embedding API를 다시 호출하지 않아야 한다.

## Scope

### 조사

구현 전에 다음을 실제 repository 기준으로 확인한다.

- `articles` table schema와 ID type
- 제목 및 RSS 요약 컬럼명
- 현재 migration 작성 방식
- 현재 SQLAlchemy 및 PostgreSQL driver
- 현재 AI provider와 설정 구조
- 사용 가능한 embedding model과 dimension
- 기존 embedding 관련 코드 또는 dependency
- 현재 테스트 구조

조사 결과가 task의 예시와 다르면 실제 repository 구조를 우선한다.

### DB

Version-controlled migration을 작성한다.

포함할 내용:

- Supabase `vector` extension 활성화
- `article_embeddings` table 생성
- `articles(id)` foreign key
- `ON DELETE CASCADE`
- embedding vector column
- provider, model, dimension
- source text type
- source text hash
- timestamp
- 모델과 입력 유형별 최신 embedding 하나를 유지하기 위한 unique constraint

초기 저장 정책:

```text
기존 row 없음
→ 생성 후 insert

기존 row 있음 + hash 동일
→ API 미호출, 재사용

기존 row 있음 + hash 변경
→ 재생성 후 update

model 또는 source type 변경
→ 별도 row 생성
```

HNSW 또는 IVFFlat index는 이번 범위에서 추가하지 않는다.

### Application

다음을 구현한다.

- 제목과 요약 기반 embedding 입력 텍스트 생성
- 공백 및 줄바꿈 정규화
- UTF-8 SHA-256 hash 계산
- embedding provider 호출 코드 분리
- fake client를 사용할 수 있는 테스트 경계
- 기존 embedding 조회
- 생성, 갱신, 재사용 판정
- vector dimension 검증
- bind parameter 기반 SQL
- 처리 결과 반환

처리 상태:

```text
created
updated
reused
failed
```

### Batch script

소량 기사를 독립적으로 처리할 script를 구현한다.

필수 옵션:

```text
--limit
--article-id
--dry-run
```

기본 실행은 소량으로 제한한다.

결과에는 다음 집계를 포함한다.

```text
selected
created
updated
reused
failed
```

`--dry-run`에서는 embedding API 호출과 DB write를 수행하지 않는다.

### Similarity verification

저장된 embedding을 cosine similarity로 조회할 수 있는 내부 함수 또는 CLI 검증 경로를 구현한다.

Public API endpoint는 추가하지 않는다.

비교 대상은 같은 provider, model, dimension과 source text type으로 제한한다.

### Tests

최소한 다음을 검증한다.

- 입력 텍스트 정규화
- 동일 입력의 동일 hash
- 제목 또는 요약 변경 시 hash 변경
- 요약이 없는 경우
- 동일 hash일 때 provider 미호출
- 신규 embedding 생성
- 입력 변경 시 embedding 갱신
- model 변경 시 별도 row 생성
- dimension 불일치 시 저장 중단
- batch 집계
- cosine similarity 조회

가능하면 별도 테스트 DB에서 insert, update, unique constraint와 cascade delete를 검증한다.

운영 Supabase DB를 자동 테스트 대상으로 사용하지 않는다.

### Documentation

다음을 갱신한다.

- `docs/architecture/database.md`
- `docs/architecture/pipeline.md`
- 관련 runbook
- verification
- devlog
- PR draft

설계 대안과 선택 이유를 devlog에 기록한다.

## Do not change

- 기존 raw SQL 전체를 ORM으로 전환하지 않는다.
- 기존 SQL 전면 리팩터링을 하지 않는다.
- Public API contract를 변경하지 않는다.
- Daily topic pipeline에 연결하지 않는다.
- CronJob과 K3s manifest를 변경하지 않는다.
- K3s PV/PVC 또는 별도 vector DB를 추가하지 않는다.
- ANN vector index를 추가하지 않는다.
- 모든 기존 기사를 일괄 처리하지 않는다.
- 별도 `embedding_runs` table을 추가하지 않는다.
- Topic clustering을 변경하지 않는다.
- Frontend를 변경하지 않는다.
- Secret, 환경 파일 또는 kubeconfig를 읽거나 수정하지 않는다.
- Supabase 운영 migration을 agent가 실행하지 않는다.
- 운영 article 데이터를 수정하거나 삭제하지 않는다.
- `git push`, merge 또는 PR merge를 수행하지 않는다.

## Expected files

실제 repository 구조를 우선한다.

예상 변경 영역:

```text
db/migrations/
app/
scripts/embed_articles.py
tests/
docs/architecture/database.md
docs/architecture/pipeline.md
docs/runbooks/
docs/verification/
docs/pr/
docs/devlog/
```

새로운 `services`, `repositories`, `clients` 계층을 기존 구조와 맞지 않는데도 강제로 만들지 않는다.

필요한 dependency는 최소 범위에서 추가할 수 있으며 추가 이유와 runtime 영향을 기록한다.

## DB changes

- `vector` extension
- `article_embeddings` table
- article foreign key
- model/source type 기반 unique constraint
- vector dimension은 확정한 embedding model과 일치

Migration은 repository에 작성하되 운영 Supabase 적용은 사람이 수행한다.

Codex는 다음을 제공한다.

- migration file
- 적용 전 확인 사항
- 적용 후 schema 확인 SQL
- 실패 시 중단 기준
- rollback 또는 복구 방향

## API changes

Public API 변경 없음.

Similarity search는 내부 repository, service 또는 CLI에서만 검증한다.

Public endpoint가 필요하다고 판단되면 구현하지 말고 별도 제안으로 남긴다.

## Test commands

Repository의 기존 command를 우선한다.

최소 확인:

```bash
python -m compileall app scripts tests
pytest
python scripts/embed_articles.py --help
python scripts/embed_articles.py --limit 3 --dry-run
git diff --check
git diff --name-only
git diff --stat
```

실제 실행한 command와 결과는 verification에 기록한다.

## Acceptance criteria

- [x] 실제 article schema, ID type, 요약 컬럼과 DB driver를 확인했다.
- [x] embedding provider, model과 dimension을 확정했다.
- [x] pgvector migration을 작성했다.
- [x] `article_embeddings` table과 constraint를 작성했다.
- [x] 입력 텍스트 정규화와 SHA-256 hash를 구현했다.
- [x] embedding provider와 DB 저장 로직을 분리했다.
- [x] fake embedding client로 테스트할 수 있다.
- [x] 같은 hash는 provider 호출 없이 재사용한다.
- [x] hash 변경 시 기존 row를 갱신한다.
- [x] model 또는 source type 변경 시 별도 row를 생성한다.
- [x] dimension 불일치 vector는 저장하지 않는다.
- [x] 신규 SQL의 runtime 값은 bind parameter를 사용한다.
- [x] 소량 batch script와 dry-run을 구현했다.
- [x] created, updated, reused, failed 집계를 제공한다.
- [x] cosine similarity 조회를 구현했다.
- [ ] 단위 테스트와 가능한 DB 통합 테스트가 통과했다.
  - 단위 테스트 136건은 통과했다.
  - `pytest`는 현재 환경에 설치되지 않아 실패했다.
  - 별도 PostgreSQL/pgvector test DB가 없어 통합 테스트는 환경 제약으로
    미수행이다.
- [x] Architecture, runbook, verification과 devlog를 갱신했다.
- [x] Daily pipeline, CronJob, K3s와 frontend를 변경하지 않았다.
- [x] Agent가 운영 Supabase migration을 실행하지 않았다.
- [x] 실제 credential을 기록하지 않았다.

## Human-controlled steps

다음은 사람이 수행한다.

- [ ] Codex 구현 결과와 migration SQL을 검토한다.
- [ ] Antigravity review 후 적용할 항목만 Approved Fixes로 승인한다.
- [ ] 승인 수정 적용 후 재검토한다.
- [ ] Supabase 운영 DB에 migration을 적용한다.
- [ ] 적용 후 extension, table과 constraint를 확인한다.
- [ ] 실제 기사 3건 정도로 batch를 실행한다.
- [ ] 같은 batch를 다시 실행해 `reused`를 확인한다.
- [ ] cosine similarity 조회 결과를 확인한다.
- [ ] 최종 diff와 verification 확인 후 push와 PR을 진행한다.

운영 article의 제목이나 요약을 테스트 목적으로 수정하지 않는다.

Hash 변경 update는 test fixture 또는 별도 테스트 환경에서 확인한다.

## Notes

- Supabase PostgreSQL을 embedding 저장소로 사용한다.
- 초기 입력 유형은 `title_summary`다.
- 실제 요약 컬럼명은 조사 후 확정한다.
- `article_embeddings`에는 성공한 최신 embedding만 저장한다.
- 실행 이력 table은 daily pipeline 분리 시 다시 검토한다.
- Vector index는 실제 데이터와 query latency를 확인한 뒤 후속 작업에서 검토한다.
- 기존 SQL 전면 정리는 별도 refactoring task로 유지한다.
- 작업은 WIP 1로 진행한다.

```text
조사
→ 변경
→ 문서화
→ 검증
→ verification 기록
→ checklist 갱신
```
