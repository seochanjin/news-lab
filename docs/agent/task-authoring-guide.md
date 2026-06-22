# Task 작성 가이드

[Backend agent workflow로 돌아가기](backend-workflow.md)

## 원칙

Task에는 현재 작업에 고유한 요구사항만 작성한다. 공통 안전 규칙은
`AGENTS.md`, backend workflow, verification gate와 forbidden commands를
참조한다. Chat prompt보다 Task가 우선한다.

```markdown
# Task: <작업명>

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
```

## Section 작성 기준

- Goal: 해결할 문제와 완료 후 상태
- Scope: 이번 Task에서 실제로 변경할 동작과 문서
- Do not change: 인접하지만 건드리지 않을 영역
- Expected files: 예상 변경 경로와 허용할 조정 범위
- DB/API changes: 없으면 `없음`으로 명확히 기록
- Test commands: Agent가 실행해도 되는 command만 기록
- Acceptance criteria: 관찰 가능한 완료 조건
- Notes: 선택 배경, 사람 작업, 후속 범위

## Implementation Units

일반 모드의 기본값:

```markdown
## Implementation Units

없음
```

UNIT 모드가 필요하면 `없음`을 삭제하고 순서대로 작성한다.

```markdown
## Implementation Units

- [ ] UNIT-01: 첫 번째 작업 단위
- [ ] UNIT-02: 두 번째 작업 단위
```

각 UNIT은 조사, 변경, 문서화, 검증과 기록까지 끝낼 수 있는 크기로 작성한다.
앞선 UNIT이 미완료인데 뒤 UNIT을 완료 표시하지 않는다. `없음`과 checklist를
함께 두지 않는다. Goal과 Scope를 Agent가 자동 분할하지 않는다.

## 공통으로 반복하지 않아도 되는 규칙

- Production-impacting command는 사람이 수행한다.
- Secret, credential, kubeconfig를 수정하지 않는다.
- Agent는 push와 merge를 실행하지 않는다.
- 실행하지 않은 검증을 성공으로 기록하지 않는다.
- 운영 log 없이 production verification 완료를 주장하지 않는다.
- Review output은 Approved Fixes 승인 전 수정 근거가 아니다.
- Verification에는 실제 command와 결과만 기록한다.
- 현재 Scope를 자동 확장하지 않는다.
- 사람이 수행할 작업을 별도로 기록한다.

## Python 문서화 정책

Python 파일을 새로 만들거나 의미 있게 수정할 때는 파일 최상단에 한글 module
docstring을 작성한다. 파일의 핵심 역할, 주요 입력과 출력, 다른 모듈과의 관계,
담당하지 않는 책임과 파일 쓰기·subprocess 같은 주요 부수 효과를 실제 동작에
맞게 설명한다. 파일명을 번역한 한 줄 설명만 작성하지 않는다.

새로 만들거나 의미 있게 수정하는 class, function과 method에도 한글 docstring을
작성한다. 복잡도에 맞춰 책임, 보관하는 상태, 주요 인자, 반환값, 주요 예외와
부수 효과를 설명한다. 단순 property와 내부 helper도 무엇을 판단하거나
반환하는지는 명시하되 의미 없는 장문은 피한다.

Python 테스트 파일에는 검증 범위와 외부 부수 효과 여부를 설명하는 한글 module
docstring을 작성한다. 각 테스트 함수와 method에는 검증 조건, 기대하는
성공·실패 동작과 회귀 방지 대상을 설명한다.

기존 Python 파일을 의미 있게 수정할 때 module docstring이 없거나 수정한
class·function·method의 설명이 실제 동작과 맞지 않으면 함께 보완한다. 오탈자,
import 정렬처럼 동작과 무관한 사소한 변경만 한 경우나 현재 Task와 무관한
기존 파일까지 문서화만을 목적으로 범위를 확대하지 않는다. 설명 추가 때문에
공개 interface나 동작을 변경하지 않는다.

명백한 코드 한 줄마다 인라인 주석을 추가하지 않으며 module, class, function
docstring을 우선한다. 기존 영문 docstring은 실제 동작을 확인해 한글로
교체하거나 필요한 내용을 보완한다.

Task에서 더 엄격한 제약이 필요하면 명시한다. 반복 규칙을 발견하면 현재 Task
제약을 먼저 적용하고 여러 Task에 공통인지 검토한다. 공통화가 현재 Scope 밖이면
후속 작업 후보로 기록하며 Agent가 임의로 확대하지 않는다.
