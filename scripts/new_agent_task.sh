#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <branch-name> <task-title>"
  echo "Example: $0 feature/extraction-runs '본문 추출 실행 이력 저장'"
  exit 1
fi

BRANCH_NAME="$1"
TASK_TITLE="$2"
SAFE_NAME=$(echo "$BRANCH_NAME" | tr '/' '-')

git checkout main
git pull origin main
git switch -c "$BRANCH_NAME"

mkdir -p docs/tasks docs/pr docs/devlog docs/prompts docs/reviews docs/fixes docs/verification

cat > "docs/tasks/${SAFE_NAME}.md" <<TASK
# Task: ${TASK_TITLE}

## Goal

## Scope

## Do not change

## Expected files

## DB changes

## API changes

## Test commands

## Acceptance criteria

## Notes

## Implementation Units

없음
TASK

cat > "docs/tasks/main.md" <<TASK_POINTER
# Current Task

[${SAFE_NAME}.md](${SAFE_NAME}.md)
TASK_POINTER

cat > "docs/pr/${SAFE_NAME}.md" <<PR
# ${TASK_TITLE}

## 작업 내용

## 주요 변경 사항

## 테스트

## 확인 결과

## 비고
PR

cat > "docs/devlog/${SAFE_NAME}.md" <<LOG
# ${TASK_TITLE}

## 작업 목적

## 기존 문제

## 변경 내용

## 테스트

## 운영 반영

## 확인 결과

## 이번 단계의 의미

## 다음 단계
LOG

cat > "docs/reviews/${SAFE_NAME}-antigravity.md" <<REVIEW
# Antigravity Review: ${TASK_TITLE}

## Review Summary

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Risk Notes
REVIEW

cat > "docs/reviews/${SAFE_NAME}-coderabbit.md" <<REVIEW
# CodeRabbit Review: ${TASK_TITLE}

## Review Summary

## Problems Found

## Required Fixes Before PR

## Optional Improvements

## Suggested Test Commands

## Risk Notes
REVIEW

cat > "docs/fixes/${SAFE_NAME}-approved-fixes.md" <<FIXES
# Approved Fixes: ${TASK_TITLE}

## Approved Fixes

## Rejected or Deferred Suggestions

## Applied Changes

## Verification Required
FIXES

cat > "docs/verification/${SAFE_NAME}.md" <<VERIFY
# Verification: ${TASK_TITLE}

## Verification Status

pending

## Verification Scope

## Commands Run

## Results

## Manual or Production Verification

## Pending Verification

## Evidence Notes
VERIFY

echo "Created branch: $BRANCH_NAME"
echo "Task file: docs/tasks/${SAFE_NAME}.md"
echo "PR draft: docs/pr/${SAFE_NAME}.md"
echo "Worklog draft: docs/devlog/${SAFE_NAME}.md"
echo "Antigravity review log: docs/reviews/${SAFE_NAME}-antigravity.md"
echo "CodeRabbit review log: docs/reviews/${SAFE_NAME}-coderabbit.md"
echo "Approved fixes log: docs/fixes/${SAFE_NAME}-approved-fixes.md"
echo "Verification log: docs/verification/${SAFE_NAME}.md"
