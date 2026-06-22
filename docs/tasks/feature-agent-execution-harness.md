# Task: 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## Goal

현재 NewsLab Agent workflow는 다음 방식으로 운영된다.

```text
Task 작성
→ scripts/agent_next_step.sh로 프롬프트 생성
→ 사용자가 프롬프트를 Codex 또는 Antigravity에 복사
→ Agent 실행
→ 사용자가 결과 확인
→ 다음 단계 프롬프트 생성
```

이 방식은 Task, Verification, Review, Approved Fixes, PR, Devlog 문서를 기준으로 작업 절차를 표준화하지만 다음 한계가 있다.

- 생성된 프롬프트를 매번 직접 복사해야 한다.
- 현재 상태에 맞는 다음 명령을 사용자가 기억해야 한다.
- `main` 또는 잘못된 workflow 상태에서도 프롬프트를 생성할 수 있다.
- Agent 실행 결과와 로그가 자동으로 보존되지 않는다.
- Task마다 공통 안전 규칙과 검증 규칙이 반복된다.
- workflow 사용법을 설명하는 통합 한글 가이드가 부족하다.
- 현재 테스트 실행 방식이 `unittest` 중심이며 공통 pytest 실행 환경이 없다.

이번 작업에서는 기존 prompt-only workflow를 유지하면서, 명령 하나로 Codex와 Antigravity CLI를 직접 실행할 수 있는 Agent 실행 하네스를 추가한다.

구현 작업은 다음 두 가지 모드를 지원한다.

### 일반 실행 모드

Task 전체를 한 번의 Codex 실행 대상으로 사용한다.

```bash
scripts/agent_run.sh codex-implement
```

작고 명확한 기능 추가, 버그 수정, 문서 수정 및 빠른 MVP 구현에 사용한다.

### 작업 단위 실행 모드

Task에 정의된 현재 미완료 작업 단위 하나만 Codex 실행 대상으로 사용한다.

```bash
scripts/agent_run.sh codex-implement-unit
```

대규모 리팩터링, 단계별 의존성이 있는 작업, 범위 통제가 중요한 작업에 선택적으로 사용한다.

모든 작업에 작업 단위 방식을 강제하지 않는다. 기본적으로는 일반 실행 모드로 빠르게 결과를 만들고, 복잡하거나 위험한 작업에만 작업 단위 모드를 사용한다.

한글 사용 가이드와 Task 작성 가이드를 추가해 사용자가 명령 순서와 문서 역할을 기억하지 않아도 workflow를 진행할 수 있게 한다.

기존 `unittest` 테스트는 유지하면서 `pytest`를 개발 의존성과 공통 테스트 실행기로 추가한다.

---

## Scope

### 1. 기존 prompt-only workflow 유지

기존 `scripts/agent_next_step.sh`는 프롬프트만 생성하는 진입점으로 유지한다.

기존 command와 문서 경로를 조사한 뒤 현재 인터페이스를 가능한 한 유지한다.

지원 대상 예:

```bash
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh codex-implement-unit
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh codex-fix
scripts/agent_next_step.sh status
```

`agent_next_step.sh`는 Codex나 Antigravity를 직접 실행하지 않는다.

기존 `docs/prompts/*` 문서는 삭제하지 않고 호환용 보조 문서로 유지한다.

---

### 2. Agent 직접 실행 진입점 추가

다음 형태의 실행 진입점을 추가한다.

```bash
scripts/agent_run.sh codex-implement
scripts/agent_run.sh codex-implement-unit
scripts/agent_run.sh antigravity-review
scripts/agent_run.sh codex-fix
```

실행 흐름:

```text
실행 전 gate 검사
→ 대상 action의 프롬프트 생성
→ 대상 Agent CLI 실행
→ 종료 코드와 실행 시간 수집
→ prompt, stdout, stderr 및 실행 결과 저장
→ 실행 결과와 다음 확인 사항 출력
```

설치된 Codex CLI와 Antigravity CLI의 실제 명령 및 지원 옵션을 조사한 뒤 연동한다.

확인되지 않은 CLI 옵션이나 입력 형식을 추측해서 사용하지 않는다.

CLI를 찾을 수 없거나 실행 방법이 지원되지 않으면 임의로 대체하지 않고, 확인된 제약과 수동 사용 방법을 한글로 안내한다.

---

### 3. 일반 실행 모드

다음 명령은 현재 Task 전체를 Codex 구현 범위로 전달한다.

```bash
scripts/agent_run.sh codex-implement
```

실행 조건:

- 현재 branch가 `main` 또는 `master`가 아니다.
- 현재 branch에 대응하는 Task 문서가 존재한다.
- Task의 필수 section을 읽을 수 있다.
- 현재 단계가 Approved Fix 적용 전용 상태가 아니다.
- Codex CLI를 실행할 수 있다.

일반 실행 모드는 기본 구현 방식이다.

다음 작업에 사용한다.

- 빠른 MVP 구현
- 작거나 중간 규모의 기능 추가
- 범위가 명확한 버그 수정
- 문서 및 테스트 수정
- 실패 시 되돌리기 쉬운 작업
- 우선 전체 흐름을 만든 뒤 후속 작업에서 구조를 개선할 작업

Agent가 Task 전체를 구현하더라도 Task의 Scope, Do not change, Test commands 및 Acceptance criteria를 따라야 한다.

---

### 4. 작업 단위 실행 모드

향후 신규 Task 템플릿에 다음 section을 추가한다.

```markdown
## Implementation Units

없음
```

일반 실행 모드에서는 `없음`을 유지한다.

작업 단위 실행이 필요한 경우 `없음`을 삭제하고 다음처럼 작성한다.

```markdown
## Implementation Units

- [ ] UNIT-01: 첫 번째 작업 단위
- [ ] UNIT-02: 두 번째 작업 단위
- [ ] UNIT-03: 세 번째 작업 단위
```

다음 명령은 첫 번째 미완료 UNIT 하나만 Codex 구현 범위로 전달한다.

```bash
scripts/agent_run.sh codex-implement-unit
```

작업 단위 실행 모드는 다음을 수행한다.

- `Implementation Units` section을 읽는다.
- 첫 번째 미완료 `UNIT-NN` 항목을 찾는다.
- 현재 UNIT 하나만 포함한 프롬프트를 생성한다.
- 현재 UNIT 관련 구현, 테스트 및 Verification만 수행하도록 안내한다.
- 후속 UNIT을 미리 구현하거나 완료 처리하지 않도록 안내한다.
- Agent 종료 후 다음 UNIT을 자동으로 연속 실행하지 않는다.
- 사용자가 결과를 확인한 후 같은 명령을 다시 실행하면 다음 미완료 UNIT을 선택한다.

다음 경우 실행을 차단한다.

- `Implementation Units`가 `없음`
- UNIT checklist가 존재하지 않음
- `없음`과 UNIT checklist가 동시에 존재함
- UNIT 형식을 파싱할 수 없음
- 모든 UNIT이 완료됨
- 완료 순서가 비정상적임
- 현재 branch가 `main` 또는 `master`

Task의 Goal과 Scope를 AI가 자동으로 UNIT으로 나누는 기능은 이번 작업에 포함하지 않는다.

작업 단위 자동 연속 실행도 이번 작업에 포함하지 않는다.

---

### 5. 신규 Task 템플릿 갱신

`scripts/new_agent_task.sh`가 생성하는 신규 Task 템플릿을 다음 구조로 변경한다.

```markdown
# Task: <작업명>

## Goal

## Scope

## Do not change

## Expected files

## DB changes

## API changes

## Test commands

## Acceptance criteria

## Notes

## Implementation Units

없음
```

이 변경은 58차 구현이 완료된 이후 생성되는 신규 Task부터 적용한다.

현재 58차 Task에는 아직 지원되지 않는 `Implementation Units` section을 추가하지 않는다.

기존 Task 문서를 일괄 변환하지 않는다.

기존 Task에 `Implementation Units`가 없으면 기존 일반 실행 방식과 호환되도록 처리한다.

---

### 6. 실행 전 안전 gate

하네스는 action 실행 전에 최소한 다음을 검사한다.

#### 공통 검사

- 현재 위치가 NewsLab Git repository인지
- 현재 branch를 확인할 수 있는지
- 현재 branch에 대응하는 Task 문서가 존재하는지
- `docs/tasks/main.md`가 현재 Task를 올바르게 가리키는지
- action에 필요한 workflow 문서가 존재하는지
- 대상 Agent CLI를 실행할 수 있는지

#### 구현 및 Fix 검사

다음 branch에서는 실행을 차단한다.

```text
main
master
```

#### Codex Fix 검사

다음 조건을 확인한다.

- 현재 branch에 대응하는 Approved Fixes 파일이 존재한다.
- `Approved Fixes` section에 실제 적용 대상이 존재한다.
- Review 문서만 있고 Approved Fixes가 없으면 실행하지 않는다.
- 승인된 수정사항 외의 변경을 수행하지 않도록 프롬프트를 제한한다.

#### Antigravity Review 검사

다음 조건을 가능한 범위에서 확인한다.

- Task 문서가 존재한다.
- 구현 변경사항이 존재한다.
- Verification 문서가 존재한다.
- 명시적인 테스트 실패가 남아 있지 않다.

복잡한 PR readiness 상태 머신과 모든 문서의 완전한 의미 분석은 이번 범위에 포함하지 않는다.

---

### 7. 실행 전 확인 및 preview

Agent 실행 전에 다음 정보를 출력한다.

```text
Action
Target Agent
Current branch
Task path
Execution mode
Current UNIT
Log directory
Timeout
```

기존 prompt-only 방식으로 실행 내용을 미리 확인할 수 있어야 한다.

```bash
scripts/agent_next_step.sh codex-implement
```

직접 실행은 별도 명령으로 수행한다.

```bash
scripts/agent_run.sh codex-implement
```

필요하면 다음 옵션을 지원한다.

```bash
scripts/agent_run.sh codex-implement --preview
scripts/agent_run.sh codex-implement --yes
scripts/agent_run.sh codex-implement --timeout 1200
```

정확한 옵션과 기본 확인 방식은 기존 script convention 및 CLI 사용성을 조사한 뒤 결정한다.

명시적인 실행 명령과 prompt-only 명령은 구분한다.

---

### 8. 실행 로그 저장

각 Agent 실행에 대해 다음 정보를 저장한다.

- 실행 시각
- 현재 branch
- Task 경로
- 실행 action
- 일반 또는 작업 단위 모드
- 현재 UNIT
- 대상 Agent
- 사용한 prompt
- process 종료 코드
- 실행 시간
- timeout 여부
- stdout
- stderr

권장 저장 경로:

```text
.agent-runs/<safe-branch>/<timestamp>-<action>/
```

예:

```text
.agent-runs/feature-agent-execution-harness/
└── 20260622T143000-codex-implement/
    ├── prompt.md
    ├── stdout.log
    ├── stderr.log
    └── result.json
```

`.agent-runs/`는 기본적으로 Git에서 제외하는 방향을 검토한다.

Verification에는 실행 로그 전체를 복사하지 않고 다음을 기록할 수 있다.

- 실행 action
- 대상 Agent
- 대상 UNIT
- 종료 코드
- 실제 검증 결과
- 로그 위치
- 남은 사람 작업

Agent process가 종료 코드 0으로 끝났다는 사실만으로 구현, 테스트 또는 Task 완료를 자동 주장하지 않는다.

---

### 9. Timeout 및 비정상 종료 처리

Agent runner는 timeout을 지원한다.

예:

```bash
scripts/agent_run.sh codex-implement --timeout 1200
```

다음 원칙을 적용한다.

- 기본 timeout을 한글 가이드에 명시한다.
- timeout 발생 시 Agent subprocess를 종료한다.
- timeout을 성공으로 처리하지 않는다.
- 비정상 종료 코드를 보존한다.
- stdout과 stderr를 유지한다.
- 실패 원인과 로그 위치를 한글로 출력한다.
- 실패한 실행을 같은 action으로 재시도할 수 있다.
- 실패했다고 Task checklist나 Verification을 자동 완료 처리하지 않는다.

하네스는 Agent 실행 단위 전체를 중단할 수 있지만, Agent 내부의 파일 수정이나 판단 단계마다 실시간으로 개입하지 않는다.

---

### 10. 상태 확인 기능

다음 명령을 지원한다.

```bash
scripts/agent_next_step.sh status
```

또는 현재 구조에 더 적합한 별도 status entrypoint를 추가할 수 있다.

일반 Task 출력 예:

```text
Task:
- 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

Branch:
- feature/agent-execution-harness

Execution mode:
- general

Verification:
- pending

Review:
- not started

Approved fixes:
- none

Suggested next action:
- codex-implement
```

UNIT Task 출력 예:

```text
Execution mode:
- unit

Current unit:
- UNIT-02: 실행 전 gate를 구현한다.

Completed units:
- 1

Pending units:
- 3

Suggested next action:
- codex-implement-unit
```

상태 확인 명령은 repository 파일을 수정하지 않는다.

---

### 11. 한글 Agent workflow 사용 가이드

다음 내용을 포함하는 한글 사용 가이드를 작성한다.

권장 경로:

```text
docs/agent/usage-guide.md
```

포함 내용:

- 전체 workflow 개요
- 작업 branch 생성 방법
- `new_agent_task.sh` 사용법
- Task 작성 방법
- 일반 모드와 UNIT 모드의 차이
- 실행 모드 선택 기준
- prompt-only 방식
- Agent 직접 실행 방식
- Antigravity Review 실행 방법
- Approved Fixes 작성 및 Codex Fix 실행 방법
- status 확인 방법
- 실행 로그 확인 방법
- timeout 및 실패 후 재실행 방법
- PR 전 확인 사항
- 사람이 직접 수행해야 하는 고위험 작업
- 일반적인 오류와 해결 방법
- 처음부터 PR까지 복사 가능한 명령 예시

문서만 읽고 처음부터 workflow를 수행할 수 있는 수준으로 작성한다.

---

### 12. 공통 Task 작성 가이드

다음 문서를 추가한다.

```text
docs/agent/task-authoring-guide.md
```

Task마다 반복하지 않아도 되는 공통 규칙을 정리한다.

공통 규칙 예:

- Production-impacting command는 사람이 수행한다.
- Secret, credential 및 kubeconfig를 수정하지 않는다.
- Agent는 `git push`와 merge를 실행하지 않는다.
- 실행하지 않은 검증을 성공으로 기록하지 않는다.
- 운영 로그 없이 production verification 완료를 주장하지 않는다.
- Review output은 Approved Fixes 승인 전 수정 근거로 사용하지 않는다.
- Verification에는 실제 실행한 command와 결과만 기록한다.
- 현재 Task 범위를 자동으로 확장하지 않는다.
- 사람이 수행할 작업을 별도로 기록한다.

각 Task에는 작업별 내용만 작성한다.

```text
Goal
Scope
Do not change
Expected files
DB changes
API changes
Test commands
Acceptance criteria
Notes
Implementation Units
```

`Implementation Units`는 신규 템플릿에 항상 존재하지만 기본값은 `없음`이며, 실제 UNIT 모드를 사용할 때만 목록으로 교체한다.

공통 가이드에 없는 반복 규칙을 발견하면 다음 기준으로 처리한다.

1. 현재 Task에 필요한 제약을 우선 적용한다.
2. 여러 Task에 공통으로 적용되는지 판단한다.
3. 공통화 가치가 있으면 가이드 갱신 후보로 분류한다.
4. 현재 범위에 포함되면 가이드를 갱신한다.
5. 범위 밖이면 후속 작업 후보로 기록한다.
6. Agent가 임의로 공통 규칙을 확대하지 않는다.

---

### 13. pytest 도입

기존 `unittest.TestCase` 테스트를 유지한다.

pytest는 다음 목적으로 추가한다.

- 기존 테스트의 공통 실행기
- Task parser 테스트
- 일반 모드와 UNIT 모드 판정 테스트
- 실행 전 gate 테스트
- Agent runner 테스트
- timeout 및 비정상 종료 테스트
- status 출력 테스트

pytest는 개발 의존성으로 추가한다.

현재 dependency 관리 구조를 조사한 뒤 다음 중 적절한 위치를 사용한다.

```text
requirements-dev.txt
pyproject.toml의 개발 dependency
기존 개발 전용 dependency 파일
```

pytest가 운영 application image에 불필요하게 포함되지 않도록 Docker build와 dependency 설치 구조를 확인한다.

기존 테스트는 다음 명령으로 실행할 수 있어야 한다.

```bash
python -m pytest
```

기존 unittest 실행 방식도 유지한다.

```bash
python -m unittest discover -s tests
```

자동 테스트에서 실제 Codex와 Antigravity를 호출하지 않는다.

mock subprocess 또는 임시 가짜 executable을 사용해 runner 동작을 검증한다.

---

### 14. 구현 구조

복잡한 Markdown parsing과 상태 판정을 Shell 정규식에 모두 작성하지 않는다.

권장 구조:

```text
scripts/
├── new_agent_task.sh
├── agent_next_step.sh
├── agent_run.sh
└── agent_workflow/
    ├── __init__.py
    ├── task_parser.py
    ├── state.py
    ├── gates.py
    ├── prompt_builder.py
    ├── runner.py
    └── cli.py
```

실제 파일 수와 구조는 저장소 조사 결과에 따라 조정한다.

원칙:

- Shell script는 entrypoint와 최소한의 환경 확인을 담당한다.
- Parsing, 상태 판정 및 runner는 테스트 가능한 Python 코드로 작성한다.
- subprocess는 가능한 한 인자 배열로 실행한다.
- 무분별하게 `shell=True`를 사용하지 않는다.
- Import 시 Git command, 파일 쓰기, network 접근 또는 Agent 실행이 발생하지 않는다.
- 외부 orchestration framework를 도입하지 않는다.
- 역할이 작은 파일을 의미 없이 과도하게 분리하지 않는다.

---

## Do not change

- NewsLab application 기능
- FastAPI endpoint
- Request 및 response schema
- DB schema
- DB migration
- Supabase 데이터
- K3s manifest
- Daily topic pipeline
- RSS Collector
- Raw extraction
- Topic clustering 및 summary 동작
- Secret
- `.env`
- kubeconfig
- credential 및 token
- Production 배포 workflow
- 기존 application runtime dependency
- 기존 unittest 테스트의 일괄 pytest 변환
- 기존 prompt-only workflow 제거
- 기존 `docs/prompts/*` 호환 문서 삭제
- 기존 Task 문서 일괄 변환
- Git commit 자동 실행
- `git push` 자동 실행
- PR 생성 및 merge 자동 실행
- Kubernetes command 자동 실행
- DB migration 및 Supabase SQL 자동 실행
- Production curl 자동 실행

다음 기능은 이번 범위에서 제외한다.

- Task Goal과 Scope의 자동 UNIT 분할
- 여러 UNIT의 자동 연속 실행
- 모든 UNIT별 Verification 강제
- 복잡한 PR readiness 상태 머신
- Agent 내부 작업 단계에 대한 실시간 개입
- LangChain, LangGraph 또는 별도 Agent orchestration framework

---

## Expected files

실제 저장소 조사 결과에 따라 조정할 수 있다.

예상 수정 파일:

```text
scripts/new_agent_task.sh
scripts/agent_next_step.sh
AGENTS.md
docs/agent/backend-workflow.md
docs/agent/codex-instructions.md
docs/agent/verification-gates.md
docs/agent/forbidden-commands.md
.gitignore
```

예상 추가 파일:

```text
scripts/agent_run.sh
scripts/agent_workflow/__init__.py
scripts/agent_workflow/task_parser.py
scripts/agent_workflow/state.py
scripts/agent_workflow/gates.py
scripts/agent_workflow/prompt_builder.py
scripts/agent_workflow/runner.py
scripts/agent_workflow/cli.py
docs/agent/usage-guide.md
docs/agent/task-authoring-guide.md
requirements-dev.txt
pytest.ini
```

예상 테스트 파일:

```text
tests/test_agent_task_parser.py
tests/test_agent_workflow_state.py
tests/test_agent_workflow_gates.py
tests/test_agent_workflow_runner.py
tests/test_agent_workflow_cli.py
```

현재 저장소 convention에 더 적합한 경로 또는 파일 구성이 있으면 이유를 Verification이나 Devlog에 기록하고 조정할 수 있다.

---

## DB changes

없음.

- 신규 table 없음
- 기존 table 변경 없음
- Migration 없음
- Supabase SQL 없음
- Production DB 접근 없음

---

## API changes

없음.

- FastAPI endpoint 변경 없음
- Request schema 변경 없음
- Response schema 변경 없음
- Frontend API 계약 변경 없음

이번 작업은 로컬 개발 workflow와 Agent 실행 도구에만 영향을 준다.

---

## Test commands

실제 dependency와 파일 구조를 조사한 뒤 필요한 명령을 조정한다.

### 신규 하네스 테스트

```bash
python -m pytest \
  tests/test_agent_task_parser.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

### 전체 pytest

```bash
python -m pytest
```

### 기존 unittest 호환

```bash
python -m unittest discover -s tests
```

### Python 문법 및 import 검증

```bash
python -m compileall app scripts tests
python -c "import scripts.agent_workflow"
```

Import 시 다음 동작이 발생하지 않아야 한다.

- Git command 실행
- 파일 쓰기
- 외부 network 접근
- Codex 실행
- Antigravity 실행

### Shell 문법 검증

```bash
bash -n scripts/new_agent_task.sh
bash -n scripts/agent_next_step.sh
bash -n scripts/agent_run.sh
```

추가 Shell script가 있다면 함께 검사한다.

### Diff 검증

```bash
git diff --check
git diff --stat
git status --short --branch
```

### 변경 금지 영역 확인

```bash
git diff -- \
  app \
  db \
  k8s
```

실제 migration 또는 manifest 경로가 다르면 해당 경로를 사용한다.

### 주요 시나리오

자동 테스트 또는 임시 fixture repository에서 다음을 검증한다.

```text
main에서 codex-implement 차단
master에서 codex-fix 차단
기존 Task에서 codex-implement 허용
Implementation Units가 없음인 Task에서 일반 모드 허용
Implementation Units가 없음인 Task에서 UNIT 모드 차단
UNIT Task에서 첫 번째 미완료 UNIT 선택
UNIT Task에서 일반 모드 실행 시 경고 또는 명시적 확인
없음과 UNIT checklist가 동시에 있으면 차단
Task 파일이 없으면 차단
Approved Fixes가 없으면 codex-fix 차단
가짜 Codex executable 정상 종료 처리
가짜 Codex executable 비정상 종료 처리
가짜 Antigravity executable 실행 처리
timeout 처리
stdout, stderr 및 result 저장
status 명령이 파일을 수정하지 않음
```

실제 외부 Agent CLI는 자동 테스트에서 호출하지 않는다.

---

## Acceptance criteria

### 두 가지 실행 모드

- 일반 Task를 전체 범위로 Codex에 실행할 수 있다.
- UNIT Task의 첫 번째 미완료 UNIT만 Codex에 실행할 수 있다.
- 일반 모드와 UNIT 모드가 동일한 Task 및 workflow 문서 체계를 사용한다.
- 모든 Task에 UNIT 작성을 강제하지 않는다.
- 기본적인 빠른 개발 흐름은 일반 모드로 유지된다.

### 신규 Implementation Units 형식

- 58차 완료 후 생성되는 신규 Task에 `Implementation Units` section이 포함된다.
- 기본값은 `없음`이다.
- `없음`이면 일반 모드로 판단한다.
- `없음`을 UNIT checklist로 교체하면 UNIT 모드를 사용할 수 있다.
- `없음`과 UNIT checklist가 함께 있으면 명확한 한글 오류를 출력한다.
- 기존 Task에 해당 section이 없어도 일반 모드와 호환된다.
- 58차 이전 Task를 일괄 수정하지 않는다.
- Task를 자동으로 UNIT으로 분해하지 않는다.

### Agent 직접 실행

- 명령 하나로 Codex 일반 구현을 실행할 수 있다.
- 명령 하나로 Codex 작업 단위 구현을 실행할 수 있다.
- 명령 하나로 Antigravity Review를 실행할 수 있다.
- 명령 하나로 Approved Fixes 기반 Codex 수정을 실행할 수 있다.
- 기존 prompt-only 방식도 계속 사용할 수 있다.
- 실행 전에 대상 Agent, branch, Task, mode 및 UNIT을 확인할 수 있다.

### 안전 gate

- `main`과 `master`에서 구현 및 Fix 실행을 차단한다.
- Task 문서가 없으면 실행을 차단한다.
- Approved Fixes가 없으면 Fix 실행을 차단한다.
- 일반 Task에서 UNIT 모드를 요청하면 올바른 사용법을 안내한다.
- Agent CLI를 찾을 수 없으면 확인 방법을 한글로 안내한다.
- runner가 Production-impacting command를 직접 실행하지 않는다.

### 실행 기록

- 사용한 prompt를 저장한다.
- stdout과 stderr를 저장한다.
- 종료 코드와 실행 시간을 저장한다.
- timeout 여부를 저장한다.
- 비정상 종료를 성공으로 처리하지 않는다.
- Agent 실행 성공만으로 Task나 Verification 완료를 자동 주장하지 않는다.

### 상태 확인

- 현재 branch와 Task를 출력한다.
- 일반 또는 UNIT 모드를 출력한다.
- UNIT 모드에서는 현재 미완료 UNIT을 출력한다.
- Review와 Approved Fixes 상태를 가능한 범위에서 출력한다.
- 다음 권장 action을 출력한다.
- status 명령은 파일을 수정하지 않는다.

### 한글 가이드

- 처음 사용하는 사람이 문서만 보고 workflow를 진행할 수 있다.
- 일반 모드와 UNIT 모드의 선택 기준이 설명되어 있다.
- prompt-only 방식과 직접 실행 방식이 설명되어 있다.
- 각 script와 workflow 문서의 역할이 설명되어 있다.
- 사람이 수행해야 하는 고위험 작업이 구분되어 있다.
- 일반적인 오류와 복구 방법이 설명되어 있다.
- Task에서 반복 작성하지 않아도 되는 공통 규칙이 정리되어 있다.

### pytest

- pytest가 개발 의존성으로 추가된다.
- 기존 unittest 테스트를 pytest로 실행할 수 있다.
- 기존 unittest 실행 방식도 유지된다.
- 신규 하네스 핵심 기능에 pytest 테스트가 존재한다.
- 실제 외부 Agent는 mock 또는 가짜 executable로 테스트한다.
- pytest가 운영 image에 불필요하게 포함되지 않는다.

### 회귀

- Backend application 동작에 변화가 없다.
- DB와 API 변경이 없다.
- K3s 및 Daily pipeline 변경이 없다.
- 기존 prompt-only workflow가 유지된다.
- 기존 Task 문서를 강제로 변환하지 않는다.
- 전체 테스트가 통과한다.

---

## Checklist

- [x] Task parser와 workflow 상태 판정을 구현하고 검증한다.
- [x] 실행 gate와 prompt builder를 구현하고 검증한다.
- [x] Agent runner와 CLI entrypoint를 구현하고 검증한다.
- [x] 기존 prompt-only script와 신규 Task template을 갱신하고 검증한다.
- [x] 한글 가이드와 pytest 개발 환경을 추가하고 전체 검증을 완료한다.

---

## Notes

### 기본 개발 방향

NewsLab은 빠르게 전체 흐름을 구현한 뒤 실제 결과를 확인하고 내부 구조를 개선하는 탑다운 방식을 기본으로 한다.

```text
전체 기능을 빠르게 연결
→ 실제 실행 결과 확인
→ 병목과 구조 문제 확인
→ 내부 구현과 테스트 개선
```

하네스는 이 방식을 방해하지 않아야 한다.

일반 모드는 빠른 전체 구현에 사용한다.

```bash
scripts/agent_run.sh codex-implement
```

UNIT 모드는 다음과 같은 작업에 선택적으로 사용한다.

- 작업 범위가 크다.
- 여러 단계에 선후 관계가 있다.
- 중간 검증이 필요하다.
- DB, 배포, 인증 등 위험도가 높다.
- Agent의 범위 초과 가능성이 크다.
- 한 번에 수정하면 실패 원인을 찾기 어렵다.

```bash
scripts/agent_run.sh codex-implement-unit
```

어느 모드를 사용할지 애매하면 일반 모드로 전체 흐름을 먼저 구현하고, 확인된 문제를 후속 Task에서 UNIT 모드로 개선한다.

### 58차 Task의 형식

현재 하네스에는 아직 `Implementation Units`를 해석하는 기능이 없다.

따라서 이 58차 Task에는 `Implementation Units` section을 추가하지 않는다.

58차 구현 결과로 `new_agent_task.sh`, Task parser 및 실행 하네스가 해당 section을 지원하게 만든다.

58차 이후 생성하는 신규 Task부터 다음 형식을 사용한다.

```markdown
## Implementation Units

없음
```

### 자동화의 한계

Agent runner가 Codex 또는 Antigravity를 직접 실행해도 Agent 내부 판단을 실시간으로 통제하는 것은 아니다.

하네스가 통제하는 범위는 다음과 같다.

```text
Agent 실행 전 gate
→ Agent subprocess 실행
→ 종료 코드와 로그 수집
→ 실행 후 상태 안내
```

코드 설계 품질, Task 의도 충족 여부 및 Review 의견의 타당성은 사람이 최종 판단한다.

### 사람이 수행하는 작업

다음 작업은 자동화하지 않는다.

- Task 요구사항 승인
- Agent 구현 결과 검토
- Antigravity Review 결과 판단
- Approved Fixes 승인
- Git commit
- Git push
- PR 생성
- PR merge
- Docker image 배포
- Kubernetes 반영
- DB migration
- Production verification

이번 Task에는 Production 배포나 K3s 검증이 필요하지 않다.
