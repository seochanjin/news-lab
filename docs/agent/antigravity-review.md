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

Review artifact에는 `file://` URI, 사용자 홈 디렉터리, 로컬 사용자명, absolute
filesystem path를 기록하지 않는다. Repository 내부 파일은 review artifact 위치를
기준으로 한 repository-relative Markdown link로 기록한다. 경로를 확정할 수 없으면
clickable link를 만들지 않고 repository-relative plain path로 기록한다.

자동 실행과 수동 fallback 모두 `Verdict`에는 다음 세 값만 사용한다.

- `PASS`
- `CHANGES REQUIRED`
- `BLOCKED`

Human operator가 fix를 승인하면 별도의 approved fixes 문서에 기록하고 Codex가
그 항목만 적용한다.

## 자동 실행과 수동 fallback

자동 UNIT Review는 `agy --print <prompt> --sandbox --print-timeout <초>s`
adapter를 사용한다. Gemini CLI는 Antigravity adapter나 fallback으로 사용하지
않으며 `UNSUPPORTED_CLIENT`를 성공으로 처리하지 않는다. `agy`에는 repository
파일 수정이 아니라 선택 mode의 새 Review section 하나만 stdout으로 반환하게
한다.

```bash
scripts/agent_run.sh antigravity-review-unit --dry-run
scripts/agent_run.sh antigravity-review-unit
scripts/agent_run.sh antigravity-review --dry-run
scripts/agent_run.sh antigravity-review
```

`antigravity-review-unit`은 구현 완료됐지만 Review 미통과인 UNIT 하나만
검토한다. 마지막 UNIT도 이 action에서는 `UNIT Review`로 유지하며 Integration
또는 Re-review로 전환하지 않는다. `antigravity-review`는 모든 UNIT Review가
완료된 뒤 Integration Review, Re-review 또는 일반 Task Review만 수행한다.

`--dry-run`은 현재 branch, 선택 mode와 UNIT, 예상 heading, prompt 크기,
제한 diff 파일 수, Approved Fixes, 최신 전체 테스트 수와 생성 prompt를 읽기
전용으로 출력한다. 기본 실행은 응답을 검증한 뒤에만 기존 Review 파일에
append한다.

자동 실행이 불가능하거나 실패하면 다음 순서로 수동 review를 진행한다.

```bash
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
```

- `antigravity-review`: review 대상과 기준을 포함한 chat prompt를 출력한다.
- `antigravity-review-write`: review 결과를
  `docs/reviews/<safe-branch>-antigravity.md`에 작성하는 prompt를 출력한다.

수동 fallback도 자동 Review와 같은 heading, 필수 section과 `PASS`,
`CHANGES REQUIRED`, `BLOCKED` Verdict 계약을 사용한다.

`agy`가 없으면 Agent process와 실행 로그를 만들지 않고 non-zero로 종료하며 위
수동 명령을 안내한다.

## UNIT Review 상태와 대상 선택

Task 구현 checklist와 Review 통과 checklist는 의미가 다르다.

- Task `[x]`: 해당 UNIT의 구현·문서화·검증·Verification 기록 완료
- Review Status `[x]`: 해당 UNIT Review의 `PASS`

하네스는 Task의 UNIT ID, 제목과 순서를 그대로 사용해 Review 파일에
`Unit Review Status`를 생성한다. 기존 section이 있으면 Task와 완전히
일치하는지 검증하고 기존 체크 상태와 Review History를 보존한다.

`antigravity-review-unit`의 다음 대상은 Task에서 `[x]`이고 Review Status에서
`[ ]`인 가장 앞선 UNIT이다. `antigravity-review`는 미검토 UNIT이 있으면 실패하고
새 action 사용을 안내한다. 모든 UNIT Review가 끝난 뒤 Integration Review가
없으면 마지막 UNIT을 대상으로 전체 Acceptance Criteria와 UNIT 간 계약을 검토하는
`Integration Review`를 선택한다. Integration Review 이후 구현 Approved Fixes가
모두 적용되면 기존 History에서 다음 번호를 계산해 `Re-review N`을 선택한다.
`human-verification`으로 분류된 미완료 항목만 남은 경우에는 Re-review를
차단하지 않는다.

## 자동 응답 계약과 파일 반영

자동 Review 응답의 허용 Verdict는 다음 세 값이다.

- `PASS`
- `CHANGES REQUIRED`
- `BLOCKED`

응답은 선택 mode에 맞는 단일 2단계 heading과 정해진 순서의 3단계 section만
포함해야 한다. 문제가 있으면 `- [ ] REVIEW-<UNIT>-NN: 설명` 형식으로 기록한다.
`PASS`인 경우에만 선택 UNIT의 Review Status를 `[x]`로 변경하며, 다른 Verdict는
`[ ]`를 유지한다.

하네스는 다음 경우 Review 파일을 변경하지 않는다.

- process 실패, timeout 또는 빈·잘린 stdout
- 선택 UNIT이나 Re-review 번호와 다른 heading
- 필수 section, 본문, Verdict 또는 finding ID 오류
- Approved Fixes가 있는데 없다고 작성한 Re-review
- 최신 전체 테스트 수 대신 과거 수치를 현재 결과로 작성한 Re-review
- 기존 section과 동일한 fingerprint
- Shell·Agent·테스트·Script 실행 또는 background 대기 의도를 나타내는 응답

Agent가 Review 파일을 직접 변경하면 실행 전 bytes로 복구하고
`review_file_modified_by_agent`로 실패한다. 정상 반영은 검증된 section과
필요한 Review Status 변경을 하나의 원자적 writer 작업으로 수행한다.
Review subprocess에는 `NEWSLAB_ANTIGRAVITY_REVIEW_ACTIVE=1`을 전달하며 하위
process의 재귀 `antigravity-review-unit` 또는 `antigravity-review` 호출은 즉시
차단한다.

## Review 완료 조건

파일 존재만으로 review를 완료 처리하지 않는다. 파일 없음, 빈 파일, heading만
있는 초기 템플릿, 필수 section 누락, 실제 review 본문 없음, Verdict 누락과
허용되지 않은 Verdict는 모두 미완성이다.

허용 Verdict는 `PASS`, `CHANGES REQUIRED`, `BLOCKED` 세 값뿐이다. 자동 Review는
Agent process 성공, stdout 응답 검증, append-only writer 성공을 모두 통과해야
완료다. 수동 review는 자동 실행 기록 없이도 동일한 heading, 필수 section,
본문과 Verdict 구조 검증을 통과하면 완료다. Review finding은 사람이 Approved
Fixes에 승인하기 전까지 구현 변경 근거가 아니다.

## 실패 후 복구

`scripts/agent_next_step.sh status`에서 자동 실행 지원, 실행 상태, review 파일
검증, 수동 review 필요 여부와 다음 action을 확인한다. 실행 파일 미설치,
지원되지 않는 client, 인증 실패, 비대화형 실행 미지원, timeout, non-zero
exit, Agent 직접 파일 변경과 응답 검증 실패는 다음 내부 failure category로
구분해 기록한다.

- `executable_missing`
- `unsupported_client`
- `authentication_failed`
- `noninteractive_unsupported`
- `timeout`
- `nonzero_exit`
- `review_file_modified_by_agent`
- `review_agent_attempted_execution`
- `review_response_invalid`

외부 Gemini 오류의 `reasonCode: UNSUPPORTED_CLIENT`는 내부
`unsupported_client` category로 기록한다. 이 오류가 발생하면 해당 client로
재시도해 성공으로 간주하지 않는다. 수동 fallback을 사용하고, review 파일이 완료
조건을 충족하는지 status로 다시 확인한다. 자동 실행 실패 또는 미완성 review
상태에서는 `codex-fix`나 PR 초안 단계로 진행하지 않는다.
최신 실패 로그의 `action`이 `antigravity-review-unit`이면 같은 UNIT Review
action으로 복구하고, `antigravity-review`이면 최종 Review action으로 복구한다.
실패 로그에서 action을 판별할 수 없으면 임의로 최종 Review에 라우팅하지 않고
상태 출력을 차단 상태로 남겨 최신 `.agent-runs`의 `result.json` 확인을 요구한다.

## 최초 Review와 Re-review

Antigravity review는 `docs/reviews/<safe-branch>-antigravity.md` 하나를 사용한다.

- 파일이 없거나 비어 있으면 최초 review를 작성한다.
- 최초 review는 위 `Output` 구조를 사용하며 문제는 `Problems Found`에
  기록한다.
- `Existing Problems Status`와 `New Problems Found`는 최초 review 최상위
  구조에 사용하지 않고 `Re-review N` 내부에서만 사용한다.
- 기존 파일이 있으면 최초 review 전체와 기존 `Re-review` 이력을 불변
  기록으로 보존한다.
- 재검토 결과는 파일 아래에 다음 번호의 `Re-review N` 섹션으로 추가한다.
- 최초 review의 `Problems Found` 원문, `Required Fixes Before PR` 원문과
  checkbox, `Verdict`를 수정하지 않는다.
- 기존 `Re-review` 이력도 수정하지 않는다.
- 기존 문제는 번호 또는 명확한 제목으로 최초 review 항목과 연결한다.
- 기존 문제는 해결됨, 부분 해결, 미해결, 적용 대상 아님으로 판정하고
  `Re-review N`의 `Existing Problems Status`에 기록한다.
- 해결 판정에는 Approved Fixes, 현재 diff와 verification evidence를 함께
  기록한다.
- 새 문제는 `New Problems Found`, 현재 재검토 기준의 PR blocker는
  `Required Fixes Before PR`에 기록한다.
- 최종 판단은 해당 `Re-review N`의 `Verdict`에 `PASS`, `CHANGES REQUIRED`,
  `BLOCKED` 중 하나로 기록한다.

재검토 구조:

```text
## Re-review N
### Existing Problems Status
### Approved Fixes Verification
### Verification Evidence
### New Problems Found
### Required Fixes Before PR
### Verdict
```
