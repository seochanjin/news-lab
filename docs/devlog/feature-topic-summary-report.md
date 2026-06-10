# Raw text 기반 topic summary report MVP

## 작업 목적

NewsLab의 기존 데이터 흐름은 RSS article metadata 수집과 raw article text
추출까지 제공한다. 이번 작업은 확보된 `raw_articles.raw_text`를 topic grouping
결과와 연결해 사람이 검토할 수 있는 한국어 summary report 생성 가능성을
확인하는 단계다.

summary를 DB에 저장하거나 API로 제공하기 전에 deterministic 기준선과 실제
provider 결과를 report로 비교하고, 품질과 운영 안전성을 검증하는 것을
목적으로 했다.

## 기존 문제

- topic grouping과 representative candidate 결과는 있었지만 raw text를 topic
  summary input으로 연결하는 흐름이 없었다.
- raw text가 부족한 topic과 실제 summary 가능한 topic을 구분해 검토할 report가
  없었다.
- 실제 provider를 기본 실행에 연결하면 비용과 외부 의존성이 발생하고, 품질
  검증 전에 결과가 운영 데이터로 확산될 위험이 있었다.
- 초기 구현은 `max_topics`를 raw text 가용성 평가보다 먼저 적용해, raw text가
  확보된 topic이 뒤쪽에 있으면 summary 대상에서 제외되는 문제가 있었다.

## 변경 내용

- raw text 기반 summary input 구성과 markdown report helper를 추가했다.
- deterministic/mock summary를 기본 동작으로 구현했다.
- OpenAI summary provider를 explicit opt-in으로 구현하고 API key, model,
  실행 범위 guard를 추가했다.
- read-only topic summary report CLI와 unit tests를 추가했다.
- Approved Fix 1을 적용해 전체 topic의 raw text 가용성을 먼저 평가하고 ready
  topic을 우선 선택하도록 수정했다.
- public JSON/markdown output에는 raw text 전문을 노출하지 않고 used article
  metadata와 `raw_text_length`만 남기도록 제한했다.

## 구현 상세

### Summary input과 우선순위

- 기존 deterministic topic grouping과 representative candidate 흐름을
  재사용한다.
- `raw_articles.raw_text`가 있는 article만 summary input에 포함한다.
- 모든 topic candidate의 raw text 가용성을 먼저 평가한다.
- ready topic을 insufficient topic보다 앞에 배치한 뒤 `max_topics`를 적용한다.
- ready topic은 used article count, source count, 기존 deterministic order
  순으로 정렬한다.
- limit에 자리가 남으면 raw text가 없는 topic도
  `insufficient_raw_text` 상태로 report에 포함한다.

### Deterministic summary

- 기본 실행은 API key가 필요 없는 deterministic/mock summary다.
- deterministic summary는 article title과 source metadata를 기반으로
  검토용 한국어 title, summary, key points, keywords, confidence를 생성한다.
- raw text는 summary 가능 여부와 provider input 구성에 사용하지만 public
  summary output에는 포함하지 않는다.

### Provider 경계

- 실제 provider는 `--use-summary-provider`가 있을 때만 생성한다.
- `OPENAI_SUMMARY_API_KEY`가 없으면 provider 실행 전에 실패한다.
- 기본 모델은 `gpt-5-nano`이며 `gpt-5-mini` 비교를 지원한다.
- `--max-topics`, `--max-articles-per-topic`,
  `--max-raw-chars-per-article`로 실행 범위를 제한한다.
- provider response는 structured JSON으로 parsing하고 JSON/markdown report에만
  남긴다.

### Read-only 정책

- CLI는 read-only transaction으로 `articles`, `sources`, `raw_articles`를
  조회한다.
- topic summary DB 저장, raw extraction, extraction run 기록은 수행하지 않는다.
- `.env`를 자동으로 읽거나 수정하지 않는다.

## 대안 검토

### Summary를 즉시 DB에 저장

품질 기준이 확정되지 않은 상태에서 schema와 write 경로를 추가하게 되므로
제외했다.

### Raw text가 부족하면 extraction 자동 실행

summary report 생성과 raw extraction 실행의 책임이 섞이고 DB write가
발생하므로 제외했다.

### 기본 실행에서 provider 호출

비용과 외부 의존성이 발생하고 반복 가능한 테스트 기준선이 사라지므로
제외했다.

### Topic order를 유지한 채 `max_topics`를 먼저 적용

raw text가 있는 topic이 뒤쪽에 있을 때 summary 가능성을 검증하지 못하는 실제
gap이 확인되어 Approved Fix 1에서 변경했다.

### Raw text 전체 또는 excerpt를 public output에 포함

검토 편의성은 높지만 데이터 노출 범위와 report 크기가 커지므로 제외했다.

## 선택한 접근과 근거

- deterministic/mock 기본값으로 반복 가능한 기준선과 unit test를 확보했다.
- 실제 provider는 작은 범위의 explicit opt-in으로 분리해 비용과 호출 권한을
  human approval 아래 유지했다.
- raw text 가용성을 먼저 평가해 report MVP의 핵심 목적인 실제 summary 가능
  topic 검증을 우선했다.
- report-only output을 유지해 DB/API 설계 결정을 품질 검증 이후로 미뤘다.
- raw text 전문을 public output에서 제거해 used article 추적 가능성과 데이터
  최소화를 함께 확보했다.

## 트레이드오프

- deterministic summary는 흐름과 report 구조 검증용 기준선이며 실제 자연어
  summary 품질을 대표하지 않는다.
- ready topic 우선순위는 summary 가능성 검증에는 적합하지만 기존 topic
  중요도 순서를 그대로 보존하지 않는다.
- `gpt-5-mini`는 더 자연스럽고 구체적인 결과를 생성했지만 비용과 품질 기준을
  추가로 검토해야 한다.
- provider 결과를 DB/API로 승격하기 전 factuality 평가와 운영 정책이 필요하다.
- 자동 fallback/retry와 provider 비용 추적은 이번 범위에 포함하지 않았다.

## 테스트

`docs/verification/feature-topic-summary-report.md`에 기록된 실제 결과는 다음과
같다.

- Python compile: passed.
- Focused unittest: 15 tests passed.
- Full unittest: 90 tests passed.
- CLI help: passed.
- `git diff --check`: passed.
- K8s 및 보호 범위 변경 없음 확인.
- Security checks: credential 값 노출 없음 확인.
- `pytest`: 설치되어 있지 않아 pending.

Approved Fix 1 테스트에서 다음을 확인했다.

- initial `max_topics` 범위 밖의 ready topic 우선 포함
- ready topic의 used article/source count 기반 정렬
- limit에 포함되는 insufficient topic 유지
- public JSON/markdown에 raw text 전문 미노출

## 운영 반영

- Human-approved deterministic actual-data rerun은 성공했다.
  - topic count: 3
  - summarized topic count: 3
  - insufficient raw text topic count: 0
  - `db_write_performed=false`
  - `raw_extraction_performed=false`
- Human-approved `gpt-5-nano` provider 소량 검증은 성공했다.
- Human-approved `gpt-5-mini` provider 비교 검증은 성공했다.
- 두 provider 결과는 markdown report에만 기록되었으며 topic summary DB
  write는 수행하지 않았다.
- API, K8s, CronJob, deployment, rollout은 수행하지 않았다.
- production verification과 PR merge는 pending이다.

## README 업데이트 판단

README 변경은 필요하지 않다고 판단했다.

이번 변경은 내부 품질 검증용 report MVP이며 summary DB 저장, `/topics` API,
자동 운영 절차는 아직 확정되지 않았다. 운영 모델과 factuality 기준, 사용자
노출 방식이 결정된 후 README 또는 RUNBOOK 업데이트를 별도 검토한다.

## 확인 결과

- raw text가 있는 ready topic이 `max_topics` 범위 밖에 있어도 우선 포함되는
  것을 확인했다.
- deterministic actual-data report에서 3개 topic 모두 summary가 생성되었다.
- public report에는 used article metadata와 raw text length만 표시되고 raw text
  전문은 노출되지 않았다.
- `gpt-5-nano`는 저비용 MVP summary로 사용 가능한 결과를 생성했다.
- `gpt-5-mini`는 더 자연스럽고 구체적인 한국어 summary를 생성했다.
- deterministic/provider 검증 모두 DB write와 raw extraction 없이 report만
  생성했다.

## 이번 단계의 의미

topic grouping과 raw article text 사이에 read-only summary report 단계를
추가했다. 단순한 mock 구현을 넘어 실제 raw text가 있는 topic을 우선 선택하고,
deterministic 및 두 provider 모델의 결과를 report-only 방식으로 비교했다.

이를 통해 summary 저장/API 단계로 넘어가기 전에 input 선정 정책, provider
품질 차이, 데이터 노출 경계, 운영 안전성을 검토할 수 있는 기반을 마련했다.

## 포트폴리오용 요약

뉴스 topic 후보와 raw article text를 결합하는 deterministic-first 한국어 topic
summary report MVP를 구현했다. 전체 topic의 raw text 가용성을 평가해 ready
topic을 우선 선택하고, bounded OpenAI provider opt-in과 structured response
parsing을 추가했다. `gpt-5-nano`와 `gpt-5-mini`를 human-approved 소량 조건으로
비교하면서도 summary 결과는 report에만 남기고 DB write, raw extraction,
API/K8s 변경 없이 품질 검증 경계를 유지했다.

## 다음 단계 후보

- provider summary factuality와 source-grounding 평가 기준 수립
- nano/mini 품질 및 비용 비교를 위한 추가 표본 검증
- summary output validation과 실패 report 개선
- 운영 모델 선택 및 비용 제한/fallback 정책 검토
- 품질 기준 충족 후 topic summary DB 저장과 `/topics` API를 별도 task로 검토
- 운영 경로 확정 후 README/RUNBOOK 문서화
