# Task: README 및 아키텍처 문서 현행화

## Goal

NewsLab의 `README.md`와 Architecture 문서를 현재 Production 운영 구조에 맞게 현행화한다.

70~73차에서 완성하고 운영 검증한 다음 구조를 프로젝트 진입 문서에 반영한다.

- Backend immutable full Git SHA image 기반 배포
- GitHub Actions의 ARM64 image build/push와 manifest image 갱신 PR
- Argo CD Manual Sync 기반 승인형 GitOps 운영
- Redis cache-aside와 fail-open 정책
- Daily·3-day·Weekly Home Cache
- Pipeline-driven Home Cache prewarming
- Oracle Cloud A1과 Raspberry Pi 기반 hybrid 3-node K3s cluster
- 현재 실제 workload 배치, nodeSelector와 taint 정책
- Prometheus·Grafana·node-exporter 기반 monitoring 구조
- Tailscale 기반 hybrid node 연결과 operator 접근 경로

README는 프로젝트를 처음 보는 사람이 핵심 기능, 데이터 흐름, 운영 인프라와 주요 설계 결정을 빠르게 이해할 수 있는 진입점으로 정리한다.

세부 설계와 운영 절차는 `docs/ARCHITECTURE.md`, 하위 Architecture 문서와 `docs/RUNBOOK.md`로 연결한다.

## Scope

- 현재 `README.md`, Architecture, Runbook, Kubernetes manifest와 GitHub Actions workflow를 대조해 오래된 정보와 누락된 내용을 조사한다.
- `README.md`의 프로젝트 소개, 주요 기능, 데이터 파이프라인, 시스템 아키텍처, Cache, K3s 운영, 배포, 관측성과 문서 링크를 현재 구조에 맞게 정리한다.
- `docs/ARCHITECTURE.md`와 필요한 `docs/architecture/*.md`를 최신 운영 구조에 맞게 갱신한다.
- 사용자가 추가하는 `docs/images/newslab-architecture_R1.png`를 대표 아키텍처 이미지로 연결한다.
- 사용자 요청 경로를 다음 논리 흐름으로 설명한다.

```
User
→ Public DNS
→ Oracle Public IP
→ Traefik Ingress
→ Kubernetes Service
→ Application Pod
```

- Frontend와 Backend가 별도 Service인 경우 하나의 Service가 Next.js와 FastAPI Pod를 함께 선택하는 것처럼 표현하지 않는다.
- 다음 K3s node 역할과 현재 placement를 문서화한다.
  - `arm-master-node`: Oracle Cloud A1 Control Plane, 일반 application workload 미배치
  - `arm-worker-node`: Frontend, Backend, Redis, Pipeline과 Monitoring Core 실행
  - `pi-worker-node`: Raspberry Pi worker, `NoSchedule` taint로 일반 application 미배치, 향후 explicit toleration 기반 edge/batch 후보
- PostgreSQL/Supabase를 Source of Truth로, Redis를 삭제 가능한 fail-open cache 계층으로 설명한다.
- Home API cache-aside와 Pipeline prewarming 관계를 문서화한다.

```
Daily Pipeline
→ PostgreSQL 저장
→ topics:home:v1 prewarm

3-day Pipeline
→ PostgreSQL 저장
→ three-day-topics:home:v1 prewarm

Weekly Pipeline
→ PostgreSQL 저장
→ weekly-topics:home:v1 prewarm
```

- Cache TTL 정책을 현재 구현과 일치시킨다.
  - Daily: `108000`초
  - 3-day: `108000`초
  - Weekly: `691200`초
- Redis와 PostgreSQL이 서로 직접 통신하는 것처럼 표현하지 않는다. 실제 접근 주체는 FastAPI와 각 Pipeline이다.
- Backend 배포 흐름을 다음 승인형 GitOps 구조로 설명한다.

```
Application code PR merge
→ GitHub Actions가 ARM64 immutable full Git SHA image build/push
→ Backend workload manifest image 갱신 PR 생성
→ 사람이 manifest diff 검토 후 merge
→ Argo CD가 OutOfSync 감지
→ 사람이 Argo CD diff 검토
→ Manual Sync
→ rollout, workload image와 production health 검증
```

- README에서 특정 시점의 image SHA를 영구 구조처럼 고정하지 않고 `seocj/news-api:<full-git-sha>` 형태로 정책을 설명한다.
- README, Architecture, Runbook과 실제 repository 설정 사이의 용어와 설명을 대조한다.

## Do not change

- Backend application business logic
- FastAPI endpoint 동작과 API response schema
- Redis cache 구현
- RSS 수집, 원문 추출, embedding, Topic pipeline과 summary logic
- Kubernetes Deployment, Service, Ingress, Redis와 CronJob 동작
- CronJob schedule, command, suspend와 concurrency policy
- GitHub Actions workflow 동작
- Argo CD Application 설정과 Manual Sync 정책
- database schema, migration과 Supabase SQL
- Frontend implementation과 Frontend repository
- production Secret과 credential
- Production resource
- 사람이 승인해야 하는 다음 작업의 자동 실행
  - PR merge
  - `kubectl apply/delete/patch/rollout`
  - Argo CD Sync
  - DB migration
  - Secret 변경

이번 Task는 문서와 이미지 참조 현행화만 수행한다.

실제 구조와 문서가 불일치하면 repository manifest와 기존 Production Verification을 기준으로 문서를 수정하고, application 또는 Infrastructure를 이번 Task에서 변경하지 않는다.

## Expected files

작업 중 실제 repository 구조를 확인한 뒤 최소 범위로 수정한다.

예상 주요 변경 파일:

```
README.md
docs/ARCHITECTURE.md
docs/architecture/*.md
docs/images/newslab-architecture_R1.png
```

예상 작업 문서:

```
docs/tasks/docs-readme-architecture-refresh.md
docs/reviews/docs-readme-architecture-refresh-antigravity.md
docs/reviews/docs-readme-architecture-refresh-coderabbit.md
docs/fixes/docs-readme-architecture-refresh-approved-fixes.md
docs/verification/docs-readme-architecture-refresh.md
docs/pr/docs-readme-architecture-refresh.md
docs/devlog/docs-readme-architecture-refresh.md
```

`docs/RUNBOOK.md`는 현재 운영 절차와 상충하는 문구나 깨진 연결이 확인된 경우에만 최소 범위로 수정한다.

사용자는 다음 파일을 직접 추가한다.

```
docs/images/newslab-architecture_R1.png
```

Codex는 이미지 파일을 생성하거나 편집하지 않는다.

구현 전에 다음 항목을 조사한다.

- 현재 README의 image path와 문서 구조
- `docs/ARCHITECTURE.md`와 `docs/architecture/*.md`의 현재 설명
- Backend Deployment와 네 CronJob의 image tag 정책
- GitHub Actions image build와 manifest PR workflow
- Redis key, TTL, cache-aside와 prewarm 구현
- CronJob의 실제 schedule과 nodeSelector
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`의 검증된 역할과 placement
- Argo CD `news-api` Application의 Manual Sync 운영 범위
- Frontend repository 밖의 내용을 Backend repository에서 증명할 수 있는 범위
- README와 Architecture에 남아 있는 `latest`, 이전 image path와 오래된 운영 설명

## DB changes

없음.

- table, column, index와 constraint 변경 없음
- migration file 추가 없음
- Supabase SQL 실행 없음
- 운영 데이터 변경 없음

## API changes

없음.

- 신규 endpoint 없음
- 기존 endpoint path 변경 없음
- request/response schema 변경 없음
- 인증과 권한 정책 변경 없음

## Test commands

### 현재 문서와 repository 구조 조사

```bash
rg -n \
  'newslab-architecture|seocj/news-api:latest|full Git SHA|Redis|prewarm|Argo CD|Manual Sync|Tailscale' \
  README.md docs .github/workflows k8s
```

```bash
rg -n \
  'kind: Deployment|kind: CronJob|image:|schedule:|nodeSelector:|workload: app' \
  k8s
```

### 작업 범위 확인

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

### 새 아키텍처 이미지 확인

```bash
test -f docs/images/newslab-architecture_R1.png
```

```bash
rg -n \
  'docs/images/newslab-architecture_R1\.png' \
  README.md docs/ARCHITECTURE.md docs/architecture
```

### 오래된 image와 `latest` 설명 확인

```bash
rg -n \
  'docs/images/newslab-architecture\.png|seocj/news-api:latest' \
  README.md docs/ARCHITECTURE.md docs/architecture
```

완료 시 현재 대표 image 경로 또는 Backend desired state를 설명하는 오래된 결과가 없어야 한다.

과거 이력이나 migration 설명을 인용하는 문맥이 발견되면 현재 상태와 혼동되지 않는지 수동 검토한다.

### Cache key와 TTL 설명 확인

```bash
rg -n \
  'topics:home:v1|three-day-topics:home:v1|weekly-topics:home:v1|108000|691200|fail-open|prewarm' \
  README.md docs/ARCHITECTURE.md docs/architecture app k8s
```

확인 조건:

- Daily와 3-day TTL은 `108000`초다.
- Weekly TTL은 `691200`초다.
- Redis는 fail-open cache 계층으로 설명된다.
- PostgreSQL/Supabase는 Source of Truth로 설명된다.
- Pipeline이 PostgreSQL 저장 성공 후 Redis를 prewarm하는 흐름이 설명된다.

### CronJob schedule 정합성 확인

```bash
rg -n \
  '^\s*schedule:|timeZone:|news-rss-collector|news-daily-topic-pipeline|news-three-day-topic-pipeline|news-weekly-topic-pipeline' \
  k8s README.md docs/ARCHITECTURE.md docs/architecture
```

확인 조건:

- RSS: 매일 `03:00 Asia/Seoul`
- Daily: 매일 `04:00 Asia/Seoul`
- 3-day: 매일 `05:00 Asia/Seoul`
- Weekly: 매주 월요일 `00:30 Asia/Seoul`

### Markdown 상대 링크와 image path 확인

```bash
python - <<'PY'
from pathlib import Path
import re

paths = [Path('README.md'), Path('docs/ARCHITECTURE.md')]
missing = []

for path in paths:
    text = path.read_text(encoding='utf-8')
    for target in re.findall(r'!??\[[^\]]*\]\(([^)]+)\)', text):
        target = target.split('#', 1)[0]
        if not target or '://' in target or target.startswith('#'):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            missing.append(f'{path}: {target}')

if missing:
    raise SystemExit('missing relative links:\n' + '\n'.join(missing))

print('markdown relative links passed')
PY
```

### 금지 영역 변경 확인

```bash
git diff --name-only -- \
  app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml
```

기대 결과: 출력 없음.

### 최종 문서 검증

```bash
git diff --check
```

Application test suite는 이번 documentation-only Task의 기본 범위가 아니다. 실행하지 않은 test는 Verification에 통과로 기록하지 않는다.

## Acceptance criteria

- README가 현재 NewsLab의 실제 Production 구조를 반영한다.
- `docs/images/newslab-architecture_R1.png`가 README와 필요한 Architecture 문서에서 정상 참조된다.
- README의 기존 대표 architecture image 경로가 새 image로 교체된다.
- 70차의 immutable full Git SHA image와 승인형 GitOps 구조가 반영된다.
- 71차의 Redis cache-aside와 fail-open 구조가 반영된다.
- 72차의 Daily·3-day·Weekly Home Cache와 Pipeline prewarming 구조가 반영된다.
- 73차에서 Production 검증한 Pipeline-driven prewarm 상태가 반영된다.
- Backend desired state를 `seocj/news-api:latest` 기반으로 설명하지 않는다.
- 특정 시점의 현재 SHA를 영구적인 아키텍처 설명처럼 고정하지 않는다.
- hybrid 3-node K3s cluster와 현재 workload placement가 정확하게 설명된다.
- `arm-master-node`는 Control Plane, `arm-worker-node`는 현재 application workload node, `pi-worker-node`는 `NoSchedule` worker로 구분된다.
- Public ingress와 Tailscale의 역할이 혼동되지 않는다.
- Frontend와 Backend Service가 하나의 Service처럼 잘못 표현되지 않는다.
- PostgreSQL/Supabase와 Redis의 역할이 명확하게 분리된다.
- Redis와 PostgreSQL이 서로 직접 통신하는 것처럼 표현하지 않는다.
- CronJob schedule이 실제 manifest와 일치한다.
- README는 프로젝트 진입점 역할을 유지하고 세부 설계와 운영 절차는 Architecture와 Runbook으로 연결한다.
- README, Architecture, Runbook과 실제 repository 사이의 주요 불일치가 제거된다.
- Application code, Kubernetes behavior, workflow, DB, API contract, Frontend code와 Secret 변경이 없다.
- Markdown 상대 링크와 image path 검증을 통과한다.
- `git diff --check`를 통과한다.
- Verification에는 실제 실행한 command와 실제 결과만 기록한다.
- Task checklist와 Verification status가 일치한다.

## Notes

- Branch: `docs/readme-architecture-refresh`
- Task artifact: `docs/tasks/docs-readme-architecture-refresh.md`
- 새 architecture image: `docs/images/newslab-architecture_R1.png`
- 사용자가 image를 직접 추가하며 Codex는 생성하거나 편집하지 않는다.
- 문서 수정 전에 현재 README와 실제 manifest·workflow의 차이를 먼저 조사한다.
- 문서보다 실제 repository manifest와 기존 Production Verification을 우선한다.
- Frontend repository 밖의 내용을 Backend repository만으로 증명할 수 없으면 해당 범위를 명확히 표현한다.
- README에는 특정 실행 시점의 상세 운영 로그를 과도하게 복사하지 않는다.
- 구조, 핵심 설계 판단과 검증된 운영 상태를 중심으로 작성한다.
- Production mutation은 수행하지 않는다.
- Review에서 수정 사항이 없으면 Approved Fixes에 `없음`을 명시한다.

## Implementation Units

- [x] UNIT-01: 현재 README, Architecture, Runbook, Kubernetes manifest와 GitHub Actions workflow를 조사하고 오래된 정보·누락 항목·repository가 증명할 수 있는 범위를 확정
- [x] UNIT-02: 사용자가 추가한 `newslab-architecture_R1.png`를 README와 Architecture에 연결하고 요청 경로·K3s topology·외부 운영 경로 설명을 이미지와 일치하도록 수정
- [x] UNIT-03: README의 프로젝트 소개, 주요 기능, 데이터 파이프라인, 시스템 아키텍처와 문서 탐색 구조를 현재 서비스 기준으로 현행화
- [x] UNIT-04: Redis cache-aside·fail-open, Daily·3-day·Weekly Pipeline prewarming과 TTL 정책을 README 및 Architecture 문서에 반영
- [x] UNIT-05: immutable image·manifest PR·Argo CD Manual Sync 기반 승인형 GitOps와 hybrid K3s node placement·monitoring·Tailscale 운영 구조를 문서화
- [x] UNIT-06: README·Architecture·Runbook·manifest·workflow 간 용어, 링크, image path와 운영 사실의 정합성을 검토하고 승인된 Review fix를 반영
- [x] UNIT-07: 최종 문서 검증, Verification·PR·Devlog 작성과 Task checklist 상태 정리
