# Verification: 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## Verification Status

passed

## Verification Scope

- Task parser, 일반/UNIT mode 판정과 status
- 실행 전 gate와 prompt 생성
- 가짜 Agent executable 기반 runner 정상·비정상·timeout 처리
- prompt-only 및 직접 실행 preview
- 기존 unittest 회귀
- Shell/Python 정적 검증과 변경 금지 영역 확인

## Commands Run

Command:
`python -m pip install -r requirements-dev.txt`

Result:
- `requirements.txt`와 `requirements-dev.txt`의 모든 package가 현재 Python 환경에 이미 설치되어 있었다.
- 마지막 pyenv rehash 단계에서 `~/.pyenv/shims` 쓰기 권한이 없어 exit code 1로 종료됐다.
- 신규 package 설치나 dependency 변경은 발생하지 않았다.

Status: failed

Notes:
의존성 누락 실패가 아니라 pyenv shim 권한 문제다. 이후 같은 Python executable로 pytest와 unittest를 실행해 전체 통과를 확인했다.

Command:
`python --version && python -m pytest --version && python -m pytest`

Result:
- Python 3.11.7
- pytest 9.1.1
- collected 177 items
- 177 passed in 3.88s

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
- Ran 177 tests in 3.624s
- OK

Status: passed

Notes:
중간 argparse `usage:` 및 `error:` 출력은 invalid input을 검증하는 기존 test의 예상 stderr다. CodeRabbit의 100 tests / 12 errors는 현재 환경에서 재현되지 않았다.

Command:
`python -m pytest tests/test_agent_workflow_state.py tests/test_agent_workflow_gates.py -v`

Result:
- 첫 실행: status 안내 문구 expectation 1건 실패
- 안내 문구를 실행 가능한 표현으로 맞춘 뒤 17 passed, 3 subtests passed in 1.32s

Status: passed

Notes:
Review가 존재하는 failed/pending 상태는 `resolve-verification`을 반환하고 Review gate를 통과하지 않는다. passed/applied 상태는 기존 `pr-draft` 계약을 유지한다.

Command:
`python -m pytest tests/test_agent_workflow_state.py -v`

Result:
`13 passed, 3 subtests passed in 1.06s`

Status: passed

Notes:
정상 Markdown link target은 허용하고 잘못된 link, 일반 본문 파일명과 fenced code 예시는 `docs/tasks/main.md` pointer로 인정하지 않음을 확인했다.

Command:
`python -m pytest tests/test_agent_workflow_gates.py -v`

Result:
`10 passed, 2 subtests passed in 0.48s`

Status: passed

Notes:
환경변수의 정상 executable과 PATH command는 허용하고 누락 경로와 디렉터리는 값 노출 없이 GateError로 차단함을 확인했다.

Command:
`python -m pytest tests/test_agent_workflow_runner.py -v`

Result:
`4 passed in 2.13s`

Status: passed

Notes:
repository 내부 로그의 기존 동작과 외부 로그 경로의 절대 경로 직렬화, 정상·비정상 종료 및 timeout 로그 보존을 확인했다.

Command:
`rg -n '~/?news-lab|file://|/Users/[^ )]+/news-lab' docs/reviews/feature-agent-execution-harness-antigravity.md || true`

Result:
출력 없음.

Status: passed

Notes:
Antigravity Review의 로컬 경로 link를 저장소 상대 Markdown link로 변경했고 Review 내용과 판정은 유지했다.

Command:
`command -v codex`, `command -v antigravity`, `command -v gemini`

Result:
- Codex: `/opt/homebrew/bin/codex`
- Antigravity: 찾지 못함
- Gemini: `/opt/homebrew/bin/gemini`

Status: passed

Notes:
실제 Agent는 실행하지 않았다.

Command:
`codex --help`, `codex exec --help`, `gemini --help`

Result:
- Codex 비대화형 입력: `codex exec -C <repo> -`
- Gemini 비대화형 prompt와 승인 mode: `--prompt`, `--approval-mode auto_edit`

Status: passed

Command:
`python -m pytest tests/test_agent_task_parser.py tests/test_agent_workflow_state.py -v`

Result:
`No module named pytest`

Status: superseded

Notes:
당시 system Python에 pytest가 설치되어 있지 않았다. 이후 FIX-02 재검증에서 pytest 9.1.1과 전체 test 통과를 확인했다.

Command:
`.venv/bin/python -m pytest --version`

Result:
`No module named pytest`

Status: superseded

Notes:
당시 기존 `.venv`에도 pytest가 설치되어 있지 않았다. 현재 재검증은 system Python의 pytest 9.1.1로 완료했다.

Command:
`python -m unittest discover -s tests`

Result:
- 첫 실행: 신규 runner path 처리 3건과 main branch test fixture 1건 실패
- 결함 수정 후 실행: 168 tests passed
- fenced Markdown heading parser 수정 후 실행: 169 tests passed
- 최종 실행: 171 tests passed

Status: passed

Command:
`bash -n scripts/new_agent_task.sh && bash -n scripts/agent_next_step.sh && bash -n scripts/agent_run.sh`

Result:
Shell syntax error 없음.

Status: passed

Command:
`scripts/agent_next_step.sh antigravity-review | rg -n '한글 module|docstring|실제 구현'`

Result:
Antigravity Review prompt에 Python module/class/function/method docstring 존재와 실제 구현·테스트 목적 일치 여부 확인 항목이 포함됨을 확인했다.

Status: passed

Command:
`scripts/agent_run.sh status`

Result:
- Verification: `present`
- Review: `present`
- Approved fixes: `applied`
- Suggested next action: `antigravity-review`

Status: passed

Notes:
과거 pytest 미설치 기록의 `Status: failed`가 현재 상태를 오염시키지 않으며 승인 Fix 적용 완료 상태가 반영된다.

Command:
`git diff --check && git diff --stat && git status --short --branch`

Result:
- whitespace error 없음
- tracked 변경 통계 출력
- 신규 workflow, 문서와 test 파일은 기존과 같이 untracked 상태로 확인

Status: passed

Command:
`git diff -- app db k8s`

Result:
출력 없음.

Status: passed

Command:
`scripts/agent_next_step.sh status`

Result:
FIX-03 문서 기록 완료 후에도 Verification `passed`, Review `present`, Approved fixes `applied`, 다음 action `pr-draft`를 출력했다.

Status: passed

Command:
`git diff --check && git status --short --branch`

Result:
최종 workflow 문서 갱신 후 whitespace error가 없고 현재 branch의 변경 상태를 확인했다.

Status: passed

Command:
`git diff --check && git status --short --branch`

Result:
Verification 최종 갱신 후 whitespace error가 없고 현재 branch의 기존 변경·신규 파일 상태를 다시 확인했다.

Status: passed

Command:
`python -m pytest tests/test_agent_workflow_state.py -v`

Result:
`8 passed, 3 subtests passed in 0.71s`

Status: passed

Notes:
과거 실패 문장, fenced code 예시, `passed`/`failed`/`pending`, 상태 section 없음, 문서 없음과 PR 초안 권장 상태를 검증했다.

Command:
`python -m pytest`

Result:
`177 passed in 3.94s`

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
`Ran 177 tests in 3.595s`, `OK`

Status: passed

Notes:
중간 argparse `usage:` 및 `error:` 출력은 잘못된 입력을 검증하는 기존 test의 예상 stderr다.

Command:
`python -m compileall app scripts tests`

Result:
변경된 상태 parser와 테스트를 포함한 Python compile이 성공했다.

Status: passed

Command:
`bash -n scripts/new_agent_task.sh && bash -n scripts/agent_next_step.sh && bash -n scripts/agent_run.sh`

Result:
신규 Verification template 변경 후에도 Shell syntax error 없음.

Status: passed

Command:
`scripts/agent_next_step.sh status`

Result:
- Verification: `passed`
- Review: `present`
- Approved fixes: `applied`
- Suggested next action: `pr-draft`

Status: passed

Notes:
과거 `Status: failed` 문구가 현재 상태를 오염시키지 않으며 PR 준비 단계를 권장한다.

Command:
`git diff --check && git diff --stat && git status --short --branch`

Result:
- whitespace error 없음
- tracked 변경 통계 출력
- 기존 working tree의 변경·신규 파일 상태 확인

Status: passed

Command:
`git diff -- app db k8s`

Result:
출력 없음.

Status: passed

Command:
`python -m compileall app scripts tests && python -c "import scripts.agent_workflow"`

Result:
compile 및 import 성공. Import 시 Agent 실행이나 파일 쓰기 없음.

Status: passed

Command:
`scripts/agent_next_step.sh status`

Result:
- 첫 실행: fenced code block의 예시 heading을 실제 Implementation Units로 오인해 차단
- parser 수정 후: 현재 branch, general mode, workflow 상태와 권장 action 출력

Status: passed

Command:
`scripts/agent_run.sh codex-implement --preview`

Result:
- 첫 실행: 같은 parser 결함으로 차단
- parser 수정 후: Codex, branch, Task, general mode, 로그 예정 경로, 1200초 timeout과 prompt 출력
- Codex subprocess와 로그 디렉터리는 생성하지 않음

Status: passed

Command:
`scripts/agent_next_step.sh codex-implement-unit`

Result:
현재 Task에는 실제 Implementation Units section이 없으므로 한글 안내와 함께 exit code 2로 차단.

Status: passed

Command:
`git diff --check && git diff --stat && git status --short --branch`

Result:
- whitespace error 없음
- tracked 변경 통계 출력
- 신규 workflow, 문서, test 파일은 untracked 상태로 확인

Status: passed

Command:
`git diff -- app db k8s`

Result:
출력 없음.

Status: passed

Command:
`git diff --name-only --diff-filter=ACM -- '*.py'`

Result:
tracked Python diff는 없었다. 이번 branch의 신규 Python 파일은 untracked 상태이므로 `rg --files scripts/agent_workflow tests`로 대상 12개 파일을 함께 확인했다.

Status: passed

Command:
`rg -n '^(class |def |    def )|^\\s*\"\"\"' scripts/agent_workflow tests/test_agent_*.py`

Result:
Agent workflow 모듈 7개와 테스트 5개의 module, class, function 및 method docstring 위치를 확인했다. 모든 추가 설명은 한글이며 실제 책임, 반환값, 예외 또는 부수 효과와 테스트 목적을 설명한다.

Status: passed

Command:
`grep -n "한글.*docstring\\|module docstring\\|Python 문서화" docs/agent/task-authoring-guide.md docs/agent/codex-instructions.md`

Result:
Task 작성 가이드의 상세 Python 문서화 정책과 Codex 지침의 핵심 규칙 및 링크를 확인했다.

Status: passed

Command:
`scripts/agent_next_step.sh codex-implement | rg -n 'Python 문서화|한글 docstring|task-authoring-guide'`

Result:
codex-implement prompt에 공통 Python 문서화 정책과 한글 docstring 규칙이 포함됨을 확인했다.

Status: passed

Command:
`scripts/agent_next_step.sh codex-fix | rg -n 'Python 문서화|한글 docstring|task-authoring-guide'`

Result:
codex-fix prompt에 공통 Python 문서화 정책과 한글 docstring 규칙이 포함됨을 확인했다.

Status: passed

Command:
`python -m pytest --version`

Result:
`pytest 9.1.1`

Status: passed

Command:
`python -m pytest tests/test_agent_task_parser.py tests/test_agent_workflow_state.py tests/test_agent_workflow_gates.py tests/test_agent_workflow_runner.py tests/test_agent_workflow_cli.py -v`

Result:
`19 passed, 4 subtests passed in 2.95s`

Status: passed

Command:
`python -m pytest`

Result:
`171 passed in 2.80s`

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
`Ran 171 tests in 2.453s`, `OK`

Status: passed

Notes:
중간 argparse `usage:` 및 `error:` 출력은 잘못된 입력을 검증하는 기존 test의 예상 stderr다.

Command:
`python -m compileall app scripts tests && python -c "import scripts.agent_workflow"`

Result:
변경된 Python 파일 compile과 package import가 성공했다.

Status: passed

Command:
`bash -n scripts/new_agent_task.sh && bash -n scripts/agent_next_step.sh && bash -n scripts/agent_run.sh`

Result:
Shell syntax error 없음.

Status: passed

## Results

- 일반 Task와 `없음` Task는 general mode로 처리한다.
- UNIT Task는 첫 미완료 UNIT만 선택하며 혼합 형식, 잘못된 형식, 역순 완료를 차단한다.
- `main`/`master`, Task/Approved Fixes 누락, 명시적 verification 실패를 gate에서 차단한다.
- runner는 prompt, stdout, stderr, result JSON을 저장하고 비정상 exit code와 timeout 124를 보존한다.
- status와 preview는 repository workflow 파일을 수정하거나 Agent를 실행하지 않는다.
- 기존 prompt-only command와 `codex-apply-fixes` 호환 alias를 유지한다.
- pytest는 `requirements-dev.txt`에만 추가했으며 production `requirements.txt`와 Dockerfile은 변경하지 않았다.
- Python workflow 모듈과 테스트에 한글 docstring을 추가하고 향후 구현·Fix·Review prompt에 공통 정책을 연결했다.
- pytest 9.1.1에서 전체 171개 test가 통과해 과거 미설치 상태를 재검증으로 해소했다.
- Verification 현재 상태는 명시적 `Verification Status` section만 사용하며 과거 실패 이력과 예시 문구를 무시한다.
- 전체 회귀 test는 FIX-03 테스트 추가 후 177개가 통과했다.
- FIX-05부터 FIX-09까지의 회귀 테스트 추가 후 전체 pytest 187개와 unittest 187개가 통과했다.
- failed/pending Verification은 Review 재실행 대신 `resolve-verification` 안내를 제공한다.
- `main.md`는 실제 Markdown link target만 현재 Task pointer로 인정한다.
- 환경변수 Agent binary는 존재하고 실행 가능한 파일 또는 PATH command인지 사전 검증한다.
- repository 외부 로그 경로도 절대 경로로 안전하게 result JSON에 저장한다.
- Antigravity Review의 로컬 절대·home 경로 link는 저장소 상대 Markdown link로 정규화됐다.

Command:
`python -m pytest`

Result:
- Python 3.11.7
- pytest 9.1.1
- collected 187 items
- 187 passed in 4.33s

Status: passed

Command:
`python -m unittest discover -s tests`

Result:
- Ran 187 tests in 3.803s
- OK

Status: passed

Notes:
중간 argparse `usage:` 및 `error:` 출력은 invalid input을 검증하는 기존 test의 예상 stderr다.

Command:
`python -m compileall app scripts tests && python -c "import scripts.agent_workflow" && bash -n scripts/new_agent_task.sh && bash -n scripts/agent_next_step.sh && bash -n scripts/agent_run.sh`

Result:
Python compile/import와 세 Shell entrypoint 문법 검증 성공.

Status: passed

Command:
`scripts/agent_next_step.sh status && git diff --check && git diff --stat && git status --short --branch && git diff -- app db k8s`

Result:
- Verification: `passed`
- Review: `present`
- Approved fixes: `applied`
- Suggested next action: `pr-draft`
- whitespace error 없음
- app, db, k8s diff 없음

Status: passed

Command:
`git diff --check && scripts/agent_next_step.sh status && git diff -- app db k8s && git status --short --branch`

Result:
- 최종 문서 갱신 후 whitespace error 없음
- Verification: `passed`
- Review: `present`
- Approved fixes: `applied`
- Suggested next action: `pr-draft`
- app, db, k8s diff 없음
- CodeRabbit review의 기존 user change를 포함한 working tree 상태 확인

Status: passed

## Manual or Production Verification

- Production verification: 사람이 수행할 필요 없음. 이번 Task는 로컬 workflow 도구 변경이다.
- 실제 Codex/Gemini 실행: 자동으로 수행하지 않음.

## Pending Verification

- 실제 Antigravity 전용 CLI는 현재 환경에서 발견되지 않았고 비대화형 입력 형식도 확인하지 못했다. 검증된 wrapper를 사용할 경우 `AGENT_ANTIGRAVITY_BIN`에 지정해야 한다.

## Evidence Notes

- 자동 test는 실제 Codex, Gemini 또는 Antigravity를 호출하지 않고 임시 가짜 executable을 사용했다.
- unittest 출력 중 argparse error 문구는 기존 테스트가 오류 조건을 검증하며 발생시키는 예상 stderr이고 최종 exit code는 0이다.
- Git commit, push, merge, Kubernetes, DB, production curl은 실행하지 않았다.
