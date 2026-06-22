# Codex 구현 지침

[Backend agent workflow로 돌아가기](backend-workflow.md)

## 구현 전

- 현재 branch와 working tree를 확인한다.
- Task의 Scope, Do not change, Test commands, Acceptance criteria를 읽는다.
- 관련 파일의 현재 구조를 설명하고 짧은 계획을 제시한다.
- 변경 금지 영역과 production 영향 여부를 확인한다.

## 구현 중

- WIP 1을 유지하고 한 번에 하나의 checklist 작업 단위만 진행한다.
- 조사, 변경, 문서화, 검증, verification 기록, checklist 갱신을 완료한 뒤
  다음 단위로 이동한다.
- 코드 변경만 끝나고 검증이 끝나지 않은 항목은 완료 처리하지 않는다.
- 완료하지 않은 checklist 항목은 체크하지 않는다.
- 변경은 작고 review 가능하게 유지한다.
- 기존 user change와 무관한 file을 수정하지 않는다.
- Review feedback 적용 시 approved fixes file의 승인된 항목만 적용한다.
- Review file은 명시적 요청 없이 수정하지 않는다.
- 새 문제는 현재 작업 blocker, 범위 내 결함, 후속 작업 후보, 과거 기록으로
  분류하고 자동으로 scope를 확장하지 않는다.
- Python 파일을 새로 만들거나 의미 있게 수정할 때는 module, class, function,
  method와 테스트에 실제 역할과 검증 목적을 설명하는 한글 docstring을 작성한다.
- 상세 기준과 기존 파일 적용 범위는
  [Task 작성 가이드의 Python 문서화 정책](task-authoring-guide.md#python-문서화-정책)을
  따른다.

## 검증과 기록

- Task가 허용한 command만 실행한다.
- 실행한 command, exit/result, skipped check만 verification에 기록한다.
- 예상 결과나 제안 command를 실제 실행 결과처럼 쓰지 않는다.
- 실행하지 않은 검증은 미수행, 환경 제약으로 실패, 운영 반영 후 확인 필요,
  사람이 수행 필요 중 하나로 기록한다.
- 코드, API, DB, script 또는 pipeline 동작 변경은 task 범위에 맞는
  end-to-end 검증을 수행한다.
- PR과 devlog는 verification 문서의 결과를 사용한다.
- Production verification, rollout, deployment, merge는 human log 없이 완료로
  표시하지 않는다.

## 완료 보고

- 변경 파일
- 동작 또는 문서 책임 변화
- 실행한 검증 command와 결과
- 의도적으로 수정하지 않은 영역
- 위험과 남은 사람 작업

상세 gate는 [Verification gate](verification-gates.md), 실행 금지는
[금지 및 사람 통제 작업](forbidden-commands.md)을 따른다.

## 직접 실행 하네스

`scripts/agent_run.sh codex-implement`는 Task 전체를 대상으로 하고,
`scripts/agent_run.sh codex-implement-unit`는 첫 번째 미완료 UNIT 하나만
대상으로 한다. UNIT 실행에서는 후속 UNIT을 미리 구현하거나 자동 연속 실행하지
않는다. 실행 로그는 `.agent-runs/`에 저장되며 workflow 문서를 자동 완료하지
않는다.
