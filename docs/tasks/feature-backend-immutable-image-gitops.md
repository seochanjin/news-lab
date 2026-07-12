# Task: Backend immutable image 기반 GitOps 배포 파이프라인 완성

## Goal

Backend `news-api`의 운영 image를 `latest`에서 immutable full Git SHA tag로 전환하고, GitHub Actions가 새 image를 build/push한 뒤 Kubernetes manifest의 image tag 갱신 PR을 생성하도록 구성한다.

최종적으로 다음 승인형 GitOps 배포 흐름을 완성한다.

```
애플리케이션 코드 PR merge
→ GitHub Actions가 full Git SHA image build/push
→ manifest image tag 갱신 branch/PR 생성
→ 사람이 manifest diff 검토 후 merge
→ Argo CD가 OutOfSync 감지
→ 사람이 Argo CD diff 검토
→ 사람이 Manual Sync 승인
→ rollout, workload와 API 상태 확인
→ 필요 시 이전 SHA로 controlled rollback
```

이번 Task의 핵심 완료 기준은 Git commit, Docker image와 K3s에서 실행 중인 Backend workload image를 하나의 full Git SHA로 추적할 수 있게 만드는 것이다.

## Scope

- Backend Docker image를 full Git SHA tag로 build하고 Docker Hub에 push한다.
- 기존 `latest` tag 발행은 호환 목적의 보조 tag로 유지할 수 있지만 K3s workload에서는 사용하지 않는다.
- Backend Deployment와 네 CronJob의 image reference를 동일한 immutable SHA tag로 통일한다.
- GitHub Actions가 image build 성공 이후 Kubernetes manifest의 image tag를 갱신하는 별도 branch를 만들고 PR을 생성하도록 구성한다.
- manifest 갱신은 직접 `main`에 commit하지 않고 사람이 검토 가능한 PR 방식으로 제한한다.
- 같은 SHA가 Deployment와 모든 CronJob에 반영되는지 정적 검증한다.
- image tag 갱신 PR merge 이후 Argo CD `news-api` Application의 `OutOfSync`와 diff를 확인한다.
- 사람이 Manual Sync를 실행한 뒤 Backend rollout, Pod image, Service, Ingress, CronJob과 production `/health`를 확인한다.
- 이전 정상 SHA를 manifest에 반영해 controlled rollback을 수행하고, 정상 상태 확인 후 최신 SHA로 다시 복원한다.
- rollback과 restore 과정에서 사용한 명령, 실제 output, 승인 지점과 실패 대응 절차를 Verification과 Runbook에 기록한다.
- Architecture 문서에 immutable image와 manifest PR 기반 배포 흐름을 반영한다.
- 최종 운영 흐름이 확정되면 README 업데이트 필요성을 판단하고, 반영하지 않을 경우 근거를 문서화한다.

## Do not change

- Backend application business logic
- FastAPI endpoint 동작과 API response schema
- database schema, migration, Supabase SQL
- RSS 수집, 본문 추출, Topic pipeline과 summary logic
- Frontend repository와 Frontend Argo CD Application
- `ClusterIssuer/letsencrypt-prod` ownership
- Argo CD의 Manual Sync 정책
- automated sync, automatic prune, automatic self-heal
- Argo CD public Ingress, SSO, HA와 external Redis 구성
- Kubernetes Service, Ingress, selector, port, probe와 resource request/limit 값
- CronJob schedule, command, suspend와 concurrency policy
- production Secret 값
- image signing, SBOM, provenance attestation와 digest pinning
- 사람이 승인해야 하는 다음 작업의 자동 실행
  - PR merge
  - `kubectl apply/delete/patch/rollout`
  - Argo CD Sync
  - DB migration
  - Secret 변경
  - production rollback/restore

## Expected files

작업 중 실제 repository 구조를 확인한 뒤 최소 범위로 수정한다.

예상 수정 파일:

```
.github/workflows/*
k8s/*deployment*.yaml
k8s/*cronjob*.yaml
```

예상 문서 파일:

```
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/design/backend-immutable-image-gitops.md
docs/tasks/feature-backend-immutable-image-gitops.md
docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
docs/reviews/feature-backend-immutable-image-gitops-coderabbit.md
docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md
docs/verification/feature-backend-immutable-image-gitops.md
docs/pr/feature-backend-immutable-image-gitops.md
docs/devlog/feature-backend-immutable-image-gitops.md
README.md
```

실제 workflow와 manifest filename이 다르면 기존 파일명을 우선 사용한다. 같은 목적의 workflow를 불필요하게 중복 생성하지 않는다.

구현 전에 다음 항목을 조사한다.

- 현재 Backend image build/push workflow의 trigger, architecture, tag 정책
- Docker Hub repository와 현재 SHA tag 발행 여부
- Deployment와 네 CronJob의 실제 manifest 경로
- 모든 Backend workload가 사용하는 image reference
- Argo CD `news-api` Application이 관리하는 정확한 resource 범위
- GitHub Actions에서 manifest 갱신 PR을 만들 때 사용할 인증 방식과 최소 권한
- workflow 재실행 시 동일 SHA PR의 중복 생성 방지 방법
- manifest update PR과 application code PR 사이의 commit 추적 방법
- 이전 정상 SHA 선정 기준과 rollback/restore 절차

## DB changes

없음.

- table, column, index, constraint 변경 없음
- migration file 추가 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음

## API changes

없음.

- 신규 endpoint 없음
- 기존 endpoint path 변경 없음
- request/response schema 변경 없음
- 인증과 권한 정책 변경 없음
- production 회귀 확인은 `/health`를 기준으로 한다.

## Test commands

### 현재 구조 조사

```bash
rg -n \
  "docker/build-push-action|github.sha|latest|seocj/news-api" \
  .github/workflows k8s
```

```bash
rg -n \
  "kind: Deployment|kind: CronJob|image:" \
  k8s
```

### 변경 범위 확인

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

### K3s workload의 `latest` 제거 확인

```bash
rg -n \
  'seocj/news-api:latest|image:\s*.*news-api:latest' \
  k8s
```

완료 시 Backend Deployment와 네 CronJob manifest에서는 결과가 없어야 한다.

### Backend workload image 일치 확인

실제 manifest 경로를 조사한 뒤 해당 경로를 사용한다.

```bash
rg -n '^\s*image:\s*seocj/news-api:' k8s/*.yaml
```

확인 조건:

- Deployment와 네 CronJob이 모두 같은 full Git SHA tag를 사용한다.
- tag는 40자리 lowercase hexadecimal SHA다.
- `latest`를 사용하지 않는다.

### YAML syntax 확인

```bash
ruby -e '
require "yaml"
Dir["k8s/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

### Image tag assertion

```bash
ruby -ryaml -e '
paths = Dir["k8s/*.yaml"].sort
images = []

paths.each do |path|
  YAML.load_stream(File.read(path)).compact.each do |doc|
    kind = doc["kind"]
    next unless ["Deployment", "CronJob"].include?(kind)

    containers = if kind == "Deployment"
      doc.dig("spec", "template", "spec", "containers")
    else
      doc.dig("spec", "jobTemplate", "spec", "template", "spec", "containers")
    end

    Array(containers).each do |container|
      image = container["image"]
      next unless image&.start_with?("seocj/news-api:")
      images << [kind, doc.dig("metadata", "name"), image]
    end
  end
end

raise "expected five workload images, got #{images.size}" unless images.size == 5

tags = images.map { |_, _, image| image.split(":", 2).last }.uniq
raise "workloads use different tags: #{tags.inspect}" unless tags.size == 1
raise "image tag is not full git SHA: #{tags.first}" unless tags.first.match?(/\A[0-9a-f]{40}\z/)

images.each { |kind, name, image| puts "#{kind}/#{name} #{image}" }
puts "immutable image assertions passed"
'
```

### GitHub Actions 정책 확인

```bash
rg -n \
  'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch' \
  .github/workflows
```

확인 조건:

- image tag source가 full `${{ github.sha }}` 또는 동등한 40자리 commit SHA다.
- manifest update는 image build 성공 이후에만 실행된다.
- `main` 직접 push를 하지 않는다.
- 별도 branch와 PR 생성 방식을 사용한다.
- Secret 값이 로그에 출력되지 않는다.
- workflow permission이 필요한 최소 범위로 제한된다.

설치된 환경에서는 다음 lint를 실행한다.

```bash
actionlint
```

설치되지 않았다면 미실행 사실을 Verification에 기록한다.

### 문서 및 금지 영역 확인

```bash
git diff --check
```

```bash
git diff --name-only -- \
  app scripts db requirements.txt docker-compose.yml
```

기대 결과: 출력 없음.

### Docker Hub image 확인

```bash
IMAGE_SHA='<40자리 Git SHA>'
docker buildx imagetools inspect "seocj/news-api:${IMAGE_SHA}"
```

확인 조건:

- image manifest 조회 성공
- ARM64 platform 포함
- 해당 SHA tag가 실제 Docker Hub에 존재

### Argo CD diff 확인

사람이 port-forward와 login을 완료한 환경에서 실행한다.

```bash
argocd app get news-api \
  --server localhost:8080 \
  --insecure \
  --refresh

argocd app diff news-api \
  --server localhost:8080 \
  --insecure
```

기대 조건:

- Application은 `Manual`
- manifest PR merge 후 `OutOfSync`
- diff는 Deployment와 네 CronJob의 image tag 변경으로 제한
- delete, recreate, Service, Ingress, Secret과 `ClusterIssuer` 변경 없음

### Manual Sync 이후 운영 확인

다음 명령은 사람이 승인한 뒤 실행하고 실제 결과를 Verification에 기록한다.

```bash
argocd app sync news-api \
  --server localhost:8080 \
  --insecure

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl rollout status deployment/news-api \
  -n default \
  --timeout=10m

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get deployment,service,ingress,cronjob \
  -n default

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get deployment/news-api \
  -n default \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get cronjob \
  -n default \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.jobTemplate.spec.template.spec.containers[0].image}{"\n"}{end}'

curl -fsS https://api.newslab.ai.kr/health
```

### Controlled rollback과 restore

```bash
PREVIOUS_SHA='<이전 정상 40자리 SHA>'
CURRENT_SHA='<현재 최신 40자리 SHA>'
```

절차:

```
이전 SHA manifest PR 생성
→ 사람이 PR diff 확인 및 merge
→ Argo CD OutOfSync/diff 확인
→ 사람이 Manual Sync
→ rollout, Pod image와 /health 확인
→ 최신 SHA restore PR 생성
→ 사람이 merge
→ Argo CD Manual Sync
→ 최신 SHA와 정상 상태 재확인
```

rollback과 restore 각각의 실제 command, Git revision, image tag, Sync result와 `/health` 결과를 Verification에 기록한다.

## Acceptance criteria

- GitHub Actions가 Backend image를 full 40자리 Git SHA tag로 build하고 Docker Hub에 push한다.
- image build 결과에 ARM64 platform이 포함된다.
- K3s에서 사용하는 Backend Deployment와 네 CronJob image가 모두 동일한 full Git SHA tag다.
- K3s workload manifest에서 `seocj/news-api:latest`가 제거된다.
- manifest tag 갱신은 별도 branch와 PR로 수행되며 `main` 직접 push를 하지 않는다.
- manifest update workflow는 image build 성공 이후에만 실행된다.
- workflow 권한은 필요한 최소 범위로 제한되고 credential과 Secret이 로그에 노출되지 않는다.
- manifest PR에는 image tag 변경 외 불필요한 resource spec 변경이 없다.
- manifest PR merge 이후 Argo CD가 `OutOfSync`를 감지한다.
- Argo CD diff가 Deployment와 네 CronJob의 image tag 변경으로 제한된다.
- 사람이 Manual Sync를 승인하고 operation이 성공한다.
- Backend Deployment rollout이 성공하고 `2/2 Ready`를 유지한다.
- 실제 Backend Pod image가 manifest의 full SHA tag와 일치한다.
- 네 CronJob image가 동일한 full SHA tag와 일치한다.
- Service, Ingress, CronJob schedule과 shared `ClusterIssuer`에 회귀가 없다.
- production `/health`가 정상 응답한다.
- 이전 정상 SHA로 controlled rollback을 실제 수행하고 정상 상태를 확인한다.
- 최신 SHA로 restore한 뒤 `Synced`, `Healthy`, rollout과 `/health` 정상 상태를 재확인한다.
- Architecture, Runbook과 Verification에 최종 배포 흐름, 승인 gate, rollback과 실패 대응이 기록된다.
- 실행하지 않은 검증은 통과로 기록하지 않는다.
- Task checklist, Verification status와 Approved Fixes 상태가 일치한다.
- CodeRabbit review와 사람 검토에서 bootstrap 범위의 남은 blocker가 없음을 확인한다.

## Notes

- Branch: `feature/backend-immutable-image-gitops`
- Task artifact: `docs/tasks/feature-backend-immutable-image-gitops.md`
- Argo CD Application: `news-api`
- Argo CD sync policy는 Manual을 유지한다.
- immutable image는 우선 full Git SHA tag를 사용한다.
- digest pinning은 이번 범위에 포함하지 않는다.
- manifest update workflow가 사용할 인증과 PR 생성 방식은 UNIT-01 조사 결과로 확정한다.
- 이전 정상 SHA는 실제 Docker Hub image 존재 여부와 운영 성공 이력이 확인된 revision을 사용한다.
- 사람이 수행하는 merge, Sync, rollback과 restore는 Agent가 대신 실행하지 않는다.
- Verification에는 실제 실행한 명령과 실제 결과만 기록한다.

## UNIT-01 설계 확정

UNIT-01 조사와 설계 결정은
[`docs/design/backend-immutable-image-gitops.md`](../design/backend-immutable-image-gitops.md)에
기록했다.

확정한 후속 구현 방향은 다음과 같다.

- Backend workflow는 현재 `.github/workflows/docker-build.yml`에서 `main` push와
  `workflow_dispatch`로 `linux/arm64` image를 build/push하며, 이미
  `${{ github.sha }}`와 `latest` tag를 함께 발행한다.
- 현재 K8s manifest의 `Deployment/news-api`와 네 CronJob은 모두
  `seocj/news-api:latest`를 사용한다.
- `news-api` Argo CD Application은 `main`의 `k8s` path를 `recurse: false`로
  추적하고 `cluster-issuer.yaml`을 제외한다. 관리 범위는 Backend Deployment,
  Service, Ingress와 네 CronJob으로 제한된다.
- 운영 manifest image는 `seocj/news-api:<40자리 full Git SHA>`로 전환하고,
  Deployment와 네 CronJob은 항상 같은 SHA를 사용한다.
- `latest`는 Docker Hub 호환용 보조 tag로 유지할 수 있지만, K3s workload와
  rollback 기준으로 사용하지 않는다.
- manifest update는 image build 성공 이후 별도 branch/PR로만 수행한다. 기본
  구현 방식은 `peter-evans/create-pull-request`와 `GITHUB_TOKEN`이며, manifest
  update job에만 `contents: write`, `pull-requests: write`를 부여한다.
- 동일 SHA 재실행 중복 방지는 `bot/update-news-api-image-${{ github.sha }}`
  branch를 재사용하는 방식으로 처리한다.
- 이전 정상 SHA는 Docker Hub image 존재, ARM64 manifest, 운영 성공 기록과
  DB/Secret/ConfigMap 호환성이 확인된 revision에서만 선택한다.

## UNIT-02 workflow 구현

UNIT-02 구현 결과는
[`docs/design/backend-immutable-image-gitops.md`](../design/backend-immutable-image-gitops.md)의
`UNIT-02 구현 결과`에 기록했다.

완료한 범위는 `.github/workflows/docker-build.yml`의 Backend image build/push
job이다.

- Workflow 권한을 `contents: read`로 명시했다.
- Docker Hub 대상 image repository를 `seocj/news-api`로 고정했다.
- Build 전에 `GITHUB_SHA`가 40자리 lowercase hexadecimal Git SHA인지 검증한다.
- `docker/build-push-action@v6`가 `linux/arm64` image를
  `seocj/news-api:${{ github.sha }}`로 push한다.
- `latest` tag는 Docker Hub 호환용 보조 tag로 유지하지만, K3s workload 전환은
  UNIT-04에서 수행한다.

UNIT-03의 manifest update PR 생성과 UNIT-04의 Kubernetes manifest image tag
변경은 이번 UNIT에서 수행하지 않았다.

## UNIT-03 manifest update PR workflow 구현

UNIT-03 구현 결과는
[`docs/design/backend-immutable-image-gitops.md`](../design/backend-immutable-image-gitops.md)의
`UNIT-03 구현 결과`에 기록했다.

완료한 범위는 `.github/workflows/docker-build.yml`의 manifest update branch/PR
생성 job이다.

- `update-manifest` job은 `needs: build`로 image build 성공 이후에만 실행되며,
  `main` branch context에서만 manifest PR을 만든다.
- `build` job은 `contents: read`, `update-manifest` job은 `contents: write`와
  `pull-requests: write` 권한만 사용한다.
- Manifest update script는 `GITHUB_SHA`를 40자리 lowercase Git SHA로 검증하고,
  다섯 Backend workload manifest의 image reference를 같은
  `seocj/news-api:${{ github.sha }}` 값으로 갱신한다.
- 같은 job에서 다섯 workload image 수, tag 일치, full SHA 형식과 workflow SHA
  일치를 검증한다.
- `peter-evans/create-pull-request@v6`가
  `bot/update-news-api-image-${{ github.sha }}` branch와 `main` 대상 PR을
  생성한다.
- PR body에는 source commit, image와 대상 resource 목록을 기록한다.

UNIT-04의 Kubernetes manifest image tag 직접 전환, UNIT-05 이후의 Docker Hub,
Argo CD, rollout, production `/health`, rollback/restore 검증은 이번 UNIT에서
수행하지 않았다.

## UNIT-04 immutable workload manifest 전환

UNIT-04 구현 결과는
[`docs/design/backend-immutable-image-gitops.md`](../design/backend-immutable-image-gitops.md)의
`UNIT-04 구현 결과`에 기록했다.

완료한 범위는 Backend Deployment와 네 CronJob manifest의 image reference
전환과 로컬 정적 검증이다.

- `Deployment/news-api`와 네 CronJob image를 모두
  `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 전환했다.
- `seocj/news-api:latest`는 K8s workload manifest에서 제거했다.
- YAML syntax 검증과 image assertion으로 다섯 workload image 수, tag 일치와
  40자리 lowercase Git SHA 형식을 확인했다.
- GitHub Actions workflow는 image build 성공 이후 `update-manifest` job이
  별도 branch와 PR을 생성하는 정책을 유지한다.
- `actionlint`는 현재 로컬 환경에 설치되어 있지 않아 실행하지 못했고,
  Verification에 skipped로 기록했다.

Rollback/restore와 전체 회귀 검증은 UNIT-07~UNIT-08의 사람 통제 단계로 남겼다.

## UNIT-05~UNIT-06 운영 검증 완료

사람이 Docker Hub image, Argo CD diff/Manual Sync, K3s rollout과 production
`/health` 운영 검증 결과를 제공했다.

- Docker Hub image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- image platform: `linux/arm64`
- image index digest:
  `sha256:2024f4e3ff050f63588c316edcf90bcd6533c1047a78a15547666f101dad43d7`
- Argo CD sync 전 상태: main revision `7aa3971` 기준 `OutOfSync`
- diff 대상: `Deployment/news-api` 1개, CronJob 4개
- diff 내용: image가 `latest`에서 full SHA image로 변경된 내용만 존재
- Manual Sync: succeeded
- Sync revision: `7aa397148a5d1c3d931cd9205553d1cd7f5838dc`
- Deployment rollout: successfully rolled out
- Deployment image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- Pod: 2개 모두 `Running`, `READY=true`, `arm-worker-node`
- CronJob: 4개 모두
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- Argo CD 최종 상태: `Synced`, `Healthy`
- production `/health`:
  `{"status":"ok","service":"news-api","hostname":"news-api-5755fd5b99-kv847"}`

UNIT-05와 UNIT-06은 완료 처리했다. UNIT-07 rollback/restore와 UNIT-08 전체 회귀
검증도 아래 기록과 최종 검증으로 완료 처리한다.

## UNIT-07 rollback/restore 운영 검증 완료

사람이 이전 정상 SHA로 controlled rollback을 수행하고, 최신 SHA로 restore한 뒤
운영 상태를 재확인한 결과를 제공했다.

Rollback:

- rollback image:
  `seocj/news-api:8760b1a6dfa523d1cef7a0c0b5fc22ee014a831f`
- Docker Hub image 존재와 `linux/arm64` platform을 확인했다.
- rollback SHA는 `origin/main` history에 포함된다.
- Argo CD sync 전 상태는 main revision `1766100` 기준 `OutOfSync`였다.
- diff는 Deployment 1개와 CronJob 4개의 image 변경만 포함했다.
- Manual Sync는 revision
  `1766100d4e8f5abb47b95afc200555b38c7c5bcb`로 성공했다.
- Deployment rollout은 성공했다.
- Pod 2개는 `Running`, `READY=true`였다.
- CronJob 4개는 모두 rollback SHA image를 사용했다.
- Argo CD 최종 상태는 `Synced`, `Healthy`였다.
- production `/health`는 정상이다.

Restore:

- restored image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- Argo CD sync 전 상태는 main revision `522bc4a` 기준 `OutOfSync`였다.
- diff는 Deployment 1개와 CronJob 4개의 image 변경만 포함했다.
- Manual Sync는 revision
  `522bc4a6331dcc36fda17fbec59557c11c2682ec`로 성공했다.
- Deployment rollout은 성공했다.
- Pod 2개는 `Running`, `READY=true`였다.
- CronJob 4개는 모두 restored SHA image를 사용했다.
- Argo CD 최종 상태는 `Synced`, `Healthy`였다.
- production `/health`는 정상이다.

UNIT-07은 완료 처리한다.

## UNIT-08 최종 정리

최종 운영 기준은 다음과 같다.

- 배포 image는 full Git SHA tag를 사용한다.
- GitHub Actions가 image build 성공 후 manifest update bot PR을 생성한다.
- 사람이 manifest PR diff를 검토하고 merge한다.
- Argo CD는 automated sync 없이 `OutOfSync`와 diff를 보여주며, 사람이 Manual Sync를
  승인한다.
- rollback도 이전 정상 full SHA로 manifest를 바꾸는 PR, merge, Argo CD Manual
  Sync로 수행한다.
- `kubectl rollout restart`만으로 image version을 변경하지 않는다.
- auto sync, automatic prune, automatic self-heal은 적용하지 않는다.
- 최종 review gate는 CodeRabbit review와 사람 검토로 유지한다. Antigravity
  재실행은 요구하지 않는다.

## Implementation Units

- [x] UNIT-01: 현재 Backend image build workflow, manifest image reference와 Argo CD 관리 범위를 분석하고 immutable image 전환 설계를 확정
- [x] UNIT-02: full Git SHA 기반 Backend image build·push workflow 구현
- [x] UNIT-03: image build 성공 후 manifest SHA 갱신 branch·PR 생성 workflow 구현
- [x] UNIT-04: Deployment와 네 CronJob을 동일한 immutable SHA image로 전환하고 정적·CI 검증 완료
- [x] UNIT-05: 실제 SHA image 발행과 manifest PR merge 후 Argo CD OutOfSync·diff·Manual Sync 검증
- [x] UNIT-06: Backend rollout, Pod·CronJob image 일치와 production `/health` 검증
- [x] UNIT-07: 이전 정상 SHA controlled rollback과 최신 SHA restore 검증
- [x] UNIT-08: 전체 회귀 검증, Architecture·Runbook·Verification·README 판단 및 PR·devlog 정리
