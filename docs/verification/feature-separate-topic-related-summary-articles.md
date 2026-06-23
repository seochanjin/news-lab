# Verification: Topic 관련 기사 보존과 Summary 근거 기사 분리

## Verification Status

passed

## Verification Scope

UNIT-01부터 UNIT-03까지 관련 기사와 Summary 근거 기사 분리, 원문 확보 대상 제한, Summary 입력 및 Topic 관련 기사 전체 저장 계약을 검증했다.

UNIT-04에서는 Topic API 회귀, Daily CronJob 운영 인자, architecture/runbook 동기화와 전체 로컬 회귀를 검증했다.

Task에서 허용한 pytest, unittest, compileall 및 diff 검증은 모두 통과했다.

Production K3s apply, CronJob 실행, DB 저장 결과 및 운영 API 확인은 수행하지 않았으며 human operator 작업으로 남긴다.

---

## UNIT-01 Verification

### Scope

관련 기사와 Summary 근거 기사 설정 및 단계 결과 모델을 분리했다.

### Commands

```bash
python -m pytest \
  tests/test_daily_topic_pipeline_configuration.py \
  tests/test_run_daily_topic_pipeline.py \
  -v

python -m unittest \
  tests.test_daily_topic_pipeline_configuration \
  tests.test_run_daily_topic_pipeline

python -m compileall \
  scripts/run_daily_topic_pipeline.py \
  app/services/daily_topic_pipeline/models.py \
  app/services/daily_topic_pipeline/topic_selection_stage.py \
  tests/test_daily_topic_pipeline_configuration.py

git diff --check

git diff --name-only -- \
  db/migrations \
  app/routers \
  app/main.py
```

### Results

```text
pytest:
26 passed in 0.21s

unittest:
Ran 26 tests in 0.021s
OK

compileall:
exit code 0

git diff --check:
exit code 0

변경 금지 영역:
no output
```

### Contract Verification

- 관련 기사 기본 상한을 20건으로 분리했다.
- Summary 근거 기사 기본 상한을 3건으로 분리했다.
- `1 <= max_summary_articles_per_topic <= max_related_articles_per_topic` 관계를 검증한다.
- `TopicSelectionResult`가 `related_article_ids`와 `summary_article_ids`를 별도로 보관한다.
- Summary 기사는 관련 기사 집합의 부분집합이어야 한다.
- 대표 기사는 Summary 기사 집합에 포함되어야 한다.
- 기존 `selected_article_ids`는 downstream 호환 property로 유지한다.
- 기존 `--max-articles-per-topic`은 deprecated alias로 유지한다.
- 기존 alias와 신규 옵션을 함께 지정하면 실행 전에 차단한다.
- UNIT-01에서는 원문 확보, Summary provider 및 DB 저장 동작을 변경하지 않았다.

### Status

passed

---

## UNIT-02 Verification

### Scope

관련 기사와 Summary 근거 기사를 결정론적으로 선정하고, Raw acquisition 대상을 Summary 근거 기사로 제한했다.

### Commands

```bash
python -m pytest \
  tests/test_daily_topic_article_selection.py \
  -v

python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_topic_representatives.py \
  tests/test_raw_extraction_targets.py \
  tests/test_daily_topic_pipeline_configuration.py \
  -v

python -m unittest \
  tests.test_daily_topic_article_selection \
  tests.test_run_daily_topic_pipeline \
  tests.test_topic_representatives \
  tests.test_raw_extraction_targets \
  tests.test_daily_topic_pipeline_configuration

python -m compileall \
  app/services/daily_topic_pipeline/topic_selection_stage.py \
  app/services/daily_topic_pipeline/raw_acquisition_stage.py \
  tests/test_daily_topic_article_selection.py

git diff --check

git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  k8s \
  app/services/daily_topic_pipeline/summary_persistence_stage.py
```

### Results

```text
전용 pytest:
3 passed in 0.15s

관련 회귀 pytest:
42 passed in 0.19s

unittest:
Ran 45 tests in 0.022s
OK

compileall:
exit code 0

git diff --check:
exit code 0

변경 금지 영역:
no output
```

### Contract Verification

- 관련 기사를 설정 상한까지 결정론적으로 선정한다.
- Summary 근거 기사는 관련 기사 집합의 부분집합이다.
- 대표 기사를 Summary 근거 기사에 포함한다.
- 중복 URL과 정규화된 중복 제목을 제외한다.
- 가능한 범위에서 source 다양성을 반영한다.
- Raw acquisition 진입 전 Summary 기사만 대상으로 필터링한다.
- 기존 원문 재사용과 신규 추출 통계는 Summary 기사만 대상으로 계산한다.
- Summary 근거가 아닌 관련 기사에는 원문 조회나 신규 추출을 수행하지 않는다.
- 기사별 추출 실패가 다른 기사 처리를 중단시키지 않는다.
- Summary provider 입력과 최종 Topic 저장은 UNIT-03 범위로 유지했다.

### Status

passed

---

## UNIT-03 Verification

### Scope

Summary provider 입력을 Summary 근거 기사로 제한하고, Topic 관련 기사 전체를 `topic_articles` 저장 계획에 반영했다.

실행 통계에서 관련 기사, Summary 기사, 원문 확보 대상과 실제 저장 관계 수를 분리했다.

### Commands

```bash
python -m pytest \
  tests/test_daily_topic_summary_persistence.py \
  -v

python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_save_topic_summaries.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_daily_topic_pipeline_configuration.py \
  -v

python -m unittest \
  tests.test_daily_topic_summary_persistence \
  tests.test_run_daily_topic_pipeline \
  tests.test_save_topic_summaries \
  tests.test_daily_topic_article_selection \
  tests.test_daily_topic_pipeline_configuration

python -m compileall \
  app/services/daily_topic_pipeline/summary_persistence_stage.py \
  app/services/daily_topic_pipeline/reporting.py \
  scripts/run_daily_topic_pipeline.py \
  tests/test_daily_topic_summary_persistence.py

git diff --check

git diff -- \
  db/migrations \
  app/routers \
  app/main.py \
  k8s
```

### Results

```text
전용 pytest:
4 passed in 0.12s

관련 회귀 pytest:
37 passed in 0.16s

unittest:
Ran 41 tests in 0.027s
OK

compileall:
exit code 0

git diff --check:
exit code 0

변경 금지 영역:
no output
```

### Contract Verification

- Summary 단계에는 `summary_article_ids`에 포함된 기사만 전달한다.
- Summary input hash와 provider 입력은 Summary 근거 기사 원문만 반영한다.
- 저장 후보의 `articles`, `article_count`, `source_count`는 관련 기사 전체 기준으로 구성한다.
- 관련 기사 전체가 기존 순서, 대표 역할 및 similarity와 함께 저장 계획에 포함된다.
- 동일 기사 ID가 중복되면 최초 관계만 보존한다.
- 기존 `topic_articles` upsert 및 transaction 경계는 변경하지 않았다.
- 한 Topic의 Summary 실패가 다른 Topic의 Summary와 저장 계획을 중단시키지 않는다.
- 실행 결과와 Markdown report에서 다음 항목을 구분한다.
  - 관련 기사 수
  - Summary 근거 기사 수
  - 원문 확보 대상 수
  - 기존 원문 재사용 수
  - 신규 원문 추출 수
  - 실제 저장 관계 수
- DB schema, migration, router 및 K3s manifest를 변경하지 않았다.

### Status

passed

---

## UNIT-04 Verification

### Scope

Topic API의 기존 endpoint와 response field 계약을 회귀 검증했다.

Daily topic pipeline CronJob을 관련 기사 20건, Summary 근거 기사 3건 설정으로 변경하고 architecture와 runbook을 실제 동작에 맞게 동기화했다.

### Commands

```bash
python -m pytest \
  tests/test_topics_api.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v

python -m pytest \
  tests/test_daily_topic_pipeline_configuration.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_daily_topic_summary_persistence.py \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_topic_representatives.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_topics_api.py \
  -v

python -m pytest

python -m unittest discover -s tests

python -m compileall app scripts tests

git diff --check

git diff -- \
  db/migrations \
  app/routers \
  app/main.py

rg -n \
  "max-articles-per-topic|max-related-articles-per-topic|max-summary-articles-per-topic" \
  scripts k8s docs tests

git status --short --branch

git diff --stat
```

### Results

```text
Topic API 및 CronJob manifest:
10 passed in 0.25s

관련 수직 회귀 테스트:
50 passed in 0.36s

전체 pytest:
201 passed in 5.06s

전체 unittest:
Ran 201 tests in 3.927s
OK

compileall:
exit code 0

git diff --check:
exit code 0

변경 금지 영역:
no output
```

`unittest` 실행 중 출력된 `usage:`, `error:`, provider failure 및 embedding mismatch 문구는 잘못된 입력과 실패 격리를 검증하는 테스트의 예상 stderr 및 로그다. 최종 결과는 `OK`다.

### API Contract Verification

- Topic 상세 API가 저장된 관련 기사 전체를 관계 순서대로 반환한다.
- 홈 API의 기존 lightweight response schema가 유지된다.
- Topic 목록 pagination 및 filter 계약이 유지된다.
- 존재하지 않는 Topic의 404 응답이 유지된다.
- 관련 기사 수 증가가 endpoint 또는 response field 변경 없이 반영된다.
- Router 구현은 변경하지 않았다.

### CronJob Contract Verification

Daily CronJob은 다음 신규 옵션을 사용한다.

```text
--max-related-articles-per-topic 20
--max-summary-articles-per-topic 3
```

다음 기존 계약도 유지한다.

- `--execute`
- 기사 처리량 상한
- Embedding 및 Summary provider 사용
- 기존 image 및 image pull secret
- 보안 설정
- schedule 및 job safety 설정
- 별도 raw extractor CronJob을 사용하지 않는 구조

### Documentation Verification

다음 문서를 현재 동작에 맞게 갱신했다.

- `docs/architecture/backend-api.md`
- `docs/architecture/pipeline.md`
- `docs/runbooks/cronjobs.md`

### Legacy Argument Review

기존 `--max-articles-per-topic`은 다음 위치에 남아 있다.

- `scripts/run_daily_topic_pipeline.py`
  - deprecated alias
- 신규 configuration 테스트
  - alias 호환 및 신규 옵션 충돌 검증
- `scripts/generate_topic_summary_report.py`
  - Daily pipeline과 별개의 기존 report command
- 과거 Task, Verification, Review, Fix 및 Devlog
  - 당시 실행 증적

현재 Daily CronJob과 최신 운영 runbook은 신규 20/3 옵션을 사용한다.

과거 증적 문서와 별도 report command는 이번 Task 범위에서 일괄 변경하지 않았다.

### Status

passed

---

## Final Verification Summary

### Configuration

- 관련 기사 상한과 Summary 근거 기사 상한을 분리했다.
- Daily 기본값은 관련 기사 20건, Summary 기사 3건이다.
- 잘못된 상한 관계와 신규·기존 옵션 혼용을 실행 전에 차단한다.

### Article Selection

- 관련 기사를 설정 상한까지 결정론적으로 선정한다.
- Summary 기사는 관련 기사 집합의 부분집합이다.
- 대표 기사, source 다양성 및 중복 제외 계약을 유지한다.

### Raw Acquisition

- Summary 근거 기사만 원문 확보 대상으로 사용한다.
- 기존 원문을 재사용한다.
- Summary에 사용하지 않는 관련 기사에는 신규 추출을 수행하지 않는다.
- 기사 단위 실패 격리를 유지한다.

### Summary and Persistence

- Summary provider에는 Summary 근거 기사만 전달한다.
- `topic_articles`에는 Topic 관련 기사 전체를 연결한다.
- 중복 관계를 방지하고 기존 transaction 계약을 유지한다.
- 실행 보고서에서 각 기사 집합과 처리 수를 구분한다.

### API and Operations

- API endpoint와 response schema 변경 없음
- DB schema와 migration 변경 없음
- Daily CronJob은 신규 관련 기사 및 Summary 기사 옵션을 사용
- architecture와 runbook 동기화 완료
- 실제 K3s 적용과 Production 검증은 수행하지 않음

### Final Result

- UNIT-01부터 UNIT-04까지 구현 및 로컬 검증 완료
- 전체 pytest 201건 통과
- 전체 unittest 201건 통과
- compileall 및 diff check 통과
- 변경 금지 영역 수정 없음
- Antigravity Review 진행 가능

---

## Human-required Production Verification

다음 작업은 수행하지 않았다.

- K3s manifest apply
- Kubernetes rollout
- CronJob 수동 실행
- Production CronJob 로그 확인
- Production DB 저장 결과 확인
- Production API 응답 확인
- Git push 및 merge
- Supabase SQL

위 작업은 PR merge 및 운영 반영 단계에서 사람이 수행해야 한다.
