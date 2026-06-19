# Task: backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## Goal

NewsLab backend repository에서 Codex와 Antigravity가 작업할 때 읽어야 하는 문서의 크기와 범위를 줄이고, 작업 진행 및 검증 절차를 명확히 한다.

현재 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`가 길어지면서 다음 문제가 발생하고 있다.

- Agent가 작업마다 현재 범위와 직접 관련 없는 문서를 과도하게 읽는다.
- 현재 운영 기준, 과거 작업 이력, 검증 기록이 하나의 문서에 혼재한다.
- Codex 구현과 Antigravity review에 필요한 context를 작게 전달하기 어렵다.
- 문서가 영어 중심으로 작성되어 있어 사용자가 직접 검토하고 유지보수하는 비용이 크다.
- 작업 단위별 완료 조건과 중간 검증 gate가 명확하지 않다.
- 기능 구현, 문서 작성, 검증을 완료하기 전에 다음 작업으로 넘어갈 가능성이 있다.

이번 작업에서는 backend repository의 현재 운영 기준 문서를 한국어로 정리하고, 긴 architecture/runbook 문서를 index와 세부 문서로 분리한다.

또한 다음 원칙을 backend agent workflow에 명문화한다.

```text
WIP 1
= 한 번에 하나의 작업 단위만 진행한다.

작업 단위 완료
= 조사 → 변경 → 문서화 → 검증 → checklist 갱신까지 완료한다.
```

이번 작업은 완전 자동화된 agent harness를 구현하는 작업이 아니다.

현재의 문서 기반 agent-assisted development workflow를 명확히 정의하고, 이후 검증 script와 자동 gate를 추가할 수 있는 기반을 마련하는 작업이다.

## Scope

### 1. Backend repository만 정리

대상 repository는 다음과 같다.

```text
/Users/seochanjin/workspace/NewsLab/news-lab
```

frontend repository와 frontend 문서는 이번 작업에서 다루지 않는다.

### 2. Architecture 문서 경량화

기존 `docs/ARCHITECTURE.md`는 삭제하지 않고 다음 역할의 index 문서로 축소한다.

```text
- NewsLab backend 전체 구조 요약
- 현재 운영 구성 요약
- 주요 데이터 흐름 요약
- 세부 architecture 문서 링크
```

긴 설명은 작업 범위에 따라 다음과 같은 세부 문서로 분리한다.

```text
docs/architecture/overview.md
docs/architecture/backend-api.md
docs/architecture/database.md
docs/architecture/pipeline.md
docs/architecture/k3s-runtime.md
docs/architecture/domains.md
```

실제 기존 문서 내용을 조사한 뒤 필요한 문서만 생성한다. 문서를 만들기 위해 내용을 인위적으로 중복하지 않는다.

### 3. Runbook 문서 경량화

기존 `docs/RUNBOOK.md`는 삭제하지 않고 다음 역할의 index 문서로 축소한다.

```text
- 일상 운영 점검에 필요한 핵심 command
- 장애 발생 시 첫 확인 순서
- 세부 runbook 문서 링크
- human-controlled operation 안내
```

긴 운영 절차는 작업 범위에 따라 다음과 같은 세부 문서로 분리한다.

```text
docs/runbooks/routine-check.md
docs/runbooks/backend-deploy.md
docs/runbooks/cronjobs.md
docs/runbooks/database-check.md
docs/runbooks/troubleshooting.md
```

실제 기존 문서 내용을 기준으로 필요한 문서만 생성한다.

### 4. Backend agent workflow 문서 추가

Backend 작업에서 Codex와 Antigravity가 공통으로 따라야 할 workflow를 문서화한다.

예상 문서:

```text
docs/agent/backend-workflow.md
docs/agent/codex-instructions.md
docs/agent/antigravity-review.md
docs/agent/verification-gates.md
docs/agent/forbidden-commands.md
```

문서 수 자체를 늘리는 것이 목적이 아니다. 다음 55차부터 agent가 실제로 참조할 수 있도록 역할과 읽기 순서를 명확히 한다.

### 5. WIP 1 원칙 문서화

Backend agent workflow에서는 한 번에 하나의 작업 단위만 진행한다.

하나의 작업 단위는 다음 과정을 모두 포함한다.

```text
1. 관련 문서와 코드 위치 조사
2. 현재 작업 단위 변경
3. 필요한 문서 작성 또는 갱신
4. 정적 검증 및 테스트 실행
5. verification 문서에 command와 결과 기록
6. task checklist 갱신
7. 완료 조건 확인
8. 다음 작업 단위로 이동
```

현재 작업 단위가 완료되지 않은 상태에서 다음 작업 단위로 이동하지 않는다.

새로운 문제가 발견되면 즉시 범위를 확장하지 않고 다음 중 하나로 분류한다.

```text
- 현재 작업의 blocker
- 이번 작업 범위에서 처리할 결함
- 후속 작업 후보
- 과거 기록으로 유지할 항목
```

### 6. Verification gate 문서화

Backend 작업은 최소한 다음 gate를 따른다.

#### Gate 1. 작업 전 상태 확인

- 현재 branch 확인
- working tree 상태 확인
- 관련 파일 위치 검색
- task scope 확인
- 변경 금지 영역 확인

#### Gate 2. 작업 단위 완료 확인

- 현재 작업 단위의 변경 완료
- 필요한 문서 갱신
- 정적 검증 또는 테스트 실행
- task checklist 갱신
- 실패 또는 미수행 항목 기록

#### Gate 3. 전체 변경 범위 확인

- `git diff --stat`
- `git diff --check`
- `git diff --name-only`
- 범위를 벗어난 파일 변경 여부 확인
- 기존 운영 기준과 신규 문서의 충돌 여부 확인

#### Gate 4. End-to-end 검증 확인

코드 또는 pipeline 변경 작업은 가능한 범위에서 end-to-end 흐름을 검증해야 한다.

예:

```text
입력 데이터
→ application 또는 script 처리
→ DB 저장
→ API 또는 조회 command로 결과 확인
```

운영 적용이 필요한 검증은 agent가 직접 실행하지 않는다. 대신 다음 중 하나로 명시한다.

```text
- 로컬 검증 완료
- dry-run 완료
- 운영 검증 대기
- 사람이 수행 필요
```

이번 54차는 문서 구조 변경 작업이므로 end-to-end 검증 대신 다음 흐름을 확인한다.

```text
index 문서
→ 세부 문서 링크
→ 세부 운영 절차
→ agent workflow 및 verification gate 참조
```

#### Gate 5. 고위험 작업 중단

Agent는 고위험 작업이 필요한 시점에서 자동 실행하지 않고 중단한다.

중단 시 다음 내용을 기록한다.

```text
- 현재까지 완료한 작업
- 필요한 고위험 작업
- 사람이 실행해야 하는 command
- 실행 후 확인할 결과
- 실패 시 rollback 또는 troubleshooting 문서
```

### 7. Checklist 운영 방식 정리

모든 backend task 문서는 checklist를 포함해야 한다.

Agent는 실제 완료한 항목만 체크한다.

실행하지 않은 검증은 완료 처리하지 않고 다음과 같이 표시한다.

```text
- 미수행
- 환경 제약으로 실패
- 운영 반영 후 확인 필요
- 사람이 수행 필요
```

이번 task의 checklist는 다음과 같다.

```md
## Checklist

- [x] 작업 전 branch와 working tree 확인
- [x] `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 역할 확인
- [x] 기존 architecture 문서의 주요 섹션과 줄 수 확인
- [x] 기존 runbook 문서의 주요 섹션과 줄 수 확인
- [x] 현재 운영 기준과 과거 기록의 혼재 구간 확인
- [x] architecture 분리 계획 확정
- [x] `docs/ARCHITECTURE.md` index화
- [x] 필요한 `docs/architecture/*` 세부 문서 작성
- [x] architecture 문서 링크 검증
- [x] runbook 분리 계획 확정
- [x] `docs/RUNBOOK.md` index화
- [x] 필요한 `docs/runbooks/*` 세부 문서 작성
- [x] runbook 문서 링크 검증
- [x] backend agent workflow 문서 작성
- [x] WIP 1 원칙 문서화
- [x] verification gate 문서화
- [x] forbidden command와 human-controlled command 구분
- [x] 신규 기준 문서를 한국어로 작성
- [x] 기존 과거 문서를 불필요하게 번역하지 않음
- [x] 운영 기준의 중복 또는 충돌 확인
- [x] `git diff --check` 통과
- [x] 변경 파일이 문서 범위에 한정됨을 확인
- [x] verification 문서 작성
- [x] PR 문서 작성
- [x] devlog 작성
- [x] 후속 자동화 후보 정리
```

### 8. 한국어 기준 문서 정리

다음 문서는 한국어를 기본 언어로 정리한다.

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/architecture/*
docs/runbooks/*
docs/agent/*
```

명령어, 파일명, Kubernetes resource명, API path, 기술 고유명사는 원문 표기를 유지할 수 있다.

과거 이력을 보존하는 다음 문서는 대규모 번역하지 않는다.

```text
docs/tasks/*
docs/verification/*
docs/devlog/*
docs/reviews/*
docs/fixes/*
docs/pr/*
```

단, 이번 54차에 새로 작성하는 task, verification, PR, devlog 문서는 한국어로 작성한다.

## Do not change

다음 항목은 이번 작업 범위에서 변경하지 않는다.

### Repository 및 기능 범위

- frontend repository
- frontend source code
- frontend documentation
- backend application source code
- API router와 endpoint 구현
- collector, extractor, topic, summary script
- embedding 관련 코드와 문서 설계
- daily pipeline 구현
- RSS source 확장

### Database

- DB schema
- table
- column
- index
- constraint
- migration
- Supabase SQL
- seed data
- production data
- `DATABASE_URL`
- database credential

### Infrastructure 및 배포

- `k8s/*.yaml`
- K3s resource
- CronJob manifest
- Deployment manifest
- Service 및 Ingress
- Dockerfile
- Docker Compose
- GitHub Actions workflow
- domain 및 TLS
- Secret 및 ConfigMap
- node label과 scheduling 설정

### 환경 및 민감정보

- `.env`
- `.env.*`
- kubeconfig
- API key
- token
- password
- private key
- secret 값

### 실행하지 않을 명령

Agent는 다음 명령과 이에 준하는 production-impacting command를 실행하지 않는다.

```text
git push
git merge
gh pr merge
kubectl apply
kubectl delete
kubectl patch
kubectl edit
kubectl rollout restart
helm install
helm upgrade
helm uninstall
docker push
production DB migration
Supabase 운영 SQL 실행
```

문서에 운영 명령을 기록할 수는 있지만 다음 조건을 만족해야 한다.

- 사람이 실행해야 하는 명령임을 명시한다.
- 검증 command와 변경 command를 구분한다.
- rollback 또는 확인 절차를 함께 제공한다.
- 실제 실행 결과처럼 작성하지 않는다.

## Expected files

실제 기존 문서 구조를 조사한 뒤 필요한 파일만 수정하거나 생성한다.

예상 변경 파일은 다음과 같다.

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

Architecture 분리 후보:

```text
docs/architecture/overview.md
docs/architecture/backend-api.md
docs/architecture/database.md
docs/architecture/pipeline.md
docs/architecture/k3s-runtime.md
docs/architecture/domains.md
```

Runbook 분리 후보:

```text
docs/runbooks/routine-check.md
docs/runbooks/backend-deploy.md
docs/runbooks/cronjobs.md
docs/runbooks/database-check.md
docs/runbooks/troubleshooting.md
```

Agent workflow 문서 후보:

```text
docs/agent/backend-workflow.md
docs/agent/codex-instructions.md
docs/agent/antigravity-review.md
docs/agent/verification-gates.md
docs/agent/forbidden-commands.md
```

이번 작업 기록:

```text
docs/tasks/feature-backend-agent-workflow-docs.md
docs/verification/feature-backend-agent-workflow-docs.md
docs/pr/feature-backend-agent-workflow-docs.md
docs/devlog/feature-backend-agent-workflow-docs.md
```

Review가 수행되면 다음 파일을 추가할 수 있다.

```text
docs/reviews/feature-backend-agent-workflow-docs-antigravity.md
docs/reviews/feature-backend-agent-workflow-docs-coderabbit.md
```

필수 수정이 승인된 경우에만 다음 파일을 추가한다.

```text
docs/fixes/feature-backend-agent-workflow-docs-approved-fixes.md
```

예상 목록의 모든 파일을 의무적으로 생성하지 않는다.

다음 기준으로 파일 생성을 최소화한다.

- 독립적으로 자주 참조되는 내용인가
- 다른 문서와 명확히 다른 책임을 갖는가
- 다음 작업에서 agent context를 줄이는 데 도움이 되는가
- 동일 내용을 중복하지 않는가

## DB changes

없음.

이번 작업은 문서 및 agent workflow 구조 정리만 수행한다.

다음 작업은 하지 않는다.

```text
- schema 생성 및 변경
- migration 생성 및 실행
- table 또는 column 변경
- index 추가
- pgvector 활성화
- article_embeddings 설계 및 구현
- Supabase SQL 작성 및 실행
- production data 조회 및 수정
```

DB 관련 기존 설명은 `docs/architecture/database.md`로 이동하거나 현재 구조에 맞게 정리할 수 있다.

이 경우에도 기존 DB 구조를 사실대로 재배치하는 것만 허용하며, 신규 schema를 결정하거나 향후 embedding 구조를 확정하지 않는다.

Embedding 저장 구조 검토는 후속 차수에서 수행한다.

```text
55차: embedding 저장 구조 검토 및 재사용 설계
```

## API changes

없음.

다음 항목은 변경하지 않는다.

```text
- endpoint path
- request parameter
- response schema
- status code
- pagination
- filter
- error response
- FastAPI router
- dependency injection
- DB query
- application behavior
```

기존 API architecture 설명을 세부 문서로 이동할 수는 있지만 실제 API 동작을 변경하거나 문서에서 새로운 contract를 정의하지 않는다.

현재 API 설명과 실제 구현 사이에 불일치가 발견되면 이번 작업에서 임의 수정하지 않는다.

다음과 같이 분류해 기록한다.

```text
- 명백한 문서 오류이며 현재 구현으로 확인 가능: 문서 수정
- 구현 확인이 필요한 불일치: 후속 작업 후보
- API contract 변경이 필요한 사항: 현재 task 범위 밖
```

## Test commands

이번 작업은 문서 구조 변경이므로 backend application test보다 문서 범위, 링크, 중복, 변경 금지 영역을 검증한다.

### 1. 작업 전 상태 확인

```bash
git status --short --branch
```

### 2. 현재 문서 크기 확인

```bash
wc -l AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md
```

### 3. 현재 문서 구조 확인

```bash
find docs -maxdepth 2 -type f | sort
```

### 4. 주요 섹션 확인

```bash
rg -n "^#|^##|^###" AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md
```

### 5. Agent 및 고위험 작업 관련 기존 규칙 확인

```bash
rg -n \
  "Codex|Antigravity|WIP|checklist|검증|verification|kubectl apply|kubectl delete|kubectl rollout|docker push|git push|Supabase|DATABASE_URL|secret" \
  AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md
```

### 6. 변경 파일 확인

```bash
git diff --name-only
git diff --stat
```

확인 기준:

- 변경 파일이 문서 범위에 한정되어 있다.
- backend application source code 변경이 없다.
- migration 변경이 없다.
- K3s manifest 변경이 없다.
- Dockerfile과 GitHub Actions workflow 변경이 없다.

### 7. diff 형식 확인

```bash
git diff --check
```

### 8. 신규 문서 크기 확인

```bash
wc -l \
  AGENTS.md \
  docs/ARCHITECTURE.md \
  docs/RUNBOOK.md \
  docs/architecture/*.md \
  docs/runbooks/*.md \
  docs/agent/*.md
```

목표는 단순히 줄 수를 줄이는 것이 아니라 index 문서와 세부 문서의 책임을 분리하는 것이다.

다만 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`가 다시 장문의 세부 설명을 포함하고 있지 않은지 확인한다.

### 9. Markdown link 검색

```bash
rg -n "\]\(" \
  AGENTS.md \
  docs/ARCHITECTURE.md \
  docs/RUNBOOK.md \
  docs/architecture \
  docs/runbooks \
  docs/agent
```

### 10. Markdown 상대 링크 유효성 검사

Repository에 기존 link checker가 있다면 이를 우선 사용한다.

없다면 문서에 작성한 상대 경로가 실제로 존재하는지 수동 또는 간단한 read-only script로 확인한다.

최소 확인 대상:

```text
AGENTS.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/architecture/*
docs/runbooks/*
docs/agent/*
```

### 11. 현재 운영 기준 검색

```bash
rg -n \
  "api\.newslab\.ai\.kr|api\.dev-scj\.site|news-api|news-rss-collector|news-raw-extractor|arm-master-node|arm-worker-node|workload=app|workload: app|Tailscale|Supabase" \
  AGENTS.md \
  docs/ARCHITECTURE.md \
  docs/RUNBOOK.md \
  docs/architecture \
  docs/runbooks
```

동일 항목이 여러 문서에 서로 다른 현재값으로 기록되지 않았는지 확인한다.

### 12. WIP 1 및 verification gate 확인

```bash
rg -n \
  "WIP 1|작업 단위|checklist|체크리스트|Gate 1|Gate 2|Gate 3|Gate 4|Gate 5|end-to-end|사람이 수행" \
  AGENTS.md \
  docs/agent \
  docs/tasks/feature-backend-agent-workflow-docs.md
```

### 13. 고위험 명령 문맥 확인

```bash
rg -n \
  "git push|git merge|kubectl apply|kubectl delete|kubectl patch|kubectl edit|kubectl rollout restart|helm upgrade|docker push|migration|Supabase 운영 SQL" \
  AGENTS.md \
  docs/ARCHITECTURE.md \
  docs/RUNBOOK.md \
  docs/architecture \
  docs/runbooks \
  docs/agent
```

고위험 명령이 발견되어도 즉시 실패로 판단하지 않는다.

각 명령이 다음 문맥 중 하나에 있는지 확인한다.

```text
- 금지 명령
- 사람이 수행하는 운영 절차
- rollback 또는 troubleshooting 절차
```

Agent가 자동 실행하도록 작성된 문맥이 있으면 실패로 본다.

### 14. 민감정보 pattern 검사

```bash
git grep -n -i -E \
  "API_KEY|TOKEN|PASSWORD|PRIVATE KEY|BEGIN PRIVATE|DATABASE_URL=|SECRET=" \
  -- \
  ':!package-lock.json' \
  ':!docs/tasks/**' \
  ':!docs/reviews/**' \
  ':!docs/fixes/**' \
  ':!docs/verification/**' \
  ':!docs/pr/**' \
  ':!docs/devlog/**'
```

실제 credential 값이 없어야 한다.

정책 문구, 환경 변수명, Kubernetes Secret resource명은 허용할 수 있으나 verification 문서에 예상된 선언임을 기록한다.

### 15. 최종 상태 확인

```bash
git status --short --branch
git diff --stat
git diff --check
```

## Acceptance criteria

### 문서 구조

- [x] `docs/ARCHITECTURE.md`가 전체 architecture의 짧은 index 역할로 정리되어 있다.
- [x] `docs/RUNBOOK.md`가 운영 절차의 짧은 index 역할로 정리되어 있다.
- [x] architecture 세부 내용이 책임에 따라 하위 문서로 분리되어 있다.
- [x] runbook 세부 내용이 운영 목적에 따라 하위 문서로 분리되어 있다.
- [x] 동일한 운영 기준이 여러 문서에 불필요하게 중복되지 않는다.
- [x] index 문서에서 세부 문서로 이동할 수 있다.
- [x] 세부 문서에서 관련 index 또는 인접 문서로 이동할 수 있다.

### Agent workflow

- [x] backend 작업에서 agent가 먼저 읽어야 할 문서가 명확하다.
- [x] Codex 구현과 Antigravity review의 역할이 구분되어 있다.
- [x] `WIP 1` 원칙이 명문화되어 있다.
- [x] 하나의 작업 단위 완료 조건이 정의되어 있다.
- [x] 조사, 변경, 문서화, 검증, checklist 갱신 후 다음 작업으로 이동하도록 정의되어 있다.
- [x] 새 문제 발견 시 blocker와 후속 작업 후보를 구분하도록 정의되어 있다.
- [x] 모든 task 문서에 checklist를 포함하도록 정의되어 있다.
- [x] 완료하지 않은 항목을 임의로 체크하지 않도록 정의되어 있다.

### Verification

- [x] 작업 전 확인 gate가 정의되어 있다.
- [x] 작업 단위별 검증 gate가 정의되어 있다.
- [x] 전체 diff 및 범위 확인 gate가 정의되어 있다.
- [x] 코드 또는 pipeline 작업의 end-to-end 검증 원칙이 정의되어 있다.
- [x] 운영 검증을 agent 검증과 human-controlled 검증으로 구분한다.
- [x] 미수행 검증과 실패한 검증을 사실대로 기록하도록 정의되어 있다.
- [x] verification 문서에 실제 command와 결과를 기록하도록 정의되어 있다.
- [x] `git diff --check`가 통과한다.
- [x] Markdown 문서 링크가 유효하다.

### 안전성 및 범위

- [x] 고위험 명령이 명확하게 분리되어 있다.
- [x] production-impacting command는 사람이 수행하도록 정의되어 있다.
- [x] backend application source code 변경이 없다.
- [x] DB schema와 migration 변경이 없다.
- [x] Supabase SQL 변경이 없다.
- [x] K3s manifest 변경이 없다.
- [x] Docker 및 GitHub Actions workflow 변경이 없다.
- [x] frontend repository 및 frontend 문서 변경이 없다.
- [x] secret, credential, `.env`, kubeconfig 값이 기록되지 않았다.
- [x] embedding과 daily pipeline 기능 구현이 포함되지 않았다.

### 언어 및 유지보수성

- [x] 현재 기준 문서는 한국어를 기본 언어로 사용한다.
- [x] 기술 고유명사와 command는 필요한 경우 원문 표기를 유지한다.
- [x] 과거 task, verification, review, devlog를 불필요하게 전면 번역하지 않았다.
- [x] 문서를 읽기 위해 다시 1000줄 이상의 단일 문서 전체를 확인할 필요가 줄었다.
- [x] 다음 55차 embedding 설계 작업에서 필요한 문서만 선택적으로 읽을 수 있다.

### 작업 기록

- [x] task checklist가 실제 진행 상태에 맞게 갱신되어 있다.
- [x] `docs/verification/feature-backend-agent-workflow-docs.md`가 작성되어 있다.
- [x] `docs/pr/feature-backend-agent-workflow-docs.md`가 작성되어 있다.
- [x] `docs/devlog/feature-backend-agent-workflow-docs.md`가 작성되어 있다.
- [x] 발견된 후속 자동화 후보가 별도로 기록되어 있다.
- [x] 미완료 운영 검증을 완료한 것처럼 기록하지 않았다.

## Notes

- 이번 작업은 완성된 자동화 harness 구현이 아니다.
- 현재 구조의 정확한 표현은 `backend agent-assisted development workflow` 또는 `backend agent workflow`에 가깝다.
- 문서에서 `agent harness`라는 표현을 사용하는 경우, 현재 단계가 문서 기반 workflow이며 자동화된 task runner나 hook 기반 harness는 아니라는 점을 명시한다.
- 문서를 많이 생성하는 것이 목표가 아니다.
- `ARCHITECTURE.md`, `RUNBOOK.md`의 줄 수를 기계적으로 줄이는 것이 목표가 아니다.
- 핵심 목표는 다음 작업에서 agent가 필요한 context만 선택해 읽도록 만드는 것이다.
- 세부 문서는 하나의 책임을 가져야 한다.
- 동일한 운영 기준을 여러 문서에 복사하지 말고 source of truth를 정해야 한다.
- 과거 작업 기록은 현재 운영 기준 문서와 분리해 보존한다.
- 문서 이동 과정에서 과거 운영 상태를 현재 상태처럼 다시 작성하지 않는다.
- 기존 문서와 실제 repository 구조가 다르면 실제 repository를 기준으로 한다.
- 불확실한 내용은 추측해 확정하지 않고 후속 확인 항목으로 기록한다.
- agent 작업 속도 개선 효과는 문서 크기뿐 아니라 읽기 순서와 필수 문서 수로 평가한다.
- 향후 별도 차수에서 다음 자동화 후보를 검토할 수 있다.

```text
scripts/check_agent_task.sh
scripts/check_docs_links.sh
scripts/check_forbidden_changes.sh
scripts/check_task_checklist.sh
scripts/check_verification_commands.sh
```

- 자동화 script를 추가하는 작업은 이번 범위에 포함하지 않는다.
- 다음 차수는 기능 개발로 복귀한다.

```text
55차: embedding 저장 구조 검토 및 재사용 설계
56차: article embedding 저장/재사용 MVP 구현
57차: daily pipeline 분리 설계
58차: daily pipeline 분리 구현
```
