# Verification: Argo CD 최소 설치 및 Backend Manual Sync 검증

## Verification Status

passed

## Verification Scope

UNIT-01부터 UNIT-04까지 완료했다.

Argo CD `v3.4.2` 공식 non-HA manifest를 `argocd` namespace에 설치했고,

ARM64 node scheduling, 핵심 component Ready, ClusterIP와 Ingress 미생성을 통한

public 비노출, port-forward HTTPS 접근, admin 로그인, 초기 비밀번호 변경 및

초기 credential Secret 삭제를 검증했다.

Backend `news-api` Application을 선언형 manifest로 등록하고, generated resource

7개와 ownership 범위를 확인했다. 최초 diff가 Argo CD tracking annotation 추가만

포함하는 것을 검토한 뒤 Manual Sync를 수행했다.

최종적으로 Application은 `Manual`, `Synced`, `Healthy` 상태이며,

Backend Deployment, Service, Ingress, 네 CronJob, production health endpoint와

Argo CD component가 정상임을 재확인했다. Git desired state와 live cluster state

사이의 최종 diff는 없었다.

## Commands Run

### UNIT-01 — 설치 전제와 ownership 확인

Command:

`git branch --show-current && git status --short`

Result:

현재 branch가 `feature/argocd-backend-manual-sync`임을 확인했다.

기존 workflow 문서 변경과 untracked 상태는 보존했다.

Status: passed

Command:

`git log --oneline -5`

Result:

최신 commit이 68차 Argo CD 설계 문서 commit

`2ef4adb docs: Argo CD 수동 동기화와 GitOps 배포 구조 설계 (#48)`임을 확인했다.

Status: passed

Command:

`rg -n "kind:|metadata:|name:|image:|schedule:|namespace:|ClusterIssuer" k8s`

Result:

`k8s/`에 Backend Deployment, Service, Ingress, 네 CronJob과

`ClusterIssuer/letsencrypt-prod`가 함께 있음을 확인했다.

Status: passed

Notes:

`news-api` Application에서 `cluster-issuer.yaml`을 제외해야 하는 repository 근거로 사용했다.

Command:

Argo CD 공식 release, installation/getting-started 문서와 K3s requirements 공식 문서를 2026-07-09에 조회.

Result:

공식 stable release `v3.4.2`, pinned version manifest, non-HA 설치,

Argo CD 3.4의 Kubernetes 테스트 범위 `v1.32`~`v1.35`, K3s ARM64 지원,

port-forward와 초기 admin credential 절차를 확인했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl config current-context`

Result:

현재 context가 `default`임을 확인했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl cluster-info`

Result:

Kubernetes control plane, CoreDNS와 metrics-server가

`https://127.0.0.1:6443`을 통해 정상 응답했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl version`

Result:

Client는 `v1.34.1`, Server는 `v1.35.5+k3s1`이다.

Status: passed

Notes:

K3s server version이 Argo CD 3.4 공식 테스트 범위에 포함된다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o custom-columns=NAME:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,ARCH:.status.nodeInfo.architecture,CPU:.status.allocatable.cpu,MEMORY:.status.allocatable.memory`

Result:

`arm-master-node`, `arm-worker-node`, `pi-worker-node` 모두

`v1.35.5+k3s1`, `arm64`이며 allocatable 자원은 각각

2 CPU/약 12Gi, 2 CPU/약 12Gi, 4 CPU/약 8Gi다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe nodes | grep -A 15 "Allocated resources"`

Result:

현재 requests 기준으로 Argo CD 최소 설치를 검토할 자원 여유가 있음을 확인했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get clusterissuer letsencrypt-prod -o jsonpath='{.metadata.name}{"\n"}{.status.conditions[*].type}{"\n"}{.status.conditions[*].status}{"\n"}'`

Result:

`ClusterIssuer/letsencrypt-prod`가 존재하며 `Ready=True`다.

Status: passed

Notes:

해당 resource는 shared infrastructure 소유로 유지하고 `news-api` Application에서 제외한다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,service,ingress,cronjob -n default`

Result:

Backend Deployment, Service, Ingress와 네 CronJob이 존재하고

`news-api` Deployment는 `2/2 Ready`였다.

Status: passed

### UNIT-02 — Argo CD 설치와 접근 검증

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get namespace argocd`

Result:

설치 전 `argocd` namespace가 존재하지 않음을 확인했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create namespace argocd`

Result:

`argocd` namespace가 생성되었다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --server-side --force-conflicts -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.4.2/manifests/install.yaml`

Result:

Argo CD `v3.4.2` 공식 non-HA manifest가 적용되었다.

Status: passed

Notes:

`stable` URL이 아닌 고정 version URL을 사용했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl wait --for=condition=Ready pod --all -n argocd --timeout=10m`

Result:

Argo CD 핵심 Pod 7개가 모두 Ready condition을 충족했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,statefulset,service -n argocd`

Result:

Deployment 6개와 StatefulSet 1개가 모두 Ready 상태였다.

모든 Service는 `ClusterIP`였고 External IP는 없었다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress -n argocd`

Result:

`No resources found in argocd namespace.`가 출력되었다.

Status: passed

Notes:

Argo CD public Ingress를 생성하지 않았다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward service/argocd-server -n argocd 8080:443`

Result:

로컬 `127.0.0.1:8080`에서 Argo CD HTTPS port-forward가 시작되었다.

Status: passed

Command:

`curl -kI https://localhost:8080`

Result:

`HTTP/1.1 200 OK`로 응답했다.

Status: passed

Command:

`argocd version --client`

Result:

Argo CD CLI `v3.4.4`, platform `darwin/arm64`가 설치되었음을 확인했다.

Status: passed

Notes:

로컬 CLI는 `v3.4.4`, cluster Argo CD Server는 고정 version `v3.4.2`다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml argocd admin initial-password -n argocd`

Result:

초기 admin credential을 사람이 확인했다.

Status: passed

Notes:

실제 password 값은 Verification, Git 또는 운영 문서에 기록하지 않았다.

Command:

`argocd login localhost:8080 --username admin --insecure`

Result:

초기 admin 로그인에 성공했다.

Status: passed

Command:

`argocd account update-password --server localhost:8080 --insecure`

Result:

초기 admin password를 변경했다.

Status: passed

Command:

`argocd logout localhost:8080` 후 `argocd login localhost:8080 --username admin --insecure`

Result:

변경한 password로 재로그인에 성공했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete secret argocd-initial-admin-secret -n argocd`

Result:

`argocd-initial-admin-secret`이 삭제되었다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret argocd-initial-admin-secret -n argocd`

Result:

`NotFound`가 반환되었다.

Status: passed

### UNIT-03 — Application 등록·최초 diff·Manual Sync 검증

Command:

`find k8s -maxdepth 3 -type f -print | sort` 및 `git ls-tree -r --name-only main k8s`

Result:

`k8s/` root의 Backend manifest와 `cluster-issuer.yaml`, 하위 monitoring 파일을 확인했다.

Status: passed

Notes:

Directory recursion을 끄고 `cluster-issuer.yaml`을 제외해야 Backend 7개 resource로 ownership을 제한할 수 있다.

Command:

```bash
ruby -ryaml -e '
manifest = YAML.load_file("k8s/argocd/news-api-application.yaml")
raise "kind mismatch" unless manifest["kind"] == "Application"
raise "repoURL mismatch" unless manifest.dig("spec", "source", "repoURL") == "https://github.com/seochanjin/news-lab.git"
raise "targetRevision mismatch" unless manifest.dig("spec", "source", "targetRevision") == "main"
raise "path mismatch" unless manifest.dig("spec", "source", "path") == "k8s"
raise "recurse mismatch" unless manifest.dig("spec", "source", "directory", "recurse") == false
raise "exclude mismatch" unless manifest.dig("spec", "source", "directory", "exclude") == "cluster-issuer.yaml"
raise "destination server mismatch" unless manifest.dig("spec", "destination", "server") == "https://kubernetes.default.svc"
raise "destination namespace mismatch" unless manifest.dig("spec", "destination", "namespace") == "default"
raise "syncPolicy must be absent" if manifest.dig("spec", "syncPolicy")
puts "Application manifest assertions passed"
'
```

Result:

Application kind, repository, `main`, `k8s`, `recurse: false`,

`cluster-issuer.yaml` exclude, in-cluster destination, `default` namespace와

`spec.syncPolicy` 부재를 확인했다.

Status: passed

Command:

`rg -n "automated:|prune:|selfHeal:|resources-finalizer" k8s/argocd/news-api-application.yaml`

Result:

출력 없음.

Status: passed

Notes:

Automated sync, automatic prune, automatic self-heal과 cascade deletion finalizer를 사용하지 않았다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get applications.argoproj.io -n argocd`

Result:

등록 전 기존 Application이 없음을 확인했다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/argocd/news-api-application.yaml`

Result:

`application.argoproj.io/news-api created`가 출력되었다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get application news-api -n argocd`

Result:

초기 상태는 `OutOfSync`, `Healthy`였다.

Status: passed

Command:

`argocd app get news-api --server localhost:8080 --insecure --refresh`

Result:

Source는 public Backend repository의 `main`/`k8s`, destination은

in-cluster `default`, Sync Policy는 `Manual`이었다.

관리 대상은 Deployment 1개, Service 1개, Ingress 1개, CronJob 4개였다.

Status: passed

Command:

`argocd app manifests news-api --source git --server localhost:8080 --insecure > /tmp/news-api-argocd-manifests.yaml`

Result:

Argo CD generated manifest를 로컬 임시 파일로 저장했다.

Status: passed

Command:

`grep -E '^(kind:|  name:)' /tmp/news-api-argocd-manifests.yaml`

Result:

다음 7개 resource를 확인했다.

- `Service/news-api`
- `Deployment/news-api`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-rss-collector`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`
- `Ingress/news-api-ingress`

Status: passed

Command:

`grep -n '^kind: ClusterIssuer$' /tmp/news-api-argocd-manifests.yaml`

Result:

출력 없음.

Status: passed

Notes:

`ClusterIssuer/letsencrypt-prod` resource는 관리 대상에서 제외되었다.

Ingress의 issuer annotation은 기존 shared ClusterIssuer 참조이므로 정상이다.

Command:

`argocd app diff news-api --server localhost:8080 --insecure`

Result:

7개 resource에 `argocd.argoproj.io/tracking-id` annotation을 추가하는 diff만 확인되었다.

Status: passed

Notes:

Deployment spec, Service selector/port, Ingress host/TLS,

CronJob schedule/image/command, Secret, ClusterIssuer와 삭제 대상 resource 변경은 없었다.

Command:

`argocd app sync news-api --server localhost:8080 --insecure`

Result:

Sync revision `2ef4adb60fb3384b96857a2e11f13d28e4f7ac28` 기준으로

Operation Phase가 `Succeeded`였다.

Status: passed

Notes:

`--prune`, `--force`, `--replace` 없이 Manual Sync를 수행했다.

Command:

`argocd app wait news-api --sync --health --timeout 600 --server localhost:8080 --insecure`

Result:

Application이 `Synced`, `Healthy` 상태에 도달했다.

Status: passed

Command:

`argocd app resources news-api --server localhost:8080 --insecure`

Result:

Backend resource 7개가 모두 `ORPHANED: No`였다.

Status: passed

Command:

`curl -fsS https://api.newslab.ai.kr/health`

Result:

`{"status":"ok","service":"news-api",...}` 응답을 확인했다.

Status: passed

### UNIT-04 — 최종 운영 상태·문서·후속 task 정리

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default --timeout=10m`

Result:

`deployment "news-api" successfully rolled out`가 출력되었다.

Status: passed

Notes:

Manual Sync 이후 Backend Deployment rollout이 정상임을 확인했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,service,ingress,cronjob -n default`

Result:

`news-api` Deployment는 `2/2 Ready`, Service와 Ingress는 정상 존재했다.

네 CronJob은 모두 `SUSPEND=False`, `ACTIVE=0` 상태였다.

Status: passed

Notes:

Backend 운영 resource와 schedule 상태가 정상임을 확인했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -o wide`

Result:

Backend Pod 2개와 Frontend Pod 2개는 모두 `Running`, restart count 0이었다.

최근 Daily, RSS, Three-day, Weekly pipeline Pod는 모두 `Completed` 상태였다.

Status: passed

Notes:

운영 workload와 최근 scheduled Job 실행 결과가 정상임을 확인했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get events -n default --sort-by=.lastTimestamp | tail -40`

Result:

`No resources found in default namespace.`가 출력되었다.

Status: passed

Notes:

최근 default namespace에 보존된 warning 또는 error event가 없음을 확인했다.

Command:

`curl -fsS https://api.newslab.ai.kr/health`

Result:

`{"status":"ok","service":"news-api",...}` 응답을 확인했다.

Status: passed

Notes:

최종 production API health endpoint가 정상 응답했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n argocd -o wide`

Result:

Argo CD 핵심 Pod 7개가 모두 `1/1 Running` 상태이며 restart count는 0이었다.

Status: passed

Notes:

설치 후 약 2시간 동안 Argo CD component가 안정적으로 유지됨을 확인했다.

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment,statefulset,service -n argocd`

Result:

Argo CD Deployment 6개와 StatefulSet 1개가 모두 Ready 상태였다.

모든 Service는 `ClusterIP`이며 External IP는 없었다.

Status: passed

Command:

`KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress -n argocd`

Result:

`No resources found in argocd namespace.`가 출력되었다.

Status: passed

Notes:

Argo CD public Ingress가 생성되지 않았음을 재확인했다.

Command:

`argocd app get news-api --server localhost:8080 --insecure --refresh`

Result:

Sync Policy는 `Manual`, Sync Status는 `Synced to main (2ef4adb)`,

Health Status는 `Healthy`였다.

Status: passed

Notes:

사람 승인형 CD 정책과 Git/live 상태 일치가 유지됨을 확인했다.

Command:

`argocd app resources news-api --server localhost:8080 --insecure`

Result:

Backend 관리 resource 7개가 모두 `ORPHANED: No`였다.

Status: passed

Notes:

Application ownership 범위가 유지되고 있으며 `ClusterIssuer`는 포함되지 않았다.

Command:

`argocd app diff news-api --server localhost:8080 --insecure`

Result:

출력이 없었고 종료 코드는 `0`이었다.

Status: passed

Notes:

Git desired state와 live cluster state 사이에 미해결 diff가 없음을 확인했다.

Command:

`git diff --check`

Result:

출력 없이 exit code 0으로 통과했다.

Status: passed

Command:

`git diff --name-only -- app scripts db .github Dockerfile requirements.txt docker-compose.yml`

Result:

출력 없음.

Status: passed

Notes:

Application code, script, DB, GitHub Actions, Docker와 dependency 영역을 변경하지 않았다.

### Approved Fixes 적용 재검증

Command:

`rg -n "UNIT-01|UNIT-02|UNIT-03|UNIT-04|Verification Status|Pending Verification" docs/tasks/feature-argocd-backend-manual-sync.md docs/verification/feature-argocd-backend-manual-sync.md docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`

Result:

Task의 UNIT-01부터 UNIT-04까지 모두 `[x]`이고, Verification Status는 `passed`,
Pending Verification은 `없음`임을 확인했다. Task와 Approved Fixes에 사람
검증으로 UNIT-04의 pending 조건을 해소한 설명이 있음을 확인했다.

Status: passed

Command:

`git diff --check`

Result:

출력 없이 exit code 0으로 통과했다.

Status: passed

Notes:

세 fix 대상 문서는 현재 untracked 상태이므로 이 명령은 기존 tracked diff의
whitespace 오류를 검사했다.

Command:

`git diff --name-only -- app scripts db .github Dockerfile requirements.txt docker-compose.yml`

Result:

출력 없음.

Status: passed

Notes:

승인 fix 적용으로 금지 영역을 변경하지 않았다.

Command:

`git status --short`, `git diff --stat`,
`git diff -- docs/tasks/feature-argocd-backend-manual-sync.md docs/verification/feature-argocd-backend-manual-sync.md docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`

Result:

세 fix 대상 문서가 untracked 상태임을 확인했다. 따라서 tracked 파일만 표시하는
`git diff --stat`과 대상 문서 `git diff`에는 이번 문서 변경이 출력되지 않았다.
기존 architecture, runbook, task main 변경과 그 밖의 untracked 작업 파일은
보존했다.

Status: passed

### Approved Fixes FIX-03~07 재검증

Command:

```bash
rg -n \
  "/version|/health|\.\./docs/|feature-argocd-manual-sync-baseline|<k8s/argocd/news-api-application.yaml field assertions>|Verdict|Problems Found|Required Fixes Before PR" \
  docs/reviews/feature-argocd-backend-manual-sync-antigravity.md \
  docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md
```

Result:

Antigravity review의 production API 완료 주장은 `/health`로 한정되었다.
Antigravity review에서 잘못된 `../docs/` 링크가 검색되지 않았고, Task에서 이전
baseline Verification 참조가 검색되지 않았으며, Verification에서 Ruby
placeholder가 검색되지 않았다. CodeRabbit artifact에는 Problems Found,
Required Fixes Before PR와 현재 Verdict가 기록되어 있다.

Task의 acceptance criteria와 제안 command에는 `/version`이 계속 존재하고,
CodeRabbit artifact에는 `/version` 실행 증거가 없다는 지적이 남아 있다. 이는
검증 완료 주장이 아니라 요구사항과 finding이다.

Status: passed

Command:

```bash
ruby -ryaml -e '
manifest = YAML.load_file("k8s/argocd/news-api-application.yaml")
raise "kind mismatch" unless manifest["kind"] == "Application"
raise "repoURL mismatch" unless manifest.dig("spec", "source", "repoURL") == "https://github.com/seochanjin/news-lab.git"
raise "targetRevision mismatch" unless manifest.dig("spec", "source", "targetRevision") == "main"
raise "path mismatch" unless manifest.dig("spec", "source", "path") == "k8s"
raise "recurse mismatch" unless manifest.dig("spec", "source", "directory", "recurse") == false
raise "exclude mismatch" unless manifest.dig("spec", "source", "directory", "exclude") == "cluster-issuer.yaml"
raise "destination server mismatch" unless manifest.dig("spec", "destination", "server") == "https://kubernetes.default.svc"
raise "destination namespace mismatch" unless manifest.dig("spec", "destination", "namespace") == "default"
raise "syncPolicy must be absent" if manifest.dig("spec", "syncPolicy")
puts "Application manifest assertions passed"
'
```

Result:

`Application manifest assertions passed`가 출력되었고 exit code 0으로 통과했다.

Status: passed

Command:

`git diff --check`

Result:

출력 없이 exit code 0으로 통과했다.

Status: passed

Command:

`git diff --name-only -- app scripts db .github Dockerfile requirements.txt docker-compose.yml`

Result:

출력 없음.

Status: passed

Notes:

FIX-03~07 적용으로 금지 영역을 변경하지 않았다.

Command:

`git status --short`, `git diff --stat`,
`git diff -- docs/reviews/feature-argocd-backend-manual-sync-antigravity.md docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md docs/tasks/feature-argocd-backend-manual-sync.md docs/verification/feature-argocd-backend-manual-sync.md docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`

Result:

승인된 FIX-03~07 범위인 review artifact 두 개, Task, Verification과 Approved
Fixes 문서만 변경된 것을 확인했다.

Status: passed

## Results

### UNIT-01

- Argo CD `v3.4.2`와 K3s `v1.35.5+k3s1` 호환성을 확인했다.
- 모든 cluster node가 ARM64임을 확인했다.
- 설치 자원 여유를 확인했다.
- `ClusterIssuer/letsencrypt-prod`를 shared infrastructure로 유지하기로 결정했다.

### UNIT-02

- Argo CD `v3.4.2`를 `argocd` namespace에 설치했다.
- 핵심 Pod 7개, Deployment 6개, StatefulSet 1개가 Ready 상태다.
- Argo CD, Redis와 Dex image의 ARM64 실행을 확인했다.
- `argocd-server`는 ClusterIP이고 public Ingress는 없다.
- port-forward HTTPS 접근과 admin 로그인을 확인했다.
- 초기 password를 변경하고 초기 credential Secret을 삭제했다.

### UNIT-03

- `news-api` Application을 선언형 manifest로 등록했다.
- Source는 `main`/`k8s`, destination은 in-cluster/`default`, Sync Policy는 `Manual`이다.
- generated resource는 Backend 7개이고 `ClusterIssuer`는 제외되었다.
- 최초 diff는 tracking annotation 추가만 포함했다.
- Manual Sync가 성공했고 최종 상태는 `Synced`, `Healthy`다.
- 관리 resource 7개는 모두 `ORPHANED: No`다.

### UNIT-04

- Backend Deployment rollout이 정상이다.
- Deployment `2/2`, Service, Ingress와 네 CronJob이 정상이다.
- Backend Pod는 Running/restart 0, 최근 CronJob Pod는 Completed 상태다.
- production `/health`가 정상 응답한다.
- Argo CD 핵심 component가 Running/restart 0 상태다.
- Argo CD public Ingress가 없고 Service는 ClusterIP다.
- `news-api` Application은 `Manual`, `Synced`, `Healthy`다.
- 최종 `argocd app diff`는 출력이 없고 exit code는 `0`이다.

## Manual or Production Verification

사람이 `KUBECONFIG=~/.kube/oci-k3s.yaml`을 명시해 Argo CD 설치, component 상태,

ARM64 scheduling, public 비노출, port-forward 접근, admin 인증과 초기 credential

정리를 수행했다.

사람이 Backend Application을 생성하고 generated resource와 최초 diff를 검토한 뒤

Manual Sync를 승인했다. 이후 Argo CD Application 상태, K3s Backend workload,

CronJob 이력과 production health endpoint를 재확인했다.

초기 admin password와 변경한 password 값은 Verification, Git과 운영 문서에

기록하지 않았다.

## Pending Verification

없음.

Frontend Application, automated sync, automatic prune, self-heal, public Argo CD

Ingress, SSO와 HA 구성은 이번 Task 범위에 포함하지 않는다.

## Evidence Notes

UNIT-01에서 version, Kubernetes 호환 범위, K3s server, ARM64 node, capacity와

`ClusterIssuer` ownership을 확인했다.

UNIT-02에서 Argo CD와 부속 image의 ARM64 실행, 핵심 component Ready,

ClusterIP와 public Ingress 미생성, port-forward 접근, admin credential 정리를 확인했다.

UNIT-03에서 `news-api` Application의 source, destination, Manual Sync 정책,

resource 7개와 `ClusterIssuer` 제외를 확인했다. 최초 diff 검토 후 Manual Sync가

성공했고 Application은 `Synced`, `Healthy`가 되었다.

UNIT-04에서 Backend rollout, Pod, Service, Ingress, CronJob, production health,

Argo CD component와 최종 diff 없음까지 재확인했다.

## UI Evidence

Argo CD UI에서 다음을 확인했다.

- `news-api` Application이 `Synced`, `Healthy`
- Deployment → ReplicaSet → Pod 연결 구조
- Service → Pod 연결 구조
- Ingress → Service 연결 구조
- CronJob → Job → Completed Pod 이력
- Backend 관리 resource가 Application graph에 정상 표시됨

과거 ReplicaSet과 완료된 Job/Pod가 UI에 표시되는 것은 Deployment 및 CronJob의

정상 실행 이력을 나타낸다.

## Follow-up Tasks

후속 작업은 별도 task로 분리한다.

- Backend image를 `latest`에서 immutable SHA tag로 전환
- CI image build와 manifest image tag 갱신 흐름 연결
- Frontend Argo CD Application 도입
- Argo CD backup, upgrade와 recovery runbook 정리
- 운영 안정성 검증 후 Automated Sync 도입 여부 검토
