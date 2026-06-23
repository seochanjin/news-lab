# Verification: 3일 Topic pipeline·저장·API·CronJob 구축

## Verification Status

passed

## Verification Scope

- UNIT-01부터 UNIT-08까지 검증했다.
- 기존 Daily Topic, article embedding, Topic 저장/API와 CronJob 구조를
  read-only로 조사했다.
- `docs/design/three-day-topic-pipeline.md`의 시간 범위, 저장 원자성,
  idempotency, 실행 상태와 단계 경계 계약을 정적 검증했다.
- UNIT-02의 전용 migration, 저장 model과 transaction repository를 가짜
  SQLAlchemy engine으로 검증했다.
- UNIT-03의 서울 기준 72시간 context, 후보 조회 SQL과 기존 article embedding
  재사용·누락 분류를 가짜 SQLAlchemy connection으로 검증했다.
- UNIT-04의 기사 embedding 직접 재클러스터링, Topic 정렬, 대표·관련·Summary
  근거 기사 부분집합과 3일 전용 상한을 메모리 fixture로 검증했다.
- UNIT-05의 선택 기사 원문 재사용·지연 추출, 3일 전용 prompt/hash,
  Topic별 실패 격리와 성공 부분집합의 원자 저장 연결을 mock과 가짜 repository로
  검증했다.
- UNIT-06의 3일 Topic archive filter/pagination, 최신 publishable window home,
  관련 기사 역할을 포함한 detail, 빈 응답·404와 route 순서를 가짜 SQLAlchemy
  connection으로 검증했다.
- UNIT-07의 전용 실행 script, CLI 안전 조건, 단계 조정, run 종료 통계와 3일
  CronJob manifest를 mock 및 로컬 YAML 파싱으로 검증했다.
- UNIT-08의 README, Architecture, Runbook, 설계, PR과 devlog 문서 정리,
  전체 pytest/unittest/compileall과 scope 검사를 검증했다.
- 실제 DB 연결·쓰기, 외부 Summary API, 원문 추출, Kubernetes object 생성과
  production 동작은 검증 범위에 포함하지 않았다.

## Commands Run

### 1. 작업 전 branch와 working tree 확인

Command:

```bash
git branch --show-current && git status --short
```

Result:

- 현재 branch는 `feature/three-day-topic-pipeline`이었다.
- task/verification과 review/fix/PR/devlog 문서의 기존 미커밋 변경을
  확인했으며 삭제하거나 덮어쓰지 않았다.

Status: passed

### 2. 필수 지침과 Task 확인

Command:

```bash
sed -n '1,260p' AGENTS.md
sed -n '1,760p' docs/tasks/feature-three-day-topic-pipeline.md
sed -n '1,320p' docs/agent/backend-workflow.md
sed -n '1,320p' docs/agent/codex-instructions.md
sed -n '1,320p' docs/agent/verification-gates.md
sed -n '1,320p' docs/agent/forbidden-commands.md
sed -n '1,320p' docs/agent/task-authoring-guide.md
```

Result:

- UNIT-01만 수행하고 후속 UNIT을 구현하지 않는 범위를 확인했다.
- DB write pipeline, migration 적용, Kubernetes 변경과 production 검증이
  사람 통제 작업임을 확인했다.
- UNIT-01은 Python 파일을 변경하지 않으므로 Python docstring 변경 대상이
  없음을 확인했다.

Status: passed

### 3. 현재 Architecture와 Runbook 확인

Command:

```bash
sed -n '1,260p' docs/ARCHITECTURE.md
sed -n '1,260p' docs/RUNBOOK.md
sed -n '1,320p' docs/architecture/pipeline.md
sed -n '1,320p' docs/architecture/database.md
sed -n '1,280p' docs/runbooks/cronjobs.md
```

Result:

- Daily Topic이 24시간 후보, embedding 생성·재사용, 관련 기사와 Summary 근거
  기사 분리, 선택 기사 원문 확보, `topics` 저장을 담당함을 확인했다.
- `article_embeddings`의 provider/model/dimension/source type/hash 재사용
  계약과 Daily CronJob의 기존 실행 계약을 확인했다.

Status: passed

### 4. 관련 코드와 schema 조사

Command:

```bash
sed -n '1,760p' scripts/run_daily_topic_pipeline.py
sed -n '1,360p' scripts/analyze_topic_groups.py
sed -n '1,320p' app/utils/article_embedding_storage.py
sed -n '1,420p' app/services/daily_topic_pipeline/context.py
sed -n '1,420p' app/services/daily_topic_pipeline/models.py
sed -n '1,420p' app/services/daily_topic_pipeline/embedding_stage.py
sed -n '1,420p' app/services/daily_topic_pipeline/topic_selection_stage.py
sed -n '1,420p' app/services/daily_topic_pipeline/raw_acquisition_stage.py
sed -n '1,420p' app/services/daily_topic_pipeline/summary_persistence_stage.py
sed -n '1,380p' scripts/save_topic_summaries.py
sed -n '1,360p' app/utils/topic_summary.py
sed -n '1,260p' db/migrations/005_create_topics_tables.sql
sed -n '1,300p' db/migrations/006_create_article_embeddings.sql
sed -n '1,360p' app/routers/topics.py
sed -n '1,220p' app/main.py
sed -n '1,280p' k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- 기존 candidate query가 `coalesce(published_at, created_at)`와 DB `now()`를
  사용함을 확인했다.
- Daily context는 `pipeline_date`는 고정하지만 명시적 window bound는 보관하지
  않음을 확인했다.
- Daily embedding stage는 저장 row가 없거나 hash가 바뀌면 provider를
  호출하므로 3일 candidate stage에 그대로 사용할 수 없음을 확인했다.
- clustering, 대표 기사 선정, 관련/Summary 기사 부분집합, Topic별 Summary
  실패 격리는 재사용 가능한 처리로 분류했다.
- 기존 Topic 저장은 window 전체 원자적 교체와 run 이력을 제공하지 않음을
  확인했다.

Status: passed

### 5. UNIT-01 설계와 문서 상태 정적 검증

Command:

```bash
if rg -n '[[:blank:]]+$' \
  docs/design/three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- trailing whitespace가 없어 exit code 0으로 완료했다.

Status: passed

Command:

```bash
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
```

Result:

- UNIT-01만 `[x]`이고 UNIT-02부터 UNIT-08까지 `[ ]`임을 확인했다.

Status: passed

Command:

```bash
rg -n \
  'three-day-flow-v1|candidate_count = embedding_count \+ missing_embedding_count|unique \(window_start, window_end, topic_candidate_id\)|running|partial_success|failed|UNIT-01에서는' \
  docs/design/three-day-topic-pipeline.md
```

Result:

- prompt version, embedding count 관계, window idempotency key, run 상태와
  후속 UNIT 비구현 경계가 설계 문서에 있음을 확인했다.

Status: passed

Command:

```bash
git diff --check && git status --short
```

Result:

- `git diff --check`가 exit code 0으로 완료했다.
- 신규 설계/task/verification 문서가 untracked 상태임을 확인했다.
- 기존 `docs/tasks/main.md` 수정과 review/fix/PR/devlog 문서는 그대로
  보존되어 있다.

Status: passed

### 6. UNIT-02 최초 집중 테스트

Command:

```bash
python -m pytest tests/test_three_day_topic_repository.py -v
```

Result:

- 7개 중 6개가 통과했다.
- repository transaction은 정상 동작했으나 Topic insert parameter를 확인하는
  테스트가 article insert event를 잘못 참조해 `KeyError: 'article_count'`로
  1개 실패했다.
- 테스트 event 인덱스를 수정하고 72시간 window 및 서울 기준일 검증을
  추가했다.

Status: failed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- 신규 package와 테스트가 모두 compile되었다.

Status: passed

Command:

```bash
git diff --check -- \
  db/migrations/007_create_three_day_topic_tables.sql \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- exit code 0으로 완료했다.

Status: passed

### 7. UNIT-02 수정 후 집중 테스트

Command:

```bash
python -m pytest tests/test_three_day_topic_repository.py -v
```

Result:

- 8개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- 수정한 model, repository와 테스트가 모두 compile되었다.

Status: passed

Command:

```bash
git diff --check -- \
  db/migrations/007_create_three_day_topic_tables.sql \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- exit code 0으로 완료했다.

Status: passed

### 8. UNIT-02 최종 집중 및 기존 migration 회귀 테스트

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_repository.py \
  tests/test_article_embedding_migration.py \
  tests/test_topic_summary_migration.py \
  -v
```

Result:

- 3일 Topic migration/repository 9개와 기존 embedding/Topic migration
  회귀 2개를 포함해 11개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest tests.test_three_day_topic_repository
```

Result:

- 9개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- exit code 0으로 완료했다.

Status: passed

Command:

```bash
git diff --check && \
rg -n \
  "three_day_topics|three_day_topic_articles|three_day_topic_runs" \
  db/migrations \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- `git diff --check`가 exit code 0으로 완료했다.
- 전용 세 table 이름이 migration, repository와 테스트에만 존재함을 확인했다.

Status: passed

### 9. UNIT-02 문서 및 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_repository.py \
  tests/test_article_embedding_migration.py \
  tests/test_topic_summary_migration.py \
  -q
```

Result:

- 11개 테스트가 모두 통과했다.

Status: passed

### 10. UNIT-03 context와 candidate stage 집중 테스트

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -v
```

Result:

- 명시적 `window_end`의 UTC 정규화와 서울 기준일, naive datetime 거부,
  `[window_start, window_end)` query bind, 후보 상한과 결정론적 정렬을
  검증했다.
- 저장 embedding의 metadata, 현재 title/summary source hash와 vector 차원을
  검증하고 `missing_row`, `incompatible_metadata`, `stale_hash`,
  `invalid_vector` 누락 분류를 확인했다.
- 후보가 없을 때 embedding query를 생략하는 동작과 UNIT-02 repository 회귀를
  포함해 14개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
```

Result:

- UNIT-03 신규 context, candidate stage, model과 테스트가 모두 compile되었다.

Status: passed

Command:

```bash
git diff --check -- \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- `git diff --check`가 exit code 0으로 완료했다.
- 기존 Daily Topic service, 실행 script와 CronJob manifest diff가 없었다.

Status: passed

### 11. UNIT-03 Daily Topic 회귀 테스트

Command:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

Result:

- 기존 Daily Topic pipeline 19개와 CronJob manifest 4개를 포함해 23개
  테스트가 모두 통과했다.

Status: passed

Command:

```bash
if rg -n '[[:blank:]]+$' \
  db/migrations/007_create_three_day_topic_tables.sql \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py \
  docs/design/three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- 신규·수정 파일에 trailing whitespace가 없어 exit code 0으로 완료했다.

Status: passed

Command:

```bash
git diff --check
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
git status --short
```

Result:

- `git diff --check`가 exit code 0으로 완료했다.
- Daily Topic service, 실행 script와 CronJob manifest diff가 없었다.
- UNIT-01과 UNIT-02만 `[x]`이고 UNIT-03부터 UNIT-08은 `[ ]`다.
- 기존 UNIT-01 workflow 문서와 이번 UNIT-02 신규 파일이 미커밋 상태이며,
  기존 파일을 삭제하거나 되돌리지 않았다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_repository.py
```

Result:

- exit code 0으로 완료했다.

Status: passed

### 12. UNIT-03 문서 및 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -q
python -m unittest tests.test_three_day_topic_pipeline
```

Result:

- Pytest 14개와 unittest 5개가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
```

Result:

- exit code 0으로 완료했다.

Status: passed

Command:

```bash
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
git status --short
git diff --check
if rg -n '[[:blank:]]+$' \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- UNIT-01부터 UNIT-03까지만 `[x]`이고 UNIT-04부터 UNIT-08은 `[ ]`다.
- `git diff --check`가 exit code 0으로 완료했다.
- UNIT-03 관련 코드·테스트·task·verification에 trailing whitespace가 없었다.
- 기존 미커밋 UNIT-01/02 산출물과 `docs/tasks/main.md` 변경을 보존했고,
  파일을 삭제하거나 되돌리지 않았다.

Status: passed

### 13. UNIT-04 작업 전 상태와 요구사항 확인

Command:

```bash
git branch --show-current
git status --short
sed -n '1,920p' docs/tasks/feature-three-day-topic-pipeline.md
sed -n '1,260p' AGENTS.md
sed -n '1,320p' docs/agent/backend-workflow.md
sed -n '1,320p' docs/agent/codex-instructions.md
sed -n '1,360p' docs/agent/task-authoring-guide.md
sed -n '1,360p' docs/agent/verification-gates.md
sed -n '1,360p' docs/agent/forbidden-commands.md
```

Result:

- 현재 branch가 `feature/three-day-topic-pipeline`임을 확인했다.
- 기존 UNIT-01부터 UNIT-03 산출물과 workflow 문서의 미커밋 변경을 보존했다.
- UNIT-04만 구현하고 provider, 원문, Summary, API, CronJob과 운영 작업을
  수행하지 않는 범위를 확인했다.
- Python module, 함수와 테스트에 한글 docstring을 작성하는 정책을 확인했다.

Status: passed

### 14. UNIT-04 최초 집중 테스트와 정적 검증

Command:

```bash
python -m pytest tests/test_three_day_topic_pipeline.py -v
```

Result:

- 기존 context/candidate 5개와 신규 selection 4개를 포함한 9개 테스트가 모두
  통과했다.
- 저장 embedding 직접 재클러스터링, 최대 Topic 수, 관련·Summary 기사 상한,
  대표 기사 포함, URL·제목 중복 제외와 2건 미만 빈 결과를 확인했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_daily_topic_article_selection.py \
  tests/test_run_daily_topic_pipeline.py \
  -v
```

Result:

- 공통 selection helper 추출 후 Daily 기사 선정 4개와 pipeline 19개를 포함한
  23개 회귀 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline \
  tests/test_three_day_topic_pipeline.py
git diff --check -- \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline/topic_selection_stage.py \
  tests/test_three_day_topic_pipeline.py
```

Result:

- Python compile은 성공했다.
- `git diff --check`가 Daily selection 파일 끝의 불필요한 빈 줄을
  `new blank line at EOF`로 보고해 exit code 2로 실패했다.
- 빈 줄을 제거한 뒤 재검증했다.

Status: failed

### 15. UNIT-04 수정 후 집중·Daily 회귀 검증

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_topic_grouping.py \
  tests/test_topic_representatives.py \
  -v
```

Result:

- 3일 context/candidate/selection, Daily pipeline, 공통 grouping과 대표 기사
  점수 회귀를 포함한 42개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest tests.test_three_day_topic_pipeline
```

Result:

- UNIT-04 신규 테스트를 포함한 9개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline \
  tests/test_three_day_topic_pipeline.py
git diff --check -- \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline/topic_selection_stage.py \
  tests/test_three_day_topic_pipeline.py
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- compileall과 수정 범위 `git diff --check`가 exit code 0으로 완료했다.
- Daily 변경은 selection helper의 내부 공통화에 한정되며 Daily 실행 script와
  CronJob manifest에는 diff가 없었다.

Status: passed

### 16. UNIT-04 문서와 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_topic_grouping.py \
  tests/test_topic_representatives.py \
  -q
python -m unittest tests.test_three_day_topic_pipeline
```

Result:

- Pytest 42개와 unittest 9개가 모두 통과했다.

Status: passed

### 17. UNIT-05 작업 전 상태와 요구사항 확인

Command:

```bash
git branch --show-current && git status --short
sed -n '1,260p' AGENTS.md
sed -n '1,760p' docs/tasks/feature-three-day-topic-pipeline.md
sed -n '1,320p' docs/agent/backend-workflow.md
sed -n '1,300p' docs/agent/codex-instructions.md
sed -n '1,320p' docs/agent/verification-gates.md
sed -n '1,340p' docs/agent/forbidden-commands.md
sed -n '1,300p' docs/agent/task-authoring-guide.md
sed -n '1,320p' docs/verification/feature-three-day-topic-pipeline.md
```

Result:

- 현재 branch가 `feature/three-day-topic-pipeline`임을 확인했다.
- 기존 UNIT-01부터 UNIT-04 산출물과 workflow 문서의 미커밋 변경을 보존했다.
- UNIT-05만 구현하고 API, 실행 script, CronJob과 production 작업은 수행하지
  않는 범위를 확인했다.
- 당시 UNIT 검증에서는 Approved Fixes 적용 대상이 없었다. 이후
  `docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md`의 FIX-01부터
  FIX-09까지 승인 항목을 적용하고 이 문서의 Approved Fixes Verification에
  별도로 기록했다.

Status: passed

### 18. UNIT-05 최초 집중 테스트

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -v
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
git diff --check -- \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
```

Result:

- 원문 확보, Summary 입력/hash, 부분 성공 저장과 전부 실패 시 결과 보존을
  포함한 3일 pipeline/repository 테스트 23개가 모두 통과했다.
- 신규·수정 Python 파일이 모두 compile되었다.
- 수정 범위 `git diff --check`가 exit code 0으로 완료했다.

Status: passed

### 19. 3일 전용 OpenAI prompt adapter 추가 후 재검증

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -v
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
git diff --check -- \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
```

Result:

- OpenAI Responses API 요청 payload가 `three-day-flow-v1` 전용 prompt와 strict
  schema를 사용하는 테스트를 추가했다.
- 3일 pipeline/repository 테스트 24개가 모두 통과했다.
- compileall과 수정 범위 `git diff --check`가 exit code 0으로 완료했다.

Status: passed

### 20. UNIT-05 Daily 인접 회귀와 unittest 검증

Command:

```bash
python -m pytest \
  tests/test_daily_topic_article_selection.py \
  tests/test_daily_topic_summary_persistence.py \
  tests/test_run_daily_topic_pipeline.py \
  -v
```

Result:

- Daily 원문 대상 선정, Summary/관련 기사 저장 분리와 실행 pipeline 회귀 테스트
  27개가 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest \
  tests.test_three_day_topic_pipeline \
  tests.test_three_day_topic_repository
```

Result:

- 3일 pipeline과 repository unittest 24개가 모두 통과했다.
- 의도적으로 실패시킨 Topic의 warning log만 출력되었고 test failure는 없었다.

Status: passed

### UNIT-04 기존 최종 정적 기록

Command:

```bash
python -m compileall \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline \
  tests/test_three_day_topic_pipeline.py
git diff --check
if rg -n '[[:blank:]]+$' \
  app/services/topic_pipeline \
  app/services/three_day_topic_pipeline \
  app/services/daily_topic_pipeline/topic_selection_stage.py \
  tests/test_three_day_topic_pipeline.py \
  docs/design/three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- compileall, `git diff --check`와 trailing whitespace 검사가 exit code 0으로
  완료했다.

Status: passed

Command:

```bash
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
git status --short
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- UNIT-01부터 UNIT-04까지만 `[x]`이고 UNIT-05부터 UNIT-08은 `[ ]`다.
- 기존 미커밋 산출물과 `docs/tasks/main.md` 변경을 보존했다.
- Daily diff는 selection helper 공통화에 한정되며 실행 script와 CronJob
  manifest에는 변경이 없었다.

Status: passed

### 21. UNIT-05 문서와 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_daily_topic_summary_persistence.py \
  tests/test_run_daily_topic_pipeline.py \
  -q
python -m unittest \
  tests.test_three_day_topic_pipeline \
  tests.test_three_day_topic_repository
```

Result:

- UNIT-05 집중 테스트와 Daily 인접 회귀를 합친 pytest 51개가 모두 통과했다.
- 3일 pipeline/repository unittest 24개가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py
git diff --check
if rg -n '[[:blank:]]+$' \
  app/services/three_day_topic_pipeline \
  tests/test_three_day_topic_pipeline.py \
  docs/design/three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- UNIT-05 Python 파일과 테스트가 compile되었다.
- 전체 `git diff --check`와 대상 파일 trailing whitespace 검사가 exit code
  0으로 완료했다.

Status: passed

Command:

```bash
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
git status --short
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- UNIT-01부터 UNIT-05까지만 `[x]`이고 UNIT-06부터 UNIT-08은 `[ ]`다.
- 기존 미커밋 산출물과 `docs/tasks/main.md` 변경을 보존했다.
- Daily diff는 UNIT-04의 selection helper 공통화뿐이며 Daily 실행 script와
  CronJob manifest에는 변경이 없다.

Status: passed

### 22. UNIT-06 작업 전 상태와 요구사항 확인

Command:

```bash
git branch --show-current && git status --short
sed -n '1,260p' AGENTS.md
sed -n '1,620p' docs/tasks/feature-three-day-topic-pipeline.md
sed -n '1,280p' docs/agent/backend-workflow.md
sed -n '1,280p' docs/agent/codex-instructions.md
sed -n '1,300p' docs/agent/verification-gates.md
sed -n '1,320p' docs/agent/forbidden-commands.md
sed -n '1,280p' docs/agent/task-authoring-guide.md
sed -n '1,320p' docs/verification/feature-three-day-topic-pipeline.md
```

Result:

- 현재 branch가 `feature/three-day-topic-pipeline`임을 확인했다.
- 기존 UNIT-01부터 UNIT-05 산출물과 workflow 문서의 미커밋 변경을 보존했다.
- UNIT-06만 구현하고 실행 script, CronJob, migration 적용과 production
  verification을 수행하지 않는 범위를 확인했다.
- 새 Python router, 수정한 application module과 테스트에 한글 docstring을
  작성하는 정책을 확인했다.

Status: passed

### 23. UNIT-06 최초 집중 테스트와 기존 Topics API 회귀

Command:

```bash
python -m pytest tests/test_three_day_topics_api.py -v
python -m pytest tests/test_topics_api.py -v
```

Result:

- 3일 Topic archive filter/pagination, 최신 publishable window home, 빈 home,
  상세 기사 역할, 404와 `/home` route 순서 테스트 6개가 모두 통과했다.
- 기존 `/topics` 목록·홈·상세 회귀 테스트 6개가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/routers/three_day_topics.py \
  app/main.py \
  tests/test_three_day_topics_api.py
git diff --check -- \
  app/routers/three_day_topics.py \
  app/main.py \
  tests/test_three_day_topics_api.py
rg -n \
  "three-day-topics|three_day_topics" \
  app tests/test_three_day_topics_api.py
```

Result:

- UNIT-06 Python module과 테스트가 compile되었다.
- 대상 파일 `git diff --check`가 exit code 0으로 완료했다.
- 새 route, application 등록과 API 테스트 위치를 확인했다.

Status: passed

### 24. UNIT-06 문서화 후 최종 집중 검증

Command:

```bash
python -m pytest \
  tests/test_three_day_topics_api.py \
  tests/test_topics_api.py \
  -q
python -m unittest tests.test_three_day_topics_api
```

Result:

- 신규 API와 기존 Topics API pytest 12개가 모두 통과했다.
- 3일 Topic API unittest 6개가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  app/routers/three_day_topics.py \
  app/main.py \
  tests/test_three_day_topics_api.py
git diff --check
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- compileall과 전체 `git diff --check`가 exit code 0으로 완료했다.
- Daily service diff는 기존 UNIT-04 selection helper 공통화에 한정되며 Daily
  실행 script와 CronJob manifest에는 변경이 없었다.

Status: passed

### 25. UNIT-06 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_three_day_topics_api.py \
  tests/test_topics_api.py \
  -q
python -m unittest tests.test_three_day_topics_api
python -m compileall \
  app/routers/three_day_topics.py \
  app/main.py \
  tests/test_three_day_topics_api.py
```

Result:

- API pytest 12개와 3일 Topic API unittest 6개가 모두 통과했다.
- UNIT-06 Python 파일이 모두 compile되었다.

Status: passed

Command:

```bash
git diff --check
if rg -n '[[:blank:]]+$' \
  app/routers/three_day_topics.py \
  app/main.py \
  tests/test_three_day_topics_api.py \
  docs/architecture/backend-api.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
git status --short
```

Result:

- 전체 `git diff --check`와 대상 파일 trailing whitespace 검사가 exit code
  0으로 완료했다.
- UNIT-01부터 UNIT-06까지만 `[x]`이고 UNIT-07과 UNIT-08은 `[ ]`다.
- 기존 미커밋 UNIT-01부터 UNIT-05 산출물과 `docs/tasks/main.md` 변경을
  보존했으며 삭제하거나 되돌리지 않았다.

Status: passed

### 26. UNIT-07 최초 실행 진입점·CronJob 집중 검증

Command:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  -v
```

Result:

- 20개 중 기존 3일 stage 테스트 15개와 신규 진입점 테스트 4개가 통과했다.
- 신규 timezone 테스트가 `05:00+09:00`의 비교 기대값을 `14:00+09:00`으로
  잘못 계산해 1개 실패했다.
- CLI parser와 context 구현 문제가 아니라 신규 테스트 fixture 결함으로
  분류하고 기대값을 `05:00+09:00`으로 수정했다.

Status: failed

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

Result:

- 3개 테스트가 모두 통과했다.
- `05:00 Asia/Seoul`, `concurrencyPolicy: Forbid`, history limit,
  `activeDeadlineSeconds`, `backoffLimit`, 전용 script와 72시간 bounded 인자,
  기존 image·Secret·security/resource pattern 재사용을 확인했다.
- embedding provider option과 `OPENAI_EMBEDDING_API_KEY`가 3일 CronJob에
  포함되지 않음을 확인했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/run_three_day_topic_pipeline.py \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py
git diff --check -- \
  scripts/run_three_day_topic_pipeline.py \
  k8s/news-three-day-topic-pipeline-cronjob.yaml \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py
```

Result:

- 신규 Python 파일이 모두 compile되었다.
- UNIT-07 코드, manifest와 테스트의 whitespace 검사가 exit code 0으로
  완료됐다.

Status: passed

### 27. UNIT-07 수정 후 집중 테스트와 Daily 회귀

Command:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  -v
```

Result:

- 실행 진입점 5개와 기존 3일 pipeline 15개, 총 20개 테스트가 모두 통과했다.
- 기본 dry-run, timezone-aware `--window-end`, 72시간 고정, embedding provider
  option 부재, execute의 Summary provider/key 요구를 확인했다.
- 후보·선정·원문·Summary 단계가 동일 context를 받고 실제 count가 run 종료
  model과 JSON 분석 결과에 유지됨을 확인했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

Result:

- 기존 Daily 실행 진입점 19개와 CronJob manifest 4개, 총 23개 테스트가 모두
  통과했다.
- 기존 Daily script와 `04:00 Asia/Seoul` CronJob command·Secret 계약에
  회귀가 없음을 확인했다.

Status: passed

Command:

```bash
python -m unittest \
  tests.test_run_three_day_topic_pipeline \
  tests.test_three_day_topic_pipeline_cronjob_manifest
```

Result:

- 신규 UNIT-07 unittest 8개가 모두 통과했다.
- 의도한 argparse 오류 경로가 stderr에 출력됐지만 전체 command는 exit code
  0으로 완료됐다.

Status: passed

Command:

```bash
python scripts/run_three_day_topic_pipeline.py --help
```

Result:

- 전용 CLI help가 exit code 0으로 출력됐다.
- `--window-end`, 72시간 고정, 3일 전용 기사·Topic 상한, Summary provider와
  `--execute` option을 확인했다.
- embedding provider option은 노출되지 않았다.

Status: passed

### 28. UNIT-07 Kubernetes client dry-run 미실행

Command:

```bash
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

Result:

- 실행하지 않았다.
- 현재 사용자 지시와 forbidden command가 `kubectl apply` 실행을 금지하므로
  client-side dry-run도 자동 실행하지 않았다.
- 로컬 YAML 파싱 테스트로 manifest 구조를 검증했으며 Kubernetes client/server
  schema dry-run과 실제 apply는 사람 수행 항목으로 남겼다.

Status: human-required

### 29. UNIT-07 checklist 갱신 후 최종 확인

Command:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -q
```

Result:

- UNIT-07 실행 진입점, 기존 3일 stage와 CronJob manifest 총 23개 테스트가 모두
  통과했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/run_three_day_topic_pipeline.py \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py
git diff --check
```

Result:

- UNIT-07 Python 파일이 모두 compile되었다.
- 전체 작업 트리의 `git diff --check`가 exit code 0으로 완료됐다.

Status: passed

Command:

```bash
git diff -- \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
rg -n '^- \[[x ]\] UNIT-' \
  docs/tasks/feature-three-day-topic-pipeline.md
if rg -n '[[:blank:]]+$' \
  scripts/run_three_day_topic_pipeline.py \
  k8s/news-three-day-topic-pipeline-cronjob.yaml \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  docs/design/three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- 기존 Daily 실행 script와 CronJob manifest diff가 비어 있었다.
- UNIT-01부터 UNIT-07까지만 `[x]`이고 UNIT-08은 `[ ]`다.
- UNIT-07 대상 코드·manifest·문서에 trailing whitespace가 없어 exit code
  0으로 완료됐다.

Status: passed

Command:

```bash
git diff --stat
git status --short
```

Result:

- 기존 UNIT-01부터 UNIT-06의 미커밋 변경과 UNIT-07 신규 파일이 함께 있는
  작업 트리를 확인했다.
- 기존 변경을 삭제하거나 되돌리지 않았고 후속 UNIT-08 파일을 구현 또는 완료
  처리하지 않았다.

Status: passed

### 30. UNIT-08 문서 변경 전 구조와 구현 계약 확인

Command:

```bash
sed -n '1,280p' docs/ARCHITECTURE.md
sed -n '1,280p' docs/RUNBOOK.md
sed -n '1,320p' README.md
sed -n '1,380p' docs/design/three-day-topic-pipeline.md
sed -n '1,380p' docs/architecture/pipeline.md
sed -n '1,380p' docs/architecture/database.md
sed -n '1,380p' docs/architecture/backend-api.md
sed -n '1,460p' docs/runbooks/cronjobs.md
sed -n '1,300p' docs/runbooks/database-check.md
sed -n '1,260p' docs/runbooks/routine-check.md
sed -n '1,320p' k8s/news-three-day-topic-pipeline-cronjob.yaml
sed -n '1,360p' scripts/run_three_day_topic_pipeline.py
sed -n '1,360p' db/migrations/007_create_three_day_topic_tables.sql
sed -n '1,420p' app/routers/three_day_topics.py
```

Result:

- README에 기존 3일 API와 실행 안내가 없고 Architecture/Runbook index의 현재
  운영 workload와 수동 반영 절차가 불완전함을 확인했다.
- 실제 manifest의 `05:00 Asia/Seoul`, Secret reference와 안전 설정, CLI의
  기본 dry-run과 execute 조건, migration의 additive table·constraint를
  문서화 기준으로 확인했다.
- 운영 절차에 migration 적용 전후 schema 확인, manifest dry-run/apply, 수동
  Job, API 확인, suspend와 rollback 판단이 필요함을 확인했다.

Status: passed

### 31. UNIT-08 집중 및 Daily 회귀 테스트

Command:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  -v
```

Result:

- 3일 CLI/context/candidate/clustering/raw/Summary/저장 조정 테스트 20개가 모두
  통과했다.

Status: passed

Command:

```bash
python -m pytest tests/test_three_day_topics_api.py -v
```

Result:

- Archive filter/pagination, 최신 home, detail 역할, 빈 응답, 404와 route 순서
  테스트 6개가 모두 통과했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

Result:

- Schedule, 전용 command, Secret, resource와 job 안전 설정 테스트 3개가 모두
  통과했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

Result:

- 기존 Daily 실행 계약과 CronJob manifest 회귀 테스트 23개가 모두 통과했다.

Status: passed

### 32. UNIT-08 전체 회귀와 compile 검증

Command:

```bash
python -m pytest
```

Result:

- 전체 261개 테스트가 8.94초에 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 261개 unittest가 6.604초에 모두 통과했다.
- 의도적으로 잘못된 CLI 인자를 검증하는 테스트의 argparse stderr와 실패 격리
  log가 출력됐지만 command exit code는 0이었다.

Status: passed

Command:

```bash
python -m compileall app scripts tests
```

Result:

- Application, script와 test Python module이 모두 compile됐고 exit code 0으로
  완료됐다.

Status: passed

### 33. UNIT-08 whitespace, scope와 문서 일관성 확인

Command:

```bash
git diff --check
git diff --stat
git diff --name-only
git status --short
```

Result:

- `git diff --check`가 exit code 0으로 완료됐다.
- UNIT-01부터 UNIT-07의 기존 코드·migration·manifest·테스트와 UNIT-08 문서
  변경만 존재함을 확인했다.
- 기존 미커밋 작업을 삭제하거나 되돌리지 않았다.

Status: passed

Command:

```bash
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- Daily 실행 script와 CronJob manifest diff는 없었다.
- Daily `topic_selection_stage.py`에는 UNIT-04에서 검증한 기간 독립 순수 helper
  추출 diff만 있었고 public 결과 model과 실행 계약은 변경되지 않았다.
- Daily 집중 회귀 23개와 전체 test 통과로 기존 계약을 확인했다.

Status: passed

Command:

```bash
rg -n \
  "three_day_topics|three_day_topic_articles|three_day_topic_runs" \
  db/migrations app scripts tests
rg -n \
  "three-day-topics|three_day_topics" \
  app tests docs README.md
rg -n \
  "news-three-day-topic-pipeline|05:00 Asia/Seoul|0 5 \* \* \*" \
  README.md docs k8s tests
```

Result:

- 전용 table 이름이 migration, repository, API, 테스트와 문서에 일관되게
  연결됨을 확인했다.
- API route와 정적 `/home` 계약이 application, tests와 운영 문서에 반영됐다.
- CronJob 이름, schedule과 진입점이 manifest, tests, Architecture와 Runbook에
  일치했다.

Status: passed

Command:

```bash
if rg -n '[[:blank:]]+$' \
  README.md \
  docs/ARCHITECTURE.md \
  docs/RUNBOOK.md \
  docs/architecture \
  docs/runbooks \
  docs/design/three-day-topic-pipeline.md \
  docs/devlog/feature-three-day-topic-pipeline.md \
  docs/pr/feature-three-day-topic-pipeline.md \
  docs/tasks/feature-three-day-topic-pipeline.md \
  docs/verification/feature-three-day-topic-pipeline.md
then
  exit 1
else
  exit 0
fi
```

Result:

- UNIT-08 관련 문서에 trailing whitespace가 없어 exit code 0으로 완료됐다.

Status: passed

### 34. Kubernetes manifest dry-run 및 운영 검증 미실행

Command:

```bash
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

Result:

- 실행하지 않았다.
- 현재 사용자 지시와 forbidden command가 `kubectl apply`를 금지하므로
  client-side dry-run도 사람 수행 항목으로 유지했다.
- 로컬 YAML manifest 테스트 3개는 통과했다.

Status: human-required

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

Result:

- 실행하지 않았다.
- Cluster 접근과 server-side admission 검증은 사람 수행 항목이다.

Status: human-required

## Results

- 설계 문서: `docs/design/three-day-topic-pipeline.md`
- Migration:
  `db/migrations/007_create_three_day_topic_tables.sql`
- 저장 구현:
  - `app/services/three_day_topic_pipeline/models.py`
  - `app/services/three_day_topic_pipeline/repository.py`
- 후보 조회와 embedding 재사용 구현:
  - `app/services/three_day_topic_pipeline/context.py`
  - `app/services/three_day_topic_pipeline/candidate_stage.py`
- 공통 Topic 기사 선정 정책:
  - `app/services/topic_pipeline/selection.py`
- 3일 재클러스터링과 기사 선정:
  - `app/services/three_day_topic_pipeline/topic_selection_stage.py`
- 선택 원문 확보:
  - `app/services/three_day_topic_pipeline/raw_acquisition_stage.py`
- 3일 Summary와 저장 연결:
  - `app/services/three_day_topic_pipeline/summary_persistence_stage.py`
- 3일 Topic read API:
  - `app/routers/three_day_topics.py`
  - `app/main.py`
- 3일 Topic 실행 진입점:
  - `scripts/run_three_day_topic_pipeline.py`
- 3일 Topic CronJob:
  - `k8s/news-three-day-topic-pipeline-cronjob.yaml`
- 문서:
  - `README.md`
  - `docs/ARCHITECTURE.md`
  - `docs/architecture/overview.md`
  - `docs/architecture/pipeline.md`
  - `docs/architecture/database.md`
  - `docs/architecture/backend-api.md`
  - `docs/architecture/k3s-runtime.md`
  - `docs/RUNBOOK.md`
  - `docs/runbooks/cronjobs.md`
  - `docs/runbooks/database-check.md`
  - `docs/runbooks/routine-check.md`
  - `docs/design/three-day-topic-pipeline.md`
  - `docs/pr/feature-three-day-topic-pipeline.md`
  - `docs/devlog/feature-three-day-topic-pipeline.md`
- 집중 테스트:
  `tests/test_three_day_topic_pipeline.py`,
  `tests/test_three_day_topic_repository.py`,
  `tests/test_three_day_topics_api.py`,
  `tests/test_run_three_day_topic_pipeline.py`,
  `tests/test_three_day_topic_pipeline_cronjob_manifest.py`
- 확정한 주요 계약:
  - `Asia/Seoul` 기준으로 한 번 확정한 `[window_start, window_end)` 72시간 범위
  - `coalesce(published_at, created_at)` 기사 시간 정책
  - 호환 metadata와 현재 source hash가 일치하는 저장 embedding만 사용
  - embedding 누락은 제외하고 `missing_embedding_count`로 기록
  - 저장 embedding 기사 직접 재클러스터링과 3일 전용 threshold/상한
  - 대표 기사 ⊆ Summary 근거 기사 ⊆ 관련 기사 부분집합
  - URL·정규화 제목 중복을 제거한 결정론적 Summary 근거 기사 선정
  - Topic 관련 기사와 Summary 근거 기사 분리
  - `three-day-flow-v1` Summary prompt version
  - 저장 원문 우선 사용과 Summary 근거 기사만 대상으로 한 지연 추출
  - 기사·Topic 단위 원문/요약 실패 격리
  - 기사 시각과 bounded 원문을 포함한 versioned Summary input hash
  - 실제 provider 입력 기사만 `is_summary_evidence=true`로 저장
  - 일부 성공은 성공 부분집합 교체, 전부 실패는 기존 window 결과 보존
  - provider 작업 완료 후 transaction 안에서 동일 window 결과 원자적 교체
  - `running`, `success`, `partial_success`, `failed` run 상태
  - 동일 window 결과는 교체하고 run 감사 이력은 보존하는 idempotency 정책
  - 실행 이력 생성·종료 transaction과 결과 교체 transaction 분리
  - advisory transaction lock 이후 기존 window 삭제와 신규 결과 삽입
  - 빈 결과 교체 허용 및 insert 실패 시 전체 rollback
  - archive의 bind filter와 `reference_date`, `window_end`, `id` 최신순 정렬
  - 성공·부분 성공 run의 최신 window 하나만 반환하는 경량 home payload
  - detail의 대표·Summary 근거 flag와 `rank`, `article_id` 기사 정렬
  - 정상 빈 home payload, detail 404와 정적 `/home` 우선 route
  - 기본 dry-run과 timezone-aware ISO 8601 `--window-end`
  - execute에서 Summary provider/key 요구 및 embedding provider option 부재
  - 단계별 count를 포함한 run 성공·부분 성공·실패 종료
  - Daily 이후 `05:00 Asia/Seoul` 전용 CronJob schedule
  - 동시 실행 차단, history/resource/deadline 제한과 기존 runtime pattern 재사용
- 기존 Daily Topic의 외부 계약, 실행 script와 manifest는 변경하지 않았다.
- Daily selection stage는 기간 독립적인 순수 helper를 공통 package에서
  호출하도록 내부 구현만 변경했다.
- 3일 candidate stage는 `article_embeddings`를 조회만 하며 provider 호출,
  embedding insert/update와 Daily Topic table 조회를 수행하지 않는다.

## Manual or Production Verification

- 수행하지 않음.
- `007_create_three_day_topic_tables.sql`의 DB migration 적용과 Supabase SQL은
  사람 통제 작업으로 남겼다.
- Kubernetes client/server dry-run, K3s apply/rollout/Job 실행과 production
  API 확인은 사람 통제 범위이며 수행하지 않았다.

## Pending Verification

- Kubernetes client/server-side manifest dry-run
- 사람 수행 migration 적용과 schema 확인
- 사람 수행 server-side dry-run, K3s 적용과 production verification

## Evidence Notes

- UNIT-01은 설계 작업이므로 DB 또는 provider에 접근하는 pipeline command를
  실행하지 않았다.
- UNIT-02 테스트는 가짜 engine과 migration SQL 정적 검사만 사용했으며 실제
  DB write 또는 migration 적용을 수행하지 않았다.
- UNIT-03 테스트는 가짜 connection만 사용했으며 실제 DB, embedding provider와
  외부 API를 호출하지 않았다.
- UNIT-04 테스트는 메모리 기사·vector fixture만 사용했으며 실제 DB, provider,
  원문 추출과 외부 API를 호출하지 않았다.
- UNIT-05 테스트는 mock extractor·HTTP 요청과 가짜 repository만 사용했으며
  실제 원문 추출, 외부 provider 호출과 DB write를 수행하지 않았다.
- UNIT-06 테스트는 가짜 connection만 사용했으며 실제 DB와 Production API에
  접근하지 않았다.
- UNIT-07 테스트는 mock stage와 로컬 YAML 파싱만 사용했으며 실제 DB write,
  원문 추출, 외부 Summary API와 Kubernetes command를 실행하지 않았다.
- UNIT-08은 문서와 전체 로컬 회귀만 검증했으며 실제 DB, provider, cluster와
  production API에 접근하지 않았다.
- review 문서는 수정 근거로 직접 사용하지 않았고
  `docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md`의 승인 항목만
  적용했다.
- production verification, rollout, deployment와 merge 완료를 주장하지 않는다.

## Approved Fixes Verification

### 53. Approved fixes 적용 전 상태 확인

Command:

```bash
pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/feature-three-day-topic-pipeline.md' -g 'docs/verification/feature-three-day-topic-pipeline.md' -g 'docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'
git status --short
```

Result:

- 현재 작업 경로는 `<repo-root>`였고 branch는
  `feature/three-day-topic-pipeline`이었다.
- 필수 문서가 모두 존재했다.
- 작업 전 변경 파일은
  `docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md`와
  `docs/reviews/feature-three-day-topic-pipeline-coderabbit.md`였다.

Status: passed

### 54. 3일 Pipeline 및 저장 회귀

Command:

```bash
python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topic_repository.py -v
```

Result:

- 첫 실행은 신규 execute-mode fixture가 `summary articles must be a subset of
  related articles` model 불변식을 어겨 1개 실패했다.
- 테스트 fixture의 `related_article_ids`를 실제 계약에 맞게 보정했다.
- 재실행 결과 33개 테스트와 6개 subtest가 모두 통과했다.
- 검증 범위: Dry-run provider 호출 0회, Dry-run API key 불필요, Dry-run 결과
  교체 미실행, execute mode 원문·Summary·repository stage 유지, 후보 조회
  connection 조기 반환, 절대 window 기반 repository 교체 계약.

Status: passed

### 55. 설정 검증 및 공통 Selection 회귀

Command:

```bash
python -m pytest tests/test_three_day_topic_pipeline.py tests/test_daily_topic_article_selection.py tests/test_run_daily_topic_pipeline.py -v
```

Result:

- 39개 테스트와 6개 subtest가 모두 통과했다.
- 비문자열, 빈 문자열과 공백 embedding 설정값이 field 이름을 포함한
  `ValueError`로 처리됨을 확인했다.
- `_as_utc()`의 기존 UTC 변환 동작과 Daily Topic 기사 선정 회귀가 없음을
  확인했다.

Status: passed

### 56. API 및 CronJob manifest 검증

Command:

```bash
python -m pytest tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v
```

Result:

- 9개 테스트가 모두 통과했다.
- Home API가 최신 publishable window의 경량 payload를 유지하고, CronJob이
  기존 schedule, command, Secret, resource, deadline, capability drop,
  seccomp와 `/tmp` `emptyDir` mount 계약을 만족함을 확인했다.
- Dockerfile 최종 `USER`가 없어 `runAsNonRoot`와 `readOnlyRootFilesystem`은
  적용하지 않고 별도 image hardening 작업으로 문서화했다.

Status: passed

### 57. 전체 pytest 회귀

Command:

```bash
python -m pytest
```

Result:

- 265개 테스트가 모두 통과했다.

Status: passed

### 58. unittest 전체 회귀

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 265개 테스트가 모두 통과했다.
- 출력된 argparse usage/error, provider failure와 clustering skipped 로그는
  잘못된 입력과 실패 격리를 검증하는 테스트의 예상 출력이었다.

Status: passed

### 59. Compile 검증

Command:

```bash
python -m compileall app scripts tests
```

Result:

- `app`, `scripts`, `tests`가 모두 compile되었다.
- 생성된 `__pycache__` 디렉터리는 검증 후 제거했다.

Status: passed

### 60. Whitespace와 문서 정합성

Command:

```bash
git diff --check
rg -n 'file://''/|/Users/seo''chanjin|reference_date.*id''empot|id''empot.*reference_date' docs README.md
rg -n 'to_regclass|::regclass|three_day_topic_runs|three_day_topics|three_day_topic_articles' docs/runbooks/database-check.md
```

Result:

- `git diff --check`는 exit code 0으로 완료했다.
- 개인 workspace URI와 `reference_date`를 결과 교체 key처럼 설명하는 문구
  검색은 exit code 1로 match가 없었다.
- `docs/runbooks/database-check.md`에서 3일 Topic table 존재 여부는
  `to_regclass()`로 확인하고, constraint 조회는 존재하는 relation만 대상으로
  사용한다. 출력에 남은 `article_embeddings`의 `::regclass`와
  `conrelid::regclass` 표시 cast는 부분 적용될 수 있는 3일 Topic relation을
  직접 변환하는 용도가 아니다.

Status: passed

### 61. 변경 금지 영역 확인

Command:

```bash
git diff -- app/services/daily_topic_pipeline scripts/run_daily_topic_pipeline.py k8s/news-daily-topic-pipeline-cronjob.yaml
```

Result:

- 출력이 없었다.
- 기존 Daily Topic pipeline package, 실행 script와 Daily CronJob manifest는
  변경하지 않았다.

Status: passed

### 62. Kubernetes dry-run

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=client -f k8s/news-three-day-topic-pipeline-cronjob.yaml
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

Result:

- 실행하지 않았다.
- `kubectl apply`는 project forbidden command에 포함되므로 client/server dry-run도
  사람이 수행할 항목으로 남겼다.

Status: human-required
