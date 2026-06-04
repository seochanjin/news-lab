# PR Draft Prompt

Read `AGENTS.md`, the task file, `docs/fixes/<safe-branch-name>-approved-fixes.md`, `docs/verification/<safe-branch-name>.md`, and the current git diff.

Create a PR draft under `docs/pr/`.

Use `docs/verification/<safe-branch-name>.md` as the source of truth for test and verification results.

Use `docs/fixes/<safe-branch-name>-approved-fixes.md` as the source of truth for approved review fixes that were applied.

The PR draft must include:

## 작업 내용

## 주요 변경 사항

## 추가/변경된 API

## DB 변경 사항

## 테스트

## 확인 결과

## 비고

Rules:

- Do not claim PR merge is complete.
- Do not claim production deployment is complete.
- Do not claim K3s rollout is complete.
- Only include tests that are recorded in `docs/verification/<safe-branch-name>.md` or explicitly provided by the human.
- If a command is only suggested but not run, put it in pending or notes, not in completed results.
- If production verification is not done yet, write it as pending.
- Do not use review files as proof that verification passed.
