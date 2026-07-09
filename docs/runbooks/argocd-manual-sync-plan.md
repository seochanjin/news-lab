# Argo CD Manual Sync Plan

[Runbook index로 돌아가기](../RUNBOOK.md)

이 문서는 Argo CD 승인형 배포 구조를 도입하기 전 사람이 실행할 절차와 확인
경계를 정리하기 위한 계획 문서다. Namespace 생성, Argo CD 설치,
`kubectl apply`, credential 변경과 Application Sync는 사람이 수행한다.
Agent는 read-only 결과와 사람이 제공한 실행 결과만 검증 기록으로 사용한다.

## 현재 Backend 운영 기준

2026-07-09 기준 Argo CD `v3.4.2` non-HA 구성과 `news-api` Application의 최초
Manual Sync가 사람 통제 작업으로 완료되었다. 당시 실제 결과는
`docs/verification/feature-argocd-backend-manual-sync.md`에 기록되어 있다.
Application은 automated sync, automatic prune, automatic self-heal을 사용하지
않으며, `ClusterIssuer/letsencrypt-prod`를 관리하지 않는다.

운영 상태를 다시 확인할 때는 다음 read-only 조회를 사용한다. 이 명령은 Sync나
rollout을 발생시키지 않는다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get application news-api -n argocd
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,statefulset,pods,service,ingress -n argocd -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default --timeout=300s
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,pods,service,ingress,cronjob -n default -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate -n default
curl -fsS https://api.newslab.ai.kr/health
curl -fsS https://api.newslab.ai.kr/version
```

추가 read-only API는 [일상 운영 점검](routine-check.md)의 현재 endpoint를
사용한다. Application의 `Synced`/`Healthy`, Deployment rollout, Pod Ready와
restart count, Service·Ingress·Certificate, 네 CronJob의 존재와 schedule,
`/health`·`/version`을 함께 확인해야 한다. 한 항목이라도 실패하면 재Sync,
restart, patch 또는 삭제를 자동 수행하지 않고 event와 현재 revision을 기록해
사람이 복구 방향을 결정한다.

Argo CD CLI/UI가 필요할 때만 local port-forward를 열고 작업 후 종료한다.
Service type 변경이나 public Ingress 생성은 이 운영 기준에 포함되지 않는다.

## Backend 설치 전 승인 gate

Backend 첫 설치 후보는 공식 Argo CD `v3.4.2` non-HA
`manifests/install.yaml`, namespace는 `argocd`다. 설치는 human-controlled
operation이다. UNIT-01에서 아래 read-only 조회 결과를 확인했으며, 설치 직전
동일 기준에 변화가 없는지 사람이 다시 확인한다.

```bash
kubectl version
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,ARCH:.status.nodeInfo.architecture,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory
kubectl describe nodes
kubectl get clusterissuer letsencrypt-prod -o yaml
```

승인 조건은 다음과 같다.

- Kubernetes server/K3s version이 Argo CD 3.4 공식 테스트 범위
  `v1.32`~`v1.35`에 포함된다.
- 설치 대상 node가 `arm64`다. 실제 image pull과 scheduling은 설치 후
  UNIT-02에서 확인하며 실패하면 진행하지 않는다.
- allocatable 자원과 현재 requests를 비교했을 때 component scheduling
  여유가 있다.
- live `ClusterIssuer/letsencrypt-prod`의 존재와 현재 관리 주체를 확인했다.
- 설치 직전 URL이 `stable`이 아니라 `v3.4.2`로 고정되어 있다.

`news-api` Application은 `k8s/`를 읽되 directory exclude에
`cluster-issuer.yaml`을 지정한다. Application 생성 전에 generated manifest
목록에 `ClusterIssuer`가 없고 다음 일곱 resource만 포함되는지 확인한다.

- `Deployment/news-api`
- `Service/news-api`
- `Ingress/news-api-ingress`
- `CronJob/news-rss-collector`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`

설치 manifest, namespace, Application 생성·Sync, password 변경과 Secret
삭제는 사람이 수행한다. 초기 admin credential 값은 어떤 실행 기록에도 남기지
않는다. 제거가 필요하면 먼저 Application finalizer와 cascade 영향, workload
보존 여부를 확인하고 Application ownership을 분리한다. 그 확인 없이
Application 또는 `argocd` namespace를 삭제하지 않는다.

## Backend 도입 UNIT-03 Application 등록과 Manual Sync

아래 변경 명령은 모두 human-controlled operation이다. 먼저
`k8s/argocd/news-api-application.yaml`의 local diff와 source 설정을 확인한다.
Application 정의는 현재 feature branch의 local 파일로 bootstrap하되, Application
source는 운영 workload manifest가 있는 `main`을 계속 추적한다. PR merge 전에는
bootstrap 정의가 아직 `main`에 없다는 상태를 Verification에 명시한다.

### 1. Bootstrap 전 정적 확인

Application manifest에서 다음 값과 자동화 옵션 부재를 확인한다.

```bash
kubectl create --dry-run=client \
  -f k8s/argocd/news-api-application.yaml -o yaml
rg -n "repoURL:|targetRevision:|path:|recurse:|exclude:|server:|namespace:|automated:|prune:|selfHeal:" \
  k8s/argocd/news-api-application.yaml
```

기대값은 repository `https://github.com/seochanjin/news-lab.git`, revision
`main`, path `k8s`, in-cluster server, namespace `default`, directory
`recurse: false`, exclude `cluster-issuer.yaml`이다. `automated`, `prune`,
`selfHeal`은 없어야 한다.

### 2. Application 생성과 generated resource 확인

다음 변경 명령은 사람이 실행한다.

```bash
kubectl apply -f k8s/argocd/news-api-application.yaml
```

적용 직후 Sync하지 않고 read-only 조회만 수행한다.

```bash
kubectl get applications.argoproj.io news-api -n argocd
kubectl describe application news-api -n argocd
argocd app manifests news-api
argocd app get news-api --show-operation
argocd app diff news-api
```

generated manifest가 정확히 다음 7개인지 확인한다.

- `Deployment/news-api`
- `Service/news-api`
- `Ingress/news-api-ingress`
- `CronJob/news-rss-collector`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`

`ClusterIssuer`, `Application`, monitoring values, Secret, ConfigMap, PVC 또는
그 밖의 resource가 보이면 Sync하지 않는다. Repository 읽기나 manifest 생성이
실패해도 exclude를 추측으로 넓히지 않고 오류와 generated 목록을 기록한다.

### 3. 최초 diff 승인 gate

Sync 전에 다음 live baseline과 diff를 함께 보존한다.

```bash
kubectl get deployment news-api -n default -o wide
kubectl get pods -n default -l app=news-api -o wide
kubectl get service,ingress -n default
kubectl get cronjob -n default
argocd app get news-api
argocd app diff news-api
```

Deployment selector/label, Service ClusterIP와 selector, Ingress annotation,
host와 TLS, 네 CronJob의 schedule/command/suspend, image, Secret reference를
확인한다. 생성·삭제·recreate, Deployment selector 변경, Service ClusterIP
교체 또는 예상하지 않은 defaulted-field 차이가 있으면 중단한다.

### 4. Manual Sync와 결과 확인

diff에 예상하지 않은 변경과 삭제가 없다는 사람의 명시적 승인 후에만 사람이
다음 변경 명령을 실행한다.

```bash
argocd app sync news-api
```

Sync 직후 UNIT-03에서는 Application operation과 resource health를 확인한다.
Deployment rollout, endpoint와 scheduled workload의 최종 production 검증은
UNIT-04에서 별도 수행한다.

```bash
argocd app get news-api --show-operation
kubectl get applications.argoproj.io news-api -n argocd
kubectl describe application news-api -n argocd
```

Sync 실패, `Degraded`, 예상하지 않은 resource 변경 또는 operation history
누락 시 재Sync하거나 resource를 삭제하지 않는다. 현재 Git revision, operation
message, resource 상태와 event를 기록하고 UNIT-04로 진행하지 않는다.

## Backend 도입 UNIT-02 설치와 접근 절차

아래 절차는 human-controlled operation이다. 사람은 NewsLab K3s context와
UNIT-01 승인 조건을 다시 확인한 뒤 명령을 한 단계씩 실행하고, credential 값을
제외한 stdout/stderr를 Verification 근거로 제공한다. Agent는 설치 또는
credential 관련 명령을 대신 실행하지 않는다.

### 1. 고정 version 설치

변경 명령과 read-only 검증 명령을 분리한다. `stable` URL이나 local copy가 아닌
공식 `v3.4.2` URL을 사용한다.

```bash
# 변경 명령: 사람이 실행
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.4.2/manifests/install.yaml
```

Namespace가 이미 존재하면 생성 실패를 무시하고 바로 apply하지 않는다. 기존
Argo CD resource, version과 ownership을 먼저 조회해 신규 설치인지 재적용인지
판단한다. URL fetch, manifest parsing 또는 apply가 실패하면 일부 생성된
resource를 임의로 삭제하지 않고 현재 상태와 event를 기록한 뒤 중단한다.

### 2. Core component와 ARM64 scheduling 확인

다음은 read-only 조회이며, readiness 대기 명령은 resource를 변경하지 않는다.

```bash
kubectl get all -n argocd
kubectl get pods -n argocd -o wide
kubectl get deployment,statefulset,service -n argocd
kubectl get events -n argocd --sort-by=.lastTimestamp
kubectl wait --for=condition=Available deployment --all \
  -n argocd --timeout=300s
kubectl wait --for=condition=Ready pod --all \
  -n argocd --timeout=300s
kubectl get pods -n argocd \
  -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,PHASE:.status.phase,READY:.status.containerStatuses[*].ready,IMAGES:.spec.containers[*].image
kubectl get nodes \
  -o custom-columns=NAME:.metadata.name,ARCH:.status.nodeInfo.architecture
```

설치 성공 조건은 application controller StatefulSet과 server, repo server,
applicationset controller, Dex, notifications controller Deployment가 준비되고,
Redis Pod를 포함한 모든 Pod가 ARM64 node에서 `Running`/Ready인 것이다. 실제
resource 이름과 개수는 고정 manifest 결과를 기준으로 기록한다.

`ImagePullBackOff`, `ErrImagePull`, `CrashLoopBackOff`, `Pending`, readiness
timeout, ARM64가 아닌 node 배치 또는 반복 warning event가 있으면 접근 검증과
Application 등록으로 진행하지 않는다. 실패 Pod의 `describe`와 container별
log를 읽어 원인을 기록하되 resource를 patch, restart 또는 delete하지 않는다.

```bash
kubectl describe pod <pod-name> -n argocd
kubectl logs <pod-name> -n argocd --all-containers
```

### 3. Port-forward와 로그인

Core component가 모두 Ready인 뒤 사람의 로컬 terminal에서 실행한다.

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

별도 terminal에서 `https://127.0.0.1:8080`으로 UI/API 연결을 확인한다. 초기
admin password 조회와 UI 또는 CLI 로그인, password 변경은 사람이 수행한다.
조회 command, password, token과 shell history 출력은 Verification이나 채팅에
남기지 않는다. 기록에는 연결 성공, 로그인 성공 여부와 확인 시각만 남긴다.

로그인 검증 후 port-forward process를 종료하고 `8080` listener가 사라졌는지
확인한다. Service type을 변경하거나 Ingress, LoadBalancer, NodePort를 만들지
않는다. 따라서 public DNS와 외부 network에서 접근 가능하다는 결과가 나오면
UNIT-02 성공이 아니라 노출 조사와 중단 사유다.

### 4. 실패 시 보존과 다음 단계 gate

이 UNIT에서는 자동 제거 또는 rollback을 하지 않는다. 설치 실패 시 namespace나
cluster-scoped RBAC를 삭제하기 전에 생성된 resource, event, 적용 version과
실패 원인을 사람이 검토한다. Application은 core component Ready, port-forward
연결과 로그인 성공, public 노출 없음이 모두 실제 결과로 확인된 뒤에만
UNIT-03에서 등록한다.

## UNIT-01 현재 수동 배포 흐름

NewsLab의 현재 배포 흐름은 image 발행과 K3s 반영이 분리되어 있다.

```text
코드 변경
→ PR review 및 merge
→ GitHub Actions build
→ Docker Hub image push
→ 사람이 rollout 또는 manifest apply
→ 사람이 상태와 서비스 확인
```

### Backend

Backend image는 `news-lab` repository의
`.github/workflows/docker-build.yml`에서 `linux/arm64`로 build되어 Docker Hub에
push된다. workflow는 full Git SHA tag와 `latest` tag를 발행하지만, 현재
운영 manifest는 `seocj/news-api:latest`를 참조한다.

Backend Kubernetes resource는 `news-lab/k8s/`에 있다.

- `news-api.yaml`: Deployment, Service, Ingress
- `news-rss-collector-cronjob.yaml`: RSS collector CronJob
- `news-daily-topic-pipeline-cronjob.yaml`: daily topic pipeline CronJob
- `news-three-day-topic-pipeline-cronjob.yaml`: three-day topic pipeline CronJob
- `news-weekly-topic-pipeline-cronjob.yaml`: weekly topic pipeline CronJob

현재 backend 배포에서 사람이 판단하는 대표 작업은 다음이다.

- 새 image가 registry에 준비되었는지 확인
- manifest 변경 시 apply 여부 결정
- `latest` image refresh가 필요할 때 rollout restart 여부 결정
- rollout status, Pod 상태, running image, production endpoint 확인
- 실패 시 원인 확인 후 rollback 또는 재적용 여부 결정

### Frontend

Frontend image는 `news-lab-web` repository의
`.github/workflows/docker-build.yml`에서 `linux/arm64`로 build된다. pull
request에서는 push하지 않고, `main` branch push, `v*` tag push,
`workflow_dispatch` 같은 non-PR event에서 Docker Hub에 push한다.

현재 tag policy는 다음과 같다.

- `main`
- `latest`
- `v*` version tag
- `sha-<short-sha>`

현재 운영 manifest는 `seocj/news-lab-web:latest`를 참조한다.

Frontend Kubernetes resource는 `news-lab-web/k8s/`에 있다.

- `news-lab-web-deployment.yaml`: Deployment
- `news-lab-web-service.yaml`: Service
- `news-lab-web-ingress.yaml`: Ingress
- `news-lab-web-redirect-https-middleware.yaml`: Traefik Middleware

### 현재 manual operation 원칙

다음 command는 agent가 실행하지 않고 사람이 통제한다.

- `kubectl apply`
- `kubectl delete`, `kubectl patch`, `kubectl edit`
- `kubectl rollout restart`
- Helm install, upgrade, uninstall
- Docker push
- Supabase SQL과 production migration
- Secret, credential, kubeconfig 변경
- production verification

현재 runbook의 backend 배포 절차도 같은 원칙을 따른다. Agent는 command를
제안하거나 사람이 제공한 결과를 정리할 수 있지만, cluster 변경과 production
검증을 완료로 주장하지 않는다.

## UNIT-02 초기 Application 등록 기준

### 설치 전제

후속 task에서 사람이 Argo CD를 설치할 때의 namespace 후보는 `argocd`다. 이
문서는 설치 완료를 전제로 하지 않으며, namespace 생성이나 Helm 실행 결과를
기록하지 않는다.

Argo CD server 접근은 처음에는 `kubectl port-forward`를 우선한다. 이 방식은
public internet에 UI/API를 노출하지 않고, kubeconfig를 가진 사람이 필요할 때만
접속한다. 반복 운영이 불편해지는 시점에 Tailscale 내부 접근 또는 내부 전용
Ingress를 별도 task로 검토한다.

초기 admin credential은 설치 직후 사람이 확인하고 변경한다. 실제 password,
token, kubeconfig, repository credential 값은 Git과 문서에 기록하지 않는다.

### Application 후보

후속 Application 등록 task에서 사용할 초기 후보는 다음이다.

| Application | Repository | Revision | Path | Destination | Namespace | Sync |
| --- | --- | --- | --- | --- | --- | --- |
| `news-api` | `https://github.com/seochanjin/news-lab.git` | `main` | `k8s/` | in-cluster | `default` | Manual |
| `news-lab-web` | `https://github.com/seochanjin/news-lab-web.git` | `main` | `k8s/` | in-cluster | `default` | Manual |

두 Application 모두 `spec.syncPolicy.automated`를 설정하지 않는 방향으로
등록한다. automatic prune과 automatic self-heal도 초기에는 사용하지 않는다.

삭제가 포함된 Sync는 일반 수동 Sync와 구분해 별도 사람 승인을 요구한다. 특히
Deployment, Service, Ingress, CronJob, Traefik Middleware 삭제는 service
availability와 scheduled workload에 직접 영향을 줄 수 있으므로 Sync 전에 diff를
분리해 확인한다.

### Backend 등록 전 확인

`news-api` Application의 ownership은 backend workload에 한정한다.

- Deployment `news-api`
- Service `news-api`
- Ingress `news-api-ingress`
- CronJob `news-rss-collector`
- CronJob `news-daily-topic-pipeline`
- CronJob `news-three-day-topic-pipeline`
- CronJob `news-weekly-topic-pipeline`

현재 backend `k8s/` 경로에는 `ClusterIssuer/letsencrypt-prod` manifest도 있다.
이 resource는 cluster-wide TLS 인프라이므로 shared infrastructure 소유로
남기고 `news-api`의 directory exclude에서 `cluster-issuer.yaml`을 제외한다.
Application 등록 전에 generated manifest 목록에서 실제 제외 여부를 확인한다.

### Frontend 등록 전 확인

`news-lab-web` Application의 ownership은 frontend resource에 한정한다.

- Deployment `news-lab-web`
- Service `news-lab-web`
- Ingress `news-lab-web-ingress`
- Traefik Middleware `news-lab-web-redirect-https`

Frontend repository의 `k8s/` 경로는 현재 frontend resource만 포함하므로 초기
Application 경계와 repository path가 비교적 일치한다. 그래도 첫 Sync 전에는
Argo CD diff에서 destination namespace, image, Service selector, Ingress host,
Middleware reference를 사람이 확인한다.

### Repository credential 원칙

현재 후보 repository는 public HTTPS URL이다. public read 접근이 유지되면 별도
repository credential 없이 Application source로 사용할 수 있다.

Repository가 private으로 바뀌면 Argo CD repository credential을 별도로 등록해야
한다. credential은 Argo CD 또는 Kubernetes Secret 관리 범위에 두고, 이 repository
문서나 manifest에 평문으로 기록하지 않는다.

### Manual Sync 운영 원칙

Manual Sync의 기본 흐름은 다음으로 둔다.

```text
Git manifest 변경 감지
→ Argo CD가 OutOfSync와 diff 표시
→ 사람이 Application, repository, revision, path, namespace 확인
→ 사람이 삭제·Secret·DB migration·CronJob 영향 여부 확인
→ 사람이 Sync 승인
→ Argo CD가 cluster에 반영
→ 사람이 rollout, Pod, endpoint 상태 확인
```

`OutOfSync`는 자동 배포 대기 상태가 아니라 사람이 diff를 검토해야 하는 상태다.
`Synced`는 Git desired state와 cluster live state가 맞는다는 뜻이지 production
API나 web service가 정상이라는 최종 판정은 아니다.

DB migration, Supabase SQL, Secret 값 변경, Docker push, production endpoint
verification은 Argo CD Sync에 자동 포함하지 않는다. 해당 작업은 별도 task와
사람 실행 기록이 필요하다.

## UNIT-03 고정 tag, Sync, rollback 실행 계획

### 고정 image tag 전환 계획

초기 운영 manifest는 `latest` 대신 Git commit을 식별할 수 있는 고정 image tag를
사용하는 방향으로 전환한다.

- Backend 권장 형식: `seocj/news-api:<full-git-sha>`
- Frontend 권장 형식: `seocj/news-lab-web:<full-git-sha>`
- `latest`: 보조 tag로는 발행 가능하지만 운영 manifest 기준으로 사용하지 않음
- manifest tag 갱신: 초기에는 사람이 manifest 변경 PR을 작성하고 review 후 merge
- 자동 tag update: Manual Sync와 rollback 검증 이후 별도 task에서 재검토

Frontend는 현재 `sha-<short-sha>` tag를 발행하므로, full Git SHA tag 발행은
별도 GitHub Actions 변경 task에서 다룬다. 이 plan에서는 workflow를 수정하지
않는다.

### Manual Sync 전 checklist

사람이 Argo CD에서 Sync를 승인하기 전에 다음을 확인한다.

- Application:
  - 대상이 `news-api` 또는 `news-lab-web` 중 의도한 Application인지 확인
  - source repository, revision, path가 기대값인지 확인
  - destination cluster와 namespace가 기대값인지 확인
- Diff:
  - image tag가 의도한 고정 tag인지 확인
  - Deployment, Service, Ingress, CronJob, Middleware 변경을 구분
  - 삭제가 포함되면 일반 Sync와 분리해 별도 승인
  - Backend에서는 CronJob schedule, command, Secret reference 변경 확인
  - Frontend에서는 Ingress host, TLS Secret resource name, Middleware reference 확인
- 운영 영향:
  - Secret 또는 ConfigMap 변경 필요 여부 확인
  - DB migration 또는 Supabase SQL 필요 여부 확인
  - production endpoint 영향 범위 확인
  - rollback에 사용할 이전 Git revision 또는 image tag 확인

Secret 값 변경, DB migration, Supabase SQL, data write script는 Argo CD Sync와
분리해 별도 승인과 실행 기록을 남긴다.

### Manual Sync 후 checklist

Sync 후에는 Argo CD status와 Kubernetes/service 상태를 모두 확인한다. 이 task는
cluster command를 실행하지 않으며, 아래 항목은 후속 작업의 사람 실행 기준이다.

- Argo CD Application status가 `Synced`인지 확인
- Argo CD Application health가 `Healthy`인지 확인
- Deployment rollout 상태 확인
- Pod 상태, restart count, event 확인
- 실행 중인 Pod image가 의도한 고정 tag인지 확인
- Service endpoint와 Ingress routing 확인
- Backend API health 또는 Frontend service endpoint 확인
- CronJob 변경이 있으면 schedule과 최근 Job 상태 확인

사람이 제공한 실제 결과 없이 production verification을 완료로 기록하지 않는다.

### Rollback 절차 기준

초기 rollback은 사람이 승인하고 실행한다. 자동 rollback은 사용하지 않는다.

권장 rollback 흐름은 다음이다.

```text
장애 또는 회귀 확인
→ 영향 범위와 현재 running image 확인
→ 이전 정상 Git revision 또는 고정 image tag 선택
→ manifest rollback PR 작성
→ review 및 merge
→ Argo CD diff 확인
→ 사람이 Manual Sync 승인
→ rollout, Pod, endpoint 상태 검증
```

긴급 상황에서 사람이 cluster에서 직접 rollback 명령을 선택할 수는 있지만, 그
경우에도 Git desired state와 live state가 달라진다. 이후에는 Git manifest를
실제 운영 상태에 맞게 복구하거나, Argo CD diff를 확인해 다시 Sync 계획을 세운다.

Rollback 전 확인 항목은 다음이다.

- 이전 image tag가 registry에 존재하는지 확인
- DB schema와 data가 이전 app version과 호환되는지 확인
- Secret과 ConfigMap이 이전 app version과 호환되는지 확인
- CronJob이 중복 실행되거나 누락되지 않는지 확인
- Ingress와 Service 변경이 rollback 대상에 포함되는지 확인

`latest`는 rollback 기준으로 사용하지 않는다.

### 후속 task 분리

실제 운영 반영은 다음 순서의 별도 task로 수행한다.

1. Argo CD 최소 설치
   - 사람이 설치 방식과 version을 공식 문서로 재확인한다.
   - namespace 후보는 `argocd`다.
   - public internet 노출 없이 `kubectl port-forward` 접근을 우선한다.
2. Backend Application 등록
   - `ClusterIssuer/letsencrypt-prod` ownership을 먼저 결정한다.
   - `news-api` Application은 Manual Sync로 등록한다.
3. Backend Manual Sync 검증
   - diff, Sync, rollout, API health, CronJob 상태를 사람이 확인한다.
4. Frontend Application 등록
   - `news-lab-web` Application은 Manual Sync로 등록한다.
5. Frontend Manual Sync 검증
   - diff, Sync, rollout, web endpoint, Ingress/Middleware 상태를 사람이 확인한다.
6. 고정 image tag 적용
   - Backend와 Frontend tag 형식과 workflow 변경 여부를 별도 PR로 다룬다.
7. 이전 revision rollback 검증
   - 실제 rollback 가능성을 사람이 controlled test로 확인한다.
8. Architecture와 Runbook 갱신
   - 실제 설치·검증 결과가 생긴 뒤 현재 운영 문서로 승격한다.
9. README GitOps 배포 구조 반영
   - Argo CD Manual Sync가 검증된 뒤에만 현재 배포 구조로 작성한다.

위 단계의 command 예시는 후속 runbook에서 human-controlled command로만 작성할
수 있다. 이 task의 verification에는 실행하지 않은 설치, Sync, rollback 결과를
기록하지 않는다.
