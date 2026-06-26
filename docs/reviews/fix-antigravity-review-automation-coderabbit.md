# CodeRabbit Review: Antigravity UNIT Review 자동화 및 Re-review 상태 검증 개선

## Review Summary

Antigravity UNIT Review 자동화는 현재 `antigravity-review-unit`과
`antigravity-review` action으로 분리되어 있다. UNIT Review, Integration Review,
Re-review와 수동 fallback의 heading, 필수 section과 Verdict 계약은
`PASS`, `CHANGES REQUIRED`, `BLOCKED`로 정렬해야 한다.

이 문서는 현재 브랜치의 workflow artifact 정합성을 보조 검토한 기록이며,
외부 CodeRabbit 서비스를 새로 호출했다는 의미가 아니다.

## Problems Found

없음.

## Required Fixes Before PR

없음.

## Optional Improvements

- 최신 Review 실행 실패를 workflow state와 다음 action 판단에 반영하는
  FIX-23은 별도 승인 항목으로 남아 있다.
- tracked diff와 changed files의 민감 경로 필터 강화인 FIX-20은 별도 승인
  항목으로 남아 있다.

## Suggested Test Commands

- `python -m pytest tests/test_agent_review_validation.py tests/test_agent_review_docs.py -v`
- `python -m compileall scripts tests`
- `bash -n scripts/agent_run.sh scripts/agent_next_step.sh`
- `git diff --check`

## Risk Notes

- 이 작업은 backend application, DB schema, Kubernetes manifest와 dependency를
  변경하지 않는다.
- 과거 Verification section에는 FIX-16 적용 전 action 계약과 Re-review pending
  기록이 남아 있으므로, 현재 상태 판단은 문서의 최종 결과와 Approved Fixes
  checklist를 기준으로 해야 한다.
