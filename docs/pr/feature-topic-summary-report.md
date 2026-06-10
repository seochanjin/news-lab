# Raw text 기반 topic summary report MVP

## 작업 내용

- `raw_articles.raw_text`가 확보된 topic 후보를 대상으로 사람이 검토할 수 있는
  한국어 summary JSON/markdown report 생성 흐름을 추가했습니다.
- 기본 실행은 deterministic/mock summary이며, OpenAI summary provider는
  명시적인 `--use-summary-provider`와 API key가 있을 때만 사용할 수 있습니다.
- summary 결과는 DB에 저장하지 않고 report로만 출력합니다.

## 주요 변경 사항

- `app/utils/topic_summary.py`
  - raw text가 있는 article만 summary input으로 구성합니다.
  - deterministic 한국어 summary와 `insufficient_raw_text` 처리를 제공합니다.
  - OpenAI Responses provider와 structured response parsing을 지원합니다.
  - JSON/markdown 공개 output에서는 raw text 전문을 제거하고 used article
    metadata와 `raw_text_length`만 유지합니다.
- `scripts/generate_topic_summary_report.py`
  - 기존 deterministic topic grouping과 representative candidate 흐름을
    재사용합니다.
  - `--max-topics`, `--max-articles-per-topic`,
    `--max-raw-chars-per-article`로 실행 범위를 제한합니다.
  - provider 기본 모델은 `gpt-5-nano`이며 `gpt-5-mini` 비교를 지원합니다.
  - read-only transaction으로 article/raw text를 조회하고 JSON/markdown
    report만 생성합니다.
- Approved Fix 1 적용
  - 전체 topic candidate의 raw text 가용성을 먼저 평가합니다.
  - ready topic을 insufficient topic보다 우선 배치한 뒤 `max_topics`를
    적용합니다.
  - ready topic은 used article count, source count, 기존 deterministic order
    순으로 정렬합니다.
  - limit에 포함되는 insufficient topic은 report에 계속 표시합니다.

## 추가/변경된 API

- 없음.
- 신규 `/topics` route와 기존 API response 변경은 없습니다.

## DB 변경 사항

- DB schema 및 migration 변경 없음.
- topic summary DB 저장 없음.
- deterministic 및 human-approved provider 검증 모두
  `db_write_performed=false`로 확인되었습니다.

## README 영향

- README 변경 없음.
- 이번 변경은 품질 검증용 내부 report MVP이며 API 또는 운영 자동화 절차를
  추가하지 않아 README 업데이트가 필요하지 않다고 판단했습니다.

## 테스트

- Python compile: passed.
- Focused unittest: 15 tests passed.
- Full unittest: 90 tests passed.
- CLI help: passed.
- `git diff --check`: passed.
- K8s 및 보호 범위 변경 없음 확인.
- Security checks: credential 값 노출 없음 확인.
- `pytest`: pending. 설치되어 있지 않아 실행하지 않았습니다.

Approved Fix 1 테스트에서 다음을 확인했습니다.

- initial `max_topics` 범위 밖의 ready topic 우선 포함
- ready topic의 used article/source count 기반 정렬
- limit에 포함되는 insufficient topic 유지
- 공개 JSON/markdown에 raw text 전문 미노출

## 확인 결과

- Human-approved deterministic actual-data rerun:
  - report 생성 성공
  - topic count: 3
  - summarized topic count: 3
  - insufficient raw text topic count: 0
  - `db_write_performed=false`
  - `raw_extraction_performed=false`
- Human-approved `gpt-5-nano` provider test:
  - report 생성 성공
  - summarized topic count: 1
  - provider output은 markdown report에만 기록
  - DB write 및 raw extraction 없음
- Human-approved `gpt-5-mini` comparison test:
  - report 생성 성공
  - summarized topic count: 1
  - provider output은 markdown report에만 기록
  - DB write 및 raw extraction 없음
- 비교 결과 `gpt-5-nano`는 저비용 MVP 기본 후보이며, `gpt-5-mini`는 더
  자연스럽고 구체적인 한국어 summary를 생성했습니다.
- API, DB schema, K8s, CronJob, Docker workflow, frontend는 변경하지
  않았습니다.

## 비고

- provider 호출은 human-approved verification으로 수행되었으며 자동 운영이나
  fallback/retry 정책은 구현하지 않았습니다.
- provider 결과를 사용자-facing DB/API로 승격하기 전 추가 factuality 및 품질
  검증이 필요합니다.
- production verification, deployment, K3s rollout, PR merge는 수행하지
  않았으며 pending입니다.
