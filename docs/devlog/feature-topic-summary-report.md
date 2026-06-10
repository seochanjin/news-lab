# Raw text 기반 topic summary report MVP

## 작업 목적

raw extraction target 실행 흐름 이후 확보된 원문을 topic 단위로 묶어 사람이
검토할 수 있는 한국어 summary report 생성 가능성을 확인한다. 이번 단계는
summary 저장/API가 아닌 read-only report MVP다.

## 기존 문제

- topic grouping과 대표 후보 선정 결과는 있었지만 raw text를 summary input으로
  연결하는 흐름이 없었다.
- 실제 LLM 호출 전에 deterministic 결과, 입력 범위, raw text 부족 상태를
  검토할 방법이 필요했다.
- summary를 DB에 저장하거나 자동 운영하면 품질 검증 전 운영 영향이 커진다.

## 변경 내용

- raw text 기반 summary input/helper와 markdown renderer를 추가했다.
- deterministic/mock summary를 기본 동작으로 구현했다.
- OpenAI summary provider를 opt-in으로 구현하고 API key/model/range guard를
  추가했다.
- read-only topic summary report CLI와 unit tests를 추가했다.

## 구현 상세

- 기존 deterministic topic grouping과 representative candidate 흐름을
  재사용한다.
- `raw_articles.raw_text`가 있는 article만 summary input에 포함한다.
- raw text가 없는 topic은 extraction을 실행하지 않고
  `insufficient_raw_text`로 표시한다.
- deterministic summary는 원문 excerpt를 key point로 사용하고 한국어
  report를 생성한다.
- provider 기본 모델은 `gpt-5-nano`이며 `gpt-5-mini` 비교를 지원한다.
- provider는 `--use-summary-provider`와 `OPENAI_SUMMARY_API_KEY`가 모두
  있어야 생성된다.
- provider 결과와 deterministic 결과는 JSON/markdown에만 남기며 DB에
  저장하지 않는다.
- 새 CLI는 `.env`를 자동으로 읽지 않는다.

## 대안 검토

- summary를 즉시 DB에 저장: 품질 검증 전 schema/write가 필요해 제외했다.
- raw text가 부족하면 extraction 자동 실행: task safety boundary를 위반해
  제외했다.
- 기본 실행에서 provider 호출: 비용과 외부 의존성이 생겨 제외했다.
- raw text 전체를 JSON output에 포함: report 크기와 데이터 노출 범위가
  커져 제외했다.

## 선택한 접근과 근거

- deterministic/mock 기본값으로 반복 가능한 report와 unit test를 확보했다.
- provider를 작은 범위의 explicit opt-in으로 분리해 비용과 호출 위험을
  human approval 뒤로 유지했다.
- raw text는 summary 생성 입력으로만 사용하고 output에는 article metadata와
  길이만 남겨 검토 가능성과 데이터 최소화를 함께 고려했다.

## 트레이드오프

- deterministic summary는 품질 평가용 기준선이며 실제 자연어 summary 품질을
  대표하지 않는다.
- deterministic actual-data report는 현재 환경의 `DATABASE_URL` 부재로
  생성하지 못했다.
- 실제 `gpt-5-nano`/`gpt-5-mini` 품질과 비용은 human-approved 실행 전까지
  확인되지 않는다.

## 테스트

- Python compile: passed.
- Focused unittest: 12 tests passed.
- Full unittest: 87 tests passed.
- CLI help: passed.
- Deterministic actual-data report: `DATABASE_URL` 부재로 pending.
- `pytest`: 미설치로 pending.

## 운영 반영

- provider 호출, raw extraction, DB write를 수행하지 않았다.
- API, DB schema, K8s, CronJob, Docker workflow, frontend를 변경하지 않았다.
- production verification, deployment, rollout, PR merge는 pending이다.

## README 업데이트 판단

- README 변경은 필요하지 않다고 판단했다. 이번 변경은 품질 검증용 내부
  report MVP이며 API나 운영 사용법은 아직 확정되지 않았다.

## 확인 결과

- deterministic/mock summary와 `insufficient_raw_text` 처리를 unit test로
  확인했다.
- provider guard, 기본 nano 모델, mini 비교 지원, response parsing을
  mock으로 확인했다.
- report safety fields와 used article/source/raw text length 표시를 확인했다.

## 이번 단계의 의미

topic grouping 결과와 확보된 raw text 사이에 summary report 단계를 추가했다.
운영 write 없이 summary 입력 품질과 provider 비교 가능성을 검토할 수 있는
기반을 마련했다.

## 포트폴리오용 요약

뉴스 topic 후보와 raw article text를 결합해 deterministic-first 한국어 summary
report MVP를 구현했다. raw-text-only input, 부족 상태 처리, bounded provider
opt-in, structured response parsing, report-only output을 통해 외부 API 비용과
DB write 없이 summary 생성 가능성을 검증할 수 있도록 설계했다.

## 다음 단계 후보

- 명시적으로 제공된 `DATABASE_URL` 환경에서 deterministic report 생성
- human-approved `gpt-5-nano` 소량 품질 검증
- 필요 시 동일 조건의 `gpt-5-mini` 비교
- 품질 기준 확정 후 summary 저장/API 단계 별도 검토
