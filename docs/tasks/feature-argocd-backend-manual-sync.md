# Task: Argo CD 최소 설치 및 Backend Manual Sync 검증

## Goal

68차에서 확정한 승인형 GitOps 설계를 기준으로 K3s 클러스터에 Argo CD를 최소 구성으로 설치하고, Backend `news-api` Application을 등록해 사람이 diff를 확인한 뒤 Manual Sync를 수행하는 흐름을 검증한다.

이번 작업의 목표는 Argo CD를 완전 자동 배포 도구로 전환하는 것이 아니다. 다음 흐름을 실제 운영 환경에서 증명하는 것이 핵심이다.

```
Git repository의 k8s manifest
→ Argo CD가 desired/live state 차이 감지
→ 사람이 diff와 삭제 영향 확인
→ 사람이 Manual Sync 승인
→ Argo CD가 K3s resource 반영
→ 사람이 rollout, Pod, API, CronJob 상태 검증
```

이번 단계에서는 Backend만 Argo CD 관리 대상으로 등록한다. Frontend Application, 고정 image tag 전환, rollback 실제 시험은 후속 작업으로 분리한다.

## Scope

### 1. 68차 설계 문서 재확인

다음 문서를 기준으로 실제 설치와 Application 등록 조건을 확인한다.

```
docs/architecture/argocd-manual-sync-design.md
docs/runbooks/argocd-manual-sync-plan.md
docs/verification/feature-argocd-manual-sync-baseline.md
```

확인 항목:

- Backend repository: `https://github.com/seochanjin/news-lab.git`
- Target revision: `main`
- Manifest path: `k8s/`
- Destination cluster: 현재 K3s cluster
- Destination namespace: `default`
- Sync policy: Manual
- Automated sync: 비활성화
- Automatic prune: 비활성화
- Automatic self-heal: 비활성화
- Argo CD server 접근: `kubectl port-forward` 우선

설계와 실제 cluster 상태가 다르면 설치를 진행하지 않고 차이를 기록한다.

### 2. 설치 방식과 버전 확정

실제 설치 직전에 Argo CD 공식 문서를 기준으로 다음을 확인한다.

- 지원되는 최신 안정 버전
- 설치 manifest 또는 Helm chart 선택
- K3s와 ARM64 호환 여부
- 요구 Kubernetes version
- 설치 namespace
- 기본 resource 요구량
- 초기 admin credential 확인 방법
- 제거 및 복구 방법

초기 도입에서는 설치 구조를 단순하게 유지한다. HA 설치, SSO, external Redis, public Ingress는 사용하지 않는다.

설치 방식 후보:

- 공식 install manifest
- 공식 Helm chart

이번 작업에서는 한 가지 방식만 선택해 설치하고, 선택 근거를 문서에 남긴다.

### 3. Argo CD namespace와 core component 설치

사람이 승인 후 다음 범위의 설치 명령을 직접 실행한다.

- `argocd` namespace 생성
- Argo CD core component 설치
- Deployment, StatefulSet, Service, Pod 상태 확인
- Image architecture와 scheduling 상태 확인
- 설치 완료 전 readiness 확인

설치 후 확인 대상:

- `argocd-server`
- `argocd-repo-server`
- `argocd-application-controller`
- `argocd-redis` 또는 선택한 설치 방식의 cache component
- `argocd-dex-server`가 포함되는 경우 필요성 기록
- 관련 ServiceAccount, Role, ClusterRole

실제 resource 이름은 선택한 공식 설치 방식의 결과를 기준으로 기록한다.

### 4. Argo CD 접근과 초기 로그인 검증

Public Ingress를 만들지 않고 다음 방식으로 접근한다.

```
kubectl port-forward
```

검증 항목:

- Local port-forward 연결
- Argo CD UI 또는 CLI 접속
- 초기 admin credential 조회
- 로그인 성공
- Credential 값은 문서에 기록하지 않음
- 로그인 후 password 변경 여부 판단
- Port-forward 종료 후 외부에서 접근되지 않는지 확인

Tailscale 내부 Ingress와 public domain은 이번 범위에서 제외한다.

### 5. `ClusterIssuer/letsencrypt-prod` ownership 결정

Backend `k8s/` 경로에는 cluster-wide TLS resource가 포함될 수 있으므로 `news-api` Application 등록 전에 ownership을 확정한다.

선택 후보:

- Backend Application이 함께 관리
- Backend Application source path에서 제외
- 별도 infrastructure Application으로 후속 분리

초기 권장 방향은 application workload와 shared infrastructure의 책임을 분리하는 것이다.

`news-api` Application이 관리할 resource 목록과 제외할 resource를 Application 생성 전에 문서로 확정한다. 이를 위해 필요하면 Backend manifest 경로 구조를 분리하는 후속 task를 생성한다.

### 6. Backend `news-api` Application 정의

68차 설계를 기준으로 Backend Application manifest 또는 생성 명령을 준비한다.

초기 후보:

```
Application name: news-api
Repository: https://github.com/seochanjin/news-lab.git
Target revision: main
Path: k8s/
Destination server: in-cluster
Destination namespace: default
Sync: Manual
Prune: Off
Self-heal: Off
```

Application 정의는 Git에 기록 가능한 declarative YAML을 우선한다.

Application 자체를 Git으로 관리할 경우 다음을 결정한다.

- 저장 경로
- Bootstrap 시 최초 apply 주체
- Application resource와 workload manifest의 ownership
- Repository가 public인지 private인지
- Repository credential 필요 여부

### 7. 최초 diff와 ownership 충돌 확인

기존 K3s resource가 이미 실행 중인 상태에서 Argo CD가 동일 resource를 처음 관리하게 되므로 최초 Sync 전에 반드시 diff를 확인한다.

확인 항목:

- 예상하지 않은 resource 생성 또는 삭제
- Deployment selector와 label 차이
- Service ClusterIP 차이
- Ingress annotation과 TLS 차이
- CronJob schedule과 suspend 상태
- Defaulted field로 인한 불필요한 diff
- Runtime field가 desired manifest와 비교되는지
- `ClusterIssuer` 포함 여부
- Secret, ConfigMap, PVC 포함 여부

예상하지 않은 삭제, recreate, selector 변경이 보이면 Sync를 중단한다.

### 8. Backend Manual Sync 수행

사람이 Argo CD diff를 확인하고 승인한 뒤 Manual Sync를 수행한다.

Sync 전 기록:

- Application Sync status
- Health status
- Git revision
- 관리 대상 resource 목록
- 생성, 수정, 삭제 예정 resource
- 현재 Deployment image
- 현재 ready replica 수
- 현재 CronJob 상태

Sync 후 기록:

- Sync result
- Application status
- Resource health
- Deployment rollout
- Pod restart 및 image
- Service와 Ingress 상태
- CronJob 목록과 schedule
- Argo CD event와 operation history

삭제가 포함되거나 예상하지 않은 resource replacement가 필요한 경우 Sync하지 않고 중단한다.

### 9. 운영 서비스 검증

Manual Sync 이후 사람이 다음을 검증한다.

- Backend Deployment rollout 성공
- Backend Pod readiness/liveness 정상
- `/health` 정상
- `/version` 정상
- 주요 read-only API 정상
- Ingress와 TLS 정상
- RSS/Daily/Three-day/Weekly CronJob이 유지됨
- 기존 production endpoint 정상
- Prometheus/Grafana 관측 상태에 이상 없음

운영 데이터 변경 요청이나 CronJob 수동 실행은 수행하지 않는다.

### 10. 실패와 중단 기준 기록

다음 상황에서는 작업을 중단하고 rollback 또는 기존 수동 관리 상태를 유지한다.

- Argo CD component가 Ready가 되지 않음
- ARM64 image pull 또는 scheduling 실패
- Application source repository 읽기 실패
- 예상하지 않은 삭제 또는 resource recreate
- Deployment selector 변경
- Service 또는 Ingress 연결 손실 위험
- CronJob 누락
- Production health check 실패
- Argo CD가 shared infrastructure resource를 예상과 다르게 관리

이번 작업에서는 workload rollback 실제 시험을 수행하지 않는다. 실패 시 Git revision과 cluster 상태를 기록하고 사람 판단으로 복구한다.

### 11. 문서와 후속 task 정리

실제 결과를 다음 문서에 반영한다.

- Argo CD 설치 방식과 version
- 설치 component 상태
- 접근 방식
- Backend Application 정의
- 최초 diff 결과
- Manual Sync 결과
- 운영 검증 결과
- 실패 또는 중단 사항
- `ClusterIssuer` ownership 결정
- Frontend 적용 전 선행 조건

후속 task 후보:

1. Frontend `news-lab-web` Application 등록 및 Manual Sync 검증
2. Backend/Frontend 고정 Git SHA image tag 전환
3. Rollback controlled test
4. Argo CD 접근 방식의 Tailscale 내부화 검토
5. Architecture, Runbook, README 최종 갱신

## Do not change

이번 작업에서 임의로 변경하지 않는다.

- Application source code
- FastAPI endpoint와 schema
- Frontend source code
- DB schema와 migration
- Supabase data
- GitHub Actions workflow
- Docker build 설정
- Docker Hub image 발행 정책
- Backend와 Frontend의 `latest` tag 정책
- Frontend K3s resource
- DNS
- Public Ingress
- TLS certificate 발급 구조
- Traefik 설정
- Existing Secret 값
- Repository credential 값
- Kubeconfig 내용
- CronJob schedule
- CronJob 수동 실행
- Production DB write
- README의 현재 운영 구조 설명

다음 고급 기능은 사용하지 않는다.

- Automated Sync
- Automatic Prune
- Automatic Self-Heal
- ApplicationSet
- App of Apps
- Argo CD Image Updater
- Argo Rollouts
- Canary Deployment
- Blue/Green Deployment
- Sealed Secrets
- External Secrets
- SSO
- Multi-cluster
- HA install
- Public Argo CD Ingress
- 자동 rollback
- 자동 DB migration

고위험 작업은 사람이 직접 수행한다.

- Namespace 생성
- Argo CD 설치
- Helm install/upgrade
- `kubectl apply`, `delete`, `patch`, `rollout`
- Application 생성과 Sync
- Credential 조회와 변경
- Production verification
- Rollback
- Git push와 merge

## Expected files

예상 문서 변경:

```
docs/architecture/argocd-manual-sync-design.md
docs/runbooks/argocd-manual-sync-plan.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

Application manifest를 Git에 저장하기로 결정한 경우 후보:

```
k8s/argocd/news-api-application.yaml
```

Shared infrastructure 분리가 필요한 경우 후보:

```
k8s/apps/**
k8s/infrastructure/**
```

단, 경로 분리는 최초 diff와 ownership 검토 결과를 근거로 수행한다. Task 시작 전에 임의로 구조를 바꾸지 않는다.

Workflow 문서:

```
docs/tasks/
docs/verification/
docs/reviews/
docs/fixes/
docs/pr/
docs/devlog/
```

실제 Argo CD 설치 manifest 전체를 repository에 복사해 장기 유지할지는 선택한 설치 방식에 따라 결정한다.

## DB changes

없음.

- Schema 변경 없음
- Migration 없음
- Table 변경 없음
- Column 변경 없음
- Index 변경 없음
- Constraint 변경 없음
- Supabase SQL 없음
- Production DB write 없음
- Argo CD Sync에 DB migration 포함하지 않음

## API changes

없음.

- Endpoint 추가 없음
- Request schema 변경 없음
- Response schema 변경 없음
- Public API 계약 변경 없음
- API version 변경 없음

Manual Sync 후 기존 API가 유지되는지만 검증한다.

## Test commands

### 사전 cluster 상태

```bash
kubectl get nodes -o wide
kubectl get namespace
kubectl get deployment,service,ingress,cronjob -n default
kubectl get pods -n default -o wide
kubectl get clusterissuer
```

### 설치 전 repository 상태

```bash
git status --short
git branch --show-current
git log --oneline -5
```

```bash
rg -n "kind:|metadata:|name:|image:|schedule:|namespace:|ClusterIssuer" k8s
```

### Argo CD 설치 검증

선택한 공식 설치 방법에 맞게 실제 명령을 Verification에 기록한다.

설치 후 공통 확인:

```bash
kubectl get all -n argocd
kubectl get pods -n argocd -o wide
kubectl get deployment,statefulset,service -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
```

```bash
kubectl wait --for=condition=Available deployment --all -n argocd --timeout=300s
```

### Port-forward와 로그인

실제 Service 이름과 local port는 설치 결과에 맞춰 기록한다.

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

초기 credential 값은 Verification에 기록하지 않는다.

### Application 상태

Application 생성 후:

```bash
kubectl get applications.argoproj.io -n argocd
kubectl describe application news-api -n argocd
```

Argo CD CLI를 설치해 사용하는 경우:

```bash
argocd app get news-api
argocd app diff news-api
```

CLI를 사용하지 않는 경우 UI와 Kubernetes resource 결과를 Verification에 기록한다.

### Sync 전 Backend 상태

```bash
kubectl get deployment news-api -n default -o wide
kubectl get pods -n default -l app=news-api -o wide
kubectl get service,ingress -n default
kubectl get cronjob -n default
```

실제 label은 manifest를 기준으로 조정한다.

### Manual Sync 후 검증

```bash
kubectl rollout status deployment/news-api -n default --timeout=300s
kubectl get deployment news-api -n default -o wide
kubectl get pods -n default -o wide
kubectl get service,ingress,cronjob -n default
```

```bash
curl -fsS https://api.newslab.ai.kr/health
curl -fsS https://api.newslab.ai.kr/version
```

추가 read-only endpoint는 기존 Runbook 기준으로 확인한다.

### 금지 영역과 문서 형식

```bash
git diff --name-only -- app scripts db .github Dockerfile requirements.txt docker-compose.yml
```

```bash
git diff --check
git status --short
```

실행하지 않은 명령을 Verification에 실행 결과처럼 기록하지 않는다.

## Acceptance criteria

- 68차 설계 문서를 실제 작업 기준으로 사용한다.
- 실제 설치 전에 Argo CD 공식 문서와 안정 version을 다시 확인한다.
- K3s와 ARM64 호환성을 확인한다.
- 선택한 설치 방식과 선택 근거를 기록한다.
- Argo CD가 `argocd` namespace에 설치된다.
- 핵심 Argo CD component가 Ready 상태다.
- Argo CD UI/API를 public internet에 노출하지 않는다.
- `kubectl port-forward`를 통해 로그인할 수 있다.
- Credential 실제 값이 Git 또는 문서에 기록되지 않는다.
- Backend Application 등록 전에 `ClusterIssuer/letsencrypt-prod` ownership을 결정한다.
- `news-api` Application의 repository, revision, path, destination이 68차 설계와 일치한다.
- Automated Sync가 비활성화되어 있다.
- Automatic prune이 비활성화되어 있다.
- Automatic self-heal이 비활성화되어 있다.
- 최초 Sync 전에 desired/live diff를 확인하고 기록한다.
- 예상하지 않은 삭제 또는 resource recreate가 있으면 Sync를 중단한다.
- 사람이 Manual Sync를 명시적으로 승인하고 수행한다.
- Sync operation과 Application history가 확인된다.
- Backend Deployment rollout이 정상 완료된다.
- Backend Pod readiness와 liveness가 정상이다.
- Backend Service, Ingress, TLS가 유지된다.
- `/health`와 `/version`이 정상 응답한다.
- RSS/Daily/Three-day/Weekly CronJob이 유지된다.
- Production endpoint에 기능 회귀가 없다.
- Application code, DB, API, GitHub Actions, image tag 정책을 변경하지 않는다.
- README에는 아직 Argo CD를 현재 운영 구조로 반영하지 않는다.
- 실제 실행 명령과 결과만 Verification에 기록한다.
- 실패 또는 중단 조건이 발생하면 원인과 현재 상태를 기록한다.
- Frontend Application과 고정 image tag 전환은 후속 task로 남긴다.
- `git diff --check`가 통과한다.

## Notes

- 이 작업부터 실제 K3s 운영 변경이 발생한다. 코드 작성 Agent가 설치나 Sync 명령을 대신 실행하지 않는다.
- 사람은 각 고위험 단계 직전에 diff와 영향 범위를 확인한다.
- Argo CD 설치 완료와 Backend Application Sync 완료를 별도 상태로 구분한다.
- 설치 성공만으로 GitOps 적용이 완료된 것이 아니다.
- Application이 `Synced`여도 resource가 `Healthy`하지 않을 수 있다.
- 기존 resource를 Argo CD 관리 대상으로 전환하는 최초 Sync가 가장 위험한 단계다.
- Service ClusterIP, Deployment selector, Ingress annotation처럼 recreate 위험이 있는 차이를 우선 확인한다.
- `latest` image tag는 이번 작업에서 유지한다. 따라서 이번 단계는 Argo CD의 diff, Sync, history 흐름 검증이 목적이며 완전한 배포 재현성은 다음 고정 tag 작업에서 확보한다.
- Application source가 public repository라면 credential 없이 시작할 수 있다. Private 전환 시 credential 관리 task를 별도로 만든다.
- 설치 manifest 또는 Helm chart version은 Task 문서에 고정하지 않고 실제 실행 시 공식 문서에서 다시 확인한다.
- 초기 admin password를 조회한 경우 실제 값을 문서나 채팅에 붙여 넣지 않는다.
- Argo CD를 제거해야 할 경우 Application resource 삭제와 workload 삭제의 관계를 먼저 확인한다.
- README 갱신은 Backend와 Frontend Manual Sync, 고정 tag, rollback 검증 이후 수행한다.

## Implementation Units

- [x] UNIT-01: 설치 전제·공식 버전·K3s ARM64 호환성 및 ownership 확인
- [x] UNIT-02: Argo CD 최소 설치·port-forward 접근·핵심 component 검증 (사람 통제 설치와 cluster API 접근 가능한 환경의 실제 검증 필요)
- [x] UNIT-03: Backend `news-api` Application 정의·최초 diff·Manual Sync 검증 (Application 정의 완료, 최초 diff와 Manual Sync는 사람이 수행 필요)
- [x] UNIT-04: Backend 운영 상태 확인·문서·Verification·후속 task 정리

사람이 cluster 접근 가능한 환경에서 최종 운영 상태를 직접 재확인했다.

- `news-api` Deployment rollout 성공 및 `2/2 Ready`
- Backend Pod 2개 `Running`, restart count 0
- 네 CronJob `SUSPEND=False`, `ACTIVE=0` 및 최근 Pod `Completed`
- Argo CD 핵심 Pod 7개 `1/1 Running`, restart count 0
- Argo CD Deployment 6개와 StatefulSet 1개 Ready
- `argocd-server`는 `ClusterIP`, Argo CD Ingress 없음
- `news-api` Application은 `Manual`, `Synced`, `Healthy`
- 관리 resource 7개는 모두 `ORPHANED: No`
- production `/health` 정상 응답
- `argocd app diff` 출력 없음, exit code 0

Agent 환경의 K3s API 접근 실패는 sandbox의 loopback network 제약으로 발생한
과거 환경 제약이다. 이후 사람이 동일 kubeconfig를 사용해 실제 운영 상태를
확인하여 UNIT-04의 pending 조건을 해소했다.
