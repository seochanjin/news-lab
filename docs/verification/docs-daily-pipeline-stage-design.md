# Verification: Daily topic pipeline 분리 설계

## Verification Scope

- Daily topic pipeline 역할별 단계 분리
- selected article 원문 확보와 재사용/추출 통계
- Asia/Seoul 기준 공통 `pipeline_date`
- Raw extractor CronJob 배포 대상 제거
- 관련 문서와 변경 금지 영역 확인

## Commands Run

Command:

```bash
python -m unittest tests.test_run_daily_topic_pipeline
```

Result:

- 13 tests passed.

Status: passed

Notes:

- 단계 분리 직후 기존 pipeline 회귀를 먼저 확인했다.

Command:

```bash
python -m unittest tests.test_run_daily_topic_pipeline
```

Result:

- 신규 날짜 경계, selected article 원문 재사용/추출, selected article 지연 조회 테스트를 포함해 16 tests passed.

Status: passed

Notes:

- `2026-06-20 19:00 UTC`가 `2026-06-21 Asia/Seoul` pipeline date로 전달되고 save plan의 `topic_date`에도 사용되는 것을 확인했다.

Command:

```bash
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest
```

Result:

- 4 tests passed.

Status: passed

Notes:

- `news-raw-extractor` manifest 부재와 `03:00 Asia/Seoul` RSS Collector, `04:00 Asia/Seoul` Daily topic pipeline schedule 보존을 확인했다.

Command:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

Result:

- 중간 단계에서 34 tests passed.
- topic 단위 summary 실패 격리 테스트 추가 후 최종 35 tests passed.

Status: passed

Notes:

- embedding 저장 계약, 단계별 pipeline 동작, 공통 날짜, selected article 원문 처리, CronJob manifest를 함께 검증했다.

Command:

```bash
python -m compileall app scripts tests
```

Result:

- `app`, `scripts`, `tests` compile completed without errors.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 중간 전체 회귀에서 149 tests passed.
- 최종 전체 회귀에서 150 tests passed.

Status: passed

Command:

```bash
git diff --check
```

Result:

- No whitespace errors.

Status: passed

Command:

```bash
git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  requirements.txt
```

Result:

- No diff.

Status: passed

Notes:

- DB migration, Public API router, application entrypoint, dependency 영역을 수정하지 않았다.

Command:

```bash
rg -n '03:30|30 3 \* \* \*|news-raw-extractor' \
  docs/ARCHITECTURE.md docs/architecture docs/runbooks k8s tests \
  -g '*.md' -g '*.yaml' -g '*.py'
```

Result:

- Active 03:30 schedule 또는 raw extractor manifest 정의는 발견되지 않았다.
- 남은 `news-raw-extractor` 언급은 배포 대상에서 제거됐다는 문서 설명과 manifest 부재 테스트뿐이다.

Status: passed

Command:

```bash
git status --short --branch
```

Result:

- Current branch: `docs/daily-pipeline-stage-design`
- Task 범위 변경 파일과 기존 workflow artifact 미추적 파일을 확인했다.
- Review 파일은 수정하지 않았다.

Status: passed

## Results

- Pipeline 코드 작업 단위: passed
- CronJob 및 문서 작업 단위: passed
- 관련 테스트: passed (35 tests)
- 전체 회귀: passed (150 tests)
- Compile check: passed
- Diff check: passed
- 변경 금지 영역 확인: passed

## Manual or Production Verification

- K3s manifest apply와 기존 `news-raw-extractor` CronJob 제거는 사람이 수행해야 한다.
- Production scheduled execution 및 저장 결과 검증은 사람이 수행해야 한다.
- 상태: human-required

## Pending Verification

- 기존 K3s `news-raw-extractor` CronJob object 제거
- 변경된 manifest 운영 반영
- 다음 04:00 scheduled pipeline completion 확인
- 운영 log의 `pipeline_date`, `business_timezone` 확인
- 생성된 `topics.topic_date`가 실행일의 Asia/Seoul 날짜와 일치하는지 확인

## Evidence Notes

- Production-impacting command, DB write script, provider call은 실행하지 않았다.
- `kubectl apply`, `kubectl delete`, `kubectl rollout`, production curl을 실행하지 않았다.
- 기존 DB의 topic 날짜와 raw article 데이터는 수정하지 않았다.

## Approved Fix Verification

Command:

```bash
wc -l \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/*.py
```

Result:

- `scripts/run_daily_topic_pipeline.py`: 381 lines
- Package files: 8–182 lines
- 모든 대상 Python 파일이 500줄 이하이다.

Status: passed

Command:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

Result:

- 35 tests passed.

Status: passed

Notes:

- stage 이동 후 pipeline date, embedding 통계와 실패 격리, clustering/topic
  선택, selected article 원문 처리, summary 실패 격리와 CronJob 계약이
  유지되는 것을 확인했다.

Command:

```bash
python -m compileall app scripts tests
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
```

Result:

- Compile completed without errors.
- Script와 package import가 모두 성공했다.
- Import 시 DB 연결 또는 provider 호출은 발생하지 않았다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 150 tests passed.

Status: passed

Command:

```bash
git diff --check
git diff --stat
git status --short --branch
git diff -- db/migrations app/routers app/main.py requirements.txt
```

Result:

- `git diff --check`: no errors.
- Current branch: `docs/daily-pipeline-stage-design`
- `app/services/` 신규 package와 task 범위 변경 파일을 확인했다.
- DB migration, router, `app/main.py`, dependency diff는 없다.
- 기존 review 파일은 수정하지 않았다.

Status: passed

Notes:

- `git diff --stat`는 untracked 신규 package를 포함하지 않으므로 package
  파일 존재와 크기는 `git status`와 `wc -l` 결과로 별도 확인했다.

## Approved Fix 7 Verification

Command:

```bash
rg -n '"""' \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline
```

Result:

- 공통 context 생성 함수, 결과 dataclass 5개, 네 stage 진입 함수,
  embedding 실패 격리 함수, runtime adapter와 orchestration 함수에서
  한글 docstring을 확인했다.
- 단순 formatting, 정렬, ID 추출 helper에는 장문 docstring을 추가하지 않았다.

Status: passed

Notes:

- Docstring은 현재 구현의 article 단위 embedding/raw 실패 격리, topic 단위
  summary 실패 격리, provider 반환 계약 fail-fast, read-only 조회와 write
  transaction 경계를 설명한다.

Command:

```bash
wc -l \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/*.py
```

Result:

- `scripts/run_daily_topic_pipeline.py`: 400 lines
- Package files: 8–190 lines
- Docstring 추가 후에도 모든 대상 Python 파일이 500줄 이하이다.

Status: passed

Command:

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

Result:

- 35 tests passed.

Status: passed

Command:

```bash
python -m compileall app scripts tests
python -c "import scripts.run_daily_topic_pipeline"
python -c "import app.services.daily_topic_pipeline"
```

Result:

- Compile completed without errors.
- Script와 package import가 모두 성공했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 150 tests passed.

Status: passed

Command:

```bash
git diff --check
git diff --stat
git status --short --branch
git diff -- db/migrations app/routers app/main.py requirements.txt
```

Result:

- `git diff --check`: no errors.
- Current branch: `docs/daily-pipeline-stage-design`
- Approved Fix 7 대상 코드와 기존 task 범위 변경 파일을 확인했다.
- DB migration, router, `app/main.py`, dependency diff는 없다.
- Review 파일은 수정하지 않았다.

Status: passed
