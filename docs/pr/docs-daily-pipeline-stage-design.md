# Daily topic pipeline 내부 단계 분리

## 작업 내용

- 하나의 함수와 파일에 결합되어 있던 Daily topic pipeline을 다음 네 단계로
  분리했다.
  1. 기사 후보 및 embedding 준비
  2. 유사 기사 clustering 및 topic 선정
  3. selected article 원문 확보
  4. topic summary 생성 및 저장
- Pipeline 시작 시 `Asia/Seoul` 기준 실행 날짜를 한 번 결정하고 모든 단계와
  최종 `topics.topic_date` 저장에 동일한 `pipeline_date`를 전달하도록 했다.
- 03:30 `news-raw-extractor` CronJob manifest를 제거하고, topic 선정 이후
  selected article만 Daily topic pipeline에서 원문 확보 대상으로 처리하도록
  운영 흐름을 변경했다.
- 승인된 fix에 따라 단계 구현, 공통 context와 결과 타입, runtime adapter,
  report rendering을 `app/services/daily_topic_pipeline/` 패키지로 분리했다.

## 주요 변경 사항

- `scripts/run_daily_topic_pipeline.py`
  - CLI 인자 검증, 실행 context와 dependency 생성, 단계 호출, 최종 결과 출력
    중심의 진입점으로 축소했다.
  - 기존 script import와 테스트 patch 계약은 re-export로 유지했다.
- `app/services/daily_topic_pipeline/`
  - `context.py`: UTC 시작 시각과 `Asia/Seoul` 업무 날짜 결정
  - `models.py`: 단계 사이에 전달하는 context와 결과 dataclass
  - `embedding_stage.py`: embedding 생성·갱신·재사용 및 article 단위 실패 격리
  - `topic_selection_stage.py`: clustering, topic 정렬, 대표·관련 기사 선정
  - `raw_acquisition_stage.py`: selected article의 저장 원문 재사용과 신규 추출
  - `summary_persistence_stage.py`: topic별 summary 생성, skip/failure 처리,
    save plan 및 저장 호출
  - `runtime.py`: embedding storage, raw text 조회, topic 저장 transaction adapter
  - `reporting.py`: 기존 pipeline report rendering
- 기존 동작 유지
  - embedding provider 반환 계약 위반은 fail-fast한다.
  - embedding 및 raw extraction 실행 실패는 article 단위로 격리한다.
  - summary provider 실패는 topic 단위로 격리한다.
  - 정상 vector가 2건 미만이면 clustering과 후속 저장을 건너뛴다.
  - clustering 알고리즘, threshold, 최대 topic 수, provider/model/prompt와 저장
    정책은 변경하지 않았다.
- 결과 통계
  - embedding created/updated/reused/failed
  - selected article 수
  - raw reused/extracted/failed/missing
  - topic generated/saved/skipped/failed
  - `pipeline_date`, `business_timezone`, 실행 시작 시각
- 운영 정의
  - `k8s/news-raw-extractor-cronjob.yaml`을 삭제했다.
  - RSS Collector 03:00과 Daily topic pipeline 04:00 schedule은 유지했다.
  - Architecture index, pipeline/K3s 문서와 CronJob runbook을 갱신했다.
- 승인 fix
  - 단계별 package 분리와 실행 진입점 책임 축소
  - 공통 context 및 결과 타입 분리
  - 관련 Python 파일당 500줄 이하 유지
  - import 시 DB/provider 호출이 없는 단방향 의존성 구조
  - 핵심 단계, 결과 계약, 실패 정책과 transaction 경계의 한글 docstring 추가

## 추가/변경된 API

- Public API 추가 또는 변경 없음
- 다음 endpoint의 request/response 계약을 유지한다.
  - `/topics`
  - `/topics/{id}`
  - `/topics/home`
- 단계별 context와 결과 타입은 pipeline process 내부에서만 사용한다.

## DB 변경 사항

- DB schema, table, column, index 및 migration 변경 없음
- 기존 `articles`, `article_embeddings`, `raw_articles`, `extraction_runs`,
  `topics`, `topic_articles`만 사용한다.
- `topics.topic_date`는 pipeline 시작 시 결정한 `Asia/Seoul` 기준
  `pipeline_date`를 사용한다.
- 기존 topic 날짜, raw article 데이터 및 extraction run 데이터는 수정하거나
  삭제하지 않았다.

## README 영향

- README 변경 없음
- Public API, 설치 방법, 실행 command와 사용자 기능 계약은 변경되지 않았다.
- 내부 pipeline 구조와 CronJob 운영 흐름 변경은 `docs/architecture/`와
  `docs/runbooks/cronjobs.md`에 반영하는 것이 적절하다고 판단했다.

## 테스트

실행 완료:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

- 35 tests passed

```bash
python -m compileall app scripts tests
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
```

- Compile 완료
- Script 및 package import 성공
- Import 과정에서 DB 연결 또는 provider 호출 없음

```bash
python -m unittest discover -s tests
```

- 150 tests passed

```bash
wc -l \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/*.py
```

- 실행 진입점: 400줄
- Package 파일: 8–190줄
- 모든 대상 Python 파일이 500줄 이하

```bash
rg -n '"""' \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline
```

- 공통 context, 결과 타입, 네 stage, runtime adapter와 orchestration의 한글
  docstring 확인

```bash
git diff --check
git diff --stat
git status --short --branch
git diff -- db/migrations app/routers app/main.py requirements.txt
```

- `git diff --check` 통과
- 현재 branch `docs/daily-pipeline-stage-design` 확인
- DB migration, router, `app/main.py`, dependency 변경 없음

## 확인 결과

- 네 단계의 입력과 결과 타입이 코드 구조에서 분리됐다.
- 모든 단계가 동일한 `PipelineContext`와 `pipeline_date`를 사용한다.
- UTC 날짜 경계 입력이 `Asia/Seoul` 기준 날짜로 save plan에 전달되는 테스트가
  통과했다.
- selected article만 원문 조회·추출 대상이 되며 기존 저장 원문 재사용과 신규
  추출 통계가 구분된다.
- article 단위 embedding/raw 실패 및 topic 단위 summary 실패 격리 테스트가
  통과했다.
- Raw extractor manifest 부재와 RSS Collector 03:00, Daily topic pipeline
  04:00 schedule 유지 테스트가 통과했다.
- Active 03:30 schedule 설명은 운영 문서와 manifest에서 제거됐다.
- Production DB write, provider 호출, K3s apply/삭제 및 production API 확인은
  수행하지 않았다.

## 비고

- PR merge 완료 상태가 아니다.
- Production deployment, K3s rollout 및 production verification은 완료되지
  않았다.
- 다음 작업은 human operator가 수행해야 한다.
  - 기존 K3s `news-raw-extractor` CronJob object 제거
  - 변경된 manifest 및 application image 운영 반영
  - 다음 04:00 scheduled pipeline 완료 여부 확인
  - 운영 log의 `pipeline_date`, `business_timezone` 확인
  - 생성된 `topics.topic_date`가 실행일의 `Asia/Seoul` 날짜와 일치하는지 확인
- `git push`, `git merge`, Kubernetes 변경 command, Supabase SQL과 production
  curl verification은 실행하지 않았다.
