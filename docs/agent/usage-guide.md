# Agent workflow 사용 가이드

[Backend agent workflow로 돌아가기](backend-workflow.md)

## 전체 흐름

```text
작업 branch와 Task 생성
→ 구현과 실제 검증 기록
→ Antigravity Review
→ 사람이 Approved Fixes 승인
→ 승인 Fix 적용
→ PR·Devlog 초안
→ 사람이 commit, push, PR, merge 및 운영 반영
```

요구사항은 `docs/tasks/<safe-branch>.md`, 실제 검증은
`docs/verification/<safe-branch>.md`, 수정 승인은
`docs/fixes/<safe-branch>-approved-fixes.md`가 source of truth다.

## 작업 시작

`new_agent_task.sh`는 main 갱신과 신규 branch 생성 및 workflow 문서 생성을
수행하므로 깨끗한 working tree에서 사람이 실행한다.

```bash
scripts/new_agent_task.sh feature/example "작업 제목"
```

생성 후 `docs/tasks/main.md`는 현재 Task를 가리킨다. Task 형식은
[Task 작성 가이드](task-authoring-guide.md)를 따른다.

## 일반 모드와 UNIT 모드

일반 모드는 Task 전체를 한 번에 구현한다.

```bash
scripts/agent_run.sh codex-implement
```

작고 명확한 기능, 빠른 MVP, 되돌리기 쉬운 변경에 적합하다.

UNIT 모드는 `Implementation Units`의 첫 번째 미완료 항목 하나만 구현한다.

```bash
scripts/agent_run.sh codex-implement-unit
```

선후 관계가 있거나 중간 검증이 필요하고 범위 초과 위험이 큰 작업에 사용한다.
후속 UNIT은 자동 실행하지 않는다. 일반 모드가 기본이며 모든 Task를 UNIT으로
나눌 필요는 없다.

## Prompt-only 방식

Agent를 실행하지 않고 prompt만 확인하거나 복사한다.

```bash
scripts/agent_next_step.sh status
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh codex-implement-unit
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh codex-fix
```

기존 `codex-apply-fixes` command도 호환된다.

## 직접 실행 방식

```bash
scripts/agent_run.sh codex-implement --preview
scripts/agent_run.sh codex-implement
scripts/agent_run.sh codex-implement --yes --timeout 1200
```

기본 timeout은 1200초다. 실행 전 action, Agent, branch, Task, mode, UNIT,
로그 경로와 timeout을 출력한다. 비대화형 실행은 `--yes`가 필요하다.

Codex는 확인된 `codex exec -C <repo> -` 입력 형식을 사용한다. 현재 환경에서
별도 `antigravity` command의 비대화형 입력 형식은 확인되지 않았으므로 Review는
설치된 Gemini CLI의 `--prompt`와 `--approval-mode auto_edit`를 사용한다.
검증된 Antigravity wrapper가 있으면 prompt를 stdin으로 받는 executable 경로를
`AGENT_ANTIGRAVITY_BIN`에 지정할 수 있다. CLI가 없으면 prompt-only 방식을
사용한다.

## Review와 승인 Fix

```bash
scripts/agent_run.sh antigravity-review --preview
scripts/agent_run.sh antigravity-review
```

Review는 승인 자체가 아니다. 사람이 Approved Fixes section에 적용 항목을
명시한 경우에만 다음을 실행한다.

```bash
scripts/agent_run.sh codex-fix --preview
scripts/agent_run.sh codex-fix
```

Approved Fixes가 없거나 비어 있으면 gate가 실행을 차단한다.

## 상태와 로그

```bash
scripts/agent_next_step.sh status
```

현재 mode, UNIT 진행 수, Verification, Review, Approved Fixes와 권장 action을
읽기 전용으로 출력한다.

Verification 문서의 현재 전체 상태는 다음 section으로 관리한다.

```markdown
## Verification Status

pending
```

허용된 검증이 실제로 모두 통과한 뒤에만 `passed`로 바꾸고, 현재 실패가 있으면
`failed`를 사용한다. 과거 실패 기록이나 command별 `Status: failed` 문구는
삭제하지 않아도 되며 현재 상태 판정에는 사용되지 않는다. 상태 section이 없는
기존 문서는 `present`, 문서가 없으면 `missing`으로 표시된다.

```text
.agent-runs/<safe-branch>/<timestamp>-<action>/
├── prompt.md
├── stdout.log
├── stderr.log
└── result.json
```

`.agent-runs/`는 Git에서 제외된다. 종료 코드 0도 Task 완료나 test 통과를
의미하지 않으므로 실제 검증 결과는 Verification에 별도로 기록한다.

## Timeout과 실패 복구

Timeout은 exit code 124로 기록하고 process group을 종료한다. stdout, stderr,
prompt와 result는 유지된다. 비정상 종료도 exit code를 보존한다.

1. 로그를 확인한다.
2. Agent가 남긴 working tree 변경을 검토한다.
3. Task checklist와 Verification을 자동 완료하지 않는다.
4. 원인을 수정한 뒤 같은 action을 다시 실행한다.

## PR 전 확인

Task가 허용한 command만 실행하고 실제 결과를 Verification에 기록한다.

```bash
python -m pytest
python -m unittest discover -s tests
git diff --check
git diff --stat
git status --short --branch
```

## 사람이 직접 수행하는 작업

- Git commit, push, PR 생성과 merge 판단
- Supabase SQL과 migration 실행
- Kubernetes apply, rollout, restart
- Secret, credential, DNS, TLS 변경
- Production verification

직접 실행 하네스는 위 작업을 자동 수행하지 않는다.

## 일반 오류

- `docs/tasks/main.md` 오류: 현재 Task 파일 링크로 갱신한다.
- Task 없음: branch의 `/`를 `-`로 바꾼 safe name 파일을 생성한다.
- UNIT 실행 차단: `없음`을 제거하고 올바른 `UNIT-NN` checklist를 작성한다.
- 완료 순서 오류: 앞선 미완료 UNIT보다 뒤의 UNIT을 완료 표시하지 않는다.
- CLI 없음: 설치와 PATH를 확인하거나 prompt-only 방식을 사용한다.
- Review 차단: 구현 diff, Verification 문서, 명시적 test 실패를 확인한다.

## 처음부터 PR 초안까지

```bash
scripts/new_agent_task.sh feature/example "작업 제목"
scripts/agent_next_step.sh status
scripts/agent_run.sh codex-implement --preview
scripts/agent_run.sh codex-implement
scripts/agent_run.sh antigravity-review
# 사람이 Approved Fixes를 승인한 경우에만:
scripts/agent_run.sh codex-fix
scripts/agent_next_step.sh pr-draft
scripts/agent_next_step.sh devlog-draft
```

이후 commit, push, PR 생성과 merge는 사람이 수행한다.
