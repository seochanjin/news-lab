# Argo CD 승인형 배포 구조 설계

## 작업 내용

- NewsLab의 현재 GitHub Actions 기반 image build/push 흐름과 사람이 수행하는 K3s 반영 절차를 조사했다.
- Argo CD를 곧바로 설치하지 않고, Manual Sync 기반 승인형 GitOps 배포 구조를 설계 문서와 실행 계획 문서로 정리했다.
- Backend와 Frontend를 각각 `news-api`, `news-lab-web` Argo CD Application 후보로 분리하고 repository, revision, manifest path, namespace, sync policy 후보를 기록했다.
- `latest` image tag를 운영 manifest 기준으로 사용할 때의 GitOps 한계를 정리하고, 고정 image tag와 rollback 기준을 문서화했다.
- Architecture/Runbook index에 Argo CD Manual Sync 설계와 실행 계획 링크를 추가했다.

## 주요 변경 사항

- `docs/architecture/argocd-manual-sync-design.md`
  - CI와 CD의 역할 차이, 현재 수동 배포 baseline, Backend/Frontend CI와 image tag 정책을 정리했다.
  - Backend manifest는 `news-lab/k8s/`, Frontend manifest는 `news-lab-web/k8s/`에 분산되어 있음을 기록했다.
  - 초기 Application 후보를 `news-api`, `news-lab-web` 2개로 결정했다.
  - 초기 정책을 Manual Sync로 두고 `spec.syncPolicy.automated`, automatic prune, automatic self-heal을 사용하지 않는 설계로 정리했다.
  - Argo CD server 접근은 public exposure가 아니라 `kubectl port-forward`를 1순위 후보로 기록했다.
  - Secret, DB migration, production endpoint verification은 Argo CD Sync 자동 범위에 포함하지 않는 책임 경계를 명시했다.
- `docs/runbooks/argocd-manual-sync-plan.md`
  - 설치 전제, Application 등록 전 확인 항목, Manual Sync 전/후 checklist, rollback 절차 기준, 후속 task 분리 계획을 정리했다.
  - `ClusterIssuer/letsencrypt-prod` ownership은 Backend Application 등록 전에 사람이 결정해야 하는 항목으로 남겼다.
- `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`
  - 새 Argo CD Manual Sync 설계/계획 문서 링크를 추가했다.
- `docs/tasks/main.md`
  - 현재 task link를 `feature-argocd-manual-sync-baseline.md`로 갱신했다.
- workflow artifact
  - `docs/tasks/feature-argocd-manual-sync-baseline.md`
  - `docs/verification/feature-argocd-manual-sync-baseline.md`
  - `docs/fixes/feature-argocd-manual-sync-baseline-approved-fixes.md`
  - `docs/pr/feature-argocd-manual-sync-baseline.md`

Approved fixes source of truth인 `docs/fixes/feature-argocd-manual-sync-baseline-approved-fixes.md`에는 승인된 fix 항목이 없어 별도 fix 적용은 없었다.

## 추가/변경된 API

없음.

- FastAPI endpoint 추가/변경 없음
- Request/response schema 변경 없음
- Public API 계약 변경 없음
- Backend 또는 Frontend 배포 없음

## DB 변경 사항

없음.

- DB schema/migration/table/column/index/constraint 변경 없음
- Supabase SQL 실행 없음
- DB write 없음
- Argo CD가 DB migration을 자동 실행하도록 설계하지 않음

## README 영향

- README 변경 없음.
- 이번 task는 Argo CD 설치나 실제 Manual Sync 검증이 아니라 승인형 배포 구조의 baseline 설계가 목적이다.
- README에는 Argo CD 설치와 Manual Sync가 실제로 검증된 뒤에만 현재 배포 구조로 반영한다는 task 기준을 따랐다.

## 테스트

- `docs/verification/feature-argocd-manual-sync-baseline.md` 기준으로 read-only 조사와 문서 검증을 수행했다.
- Backend CI/image 조사:
  - `rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`
  - Backend workflow가 `main` push, `workflow_dispatch`, Buildx, `linux/arm64`, full Git SHA tag, `latest` tag를 사용하고 운영 manifest는 `seocj/news-api:latest`를 참조함을 확인.
- Backend manifest 조사:
  - `rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s`
  - API Deployment/Service/Ingress, RSS/Daily/Three-day/Weekly CronJob, `replicas: 2`, `workload: app`, `seocj/news-api:latest` 확인.
- Frontend repository 조사:
  - `cd ~/workspace/NewsLab/news-lab-web && rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`
  - `cd ~/workspace/NewsLab/news-lab-web && rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s`
  - Frontend Docker workflow, `latest`, `sha-*`, `main` tag policy와 `news-lab-web` Deployment/Service/Ingress/Middleware manifest 확인.
- Argo CD resource 부재 확인:
  - `find . -maxdepth 4 -type f \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) | sort`
  - 설치 manifest나 Application YAML 없이 문서 산출물만 검색됨.
- 설계 문서 핵심 결정 확인:
  - `rg -n "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md`
- 금지 영역 변경 여부:
  - `git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`
  - 출력 없음.
- Markdown/whitespace 확인:
  - `git diff --check`
  - `grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`
  - whitespace 오류 없음.

Application test, deployment test, Argo CD Sync test는 실행하지 않았다. 이번 작업은 조사와 설계 문서 작성이며 application code, DB, API, K3s manifest, GitHub Actions workflow를 변경하지 않았다.

## 확인 결과

- Verification status는 `passed`다.
- 이번 task에서 허용된 read-only 조사와 문서 검증은 통과했다.
- Backend와 Frontend는 현재 각 repository의 `k8s/` manifest에서 `latest` image tag를 운영 기준으로 사용하고 있음이 확인됐다.
- 초기 Argo CD Application 후보는 `news-api`, `news-lab-web` 2개로 정리됐다.
- 초기 target revision 후보는 `main`, manifest path 후보는 각 repository의 `k8s/`, destination namespace 후보는 현재 manifest 기준 `default`다.
- 초기 Sync 정책은 Manual Sync이며 automated sync, automatic prune, automatic self-heal은 사용하지 않는 설계다.
- Argo CD 설치, namespace 생성, Helm 실행, `kubectl apply`, `kubectl rollout`, Docker push, Supabase SQL, production endpoint verification은 수행하지 않았다.
- Pending verification은 없음. 단, Argo CD 설치, Application 등록, Manual Sync, rollback, production endpoint verification은 후속 task의 사람 실행 대상이다.

## 비고

- PR merge 완료를 주장하지 않는다.
- Production deployment, K3s rollout, Argo CD 설치, Manual Sync 완료를 주장하지 않는다.
- 실행하지 않은 설치/Sync/rollback command는 후속 작업의 사람 실행 후보일 뿐, 이번 verification 결과가 아니다.
- Review 파일은 verification 통과 근거로 사용하지 않았다.
- `ClusterIssuer/letsencrypt-prod`는 backend `k8s/`에 함께 있으나 cluster-wide TLS infrastructure 성격이 있어 Backend Application 등록 전 ownership 결정을 별도로 해야 한다.
