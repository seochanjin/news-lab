# Raw text 기반 topic summary report MVP

## 작업 내용

- raw text가 확보된 topic 후보를 대상으로 한국어 summary JSON/markdown
  report를 생성하는 read-only CLI를 추가했습니다.
- 기본 실행은 deterministic/mock summary이며 OpenAI provider는 명시적인
  `--use-summary-provider`가 있을 때만 사용할 수 있습니다.

## 주요 변경 사항

- `app/utils/topic_summary.py`
  - raw-text-only summary input 구성
  - deterministic 한국어 summary와 `insufficient_raw_text` 처리
  - opt-in OpenAI Responses provider와 structured response parsing
  - markdown report rendering
- `scripts/generate_topic_summary_report.py`
  - deterministic topic grouping 재사용
  - summary 범위 제한과 provider/API key/model guard
  - read-only raw text 조회 및 JSON/markdown 출력
  - `.env` 자동 로드 없음
- summary output에는 title, summary, key points, keywords, confidence,
  source/article count, used article metadata, provider/model을 포함합니다.
- raw text content는 summary input으로만 사용하고 최종 output에는 포함하지
  않습니다.

## 추가/변경된 API

- 없음.

## DB 변경 사항

- DB schema/migration 변경 없음.
- topic summary DB 저장 없음.
- 실제 DB write는 수행하지 않았습니다.

## README 영향

- 없음. report MVP와 내부 CLI 범위이며 API/운영 기본 동작은 변경하지
  않았습니다.

## 테스트

- Python compile: passed.
- Focused unittest: 12 tests passed.
- Full unittest: 87 tests passed.
- CLI help: passed.
- Deterministic actual-data report: pending. 현재 환경에 `DATABASE_URL`이 없어
  DB 접근 전에 실패했습니다.
- `pytest`: pending, command not installed.

## 확인 결과

- 기본 경로는 provider/API key 없이 deterministic/mock summary를 생성합니다.
- raw text가 없는 topic은 `insufficient_raw_text`로 처리합니다.
- provider guard, `gpt-5-nano` 기본값, `gpt-5-mini` 지원은 unit test/mock으로
  확인했습니다.
- provider 호출, raw extraction, DB write는 수행하지 않았습니다.
- API, DB schema, K8s, CronJob, Docker workflow, frontend는 변경하지
  않았습니다.

## 비고

- 실제 provider report와 deterministic actual-data report 생성은 pending입니다.
- production verification, deployment, rollout, PR merge는 수행하지 않았습니다.
