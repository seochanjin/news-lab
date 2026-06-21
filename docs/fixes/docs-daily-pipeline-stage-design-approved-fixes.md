# Approved Fixes: Daily topic pipeline 분리 설계

## Approved Fixes

### 1. Daily topic pipeline을 역할별 패키지로 분리

현재 단계별 함수는 분리되었지만 대부분의 구현이 여전히 `scripts/run_daily_topic_pipeline.py` 한 파일에 남아 있어 파일 크기가 1,000줄을 초과한다.

이번 작업의 목적은 함수 이름만 분리하는 것이 아니라 다음 책임을 코드 구조에서도 명확하게 구분하는 것이다.

```text
기사 후보 및 Embedding 준비
→ Clustering 및 Topic 선정
→ Selected article 원문 확보
→ Topic Summary 생성 및 저장
```

따라서 각 단계 구현을 전용 패키지 또는 모듈로 이동한다.

권장 구조:

```text
scripts/
└── run_daily_topic_pipeline.py

app/services/daily_topic_pipeline/
├── __init__.py
├── context.py
├── models.py
├── embedding_stage.py
├── topic_selection_stage.py
├── raw_acquisition_stage.py
└── summary_persistence_stage.py
```

실제 파일명은 기존 프로젝트의 service 및 module naming convention에 맞게 조정할 수 있다.

### 2. 실행 진입점의 책임 축소

`scripts/run_daily_topic_pipeline.py`는 다음 책임만 담당하도록 축소한다.

- 실행 인자 및 환경값 처리
- 공통 `pipeline_date`와 context 생성
- 기존 의존성 생성
- 역할별 단계 함수 호출
- 단계 간 결과 전달
- 최종 처리 결과 및 오류 출력
- process exit code 결정

다음 구현 세부사항은 실행 진입점에 남기지 않는다.

- embedding 생성 및 저장 로직
- clustering 계산
- topic 및 기사 선택 로직
- raw article 조회와 추출 로직
- summary provider 호출
- topic 및 topic_articles 저장 세부 로직

### 3. 단계별 결과 타입 분리

단계 사이에서 전달되는 결과 타입을 공용 module로 이동한다.

대상 예시:

```text
EmbeddingStageResult
TopicSelectionResult
RawAcquisitionResult
TopicSaveResult
PipelineContext
```

각 결과 타입은 해당 단계의 출력 계약만 표현해야 한다.

단계 구현이 다음 단계의 내부 구현 세부사항에 직접 의존하지 않도록 한다.

### 4. 파일 크기 제한 적용

이번 리팩터링으로 수정하거나 추가하는 Daily topic pipeline 관련 Python 파일은 원칙적으로 파일당 500줄 이하로 유지한다.

적용 대상:

```text
scripts/run_daily_topic_pipeline.py
app/services/daily_topic_pipeline/*.py
```

단, 줄 수를 맞추기 위해 의미 없는 wrapper, 단일 함수 전용 파일 또는 과도하게 작은 module을 만들지 않는다.

500줄을 초과해야 하는 불가피한 사유가 있다면 다음 내용을 PR 문서에 기록한다.

- 초과한 파일
- 초과 이유
- 추가 분리가 부적절한 이유
- 후속 분리 계획

### 5. 기존 동작과 계약 유지

파일 분리 과정에서 다음 동작을 변경하지 않는다.

- 기사 후보 조회 조건
- embedding 생성·갱신·재사용 정책
- article 단위 embedding 실패 격리
- clustering 알고리즘
- similarity threshold
- 최대 topic 수
- 대표·관련 기사 선택 정책
- selected article만 원문 추출하는 정책
- 기존 raw text 우선 재사용
- article 단위 원문 추출 실패 격리
- summary provider, model 및 prompt
- topic 및 topic_articles 저장 정책
- `Asia/Seoul` 기준 공통 `pipeline_date`
- 기존 반환 통계와 로그의 의미
- Public API 및 DB schema

### 6. Import 및 의존성 구조 검증

패키지 분리 후 다음 문제가 발생하지 않도록 한다.

- stage module 간 순환 import
- module import 시 DB 연결 또는 provider 호출
- 전역 mutable state 추가
- script 경로에서만 동작하는 상대 import
- test patch 경로 변경으로 인한 격리 테스트 무력화

공통 타입과 context는 하위 stage module을 import하지 않는 독립 module에 배치한다.

### 7. 핵심 함수와 결과 타입의 역할을 한글 docstring으로 문서화

패키지 분리 이후 물리적인 구조는 명확해졌지만, 각 함수가 pipeline에서 담당하는 역할과 단계 사이의 데이터 전달 계약을 코드만 보고 바로 파악하기 어렵다.

핵심 함수와 결과 타입에 한글 docstring을 추가한다.

적용 대상:

- `PipelineContext` 생성 및 날짜 결정 함수
- 기사 후보 및 embedding 준비 단계의 진입 함수
- clustering 및 topic 선정 단계의 진입 함수
- selected article 원문 확보 단계의 진입 함수
- topic summary 생성 및 저장 단계의 진입 함수
- DB, embedding provider, summary provider, 원문 extractor와 연결되는 주요 adapter
- transaction 또는 부분 실패 격리를 담당하는 주요 함수
- `PipelineContext`, `EmbeddingStageResult`, `TopicSelectionResult`, `RawAcquisitionResult`, `TopicSaveResult`
- 함수명만으로 책임이나 부수 효과를 파악하기 어려운 핵심 helper

각 docstring에는 필요한 범위에서 다음 내용을 포함한다.

- 함수 또는 클래스의 책임
- 주요 입력값의 의미
- 반환값과 다음 단계에서 사용하는 데이터
- article 단위, topic 단위 또는 stage 단위 실패 정책
- DB 저장, provider 호출 등 주요 부수 효과
- 재사용, skip, fail-fast 등 호출자가 알아야 할 제약

예시:

```python
def prepare_article_embeddings(...):
    """기사 후보를 조회하고 clustering에 사용할 embedding을 준비한다.

    저장된 embedding의 source hash가 현재 입력과 같으면 재사용하고,
    없거나 변경된 경우에만 새 embedding을 생성하거나 갱신한다.

    단일 기사 처리 실패는 해당 기사에 한정해 격리한다.
    provider 반환 타입, status 또는 vector 계약 위반은 stage 오류로 전파한다.

    Returns:
        정상 기사와 vector의 대응 관계 및 created, updated, reused,
        failed 처리 통계를 포함한 EmbeddingStageResult.
    """
```

코드 내부의 특정 판단이나 순서 제약을 설명해야 하는 경우에만 인라인 주석을 추가한다.

예시:

```python
# article과 vector는 동일한 인덱스를 유지해야 clustering 결과를
# 원본 기사에 안전하게 다시 연결할 수 있다.
```

다음과 같은 주석은 추가하지 않는다.

- 함수 이름이나 코드 내용을 그대로 한국어로 반복하는 주석
- 모든 코드 줄을 설명하는 주석
- 한 줄짜리 단순 helper에 대한 장문의 설명
- 타입 힌트로 충분히 알 수 있는 매개변수 설명의 반복
- 실제 구현과 쉽게 불일치할 수 있는 상세 실행 절차 복제
- 아직 구현되지 않은 기능이나 정책에 대한 설명

docstring과 주석은 현재 코드의 실제 동작과 일치해야 한다.

---

## Rejected or Deferred Suggestions

### 단계별 독립 실행 및 CronJob 분리

이번 수정에서는 단계별 script, subcommand 또는 CronJob을 추가하지 않는다.

단계들은 여전히 하나의 Daily topic pipeline process 안에서 기존 순서대로 실행한다.

### 중간 결과 DB 영속화

다음 table 또는 상태 저장 구조는 추가하지 않는다.

```text
pipeline_runs
pipeline_stage_runs
topic_candidate_runs
```

단계 간 결과는 동일 process 안에서 Python 객체로 전달한다.

### Workflow engine 도입

다음 도구는 도입하지 않는다.

- Airflow
- Argo Workflows
- Celery
- Kafka
- RabbitMQ
- 별도 orchestration framework

### 기존 알고리즘 변경

파일 분리와 문서화 과정에서 clustering, topic selection, raw extraction, summary 및 저장 알고리즘을 변경하지 않는다.

### 전역적인 500줄 제한

파일당 500줄 제한은 이번 Daily topic pipeline 관련 파일에만 적용한다.

저장소 전체 Python 파일에 대한 일괄 제한이나 무관한 파일 리팩터링은 이번 범위에서 제외한다.

### 모든 함수에 장문의 주석 추가

모든 함수와 단순 helper에 상세 주석을 강제하지 않는다.

핵심 단계, 결과 계약, 외부 시스템 연결, 실패 정책 또는 부수 효과가 있는 함수만 문서화한다.

---

## Applied Changes

현재까지 실제 반영된 변경:

- Approved Fix 1, 3:
  - `app/services/daily_topic_pipeline/context.py`에 공통 실행 context 생성을 이동했다.
  - `app/services/daily_topic_pipeline/models.py`에 `PipelineContext`,
    `EmbeddingStageResult`, `TopicSelectionResult`, `RawAcquisitionResult`,
    `TopicSaveResult`를 이동했다.
  - `embedding_stage.py`, `topic_selection_stage.py`,
    `raw_acquisition_stage.py`, `summary_persistence_stage.py`에 네 단계 구현을 각각 이동했다.
- Approved Fix 2:
  - `scripts/run_daily_topic_pipeline.py`를 CLI 검증, context와 provider 생성,
    단계 호출과 결과 조립, report/JSON 출력 중심의 진입점으로 축소했다.
  - embedding storage, raw text loader, save executor adapter는 `runtime.py`로 이동했다.
  - report rendering은 `reporting.py`로 이동했다.
- Approved Fix 4:
  - `scripts/run_daily_topic_pipeline.py`와 package 내 모든 Python 파일이
    500줄 이하임을 확인했다.
- Approved Fix 5:
  - 기존 script import 계약을 re-export로 유지해 기존 테스트 patch 경로와 호출 계약을 유지했다.
  - 관련 테스트와 전체 회귀 테스트가 통과했다.
- Approved Fix 6:
  - `context.py`, `models.py`, `errors.py`는 stage 구현을 import하지 않는다.
  - package와 script 직접 import 검증이 통과했고 import 시 DB 연결이나 provider 호출이 발생하지 않았다.
- Documentation:
  - `docs/architecture/pipeline.md`에 실제 package 구조와 단방향 의존성 원칙을 반영했다.

- Approved Fix 7:
  - `resolve_pipeline_context()`에 UTC 정규화, Asia/Seoul 업무 날짜 결정,
    모든 stage와 topic 저장에서 공유하는 계약을 한글 docstring으로 기록했다.
  - `PipelineContext`, `EmbeddingStageResult`, `TopicSelectionResult`,
    `RawAcquisitionResult`, `TopicSaveResult`에 다음 단계가 사용하는 데이터와
    실패·skip 통계의 의미를 기록했다.
  - 네 stage 진입 함수에 책임, 주요 입력과 반환 결과, article/topic/stage 단위
    실패 정책, provider·extractor·DB 부수 효과를 기록했다.
  - `acquire_pipeline_embeddings()`에 article 단위 예외 격리와 provider 반환
    계약 위반 fail-fast 경계를 기록했다.
  - `runtime.py`의 embedding, raw text, save adapter에 read-only/write
    transaction과 실제 DB/provider 부수 효과 조건을 기록했다.
  - `build_pipeline()`, `_run()`, `_load_candidates()`,
    `_create_extraction_executor()`에 orchestration 및 외부 연결 경계를 기록했다.
  - 단순 formatting, 정렬, ID 추출 helper에는 장문 docstring을 추가하지 않았다.

---

## Apply Checklist

- [x] Approved Fix 1: 역할별 package/module 분리
- [x] Approved Fix 2: 실행 진입점 책임 축소
- [x] Approved Fix 3: 공통 context와 단계 결과 타입 분리
- [x] Approved Fix 4: 관련 Python 파일당 500줄 이하 확인
- [x] Approved Fix 5: 기존 동작과 계약 회귀 확인
- [x] Approved Fix 6: import 및 의존성 구조 확인
- [x] Approved Fix 7: 핵심 함수와 단계 결과 타입의 한글 docstring 작성

---

## Verification Required

### Docstring 적용 확인

다음 대상에 한글 docstring이 작성되어 있는지 확인한다.

- 네 개 stage 진입 함수
- `PipelineContext` 생성 및 날짜 결정 함수
- 핵심 결과 dataclass
- 외부 provider 및 DB 연결 adapter
- 부분 실패 격리와 transaction 경계를 담당하는 함수

검색 명령:

```bash
rg -n '"""' \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline
```

수동 확인 항목:

- 책임, 입력, 반환값이 실제 코드와 일치하는지
- article, topic, stage 단위 실패 정책이 올바르게 설명되어 있는지
- DB 쓰기와 외부 provider 호출 부수 효과가 명시되어 있는지
- 재사용, skip, fail-fast 조건이 실제 구현과 일치하는지
- 모든 코드 줄을 번역하는 과도한 주석이 추가되지 않았는지
- 단순 helper에 불필요한 장문 docstring이 추가되지 않았는지

### 파일 크기 확인

```bash
wc -l \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/*.py
```

Docstring 추가 후에도 Daily topic pipeline 관련 각 Python 파일이 500줄 이하인지 확인한다.

### 관련 테스트

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

### 전체 회귀

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
```

### Import 검증

```bash
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
```

### 변경 품질 확인

```bash
git diff --check
git diff --stat
git status --short --branch
```

### 변경 금지 영역 확인

```bash
git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  requirements.txt
```

### 필수 회귀 항목

- 모든 stage가 동일한 `pipeline_date`를 사용하는지
- embedding created, updated, reused, failed 통계가 유지되는지
- 정상 vector 2건 미만 시 후속 단계가 실행되지 않는지
- clustering과 topic 선택 결과가 기존과 동일한지
- selected article만 원문 추출 대상으로 사용하는지
- 기존 raw text 재사용과 신규 extraction이 구분되는지
- article 단위 raw extraction 실패가 격리되는지
- topic 단위 summary 실패가 격리되는지
- topic 저장 결과와 반환 통계가 유지되는지
- Raw extractor CronJob 제거 상태가 유지되는지
- 전체 테스트가 통과하는지

Verification 문서에는 실제 실행한 명령과 실제 결과만 기록한다.
