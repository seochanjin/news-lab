# Argo CD Manual Sync Design

[Architecture index로 돌아가기](../ARCHITECTURE.md)

이 문서는 NewsLab의 Argo CD 승인형 GitOps 배포 구조와 Backend 최초 도입 결과를
정리한다. 기존 CI, image tag, manifest, 수동 배포 흐름, Application 경계,
Manual Sync 정책을 repository 근거로 설명하고, 실제 설치·Sync 결과는
`docs/verification/feature-argocd-backend-manual-sync.md`를 source of truth로
사용한다.

## Backend 도입 UNIT-01 설치 전 결정

2026-07-09 공식 자료를 다시 확인한 결과, Backend 첫 검증에는 Argo CD
`v3.4.2`의 공식 non-HA `manifests/install.yaml`을 고정해서 사용한다.
`stable` branch URL은 이후 내용이 바뀔 수 있으므로 운영 설치 입력으로 사용하지
않는다.

### 설치 방식과 구성

| 항목 | 결정 | 근거 |
| --- | --- | --- |
| Version | `v3.4.2` | 확인 시점의 공식 최신 stable release이며 production 설치는 version 고정을 권장한다. |
| 배포 자료 | 공식 non-HA `install.yaml` | Helm chart는 community maintained이고, 최초 검증에는 공식 release와 직접 대응하는 단일 manifest가 더 단순하다. |
| Namespace | `argocd` | 공식 manifest의 ClusterRoleBinding이 이 namespace의 ServiceAccount를 참조한다. |
| 설치 유형 | 표준 multi-tenant non-HA | UI/API와 in-cluster 배포 권한이 필요하므로 API/UI가 없는 core 설치는 목적에 맞지 않는다. |
| 제외 구성 | HA, SSO 설정, external Redis, public Ingress | 이번 검증 범위 밖이며 public 노출 없이 port-forward만 사용한다. |

공식 문서는 non-HA 설치를 평가·검증 용도로 설명하고 production에는 HA를
권장한다. NewsLab은 이번 단계에서 최소 설치와 Manual Sync 흐름만 검증하므로
non-HA를 선택한다. 이는 고가용성 보장을 의미하지 않으며, 장기 운영 전 HA 전환
여부는 별도 판단이 필요하다.

표준 manifest에는 application controller, applicationset controller,
repo server, server, Redis와 Dex가 포함된다. Dex는 이번 단계에서 SSO에
사용하지 않지만, 공식 manifest를 임의로 변형하지 않기 위해 설치 구성은
유지한다. 실제 생성 resource와 Ready 상태는 설치 후 UNIT-02에서 확인한다.

### Kubernetes와 ARM64 전제

Argo CD 3.4의 공식 테스트 Kubernetes 범위는 `v1.32`부터 `v1.35`까지다.
K3s 자체는 `arm64/aarch64`를 지원하고, Argo CD v3.4.2 release는 Linux ARM64
CLI artifact를 제공한다. 현재 cluster 조회 결과 세 node는 모두
`v1.35.5+k3s1`/`arm64`이며, Argo CD 3.4의 공식 Kubernetes 테스트 범위에
포함된다. 설치 전제는 충족하지만 실제 container image pull과 scheduling은
설치 후 UNIT-02에서 확인한다.

- K3s server version이 Argo CD 3.4 테스트 범위인 `v1.32`~`v1.35`인지
- 모든 설치 대상 node의 `kubernetes.io/arch`가 `arm64`인지
- allocatable CPU/memory와 현재 requests 기준으로 모든 component를 배치할
  여유가 있는지

확인 시점의 allocatable 자원은 node별 CPU `2`, `2`, `4`와 memory 약
`12Gi`, `12Gi`, `8Gi`다. 현재 requests는 master `200m/140Mi`, worker
`550m/1280Mi`, Pi worker `0/0`으로 확인되어 최소 설치를 검토할 여유가 있다.
이는 component Ready를 보장하지 않으며, image pull 또는 scheduling 실패 시
UNIT-02에서 설치를 중단한다. 공식 install manifest는 NewsLab 전용 sizing
자료가 아니므로 K3s 자체 최소 사양만으로 capacity를 판정하지 않는다.

### Credential, 제거와 복구 전제

초기 접근은 `argocd-server` Service에 대한 `kubectl port-forward`만 사용한다.
초기 admin password는 `argocd-initial-admin-secret`에서 사람이 조회하되 값을
문서나 Git에 기록하지 않는다. 첫 로그인 후 password를 변경하고 초기 Secret을
삭제하는 절차도 사람 통제 작업으로 둔다.

제거 전에는 Application finalizer와 cascade 삭제가 기존 workload를 함께
삭제할 수 있으므로, Application ownership을 해제하고 workload 보존 여부를
확정하기 전에는 Argo CD resource나 namespace를 삭제하지 않는다. 복구는 같은
고정 version manifest 재설치, 설정/credential 복원, Application diff 재검토
순서로 계획하며 실제 제거·복구 시험은 이번 UNIT에서 수행하지 않는다.

### `ClusterIssuer/letsencrypt-prod` ownership

`ClusterIssuer/letsencrypt-prod`는 Backend Application이 아니라 shared
infrastructure 소유로 확정한다. `k8s/cluster-issuer.yaml`을 이번 작업에서
이동하지 않고, `news-api` Application의 directory source에서
`cluster-issuer.yaml`을 명시적으로 제외한다.

따라서 `news-api`의 관리 대상은 `Deployment/news-api`, `Service/news-api`,
`Ingress/news-api-ingress`와 네 Backend CronJob뿐이다. Application 생성 전
rendered resource 목록에 `ClusterIssuer`가 없음을 확인해야 하며, live
`ClusterIssuer`의 존재와 현재 관리 주체도 사람이 확인한다. 제외 설정이
동작하지 않거나 ownership이 불명확하면 Application 생성과 Sync를 중단한다.

## Backend 도입 UNIT-03 Application 정의

`news-api`의 선언형 Application은
`k8s/argocd/news-api-application.yaml`에 둔다. Bootstrap은 사람이 이 파일을
명시해 최초 한 번 수행하며, Application source는 `main` revision의 `k8s`
directory다. Source directory의 `recurse`는 `false`로 고정한다.

이 설정은 root의 Backend manifest만 읽고 `k8s/monitoring/`의 Helm values와
`k8s/argocd/`의 Application 정의는 workload source에서 제외한다.
`cluster-issuer.yaml`은 directory exclude로 별도 제외한다. 따라서 기대하는
generated resource는 기존에 확정한 Backend resource 7개뿐이다.

Application에는 `spec.syncPolicy.automated`를 두지 않는다. 따라서 automated
sync, automatic prune, automatic self-heal은 모두 비활성 상태다. Application
삭제가 Backend workload의 cascade 삭제로 이어지지 않도록 resources finalizer도
추가하지 않는다.

Application manifest 자체는 workload Application의 관리 대상이 아니다. 최초
생성과 이후 Application spec 변경은 사람이 manifest diff를 검토한 뒤
명시적으로 적용한다. 별도 App of Apps 또는 bootstrap Application 도입은 이번
범위에 포함하지 않는다.

## Backend 최초 도입 운영 상태

2026-07-09 사람 통제 작업으로 Argo CD `v3.4.2` non-HA 구성을 `argocd`
namespace에 설치하고 `news-api` Application의 최초 Manual Sync를 수행했다.
확인된 상태는 다음과 같다.

- Argo CD 핵심 Pod 7개가 ARM64 node에서 Ready 상태다.
- `argocd-server`는 `ClusterIP`이고 Argo CD Ingress는 없다.
- 접근은 local `kubectl port-forward`로 제한한다.
- `news-api`는 `main`의 `k8s` path를 추적하며 Sync Policy는 Manual이다.
- 관리 대상은 Backend Deployment, Service, Ingress와 네 CronJob 등 7개다.
- `ClusterIssuer/letsencrypt-prod`는 shared infrastructure 소유로 제외했다.
- 최초 diff는 7개 resource의 Argo CD tracking annotation 추가만 포함했다.
- 최초 Sync operation은 성공했고 당시 Application은 `Synced`, `Healthy`였다.
- 당시 Backend Deployment `2/2 Ready`, 네 CronJob `SUSPEND=False`,
  production `/health` 정상 응답을 확인했다.

위 내용은 해당 시점의 검증 결과다. 이후 운영 상태를 보장하지 않으며 현재
상태는 runbook의 read-only 점검을 다시 수행해 판단한다. `latest` image tag,
non-HA 구성, admin 기반 port-forward 접근은 그대로 남아 있으므로 완전한 배포
재현성, Argo CD 고가용성 또는 장기 접근 정책이 확립됐다는 뜻은 아니다.

Frontend Application 등록, Backend·Frontend 고정 image tag 전환, controlled
rollback 시험, Tailscale 내부 접근 검토와 README 운영 구조 갱신은 별도 후속
task로 분리한다.

## UNIT-01 현재 배포 baseline

### CI와 CD 역할 구분

CI는 code change를 build와 test 가능한 artifact로 만드는 단계다. NewsLab의
현재 CI는 GitHub Actions에서 Docker image를 build하고 Docker Hub에 push하는
역할까지 담당한다.

CD는 어떤 artifact를 어떤 manifest로 운영 cluster에 반영할지 결정하고, live
state를 확인하는 단계다. 현재 NewsLab은 이 CD 단계를 완전 자동화하지 않는다.
운영 apply, rollout restart, rollout 상태 확인, production endpoint 확인은
사람이 통제한다.

현재 흐름은 다음과 같다.

```text
코드 변경
→ PR review 및 merge
→ GitHub Actions build
→ Docker Hub image push
→ 사람이 rollout 또는 manifest apply
→ 사람이 상태와 서비스 확인
```

### Backend CI와 image tag

Backend repository는 `news-lab`이다.

- Workflow: `.github/workflows/docker-build.yml`
- Trigger:
  - `main` branch push
  - path filter: `app/**`, `scripts/**`, `requirements.txt`, `Dockerfile`,
    `.github/workflows/docker-build.yml`
  - `workflow_dispatch`
- Build runner: `ubuntu-latest`
- Build action: `docker/build-push-action@v6`
- Build platform: `linux/arm64`
- Push: 항상 `true`
- Docker Hub image:
  - `${{ secrets.DOCKERHUB_USERNAME }}/news-api:${{ github.sha }}`
  - `${{ secrets.DOCKERHUB_USERNAME }}/news-api:latest`
- 운영 manifest의 실제 image reference:
  - `seocj/news-api:latest`

Backend workflow는 full Git SHA tag와 `latest` tag를 함께 발행한다. 그러나
현재 K3s manifest는 full Git SHA tag가 아니라 `latest`만 참조한다.

### Backend K3s manifest

Backend repository의 `k8s/`에는 다음 운영 manifest가 있다.

| File | Resource | 현재 image |
| --- | --- | --- |
| `k8s/news-api.yaml` | Deployment `news-api`, Service `news-api`, Ingress `news-api-ingress` | `seocj/news-api:latest` |
| `k8s/news-rss-collector-cronjob.yaml` | CronJob `news-rss-collector` | `seocj/news-api:latest` |
| `k8s/news-daily-topic-pipeline-cronjob.yaml` | CronJob `news-daily-topic-pipeline` | `seocj/news-api:latest` |
| `k8s/news-three-day-topic-pipeline-cronjob.yaml` | CronJob `news-three-day-topic-pipeline` | `seocj/news-api:latest` |
| `k8s/news-weekly-topic-pipeline-cronjob.yaml` | CronJob `news-weekly-topic-pipeline` | `seocj/news-api:latest` |
| `k8s/cluster-issuer.yaml` | ClusterIssuer `letsencrypt-prod` | image 없음 |

API Deployment와 CronJob은 `workload: app` node selector를 사용한다. Backend
Deployment는 `replicas: 2`이고, image pull policy는 `Always`다. Secret 값은
manifest에 평문으로 저장하지 않고 `news-api-secret` reference로만 연결한다.

### Frontend CI와 image tag

Frontend repository는 `news-lab-web`이다.

- Docker workflow: `.github/workflows/docker-build.yml`
- Docker workflow trigger:
  - `pull_request`
  - `main` branch push
  - `v*` tag push
  - `workflow_dispatch`
- Build runner: `ubuntu-latest`
- Build actions:
  - `docker/setup-qemu-action@v3`
  - `docker/setup-buildx-action@v3`
  - `docker/metadata-action@v5`
  - `docker/build-push-action@v6`
- Build platform: `linux/arm64`
- Push:
  - pull request에서는 push하지 않음
  - non-PR event에서는 Docker Hub push
- Docker Hub image: `seocj/news-lab-web`
- Tag policy:
  - `main` branch에서 `main`
  - `main` branch에서 `latest`
  - `v*` tag push에서 version tag
  - 모든 event에서 `sha-<short-sha>` 형식의 SHA tag
- 운영 manifest의 실제 image reference:
  - `seocj/news-lab-web:latest`

Frontend에는 별도 `.github/workflows/ci.yml`도 있다. 이 workflow는
`pull_request`, `main` branch push, `feature/frontend-baseline` branch push에서
lint, typecheck, build를 실행한다.

### Frontend K3s manifest

Frontend repository의 `k8s/`에는 다음 운영 manifest가 있다.

| File | Resource | 현재 image |
| --- | --- | --- |
| `k8s/news-lab-web-deployment.yaml` | Deployment `news-lab-web` | `seocj/news-lab-web:latest` |
| `k8s/news-lab-web-service.yaml` | Service `news-lab-web` | image 없음 |
| `k8s/news-lab-web-ingress.yaml` | Ingress `news-lab-web-ingress` | image 없음 |
| `k8s/news-lab-web-redirect-https-middleware.yaml` | Traefik Middleware `news-lab-web-redirect-https` | image 없음 |

Frontend Deployment는 `replicas: 2`, `workload: app` node selector,
`imagePullPolicy: Always`, `/api/health` readiness/liveness probe를 사용한다.

### Manifest repository 분산 상태

현재 backend와 frontend는 각 repository가 자신의 Kubernetes manifest를
보유한다.

- Backend API, backend Service, backend Ingress, backend CronJob은
  `news-lab/k8s/`에 있다.
- Frontend Deployment, Service, Ingress, Traefik Middleware는
  `news-lab-web/k8s/`에 있다.
- Backend repository에는 Argo CD Application manifest 또는 Argo CD 설치
  manifest가 없다.

별도 deployment repository는 현재 baseline에 없다. Application 경계와 GitOps
source repository 전략은 UNIT-02에서 아래와 같이 결정한다.

### 현재 수동 승인 지점

현재 사람이 승인하고 실행하는 지점은 다음과 같다.

- PR review 및 merge
- GitHub Actions 결과 확인
- Docker Hub에 새 image가 준비됐는지 확인
- manifest 변경이 있으면 `kubectl apply` 실행 여부 판단
- `latest` image refresh가 필요하면 `kubectl rollout restart` 실행 여부 판단
- rollout 상태와 Pod 상태 확인
- Ingress, TLS, endpoint 등 production service 확인
- 실패 시 rollback 또는 재적용 판단

이 구조의 장점은 운영 변경 승인권이 사람에게 남아 있고, cluster 변경 command가
자동으로 실행되지 않는다는 점이다. 단점은 `latest` tag를 사용할 때 어떤
Git commit의 image가 실제 Pod에 실행 중인지 Git manifest만으로 식별하기
어렵고, 새 image push가 Git diff로 표현되지 않는다는 점이다.

## UNIT-02 Application 경계와 Manual Sync 정책

### Argo CD의 역할

Argo CD는 Git repository의 Kubernetes manifest를 desired state로 보고, K3s
cluster의 live state와 비교하는 CD 도구로 둔다. CI가 Docker image를 build하고
registry에 push하는 책임을 계속 맡고, Argo CD는 Git에 기록된 manifest revision을
cluster에 반영할지 보여주고 실행하는 책임을 맡는다.

Argo CD 공식 문서의 Application 예시도 `source.repoURL`,
`source.targetRevision`, `source.path`, `destination.server`,
`destination.namespace`로 Git source와 적용 대상 cluster/namespace를 분리해
정의한다. NewsLab도 이 구조를 따른다.

### Application 분리 결정

초기에는 App of Apps, ApplicationSet, Argo CD Image Updater를 사용하지 않고
standalone Application 2개로 시작한다.

| Application | Source repository | targetRevision | path | Destination | Namespace | Resource ownership |
| --- | --- | --- | --- | --- | --- | --- |
| `news-api` | `https://github.com/seochanjin/news-lab.git` | `main` | `k8s/` | in-cluster K3s | `default` | Backend Deployment, Service, Ingress, CronJob |
| `news-lab-web` | `https://github.com/seochanjin/news-lab-web.git` | `main` | `k8s/` | in-cluster K3s | `default` | Frontend Deployment, Service, Ingress, Traefik Middleware |

`targetRevision`은 운영 반영 기준 branch인 `main`으로 둔다. feature branch는
설계와 review 대상일 뿐, 운영 Argo CD Application이 추적할 revision으로 두지
않는다.

현재 manifest는 namespace를 명시하지 않으므로 destination namespace 후보는
현재 운영 기준인 `default`다. 전용 namespace 분리는 별도 manifest 변경과 운영
검증이 필요하므로 이번 baseline에 포함하지 않는다.

### Backend ownership 주의점

Backend repository의 `k8s/`에는 `k8s/cluster-issuer.yaml`도 있다.
`ClusterIssuer`는 backend workload가 아니라 cluster-wide TLS 인프라다. 따라서
`news-api` Application의 소유 범위는 다음으로 제한하는 것이 원칙이다.

- `Deployment/news-api`
- `Service/news-api`
- `Ingress/news-api-ingress`
- `CronJob/news-rss-collector`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`

Backend 도입 UNIT-01에서 `cluster-issuer.yaml`은 shared infrastructure 소유로
남기고 Argo CD directory exclude로 제외하기로 확정했다. 이 task에서는
manifest를 이동하거나 수정하지 않는다.

### GitOps source repository 선택

현재 규모에서는 별도 deployment repository를 만들지 않는다. Backend와 Frontend
각 repository가 이미 자신의 K3s manifest를 갖고 있으므로, 초기 Argo CD
Application은 각 repository의 `k8s/` 경로를 직접 추적한다.

이 선택의 장점은 다음이다.

- 현재 repository 구조를 거의 바꾸지 않는다.
- Backend와 Frontend 배포 경계가 code ownership과 일치한다.
- 처음 Argo CD를 도입할 때 학습 비용과 migration 범위가 작다.

한계도 명확하다.

- Backend와 Frontend가 한 화면의 단일 배포 묶음으로 보이지 않는다.
- shared infrastructure resource가 app 경계에 섞일 수 있다.
- 두 repository의 image tag 변경 commit을 동시에 관리하기 어렵다.

별도 deployment repository는 고정 image tag 전환과 rollback 검증이 끝난 뒤,
두 app의 release coordination 문제가 실제로 커질 때 재검토한다.

### Sync policy

초기 정책은 사람 승인 기반 Manual Sync다.

| 항목 | 초기 결정 | 이유 |
| --- | --- | --- |
| Manual Sync | 사용 | Git diff와 영향 범위를 사람이 확인한 뒤 반영한다. |
| `spec.syncPolicy.automated` | 사용하지 않음 | Git 변경이 운영 cluster에 자동 반영되지 않게 한다. |
| automatic prune | 사용하지 않음 | 삭제가 포함된 변경은 별도 사람 확인을 요구한다. |
| automatic self-heal | 사용하지 않음 | live state drift를 사람이 원인 확인 없이 되돌리지 않는다. |
| deletion 포함 Sync | 별도 사람 승인 필요 | Service, Ingress, CronJob 삭제는 운영 영향이 크다. |

Argo CD 공식 문서는 automated sync가 Git desired manifest와 cluster live state의
차이를 감지해 자동 반영할 수 있고, automated prune과 self-heal도 별도 옵션으로
활성화할 수 있다고 설명한다. NewsLab은 운영 변경 승인권을 사람에게 유지하는
것이 우선이므로 이 자동화 옵션을 초기 baseline에서 제외한다.

### Application 상태 해석

운영자가 Argo CD 화면이나 CLI에서 보는 상태는 다음처럼 해석한다.

- `Synced`: Git desired state와 cluster live state가 일치한다.
- `OutOfSync`: Git과 cluster live state에 차이가 있다. 아직 운영 반영을 뜻하지
  않는다.
- `Healthy`: Argo CD가 resource 상태를 기대 상태로 판단한다.
- `Degraded`: 일부 resource가 정상 상태가 아니거나 rollout이 실패했다.
- Refresh: Git과 live state를 다시 비교한다.
- Sync: Git desired state를 cluster에 반영한다. NewsLab에서는 사람이 승인한
  뒤에만 실행한다.

`OutOfSync`는 장애가 아니라 검토 대기 상태일 수 있다. 반대로 `Synced`여도
production endpoint나 business-level 동작이 정상이라는 뜻은 아니므로 Sync 후
별도 서비스 검증이 필요하다.

### 접근과 보안 방향

Argo CD namespace 후보는 `argocd`다. 설치 시점에 공식 설치 문서와 chart 또는
manifest version을 다시 확인하고, 이 task에서는 namespace를 생성하지 않는다.

초기 Argo CD server 접근 방식은 public internet 노출을 기본값으로 두지 않는다.

| 후보 | 초기 판단 | 비고 |
| --- | --- | --- |
| `kubectl port-forward` | 1순위 | 가장 단순하고 외부 노출이 없다. 사람이 kubeconfig로 접근한다. |
| Tailscale 내부 접근 | 2순위 | 반복 운영이 필요해지면 내부망 접근으로 검토한다. |
| 내부 전용 Ingress | 후순위 | DNS, TLS, network policy 검토 후 별도 task로 다룬다. |
| Public Ingress | 기본값 아님 | 별도 보안 검토 없이 사용하지 않는다. |

초기 admin credential은 설치 직후 사람이 회수하고 변경한다. password, token,
kubeconfig, repository credential 값은 Git과 문서에 기록하지 않는다.

Backend와 Frontend repository가 public으로 유지된다면 Argo CD repository
credential 없이 읽기 접근할 수 있다. private repository로 전환하거나 private
submodule, private Helm chart 같은 의존성이 생기면 Argo CD repository credential을
별도로 등록해야 한다. 공식 문서 기준 private repository에는 HTTPS 또는 SSH Git
credential을 설정할 수 있지만, 실제 값은 Kubernetes Secret 또는 Argo CD 내부
설정으로만 관리하고 Git에 평문 저장하지 않는다.

RBAC와 SSO는 초기 설치와 Manual Sync 검증 이후에 도입한다. 처음에는 최소
운영자만 접근하고, 반복 운영자가 늘어날 때 role과 project 경계를 별도 task로
설계한다.

### 책임 경계

Argo CD가 담당하는 것은 다음이다.

- Git manifest와 live state 비교
- Application별 diff 표시
- 사람이 승인한 Manual Sync 실행
- resource health와 sync history 제공

Argo CD가 자동으로 담당하지 않는 것은 다음이다.

- Docker image build와 push
- Git manifest의 image tag 변경 commit 작성
- Secret 값 생성 또는 변경
- Supabase SQL과 DB migration 실행
- production endpoint 최종 검증
- 자동 rollback

DB migration과 Secret 변경이 포함된 배포는 Argo CD Sync만으로 완료하지 않는다.
사람이 migration 순서, Secret 준비 여부, rollback 가능성을 별도로 확인한 뒤
작업해야 한다.

## UNIT-03 고정 image tag, Sync, rollback 계획

### 고정 image tag 전략

현재 `latest` tag는 GitOps 기준으로 다음 한계가 있다.

- Git commit만 보고 실제 배포 image를 식별하기 어렵다.
- Argo CD는 registry의 새 `latest` push를 Git diff로 감지하지 못한다.
- 같은 manifest revision에서도 다른 image가 실행될 수 있다.
- rollback 기준이 Git revision인지 registry tag인지 불명확해진다.

고정 tag 후보는 다음처럼 비교한다.

| 후보 | 판단 |
| --- | --- |
| `<full-git-sha>` | Backend가 이미 발행한다. 충돌 가능성이 가장 낮고 commit 추적이 명확하다. |
| `<short-git-sha>` | 사람이 읽기 쉽지만 충돌 가능성을 완전히 제거하지는 않는다. |
| `YYYYMMDD-<short-git-sha>` | 배포 날짜를 읽기 쉽지만 source commit 추적은 short SHA에 의존한다. |
| release version tag | 사용자 의미가 있는 release에는 좋지만 현재 모든 운영 배포에 versioning 절차가 없다. |

초기 권장안은 Backend와 Frontend 모두 full Git SHA 기반 tag를 운영 manifest에
기록하는 것이다. Backend는 이미 `${{ github.sha }}` tag를 발행하므로 후속
작업에서 manifest image를 `seocj/news-api:<full-git-sha>` 형식으로 바꿀 수
있다. Frontend는 현재 `sha-<short-sha>` tag를 발행하므로 full Git SHA tag를
추가 발행할지, 기존 `sha-<short-sha>`를 임시 고정 tag로 사용할지 별도 workflow
변경 task에서 결정한다.

`latest`는 사람이 편의상 registry에서 최신 image를 확인하는 보조 tag로 계속
발행할 수 있다. 다만 운영 manifest와 Argo CD Sync 기준은 `latest`가 아니라
고정 tag가 되어야 한다.

Git manifest의 image tag 갱신 주체는 CI가 자동 commit을 만드는 방식으로
시작하지 않는다. 초기에는 사람이 build 결과의 Git SHA tag를 확인하고 manifest
변경 PR을 올린 뒤 review와 merge를 거친다. 이 방식은 번거롭지만 처음 Argo CD를
도입하는 단계에서 운영 승인권과 변경 이력을 분명하게 유지한다. 자동 manifest
update는 Manual Sync와 rollback 검증이 끝난 뒤 별도 task에서 재검토한다.

고정 tag 기반 목표 흐름은 다음이다.

```text
코드 변경
→ PR review 및 merge
→ GitHub Actions가 고정 image tag 발행
→ Git manifest의 image tag 변경 PR 작성
→ manifest PR review 및 merge
→ Argo CD가 Git과 K3s 차이 감지
→ 사람이 diff와 영향 범위 확인
→ 사람이 Sync 승인
→ Argo CD가 K3s에 반영
→ 사람이 rollout과 서비스 상태 검증
```

### Sync 전 확인 항목

Manual Sync 전에는 Argo CD diff와 Git 변경을 함께 확인한다.

- Application 이름이 의도한 대상인지 확인한다.
- source repository, target revision, manifest path가 기대값인지 확인한다.
- destination cluster와 namespace가 기대값인지 확인한다.
- image tag가 `latest`가 아니라 의도한 고정 tag인지 확인한다.
- Deployment replicas, selector, Service port, Ingress host, Middleware reference
  변경 여부를 확인한다.
- Backend Sync에서는 CronJob schedule, command, Secret reference 변경 여부를
  확인한다.
- resource 삭제가 포함되면 일반 Sync와 분리해 별도 사람 승인을 받는다.
- Secret 또는 ConfigMap 변경이 포함되면 실제 값 준비와 적용 주체를 별도로
  확인한다.
- DB migration, Supabase SQL, data write script가 필요한 변경인지 확인한다.

DB migration이나 Secret 값 변경이 필요한 배포는 Argo CD Sync만으로 완료하지
않는다. migration 순서와 rollback 가능성을 별도 runbook 또는 task로 확정한 뒤
진행한다.

### Sync 후 검증 항목

Manual Sync 후에는 Argo CD 상태만으로 완료 판단을 하지 않는다. 사람이 다음을
확인하고 실제 결과를 verification 또는 운영 기록에 남긴다.

- Application이 `Synced`인지 확인한다.
- Application health가 `Healthy`인지 확인한다.
- Deployment rollout 상태와 Pod restart count를 확인한다.
- 실행 중인 Pod image가 의도한 고정 tag인지 확인한다.
- Service endpoint와 Ingress routing이 기대 상태인지 확인한다.
- Backend API 또는 Frontend service의 production endpoint를 확인한다.
- Backend CronJob 변경이 있으면 다음 schedule과 최근 Job 상태를 확인한다.

이 task에서는 production verification을 수행하지 않는다. 위 항목은 후속 작업에서
사람이 실행할 확인 기준이다.

### Rollback 기준

초기 rollback은 자동 rollback이 아니라 사람이 승인하는 수동 절차로 둔다.
rollback 기준은 다음 둘 중 하나다.

- 이전 Git revision으로 manifest를 되돌린 뒤 Argo CD Manual Sync를 실행한다.
- 이전에 정상 동작이 확인된 고정 image tag로 manifest를 수정한 뒤 PR, merge,
  Manual Sync를 실행한다.

`latest` tag로 rollback하지 않는다. `latest`는 시간이 지나면 다른 image를
가리킬 수 있으므로, rollback 이력과 재현성을 보장하지 못한다.

rollback 전에는 DB migration과 data compatibility를 확인한다. schema가 이미
앞으로 진행된 상태라면 image만 이전으로 돌리는 rollback이 실패할 수 있다.
Secret 변경도 동일하게 이전 값과 현재 값의 호환성을 별도로 확인한다.

### 후속 실행 계획

최초 Backend 설치와 Manual Sync는 완료되었다. 남은 운영 변경은 별도 task로
분리한다.

1. Frontend Application 등록 및 Manual Sync 검증
2. Backend·Frontend 고정 image tag 적용
3. 이전 revision controlled rollback 검증
4. Argo CD 접근 방식의 Tailscale 내부화 검토
5. Backend와 Frontend 검증 완료 후 README GitOps 배포 구조 반영

각 단계는 사람 승인과 실제 검증 기록을 별도로 요구한다. 이 문서는 Argo CD가
완전 자동 배포, 고가용성 또는 재현 가능한 고정 image 배포를 제공한다고
주장하지 않는다.
