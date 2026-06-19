# Antigravity Review: Supabase pgvector 기반 article embedding 저장·재사용 MVP

## Review Summary

본 변경 사항은 `feature/article-embedding-storage` 브랜치에 대응하여 Supabase PostgreSQL의 `vector` 익스텐션을 활성화하고, 기사(`articles`)의 제목 및 요약을 임베딩하여 효율적으로 저장하고 재사용하는 MVP 기능을 제공하기 위해 수행되었습니다.

- **데이터베이스 모델**: `article_embeddings` 테이블 마이그레이션 파일이 구축되었고, OpenAI `text-embedding-3-small` 임베딩에 맞추어 `1536` 차원의 pgvector 타입 컬럼이 설계되었습니다.
- **애플리케이션 로직**: 화이트스페이스 정규화 및 SHA-256 해시를 이용한 효율적인 변경 감지(Change Detection) 로직이 도입되었으며, 동일한 데이터에 대한 임베딩 생성 시 저장된 기존 벡터를 재사용하도록 설계되었습니다.
- **배치 처리**: `--limit`, 반복 가능한 `--article-id`, `--dry-run` 옵션을 지원하는 독립 실행형 `scripts/embed_articles.py` 스크립트가 구현되어 수동 소량 배치 처리가 안정적으로 가능해졌습니다.

전반적인 설계 구조와 구현 수준은 요구사항의 기능적 무결성을 엄격하게 준수하며, 운영 안전 가이드라인에 완전히 부합합니다.

## Requirement Coverage

[docs/tasks/feature-article-embedding-storage.md](~/news-lab/docs/tasks/feature-article-embedding-storage.md)에 명시된 요구사항 및 인수 조건(Acceptance criteria)을 모두 해결하였습니다.

- **DB 스키마 구성**:
  - `vector` 익스텐션의 비침습적인 활성화와 cascade delete 규칙을 지정한 `article_embeddings` 테이블 설계가 [db/migrations/006_create_article_embeddings.sql](~/news-lab/db/migrations/006_create_article_embeddings.sql)에 올바르게 작성되었습니다.
- **임베딩 재사용 및 갱신**:
  - 입력 값의 공백 정규화 및 UTF-8 SHA-256 해시 비교 로직을 통해 해시가 동일한 경우 임베딩 API를 재호출하지 않고 저장된 레코드를 재사용(`reused`)하며, 해시가 변경된 경우 갱신(`updated`), 새로운 조합일 경우 신규 생성(`created`)이 정확히 작동합니다.
  - 벡터 차원(dimension = 1536)을 검증하여 불일치할 시 예외를 발생시키고 처리를 중단하는 가드 조건이 적용되었습니다.
- **수동 배치 스크립트**:
  - `scripts/embed_articles.py`가 `--limit` (기본 10, 최대 100 제한), `--article-id`, `--dry-run` 옵션을 완벽히 지원하며, 각 상태에 따른 집계 결과를 JSON 형태로 출력합니다.
- **유사도 조회**:
  - pgvector의 `<=>` (cosine distance) 연산자를 사용해 동일한 모델/유형의 임베딩 간 코사인 유사도를 연산하는 코사인 유사도 검색 메서드가 구현되었습니다.

## Code Quality / Maintainability

- **가독성 및 모듈화**: 핵심 임베딩 조회/저장 로직이 [app/utils/article_embedding_storage.py](~/news-lab/app/utils/article_embedding_storage.py)에 잘 구조화되었고, 예외 처리와 트랜잭션 범위가 안전하게 격리되었습니다.
- **의존성 주입 및 테스트 용이성**: `FakeConnection` 및 `FakeProvider`를 이용해 실제 데이터베이스 커넥션이나 OpenAI API key 연결 없이도 임베딩 캐싱 및 갱신 상태(insert, update, reuse 등)의 비즈니스 로직을 완벽하게 검증하는 모의 테스트(Mock Test) 코드가 우수하게 구현되었습니다.
- **바인드 파라미터**: 새로 도입된 모든 SQL 쿼리(FIND, INSERT, UPDATE, SIMILARITY)가 SQLAlchemy `text()` 객체 및 명시적인 바인드 파라미터를 사용하여 SQL injection 위험이 사전에 방지되었습니다.

## Security Review

- **인증 정보 노출 없음**: 소스코드나 구성 문서 내에 `OPENAI_EMBEDDING_API_KEY`, `DATABASE_URL` 같은 비밀 정보가 하드코딩되지 않고 안전하게 `os.getenv`를 통해 처리됩니다.
- **안전한 플레이스홀더 사용**: 마이그레이션 가이드라인이나 테스트 문서 내에서도 구조 설명용 변수명이나 플레이스홀더 외에 실제 유출될 위험이 있는 민감 정보는 전혀 존재하지 않습니다.

## Operational Risk

- **배치 실행량 강제 제한**: `scripts/embed_articles.py` 스크립트에서 배치 실행 시 발생할 수 있는 대량의 API 호출 및 DB 쓰기 부하를 방지하기 위해 `--limit` 최대 크기를 100으로 제한하여 안정 장치를 걸어두었습니다.
- **마이그레이션 제어 분리**: 에이전트가 데이터베이스에 마이그레이션을 자동 실행하지 않도록 분리하고, 런북([docs/runbooks/database-check.md](~/news-lab/docs/runbooks/database-check.md))에 휴먼 오퍼레이터가 점검해야 할 사전 조건, 사후 조회 쿼리, 롤백을 위한 `drop table` SQL 구문을 상세히 포함시켰습니다.

## Scope Control

- **변경 영역 격리**: 요구사항 범위를 넘어서는 변경이 전혀 발생하지 않았습니다. 수정된 파일은 오직 `docs/architecture/database.md`, `docs/architecture/pipeline.md`, `docs/runbooks/database-check.md`이며, 그 외의 어플리케이션 메인 라우터 코드, 다른 크론잡 매니페스트, 프론트엔드 레포지토리는 수정되지 않고 고유 상태를 유지하고 있습니다.

## Verification Review

- **단위 테스트 무결성**: [docs/verification/feature-article-embedding-storage.md](~/news-lab/docs/verification/feature-article-embedding-storage.md)에 정적 컴파일(`compileall`), 전체 136건의 단위 테스트(`unittest discover`), 드라이런 실행 확인 등에 대한 명확한 실행 명령어와 실행 상태 결과가 상세하게 증적(evidence)으로 기록되어 있어 결과 신뢰도가 매우 높습니다.
- **예외 사항 기록**: 환경 제약으로 인해 설치되지 않은 `pytest` 대신 표준 모듈인 `unittest`를 활용하여 테스트를 우회 수행한 점과 실제 원격 DB가 필요한 E2E/통합 테스트 영역은 '사람이 수행 필요' 상태로 솔직하고 구체적이게 남겨둔 검증 무결성을 칭찬합니다.

## Documentation Review

- **문서 갱신 정합성**: [docs/architecture/database.md](~/news-lab/docs/architecture/database.md) 및 [docs/architecture/pipeline.md](~/news-lab/docs/architecture/pipeline.md)에 `article_embeddings` 테이블의 연관 관계와 배치 임베딩의 흐름이 최신으로 정비되었으며, [docs/runbooks/database-check.md](~/news-lab/docs/runbooks/database-check.md)에도 프로덕션 적용/검증 가이드라인이 명료한 한국어로 기재되어 가독성이 뛰어납니다.

## Problems Found

- **결함 사항 없음**: 정적 분석 결과와 코드 구현 정합성 및 테스트의 정상 동작 유무를 전반적으로 분석하였을 때, 본 브랜치 내에 구현된 코드 및 문서에는 설계 규칙을 위반하거나 오동작을 일으킬 가능성이 있는 결함이 발견되지 않았습니다.

## Required Fixes Before PR

- **해당 사항 없음** (PR 병합 절차를 진행하기 전 반드시 수정되어야 할 블로커 요소는 없습니다).

## Optional Improvements

- **대용량 배치 성능 고려**: 향후 배치 처리 기사 개수가 늘어날 경우, 단일 `store_article_embedding`을 루프 내에서 순차 트랜잭션으로 처리하는 현 구조에서 OpenAI batch embedding API 및 DB bulk insert/update 방식을 결합 적용하는 방식(Bulk Processing)으로 성능 개선을 고안해볼 수 있습니다. 다만, 현 시점의 소량 MVP 범위에서는 현재 구현으로도 충분합니다.

## Suggested Test Commands

본 브랜치의 검증 동작을 다시 확인하려면 아래의 읽기 전용 커맨드들을 검토해 볼 수 있습니다:

1. **정적 분석 및 전체 단위 테스트 실행**:
   ```bash
   python -m compileall app scripts tests && python -m unittest discover -s tests
   ```
2. **도움말 및 배치 스크립트 드라이런 문법 검증**:
   ```bash
   python scripts/embed_articles.py --help
   python scripts/embed_articles.py --limit 3 --dry-run
   ```
3. **변경 포맷 정합성 확인**:
   ```bash
   git diff --check
   ```

## Verdict

- **APPROVED**
  - 본 MVP 설계 및 구현 결과는 요구사항에 명시된 범위에 일치하며, 테스트 및 문서화의 질적 수준이 매우 우수하여 추가 수정 없이 PR 등록 및 검토를 진행하기에 적절합니다.

## Re-review 1

### Existing Problems Status

- **최초 리뷰 상의 문제점**: 최초 리뷰 시 발견된 결함 및 문제점 없음 (해결됨).

### Approved Fixes Verification

- **Approved Fixes**: [docs/fixes/feature-article-embedding-storage-approved-fixes.md](~/news-lab/docs/fixes/feature-article-embedding-storage-approved-fixes.md) 문서상에 승인된 수정 사항이 존재하지 않으며, 기존 구현이 요구 조건을 모두 완전히 만족합니다 (해결됨).

### Verification Evidence

`git status --short`에 표시된 모든 변경(modified/untracked) 파일 및 핵심 코드를 실제 분석 및 실행하여 교차 검증하였습니다.

- **검토 대상 핵심 파일**:
  - 데이터베이스 마이그레이션: [db/migrations/006_create_article_embeddings.sql](~/news-lab/db/migrations/006_create_article_embeddings.sql)
  - 코어 비즈니스 로직: [app/utils/article_embedding_storage.py](~/news-lab/app/utils/article_embedding_storage.py)
  - 배치 처리 CLI 스크립트: [scripts/embed_articles.py](~/news-lab/scripts/embed_articles.py)
  - 신규 단위 테스트 코드: [tests/test_article_embedding_migration.py](~/news-lab/tests/test_article_embedding_migration.py), [tests/test_article_embedding_storage.py](~/news-lab/tests/test_article_embedding_storage.py), [tests/test_embed_articles.py](~/news-lab/tests/test_embed_articles.py)
  - 작업 전후 요구사항 및 검증 데이터: [docs/tasks/feature-article-embedding-storage.md](~/news-lab/docs/tasks/feature-article-embedding-storage.md), [docs/verification/feature-article-embedding-storage.md](~/news-lab/docs/verification/feature-article-embedding-storage.md)
  - 아키텍처 및 런북: [docs/architecture/database.md](~/news-lab/docs/architecture/database.md), [docs/architecture/pipeline.md](~/news-lab/docs/architecture/pipeline.md), [docs/runbooks/database-check.md](~/news-lab/docs/runbooks/database-check.md)
- **테스트 실행 결과**:
  - `python -m compileall app scripts tests && python -m unittest discover -s tests` 실행 시 총 136개의 테스트 케이스가 성공적으로 통과(`OK`)하여 무결함을 확인했습니다.

### New Problems Found

- **새로운 문제 없음**: `git status --short`에 명시된 모든 변경 사항 및 신규 추가된 테스트 코드 등 대상 범위의 전체 파일을 수동 및 컴파일 결과로 검토한 결과, 추가 오동작이나 불일치 및 요구되지 않은 파일 변경(Scope Creep)이 전혀 발견되지 않았습니다.

### Required Fixes Before PR

- **해당 사항 없음** (PR 진행을 위한 블로커 없음).

### Verdict

- **APPROVED**
