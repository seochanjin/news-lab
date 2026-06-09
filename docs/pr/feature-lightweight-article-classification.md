# Lightweight article classification MVP

## 작업 내용

- LLM이나 embedding 없이 article metadata를 분석하는 deterministic
  lightweight classification helper를 추가했습니다.
- 현재 DB의 `articles` 데이터를 읽기 전용으로 조회해 source category,
  rule category, language 후보, importance signal을 분석하는 dry-run
  script를 추가했습니다.
- 발행 시각 기준 제품 분석과 수집 시각 기준 운영 분석을 분리하고,
  24h/72h/168h/전체 범위를 지원하도록 했습니다.
- classification helper와 분석 집계 동작을 확인하는 단위 테스트를
  추가했습니다.

## 주요 변경 사항

- source category를 기본 category로 유지하고, title/summary keyword 기반
  rule category를 별도 후보 signal로 계산합니다. Rule category는 article
  category를 덮어쓰지 않습니다.
- 초기 category 후보 `tech`, `world`, `business`, `politics`, `security`,
  `ai`, `climate`, `sports`, `unknown`을 지원합니다.
- title keyword match를 summary match보다 높게 가중하고, deterministic
  priority를 사용해 동일 입력에 동일 rule category를 반환합니다.
- 문자 script 기반 language 감지와 source registry language fallback을
  적용합니다. 현재 DB의 `sources` 테이블에 `language` column이 없어
  repository의 `RSS_SOURCES` 설정을 fallback으로 사용합니다.
- title/summary keyword, source category, recency, breaking/live/update,
  high-impact keyword를 구성 요소로 importance 후보 점수를 계산합니다.
- 분석 script는 24h/72h/168h/all 및 published/created 기준을 지원하고
  transaction을 read-only로 설정합니다.
- category/language count, source/rule category mismatch, importance 상위
  후보와 점수 집계를 JSON으로 출력합니다.
- `--max-examples`로 상세 후보 출력량을 제한할 수 있으며, verification
  실행에서는 기사 제목과 후보 상세를 출력하지 않도록 `0`을
  사용했습니다.

## 추가/변경된 API

- 추가되거나 변경된 API는 없습니다.
- 기존 `/articles`, `/collector/status`, `/collector/runs` 응답 구조를
  변경하지 않았습니다.
- Classification 후보 분석은 API가 아닌
  `scripts/analyze_article_classification.py`를 통해 수행합니다.

## DB 변경 사항

- DB schema 변경 및 migration 파일 추가는 없습니다.
- Supabase SQL과 DB migration을 실행하지 않았습니다.
- 분석 script는 `set transaction read only`를 실행한 뒤
  `articles`/`sources` 데이터를 SELECT하며 article/source row를 수정하지
  않습니다.
- 후속 차수에서 `detected_language`, `rule_category`,
  `importance_score`, `importance_signals`, `classified_at` column과
  category/language index 필요성을 검토할 예정입니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 이번 변경은 내부 helper와 수동 read-only 분석 script 추가이며, 기존
  서비스 실행 방법, 공개 API, K3s 운영 절차를 변경하지 않습니다.

## 테스트

- `.venv/bin/python -m unittest discover -s tests -v`: 전체 19개 테스트
  통과
- Python compile: 통과
- `.venv/bin/python scripts/analyze_article_classification.py --help`: 통과
- `git diff --check`: 통과
- 신규 untracked 파일 whitespace 검사: 통과
- published 기준 24h/72h/168h/all DB read-only dry-run: 통과
- created 기준 24h DB read-only dry-run: 통과
- security grep: 실제 credential 값 없음
- `pytest`: `.venv/bin/pytest`가 설치되어 있지 않아 pending
- 상세 실행 기록은
  `docs/verification/feature-lightweight-article-classification.md`를
  참조합니다.

## 확인 결과

- published 기준:
  - 24h 169건: source/rule mismatch 51건, importance 평균 5.25
  - 72h 253건: mismatch 70건, importance 평균 4.69
  - 168h 347건: mismatch 102건, importance 평균 4.07
  - 전체 376건: mismatch 112건, importance 평균 4.0
- created 기준 최근 24h 293건에서는 mismatch 76건, importance 평균
  4.81이었습니다.
- 전체 source category는 `tech` 208건, `world` 165건, `ai` 1건,
  `unknown` 2건이었습니다.
- 전체 rule category는 `unknown` 224건, `ai` 42건, `politics` 37건,
  `world` 27건 순이었습니다.
- 전체 language 후보는 `en` 373건, `ko` 3건이었으며 모두 문자 script로
  감지됐습니다.
- 전체 importance 후보 점수는 최대 30, 평균 4.0이었습니다.
- `git diff -- k8s` 결과 K8s manifest 변경은 없었습니다.

## 비고

- Importance score는 최종 ranking이 아니라 topic grouping/ranking 전 후보
  signal입니다.
- DB schema, API, collector/extractor, frontend, K8s manifest는 변경하지
  않았습니다.
- LLM, embedding, topic grouping, AI summary는 구현하지 않았습니다.
- 인간 승인되어 적용된 review fix는 없습니다.
- Category keyword 및 importance weight 설정 외부화는 candidate fix이며
  아직 승인 또는 적용되지 않았습니다.
- Source/rule mismatch 예시와 top importance 후보에 대한 human review,
  추가 데이터 누적 후 rule/weight 조정은 pending입니다.
- migration, rollout, production verification, push, merge는 수행하지
  않았습니다.
