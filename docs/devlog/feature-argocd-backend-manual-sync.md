# Argo CD 최소 설치 및 Backend Manual Sync 검증

## 작업 목적

기존 수동 K3s 운영을 즉시 완전 자동화하지 않고, Backend `news-api`부터 Argo CD가
Git desired state와 live state의 차이를 보여주고 사람이 승인한 뒤 반영하는
흐름을 실제 환경에서 검증하는 것이 목적이었다.

핵심 흐름은 다음과 같다.

```text
Git의 Backend manifest
→ Argo CD diff
→ 사람이 resource와 삭제 영향 검토
→ 사람이 Manual Sync 승인
→ K3s 반영
→ 사람이 rollout, workload와 API 상태 확인
```

## 기존 문제

- CI가 Backend image를 Docker Hub에 발행한 뒤 K3s 반영과 상태 확인은 사람이
  직접 수행하고 있었다.
- 운영 manifest는 `latest` image tag를 사용해 Git revision만으로 실제 실행
  image를 완전히 재현하기 어려웠다.
- `k8s/` root에는 Backend workload와 cluster-wide
  `ClusterIssuer/letsencrypt-prod`가 함께 있어 Application ownership 경계를
  먼저 정해야 했다.
- 기존 resource를 Argo CD가 처음 관리할 때 annotation 외에 selector,
  Service ClusterIP, Ingress/TLS 또는 CronJob schedule 차이가 생기면
  availability와 scheduled workload에 영향을 줄 수 있었다.
- Argo CD UI/API의 장기 접근 방식, 고가용성, rollback과 Frontend 적용까지 한
  번에 도입하면 최초 변경의 영향 범위가 지나치게 커졌다.

## 변경 내용

- Argo CD `v3.4.2` 공식 non-HA manifest를 Backend 최초 도입 기준으로 정했다.
- K3s `v1.35.5+k3s1`과 세 ARM64 node의 호환성 및 설치 자원을 확인했다.
- `k8s/argocd/news-api-application.yaml`에 선언형 Backend Application을
  추가했다.
- `ClusterIssuer/letsencrypt-prod`를 shared infrastructure 소유로 확정하고
  `cluster-issuer.yaml`을 Application source에서 제외했다.
- automated sync, automatic prune과 automatic self-heal을 사용하지 않는
  Manual Sync 정책을 유지했다.
- Architecture 문서에 설치 결정, ownership, 최초 도입 결과와 남은 제약을
  반영했다.
- Runbook에 설치 전 gate, bootstrap, 최초 diff, Manual Sync와 운영 상태 확인
  절차를 기록했다.
- 승인된 FIX-01과 FIX-02를 적용해 Task의 UNIT-04, Verification의 `passed` 및
  Pending Verification `없음` 상태를 일치시키고 재검증 기록을 남겼다.

## 구현 상세

`Application/news-api`는 public Backend repository의 `main` revision과 `k8s`
path를 source로 사용하고, in-cluster의 `default` namespace를 destination으로
사용한다.

directory source는 `recurse: false`다. 이 설정으로 `k8s/monitoring/`과
`k8s/argocd/` 하위 파일이 Backend workload로 함께 생성되는 것을 막았다.
root에 있는 `cluster-issuer.yaml`은 `exclude`로 별도 제외했다. 최종 generated
resource는 다음 7개로 제한했다.

- `Deployment/news-api`
- `Service/news-api`
- `Ingress/news-api-ingress`
- `CronJob/news-rss-collector`
- `CronJob/news-daily-topic-pipeline`
- `CronJob/news-three-day-topic-pipeline`
- `CronJob/news-weekly-topic-pipeline`

`spec.syncPolicy.automated`를 선언하지 않았고 resources finalizer도 추가하지
않았다. 따라서 변경 반영은 사람의 명시적 Sync가 필요하며, Application 삭제가
Backend workload의 cascade 삭제로 바로 이어지는 구성도 피했다.

접근은 `argocd-server`의 Service type을 바꾸거나 Ingress를 추가하지 않고
local `kubectl port-forward`를 사용했다. 초기 admin credential은 사람이
확인하고 password를 변경한 뒤 초기 credential Secret을 삭제했으며, 실제
credential 값은 문서에 남기지 않았다.

최초 diff에서는 7개 resource에 Argo CD tracking annotation이 추가되는 변경만
확인했다. Deployment spec, Service, Ingress/TLS, CronJob, Secret,
`ClusterIssuer`와 삭제 대상에는 변경이 없었다. 이후 사람 통제 Manual Sync는
`--prune`, `--force`, `--replace` 없이 수행됐다.

## 대안 검토

### 공식 install manifest와 Helm chart

- 공식 install manifest: release version과 직접 대응하고 최초 설치 입력이
  단순하다.
- Helm chart: values 기반 조정과 업그레이드에는 유리하지만 최초 검증에서는
  chart release와 values 관리까지 결정해야 한다.

### non-HA와 HA

- non-HA: 작은 cluster에서 최초 흐름을 검증하기 쉽고 구성 요소가 단순하다.
- HA: 운영 가용성에는 유리하지만 replica, Redis와 자원 운영 부담이 커진다.

### `ClusterIssuer` ownership

- Backend Application에 포함: source path는 단순하지만 application workload가
  shared TLS infrastructure를 소유하게 된다.
- directory exclude: 기존 파일 구조를 바꾸지 않고 ownership을 즉시 분리할 수
  있다.
- 별도 infrastructure Application: 장기적으로 명확하지만 이번 단계의 manifest
  재구성과 bootstrap 범위가 커진다.

### 동기화 정책

- Automated Sync: Git 변경 반영은 빠르지만 최초 ownership 전환에서 사람의
  diff 승인 gate가 사라진다.
- Manual Sync: 반영 속도는 느리지만 삭제와 recreate 위험을 확인한 뒤 진행할 수
  있다.

### 접근 방식

- Public Ingress: 접근은 편하지만 인증, TLS와 외부 노출 정책이 추가로 필요하다.
- Tailscale 내부 접근: 장기 운영 후보지만 별도 네트워크·접근 정책 설계가
  필요하다.
- Port-forward: 반복 운영은 불편하지만 public endpoint 없이 즉시 사용할 수
  있다.

## 선택한 접근과 근거

- 확인 시점의 공식 stable release인 Argo CD `v3.4.2` URL을 고정한 공식
  non-HA manifest를 선택했다. `stable` URL의 내용 변경 위험을 피하고 최초
  설치와 release의 대응 관계를 명확히 하기 위해서다.
- Backend 하나만 첫 Application으로 등록했다. Frontend와 shared
  infrastructure까지 동시에 전환하지 않아 최초 Sync의 영향 범위를 줄였다.
- `ClusterIssuer`는 directory exclude로 분리했다. 기존 manifest 이동 없이도
  workload와 TLS infrastructure의 ownership 경계를 만들 수 있기 때문이다.
- Manual Sync와 prune/self-heal 비활성화를 유지했다. 기존 live resource를
  처음 인수하는 단계에서는 자동화보다 diff와 삭제 영향의 사람 검토가
  우선이라고 판단했다.
- port-forward를 선택했다. Argo CD UI/API를 public internet에 노출하지 않고
  kubeconfig를 가진 운영자만 필요할 때 접근할 수 있기 때문이다.

## 트레이드오프

- non-HA 구성은 단순하지만 Argo CD 자체의 고가용성을 보장하지 않는다.
- `latest` image tag를 유지했으므로 Git desired state와 live manifest가
  같아도 실제 image artifact를 Git revision만으로 재현할 수 없다.
- directory exclude는 현재 파일 구조에서 효과적이지만, root manifest가
  늘어나면 제외 목록과 ownership이 다시 복잡해질 수 있다.
- Manual Sync는 잘못된 자동 반영을 줄이는 대신 운영자의 검토와 승인 시간을
  요구한다.
- port-forward는 외부 노출을 피하지만 반복 접근과 다수 운영자 협업에는
  불편하다.
- resources finalizer를 두지 않아 Application 삭제 시 workload cascade 위험을
  낮췄지만, Application lifecycle과 workload 정리 책임은 사람이 별도로
  관리해야 한다.

## 테스트

- Repository와 manifest 정적 검증
  - branch, working tree와 최근 commit 확인
  - Backend resource와 `ClusterIssuer` 위치 확인
  - Application kind, repository, revision, path, destination, recursion과
    exclude 설정 확인
  - automated sync, prune, self-heal과 resources finalizer 부재 확인
- 호환성과 설치 전제 확인
  - K3s server `v1.35.5+k3s1`
  - 세 node 모두 `arm64`
  - node별 allocatable 자원과 현재 requests 확인
  - `ClusterIssuer/letsencrypt-prod`의 `Ready=True` 확인
- Verification에 기록된 사람 통제 환경의 검증
  - Argo CD 핵심 Pod 7개 Ready
  - Deployment 6개와 StatefulSet 1개 Ready
  - 모든 Argo CD Service `ClusterIP`, Ingress 없음
  - port-forward HTTPS와 admin 로그인 확인
  - password 변경과 초기 credential Secret 삭제 확인
  - generated Backend resource 7개와 `ClusterIssuer` 제외 확인
  - tracking annotation만 포함한 최초 diff 확인
  - Manual Sync operation 성공 및 `Synced`/`Healthy` 확인
  - Backend rollout, `2/2 Ready`, Pod restart count 0 확인
  - Service, Ingress와 네 CronJob 유지 확인
  - production `/health` 정상 응답 확인
  - 최종 `argocd app diff` 출력 없음, exit code 0 확인
- 문서와 변경 범위 검증
  - `git diff --check`: exit code 0
  - `app`, `scripts`, `db`, `.github`, Docker와 dependency 금지 영역 diff:
    출력 없음
  - UNIT-01~04, Verification `passed`, Pending Verification `없음`의 상태 일치
    확인

Verification 문서에는 `/version`, 주요 read-only API와 Prometheus/Grafana의
개별 command 결과가 기록되어 있지 않다. 이 devlog에서는 해당 항목을 별도로
통과했다고 주장하지 않는다.

## 운영 반영

Verification 기록에 따르면 사람 통제 작업으로 다음이 수행됐다.

- `argocd` namespace에 Argo CD `v3.4.2` 공식 non-HA manifest 설치
- port-forward 접속, admin 인증과 초기 credential 정리
- `Application/news-api` 생성
- generated resource 및 최초 diff 검토
- Manual Sync 승인과 실행
- Backend rollout, Pod, Service, Ingress, CronJob과 production `/health` 확인

확인 시점의 Application은 `Manual`, `Synced to main (2ef4adb)`,
`Healthy`였고 관리 resource 7개는 모두 `ORPHANED: No`였다. Backend
Deployment는 `2/2 Ready`, Backend Pod 2개는 `Running`/restart count 0이었다.
Argo CD 핵심 Pod 7개도 `1/1 Running`/restart count 0이었다.

이 devlog 작성 과정에서는 `kubectl apply`, rollout, Sync, production curl,
push 또는 merge를 새로 실행하지 않았다. 위 결과는 Verification에 보존된 사람
실행 기록의 확인 시점 결과이며, 현재 시점 상태나 이 PR의 merge·배포 완료를
의미하지 않는다.

## README 업데이트 판단

README는 이번 단계에서 변경하지 않았다.

Backend 하나의 Manual Sync 흐름은 검증됐지만 Frontend Application, immutable
image tag와 controlled rollback이 남아 있다. 지금 README를 Argo CD 기반 운영
구조로 갱신하면 `latest` 기반 수동 운영과 향후 목표 상태를 혼동할 수 있다.
Backend와 Frontend 적용, 고정 tag와 rollback 검증이 끝난 뒤 최종 운영 구조를
README에 반영하는 것이 적절하다.

## 확인 결과

- Verification Status: `passed`
- Pending Verification: `없음`
- `news-api`: `Manual`, `Synced`, `Healthy`
- 관리 resource: Backend 7개, 모두 `ORPHANED: No`
- shared infrastructure: `ClusterIssuer/letsencrypt-prod` 제외
- Backend: Deployment `2/2 Ready`, Pod 2개 Running/restart 0
- CronJob: 네 개 모두 `SUSPEND=False`, `ACTIVE=0`, 최근 Pod `Completed`
- Argo CD: 핵심 Pod 7개 Running/restart 0, Deployment 6개와 StatefulSet 1개
  Ready
- 접근 경계: Service `ClusterIP`, Argo CD Ingress 없음
- production `/health`: 정상 응답
- 최종 desired/live diff: 없음, exit code 0
- Approved Fixes: FIX-01과 FIX-02 적용 및 재검증 완료

## 이번 단계의 의미

단순히 Argo CD를 설치한 것이 아니라, 이미 실행 중인 Backend resource의
ownership을 안전하게 인수하는 절차를 검증했다. Git source와 live resource
목록을 제한하고, 최초 diff에서 삭제·recreate 위험이 없음을 확인한 뒤 사람이
Manual Sync를 승인했다.

이를 통해 CI의 image 발행 이후 단계에 Git desired state, diff, 승인, Sync와
operation history라는 통제 지점을 추가했다. 다만 `latest` tag와 non-HA 구성이
남아 있으므로 이번 결과는 완전한 GitOps 자동화나 재현 가능한 배포의 완성이
아니라 승인형 CD의 첫 운영 검증이다.

## 포트폴리오용 요약

Oracle Cloud ARM64 K3s 환경에 Argo CD `v3.4.2` non-HA 구성을 도입하고,
FastAPI Backend의 기존 Deployment, Service, Ingress와 네 CronJob을 중단 없이
Manual Sync 관리 대상으로 전환했다. cluster-wide `ClusterIssuer`는 shared
infrastructure로 분리하고, directory recursion·exclude와 수동 승인 gate로
Application ownership을 7개 resource에 제한했다. 최초 diff, Sync, rollout,
Pod/CronJob 및 production health를 사람 통제 절차로 검증하고 Architecture,
Runbook과 Verification 근거를 함께 문서화했다.

## 다음 단계 후보

1. Backend image를 `latest`에서 immutable full Git SHA tag로 전환
2. CI image build와 manifest image tag 갱신 흐름 연결
3. Frontend `news-lab-web` Application 등록 및 Manual Sync 검증
4. 이전 정상 revision을 사용하는 controlled rollback 시험
5. Argo CD backup, upgrade와 recovery runbook 정리
6. port-forward를 대체할 Tailscale 내부 접근 방식 검토
7. 운영 안정성 확인 후 Automated Sync 도입 여부 검토
8. Backend·Frontend와 rollback 검증 완료 후 README 운영 구조 갱신
