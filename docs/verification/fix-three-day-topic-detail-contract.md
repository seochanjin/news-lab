# Verification: 3일 Topic 상세 API key_points 응답 계약 수정

## Verification Status

passed

## Verification Scope

- UNIT-01: Three-day Topic 상세 API 계약과 `key_points` 누락 지점 조사
- UNIT-02: `key_points` 상세 응답 추가 및 API contract test 보강
- UNIT-03: Three-day·Daily·Weekly 회귀 검증 및 작업 문서 정리

## Commands Run

Command:
`pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/fix-three-day-topic-detail-contract.md' -g 'docs/verification/fix-three-day-topic-detail-contract.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'`
Result:
현재 경로가 `/Users/seochanjin/workspace/NewsLab/news-lab`이고 현재 branch가
`fix/three-day-topic-detail-contract`임을 확인했다. 필수 문서 파일이 모두
존재했다.
Status: passed
Notes:
작업 전 branch와 필수 문서 위치 확인.

Command:
`git status --short`
Result:
기존 변경으로 `docs/tasks/main.md`가 modified이고, 현재 task·verification 및
review/fix/pr/devlog 문서가 untracked 상태였다.
Status: passed
Notes:
기존 작업 트리 변경은 사용자 변경으로 간주했다.

Command:
`sed -n '1,240p' AGENTS.md`
Result:
WIP 1, 금지 command, workflow artifact, 검증 원칙과 주요 backend 구성 지침을
확인했다.
Status: passed
Notes:
Read-only 문서 확인.

Command:
`sed -n '1,260p' docs/tasks/fix-three-day-topic-detail-contract.md`
Result:
Goal, Scope, Do not change, Expected files, DB changes, API changes를 확인했다.
Status: passed
Notes:
Task가 요구사항의 source of truth임을 확인했다.

Command:
`sed -n '1,260p' docs/verification/fix-three-day-topic-detail-contract.md`
Result:
Verification 문서가 `pending` 상태이고 command 기록이 비어 있음을 확인했다.
Status: passed
Notes:
UNIT-01 실제 실행 command를 기록하기 전 상태 확인.

Command:
`sed -n '1,240p' docs/agent/backend-workflow.md`
Result:
WIP 1 순서, checklist 갱신 기준, source of truth 우선순위와 review/fix 역할을
확인했다.
Status: passed
Notes:
Read-only 문서 확인.

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`
Result:
구현 전 확인 항목, 검증 기록 기준, Python docstring 정책 참조를 확인했다.
Status: passed
Notes:
Read-only 문서 확인.

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`
Result:
작업 전 상태, 작업 단위 완료, 전체 변경 범위, end-to-end gate와 command 기록
형식을 확인했다.
Status: passed
Notes:
Read-only 문서 확인.

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`
Result:
`git push`, `git merge`, production DB/Supabase SQL, Kubernetes 변경 command와
secret 수정 금지를 확인했다.
Status: passed
Notes:
Read-only 문서 확인.

Command:
`sed -n '1,260p' docs/agent/task-authoring-guide.md`
Result:
Implementation Units 형식과 Python 문서화 정책을 확인했다.
Status: passed
Notes:
UNIT-01에서는 Python 코드를 수정하지 않았다.

Command:
`sed -n '241,520p' docs/tasks/fix-three-day-topic-detail-contract.md`
Result:
Test commands와 Acceptance criteria를 확인했다.
Status: passed
Notes:
UNIT-01 범위에서는 조사 command만 실행했다.

Command:
`sed -n '521,760p' docs/tasks/fix-three-day-topic-detail-contract.md`
Result:
Notes와 Implementation Units를 확인했다. 현재 대상은 UNIT-01이고 UNIT-02,
UNIT-03은 아직 진행하지 않았다.
Status: passed
Notes:
WIP 1 유지.

Command:
`rg -n "ThreeDayTopic|three_day_topic|three-day-topics|key_points" app tests`
Result:
Three-day Topic API는 `app/routers/three_day_topics.py`와
`tests/test_three_day_topics_api.py`에 위치했다. Three-day pipeline 저장 경로는
`app/services/three_day_topic_pipeline/repository.py`에서 `key_points`를
저장하고, API 상세 router 검색 결과에는 `key_points` 조회가 없었다.
Status: passed
Notes:
Task의 구현 전 검색 command 실행.

Command:
`rg -n "response_model|BaseModel|articles|keywords" app/routers app/schemas app/services tests`
Result:
`app/schemas` 경로가 없어 `rg: app/schemas: No such file or directory`로 exit
code 2가 반환됐다. 출력에는 `app/routers/three_day_topics.py` 상세 query가
`keywords`와 `articles`를 반환하지만 `key_points`를 조회하지 않는 정황이
포함됐다.
Status: failed
Notes:
Task에 제시된 검색 command를 그대로 실행했으며, 실패 원인은 현재 저장소에
`app/schemas` 디렉터리가 없기 때문이다. 코드 수정 검증 실패가 아니라 조사
command의 경로 불일치다.

Command:
`rg --files app tests | rg '(^app/(routers|services|schemas)|tests/test_three_day_topics_api.py|tests/test_weekly_topics_api.py)'`
Result:
`app/routers/three_day_topics.py`, `app/routers/weekly_topics.py`,
`tests/test_three_day_topics_api.py`, `tests/test_weekly_topics_api.py`와 topic
pipeline service 파일들을 확인했다. `app/schemas` 파일은 없었다.
Status: passed
Notes:
없는 `app/schemas` 경로를 제외하고 실제 구조를 재확인했다.

Command:
`nl -ba app/routers/three_day_topics.py | sed -n '1,230p'`
Result:
Three-day Topic router가 목록, home, 상세 endpoint를 한 파일에서 구현하며
별도 response model 없이 dict를 반환함을 확인했다. 상세 query는
`app/routers/three_day_topics.py` 151-167행에서 topic row를 조회하지만
`key_points`를 SELECT하지 않는다. 반환은 196행에서 `dict(row)`와 `articles`를
합치는 방식이다.
Status: passed
Notes:
UNIT-01 누락 지점 확인.

Command:
`nl -ba tests/test_three_day_topics_api.py | sed -n '1,300p'`
Result:
Three-day Topic API 테스트는 fake connection으로 SQL bind와 payload 조립을
검증한다. `three_day_topic_row()` fixture에는 `key_points`가 없고, 상세 테스트는
기사 정렬과 role flag만 확인한다.
Status: passed
Notes:
UNIT-02에서 API contract test 보강 필요.

Command:
`nl -ba app/routers/weekly_topics.py | sed -n '145,220p'`
Result:
Weekly Topic 상세 query는 `app/routers/weekly_topics.py` 161-180행에서
`key_points`를 SELECT하고 210행에서 `dict(row)`와 `articles`를 합쳐 반환한다.
Status: passed
Notes:
Three-day 상세 query와 비교 기준으로 확인했다.

Command:
`git status --short`
Result:
`docs/tasks/main.md`는 기존 modified 상태이고, branch별 task, verification,
review, fix, pr, devlog 문서가 untracked 상태로 표시됐다.
Status: passed
Notes:
UNIT-01에서 갱신한 문서는 `docs/tasks/fix-three-day-topic-detail-contract.md`와
`docs/verification/fix-three-day-topic-detail-contract.md`다.

Command:
`git diff --stat`
Result:
Tracked diff 기준으로 `docs/tasks/main.md | 2 +-`만 표시됐다. 현재 branch별
task/verification 문서는 untracked라 이 출력에는 포함되지 않았다.
Status: passed
Notes:
기존 tracked 변경을 되돌리지 않았다.

Command:
`git diff --check`
Result:
출력 없음. Tracked diff 기준 whitespace error가 없었다.
Status: passed
Notes:
Untracked 문서는 `git diff --check` 대상에 포함되지 않는다.

Command:
`git diff --name-only`
Result:
Tracked diff 기준 `docs/tasks/main.md`만 표시됐다.
Status: passed
Notes:
Untracked 문서는 `git status --short`로 확인했다.

Command:
`rg -n "UNIT-01|누락 지점|key_points|Status:" docs/tasks/fix-three-day-topic-detail-contract.md docs/verification/fix-three-day-topic-detail-contract.md`
Result:
Task 문서에 UNIT-01 완료 체크와 조사 결과가 있고, Verification 문서에
`key_points` 누락 지점과 command별 status가 기록되어 있음을 확인했다.
Status: passed
Notes:
문서 갱신 내용 확인.

Command:
`git diff -- db/migrations requirements.txt pyproject.toml poetry.lock uv.lock`
Result:
출력 없음. DB migration, dependency 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- app/services/daily_topic_pipeline scripts/run_daily_topic_pipeline.py k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Daily Topic pipeline 및 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- app/services/weekly_topic_pipeline scripts/run_weekly_topic_pipeline.py k8s/news-weekly-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Weekly Topic pipeline 및 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- k8s Dockerfile .github`
Result:
출력 없음. Kubernetes manifest, Dockerfile, GitHub Actions 관련 tracked diff가
없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`python -m pytest tests/test_three_day_topics_api.py -v`
Result:
8개 테스트가 모두 통과했다.
Status: passed
Notes:
Three-day Topic 상세 API의 `key_points` 값 있음, `NULL`, 빈 배열 계약과 기존
articles 정렬/role flag 회귀를 확인했다.

Command:
`python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topics_api.py tests/test_three_day_topic_pipeline_cronjob_manifest.py -v`
Result:
35개 테스트와 6개 subtest가 모두 통과했다.
Status: passed
Notes:
Three-day Topic pipeline, API, CronJob manifest 회귀 확인.

Command:
`python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v`
Result:
23개 테스트가 모두 통과했다.
Status: passed
Notes:
Daily Topic pipeline과 CronJob manifest 회귀 확인.

Command:
`python -m pytest tests/test_run_weekly_topic_pipeline.py tests/test_weekly_topic_pipeline.py tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`
Result:
44개 테스트와 13개 subtest가 모두 통과했다.
Status: passed
Notes:
Weekly Topic pipeline, API, CronJob manifest 회귀 확인.

Command:
`python -m pytest`
Result:
409개 테스트가 모두 통과했다.
Status: passed
Notes:
전체 pytest 회귀 확인.

Command:
`python -m unittest discover -s tests`
Result:
409개 테스트가 모두 통과했다. 일부 테스트가 의도적으로 argparse 오류 메시지와
실패 시나리오 로그를 출력했지만 최종 결과는 `OK`였다.
Status: passed
Notes:
전체 unittest 회귀 확인.

Command:
`python -m compileall app scripts tests`
Result:
app, scripts, tests compile 검증이 통과했다.
Status: passed
Notes:
Python compile gate 확인.

Command:
`git status --short`
Result:
`app/routers/three_day_topics.py`, `tests/test_three_day_topics_api.py`,
`docs/tasks/main.md`가 modified이고, branch별 task/verification/review/fix/pr/devlog
문서가 untracked 상태였다.
Status: passed
Notes:
`docs/tasks/main.md`는 현재 task pointer 변경으로 기존 tracked 변경 상태를
유지했다.

Command:
`git diff --stat`
Result:
Tracked diff 기준 `app/routers/three_day_topics.py`, `tests/test_three_day_topics_api.py`,
`docs/tasks/main.md`에 54 insertions, 4 deletions가 표시됐다.
Status: passed
Notes:
Branch별 문서는 untracked라 stat에 포함되지 않는다.

Command:
`git diff --check`
Result:
출력 없음. Whitespace error가 없었다.
Status: passed
Notes:
Whitespace gate 확인.

Command:
`git diff --name-only`
Result:
Tracked diff 기준 `app/routers/three_day_topics.py`, `docs/tasks/main.md`,
`tests/test_three_day_topics_api.py`가 표시됐다.
Status: passed
Notes:
변경 범위 확인.

Command:
`git diff -- db/migrations requirements.txt pyproject.toml poetry.lock uv.lock`
Result:
출력 없음. DB migration과 dependency 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- app/services/daily_topic_pipeline scripts/run_daily_topic_pipeline.py k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Daily Topic pipeline과 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- app/services/weekly_topic_pipeline scripts/run_weekly_topic_pipeline.py k8s/news-weekly-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Weekly Topic pipeline과 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`git diff -- k8s Dockerfile .github`
Result:
출력 없음. Kubernetes manifest, Dockerfile, GitHub Actions 관련 tracked diff가
없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

Command:
`rg -n "key_points" app/routers app/services tests/test_three_day_topics_api.py`
Result:
`app/routers/three_day_topics.py` 상세 query와 반환 정규화, Three-day/Weekly
pipeline 저장 경로, Daily reporting, Weekly 상세 API, Three-day API 테스트의
`key_points` 검증 위치가 표시됐다.
Status: passed
Notes:
현재 저장소에는 `app/schemas` 디렉터리가 없어 실제 존재 경로 기준으로 확인했다.

Command:
`git diff -- docs/tasks/main.md`
Result:
`docs/tasks/main.md`가 현재 task pointer를
`fix-three-day-topic-detail-contract.md`로 가리키는 diff를 확인했다.
Status: passed
Notes:
기존 변경으로 간주하고 되돌리지 않았다.

Command:
`git diff -- app/routers/three_day_topics.py tests/test_three_day_topics_api.py`
Result:
Three-day 상세 SELECT에 `key_points`를 추가하고, `NULL`을 `[]`로 정규화하며,
테스트 fixture와 상세 API contract test가 추가된 diff를 확인했다.
Status: passed
Notes:
UNIT-02 구현 diff 재확인.

Command:
`rg -n "Verification Status|passed|UNIT-03|Pending Verification|409 passed|35개|23개|44개|compileall|git diff --check" docs/verification/fix-three-day-topic-detail-contract.md docs/tasks/fix-three-day-topic-detail-contract.md docs/pr/fix-three-day-topic-detail-contract.md docs/devlog/fix-three-day-topic-detail-contract.md`
Result:
Verification status, UNIT-03 체크리스트, PR/devlog 테스트 결과 기록 위치를
확인했다. 이 과정에서 UNIT-01 당시 상태 설명이 현재 상태처럼 읽힐 수 있음을
확인해 문구를 보정했다.
Status: passed
Notes:
문서 정합성 확인.

Command:
`sed -n '96,120p' docs/verification/fix-three-day-topic-detail-contract.md`
Result:
UNIT-01 당시 command 결과 section에 "UNIT-03은 아직 진행하지 않았다"는 과거
실행 시점의 결과가 남아 있음을 확인했다.
Status: passed
Notes:
Historical command result로 보존했다.

Command:
`sed -n '580,594p' docs/verification/fix-three-day-topic-detail-contract.md`
Result:
Manual/Production Verification은 미수행, Pending Verification은 없음으로 기록된
것을 확인했다.
Status: passed
Notes:
Production verification을 완료로 표시하지 않았다.

Command:
`rg -n "Status: failed|아직|pending" docs/verification/fix-three-day-topic-detail-contract.md docs/tasks/fix-three-day-topic-detail-contract.md`
Result:
초기 Verification 문서가 pending이었던 이력, UNIT-01 당시 UNIT-03 미진행 이력,
`app/schemas` 경로 부재로 실패한 조사 command, task의 production curl 미실행
주의 문구를 확인했다.
Status: passed
Notes:
과거 실패/미진행 이력은 실제 실행 결과로 보존했다.

Command:
`git diff --check`
Result:
출력 없음. Whitespace error가 없었다.
Status: passed
Notes:
문서 갱신 후 whitespace 확인.

Command:
`git status --short`
Result:
`app/routers/three_day_topics.py`, `tests/test_three_day_topics_api.py`,
`docs/tasks/main.md`가 modified이고, branch별 task/verification/review/fix/pr/devlog
문서가 untracked 상태였다.
Status: passed
Notes:
최종 working tree 상태 확인.

Command:
`rg -n "Verification Status|Pending Verification|UNIT-03 검증 결과|\[x\] UNIT-03|409 passed|409개 테스트|없음\." docs/verification/fix-three-day-topic-detail-contract.md docs/tasks/fix-three-day-topic-detail-contract.md docs/pr/fix-three-day-topic-detail-contract.md docs/devlog/fix-three-day-topic-detail-contract.md`
Result:
Verification status, pending 없음, UNIT-03 완료 체크, task/pr/devlog의 주요 검증
결과 기록을 확인했다.
Status: passed
Notes:
최종 문서 기록 확인.

Command:
`sed -n '241,620p' docs/tasks/fix-three-day-topic-detail-contract.md`
Result:
Test commands, Acceptance criteria, Notes, Implementation Units를 확인했다. 현재
요청 대상은 UNIT-02 하나뿐임을 확인했다.
Status: passed
Notes:
UNIT-02 시작 전 task 범위 재확인.

Command:
`sed -n '1,260p' app/routers/three_day_topics.py`
Result:
상세 router가 topic row와 article rows를 각각 조회한 뒤 `dict(row)`에
`articles`를 추가해 반환하는 구조임을 확인했다. 상세 topic SELECT에는
`key_points`가 없었다.
Status: passed
Notes:
UNIT-02 수정 전 코드 구조 확인.

Command:
`sed -n '1,340p' tests/test_three_day_topics_api.py`
Result:
기존 상세 테스트가 `articles` 순서와 role flag를 검증하지만 `key_points` 응답
계약은 검증하지 않음을 확인했다.
Status: passed
Notes:
UNIT-02 테스트 보강 지점 확인.

Command:
`sed -n '1,260p' docs/pr/fix-three-day-topic-detail-contract.md && sed -n '1,260p' docs/devlog/fix-three-day-topic-detail-contract.md`
Result:
PR draft와 devlog draft는 heading만 있는 빈 초안 상태임을 확인했다.
Status: passed
Notes:
UNIT-02에서는 요청된 Verification과 UNIT checklist만 갱신하고, 최종 문서 정리는
UNIT-03 범위로 남겼다.

Command:
`rg -n "key_points" app/routers app/services tests/test_three_day_topics_api.py`
Result:
`app/routers/three_day_topics.py` 상세 query와 반환 정규화에 `key_points`가
반영됐고, `tests/test_three_day_topics_api.py`에 값 있음, `NULL`, 빈 배열 계약
검증이 추가됐음을 확인했다. Three-day pipeline 저장 경로에는 기존
`key_points` 저장 코드가 유지됐다.
Status: passed
Notes:
Task에 지정된 변경 후 `key_points` 반영 확인. 현재 저장소에는 `app/schemas`
경로가 없어 실제 존재 경로만 대상으로 실행했다.

Command:
`python -m pytest tests/test_three_day_topics_api.py -v`
Result:
8개 테스트가 모두 통과했다.
Status: passed
Notes:
상세 API의 `key_points` 값 있음, `NULL`, 빈 배열 계약과 기존 archive/home/detail
회귀를 포함한 집중 테스트.

Command:
`git status --short`
Result:
`app/routers/three_day_topics.py`와 `tests/test_three_day_topics_api.py`가 modified로
표시됐다. 기존 변경인 `docs/tasks/main.md` modified와 branch별 task,
verification, review, fix, pr, devlog untracked 상태도 유지됐다.
Status: passed
Notes:
UNIT-02 코드 변경과 기존 작업 트리 상태 확인.

Command:
`git diff --stat`
Result:
Tracked diff 기준 `app/routers/three_day_topics.py`, `docs/tasks/main.md`,
`tests/test_three_day_topics_api.py`가 표시됐다. Branch별 task/verification 문서는
untracked라 stat에는 포함되지 않았다.
Status: passed
Notes:
기존 `docs/tasks/main.md` 변경은 되돌리지 않았다.

Command:
`git diff --check`
Result:
출력 없음. Tracked diff 기준 whitespace error가 없었다.
Status: passed
Notes:
UNIT-02 변경 후 whitespace 확인.

Command:
`rg -n "UNIT-02|key_points|Status:" docs/tasks/fix-three-day-topic-detail-contract.md docs/verification/fix-three-day-topic-detail-contract.md`
Result:
Task 문서에 UNIT-02 구현 결과와 완료 checklist가 있고, Verification 문서에
UNIT-02 command 결과와 `key_points` 변경 내용이 기록되어 있음을 확인했다.
Status: passed
Notes:
UNIT-02 문서 갱신 확인.

Command:
`git diff --name-only`
Result:
Tracked diff 기준 `app/routers/three_day_topics.py`,
`tests/test_three_day_topics_api.py`, 기존 변경 `docs/tasks/main.md`가 표시됐다.
Status: passed
Notes:
Branch별 task/verification 문서는 untracked라 이 출력에는 포함되지 않는다.

Command:
`git diff -- db/migrations requirements.txt pyproject.toml poetry.lock uv.lock`
Result:
출력 없음. DB migration과 dependency 관련 tracked diff가 없었다.
Status: passed
Notes:
비대상 영역 변경 없음.

Command:
`git diff -- app/services/daily_topic_pipeline scripts/run_daily_topic_pipeline.py k8s/news-daily-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Daily Topic pipeline과 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
비대상 영역 변경 없음.

Command:
`git diff -- app/services/weekly_topic_pipeline scripts/run_weekly_topic_pipeline.py k8s/news-weekly-topic-pipeline-cronjob.yaml`
Result:
출력 없음. Weekly Topic pipeline과 CronJob 관련 tracked diff가 없었다.
Status: passed
Notes:
비대상 영역 변경 없음.

Command:
`git diff -- k8s Dockerfile .github`
Result:
출력 없음. Kubernetes manifest, Dockerfile, GitHub Actions 관련 tracked diff가
없었다.
Status: passed
Notes:
금지 또는 비대상 영역 변경 없음.

## Results

- 누락 지점: `app/routers/three_day_topics.py`의 `GET /three-day-topics/{topic_id}`
  상세 topic SELECT가 `key_points`를 조회하지 않는다.
- 현재 Three-day Topic API에는 별도 `app/schemas` response model이 없고, router가
  SQLAlchemy mapping row를 `dict(row)`로 변환해 반환한다.
- 상세 반환 조립은 `dict(row)`에 `articles`만 추가하므로, row에 없는
  `key_points`는 응답에 포함될 수 없다.
- Three-day Topic 목록 API와 home API의 SELECT에도 `key_points`가 없으며, 이는
  이번 task의 "목록 API와 홈 API 계약은 변경하지 않는다" 조건과 일치한다.
- Weekly Topic 상세 API는 같은 패턴에서 `key_points`를 SELECT하고 있어,
  Three-day Topic 상세 API도 UNIT-02에서 상세 SELECT와 반환 정규화만 최소 수정하면
  될 것으로 판단된다.
- UNIT-01 당시 `tests/test_three_day_topics_api.py`의 fixture와 상세 테스트에는
  `key_points` 계약 검증이 없었다.
- UNIT-02에서 `app/routers/three_day_topics.py` 상세 SELECT에 `key_points`를
  추가했다.
- UNIT-02에서 상세 row를 dict로 변환한 뒤 `topic["key_points"] =
  topic.get("key_points") or []`로 정규화해 DB 값이 `NULL`인 경우 빈 배열을
  반환하도록 했다. DB 값이 기존 배열이면 순서를 변경하지 않는다.
- UNIT-02에서 `tests/test_three_day_topics_api.py`에 상세 전용 row fixture를
  추가하고, `key_points` 값 있음, `NULL`, 빈 배열 응답 계약을 검증했다.
- 기존 `articles` 배열 구조와 정렬 검증은 유지했다.
- UNIT-03에서 task 지정 집중 테스트, Three-day/Daily/Weekly 회귀 테스트, 전체
  pytest, 전체 unittest, compileall, diff/금지 영역 gate가 모두 통과했다.

## Manual or Production Verification

- 수행하지 않음.
- Production DB 조회, production API curl, K3s 변경, deploy, rollout은 실행하지
  않았다.

## Pending Verification

- 없음.

## Evidence Notes

- `three_day_topics.key_points` 저장 경로는 pipeline repository에 이미 존재하므로
  UNIT-01 기준 DB schema, migration, pipeline 저장 로직 변경 필요성은 발견되지
  않았다.
- UNIT-01에서 확인된 현재 범위의 결함인 Three-day Topic 상세 query의
  `key_points` 누락은 UNIT-02에서 수정했다.
- 후속 작업 후보: Frontend 상세 페이지의 기간 및 관련 기사 표시 문제는 task Notes
  그대로 별도 작업 대상이다.

## 조사 결과

### UNIT-01 조사 결과

- 현재 Three-day Topic API는 별도 `app/schemas` response model 없이
  `app/routers/three_day_topics.py` router에서 SQLAlchemy mapping row를
  `dict(row)`로 변환해 반환한다.
- `GET /three-day-topics/{topic_id}` 상세 query는 `id`, `reference_date`,
  `window_start`, `window_end`, `title_ko`, `summary_ko`, `keywords`,
  `article_count`, `source_count`, `status`, `provider`, `model`,
  `prompt_version`, `created_at`, `updated_at`를 조회하지만 `key_points`를
  조회하지 않는다.
- 상세 응답 조립은 topic row에 `articles` 배열만 추가하므로, DB row에 존재하는
  `key_points`도 SELECT되지 않으면 응답에 포함될 수 없다.
- Three-day Topic 목록 API와 home API에는 `key_points`를 추가하지 않는 것이 현재
  task의 "목록 API와 홈 API 계약은 변경하지 않는다" 조건에 맞다.
- `tests/test_three_day_topics_api.py`의 fixture와 상세 API 테스트는 현재
  `key_points` 값 있음, `NULL`, 빈 배열 계약을 검증하지 않는다.
- UNIT-02에서는 상세 SELECT에 `key_points`를 추가하고, `NULL`을 `[]`로 정규화하며,
  기존 `articles` 배열 구조와 정렬을 유지하는 API contract test를 보강해야 한다.
