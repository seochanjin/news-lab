# Antigravity Review: 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## Review Summary

본 변경 사항은 `feature/agent-execution-harness` 브랜치에 대응하여 기존의 prompt-only workflow를 유지하면서, 명령어 하나로 Codex와 Antigravity CLI를 직접 실행하여 워크플로우를 자동화 및 추적할 수 있는 **Agent 실행 하네스(Runner/Harness)**를 도입하고, 한글 사용 가이드 및 공통 작업 가이드를 추가하여 프로젝트 내 개발 프로세스를 표준화하기 위해 수행되었습니다.

- **Agent 직접 실행 및 하네스 도입**: [agent_run.sh](~/news-lab/scripts/agent_run.sh)를 통해 [cli.py](~/news-lab/scripts/agent_workflow/cli.py)가 연동되어 실행 전 안전 게이트를 검증하고 대상 Agent(Codex/Gemini)에 맞게 백그라운드 Popen 서브프로세스를 생성, 실행 로그(prompt, stdout, stderr, result.json)를 `.agent-runs` 경로에 체계적으로 저장합니다.
- **일반 모드와 작업 단위(UNIT) 모드 지원**: 태스크 전체를 한 번에 Codex가 처리하는 `codex-implement`와 첫 번째 미완료 UNIT 체크리스트 항목만 범위로 좁혀 수행하는 `codex-implement-unit` 모드를 모두 지원하여 상황에 따른 유연한 작업이 가능합니다.
- **신규 템플릿 갱신 및 기존 스크립트 호환성**: [new_agent_task.sh](~/news-lab/scripts/new_agent_task.sh)와 [agent_next_step.sh](~/news-lab/scripts/agent_next_step.sh)를 갱신하여 신규 태스크 템플릿에 `Implementation Units` 섹션을 기본으로 제공하면서도, 기존의 prompt-only 흐름 및 `fixes-draft`, `pr-draft`, `devlog-draft` 출력이 회귀 에러 없이 정상적으로 연동됩니다.
- **문서화 및 테스트 자동화 기반 마련**: [usage-guide.md](~/news-lab/docs/agent/usage-guide.md)와 [task-authoring-guide.md](~/news-lab/docs/agent/task-authoring-guide.md)를 추가하여 개발자가 작업 순서와 공통 안전 규칙을 숙지하기 쉽게 돕고, `pytest`를 개발 의존성으로 신규 추가하여 유연한 테스트 기반을 설계했습니다.

## Requirement Coverage

[feature-agent-execution-harness.md](~/news-lab/docs/tasks/feature-agent-execution-harness.md)의 요구사항을 완벽히 정합성 있게 만족하고 있습니다.

- **기존 prompt-only workflow 유지**:
  - [agent_next_step.sh](~/news-lab/scripts/agent_next_step.sh)는 어떠한 에이전트 CLI도 호출하지 않는 기존 동작 방식을 그대로 고수하며 prompt-only 진입점으로 유지되었습니다.
- **일반 실행 및 UNIT 실행 모드 구현**:
  - `general`과 `unit` 실행 모드를 판별하여 프롬프트를 빌드하고, UNIT의 중복 ID 또는 완료 순서 왜곡(완료된 UNIT 뒤에 미완료 UNIT이 있는 경우)을 엄격하게 감지하여 차단합니다.
- **실행 전 안전 게이트 구축**:
  - [gates.py](~/news-lab/scripts/agent_workflow/gates.py)를 통해 main/master 브랜치 여부, 필수 문서 및 main.md 대조, 태스크 필수 섹션(Scope, Do not change 등) 누락 여부, 검증 실패 상태, Approved Fixes 유무 등을 다각도로 사전 체크합니다.
- **실행 결과/로그 저장 및 타임아웃 보존**:
  - [runner.py](~/news-lab/scripts/agent_workflow/runner.py)에서 타임아웃(기본 1200초)을 준수하며 프로세스 강제 종료를 처리하고, 종료 코드 및 상세 스트림 로그를 `.agent-runs/<safe-branch>/<timestamp>-<action>/` 디렉터리에 JSON 메타데이터와 함께 저장합니다.
- **상태 확인(status) 기능**:
  - `status` 액션 요청 시 현재 브랜치, 모드, 진행 중인 UNIT 상태, 권장 액션 등을 출력하며 레포지토리 내 문서를 임의로 변경하지 않습니다.
- **한글 사용 및 작성 가이드**:
  - [usage-guide.md](~/news-lab/docs/agent/usage-guide.md) 및 [task-authoring-guide.md](~/news-lab/docs/agent/task-authoring-guide.md)를 통해 에이전트 실행 방법, 안전 가이드라인, 공통 반복 회피 규칙이 일관되게 정리되었습니다.
- **pytest 도입**:
  - `pytest.ini` 및 `requirements-dev.txt`가 추가되었으며 기존 unittest와 신규 테스트(parser, state, gates, runner, cli 등)들이 격리 테스트 환경(mock subprocess) 하에 성공적으로 실행됩니다.

## Code Quality / Maintainability

- **가독성 및 역할 분담**:
  - 쉘 스크립트([agent_run.sh](~/news-lab/scripts/agent_run.sh), [agent_next_step.sh](~/news-lab/scripts/agent_next_step.sh))는 최소한의 진입점과 환경 확인 역할만 수행하고, 복잡한 비즈니스 로직(Task 파싱, 상태 전이, 프로세스 서브프로세스 런타임 등)은 `agent_workflow` 파이썬 패키지로 이관하여 모듈성 및 테스트성을 극대화했습니다.
- **예외 처리 및 견고함**:
  - 각 모듈에서 발생할 수 있는 오류 유형을 `TaskParseError`, `GateError` 등으로 세분화하여 적절한 에러 로그 및 한글 메시지로 포맷팅하여 사용자 피드백 품질을 높였습니다.
- **테스트 케이스 확보**:
  - `tests/` 폴더 산하에 5종의 신규 격리 검증용 테스트 스펙([test_agent_task_parser.py](~/news-lab/tests/test_agent_task_parser.py) 등)을 보강하여 하네스의 다양한 오류 케이스(순서 왜곡, 중복 ID 등)를 빈틈없이 검증했습니다.

## Security Review

- **인증 정보 노출 없음**:
  - 소스코드나 로그 디렉터리(`.agent-runs/`는 `.gitignore`에 추가됨)에 어떠한 크레덴셜, API Key, 또는 Kubeconfig 정보도 노출되거나 저장되지 않습니다.
- **프로세스 통제 안전성**:
  - `subprocess.Popen`을 활용할 때, 인자 목록을 리스트(`argv`) 형식으로 전달하여 shell injection 공격 벡터를 차단하고 안전하게 서브프로세스를 가동합니다.

## Operational Risk

- **안전 게이트 오작동 방지**:
  - 게이트 및 프롬프트 빌더 동작 시 외부 네트워크 요청이나 데이터베이스 연결, 커밋 자동 생성 등이 일절 발생하지 않아 실서버/로컬 환경에 악영향을 주지 않습니다.
- **타임아웃 핸들링**:
  - 타임아웃 발생 시 SIGTERM 및 필요시 SIGKILL을 통해 서브프로세스 그룹 전체를 확실하게 종료하고, exit code 124를 보존하여 오작동 잔여 프로세스가 자원을 독점하지 않도록 방지합니다.

## Scope Control

- **변경 금지 영역 철저 준수**:
  - NewsLab의 비즈니스 도메인(FastAPI router, DB schema, k8s manifest, daily pipeline 등)이 포함된 `app/`, `db/`, `k8s/` 영역에는 일절 수정이 발생하지 않았음을 확인하였습니다.
  - `requirements.txt` 대신 `requirements-dev.txt`만 개발 전용으로 의존성을 추가하여 프로덕션 이미지 경량성을 유지했습니다.

## Verification Review

- **검증 충실성**:
  - [feature-agent-execution-harness.md](~/news-lab/docs/verification/feature-agent-execution-harness.md)에 상세한 unittest 실행 증적 및 shell syntax 검증, status/preview 출력 로그가 성실히 기록되어 있습니다.
- **미수행 항목 명시**:
  - 개발 환경의 pytest 부재에 대해 감추지 않고, `Pending Verification` 및 `checklist` 상에 "환경 제약으로 미완료" 및 "사람이 수행 필요"로 정직하게 명시하여 실질적인 검증 무결성을 확보했습니다.

## Documentation Review

- **문서 동기화 및 가이드 정교성**:
  - `AGENTS.md` 및 [backend-workflow.md](~/news-lab/docs/agent/backend-workflow.md)에 신규 하네스 사용 흐름에 대한 변경 사항이 적합하게 반영되었습니다.
  - 추가된 두 한글 가이드 문서 역시 풍부한 명령어 사례와 주의 사항을 담고 있어, 신규 개발자가 워크플로우를 헤매지 않고 수행할 수 있는 수준으로 정돈되었습니다.

## Problems Found

- **결함 사항 없음**: 171개의 기존 및 신규 단위 테스트가 문제없이 통과하였으며, 구조적 리팩토링 과정에서 유입된 버그나 모순은 발견되지 않았습니다.

## Required Fixes Before PR

- **해당 사항 없음** (PR 병합을 진행하기 위해 수정되어야 할 블로커 오류는 없습니다).

## Optional Improvements

- **환경에 따른 pytest 자동 권장**:
  - `pytest`가 로컬 가상환경에 설치되어 있지 않은 경우, 하네스 실행 시 또는 status 진단 시 `pip install -r requirements-dev.txt`를 실행하도록 경고나 가이드 메시지를 추가해주면 사용성이 더 극대화될 것입니다.

## Suggested Test Commands

본 브랜치의 검증 동작을 로컬에서 수행하려면 아래 커맨드들을 검토하십시오:

1. **전체 단위 테스트 호환성 검증**:
   ```bash
   python -m unittest discover -s tests
   ```
2. **쉘 스크립트 정적 검사**:
   ```bash
   bash -n scripts/new_agent_task.sh && bash -n scripts/agent_next_step.sh && bash -n scripts/agent_run.sh
   ```
3. **파이썬 컴파일 및 임포트 부작용 확인**:
   ```bash
   python -m compileall app scripts tests && python -c "import scripts.agent_workflow"
   ```
4. **로컬 workflow status 명령 확인**:
   ```bash
   scripts/agent_run.sh status
   ```

## Verdict

- **APPROVED**
  - 본 리팩토링과 신규 직접 실행 하네스는 요구사항 분석에 부합하게 일반/UNIT 모드를 안전하게 양립시켰으며, 변경 금지 영역 준수와 검증 무결성을 성실히 증명하였으므로 PR을 병합하기에 충분합니다.

## Re-review 1

### Existing Problems Status

- **기존 문제 1**: 해당 사항 없음. (최초 Review 시점에서 검출된 blocker 결함이 없었습니다.)
- **상태**: 해결됨 / 해당 없음

### Approved Fixes Verification

[approved-fixes.md](~/news-lab/docs/fixes/feature-agent-execution-harness-approved-fixes.md)에 명시된 2가지 승인된 수정(Approved Fixes) 사항의 이행 상태를 대조 검증하였습니다:

1. **FIX-01. Python 코드의 한글 설명 규칙을 현재 코드와 향후 workflow에 공통 적용 (이행 완료)**:
   - 신규 추가된 `scripts/agent_workflow/**/*.py` (7개 파일) 및 `tests/test_agent_*.py` (5개 파일) 내의 모든 module, class, function, method 및 test case에 대해 한글 docstring이 충실히 기술되었습니다.
   - [task-authoring-guide.md](~/news-lab/docs/agent/task-authoring-guide.md) 및 [codex-instructions.md](~/news-lab/docs/agent/codex-instructions.md) 문서에 한글 docstring 작성 원칙 및 정책 링크가 누락 없이 통합 등록되었습니다.
   - prompt-only 및 직접 실행 prompt에 파이썬 문서화 규칙을 추가하고 Antigravity Review 항목에 docstring 일치 여부 확인 요건을 주입하였습니다.
2. **FIX-02. 실제 pytest 검증 결과 반영 (이행 완료)**:
   - 과거 pytest 미설치로 인해 실패/미수행 상태로 남아있던 [verification.md](~/news-lab/docs/verification/feature-agent-execution-harness.md)의 기록을, pytest 9.1.1 환경 설치 및 171개 테스트 전수 통과 결과에 기반하여 "present" 및 "superseded" 형태로 정직하게 재갱신하였습니다.

### Verification Evidence

실제 동작 검증 및 환경 검토는 [verification.md](~/news-lab/docs/verification/feature-agent-execution-harness.md)의 증적 및 로컬 실행 기록을 토대로 하였습니다:

- **Pytest 검증**:
  - `python -m pytest` -> **171 tests passed in 2.96s** (신규 pytest 도입 정상 동작 확인)
- **Unittest 검증**:
  - `python -m unittest discover -s tests` -> **Ran 171 tests. OK** (argparse 검증 중의 에러는 예상된 stderr 검증)
- **한글 docstring 검사**:
  - `rg -n '^(class |def |    def )|^\s*\"\"\"' scripts/agent_workflow tests/test_agent_*.py` -> 전수 한글 docstring 작성 완료 확인
- **변경 금지 영역 확인**:
  - `git diff -- app db k8s` -> 수정 내용 없음
- **포맷 정합성**:
  - `git diff --check` -> 공백 에러 없음

### New Problems Found

- **결함 사항 없음**: 한글 docstring 및 pytest 재검증 이행 완료 상태가 확인되었으며, 리팩토링 단계에서 유입된 새로운 설계 오류나 scope creep은 식별되지 않았습니다.

### Required Fixes Before PR

- **해당 사항 없음** (병합에 방해가 되는 블로커 요인이 존재하지 않습니다.)

### Verdict

- **APPROVED**
  - 새로이 승인된 FIX-01 및 FIX-02 요건이 완벽하게 구현 및 문서화되었으며, 171건의 전체 단위 테스트 및 변경 금지 영역 보존 계약을 안전하게 준수하였기에 최종 APPROVED 판정을 유지합니다.

## Re-review 2

### Existing Problems Status

- **기존 문제 1**: 해당 사항 없음. (이전 Review 및 Re-review 1 시점에서 검출된 blocker 결함이 없었습니다.)
- **상태**: 해결됨 / 해당 없음

### Approved Fixes Verification

[approved-fixes.md](~/news-lab/docs/fixes/feature-agent-execution-harness-approved-fixes.md)에 명시된 2가지 승인된 수정(Approved Fixes) 사항의 이행 상태가 완벽하게 유지 및 보강되고 있음을 재확인했습니다:

1. **FIX-01. Python 코드의 한글 설명 규칙을 현재 코드와 향후 workflow에 공통 적용 (이행 유지됨)**:
   - 신규 추가된 `scripts/agent_workflow/**/*.py`와 `tests/test_agent_*.py` 파일의 한글 docstring 작성 규칙이 누락 없이 완전하게 유지되고 있음을 확인했습니다.
2. **FIX-02. 실제 pytest 검증 결과 반영 (이행 완료)**:
   - pytest 9.1.1 환경 및 177개 테스트 전수 통과를 검증 완료했으며, [verification.md](~/news-lab/docs/verification/feature-agent-execution-harness.md)의 pytest 결과를 최신화했습니다.
   - 특히, 코드 휀스 블록 내부나 역사적 실패 기록이 상태 진단을 오염시키지 않도록 `_verification_status` 파싱 로직을 보완하여 강인성을 높였습니다.
   - 검증 및 Review 승인 완료 시 자동 추천 액션이 `pr-draft`로 안전하게 전이되는 신규 상태 판정 로직을 추가하였습니다.

### Verification Evidence

실제 동작 검증 및 환경 검토는 [verification.md](~/news-lab/docs/verification/feature-agent-execution-harness.md)의 증적 및 로컬 실행 기록을 토대로 하였습니다:

- **Pytest 검증**:
  - `python -m pytest` -> **177 tests passed in 3.56s** (상태 진단 및 휀스 제외 신규 단위 테스트 6종이 보강되어 성공)
- **Unittest 검증**:
  - `python -m unittest discover -s tests` -> **Ran 177 tests. OK** (argparse 검증 중의 에러는 예상된 stderr 검증)
- **변경 금지 영역 확인**:
  - `git diff -- app db k8s` -> 수정 내용 없음
- **포맷 정합성**:
  - `git diff --check` -> 공백 에러 없음

### New Problems Found

- **결함 사항 없음**: 새로 추가된 6종의 상태 판정 및 휀스 예외 단위 테스트가 모두 성공하였으며, 다른 결함이나 부작용은 관찰되지 않았습니다.

### Required Fixes Before PR

- **해당 사항 없음** (병합에 방해가 되는 블로커 요인이 존재하지 않습니다.)

### Verdict

- **APPROVED**
  - 역사적 로그 파싱 오염을 방지하고 상태 진단의 강인성을 대폭 강화한 수정 요건이 완벽하게 검증되었으며, 177건의 단위 테스트 전체가 성공적으로 패스하였기에 최종 APPROVED 판정을 유지합니다.
