# Verification: Backend immutable image 기반 GitOps 배포 파이프라인 완성

## Verification Status

pending

## Verification Scope

UNIT-01~UNIT-04: 현재 Backend image build workflow, manifest image reference,
Argo CD `news-api` Application 관리 범위를 조사하고 immutable image 전환 설계를
문서로 확정했다. UNIT-02에서는 full Git SHA 기반 Backend image build/push
workflow를 구현했다. UNIT-03에서는 image build 성공 이후 Kubernetes manifest
image tag 갱신 branch와 PR을 생성하는 workflow job을 구현했다. UNIT-04에서는
Deployment와 네 CronJob manifest를 동일한 full Git SHA image로 전환하고 로컬
정적 검증을 수행했다.

UNIT-05에서는 사람이 제공한 운영 검증 결과로 Docker Hub SHA image 존재,
`linux/arm64` platform, Argo CD `OutOfSync`와 image-only diff, Manual Sync 성공을
확인했다. UNIT-06에서는 사람이 제공한 운영 검증 결과로 Backend rollout, Pod와
CronJob image 일치, Argo CD `Synced`/`Healthy`, production `/health` 정상 응답을
확인했다.

UNIT-07 rollback/restore와 UNIT-08 전체 회귀 검증은 아직 수행하지 않았다.

## Commands Run

Command:
`pwd && git branch --show-current && git status --short`

Result:
현재 작업 경로는 repository root, branch는 `feature/backend-immutable-image-gitops`다.
작업 시작 전 `docs/tasks/main.md` 수정과 현재 task 관련 문서들의 untracked 상태가
있었다.

Status: passed

## Placeholder Cleanup Verification

Command:
`command -v rg`

Result:
`rg` 사용 가능을 확인했다. 출력 경로는 로컬 사용자 경로를 포함하므로 문서에는
기록하지 않는다.

Status: passed

Command:
`grep -En "$(printf '\\x3c[^\\x3e]+\\x3e')" docs/verification/feature-backend-immutable-image-gitops.md`

Result:
출력 없음. Verification Command 항목에 남아 있던 angle-bracket placeholder가
제거됐다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git diff -- docs/verification/feature-backend-immutable-image-gitops.md`

Result:
Verification 문서 diff가 출력됐다. 변경 범위는 placeholder command 정리,
Ruby assertion 원문 미보존 항목의 `Command summary`/`not-recorded` 전환,
그리고 이번 placeholder cleanup 검증 기록이다.

Status: passed

## Approved Fixes Verification 3

Command:
`git status --short --branch`

Result:
현재 branch는 `feature/backend-immutable-image-gitops`다. 작업 시작 시
`docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`가 modified
상태였고, Approved Fixes에 FIX-08~FIX-12가 미완료로 추가돼 있었다.

Status: passed

Command:
`sed -n '1,360p' docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
FIX-08~FIX-12가 CodeRabbit review 결과 기반 승인 항목임을 확인했다. 수정 허용
범위는 workflow와 task/pr/devlog/verification/fixes/review artifact 문서로
제한되고, K8s manifest, app, scripts, db, dependency 파일은 변경 금지로 기록돼
있다.

Status: passed

Command:
`rg -n -A 5 'name: Checkout source' .github/workflows/docker-build.yml`

Result:
`update-manifest` job의 `Checkout source` step에 `with:
persist-credentials: false`가 출력됐다. `build` job checkout에는 credential write
권한이 필요하지 않고 job 권한도 `contents: read`로 유지된다.

Status: passed

Command:
```bash
ruby -e '
require "yaml"
YAML.load_file(".github/workflows/docker-build.yml")
puts "workflow yaml ok"
'
```

Result:
`workflow yaml ok`가 출력됐다.

Status: passed

Command:
`rg -n '70차 전체 완료|전체 Task 완료' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
기존 숫자-prefixed 전체 완료 표현은 출력되지 않았다. `전체 Task 완료` 표현만
review artifact와 fixes 문서에서 출력됐다.

Status: passed

Command:
`rg -n '\.\./docs/|\]\(\.\./\.github/|\]\(\.\./k8s/' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. Re-review 2의 잘못된 `../docs/...`, `../.github/...`, `../k8s/...`
링크가 제거됐다.

Status: passed

Command:
`rg -n '\.\./fixes/|\.\./verification/|\.\./\.\./\.github/|\.\./\.\./k8s/' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
review artifact 기준 repository-relative 링크만 출력됐다. Approved Fixes와
Verification은 `../fixes/`, `../verification/`, root의 workflow와 K8s manifest는
`../../.github/`, `../../k8s/` 형태다.

Status: passed

Command:
`rg -n -e 'f[i]le://' -e '/U[s]ers/' -e '/h[o]me/' -e '[A-Za-z]:\\\\' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
출력 없음. Review artifact와 Verification 문서에 local URI, local absolute path,
Windows drive absolute path가 남아 있지 않다.

Status: passed

Command:
`rg -n '완벽하게 배제|완전히 제거|리스크가 없다|완벽히 조율' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. Re-review 2의 과도한 표현이 제거됐다.

Status: passed

Command:
`rg -n -e 'Antigravity.*PASS' -e 'antigravity-''review' -e '최종 review gate' -e 'CodeRabbit' -e '사람 검토' docs/tasks/feature-backend-immutable-image-gitops.md docs/pr/feature-backend-immutable-image-gitops.md docs/devlog/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
Task, PR, devlog에는 CodeRabbit review와 사람 검토가 최종 review gate로 기록돼
있다. 과거 review artifact를 merge 또는 Task 완료 조건으로 요구하는 문구와
해당 review 재실행 요구는 출력되지 않았다. Verification에는 과거 자동실행
금지 지시 기록만 남아 있다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- k8s app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. 이번 FIX-08~FIX-12 적용으로 K8s manifest, application code, scripts,
DB, dependency, compose 파일에 신규 변경이 생기지 않았다.

Status: passed

Command:
`git status --short --branch`

Result:
현재 branch는 `feature/backend-immutable-image-gitops`다. FIX-08~FIX-12 적용으로
workflow, task, review, fixes, verification, PR draft, devlog draft 문서가
수정된 상태다.

Status: passed

Command:
`rg -n 'FIX-08|FIX-09|FIX-10|FIX-11|FIX-12|Applied Changes|적용 대기|pending' docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
FIX-08~FIX-12가 `[x]` 상태이며 Applied Changes에 각 fix 적용 내역이 기록돼
있다. `pending` 문구는 전체 Task의 남은 UNIT-05~UNIT-08 상태와 운영 검증
보류 설명으로만 남아 있다.

Status: passed

Command:
`git diff --stat`

Result:
7개 파일이 수정된 상태다. 변경 범위는 `.github/workflows/docker-build.yml`,
task, approved fixes, PR draft, devlog draft, review artifact, verification 문서다.

Status: passed

Command:
`CodeRabbit final review`

Result:
자동 실행하지 않았다. 사용자 지시에서 CodeRabbit 자동 실행을 금지했다. FIX-08~FIX-11
해결 여부와 workflow 권한, manifest update 순서, 문서 범위 최종 확인은 사람이
검토해야 한다.

Status: human-required

Command:
`sed -n '1,240p' AGENTS.md`

Result:
WIP 1, 금지 명령, task/verification source of truth, Kubernetes/production
작업의 사람 통제 원칙을 확인했다.

Status: passed

Command:
`sed -n '1,620p' docs/tasks/feature-backend-immutable-image-gitops.md`

Result:
Scope, Do not change, Test commands, Acceptance criteria, UNIT 목록을 확인했다.
현재 수행 대상은 UNIT-01 하나로 제한했다.

Status: passed

Command:
`sed -n '1,260p' docs/agent/backend-workflow.md`

Result:
조사, 변경, 문서화, 검증, Verification 기록, checklist 갱신 순서와 WIP 1 원칙을
확인했다.

Status: passed

Command:
`sed -n '1,260p' docs/agent/codex-instructions.md`

Result:
현재 branch와 working tree 확인, scope 준수, Approved Fixes 외 review output
미적용, Python docstring 규칙과 완료 보고 기준을 확인했다.

Status: passed

Command:
`sed -n '1,260p' docs/agent/verification-gates.md`

Result:
Verification status는 전체 허용 검증 완료 전까지 `pending`으로 유지하고, 실제
실행한 command와 skipped/human-required 상태만 기록해야 함을 확인했다.

Status: passed

Command:
`sed -n '1,260p' docs/agent/forbidden-commands.md`

Result:
`git push`, `git merge`, `kubectl apply/delete/patch/edit`, rollout restart,
Helm 변경, Docker push, Supabase 운영 SQL과 Secret 변경을 자동 실행하지 않는
원칙을 확인했다.

Status: passed

Command:
`sed -n '74,125p' docs/agent/task-authoring-guide.md`

Result:
Python 파일을 새로 만들거나 의미 있게 수정할 때 한글 module/class/function/test
docstring을 작성해야 함을 확인했다. UNIT-01에서는 Python 파일을 수정하지 않았다.

Status: passed

Command:
`sed -n '1,220p' docs/ARCHITECTURE.md`

Result:
Backend 운영 구성, scheduled workload 목록, K3s runtime과 Argo CD Manual Sync
설계 문서 위치를 확인했다.

Status: passed

Command:
`sed -n '1,220p' docs/RUNBOOK.md`

Result:
Backend 운영 점검과 Argo CD Manual Sync plan 문서 위치, production 작업은 사람이
실행한다는 원칙을 확인했다.

Status: passed

Command:
`rg --files .github/workflows k8s docs | rg 'argocd|argo|deploy|deployment|cronjob|image|gitops|architecture|runbook'`

Result:
조사 대상 workflow, K8s manifest, Argo CD Application, architecture/runbook 문서
경로를 식별했다.

Status: passed

Command:
`rg -n "docker/build-push-action|github.sha|latest|seocj/news-api|kind: Deployment|kind: CronJob|image:|Application|argocd|Argo" .github/workflows k8s docs/ARCHITECTURE.md docs/RUNBOOK.md`

Result:
`.github/workflows/docker-build.yml`은 `docker/build-push-action@v6`로
`${{ github.sha }}`와 `latest` tag를 발행한다. `k8s/news-api.yaml`과 네 CronJob
manifest는 모두 `seocj/news-api:latest`를 사용한다. Argo CD Application manifest는
`k8s/argocd/news-api-application.yaml`에 있다.

Status: passed

Command:
`sed -n '1,240p' .github/workflows/docker-build.yml`

Result:
Workflow trigger는 `main` push와 `workflow_dispatch`다. Path filter는 `app/**`,
`scripts/**`, `requirements.txt`, `Dockerfile`, workflow 파일이다. Build platform은
`linux/arm64`, tags는 `${{ secrets.DOCKERHUB_USERNAME }}/news-api:${{ github.sha }}`
와 `${{ secrets.DOCKERHUB_USERNAME }}/news-api:latest`다.

Status: passed

Command:
`sed -n '1,240p' k8s/argocd/news-api-application.yaml`

Result:
`news-api` Application source는 `https://github.com/seochanjin/news-lab.git`,
`targetRevision: main`, `path: k8s`, `recurse: false`,
`exclude: cluster-issuer.yaml`이다. Destination은 in-cluster `default` namespace다.
`spec.syncPolicy.automated`는 없다.

Status: passed

Command:
`sed -n '1,620p' docs/architecture/argocd-manual-sync-design.md`

Result:
기존 Argo CD Manual Sync 설계와 현재 baseline을 확인했다. `news-api` 관리 대상은
Backend Deployment, Service, Ingress와 네 CronJob이며 `ClusterIssuer`는 shared
infrastructure 소유로 제외된다.

Status: passed

Command:
`sed -n '1,260p' docs/architecture/k3s-runtime.md`

Result:
Backend K3s manifest 구성, `workload: app` node selector, 현재
`seocj/news-api:latest` image reference와 운영 변경의 사람 통제 원칙을 확인했다.

Status: passed

Command:
`sed -n '1,570p' docs/runbooks/argocd-manual-sync-plan.md`

Result:
Manual Sync 운영 원칙, current manual deployment flow, Application ownership,
고정 tag 전환 계획과 rollback 기준의 기존 runbook 내용을 확인했다.

Status: passed

Command:
`sed -n '1,240p' k8s/news-api.yaml`

Result:
`Deployment/news-api` image는 `seocj/news-api:latest`다. 같은 파일에
`Service/news-api`와 `Ingress/news-api-ingress`가 있다.

Status: passed

Command:
`sed -n '1,180p' k8s/news-rss-collector-cronjob.yaml`

Result:
`CronJob/news-rss-collector` image는 `seocj/news-api:latest`다.

Status: passed

Command:
`sed -n '1,180p' k8s/news-daily-topic-pipeline-cronjob.yaml`

Result:
`CronJob/news-daily-topic-pipeline` image는 `seocj/news-api:latest`다.

Status: passed

Command:
`sed -n '1,180p' k8s/news-three-day-topic-pipeline-cronjob.yaml`

Result:
`CronJob/news-three-day-topic-pipeline` image는 `seocj/news-api:latest`다.

Status: passed

Command:
`sed -n '1,180p' k8s/news-weekly-topic-pipeline-cronjob.yaml`

Result:
`CronJob/news-weekly-topic-pipeline` image는 `seocj/news-api:latest`다.

Status: passed

Command:
`rg -n "peter-evans/create-pull-request|create-pull-request|pull-requests: write|contents: write|GITHUB_TOKEN|permissions:" .github docs k8s`

Result:
현재 repository에는 manifest update PR 생성 workflow, `create-pull-request`,
`contents: write`, `pull-requests: write` 설정이 아직 없다. 후속 UNIT에서 추가가
필요하다.

Status: passed

Command:
`rg -n "kind: Deployment|kind: CronJob|image:" k8s`

Result:
`k8s/news-api.yaml`의 Deployment 1개와 네 CronJob manifest의 image reference를
확인했다. 다섯 workload 모두 `seocj/news-api:latest`다.

Status: passed

Command:
`rg -n "docker/build-push-action|github.sha|latest|seocj/news-api" .github/workflows k8s`

Result:
Workflow에는 `docker/build-push-action@v6`, `${{ github.sha }}`, `latest` tag가
있고, K8s workload manifest에는 `seocj/news-api:latest` 5건이 있다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --stat`

Result:
`docs/tasks/main.md | 2 +-`만 출력됐다. 현재 task 관련 문서는 untracked 상태라
`git diff --stat`에는 포함되지 않는다.

Status: passed

Command:
`git diff --name-only`

Result:
`docs/tasks/main.md`만 출력됐다. 현재 task 관련 문서는 untracked 상태라
`git diff --name-only`에는 포함되지 않는다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. UNIT-01에서 application code, scripts, DB migration, dependency,
compose 파일은 변경하지 않았다.

Status: passed

Command:
`sed -n '1,260p' docs/design/backend-immutable-image-gitops.md`

Result:
새 설계 문서에 UNIT-01 조사 결과, image tag 정책, manifest update PR 방식,
workflow sequencing, 정적 검증, Argo CD 승인 gate, rollback/restore 기준과
UNIT-01에서 변경하지 않는 범위가 기록된 것을 확인했다.

Status: passed

Command:
`sed -n '380,430p' docs/tasks/feature-backend-immutable-image-gitops.md && sed -n '1,260p' docs/verification/feature-backend-immutable-image-gitops.md`

Result:
Task 문서에 UNIT-01 설계 확정 section이 추가됐고 UNIT-01 checklist가 `[x]`로
갱신된 것을 확인했다. Verification 문서에는 UNIT-01 scope와 실제 실행한 조사
명령이 기록되어 있다.

Status: passed

Command:
`git status --short`

Result:
`docs/tasks/main.md`는 작업 전부터 수정된 tracked file로 남아 있다. 현재 task
관련 untracked 파일은 `docs/design/backend-immutable-image-gitops.md`,
`docs/tasks/feature-backend-immutable-image-gitops.md`,
`docs/verification/feature-backend-immutable-image-gitops.md`와 기존 task 관련
review/fix/pr/devlog 문서들이다.

Status: passed

Command:
`sed -n '1,280p' .github/workflows/docker-build.yml`

Result:
UNIT-05 시작 시점의 workflow를 확인했다. `build` job은 `linux/arm64` image를
`seocj/news-api:${{ github.sha }}`와 `latest`로 push하고, `update-manifest` job은
`needs: build`, `github.ref == 'refs/heads/main'`, `contents: write`,
`pull-requests: write`, `peter-evans/create-pull-request@v6` 설정을 유지한다.

Status: passed

Command:
`rg -n '^[[:space:]]*image:[[:space:]]*seocj/news-api:|seocj/news-api:latest|kind: Deployment|kind: CronJob' k8s/*.yaml`

Result:
`Deployment/news-api`와 네 CronJob manifest image가 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 출력됐다.
`seocj/news-api:latest`는 K8s workload manifest에서 출력되지 않았다.

Status: passed

Command:
`git rev-parse HEAD && git status --short`

Result:
현재 branch HEAD는 `5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`이며, K8s workload
manifest에 기록된 image tag와 일치한다. Working tree에는 기존 UNIT-02~UNIT-04
변경 파일과 task 관련 untracked 문서가 남아 있다.

Status: passed

Command:
`command -v docker || true; command -v argocd || true; command -v gh || true`

Result:
`/usr/local/bin/docker`와 `/opt/homebrew/bin/argocd`가 출력됐다. `gh`는 출력되지
않았다.

Status: passed

Command:
`IMAGE_SHA='5cbb040f3efe858c7a898ddae611f00ad1d2aeb5'
docker buildx imagetools inspect "seocj/news-api:${IMAGE_SHA}"`

Result:
`ERROR: failed to do request: Head "https://registry-1.docker.io/v2/seocj/news-api/manifests/5cbb040f3efe858c7a898ddae611f00ad1d2aeb5": dial tcp: lookup registry-1.docker.io: no such host`
가 출력되고 exit code 1로 종료됐다. 현재 로컬 환경에서 Docker Hub registry DNS
조회가 실패해 SHA image 존재와 ARM64 platform을 확인하지 못했다.

Status: failed
Notes: 환경 제약으로 실패한 read-only Docker Hub 조회다. image 발행 검증은
네트워크가 가능한 환경에서 같은 command를 재실행해야 하며, 이 실패 때문에
UNIT-05를 완료 처리하지 않는다.

Command:
`argocd app get news-api --server localhost:8080 --insecure --refresh`

Result:
실행하지 않았다. Task는 사람이 port-forward와 login을 완료한 환경에서 실행하도록
요구하며, 현재 session에는 manifest PR merge 및 Argo CD 접근 준비 결과가 제공되지
않았다.

Status: human-required

Command:
`argocd app diff news-api --server localhost:8080 --insecure`

Result:
실행하지 않았다. manifest PR merge 후 사람이 Argo CD diff를 확인하고 실제 diff가
Deployment와 네 CronJob image tag 변경으로 제한되는지 log를 제공해야 한다.

Status: human-required

Command:
`argocd app sync news-api --server localhost:8080 --insecure`

Result:
실행하지 않았다. Manual Sync는 사람이 승인하고 실행해야 하는 production-impacting
운영 단계다.

Status: human-required

## Human Verification: UNIT-05~UNIT-06

Command summary:
사람이 Docker Hub image, Argo CD diff/Manual Sync, K3s rollout과 production
`/health`를 운영 환경에서 검증하고 결과를 제공했다. Agent는 production command,
`kubectl`, `argocd`, `git push`, `git merge`를 실행하지 않았다.

Result:
Docker Hub image `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`가
존재하며 image platform은 `linux/arm64`다. Image index digest는
`sha256:2024f4e3ff050f63588c316edcf90bcd6533c1047a78a15547666f101dad43d7`다.

Argo CD sync 전 상태는 main revision `7aa3971` 기준 `OutOfSync`였다. Diff 대상은
`Deployment/news-api` 1개와 CronJob 4개였고, diff 내용은 image가 `latest`에서
`seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`로 변경된 내용만
존재했다.

Manual Sync는 성공했다. Sync revision은
`7aa397148a5d1c3d931cd9205553d1cd7f5838dc`다. Deployment rollout은
successfully rolled out 상태였고 Deployment image는
`seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`다.

Pod 2개는 모두 `Running`, `READY=true`, node는 `arm-worker-node`였다. CronJob
4개는 모두 `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1` image를
사용했다. Argo CD 최종 상태는 `Synced`, `Healthy`다. Production health 응답은
`{"status":"ok","service":"news-api","hostname":"news-api-5755fd5b99-kv847"}`다.

UNIT-05와 UNIT-06은 완료로 기록한다. UNIT-07 rollback/restore와 UNIT-08 전체
회귀 검증은 수행하지 않았으므로 pending으로 유지한다. Verification Status도
UNIT-07~UNIT-08 완료 전까지 `pending`으로 유지한다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. UNIT-05 기록 갱신 후에도 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. UNIT-05에서는 application code, scripts, DB migration, dependency,
compose 파일을 수정하지 않았다.

Status: passed

Command:
`rg -n 'UNIT-05|Docker Hub|human-required|registry-1.docker.io|\[ \] UNIT-05|\[x\] UNIT-05' docs/tasks/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
Task와 Verification에 UNIT-05 운영 검증 대기, Docker Hub DNS 실패,
Argo CD/Manual Sync `human-required` 기록이 존재함을 확인했다. Task checklist는
`[ ] UNIT-05`로 남아 있고 `[x] UNIT-05`는 출력되지 않았다.

Status: passed

Command:
`git diff --stat && git status --short`

Result:
Tracked diff에는 `.github/workflows/docker-build.yml`, 작업 전부터 수정되어 있던
`docs/tasks/main.md`, 다섯 K8s workload manifest가 출력됐다. 현재 task 관련
Design, Task, Verification, review/fix/pr/devlog 문서는 untracked 상태로 남아
있다.

Status: passed

Command:
`git diff -- docs/tasks/main.md`

Result:
`docs/tasks/main.md`의 current task link가
`feature-argocd-backend-manual-sync.md`에서
`feature-backend-immutable-image-gitops.md`로 바뀐 상태임을 확인했다. 이 변경은
UNIT-01 작업 중 새로 만든 변경이 아니므로 수정하지 않았다.

Status: passed

Command:
`git ls-files --others --exclude-standard docs/design/backend-immutable-image-gitops.md docs/tasks/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
세 파일 모두 untracked 상태로 확인됐다.

Status: passed

Command:
`rg -n "UNIT-01|Backend Immutable Image|peter-evans/create-pull-request|bot/update-news-api-image|\[x\] UNIT-01|Verification Status|git diff --check|git diff --name-only" docs/design/backend-immutable-image-gitops.md docs/tasks/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
새 설계 문서, task의 UNIT-01 완료 표시, Verification status와 주요 결정 내용이
대상 문서에 존재함을 확인했다.

Status: passed

Command:
`sed -n '1,280p' docs/design/backend-immutable-image-gitops.md`

Result:
UNIT-01 설계 문서와 확정된 image tag 정책, manifest update PR 방식, workflow
sequencing, 정적 검증, Argo CD 승인 gate와 rollback/restore 기준을 확인했다.

Status: passed

Command:
`sed -n '1,260p' .github/workflows/docker-build.yml`

Result:
기존 workflow는 `main` push와 `workflow_dispatch`에서 `linux/arm64` image를
build/push하고, `${{ secrets.DOCKERHUB_USERNAME }}/news-api:${{ github.sha }}`와
`latest` tag를 발행하고 있었다.

Status: passed

Command:
`rg -n "docker/build-push-action|github.sha|latest|seocj/news-api|DOCKERHUB|tags:|platforms:|permissions:" .github/workflows k8s`

Result:
수정 전 조사에서 workflow의 `docker/build-push-action@v6`, `linux/arm64`,
`${{ github.sha }}`, Docker Hub credential 사용과 K8s workload manifest의
`seocj/news-api:latest` 5건을 확인했다.

Status: passed

Command:
`find .github/workflows -maxdepth 1 -type f -print -exec sed -n '1,220p' {} \;`

Result:
현재 repository의 GitHub Actions workflow는 `.github/workflows/docker-build.yml`
하나임을 확인했다.

Status: passed

Command:
`git diff -- .github/workflows/docker-build.yml docs/tasks/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md docs/design/backend-immutable-image-gitops.md`

Result:
UNIT-02 수정 전 기준으로 대상 파일들의 tracked diff는 없었다. Task, Verification,
Design 문서는 untracked 상태라 이 command에는 표시되지 않았다.

Status: passed

Command:
`git ls-files .github/workflows/docker-build.yml docs/design/backend-immutable-image-gitops.md docs/tasks/feature-backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
tracked file로는 `.github/workflows/docker-build.yml`만 출력됐다. Design, Task,
Verification 문서는 untracked 상태임을 재확인했다.

Status: passed

Command:
`rg -n "docker/build-push-action|github.sha|latest|seocj/news-api" .github/workflows k8s`

Result:
수정 후 workflow에는 `IMAGE_NAME: seocj/news-api`,
`docker/build-push-action@v6`, `${{ env.IMAGE_NAME }}:${{ github.sha }}`와
`${{ env.IMAGE_NAME }}:latest`가 있다. K8s workload manifest의
`seocj/news-api:latest` 5건은 UNIT-04 범위라 아직 남아 있다.

Status: passed

Command:
`rg -n "github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch|permissions:|IMAGE_NAME|GITHUB_SHA" .github/workflows`

Result:
수정 후 workflow에는 `workflow_dispatch`, `permissions:`, `IMAGE_NAME:
seocj/news-api`, `GITHUB_SHA` 40자리 검증, `docker/build-push-action@v6`,
`${{ env.IMAGE_NAME }}:${{ github.sha }}`가 있다. `pull-requests: write`,
`contents: write`, `create-pull-request`, `workflow_run`은 아직 없으며 UNIT-03
범위다.

Status: passed

Command:
`git diff -- .github/workflows/docker-build.yml`

Result:
Workflow에 `permissions: contents: read`, `env.IMAGE_NAME: seocj/news-api`,
`GITHUB_SHA` 40자리 lowercase hexadecimal 검증 step이 추가됐고, build/push tag가
`${{ env.IMAGE_NAME }}:${{ github.sha }}`와 `${{ env.IMAGE_NAME }}:latest`로
변경됐다.

Status: passed

Command:
`command -v actionlint && actionlint`

Result:
출력 없이 exit code 1로 종료됐다. `actionlint` 실행 파일이 현재 환경에 없어
lint를 실행하지 못했다.

Status: skipped

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --stat`

Result:
Tracked diff 기준 `.github/workflows/docker-build.yml`과 `docs/tasks/main.md`가
출력됐다. 현재 task 관련 Design, Task, Verification 문서는 untracked 상태라
`git diff --stat`에는 포함되지 않는다.

Status: passed

Command:
`git diff --name-only`

Result:
Tracked diff 기준 `.github/workflows/docker-build.yml`과 `docs/tasks/main.md`가
출력됐다. `docs/tasks/main.md`는 작업 전부터 수정된 파일이며 이번 UNIT에서
수정하지 않았다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. Application code, scripts, DB migration, dependency, compose 파일은
수정하지 않았다.

Status: passed

Command:
`git status --short`

Result:
`.github/workflows/docker-build.yml`이 수정됐다. `docs/tasks/main.md`는 작업
전부터 수정된 tracked file로 남아 있다. 현재 task 관련 Design, Task,
Verification, review/fix/pr/devlog 문서는 untracked 상태로 남아 있다.

Status: passed

Command:
`rg -n "UNIT-02|\[x\] UNIT-02|IMAGE_NAME: seocj/news-api|GITHUB_SHA|contents: read|seocj/news-api:[0-9a-f]{40}|Verification Status|Pending Verification|actionlint" docs/tasks/feature-backend-immutable-image-gitops.md docs/design/backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md .github/workflows/docker-build.yml`

Result:
Task, Design, Verification과 workflow에서 UNIT-02 구현 결과, `[x] UNIT-02`,
`contents: read`, `IMAGE_NAME: seocj/news-api`, `GITHUB_SHA` 검증, `actionlint`
미실행 기록과 pending verification section을 확인했다.

Status: passed

Command:
`git diff -- .github/workflows/docker-build.yml`

Result:
최종 workflow diff는 `permissions: contents: read`, `IMAGE_NAME: seocj/news-api`,
`Verify immutable image tag source` step 추가와 build/push tag를
`${{ env.IMAGE_NAME }}:${{ github.sha }}`, `${{ env.IMAGE_NAME }}:latest`로 바꾼
내용으로 제한된다.

Status: passed

Command:
`sed -n '400,470p' docs/tasks/feature-backend-immutable-image-gitops.md && sed -n '1,70p' docs/verification/feature-backend-immutable-image-gitops.md`

Result:
Task 문서에 UNIT-02 workflow 구현 section과 `[x] UNIT-02` checklist가 있고,
Verification scope가 UNIT-01~UNIT-02로 갱신됐으며 전체 status는 후속 운영 검증이
남아 `pending`으로 유지됨을 확인했다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. 최종 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git status --short`

Result:
최종 상태에서 `.github/workflows/docker-build.yml`이 수정됐다. `docs/tasks/main.md`
는 작업 전부터 수정된 tracked file로 남아 있다. 현재 task 관련 Design, Task,
Verification, review/fix/pr/devlog 문서는 untracked 상태로 남아 있다.

Status: passed

Command:
`git diff -- .github/workflows/docker-build.yml`

Result:
UNIT-03 시작 시점의 workflow diff를 확인했다. 기존 UNIT-02 변경으로
`permissions: contents: read`, `IMAGE_NAME: seocj/news-api`, `GITHUB_SHA` 검증과
`${{ env.IMAGE_NAME }}:${{ github.sha }}` tag 발행이 추가된 상태였다.

Status: passed

Command:
`sed -n '1,260p' .github/workflows/docker-build.yml`

Result:
기존 workflow는 `build` job 하나만 있고 manifest update branch/PR 생성 job은
아직 없음을 확인했다.

Status: passed

Command:
`sed -n '1,260p' docs/design/backend-immutable-image-gitops.md`

Result:
UNIT-01 설계에서 manifest update는 image build 성공 이후 같은 workflow의 별도
job으로 실행하고, `peter-evans/create-pull-request`와 `GITHUB_TOKEN`, job-level
`contents: write`, `pull-requests: write`를 사용하는 것으로 확정되어 있음을
확인했다.

Status: passed

Command:
`rg -n "UNIT-03|create-pull-request|manifest update|manifest" docs/design docs/tasks docs/verification .github/workflows k8s`

Result:
UNIT-03 구현 전 repository에는 manifest update PR 생성 workflow가 없고, task와
design 문서에 UNIT-03 요구사항과 구현 방향이 기록되어 있음을 확인했다.

Status: passed

Command:
`ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`

Result:
`workflow yaml ok`가 출력되었고 exit code 0으로 통과했다.

Status: passed

Command:
`rg -n 'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch|needs: build|bot/update-news-api-image' .github/workflows`

Result:
`.github/workflows/docker-build.yml`에서 `workflow_dispatch`, `docker/build-push-action@v6`,
`${{ github.sha }}`, `needs: build`, `contents: write`, `pull-requests: write`,
`peter-evans/create-pull-request@v6`, `bot/update-news-api-image-${{ github.sha }}`
설정을 확인했다.

Status: passed

Command:
`command -v actionlint && actionlint`

Result:
출력 없이 exit code 1로 종료됐다. `actionlint` 실행 파일이 설치되어 있지 않아
workflow lint는 수행하지 못했다.

Status: skipped

Command:
`ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`

Result:
최종 workflow 변경 후 `workflow yaml ok`가 출력되었고 exit code 0으로 통과했다.

Status: passed

Command:
`rg -n 'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch|needs: build|github\.ref ==|bot/update-news-api-image' .github/workflows`

Result:
최종 workflow에서 `workflow_dispatch`, `docker/build-push-action@v6`, full
`${{ github.sha }}` image tag, `needs: build`, manifest update job의
`github.ref == 'refs/heads/main'` guard, `contents: write`, `pull-requests: write`,
`peter-evans/create-pull-request@v6`, `bot/update-news-api-image-${{ github.sha }}`
branch 설정을 확인했다.

Status: passed

Command:
`if command -v actionlint >/dev/null 2>&1; then actionlint; else echo 'actionlint not installed'; exit 127; fi`

Result:
`actionlint not installed`가 출력되고 exit code 127로 종료됐다. 현재 환경에
`actionlint`가 없어 workflow lint는 수행하지 못했다.

Status: skipped

Command:
`git diff --check`

Result:
출력 없음. 최종 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. Application code, scripts, DB migration, dependency, compose 파일은
수정하지 않았다.

Status: passed

Command:
`git diff --stat && git diff --name-only && git status --short`

Result:
Tracked diff에는 `.github/workflows/docker-build.yml`과 작업 전부터 수정되어 있던
`docs/tasks/main.md`가 출력됐다. `git status --short` 기준 현재 task 관련 Design,
Task, Verification, review/fix/pr/devlog 문서는 untracked 상태이며,
`.github/workflows/docker-build.yml`이 수정된 상태다.

Status: passed

Command:
`ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`

Result:
최종 문서 보정 후에도 `workflow yaml ok`가 출력되었고 exit code 0으로 통과했다.

Status: passed

Command:
`rg -n 'UNIT-03|\[x\] UNIT-03|update-manifest|github\.ref ==|needs: build|create-pull-request|Verification Status|Pending Verification|actionlint' docs/tasks/feature-backend-immutable-image-gitops.md docs/design/backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md .github/workflows/docker-build.yml`

Result:
Workflow, Design, Task, Verification에서 UNIT-03 구현 결과, `[x] UNIT-03`,
`update-manifest`, `needs: build`, `github.ref == 'refs/heads/main'`,
`create-pull-request`, `Verification Status`, `Pending Verification`, `actionlint`
기록을 확인했다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. 최종 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. Application code, scripts, DB migration, dependency, compose 파일은
수정하지 않았다.

Status: passed

Command:
`git diff --stat && git diff --name-only && git status --short`

Result:
Tracked diff에는 `.github/workflows/docker-build.yml`과 작업 전부터 수정되어 있던
`docs/tasks/main.md`가 출력됐다. `git status --short` 기준 현재 task 관련 Design,
Task, Verification, review/fix/pr/devlog 문서는 untracked 상태이며,
`.github/workflows/docker-build.yml`이 수정된 상태다.

Status: passed

Command:
`git rev-parse HEAD`

Result:
현재 branch HEAD는 `5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`다. UNIT-04의
manifest image tag 기준 SHA로 사용했다.

Status: passed

Command:
`rg -n "docker/build-push-action|github.sha|latest|seocj/news-api" .github/workflows k8s`

Result:
Workflow에는 `docker/build-push-action@v6`, `${{ github.sha }}`,
`seocj/news-api:${{ github.sha }}`와 보조 `latest` tag가 남아 있다. K8s
workload manifest 다섯 파일은 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`를 사용한다.

Status: passed

Command:
`rg -n "kind: Deployment|kind: CronJob|image:" k8s`

Result:
`Deployment/news-api` 1개와 `CronJob` 4개의 image가 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 출력됐다.

Status: passed

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`

Result:
Branch는 `feature/backend-immutable-image-gitops`다. Tracked diff에는
`.github/workflows/docker-build.yml`, 작업 전부터 수정되어 있던
`docs/tasks/main.md`, 다섯 K8s workload manifest가 포함된다. 현재 task 관련
Design, Task, Verification, review/fix/pr/devlog 문서는 untracked 상태다.

Status: passed

Command:
`rg -n 'seocj/news-api:latest|image:[[:space:]]*.*news-api:latest' k8s`

Result:
출력 없음. K8s workload manifest에서 `seocj/news-api:latest`가 제거됐다.

Status: passed

Command:
`rg -n '^[[:space:]]*image:[[:space:]]*seocj/news-api:' k8s/*.yaml`

Result:
다섯 workload image가 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 출력됐다.

Status: passed

Command:
`ruby -e 'require "yaml"; Dir["k8s/*.yaml"].sort.each do |path| YAML.load_stream(File.read(path)); puts "ok #{path}"; end'`

Result:
`k8s/cluster-issuer.yaml`, `k8s/news-api.yaml`과 네 CronJob manifest가 모두
`ok`로 출력되어 YAML syntax 검증을 통과했다.

Status: passed

Command summary:
K8s YAML을 읽어 Deployment 1개와 CronJob 4개의 image가 동일한
40자리 Git SHA를 사용하는지 검사한 historical assertion.

Result:
`Deployment/news-api`, `CronJob/news-daily-topic-pipeline`,
`CronJob/news-rss-collector`, `CronJob/news-three-day-topic-pipeline`,
`CronJob/news-weekly-topic-pipeline`이 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`를 사용한다고 출력됐고,
`immutable image assertions passed`가 출력됐다.

Status: not-recorded

Command:
`rg -n 'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch' .github/workflows`

Result:
Workflow에서 `workflow_dispatch`, `docker/build-push-action@v6`,
`${{ github.sha }}`, `contents: write`, `pull-requests: write`,
`peter-evans/create-pull-request@v6`,
`bot/update-news-api-image-${{ github.sha }}` 설정을 확인했다.

Status: passed

Command:
`if command -v actionlint >/dev/null 2>&1; then actionlint; else echo 'actionlint not installed'; exit 127; fi`

Result:
`actionlint not installed`가 출력되고 exit code 127로 종료됐다. 현재 환경에
`actionlint`가 없어 workflow lint는 수행하지 못했다.

Status: skipped

Command:
`git diff --check`

Result:
출력 없음. 현재 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. Application code, scripts, DB migration, dependency, compose 파일은
수정하지 않았다.

Status: passed

Command:
`rg -n 'needs: build|github\.ref ==|permissions:|contents: read|contents: write|pull-requests: write|create-pull-request|bot/update-news-api-image|GITHUB_SHA|IMAGE_NAME|docker/build-push-action|workflow_dispatch' .github/workflows/docker-build.yml`

Result:
Workflow에서 `contents: read`, `IMAGE_NAME: seocj/news-api`, `GITHUB_SHA` 40자리
검증, `docker/build-push-action@v6`, `needs: build`,
`github.ref == 'refs/heads/main'`, `contents: write`, `pull-requests: write`,
`peter-evans/create-pull-request@v6`와
`bot/update-news-api-image-${{ github.sha }}` branch 설정을 확인했다.

Status: passed

Command:
`ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`

Result:
`workflow yaml ok`가 출력되었고 exit code 0으로 통과했다.

Status: passed

Command:
`rg -n 'UNIT-04|\[x\] UNIT-04|5cbb040f3efe858c7a898ddae611f00ad1d2aeb5|latest|actionlint|Pending Verification' docs/tasks/feature-backend-immutable-image-gitops.md docs/design/backend-immutable-image-gitops.md docs/verification/feature-backend-immutable-image-gitops.md k8s .github/workflows/docker-build.yml`

Result:
Task, Design, Verification, K8s manifest와 workflow에서 UNIT-04 기록,
`[x] UNIT-04`, 기준 SHA, `actionlint` skipped 기록과 Pending Verification section을
확인했다. `latest`는 과거 baseline 기록, task 문구와 workflow 보조 tag에는 남아
있지만 K8s workload manifest image에는 남아 있지 않음을 같은 최종 확인에서
분리해 검증했다.

Status: passed

Command:
`rg -n 'seocj/news-api:latest|image:[[:space:]]*.*news-api:latest' k8s`

Result:
출력 없음. 최종 확인에서도 K8s workload manifest에 `latest` image reference가
없다.

Status: passed

Command summary:
K8s YAML을 읽어 Deployment 1개와 CronJob 4개의 image가 동일한
40자리 Git SHA를 사용하는지 검사한 historical assertion.

Result:
다섯 workload image가 모두
`seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 출력됐고,
`immutable image assertions passed`가 출력됐다.

Status: not-recorded

Command:
`git diff --check`

Result:
출력 없음. 최종 tracked diff 기준 whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db requirements.txt docker-compose.yml`

Result:
출력 없음. 최종 확인에서도 application code, scripts, DB migration, dependency,
compose 파일은 수정하지 않았다.

Status: passed

Command:
`git diff --stat && git diff --name-only && git status --short`

Result:
Tracked diff에는 `.github/workflows/docker-build.yml`, 작업 전부터 수정되어 있던
`docs/tasks/main.md`, 다섯 K8s workload manifest가 출력됐다. `git status --short`
기준 현재 task 관련 Design, Task, Verification, review/fix/pr/devlog 문서는
untracked 상태로 남아 있다.

Status: passed

Command:
`git diff --check`

Result:
Verification 기록 갱신 후 최종 확인에서도 출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git status --short`

Result:
`.github/workflows/docker-build.yml`, 작업 전부터 수정되어 있던 `docs/tasks/main.md`,
다섯 K8s workload manifest가 modified 상태다. 현재 task 관련 Design, Task,
Verification, review/fix/pr/devlog 문서는 untracked 상태로 남아 있다.

Status: passed

## Results

UNIT-01 조사와 설계 확정, UNIT-02 full Git SHA image build/push workflow 구현,
UNIT-03 manifest update branch/PR 생성 workflow 구현, UNIT-04 immutable K8s
workload manifest 전환과 정적 검증을
완료했다.

- 설계 문서 `docs/design/backend-immutable-image-gitops.md`를 추가했다.
- Backend workflow는 이미 full `${{ github.sha }}` image tag를 발행하지만, 운영
  manifest는 아직 `latest`를 사용한다는 baseline을 기록했다.
- `news-api` Argo CD Application의 source, exclude, Manual Sync 정책과 resource
  ownership 범위를 기록했다.
- 후속 구현 방식으로 image build 성공 이후 별도 manifest update branch/PR 생성,
  `peter-evans/create-pull-request`, 동일 SHA branch 재사용, job-level 최소
  permission을 확정했다.
- 이전 정상 SHA 선정과 rollback/restore 기준을 문서화했다.
- `.github/workflows/docker-build.yml`에 `permissions: contents: read`를 명시했다.
- Docker Hub 대상 image repository를 `seocj/news-api`로 고정했다.
- Build 전에 `GITHUB_SHA`가 full 40자리 lowercase Git SHA인지 검증하도록 했다.
- `docker/build-push-action@v6`가 `linux/arm64` image를
  `seocj/news-api:${{ github.sha }}`로 push하고, `latest`는 보조 tag로 유지한다.
- `.github/workflows/docker-build.yml`에 `update-manifest` job을 추가했다.
- `update-manifest`는 `needs: build`로 build 성공 이후에만 실행되며,
  `main` branch context에서만 manifest PR을 만든다.
- `update-manifest` job에만 `contents: write`, `pull-requests: write` 권한을
  부여했다.
- Manifest update script는 다섯 Backend workload manifest image를 같은
  `seocj/news-api:${{ github.sha }}` 값으로 갱신하고, 같은 job에서 다섯 image 수,
  tag 일치, full SHA 형식과 workflow SHA 일치를 검증한다.
- `peter-evans/create-pull-request@v6`가
  `bot/update-news-api-image-${{ github.sha }}` branch와 `main` 대상 PR을 생성한다.
- `Deployment/news-api`와 네 CronJob image를 모두
  `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 전환했다.
- K8s workload manifest에서 `seocj/news-api:latest`가 제거됐고, 다섯 workload가
  같은 40자리 lowercase Git SHA tag를 사용함을 정적 검증했다.

## Manual or Production Verification

수행하지 않음. UNIT-01~UNIT-04는 production-impacting command가 필요 없는 조사,
문서화, GitHub Actions workflow 정적 변경과 K8s manifest 정적 변경 작업이다.
Docker Hub image 조회, manifest PR merge, Argo CD refresh/diff/Sync, K3s rollout,
production `/health`, controlled rollback/restore는 후속 UNIT 또는 사람이 수행할
검증으로 남겼다.

## Pending Verification

- UNIT-05: Docker Hub SHA image 존재와 ARM64 platform 확인, manifest PR merge 후
  Argo CD OutOfSync/diff 확인
- UNIT-06: Manual Sync 이후 rollout, Pod/CronJob image, Service, Ingress,
  production `/health` 확인
- UNIT-07: 이전 정상 SHA rollback과 최신 SHA restore 실제 검증
- UNIT-08: 전체 회귀 검증, Architecture/Runbook/Verification/README 판단,
  PR/devlog 정리와 re-review

## Evidence Notes

UNIT-01~UNIT-04에서 Python 파일은 수정하지 않았다. Application code, scripts,
DB migration, requirements, Secret, kubeconfig, credential 값도 수정하지 않았다.
GitHub Actions workflow는 UNIT-02~UNIT-03 범위에서 수정했고, K8s workload
manifest image reference는 UNIT-04 범위에서 수정했다.

## Approved Fixes Verification

Command:
`sed -n '1,260p' docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
Approved Fixes가 Antigravity review artifact의 경로, 표현, PR 단계 설명 보정으로
제한돼 있음을 확인했다. 적용 승인 source of truth는 FIX-01~FIX-05뿐이며,
구현 코드 추가 수정은 rejected/deferred로 기록돼 있다.

Status: passed

Command:
`sed -n '1,260p' docs/prompts/codex-implement.md`

Result:
호환용 보조 문서의 구현 규칙, approved fixes 적용 규칙, verification 기록 원칙과
금지 명령을 확인했다.

Status: passed

Command:
`sed -n '1,260p' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
Antigravity review artifact에서 잘못된 상대 링크, `5개 파드` 표현, 절대적 보안
표현, main merge 전 운영 검증 완료 요구로 읽히는 문구, 범위가 넓은 Verdict
표현을 확인했다.

Status: passed

Command:
`rg -n '\.\./docs/' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. `../docs/...` 형태의 잘못된 링크가 제거됐다.

Status: passed

Command:
`rg -n '\.\./tasks/|\.\./design/|\.\./verification/|\.\./\.\./k8s/|\.\./\.\./\.github/' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
`../tasks/`, `../design/`, `../verification/`, `../../k8s/`, `../../.github/` 링크만
출력됐다. 모두 `docs/reviews/` 기준 실제 repository 위치와 일치한다.

Status: passed

Command:
`rg -n '5개 파드|다섯 파드|Pod 5개' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. 실제 Pod 실행 상태를 검증한 것처럼 읽히는 대상 표현을 제거했다.

Status: passed

Command:
`rg -n '완벽하게 배제|완전히 제거|리스크가 없다' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. 보안 효과의 절대적 표현을 제거했다.

Status: passed

Command:
`rg -n 'bootstrap|UNIT-01~UNIT-04|UNIT-05~UNIT-08|PASS.*UNIT-01|pending|전체 Task' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
bootstrap PR merge 이후 `main SHA image build/push`, manifest image 갱신 bot PR,
Argo CD OutOfSync/diff, Manual Sync와 rollout, rollback/restore, 최종 문서 및
re-review 순서가 출력됐다. Verdict는 `PASS — UNIT-01~UNIT-04`로 한정돼 있고,
전체 Task는 UNIT-05~UNIT-08 완료 전까지 `pending`이라고 기록돼 있다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- .github/workflows k8s app scripts db`

Result:
`.github/workflows/docker-build.yml`과 다섯 K8s workload manifest가 출력됐다.
이 파일들은 이번 approved fix 적용 전 `git status --short --branch`에서 이미
modified 상태였던 UNIT-02~UNIT-04 선행 변경이다. 이번 approved fix에서는
workflow, K8s manifest, application code, scripts와 DB 파일을 새로 수정하지
않았다. `app`, `scripts`, `db` 경로 출력은 없다.

Status: passed

Command:
```bash
rg -n 'PR 블로커|bootstrap PR|전체 Task|UNIT-05~UNIT-08|완료|passed|Status를 `passed`' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

Result:
`PR 블로커: 없음`이 유지돼 있고, review artifact는 bootstrap PR 제출 가능 여부와
전체 Task 완료 여부를 구분한다. UNIT-05~UNIT-08은 bootstrap 이후 수행 대상으로
남아 있으며, 실행하지 않은 운영 검증을 완료로 주장하지 않는다.

Status: passed

Command:
`git status --short --branch`

Result:
현재 branch는 `feature/backend-immutable-image-gitops`다. 선행 UNIT 변경인
workflow와 K8s manifest, `docs/tasks/main.md`는 modified 상태이며, 현재 task
관련 Design, Task, Verification, review/fix/pr/devlog 문서는 untracked 상태다.

Status: passed

Command:
`git diff --check`

Result:
Approved Fixes verification 기록 갱신 후 최종 확인에서도 출력 없음. Whitespace
error가 없다.

Status: passed

Command:
`rg -n '\.\./docs/|5개 파드|다섯 파드|Pod 5개|완벽하게 배제|완전히 제거|리스크가 없다' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. Review artifact에는 잘못된 상대 링크, 잘못된 검증 대상 표현, 절대적
보안 표현이 남아 있지 않다.

Status: passed

Command:
`rg -n 'PASS — UNIT-01~UNIT-04|bootstrap PR merge|전체 Task|UNIT-05~UNIT-08|PR 블로커' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
`PR 블로커: 없음`, bootstrap PR merge 이후 운영 검증 순서, `PASS —
UNIT-01~UNIT-04`, 전체 Task `pending` 문구가 출력됐다.

Status: passed

## Approved Fixes Verification 2

Command:
`git status --short --branch`

Result:
현재 branch는 `feature/backend-immutable-image-gitops`다. 선행 UNIT 변경인
workflow와 K8s manifest, `docs/tasks/main.md`는 modified 상태이며, 현재 task
관련 Design, Task, Verification, review/fix/pr/devlog 문서는 untracked 상태다.

Status: passed

Command:
`sed -n '1,260p' docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
Approved Fixes에서 FIX-06과 FIX-07이 미완료 상태로 추가돼 있음을 확인했다. 이번
작업의 승인 source of truth는 FIX-06~FIX-07이며, 구현 코드 추가 수정과
Antigravity harness 실행 방식 변경은 rejected/deferred로 기록돼 있다.

Status: passed

Command:
`rg -n -e 'f[i]le://' -e '/U[s]ers/' -e '/h[o]me/' -e '[A-Za-z]:\\\\' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. Review artifact의 local absolute path와 local URI가 제거됐다.

Status: passed

Command:
`rg -n '\.\./tasks/|\.\./design/|\.\./verification/|\.\./fixes/|\.\./\.\./k8s/|\.\./\.\./\.github/' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
`../tasks/`, `../design/`, `../verification/`, `../fixes/`, `../../k8s/`,
`../../.github/` 링크가 출력됐다. 모두 `docs/reviews/` 기준 repository-relative
경로다.

Status: passed

Command:
`rg -n 'Antigravity|review action|review artifact|repository-relative|local URI' docs/agent docs/prompts scripts`

Result:
Antigravity review 관련 instruction과 prompt source 후보를 확인했다. 실제 공통
instruction source로 review instruction 문서를 선택했다. 이 문서에
review artifact의 local URI, 사용자 홈 경로, absolute filesystem path 기록 금지와
repository-relative Markdown/plain path 규칙을 추가했다.

Status: passed

Command:
`rg -n 'local URI|사용자 홈|absolute filesystem path|repository-relative Markdown link|repository-relative plain path' docs/agent/antigravity-review.md`

Result:
review instruction 문서에 local URI 금지, 사용자 홈 경로와 absolute
filesystem path 금지, repository-relative Markdown link 사용, 확정할 수 없는
경로의 repository-relative plain path 사용 규칙이 출력됐다.

Status: passed

Command:
`rg -n 'Approved Fixes Verification|FIX-01|FIX-06|FIX-07|추가된 수정 요구 사항이 없|적용 대상 아님' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
Re-review 1의 `Approved Fixes Verification`이 FIX-01~FIX-07 존재와 적용 상태를
기록한다. `추가된 수정 요구 사항이 없`과 `적용 대상 아님` 문구는 출력되지
않았다. 구현 코드 필수 수정 없음과 review artifact 보정 항목 존재를 구분했다.

Status: passed

Command:
`rg -n '5개 파드|다섯 파드|Pod 5개' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. 잘못된 검증 대상 표현이 없다.

Status: passed

Command:
`rg -n '완벽하게 배제|완전히 제거|리스크가 없다|완벽히 조율' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. 절대적 보안 표현과 과장 표현이 없다.

Status: passed

Command:
`rg -n 'bootstrap|UNIT-01~UNIT-04|UNIT-05~UNIT-08|PASS.*UNIT-01|pending|전체 Task' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
bootstrap PR merge 이후 운영 검증 순서, `PASS — UNIT-01~UNIT-04`, 전체 Task
`pending`, UNIT-05~UNIT-08 후속 수행 문구가 출력됐다.

Status: passed

Command:
`git diff --check`

Result:
출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- .github/workflows k8s app scripts db`

Result:
`.github/workflows/docker-build.yml`과 다섯 K8s workload manifest가 출력됐다.
이 파일들은 이번 approved fix 적용 전부터 modified 상태였던 UNIT-02~UNIT-04
선행 변경이다. 이번 FIX-06~FIX-07 적용으로 `app`, `scripts`, `db` 경로에는 신규
변경이 생기지 않았다.

Status: passed

Command:
`git diff -- scripts/agent_workflow/review_prompt.py`

Result:
출력 없음. 공통 instruction 보정은 `scripts/`가 아니라
review instruction 문서에만 적용했다.

Status: passed

Command summary:
Antigravity re-review command was intentionally not executed in this step.

Result:
실행하지 않았다. 사용자 지시에서 Codex, Gemini/Antigravity, GitHub, CodeRabbit을
자동 실행하지 말라고 명시했으므로 Re-review 재실행은 사람이 수행해야 한다.

Status: skipped

Command:
`rg -n '\[ \] \*\*FIX-|FIX-06|FIX-07|Applied Changes' docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`

Result:
미완료 FIX checkbox는 출력되지 않았다. FIX-06과 FIX-07은 `[x]` 상태이며,
Applied Changes에는 실제 수정 파일과 적용 내역이 기록돼 있다.

Status: passed

Command:
`git diff --check`

Result:
최종 확인에서도 출력 없음. Whitespace error가 없다.

Status: passed

Command:
`git diff --name-only -- app scripts db`

Result:
출력 없음. 이번 FIX-06~FIX-07 적용으로 application code, scripts, DB 파일은
수정하지 않았다.

Status: passed

Command:
`rg -n -e 'f[i]le://' -e '/U[s]ers/' -e '/h[o]me/' -e '[A-Za-z]:\\\\' -e '추가된 수정 요구 사항이 없' -e '적용 대상 아님' -e '완벽히 조율' docs/reviews/feature-backend-immutable-image-gitops-antigravity.md`

Result:
출력 없음. Review artifact에 local URI/absolute path, 잘못된 Approved Fixes
부재 주장, 과장 표현이 남아 있지 않다.

Status: passed

Command:
`git status --short --branch`

Result:
현재 branch는 `feature/backend-immutable-image-gitops`다. 이번 FIX-06~FIX-07로
review instruction 문서, review/fixes/verification 문서를 수정했다.
선행 UNIT 변경인 workflow와 K8s manifest, `docs/tasks/main.md`는 modified 상태로
남아 있다.

Status: passed
