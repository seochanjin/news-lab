# 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## 작업 목적

기존 문서 기반 Agent workflow를 유지하면서 prompt 복사, 실행 전 상태 확인,
Agent 실행 로그 보존을 자동화하는 로컬 실행 하네스를 추가하는 것이 목적이었다.

작은 작업은 Task 전체를 한 번에 구현하는 일반 모드로 빠르게 진행하고, 범위와
순서 통제가 필요한 작업은 첫 번째 미완료 UNIT 하나만 실행하는 방식으로
분리했다. 동시에 처음 사용하는 사람도 문서만 보고 Task 생성부터 PR 준비까지
진행할 수 있도록 한글 가이드와 공통 Task 작성 정책을 정리했다.

## 기존 문제

- `agent_next_step.sh`가 prompt만 생성해 사용자가 매번 복사해야 했다.
- 현재 branch와 workflow 문서 상태가 잘못되어도 다음 prompt를 생성할 수 있었다.
- 일반 구현과 큰 작업의 단계별 구현을 구분하는 표준 형식이 없었다.
- Agent의 prompt, stdout, stderr, 종료 코드와 timeout 결과가 자동으로
  보존되지 않았다.
- 다음 action을 판단하려면 Task, Verification, Review와 Approved Fixes를
  사람이 직접 확인해야 했다.
- workflow 사용법과 공통 안전 규칙이 여러 Task prompt에 반복됐다.
- 기존 테스트는 `unittest` 중심이었고 공통 pytest 개발 환경이 없었다.
- 초기 상태 판정은 Verification 문서 전체에서 `Status: failed` 문자열을 찾아
  과거 실패 이력과 설명 문구까지 현재 실패로 오인할 수 있었다.

## 변경 내용

- `scripts/agent_run.sh` 직접 실행 진입점을 추가했다.
- 일반 구현, UNIT 구현, Antigravity Review, 승인 Fix action을 지원했다.
- Task parser, workflow 상태 판정, gate, prompt builder, runner와 CLI를
  테스트 가능한 Python package로 분리했다.
- `Implementation Units`가 없는 기존 Task와 기본값 `없음`을 일반 모드로
  호환했다.
- 신규 Task template에 `Implementation Units`, 현재 Task pointer와
  `Verification Status: pending`을 추가했다.
- `.agent-runs/`에 prompt, stdout, stderr와 result JSON을 저장하고 Git에서
  제외했다.
- status와 preview를 추가하고 `--yes`, `--timeout` option을 지원했다.
- 한글 workflow 사용 가이드, Task 작성 가이드와 Python docstring 정책을
  추가했다.
- pytest를 production dependency가 아닌 `requirements-dev.txt`에 추가했다.
- Verification 현재 상태를 명시적 `Verification Status` section으로 관리하고
  완료 상태에서는 `pr-draft`를 권장하도록 변경했다.

## 구현 상세

### Task와 UNIT parser

Markdown의 2단계 heading을 section으로 분리하되 fenced code block 안의 heading은
예시로 처리한다. `Implementation Units`는 다음 조건을 검증한다.

- `없음`과 checklist가 동시에 존재하지 않음
- `- [ ] UNIT-NN: 설명` 형식
- UNIT identifier 중복 없음
- 앞선 UNIT이 미완료인 상태에서 뒤 UNIT이 완료되지 않음

UNIT mode는 첫 번째 미완료 항목 하나만 prompt에 포함하며 다음 UNIT을 자동으로
실행하지 않는다.

### Workflow gate

직접 실행 전에 repository와 branch, branch별 Task, `docs/tasks/main.md`,
필수 workflow 문서와 대상 CLI를 검사한다.

- `main`, `master`에서 구현과 Fix 차단
- Approved Fixes가 없거나 비어 있으면 Fix 차단
- 일반 Task에서 UNIT 실행 차단
- 구현 diff나 Verification이 준비되지 않은 Review 차단
- 명시적 `Verification Status: failed` 상태에서 Review 차단

Gate는 실행 가능 여부만 판정하며 production command를 대신 실행하지 않는다.

### Agent runner와 로그

Codex는 확인된 `codex exec -C <repo> -` 입력 방식을 사용한다. 현재 환경에서
별도 Antigravity CLI는 발견되지 않아 확인된 Gemini CLI의 `--prompt`와
`--approval-mode auto_edit`를 사용하고, 검증된 stdin wrapper는
`AGENT_ANTIGRAVITY_BIN`으로 지정할 수 있게 했다.

실행 로그 구조:

```text
.agent-runs/<safe-branch>/<timestamp>-<action>/
├── prompt.md
├── stdout.log
├── stderr.log
└── result.json
```

Timeout 시 process group을 종료하고 exit code 124로 기록한다. 비정상 종료
코드는 그대로 보존하며, Agent 종료 코드 0만으로 Task 또는 Verification을
자동 완료하지 않는다.

### 상태 판정

status는 branch, Task, 실행 mode, UNIT 진행 상태, Verification, Review,
Approved Fixes와 다음 action을 읽기 전용으로 출력한다.

Verification은 문서 전체 문자열 검색 대신 다음 section만 현재 상태로 사용한다.

```markdown
## Verification Status

passed
```

지원 상태는 `pending`, `passed`, `failed`다. 상태 section이 없는 기존 문서는
`present`, 문서가 없으면 `missing`으로 처리한다. 과거 실패 기록과 fenced code
예시는 현재 실패 판정에 영향을 주지 않는다.

### 승인 Fix 반영

- FIX-01: workflow Python 모듈과 테스트에 실제 역할, 입력·출력, 예외,
  부수 효과 및 검증 목적을 설명하는 한글 docstring을 추가하고 공통 정책과
  prompt에 연결했다.
- FIX-02: pytest 9.1.1 환경에서 실제 전체 테스트 결과를 Verification에
  반영하고 과거 미설치 이력은 superseded 기록으로 보존했다.
- FIX-03: Verification 상태 문자열 오탐을 제거하고 상태별 회귀 테스트 및
  PR 준비 action 판정을 추가했다.

## 대안 검토

### 기존 Bash script에 모든 기능 구현

진입점 수를 줄일 수 있지만 Markdown section, UNIT 순서, workflow 상태와 timeout
처리를 Shell 정규식과 process 제어로 구현하면 테스트와 유지보수가 어려워진다.

### 기존 prompt-only workflow 제거

직접 실행만 제공하면 단순히 prompt를 검토하거나 다른 Agent UI에 복사하려는
사용 흐름을 잃는다. CLI가 없거나 실행 방법이 확인되지 않은 환경의 fallback도
사라진다.

### 모든 Task에 UNIT mode 강제

범위 통제에는 유리하지만 작은 기능과 문서 수정까지 절차가 늘어나 NewsLab의
빠른 전체 흐름 구현 방식을 방해한다.

### pytest를 production dependency에 추가

설정은 단순하지만 runtime image에 개발 전용 dependency가 포함된다.

### pytest 미설치 시 자동 설치

편의성은 높지만 status나 Agent 실행이 사용자의 Python 환경을 묵시적으로
변경한다. 승인 Fix에서 deferred로 유지했다.

### Verification 전체 문자열 검색

구현은 단순하지만 과거 기록과 설명 속 `Status: failed`를 현재 상태로 오인한다.
명시적 상태 section 방식으로 교체했다.

### 외부 orchestration framework 도입

Agent graph와 상태 머신 확장에는 유리하지만 현재 범위보다 복잡하며 dependency와
운영 부담이 커진다.

## 선택한 접근과 근거

- Bash는 repository 진입점과 기존 prompt 호환을 담당하고, parser·상태·gate·
  runner는 Python으로 분리했다. 복잡한 로직을 단위 테스트할 수 있고
  `shell=True` 없이 인자 배열로 subprocess를 실행할 수 있기 때문이다.
- prompt-only와 직접 실행을 병행했다. 사용자가 실행 전 prompt를 확인하고 CLI가
  없는 환경에서도 기존 workflow를 계속 사용할 수 있다.
- 일반 mode를 기본값으로 유지하고 UNIT mode를 선택적으로 사용했다. 빠른 MVP와
  위험한 대형 작업의 범위 통제를 동시에 지원한다.
- 로그는 repository 내부 `.agent-runs/`에 저장하되 Git에서 제외했다. 실행
  evidence를 남기면서 PR diff를 오염시키지 않는다.
- Verification 현재 상태를 별도 section으로 분리했다. 과거 evidence를 삭제하지
  않고도 현재 상태를 안정적으로 판정할 수 있다.
- pytest는 개발 의존성에만 추가했다. 기존 unittest 실행 방식과 production
  image를 유지한다.

## 트레이드오프

- 하네스가 Agent subprocess 전체를 중단할 수는 있지만 Agent 내부의 개별 판단과
  파일 변경 단계를 실시간 통제하지는 못한다.
- status는 복잡한 PR readiness 상태 머신이 아니다. 문서의 제한된 구조만
  해석하며 최종 품질과 merge 가능 여부는 사람이 판단한다.
- 현재 환경에서 별도 Antigravity CLI의 비대화형 입력 형식을 확인하지 못했다.
  Gemini adapter와 prompt-only fallback을 제공하지만 전용 wrapper 사용 시 별도
  검증이 필요하다.
- 일반 mode로 UNIT Task 전체를 실행할 수 있어 유연하지만 scope가 커질 수 있다.
  이 경우 실행 전에 경고를 출력하고 사용자가 판단한다.
- 로그는 로컬에만 남기므로 장기 보관과 팀 공유가 필요하면 별도 정책이 필요하다.
- Python docstring 정책은 이해 가능성을 높이지만 변경 시 문서 유지 비용이
  증가한다.

## 테스트

Verification 문서에 기록된 실제 결과:

- `python -m pytest tests/test_agent_workflow_state.py -v`
  - 8 passed, 3 subtests passed
- `python -m pytest`
  - 177 passed
- `python -m unittest discover -s tests`
  - Ran 177 tests
  - OK
  - argparse의 `usage:`와 `error:` 출력은 잘못된 입력을 검증하는 기존 테스트의
    예상 stderr다.
- `python -m compileall app scripts tests`
  - 성공
- `python -c "import scripts.agent_workflow"`
  - 성공
  - import 시 Git command, 파일 쓰기, network 접근 또는 Agent 실행 없음
- 세 Shell entrypoint의 `bash -n`
  - 성공
- `git diff --check`
  - whitespace error 없음
- `git diff -- app db k8s`
  - 출력 없음

자동 테스트에서는 실제 Codex, Gemini 또는 Antigravity를 호출하지 않고 mock과
임시 가짜 executable을 사용했다.

## 운영 반영

이번 변경은 로컬 개발 workflow 도구와 문서에만 영향을 준다.

- Production deployment: 대상 아님
- K3s manifest 및 rollout: 변경·실행 없음
- DB migration 및 Supabase SQL: 변경·실행 없음
- Production curl verification: 실행하지 않음
- Secret과 credential: 변경 없음

PR merge, Git push와 merge는 완료되지 않았으며 사람이 수행해야 한다.

## README 업데이트 판단

README는 수정하지 않았다.

이번 기능은 application 사용자 기능이 아니라 repository 내부 Agent 개발
workflow다. 상세 사용법과 정책은 `docs/agent/usage-guide.md`,
`docs/agent/task-authoring-guide.md`, `docs/agent/backend-workflow.md`와
verification gate에 배치하는 것이 문서 책임상 적절하다고 판단했다.

## 확인 결과

- Task checklist 전체 완료
- Verification Status: `passed`
- Review 상태: `present`
- Approved Fixes 상태: `applied`
- Suggested next action: `pr-draft`
- 일반 mode와 UNIT mode parser 및 gate 동작 확인
- 정상 종료, 비정상 종료, timeout과 로그 보존 확인
- 기존 prompt-only command 호환 유지
- 기존 Task의 일반 mode 호환 유지
- production runtime dependency 변경 없음
- FastAPI API, DB, K3s 및 daily pipeline 변경 없음

실제 Antigravity 전용 CLI wrapper 검증은 pending이다. 현재 제공되는 fallback은
Gemini CLI와 prompt-only 방식이다.

## 이번 단계의 의미

NewsLab의 Agent workflow가 문서와 수동 prompt 복사에만 의존하던 단계에서,
문서 상태를 확인하고 안전 gate를 통과한 뒤 실행 evidence를 남기는 로컬 실행
도구 단계로 확장됐다.

자동화를 늘리면서도 Task, Approved Fixes와 Verification을 source of truth로
유지하고 production-impacting 작업은 사람 통제 범위에 남겼다. 일반 mode와
UNIT mode를 함께 제공해 빠른 개발과 범위 통제를 작업 성격에 따라 선택할 수
있게 됐다.

## 포트폴리오용 요약

문서 기반 개발 workflow를 실행 가능한 로컬 Agent 하네스로 확장했다. Markdown
Task와 UNIT parser, branch별 상태 판정, action gate, Codex/Gemini adapter,
timeout과 구조화 로그 저장을 Python으로 구현하고 기존 Bash prompt workflow와
호환했다. 명시적 Verification 상태 모델과 177개 회귀 테스트를 통해 과거 로그
문자열 오탐, unsafe branch 실행, 잘못된 UNIT 순서와 비정상 subprocess 종료를
검증했다. Production 자동화 범위는 확대하지 않고 승인 Fix와 실제 Verification
evidence 중심의 운영 원칙을 유지했다.

## 다음 단계 후보

- 사람이 working tree와 PR 초안을 최종 검토한 뒤 commit, push 및 PR을 생성한다.
- 별도 Antigravity CLI를 사용할 경우 검증된 비대화형 wrapper와 입력 계약을
  확인하고 `AGENT_ANTIGRAVITY_BIN` 경로로 통합 검증한다.
- 로컬 `.agent-runs/`의 보존 기간과 정리 정책을 후속 Task에서 검토한다.
- 상태 모델 확장이 필요하면 Review verdict와 PR readiness를 명시적 section으로
  관리하는 방안을 별도 Task로 검토한다.
- pytest가 없는 환경에서는 자동 설치가 아니라 `requirements-dev.txt` 설치
  안내를 출력하는 기능을 검토한다.
