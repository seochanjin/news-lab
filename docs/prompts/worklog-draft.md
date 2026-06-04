# Worklog Draft Prompt

Read `AGENTS.md`, `docs/ARCHITECTURE.md`, the task file, PR draft, and human-provided verification logs.

Create a worklog draft under `docs/devlog/`.

The worklog must be suitable for Notion.

Include:

## 작업 목적

## 기존 문제

## 변경 내용

## 구현 상세

## 테스트

## 운영 반영

## 확인 결과

## 이번 단계의 의미

## 포트폴리오용 요약

## 다음 단계 후보

Rules:

- Do not claim PR merge is complete unless the human explicitly says it was merged.
- Do not claim production deployment is complete unless the human provides rollout and curl verification logs.
- Do not invent test results.
- If something was not verified, mark it as pending.
