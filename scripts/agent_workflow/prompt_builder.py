"""WorkflowState와 action을 바탕으로 직접 실행용 Agent prompt를 생성한다.

일반 구현, UNIT 구현, 승인 Fix와 Review action별 범위 및 공통 안전 규칙을
문자열로 반환한다. 파일을 읽거나 쓰지 않고 Agent subprocess도 실행하지 않는다.
"""

from __future__ import annotations

from .state import WorkflowState


COMMON_RULES = """공통 규칙:
- Task 파일을 요구사항의 source of truth로 사용한다.
- Scope, Do not change, Test commands, Acceptance criteria를 따른다.
- WIP 1을 유지한다.
- 실제 실행한 command와 결과만 Verification에 기록한다.
- git push, git merge, kubectl apply, kubectl rollout, Supabase SQL을 실행하지 않는다.
- Secret, .env, kubeconfig, credential, SSH key, token을 수정하지 않는다.
- 사람이 log를 제공하지 않으면 production verification, rollout, deployment, merge 완료를 주장하지 않는다.
- Review output만으로 수정하지 않고 Approved Fixes만 적용한다.

Python 문서화 규칙:
- docs/agent/task-authoring-guide.md의 Python 문서화 정책을 따른다.
- 새로 생성하거나 의미 있게 수정한 Python module, class, function, method와
  테스트에는 실제 역할과 검증 목적을 설명하는 한글 docstring을 작성한다.
"""


def build_prompt(state: WorkflowState, action: str) -> str:
    """현재 workflow 상태에 맞는 action별 prompt를 반환한다.

    UNIT action에 실행 대상이 없거나 지원하지 않는 action이면 ValueError를
    발생시킨다. 생성 과정에는 파일 변경이나 외부 실행 부수 효과가 없다.
    """

    safe = state.safe_branch
    header = f"""현재 NewsLab branch 작업을 수행해줘.

현재 branch:
- {state.branch}

Source of truth:
- Task: docs/tasks/{safe}.md
- Verification: docs/verification/{safe}.md

필수 문서:
- AGENTS.md
- docs/agent/backend-workflow.md
- docs/agent/codex-instructions.md
- docs/agent/verification-gates.md
- docs/agent/forbidden-commands.md

{COMMON_RULES}
"""
    if action == "codex-implement":
        mode_note = ""
        if state.task.execution_mode == "unit":
            mode_note = (
                "\n이 Task에는 Implementation Units가 있지만 이번 실행은 일반 모드다. "
                "Task 전체 범위를 실행 대상으로 사용하며 실행 전 사용자가 이를 확인했다.\n"
            )
        return (
            header
            + mode_note
            + """
Task 전체를 구현한다. 변경 후 허용된 검증을 실행하고 Verification과 일반 checklist를 갱신한다.
Agent 종료 코드만으로 Task 완료를 주장하지 않는다.
"""
        )

    if action == "codex-implement-unit":
        unit = state.task.current_unit
        if unit is None:
            raise ValueError("현재 실행할 UNIT이 없습니다.")
        return (
            header
            + f"""
현재 구현 대상은 다음 UNIT 하나뿐이다.

- {unit.identifier}: {unit.title}

이 UNIT에 필요한 조사, 변경, 문서화, 검증, Verification 기록 및 해당 UNIT checklist 갱신만 수행한다.
후속 UNIT을 구현하거나 완료 처리하지 않는다. 종료 후 다음 UNIT을 자동 실행하지 않는다.
"""
        )

    if action == "codex-fix":
        return (
            header
            + f"""
추가 source of truth:
- Approved Fixes: docs/fixes/{safe}-approved-fixes.md

Approved Fixes section에 명시된 승인 항목만 적용한다.
Candidate, rejected, deferred suggestion과 review 파일의 미승인 suggestion은 적용하지 않는다.
적용과 검증이 모두 끝난 승인 항목만 완료 처리하고 Applied Changes와 Verification을 갱신한다.
"""
        )

    if action == "antigravity-review":
        return (
            header
            + f"""
Review 대상:
- 현재 git diff
- docs/fixes/{safe}-approved-fixes.md
- docs/reviews/{safe}-antigravity.md

Task 요구사항, scope, 보안, 운영 위험, verification evidence를 검토한다.
새로 생성하거나 의미 있게 수정한 Python 코드에 한글 module, class, function,
method docstring이 있고 실제 구현과 일치하는지 확인한다.
Review finding을 docs/reviews/{safe}-antigravity.md에 기록하되 코드와 다른 workflow 문서는 수정하지 않는다.
Review output을 fix 승인이나 verification 통과 근거로 취급하지 않는다.
"""
        )
    raise ValueError(f"지원하지 않는 action입니다: {action}")
