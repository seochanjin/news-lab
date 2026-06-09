# URL 정규화와 중복 후보 분석 MVP

## 작업 목적

27차에서 수집된 multi-source article metadata에 deterministic
normalization을 적용해 normalized URL과 normalized title exact-match 중복
후보의 현재 규모를 파악한다.

이번 단계에서는 중복 제거를 즉시 운영에 적용하지 않고, 향후
`normalized_url`, `title_hash`, `duplicate_of_article_id`를 DB에 반영할지
판단할 수 있는 read-only 분석 기반을 만드는 것을 목표로 했다.

## 기존 문제

- 수집 시 원본 URL에 대해서만 unique conflict를 처리하므로 tracking
  query나 표현 차이가 있는 동일 URL을 식별할 근거가 없었다.
- title 기반 후보를 일관되게 비교하는 helper와 dry-run 도구가 없었다.
- 발행 시각 기준 제품 분석과 수집 시각 기준 운영 분석이 분리되어 있지
  않았다.
- 정규화 규칙을 DB write-time deduplication에 바로 적용하면 false
  positive나 multi-source 원문 손실 가능성을 사전에 확인하기 어려웠다.

## 변경 내용

- `app/utils/url_normalization.py`
  - URL normalization, title normalization, SHA-256 title hash helper 추가
  - 공통 tracking parameter와 현재 source domain별 제거 규칙 정의
- `scripts/analyze_article_duplicates.py`
  - 현재 `articles`와 `sources`를 조회하는 read-only duplicate candidate
    분석 script 추가
  - 24h/72h/168h/전체 범위 및 published/created time basis 지원
  - normalized URL과 title hash 후보 그룹 및 집계 결과를 JSON으로 출력
- `tests/`
  - URL/title normalization과 duplicate candidate 집계 동작을 확인하는
    단위 테스트 추가
- workflow 문서
  - 실제 분석 결과, 후속 DB 정책, PR/devlog 초안 기록

API, DB schema, collector/extractor, frontend, K8s manifest는 변경하지
않았다.

## 구현 상세

### URL normalization

- `http`/`https` URL만 처리하고 credential userinfo가 포함되거나
  파싱할 수 없는 URL은 정규화 불가로 처리한다.
- scheme/host를 소문자화하고 host trailing dot, default port,
  fragment를 제거한다.
- 빈 path는 `/`로 만들고 root 외 trailing slash를 제거한다.
- path case, percent encoding, 비추적 query 값은 보존한다.
- `utm_*`, `fbclid`, `gclid`, `at_medium`, `at_campaign`,
  `traffic_source` 등 공통 tracking parameter를 제거한다.
- BBC, DW, TechCrunch, The Guardian, Wired 등 현재 source domain에
  명시적인 tracking parameter 규칙을 적용한다.
- 남은 query parameter는 deterministic 비교가 가능하도록 정렬한다.

### Title normalization

- Unicode NFKC와 casefold를 적용한다.
- punctuation을 공백으로 바꾸고 연속 whitespace를 정리한다.
- normalized title의 SHA-256 digest를 `title_hash` 후보 값으로 생성한다.

### Duplicate analysis

- DB 연결 후 `set transaction read only`를 실행하고 SELECT만 수행한다.
- 기본 제품 기준 timestamp는 `coalesce(published_at, created_at)`이다.
- `--time-basis created`를 사용하면 collection/operation 기준인
  `created_at`만 사용한다.
- `--window-hours`는 24, 72, 168만 허용하며 `--all`로 전체 데이터를
  분석할 수 있다.
- normalized URL과 title hash exact-match 그룹만 후보로 출력한다.
- `--max-groups`로 상세 후보 출력량을 제한할 수 있다. Verification
  실행에서는 `--max-groups 0`을 사용해 기사 제목과 URL을 로그에 남기지
  않았다.

## 대안 검토

- **수집 시점에 normalized URL unique constraint 적용**
  - 즉시 중복 insert를 막을 수 있지만, 규칙 검증 전에 적용하면 서로 다른
    원문을 동일 기사로 오인하거나 multi-source 기록을 잃을 수 있어
    보류했다.
- **DB column과 backfill migration을 이번 단계에 함께 추가**
  - 쿼리와 운영 자동화에는 유리하지만, 현재 후보 규모와 collision 특성을
    먼저 확인한다는 MVP 목적에 맞지 않아 보류했다.
- **LLM, embedding, topic grouping 기반 유사도 분석**
  - 표현이 다른 관련 기사를 찾을 수 있지만 비용, 비결정성, 운영 복잡도가
    증가하며 이번 task 범위를 벗어나 제외했다.
- **title 원문 또는 normalized title을 직접 비교**
  - 디버깅에는 직관적이지만 저장/인덱싱 후보로는 고정 길이 SHA-256 hash가
    다루기 쉬워 normalized title 기반 hash를 선택했다.
- **대용량 chunk/batch 조회**
  - 전체 분석 대상이 376건인 현재 규모에서는 필요성이 낮아 보류했다.
    article 수가 수천~수만 건으로 증가하면 다시 검토한다.

## 선택한 접근과 근거

- deterministic rule과 exact-match 후보 분석을 선택했다. 동일 입력에
  동일 결과를 내므로 규칙 변경 전후의 candidate count를 비교하기 쉽다.
- URL normalization은 보수적으로 적용했다. tracking 정보는 제거하되
  path case, percent encoding, 비추적 query처럼 기사 의미에 영향을 줄 수
  있는 값은 유지했다.
- DB write보다 read-only dry-run을 먼저 선택했다. 현재 데이터에서
  collision과 title 후보 규모를 확인한 뒤 schema 및 deduplication 정책을
  결정하기 위해서다.
- 제품 분석과 운영 분석의 timestamp 기준을 분리했다. 뉴스 흐름은
  발행 시각이 적합하고, 수집량 점검은 저장 시각이 적합하기 때문이다.

## 트레이드오프

- exact-match 방식은 설명 가능성과 재현성이 높지만, 제목 표현이 조금만
  달라도 동일 기사 후보를 찾지 못한다.
- 보수적 URL normalization은 false positive 위험을 낮추지만, 제거 규칙에
  포함되지 않은 tracking parameter 때문에 일부 중복을 놓칠 수 있다.
- domain별 규칙은 현재 source에 맞게 정밀 조정할 수 있지만 source가
  늘어날 때 유지보수가 필요하다.
- 전체 데이터를 메모리에 올리는 현재 script는 수백 건 규모에는
  단순하고 충분하지만, 대규모 데이터에서는 chunk/batch 처리가 필요하다.
- title hash는 후보 생성에는 적합하지만 실제 중복 여부나 canonical
  article을 결정하지는 못한다.

## 테스트

- `.venv/bin/python -m unittest tests/test_url_normalization.py -v`: 통과
- `.venv/bin/python -m unittest discover -s tests -v`: 9개 테스트 통과
- Python compile 검증: 통과
- CLI help 검증: 통과
- `git diff --check`: 통과
- published 기준 24h/72h/168h/전체 DB read-only dry-run: 통과
- created 기준 24h DB read-only dry-run: 통과
- security grep: 실제 credential 값 없음
- `pytest`: `.venv/bin/pytest`가 설치되어 있지 않아 pending

실제 실행 명령과 상세 결과의 source of truth는
`docs/verification/feature-url-normalization-duplicates.md`다.

## 운영 반영

- 운영 반영 없음.
- DB migration 및 Supabase SQL을 실행하지 않았다.
- K8s manifest 변경, apply, rollout을 수행하지 않았다.
- production API curl과 production verification을 수행하지 않았다.
- PR merge, git push, git merge를 수행하지 않았다.
- human-provided production verification log는 없다.

## README 업데이트 판단

README는 변경하지 않았다.

이번 변경은 내부 normalization helper와 수동 dry-run 분석 script를
추가하는 작업이며 기존 FastAPI 실행 방법, 공개 API, K3s 운영 절차를
변경하지 않는다. 향후 duplicate analysis가 정식 운영 절차나 공개 기능이
되면 README 또는 Runbook에 사용 방법을 추가하는 것이 적절하다.

## 확인 결과

- published 기준:
  - 24h 180건: normalized URL/title hash 후보 없음
  - 72h 254건: normalized URL/title hash 후보 없음
  - 168h 347건: normalized URL 후보 없음, title hash 1그룹/2건
  - 전체 376건: normalized URL 후보 없음, title hash 2그룹/4건
- created 기준 최근 24h 293건: normalized URL/title hash 후보 없음
- 성공한 모든 DB 분석에서 invalid/missing URL과 title은 각각 0건이었다.
- 현재 표본에서는 URL normalization collision이 확인되지 않았다.
- title hash 후보는 실제 중복인지 human review가 필요하다.
- 승인된 필수 fix는 없었으며 fixes 단계에서 추가 코드 변경은 수행하지
  않았다.

## 이번 단계의 의미

현재 rule을 collector의 write-time deduplication에 즉시 적용하기보다,
추가 데이터에서 collision과 false positive를 관찰할 수 있는 반복 가능한
dry-run 기반을 만들었다.

또한 제품 관점의 발행 시각과 운영 관점의 수집 시각을 분리해 분석할 수
있게 하여, 향후 중복 방지 정책과 뉴스 흐름 분석 정책을 구분할 수 있는
기준을 마련했다.

## 포트폴리오용 요약

multi-source RSS로 수집된 뉴스 metadata에 대해 deterministic URL/title
normalization 모듈과 read-only duplicate candidate 분석 도구를 설계하고
구현했다. Tracking parameter와 source별 query 규칙을 제거하면서도 의미가
달라질 수 있는 URL 요소는 보존하는 보수적 정책을 적용했다.

발행 시각 우선과 수집 시각 기준을 분리한 24h/72h/168h/전체 dry-run을
실행해 전체 376건에서 normalized URL collision은 없고 title hash 후보는
2그룹/4건임을 확인했다. DB schema나 운영 시스템을 변경하기 전에 실제
데이터로 정책 위험을 검증하는 단계적 접근을 사용했다.

## 다음 단계 후보

- `normalized_url`은 rule 안정화 후 nullable column과 비고유 index로 먼저
  도입하고 기존 데이터를 backfill하는 방안을 검토한다.
- normalized URL unique constraint는 multi-source 원문 보존을 막을 수
  있으므로 collision 검토와 보존 정책 확정 전에는 추가하지 않는다.
- `title_hash`는 검색/후보 생성용 nullable column 및 비고유 index로만
  검토하며 unique constraint로 사용하지 않는다.
- `duplicate_of_article_id`는 canonical article 선택 기준과 사람이 확인한
  후보 처리 정책을 정의한 뒤 검토한다.
- 위 변경이 승인되면 별도 차수에서 migration SQL 초안을 작성하고,
  Supabase 실행은 human operator가 수행한다.
- all-time title hash 후보 2그룹의 실제 중복 여부를 사람이 확인한다.
- 추가 multi-source 데이터가 누적된 후 동일 dry-run을 다시 실행해
  domain별 제거 규칙과 collision 추이를 확인한다.
- article 수가 증가하면 pagination, cursor, `yield_per` 기반 chunk/batch
  분석을 검토한다.
- Google News RSS는 normalization과 duplicate policy가 안정화된 이후
  enabled 여부를 다시 검토한다.
