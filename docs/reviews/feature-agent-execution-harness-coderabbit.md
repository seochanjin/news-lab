# CodeRabbit Review: 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## Review Summary

CodeRabbit Review에서 테스트 증적의 환경 차이, workflow 상태 전이, Task 포인터 검증 및 실행 경로 처리와 관련된 문제들이 확인되었다.

Review 결과는 다음과 같이 분류한다.

- PR 전 확인 및 수정이 필요한 항목: 3건
- 방어적 안정성 개선 항목: 2건
- 문서 링크 형식 개선 항목: 1건

CodeRabbit이 제안한 내용을 그대로 적용하지 않고, NewsLab 저장소의 workflow 정책과 실제 로컬 검증 결과를 기준으로 수정 범위를 승인한다.

## Problems Found

### CR-01. PR 문서의 테스트 결과와 CodeRabbit 실행 결과 불일치

`docs/pr/feature-agent-execution-harness.md`에는 다음 결과가 기록되어 있다.

```text
python -m pytest
→ 177 passed

python -m unittest discover -s tests
→ Ran 177 tests
→ OK
```

하지만 CodeRabbit 환경에서는 100개 테스트가 수집되고 12개 오류가 발생했다고 보고했다.

현재 로컬 `.venv`에서는 다음 결과가 실제로 확인되었다.

```text
pytest 9.1.1
177 passed

Ran 177 tests
OK
```

따라서 문서 내용이 즉시 허위라고 단정할 수는 없지만, 실행 환경 또는 의존성 설치 상태에 따른 차이가 존재할 가능성이 있다.

PR 병합 전에 깨끗한 개발 환경에서 `requirements-dev.txt`를 설치하고 전체 테스트를 다시 실행하여 다음을 확인해야 한다.

- 테스트 수집 수가 177건인지
- Import error 또는 dependency error가 발생하지 않는지
- `requirements-dev.txt`가 실행에 필요한 운영 의존성도 포함하는지
- CodeRabbit 오류가 코드 결함인지 Review 환경 제약인지

PR 문서에는 테스트 실행 환경과 명령을 명확히 기록해야 한다.

### CR-02. 실행할 수 없는 다음 action을 추천할 수 있음

`scripts/agent_workflow/state.py`의 다음 action 판정은 Verification이 실패한 경우에도 기본 분기로 `antigravity-review`를 반환할 수 있다.

하지만 Review gate는 Verification 실패 상태에서 `antigravity-review`를 차단한다.

따라서 status가 다음처럼 모순된 안내를 제공할 수 있다.

```text
Verification:
- failed

Suggested next action:
- antigravity-review
```

사용자에게 실행을 권장한 명령이 실제 gate에서 차단되므로 상태 UX와 gate 계약이 일치하지 않는다.

### CR-03. `docs/tasks/main.md` 포인터 검사가 지나치게 느슨함

현재 구현은 `docs/tasks/main.md` 본문 어디엔가 현재 Task 파일명이 포함되어 있는지만 검사한다.

따라서 다음과 같은 무관한 문장도 검사를 통과할 수 있다.

```text
이전 Task는 feature-agent-execution-harness.md였다.
```

`docs/tasks/main.md`가 현재 Task를 실제 Markdown link 대상으로 가리키는지 검증해야 한다.

### CR-04. 환경변수로 지정한 Agent 실행 파일 검증 부족

다음 환경변수가 설정되어 있으면 현재 구현은 경로의 존재 여부와 실행 가능 여부를 충분히 검사하지 않고 통과시킬 수 있다.

```text
AGENT_CODEX_BIN
AGENT_ANTIGRAVITY_BIN
```

잘못된 경로가 설정되면 gate는 통과하고 실제 subprocess 실행 단계에서 실패한다.

실행 전 gate에서 다음을 확인해야 한다.

- 대상 경로 또는 command가 존재함
- 디렉터리가 아닌 파일 또는 실행 가능한 command임
- 현재 운영체제에서 실행 가능함

### CR-05. 저장소 외부 로그 경로에서 `relative_to()` 예외 가능

`scripts/agent_workflow/runner.py`는 결과에 로그 경로를 기록할 때 다음 전제를 가진다.

```python
log_dir.resolve().relative_to(state.repo.resolve())
```

사용자가 저장소 밖의 custom log directory를 지정하면 `ValueError`가 발생할 수 있다.

Agent 실행과 로그 저장은 이미 완료됐더라도 결과 생성 과정에서 전체 run이 실패할 수 있다.

### CR-06. Antigravity Review 문서 링크가 로컬 환경에 종속됨

Review 문서에서 다음과 같은 경로가 사용되고 있다.

```text
~/news-lab/scripts/agent_run.sh
```

CodeRabbit은 이를 `file://` 절대 URL로 변경하도록 제안했다.

하지만 `file://` 절대 경로 역시 작성자의 로컬 환경에 종속되고 GitHub 및 다른 개발자 환경에서 사용할 수 없다.

저장소 기준 상대 Markdown link를 사용해야 한다.

예:

```markdown
[agent_run.sh](../../scripts/agent_run.sh)
[cli.py](../../scripts/agent_workflow/cli.py)
```

## Required Fixes Before PR

### FIX-04. 테스트 결과 불일치 재검증 및 문서 명확화

- 깨끗한 가상환경 또는 현재 가상환경에서 개발 의존성을 다시 확인한다.
- `python -m pip install -r requirements-dev.txt` 이후 전체 테스트를 실행한다.
- pytest 및 unittest의 실제 수집 수와 결과를 기록한다.
- 실패 시 오류 12건의 원인을 확인하고 코드 또는 dependency 파일을 수정한다.
- 통과 시 PR 문서에 로컬 실행 환경과 실제 명령을 명시한다.
- CodeRabbit 환경의 실패를 확인하지 않고 단순히 무시하거나 PR 문구만 삭제하지 않는다.

### FIX-05. 실패 상태의 다음 action 판정 수정

- Verification이 `failed` 또는 `pending`이면 실행 불가능한 `antigravity-review`를 추천하지 않는다.
- status 전용 안내 상태를 사용하거나 사용자가 먼저 Verification 문제를 해결하도록 명확히 출력한다.
- `suggested_action`과 `validate_action`의 계약이 일치하도록 테스트를 추가한다.

### FIX-06. `docs/tasks/main.md` 포인터 검증 강화

- 파일명 단순 포함 검색을 제거한다.
- Markdown link의 실제 대상 경로를 추출한다.
- 정규화한 경로가 현재 Task 파일과 정확히 일치할 때만 통과한다.
- 무관한 본문에 Task 파일명이 존재하는 경우 차단하는 회귀 테스트를 추가한다.

### FIX-07. 설정된 Agent binary 사전 검증

- `AGENT_CODEX_BIN`과 `AGENT_ANTIGRAVITY_BIN` 값을 gate 단계에서 검증한다.
- 존재하지 않는 경로, 디렉터리 및 실행할 수 없는 파일을 명확한 한글 오류로 차단한다.
- command 이름이 지정된 경우 PATH에서 확인한다.
- 정상 경로와 잘못된 경로에 대한 테스트를 추가한다.

### FIX-08. 저장소 외부 로그 경로 처리

- `log_directory`가 저장소 내부면 저장소 상대 경로를 기록한다.
- 저장소 외부면 예외를 발생시키지 않고 정규화된 절대 경로를 기록한다.
- 경로 표시 실패 때문에 이미 완료된 Agent 실행 결과가 유실되지 않도록 한다.
- 저장소 내부와 외부 경로 테스트를 추가한다.

### FIX-09. 문서 링크를 저장소 상대 경로로 정규화

- `~/news-lab/...` 형식의 로컬 경로를 저장소 상대 Markdown link로 변경한다.
- `file://` 로컬 절대 URL은 사용하지 않는다.
- Review 문서의 의미나 실행 증적은 변경하지 않는다.

## Optional Improvements

### CodeRabbit의 `file://` 변환 제안

제안된 구현 방식은 적용하지 않는다.

`file://` URL은 특정 사용자의 로컬 절대 경로에 종속되므로 GitHub Review 문서에 적합하지 않다.

대신 저장소 상대 Markdown link로 변경한다.

### pytest 자동 설치

하네스가 자동으로 `pip install`을 수행하는 기능은 이번 수정에 포함하지 않는다.

환경을 자동 변경하지 않고 다음 설치 명령을 문서로 안내한다.

```bash
python -m pip install -r requirements-dev.txt
```

## Suggested Test Commands

### 개발 의존성 확인

```bash
python -m pip install -r requirements-dev.txt
python -m pytest --version
```

### Agent workflow 핵심 테스트

```bash
python -m pytest \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

### 전체 테스트

```bash
python -m pytest
python -m unittest discover -s tests
```

### Python 및 Shell 검증

```bash
python -m compileall app scripts tests
python -c "import scripts.agent_workflow"

bash -n scripts/new_agent_task.sh
bash -n scripts/agent_next_step.sh
bash -n scripts/agent_run.sh
```

### 상태와 포인터 검증

```bash
scripts/agent_next_step.sh status
git diff --check
git diff --stat
git status --short --branch
```

### 변경 금지 영역

```bash
git diff -- app db k8s
```

## Risk Notes

- 상태 판정과 gate가 불일치하면 사용자가 실행할 수 없는 action을 반복적으로 안내받을 수 있다.
- `main.md` 포인터 검증이 느슨하면 잘못된 Task를 기준으로 Agent가 실행될 수 있다.
- 설정된 binary 경로를 검증하지 않으면 preflight gate의 신뢰성이 떨어진다.
- 외부 로그 경로 처리 오류는 Agent 실행 이후 결과 기록 단계에서 실패를 유발할 수 있다.
- 테스트 결과 차이를 해소하지 않고 병합하면 PR 검증 증적의 신뢰성이 훼손될 수 있다.
