# Backend immutable image 기반 GitOps 배포 파이프라인 완성

## 작업 목적

Backend `news-api`의 운영 image 기준을 `latest`에서 full Git SHA 기반 immutable
tag로 전환하고, GitHub Actions가 image build 성공 이후 Kubernetes manifest image
tag 갱신 PR을 생성하는 bootstrap 흐름을 마련한다.

최종 목표는 다음 운영 흐름이다.

```text
application code PR merge
→ full Git SHA image build/push
→ manifest image tag 갱신 branch/PR 생성
→ 사람이 manifest diff 검토 후 merge
→ Argo CD OutOfSync/diff 확인
→ 사람이 Manual Sync 승인
→ rollout, workload image, production /health 확인
→ 필요 시 이전 SHA로 controlled rollback
```

이번 단계는 UNIT-01~UNIT-08 구현, 정적 검증, 사람이 수행한 운영 검증 결과 정리와
승인된 review artifact 보정까지 포함한다. Agent는 production-impacting command,
`kubectl`, `argocd`, `git push`, `git merge`를 실행하지 않았다.

## 기존 문제

- Backend workflow는 `${{ github.sha }}` image tag를 이미 발행했지만, K3s
  workload manifest는 `seocj/news-api:latest`를 참조하고 있었다.
- `latest` 기반 manifest는 Git commit, Docker image, K3s에서 실행 중인 workload
  image를 하나의 immutable revision으로 추적하기 어렵다.
- Argo CD는 registry의 새 `latest` push를 Git diff로 감지하지 못한다.
- API Deployment와 scheduled pipeline CronJob이 서로 다른 image revision으로
  실행될 위험을 manifest 수준에서 차단하지 못했다.
- rollback 기준이 Git revision인지 registry tag인지 불명확했다.
- 운영 반영과 production verification은 사람 통제 작업인데, review artifact 일부
  표현은 bootstrap PR 전후의 순서와 검증 범위를 혼동하게 만들 수 있었다.

## 변경 내용

- `.github/workflows/docker-build.yml`
  - `IMAGE_NAME: seocj/news-api`를 workflow env로 고정했다.
  - build 전 `GITHUB_SHA`가 full 40자리 lowercase hexadecimal Git SHA인지
    검증한다.
  - image를 `seocj/news-api:${{ github.sha }}`로 build/push하고, `latest`는
    Docker Hub 호환용 보조 tag로 유지한다.
  - `build` job은 `contents: read` 권한만 사용한다.
  - image build 성공 이후에만 실행되는 `update-manifest` job을 추가했다.
  - `update-manifest` job은 `main` branch context에서만 manifest update PR을
    만들고, job-level `contents: write`, `pull-requests: write`만 사용한다.
  - `peter-evans/create-pull-request@v6`로
    `bot/update-news-api-image-${{ github.sha }}` branch와 `main` 대상 PR을
    생성한다.

- `k8s/`
  - `Deployment/news-api`와 네 CronJob image를 모두
    `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 전환했다.
  - `seocj/news-api:latest`는 Backend workload manifest에서 제거했다.
  - Service, Ingress, selector, port, probe, resource request/limit, CronJob
    schedule, command, `suspend`, concurrency policy, Secret reference는 변경하지
    않았다.

- 문서와 workflow artifact
  - `docs/design/backend-immutable-image-gitops.md`에 image tag 정책, manifest PR
    방식, Argo CD 승인 gate, rollback/restore 기준을 정리했다.
  - `docs/tasks/feature-backend-immutable-image-gitops.md`에 UNIT별 진행 상태와
    pending 운영 검증을 기록했다.
  - `docs/verification/feature-backend-immutable-image-gitops.md`에 실제 실행한
    명령과 결과를 source of truth로 기록했다.
  - `docs/pr/feature-backend-immutable-image-gitops.md`에 PR 초안을 작성했다.
  - `docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`의
    FIX-01~FIX-07을 적용했다.
  - review instruction에 review artifact가 local URI, 사용자 홈 경로, absolute
    path를 기록하지 않도록 repository-relative link 규칙을 추가했다.

## 구현 상세

Workflow는 build와 manifest update를 같은 파일의 별도 job으로 분리했다. `build`
job이 먼저 Docker Hub에 ARM64 image를 push하고, `update-manifest` job은
`needs: build`로 build 성공 이후에만 실행된다.

`update-manifest`는 Ruby script로 다섯 Backend workload manifest의
`seocj/news-api:*` image reference만 같은 SHA image로 갱신한다. 이어서 YAML을
파싱해 다음 조건을 확인한다.

- Deployment와 CronJob image 수가 정확히 5개다.
- 모든 image tag가 하나의 값으로 일치한다.
- tag는 full 40자리 lowercase Git SHA다.
- tag가 workflow의 `GITHUB_SHA`와 일치한다.

Manifest update PR body에는 source commit, image, 대상 resource 목록을 기록해
application code merge commit과 manifest update PR의 연결을 추적할 수 있게 했다.

K8s manifest 직접 변경은 현재 branch HEAD
`5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`를 기준으로 했다. 이 SHA가 다섯
workload manifest에 동일하게 들어갔고, 정적 검증에서 `latest` 제거와 image 일치를
확인했다.

Approved Fixes는 구현 코드 결함 수정이 아니라 review artifact와 review 출력 규칙
보정이었다. 상대 링크, 정적 검증 대상 표현, 보안 효과 과장, bootstrap/운영 검증
순서, Verdict 범위, local absolute path, 실제 Approved Fixes 인식 문구를 보정했다.

## 대안 검토

- `latest` 유지
  - 장점: 기존 운영 방식과 호환된다.
  - 단점: Git manifest만으로 실제 실행 image revision을 추적하기 어렵고, Argo CD
    diff가 새 image push를 감지하지 못한다.

- Docker image digest pinning
  - 장점: registry artifact를 가장 엄밀하게 고정할 수 있다.
  - 단점: 이번 task scope에서 제외됐다. image signing, SBOM, provenance attestation,
    digest pinning은 별도 보안/배포 task로 다루는 편이 맞다.

- 수동 manifest update PR만 사용
  - 장점: 자동 branch 생성 권한이 필요 없고 운영 승인권이 분명하다.
  - 단점: build 성공 후 사람이 매번 image tag PR을 작성해야 해 반복 작업이 크다.

- Argo CD Image Updater 또는 automated sync 사용
  - 장점: image tag 갱신과 cluster 반영 자동화 수준을 높일 수 있다.
  - 단점: 현재 운영 원칙은 Manual Sync와 사람 승인이다. 자동 sync, prune,
    self-heal은 task의 Do not change 범위에 포함돼 있어 제외했다.

- 별도 deployment repository 도입
  - 장점: Backend/Frontend release coordination을 한 곳에서 관리할 수 있다.
  - 단점: 현재 repository 구조 변경이 커지고, 이번 bootstrap 목표보다 범위가 넓다.

## 선택한 접근과 근거

선택한 접근은 full Git SHA image tag와 manifest update PR 기반 GitOps 흐름이다.

- Backend workflow가 이미 `${{ github.sha }}`를 사용할 수 있어 source commit과
  image tag를 직접 연결하기 쉽다.
- Full 40자리 SHA는 short SHA보다 충돌 가능성이 낮고, rollback 기준으로도 더
  명확하다.
- Manifest update를 PR로 만들면 운영 desired state 변경이 Git diff로 남고, 사람이
  diff를 검토한 뒤 merge할 수 있다.
- Argo CD Manual Sync 정책을 유지해 Git merge와 cluster 반영 사이에 사람이
  OutOfSync/diff를 확인하는 승인 gate를 둘 수 있다.
- `latest`는 registry 호환용 보조 tag로 남기되 K3s workload manifest와 rollback
  기준에서는 제거했다.

## 트레이드오프

- 장점
  - Git commit, Docker image, K8s workload manifest를 하나의 full SHA로 연결한다.
  - Deployment와 네 CronJob이 같은 image revision을 사용하도록 정적 검증한다.
  - 운영 cluster 변경은 여전히 사람 승인 뒤 진행된다.
  - rollback은 이전 정상 SHA를 manifest에 되돌리는 PR 기반 절차로 정리할 수 있다.

- 비용과 한계
  - Production-impacting 단계는 사람이 수행해야 하므로 Agent 단독으로 재현하지
    않는다.
  - 운영 검증 결과는 사람이 제공한 실제 결과를 Verification source of truth로
    사용한다.
  - `latest` tag는 workflow에서 보조 tag로 계속 발행되므로 registry에는 남는다.
    다만 운영 manifest와 rollback 기준으로는 사용하지 않는다.
  - `actionlint`가 로컬에 없어 workflow lint는 수행하지 못했다.

## 테스트

Source of truth:
`docs/verification/feature-backend-immutable-image-gitops.md`

통과한 검증:

- 현재 workflow와 K8s image reference 조사
  - `rg -n "docker/build-push-action|github.sha|latest|seocj/news-api" .github/workflows k8s`
  - `rg -n "kind: Deployment|kind: CronJob|image:" k8s`
- 변경 범위 확인
  - `git branch --show-current && git status --short && git diff --stat && git diff --name-only`
- `latest` 제거 확인
  - `rg -n 'seocj/news-api:latest|image:\s*.*news-api:latest' k8s`
  - 결과: 출력 없음
- Backend workload image 일치 확인
  - `rg -n '^\s*image:\s*seocj/news-api:' k8s/*.yaml`
  - 결과: Deployment 1개와 CronJob 4개가 같은 full SHA image 사용
- K8s YAML syntax 확인
  - `ruby -e 'require "yaml"; Dir["k8s/*.yaml"].sort.each { |path| YAML.load_stream(File.read(path)); puts "ok #{path}" }'`
- Image tag assertion
  - `ruby -ryaml -e '<image assertion script>'`
  - 결과: `immutable image assertions passed`
- Workflow YAML 확인
  - `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`
- GitHub Actions 정책 확인
  - `rg -n 'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch' .github/workflows`
- 문서 및 금지 영역 확인
  - `git diff --check`
  - `git diff --name-only -- app scripts db requirements.txt docker-compose.yml`
  - 결과: application code, scripts, DB migration, dependency, compose 파일 변경 없음
- Approved Fixes 검증
  - review artifact의 잘못된 상대 링크, local URI/absolute path, 잘못된 검증 대상
    표현, 절대적 보안 표현, Approved Fixes 부재 주장 제거 확인

환경 제약 또는 skipped:

- Docker Hub image 조회
  - `docker buildx imagetools inspect "seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5"`
  - 결과: Docker Hub registry DNS 조회 실패
  - 상태: 이후 사람이 운영 환경에서 image 존재와 ARM64 platform을 확인
- `actionlint`
  - 현재 로컬 환경에 설치되어 있지 않아 skipped

## 운영 반영

사람이 Docker Hub image, manifest PR merge 후 Argo CD diff와 Manual Sync, K3s
rollout, workload image, Argo CD `Synced`/`Healthy`, production `/health`를
확인했다. 이어서 이전 정상 full SHA로 rollback하고 최신 full SHA로 restore하는
controlled test도 수행했다.

Rollback과 restore 모두 Deployment 1개와 CronJob 4개의 image 변경만 diff에
포함됐고, Manual Sync, rollout, Pod Ready, CronJob image 일치, production
`/health`가 정상으로 확인됐다.

## README 업데이트 판단

이번 bootstrap PR에서는 README를 변경하지 않았다.

판단 근거:

- 최종 운영 흐름은 Architecture, Runbook, Verification, PR draft와 devlog에
  반영했다.
- README는 backend 운영자용 상세 절차의 source of truth가 아니며, 이번 변경은
  사용자-facing 사용법보다 운영 workflow와 verification artifact에 집중된다.
- README 반영은 frontend Application과 전체 배포 문서 구조를 함께 정리할 때 별도
  task로 검토한다.

## 확인 결과

- UNIT-01~UNIT-04는 조사, 구현, 문서화, 정적 검증, Verification 기록까지 완료됐다.
- `Deployment/news-api`와 네 CronJob manifest는 같은 full Git SHA image tag를
  사용한다.
- K8s workload manifest에 `seocj/news-api:latest`가 남아 있지 않다.
- Workflow는 full `${{ github.sha }}` image tag를 발행하고, image build 성공 이후
  manifest update PR을 생성하는 job을 갖는다.
- Workflow permission은 build read-only와 manifest update write 권한으로 job-level
  분리됐다.
- API, DB, application code, script, dependency 변경은 없다.
- Approved Fixes FIX-01~FIX-07은 적용 및 검증 기록이 완료됐다.
- Docker Hub image 존재와 ARM64 platform, Argo CD, rollout, production endpoint,
  rollback/restore 검증은 사람이 수행했고 Verification에 기록했다.

## 이번 단계의 의미

이번 단계는 운영 cluster에 바로 반영한 배포 완료가 아니라, immutable image 기반
GitOps 흐름을 가능하게 하는 bootstrap 변경이다.

이전에는 `latest` image push와 운영 workload 사이의 추적성이 약했다. 이번 변경으로
Backend application code commit, Docker image tag, Kubernetes desired state가 full
Git SHA를 중심으로 연결될 수 있게 됐다. 또한 manifest update가 직접 `main`에
push되는 대신 PR로 남기 때문에, 운영 반영 전 사람이 diff를 검토하고 Argo CD
Manual Sync로 승인하는 구조를 유지한다.

## 포트폴리오용 요약

NewsLab backend 배포 흐름을 `latest` 기반 수동 배포에서 full Git SHA 기반 GitOps
bootstrap 구조로 전환했다. GitHub Actions는 ARM64 backend image를 immutable SHA
tag로 발행하고, build 성공 이후 K8s manifest image tag 갱신 PR을 생성하도록
구성했다. Backend Deployment와 네 CronJob은 동일한 full SHA image를 사용하도록
정적 검증했으며, Argo CD Manual Sync와 rollback/restore는 사람 승인 기반 운영
단계로 분리했다.

## 다음 단계 후보

- Frontend Application 등록과 Manual Sync 검증
- Frontend full Git SHA image tag 전환
- Argo CD 접근 방식의 Tailscale 내부화 검토
- README GitOps 배포 구조 반영 여부를 전체 운영 문서 구조와 함께 검토
- `actionlint` 설치 또는 CI 도입 여부를 별도 개선으로 검토
- CodeRabbit review와 사람 검토로 최종 review gate 확인
