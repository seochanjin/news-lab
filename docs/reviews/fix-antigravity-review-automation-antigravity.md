# Antigravity Review: Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## Unit Review Status

- [x] UNIT-01: 기존 Antigravity Review 실행 경로와 Re-review 실패 사례 분석
- [x] UNIT-02: Task Implementation Units Parser와 Review Status 자동 생성 구현
- [x] UNIT-03: 다음 UNIT Review 대상 탐지와 구조화된 Review Context 생성 구현
- [x] UNIT-04: Antigravity Review Prompt 자동 생성과 실제 실행 경로 구현
- [x] UNIT-05: UNIT Review 응답 검증과 Append-only Writer 구현
- [x] UNIT-06: UNIT Review Verdict 기반 Review Status 갱신 구현
- [x] UNIT-07: Approved Fixes·최신 Verification·Review History Parser와 모순 검증 구현
- [x] UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신

## Review Summary

Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선 작업에 대해 UNIT-01부터 UNIT-08까지 순차 Review를 완료했다.

Task Implementation Units 파싱, 다음 Review 대상 자동 선택, 구조화된 Review Context와 Prompt 생성, 실제 `agy-print` 실행, 응답 검증, Append-only Writer, Verdict 기반 Review Status 갱신, Approved Fixes·Verification·Review History 파싱과 전체 회귀 테스트 연결을 확인했다.

실제 외부 Antigravity Review 과정에서 다음 문제를 발견하고 수정했다.

- Review Agent가 명령 실행을 시도하는 응답
- `agy --print` Prompt 인자 순서 오류
- `- 없음`, `- PASS`와 같은 Markdown bullet scalar 처리 실패
- Review 본문의 명령 경로 언급을 실행 시도로 오탐하는 문제
- `- 없음.`처럼 종결부호가 포함된 scalar 처리 실패

수정 후 UNIT-01부터 UNIT-08까지 모두 `PASS` Verdict로 완료됐으며, UNIT-08 Integration Review에서 전체 Acceptance Criteria, UNIT 간 계약, 회귀 테스트, 문서와 구현의 일치 여부 및 변경 금지 영역 준수를 확인했다.

## Problems Found

- 없음

모든 Review finding은 승인된 FIX 절차를 통해 수정 및 재검증됐다. 최종 Integration Review 기준 미해결 문제는 없다.

## Required Fixes Before PR

- 없음

코드 수정이 필요한 미완료 Review finding은 없다.

다만 실제 외부 Review 완료 결과를 Approved Fixes와 Verification 문서에 최종 반영하고, FIX-09 및 FIX-14의 완료 상태를 확인해야 한다.

## Optional Improvements

- Review 자연어 본문과 기계 판정용 Metadata를 분리하는 구조 검토
- `REVIEW_RESULT`, `PROBLEM_COUNT` 등의 고정 필드를 통한 Validator 단순화
- Task mode, Agent action mode, Review mode와 선택 Target을 명시적으로 분리하는 Workflow 상태 모델 도입
- 완료된 여러 UNIT을 한 번에 통합 검토할 수 있는 Full Review mode 추가
- 외부 Agent CLI 계약을 확인하는 경량 Contract Test 추가
- UNIT별 관련 diff 또는 commit 범위를 더 정확히 제한하는 Context 생성 방식 검토

위 항목은 현재 PR의 필수 수정 사항이 아니며 별도 Task로 분리한다.

## Suggested Test Commands

```bash
python -m pytest tests/test_agent_*.py -v
python -m pytest
python -m unittest discover -s tests
python -m compileall scripts tests
bash -n scripts/agent_run.sh
git diff --check
```

변경 금지 영역 확인:

```bash
git diff -- app db k8s requirements.txt
```

최종 Workflow 상태 확인:

```bash
scripts/agent_next_step.sh status
```

## Risk Notes

- Antigravity Review 응답은 자연어 Markdown이므로, 새로운 표현 변형이 엄격한 Validator와 충돌할 가능성이 있다.
- 현재 실행 시도 탐지는 텍스트 패턴에 의존하므로 실제 의도와 단순 문서 인용을 완전히 구분하지 못할 가능성이 있다.
- `--sandbox`는 Terminal restriction을 제공하지만 모든 Tool과 외부 동작을 완전히 비활성화하는 전용 read-only mode는 아니다.
- Review 파일 직접 변경 복구와 Append-only Writer가 적용돼 있으나, 향후 Writer 또는 응답 형식 변경 시 기존 Review History 보존 테스트를 유지해야 한다.
- 외부 `agy` 동작이나 CLI 인자 계약이 변경되면 Adapter와 Contract Test를 함께 갱신해야 한다.

## UNIT Review: UNIT-01

### Review Scope

- UNIT-01(기존 Antigravity Review 실행 경로와 Re-review 실패 사례 분석) 요구사항에 따른 NewsLab backend 구현 검토
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py` 및 관련 테스트 코드의 변경사항 분석

### Requirement Coverage

- Antigravity Review 자동 실행을 위한 `agy-print` 어댑터 선택 및 실행 인자(`--print`, `--sandbox`, `--print-timeout`) 적용 완료
- `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 활용한 재귀 실행 차단 가드 및 프롬프트 크기 상한 검증 로직 반영 완료
- 에이전트의 불법 실행 시도 감지(`_detect_review_execution_attempt`) 및 실제 실패 사례(sandbox, user request)에 대응하는 Fixture 검증 추가 완료
- UNIT Task 실행 시 pending 상태의 Verification을 허용하는 게이트 예외 처리 반영 완료

### Previous UNIT Contract Regression

- 없음

### Code Quality / Maintainability

- 실행 시도 감지 및 파일 복구 등 복잡한 하네스 예외 상황에 대응하는 로직이 구조적으로 깔끔하게 분리됨
- 새로 작성 및 수정된 Python 코드와 테스트에 한글 docstring이 명세에 맞추어 충실하게 작성됨

### Scope Control

- UNIT-01 범위에 규정된 실행 경로 개선 및 실패 방지 가드 구현에만 집중하였으며, Do not change 정책 침범이나 Scope creep은 발견되지 않음

### Verification Evidence

- `tests/test_agent_workflow_cli.py`, `tests/test_agent_workflow_gates.py`, `tests/test_agent_workflow_runner.py` 내의 신규 기능 및 예외 처리에 대한 테스트 검증 완료
- 최신 Verification Snapshot 기준 `pytest: 324 passed`, `unittest: 324 passed` 완료

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-02

### Review Scope

- UNIT-02(Task Implementation Units Parser와 Review Status 자동 생성 구현) 범위에 해당하는 CLI 연동, 게이트 및 실행 러너 변경사항 검토
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py` 및 관련 검증 테스트 확인

### Requirement Coverage

- **Task 파싱 및 Status 생성**: Task에서 UNIT ID, 제목 및 구현 완료 체크 상태를 온전히 파싱하여 `Unit Review Status`가 누락된 경우 생성하고, 존재하는 경우 기존 이력을 보존하도록 구현됨
- **UNIT 자동 선택 및 Context 생성**: 구현 완료되었으나 리뷰가 되지 않은 가장 첫 UNIT을 검토 대상으로 자동 선택하고 Prompt를 빌드함
- **샌드박스 실행 및 Append-only 반영**: Antigravity가 리뷰 파일을 직접 덮어쓰지 못하도록 사후 복구 로직(`_restore_review_file`)을 추가하고, 유효한 응답 결과만 검증해 파일 끝에 덧붙이도록 개선함
- **Dry-run 지원**: `--dry-run` 인자를 추가하여 외부 Agent 연동 없이 생성할 Prompt 정보와 타겟 모드 등을 요약하여 확인할 수 있도록 지원함

### Previous UNIT Contract Regression

- 기존 수동 실행 모드와의 역호환성을 보존하고, UNIT-01에서 도출한 분석 내용과 충돌하는 로직은 보이지 않음. 이전 계약 회귀 없음

### Code Quality / Maintainability

- 오류 발생 시 `GateError` 및 `ReviewResponseError` 등을 적절히 구분하고 `failure_category`를 지정하여 안정성이 뛰어남
- 한글 Docstring과 주석이 변경 및 신규 파일에 명확하게 명시되어 관리 효율이 우수함

### Scope Control

- K3s, Supabase 인프라 변경이나 DB Migration 등의 통제 영역 침범 없음
- `Do not change` 영역인 Codex WIP 1 정책이나 Git push 등의 사람 통제 원칙이 적절히 유지됨

### Verification Evidence

- `tests/test_agent_workflow_*.py` 테스트를 통해 UNIT Review의 pending Verification 허용 정책, dry-run, 재귀 실행 방지 가드 등이 완전히 검증됨
- pytest 및 unittest 324 passed 완료로 안정성 확인됨

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-03

### Review Scope

- UNIT-03 요구사항인 '다음 UNIT Review 대상 탐지와 구조화된 Review Context 생성 구현'에 관련된 변경사항 검토.
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py` 및 관련 테스트 코드(`tests/test_agent_workflow_*.py`)의 변경 내용 검토.
- `agy-print` 어댑터를 통한 비대화형 `--print` 처리, 재귀 실행 방지 Guard, prompt 크기 상한 검증 및 append-only Writer 구현의 적절성 검토.

### Requirement Coverage

- **Review 대상 자동 선택 및 Context 생성**: `_review_status_for_prompt` 및 `_build_antigravity_prompt`를 통해 Task의 Implementation Units를 파싱하고 다음 미검토 UNIT을 자동 탐색하여 Review Context를 구조화하는 로직이 반영됨.
- **자동 실행 어댑터 추가**: `gates.py`에서 `agy` 실행 파일 존재 시 `agy-print` 어댑터와 함께 자동 실행 지원 상태(`automatic_execution_supported=True`)를 반환하며, `runner.py`에서 sandbox 및 timeout 인자가 포함된 명령어 옵션을 바인딩하도록 구현됨.
- **Append-only Writer 및 파일 복구**: Agent가 직접 Review 파일을 변경하는 것을 차단하고(`review_file_modified_by_agent`), 실행 후 정상적인 검증 단계를 거친 section만 append하고 실패 시에는 이전 상태로 안전하게 복구하는 로직이 `runner.py`에 적용됨.
- **재귀 실행 차단**: `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 설정하고 CLI 진입 시 이를 검사해 재귀 실행을 원천 차단하는 가드 구현.
- **Verification Gate 완화**: UNIT Review 모드에 한하여 전체 Verification 상태가 pending이어도 실행이 가능하도록 예외 규칙 적용.
- **Dry-run 기능 제공**: `--dry-run` 및 `--preview` 인자를 통해 실제 실행을 하지 않고 Review 대상 정보와 생성될 Prompt 및 Context 정보를 확인할 수 있도록 구현됨.

### Previous UNIT Contract Regression

- 없음. 기존 Codex 구현 workflow 및 수동 prompt 방식 등 이전 UNIT 계약 요소들과의 충돌 없이 동작하도록 독립적인 어댑터 구조로 설계됨.

### Code Quality / Maintainability

- `run_agent` 함수 내에서 오류 상황에 대한 세분화된 failure category 설정과 파일 복원 로직(`_restore_review_file`)이 유기적으로 연결되어 코드 안정성이 높음.
- CLI, Gates, Runner 각 모듈별 유닛 테스트가 꼼꼼하게 작성되어 다양한 실패 및 성공 시나리오를 충실히 검증함.

### Scope Control

- 없음. Do not change 영역을 침범하거나 불필요한 기능(Scope creep)을 추가한 정황은 발견되지 않음.

### Verification Evidence

- `tests/test_agent_workflow_cli.py`, `tests/test_agent_workflow_gates.py`, `tests/test_agent_workflow_runner.py`에 각각 테스트 케이스가 작성 및 검증되었으며, 최신 verification 결과(`pytest` 324 passed, `unittest` 324 passed)가 정상적으로 수집되어 있음.

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-04

### Review Scope

- UNIT-04: Antigravity Review Prompt 자동 생성과 실제 실행 경로 구현 관련 변경 사항 검토
- `scripts/agent_workflow/cli.py`, `gates.py`, `runner.py` 및 관련 테스트 코드 변경 검토
- `agy-print` 어댑터를 통한 비대화형 자동 실행 구현 및 재귀 실행 방지, 명령 실행 의도 차단 로직 검토

### Requirement Coverage

- `scripts/agent_run.sh antigravity-review` 명령을 수동 Prompt 작성 없이 자동으로 실행할 수 있는 `agy-print` 어댑터가 구현됨
- Antigravity가 직접 Review 파일을 변경하는 것을 복구하고, 하네스 단에서 응답 검증 후 append-only 방식으로 추가하도록 통제함
- `--dry-run` 및 `--preview` 옵션을 통해 사전에 Prompt 크기, mode, context 요약 등을 확인할 수 있는 기능이 구현됨
- `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 사용하여 서브프로세스에서의 재귀 실행을 원천 차단함
- Agent 응답 내에 명령 실행 의도가 포함된 문구가 존재할 경우 이를 감지하여 실패 처리하는 안전 가드가 추가됨

### Previous UNIT Contract Regression

- 없음

### Code Quality / Maintainability

- 새로 추가 및 수정된 함수와 메서드에 명확한 한글 Docstring이 작성됨
- `cli.py`, `gates.py`, `runner.py` 각각에 대응하는 단위 테스트가 `test_agent_workflow_cli.py`, `test_agent_workflow_gates.py`, `test_agent_workflow_runner.py`에 세부 시나리오(dry-run, recursion guard, 실행 시도 감지 등)별로 충실하게 보강됨

### Scope Control

- Antigravity Review의 자동화 범위 내에서만 하네스 개선이 수행되었으며, Do not change 정책(수동 배포 통제, Codex workflow 정책 보존 등)을 명확하게 준수함

### Verification Evidence

- Verification 문서 정보에 기반하여 pytest 및 unittest 총 326개의 테스트가 모두 통과 상태(`passed`)임을 확인
- `test_agent_workflow_gates.py`, `test_agent_workflow_cli.py`, `test_agent_workflow_runner.py`에서 신규 기능(재귀 가드, 실행 의도 감지, dry-run 등)에 대한 검증 코드가 통과함

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-05

### Review Scope

- Antigravity Review 응답의 필수 Section 유효성 검증 로직 및 기존 Review를 훼손하지 않는 Append-only Writer의 안전성 검토
- `--dry-run` 모드 및 재귀 실행 방지용 환경변수(`NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE`) 가드 메커니즘 검토
- `agy-print` 어댑터를 통한 비대화형 샌드박스 실행 인수 구성 검토

### Requirement Coverage

- Antigravity 실행 또는 응답 검증 실패 시 Review 파일의 원본을 완벽히 복구하고 수정을 제한하여 안전성 확보 완료
- `--dry-run` 옵션을 구현하여 실제 Agent 실행 없이 대상 UNIT, 예상 Heading, Prompt 정보 등을 확인할 수 있도록 지원 완료
- 응답 내 실행/대기 의도를 담은 특정 패턴 문자열 감지 기능 및 단순 경로 언급에 대한 오탐 방지 로직 적용 완료
- UNIT Task인 경우 Verification이 pending 상태여도 Review gate를 통과할 수 있도록 유연하게 완화 완료

### Previous UNIT Contract Regression

- 없음

### Code Quality / Maintainability

- 실행 제어 환경변수 및 검증 실패 시 원본 복구 흐름(`_restore_review_file`)의 흐름 제어가 명확하고 예외 처리가 견고하게 설계됨
- 다양한 오탐 케이스, 환경변수 주입, 인수 구조 검증 등의 시나리오가 풍부한 단위 테스트로 커버됨

### Scope Control

- UNIT-05 요구사항인 응답 검증 및 Append-only Writer 구현 범위 내에서 일관되게 개발되었으며 Scope Creep은 식별되지 않음

### Verification Evidence

- Verification Snapshot 기준 pytest 및 unittest 326개 테스트 전체 통과 완료

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-06

### Review Scope

- UNIT-06 요구사항인 "UNIT Review Verdict 기반 Review Status 갱신 구현"과 관련된 변경사항 검토
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py` 및 관련 테스트 코드(`tests/test_agent_workflow_*.py`)를 중심으로 검토 진행

### Requirement Coverage

- Agent 실행 후 Verdict가 `PASS`인 경우 Review Status를 완료(`[x]`)로 갱신하고, 그 외의 경우 `[ ]`를 유지하는 로직 구현 확인
- Agent 응답 검증을 통해 유효한 Review Section만 append하고, 검증 실패 시 기존 Review 파일을 원래대로 복원하여 보존하는 안전장치 구현 완료
- `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 활용한 재귀 실행 차단 Guard, 실행 시도 의도 문구 감지(exit 1 및 `review_agent_attempted_execution` 처리), Prompt 크기 제한 검증 추가 확인
- `agy-print` 어댑터를 적용하여 sandbox 및 timeout 인자를 포함한 비대화형 실행 명령 생성 로직 구현 확인
- UNIT Review 모드일 때 Verification pending 상태를 허용하도록 gate 조건 완화 반영 확인

### Previous UNIT Contract Regression

- 없음. 이전 UNIT에서 정의된 Task 파싱 및 Context/Prompt 빌더와의 계약이 안정적으로 유지됨

### Code Quality / Maintainability

- CLI, Gates, Runner에 걸쳐 역할을 명확히 분담하고 헬퍼 함수(`_review_status_for_prompt`, `_detect_review_execution_attempt` 등)를 통해 코드 가독성 및 유지보수성 향상
- 복구 로직(`_restore_review_file`)과 실행 시도 감지 로직의 예외 처리 및 검증 구조가 직관적이고 견고함

### Scope Control

- 허용되지 않은 Application 코드나 인프라 설정 변경이 없으며, 요구사항에 명시된 하네스 제어 범위 내에서만 구현이 이루어짐

### Verification Evidence

- 최신 Verification Snapshot 기준 pytest 326 passed, unittest 326 passed 통과 확인
- 신규 구현된 기능(재귀 방지, Prompt 크기 제한, 실행 시도 감지, 정상 Verdict 갱신 및 파일 복구)을 철저히 검증하는 테스트 코드가 작성되어 성공적으로 수행됨을 확인

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## UNIT Review: UNIT-07

### Review Scope

- UNIT-07: Approved Fixes·최신 Verification·Review History Parser와 모순 검증 구현에 대한 백엔드 변경사항 검토.
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py`, `scripts/agent_workflow/approved_fixes.py` 및 관련 테스트 코드의 변경 범위 분석.

### Requirement Coverage

- **체크리스트 및 상세 FIX 파싱**: `approved_fixes.py`를 통해 Approved Fixes 문서의 canonical checklist를 검증 및 자동 생성하는 로직이 적용됨.
- **Verification Gate 조건 완화**: UNIT Task의 경우 verification pending 상태에서도 review를 허용하도록 검증 로직이 분기 처리됨.
- **재귀 실행 방지 및 명령 실행 의도 차단**: `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 통해 재귀 호출을 막고, `REVIEW_EXECUTION_ATTEMPT_PATTERNS`를 활용해 응답 내의 명령 실행/대기 시도 문구를 차단함.
- **안전한 Append-only 반영**: Agent가 review 파일을 직접 변경할 경우 롤백 후 검증된 stdout 내용만 파일 끝에 append하는 동작이 정상 구현됨.
- **Dry-run 모드 지원**: `--dry-run` 및 `--preview` 옵션을 통해 실제 실행 없이 모드, 대상 UNIT, prompt 크기, verification 및 prompt 본문을 출력하는 기능이 추가됨.

### Previous UNIT Contract Regression

- 없음. 기존 Codex workflow 및 CLI 동작이 정상적으로 보존되었으며, 일반 review 시 verification pending에 대한 엄격한 차단 기준이 유지되면서도 UNIT Review에 한해 완화된 계약이 올바르게 통합됨.

### Code Quality / Maintainability

- `cli.py`와 `runner.py`에 Review Context를 활용하여 검증 및 기록을 분리하는 구조가 체계적으로 정착됨.
- 에러 상황에 대한 구체적인 실패 카테고리(`review_file_modified_by_agent`, `review_agent_attempted_execution`, `review_response_invalid`)를 추가하여 유지보수성과 디버깅 용이성을 확보함.

### Scope Control

- 요구된 UNIT-07 명세 범위를 벗어난 비정상적인 변경사항이나 Scope creep은 발견되지 않음.

### Verification Evidence

- `tests/test_agent_workflow_cli.py`, `tests/test_agent_workflow_gates.py`, `tests/test_agent_workflow_runner.py`에서 dry-run, 재귀 실행 차단, print adapter, 실행 감지 및 validation 관련 테스트가 정상 수행됨.
- 전체 테스트 327 passed 기록.

### Problems Found

- 없음

### Required Fixes Before Next UNIT

- 없음

### Verdict

- PASS

## Integration Review: UNIT-08

### Review Scope

- UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신 검토.
- `scripts/agent_workflow/cli.py`, `scripts/agent_workflow/gates.py`, `scripts/agent_workflow/runner.py` 및 관련 단위/통합 테스트 코드(`tests/test_agent_workflow_cli.py`, `tests/test_agent_workflow_gates.py`, `tests/test_agent_workflow_runner.py`) 검토.
- 검토 범위: `agy-print` 어댑터를 통한 자동 실행 및 `--print` 파라미터 연동, `--dry-run` 프리뷰 기능, Antigravity 재귀 실행 차단, Agent의 명령 실행 의도 탐지 및 파일 직접 수정 방어 메커니즘, pending verification의 UNIT/일반 Task 분기 처리 정합성.

### Acceptance Criteria Coverage

- **자동화된 Review 실행 및 Prompt 구성**: Branch 자동 탐색, Task/Review/Verification/Approved Fixes 파일 자동 매핑, `build_review_context`와 `build_review_prompt`를 통한 비대화형 prompt 자동 생성이 정상 구현됨.
- **재귀 실행 차단 (FIX-03, FIX-04)**: `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 하위 프로세스에 전달하고, 중복 실행 시 `GateError`를 즉시 발생시켜 무한 재귀를 사전에 차단함.
- **명령 및 도구 실행 시도 차단 (FIX-01, FIX-05, FIX-13)**: `REVIEW_EXECUTION_ATTEMPT_PATTERNS` 검사를 통해 실행/대기 의도가 응답에 포함될 경우 `review_agent_attempted_execution`으로 분류하고, Agent가 임의로 수정한 파일은 백업본(`review_before`)으로 자동 복구함.
- **응답 검증 및 Append-only Writer**: `validate_review_response`와 `append_review_response`를 통해 UNIT heading, FIX 개수, Verification 일치 여부를 파싱/검증하여 정상 PASS일 때만 점진적으로 추가하고 Status를 업데이트함.
- **드라이런 기능 (FIX-07)**: `--dry-run` 및 `--preview` 인자를 통해 실제 실행 없이 Prompt 크기, Context 요약, Target UNIT 정보를 출력해 줌.
- **체크리스트 자동 생성 (FIX-10)**: `normalize_approved_fixes`를 통해 header를 기반으로 checklist를 무결하게 자동 생성함.
- 모든 Acceptance Criteria를 정확히 구현 및 만족하고 있음.

### Cross-UNIT Contract Review

- **선행 UNIT 계약 정합성**: UNIT-01부터 UNIT-07까지 구현된 파서, Context 생성기, 프롬프트 빌더, 검증 모듈 및 Append-only Writer가 `cli.py`와 `runner.py`에 유기적으로 연결 및 통합되었으며, 상호 모순 없이 정상 작동함을 회귀 테스트로 검증함.
- **데이터 흐름 안전성**: 빌드된 Context가 Prompt를 거쳐 `agy-print` 인자로 들어가고, 응답 출력 검증 단계를 통과하여 최종 Append-only 및 Status 반영에 도달하는 라이프사이클이 안전하게 정렬됨.

### Code Quality / Maintainability

- `cli.py`, `gates.py`, `runner.py` 각 계층별 책임이 명확히 구분되어 있음.
- 예외적인 상황(예: Agent가 Review 파일을 강제 변경하는 경우, 혹은 샌드박스를 우회하려는 경우)에 대해 복구 및 차단 로직이 견고하게 작성됨.
- `MAX_REVIEW_PROMPT_BYTES` 및 `REVIEW_EXECUTION_ATTEMPT_PATTERNS` 등 주요 환경 제한 정보가 상수로 잘 격리되어 관리됨.

### Security / Operational Risk

- **명령 실행 및 파일 위변조 원천 방어**: Agent의 악의적이거나 비정상적인 외부 명령 시도를 환경변수 수준과 텍스트 패턴 매칭으로 2중 보호하며, 위변조된 파일 복구 메커니즘을 적용하여 시스템의 무결성을 확보함.
- **안전한 실행 샌드박스 유도**: `agy-print` 어댑터가 `--sandbox` 파라미터를 명시적으로 사용하도록 작성되어 운영 위험을 효과적으로 제어함.

### Scope Control

- **Do not change 원칙 준수**: WIP 1 정책, Task 체크박스 세부 규칙, PR Merge 및 DB 배포에 대한 사람 통제 원칙 등 기존 제약조건을 침범하지 않음. 불필요한 기능(Scope creep) 추가 없음.

### Verification Evidence

- `tests/` 디렉터리에 추가된 풍부한 테스트 케이스(재귀 차단 검증, 드라이런 확인, pending 상태 허용 정책, 어댑터 파라미터 매핑 등)가 작성되어, 최종 스냅샷 기준 327건의 pytest 및 unittest가 모두 정상 패스함을 확인하여 회귀 안전성을 검증함.

### Documentation Review

- 새로 작성 및 수정된 코드 파일(`approved_fixes.py`, `review_context.py` 등)과 기존 CLI/Gates/Runner 모듈 전반에 비즈니스 로직과 역할을 설명하는 명확한 한글 Docstring 및 주석이 정밀하게 기술되어 있음.

### Problems Found

- 없음

### Required Fixes Before PR

- 없음

### Verdict

- PASS

## Re-review 1
### Existing Problems Status
- 이전 UNIT Review에서 지적된 미해결 문제 없음.

### Approved Fixes Verification
- FIX-01: 적용 완료. `runner.py`의 `_detect_review_execution_attempt` 및 `review_agent_attempted_execution` 로직을 통해 실행 차단 계약이 강화되었음을 확인했습니다.
- FIX-02: 적용 완료. Context 최소화 및 Task/Verification 원문 전체 주입 제거 구현을 확인했습니다.
- FIX-03: 적용 완료. `cli.py`에서 `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE` 환경변수를 검사하여 재귀 실행을 방지하는 가드가 정상 동작함을 확인했습니다.
- FIX-04: 적용 완료. `runner.py`에서 실행 시도 탐지 시 `review_agent_attempted_execution` 실패 카테고리가 할당되는 것을 확인했습니다.
- FIX-05: 적용 완료. `test_agent_workflow_runner.py`에 실제 실패 응답에 대한 회귀 테스트 케이스가 추가되었습니다.
- FIX-06: 적용 완료. Prompt 생성 시 예상 heading을 상하단에 명시하고 검증하는 로직을 확인했습니다.
- FIX-07: 적용 완료. 외부 실행 전 prompt 크기, 문자 수, 바이트 크기 및 context 요약을 CLI에서 출력하도록 구현되었습니다.
- FIX-08: 적용 완료. `build_agent_argv`를 통해 `--sandbox` 옵션이 인자로 전달되어 `agy` 실행 시 tool/shell이 비활성화되도록 조치되었습니다.
- FIX-09: human-verification pending 상태. 본 항목은 `human-verification` 분류에 속하며 현재 대기 중입니다. 이번 Re-review 1이 PASS로 완료된 후 사용자가 최종적으로 Antigravity 검증을 확인함으로써 최종 완료 처리됩니다.
- FIX-10: 적용 완료. `cli.py` 내 `normalize_approved_fixes` 호출을 통해 Approved Fixes 목록 기반 체크리스트가 자동 생성되는 것을 확인했습니다.
- FIX-11: 적용 완료. `runner.py`에서 `agy --print` 명령 인자의 순서가 CLI 계약에 맞게 수정되었습니다.
- FIX-12: 적용 완료. 단일 Markdown bullet 표현에 대한 정규화 처리를 확인했습니다.
- FIX-13: 적용 완료. 경로 언급만 있는 경우는 오탐으로 분류하지 않고 실제 실행/대기 의도를 가진 키워드 패턴만 감지하도록 검증 방식이 정규화되었습니다.
- FIX-14: 적용 완료. Review scalar 값의 종결부호 정규화 처리를 확인했습니다.
- FIX-15: 적용 완료. Integration Review 완료 후 최상위 Review 요약이 정상 반영되는 구조를 확인했습니다.
- FIX-16: 적용 완료. `antigravity-review-unit`과 `antigravity-review`가 개별 action으로 분리되어 검증되는 것을 확인했습니다.
- FIX-17: 적용 완료. Re-review prompt 생성 시 개별 Approved Fix ID와 상태를 검증하도록 템플릿과 로직이 강화되었습니다.

### Verification Evidence
- Verification Status: passed
- pytest: 339 passed
- unittest: 339 passed
- docs/verification/fix-antigravity-review-automation.md에 기록된 테스트 실행 결과 확인 완료.

### New Problems Found
- 없음.

### Required Fixes Before PR
- 없음.

### Verdict
- PASS
