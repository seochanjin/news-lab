# Antigravity Review: Backend immutable image 기반 GitOps 배포 파이프라인 완성

## Review Summary

본 리뷰는 `feature/backend-immutable-image-gitops` 브랜치의 [UNIT-01]부터 [UNIT-04]까지 완료된 작업 결과물을 검토한 보고서입니다. 본 작업의 주요 목적은 `news-api` 백엔드 서버의 운영 이미지를 기존 `latest` 태그 대신 full Git SHA 태그로 대체하고, GitHub Actions가 이미지를 빌드한 후 Kubernetes 매니페스트 이미지 정보를 자동으로 갱신하여 PR을 올리는 GitOps 파이프라인을 구축하는 것입니다.

현재 시점에서 백엔드 이미지 빌드/푸시 워크플로우에 full Git SHA 태그 검증 및 발행 로직이 완료되었고, 빌드 성공 후 매니페스트를 자동으로 갱신하고 PR을 생성하는 `update-manifest` 잡(job)이 성공적으로 구현되었습니다. 또한 쿠버네티스 디플로이먼트 및 4개 크론잡 매니페스트에 동일한 full Git SHA 태그가 하드코딩 형태로 안전하게 반영되었으며, 로컬 정적 검증(Ruby 구문 분석 등)이 검증 문서 및 태스크 리포트에 명확하게 수행된 상태로 기록되어 있습니다.

## Requirement Coverage

태스크 문서 [feature-backend-immutable-image-gitops.md](../tasks/feature-backend-immutable-image-gitops.md)의 요구사항 충족도를 검증한 결과는 다음과 같습니다.

- **`latest` 제거 검증**: K3s 워크로드 매니페스트 파일 [news-api.yaml](../../k8s/news-api.yaml) 및 네 개의 크론잡 매니페스트에서 `seocj/news-api:latest`가 모두 제거되고 full Git SHA로 전환되었습니다.
- **동일 이미지 태그 통일**: Deployment 1개와 CronJob 4개의 컨테이너 이미지 레퍼런스가 동일한 Git SHA인 `5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`로 안전하게 통일되었습니다.
- **GitHub Actions 워크플로우**: 이미지 빌드가 성공적으로 끝난 뒤에만 `needs: build` 조건 및 `main` 브랜치 필터에 따라 [docker-build.yml](../../.github/workflows/docker-build.yml)의 `update-manifest` 잡이 동작하도록 제어 흐름이 바르게 정립되었습니다.
- **정적 검증 스크립트**: 워크플로우 내에서 이미지 빌드 전 `GITHUB_SHA` 값에 대한 40자리 hexadecimal 검증 로직이 추가되었고, 매니페스트 갱신 후에도 루비 스크립트를 사용하여 다섯 Backend workload manifest가 정확히 변경된 태그를 지녔는지 정적 검증 단계를 수행합니다.
- **PR 생성 자동화**: `peter-evans/create-pull-request@v6` 액션을 활용하여 `bot/update-news-api-image-${{ github.sha }}` 브랜치로부터 `main`으로 향하는 매니페스트 변경 PR을 생성하도록 설정되었습니다.

## Code Quality / Maintainability

- **Python 문서화 규칙**: 본 태스크의 구현 범위인 [UNIT-01] ~ [UNIT-04]는 파이썬 파일 수정을 포함하지 않습니다. 따라서 `app/` 혹은 `scripts/` 디렉터리 내의 파이썬 코드 수정이 발생하지 않아, 신규 한글 docstring 추가 대상이 없습니다.
- **워크플로우 가독성 및 이식성**: 쉘 커맨드 체인 대신 인라인 루비 스크립트를 워크플로우 내부에서 실행하여 YAML의 매니페스트 파싱 및 이미지 태그 치환, 검증을 보다 명시적이고 디버깅이 쉬운 구조로 개선했습니다.
- **안정적인 브랜치 관리**: 중복 PR 방지를 위해 커밋 SHA 별로 고유 브랜치(`bot/update-news-api-image-${{ github.sha }}`)를 발급 및 덮어쓰도록 처리하여 리포지토리 청결도를 유지하고 있습니다.

## Security Review

- **최소 권한의 법칙(Principle of Least Privilege) 적용**: 워크플로우 전역에는 `contents: read` 권한을 선언하였으며, PR 및 커밋 작성이 필수적인 `update-manifest` 잡에만 한정하여 job-level `contents: write` 및 `pull-requests: write` 권한을 선언했습니다. 이 구성은 불필요한 권한 범위와 credential 노출 위험을 줄입니다.
- **Secrets 보존**: 로그에 토큰값이나 개인 증명용 인증정보(Credentials)가 노출되지 않도록 기본 `GITHUB_TOKEN`과 안전하게 주입된 `DOCKERHUB_TOKEN` 비밀 값을 사용하였습니다.

## Operational Risk

- **Argo CD 동기화 정책 준수**: `news-api` 애플리케이션의 Argo CD 매니페스트는 수동 배포(Manual Sync) 정책을 유지합니다. 자동 Sync(`syncPolicy.automated`)로 인한 오동작이나 원치 않는 실시간 배포 충돌 가능성이 차단되어 있습니다.
- **로컬 조회 실패 대응**: 검증 문서 [feature-backend-immutable-image-gitops.md](../verification/feature-backend-immutable-image-gitops.md)에서 알 수 있듯이, 로컬 환경에서 Docker Hub registry의 DNS 조회가 불가능하여 발생한 빌드 이미지 조회 실패 이력을 `Status: failed`로 정직하게 기재하고, 이를 이유로 [UNIT-05]를 완료 처리하지 않고 대기 상태로 유지하였습니다. 이는 운영 환경에서 안전성을 검증하려는 보수적인 접근으로 매우 바람직합니다.

## Scope Control

- 태스크 요구사항에 선언된 "Do not change" 원칙에 의거하여, 백엔드 서버 비즈니스 로직, FastAPI 엔드포인트 응답 스키마, 데이터베이스 스키마 및 마이그레이션 파일(`db/migrations/*`), Supabase 관련 데이터, 그리고 프론트엔드 레포지토리와 공용 `ClusterIssuer` 등을 일절 건드리지 않았습니다. `git diff`를 통해 변경 대상이 파일 경로 기준 최소 범위로 통제되었음이 확인됩니다.

## Verification Review

- **검증 증적 문서의 정합성**: 검증 문서 [feature-backend-immutable-image-gitops.md](../verification/feature-backend-immutable-image-gitops.md)의 모든 기재 내용이 정직하고 완전합니다.
- **미실행 항목 관리**: 로컬 개발 머신에서 물리적으로 도달 불가능한 도커 허브 이미지 플랫폼 검증([UNIT-05]), 실제 Argo CD 연동 테스트([UNIT-06]), 롤백/복원 테스트([UNIT-07])는 `pending` 또는 `human-required`로 투명하게 기재되어 있으며, 증거 없이 체크리스트를 통과 처리한 이력이 발견되지 않았습니다.

## Documentation Review

- **설계 상세 기록**: 아키텍처 및 상세 흐름 설계 결과가 [backend-immutable-image-gitops.md](../design/backend-immutable-image-gitops.md)에 상세히 조율 및 서술되었습니다.
- **메인 태스크 인덱스**: [main.md](../tasks/main.md)의 타겟 태스크 링크가 현재 진행 중인 태스크로 정상 수정되었습니다.

## Problems Found

- 현재까지 구현된 [UNIT-01] ~ [UNIT-04] 범위 내에서 시스템적인 오동작, 크리티컬 버그, 혹은 보안 위협은 발견되지 않았습니다.

## Required Fixes Before PR

- **PR 블로커**: 없음. (동작 및 설정 상의 즉각적인 결함이나 필수 조치 사항은 부재합니다.)
- **작업 진행 상의 후속 조치**: 현재 UNIT-01~UNIT-04 변경은 실제 workflow 실행을 가능하게 하는 bootstrap PR입니다. bootstrap PR merge 이후 다음 순서로 UNIT-05~UNIT-08을 수행하고, 해당 검증 로그를 [feature-backend-immutable-image-gitops.md](../verification/feature-backend-immutable-image-gitops.md)에 실제 커맨드 결과와 함께 업데이트해야 합니다.

```text
bootstrap PR merge
→ main SHA image build/push
→ manifest image 갱신 bot PR 생성·검토·merge
→ Argo CD OutOfSync와 diff 확인
→ Manual Sync와 rollout 검증
→ rollback/restore 검증
→ 최종 문서 및 re-review
```

## Optional Improvements

- `actionlint`가 로컬에 설치되어 있지 않아 워크플로우에 대한 구문 linter 정적 검증이 `skipped` 처리되었습니다. 개발 머신 혹은 CI 런타임 이미지에 `actionlint` 바이너리를 추가 구축하면 워크플로우 변경 시 구문 에러를 미리 방지할 수 있을 것입니다.

## Suggested Test Commands

백엔드 매니세프트 전체의 이미지 태그 통일성 및 Git SHA 적합 여부를 재차 정적으로 체크하기 위해 아래의 커맨드를 보조적으로 활용해볼 수 있습니다.

```bash
ruby -ryaml -e '
paths = Dir["k8s/*.yaml"].sort
images = []
paths.each do |path|
  YAML.load_stream(File.read(path)).compact.each do |doc|
    kind = doc["kind"]
    next unless ["Deployment", "CronJob"].include?(kind)
    containers = kind == "Deployment" ? doc.dig("spec", "template", "spec", "containers") : doc.dig("spec", "jobTemplate", "spec", "template", "spec", "containers")
    Array(containers).each do |c|
      images << c["image"] if c["image"]&.start_with?("seocj/news-api:")
    end
  end
end
if images.uniq.size != 1
  raise "Workloads use inconsistent image tags!"
else
  tag = images.uniq.first.split(":").last
  raise "Tag is not a valid 40-character Git SHA: #{tag}" unless tag.match?(/\A[0-9a-f]{40}\z/)
  puts "Static check passed. Unified tag: #{tag}"
end
'
```

## Verdict

- `PASS — UNIT-01~UNIT-04` (현재 bootstrap 구현 범위인 UNIT-01부터 UNIT-04까지의 결과물은 검증 기준과 제약 조건을 모두 정상적으로 충족하므로 PR 제출 가능 상태로 판정합니다. 전체 Task는 UNIT-05~UNIT-08 완료 전까지 `pending`이며, bootstrap PR과 bot manifest PR의 merge가 70차 전체 완료를 의미하지 않습니다.)

## Re-review 1

### Existing Problems Status

- 최초 리뷰 시 UNIT-01~UNIT-04 구현 코드의 PR blocker는 없었으므로 기존 구현 결함 상태는 **해당 없음**입니다.

### Approved Fixes Verification

- 승인된 픽스 문서 [feature-backend-immutable-image-gitops-approved-fixes.md](../fixes/feature-backend-immutable-image-gitops-approved-fixes.md)에는 review artifact 보정 항목인 FIX-01~FIX-07이 존재합니다.
- FIX-01~FIX-05는 상대 링크, 정적 검증 대상 표현, 보안 효과 표현, bootstrap PR 이후 운영 검증 순서와 Verdict 범위 보정으로 적용됐습니다.
- FIX-06은 review artifact의 로컬 절대 경로 링크를 repository-relative link로 교체하고 Antigravity review prompt의 repository-relative 출력 규칙을 보정해 적용됐습니다.
- FIX-07은 Re-review가 실제 Approved Fixes 존재 여부와 구현 코드 필수 수정 없음, review artifact 보정 항목 존재를 구분하도록 정합성을 맞춰 적용됐습니다.

### Verification Evidence

- 검증 문서 [feature-backend-immutable-image-gitops.md](../verification/feature-backend-immutable-image-gitops.md)에 기록된 정적 검증 명령어들과 루비 스크립트를 통한 다섯 워크로드 이미지의 full Git SHA tag 일치 검사 결과가 `Status: passed`로 정상 수행되었음을 확인하였습니다.
- [docker-build.yml](../../.github/workflows/docker-build.yml) 워크플로우에 `update-manifest` 잡의 PR 생성 최소 권한 부여와 GITHUB_SHA 유효성 검증이 설계에 맞게 반영됐으며, [news-api.yaml](../../k8s/news-api.yaml) 매니페스트에도 의도한 SHA `5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`가 적용되었습니다.

### New Problems Found

- 새로 발견된 오동작, 보안 위협 및 Scope creep은 발견되지 않았습니다.

### Required Fixes Before PR

- 없음.

### Verdict

- PASS

## Re-review 2

### Existing Problems Status

- 최초 리뷰 및 Re-review 1 단계에서 지적된 코드/설정상의 결함이나 PR blocker는 없었습니다. 따라서 기존 결함 상태는 **해결됨 (적용 대상 아님)**입니다.

### Approved Fixes Verification

- 승인된 픽스 문서 [feature-backend-immutable-image-gitops-approved-fixes.md](../docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md)를 기준으로, 리뷰 아티팩트 보정 항목(FIX-01~FIX-07)들이 정상 반영 상태를 유지하고 있으며 추가 승인된 픽스 요구 사항은 존재하지 않습니다.

### Verification Evidence

- 검증 문서 [feature-backend-immutable-image-gitops.md](../docs/verification/feature-backend-immutable-image-gitops.md)에서 [UNIT-01] ~ [UNIT-04] 범위의 정적/CI 검증 결과가 `Status: passed`로 정상 수행되어 기록된 것을 확인했습니다.
- [docker-build.yml](../.github/workflows/docker-build.yml) 워크플로우에 `update-manifest` 잡의 PR 생성 최소 권한 부여, GITHUB_SHA 유효성 검증 등이 설계에 맞게 완벽히 조율되었으며, [news-api.yaml](../k8s/news-api.yaml) 매니페스트에도 의도한 SHA `5cbb040f3efe858c7a898ddae611f00ad1d2aeb5`가 올바르게 적용되었습니다.

### New Problems Found

- 새로 발견된 오동작, 보안 위협 및 Scope creep은 발견되지 않았습니다.

### Required Fixes Before PR

- 없음.

### Verdict

- PASS
