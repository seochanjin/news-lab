# Task: Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## Goal

현재 Antigravity review workflow는 사용자가 긴 review prompt를 직접 작성해 입력해야 하며, Re-review 과정에서 기존 Review의 과거 상태를 최신 상태로 잘못 해석할 수 있다.

이번 작업의 목표는 Review action별 명령으로 현재 작업 상태를 분석하고, 적절한
Review를 자동 실행하도록 개선하는 것이다. UNIT Review와 최종 Review는
FIX-16에서 분리된 현재 계약을 따른다.

```bash
scripts/agent_run.sh antigravity-review-unit
scripts/agent_run.sh antigravity-review
```

하네스는 Task의 Implementation Units, 기존 Antigravity Review, Approved Fixes, Verification과 현재 Git diff를 분석해 다음 Review 모드를 자동 결정해야 한다.

- UNIT Review (`antigravity-review-unit`)
- 모든 UNIT Review 완료 후 별도 전체 통합 Review (`antigravity-review`)
- Approved Fixes 적용 후 Re-review

Task에 정의된 UNIT 목록을 기준으로 Antigravity Review 파일에 Review Status 체크리스트를 자동 생성한다. 구현이 완료됐지만 아직 Review를 통과하지 않은 다음 UNIT을 선택하고, Antigravity 실행 결과를 같은 Review 파일에 누적한다.

Re-review에서는 Approved Fixes와 최신 Verification 상태를 하네스가 구조적으로 추출해야 한다. 모델 출력이 실제 상태와 충돌하면 Review 파일에 기록하지 않고 실행을 실패시켜야 한다.

최종적으로 사용자가 Review prompt를 직접 생성하거나 복사하지 않아도 다음 과정이 자동으로 수행되어야 한다.

```text
현재 Branch와 Task 탐색
→ Review 모드 결정
→ action별 다음 Review 대상 선택
→ Review Context와 Prompt 생성
→ Antigravity 실행
→ 응답 구조와 상태 검증
→ 기존 Review 파일에 Append
→ PASS 시 UNIT Review 상태 완료
```

## Scope

- `scripts/agent_run.sh antigravity-review-unit`와
  `scripts/agent_run.sh antigravity-review` 실행 경로 추가 또는 기존 경로 개선
- 사용자의 수동 Prompt 입력 없이 Antigravity 실행
- 현재 Git Branch 기준 Task, Review, Verification, Approved Fixes 파일 탐색
- Task의 `Implementation Units` 파싱
- Task에 작성된 UNIT ID, 상태와 제목 보존
- Antigravity Review 파일에 `Unit Review Status` 자동 생성
- Task에서 구현 완료됐지만 Review가 완료되지 않은 다음 UNIT 자동 선택
- UNIT별 Review Context와 Prompt 자동 생성
- UNIT Review 결과를 기존 Antigravity Review 파일에 누적
- UNIT Review 결과가 `PASS`일 때만 Review Status를 `[x]`로 변경
- `CHANGES REQUIRED` 또는 `BLOCKED`이면 `[ ]` 유지
- 모든 UNIT Review가 완료된 뒤 별도 최종 Review action에서 전체 통합 Review 처리
- Approved Fixes의 FIX ID, 완료 여부, 보류·거절 상태 파싱
- Verification에서 최신 테스트와 정적 검사 결과 파싱
- 기존 Review History에서 다음 Re-review 번호 계산
- 최초 Review, UNIT Review, 전체 통합 Review, Re-review 모드 구분
- Antigravity 응답 필수 Section 검증
- Antigravity 응답과 현재 Repository 상태 간 모순 검증
- 기존 Review 내용을 변경하지 않는 Append-only Writer
- Antigravity 실행 또는 검증 실패 시 Review 파일 미변경
- 동일 UNIT Review의 중복 기록 방지
- `--dry-run` 또는 이에 준하는 Prompt·Context 확인 기능
- 기존 수동 Prompt 생성 방식은 디버깅 및 Fallback 용도로 유지 가능
- 기존 Agent workflow 관련 문서와 테스트 갱신

UNIT Review는 해당 UNIT의 변경 범위만 검토하는 짧은 Review로 구성한다.

검토 범위는 다음과 같다.

- 해당 UNIT 요구사항
- 해당 UNIT 관련 Git diff
- 해당 UNIT 집중 테스트 결과
- `Do not change` 영역 침범 여부
- 이전 UNIT 계약 회귀 여부
- 코드와 테스트의 문서화 정책

현재 계약에서 마지막 UNIT Review는 해당 UNIT의 Review 통과만 의미한다. 전체
통합 Review는 모든 UNIT Review가 완료된 뒤 `antigravity-review`에서 별도로
수행한다.

검토 범위는 다음과 같다.

- 전체 Acceptance Criteria
- UNIT 사이의 데이터 및 호출 계약
- Migration, Repository, Service, API, CLI, Manifest 연결
- 전체 테스트와 정적 검사
- 문서와 실제 구현의 일치 여부
- Scope creep
- 사람에게 남겨진 운영 검증 항목

Re-review는 다음 정보를 우선 사용한다.

1. 현재 Git diff
2. Approved Fixes
3. 최신 Verification
4. Task
5. 기존 Review History
6. CodeRabbit Review가 존재할 경우 보조 Context

과거 Review의 결론이나 중간 테스트 결과를 현재 상태보다 우선해서는 안 된다.

## Do not change

- 기존 Codex UNIT 구현 workflow의 WIP 1 정책
- Task의 구현 완료 체크박스 의미
- Approved Fixes의 사람 승인 절차
- CodeRabbit Review 처리 방식과 파일 계약
- 기존 Review History의 내용
- 기존 Verification History의 내용
- Git push와 Pull Request Merge의 사람 통제 원칙
- DB Migration 실행의 사람 통제 원칙
- Kubernetes Apply, Delete, Patch, Rollout의 사람 통제 원칙
- Production 배포와 Secret 수정의 사람 통제 원칙
- 기존 Daily Topic과 3일 Topic의 Application 기능
- K3s, Supabase 또는 외부 Infrastructure 설정
- 실제 Production 환경에 영향을 주는 명령 실행

Antigravity가 Review 과정에서 Application 코드나 테스트를 직접 수정하게 해서는 안 된다.

Review finding은 자동 수정 승인이 아니다. 수정이 필요하면 기존 Approved Fixes 절차를 사용해야 한다.

## Expected files

실제 Repository 구조를 먼저 조사한 뒤 필요한 파일만 수정하거나 추가한다.

예상 변경 대상:

```text
scripts/agent_run.sh
scripts 또는 scripts/agents 아래의 Antigravity 실행 Adapter
scripts 또는 scripts/agents 아래의 Review Context Builder
scripts 또는 scripts/agents 아래의 Review Parser
scripts 또는 scripts/agents 아래의 Review Output Validator
scripts 또는 scripts/agents 아래의 Append-only Writer
```

예상 테스트 파일:

```text
tests/test_agent_review_unit_parser.py
tests/test_agent_review_context.py
tests/test_agent_review_validator.py
tests/test_agent_review_writer.py
```

실제 기존 테스트 구조가 다르면 기존 명명과 배치 규칙을 따른다.

예상 문서 변경 대상:

```text
README.md
AGENTS.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

모든 문서를 수정할 필요는 없다. Antigravity Review 실행 방법과 상태 전이 계약을 설명하는 기존 문서만 갱신한다.

작업용 자동 생성 문서는 기존 `scripts/new_agent_task.sh` 계약을 따른다.

```text
docs/tasks/
docs/reviews/
docs/fixes/
docs/verification/
docs/pr/
docs/devlog/
```

UNIT별 별도 Review 파일은 만들지 않는다.

브랜치당 기존 Antigravity Review 파일 하나를 사용한다.

```text
docs/reviews/<safe-branch>-antigravity.md
```

## DB changes

없음.

Database Migration, Schema, Table, Constraint, Index와 운영 데이터는 변경하지 않는다.

## API changes

없음.

FastAPI Route, Request·Response Schema와 기존 Public API 계약은 변경하지 않는다.

이번 작업에서 변경되는 인터페이스는 내부 Agent CLI뿐이다.

목표 명령:

```bash
scripts/agent_run.sh antigravity-review-unit
scripts/agent_run.sh antigravity-review
```

Context와 Prompt만 확인하는 기능도 제공한다.

예시:

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

기존 CLI 구조상 다른 Option 이름이 더 적합하면 기존 Convention을 따른다.

기본 명령은 다음 동작을 포함해야 한다.

```text
상태 파싱
→ Prompt 생성
→ Antigravity 실제 실행
→ 응답 검증
→ Review 파일 반영
```

## Test commands

실제 추가된 테스트 파일에 맞춰 집중 테스트를 실행한다.

```bash
python -m pytest \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_review_context.py \
  tests/test_agent_review_validator.py \
  tests/test_agent_review_writer.py \
  -v
```

```bash
python -m unittest \
  tests.test_agent_review_unit_parser \
  tests.test_agent_review_context \
  tests.test_agent_review_validator \
  tests.test_agent_review_writer
```

기존 Agent workflow 테스트가 존재하면 함께 실행한다.

```bash
python -m pytest tests/test_agent_*.py -v
```

Python 정적 검증:

```bash
python -m compileall scripts tests
```

Shell Script가 변경되면 문법을 검사한다.

```bash
bash -n scripts/agent_run.sh
```

변경된 다른 Shell Script도 동일하게 검사한다.

Repository 전체 회귀 테스트는 마지막 UNIT 구현과 별도 Integration Review 전후에
실행한다.

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

Diff 형식 검사:

```bash
git diff --check
```

수동 실행 없이 Context가 올바르게 생성되는지도 확인한다.

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

테스트에서는 실제 Antigravity 호출을 Stub 또는 Fake Process로 대체한다. 외부 Agent 호출에 테스트 결과가 의존하지 않도록 한다.

## Acceptance criteria

- 사용자가 긴 Antigravity Review Prompt를 직접 작성하지 않아도 된다.
- `scripts/agent_run.sh antigravity-review-unit`와
  `scripts/agent_run.sh antigravity-review`가 현재 Branch를 자동으로 확인한다.
- 현재 Branch에 해당하는 Task, Review, Verification과 Approved Fixes 파일을 자동으로 탐색한다.
- Task의 `Implementation Units`에서 UNIT ID, 상태와 제목을 정확히 파싱한다.
- Task에 작성된 UNIT 제목을 축약하거나 바꾸지 않는다.
- Review 파일이 없으면 Task UNIT 목록으로 `Unit Review Status`를 자동 생성한다.
- Review 파일이 이미 있으면 기존 상태와 이력을 보존한다.
- Task에서 `[x]`이고 Review Status에서 `[ ]`인 가장 앞선 UNIT을 다음 Review 대상으로 선택한다.
- 사용자가 Review 대상 UNIT을 직접 지정하지 않아도 된다.
- UNIT Review Context와 Prompt를 자동으로 생성한다.
- 기본 명령에서 Antigravity를 실제로 실행한다.
- Antigravity는 새 Review Section만 반환한다.
- 하네스는 Antigravity에게 Review 파일 전체를 다시 작성하게 하지 않는다.
- 검증된 Review Section만 기존 Review 파일 끝에 추가한다.
- UNIT Review Verdict가 `PASS`인 경우에만 해당 Review Status를 `[x]`로 변경한다.
- `CHANGES REQUIRED` 또는 `BLOCKED`인 경우 Review Status를 `[ ]`로 유지한다.
- Review에서 발견한 문제는 `- [ ] REVIEW-<UNIT>-<번호>` 형식으로 추적할 수 있다.
- 동일 UNIT의 동일 Review Section이 중복으로 추가되지 않는다.
- 마지막 UNIT Review는 UNIT Review로 완료되고, 모든 UNIT Review 완료 후 별도
  Integration Review가 실행된다.
- Approved Fixes의 FIX 개수와 상태를 하네스가 직접 파싱한다.
- Verification의 최신 결과를 과거 중간 결과와 구분한다.
- 기존 Re-review 번호를 읽고 다음 번호를 자동으로 계산한다.
- Approved Fixes가 존재하는데 “승인된 수정 없음”이라고 작성한 출력을 거부한다.
- 최신 테스트 결과와 다른 과거 수치를 현재 최종 결과로 작성한 출력을 거부한다.
- 계산된 Re-review 번호와 다른 Heading을 작성한 출력을 거부한다.
- 선택된 UNIT과 다른 UNIT Review Heading을 작성한 출력을 거부한다.
- 필수 Review Section이 누락된 출력을 거부한다.
- Antigravity 실행 실패, 응답 잘림 또는 Validation 실패 시 Review 파일을 수정하지 않는다.
- 기존 Review와 Verification History를 삭제하거나 덮어쓰지 않는다.
- `--dry-run`으로 선택된 Mode, UNIT, FIX 상태, Verification과 생성 Prompt를 확인할 수 있다.
- 기존 수동 Prompt 방식은 필요할 경우 Fallback으로 사용할 수 있다.
- 실제 Application, DB, API와 K3s 설정은 변경하지 않는다.
- 집중 테스트와 기존 Agent workflow 회귀 테스트가 통과한다.
- 전체 Repository 테스트가 통과한다.
- `compileall`, Shell 문법 검사와 `git diff --check`가 통과한다.
- 변경된 Python 코드와 테스트에는 필요한 한글 Docstring을 작성한다.
- 실행 방식과 실패 처리 계약을 기존 Agent 문서에 기록한다.

다음 실제 실패 사례를 회귀 테스트로 포함한다.

```text
기존 Review:
- Approved Fixes 없음
- 261 passed
- Re-review 2까지 존재

현재 Approved Fixes:
- FIX-01부터 FIX-09까지 적용 완료

현재 Verification:
- 최신 전체 테스트 265 passed

기대 결과:
- Mode는 Re-review
- 다음 Heading은 Re-review 3
- Approved Fix 수는 9
- 최신 테스트 수는 265
```

다음 출력은 Validation 실패로 처리한다.

```text
승인된 수정 항목이 없습니다.
현재 최종 테스트는 261 passed입니다.
## Re-review 2
```

## Notes

- Review 파일 수 증가를 막기 위해 UNIT별 별도 파일을 생성하지 않는다.
- 모든 UNIT Review와 Re-review는 브랜치당 하나의 Antigravity Review 파일에 누적한다.
- `Unit Review Status`는 사용자가 직접 작성하지 않는다.
- Antigravity가 UNIT 목록을 자유롭게 생성하게 하지 않는다.
- UNIT 목록과 체크박스는 Task를 기준으로 하네스가 결정론적으로 생성한다.
- Antigravity는 Review 판단과 Review 본문 작성만 담당한다.
- Review Status의 `[x]`는 해당 UNIT의 Review Gate 통과를 의미한다.
- Task의 `[x]`는 해당 UNIT 구현 완료를 의미한다.
- 두 체크박스는 서로 다른 상태다.
- UNIT Review는 국소 결함을 조기에 발견하기 위한 짧은 검토다.
- 마지막 UNIT은 UNIT Review로만 완료되며 전체 통합 Review는 별도
  `antigravity-review` action이 수행한다.
- Approved Fixes는 계속 별도 문서에서 사람이 승인한다.
- Review finding을 발견했다고 자동으로 Codex Fix를 실행하지 않는다.
- Review 결과가 `CHANGES REQUIRED`이면 Workflow를 중단하고 사람의 판단을 기다린다.
- CodeRabbit Review는 필수 Source of Truth가 아니다.
- CodeRabbit 파일이 존재하면 보조 Context로만 사용할 수 있다.
- 현재 상태의 우선순위는 Git diff, Approved Fixes, 최신 Verification, Task, Review History 순서다.
- 오래된 Review 문구나 중간 테스트 수치가 최신 상태를 덮어쓰지 못하게 해야 한다.
- 구조적 Parser와 Output Validator를 통해 모델의 해석 오류를 방어한다.
- Antigravity CLI의 실제 명령과 입출력 방식은 UNIT-01에서 기존 구현을 조사한 뒤 확정한다.
- 현재 Repository Convention을 무시하고 새로운 Framework나 과도한 의존성을 도입하지 않는다.
- Review 자동화 자체가 복잡한 범용 Workflow Engine으로 확대되지 않도록 범위를 제한한다.

### UNIT-01 분석 결과

#### 현재 실행 경로

현재 `scripts/agent_run.sh antigravity-review` 경로는 다음과 같다.

```text
scripts/agent_run.sh
→ scripts.agent_workflow.cli
→ load_state()
→ validate_action()
→ build_prompt()
→ resolve_agent()
→ run_agent()
→ validate_review_file()
```

- `validate_action()`은 현재 branch의 Verification 상태가 `pending` 또는
  `failed`이면 Review 실행을 차단한다. 따라서 Task 전체 Verification을
  `pending`으로 유지하는 현재 WIP 1 방식에서는 UNIT 완료 직후 Review를 실행할
  수 없다.
- `resolve_agent()`는 `agy` 설치 후보만 탐지하고 Gemini CLI를 fallback으로
  사용하지 않는다. 현재 검증된 비대화형 Antigravity adapter가 없으므로
  `automatic_execution_supported=False`와 수동 fallback을 반환한다.
- `run_agent()`는 자동 실행이 지원되는 경우에만 subprocess를 시작한다. Review
  전후 파일 byte 비교와 최종 Markdown 구조 검증은 수행하지만, 기존 내용을
  전면 재작성했는지, 같은 Review를 중복 추가했는지, 현재 상태와 본문이
  모순되는지는 검사하지 않는다.
- 현재 실제 사용 가능한 경로는
  `scripts/agent_next_step.sh antigravity-review`로 chat prompt를 만들고,
  `antigravity-review-write` prompt로 모델이 Review 파일을 직접 수정하게 하는
  두 단계 수동 흐름이다.

#### 현재 Parser와 상태 모델의 한계

- `task_parser.py`는 Task의 UNIT ID, 제목과 구현 완료 상태를 순서대로 파싱하지만
  별도의 Unit Review Status는 관리하지 않는다.
- `state.py`의 Approved Fixes 판정은 `Approved Fixes` section에 unchecked
  checklist가 있으면 `approved`, checked checklist가 있으면 `applied`로
  축약한다. FIX ID, 개수, 완료·보류·거절 상태는 추출하지 않는다.
- Verification 판정은 `Verification Status`의 `pending`, `passed`, `failed`
  값만 읽는다. 최신 command, 테스트 수와 과거 결과의 선후 관계는 추출하지
  않는다.
- `review_validation.py`는 최초 Review와 최신 Re-review의 필수 heading, 본문과
  허용 Verdict만 검증한다. 다음 Re-review 번호, 선택된 UNIT, FIX 개수, 최신
  테스트 수와 기존 section 중복 여부는 검증하지 않는다.
- `prompt_builder.py`와 수동 Review prompt는 관련 문서를 읽고 현재 diff와
  대조하라고 지시하지만, 하네스가 계산한 구조화된 current-state snapshot을
  제공하지 않는다.

#### Re-review 실패 사례

회귀 사례는 `feature/three-day-topic-pipeline` workflow artifact에서 확인했다.

```text
과거 Review History:
- Re-review 2까지 존재
- Approved Fixes 없음
- 전체 테스트 261 passed

현재 Approved Fixes:
- FIX-01부터 FIX-09까지 적용 완료

현재 Verification:
- 전체 pytest 265 passed
- 전체 unittest 265 passed
```

기존 Re-review 1과 Re-review 2에는 당시 상태인 “승인된 수정 항목 없음”과
`261 passed`가 기록되어 있다. 이후 Re-review 3은 현재 Approved Fixes 9개와
`265 passed`를 반영했다. 문제는 현재 validator가 Re-review 2 heading과 오래된
FIX·테스트 내용을 가진 새 출력도 필수 section과 허용 Verdict만 있으면
`completed`로 승인한다는 점이다.

실패 원인은 모델이 과거 기록과 현재 상태를 구분하도록 prompt에만 의존하고,
다음 값을 하네스가 결정론적으로 계산·검증하지 않는 데 있다.

- Review mode와 선택된 UNIT
- 다음 Re-review 번호
- Approved Fixes의 ID, 개수와 상태
- Verification의 최신 실행 결과
- append 대상인 새 Review section의 fingerprint

#### 후속 UNIT 구현 경계

- Task 구현 완료 checkbox와 Unit Review Status를 별도 상태로 유지한다.
- Review mode, 다음 UNIT, 다음 Re-review 번호, FIX 상태와 최신 Verification은
  모델이 아니라 하네스가 구조적으로 계산한다.
- Antigravity에는 전체 파일 재작성 대신 새 Review section만 반환하게 한다.
- 모델 출력은 임시 결과로 받은 뒤 heading, 필수 section, 선택 UNIT, 번호,
  current-state snapshot과의 모순 및 중복을 검증한다.
- 모든 검증을 통과한 경우에만 기존 Review History를 보존한 append-only
  writer로 반영한다.
- UNIT Review를 허용하기 위해 Task 전체 `Verification Status`만으로 실행을
  차단하지 않고, 선택된 UNIT에 필요한 최신 검증 evidence를 별도로 판단해야
  한다.

UNIT-01에서 Application, DB, API, K3s, Review 파일과 Agent 실행 코드는
변경하지 않았다. 위 분석을 후속 UNIT의 구현 계약으로 사용한다.

## Implementation Units

- [x] UNIT-01: 기존 Antigravity Review 실행 경로와 Re-review 실패 사례 분석
- [x] UNIT-02: Task Implementation Units Parser와 Review Status 자동 생성 구현
- [x] UNIT-03: 다음 UNIT Review 대상 탐지와 구조화된 Review Context 생성 구현
- [x] UNIT-04: Antigravity Review Prompt 자동 생성과 실제 실행 경로 구현
- [x] UNIT-05: UNIT Review 응답 검증과 Append-only Writer 구현
- [x] UNIT-06: UNIT Review Verdict 기반 Review Status 갱신 구현
- [x] UNIT-07: Approved Fixes·최신 Verification·Review History Parser와 모순 검증 구현
- [x] UNIT-08: 전체 Agent Workflow 회귀 테스트와 문서 갱신
