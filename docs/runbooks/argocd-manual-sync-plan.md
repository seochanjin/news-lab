# Argo CD Manual Sync Plan

[Runbook index로 돌아가기](../RUNBOOK.md)

이 문서는 Argo CD 승인형 배포 구조를 도입하기 전 사람이 실행할 절차와 확인
경계를 정리하기 위한 계획 문서다. 현재 단계에서는 Argo CD 설치, namespace
생성, Helm 실행, `kubectl apply`, `kubectl rollout`을 수행하지 않고, 초기
Application 등록 기준과 Manual Sync 운영 원칙만 정리한다.

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
이 resource는 cluster-wide TLS 인프라라서 `news-api` Application에 포함할지
별도 인프라 소유로 남길지 Application 등록 전에 사람이 결정해야 한다. 이
결정이 끝나기 전에는 backend Application을 운영 Sync 대상으로 등록하지 않는다.

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
