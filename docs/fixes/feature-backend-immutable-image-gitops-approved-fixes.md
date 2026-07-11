# Approved Fixes: Backend immutable image 기반 GitOps 배포 파이프라인 완성

## Approved Fixes

이번 승인 항목은 UNIT-01~UNIT-04 구현 코드의 결함 수정이 아니라, Antigravity review artifact의 경로·표현·PR 단계 설명과 re-review 출력 규칙을 실제 작업 흐름에 맞추기 위한 문서 및 review workflow 보정이다.

- [x] **FIX-01: review artifact의 상대 링크 경로 수정**
  - `docs/reviews/`에서 `docs/tasks/`, `docs/design/`, `docs/verification/`로 이동하는 링크는 `../tasks/`, `../design/`, `../verification/` 형식으로 수정한다.
  - repository root의 `.github/`와 `k8s/`를 가리키는 링크는 `../../.github/`, `../../k8s/` 형식으로 수정한다.
  - `../docs/...` 형태의 잘못된 링크를 제거한다.
- [x] **FIX-02: 정적 검증 대상을 정확하게 표현**
  - `5개 파드`라는 표현을 `Deployment 1개와 CronJob 4개`, 또는 `다섯 Backend workload manifest`로 수정한다.
  - 실제 Pod 실행 상태를 검증한 것처럼 읽히는 문구를 제거한다.
- [x] **FIX-03: 보안 효과의 절대적 표현 완화**
  - `권한 유출 및 탈취 리스크를 완벽하게 배제`했다는 문구를 제거한다.
  - job-level 최소 권한으로 불필요한 권한 범위와 credential 노출 위험을 줄였다고 표현한다.
- [x] **FIX-04: bootstrap PR과 후속 운영 검증 순서 정정**
  - `main` merge 전에 SHA image 발행, Argo CD Manual Sync와 rollback/restore를 완료해야 한다는 문구를 제거한다.
  - UNIT-01~UNIT-04 변경은 실제 workflow 실행을 가능하게 하는 bootstrap PR임을 명시한다.
  - bootstrap PR merge 이후 다음 순서로 UNIT-05~UNIT-08을 수행한다고 기록한다.

```
bootstrap PR merge
→ main SHA image build/push
→ manifest image 갱신 bot PR 생성·검토·merge
→ Argo CD OutOfSync와 diff 확인
→ Manual Sync와 rollout 검증
→ rollback/restore 검증
→ 최종 문서 및 re-review
```

- [x] **FIX-05: Verdict 범위 명확화**
  - Verdict를 `PASS — UNIT-01~UNIT-04`로 한정한다.
  - 현재 bootstrap 구현 범위는 PR 제출 가능하지만 전체 Task는 UNIT-05~UNIT-08 완료 전까지 `pending`임을 명시한다.
  - bootstrap PR과 bot manifest PR의 merge가 70차 전체 완료를 의미하지 않는다고 기록한다.
- [x] **FIX-06: Antigravity review와 re-review에서 로컬 절대 경로 및 `file://` URI 금지**
  - 현재 review artifact의 `file:///Users/...`, `/Users/...`, `/home/...` 또는 Windows drive absolute path 링크를 모두 repository-relative Markdown 링크로 교체한다.
  - Antigravity review를 생성하는 실제 공통 instruction 또는 prompt source를 조사하고, 다음 규칙을 추가한다.
    - review artifact에는 `file://` URI를 기록하지 않는다.
    - 사용자 홈 디렉터리, 로컬 사용자명과 absolute filesystem path를 기록하지 않는다.
    - repository 내부 파일 링크는 review artifact 위치를 기준으로 한 repository-relative Markdown 경로만 사용한다.
    - 경로를 확정할 수 없으면 clickable link를 만들지 않고 repository-relative plain path로 기록한다.
  - 공통 instruction 보정은 review 출력 규칙에만 한정하며 Antigravity 실행 방식, timeout, sandbox와 review 판정 로직은 변경하지 않는다.
- [x] **FIX-07: re-review가 실제 Approved Fixes를 확인하도록 정합성 수정**
  - Approved Fixes 문서에 FIX 항목이 존재하는데도 `추가된 수정 요구 사항이 없다`고 기록한 문구를 제거한다.
  - Re-review의 `Approved Fixes Verification`에서 FIX-01~FIX-07의 적용 여부를 실제 artifact와 검증 결과를 기준으로 확인한다.
  - 구현 코드 필수 수정이 없다는 사실과 review artifact 보정 항목이 존재한다는 사실을 구분한다.
  - 아직 미적용된 FIX는 완료로 주장하지 않는다.

## Rejected or Deferred Suggestions

- **구현 코드 추가 수정**: 거절한다. 현재 Antigravity review에서 UNIT-01~UNIT-04 구현에 대한 필수 코드 수정이나 PR blocker는 발견되지 않았다.
- **별도 기능 범위 확대**: 거절한다. Frontend Argo CD Application, Automated Sync, digest pinning, image signing, SBOM, HA와 public Argo CD 접근은 이번 bootstrap PR에 포함하지 않는다.
- **`actionlint` 설치 및 CI 도입**: 선택 개선으로 연기한다. 현재 local 환경에서 미설치 상태를 `skipped`로 정확히 기록했으며 이번 PR의 blocker로 취급하지 않는다.
- **UNIT-05~UNIT-08 선행 완료 요구**: 현재 PR 전 조건으로는 거절한다. workflow 변경이 `main`에 반영돼야 실제 SHA image 발행과 manifest update PR 생성 흐름을 검증할 수 있으므로 bootstrap merge 이후 사람 통제 단계로 수행한다.
- **운영 명령의 Agent 실행**: 거절한다. PR merge, Argo CD Sync, K3s rollout, rollback과 restore는 사람이 승인하고 실행한다.
- **Antigravity harness 실행 방식 변경**: 연기한다. 이번 수정은 출력 경로 규칙과 현재 artifact 정합성에만 한정하며 `agy` argument, sandbox, timeout과 adapter 실행 동작은 변경하지 않는다.

## Applied Changes

FIX-01~FIX-05는 다음 review artifact에 적용했다.

```
docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

적용 내역:

- FIX-01: `docs/reviews/` 기준 상대 링크를 `../tasks/`, `../design/`, `../verification/`, `../../.github/`, `../../k8s/` 형태로 수정했다.
- FIX-02: `5개 파드` 표현을 `다섯 Backend workload manifest`로 수정했다.
- FIX-03: 보안 효과를 절대적으로 단정한 표현을 완화했다.
- FIX-04: bootstrap PR merge 이후 UNIT-05~UNIT-08 수행 순서를 명시했다.
- FIX-05: Verdict를 `PASS — UNIT-01~UNIT-04`로 한정했다.

FIX-06~FIX-07은 다음 범위에 적용했다.

```
docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
docs/agent/antigravity-review.md
docs/fixes/feature-backend-immutable-image-gitops-approved-fixes.md
docs/verification/feature-backend-immutable-image-gitops.md
```

적용 내역:

- FIX-06: review artifact의 Re-review 1에 있던 `file://` URI와 local absolute
  path 링크를 repository-relative Markdown link로 교체했다. Antigravity review
  공통 instruction인 `docs/agent/antigravity-review.md`에 `file://`, 사용자
  홈 경로, absolute path 기록 금지와 repository-relative link 사용 규칙을
  추가했다.
- FIX-07: Re-review 1의 `Approved Fixes Verification`에서 Approved Fixes가
  존재하지 않는다는 문구를 제거하고, 구현 코드 필수 수정 없음과 review artifact
  보정 항목 존재를 구분해 FIX-01~FIX-07 적용 상태를 기록했다.

공통 instruction 또는 prompt source는 repository에서 실제 사용 경로를 조사한 뒤
`docs/agent/antigravity-review.md` 하나만 선택했다. 같은 규칙을 여러 문서에
중복 추가하지 않았다.

다음 영역은 변경하지 않는다.

```
.github/workflows/docker-build.yml
k8s/*.yaml
app/
scripts/
db/
```

적용 후 FIX-06~FIX-07 체크박스는 실제 수정과 검증이 완료된 경우에만 `[x]`로 갱신한다.

## Verification Required

다음 검증을 실제 실행하고 결과를 Verification에 기록한다.

### 잘못된 상대 링크 제거

```bash
rg -n '\.\./docs/' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

### 로컬 절대 경로와 `file://` URI 제거

```bash
rg -n \
  'file://|/Users/|/home/|[A-Za-z]:\\\\' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

### repository-relative 링크 확인

```bash
rg -n \
  '\.\./tasks/|\.\./design/|\.\./verification/|\.\./fixes/|\.\./\.\./k8s/|\.\./\.\./\.github/' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 실제 repository 위치와 일치하는 링크만 출력된다.

### Antigravity 공통 instruction 반영 확인

먼저 실제 review prompt 또는 instruction source를 찾는다.

```bash
rg -n \
  'Antigravity|antigravity-review|review artifact|repository-relative|file://' \
  docs/agent docs/prompts scripts
```

확정한 instruction source에서 다음 의미의 규칙이 존재해야 한다.

- `file://` URI 금지
- 사용자 홈 경로와 absolute path 금지
- repository-relative Markdown link 사용
- 확정할 수 없는 경로는 plain repository-relative path 사용

### Approved Fixes re-review 정합성 확인

```bash
rg -n \
  'Approved Fixes Verification|FIX-01|FIX-06|FIX-07|추가된 수정 요구 사항이 없|적용 대상 아님' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

확인 조건:

- 실제 Approved Fixes가 존재함을 re-review가 인식한다.
- 구현 코드 필수 수정 없음과 review artifact 수정 존재를 구분한다.
- 미적용 FIX를 완료로 주장하지 않는다.

### 잘못된 검증 대상 표현 제거

```bash
rg -n \
  '5개 파드|다섯 파드|Pod 5개' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

### 절대적 보안 표현 제거

```bash
rg -n \
  '완벽하게 배제|완전히 제거|리스크가 없다|완벽히 조율' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

기대 결과: 출력 없음.

### PR 단계와 Verdict 확인

```bash
rg -n \
  'bootstrap|UNIT-01~UNIT-04|UNIT-05~UNIT-08|PASS.*UNIT-01|pending|전체 Task' \
  docs/reviews/feature-backend-immutable-image-gitops-antigravity.md
```

확인 조건:

- bootstrap PR merge 이후 운영 검증을 진행하는 순서가 기록돼 있다.
- Verdict가 UNIT-01~UNIT-04에 한정돼 있다.
- 전체 Task는 UNIT-05~UNIT-08 완료 전까지 `pending`으로 유지된다.

### 변경 범위 확인

```bash
git diff --check

git diff --name-only -- \
  .github/workflows k8s app scripts db
```

기대 결과:

- `git diff --check`는 exit code 0이다.
- 이번 fix 적용으로 workflow, K8s manifest, application code, scripts와 DB 파일에 신규 변경이 생기지 않는다.

### Re-review 재실행

Codex가 Approved Fixes를 적용하고 검증한 뒤 다음 순서로 진행한다.

```bash
scripts/agent_run.sh codex-fix
scripts/agent_run.sh antigravity-review
```

새 re-review 확인 조건:

- `file://`, `/Users/`, `/home/` 또는 로컬 사용자명이 출력되지 않는다.
- 모든 repository 파일 참조가 상대 링크 또는 repository-relative plain path다.
- FIX-01~FIX-07의 실제 적용 상태를 검토한다.
- UNIT-01~UNIT-04 범위만 `PASS`로 판정한다.
- UNIT-05~UNIT-08과 전체 Verification은 `pending`으로 유지한다.

### 최종 확인

- Antigravity review의 `Required Fixes Before PR`에 PR blocker가 없다고 기록돼 있다.
- review artifact는 bootstrap PR 제출 가능 여부와 전체 Task 완료 여부를 구분한다.
- 실행하지 않은 UNIT-05~UNIT-08 검증을 완료로 주장하지 않는다.
- Task와 Verification의 UNIT checklist 및 `pending` 상태와 모순되지 않는다.
