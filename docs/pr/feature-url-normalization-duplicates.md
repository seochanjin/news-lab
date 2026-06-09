# URL 정규화와 중복 후보 분석 MVP

## 작업 내용

- multi-source article metadata에 적용할 deterministic URL/title
  normalization helper를 추가했습니다.
- 현재 DB의 `articles` 데이터를 읽기 전용으로 조회해 normalized URL과
  title hash 기준 중복 후보를 분석하는 dry-run script를 추가했습니다.
- 발행 시각 기준 제품 분석과 수집 시각 기준 운영 분석을 분리하고,
  24h/72h/168h/전체 범위 분석을 지원하도록 했습니다.
- normalization 규칙과 duplicate candidate 집계 동작을 확인하는 단위
  테스트를 추가했습니다.

## 주요 변경 사항

- URL scheme/host를 소문자화하고 default port, fragment, host trailing
  dot, root 외 trailing slash를 제거합니다.
- path case, percent encoding, 비추적 query 값은 보존해 의미가 달라질 수
  있는 과도한 정규화를 피합니다.
- `utm_*`, `fbclid`, `gclid`, `at_medium`, `at_campaign`,
  `traffic_source` 등 공통 tracking parameter를 제거합니다.
- BBC, DW, TechCrunch, The Guardian, Wired 등 현재 source domain의 명시적
  tracking parameter rule을 적용합니다.
- 제목은 NFKC, casefold, punctuation/whitespace 정규화 후 SHA-256
  `title_hash`를 생성합니다.
- 분석 script는 24h/72h/168h/전체 범위와 published/created time basis를
  지원하고, DB transaction을 read-only로 설정합니다.
- 기본 제품 기준은 `coalesce(published_at, created_at)`이며,
  `--time-basis created`를 사용하면 `created_at` 기준 운영 분석을
  수행합니다.
- 후보 그룹과 분석 요약을 JSON으로 출력하며, `--max-groups`로 출력할
  상세 후보 그룹 수를 제한할 수 있습니다.

## 추가/변경된 API

- 추가되거나 변경된 API는 없습니다.
- 기존 `/articles`, `/collector/status`, `/collector/runs` 응답 구조도
  변경하지 않았습니다.
- 중복 후보 분석은 API가 아닌
  `scripts/analyze_article_duplicates.py`를 통해 수행합니다.

## DB 변경 사항

- DB schema 변경 및 migration 파일 추가는 없습니다.
- Supabase SQL 및 DB migration을 실행하지 않았습니다.
- 분석 script는 `set transaction read only`를 실행한 뒤 현재
  `articles`/`sources` 데이터를 SELECT하며, article row를 수정하지
  않습니다.
- 후속 차수에서 `normalized_url`, `title_hash`,
  `duplicate_of_article_id` column과 index 정책을 검토할 예정입니다.
  현재 단계에서는 unique constraint를 추가하지 않습니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 이번 변경은 내부 normalization helper와 수동 dry-run 분석 script
  추가이며, 기존 서비스 실행 방법과 공개 API 사용 방법은 동일합니다.

## 테스트

- `.venv/bin/python -m unittest tests/test_url_normalization.py -v`: 통과
- `.venv/bin/python -m unittest discover -s tests -v`: 9개 테스트 통과
- `.venv/bin/python -m py_compile app/utils/url_normalization.py scripts/analyze_article_duplicates.py tests/test_url_normalization.py tests/test_analyze_article_duplicates.py`:
  통과
- `.venv/bin/python scripts/analyze_article_duplicates.py --help`: 통과
- `git diff --check`: 통과
- published 기준 24h/72h/168h/전체 DB read-only dry-run: 통과
- created 기준 24h DB read-only dry-run: 통과
- `pytest`: `.venv/bin/pytest`가 설치되어 있지 않아 pending
- 상세 실행 기록은
  `docs/verification/feature-url-normalization-duplicates.md`를 참조합니다.

## 확인 결과

- published 기준:
  - 24h 180건: normalized URL/title hash 후보 없음
  - 72h 254건: normalized URL/title hash 후보 없음
  - 168h 347건: normalized URL 후보 없음, title hash 1그룹/2건
  - 전체 376건: normalized URL 후보 없음, title hash 2그룹/4건
- created 기준 최근 24h 293건에서는 두 후보 유형 모두 없었습니다.
- 성공한 모든 DB 분석에서 invalid/missing URL과 title은 각각 0건으로
  확인됐습니다.
- `git diff -- k8s` 결과 K8s manifest 변경은 없었습니다.
- 보안 문자열 검사에서 실제 credential 값은 발견되지 않았습니다.

## 비고

- DB schema, API, collector/extractor, frontend, K8s manifest는 변경하지
  않았습니다.
- LLM, embedding, topic grouping, AI summary는 구현하지 않았습니다.
- 승인된 필수 review fix는 없으며 fixes 단계의 추가 코드 변경도
  없습니다.
- all-time title hash 후보 2그룹의 실제 중복 여부 확인과 추가 데이터
  누적 후 dry-run 재실행은 pending입니다.
- migration, rollout, production verification, push, merge는 수행하지
  않았습니다.
