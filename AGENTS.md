# AGENTS.md

## 프로젝트

NewsLab은 RSS 기사를 수집하고 원문과 주제 데이터를 PostgreSQL/Supabase에
저장한 뒤 FastAPI로 제공하는 backend 프로젝트다. 운영 환경은 Oracle Cloud
A1 node의 K3s cluster다.

## 먼저 읽을 문서

모든 작업에서 다음 순서를 따른다.

1. 현재 task: `docs/tasks/<safe-branch>.md`
2. 공통 workflow: [docs/agent/backend-workflow.md](docs/agent/backend-workflow.md)
3. 역할별 지침:
   - Codex: [docs/agent/codex-instructions.md](docs/agent/codex-instructions.md)
   - Antigravity: [docs/agent/antigravity-review.md](docs/agent/antigravity-review.md)
4. 작업에 필요한 문서만 선택:
   - Architecture index: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
   - Runbook index: [docs/RUNBOOK.md](docs/RUNBOOK.md)
5. 검증 기준: [docs/agent/verification-gates.md](docs/agent/verification-gates.md)
6. 금지 및 사람 통제 작업:
   [docs/agent/forbidden-commands.md](docs/agent/forbidden-commands.md)

Task file이 chat prompt와 충돌하면 task file을 우선한다.

## WIP 1

한 번에 하나의 작업 단위만 진행한다.

```text
작업 단위 완료
= 조사 → 변경 → 문서화 → 검증 → checklist 갱신
```

현재 작업 단위가 완료되지 않았으면 다음 작업 단위로 이동하지 않는다. 새로
발견한 문제는 현재 blocker, 현재 범위의 결함, 후속 작업 후보, 과거 기록 중
하나로 분류한다.

## 안전 규칙

- `main`에 직접 push하지 않는다.
- 명시적 요청 없이 `git push`, `git merge`를 실행하지 않는다.
- `kubectl apply`, `kubectl delete`, `kubectl patch`, `kubectl edit`,
  `kubectl rollout`, Helm 변경, `docker push`를 실행하지 않는다.
- Supabase SQL과 production migration을 실행하지 않는다.
- secret, `.env`, kubeconfig, credential, SSH key, token을 수정하거나 값을
  문서에 기록하지 않는다.
- Kubernetes manifest는 task가 명시적으로 요구할 때만 수정한다.
- production verification은 사람이 제공한 실제 결과 없이 완료로 표시하지
  않는다.
- DB에 쓰는 collector/extractor/pipeline script는 명시적 승인 없이 실행하지
  않는다.
- 파일을 삭제할 때는 이유를 먼저 설명한다.
- 변경은 작고 review 가능하게 유지한다.

세부 구분은 [금지 및 사람 통제 작업](docs/agent/forbidden-commands.md)을 따른다.

## 구현 규칙

- FastAPI router는 `app/routers/`에 둔다.
- 새 router는 `app/main.py`에 등록한다.
- DB query는 SQLAlchemy `text()`와 bind parameter를 우선한다.
- DB schema 변경은 `db/migrations/`에 SQL file로 추가한다.
- dependency 추가 시 `requirements.txt`를 갱신한다.
- 명시적 요청이 없으면 큰 refactor를 하지 않는다.
- frontend repository와 frontend 문서는 backend task 범위에 포함하지 않는다.

## Workflow artifact

| 목적 | 경로 |
| --- | --- |
| Task source of truth | `docs/tasks/` |
| Review finding | `docs/reviews/` |
| 사람이 승인한 fix | `docs/fixes/` |
| 실제 검증 기록 | `docs/verification/` |
| PR draft | `docs/pr/` |
| Devlog draft | `docs/devlog/` |
| Architecture decision | `docs/adr/` |

Review 결과만으로 구현을 수정하지 않는다. 사람이 승인한 항목이
`docs/fixes/<safe-branch>-approved-fixes.md`에 기록된 경우에만 적용한다.
PR과 devlog의 검증 주장은 `docs/verification/`을 source of truth로 사용한다.

## 검증 원칙

- Task 문서에는 checklist가 있어야 한다.
- 실제 완료한 항목만 체크한다.
- 실행한 command와 실제 결과만 verification 문서에 기록한다.
- 미수행, 환경 제약 실패, 운영 반영 후 확인 필요, 사람이 수행 필요를 구분한다.
- 코드 또는 pipeline 변경은 가능한 범위에서 입력부터 저장과 조회까지
  end-to-end로 검증한다.
- 운영 적용이 필요한 검증은 실행하지 않고 사람 수행 항목으로 남긴다.
- 자동 test/lint가 없는 영역을 통과한 것처럼 쓰지 않는다.

## 주요 구성

- FastAPI: `app/main.py`, `app/routers/`
- PostgreSQL/Supabase: `app/database.py`, `db/migrations/`
- RSS collector: `scripts/collect_rss.py`
- Raw extractor: `scripts/extract_raw_articles.py`
- Daily topic pipeline: `scripts/run_daily_topic_pipeline.py`
- Kubernetes manifest: `k8s/`

현재 구조와 데이터 흐름은 [Architecture index](docs/ARCHITECTURE.md), 운영
절차는 [Runbook index](docs/RUNBOOK.md)에서 필요한 문서만 선택해 확인한다.
