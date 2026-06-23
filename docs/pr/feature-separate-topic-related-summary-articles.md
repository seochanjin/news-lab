# Topic 관련 기사 보존과 Summary 근거 기사 분리

## 작업 내용

- Daily topic pipeline에서 Topic 관련 기사와 Summary 근거 기사를 별도 집합으로 관리하도록 변경했다.
- Topic 관련 기사는 기본 최대 20건까지 보존하고 기존 `topic_articles` 관계로 저장한다.
- Summary 근거 기사는 관련 기사 중 기본 최대 3건만 선택해 원문 확보와 Summary provider 입력에 사용한다.
- 관련 기사 수와 Summary 기사 수를 분리한 설정, 단계 결과 모델, 실행 통계와 보고서를 추가했다.
- Topic API의 endpoint와 response schema는 유지하면서 저장된 관련 기사 전체가 기존 집계값과 기사 목록에 반영되는지 회귀 검증했다.
- Daily CronJob과 architecture/runbook을 신규 20/3 설정에 맞게 동기화했다.

## 주요 변경 사항

- Daily pipeline 설정을 다음 두 값으로 분리했다.
  - `max_related_articles_per_topic`: 기본 20
  - `max_summary_articles_per_topic`: 기본 3
- 신규 CLI option을 추가했다.
  - `--max-related-articles-per-topic`
  - `--max-summary-articles-per-topic`
- 기존 `--max-articles-per-topic`은 deprecated alias로 유지했다.
  - 단독 사용 시 두 상한에 같은 값을 적용한다.
  - 신규 option과 동시에 사용하면 실행 전에 차단한다.
  - Summary 상한이 관련 기사 상한보다 크거나 1 미만이면 차단한다.
- `TopicSelectionResult`에 `related_article_ids`와 `summary_article_ids`를 분리했다.
  - `summary_articles ⊆ related_articles` 계약을 생성 시 검증한다.
  - 대표 기사는 Summary 기사에 포함되도록 검증한다.
  - 기존 downstream 호환을 위해 `selected_article_ids` property는 Summary 기사 alias로 유지한다.
- 관련 기사는 기존 대표 후보 정렬을 사용해 상한까지 결정론적으로 선정한다.
- Summary 근거 기사는 대표 기사를 우선 포함하고 관련도, source 다양성, URL·제목 중복 제외와 기존 tie-breaker를 적용해 선정한다.
- Raw acquisition 단계는 Summary 근거 기사만 원문 조회·재사용·신규 추출 대상으로 사용한다.
- Summary provider 입력과 Summary input hash는 Summary 근거 기사 원문만 반영한다.
- 저장 계획의 `articles`, `article_count`, `source_count`는 관련 기사 전체를 기준으로 구성한다.
- 실행 결과와 Markdown report에서 다음 통계를 구분한다.
  - 관련 기사 수
  - Summary 근거 기사 수
  - 원문 확보 대상 수
  - 기존 원문 재사용 수
  - 신규 원문 추출 수
  - 저장된 `topic_articles` 관계 수
- Daily CronJob을 다음 운영값으로 변경했다.
  - 관련 기사 최대 20건
  - Summary 근거 기사 최대 3건
- 관련 동작을 다음 문서에 반영했다.
  - `docs/architecture/backend-api.md`
  - `docs/architecture/pipeline.md`
  - `docs/runbooks/cronjobs.md`

## 추가/변경된 API

Endpoint와 response schema 변경은 없다.

- FastAPI router와 endpoint path 변경 없음
- Query parameter 변경 없음
- Response field 이름과 타입 변경 없음
- 홈 API의 기존 lightweight payload 유지
- Topic 상세 API의 기존 관련 기사 payload 유지

저장 데이터 변화에 따라 다음 값은 기존보다 커질 수 있다.

- `article_count`: 저장된 관련 기사 전체 수
- `source_count`: 관련 기사 전체의 source 수
- Topic 상세의 관련 기사 목록

대표 기사 표시와 관계 순서 기반의 결정론적인 기사 반환은 유지한다.

## DB 변경 사항

없음.

- 신규 table 또는 column 없음
- Migration 및 index 변경 없음
- Supabase SQL 실행 없음
- 기존 `topic_articles` 관계에 관련 기사 전체를 저장
- Summary 근거 기사 여부는 pipeline 실행 중 모델에서만 관리

## README 영향

README는 변경하지 않았다.

- 변경 대상은 Daily topic pipeline의 내부 기사 선정·Summary·저장 계약과 운영 설정이다.
- 동작 설명은 architecture 문서에, CronJob option과 운영 확인 절차는 runbook에 반영했다.
- 사용자-facing application 시작 방법이나 공통 repository 진입 안내에는 변화가 없다.

## 테스트

Verification 문서에 기록된 실제 결과:

- UNIT-01 설정 및 모델 분리
  - 관련 pytest: 26 passed
  - 관련 unittest: Ran 26 tests, OK
- UNIT-02 기사 선정 및 원문 확보 대상 분리
  - 전용 pytest: 3 passed
  - 관련 회귀 pytest: 42 passed
  - 관련 unittest: Ran 45 tests, OK
- UNIT-03 Summary 입력 및 관련 기사 전체 저장
  - 전용 pytest: 4 passed
  - 관련 회귀 pytest: 37 passed
  - 관련 unittest: Ran 41 tests, OK
- UNIT-04 API, CronJob 및 전체 회귀
  - Topic API·CronJob manifest: 10 passed
  - 관련 수직 회귀: 50 passed
  - 전체 pytest: 201 passed in 5.06s
  - 전체 unittest: Ran 201 tests in 3.927s, OK
- `python -m compileall app scripts tests`
  - 성공
- `git diff --check`
  - 성공
- `git diff -- db/migrations app/routers app/main.py`
  - 출력 없음

`unittest` 중 출력된 argparse 오류, provider failure 및 embedding mismatch 문구는 잘못된 입력과 실패 격리를 검증하는 테스트의 예상 stderr·로그이며 최종 결과는 `OK`다.

## 확인 결과

- 관련 기사와 Summary 근거 기사 상한이 20건과 3건으로 분리됐다.
- Summary 근거 기사는 항상 관련 기사 집합의 부분집합이다.
- 대표 기사는 기본적으로 관련 기사와 Summary 기사 집합에 포함된다.
- Summary에 사용하지 않는 관련 기사에는 원문 조회나 신규 추출이 발생하지 않는다.
- 기존 원문 재사용과 기사 단위 추출 실패 격리가 유지된다.
- Summary provider에는 근거 기사와 해당 원문만 전달된다.
- 관련 기사 전체가 기존 순서, 대표 역할과 similarity를 유지해 저장 계획에 포함된다.
- 중복 기사 관계 방지와 기존 transaction 경계를 유지했다.
- 한 Topic의 Summary 실패가 다른 Topic 처리와 저장 계획을 중단시키지 않는다.
- Topic API endpoint와 response schema가 유지된다.
- Daily CronJob과 최신 architecture/runbook이 신규 20/3 option과 일치한다.
- DB schema, migration, router와 `app/main.py`는 변경하지 않았다.
- Approved Fixes는 없으며 기존 Verification 결과를 그대로 사용했다.

## 비고

- 기존 `--max-articles-per-topic`은 deprecated alias로 유지했다. 과거 Task·Verification 문서와 Daily pipeline과 별개인 report command는 일괄 변경하지 않았다.
- K3s manifest 파일은 변경했지만 `kubectl apply`, rollout 및 CronJob 수동 실행은 수행하지 않았다.
- Production DB 저장 결과와 Production API 응답은 확인하지 않았다.
- 운영 반영 후 사람이 다음을 확인해야 한다.
  - CronJob 신규 20/3 argument 적용
  - 관련 기사와 Summary 근거 기사 수가 분리된 실행 로그
  - `topic_articles`에 관련 기사 전체가 저장되는지 여부
  - Topic API의 `article_count`, `source_count` 및 관련 기사 목록
- Git push, merge, PR merge, Docker image push와 Supabase SQL은 수행하지 않았다.
