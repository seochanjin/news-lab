# Backend immutable image 기반 GitOps 배포 파이프라인 완성

## 작업 내용

Backend `news-api` 운영 image를 `latest` 중심 배포에서 full Git SHA 기반 immutable
image tag와 manifest PR 기반 GitOps 흐름으로 전환하는 bootstrap 변경입니다.

이번 PR은 UNIT-01~UNIT-04 범위의 구현과 정적 검증, 그리고 승인된 review artifact
보정 FIX-01~FIX-07 적용까지 포함합니다. PR merge, manifest bot PR merge,
Argo CD Manual Sync, K3s rollout, production `/health`, rollback/restore 검증은
아직 수행하지 않았으며 후속 UNIT-05~UNIT-08의 human-controlled 단계로 남아
있습니다.

## 주요 변경 사항

- `.github/workflows/docker-build.yml`
  - Docker Hub image repository를 `seocj/news-api`로 고정했습니다.
  - `GITHUB_SHA`가 40자리 lowercase Git SHA인지 build 전에 검증합니다.
  - Backend image를 `seocj/news-api:${{ github.sha }}`로 build/push하고,
    `latest`는 호환용 보조 tag로만 유지합니다.
  - image build 성공 이후에만 실행되는 `update-manifest` job을 추가했습니다.
  - `update-manifest` job은 `main` branch context에서만 동작하며, 다섯 Backend
    workload manifest image를 동일한 SHA tag로 갱신한 뒤
    `peter-evans/create-pull-request@v6`로 manifest update PR을 생성합니다.
  - workflow 권한은 기본 `contents: read`, manifest update job 한정
    `contents: write`, `pull-requests: write`로 분리했습니다.

- `k8s/*.yaml`
  - `Deployment/news-api`와 네 CronJob image를 모두
    `seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 통일했습니다.
  - K8s workload manifest에서 `seocj/news-api:latest`를 제거했습니다.
  - Service, Ingress, selector, port, probe, resource, CronJob schedule, command,
    suspend, concurrency policy는 변경하지 않았습니다.

- 문서
  - `docs/design/backend-immutable-image-gitops.md`에 immutable image와 manifest
    PR 기반 배포 설계, Argo CD 승인 gate, rollback/restore 기준을 기록했습니다.
  - `docs/tasks/feature-backend-immutable-image-gitops.md`와
    `docs/verification/feature-backend-immutable-image-gitops.md`에 UNIT별 상태와
    실제 실행 결과를 기록했습니다.
  - `docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md`의
    FIX-01~FIX-07을 적용했습니다.
  - `docs/agent/antigravity-review.md`에 review artifact가 local absolute path나
    local URI를 기록하지 않도록 repository-relative link 규칙을 추가했습니다.

## 추가/변경된 API

없음.

- 신규 FastAPI endpoint 없음
- 기존 endpoint path 변경 없음
- request/response schema 변경 없음
- 인증과 권한 정책 변경 없음

## DB 변경 사항

없음.

- migration file 추가 없음
- table, column, index, constraint 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음

## README 영향

이번 bootstrap PR에서는 README를 변경하지 않았습니다.

현재 변경은 GitHub Actions, K8s manifest, 운영 절차 문서와 verification artifact에
집중되어 있고, production rollout과 rollback/restore까지 완료된 최종 운영 흐름은
아직 확정되지 않았습니다. README 업데이트 필요성 판단은 task의 UNIT-08 범위로
남아 있으며, 운영 검증 완료 후 Architecture/Runbook/Verification과 함께 다시
판단해야 합니다.

## 테스트

Verification source of truth:
`docs/verification/feature-backend-immutable-image-gitops.md`

실행 및 통과:

- `rg -n "docker/build-push-action|github.sha|latest|seocj/news-api" .github/workflows k8s`
- `rg -n "kind: Deployment|kind: CronJob|image:" k8s`
- `git branch --show-current && git status --short && git diff --stat && git diff --name-only`
- `rg -n 'seocj/news-api:latest|image:\s*.*news-api:latest' k8s`
  - 결과: 출력 없음
- `rg -n '^\s*image:\s*seocj/news-api:' k8s/*.yaml`
  - 결과: Deployment 1개와 CronJob 4개가 모두 동일 SHA image 사용
- `ruby -e 'require "yaml"; Dir["k8s/*.yaml"].sort.each { |path| YAML.load_stream(File.read(path)); puts "ok #{path}" }'`
- `ruby -ryaml -e '<image assertion script>'`
  - 결과: `immutable image assertions passed`
- `ruby -e 'require "yaml"; YAML.load_file(".github/workflows/docker-build.yml"); puts "workflow yaml ok"'`
- `rg -n 'github\.sha|docker/build-push-action|pull-requests: write|contents: write|create-pull-request|workflow_run|workflow_dispatch' .github/workflows`
- `git diff --check`
- `git diff --name-only -- app scripts db requirements.txt docker-compose.yml`
  - 결과: 출력 없음

실행했지만 환경 제약으로 실패:

- `docker buildx imagetools inspect "seocj/news-api:5cbb040f3efe858c7a898ddae611f00ad1d2aeb5"`
  - 결과: Docker Hub registry DNS 조회 실패
  - 상태: image 존재와 ARM64 platform은 네트워크 가능한 환경에서 재확인 필요

Skipped:

- `actionlint`
  - 현재 로컬 환경에 설치되어 있지 않아 실행하지 못했습니다.
- `scripts/agent_run.sh antigravity-review`
  - 사용자 지시상 Codex/Gemini/Antigravity 자동 실행 금지이므로 실행하지 않았습니다.

Human-required / pending:

- manifest PR merge 후 Argo CD `OutOfSync`와 diff 확인
- Argo CD Manual Sync
- K3s rollout, Pod/CronJob image, Service, Ingress 확인
- production `/health`
- controlled rollback과 latest SHA restore 검증

## 확인 결과

- UNIT-01~UNIT-04는 구현, 문서화, 정적 검증, Verification 기록을 완료했습니다.
- Workflow는 full `${{ github.sha }}` image tag를 사용하고, manifest update는
  image build 성공 이후 별도 branch와 PR로만 진행되도록 구성했습니다.
- K8s Backend workload manifest는 Deployment 1개와 CronJob 4개 모두 동일한
  40자리 full Git SHA image tag를 사용합니다.
- K8s workload manifest에는 `seocj/news-api:latest`가 남아 있지 않습니다.
- Application code, scripts, DB, dependency, compose file은 변경하지 않았습니다.
- Verification status는 아직 `pending`입니다. Docker Hub image 조회, Argo CD,
  rollout, production `/health`, rollback/restore 검증이 완료되지 않았기 때문입니다.
- Approved Fixes FIX-01~FIX-07은 적용 및 검증 기록이 완료됐습니다.

## 비고

- 이 PR은 bootstrap PR입니다. merge 완료, production deployment 완료, K3s rollout
  완료, production verification 완료를 주장하지 않습니다.
- bootstrap PR merge 이후 expected flow:

```text
bootstrap PR merge
→ main SHA image build/push
→ manifest image 갱신 bot PR 생성·검토·merge
→ Argo CD OutOfSync와 diff 확인
→ Manual Sync와 rollout 검증
→ rollback/restore 검증
→ 최종 문서 및 re-review
```

- `docs/tasks/main.md`는 current task pointer를
  `feature-backend-immutable-image-gitops.md`로 가리키도록 변경된 상태입니다.
- `docs/reviews/` 문서는 review/approved-fix workflow artifact이며, verification
  통과 근거는 `docs/verification/feature-backend-immutable-image-gitops.md`만
  사용했습니다.
