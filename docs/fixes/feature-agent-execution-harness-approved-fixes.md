# Approved Fixes: 일반 및 작업 단위 Agent 실행 하네스와 한글 가이드 추가

## Approved Fixes

### FIX-01. Python 코드의 한글 설명 규칙을 현재 코드와 향후 workflow에 공통 적용

- [x] 적용 및 검증 완료

Python 파일을 생성하거나 수정할 때 코드의 역할을 사용자가 쉽게 이해할 수 있도록 한글 docstring을 작성한다.

이번 브랜치에 추가되거나 수정된 Python 코드에 설명을 보강하는 것뿐만 아니라, 이후 모든 Agent 작업에서도 같은 규칙이 적용되도록 공통 Agent 문서와 프롬프트에 반영한다.

#### 1. 이번 브랜치 적용 대상

최소한 다음 영역을 확인한다.

```text
scripts/agent_workflow/**/*.py
tests/test_agent_*.py
```

그 밖에 이번 브랜치에서 새로 생성하거나 의미 있게 수정한 Python 파일이 있다면 동일한 규칙을 적용한다.

확인 명령:

```bash
git diff --name-only --diff-filter=ACM -- '*.py'
```

#### 2. Python 파일 설명 규칙

새로 생성하거나 의미 있게 수정하는 모든 Python 파일 최상단에는 해당 파일 전체의 역할을 설명하는 한글 module docstring을 작성한다.

예:

```python
"""NewsLab Agent 작업의 실행 전 조건을 검사하는 모듈이다.

현재 브랜치, Task 문서, Approved Fixes 및 Verification 상태를 확인하여
요청한 Agent action을 실행할 수 있는지 판정한다.

이 모듈은 Agent CLI를 직접 실행하지 않으며, 실행 가능 여부와
차단 사유를 반환하는 책임만 가진다.
"""
```

module docstring에는 가능한 범위에서 다음 내용을 포함한다.

- 파일이 담당하는 핵심 역할
- 주요 입력과 출력
- 다른 모듈과의 관계
- 해당 파일이 담당하지 않는 책임
- 파일 쓰기, subprocess 실행 등 주요 부수 효과의 존재 여부

파일명을 그대로 번역한 한 줄 설명만 작성하지 않는다.

#### 3. 클래스 설명 규칙

새로 생성하거나 의미 있게 수정하는 모든 클래스에는 한글 class docstring을 작성한다.

설명에는 다음을 포함한다.

- 클래스가 담당하는 책임
- 보관하는 상태나 데이터의 의미
- 주요 사용 흐름

예:

```python
class WorkflowState:
    """현재 Agent 작업의 문서 상태와 다음 실행 가능 action을 표현한다."""
```

#### 4. 함수 및 메서드 설명 규칙

새로 생성하거나 의미 있게 수정하는 모든 함수와 메서드에는 한글 docstring을 작성한다.

설명에는 함수 복잡도에 따라 다음 내용을 포함한다.

- 함수 또는 메서드의 역할
- 주요 인자의 의미
- 반환값의 의미
- 발생 가능한 주요 예외
- 파일 변경, subprocess 실행, 로그 저장 등 부수 효과

예:

```python
def find_current_unit(task_text: str) -> ImplementationUnit | None:
    """Task에서 첫 번째 미완료 작업 단위를 찾는다.

    Args:
        task_text: 분석할 Task Markdown 본문.

    Returns:
        첫 번째 미완료 작업 단위.
        UNIT이 없거나 모든 UNIT이 완료되었으면 None을 반환한다.

    Raises:
        TaskParseError: UNIT 식별자가 중복되었거나 형식이 잘못된 경우.
    """
```

짧은 함수라도 최소한 무엇을 판단하거나 반환하는지는 설명한다.

단순 property, 상수 반환 함수, 이름만으로 의미가 완전히 명확한 내부 보조 함수에 대해서도 현재 프로젝트 규칙상 docstring을 기본으로 작성하되, 의미 없는 장문의 설명은 피한다.

#### 5. 테스트 코드 설명 규칙

새로 생성하거나 수정하는 Python 테스트 파일에도 한글 module docstring을 작성한다.

각 테스트 함수 또는 테스트 메서드에는 검증 목적을 설명하는 한글 docstring을 작성한다.

예:

```python
def test_main_branch_is_blocked() -> None:
    """main 브랜치에서 Codex 구현 실행이 차단되는지 검증한다."""
```

테스트 구현 코드를 그대로 읽어주는 설명보다 다음을 명확히 한다.

- 어떤 동작을 검증하는지
- 어떤 조건에서 실패해야 하는지
- 회귀 방지 대상이 무엇인지

#### 6. 기존 코드 수정 시 적용 범위

앞으로 기존 Python 파일을 수정할 때에도 다음 규칙을 적용한다.

- 수정한 파일에 module docstring이 없으면 추가한다.
- 새로 추가한 클래스, 함수 및 메서드에는 한글 docstring을 작성한다.
- 기존 함수나 메서드를 의미 있게 수정했는데 설명이 없거나 실제 동작과 맞지 않으면 함께 보완한다.
- 오탈자 수정, import 정렬 등 동작과 무관한 사소한 변경만 한 경우 파일 전체를 문서화하기 위해 범위를 불필요하게 확장하지 않는다.
- 현재 Task와 무관한 기존 Python 파일 전체를 일괄 수정하지 않는다.
- 설명 추가를 이유로 공개 인터페이스나 동작을 변경하지 않는다.

#### 7. 한글 작성 원칙

- 설명은 한글로 작성한다.
- Python 표준 docstring 형식을 사용한다.
- 코드 동작과 일치하는 구체적인 설명을 작성한다.
- 명백한 코드 한 줄마다 인라인 주석을 추가하지 않는다.
- `#` 인라인 주석보다 module, class, function docstring을 우선한다.
- 구현 이유나 주의사항이 필요한 복잡한 부분에만 인라인 주석을 추가한다.
- 기존 영문 docstring이 있다면 삭제만 하지 말고 실제 동작을 확인해 한글로 교체하거나 필요한 내용을 보완한다.

#### 8. 공통 Agent 규칙으로 등록

이 규칙이 이후 Task에도 자동으로 적용되도록 공통 문서의 source of truth에 반영한다.

우선 반영 대상:

```text
docs/agent/task-authoring-guide.md
docs/agent/codex-instructions.md
```

문서 역할은 다음과 같이 구분한다.

```text
docs/agent/task-authoring-guide.md
→ 사람과 Agent가 Task를 작성할 때 참고하는 공통 Python 문서화 정책

docs/agent/codex-instructions.md
→ Codex가 구현과 Fix를 수행할 때 따라야 하는 실행 규칙
```

같은 내용을 여러 문서에 장황하게 복사하지 않는다.

한 문서에 상세 규칙을 작성하고, 다른 문서에서는 핵심 규칙과 source of truth 경로를 안내할 수 있다.

공통 규칙에는 최소한 다음 내용을 포함한다.

```text
Python 파일을 새로 만들거나 의미 있게 수정할 때는 파일 최상단에
해당 모듈의 역할을 설명하는 한글 module docstring을 작성한다.

새로 만들거나 의미 있게 수정하는 클래스, 함수 및 메서드에는
역할, 입력, 반환값, 주요 예외와 부수 효과를 설명하는 한글 docstring을 작성한다.

테스트 파일과 테스트 함수에도 검증 목적을 설명하는 한글 docstring을 작성한다.

현재 Task와 관계없는 기존 Python 파일까지 문서화만을 목적으로
일괄 수정하지 않는다.
```

#### 9. Agent 프롬프트 반영

향후 생성되는 다음 프롬프트에도 공통 문서화 규칙이 전달되어야 한다.

```text
codex-implement
codex-implement-unit
codex-fix
```

프롬프트에 전체 규칙을 매번 길게 복사하기보다 다음 형태로 제공한다.

```text
Python 문서화 규칙:
- docs/agent/task-authoring-guide.md의 Python 문서화 정책을 따른다.
- 새로 생성하거나 의미 있게 수정한 Python 모듈, 클래스, 함수 및
  메서드에는 한글 docstring을 작성한다.
```

Antigravity Review 프롬프트에는 다음 검토 항목을 추가한다.

```text
- 새로 생성하거나 의미 있게 수정한 Python 코드에 한글 module,
  class, function 및 method docstring이 있는지 확인한다.
- docstring이 실제 구현과 일치하는지 확인한다.
```

#### 10. 신규 Task 템플릿 처리

이 규칙은 모든 Python 작업에 적용되는 공통 정책이므로 신규 Task마다 반복 작성하지 않는다.

`new_agent_task.sh`가 생성하는 Task 템플릿에는 긴 문구를 추가하지 않는다.

Task에서는 다음 경우에만 작업별 문서화 조건을 별도로 작성한다.

- 특정 알고리즘 설명이 필요함
- 공개 API docstring 형식이 별도로 정해짐
- 외부 사용자용 예제나 사용법이 필요함
- 특정 모듈의 설계 배경을 상세히 기록해야 함

그 외에는 공통 Agent 가이드가 자동으로 적용된다.

#### 11. 검증

이번 브랜치에서 변경된 Python 파일을 확인한다.

```bash
git diff --name-only --diff-filter=ACM -- '*.py'
```

각 대상 파일에 대해 다음을 확인한다.

- module docstring 존재
- 클래스 docstring 존재
- 함수 및 메서드 docstring 존재
- 테스트 함수의 검증 목적 설명
- 한글로 작성됨
- 설명이 실제 동작과 일치함
- 불필요한 동작 변경 없음

공통 규칙 반영 여부를 확인한다.

```bash
grep -n "한글.*docstring\|module docstring\|Python 문서화" \
  docs/agent/task-authoring-guide.md \
  docs/agent/codex-instructions.md
```

프롬프트 생성 결과에도 문서화 규칙이 포함되는지 확인한다.

```bash
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh codex-fix
```

Python 코드 변경 후 회귀 검증을 실행한다.

```bash
python -m pytest
python -m unittest discover -s tests
python -m compileall app scripts tests
python -c "import scripts.agent_workflow"
git diff --check
```

### FIX-02. 실제 pytest 검증 결과 반영

- [x] 적용 및 재검증 완료

기존 Verification 문서에 pytest 미설치 또는 실행 미완료 상태가 남아 있다면, 사람이 실제로 실행한 다음 결과를 반영한다.

실행 명령:

```bash
python -m pytest --version
python -m pytest
python -m unittest discover -s tests
```

실제 결과:

```text
pytest 9.1.1
171 passed in 3.15s

Ran 171 tests in 2.497s
OK
```

`unittest` 실행 중 출력되는 argparse `usage:` 및 `error:` 메시지는 잘못된 입력을 검증하는 테스트에서 발생한 예상 출력이며, 최종 결과가 `OK`임을 함께 기록한다.

과거에 pytest가 없어서 미수행 또는 실패로 기록한 항목은 실제 결과에 맞게 갱신한다. 과거 기록을 숨기지 말고, 재검증을 통해 통과했다는 형태로 남긴다.

Verification 문서를 갱신한 뒤 status 명령에서 더 이상 오래된 실패 상태가 표시되지 않는지 확인한다.

### FIX-03. Verification 현재 상태 판정의 문자열 오탐 수정

- [x] 적용 및 검증 완료

실제 pytest와 unittest가 모두 통과했고 Approved Fixes 적용 및 재리뷰까지 완료되었지만, 다음 status 결과가 출력되었다.

```text
Verification:
- failed

Suggested next action:
- antigravity-review
```

원인은 `scripts/agent_workflow/state.py`가 Verification 문서 전체에서 다음 문자열을 단순 검색하기 때문이다.

```python
verification = "failed" if "status: failed" in text else "present"
```

Verification 문서에는 과거 실패 상태가 현재 상태를 오염시키지 않는다는 설명이 존재한다.

```text
과거 pytest 미설치 기록의 `Status: failed`가 현재 상태를 오염시키지 않으며...
```

현재 구현은 이 설명 속 `Status: failed`를 실제 현재 실패 상태로 오인한다.

#### 수정 요구사항

Verification 문서 전체에서 `status: failed` 문자열을 검색해 현재 상태를 판정하지 않는다.

Verification 문서에 명시적인 현재 상태 section을 사용한다.

권장 형식:

```markdown
## Verification Status

passed
```

지원할 상태는 최소한 다음과 같다.

```text
passed
failed
pending
```

필요하다면 문서 존재 여부를 표현하기 위해 다음 상태를 함께 사용할 수 있다.

```text
missing
present
```

상태 parser는 `## Verification Status` section의 값만 읽어 현재 Verification 상태를 판정해야 한다.

다음 내용은 현재 실패 판정에 영향을 주지 않아야 한다.

- 과거 실패 이력
- superseded 상태
- 예제 코드
- 테스트 설명
- `Status: failed`라는 문자열이 포함된 일반 문장
- “명시적인 verification 실패를 차단한다”와 같은 기능 설명

#### 기존 문서 호환

기존 Verification 문서에 `Verification Status` section이 없을 수 있으므로 다음과 같이 호환한다.

```text
Verification 문서 없음
→ missing

Verification 문서는 있지만 Verification Status section 없음
→ present

Verification Status: passed
→ passed

Verification Status: failed
→ failed

Verification Status: pending
→ pending
```

기존 문서를 일괄 변환하지 않는다.

현재 브랜치의 Verification 문서에는 실제 검증 결과에 맞게 다음 상태를 추가한다.

```markdown
## Verification Status

passed
```

#### 다음 action 판정

현재 상태가 다음과 같을 때:

```text
Verification: passed
Review: present
Approved fixes: applied
재리뷰 결과: APPROVED
```

다음 권장 action은 다시 `antigravity-review`가 아니라 PR 준비 단계여야 한다.

저장소의 기존 action 이름에 맞춰 다음 중 적절한 값을 사용한다.

```text
pr-draft
ready-for-pr
```

재리뷰 완료 여부를 현재 Review 문서 구조로 신뢰성 있게 판단하기 어렵다면, 최소한 Verification이 `passed`인 상태를 `failed`로 오인하여 Antigravity Review를 반복 권장하지 않도록 수정한다.

#### 테스트 추가

다음 회귀 테스트를 추가한다.

1. Verification 문서에 다음 문장이 있어도 실패로 판정하지 않는다.

```text
과거 `Status: failed` 기록은 이후 검증으로 superseded되었다.
```

2. 예제 코드에 `status: failed`가 있어도 실패로 판정하지 않는다.

3. `Verification Status`가 `passed`이면 `passed`로 판정한다.

4. `Verification Status`가 `failed`이면 `failed`로 판정한다.

5. Verification 문서는 있지만 명시적 상태 section이 없으면 기존 호환 상태로 판정한다.

6. Verification 문서가 없으면 누락 상태로 판정한다.

7. 현재 브랜치 상태에서 status 명령이 더 이상 다음과 같이 출력되지 않는다.

```text
Verification:
- failed
```

#### 문서 갱신

다음 문서에서 Verification 상태 표기 방법을 설명한다.

```text
docs/agent/usage-guide.md
docs/agent/verification-gates.md
```

신규 Task의 Verification 문서 템플릿에도 명시적인 상태 section을 추가하는 방안을 적용한다.

예:

```markdown
## Verification Status

pending
```

검증이 실제로 통과한 뒤에만 `passed`로 변경한다.

#### 검증 명령

```bash
python -m pytest tests/test_agent_workflow_state.py -v
python -m pytest
python -m unittest discover -s tests
python -m compileall app scripts tests
git diff --check
scripts/agent_next_step.sh status
```

최종 status에서 다음을 확인한다.

```text
Verification:
- passed

Review:
- present

Approved fixes:
- applied
```

다음 권장 action은 현재 workflow 상태에 맞는 PR 준비 단계여야 한다.

- [x] FIX-04. 테스트 결과 불일치 재검증 및 PR 문서 갱신
  - `python -m pip install -r requirements-dev.txt`로 개발 의존성을 확인한다.
  - `python -m pytest`와 `python -m unittest discover -s tests`를 다시 실행한다.
  - 실제 수집 수, 통과 수, 실패 및 오류 수를 Verification에 기록한다.
  - CodeRabbit이 보고한 100 tests / 12 errors가 재현되면 오류 원인을 수정한다.
  - 재현되지 않고 177건이 통과하면 실행 환경과 Python·pytest 버전을 PR 문서에 명시한다.
  - 실제 결과와 다른 테스트 수를 문서에 유지하지 않는다.

- [x] FIX-05. Verification 상태와 다음 권장 action의 계약 일치
  - Verification이 `failed` 또는 `pending`일 때 `antigravity-review`를 추천하지 않는다.
  - status에는 먼저 Verification 문제를 해결해야 한다는 실행 가능한 안내를 출력한다.
  - `suggested_action`이 반환하는 실행 action은 해당 상태에서 gate를 통과할 수 있어야 한다.
  - 실패, pending, passed 상태별 회귀 테스트를 추가한다.
  - 새로 생성하거나 수정한 Python 코드에는 한글 docstring을 작성한다.

- [x] FIX-06. `docs/tasks/main.md` 포인터 검증 강화
  - Task 파일명의 단순 문자열 포함 여부로 포인터를 판정하지 않는다.
  - `docs/tasks/main.md`에서 실제 Markdown link target을 추출한다.
  - 정규화된 link target이 현재 Task 파일 경로와 정확히 일치할 때만 통과한다.
  - 본문 설명이나 코드 예시에 Task 파일명만 포함된 경우에는 차단한다.
  - 정상 link, 잘못된 link, 일반 본문 오탐에 대한 테스트를 추가한다.
  - 새로 생성하거나 수정한 Python 코드에는 한글 docstring을 작성한다.

- [x] FIX-07. 환경변수로 지정한 Agent binary 검증
  - `AGENT_CODEX_BIN`과 `AGENT_ANTIGRAVITY_BIN`이 설정된 경우 gate에서 존재 여부와 실행 가능 여부를 확인한다.
  - 경로가 디렉터리이거나 존재하지 않거나 실행할 수 없으면 한글 `GateError`를 발생시킨다.
  - command 이름이면 PATH에서 찾을 수 있는지 확인한다.
  - 정상 executable과 잘못된 경로에 대한 테스트를 추가한다.
  - Secret, token 또는 credential 값은 출력하지 않는다.

- [x] FIX-08. 저장소 외부 로그 경로의 안전한 직렬화
  - `log_directory`가 저장소 내부일 때는 저장소 상대 경로를 기록한다.
  - 저장소 외부일 때는 `relative_to()` 예외를 발생시키지 않고 정규화된 절대 경로를 기록한다.
  - 경로 표시 실패로 Agent 실행 결과 저장이 실패하지 않게 한다.
  - 저장소 내부 및 외부 log directory 테스트를 추가한다.
  - 새로 생성하거나 수정한 Python 코드에는 한글 docstring을 작성한다.

- [x] FIX-09. 문서 링크의 저장소 상대 경로 정규화
  - Antigravity Review 문서의 `~/news-lab/...` 링크를 저장소 상대 Markdown link로 변경한다.
  - `file://` 절대 URL은 사용하지 않는다.
  - 링크 변경 외에 Review 내용과 판정은 수정하지 않는다.

## Rejected or Deferred Suggestions

### DEFERRED-01. pytest 미설치 시 자동 설치

Antigravity가 제안한 다음 기능은 이번 수정에서 보류한다.

```text
pytest가 없을 때 pip install -r requirements-dev.txt를 자동 실행
```

이유:

- 의존성 설치는 로컬 환경을 변경한다.
- status나 Agent 실행이 패키지를 묵시적으로 설치하면 예상하지 못한 환경 변경이 발생할 수 있다.
- 현재는 한글 가이드에서 설치 명령을 안내하는 것으로 충분하다.

필요하다면 향후 다음처럼 자동 설치가 아닌 안내 기능으로 검토한다.

```text
pytest를 찾을 수 없음
→ python -m pip install -r requirements-dev.txt 안내
```

## Applied Changes

- FIX-01:
  - `scripts/agent_workflow/*.py` 7개 파일에 역할, 입력·출력, 예외와 부수 효과를 설명하는 한글 module/class/function/method docstring을 추가했다.
  - `tests/test_agent_*.py` 5개 파일에 한글 module/class/helper/test method docstring을 추가했다.
  - `docs/agent/task-authoring-guide.md`에 상세 Python 문서화 정책을 추가했다.
  - `docs/agent/codex-instructions.md`에 핵심 실행 규칙과 상세 정책 링크를 추가했다.
  - prompt-only와 직접 실행 prompt에 Python 문서화 규칙을 추가하고 Antigravity Review 항목에 docstring 일치 여부 확인을 추가했다.
- FIX-02:
  - pytest 9.1.1 설치 상태와 전체 171개 test 통과 결과를 Verification에 반영했다.
  - 과거 pytest 미설치 실패는 삭제하지 않고 재검증으로 대체된 historical result로 표시했다.
- FIX-03:
  - Verification 문서 전체 문자열 검색을 제거하고 `## Verification Status` section의 `passed`, `failed`, `pending`만 현재 상태로 해석하도록 변경했다.
  - 문서가 없으면 `missing`, 상태 section이 없는 기존 문서는 `present`로 호환 처리했다.
  - 과거 실패 문장과 fenced code 예시가 현재 실패 상태를 오염시키지 않는 회귀 테스트를 추가했다.
  - Verification `passed`, Review `present`, Approved Fixes `applied` 상태에서는 `pr-draft`를 권장하도록 변경했다.
  - 신규 Verification 템플릿과 현재 문서, 사용 가이드 및 verification gate에 명시적 상태 section을 반영했다.
- FIX-04:
  - `requirements-dev.txt`의 모든 dependency가 현재 Python 3.11.7 환경에 이미 설치되어 있음을 확인했다.
  - `pip install`은 dependency 확인 후 pyenv shim rehash 권한 문제로 exit 1이었으며 환경 변경은 발생하지 않았다.
  - pytest 9.1.1에서 177개, unittest에서 177개 test가 통과해 100 tests / 12 errors는 재현되지 않았다.
  - 실제 Python·pytest 버전과 test 수를 Verification 및 PR 문서에 반영했다.
- FIX-05:
  - Review가 존재하는 `failed` 또는 `pending` Verification 상태에서는 `antigravity-review` 대신 `resolve-verification`을 안내하도록 변경했다.
  - status에 먼저 검증 문제를 해결하고 실제 결과를 기록하라는 한글 안내를 추가했다.
  - Antigravity Review gate도 `failed`와 `pending` 상태를 모두 차단하도록 계약을 일치시켰다.
  - failed, pending, passed 상태와 gate 동작 회귀 테스트를 추가했다.
- FIX-06:
  - `main.md`의 파일명 문자열 포함 검사를 제거하고 fenced code 밖의 실제 Markdown link target을 추출하도록 변경했다.
  - pointer 문서 기준으로 정규화한 link 경로가 현재 Task 경로와 정확히 일치할 때만 통과한다.
  - 정상 link, 잘못된 link, 일반 본문 파일명과 fenced code 예시 오탐 회귀 테스트를 추가했다.
- FIX-07:
  - `AGENT_CODEX_BIN`과 `AGENT_ANTIGRAVITY_BIN`의 경로 또는 command 이름을 실행 전에 검증하도록 변경했다.
  - 경로는 실행 가능한 일반 파일인지 확인하고 command 이름은 PATH에서 조회한다.
  - 누락 경로와 디렉터리는 환경변수 값을 노출하지 않는 한글 GateError로 차단한다.
  - 정상 executable, 잘못된 경로, 디렉터리와 PATH command 회귀 테스트를 추가했다.
- FIX-08:
  - repository 내부 로그는 기존처럼 상대 경로로 기록하고 외부 로그는 정규화된 절대 경로로 기록하도록 변경했다.
  - `relative_to()` 실패가 Agent 실행 결과와 `result.json` 저장을 중단하지 않도록 별도 직렬화 helper를 추가했다.
  - repository 외부 로그 디렉터리 회귀 테스트를 추가했다.
- FIX-09:
  - Antigravity Review의 `~/news-lab/...` Markdown link target을 `docs/reviews/` 기준 저장소 상대 경로로 변경했다.
  - Review 본문, finding과 verdict는 수정하지 않았고 `file://` 절대 URL도 추가하지 않았다.
- 승인 Fix 적용 외 application 동작, API, DB, K3s 및 production workflow는 변경하지 않았다.

## Verification Required

### Python docstring 존재 확인

이번 브랜치에서 추가하거나 수정한 Python 파일을 확인한다.

```bash
git diff --name-only --diff-filter=ACM -- '*.py'
```

각 대상 파일에서 다음을 확인한다.

- 파일 최상단 module docstring
- 클래스 docstring
- 함수 및 메서드 docstring
- 한글 설명
- 설명과 실제 코드 동작의 일치

자동 검사 도구를 추가하지 않는다면 코드 리뷰로 확인하고, 확인하지 않은 항목을 자동 검증 완료로 기록하지 않는다.

### 신규 하네스 테스트

```bash
python -m pytest \
  tests/test_agent_task_parser.py \
  tests/test_agent_workflow_state.py \
  tests/test_agent_workflow_gates.py \
  tests/test_agent_workflow_runner.py \
  tests/test_agent_workflow_cli.py \
  -v
```

### 전체 pytest

```bash
python -m pytest
```

기대 결과:

```text
187 passed
```

테스트 수가 docstring 전용 테스트 추가 등으로 변경되면 실제 실행 결과를 기록한다.

### 기존 unittest 호환

```bash
python -m unittest discover -s tests
```

기대 결과:

```text
OK
```

### Python 정적 검증

```bash
python -m compileall app scripts tests
python -c "import scripts.agent_workflow"
```

### Shell 문법 검증

```bash
bash -n scripts/new_agent_task.sh
bash -n scripts/agent_next_step.sh
bash -n scripts/agent_run.sh
```

### Diff 검증

```bash
git diff --check
git diff --stat
git status --short --branch
```

### 상태 재확인

Verification 문서 갱신 후 실행한다.

```bash
scripts/agent_run.sh status
```

확인 사항:

- `Verification: failed`가 과거의 pytest 미수행 기록 때문에 남아 있지 않은지
- Review가 존재하는지
- Approved Fixes가 존재하는 상태로 표시되는지
- 다음 권장 action이 현재 workflow 상태와 일치하는지

status가 계속 `Verification: failed`를 출력하면 임의로 성공 처리하지 말고, 어떤 문구나 상태를 실패로 판정했는지 조사해 수정한다.
