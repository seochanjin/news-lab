# Task: Argo CD 승인형 배포 구조 설계

## Goal

NewsLab의 현재 CI와 수동 배포 흐름을 조사하고, Argo CD를 이용한 승인형 GitOps 배포 구조를 설계한다.

현재 NewsLab은 GitHub Actions가 백엔드와 프론트엔드 이미지를 빌드해 Docker Hub에 발행하지만, 실제 K3s 반영은 사람이 `kubectl rollout restart` 또는 manifest 적용 명령을 실행하는 구조다.

이번 작업의 목표는 곧바로 Argo CD를 설치하거나 운영 배포를 자동화하는 것이 아니다. CD를 처음 다루는 상황을 고려해 다음 내용을 먼저 정확히 이해하고 결정한다.

- CI와 CD가 각각 무엇을 담당하는지
- 현재 NewsLab에서 CI가 어디까지 구현되어 있는지
- 현재 수동 배포 흐름의 문제와 장점은 무엇인지
- Argo CD가 Git repository와 K3s cluster 사이에서 어떤 역할을 하는지
- 자동 Sync가 아닌 사람 승인 기반 Manual Sync를 채택하는 이유
- Backend와 Frontend를 어떤 Argo CD Application 경계로 나눌지
- Argo CD가 추적할 Git repository, branch, manifest path는 무엇인지
- `latest` image tag를 유지할 때 GitOps 이력이 약해지는 이유
- 설치, Sync, rollback, Secret, DB migration의 책임 경계를 어떻게 둘지

이번 작업의 완료 기준은 Argo CD 설치가 아니라, 다음 단계에서 사람이 안전하게 설치와 수동 Sync를 수행할 수 있는 설계와 실행 계획을 문서로 확정하는 것이다.

## Scope

### 1. 현재 CI와 배포 흐름 조사

Backend와 Frontend repository를 기준으로 다음 항목을 조사한다.

- GitHub Actions workflow trigger
- Docker build platform
- Docker Hub repository와 image tag 정책
- `latest` 사용 여부
- K3s manifest의 image reference
- Production rollout 명령과 운영 절차
- Backend와 Frontend manifest 위치
- Deployment, Service, Ingress, CronJob의 repository 분산 상태
- 현재 사람이 수행하는 승인 지점

현재 흐름을 다음 형태로 정리한다.

```
코드 변경
→ PR review 및 merge
→ GitHub Actions build
→ Docker Hub image push
→ 사람이 rollout 또는 manifest apply
→ 사람이 상태와 서비스 확인
```

### 2. 목표 배포 흐름 설계

다음 목표 흐름을 설계한다.

```
코드 변경
→ PR review 및 merge
→ GitHub Actions가 고정 image tag 발행
→ Git manifest의 image tag 변경
→ Argo CD가 Git과 K3s 차이 감지
→ 사람이 diff와 영향 범위 확인
→ 사람이 Sync 승인
→ Argo CD가 K3s에 반영
→ 사람이 rollout과 서비스 상태 검증
```

이번 단계에서는 자동 Sync를 사용하지 않는다.

Argo CD 공식 문서상 자동 Sync는 Git의 desired manifest와 cluster live state 차이를 감지해 자동으로 반영할 수 있다. 그러나 NewsLab은 운영 변경을 사람이 승인하는 원칙을 유지하므로 `spec.syncPolicy.automated`를 활성화하지 않는 설계를 기본으로 한다.

### 3. Argo CD Application 경계 결정

현재 규모에서는 복잡한 App of Apps 또는 ApplicationSet을 사용하지 않고, 우선 다음 두 Application을 독립적으로 관리하는 방향을 검토한다.

- `news-api`
  - Backend Deployment
  - Backend Service
  - Backend Ingress
  - Backend CronJob
- `news-lab-web`
  - Frontend Deployment
  - Frontend Service
  - Frontend Ingress
  - Frontend middleware 또는 관련 resource

각 Application에 대해 다음을 결정한다.

- Application name
- source repository
- target revision
- manifest path
- destination cluster
- destination namespace
- Sync policy
- prune 사용 여부
- self-heal 사용 여부
- resource ownership 경계

초기 설계에서는 다음을 기본값으로 둔다.

```
자동 Sync: 사용하지 않음
자동 prune: 사용하지 않음
자동 self-heal: 사용하지 않음
수동 Sync: 사용
삭제가 포함된 Sync: 별도 사람 확인
```

### 4. GitOps 기준 저장소와 manifest 구조 검토

현재 Backend와 Frontend repository가 각각 자신의 K3s manifest를 보유하고 있다.

다음 대안을 비교한다.

- 각 Application이 각 repository의 `k8s/` 경로를 직접 추적
- 별도 deployment repository를 생성해 Backend와 Frontend 배포 manifest를 통합
- 현재는 각 repository를 유지하고 이후 별도 repository로 분리

이번 작업에서는 현재 규모와 학습 비용을 고려해 가장 단순한 구조를 우선한다. 별도 deployment repository가 반드시 필요하다고 가정하지 않는다.

### 5. Image tag 전략 설계

현재 `latest` tag를 사용할 경우 Git manifest가 변경되지 않아 다음 문제가 생긴다.

- Git commit만 보고 실제 배포 image를 식별하기 어렵다.
- Argo CD가 image registry의 새로운 `latest`를 Git diff로 감지하지 못한다.
- 배포 이력과 rollback 기준이 불명확해진다.
- 같은 manifest revision에서도 서로 다른 image가 실행될 수 있다.

다음 고정 tag 후보를 검토한다.

```
<full-git-sha>
<short-git-sha>
YYYYMMDD-<short-git-sha>
release version tag
```

설계 결과에는 다음을 명시한다.

- Backend와 Frontend에서 사용할 tag 형식
- `latest` 보조 발행 여부
- manifest tag 갱신 주체
- rollback 시 선택할 이전 tag와 Git revision

이번 작업에서 실제 workflow와 manifest tag를 변경하지는 않는다.

### 6. Argo CD 접근과 보안 방향 설계

Argo CD UI와 API server를 public internet에 바로 공개하지 않는 방향을 우선 검토한다.

접근 후보:

- `kubectl port-forward`
- Tailscale 내부 접근
- 내부 전용 Ingress

초기 설치에서는 가장 단순하고 노출이 적은 접근 방식을 선택한다.

다음 항목을 설계 문서에 포함한다.

- Argo CD namespace
- Argo CD server 접근 방식
- 초기 admin credential 처리 원칙
- repository credential 필요 여부
- public repository와 private repository 차이
- Secret을 Git에 평문으로 저장하지 않는 원칙
- RBAC 도입 시점

실제 password, token, kubeconfig, repository credential은 문서에 기록하지 않는다.

### 7. Sync와 rollback 책임 경계 설계

다음 상태와 행동을 구분한다.

- `Synced`: Git desired state와 cluster live state가 일치
- `OutOfSync`: Git과 cluster에 차이가 있음
- `Healthy`: Application resource가 기대 상태로 동작
- `Degraded`: 일부 resource가 정상 상태가 아님
- Refresh: Git과 live state를 다시 비교
- Sync: Git desired state를 cluster에 반영
- Rollback: 이전 Git revision 또는 image tag로 복구

사람이 반드시 확인해야 하는 항목:

- Sync diff
- resource 삭제 여부
- Deployment와 CronJob 영향
- namespace와 destination
- image tag
- Secret과 ConfigMap 변경
- DB migration 포함 여부
- Sync 후 Pod, rollout, endpoint 상태

### 8. 다음 단계 실행 계획 작성

설계 완료 후 후속 작업을 다음과 같이 분리한다.

1. Argo CD 최소 설치
2. Backend Application 등록
3. Backend Manual Sync 검증
4. Frontend Application 등록
5. Frontend Manual Sync 검증
6. 고정 image tag 적용
7. 이전 revision rollback 검증
8. Architecture와 Runbook 갱신
9. README GitOps 배포 구조 반영

각 단계는 별도 Task와 사람 승인 절차로 수행한다.

## Do not change

이번 작업은 조사와 설계 문서 작성만 수행한다.

변경하지 않는 항목:

- K3s cluster resource
- Argo CD 설치
- Argo CD namespace 생성
- Helm install 또는 upgrade
- `kubectl apply`, `delete`, `patch`, `rollout`
- Backend Deployment, Service, Ingress, CronJob
- Frontend Deployment, Service, Ingress
- GitHub Actions workflow
- Docker build 설정
- Docker Hub image
- 기존 `latest` image tag
- Application source code
- FastAPI endpoint
- Next.js route
- DB schema
- DB migration
- Supabase data
- Secret
- kubeconfig
- DNS
- TLS certificate
- Traefik configuration
- Production service
- README의 현재 기능 설명

이번 설계 문서에 Argo CD가 이미 설치되었거나 운영 중인 것처럼 작성하지 않는다.

다음 고급 기능은 범위에서 제외한다.

- Automated Sync
- Automatic Prune
- Automatic Self-Heal
- ApplicationSet
- App of Apps
- Argo CD Image Updater
- Argo Rollouts
- Progressive Delivery
- Canary Deployment
- Blue/Green Deployment
- Sealed Secrets
- External Secrets
- SSO
- Multi-cluster deployment
- 자동 rollback
- 자동 DB migration

## Expected files

예상 주요 변경 파일:

```
docs/architecture/argocd-manual-sync-design.md
docs/runbooks/argocd-manual-sync-plan.md
```

필요한 경우 기존 문서에 링크만 최소 추가한다.

```
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

작업 workflow 문서:

```
docs/tasks/
docs/verification/
docs/reviews/
docs/fixes/
docs/pr/
docs/devlog/
```

이번 작업에서는 다음 파일이 생성되거나 수정되면 안 된다.

```
k8s/argocd/**
argocd/**
.github/workflows/**
app/**
scripts/**
db/**
Dockerfile
requirements.txt
```

## DB changes

없음.

- Schema 변경 없음
- Migration 없음
- Table 변경 없음
- Column 변경 없음
- Index 변경 없음
- Constraint 변경 없음
- DB write 없음
- Supabase SQL 실행 없음
- Argo CD가 DB migration을 자동 실행하도록 설계하지 않음

## API changes

없음.

- Endpoint 추가 없음
- Request schema 변경 없음
- Response schema 변경 없음
- Public API 계약 변경 없음
- API version 변경 없음
- Backend 또는 Frontend 배포 없음

## Test commands

현재 CI workflow와 image tag를 조사한다.

```bash
rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" \
  .github README.md k8s docs
```

Backend manifest의 image와 resource를 확인한다.

```bash
rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s
```

Frontend repository의 workflow와 manifest를 별도로 확인한다.

```bash
cd ~/workspace/NewsLab/news-lab-web
rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" \
  .github README.md k8s docs
```

```bash
rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s
```

Argo CD 관련 resource가 아직 repository에 없는지 확인한다.

```bash
cd ~/workspace/NewsLab/news-lab
find . -maxdepth 4 -type f \
  \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) \
  | sort
```

설계 문서에 핵심 결정이 포함됐는지 확인한다.

```bash
rg -n \
  "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" \
  docs/architecture/argocd-manual-sync-design.md \
  docs/runbooks/argocd-manual-sync-plan.md
```

금지 영역 변경 여부를 확인한다.

```bash
git diff --name-only -- \
  app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml
```

Markdown 형식 오류를 확인한다.

```bash
git diff --check
```

전체 변경 범위를 확인한다.

```bash
git status --short
```

```bash
git diff -- docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/runbooks
```

이번 작업에서는 Argo CD 설치나 cluster 명령을 실행하지 않는다.

다음 명령은 Test commands가 아니라 후속 작업의 사람 실행 후보로만 문서화할 수 있다.

```
kubectl create namespace argocd
kubectl apply -n argocd ...
helm install ...
argocd app create ...
argocd app sync ...
argocd app rollback ...
```

실행하지 않은 명령은 Verification에 실행 결과처럼 기록하지 않는다.

## Acceptance criteria

- 현재 NewsLab의 CI와 수동 배포 흐름이 실제 repository 근거로 정리되어 있다.
- CI와 CD의 역할 차이가 문서에 설명되어 있다.
- Argo CD가 Git desired state와 K3s live state를 비교하는 역할이 설명되어 있다.
- Argo CD 설치가 완료된 것처럼 표현하지 않는다.
- Backend와 Frontend Application 경계가 결정되어 있다.
- 각 Application의 repository, target revision, manifest path, namespace 후보가 기록되어 있다.
- 자동 Sync를 사용하지 않는 이유가 명시되어 있다.
- `automated`, `prune`, `self-heal`의 초기 정책이 명시되어 있다.
- 삭제가 포함된 Sync는 별도 사람 승인이 필요하다고 기록되어 있다.
- Argo CD UI/API 접근 방식 후보와 선택 기준이 정리되어 있다.
- Public exposure를 기본값으로 두지 않는다.
- Secret과 credential을 Git에 평문 저장하지 않는 원칙이 기록되어 있다.
- 현재 `latest` tag의 GitOps 한계가 설명되어 있다.
- 고정 image tag 후보와 최종 권장안이 기록되어 있다.
- Git manifest의 tag 변경과 Argo CD Sync 관계가 설명되어 있다.
- Sync 전 확인 항목과 Sync 후 검증 항목이 구분되어 있다.
- Rollback 기준이 이전 Git revision 또는 고정 image tag로 설명되어 있다.
- DB migration과 Secret 변경이 자동 배포 범위에 포함되지 않는다.
- ApplicationSet, App of Apps, Image Updater 등 고급 기능이 범위에서 제외되어 있다.
- 후속 설치·수동 Sync·고정 tag·rollback 작업이 별도 단계로 분리되어 있다.
- Application code, DB, API, K3s manifest와 GitHub Actions workflow가 변경되지 않는다.
- `git diff --check`가 통과한다.
- 실제 실행한 조사 명령과 결과만 Verification에 기록한다.
- Task 문서에는 계획만 유지한다.

## Notes

- 사용자는 CI workflow를 운영하고 있지만 CD는 처음 다룬다. 문서에서 용어를 알고 있다는 전제로 생략하지 않는다.
- CI/CD 기본 개념은 이 Task의 하위 페이지인 `CI와 CD 입문: NewsLab 배포 흐름으로 이해하기`에 별도로 정리한다.
- Argo CD는 Kubernetes용 declarative GitOps CD 도구다. Git repository의 manifest를 desired state로 보고 cluster live state와 비교한다.
- Manual Sync 구조에서도 Argo CD는 Git 변경 감지, diff 표시, health 상태, sync history를 제공할 수 있다.
- `syncPolicy.automated`가 없거나 비활성화된 Application은 사람이 Sync를 실행하기 전까지 Git 변경을 자동 반영하지 않는 방향으로 설계한다.
- 자동화 수준을 높이는 것이 항상 목표는 아니다. 현재 NewsLab에서는 배포 이력과 재현성을 확보하면서 운영 승인권을 사람에게 유지하는 것이 우선이다.
- 첫 단계부터 완벽한 GitOps 플랫폼을 만들지 않는다.
- 초기 목표는 Backend와 Frontend 각각 하나의 Application으로 시작하는 것이다.
- 운영 중인 manifest를 Argo CD가 관리하기 시작할 때 기존 resource ownership과 drift를 주의해야 한다.
- Argo CD 도입 전후의 resource manifest가 동일하더라도 초기 Sync diff를 사람이 확인해야 한다.
- `latest` tag 문제는 Argo CD 설치와 분리해 후속 작업으로 다룰 수 있다. 다만 설계 단계에서 반드시 의사결정을 남긴다.
- Argo CD installation manifest 또는 Helm chart version은 실제 설치 시점에 공식 문서를 다시 확인한다.
- Argo CD UI를 공개 도메인으로 노출하는 작업은 별도 보안 검토 없이 수행하지 않는다.
- Production 명령은 사람이 직접 실행하고 결과를 Verification에 제공한다.
- README에는 Argo CD 설치와 실제 Manual Sync가 검증된 뒤에만 현재 배포 구조로 반영한다.

## Implementation Units

- [x] UNIT-01: 현재 CI·이미지 태그·K3s manifest·수동 배포 흐름 조사
- [x] UNIT-02: Argo CD Application 경계·Git source·Manual Sync 정책 설계
- [x] UNIT-03: 고정 이미지 태그·Sync·rollback·후속 실행 계획 문서화 및 검증
