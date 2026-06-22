# 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## 작업 내용

- 기존 prompt-only workflow를 유지하면서 Codex와 Gemini/Antigravity CLI를 선택적으로 직접 실행하는 로컬 Agent 실행 하네스를 추가했다.
- Task 전체를 대상으로 하는 일반 모드와 첫 번째 미완료 `Implementation Units` 항목만 대상으로 하는 UNIT 모드를 지원한다.
- 실행 전 workflow gate, preview, 사용자 확인, timeout, 종료 코드 보존 및 실행 로그 저장 기능을 추가했다.
- 현재 Task와 Verification, Review, Approved Fixes 및 다음 권장 action을 읽기 전용으로 확인하는 status 기능을 추가했다.
- Agent workflow 사용법, Task 작성 방식, Python 한글 docstring 정책과 Verification 상태 관리 방식을 문서화했다.
- 기존 `unittest` 호환을 유지하면서 pytest를 개발 의존성과 공통 테스트 실행기로 추가했다.

## 주요 변경 사항

- `scripts/agent_run.sh`와 `scripts/agent_workflow/` Python package를 추가했다.
  - Task Markdown과 `Implementation Units` parser
  - branch별 workflow 상태 판정
  - 구현, UNIT 구현, Review, 승인 Fix action별 gate
  - action별 prompt 생성
  - Codex 및 Gemini/Antigravity command adapter
  - timeout 시 process group 종료
  - prompt, stdout, stderr 및 result JSON 저장
- 직접 실행 결과는 `.agent-runs/<safe-branch>/<timestamp>-<action>/`에 저장하고 Git에서 제외했다.
- `scripts/agent_next_step.sh`에 `status`, `codex-implement-unit`, `codex-fix`를 추가하고 기존 `codex-apply-fixes` 호환을 유지했다.
- `scripts/new_agent_task.sh`가 신규 Task에 `Implementation Units` 기본값 `없음`, 현재 Task pointer 및 `Verification Status: pending`을 생성하도록 변경했다.
- Verification 현재 상태는 `## Verification Status` section의 `passed`, `failed`, `pending`만 해석한다.
  - 상태 section이 없는 기존 문서는 `present`
  - 문서가 없으면 `missing`
  - 과거 실패 기록과 fenced code 예시는 현재 상태에 영향을 주지 않음
- Verification `passed`, Review `present`, Approved Fixes `applied` 상태에서는 다음 action으로 `pr-draft`를 제안한다.
- Review가 존재하는 Verification `failed` 또는 `pending` 상태에서는 Review를 반복 권장하지 않고 `resolve-verification` 안내를 출력하며 Review gate를 차단한다.
- `docs/tasks/main.md`는 실제 Markdown link target을 정규화해 현재 Task와 정확히 일치할 때만 pointer로 인정한다.
- 환경변수로 지정한 Agent binary는 실행 가능한 파일 또는 PATH command인지 gate에서 검증한다.
- repository 외부 로그 경로는 예외 없이 정규화된 절대 경로로 result JSON에 저장한다.
- Antigravity Review의 로컬 home 경로 link를 저장소 상대 Markdown link로 정규화했다.
- 한글 workflow 사용 가이드와 Task 작성 가이드를 추가하고 기존 Agent workflow 문서를 갱신했다.
- 승인된 FIX-01에 따라 신규 Python workflow 모듈과 테스트에 역할, 예외, 부수 효과 및 검증 목적을 설명하는 한글 docstring을 추가했다.
- 승인된 FIX-02와 FIX-03에 따라 실제 pytest 결과와 명시적 Verification 상태 판정 방식을 반영했다.
- `requirements-dev.txt`에 pytest를 추가했으며 production `requirements.txt`와 Dockerfile은 변경하지 않았다.

## 추가/변경된 API

없음.

- FastAPI endpoint 변경 없음
- Request/response schema 변경 없음
- Frontend API 계약 변경 없음
- 로컬 Agent workflow script와 문서에만 영향을 준다.

## DB 변경 사항

없음.

- DB schema 및 migration 변경 없음
- Supabase SQL 실행 없음
- Production DB 접근 없음

## README 영향

README 변경은 필요하지 않다고 판단했다.

- 일반 사용자용 application 사용법이 아니라 repository 내부 Agent 개발 workflow 변경이다.
- 상세 사용법과 공통 정책은 `docs/agent/usage-guide.md`, `docs/agent/task-authoring-guide.md` 및 기존 backend workflow 문서에 기록했다.

## 테스트

- 실행 환경
  - Python 3.11.7
  - pytest 9.1.1
- `python -m pytest tests/test_agent_workflow_state.py -v`
  - 8 passed, 3 subtests passed
- `python -m pytest`
  - 187 passed in 4.33s
- `python -m unittest discover -s tests`
  - Ran 187 tests in 3.803s
  - OK
  - 중간 argparse `usage:` 및 `error:` 문구는 잘못된 입력을 검증하는 기존 테스트의 예상 stderr다.
- `python -m pip install -r requirements-dev.txt`
  - 모든 dependency가 이미 설치되어 있음을 확인
  - pyenv shim rehash 권한 문제로 command 자체는 exit 1
  - 이후 같은 Python 환경의 전체 pytest와 unittest는 통과
- `python -m compileall app scripts tests`
  - 성공
- `python -c "import scripts.agent_workflow"`
  - 성공
  - import 시 Git command, 파일 쓰기, network 접근 또는 Agent 실행 없음
- `bash -n scripts/new_agent_task.sh`
- `bash -n scripts/agent_next_step.sh`
- `bash -n scripts/agent_run.sh`
  - Shell syntax error 없음
- `git diff --check`
  - whitespace error 없음
- `git diff -- app db k8s`
  - 출력 없음

## 확인 결과

- 일반 Task와 `Implementation Units: 없음` Task는 general mode로 처리한다.
- UNIT Task는 첫 번째 미완료 UNIT만 선택하며 혼합 형식, 잘못된 형식, 중복 identifier와 비정상 완료 순서를 차단한다.
- `main`과 `master`, Task 또는 Approved Fixes 누락, 명시적 Verification 실패 등 안전 조건을 gate에서 차단한다.
- Verification이 failed/pending이면 먼저 검증 문제를 해결하도록 안내하며 현재 상태에서 통과할 수 없는 Review action을 제안하지 않는다.
- `main.md` 일반 본문과 fenced code의 Task 파일명은 pointer로 오인하지 않는다.
- 잘못된 Agent binary 환경변수와 repository 외부 로그 경로를 안전하게 처리한다.
- preview와 status는 Agent를 실행하거나 `.agent-runs` 로그를 생성하지 않는다.
- 가짜 executable을 사용해 정상 종료, 비정상 종료, timeout 124, stdout/stderr 및 result JSON 보존을 검증했다.
- 현재 status는 다음과 같이 확인됐다.
  - Verification: `passed`
  - Review: `present`
  - Approved fixes: `applied`
  - Suggested next action: `pr-draft`
- 기존 prompt-only workflow와 `codex-apply-fixes` command 호환을 유지한다.
- Application, API, DB, K3s manifest 및 daily pipeline 변경은 없다.

## 비고

- CodeRabbit에서 보고된 100 tests / 12 errors는 Python 3.11.7, pytest 9.1.1 환경에서 재현되지 않았다.
- 실제 Codex, Gemini 또는 Antigravity CLI는 자동 테스트에서 실행하지 않았다. 테스트는 mock과 임시 가짜 executable을 사용했다.
- 현재 환경에서 별도 Antigravity CLI는 발견되지 않았다. 검증된 stdin 기반 wrapper를 사용할 경우 `AGENT_ANTIGRAVITY_BIN`에 지정할 수 있으며, 그 외에는 Gemini CLI 또는 prompt-only 방식을 사용한다.
- Production deployment, K3s rollout 및 production verification 대상이 아닌 로컬 workflow 변경이다.
- Git commit, push, merge, PR 생성과 merge는 수행하지 않았다.
- Secret, `.env`, kubeconfig, credential 및 token은 수정하지 않았다.
