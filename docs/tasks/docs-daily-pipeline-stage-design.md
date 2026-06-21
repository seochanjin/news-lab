# Task: Daily topic pipeline 내부 단계 분리

## Goal

현재 `scripts/run_daily_topic_pipeline.py` 하나에 결합된 Daily topic pipeline을 역할별 단계로 분리한다.

현재 뉴스 처리 흐름은 다음과 같다.

```text
RSS Collector
→ 기사 제목·RSS 요약 저장
→ 제목·RSS 요약 기반 embedding 생성
→ embedding이 유사한 기사 clustering
→ 주요 topic 및 대표·관련 기사 선정
→ 선택된 기사의 원문 확보
→ 원문 기반 한국어 summary 생성
→ topics / topic_articles 저장
```

RSS Collector는 이미 별도 CronJob으로 동작하므로 이번 작업에서 변경하지 않는다.

이번 작업에서는 Daily topic pipeline 내부를 다음 네 단계로 분리한다.

```text
1. 기사 후보 및 Embedding 준비
2. 유사 기사 Clustering 및 Topic 선정
3. 선택 기사 원문 확보
4. Topic Summary 생성 및 저장
```

각 단계는 하나의 역할만 담당하고, 명확한 입력을 받아 결과를 반환하도록 한다.

기존 03:30 `news-raw-extractor` CronJob은 제거한다. 원문 추출은 topic과 기사가 선정된 이후 Daily topic pipeline 내부에서 selected article만 대상으로 수행한다.

기존 03:00 RSS Collector와 04:00 Daily topic pipeline 실행 시각, 데이터 처리 결과, DB schema 및 Public API는 유지한다.

코드 수정 후 주요 단계와 정책을 이해할 수 있도록 필요한 주석을 작성한다. 코드 내용을 그대로 반복하는 불필요한 주석은 추가하지 않는다.

---

## Scope

### 1. 기사 후보 및 Embedding 준비

다음 책임을 하나의 단계로 분리한다.

```text
최근 기사 후보 조회
→ title + rss_summary 기반 embedding 입력 생성
→ 저장된 article embedding 조회
→ source hash가 같으면 기존 embedding 재사용
→ embedding이 없거나 입력이 변경됐으면 생성 또는 갱신
→ 정상 기사와 vector 결과 반환
```

이 단계는 기사 후보와 embedding을 준비하는 역할만 수행한다.

기존 정책을 유지한다.

- embedding 실패는 article 단위로 격리한다.
- 정상 article과 vector의 대응 관계를 유지한다.
- provider 반환 계약 위반은 즉시 실패 처리한다.
- 정상 vector가 2건 미만이면 이후 단계를 실행하지 않는다.
- created, updated, reused, failed 통계를 유지한다.

예상 결과:

```text
EmbeddingStageResult
- articles_with_embeddings
- failed_article_ids
- created_count
- updated_count
- reused_count
- failed_count
```

### 2. 유사 기사 Clustering 및 Topic 선정

Embedding 단계 결과를 입력으로 받아 다음을 수행한다.

```text
기사 embedding 유사도 비교
→ 비슷한 기사끼리 cluster 생성
→ 각 cluster를 topic 후보로 구성
→ topic 중요도 또는 선택 기준 적용
→ 최대 topic 수 선택
→ 대표 기사와 관련 기사 선정
```

이 단계는 비슷한 기사를 묶고 주요 topic을 선택하는 역할만 수행한다.

원문 추출, summary 생성 및 DB 저장은 수행하지 않는다.

예상 결과:

```text
TopicSelectionResult
- selected_topics
- representative_article_ids
- related_article_ids
- selected_article_ids
- cluster_count
- selected_topic_count
```

선택된 topic이 없으면 이후 단계를 정상적으로 종료한다.

Clustering 알고리즘, similarity threshold 및 최대 topic 수는 변경하지 않는다.

### 3. 선택 기사 원문 확보

Topic 선정 결과에 포함된 기사만 대상으로 원문을 준비한다.

```text
selected article 확인
→ raw_articles에 저장된 원문 조회
→ 저장된 원문이 있으면 재사용
→ 원문이 없으면 해당 기사만 extraction
→ 추출 결과와 실패 기사 반환
```

이 단계는 선택된 기사의 원문을 확보하는 역할만 수행한다.

선택되지 않은 기사는 새로 원문을 추출하지 않는다.

기존 03:30 `news-raw-extractor` CronJob이 수행하던 선추출은 제거한다. 앞으로 원문 추출은 clustering과 topic 선정이 완료된 후 selected article에 대해서만 수행한다.

기존 `raw_articles`에 저장된 원문은 계속 재사용한다. 저장된 원문이 없는 selected article만 Daily topic pipeline에서 추출한다.

다음 통계를 유지하거나 추가한다.

```text
selected_article_count
raw_reused_count
raw_extracted_count
raw_failed_count
raw_missing_count
```

예상 결과:

```text
RawAcquisitionResult
- article_raw_texts
- reused_article_ids
- extracted_article_ids
- failed_article_ids
- summary_ready_topics
```

단일 기사 원문 추출 실패는 해당 기사만 실패 처리한다.

Topic summary에 필요한 원문이 부족하면 해당 topic을 skip할 수 있다.

### 4. Topic Summary 생성 및 저장

Topic 선정 결과와 확보된 기사 원문을 입력으로 받아 다음을 수행한다.

```text
topic별 대표·관련 기사 원문 구성
→ 한국어 topic title 생성
→ 한국어 summary 생성
→ keywords 생성
→ topic save plan 생성
→ topics 저장
→ topic_articles 연결 저장
```

이 단계는 topic summary를 생성하고 최종 결과를 저장하는 역할만 수행한다.

기존 summary provider, model, prompt 정책과 저장 방식을 유지한다.

예상 결과:

```text
TopicSaveResult
- generated_topic_count
- saved_topic_count
- skipped_topic_count
- failed_topic_count
- saved_topic_ids
```

특정 topic summary 생성 또는 저장 실패는 가능한 범위에서 해당 topic 단위로 격리한다.

### 5. 공통 Pipeline Date 전달

Pipeline 실행 시작 시 기준 날짜를 한 번 결정하고 각 단계에 전달한다.

기본 timezone은 `Asia/Seoul`을 사용한다.

```text
pipeline_date
business_timezone
started_at_utc
started_at_local
pipeline_date_source
```

각 단계가 내부에서 `date.today()` 또는 `datetime.now()`를 다시 호출해 서로 다른 날짜를 결정하지 않도록 한다.

기사 후보 조회와 최종 `topic_date` 저장은 동일한 `pipeline_date`를 사용한다.

2026년 6월 21일 04:00 KST 실행에서 `topic_date=2026-06-20`이 생성된 현상은 공통 날짜 전달 과정에서 함께 수정한다.

기존 DB에 저장된 topic 날짜는 수정하지 않는다.

### 6. 기존 Pipeline 실행 진입점 유지

기존 실행 진입점은 유지한다.

진입점은 역할별 단계 함수를 기존 순서대로 호출하고 결과를 다음 단계에 전달한다.

예상 형태:

```python
pipeline_date = resolve_pipeline_date(...)

embedding_result = prepare_article_embeddings(
    pipeline_date=pipeline_date,
)

topic_result = cluster_and_select_topics(
    embedding_result=embedding_result,
)

raw_result = acquire_selected_article_raw_texts(
    topic_result=topic_result,
)

save_result = summarize_and_save_topics(
    pipeline_date=pipeline_date,
    topic_result=topic_result,
    raw_result=raw_result,
)
```

별도의 workflow engine, 상태 관리자 또는 orchestration 계층은 도입하지 않는다.

기존 helper 함수는 가능한 범위에서 재사용한다.

### 7. Raw extractor CronJob 제거

03:30 `news-raw-extractor` CronJob을 K3s 배포 대상에서 제거한다.

다음 항목을 함께 정리한다.

- Raw extractor CronJob manifest 제거 또는 배포 대상 제외
- Raw extractor CronJob 전용 manifest 테스트 수정 또는 제거
- ARCHITECTURE 및 CronJob Runbook의 실행 흐름 수정
- 운영 흐름에서 03:30 실행 항목 제거
- Daily topic pipeline이 selected article 원문 추출을 담당한다는 설명 추가

Raw extraction 함수나 기존 저장 구조는 삭제하지 않는다. Daily topic pipeline의 selected article 원문 확보 단계에서 계속 재사용한다.

---

## Do not change

다음은 이번 작업에서 변경하지 않는다.

- RSS Collector 로직
- RSS source 목록
- 03:00 RSS Collector CronJob 및 schedule
- 04:00 Daily topic pipeline CronJob 및 schedule
- 신규 CronJob 추가
- stage별 독립 script 또는 CronJob
- 신규 DB table
- DB column, index 및 migration
- clustering 알고리즘
- similarity threshold
- 최대 topic 수
- embedding provider 및 model
- summary provider 및 model
- summary prompt 정책
- raw extraction 알고리즘
- Public API
- FastAPI router
- Frontend
- 운영 Secret 및 provider 설정
- 기존 topic 및 raw article 데이터

---

## Expected files

주요 수정 대상:

```text
scripts/run_daily_topic_pipeline.py
tests/test_run_daily_topic_pipeline.py
k8s/<raw-extractor-cronjob-manifest>
tests/<raw-extractor-cronjob-manifest-test>
docs/ARCHITECTURE.md
docs/runbooks/<cronjob-runbook>
docs/tasks/<task-name>.md
docs/verification/<task-name>.md
docs/pr/<task-name>.md
docs/devlog/<task-name>.md
```

실제 파일명은 저장소 구조를 확인해 적용한다.

필요한 경우 역할별 함수나 결과 타입을 별도 내부 모듈로 분리할 수 있다.

```text
app/services/daily_topic_pipeline.py
```

단순 함수 분리로 충분하다면 신규 파일을 만들지 않는다.

다음 영역은 변경하지 않는다.

```text
db/migrations/
app/routers/
app/main.py
requirements.txt
```

---

## DB changes

없음.

신규 table, column, index 및 migration을 추가하지 않는다.

기존 table만 사용한다.

```text
articles
article_embeddings
raw_articles
extraction_runs
topics
topic_articles
```

03:30 CronJob을 제거해도 기존 `raw_articles`와 `extraction_runs` 데이터는 삭제하지 않는다.

단계별 결과는 동일한 Python process 안에서 객체로 전달한다.

Pipeline 실행 상태나 중간 결과를 DB에 저장하는 기능은 이번 범위에 포함하지 않는다.

---

## API changes

없음.

다음 Public API의 request 및 response 계약을 유지한다.

```text
/topics
/topics/{id}
/topics/home
```

역할별 단계 결과는 pipeline 내부에서만 사용하며 API에 노출하지 않는다.

---

## Test commands

관련 테스트:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

Raw extractor CronJob manifest 관련 테스트가 별도로 존재한다면 변경 후 함께 실행한다.

전체 회귀:

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

변경 금지 영역 확인:

```bash
git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  requirements.txt
```

최소 테스트 항목:

- 기사 후보와 embedding 결과의 대응 관계가 유지되는지
- embedding created, updated, reused, failed 통계가 유지되는지
- 정상 vector 2건 미만이면 후속 단계가 실행되지 않는지
- embedding이 유사한 기사끼리 기존과 동일하게 clustering되는지
- topic과 대표·관련 기사 선택 결과가 유지되는지
- selected article만 원문 확보 대상이 되는지
- 기존 raw text 재사용과 신규 extraction이 구분되는지
- 원문 확보 실패가 article 단위로 격리되는지
- 원문이 부족한 topic이 정상 skip되는지
- summary와 topic 저장 결과가 기존과 동일한지
- 모든 단계가 동일한 `pipeline_date`를 사용하는지
- UTC 날짜 경계에서도 Asia/Seoul 기준 날짜가 저장되는지
- 단계 분리 전후 pipeline 반환 통계가 회귀하지 않는지
- Raw extractor CronJob이 배포 대상에서 제거됐는지
- Daily topic pipeline CronJob의 04:00 schedule이 유지되는지
- 문서에서 03:30 Raw extractor 실행 설명이 제거됐는지

Verification 문서에는 실제 실행한 명령과 실제 결과만 기록한다.

K3s manifest 제거와 운영 반영은 사람이 직접 수행한다.

---

## Acceptance criteria

- Daily topic pipeline이 네 개의 역할별 단계로 분리되어 있다.
- 각 단계가 하나의 책임만 수행한다.
- 각 단계의 입력과 결과가 코드에서 명확히 구분되어 있다.
- 기사 후보와 embedding 준비가 별도 단계로 분리되어 있다.
- 유사 기사 clustering과 topic 선정이 별도 단계로 분리되어 있다.
- 선택 기사 원문 확보가 별도 단계로 분리되어 있다.
- topic summary 생성과 저장이 별도 단계로 분리되어 있다.
- selected article만 신규 원문 추출 대상이 된다.
- 기존 저장 raw text를 우선 재사용한다.
- 기존 embedding 생성·재사용 정책이 유지된다.
- 기존 clustering 및 topic 선택 정책이 유지된다.
- 기존 summary 및 topic 저장 정책이 유지된다.
- pipeline 시작 시 `pipeline_date`가 한 번만 결정된다.
- 모든 단계가 동일한 `pipeline_date`를 사용한다.
- Asia/Seoul 기준 `topic_date`가 저장된다.
- 03:30 Raw extractor CronJob이 배포 대상에서 제거되어 있다.
- 03:00 RSS Collector와 04:00 Daily topic pipeline schedule이 유지된다.
- Daily topic pipeline이 selected article 원문 확보를 담당한다.
- ARCHITECTURE와 Runbook에 변경된 운영 흐름이 반영되어 있다.
- 신규 DB table과 migration이 없다.
- Public API 변경이 없다.
- 관련 테스트와 전체 회귀 테스트가 통과한다.
- migration, router 및 dependency 영역에 변경이 없다.

---

## Checklist

- [x] Pipeline 실행 컨텍스트와 네 단계 결과 타입을 정의한다.
- [x] 기사 후보 및 embedding 준비 단계를 분리한다.
- [x] clustering 및 topic 선정 단계를 분리한다.
- [x] selected article 원문 확보 단계를 분리한다.
- [x] topic summary 생성 및 저장 단계를 분리한다.
- [x] Asia/Seoul 기준 `pipeline_date`를 한 번 결정해 저장 단계까지 전달한다.
- [x] Raw extractor CronJob을 배포 대상에서 제거한다.
- [x] Architecture와 CronJob runbook을 변경된 운영 흐름에 맞게 갱신한다.
- [x] 관련 테스트와 전체 회귀 검증을 완료한다.
- [x] 변경 금지 영역에 수정이 없는지 확인한다.
- [ ] 운영 manifest 반영과 production verification을 사람 수행 항목으로 남긴다.
  - 상태: 사람이 수행 필요
  - 남은 작업: 기존 K3s `news-raw-extractor` object 제거, 변경 manifest 반영,
    04:00 scheduled pipeline 및 `topics.topic_date` 운영 확인

---

## Notes

57차의 주목적은 새로운 실행 관리 시스템을 만드는 것이 아니다.

현재 하나의 파일에 섞여 있는 다음 책임을 분리하고, 원문 추출 시점을 topic 선정 이후로 옮기는 작업이다.

```text
기사와 embedding 준비
→ 비슷한 기사 묶기
→ 주요 topic과 기사 선택
→ selected article 원문 확보
→ 원문 기반 summary와 topic 저장
```

변경 후 운영 흐름:

```text
03:00 RSS Collector
04:00 Daily Topic Pipeline
      ├─ 기사 후보 및 Embedding 준비
      ├─ Clustering 및 Topic 선정
      ├─ Selected article 원문 확보
      └─ Topic Summary 생성 및 저장
```

기존 03:30 Raw extractor CronJob은 제거한다.

후속 작업에서 필요할 경우 다음을 별도로 검토한다.

- 역할별 파일 분리
- 독립 실행 script
- CronJob 추가 분리
- 실패 단계 재실행
- 중간 결과 영속화
- pipeline 실행 이력 저장
