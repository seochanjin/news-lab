# Task: Topic 관련 기사 보존과 Summary 근거 기사 분리

## Goal

현재 Daily topic pipeline의 `max_articles_per_topic`은 다음 두 역할을 동시에 제한한다.

```text
Topic에 연결해 저장하는 관련 기사 수
+
원문을 확보하고 Summary 생성에 사용하는 기사 수
```

이 때문에 하나의 cluster에 관련 기사 4건 이상이 있어도 Summary 입력 상한만큼의 기사만 `topic_articles`에 저장되고, 나머지 관련 기사 관계는 최종 결과에서 제외된다.

이번 작업에서는 기사 집합을 다음과 같이 분리한다.

```text
Topic 관련 기사
└── Summary 근거 기사
```

- **Topic 관련 기사**
  - 해당 Topic에 속한다고 판단된 기사
  - Daily 기준 최대 20건
  - 관련 기사 전체를 `topic_articles`에 저장
  - API의 기사 목록 및 `article_count`에 반영

- **Summary 근거 기사**
  - 관련 기사 중 Summary 생성에 사용하는 상위 기사
  - Daily 기준 최대 3건
  - 원문 확보 및 Summary provider 입력 대상으로 사용
  - 항상 Topic 관련 기사의 부분집합이어야 함

목표 흐름:

```text
기사 clustering
→ Topic 관련 기사 최대 20건 선정
→ Summary 근거 기사 최대 3건 선정
→ Summary 근거 기사에만 원문 확보
→ Summary 근거 기사만 Summary 생성에 사용
→ Topic 관련 기사 전체를 topic_articles에 저장
```

예:

```text
Cluster 관련 기사: 8건

topic_articles 저장: 8건
Summary 근거 기사: 3건
원문 확보 대상: 3건
Summary provider 입력: 3건
API article_count: 8
```

기존 embedding 재사용, clustering, 대표 기사, Summary provider, 실패 격리 및 Topic 저장 계약은 유지한다.

---

## Scope

### 1. 설정 분리

기존 기사 수 설정을 다음 두 설정으로 분리한다.

```text
max_related_articles_per_topic
max_summary_articles_per_topic
```

Daily 기본값:

```text
max_related_articles_per_topic = 20
max_summary_articles_per_topic = 3
```

다음 조건을 실행 초기에 검증한다.

```text
1 <= max_summary_articles_per_topic
max_summary_articles_per_topic <= max_related_articles_per_topic
```

CLI 권장 형식:

```bash
--max-related-articles-per-topic 20
--max-summary-articles-per-topic 3
```

기존 `--max-articles-per-topic` 사용처를 조사하고 다음 중 하나를 선택한다.

- deprecated alias로 유지
- 신규 argument로 CronJob과 문서를 함께 변경

선택한 호환 정책과 근거를 Verification 또는 Devlog에 기록한다.

### 2. 단계 결과 모델 분리

Topic 선정 결과에서 다음 두 집합을 구분한다.

```text
related_articles
summary_articles
```

반드시 다음 관계를 만족해야 한다.

```text
summary_articles ⊆ related_articles
```

대표 기사는 특별한 실패 조건이 없는 한 두 집합에 모두 포함한다.

단계 간 전달 모델에는 기존 처리에 필요한 다음 정보가 유지되어야 한다.

- 대표 기사
- 관련 기사 목록
- Summary 근거 기사 목록
- 기존 정렬 또는 관련도 정보
- 기사 및 source 식별자

### 3. Topic 관련 기사 선정

Clustering 결과에서 Topic에 연결할 관련 기사를 최대 설정값까지 선정한다.

기존 다음 계약은 유지한다.

- 대표 기사 선정 기준
- 관련도 및 similarity 기준
- 중복 기사 제외 정책
- 최대 Topic 수
- 실패 기사 격리
- 결정론적인 정렬

Cluster 기사 수가 상한보다 많으면 기존 정렬 기준에 따라 최대 20건을 선택한다.

### 4. Summary 근거 기사 선정

관련 기사 중 최대 설정값만 Summary 근거 기사로 선택한다.

선정 우선순위:

1. 대표 기사 포함
2. 관련도가 높은 기사
3. 서로 다른 source 우선
4. 중복 URL 및 사실상 같은 제목 제외
5. 기존 결정론적 tie-breaker 유지

새로운 범용 ranking framework는 도입하지 않는다.

현재 metadata로 출처 다양성을 안전하게 적용하기 어렵다면 기존 정렬을 유지하고 한계를 문서에 기록한다.

### 5. 원문 확보 대상 분리

Raw acquisition 단계에는 Summary 근거 기사만 전달한다.

```text
관련 기사 최대 20건
→ Summary 근거 기사 최대 3건
→ 최대 3건만 원문 확보
```

다음 기존 동작은 유지한다.

- 기존 원문 우선 재사용
- 원문이 없을 때만 신규 추출
- 기사 단위 실패 격리
- 기존 timeout 및 추출 제한
- 추출 실패 통계
- 다른 기사와 Topic 처리 지속

Summary 근거가 아닌 관련 기사 때문에 신규 원문 추출이 발생하면 안 된다.

### 6. Summary 입력 분리

Summary provider에는 Summary 근거 기사와 해당 원문만 전달한다.

다음 계약은 유지한다.

- Summary provider와 model
- Prompt의 기본 목적
- Topic별 실패 격리
- 원문 부족 시 기존 fallback
- Topic title, keywords, summary 저장 정책

관련 기사 전체가 Summary prompt에 포함되지 않아야 한다.

### 7. Topic 관련 기사 전체 저장

최종 저장 단계에서는 Summary 근거 기사만이 아니라 관련 기사 전체를 `topic_articles`에 저장한다.

유지할 계약:

- 대표 기사 관계
- 기사 순서 또는 rank
- 중복 관계 방지
- 기존 transaction 경계
- 기존 재실행 저장 정책
- Topic 및 article foreign key

Summary 근거 기사 여부를 저장하기 위한 신규 DB column이나 table은 추가하지 않는다.

### 8. 실행 통계

로그 또는 실행 결과에서 최소한 다음 수를 구분할 수 있어야 한다.

```text
관련 기사 수
Summary 근거 기사 수
원문 확보 대상 수
기존 원문 재사용 수
신규 원문 추출 수
저장된 topic_articles 수
```

기존 통계 key를 사용하는 코드와 테스트가 있다면 호환성을 우선한다.

### 9. API 회귀 확인

Endpoint와 response schema는 변경하지 않는다.

다음 데이터는 저장된 관련 기사 전체 기준으로 변경될 수 있다.

```text
article_count
source_count
관련 기사 목록
```

확인할 사항:

- Topic 상세 API가 저장된 관련 기사를 반환하는가
- 홈 API의 `article_count`가 전체 관련 기사 수를 반영하는가
- 대표 기사 표시가 유지되는가
- 기사 순서가 결정론적인가
- API field 이름과 타입이 유지되는가

프론트엔드 코드는 수정하지 않는다.

### 10. CronJob 및 문서 동기화

Daily pipeline CronJob이 기존 기사 수 argument를 사용한다면 신규 설정으로 변경한다.

초기 운영값:

```text
관련 기사 최대 20건
Summary 근거 기사 최대 3건
```

관련 architecture, runbook, CLI 실행 예시와 검증 항목을 실제 동작에 맞게 갱신한다.

K3s manifest 수정은 가능하지만 실제 apply, rollout 및 CronJob 실행은 하지 않는다.

### UNIT별 작업 경계

#### UNIT-01: 설정 및 단계 결과 모델 분리

- 기존 설정과 CLI argument 사용처를 조사한다.
- 관련 기사 상한과 Summary 기사 상한을 분리한다.
- 설정값 관계를 검증한다.
- 기존 argument 호환 정책을 결정한다.
- 단계 결과 모델에 관련 기사와 Summary 기사 집합을 구분한다.
- `summary_articles ⊆ related_articles` 계약을 테스트한다.
- 원문 확보, Summary provider 및 DB 저장 동작은 변경하지 않는다.

#### UNIT-02: 기사 선정 및 원문 확보 대상 분리

- 관련 기사를 설정 상한까지 결정론적으로 선정한다.
- Summary 근거 기사를 설정 상한까지 선정한다.
- 대표 기사 포함과 가능한 범위의 source 다양성을 적용한다.
- Raw acquisition에는 Summary 근거 기사만 전달한다.
- 기존 원문 재사용과 기사별 실패 격리를 유지한다.
- Summary 근거가 아닌 기사에는 신규 원문 추출이 발생하지 않아야 한다.
- 최종 Topic 저장 및 API 계약은 변경하지 않는다.

#### UNIT-03: Summary 입력 및 관련 기사 전체 저장

- Summary provider 입력을 Summary 근거 기사로 제한한다.
- 관련 기사 전체를 `topic_articles`에 저장한다.
- 대표 기사, rank, 중복 방지 및 transaction 계약을 유지한다.
- 관련 기사 수와 Summary 기사 수를 통계에서 구분한다.
- 저장 및 Summary 실패 격리 회귀 테스트를 추가한다.
- DB schema와 router는 변경하지 않는다.

#### UNIT-04: API, CronJob, 문서 및 전체 검증

- Topic 상세와 홈 API의 기존 schema를 회귀 검증한다.
- `article_count`, `source_count` 및 관련 기사 목록을 확인한다.
- Daily CronJob 설정을 관련 기사 20건, Summary 기사 3건으로 동기화한다.
- 관련 architecture, runbook 및 CLI 예시를 갱신한다.
- 전체 pytest, unittest, compileall 및 diff 검증을 수행한다.
- 변경 금지 영역에 수정이 없는지 확인한다.
- 실제 K3s apply, CronJob 실행 및 Production 검증은 하지 않는다.

---

## Do not change

- Embedding 생성 및 재사용 정책
- Embedding provider와 model
- Clustering 알고리즘
- Similarity threshold 기본값
- Daily `window_hours=24`
- 최대 Topic 수 기본값
- 대표 기사 선정의 핵심 의미
- Topic title 및 keyword 계약
- Summary provider와 model
- Summary prompt의 기본 목적
- DB schema 및 migration
- Supabase SQL
- FastAPI endpoint 경로
- API response field 이름과 타입
- 프론트엔드 코드
- 3-Day 및 Weekly pipeline
- Pipeline 실행 이력 table
- Stage별 CronJob 분리
- 자동 재시도 구조
- Git commit, push, PR 및 merge
- Docker image push
- Kubernetes apply, patch, delete, rollout 및 restart
- Production DB 및 API 접근
- Secret, credential, `.env`, kubeconfig

이번 작업을 이유로 다음을 추가하지 않는다.

```text
신규 DB column
신규 relation table
pgvector ANN 검색
clustering 알고리즘 최적화
Summary 근거 기사 영구 이력
```

---

## Expected files

실제 저장소 구조를 먼저 조사한 뒤 확정한다.

예상 주요 파일:

```text
scripts/run_daily_topic_pipeline.py
app/services/daily_topic_pipeline/models.py
app/services/daily_topic_pipeline/topic_selection_stage.py
app/services/daily_topic_pipeline/raw_acquisition_stage.py
app/services/daily_topic_pipeline/summary_persistence_stage.py
```

예상 테스트 영역:

```text
tests/test_run_daily_topic_pipeline.py
tests/test_topic_representatives.py
tests/test_save_topic_summaries.py
tests/test_topics_api.py
tests/test_daily_topic_pipeline_cronjob_manifest.py
```

예상 운영 문서 및 manifest:

```text
k8s/<daily-topic-pipeline-cronjob>.yaml
docs/architecture/<daily-topic-pipeline>.md
docs/runbooks/<daily-topic-pipeline>.md
```

변경 금지 영역:

```text
db/migrations/
app/routers/
app/main.py
```

Router 계약을 변경하지 않는 범위의 API 회귀 테스트 수정은 허용한다.

---

## DB changes

없음.

- 신규 table 없음
- 신규 column 없음
- migration 없음
- index 변경 없음
- Supabase SQL 없음

기존 `topic_articles`에 관련 기사 전체를 저장한다.

Summary 근거 기사 구분은 pipeline 실행 중 데이터 모델로만 관리한다.

---

## API changes

Endpoint 및 response schema 변경 없음.

예상 데이터 변화:

```text
article_count
→ 저장된 관련 기사 전체 수 반영

source_count
→ 관련 기사 전체의 source 기준으로 증가 가능

관련 기사 목록
→ 기존보다 더 많은 기사 반환 가능
```

다음은 유지한다.

- Endpoint path
- Query parameter
- Response field 이름
- Response field 타입
- 홈 API 기본 구조
- Topic 상세 API 기본 구조

---

## Test commands

### UNIT별 관련 테스트

각 UNIT에서는 해당 변경 범위의 테스트만 먼저 실행한다.

```bash
python -m pytest <관련 테스트 파일> -v
```

### 전체 pytest

```bash
python -m pytest
```

### unittest 호환

```bash
python -m unittest discover -s tests
```

### Python 정적 검증

```bash
python -m compileall app scripts tests
```

### Diff 검증

```bash
git diff --check
git diff --stat
git status --short --branch
```

### 변경 금지 영역

```bash
git diff -- \
  db/migrations \
  app/routers \
  app/main.py
```

실제 provider, Production DB, Production API 및 Kubernetes를 테스트에서 호출하지 않는다.

---

## Acceptance criteria

### 설정

- 관련 기사 상한과 Summary 근거 기사 상한이 분리된다.
- Daily 기본값은 각각 20건과 3건이다.
- Summary 상한이 관련 기사 상한보다 크면 실행 전에 차단된다.
- 기존 CLI argument 호환 정책이 명확하다.

### 관련 기사

- Cluster 관련 기사를 설정 상한까지 보존한다.
- 관련 기사 전체가 `topic_articles` 저장 대상이다.
- Summary 상한 때문에 Topic 관계가 유실되지 않는다.
- 대표 기사와 기존 정렬 계약이 유지된다.
- 동일 입력에서 동일 결과가 나온다.

### Summary 근거 기사

- Summary 근거 기사는 관련 기사의 부분집합이다.
- Daily에서는 최대 3건을 선택한다.
- 대표 기사가 기본적으로 포함된다.
- 가능한 범위에서 source 다양성을 반영한다.
- Summary provider에는 근거 기사만 전달한다.

### 원문 확보

- 신규 원문 추출은 Summary 근거 기사에만 수행된다.
- 기존 원문은 재사용한다.
- Summary에 사용하지 않는 관련 기사 때문에 추출이 발생하지 않는다.
- 기사별 실패 격리와 fallback이 유지된다.

### 저장 및 API

- 관련 기사 전체가 저장된다.
- DB schema 변경이 없다.
- API endpoint 및 schema 변경이 없다.
- `article_count`가 관련 기사 전체를 반영한다.
- 대표 기사 표시가 유지된다.

### 품질

- 관련 기사와 Summary 기사 수를 로그 또는 통계로 구분할 수 있다.
- 관련 문서와 CronJob 설정이 실제 동작과 일치한다.
- 전체 pytest와 unittest가 통과한다.
- 변경한 Python 코드와 테스트에는 공통 정책에 따른 한글 docstring이 있다.
- Production 작업을 실행하거나 완료했다고 기록하지 않는다.

---

## Notes

### 핵심 데이터 관계

```text
Topic 관련 기사
└── Summary 근거 기사
```

```text
summary_articles ⊆ related_articles
```

### Daily 초기값

```text
관련 기사 최대 20건
Summary 근거 기사 최대 3건
```

### DB 판단

Summary 근거 기사 여부는 이번 작업에서 DB에 저장하지 않는다.

향후 다음 요구가 생기면 별도 Task에서 설계한다.

- Summary 근거 추적
- Summary 재현
- Summary input hash
- UI의 근거 기사 표시
- 안전한 재실행

### 운영 적용

Agent는 코드, 테스트, manifest 및 문서 수정과 로컬 검증까지만 수행한다.

다음은 사람이 수행한다.

- PR merge
- Docker image build 및 push
- K3s manifest apply
- CronJob 수동 실행
- 실행 로그 확인
- DB 저장 결과 확인
- API 응답 확인

---

## Implementation Units

- [x] UNIT-01: 관련 기사와 Summary 근거 기사 설정 및 단계 결과 모델 분리
- [x] UNIT-02: 관련 기사와 Summary 근거 기사 선정과 원문 확보 대상 분리
- [x] UNIT-03: Summary 입력과 Topic 관련 기사 전체 저장 반영
- [x] UNIT-04: API, CronJob, 문서 동기화 및 전체 회귀 검증
