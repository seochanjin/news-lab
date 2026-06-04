# PR Draft Prompt

Read `AGENTS.md`, the task file, and the current git diff.

Create a PR draft under `docs/pr/`.

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
- Only include tests that were actually run or explicitly provided by the human.
- If production verification is not done yet, write it as pending.
