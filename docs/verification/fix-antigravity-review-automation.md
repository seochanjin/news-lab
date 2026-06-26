# Verification: Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## Verification Status

passed

## Verification Scope

Antigravity Review workflow의 다음 기능을 구현하고 검증했다.

- Task의 Implementation Units 파싱
- Review 문서의 `Unit Review Status` 자동 생성 및 보존
- 구현 완료됐지만 아직 Review하지 않은 다음 UNIT 탐지
- UNIT별 구조화된 Review Context와 Prompt 생성
- `agy --print` 기반 비대화형 Antigravity 실행
- Review 응답 검증
- Append-only Review History 기록
- `PASS` Verdict에 따른 UNIT Review Status 갱신
- Approved Fixes, Verification, Review History 파싱
- Re-review 번호, FIX 상태와 최신 테스트 수의 모순 검증
- Agent의 Review 파일 직접 변경 복구
- 재귀 실행과 명령 실행 시도 차단
- UNIT-08 Integration Review 완료 시 상단 Summary placeholder 갱신
- `antigravity-review-unit`과 최종 `antigravity-review` action 분리
- `human-verification` FIX가 pending이어도 Re-review 진입을 차단하지 않는 분류

실제 외부 Antigravity Review를 통해 UNIT-01부터 UNIT-08까지 모두 `PASS`가
반영되는 것을 확인했다. 초기 구현 단계에서는 하나의 `antigravity-review`
action이 UNIT Review, Integration Review, Re-review와 일반 Review를 모두 자동
선택했으나, FIX-16 이후 현재 계약은 다음 두 action을 명시적으로 분리한다.

```text
antigravity-review-unit
antigravity-review
```

Application, DB, K3s와 dependency 영역은 변경하지 않는다.

---

## Commands Run

### 1. 기존 Antigravity Review 실행 경로 조사

Command:

```bash
scripts/agent_next_step.sh status
scripts/agent_run.sh antigravity-review --preview
```

Result:

- 기존 Review 실행이 전체 Verification `pending` 상태에 의해 차단되는 사례를
  확인했다.
- UNIT별 Review에서는 전체 Task Verification과 선택 UNIT의 검증 근거를
  구분해야 함을 확인했다.

Status: passed

### 2. 기존 Re-review 상태 모순 수용 사례 재현

Command:

```bash
python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from scripts.agent_workflow.review_validation import validate_review_file
from tests.test_agent_review_validation import complete_review

sections = (
    "Existing Problems Status",
    "Approved Fixes Verification",
    "Verification Evidence",
    "New Problems Found",
    "Required Fixes Before PR",
)

with TemporaryDirectory() as directory:
    path = Path(directory) / "review.md"
    stale = complete_review() + "\n## Re-review 2\n"

    for section in sections:
        body = (
            "승인된 수정 항목이 없습니다. 261 passed"
            if section in {
                "Approved Fixes Verification",
                "Verification Evidence",
            }
            else "없음"
        )
        stale += f"\n### {section}\n\n{body}\n"

    stale += "\n### Verdict\n\nAPPROVED\n"
    path.write_text(stale, encoding="utf-8")

    result = validate_review_file(path)
    print(f"status={result.status}")
    print(f"completed={result.completed}")
    print(f"verdict={result.verdict}")
PY
```

Result:

- 오래된 Re-review 번호와 테스트 수를 사용한 문서가 기존 Validator를 통과하는
  사례를 재현했다.
- Re-review 번호, Approved Fixes와 최신 Verification 수치를 하네스에서
  계산하고 검증해야 함을 확인했다.

Status: passed

### 3. UNIT Parser와 Review Status 생성 검증

Command:

```bash
python -m pytest \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_task_parser.py \
  -v
```

Result:

- Task의 UNIT ID, 제목, 순서와 구현 완료 상태를 파싱하는 동작을 검증했다.
- Review 파일이 없거나 Status section이 없을 때 Task 기준
  `Unit Review Status`를 생성하는 동작을 검증했다.
- 기존 Review Status와 Task의 UNIT ID, 제목 또는 순서가 다르면 파일을
  변경하지 않고 실패하는 동작을 검증했다.
- fenced code 내부의 UNIT 예시를 실제 UNIT으로 오인하지 않는 회귀 테스트가
  통과했다.

Status: passed

### 4. Review 대상 선택과 Context 생성 검증

Command:

```bash
python -m pytest \
  tests/test_agent_review_context.py \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_task_parser.py \
  -v
```

Result:

- Task에서 구현 완료된 `[x]` UNIT 중 Review Status가 `[ ]`인 가장 앞 UNIT을
  선택하는 동작을 검증했다.
- 선택 UNIT, 선행 UNIT 계약, Scope, Do not change, Acceptance Criteria,
  Verification, 변경 파일과 제한된 Git diff가 Context에 포함됨을 확인했다.
- `.env`, key, credential, kubeconfig, secret, binary와 대용량 파일 본문을
  제외하는 동작을 검증했다.

Status: passed

### 5. Review Prompt와 비대화형 실행 경로 검증

Command:

```bash
python -m pytest \
  tests/test_agent_review_prompt.py \
  tests/test_agent_review_context.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_cli.py \
  tests/test_agent_workflow_runner.py \
  -v
```

Result:

- 선택 UNIT과 Integration Review용 Prompt 구조를 검증했다.
- Prompt가 Shell, Agent, 테스트와 Script 실행을 금지하고 제공된 Context만
  검토하도록 지시함을 확인했다.
- 정확한 예상 Heading을 Prompt 시작과 끝에 반복하는 계약을 확인했다.
- Fake `agy`를 통해 Prompt, stdout, stderr, response와 result metadata가
  `.agent-runs`에 저장되는 경로를 검증했다.

Status: passed

### 6. `agy --print` 실제 CLI 인자 계약 확인

Command:

```bash
agy --print "반드시 OK 한 단어만 출력해라." \
  --sandbox \
  --print-timeout 30s
```

Result:

- 다음 순서에서 Prompt가 정상 사용자 요청으로 전달됨을 확인했다.

```text
agy --print <prompt> --sandbox --print-timeout <timeout>
```

- 기존 순서에서는 `--sandbox`가 사용자 Prompt로 소비되는 문제가 있었다.
- Adapter와 Fake CLI 통합 테스트를 실제 인자 순서에 맞게 수정했다.

Status: passed

### 7. Review 응답 Validator와 Writer 검증

Command:

```bash
python -m pytest \
  tests/test_agent_review_validator.py \
  tests/test_agent_review_writer.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- UNIT 및 Integration Review의 Heading, 필수 Section, Section 순서, 본문과
  허용 Verdict를 검증했다.
- 실제 문제가 있으면 `REVIEW-<UNIT>-NN` checklist를 요구함을 확인했다.
- 검증된 Review section만 기존 이력 끝에 append함을 확인했다.
- 중복 응답, 잘린 응답, 대상 불일치와 Agent 직접 파일 수정 시 기존 Review
  bytes를 보존함을 확인했다.

Status: passed

### 8. Verdict 기반 UNIT Review Status 갱신 검증

Command:

```bash
python -m pytest \
  tests/test_agent_review_writer.py \
  tests/test_agent_workflow_runner.py \
  -v
```

Result:

- `PASS`인 경우에만 선택 UNIT Review Status가 `[x]`로 변경됨을 확인했다.
- `CHANGES REQUIRED`와 `BLOCKED`에서는 기존 `[ ]` 상태가 유지됨을 확인했다.
- Status 갱신과 Review section append가 하나의 원자적 파일 교체로 처리됨을
  확인했다.

Status: passed

### 9. Approved Fixes와 Re-review Evidence 검증

Command:

```bash
python -m pytest \
  tests/test_agent_fix_parser.py \
  tests/test_agent_review_evidence.py \
  tests/test_agent_review_context.py \
  tests/test_agent_review_prompt.py \
  tests/test_agent_review_validator.py \
  tests/test_agent_review_writer.py \
  -v
```

Result:

- Approved Fixes의 ID, 제목, 체크 상태와 상세 Heading 정합성을 검증했다.
- 중복 FIX, 번호 누락, 제목 불일치와 비정상 Heading을 거부함을 확인했다.
- Verification에서 과거 테스트 수와 최신 성공한 전체 테스트 수를 구분함을
  확인했다.
- 다음 Re-review 번호를 기존 Review History에서 계산함을 확인했다.
- 계산된 Re-review 번호, 현재 FIX 상태와 최신 테스트 수가 다른 응답을
  거부함을 확인했다.

Status: passed

### 10. 실행 시도와 재귀 실행 차단 검증

Command:

```bash
NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE=1 \
scripts/agent_run.sh antigravity-review --yes
```

Result:

- 활성 Antigravity Review 하위 process에서 재귀 실행이 즉시 차단됐다.
- `agy`와 Writer는 실행되지 않았다.
- Review 파일은 변경되지 않았다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- `I am running`, `I will run`, `I will wait`,
  `in the background` 등의 실행·대기 의도 문구가
  `review_agent_attempted_execution`으로 분류됨을 확인했다.
- 정상 Review 본문의
  `scripts/agent_run.sh antigravity-review` 경로 인용은 실행 시도로
  오탐하지 않음을 확인했다.

Status: passed

### 11. Markdown scalar 정규화 검증

Command:

```bash
python -m pytest tests/test_agent_review_validator.py -v
```

Result:

- 다음 표현을 동일한 canonical scalar로 처리함을 확인했다.

```text
없음
- 없음
없음.
- 없음.
없음。
- 없음。
```

- `PASS`, `CHANGES REQUIRED`, `BLOCKED`에도 허용된 Markdown bullet과
  종결부호 정규화가 동일하게 적용됨을 확인했다.
- 일반 자연어와 `MAYBE` 같은 허용되지 않은 값은 계속 거부함을 확인했다.

Status: passed

### 12. Integration Review 상단 Summary 갱신 검증

Command:

```bash
python -m pytest tests/test_agent_review_writer.py -v
```

Result:

- UNIT-08 Integration Review가 `PASS`하면 다음 상단 placeholder가
  Integration Review 근거로 갱신됨을 확인했다.

```text
Review Summary
Problems Found
Required Fixes Before PR
Optional Improvements
Suggested Test Commands
Risk Notes
```

- 상단 placeholder 갱신, UNIT-08 Status 완료와 Integration Review append가
  하나의 Writer 처리로 반영됨을 확인했다.
- Summary 영역에 기존 내용이 있으면 덮어쓰지 않고 기존 bytes를 보존하며
  실패함을 확인했다.

Status: passed

### 13. 전체 Agent Workflow 회귀

Command:

```bash
python -m pytest tests/test_agent_*.py -q
```

Result:

- 최종 FIX-15 적용 기준 120개 테스트와 41개 subtest가 모두 통과했다.

Status: passed

### 14. 전체 Repository 회귀

Command:

```bash
python -m pytest
python -m unittest discover -s tests
```

Result:

- 최종 FIX-15 적용 기준 pytest 329개가 통과했다.
- unittest 329개가 통과했다.
- 테스트가 의도적으로 검증하는 argparse 오류 메시지와 provider 실패 log가
  출력됐지만 최종 결과는 `OK`였다.

Status: passed

### 15. 정적 검사

Command:

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
```

Result:

- `scripts`와 `tests` 전체가 오류 없이 compile됐다.
- Shell script 문법 검사가 통과했다.
- tracked diff whitespace 검사가 통과했다.

Status: passed

### 16. 변경 금지 영역 확인

Command:

```bash
git diff -- app db k8s requirements.txt
```

Result:

- 출력이 없었다.
- Application, DB, K3s manifest와 dependency 변경은 없었다.

Status: passed

### 17. 실제 외부 UNIT Review 실행

Command:

```bash
scripts/agent_run.sh antigravity-review
```

Result:

- 실제 외부 `agy`를 통해 UNIT-01부터 UNIT-08까지 순차 Review를 실행했다.
- 모든 UNIT Review와 UNIT-08 Integration Review가 `PASS`로 검증됐다.
- 각 응답은 검증 후 Review History에 append됐다.
- UNIT-01부터 UNIT-08까지 Review Status가 모두 `[x]`로 갱신됐다.
- UNIT-08 Integration Review에서 전체 Acceptance Criteria와 선행 UNIT 계약,
  Security, Scope, Verification 및 문서 변경을 검토했다.

Status: passed

### 18. FIX-17 Re-review Prompt와 Validator 보강 검증

Command:

```bash
python -m pytest tests/test_agent_review_evidence.py tests/test_agent_review_prompt.py tests/test_agent_review_validator.py -v
```

Result:

- 27개 테스트와 11개 subtest가 통과했다.
- Re-review Prompt가 FIX별 출력 골격을 생성하고 pending `human-verification`
  상태를 요구함을 확인했다.
- Validator가 범위 표현만 있는 응답과 pending `human-verification`을 완료로
  표현한 응답을 거부함을 확인했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_review_evidence.py \
  tests/test_agent_review_context.py \
  tests/test_agent_review_prompt.py \
  tests/test_agent_review_validator.py \
  tests/test_agent_review_writer.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 77개 테스트와 22개 subtest가 통과했다.
- FIX-17 적용 범위의 prompt, evidence, validator, writer, runner와 CLI 회귀가
  통과했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_*.py -v
```

Result:

- 129개 Agent workflow 테스트와 41개 subtest가 통과했다.

Status: passed

Command:

```bash
python -m pytest
```

Result:

- 전체 Repository pytest 339 passed.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 unittest 339 passed.
- argparse 오류 메시지와 provider 실패 log는 해당 테스트가 의도적으로 검증하는
  출력이며 최종 결과는 `OK`였다.

Status: passed

Command:

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
git diff -- app db k8s requirements.txt
```

Result:

- `scripts`와 `tests` 전체 compileall이 통과했다.
- Shell script 문법 검사가 통과했다.
- `git diff --check` 출력이 없었다.
- Application, DB, K3s manifest와 dependency 변경 diff가 없었다.

Status: passed

Command:

```bash
python - <<'PY'
from scripts.agent_workflow.approved_fixes import normalize_approved_fixes

result = normalize_approved_fixes(
    "docs/fixes/fix-antigravity-review-automation-approved-fixes.md"
)

print(f"created={result.created}")
print(f"pending={[fix.identifier for fix in result.fixes if not fix.checked]}")
PY
```

Result:

- FIX-17 체크 전 결과:

```text
created=False
pending=['FIX-09', 'FIX-17']
```

- FIX-17 적용 후 결과:

```text
created=False
pending=['FIX-09']
```

Status: passed

## FIX-19 ~ FIX-23 Verification

Command:

```bash
python -m pytest \
  tests/test_agent_review_context.py \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  -v
```

Result:

- 첫 실행은 56개 테스트 통과, 1개 테스트 실패였다.
- 실패 원인은 새로 추가한
  `test_review_body_can_quote_previous_execution_attempt_response` 테스트 fixture의
  지역 변수 `review` 누락이었다.
- 기능 코드 실패가 아니라 테스트 코드 오류였으며, fixture를 수정한 뒤 같은
  명령을 재실행했다.

Status: failed

Command:

```bash
python -m pytest \
  tests/test_agent_review_context.py \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  -v
```

Result:

- 58개 테스트와 12개 subtest가 통과했다.
- pending `human-verification`만 남은 상태의 Re-review 선택과 pending
  implementation FIX 차단을 확인했다.
- tracked·untracked 민감 경로와 changed files가 `<sensitive-path-redacted>`로
  대체되고 원본 경로와 민감 본문이 Context에 포함되지 않음을 확인했다.
- 민감 파일 rename diff의 old/new 경로가 원본 경로 대신
  `<sensitive-path-redacted>`로 대체됨을 확인했다.
- Unit Review Status 초기 생성의 원자적 replace 실패 시 기존 Review bytes가
  보존됨을 확인했다.
- Expected heading 뒤 Review 본문에서 과거 실행 시도 문구를 인용해도
  `review_agent_attempted_execution`으로 오탐하지 않음을 확인했다.
- 최신 Review 실패 로그가 과거 completed Review보다 우선해 다음 action을
  차단하고, 후속 성공 로그가 실패 gate를 해제함을 확인했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_review_docs.py tests/test_agent_fix_parser.py -v
```

Result:

- Approved Fixes checklist 완료 처리 후 9개 문서·FIX parser 테스트와 15개
  subtest가 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/agent_workflow \
  tests/test_agent_review_context.py \
  tests/test_agent_review_unit_parser.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py
```

Result:

- 변경한 Agent workflow 모듈과 관련 테스트 파일 compileall이 통과했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_*.py -v
```

Result:

- 139개 Agent workflow 테스트와 51개 subtest가 통과했다.

Status: passed

Command:

```bash
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
```

Result:

- Shell script 문법 검사가 통과했다.
- `git diff --check` 출력이 없었다.

Status: passed

Command:

```bash
python -m compileall scripts tests
git diff -- app db k8s requirements.txt
```

Result:

- `scripts`와 `tests` 전체 compileall이 통과했다.
- Application, DB, K3s manifest와 dependency 변경 diff가 없었다.

Status: passed

Command:

```bash
python -m pytest
```

Result:

- 전체 Repository pytest 348개가 통과했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 unittest 348개가 통과했다.
- argparse 오류 메시지와 provider 실패 log는 해당 테스트가 의도적으로 검증하는
  출력이며 최종 결과는 `OK`였다.

Status: passed

Command:

```bash
python - <<'PY'
from scripts.agent_workflow.approved_fixes import normalize_approved_fixes

result = normalize_approved_fixes(
    "docs/fixes/fix-antigravity-review-automation-approved-fixes.md"
)

print(f"created={result.created}")
print(f"pending={[fix.identifier for fix in result.fixes if not fix.checked]}")
PY
```

Result:

```text
created=False
pending=[]
```

Status: passed

Command:

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

Result:

- 첫 실행은 FIX-09를 구현 FIX pending으로 분류해 Re-review 진입을 차단했다.

```text
오류: 미적용 구현 Approved Fix가 있어 Re-review를 실행할 수 없습니다: FIX-09
```

- 원인은 Approved Fixes 문서의 `분류:` 값이 다음 fenced block에 있는 형식을
  parser가 읽지 못한 것이었다.
- parser를 보강한 뒤 같은 dry-run이 통과했고 다음 current-state를 출력했다.

```text
Action: antigravity-review
Resolved review mode: re-review
Expected heading: ## Re-review 1
Approved fixes: 17
Latest pytest passed: 339
Latest unittest passed: 339
```

- 생성 Prompt의 `Approved Fixes Snapshot`과 출력 골격에는 FIX-01부터 FIX-17이
  모두 포함됐고, FIX-09는 `approved, human-verification` 및 pending 완료 조건
  골격으로 표시됐다.
- dry-run은 외부 Agent와 Writer를 실행하지 않았다.

Status: passed

---

## Results

- Task Implementation Units와 Review Status 파싱을 구현했다.
- 구현 완료됐지만 Review하지 않은 가장 앞 UNIT을 결정론적으로 선택한다.
- 선택 UNIT과 관련된 제한된 Context와 Prompt를 자동 생성한다.
- `agy --print <prompt> --sandbox --print-timeout <timeout>` 경로로
  Antigravity를 비대화형 실행한다.
- Review Agent의 재귀 실행, 실행 의도 응답과 Review 파일 직접 변경을
  차단하거나 복구한다.
- 유효한 Review 응답만 Append-only History에 기록한다.
- `PASS`일 때만 선택 UNIT Review Status를 완료 처리한다.
- UNIT-08은 Integration Review로 전체 UNIT 간 계약과 Acceptance Criteria를
  검토한다.
- UNIT-08 Integration Review가 성공하면 상단 Summary placeholder를
  최종 통합 결과로 갱신한다.
- Approved Fixes, 최신 Verification 수치와 Review History를 구조적으로
  파싱한다.
- Re-review 번호, FIX 상태와 최신 테스트 수의 모순을 거부한다.
- Re-review Prompt는 모든 현재 FIX ID를 개별 출력 골격으로 제공하고 pending
  `human-verification` 상태 왜곡을 Validator에서 거부한다.
- 실제 외부 Antigravity 실행을 통해 UNIT-01부터 UNIT-08까지 모두
  `PASS`로 완료됐다.
- Application, DB, K3s와 dependency 영역은 변경하지 않았다.

---

## Manual or Production Verification

### 완료된 수동 검증

- 실제 설치된 `agy`를 사용해 UNIT-01부터 UNIT-08까지 Review를 실행했다.
- 정상 응답 검증, Append-only 기록과 Status 갱신을 확인했다.
- Markdown bullet, 종결부호와 정상 명령 경로 인용의 실제 응답 변형을
  확인하고 Validator 회귀 테스트에 반영했다.

### 남은 수동 검증

- 새 action 분리 후 다음 실제 CLI 동작을 검증해야 한다.

```bash
scripts/agent_run.sh antigravity-review-unit
scripts/agent_run.sh antigravity-review
```

---

## Pending Verification After FIX-17

다음 내용은 FIX-17 적용 직후 실제 외부 Re-review를 실행하기 전의 과거 pending
기록이다. 현재 최종 상태는 아래 `Final Re-review Result`를 따른다.

구현, 자동 테스트, 정적 검사, 변경 범위 검증과 FIX-17 dry-run 검증은 완료됐다.

남아 있는 항목은 실제 외부 Antigravity를 사용하는 수동 검증뿐이다.

- `antigravity-review`의 Re-review mode 실제 외부 실행 확인
- Re-review 응답 검증 및 Review History append 확인
- Re-review `PASS` 후 FIX-09 완료 처리

위 항목은 구현 Verification을 차단하지 않는 `human-verification`이다.
따라서 현재 Verification Status는 `passed`로 처리하고, 실제 외부 실행 결과는
Manual Verification과 FIX-09에 별도로 기록한다.

---

## FIX-16 Verification Required

### Action 등록

다음 action이 CLI와 Shell wrapper에서 인식돼야 한다.

```text
antigravity-review-unit
antigravity-review
```

### UNIT Review action 검증

Command:

```bash
scripts/agent_run.sh antigravity-review-unit --dry-run
```

확인 항목:

- 미검토 UNIT 하나만 선택
- `Resolved review mode: unit`
- `## UNIT Review: UNIT-NN` Heading
- Integration 또는 Re-review로 자동 전환하지 않음
- 실제 Agent와 Writer 미실행

### Integration Review action 검증

모든 UNIT Review가 완료됐지만 Integration Review가 없는 Fixture에서:

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

확인 항목:

- `Resolved review mode: integration`
- 마지막 UNIT과 전체 Acceptance Criteria를 Context에 포함
- Integration Review Heading 사용
- 성공 시 상단 Summary 갱신

### Summary 복구 검증

다음 상태 Fixture를 사용한다.

- UNIT-01부터 UNIT-08까지 `[x]`
- Integration Review 존재
- 상단 Summary placeholder는 비어 있음

기대 결과:

- `antigravity-review`가 Summary 누락을 탐지
- UNIT Review를 다시 실행하지 않음
- 기존 Review History를 훼손하지 않음
- Summary를 채우거나 필요한 최종 Review mode를 선택

### Re-review 검증

다음 상태 Fixture를 사용한다.

- 모든 UNIT Review 완료
- Integration Review 완료
- 상단 Summary 완료
- 코드 변경 Approved Fixes 모두 `[x]`
- Manual Verification만 pending
- Verification에 최신 테스트 결과 존재

기대 결과:

```text
Resolved review mode: re-review
Expected heading: ## Re-review N
```

### Re-review 차단 검증

코드 수정 Approved Fix가 하나라도 `[ ]`이면:

```text
Approved Fixes가 모두 적용되지 않아 Re-review를 실행할 수 없습니다.
```

### General Review 검증

Implementation Units가 없는 Task에서:

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

기대 결과:

```text
Resolved review mode: general
```

### 전체 회귀

```bash
python -m pytest tests/test_agent_*.py -v
python -m pytest
python -m unittest discover -s tests
```

### 정적 검사

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
```

### 변경 금지 영역

```bash
git diff -- app db k8s requirements.txt
```

출력이 없어야 한다.

---

## FIX-16 Commands Run

### 16-1. FIX-16 focused pytest

Command:

```bash
python -m pytest tests/test_agent_review_unit_parser.py tests/test_agent_review_context.py tests/test_agent_review_validator.py tests/test_agent_review_writer.py -v
```

Result:

- 40 passed
- 13 subtests passed

Status: passed

### 16-2. FIX-16 focused unittest

Command:

```bash
python -m unittest tests.test_agent_review_unit_parser tests.test_agent_review_context tests.test_agent_review_validator tests.test_agent_review_writer
```

Result:

- Ran 40 tests
- OK

Status: passed

### 16-3. Agent workflow regression pytest

Command:

```bash
python -m pytest tests/test_agent_*.py -v
```

Result:

- 127 passed
- 41 subtests passed

Status: passed

### 16-4. Python compile check

Command:

```bash
python -m compileall scripts tests
```

Result:

- scripts와 tests compileall 완료
- exit code 0

Status: passed

### 16-5. Shell syntax check

Command:

```bash
bash -n scripts/agent_run.sh && bash -n scripts/agent_next_step.sh
```

Result:

- output 없음
- exit code 0

Status: passed

### 16-6. Diff whitespace check

Command:

```bash
git diff --check
```

Result:

- output 없음
- exit code 0

Status: passed

### 16-7. 금지 영역 diff 확인

Command:

```bash
git diff -- app db k8s requirements.txt
```

Result:

- output 없음
- Application, DB, K8s manifest, dependency 변경 없음

Status: passed

### 16-8. 전체 pytest 회귀

Command:

```bash
python -m pytest
```

Result:

- 336 passed

Status: passed

### 16-9. 전체 unittest 회귀

Command:

```bash
python -m unittest discover -s tests
```

Result:

- Ran 336 tests
- OK

Status: passed

### 16-10. 외부 Antigravity 실제 실행

Command:

```text
미실행
```

Result:

- FIX-16 적용 후 실제 `agy` 기반 `antigravity-review-unit` 및
  `antigravity-review` 실행은 사람이 수행해야 하는 Manual Verification으로
  남겼다.

Status: human-required

### 16-11. CLI 출력 계약 재검증

Command:

```bash
python -m pytest tests/test_agent_review_context.py tests/test_agent_review_prompt.py tests/test_agent_workflow_cli.py -q
```

Result:

- 28 passed

Status: passed

### 16-12. 최종 compile 및 whitespace 재확인

Command:

```bash
python -m compileall scripts tests
git diff --check
```

Result:

- compileall exit code 0
- `git diff --check` output 없음

Status: passed

### 16-13. 최신 Agent 회귀 재실행

Command:

```bash
python -m pytest tests/test_agent_*.py -q
```

Result:

- 127 passed
- 41 subtests passed

Status: passed

### 16-14. 최신 전체 pytest 재실행

Command:

```bash
python -m pytest -q
```

Result:

- 336 passed
- 55 subtests passed

Status: passed

---

## Evidence Notes

- 실제 Re-review 상태 전이 참고 문서:
  - `docs/reviews/feature-three-day-topic-pipeline-antigravity.md`
  - `docs/fixes/feature-three-day-topic-pipeline-approved-fixes.md`
  - `docs/verification/feature-three-day-topic-pipeline.md`
- 실제 외부 UNIT Review 응답은 현재 Branch의 Antigravity Review 문서와
  `.agent-runs` 실행 로그를 근거로 한다.
- Review output만으로 구현을 수정하지 않으며, 수정은 Approved Fixes를 거쳐
  Codex Fix action으로 수행한다.
- 새 action 분리 작업이 완료될 때까지 전체 Verification Status는
  `pending`을 유지한다.

## Final Verification Commands Run

### 18. FIX-16 적용 후 최종 전체 검증

Command:

```bash
python -m pytest -q
```

Result:

- 336개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 336개 테스트가 모두 통과했다.
- 최종 결과는 `OK`였다.

Status: passed

Command:

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
```

Result:

- `scripts`와 `tests` 전체가 오류 없이 compile됐다.
- 두 Shell script의 문법 검사가 통과했다.
- tracked diff whitespace 검사가 출력 없이 통과했다.

Status: passed

Command:

```bash
git diff -- app db k8s requirements.txt
```

Result:

- 출력이 없었다.
- Application, DB, K3s manifest와 dependency 변경이 없음을 확인했다.

Status: passed

## FIX-16 Verification Result

- FIX-16 구현과 당시 로컬 검증을 완료했다.
- `antigravity-review-unit`과 `antigravity-review` action을 분리했다.
- UNIT Review action은 다음 미검토 UNIT 하나만 선택한다.
- 최종 Review action은 Integration, Summary recovery, Re-review 또는
  General Review만 선택한다.
- `human-verification`만 pending인 경우 Re-review 진입을 허용한다.
- 전체 pytest와 unittest 336개가 통과했다.
- Agent workflow 회귀, compile, Shell 문법, whitespace와 변경 금지 영역
  검사가 통과했다.
- 당시 남은 항목은 실제 외부 Antigravity Re-review 실행이었다. 현재 해당
  Re-review는 아래 `Final Re-review Result` 기준으로 완료됐다.

---

## Final Verification Commands Run After FIX-17

### FIX-17 최종 Agent 회귀

Command:

```bash
python -m pytest tests/test_agent_*.py -v
```

Result:

- 130개 Agent workflow 테스트와 41개 subtest가 통과했다.

Status: passed

### FIX-17 최종 전체 pytest

Command:

```bash
python -m pytest
```

Result:

- 전체 Repository pytest 339 passed.

Status: passed

### FIX-17 최종 전체 unittest

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 unittest 339 passed.
- argparse 오류 메시지와 provider 실패 log는 해당 테스트가 의도적으로 검증하는
  출력이며 최종 결과는 `OK`였다.

Status: passed

### FIX-17 정적 검사와 금지 영역 확인

Command:

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
git diff -- app db k8s requirements.txt
```

Result:

- `scripts`와 `tests` 전체 compileall이 통과했다.
- Shell script 문법 검사가 통과했다.
- `git diff --check` 출력이 없었다.
- Application, DB, K3s manifest와 dependency 변경 diff가 없었다.

Status: passed

### FIX-17 Re-review dry-run

Command:

```bash
scripts/agent_run.sh antigravity-review --dry-run
```

Result:

- Re-review mode와 `## Re-review 1` heading을 선택했다.
- Prompt에는 FIX-01부터 FIX-17까지 모두 개별 출력 골격으로 포함됐다.
- FIX-09는 `approved, human-verification` 및 pending 완료 조건 골격으로
  표시됐다.
- dry-run은 외부 Agent와 Writer를 실행하지 않았다.

Status: passed

## Final Verification Result After FIX-17

- FIX-17 구현과 로컬 검증을 완료했다.
- Re-review Prompt는 모든 현재 FIX ID를 개별 출력 골격으로 제공한다.
- Validator는 범위 표현만 있는 응답과 pending `human-verification` 상태 왜곡을
  거부한다.
- FIX-17 직후에는 Approved Fixes checklist에서 FIX-17은 완료됐고 FIX-09만
  pending으로 남았다.
- 이후 실제 외부 Antigravity Re-review 실행과 FIX-09 완료 처리는 아래
  `Final Re-review Result` 기준으로 완료됐다.

## Final Re-review Result

- `antigravity-review`가 `re-review` mode와 `## Re-review 1`을 선택했다.
- Approved Fixes FIX-01부터 FIX-17까지 개별 검증됐다.
- FIX-09는 `human-verification pending` 상태로 정확히 검토됐다.
- 최신 pytest와 unittest는 각각 339개가 통과했다.
- Re-review Verdict는 `PASS`였다.
- Review 응답 검증과 Review History append가 완료됐다.
- Re-review PASS 후 FIX-09와 VERIFY-03, VERIFY-04 완료 상태가
  Approved Fixes 문서에 반영됐다.

## FIX-18 Verification

Command:

```bash
python -m pytest tests/test_agent_review_validation.py tests/test_agent_review_docs.py -v
```

Result:

- 9개 테스트와 15개 subtest가 통과했다.
- 수동 Review validator의 허용 Verdict가 `PASS`, `CHANGES REQUIRED`,
  `BLOCKED`로 정렬됨을 확인했다.
- Review 관련 문서의 action 분리, Verdict 계약과 CodeRabbit artifact 채움
  상태를 확인했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_*.py -v
```

Result:

- 133개 Agent workflow 테스트와 51개 subtest가 통과했다.

Status: passed

Command:

```bash
python -m pytest
```

Result:

- 전체 Repository pytest 342개가 통과했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 unittest 342개가 통과했다.
- argparse 오류 메시지와 provider 실패 log는 해당 테스트가 의도적으로 검증하는
  출력이며 최종 결과는 `OK`였다.

Status: passed

Command:

```bash
python -m compileall scripts tests
bash -n scripts/agent_run.sh scripts/agent_next_step.sh
git diff --check
git diff -- app db k8s requirements.txt
```

Result:

- `scripts`와 `tests` 전체 compileall이 통과했다.
- Shell script 문법 검사가 통과했다.
- `git diff --check` 출력이 없었다.
- Application, DB, K3s manifest와 dependency 변경 diff가 없었다.

Status: passed

Command:

```bash
python - <<'PY'
from scripts.agent_workflow.approved_fixes import normalize_approved_fixes

result = normalize_approved_fixes(
    "docs/fixes/fix-antigravity-review-automation-approved-fixes.md"
)

print(f"created={result.created}")
print(f"pending={[fix.identifier for fix in result.fixes if not fix.checked]}")
PY
```

Result:

```text
created=False
pending=['FIX-19', 'FIX-20', 'FIX-21', 'FIX-22', 'FIX-23']
```

Status: passed
