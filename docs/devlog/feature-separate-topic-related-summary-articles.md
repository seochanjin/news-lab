# Topic 관련 기사 보존과 Summary 근거 기사 분리

## 작업 목적

Daily topic pipeline에서 Topic과 연결해 보존할 관련 기사와 Summary 생성에 사용할 근거 기사를 서로 다른 집합으로 관리한다.

- Topic 관련 기사: Topic별 최대 20건
- Summary 근거 기사: Topic별 최대 3건
- 불변 조건: `summary_articles ⊆ related_articles`

이를 통해 Topic API에는 더 넓은 관련 기사 목록을 제공하면서도 원문 확보와 Summary provider 호출 비용은 기존 수준으로 제한한다.

## 기존 문제

기존 pipeline은 `max_articles_per_topic` 하나로 관련 기사 보존 범위와 Summary 입력 범위를 함께 제한했다. Topic별 Summary 입력을 3건으로 제한하면 `topic_articles`에도 최대 3건만 저장되어, clustering 단계가 찾은 더 넓은 관련 기사 관계가 API까지 전달되지 않았다.

반대로 단일 상한을 20건으로 늘리면 원문 조회·추출과 Summary provider 입력도 최대 20건으로 확대되어 비용, 처리 시간, 입력 노이즈가 함께 증가할 수 있었다. 즉, 관련 기사 탐색 범위와 요약 근거 범위를 독립적으로 조절할 수 없는 구조였다.

## 변경 내용

- 관련 기사 상한과 Summary 기사 상한을 각각 설정하도록 CLI를 분리했다.
  - `--max-related-articles-per-topic`
  - `--max-summary-articles-per-topic`
- 기본값을 관련 기사 20건, Summary 기사 3건으로 설정했다.
- 기존 `--max-articles-per-topic`은 deprecated alias로 유지했다.
- Topic 선정 결과에 `related_article_ids`와 `summary_article_ids`를 분리했다.
- Summary 기사 집합이 관련 기사 집합의 부분집합이고 대표 기사를 포함하도록 결과 계약에서 검증한다.
- 원문 재사용·추출과 Summary provider 입력은 Summary 기사만 대상으로 제한했다.
- 저장 단계는 Summary 생성에 성공한 Topic에 관련 기사 전체를 연결하도록 변경했다.
- `article_count`, `source_count`, API 관련 기사 목록이 관련 기사 전체를 반영하도록 했다.
- 실행 보고서에 관련 기사, Summary 기사, 원문 확보 대상, 저장 관계 수를 구분해 표시했다.
- CronJob 인자를 관련 기사 20건, Summary 기사 3건으로 갱신했다.
- pipeline, backend API, CronJob 운영 문서를 변경된 경계에 맞게 수정했다.
- 관련 설정, 선정, 저장, API, CronJob 계약을 검증하는 테스트를 추가·보강했다.

## 구현 상세

### 설정과 호환성

CLI는 `1 <= max_summary_articles_per_topic <= max_related_articles_per_topic` 조건을 검증한다. 기존 alias를 단독으로 사용하면 과거 의미를 보존하기 위해 두 상한에 같은 값을 적용한다. 신규 옵션과 기존 alias를 함께 전달하면 설정 의도가 모호하므로 실행을 차단한다.

기존 downstream 코드가 사용하는 `max_articles_per_topic` 값은 Summary 상한을 가리키는 호환 필드로 유지했다. 따라서 원문 확보와 Summary 생성에 기존 단일 상한을 참조하던 경로가 관련 기사 상한으로 잘못 확장되지 않는다.

### Topic 선정 계약

`TopicSelectionResult`는 다음 집합을 명시적으로 전달한다.

- `related_article_ids`: Topic 관계로 저장할 기사
- `summary_article_ids`: 원문 확보와 Summary 입력에 사용할 기사
- `representative_article_ids`: 각 Topic의 대표 기사

생성 시 Summary 기사가 관련 기사에 포함되는지, 대표 기사가 Summary 기사에 포함되는지 검증한다. 기존 `selected_article_ids` 접근은 Summary 기사 ID를 반환하는 alias로 유지해 기존 원문·Summary 경로와의 호환성을 보존했다.

관련 기사는 기존 대표 후보 순위를 유지한 채 Topic별 상한까지 선택한다. Summary 근거 기사는 이 순서에서 대표 기사를 포함하고 중복 URL 또는 사실상 같은 제목을 제외한 뒤 상한까지 선택한다. ID를 마지막 tie-breaker로 사용해 같은 입력에 대해 결정론적인 결과가 나오도록 했다.

승인된 fix를 반영해 URL과 제목의 중복 비교 규칙을 분리했다.

- URL: 앞뒤 공백만 제거하고 path와 query의 대소문자는 보존
- 제목: 연속 공백을 정규화하고 대소문자는 무시

이 구분으로 URL path 또는 query의 대소문자가 실제 식별에 영향을 줄 수 있는 기사를 잘못 하나로 합치지 않으면서, 표현만 다른 중복 제목은 계속 제외한다.

### 원문 확보와 Summary 생성

원문 단계는 선택된 Topic 구조에서 `summary_article_ids`만 남긴 복사본을 만든다. 저장 원문 재사용, 신규 extractor target 결정, 추출 후 재조회는 이 기사들에만 적용된다.

Summary 단계도 같은 Summary 기사 부분집합과 해당 원문만 provider 입력으로 사용한다. Summary 입력 hash와 생성 판단 역시 Summary 근거 범위를 기준으로 유지된다. 기사별 원문 실패와 Topic별 provider 실패를 격리하는 기존 정책은 변경하지 않았다.

### 관련 기사 전체 저장

Summary 생성에 성공해 저장 후보가 된 Topic은 선정 단계의 관련 기사 전체를 `topic_articles` 저장 계획에 반영한다.

- 선정 순서를 relation rank로 유지
- 대표 후보 1순위는 `representative`, 나머지는 `supporting`
- similarity score 유지
- 중복 article ID는 첫 관계만 보존
- `article_count`는 저장할 관련 기사 수로 계산
- `source_count`는 관련 기사 전체의 source로 계산

DB schema와 저장 transaction 구조는 변경하지 않았다. 기존 `topics`와 `topic_articles` 구조에 저장되는 관계 범위만 넓혔다.

### API와 운영 설정

API endpoint와 response field 이름·타입은 변경하지 않았다. 기존 `/topics/home`은 저장된 집계값을 반환하고 `/topics/{topic_id}`는 `topic_articles` 관계를 반환하므로, 저장 범위 확장만으로 관련 기사 전체가 기존 계약을 통해 노출된다.

CronJob manifest는 신규 옵션을 사용하도록 수정했지만 실제 Kubernetes apply나 rollout은 수행하지 않았다.

## 대안 검토

### 단일 기사 상한을 20건으로 확대

구현은 단순하지만 원문 확보와 Summary provider 입력도 20건으로 늘어난다. 관련 기사 노출을 개선하기 위해 provider 비용과 입력 노이즈까지 확대할 필요는 없어 선택하지 않았다.

### Summary 근거 여부를 DB에 별도 저장

별도 column 또는 relation을 추가하면 사후 감사와 재현성이 좋아진다. 다만 DB migration과 API 계약 변경이 필요하며 현재 task의 `Do not change` 범위를 벗어나므로 적용하지 않았다.

### 모든 관련 기사를 저장한 뒤 Summary 단계에서 다시 선정

단계 경계는 명확하지만 Summary 선정 전 원문 확보 대상을 제한하기 어렵고, 불필요한 원문 조회·추출이 발생할 수 있다. 선정 단계에서 두 집합을 함께 확정하는 방식을 선택했다.

### 기존 CLI 옵션을 즉시 제거

설정은 단순해지지만 기존 수동 실행 명령과 운영 문서의 호환성이 깨진다. deprecated alias를 유지하고 신규 옵션과의 혼용만 차단했다.

### API router에서 별도 가공

현재 API는 이미 저장된 집계와 `topic_articles` 관계를 읽는다. router를 수정하면 불필요한 계약 변경 위험만 늘어나므로 저장 계획과 테스트만 변경했다.

## 선택한 접근과 근거

pipeline 초기에 관련 기사와 Summary 기사 집합을 동시에 확정하고, 이후 단계가 필요한 집합만 소비하도록 했다.

이 접근은 다음 이유로 선택했다.

- `summary_articles ⊆ related_articles` 계약을 단계 경계에서 즉시 검증할 수 있다.
- 원문 확보 전에 Summary 대상을 확정해 extractor와 provider 비용을 제한할 수 있다.
- 기존 clustering, 대표 기사 선정, failure isolation, 저장 transaction 구조를 유지할 수 있다.
- DB schema와 API schema를 변경하지 않고 관련 기사 노출 범위만 확장할 수 있다.
- 신규 옵션과 deprecated alias를 함께 제공해 운영 전환 위험을 줄일 수 있다.

## 트레이드오프

- Summary 근거 기사 목록은 별도 DB 필드로 저장하지 않으므로, 저장 데이터만으로 당시 정확한 근거 집합을 직접 조회할 수는 없다.
- `selected_article_ids`는 호환성을 위해 Summary 기사 alias로 남아 있어 이름만 보면 관련 기사 전체로 오해할 여지가 있다.
- 기존 alias를 사용하면 관련 기사와 Summary 기사 상한이 같은 값으로 설정되므로 신규 기본값 20/3의 이점을 얻지 못한다.
- URL·제목 중복 제거는 현재 기사 metadata 품질에 의존한다. URL은 보수적으로 앞뒤 공백만 제거하므로, 의미상 같지만 표기가 다른 URL은 별도 기사로 남을 수 있다.
- Topic별 저장 relation 수가 최대 20건으로 늘어 DB row 수와 API 응답량은 증가한다.
- 대신 원문 추출과 Summary provider 입력은 최대 3건으로 제한되어 비용 증가를 피한다.
- CronJob manifest는 변경되었지만 실제 cluster 반영 여부는 별도 human-controlled 단계다.

## 테스트

검증 결과의 source of truth는 `docs/verification/feature-separate-topic-related-summary-articles.md`다.

- Unit 01 설정·모델 계약
  - `pytest`: 26 passed
  - `unittest`: 26 tests, OK
  - compile 및 diff 검사: passed
- Unit 02 관련 기사·Summary 기사 선정과 원문 대상 분리
  - 전용 테스트: 3 passed
  - 관련 회귀 테스트: 42 passed
  - `unittest`: 45 tests, OK
  - compile 및 diff 검사: passed
- Unit 03 Summary 입력과 관련 기사 전체 저장
  - 전용 테스트: 4 passed
  - 관련 회귀 테스트: 37 passed
  - `unittest`: 41 tests, OK
  - compile 및 diff 검사: passed
- Unit 04 API·CronJob·전체 회귀
  - API/CronJob 테스트: 10 passed
  - vertical regression: 50 passed
  - 전체 `pytest`: 201 passed in 5.06s
  - 전체 `unittest`: 201 tests in 3.927s, OK
  - `compileall`, `git diff --check`, 금지 변경 검사: passed

`unittest` 실행 중 argparse 오류 출력, 의도적으로 발생시킨 provider 실패, embedding 차원 불일치 로그가 stderr에 나타났으며 verification 문서에서 기대된 오류 경로 검증으로 분류했다.

승인된 URL 정규화 fix 적용 후 별도 검증 결과:

- 기사 선정 전용 `pytest`: 4 passed in 0.12s
- Daily topic pipeline 관련 회귀 `pytest`: 42 passed in 0.16s
- `python -m compileall app scripts tests`: passed
- `git diff --check`: passed
- DB migration, router, `app/main.py`, K3s 변경 검사: no output

전체 201건 회귀 결과는 최초 구현 검증 기록이며, 승인 fix 이후에는 위의 허용된 대상 테스트와 정적 검증을 실행했다.

## 운영 반영

현재 상태는 코드, 테스트, 문서, CronJob manifest 초안까지 완료된 상태다.

다음 항목은 수행하지 않았으며 pending이다.

- Kubernetes manifest apply
- K3s rollout 또는 restart
- 실제 CronJob 실행 및 로그 확인
- 운영 DB의 `topics` / `topic_articles` 저장 결과 확인
- 운영 `/topics/home`, `/topics/{topic_id}` 응답 확인
- production curl verification
- Supabase SQL 실행
- git push, PR merge, 배포

운영 반영과 production verification은 실제 환경과 credential을 관리하는 사람이 수행하고, 결과 로그를 verification 문서에 추가해야 한다.

## README 업데이트 판단

README는 수정하지 않았다.

이번 변경은 외부 사용자가 호출하는 신규 API나 설치 방법 추가가 아니라 Daily topic pipeline 내부의 기사 집합 경계와 운영 인자 변경이다. 따라서 세부 동작은 다음 관련 문서에 반영하는 것이 적절하다고 판단했다.

- `docs/architecture/pipeline.md`: 관련 기사와 Summary 기사 단계 경계
- `docs/architecture/backend-api.md`: 관련 기사 전체 기준 집계와 기존 API 계약
- `docs/runbooks/cronjobs.md`: 신규 CLI 인자와 운영 확인 항목

README에 노출할 사용자 진입점이나 프로젝트 실행 절차는 변경되지 않았다.

## 확인 결과

- 관련 기사와 Summary 근거 기사가 별도 상한과 결과 필드로 분리되었다.
- Summary 기사와 대표 기사 집합의 포함 관계가 모델에서 검증된다.
- 원문 조회·추출 및 Summary provider 입력은 Summary 기사로 제한된다.
- 저장 계획과 기존 API 응답은 관련 기사 전체를 반영한다.
- DB schema, API endpoint, response schema는 변경되지 않았다.
- 승인된 URL·제목 중복 정규화 분리 fix가 적용되었다.
- URL path와 query의 대소문자가 다른 기사는 서로 다른 Summary 근거 기사로 유지된다.
- 최초 구현의 전체 자동 테스트 201건이 통과했고, 승인 fix 이후 기사 선정 4건과 관련 회귀 42건이 추가로 통과했다.
- production deployment와 verification은 수행되지 않았다.

## 이번 단계의 의미

Topic 품질을 설명하는 두 요구를 분리했다. 사용자에게는 더 많은 관련 기사를 제공하면서, Summary 생성은 대표성과 중복 제거가 적용된 소수의 근거 기사로 제한한다.

이 변경으로 기사 관계의 정보량과 LLM 처리 비용을 하나의 상한으로 절충하던 구조에서 벗어났다. 이후 관련 기사 보존 범위와 Summary 품질·비용을 독립적으로 조정하고 관찰할 수 있는 기반이 마련되었다.

## 포트폴리오용 요약

뉴스 Topic pipeline에서 관련 기사 보존 집합과 LLM Summary 근거 집합을 분리했다. 관련 기사는 Topic별 최대 20건까지 기존 API에 노출하면서, 원문 추출과 Summary provider 입력은 중복 제거된 최대 3건으로 제한했다. 단계 간 dataclass 계약으로 부분집합 불변 조건을 검증하고, URL과 제목에 서로 다른 정규화 정책을 적용해 기사 식별 정확도를 보완했다. DB/API schema 변경 없이 저장 관계와 집계 기준을 확장하고 CLI 하위 호환성, CronJob 설정, 운영 문서와 회귀 검증을 함께 정리했다.

## 다음 단계 후보

- 사람이 CronJob manifest를 검토한 뒤 Kubernetes apply와 rollout 수행
- 실제 실행 로그에서 `related_article_count`, `summary_article_count`, `raw_acquisition_target_count`, `saved_topic_article_count` 확인
- 운영 DB에서 Topic별 최대 20건의 관계, 대표·supporting 순서, `article_count`, `source_count` 확인
- 운영 API에서 home 집계와 detail 관련 기사 목록 확인
- Summary 근거 기사 재현성이 필요해질 경우 별도 DB 저장 설계를 후속 task로 검토
- API 응답량과 Topic당 relation 증가에 따른 성능 지표 관찰
