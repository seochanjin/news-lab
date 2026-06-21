# Daily topic pipeline 내부 단계 분리

## 작업 목적

Daily topic pipeline의 처리 순서를 유지하면서 한 파일에 결합된 책임을 다음 네
단계로 분리하는 것이 목적이었다.

```text
기사 후보 및 embedding 준비
→ 유사 기사 clustering 및 topic 선정
→ selected article 원문 확보
→ topic summary 생성 및 저장
```

추가로 pipeline 실행 날짜를 `Asia/Seoul` 기준으로 한 번만 결정해 모든 단계와
최종 `topics.topic_date`가 같은 날짜를 사용하도록 했다. Topic 선정 전 전체
기사를 선추출하던 03:30 Raw extractor CronJob은 제거하고, selected article만
Daily topic pipeline 내부에서 원문 확보 대상으로 처리하도록 운영 흐름을
정리했다.

## 기존 문제

- `scripts/run_daily_topic_pipeline.py`가 embedding, clustering, 원문 확보,
  summary, 저장, report rendering과 runtime dependency 구성을 함께 담당했다.
- 단계별 입력과 결과 계약이 명시적인 타입으로 구분되지 않아 책임 경계와 실패
  범위를 파악하기 어려웠다.
- 각 단계가 날짜를 별도로 계산할 수 있는 구조였고, 2026년 6월 21일 04:00 KST
  실행에서 `topic_date=2026-06-20`이 저장되는 날짜 경계 문제가 있었다.
- 03:30 Raw extractor CronJob이 topic 선정 전에 원문을 선추출해 실제 summary에
  사용되지 않는 기사도 처리할 수 있었다.
- 초기 함수 분리 후에도 script가 1,000줄을 초과해 물리적인 코드 책임 분리가
  충분하지 않았다.
- 단계 결과, 외부 provider/DB adapter, 실패 정책이 코드만으로 즉시 드러나지
  않았다.

## 변경 내용

- 공통 실행 context 추가
  - `started_at_utc`
  - `started_at_local`
  - `business_timezone`
  - `pipeline_date`
  - `pipeline_date_source`
- 단계 결과 타입 추가
  - `EmbeddingStageResult`
  - `TopicSelectionResult`
  - `RawAcquisitionResult`
  - `TopicSaveResult`
- Daily topic pipeline을 네 stage로 분리했다.
- `app/services/daily_topic_pipeline/` 패키지로 실제 구현을 이동했다.
- 실행 script는 CLI, dependency 조립, stage orchestration과 출력 중심으로
  축소했다.
- 저장 원문은 우선 재사용하고, 원문이 없는 selected article만 추출하도록 했다.
- embedding, raw acquisition, topic summary의 실패 단위와 통계를 명확히 했다.
- `k8s/news-raw-extractor-cronjob.yaml`을 제거했다.
- Architecture와 CronJob runbook을 03:00 Collector → 04:00 Daily pipeline
  흐름으로 갱신했다.
- 승인 fix에 따라 핵심 함수와 결과 타입에 한글 docstring을 추가했다.

## 구현 상세

### 실행 context

`resolve_pipeline_context()`가 pipeline 시작 시각을 UTC로 정규화한 후
`Asia/Seoul`로 변환한다. 이때 결정한 `pipeline_date`를 네 stage와 save plan에
동일하게 전달한다.

UTC 날짜 경계에서도 local 날짜가 달라지지 않도록
`2026-06-20 19:00 UTC = 2026-06-21 04:00 KST` 조건을 테스트했다.

### 기사 후보 및 embedding 준비

기사 후보를 기존 방식으로 정규화하고 저장 embedding의 source hash를 기준으로
created, updated, reused를 구분한다.

- provider 또는 저장 처리 예외: 해당 article만 실패 처리
- 잘못된 반환 타입, status, vector 누락: stage 계약 위반으로 fail-fast
- 정상 기사와 vector: tuple로 묶어 clustering까지 순서 유지
- 정상 vector 2건 미만: 이후 clustering 및 저장 생략

### Clustering 및 topic 선정

기존 clustering 알고리즘, similarity threshold, topic 정렬, 최대 topic 수와
대표·관련 기사 선정 정책을 그대로 사용한다.

Selected topic의 대표·관련 기사만 다음 원문 확보 단계에 전달하며, reference
topic은 report에만 포함하고 원문 추출·summary·저장에서는 제외한다.

### Selected article 원문 확보

`raw_articles`에 저장된 원문을 먼저 재사용한다. Execute 모드에서는 원문이 없는
selected article 중 extraction target만 extractor에 전달한다. 추출 후에도
selected article ID만 다시 조회한다.

결과는 다음 상태로 분리한다.

- reused
- extracted
- failed
- missing

단일 기사 추출 실패는 다른 기사의 원문 사용과 topic summary 진행을 막지 않는다.

### Topic summary 및 저장

확보한 원문으로 topic별 summary input을 구성한다.

- 원문 부족: skipped
- summary provider 예외: 해당 topic만 failed
- 정상 summary: save plan 구성
- Execute 모드의 저장 후보: 하나의 write transaction으로 `topics`와
  `topic_articles` 저장

Topic 단위 summary 생성은 격리하지만, 최종 save executor의 transaction 실패는
호출자에게 전파해 부분 commit을 방지한다.

### 패키지 구조

```text
app/services/daily_topic_pipeline/
├── context.py
├── models.py
├── embedding_stage.py
├── topic_selection_stage.py
├── raw_acquisition_stage.py
├── summary_persistence_stage.py
├── runtime.py
└── reporting.py
```

`context.py`, `models.py`, `errors.py`는 stage 구현을 import하지 않는다. Script
import 시 DB 연결이나 provider 호출이 발생하지 않으며 기존 테스트 import
계약은 re-export로 유지했다.

## 대안 검토

### 기존 단일 파일에 함수만 분리

초기 변경량은 작지만 script가 1,000줄을 넘고 runtime adapter, 결과 타입,
reporting까지 한 파일에 남아 책임 분리가 코드 구조에 반영되지 않는다.

### Stage별 독립 script 또는 CronJob

단계별 재실행은 쉬워지지만 중간 상태 영속화, 실패 복구, schedule 조정과 운영
복잡도가 추가된다. 이번 작업의 목표보다 범위가 크므로 적용하지 않았다.

### Workflow engine 도입

Airflow, Argo Workflows, Celery 등은 단계 orchestration과 재시도를 제공하지만
현재 네 단계와 단일 일일 실행에는 과도하다. 신규 인프라와 운영 부담도 발생한다.

### 중간 결과 DB 저장

Pipeline 실행 이력과 단계 재시작에는 유리하지만 신규 table과 migration이
필요하다. Task의 DB schema 변경 금지 조건과 충돌하므로 제외했다.

### 원문 선추출 CronJob 유지

원문을 미리 확보할 수 있지만 topic에 선택되지 않은 기사까지 처리해 외부 요청과
저장 비용이 증가한다. Topic 선정 후 필요한 기사만 처리하는 방식이 현재 목표에
더 적합했다.

## 선택한 접근과 근거

- 하나의 process와 기존 실행 진입점을 유지했다.
  - 운영 schedule과 배포 단위를 바꾸지 않고 책임만 분리할 수 있다.
- Stage 구현은 전용 package로 이동하고 dataclass 결과를 전달했다.
  - 입력·출력과 실패 범위를 코드 구조에서 확인할 수 있다.
- Existing helper와 알고리즘을 재사용했다.
  - clustering, provider, prompt, 저장 계약의 회귀 위험을 줄였다.
- 공통 날짜를 pipeline 시작 시 한 번만 결정했다.
  - 자정 경계에서 단계별 날짜 불일치를 차단한다.
- Raw extraction을 topic 선정 이후로 이동했다.
  - 실제 summary 후보에 필요한 기사만 추출할 수 있다.
- 핵심 함수에만 한글 docstring을 추가했다.
  - 외부 부수 효과와 실패 정책은 명확히 하면서 단순 helper의 설명 중복을
    피했다.

## 트레이드오프

- 단계는 분리됐지만 같은 process에서 순차 실행되므로 특정 stage만 독립적으로
  재시작할 수 없다.
- 중간 결과를 DB에 저장하지 않아 process 종료 시 단계 상태를 복구할 수 없다.
- Topic summary provider 실패는 topic 단위로 격리하지만 최종 DB 저장은 하나의
  transaction이므로 저장 오류 시 전체 save plan이 rollback된다.
- Raw extractor CronJob 제거 후 04:00 pipeline이 원문 추출까지 담당하므로 전체
  실행 시간이 늘어날 수 있다.
- Script의 기존 import 계약을 유지하기 위한 re-export가 남아 있지만 테스트
  patch 경로와 기존 호출자 호환성을 보존한다.
- 파일 수는 증가했지만 각 파일의 책임과 크기가 제한되어 변경 영향 범위가
  명확해졌다.

## 테스트

관련 테스트:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

- 결과: 35 tests passed

전체 회귀:

```bash
python -m unittest discover -s tests
```

- 결과: 150 tests passed

정적 및 import 검증:

```bash
python -m compileall app scripts tests
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
```

- Compile 완료
- Script와 package import 성공
- Import 시 DB 연결 또는 provider 호출 없음

파일 크기:

```bash
wc -l \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/*.py
```

- 실행 진입점: 400줄
- Package 파일: 8–190줄
- 모든 대상 파일: 500줄 이하

추가 확인:

- 한글 docstring 적용 대상 확인 완료
- `git diff --check` 통과
- DB migration, router, `app/main.py`, dependency 변경 없음

## 운영 반영

현재 상태: **사람이 수행 필요 / pending**

Repository에서는 Raw extractor CronJob manifest를 제거했고 03:00 RSS Collector,
04:00 Daily topic pipeline schedule을 유지했다.

다음 항목은 수행하지 않았다.

- K3s의 기존 `news-raw-extractor` CronJob object 제거
- 변경된 application image 및 manifest 반영
- K3s rollout 또는 restart
- 04:00 scheduled pipeline 실행 확인
- Production API curl 확인
- 운영 DB의 `topics.topic_date` 확인

따라서 production deployment, rollout 및 production verification 완료를
주장하지 않는다.

## README 업데이트 판단

README는 수정하지 않았다.

Public API, 설치 방법, 개발 환경 실행 command와 사용자 기능 계약은 변경되지
않았다. 이번 변경은 내부 pipeline 구조와 운영 CronJob 흐름에 해당하므로
Architecture index, pipeline/K3s 세부 문서와 CronJob runbook에 반영하는 것이
적절하다고 판단했다.

## 확인 결과

- Daily topic pipeline의 네 책임이 별도 module과 결과 타입으로 구분됐다.
- 모든 stage가 동일한 `PipelineContext`를 사용한다.
- `Asia/Seoul` 날짜 경계 테스트가 통과했다.
- Existing embedding 재사용과 created/updated/failed 통계가 유지된다.
- Selected article만 원문 조회·추출 대상이 된다.
- Raw reused/extracted/failed/missing 상태가 구분된다.
- Embedding/raw 실패는 article 단위, summary 실패는 topic 단위로 격리된다.
- Raw extractor manifest 제거와 03:00/04:00 schedule 유지 테스트가 통과했다.
- Public API, DB schema, migration, dependency 변경은 없다.
- PR merge와 production 반영 여부는 확인되지 않았다.

## 이번 단계의 의미

이번 변경은 단순 함수 추출이 아니라 Daily topic pipeline의 책임과 데이터 전달
계약을 코드 구조에 반영한 작업이다.

기사 후보부터 최종 저장까지의 흐름을 stage 결과 객체로 연결하면서도 기존
알고리즘과 운영 진입점을 유지했다. 이를 통해 특정 단계의 정책이나 실패를
독립적으로 이해하고 테스트할 수 있게 됐으며, 불필요한 원문 선추출을 제거해
topic 선정 결과와 실제 처리 비용을 연결했다.

공통 `pipeline_date` 도입은 일일 pipeline에서 날짜가 단순 표시값이 아니라
기사 처리와 topic 저장을 묶는 업무 기준이라는 점을 명확히 했다.

## 포트폴리오용 요약

FastAPI/PostgreSQL 기반 뉴스 처리 시스템의 Daily topic pipeline을 네 단계의
service package로 리팩터링했다. 기존 embedding 재사용, clustering, summary와
저장 계약을 유지하면서 selected article만 원문 추출하도록 운영 흐름을
최적화했다. `Asia/Seoul` 기준 공통 실행 날짜를 도입해 날짜 경계 오류를
해결했고, article/topic 단위 실패 격리와 transaction 경계를 명시적인 결과
타입과 docstring으로 문서화했다. 관련 테스트 35개와 전체 테스트 150개를
통과했으며 Public API와 DB schema 변경 없이 구조 개선을 완료했다.

## 다음 단계 후보

- 사람이 기존 K3s `news-raw-extractor` CronJob object를 제거하고 변경 manifest를
  반영한다.
- 다음 04:00 scheduled pipeline의 completion과 elapsed time을 확인한다.
- 운영 log에서 `pipeline_date`, `business_timezone`, raw 처리 통계를 확인한다.
- 생성된 `topics.topic_date`가 실행일의 `Asia/Seoul` 날짜와 일치하는지
  확인한다.
- 운영 실행 시간이 증가한다면 extraction limit, timeout과 CronJob
  `activeDeadlineSeconds`를 별도 task에서 검토한다.
- 필요성이 확인되면 stage 실행 이력, 실패 단계 재실행, 중간 결과 영속화를
  별도 task로 설계한다.
- 사람이 PR merge 여부를 결정한다.
