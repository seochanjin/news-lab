# Verification: Antigravity CLI review adapter 전환 및 실패 상태 개선

## Verification Status

passed

## Verification Scope

UNIT-01에서 현재 adapter 탐지·실행 흐름과 로컬 Antigravity 관련 실행 파일을
조사했다. UNIT-02에서 Gemini fallback 제거, Antigravity 실행 후보와 자동 실행
지원 상태 분리, 수동 fallback 반환, subprocess 실패 분류와 실행 기록 필드를
구현하고 workflow 집중 테스트를 수행했다.

UNIT-03에서 review Markdown의 파일 존재, 템플릿 잔존, 필수 section, 실제 본문,
Verdict와 최신 Re-review를 검증하는 전용 모듈을 추가했다. 자동 review는 process
성공과 review 파일 생성·변경·검증을 모두 통과해야 완료로 기록하고, 수동
review는 실행 기록 없이도 동일한 파일 검증을 통과하면 완료로 판정하도록
workflow state를 강화했다.

UNIT-04에서 자동·수동 review 차이, `UNSUPPORTED_CLIENT` 복구, review 완료
조건과 backend·frontend 공통 적용 기준을 workflow 문서에 동기화했다. Task에
명시된 집중 테스트, 전체 pytest·unittest, compileall과 scope diff 검사를 모두
수행했으며 실제 외부 Antigravity process는 실행하지 않았다.

## Commands Run

Command:

```bash
git branch --show-current && git status --short
```

Result:

- 현재 branch는 `fix/antigravity-cli-review-adapter`였다.
- 기존 workflow 문서 변경과 현재 branch용 미추적 문서가 있었다.

Status: passed

## UNIT-03 Commands

Command:

```bash
python -m pytest \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 36개 테스트와 9개 subtest가 모두 통과했다.
- 파일 없음, 빈 파일, heading-only 템플릿, 필수 section·본문·Verdict 누락과
  허용되지 않은 Verdict를 미완성으로 판정했다.
- 세 허용 Verdict와 최신 Re-review 구조를 인식했다.
- 자동 review의 파일 미생성, 미변경, 검증 실패와 정상 완료를 구분했다.
- 수동 review 완료와 자동 실행 실패 후 fix·PR 단계 차단을 검증했다.

Status: passed

Command:

```bash
scripts/agent_next_step.sh status
```

Result:

- 실제 branch review 파일을 `template only`와 `template_only` 검증 상태로
  판정했다.
- 자동 review는 `unavailable`, 실행 상태는 `not started`, 수동 review 필요는
  `yes`로 출력했다.
- 다음 action으로 `antigravity-review-write`와 두 수동 review 명령을 안내했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 43개 테스트와 8개 subtest가 모두 통과했다.
- UNIT-02의 adapter·실패 분류 회귀와 UNIT-03의 review 완료 및 workflow 상태
  판정이 함께 통과했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_review_validation.py -v
```

Result:

- 전용 review 검증 테스트 5개와 3개 subtest가 모두 통과했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/agent_workflow \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py
```

Result:

- 변경한 workflow module과 테스트가 오류 없이 compile됐다.

Status: passed

Command:

```bash
git diff --check
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- tracked diff whitespace 검사는 출력 없이 exit code 0이었다.
- application, Daily Topic pipeline, DB migration과 K3s manifest diff는 없었다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 최종 UNIT-03 집중 검증에서 49개 테스트와 11개 subtest가 모두 통과했다.
- Agent exit code 0이어도 review 파일이 없거나 검증에 실패하면 CLI가 non-zero를
  반환하는 회귀 테스트를 포함한다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/agent_workflow \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py
```

Result:

- 최종 변경 후 workflow module과 테스트가 오류 없이 compile됐다.

Status: passed

Notes:

- 전체 pytest, 전체 unittest와 workflow 문서 동기화는 UNIT-04에서 수행한다.
- 실제 외부 Antigravity process는 실행하지 않았다.

Command:

```bash
for path in docs/tasks/fix-antigravity-cli-review-adapter.md \
  docs/verification/fix-antigravity-cli-review-adapter.md \
  scripts/agent_workflow/review_validation.py \
  tests/test_agent_review_validation.py; do
  git diff --no-index --check /dev/null "$path" >/tmp/no-index-check.out 2>&1
  code=$?
  if [ "$code" -gt 1 ]; then
    cat /tmp/no-index-check.out
    exit "$code"
  fi
  if [ -s /tmp/no-index-check.out ]; then
    cat /tmp/no-index-check.out
    exit 1
  fi
done
```

Result:

- exit code 127로 실패했다.
- zsh의 특수 배열 변수 `path`를 loop 변수로 사용해 command search PATH를
  덮어썼고, loop 내부에서 `cat`을 찾지 못했다.
- 검사 대상 파일의 whitespace 오류를 뜻하는 실패는 아니었다.

Status: failed

Command:

```bash
for file_name in docs/tasks/fix-antigravity-cli-review-adapter.md \
  docs/verification/fix-antigravity-cli-review-adapter.md \
  scripts/agent_workflow/review_validation.py \
  tests/test_agent_review_validation.py; do
  git diff --no-index --check /dev/null "$file_name" \
    >/tmp/no-index-check.out 2>&1
  code=$?
  if [ "$code" -gt 1 ]; then
    /bin/cat /tmp/no-index-check.out
    exit "$code"
  fi
  if [ -s /tmp/no-index-check.out ]; then
    /bin/cat /tmp/no-index-check.out
    exit 1
  fi
done
```

Result:

- 출력 없이 exit code 0이었다.
- 네 미추적 UNIT-03 관련 파일에 whitespace 오류가 없었다.

Status: passed

Command:

```bash
rg -n "antigravity|gemini|adapter|agent_executable|review" \
  scripts/agent_workflow scripts/agent_run.sh scripts/agent_next_step.sh \
  tests docs/agent/antigravity-review.md docs/agent/usage-guide.md | head -n 500
```

Result:

- `gates.py`가 `AGENT_ANTIGRAVITY_BIN`을 stdin adapter로 처리하고, 설정이
  없으면 PATH의 `gemini`를 `Gemini/Antigravity`로 반환한다.
- `runner.py`의 Gemini adapter는 `--prompt <prompt> --approval-mode auto_edit`
  인자를 사용한다.
- 현재 문서는 별도 Antigravity CLI 계약이 확인되지 않았다는 전제에서 Gemini
  CLI 또는 prompt-only 흐름을 안내한다.

Status: passed

## UNIT-04 Commands

Command:

```bash
python -m pytest \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 44개 테스트와 8개 subtest가 모두 통과했다.
- adapter 탐지, 자동 실행 미지원 fallback, 실패 분류, review 파일 완료 판정과
  CLI·상태 회귀를 함께 검증했다.

Status: passed

Command:

```bash
python -m pytest tests/test_agent_review_validation.py -v
```

Result:

- 6개 테스트와 5개 subtest가 모두 통과했다.
- 미완성 review 분류, 세 허용 Verdict와 최신 Re-review 검증을 확인했다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_task_parser.py \
  tests/test_agent_workflow_cli.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  -v
```

Result:

- Agent workflow 전체 49개 테스트와 12개 subtest가 모두 통과했다.
- Codex implement·fix gate, task parser와 UNIT 실행 흐름의 회귀가 없었다.

Status: passed

Command:

```bash
python -m pytest
```

Result:

- 전체 222개 테스트가 모두 통과했다.

Status: passed

Command:

```bash
python -m unittest discover -s tests
```

Result:

- 전체 222개 테스트가 `OK`로 통과했다.
- 출력 중 argparse 오류 문구와 provider 실패 문구는 해당 실패 경로를 검증하는
  테스트의 예상 출력이었다.

Status: passed

Command:

```bash
python -m compileall app scripts tests
```

Result:

- application, script와 test module이 오류 없이 compile됐다.

Status: passed

Command:

```bash
git diff --check
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- tracked diff whitespace 검사는 출력 없이 exit code 0이었다.
- application router, Daily Topic pipeline, DB migration과 K3s manifest diff는
  없었다.

Status: passed

## UNIT-04 Documentation

- `docs/agent/backend-workflow.md`에 자동 실행 지원 판정과 두 단계 수동 fallback을
  추가했다.
- `docs/agent/antigravity-review.md`에 자동·수동 review 차이, 완료 조건, 허용
  Verdict와 실패 후 복구를 추가했다.
- `docs/agent/usage-guide.md`에서 Gemini CLI 자동 adapter 안내를 제거하고 실행
  기록, failure category별 복구와 backend·frontend 공통 적용 기준을 추가했다.
- `docs/agent/verification-gates.md`에 자동 process와 review 파일 검증을 함께
  요구하는 review gate를 추가했다.

## External Execution

- 실제 외부 Antigravity process는 실행하지 않았다.
- 현재 adapter 계약은 자동 실행 미지원이며 수동 review fallback만 제공한다.

Command:

```bash
scripts/agent_run.sh antigravity-review --preview
```

Result:

- 표시 Agent는 `Antigravity`, adapter는 `agy`, 실행 후보는 로컬 `agy` 경로였다.
- 자동 실행 지원은 `no`, failure category는
  `automatic_review_unavailable`, 수동 fallback 필요는 `yes`로 출력됐다.
- preview prompt가 출력됐고 Agent process나 실행 로그는 생성하지 않았다.

Status: passed

Command:

```bash
scripts/agent_next_step.sh status
```

Result:

- Verification은 `passed`, review는 `template only`, 자동 review는
  `unavailable`, 수동 review 필요는 `yes`로 출력됐다.
- 다음 action은 `antigravity-review-write`였고 두 수동 review 명령을 함께
  안내했다.

Status: passed

Command:

```bash
git diff --check
git diff --stat
git diff --name-only
git status --short
```

Result:

- tracked diff whitespace 검사는 출력 없이 exit code 0이었다.
- 변경 범위는 Agent workflow 구현·테스트·문서와 branch workflow artifact였다.
- 기존 UNIT-01~03 변경을 포함한 working tree 상태를 보존했다.

Status: passed

Command:

```bash
rg -n '^[-] \[ \]' docs/tasks/fix-antigravity-cli-review-adapter.md || true
rg -n 'Gemini CLI.*--prompt|--approval-mode auto_edit|Gemini/Antigravity' \
  docs/agent AGENTS.md || true
```

Result:

- 미완료 Task checklist가 없었다.
- 현재 workflow 문서에 제거 대상인 기존 Gemini 자동 adapter 안내가 없었다.

Status: passed

Command:

```bash
for file_name in docs/tasks/fix-antigravity-cli-review-adapter.md \
  docs/verification/fix-antigravity-cli-review-adapter.md \
  docs/reviews/fix-antigravity-cli-review-adapter-antigravity.md \
  docs/reviews/fix-antigravity-cli-review-adapter-coderabbit.md \
  docs/fixes/fix-antigravity-cli-review-adapter-approved-fixes.md \
  docs/pr/fix-antigravity-cli-review-adapter.md \
  docs/devlog/fix-antigravity-cli-review-adapter.md \
  scripts/agent_workflow/review_validation.py \
  tests/test_agent_review_validation.py; do
  git diff --no-index --check /dev/null "$file_name" \
    >/tmp/no-index-check.out 2>&1
  code=$?
  if [ "$code" -gt 1 ]; then
    /bin/cat /tmp/no-index-check.out
    exit "$code"
  fi
  if [ -s /tmp/no-index-check.out ]; then
    /bin/cat /tmp/no-index-check.out
    exit 1
  fi
done
```

Result:

- 미추적 branch workflow artifact와 신규 Python·test 파일의 whitespace 검사가
  출력 없이 exit code 0으로 통과했다.

Status: passed

Command:

```bash
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s \
  requirements.txt \
  app/main.py
```

Result:

- application, API 등록, dependency, Daily Topic pipeline, DB migration과 K3s
  manifest diff가 없었다.

Status: passed

Command:

```bash
scripts/agent_next_step.sh status
```

Result:

- UNIT 4개 완료, pending UNIT 0개, Verification `passed`로 출력됐다.
- Review는 `template only`, 자동 review는 `unavailable`, 수동 review 필요는
  `yes`이며 다음 action은 `antigravity-review-write`로 유지됐다.

Status: passed

Command:

```bash
for name in antigravity gemini agy; do
  if command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
    "$name" --version 2>&1 | head -n 20
    "$name" --help 2>&1 | head -n 120
  else
    echo "$name: not found"
  fi
done
```

Result:

- `antigravity` command는 발견되지 않았다.
- `gemini`는 `/opt/homebrew/bin/gemini`, version `0.45.0`이었다.
- Gemini help는 `--prompt` headless mode와 `--approval-mode`를 제공한다.
- `agy`는 `/Users/seochanjin/.local/bin/agy`, version `1.0.9`이었다.
- `agy` help는 `--print`/`--prompt` 단일 prompt 비대화형 mode,
  `--print-timeout`, `--sandbox`를 제공한다.

Status: passed

Command:

```bash
agy help 2>&1 | head -n 240
agy changelog 2>&1 | head -n 240
agy help install 2>&1 | head -n 240
agy help models 2>&1 | head -n 240
```

Result:

- 설치된 binary는 자신을 `Antigravity CLI`로 표시했다.
- changelog에는 `1.0.0` initial release가 표시됐다.
- `install`은 PATH와 shell 설정용이며 별도 인증 option은 표시하지 않았다.
- `models`는 사용 가능한 model 조회 command로 표시됐다.

Status: passed

Command:

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir" || exit 1
agy models >models.stdout 2>models.stderr
agy --print --sandbox --print-timeout 30s \
  '도구를 사용하거나 파일을 수정하지 말고 OK만 출력해.' \
  >print.stdout 2>print.stderr
rm -rf "$tmpdir"
```

Result:

- 두 command 모두 exit code 1이었다.
- stdout은 비어 있었고 진단은 stderr에 기록됐다.
- 현재 실행 sandbox가 `~/.gemini/antigravity-cli/log` 기록과
  `127.0.0.1:0` listener bind를 허용하지 않아 language server 시작 전에
  종료됐다.
- 이 결과로는 인증 성공 여부, 정상 prompt 응답, review 파일 작성과 정상
  종료 시 stdout·stderr 동작을 확인할 수 없다.

Status: failed

Notes:

- 실패 원인은 Antigravity service 또는 credential 실패가 아니라 현재 Agent
  실행 sandbox의 filesystem/network 제약이다.
- 실제 review prompt는 실행하지 않았고 repository 파일 변경 권한도 부여하지
  않았다.

Command:

```bash
scripts/agent_run.sh antigravity-review --preview
```

Result:

- exit code 2로 종료됐다.
- 현재 Verification Status가 `pending`이므로 기존 gate가 preview를 차단했다.
- Agent executable은 실행되지 않았고 `.agent-runs` 로그도 생성되지 않았다.

Status: passed

Notes:

- UNIT-02 이후에는 자동 실행 불가와 수동 review 필요 상태를 preview에서
  구분해 표시해야 한다.

Command:

```bash
git diff --check
```

Result:

- 출력 없이 exit code 0이었다.

Status: passed

Command:

```bash
python -m compileall app scripts tests
```

Result:

- app, scripts와 tests 전체 Python 파일이 오류 없이 compile됐다.

Status: passed

Command:

```bash
git diff --check
git diff --no-index --check /dev/null \
  docs/tasks/fix-antigravity-cli-review-adapter.md
git diff --no-index --check /dev/null \
  docs/verification/fix-antigravity-cli-review-adapter.md
```

Result:

- tracked diff whitespace 검사는 출력 없이 exit code 0이었다.
- 두 미추적 문서의 no-index 검사는 content difference를 뜻하는 exit code 1이고
  whitespace error 출력은 없었다.

Status: passed

Command:

```bash
git status --short
git diff --name-only
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- UNIT-02 변경은 agent workflow Python module, 해당 테스트, 현재 Task와
  Verification 문서에 한정됐다.
- 기존 사용자 변경인 `docs/tasks/main.md`와 branch용 workflow artifact는
  보존했다.
- 변경 금지 application, Daily Topic pipeline, DB migration과 K3s manifest
  diff는 없었다.

Status: passed

Notes:

- 현재 branch용 Task와 Verification은 미추적 파일이므로 별도 no-index
  whitespace 확인도 수행했다.

Command:

```bash
git diff --no-index --check /dev/null \
  docs/tasks/fix-antigravity-cli-review-adapter.md
git diff --no-index --check /dev/null \
  docs/verification/fix-antigravity-cli-review-adapter.md
```

Result:

- 두 command 모두 content difference를 뜻하는 exit code 1이었다.
- whitespace error 출력은 없었다.

Status: passed

Command:

```bash
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- 출력 없이 변경 금지 영역 diff가 없었다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- 24개 테스트와 5개 subtest가 모두 통과했다.
- Gemini만 PATH에 있는 상태, `agy` 설치와 자동 실행 지원 상태 분리,
  executable 미설치, 자동 실행 미지원 process 차단을 검증했다.
- `UNSUPPORTED_CLIENT`, 인증 실패, 비대화형 실행 미지원, timeout,
  일반 non-zero exit 분류를 검증했다.
- 자동 실행 미지원 CLI가 외부 process와 `.agent-runs` 로그를 만들지 않고
  수동 review 명령을 안내하는지 검증했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/agent_workflow \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py
```

Result:

- 변경한 workflow module과 테스트 파일이 모두 compile됐다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- Task의 Agent workflow 집중 검증 37개 테스트와 8개 subtest가 모두 통과했다.
- 기존 Codex gate, UNIT mode, verification gate와 status read-only 동작에
  회귀가 없었다.

Status: passed

Command:

```bash
git diff --check
git diff --stat
git diff --name-only
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- `git diff --check`는 출력 없이 exit code 0이었다.
- tracked 변경은 기존 `docs/tasks/main.md`와 UNIT-02 workflow Python 및 테스트
  파일에 한정됐다.
- application router, Daily Topic pipeline, DB migration과 K3s manifest
  diff는 없었다.

Status: passed

Command:

```bash
python -m pytest \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_cli.py \
  -v
```

Result:

- Verdict parser 보완 후 최종 집중 검증에서 50개 테스트와 13개 subtest가 모두
  통과했다.
- 허용 Verdict 뒤 Markdown 강조와 설명은 인식하고, `APPROVED MAYBE`처럼
  허용 값을 임의 확장한 문구는 거부했다.

Status: passed

Command:

```bash
python -m compileall \
  scripts/agent_workflow \
  tests/test_agent_review_validation.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py
```

Result:

- 최종 Python 변경이 오류 없이 compile됐다.

Status: passed

Command:

```bash
git diff --check
git diff -- \
  app/routers \
  app/services/daily_topic_pipeline \
  db/migrations \
  k8s
```

Result:

- tracked diff whitespace 검사는 출력 없이 exit code 0이었다.
- 변경 금지 application, Daily Topic pipeline, DB migration과 K3s manifest
  diff는 없었다.

Status: passed

Command:

```bash
for file_name in docs/tasks/fix-antigravity-cli-review-adapter.md \
  docs/verification/fix-antigravity-cli-review-adapter.md \
  scripts/agent_workflow/review_validation.py \
  tests/test_agent_review_validation.py; do
  git diff --no-index --check /dev/null "$file_name" \
    >/tmp/no-index-check.out 2>&1
  code=$?
  if [ "$code" -gt 1 ]; then
    /bin/cat /tmp/no-index-check.out
    exit "$code"
  fi
  if [ -s /tmp/no-index-check.out ]; then
    /bin/cat /tmp/no-index-check.out
    exit 1
  fi
done
```

Result:

- 출력 없이 exit code 0이었다.
- 최종 미추적 UNIT-03 관련 파일에 whitespace 오류가 없었다.

Status: passed

## Results

### 현재 흐름

```text
antigravity-review
→ gates.resolve_agent()
→ AGENT_ANTIGRAVITY_BIN이 없으면 gemini 탐지
→ Gemini/Antigravity 표시 이름과 gemini adapter 반환
→ runner가 gemini --prompt ... --approval-mode auto_edit 실행
```

Gemini CLI 설치 여부와 Antigravity 자동 review 지원 여부가 결합되어 있어
Task의 분리 요구를 충족하지 않는다.

### UNIT-01 adapter 계약 결정

- 표시 이름: `Antigravity`
- 기본 실행 후보: `agy`
- 금지 fallback: PATH의 `gemini`를 Antigravity adapter로 자동 선택
- 자동 실행 지원 조건:
  - 확인된 headless invocation 사용
  - 사전 인증된 사용자 session 사용
  - 비대화형 permission 동작 확인
  - review 파일 쓰기와 exit/stdout/stderr 동작 확인
- 현재 판정:
  - `automatic review unavailable`
  - `manual review required`
- 완료 판정:
  - process 성공과 review 파일 검증을 모두 통과해야 자동 review 완료
  - 수동 review는 review 파일 검증을 통과하면 완료 가능
- credential:
  - command argument와 로그에 전달하거나 기록하지 않음
- 기록 필드:
  - agent 표시 이름
  - adapter 종류
  - executable
  - 자동 실행 지원 여부
  - exit code
  - timeout 여부
  - failure category
  - manual fallback 필요 여부
  - review 파일 검증 결과
  - review 완료 판정
  - 다음 권장 action

### UNIT-02 구현 결과

- `AgentCommand`에서 표시 이름, adapter, executable 후보, 자동 실행 지원 여부,
  failure category, manual fallback과 다음 action을 분리했다.
- Antigravity 탐지는 `agy`만 후보로 사용하며 PATH의 `gemini`를 fallback으로
  선택하지 않는다.
- `agy` 또는 `AGENT_ANTIGRAVITY_BIN`이 있어도 현재 검증 수준에서는
  `automatic_review_unavailable`로 판정하고 subprocess를 시작하지 않는다.
- 실행 파일이 없거나 잘못 설정되면 `executable_missing`으로 판정한다.
- 실행 가능한 fake adapter 결과에서 다음 category를 분류하고 result JSON에
  기록한다.
  - `unsupported_client`
  - `authentication_failed`
  - `noninteractive_unsupported`
  - `timeout`
  - `nonzero_exit`
- `UNSUPPORTED_CLIENT`와 다른 Antigravity 실행 실패는 수동 review fallback과
  `scripts/agent_next_step.sh antigravity-review`를 다음 action으로 기록한다.
- review 파일 검증은 UNIT-03 전이므로 result JSON에는
  `review_file_validation: not_evaluated`, `review_completed: false`를 기록한다.
- 실제 외부 Antigravity process는 실행하지 않았다.

### UNIT-03 구현 결과

- `review_validation.py`가 파일 없음, 빈 파일, 초기 템플릿, 필수 section 누락,
  실제 review 본문 누락, Verdict 누락과 허용되지 않은 Verdict를 구분한다.
- 최초 review와 최신 `Re-review N`의 서로 다른 필수 section 구조를 검증한다.
- 허용 Verdict `APPROVED`, `APPROVED WITH NOTES`, `CHANGES REQUIRED`만 완료로
  인정한다.
- 자동 review는 process 성공뿐 아니라 review 파일 생성 또는 변경과 파일 검증을
  모두 통과해야 완료로 기록한다.
- review 파일 미생성, 미변경과 검증 실패는 각각
  `review_file_missing`, `review_file_unchanged`,
  `review_file_validation_failed`로 기록한다.
- 수동 review는 자동 실행 기록 없이도 파일 검증을 통과하면 완료로 판정한다.
- status는 review not started, template only, incomplete, completed와 자동 실행
  지원, 실행 실패, 수동 review 필요 및 다음 action을 구분한다.
- 자동 review 실패 또는 미완성 review 상태에서는 `codex-fix`나 `pr-draft`를
  제안하지 않는다.

## Manual or Production Verification

현재 sandbox 밖에서 사전 인증된 `agy` session으로 다음 항목을 사람이 확인해야
자동 실행 지원 여부를 `supported`로 전환할 수 있다.

- `agy --print` 단일 prompt의 실제 성공
- 비대화형 실행 중 permission prompt 발생 여부
- 지정 review 파일만 수정할 수 있는지
- 성공·인증 실패·일반 실패의 exit code와 stdout·stderr 위치

Production verification, deployment와 rollout은 이 UNIT의 범위가 아니다.

## Pending Verification

- UNIT-04: 수동 fallback 문서 동기화와 전체 회귀 검증
- 전체 pytest, 전체 unittest와 전체 `compileall app scripts tests`는 UNIT-04에서
  수행한다.
- 현재 sandbox 밖 실제 `agy` 실행 evidence가 제공되지 않으면 자동 실행 성공을
  주장하지 않는다.

## Evidence Notes

- 공개 웹 검색에서는 설치된 `agy` 1.0.9의 실행 계약을 확인할 공식 1차 문서를
  찾지 못했다. 확인되지 않은 외부 command나 option은 계약에 포함하지 않았다.
- 설치된 CLI의 `--help`, `--version`, `changelog` 출력과 실제 exit/output만
  근거로 사용했다.
- 현재 `UNSUPPORTED_CLIENT` 문구는 Task에 제공된 기존 Gemini CLI 오류이며,
  이번 UNIT에서 Gemini 외부 prompt를 재실행해 재현하지 않았다.
