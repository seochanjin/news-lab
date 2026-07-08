# Argo CD 승인형 배포 구조 설계

## 작업 목적

NewsLab의 현재 CI와 수동 배포 흐름을 기준으로, Argo CD를 이용한 승인형 GitOps
배포 구조를 설계한다.

이번 단계의 목표는 Argo CD 설치나 운영 자동화가 아니다. 현재처럼 운영 변경
승인권을 사람에게 두면서, 다음 단계에서 사람이 안전하게 Argo CD 설치,
Application 등록, Manual Sync, rollback 검증을 진행할 수 있도록 기준을 문서로
확정하는 것이다.

정리해야 할 핵심 질문은 다음이었다.

- CI와 CD가 각각 무엇을 담당하는가?
- NewsLab의 GitHub Actions는 현재 어디까지 자동화하고 있는가?
- 왜 `latest` image tag가 GitOps 이력과 rollback에 약한가?
- Backend와 Frontend를 어떤 Argo CD Application 경계로 나눌 것인가?
- 자동 Sync가 아니라 Manual Sync를 선택하는 이유는 무엇인가?
- Secret, DB migration, production verification은 Argo CD Sync와 어떻게
  분리할 것인가?

## 기존 문제

- NewsLab은 GitHub Actions로 backend/frontend Docker image를 Docker Hub에
  발행하지만, K3s 반영은 사람이 `kubectl apply` 또는 `kubectl rollout restart`
  계열 작업으로 수행하는 구조였다.
- Backend와 Frontend 운영 manifest가 각각 별도 repository의 `k8s/` 경로에 있어
  GitOps Application 경계를 먼저 정해야 했다.
- Backend와 Frontend 운영 manifest가 모두 `latest` image tag를 참조하고 있어,
  Git manifest만 보고 실제 running image commit을 식별하기 어려웠다.
- Argo CD를 처음 도입하는 단계에서 자동 Sync, automatic prune, self-heal 같은
  기능을 바로 켜면 기존 human approval 운영 원칙과 충돌할 수 있었다.
- Backend `k8s/`에는 workload뿐 아니라 cluster-wide TLS resource인
  `ClusterIssuer/letsencrypt-prod`도 함께 있어, Argo CD ownership 경계를 별도로
  결정해야 했다.
- Argo CD UI/API 접근, repository credential, admin credential, Secret 관리,
  DB migration 책임 경계를 문서화하지 않으면 설치 단계에서 운영 보안 판단이
  흐려질 수 있었다.

## 변경 내용

- `docs/architecture/argocd-manual-sync-design.md`를 추가했다.
  - 현재 backend/frontend CI, image tag, manifest, 수동 배포 흐름을 정리했다.
  - Argo CD Application 경계를 `news-api`, `news-lab-web` 2개로 설계했다.
  - Manual Sync 정책과 자동화 제외 항목을 명시했다.
  - 고정 image tag 전략, Sync 전후 확인 항목, rollback 기준을 정리했다.
- `docs/runbooks/argocd-manual-sync-plan.md`를 추가했다.
  - 설치 전제, Application 등록 전 확인 항목, Manual Sync checklist, rollback
    절차 기준, 후속 task 분리 계획을 작성했다.
- `docs/ARCHITECTURE.md`에 Argo CD Manual Sync 설계 문서 링크를 추가했다.
- `docs/RUNBOOK.md`에 Argo CD Manual Sync 계획 문서 링크를 추가했다.
- `docs/tasks/main.md`를 현재 branch task로 갱신했다.
- branch workflow 문서와 verification 문서를 작성했다.

## 구현 상세

현재 배포 baseline은 다음으로 정리했다.

```text
코드 변경
→ PR review 및 merge
→ GitHub Actions build
→ Docker Hub image push
→ 사람이 rollout 또는 manifest apply
→ 사람이 상태와 서비스 확인
```

Backend 기준:

- repository: `https://github.com/seochanjin/news-lab.git`
- workflow: `.github/workflows/docker-build.yml`
- trigger: `main` push, `workflow_dispatch`
- platform: `linux/arm64`
- tag: full Git SHA, `latest`
- 운영 manifest image: `seocj/news-api:latest`
- manifest path: `k8s/`
- resource: API Deployment/Service/Ingress, RSS/Daily/Three-day/Weekly CronJob

Frontend 기준:

- repository: `https://github.com/seochanjin/news-lab-web.git`
- workflow: `.github/workflows/docker-build.yml`
- trigger: PR, `main` push, `v*` tag push, `workflow_dispatch`
- platform: `linux/arm64`
- tag: `main`, `latest`, version tag, `sha-<short-sha>`
- 운영 manifest image: `seocj/news-lab-web:latest`
- manifest path: `k8s/`
- resource: Deployment/Service/Ingress/Traefik Middleware

초기 Argo CD Application 후보는 다음으로 정리했다.

| Application | Repository | Revision | Path | Namespace | Sync |
| --- | --- | --- | --- | --- | --- |
| `news-api` | `https://github.com/seochanjin/news-lab.git` | `main` | `k8s/` | `default` | Manual |
| `news-lab-web` | `https://github.com/seochanjin/news-lab-web.git` | `main` | `k8s/` | `default` | Manual |

초기 Sync 정책은 다음으로 결정했다.

- Manual Sync 사용
- `spec.syncPolicy.automated` 사용하지 않음
- automatic prune 사용하지 않음
- automatic self-heal 사용하지 않음
- 삭제가 포함된 Sync는 별도 사람 승인 필요

Argo CD 접근 방식은 public exposure를 기본값으로 두지 않고,
`kubectl port-forward`를 1순위 후보로 기록했다. Tailscale 내부 접근은 반복
운영이 필요해질 때 검토하고, Public Ingress는 별도 보안 검토 없이 사용하지
않는 방향으로 남겼다.

## 대안 검토

- 자동 Sync를 바로 켜는 방식
  - 장점: Git merge 후 cluster 반영까지 자동화 수준이 높다.
  - 단점: 현재 NewsLab의 사람 승인 운영 원칙과 충돌하고, 삭제/prune/self-heal
    영향 범위를 처음부터 안전하게 통제하기 어렵다.
- App of Apps 또는 ApplicationSet 사용
  - 장점: Application 수가 늘어날 때 중앙 관리가 쉬워진다.
  - 단점: 현재는 backend/frontend 2개 Application만 필요하므로 학습 비용과
    운영 복잡도가 과하다.
- 별도 deployment repository 생성
  - 장점: 모든 manifest와 image tag 변경을 한 곳에서 관리할 수 있다.
  - 단점: 현재 backend/frontend repository가 이미 각자의 `k8s/` manifest를
    가지고 있어 초기 도입 범위가 커진다.
- `latest` tag 유지
  - 장점: 기존 workflow와 manifest를 바로 바꾸지 않아도 된다.
  - 단점: Argo CD가 registry의 새 `latest` push를 Git diff로 감지하지 못하고,
    rollback 기준이 불명확하다.
- CI가 manifest image tag PR까지 자동 생성
  - 장점: image build 후 manifest 갱신이 자동화된다.
  - 단점: Argo CD 도입 초기에는 사람이 build 결과와 배포 영향 범위를 직접
    확인하는 단계가 더 적합하다.

## 선택한 접근과 근거

선택한 접근은 현재 repository 구조를 유지하면서 backend와 frontend를 각각
독립적인 Argo CD Application 후보로 두고, Manual Sync 기반으로 시작하는 것이다.

근거는 다음과 같다.

- 현재 규모에서는 `news-api`, `news-lab-web` 2개 Application만으로 책임 경계가
  충분히 표현된다.
- 각 repository의 `k8s/` 경로를 직접 추적하면 초기 migration 범위가 작고,
  code ownership과 deployment manifest ownership이 일치한다.
- 자동 Sync를 켜지 않아도 Argo CD는 Git/live diff, health, sync history를
  제공하므로 운영자가 변경 전후를 더 명확하게 볼 수 있다.
- `latest` 대신 고정 Git SHA tag를 manifest에 기록하는 방향이 배포 이력과
  rollback 재현성에 더 맞다.
- Secret, DB migration, production verification은 Argo CD Sync가 해결할 수 있는
  문제가 아니므로 별도 사람 승인과 실행 기록으로 남겨야 한다.

## 트레이드오프

- Manual Sync는 자동 CD보다 느리다. 대신 운영 변경 승인권과 diff 확인 절차가
  사람에게 남는다.
- 각 repository의 `k8s/`를 직접 추적하면 별도 deployment repository를 만들지
  않아도 된다. 대신 backend/frontend release coordination은 나중에 별도 문제가
  될 수 있다.
- `news-api` Application 후보가 backend `k8s/` 전체를 추적하면
  `ClusterIssuer/letsencrypt-prod` 같은 shared infrastructure resource가 섞일 수
  있다. Application 등록 전 ownership 결정을 따로 남겼다.
- full Git SHA tag는 추적성이 좋지만 사람이 읽기에는 길다. 그래도 초기 GitOps
  기준으로는 충돌 가능성이 낮고 commit 추적이 명확하다.
- README에는 이번 단계에서 Argo CD를 현재 운영 구조로 반영하지 않았다. 문서
  설계는 완료됐지만 실제 설치와 Manual Sync 검증은 아직 후속 task다.

## 테스트

실제 test와 verification 결과의 source of truth는
`docs/verification/feature-argocd-manual-sync-baseline.md`다.

실행한 주요 검증은 다음과 같다.

- Backend CI/image 조사:
  - `rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`
  - Backend workflow의 `main` push, `workflow_dispatch`, Buildx, `linux/arm64`,
    full Git SHA tag, `latest` tag와 manifest의 `seocj/news-api:latest` 참조를
    확인했다.
- Backend manifest 조사:
  - `rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s`
  - API Deployment/Service/Ingress, RSS/Daily/Three-day/Weekly CronJob,
    `replicas: 2`, `workload: app`, `seocj/news-api:latest`를 확인했다.
- Frontend repository 조사:
  - `cd ~/workspace/NewsLab/news-lab-web && rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`
  - `cd ~/workspace/NewsLab/news-lab-web && rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s`
  - Frontend Docker workflow, `latest`, `sha-*`, `main` tag policy와
    `news-lab-web` Deployment/Service/Ingress/Middleware manifest를 확인했다.
- Argo CD resource 부재 확인:
  - `find . -maxdepth 4 -type f \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) | sort`
  - 설치 manifest나 Application YAML 없이 문서 산출물만 검색됨을 확인했다.
- 설계 문서 핵심 결정 확인:
  - `rg -n "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md`
- 금지 영역 변경 여부:
  - `git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`
  - 출력 없음.
- Markdown/whitespace 확인:
  - `git diff --check`
  - `grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`
  - whitespace 오류 없음.

Application test, deployment test, Argo CD Sync test는 실행하지 않았다. 이번
작업은 조사와 설계 문서 작성이며 application code, DB, API, K3s manifest,
GitHub Actions workflow를 변경하지 않았다.

## 운영 반영

운영 반영은 수행하지 않았다.

실행하지 않은 작업:

- Argo CD 설치
- namespace 생성
- Helm install/upgrade
- `kubectl apply`
- `kubectl rollout`
- Argo CD Application 등록
- Argo CD Manual Sync
- rollback 실행
- Docker push
- Supabase SQL
- production endpoint verification
- `git push`
- `git merge`

이번 verification에서 pending은 없다. 다만 이는 이 task에서 허용된 read-only
조사와 문서 검증 기준의 pending이 없다는 뜻이다. Argo CD 설치, Application
등록, Manual Sync, rollback, production endpoint verification은 후속 task의
사람 실행 대상이다.

## README 업데이트 판단

README는 이번 단계에서 변경하지 않았다.

판단 근거:

- Task의 Do not change 범위에 `README의 현재 기능 설명`이 포함되어 있다.
- 이번 작업은 Argo CD 운영 구조를 실제로 도입한 것이 아니라 설계와 실행 계획을
  확정한 단계다.
- README에는 Argo CD 설치와 실제 Manual Sync가 검증된 뒤에만 현재 배포 구조로
  반영한다는 task 기준이 있다.

따라서 README 업데이트는 후속 단계인 Argo CD 설치, Application 등록, Manual
Sync 검증이 완료된 뒤 후보로 남긴다.

## 확인 결과

- Verification status는 `passed`다.
- Approved fixes 문서에는 승인된 fix가 없으므로 별도 approved fix 적용은 없다.
- Backend 현재 운영 image reference는 `seocj/news-api:latest`다.
- Frontend 현재 운영 image reference는 `seocj/news-lab-web:latest`다.
- Backend는 full Git SHA tag를 발행하지만 운영 manifest는 `latest`를 사용한다.
- Frontend는 `main`, `latest`, version tag, `sha-*` tag를 발행할 수 있지만 운영
  manifest는 `latest`를 사용한다.
- 초기 Argo CD Application 후보는 `news-api`, `news-lab-web` 2개다.
- 초기 target revision 후보는 `main`, manifest path 후보는 각 repository의
  `k8s/`, destination namespace 후보는 현재 manifest 기준 `default`다.
- 초기 Sync 정책은 Manual Sync이며 `spec.syncPolicy.automated`, automatic prune,
  automatic self-heal은 사용하지 않는다.
- Argo CD server 접근은 public exposure가 아니라 `kubectl port-forward`를 1순위
  후보로 둔다.
- 고정 image tag 초기 권장안은 Backend와 Frontend 모두 full Git SHA 기반 tag를
  운영 manifest에 기록하는 방식이다.
- Rollback 기준은 이전 Git revision 또는 이전에 정상 확인된 고정 image tag다.
- `ClusterIssuer/letsencrypt-prod` ownership은 Backend Application 등록 전
  별도 결정이 필요하다.

## 이번 단계의 의미

- NewsLab의 “CI는 image를 만들고, CD는 운영 cluster 반영을 관리한다”는 책임
  경계를 명확히 했다.
- Argo CD를 도입하더라도 무조건 자동화 수준을 높이는 것이 아니라, 운영 승인권을
  유지하는 Manual Sync 구조로 시작하는 결정을 남겼다.
- `latest` tag 기반 운영의 한계를 GitOps 관점에서 정리했고, 고정 tag와 Git
  revision 기반 rollback으로 갈 방향을 세웠다.
- 설치 전에 Application 경계, repository/path/revision, Secret/DB migration,
  Sync/rollback 책임을 문서화해 후속 운영 작업의 위험을 줄였다.

## 포트폴리오용 요약

NewsLab의 기존 배포는 GitHub Actions가 Docker Hub에 ARM64 image를 발행하고,
사람이 K3s 반영과 production 확인을 수행하는 구조였다. 이번 작업에서는 Argo CD를
바로 설치하지 않고, backend와 frontend를 각각 Manual Sync Application으로
관리하는 GitOps 설계를 먼저 확정했다. 자동 Sync, prune, self-heal은 초기
범위에서 제외하고, full Git SHA 기반 image tag와 사람 승인 Sync, 명시적
rollback 기준을 문서화해 운영 통제와 배포 재현성을 함께 확보하는 방향을
정리했다.

## 다음 단계 후보

- Argo CD 최소 설치 task 작성 및 사람이 설치 version과 공식 문서를 재확인한다.
- Backend `news-api` Application 등록 전 `ClusterIssuer/letsencrypt-prod`
  ownership을 결정한다.
- Backend Manual Sync를 controlled task로 검증하고 rollout/API/CronJob 상태
  확인 log를 verification에 기록한다.
- Frontend `news-lab-web` Application 등록과 Manual Sync 검증을 별도 task로
  진행한다.
- Backend/Frontend 운영 manifest를 `latest`에서 고정 image tag로 전환하는
  workflow와 manifest 변경 task를 분리한다.
- 이전 Git revision 또는 고정 image tag 기반 rollback을 controlled test로
  검증한다.
- 실제 설치와 Sync 검증이 끝난 뒤 Architecture, Runbook, README에 현재 운영
  구조로 승격한다.
