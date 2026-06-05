# Agent Handoff Prompt Rules

이 문서는 NewsLab agent workflow에서 Codex, Gemini/Antigravity, CodeRabbit, human operator 사이의 handoff prompt 작성 기준을 정의한다.

## Source of Truth

- 긴 작업 요구사항은 `docs/tasks/<safe-branch>.md`에 둔다.
- Chat prompt는 source of truth, 파일 경로, 작업 범위, 금지사항, 검증 명령 중심으로 짧게 작성한다.
- `docs/tasks/<safe-branch>.md`와 chat prompt가 충돌하면 `docs/tasks/<safe-branch>.md`를 우선한다.
- 실제 검증 결과의 source of truth는 `docs/verification/<safe-branch>.md`이다.
- 승인된 review fix의 source of truth는 `docs/fixes/<safe-branch>-approved-fixes.md`이다.

## Branch File Naming

현재 git branch를 safe branch name으로 변환해 workflow 파일 경로를 만든다.

Example:

```text
feature/raw-extractor-cronjob -> feature-raw-extractor-cronjob
```

Workflow files:

- `docs/tasks/<safe-branch>.md`
- `docs/reviews/<safe-branch>-antigravity.md`
- `docs/reviews/<safe-branch>-coderabbit.md`
- `docs/fixes/<safe-branch>-approved-fixes.md`
- `docs/verification/<safe-branch>.md`
- `docs/pr/<safe-branch>.md`
- `docs/devlog/<safe-branch>.md`

## Prompt Boundaries

모든 handoff prompt는 다음 경계를 명시한다.

- Agent가 production-impacting command를 실행하지 않는다.
- `kubectl apply`, `kubectl rollout`, Supabase SQL, production `curl` verification, `git push`, `git merge`는 human-controlled operation이다.
- secrets, `.env`, kubeconfig, credentials, SSH keys, tokens는 수정하지 않는다.
- Codex, Gemini/Antigravity, GitHub, CodeRabbit을 helper가 자동 실행하지 않는다.
- GitHub MCP integration은 별도 작업 전까지 제외한다.

## Codex Implementation Prompt

Codex implementation prompt에는 다음을 포함한다.

- `AGENTS.md`, `docs/RUNBOOK.md`, `docs/prompts/codex-implement.md`, `docs/tasks/<safe-branch>.md`를 읽으라는 지시.
- `docs/tasks/<safe-branch>.md`가 source of truth라는 지시.
- Scope, Do not change, Test commands, Acceptance criteria를 따르라는 지시.
- 실제 실행한 명령과 결과만 `docs/verification/<safe-branch>.md`에 기록하라는 지시.
- production verification, rollout, PR merge는 human log 없이는 완료로 쓰지 말라는 지시.

## Gemini/Antigravity Review Prompt

Review prompt에는 다음을 포함한다.

- `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/prompts/antigravity-review.md`, task file, current git diff를 읽으라는 지시.
- 파일을 수정하지 말고 chat에 review만 출력하라는 지시.
- review 기준: scope control, bug, unsafe production behavior, missing verification, documentation mismatch.
- review output은 approved fixes가 아니라는 명시.

Review focus:

- Requirement coverage against the task file.
- Code quality and maintainability.
- Security risks, including secret exposure, unsafe permissions, and unnecessary privileges.
- Operational safety and human-controlled operation boundaries.
- Scope control and unexpected file changes.
- Verification integrity: completed checks must match actually-run commands.
- Documentation consistency and future readability.

Review output structure:

```text
## Review Summary

## Requirement Coverage

## Code Quality / Maintainability

## Security Review

## Operational Risk

## Scope Control

## Verification Review

## Documentation Review

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Verdict
```

## Gemini/Antigravity Review Write Prompt

Review write prompt에는 다음을 포함한다.

- 수정 가능한 파일을 `docs/reviews/<safe-branch>-antigravity.md` 하나로 제한한다.
- review finding만 저장한다.
- applied fixes나 verification results를 `docs/reviews/`에 기록하지 않는다.
- review output만으로는 수정 지시가 되지 않는다고 명시한다.

Review focus:

- Requirement coverage against the task file.
- Code quality and maintainability.
- Security risks, including secret exposure, unsafe permissions, and unnecessary privileges.
- Operational safety and human-controlled operation boundaries.
- Scope control and unexpected file changes.
- Verification integrity: completed checks must match actually-run commands.
- Documentation consistency and future readability.

Review output structure:

```text
## Review Summary

## Requirement Coverage

## Code Quality / Maintainability

## Security Review

## Operational Risk

## Scope Control

## Verification Review

## Documentation Review

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Verdict
```

## Fixes Draft Prompt

Fixes draft prompt에는 다음을 포함한다.

- Review files와 current git diff를 바탕으로 candidate fixes 초안을 만들 수 있다.
- 최종 승인 주체는 human operator이다.
- human approval이 없는 항목은 approved로 쓰지 않는다.
- review output만으로는 code modification을 지시하지 않는다.
- candidate, rejected, deferred 항목을 분리한다.

## Codex Apply Fixes Prompt

Codex apply-fixes prompt에는 다음을 포함한다.

- `docs/fixes/<safe-branch>-approved-fixes.md`의 approved fixes만 반영한다.
- `docs/reviews/`의 review suggestion을 직접 적용하지 않는다.
- candidate, rejected, deferred suggestion은 적용하지 않는다.
- 실제 실행한 검증만 `docs/verification/<safe-branch>.md`에 기록한다.

## PR Draft Prompt

PR draft prompt에는 다음을 포함한다.

- `docs/verification/<safe-branch>.md`를 test/verification 결과의 source of truth로 사용한다.
- `docs/fixes/<safe-branch>-approved-fixes.md`를 applied approved fixes의 source of truth로 사용한다.
- PR merge, production deployment, K3s rollout, production verification을 human log 없이 완료로 쓰지 않는다.
- 실행하지 않은 명령은 pending 또는 notes로 기록한다.

## Devlog Draft Prompt

Devlog draft prompt에는 다음을 포함한다.

- `docs/verification/<safe-branch>.md`와 human-provided verification logs만 실제 검증 결과로 사용한다.
- `docs/fixes/<safe-branch>-approved-fixes.md`만 approved fixes 근거로 사용한다.
- Notion에 옮기기 쉬운 구조로 작성한다.
- 검증되지 않은 항목은 pending으로 남긴다.

## Helper Usage

`scripts/agent_next_step.sh`는 현재 branch에서 safe branch name과 workflow file path를 계산하고, 사람이 복사해 쓸 prompt template만 출력한다.

이 helper는 Codex, Gemini/Antigravity, GitHub, CodeRabbit을 실행하지 않는다.
