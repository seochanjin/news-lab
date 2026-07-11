# Approved Fixes: Backend immutable image 기반 GitOps 배포 파이프라인 완성

## Approved Fixes

이 문서는 이미 적용된 review artifact 보정과 현재 CodeRabbit이 발견한 수정 사항을 함께 관리한다.

Antigravity는 두 차례 re-review에서도 로컬 절대 경로, 잘못된 상대 링크와 Approved Fixes 정합성 문제를 반복했으므로 현재 Task의 필수 review gate에서 제외한다. 이번 PR의 최종 review gate는 CodeRabbit과 사람 검토로 변경한다.

- [x] **FIX-01: review artifact의 상대 링크 경로 수정**
  - `docs/reviews/`에서 `docs/tasks/`, `docs/design/`, `docs/verification/`로 이동하는 링크를 `../tasks/`, `../design/`, `../verification/` 형식으로 수정했다.
  - repository root의 `.github/`와 `k8s/` 링크를 `../../.github/`, `../../k8s/` 형식으로 수정했다.
  - `../docs/...` 형태의 잘못된 링크를 제거했다.
- [x] **FIX-02: 정적 검증 대상을 정확하게 표현**
  - `5개 파드` 표현을 `Deployment 1개와 CronJob 4개` 또는 `다섯 Backend workload manifest`로 수정했다.
  - 실제 Pod 실행 상태를 검증한 것처럼 읽히는 문구를 제거했다.
- [x] **FIX-03: 보안 효과의 절대적 표현 완화**
  - `권한 유출 및 탈취 리스크를 완벽하게 배제`한다는 문구를 제거했다.
  - job-level 최소 권한으로 불필요한 권한 범위와 credential 노출 위험을 줄였다고 표현했다.
- [x] **FIX-04: bootstrap PR과 후속 운영 검증 순서 정정**
  - UNIT-01~UNIT-04 변경은 실제 workflow 실행을 가능하게 하는 bootstrap PR임을 명시했다.
  - bootstrap PR merge 이후 다음 순서로 UNIT-05~UNIT-08을 수행한다고 기록했다.

```
bootstrap PR merge
→ main SHA image build/push
→ manifest image 갱신 bot PR 생성·검토·merge
→ Argo CD OutOfSync와 diff 확인
→ Manual Sync와 rollout 검증
→ rollback/restore 검증
→ 최종 문서 정리
```

- [x] **FIX-05: Verdict 범위 명확화**
  - Verdict를 `PASS — UNIT-01~UNIT-04`로 한정했다.
  - bootstrap 구현 범위는 PR 제출 가능하지만 전체 Task는 UNIT-05~UNIT-08 완료 전까지 `pending`임을 명시했다.
  - bootstrap PR과 bot manifest PR merge가 전체 Task 완료를 의미하지 않는다고 기록했다.
- [x] **FIX-08: update-manifest checkout credential 비영속화**
  - `.github/workflows/docker-build.yml`의 `update-manifest` job에 있는 `actions/checkout@v4` step에 `persist-credentials: false`를 추가한다.
  - checkout이 `GITHUB_TOKEN`을 `.git/config`에 남기지 않도록 한다.
  - `peter-evans/create-pull-request@v6`의 자체 인증 흐름은 유지한다.
  - 별도 PAT 또는 신규 Secret은 추가하지 않는다.
- [x] **FIX-09: 전체 Task 완료 표현 통일**
  - 기존 숫자-prefixed 전체 완료 표현을 `전체 Task 완료`로 수정한다.
  - bootstrap PR과 bot manifest PR merge가 UNIT-05~UNIT-08 완료를 의미하지 않는다는 기존 의미는 유지한다.
  - 다음 파일을 확인한다.

```
docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md
```

- [x] **FIX-10: Re-review 2의 repository-relative 링크와 과도한 표현 수정**
  - Approved Fixes 링크를 `../fixes/feature-backend-immutable-image-gitops-approved-fixes.md`로 수정한다.
  - Verification 링크를 `../verification/feature-backend-immutable-image-gitops.md`로 수정한다.
  - workflow 링크를 `../../.github/workflows/docker-build.yml`로 수정한다.
  - K8s manifest 링크를 `../../k8s/news-api.yaml`로 수정한다.
  - 검증 범위를 넘어서는 과도한 표현을 제거한다.
- [x] **FIX-11: Verification의 로컬 절대 경로와 사용자명 제거**
  - `docs/verification/feature-backend-immutable-image-gitops.md`에 기록된 `/Users/...` 절대 경로와 로컬 사용자명을 제거한다.
  - 실행 위치는 `repository root`로 기록하고, branch와 repository-relative path 정보만 유지한다.
  - 실제 실행 명령과 working tree 상태 정보는 삭제하지 않는다.
- [x] **FIX-12: Antigravity를 현재 Task의 필수 review gate에서 제외**
  - 현재 Task, PR, Verification과 devlog에서 Antigravity 최종 PASS를 merge 조건으로 사용하지 않는다.
  - 최종 review gate를 CodeRabbit review와 사람 검토로 변경한다.
  - 기존 Antigravity review artifact는 과거 검토 기록으로만 유지하며 최종 승인 증거로 사용하지 않는다.
  - `scripts/agent_run.sh antigravity-review` 재실행을 현재 Task의 필수 절차에서 제거한다.
  - repository 전체 Antigravity adapter, script와 공통 문서 삭제는 현재 GitOps bootstrap PR에 섞지 않고 별도 유지보수 Task로 진행한다.

## Rejected or Deferred Suggestions

- **FIX-06~FIX-07 Antigravity 출력 보정 지속**: 중단한다. 공통 instruction을 수정한 뒤에도 Re-review 2에서 같은 로컬 경로와 정합성 문제가 반복됐다. 추가 prompt 보정 비용이 review 효용보다 크므로 필수 gate에서 제외한다.
- **Antigravity 전체 파일 및 adapter 즉시 삭제**: 별도 유지보수 Task로 연기한다. 현재 PR은 Backend immutable image GitOps bootstrap이므로 agent workflow 전역 삭제를 함께 수행하지 않는다.
- **별도 기능 범위 확대**: 거절한다. Frontend Argo CD Application, Automated Sync, digest pinning, image signing, SBOM, HA와 public Argo CD 접근은 이번 bootstrap PR에 포함하지 않는다.
- **`actionlint` 설치 및 CI 도입**: 선택 개선으로 연기한다. 현재 미설치 상태를 `skipped`로 기록하며 이번 PR blocker로 취급하지 않는다.
- **UNIT-05~UNIT-08 선행 완료 요구**: 현재 PR 전 조건으로는 거절한다. workflow 변경이 `main`에 반영돼야 실제 SHA image와 manifest update PR 흐름을 검증할 수 있다.
- **운영 명령의 Agent 실행**: 거절한다. PR merge, Argo CD Sync, K3s rollout, rollback과 restore는 사람이 승인하고 실행한다.

## Applied Changes

FIX-01~FIX-05는 적용 완료했다.

FIX-08~FIX-12는 CodeRabbit review 결과를 바탕으로 적용 완료했다.

수정 허용 범위:

```
.github/workflows/docker-build.yml
docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md
docs/verification/feature-backend-immutable-image-gitops.md
docs/tasks/feature-backend-immutable-image-gitops.md
docs/pr/feature-backend-immutable-image-gitops.md
docs/devlog/feature-backend-immutable-image-gitops.md
```

다음 영역은 변경하지 않는다.

```
k8s/*.yaml
app/
scripts/
db/
requirements.txt
docker-compose.yml
```

FIX-08~FIX-12 체크박스는 실제 수정과 검증이 완료된 경우에만 `[x]`로 갱신한다.

FIX-08~FIX-12 적용 내역:

- FIX-08: `.github/workflows/docker-build.yml`의 `update-manifest` job checkout
  step에 `persist-credentials: false`를 추가했다.
- FIX-09: Antigravity review artifact의 기존 숫자-prefixed 전체 완료 표현을
  `전체 Task 완료`로 수정했다.
- FIX-10: Re-review 2의 Approved Fixes, Verification, workflow, K8s manifest
  링크를 repository-relative 경로로 수정하고 과도한 표현을 제거했다.
- FIX-11: Verification 문서의 repository root 기록에서 로컬 절대 경로와 로컬
  사용자명을 제거했다.
- FIX-12: 현재 Task의 최종 review gate를 CodeRabbit review와 사람 검토로
  기록하고, Antigravity 결과는 최종 승인 증거로 사용하지 않도록 정리했다.

## Verification Required

### checkout credential 비영속화 확인

```bash
rg -n -A 5 \
  'name: Checkout source' \
  .github/workflows/docker-build.yml
```

확인 조건:

```yaml
- name: Checkout source
  uses: actions/checkout@v4
  with:
    persist-credentials: false
```

### Workflow YAML 확인

```bash
ruby -e '
require "yaml"
YAML.load_file(".github/workflows/docker-build.yml")
puts "workflow yaml ok"
'
```

기대 결과: `workflow yaml ok`.

### 잘못된 Task 완료 표현 제거

```bash
rg -n \
  '<old-numbered-task-completion-phrase>|전체 Task 완료' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md \
  docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md
```

확인 조건:

- 기존 숫자-prefixed 전체 완료 표현 출력 없음
- `전체 Task 완료`만 사용

### Re-review 2 링크 확인

```bash
rg -n \
  '\.\./docs/|\]\(\.\./\.github/|\]\(\.\./k8s/' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

```bash
rg -n \
  '\.\./fixes/|\.\./verification/|\.\./\.\./\.github/|\.\./\.\./k8s/' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: repository 구조와 일치하는 상대 링크만 출력된다.

### 로컬 절대 경로와 사용자명 제거

```bash
rg -n \
  'file://|/Users/|/home/|[A-Za-z]:\\\\' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md \
  docs/verification/feature-backend-immutable-image-gitops.md
```

기대 결과: 출력 없음.

### 과도한 단정 표현 제거

```bash
rg -n \
  '완벽하게 배제|완전히 제거|리스크가 없다|<overstatement-phrase>' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

### Antigravity 필수 gate 제거 확인

```bash
rg -n \
  'Antigravity.*PASS|antigravity-review|최종 review gate|CodeRabbit|사람 검토' \
  docs/tasks/feature-backend-immutable-image-gitops.md \
  docs/pr/feature-backend-immutable-image-gitops.md \
  docs/devlog/feature-backend-immutable-image-gitops.md \
  docs/verification/feature-backend-immutable-image-gitops.md
```

확인 조건:

- Antigravity PASS가 merge 또는 Task 완료 조건으로 남아 있지 않다.
- CodeRabbit review와 사람 검토가 최종 gate로 기록돼 있다.
- Antigravity re-review 재실행을 요구하지 않는다.

### 변경 범위 확인

```bash
git diff --check

git diff --name-only -- \
  k8s app scripts db requirements.txt docker-compose.yml
```

기대 결과:

- `git diff --check`는 exit code 0이다.
- 이번 fix로 K8s manifest, application code, scripts, DB와 dependency 파일에 신규 변경이 생기지 않는다.

### 최종 review

- CodeRabbit의 FIX-08~FIX-11 지적이 해결되었는지 확인한다.
- 사람이 workflow 권한, manifest update 순서와 문서 범위를 최종 확인한다.
- UNIT-05~UNIT-08과 전체 Verification은 계속 `pending`으로 유지한다.
- Antigravity 결과는 최종 승인 증거로 사용하지 않는다.
