# Verification: Argo CD 승인형 배포 구조 설계

## Verification Status

passed

## Verification Scope

UNIT-01, UNIT-02, UNIT-03: 현재 backend/frontend CI workflow, image tag policy,
K3s manifest, 수동 배포 흐름 조사와 baseline 문서화, Argo CD Application 경계,
Git source, Manual Sync 정책 설계, 고정 image tag 전략, Sync/rollback 책임
경계, 후속 실행 계획 문서화.

## Commands Run

Command:
`pwd && git branch --show-current && git status --short`

Result:
`/Users/seochanjin/workspace/NewsLab/news-lab`, branch
`feature/argocd-manual-sync-baseline` 확인. 기존 untracked workflow 문서들과
`docs/tasks/main.md` 수정 상태가 있었다.

Status: passed

Notes:
작업 전 상태 확인용 read-only command.

Command:
`sed -n '1,220p' AGENTS.md`

Result:
필수 workflow, WIP 1, 금지 command, verification 기록 원칙 확인.

Status: passed

Notes:
문서 읽기 command.

Command:
`sed -n '1,520p' docs/tasks/feature-argocd-manual-sync-baseline.md`

Result:
Scope, Do not change, Test commands, Acceptance criteria, UNIT-01 대상 확인.

Status: passed

Notes:
Task source of truth 확인.

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`

Result:
조사, 변경, 문서화, 검증, verification 기록, checklist 갱신 순서와 WIP 1 확인.

Status: passed

Notes:
필수 workflow 문서 확인.

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`

Result:
현재 branch와 working tree 확인, 허용 command만 실행, review output만으로 수정 금지,
완료 보고 기준 확인.

Status: passed

Notes:
Codex 역할 지침 확인.

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`

Result:
Verification Status, command별 Result/Status 기록, diff 범위 확인 gate 확인.

Status: passed

Notes:
검증 기록 형식 확인.

Command:
`sed -n '1,280p' docs/agent/forbidden-commands.md`

Result:
`git push`, `git merge`, `kubectl apply`, `kubectl rollout`, Helm, Docker push,
Supabase 운영 SQL 실행 금지 확인.

Status: passed

Notes:
고위험 command 경계 확인.

Command:
`sed -n '1,220p' docs/agent/task-authoring-guide.md`

Result:
Python 문서화 정책 확인. UNIT-01에서는 Python 파일을 생성하거나 수정하지 않음.

Status: passed

Notes:
사용자 요청의 Python 문서화 규칙 확인.

Command:
`rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Backend `.github/workflows/docker-build.yml`이 `main` push와 `workflow_dispatch`,
`docker/setup-buildx-action@v3`, `docker/build-push-action@v6`,
`platforms: linux/arm64`, `${{ github.sha }}` tag, `latest` tag를 포함함을
확인. Backend manifest는 `seocj/news-api:latest`를 참조함.

Status: passed

Notes:
Task 지정 backend CI/image 조사 command.

Command:
`rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s`

Result:
Backend `k8s/`에서 Deployment `news-api`, Service `news-api`, Ingress
`news-api-ingress`, CronJob `news-rss-collector`,
`news-daily-topic-pipeline`, `news-three-day-topic-pipeline`,
`news-weekly-topic-pipeline`, ClusterIssuer `letsencrypt-prod` 확인. API와
CronJob image는 `seocj/news-api:latest`, API replicas는 `2`, CronJob schedule과
`workload: app` node selector 확인.

Status: passed

Notes:
Task 지정 backend manifest 조사 command.

Command:
`cd ~/workspace/NewsLab/news-lab-web && rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Frontend `.github/workflows/docker-build.yml`이 `pull_request`, `main` push,
`v*` tag push, `workflow_dispatch`, QEMU, Buildx, Docker metadata,
`platforms: linux/arm64`, non-PR push, `main`, `latest`, `sha-*` tag policy를
포함함을 확인. Frontend manifest는 `seocj/news-lab-web:latest`를 참조함.

Status: passed

Notes:
Task 지정 frontend CI/image 조사 command.

Command:
`cd ~/workspace/NewsLab/news-lab-web && rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s`

Result:
Frontend `k8s/`에서 Deployment `news-lab-web`, Service `news-lab-web`,
Ingress `news-lab-web-ingress`, Middleware `news-lab-web-redirect-https` 확인.
Deployment replicas는 `2`, node selector는 `workload: app`, image는
`seocj/news-lab-web:latest`.

Status: passed

Notes:
Task 지정 frontend manifest 조사 command.

Command:
`find . -maxdepth 4 -type f \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) | sort`

Result:
Backend repository에는 Argo CD 설치 manifest나 Application YAML이 없고, 현재
branch의 workflow 문서 파일만 검색됨.

Status: passed

Notes:
Task 지정 Argo CD resource 부재 확인 command.

Command:
`rg -n "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md`

Result:
UNIT-01 문서와 후속 UNIT 보류 항목에서 `Manual Sync`, `repository`, `path`,
`namespace`, `rollback`, `latest`, `automated`, `prune`, `self-heal`,
`Application` 관련 문구가 검색됨. `git-sha`, `Tailscale`, `port-forward` 같은
후속 결정어는 UNIT-01에서 확정하지 않았으므로 아직 별도 본문으로 작성하지 않음.

Status: passed

Notes:
Task 지정 설계 문서 검색 command를 UNIT-01 범위에서 실행. 전체 acceptance
criteria 충족 여부는 UNIT-02/03 완료 후 재확인 필요.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
출력 없음. 금지된 application, script, K3s manifest, workflow, DB, dependency,
Docker 관련 tracked file 변경 없음.

Status: passed

Notes:
Task 지정 금지 영역 변경 여부 확인 command.

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace 오류 없음.

Status: passed

Notes:
Task 지정 Markdown 형식 오류 확인 command. 새 문서는 untracked 상태이므로 전체
task 완료 전 다시 확인 필요.

Command:
`git status --short`

Result:
`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 수정과
`docs/architecture/argocd-manual-sync-design.md`,
`docs/runbooks/argocd-manual-sync-plan.md`,
`docs/tasks/feature-argocd-manual-sync-baseline.md`,
`docs/verification/feature-argocd-manual-sync-baseline.md` 등 branch workflow 문서
untracked 상태 확인. 기존 `docs/tasks/main.md` 수정과 review/fix/pr/devlog
untracked 파일도 남아 있음.

Status: passed

Notes:
Task 지정 전체 변경 범위 확인 command.

Command:
`git diff -- docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/runbooks`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`에 Argo CD Manual
Sync 문서 링크가 1개씩 추가된 것을 확인. 새 architecture/runbook 문서는
untracked 상태라 이 command의 diff 본문에는 표시되지 않음.

Status: passed

Notes:
Task 지정 문서 변경 범위 확인 command.

Command:
`sed -n '1,220p' docs/ARCHITECTURE.md`

Result:
Architecture index의 현재 세부 문서 목록과 K3s runtime 문서 진입점을 확인.

Status: passed

Notes:
Argo CD 설계 문서 index link 추가 위치 확인.

Command:
`sed -n '1,220p' docs/RUNBOOK.md`

Result:
Runbook index의 현재 세부 문서 목록과 human-controlled operation 원칙 확인.

Status: passed

Notes:
Argo CD runbook link 추가 위치 확인.

Command:
`rg --files .github k8s docs/architecture docs/runbooks | sort`

Result:
Backend workflow, K3s manifest, architecture/runbook 세부 문서 목록 확인.

Status: passed

Notes:
관련 파일 위치 조사.

Command:
`sed -n '1,180p' .github/workflows/docker-build.yml`

Result:
Backend Docker workflow의 trigger, path filter, Buildx, Docker Hub login,
`linux/arm64`, `${{ github.sha }}` tag, `latest` tag 확인.

Status: passed

Notes:
Backend CI 상세 확인.

Command:
`sed -n '1,140p' k8s/news-api.yaml && sed -n '1,120p' k8s/news-rss-collector-cronjob.yaml && sed -n '1,110p' k8s/news-daily-topic-pipeline-cronjob.yaml`

Result:
Backend API Deployment/Service/Ingress와 RSS/daily CronJob의 image,
`imagePullPolicy: Always`, node selector, Secret reference, schedule 일부 확인.

Status: passed

Notes:
Backend manifest 상세 확인.

Command:
`cd ~/workspace/NewsLab/news-lab-web && sed -n '1,130p' .github/workflows/docker-build.yml && sed -n '1,90p' .github/workflows/ci.yml`

Result:
Frontend Docker workflow의 trigger, QEMU, Buildx, metadata tag policy,
`linux/arm64`, non-PR push 조건과 frontend CI lint/typecheck/build workflow 확인.

Status: passed

Notes:
Frontend CI 상세 확인.

Command:
`cd ~/workspace/NewsLab/news-lab-web && sed -n '1,140p' k8s/news-lab-web-deployment.yaml && sed -n '1,120p' k8s/news-lab-web-service.yaml && sed -n '1,130p' k8s/news-lab-web-ingress.yaml && sed -n '1,80p' k8s/news-lab-web-redirect-https-middleware.yaml`

Result:
Frontend Deployment, Service, Ingress, Traefik Middleware manifest 상세 확인.
Deployment는 `replicas: 2`, `seocj/news-lab-web:latest`, `imagePullPolicy:
Always`, `/api/health` probes를 사용함.

Status: passed

Notes:
Frontend manifest 상세 확인.

Command:
`rg -n "rollout|kubectl apply|kubectl.*restart|Docker Hub|image|latest|배포|수동" docs/runbooks docs/architecture README.md docs/devlog/feature-topic-summary-api-deploy.md docs/devlog/docs-readme-portfolio-refresh.md`

Result:
README, backend deploy runbook, K3s runtime 문서, 기존 devlog에서 GitHub
Actions image push와 K3s rollout 분리, human-controlled rollout restart,
`latest` image 한계 기록을 확인.

Status: passed

Notes:
현재 수동 배포 흐름의 문서 근거 조사.

Command:
`sed -n '1,220p' docs/runbooks/backend-deploy.md`

Result:
Backend 배포 runbook에서 사람이 실행하는 preflight, manifest apply, image
rollout restart, rollout status, running image, domain/certificate 확인 절차 확인.

Status: passed

Notes:
수동 배포 흐름 근거 확인.

Command:
`sed -n '1,120p' docs/architecture/k3s-runtime.md`

Result:
Backend workload가 K3s에서 실행되고, `k8s/` manifest와 `seocj/news-api:latest`,
`workload: app` node selector를 사용하며, apply/rollout/restart는 사람이
결정한다는 운영 경계 확인.

Status: passed

Notes:
K3s runtime 근거 확인.

Command:
`git diff --check`

Result:
최종 재실행 결과 출력 없음. 현재 tracked diff 기준 whitespace 오류 없음.

Status: passed

Notes:
Verification 기록 갱신 후 재확인.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
최종 재실행 결과 출력 없음. 금지 영역 tracked file 변경 없음.

Status: passed

Notes:
Verification 기록 갱신 후 재확인.

Command:
`grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`

Result:
출력 없음, exit 1. 지정한 tracked/untracked 문서 파일에서 trailing whitespace
match 없음.

Status: passed

Notes:
`git diff --check`가 untracked 새 파일 본문을 포함하지 않는 한계를 보완하기
위한 read-only 확인.

Command:
`sed -n '1,260p' docs/tasks/feature-argocd-manual-sync-baseline.md`

Result:
Task의 Scope, Do not change, Test commands, Acceptance criteria와 UNIT-02 대상
확인.

Status: passed

Notes:
UNIT-02 시작 전 task source of truth 재확인.

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`

Result:
WIP 1, 조사→변경→문서화→검증→checklist 갱신 순서와 workflow artifact 기준
확인.

Status: passed

Notes:
필수 workflow 문서 확인.

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`

Result:
현재 branch와 working tree 확인, 허용 command만 실행, 금지 영역 변경 회피,
완료 보고 기준 확인.

Status: passed

Notes:
Codex 역할 지침 확인.

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`

Result:
작업 전 상태, 작업 단위 완료, 전체 변경 범위, verification 기록 형식 확인.

Status: passed

Notes:
검증 기준 확인.

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`

Result:
`git push`, `git merge`, `kubectl apply`, `kubectl rollout`, Helm, Docker push,
Supabase 운영 SQL 금지와 Secret/credential 기록 금지 확인.

Status: passed

Notes:
고위험 command 경계 확인.

Command:
`sed -n '70,115p' docs/agent/task-authoring-guide.md`

Result:
Python 문서화 정책 확인. UNIT-02에서는 Python 파일을 생성하거나 수정하지 않음.

Status: passed

Notes:
사용자 요청의 Python 문서화 규칙 확인.

Command:
`git status --short --branch`

Result:
현재 branch가 `feature/argocd-manual-sync-baseline`이고, UNIT-01에서 생성·수정된
workflow 문서와 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md`
변경 상태가 남아 있음을 확인.

Status: passed

Notes:
UNIT-02 작업 전 working tree 확인.

Command:
`sed -n '1,260p' docs/architecture/argocd-manual-sync-design.md`

Result:
UNIT-01 baseline과 UNIT-02 보류 항목 위치를 확인.

Status: passed

Notes:
설계 문서 갱신 위치 확인.

Command:
`sed -n '1,260p' docs/runbooks/argocd-manual-sync-plan.md`

Result:
UNIT-01 runbook baseline과 UNIT-02 보류 항목 위치를 확인.

Status: passed

Notes:
runbook 계획 문서 갱신 위치 확인.

Command:
`git remote -v`

Result:
Backend repository remote가 `https://github.com/seochanjin/news-lab.git`임을 확인.

Status: passed

Notes:
Argo CD Application source repository 근거 확인.

Command:
`cd /Users/seochanjin/workspace/NewsLab/news-lab-web && git remote -v`

Result:
Frontend repository remote가 `https://github.com/seochanjin/news-lab-web.git`임을
확인.

Status: passed

Notes:
Argo CD Application source repository 근거 확인.

Command:
`sed -n '1,220p' k8s/news-api.yaml`

Result:
Backend Deployment, Service, Ingress가 namespace를 명시하지 않고,
`seocj/news-api:latest`, `news-api-secret`, `news-api-ingress`를 사용하는 것을
확인.

Status: passed

Notes:
Backend Application ownership과 destination namespace 후보 근거 확인.

Command:
`sed -n '1,180p' k8s/news-weekly-topic-pipeline-cronjob.yaml`

Result:
Weekly topic CronJob이 namespace를 명시하지 않고, backend image와
`news-api-secret`을 참조하는 것을 확인.

Status: passed

Notes:
Backend CronJob ownership과 Secret 변경 책임 경계 근거 확인.

Command:
`cd /Users/seochanjin/workspace/NewsLab/news-lab-web && sed -n '1,180p' k8s/news-lab-web-ingress.yaml`

Result:
Frontend Ingress `news-lab-web-ingress`, TLS Secret resource name, Middleware
annotation, host 설정을 확인.

Status: passed

Notes:
Frontend Application ownership과 Sync 전 확인 항목 근거 확인.

Command:
`rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Backend workflow, `latest` image reference, UNIT 문서의 Docker/image 관련 기록이
검색됨.

Status: passed

Notes:
Task 지정 backend CI/image 조사 command를 UNIT-02 후 재실행.

Command:
`rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s`

Result:
Backend `k8s/`에서 API Deployment/Service/Ingress, CronJob들과
`ClusterIssuer/letsencrypt-prod`가 검색됨.

Status: passed

Notes:
`ClusterIssuer`가 backend Application 경계에 섞일 수 있음을 확인하고 설계에
주의 사항으로 기록.

Command:
`cd /Users/seochanjin/workspace/NewsLab/news-lab-web && rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Frontend Docker workflow, CI workflow, `seocj/news-lab-web:latest`, `latest`,
`sha-*`, `main` tag 관련 기록이 검색됨.

Status: passed

Notes:
Task 지정 frontend CI/image 조사 command를 UNIT-02 후 재실행.

Command:
`cd /Users/seochanjin/workspace/NewsLab/news-lab-web && rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s`

Result:
Frontend `k8s/`에서 Deployment `news-lab-web`, Service `news-lab-web`, Ingress
`news-lab-web-ingress`, Middleware `news-lab-web-redirect-https`가 검색됨.

Status: passed

Notes:
Frontend Application ownership 경계 근거 확인.

Command:
`find . -maxdepth 4 -type f \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) | sort`

Result:
Argo CD 설치 manifest나 Application YAML은 없고, 현재 branch의 문서 산출물만
검색됨.

Status: passed

Notes:
이번 UNIT에서 Argo CD resource를 생성하지 않았음을 확인.

Command:
`rg -n "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md`

Result:
UNIT-02 문서에서 Manual Sync, `automated`, prune, self-heal, Application,
repository, targetRevision, path, namespace, Tailscale, port-forward, rollback,
latest 관련 문구가 검색됨. `git-sha` 세부 tag 결정은 UNIT-03 범위로 남김.

Status: passed

Notes:
Task 지정 설계 문서 핵심 결정 검색 command.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
출력 없음. 금지된 application, script, K3s manifest, workflow, DB, dependency,
Docker 관련 tracked file 변경 없음.

Status: passed

Notes:
UNIT-02 후 금지 영역 변경 여부 확인.

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace 오류 없음.

Status: passed

Notes:
Task 지정 Markdown 형식 오류 확인 command. 새 문서는 untracked 상태이므로 최종
확인에서 별도 trailing whitespace grep을 다시 수행함.

Command:
`git status --short`

Result:
`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md` 수정과
branch workflow 문서 untracked 상태를 확인.

Status: passed

Notes:
전체 변경 범위 확인.

Command:
`git diff -- docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/runbooks`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`의 Argo CD Manual
Sync 문서 링크 추가만 표시됨. 새 architecture/runbook 문서는 untracked 상태라
이 command의 diff 본문에는 표시되지 않음.

Status: passed

Notes:
Task 지정 문서 변경 범위 확인 command.

Command:
`grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`

Result:
출력 없음, exit 1. 지정한 tracked/untracked 문서 파일에서 trailing whitespace
match 없음.

Status: passed

Notes:
UNIT-02 verification 기록 갱신 후 재확인.

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace 오류 없음.

Status: passed

Notes:
UNIT-02 verification 기록 갱신 후 재확인.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
출력 없음. 금지된 application, script, K3s manifest, workflow, DB, dependency,
Docker 관련 tracked file 변경 없음.

Status: passed

Notes:
UNIT-02 verification 기록 갱신 후 재확인.

Command:
`git status --short`

Result:
`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md` 수정과
branch workflow 문서 untracked 상태를 확인.

Status: passed

Notes:
UNIT-02 종료 전 전체 변경 상태 확인.

Command:
`git diff --stat`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`,
`docs/tasks/main.md` 변경이 표시됨. 새 branch workflow 문서는 untracked 상태라
stat에 포함되지 않음.

Status: passed

Notes:
전체 tracked 변경 범위 확인. `docs/tasks/main.md` 변경은 UNIT-02 시작 전부터
존재하던 상태로, 이번 UNIT에서 수정하지 않음.

Command:
`git diff --name-only`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`,
`docs/tasks/main.md`가 표시됨.

Status: passed

Notes:
전체 tracked 변경 file 확인. 새 문서는 untracked 상태라 이 command 출력에는
포함되지 않음.

Command:
`pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/feature-argocd-manual-sync-baseline.md' -g 'docs/verification/feature-argocd-manual-sync-baseline.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'`

Result:
현재 작업 directory가 `/Users/seochanjin/workspace/NewsLab/news-lab`이고 branch가
`feature/argocd-manual-sync-baseline`임을 확인. AGENTS, task, verification,
필수 workflow 문서, Python 문서화 정책 파일이 모두 존재함을 확인.

Status: passed

Notes:
UNIT-03 시작 전 source of truth와 필수 문서 위치 확인.

Command:
`sed -n '1,260p' AGENTS.md`

Result:
WIP 1, task source of truth, 금지 command, workflow artifact, verification 원칙
확인.

Status: passed

Notes:
UNIT-03 필수 문서 재확인.

Command:
`sed -n '1,760p' docs/tasks/feature-argocd-manual-sync-baseline.md`

Result:
Scope, Do not change, Test commands, Acceptance criteria, UNIT-03 대상 확인.

Status: passed

Notes:
Task source of truth 재확인.

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`

Result:
WIP 1과 조사, 변경, 문서화, 검증, verification 기록, checklist 갱신 순서 확인.

Status: passed

Notes:
UNIT-03 workflow 기준 확인.

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`

Result:
현재 branch와 working tree 확인, 허용 command만 실행, Python docstring 정책,
완료 보고 기준 확인.

Status: passed

Notes:
UNIT-03 역할 지침 확인.

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`

Result:
작업 전 상태, 작업 단위 완료, 전체 변경 범위, 문서 구조 task의 end-to-end 검증
기준 확인.

Status: passed

Notes:
UNIT-03 검증 기준 확인.

Command:
`sed -n '1,320p' docs/agent/forbidden-commands.md`

Result:
`git push`, `git merge`, `kubectl apply`, `kubectl rollout`, Helm, Docker push,
Supabase 운영 SQL, Secret/credential 기록 금지 확인.

Status: passed

Notes:
UNIT-03 고위험 command 경계 확인.

Command:
`sed -n '1,240p' docs/agent/task-authoring-guide.md`

Result:
Python 문서화 정책 확인. UNIT-03에서는 Python 파일을 생성하거나 수정하지 않음.

Status: passed

Notes:
사용자 요청의 Python 문서화 규칙 확인.

Command:
`git status --short --branch`

Result:
현재 branch가 `feature/argocd-manual-sync-baseline`이고, UNIT-01/02에서 생성·수정된
문서와 `docs/tasks/main.md` 변경 상태가 남아 있음을 확인.

Status: passed

Notes:
UNIT-03 작업 전 working tree 확인.

Command:
`sed -n '1,360p' docs/architecture/argocd-manual-sync-design.md`

Result:
UNIT-01/02 문서와 UNIT-03 보류 항목 위치를 확인.

Status: passed

Notes:
설계 문서 갱신 위치 확인.

Command:
`sed -n '1,360p' docs/runbooks/argocd-manual-sync-plan.md`

Result:
UNIT-01/02 runbook과 UNIT-03 보류 항목 위치를 확인.

Status: passed

Notes:
runbook 계획 문서 갱신 위치 확인.

Command:
`sed -n '1,180p' docs/ARCHITECTURE.md && sed -n '1,180p' docs/RUNBOOK.md`

Result:
Architecture index와 Runbook index에 Argo CD Manual Sync 설계/계획 링크가
연결되어 있음을 확인.

Status: passed

Notes:
문서 구조 task의 index 연결 확인.

Command:
`git diff -- docs/ARCHITECTURE.md docs/RUNBOOK.md docs/tasks/main.md`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`에는 Argo CD Manual
Sync 링크가 1개씩 추가되어 있고, `docs/tasks/main.md`는 current task link를
이번 branch task로 가리킴.

Status: passed

Notes:
`docs/tasks/main.md` 변경은 UNIT-03 시작 전부터 존재하던 상태.

Command:
`rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Backend workflow의 `main` push, `workflow_dispatch`, Buildx, build-push,
`linux/arm64`, full Git SHA tag, `latest` tag와 backend manifest의
`seocj/news-api:latest` reference가 검색됨. UNIT-03 문서의 `latest` 한계와
고정 tag 계획도 검색됨.

Status: passed

Notes:
Task 지정 backend CI/image 조사 command를 UNIT-03 후 재실행.

Command:
`rg -n "kind:|metadata:|name:|image:|replicas:|schedule:|nodeSelector:" k8s`

Result:
Backend `k8s/`에서 API Deployment/Service/Ingress, CronJob들,
`ClusterIssuer/letsencrypt-prod`, `seocj/news-api:latest`, replicas, schedule,
node selector가 검색됨.

Status: passed

Notes:
Task 지정 backend manifest 조사 command를 UNIT-03 후 재실행.

Command:
`cd ~/workspace/NewsLab/news-lab-web && rg -n "docker|buildx|build-push|platforms|tags:|latest|workflow_dispatch|push:" .github README.md k8s docs`

Result:
Frontend Docker workflow의 PR/main/tag/workflow_dispatch trigger, QEMU, Buildx,
metadata, build-push, `linux/arm64`, non-PR push, `latest`, `sha-*` tag policy와
frontend manifest의 `seocj/news-lab-web:latest` reference가 검색됨.

Status: passed

Notes:
Task 지정 frontend CI/image 조사 command를 UNIT-03 후 재실행.

Command:
`cd ~/workspace/NewsLab/news-lab-web && rg -n "kind:|metadata:|name:|image:|replicas:|nodeSelector:" k8s`

Result:
Frontend `k8s/`에서 Deployment `news-lab-web`, Service `news-lab-web`, Ingress
`news-lab-web-ingress`, Middleware `news-lab-web-redirect-https`,
`seocj/news-lab-web:latest`, replicas, node selector가 검색됨.

Status: passed

Notes:
Task 지정 frontend manifest 조사 command를 UNIT-03 후 재실행.

Command:
`find . -maxdepth 4 -type f \( -iname "*argocd*" -o -iname "*argo-cd*" -o -iname "*application*.yaml" \) | sort`

Result:
Argo CD 설치 manifest나 Application YAML은 없고, 현재 branch의 문서 산출물만
검색됨.

Status: passed

Notes:
이번 task에서 Argo CD resource를 생성하지 않았음을 확인.

Command:
`rg -n "Manual Sync|수동 Sync|automated|prune|self-heal|Application|repository|targetRevision|path|namespace|rollback|latest|git-sha|Tailscale|port-forward" docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md`

Result:
설계/계획 문서에서 Manual Sync, `automated`, prune, self-heal, Application,
repository, targetRevision, path, namespace, rollback, `latest`, `git-sha`,
Tailscale, `port-forward` 관련 문구가 검색됨.

Status: passed

Notes:
Task 지정 설계 문서 핵심 결정 검색 command.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
출력 없음. 금지된 application, script, K3s manifest, workflow, DB, dependency,
Docker 관련 tracked file 변경 없음.

Status: passed

Notes:
UNIT-03 후 금지 영역 변경 여부 확인.

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace 오류 없음.

Status: passed

Notes:
Task 지정 Markdown 형식 오류 확인 command. 새 문서는 untracked 상태이므로
아래 trailing whitespace grep으로 보완함.

Command:
`git status --short`

Result:
`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md` 수정과 branch
workflow 문서 untracked 상태를 확인.

Status: passed

Notes:
Task 지정 전체 변경 범위 확인 command.

Command:
`git diff -- docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/runbooks`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`의 Argo CD Manual
Sync 문서 링크 추가만 표시됨. 새 architecture/runbook 문서는 untracked 상태라
이 command의 diff 본문에는 표시되지 않음.

Status: passed

Notes:
Task 지정 문서 변경 범위 확인 command.

Command:
`grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`

Result:
출력 없음, exit 1. 지정한 tracked/untracked 문서 파일에서 trailing whitespace
match 없음.

Status: passed

Notes:
`git diff --check`가 untracked 새 파일 본문을 포함하지 않는 한계를 보완하기
위한 read-only 확인.

Command:
`git diff --stat && git diff --name-only`

Result:
Tracked diff 기준 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`,
`docs/tasks/main.md`만 표시됨. 새 branch workflow 문서는 untracked 상태라
출력에 포함되지 않음.

Status: passed

Notes:
전체 tracked 변경 범위 확인.

Command:
`git diff --check`

Result:
출력 없음. Verification 기록과 task checklist 갱신 후에도 현재 tracked diff
기준 whitespace 오류 없음.

Status: passed

Notes:
최종 Markdown 형식 오류 확인.

Command:
`git diff --name-only -- app scripts k8s .github db Dockerfile requirements.txt docker-compose.yml`

Result:
출력 없음. 금지된 application, script, K3s manifest, workflow, DB, dependency,
Docker 관련 tracked file 변경 없음.

Status: passed

Notes:
최종 금지 영역 변경 여부 확인.

Command:
`grep -n '[[:blank:]]$' docs/architecture/argocd-manual-sync-design.md docs/runbooks/argocd-manual-sync-plan.md docs/tasks/feature-argocd-manual-sync-baseline.md docs/verification/feature-argocd-manual-sync-baseline.md docs/ARCHITECTURE.md docs/RUNBOOK.md`

Result:
출력 없음, exit 1. 지정한 tracked/untracked 문서 파일에서 trailing whitespace
match 없음.

Status: passed

Notes:
최종 untracked 문서 whitespace 확인.

Command:
`git status --short`

Result:
`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md` 수정과 branch
workflow 문서 untracked 상태를 확인.

Status: passed

Notes:
최종 working tree 상태 확인.

## Results

- UNIT-01 문서화:
  - `docs/architecture/argocd-manual-sync-design.md`
  - `docs/runbooks/argocd-manual-sync-plan.md`
- UNIT-02 문서화:
  - `docs/architecture/argocd-manual-sync-design.md`
  - `docs/runbooks/argocd-manual-sync-plan.md`
- UNIT-03 문서화:
  - `docs/architecture/argocd-manual-sync-design.md`
  - `docs/runbooks/argocd-manual-sync-plan.md`
- Index link 추가:
  - `docs/ARCHITECTURE.md`
  - `docs/RUNBOOK.md`
- Task checklist에서 UNIT-01, UNIT-02, UNIT-03 완료 처리.

## Manual or Production Verification

- 실행하지 않음.
- Argo CD 설치, namespace 생성, Helm, `kubectl apply`, `kubectl rollout`,
  Docker push, Supabase SQL, production endpoint verification은 수행하지 않음.

## Pending Verification

- 없음. 이 task에서 허용된 read-only 조사와 문서 검증은 통과함.
- Argo CD 설치, Application 등록, Manual Sync, rollback, production endpoint
  verification은 후속 task의 사람 실행 대상이다.

## Evidence Notes

- Backend 현재 운영 image reference는 `seocj/news-api:latest`.
- Frontend 현재 운영 image reference는 `seocj/news-lab-web:latest`.
- Backend는 full Git SHA tag를 발행하지만 운영 manifest는 `latest`를 사용한다.
- Frontend는 `main`, `latest`, version tag, `sha-*` tag를 발행할 수 있지만 운영
  manifest는 `latest`를 사용한다.
- Backend와 Frontend manifest는 각 repository의 `k8s/`에 분산되어 있다.
- 초기 Argo CD Application 후보는 `news-api`와 `news-lab-web` 2개다.
- Application source repository 후보는 각각
  `https://github.com/seochanjin/news-lab.git`,
  `https://github.com/seochanjin/news-lab-web.git`이다.
- 초기 target revision 후보는 `main`, manifest path 후보는 각 repository의
  `k8s/`, destination namespace 후보는 현재 manifest 기준 `default`다.
- Backend `k8s/`에는 shared TLS infrastructure 성격의
  `ClusterIssuer/letsencrypt-prod`가 함께 있어, Application 등록 전 ownership
  결정을 별도로 해야 한다.
- 초기 Sync 정책은 Manual Sync이며 `spec.syncPolicy.automated`, automatic prune,
  automatic self-heal은 사용하지 않는 설계다.
- Argo CD server 접근은 public exposure가 아니라 `kubectl port-forward`를 1순위
  후보로 둔다.
- 고정 image tag 초기 권장안은 Backend와 Frontend 모두 full Git SHA 기반 tag를
  운영 manifest에 기록하는 방식이다.
- `latest`는 보조 tag로는 발행 가능하지만 운영 manifest와 rollback 기준으로
  사용하지 않는 설계다.
- 초기 manifest tag 갱신은 사람이 build 결과의 Git SHA tag를 확인하고 PR로
  변경하는 방식이다.
- Sync 전 확인 항목과 Sync 후 검증 항목을 분리해 문서화했다.
- Rollback 기준은 이전 Git revision 또는 이전에 정상 확인된 고정 image tag다.
