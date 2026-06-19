# Antigravity Review 지침

[Backend agent workflow로 돌아가기](backend-workflow.md)

Antigravity는 review agent다. 명시적 요청이 없으면 file을 수정하지 않는다.
Review output만으로 구현 수정이 승인되지는 않는다.

## 입력

1. `AGENTS.md`
2. 현재 task file
3. Verification 문서
4. Approved fixes 문서
5. 기존 Antigravity review 문서
6. Current git diff
7. `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` index와 관련 세부 문서
8. `docs/prompts/antigravity-review.md`

## Review 관점

- Task requirement와 acceptance criteria 충족
- Logic, maintainability, 누락된 등록·dependency·migration
- Secret 노출, unsafe permission, 불필요한 privilege
- Human-controlled operation 경계
- Scope 밖 file 변경
- Verification command와 완료 claim의 일치
- Task checklist 완료 상태와 실제 diff/verification evidence의 일치
- Approved Fixes checklist와 실제 적용·검증 결과의 일치
- 승인되지 않은 suggestion 적용 여부
- Fix 적용 과정의 새 결함과 scope creep
- 동작 변경의 end-to-end 검증 또는 pending/human-required 기록
- 현재 architecture/runbook과 구현의 일치

## Output

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

저장 요청이 있으면 finding만
`docs/reviews/<safe-branch>-antigravity.md`에 기록한다. Applied fix나 verification
결과를 review 문서에 기록하지 않는다.

Human operator가 fix를 승인하면 별도의 approved fixes 문서에 기록하고 Codex가
그 항목만 적용한다.

## 최초 Review와 Re-review

Antigravity review는 `docs/reviews/<safe-branch>-antigravity.md` 하나를 사용한다.

- 파일이 없거나 비어 있으면 최초 review를 작성한다.
- 기존 파일이 있으면 원문과 기존 `Re-review` 이력을 보존한다.
- 재검토 결과는 파일 아래에 다음 번호의 `Re-review N` 섹션으로 추가한다.
- 기존 문제는 해결됨, 부분 해결, 미해결, 적용 대상 아님으로 판정하고 근거를
  기록한다.
- 기존 required fix는 실제 해결이 확인된 경우에만 체크한다.
- 새 문제는 기존 문제와 구분해 기록한다.
- 최종 판단은 `APPROVED`, `APPROVED WITH NOTES`, `CHANGES REQUIRED` 중 하나다.
