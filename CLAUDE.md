# CLAUDE.md

@AGENTS.md

## Claude Code 역할

`AGENTS.md`의 "역할별 지침"에는 Codex와 Antigravity만 정의되어 있다.
**Claude Code는 Codex 지침(`docs/agent/codex-instructions.md`)을 따른다.**

나머지 규칙(WIP 1, 안전 규칙, 구현 규칙, 검증 원칙, workflow artifact 경로)은
`AGENTS.md`와 완전히 동일하다. 이 문서는 그 위에 Claude Code 전용 사항만 더한다.

## 하네스는 수정하지 않는다

`scripts/agent_run.sh`는 Codex/Gemini CLI 전용 adapter다.
**Claude Code에서는 실행하지 않는다.**

대신 `scripts/agent_next_step.sh`의 prompt-only 출력과 상태 확인만 사용한다.

```bash
scripts/agent_next_step.sh status            # 현재 branch의 workflow 상태
scripts/agent_next_step.sh codex-implement   # 구현 prompt 출력 → 복사해서 사용
```

전체 subcommand 목록은 스크립트를 직접 확인한다.
Claude adapter 추가는 **별도 후속 task**이며, 이번 작업 범위에서 하네스를 고치지 않는다.

## 세션 규칙

- 파일을 수정하기 전에 `docs/tasks/<safe-branch>.md`를 먼저 읽는다. 없으면 사람에게 확인한다.
- **WIP 1을 지킨다.** 한 작업 단위(조사 → 변경 → 문서화 → 검증 → checklist 갱신)를
  끝내기 전에 다음 단위로 넘어가지 않는다.
- `AGENTS.md`의 안전 규칙(금지 command, secret 취급, production 검증)을 그대로 따른다.
- **실행하지 않은 검증을 완료로 기록하지 않는다.** 미수행 / 환경 제약 실패 /
  운영 반영 후 확인 필요 / 사람이 수행 필요를 구분해 적는다.
- 새 Python module·class·function·test에는 한글 docstring을 쓴다
  (`docs/agent/task-authoring-guide.md`의 Python 문서화 정책).

## 코드 설명 방식

이 저장소의 코드는 상당 부분 agent가 작성했고, 소유자가 그 코드를 직접 설명할 수
있는 상태로 만드는 것이 현재 최우선 목표다. 따라서 변경을 설명할 때:

- "무엇을 하는가"가 아니라 **"왜 이렇게 짰는가 / 이 조건이 없으면 어떤 입력에서 깨지는가"**를 설명한다.
- 기존 코드를 요약해 달라는 요청에는 동작 나열 대신 **설계 판단과 그 근거**를 먼저 답한다.
- 이해 여부는 테스트로 확인한다. 설명만 하고 넘어가지 말고, 그 이해를 고정하는 테스트를 제안한다.

## 관련 저장소

| 저장소 | 역할 |
| --- | --- |
| `news-lab` | 이 저장소. FastAPI backend, pipeline script, K3s manifest, 운영 문서 |
| `news-lab-web` | Next.js frontend (별도 저장소) |
| `news-lab-exporter` | Go 기반 Prometheus exporter. 이 저장소의 DB를 **read-only**로 읽는다 (별도 저장소) |

backend task 범위에 frontend와 exporter 저장소를 포함하지 않는다.
exporter가 읽는 table의 schema를 바꿀 때는 exporter 쪽 영향도 함께 확인 대상으로 기록한다.
