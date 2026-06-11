# Topic summary DB 저장 및 조회 API MVP

## 작업 목적

35차에서 검증한 raw text 기반 topic summary report를 일회성 문서 출력에서
DB 저장 및 read API 단계로 확장하는 작업이다.

이번 단계의 목표는 summary 자동 운영이 아니라, 검증된 결과를 제한적으로
저장하고 기존 NewsLab API 구조에서 조회할 수 있는 MVP를 만드는 것이다.

## 기존 문제

- topic summary가 JSON/markdown report로만 존재해 지속적으로 조회하거나
  application에서 활용할 수 없었다.
- summary와 근거 article 사이의 연결 관계를 저장하는 구조가 없었다.
- 저장 경로를 바로 실행형으로 만들면 검증되지 않은 summary가 DB에 기록될
  위험이 있었다.
- API에서 raw text를 직접 노출하면 원문 데이터 노출 범위가 불필요하게
  커질 수 있었다.
- 초기 구현의 save upsert query는 migration의 composite unique constraint와
  conflict target이 달라 실제 저장 시 PostgreSQL 오류가 발생할 수 있었다.

## 변경 내용

- `topics`, `topic_articles` 테이블 migration SQL을 추가했다.
- 기존 topic summary 생성 helper를 재사용하는 save CLI를 추가했다.
- save CLI 기본 동작을 read-only dry-run으로 구현했다.
- 명시적인 `--execute`가 있을 때만 topic과 related article link를 저장한다.
- `GET /topics`, `GET /topics/{topic_id}` read-only API를 추가했다.
- bounded raw summary input 기반 `summary_input_hash`를 추가했다.
- raw text는 저장 report와 API 응답에서 제외했다.
- Approved fix를 적용해 migration unique constraint와 upsert conflict target을
  `(summary_input_hash, provider, model)`로 통일했다.

## 구현 상세

### 저장 구조

- `topics`는 summary 결과, provider/model, 상태, summary input hash와 생성 시점
  article/source count를 저장한다.
- `topic_articles`는 topic과 기존 `articles` row 사이의 연결 정보만 저장한다.
- article title, source, URL, raw text는 중복 저장하지 않는다.
- API 상세 조회 시 기존 `articles`, `sources`를 join해 article metadata를
  반환한다.

### 저장 CLI

- 기본 실행은 `set transaction read only`를 사용하는 dry-run이다.
- dry-run은 save candidate, skipped topic, provider/model, write/extraction 여부를
  report로 남긴다.
- 실제 저장은 `--execute`가 명시된 경우에만 write transaction으로 진입한다.
- 동일 bounded input과 provider/model 조합은 upsert하고 article link를
  동기화한다.
- raw extraction이나 provider 호출은 저장 과정에서 자동 실행하지 않는다.

### Summary input hash와 중복 처리

- `summary_input_hash`는 bounded summary input의 article ID와 raw text를
  내부적으로 hash해 계산한다.
- raw text 자체는 public summary, save report, API response에 포함하지 않는다.
- 동일 input이라도 deterministic, `gpt-5-nano`, `gpt-5-mini` 결과를 각각
  저장할 수 있도록 provider/model을 composite unique key에 포함한다.
- Approved fix로 `UPSERT_TOPIC_QUERY`도 동일한 composite conflict target을
  사용하도록 정렬했다.

### Read API

- `/topics`는 pagination과 status/date/keyword 필터를 지원한다.
- `/topics/{topic_id}`는 summary 기본 필드와 related article metadata를
  반환한다.
- 존재하지 않는 topic은 `404`를 반환한다.
- 두 API 모두 raw text를 조회하거나 반환하지 않는다.

## 대안 검토

### Save CLI를 기본 execute로 구현

운영 실수 시 검증되지 않은 summary가 DB에 기록될 위험이 있어 제외했다.

### Topic summary를 기존 articles 또는 raw_articles에 저장

topic summary는 여러 article을 묶는 별도 aggregate이며 기존 row의 책임과
맞지 않아 `topics`, `topic_articles` 구조를 선택했다.

### Article metadata와 raw text를 topic_articles에 중복 저장

조회는 단순해지지만 데이터 중복과 raw text 노출 위험이 증가하므로 기존
article/source 테이블 join을 선택했다.

### `summary_input_hash`만 unique key로 사용

같은 input에 대한 provider/model별 결과 비교 저장을 막기 때문에 제외했다.

### 실제 DB integration test를 Codex 검증에서 실행

Supabase migration 적용과 write는 human-controlled operation이므로 unit test와
fake connection 검증까지만 Codex 범위로 유지했다.

## 선택한 접근과 근거

- dry-run 기본값과 explicit `--execute`로 저장 권한 경계를 분리했다.
- 기존 summary generation helper를 재사용해 report와 DB 저장 사이의 결과
  구조 차이를 줄였다.
- topic/article 관계를 정규화해 기존 article metadata를 source of truth로
  유지했다.
- composite unique key로 동일 input의 모델별 비교 결과를 보존할 수 있게 했다.
- API는 read-only로 제한하고 raw text를 제외해 저장 단계와 공개 단계의
  데이터 경계를 명확히 했다.

## 트레이드오프

- API 조회는 article/source join이 필요하므로 denormalized 구조보다 query가
  복잡하다.
- `topic_articles` link를 upsert 시 다시 동기화하므로 대량 topic 저장에는
  추가 최적화가 필요할 수 있다.
- `summary_input_hash`는 bounded input 기준이므로 원문 전체 변경을 항상
  표현하지는 않는다.
- 자동 스케줄링, factuality gate, provider fallback은 구현하지 않아 운영
  자동화 수준은 제한적이다.
- migration과 실제 저장 검증은 human-controlled 단계에 의존한다.

## 테스트

`docs/verification/feature-topic-summary-api.md`에 기록된 실제 결과는 다음과
같다.

- 초기 구현:
  - Python compile: passed
  - focused summary/save/API tests: 30 tests passed
  - full unittest: 105 tests passed
  - save CLI help: passed
- Approved fix 적용 후:
  - Python compile: passed
  - focused migration/save/topics API tests: 11 tests passed
  - full unittest: 106 tests passed
  - 전체 및 targeted `git diff --check`: passed
- 테스트에서 migration/FK/unique/index, dry-run, mocked persistence,
  deterministic input hash, composite conflict target, API pagination/detail,
  404, raw text 미노출을 확인했다.
- K8s, GitHub Actions, frontend, Dockerfile 변경 없음과 credential 값 미노출을
  확인했다.

## 운영 반영

- Human operator가 Supabase SQL Editor에서 migration을 수동 적용했다.
- Human-approved dry-run은 성공했고 DB write와 raw extraction은 발생하지
  않았다.
- Human-approved limited execute는 `--max-topics 1`로 수행되었다.
  - deterministic topic 1개 저장
  - related article link 1개 저장
  - raw extraction 및 provider call 없음
- Human-approved local API verification에서 `/health`, `/topics`, `/topics/1`
  응답과 raw text 미노출을 확인했다.
- Production deployment, K3s rollout, production API verification은
  수행되지 않았으며 pending이다.
- PR merge도 pending이다.

## README 업데이트 판단

README는 이번 단계에서 변경하지 않았다.

`/topics` API가 추가되었지만 production deployment 및 운영 verification이
완료되지 않았고, summary 운영 모델과 provider 기반 저장 정책도 확정되지
않았다. Production surface와 운영 절차가 확정된 후 README/RUNBOOK 업데이트를
별도 검토하는 것이 적절하다.

## 확인 결과

- `topics`, `topic_articles` schema와 관계 constraint가 Supabase에 적용된 것을
  human verification으로 확인했다.
- migration과 save CLI가 동일한
  `unique(summary_input_hash, provider, model)` 기준을 사용하는 것을 확인했다.
- dry-run에서 save plan을 생성하지만 DB write를 수행하지 않는 것을 확인했다.
- limited execute에서 topic 및 article link 저장이 정상 동작하는 것을
  확인했다.
- local `/topics` 목록 및 상세 API가 저장된 데이터를 반환하는 것을 확인했다.
- 저장 report와 API 응답에 raw text가 포함되지 않는 것을 확인했다.

## 이번 단계의 의미

NewsLab의 topic summary 흐름이 report-only 검증 단계에서 저장 및 조회 가능한
application 데이터 단계로 확장되었다.

동시에 dry-run 기본값, explicit write gate, composite deduplication,
human-controlled migration, read-only API, raw text 미노출 정책을 함께 적용해
기능 확장과 운영 안전성을 분리했다.

## 포트폴리오용 요약

Raw article text를 기반으로 생성한 topic summary를 PostgreSQL/Supabase에
저장하고 FastAPI로 조회하는 MVP를 구현했다. 기본 dry-run save CLI와 명시적
execute gate, provider/model별 composite deduplication, normalized
topic-article relation, pagination/detail API를 추가했다. Human-approved
Supabase migration과 제한 저장, local API 검증까지 수행하면서 raw text를
report/API에 노출하지 않고 K8s 및 production 경계를 유지했다.

## 다음 단계 후보

- Production deployment 및 `/topics` production read verification
- Topic status lifecycle과 publish/review workflow 정의
- Provider 기반 save verification과 factuality/quality gate 설계
- Topic list/detail response schema 및 API 문서 안정화
- 대량 저장 성능과 topic_articles 동기화 전략 검토
- 운영 surface 확정 후 README/RUNBOOK/ARCHITECTURE 업데이트
- PR review 및 human-controlled merge
