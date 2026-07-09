# Antigravity Review: Argo CD 최소 설치 및 Backend Manual Sync 검증

## Review Summary
Argo CD의 K3s 클러스터 최소 설치 및 backend `news-api` 수동 동기화 검증 작업에 대한 Antigravity 검토 결과입니다. 전반적인 아키텍처 및 런북 설계, 매니페스트 파일 생성이 설계 규칙에 따라 안전하고 보수적으로 설계되었습니다. 다만 Task checklist 상태와 Verification 문서 간에 완료 상태 불일치가 감지되어 보완이 필요합니다.

## Requirement Coverage
- K3s 및 ARM64 호환성 확인(Argo CD v3.4.2 stable release 사용) 완료.
- `ClusterIssuer/letsencrypt-prod` 소유권 분리 결정 및 매니페스트 `exclude: cluster-issuer.yaml` 반영 완료.
- non-HA 수동 동기화(Manual Sync), automated/prune/self-heal 비활성화 조건 충족.
- Argo CD Core Component의 Readiness 대기 및 port-forward 접근을 통한 안전한 초기 로그인 검증 절차 수립 완료.
- `/health` production API health check를 통한 기능 회귀 검증 완료.

## Code Quality / Maintainability
- `k8s/argocd/news-api-application.yaml` 선언형 매니페스트 파일의 형식이 표준 Argo CD Application schema에 맞게 깔끔하게 작성되었습니다.
- 소스 경로 `k8s` 및 `recurse: false` 설정을 통해 불필요한 monitoring manifest 등이 포함되지 않도록 범위를 제한하여 유지보수성을 높였습니다.

## Security Review
- Argo CD Server가 `ClusterIP`로 배포되고 Ingress를 생성하지 않아 외부 노출 위험을 원천 차단함.
- 초기 admin credential(`argocd-initial-admin-secret`)의 값을 노출하지 않고 사람이 조회한 뒤 즉시 삭제하는 보안 수칙이 계획 및 검증 과정에 정확히 적용됨.
- 민감 정보(Secret, credential)가 Git이나 문서에 기록되지 않음.

## Operational Risk
- Manual Sync 방식으로 live 상태와 desired 상태 간의 diff(annotation 추가만 있음)를 사전 검증하여 기존 운영 중인 리소스의 recreate나 삭제 리스크가 없는 것을 사전에 증명함.
- 장애 및 실패 시, 자동 rollback을 사용하지 않고 상태를 보존한 채 사람이 직접 복구 개입하도록 설계하여 운영 안정성을 높임.

## Scope Control
- `app/`, `scripts/`, `db/`, `.github/` 등 애플리케이션 소스 코드 및 DB 스키마, 파이프라인 규칙을 전혀 변경하지 않아 Task의 `Do not change` 제약을 완벽히 준수함 (`git diff --name-only`로 검증됨).
- Frontend Argo CD 도입 및 immutable image tag 전환 등은 후속 태스크로 적절히 이관함.

## Verification Review
- Verification 문서([feature-argocd-backend-manual-sync.md](../verification/feature-argocd-backend-manual-sync.md))에 상세한 실행 명령어와 실제 출력 내용이 체계적으로 기록되어 있음.
- 다만, Task 문서([feature-argocd-backend-manual-sync.md](../tasks/feature-argocd-backend-manual-sync.md))의 `UNIT-04` 체크리스트는 K3s API 접근 차단 사유로 미완료(`[ ]`) 상태인 반면, Verification 문서에는 `passed` 및 Pending Verification `없음`으로 표기되어 있어 완료 상태의 불일치가 존재함.

## Documentation Review
- 신규 workflow 가이드라인에 맞추어 `docs/reviews/`, `docs/verification/`, `docs/fixes/` 등 관련 아티팩트 파일의 경로가 올바르게 배치됨.
- Python 코드 변경이 없어 한국어 docstring 관련 문서화 정책 위반은 없음.

## Problems Found
1. **Task Checklist와 Verification Document 간의 완료 상태 불일치**
   - [docs/tasks/feature-argocd-backend-manual-sync.md](../tasks/feature-argocd-backend-manual-sync.md)의 `UNIT-04`는 미완료(`[ ]`) 상태이며 본문에 "사람이 cluster 접근 가능한 환경에서 Verification의 pending 항목을 확인하기 전에는 완료로 표시하지 않는다"고 적혀 있으나, [docs/verification/feature-argocd-backend-manual-sync.md](../verification/feature-argocd-backend-manual-sync.md)에서는 Verification Status를 `passed`로 선언하고 `Pending Verification`을 `없음`으로 주장하고 있음.

## Required Fixes Before PR
- [ ] Task document [feature-argocd-backend-manual-sync.md](../tasks/feature-argocd-backend-manual-sync.md)의 `UNIT-04` 체크리스트를 `[x]`로 완료 처리하고, 검증에 대한 최종 사람의 승인 여부와 동기화를 명확히 하거나, 또는 Verification document의 상태/보류(Pending) 표기를 실제와 일치하도록 보완해야 함.

## Optional Improvements
- 향후 private repository로 전환할 경우를 대비하여, repository access credential을 Argo CD에 연동하는 안전한 방법에 대한 런북 가이드를 추가하면 좋을 것임.

## Suggested Test Commands
현재 상태를 재점검하기 위한 read-only 명령어:
```bash
# context 및 cluster 접속 확인
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl config current-context

# news-api application 상태 및 sync policy 조회
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get applications.argoproj.io news-api -n argocd -o yaml | grep -A 10 "syncPolicy"

# live diff 재확인
argocd app diff news-api --server localhost:8080 --insecure
```

## Verdict
CHANGES REQUIRED

## Re-review 1

### Existing Problems Status
- **최초 Review 문제 1 (Task Checklist와 Verification Document 간의 완료 상태 불일치)**: 미해결
  - **이유**: `docs/tasks/feature-argocd-backend-manual-sync.md`의 `UNIT-04` 체크리스트는 여전히 미완료(`[ ]`) 상태이며, `docs/verification/feature-argocd-backend-manual-sync.md`는 여전히 `passed` 상태에 보류(Pending) 항목이 없는 것으로 기재되어 있습니다. 해당 모순을 완화하는 문서 갱신이나 Approved Fixes 승인 내역이 확인되지 않았습니다.

### Approved Fixes Verification
- `docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`에 등록 및 승인된 Fix가 없으며, 현재 브랜치에 추가로 적용된 코드 변경이 없습니다.

### Verification Evidence
- 추가 검증 증거로 제출된 로그나 command output이 없으며, 기존 검증 기록과 동일합니다.

### New Problems Found
- 없음.

### Required Fixes Before PR
- [ ] [최초 Review 문제 1] Task document [feature-argocd-backend-manual-sync.md](../tasks/feature-argocd-backend-manual-sync.md)의 `UNIT-04` 체크리스트를 `[x]`로 완료 처리하고, 검증에 대한 최종 사람의 승인 여부와 동기화를 명확히 하거나, 또는 Verification document의 상태/보류(Pending) 표기를 실제와 일치하도록 보완해야 함.

### Verdict
CHANGES REQUIRED

## Re-review 2

### Existing Problems Status
- **최초 Review 문제 1 (Task Checklist와 Verification Document 간의 완료 상태 불일치)**: 해결됨
  - **해결 판정 근거**:
    - [Approved Fixes](../fixes/feature-argocd-backend-manual-sync-approved-fixes.md)의 `FIX-01`, `FIX-02`에 의거하여 `docs/tasks/feature-argocd-backend-manual-sync.md`의 `UNIT-04` 체크리스트가 `[x]`로 갱신되었습니다.
    - [Verification Document](../verification/feature-argocd-backend-manual-sync.md)에 `Approved Fixes 적용 재검증` 섹션이 추가되었고, 사람 검증을 통해 loopback network sandbox 제약으로 인한 pending 조건을 해소했음이 문서화되어 Task 완료 상태와 동기화되었습니다.
    - `git status` 결과 승인된 fix 범위(`docs/tasks/`, `docs/verification/`, `docs/fixes/`의 관련 문서 수정) 외의 금지 영역 변경 사항이 없음이 확인되었습니다.

### Approved Fixes Verification
- `docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`에 등록된 `FIX-01` 및 `FIX-02`가 성공적으로 적용되었으며, 검증 이력이 추가되었습니다.

### Verification Evidence
- `docs/verification/feature-argocd-backend-manual-sync.md`의 `Approved Fixes 적용 재검증` 섹션(L725-781)에 기록된 `rg` 명령어와 `git diff`를 통한 교차 검증 내용이 최종 통과되었습니다.

### New Problems Found
- 없음.

### Required Fixes Before PR
- 없음.

### Verdict
PASS

## Re-review 3

### Existing Problems Status
- **최초 Review 문제 1 (Task Checklist와 Verification Document 간의 완료 상태 불일치)**: 해결됨
  - **해결 판정 근거**:
    - [Approved Fixes](../fixes/feature-argocd-backend-manual-sync-approved-fixes.md)의 `FIX-01`, `FIX-02` 및 추가로 진행된 `FIX-03~07`이 모두 올바르게 적용되었습니다.
    - [Task Document](../tasks/feature-argocd-backend-manual-sync.md)의 `UNIT-04` 및 [Verification Document](../verification/feature-argocd-backend-manual-sync.md)의 모든 완료 조건과 pending 조건 해소 사실이 문서에 일치되게 기록되었습니다.

### Approved Fixes Verification
- `docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`에 정의된 `FIX-01~07`이 모두 성공적으로 적용되고 적용 완료(`[x]`) 상태로 체크되었습니다.
  - **FIX-03 (production API 검증 축소)**: Antigravity review의 검증 범위가 `/health`로 안전하게 축소되었습니다.
  - **FIX-04 (상대 경로 교정)**: Antigravity review의 깨진 링크 `../docs/...`가 올바른 `../...` 경로로 모두 교정되었습니다.
  - **FIX-05 (CodeRabbit 문서 반영)**: `docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md`가 실제 문제 발견 사항과 verdict를 기록한 문서로 정상 갱신되었습니다.
  - **FIX-06 (Task 내 Verification 참조 교체)**: Task 문서 내 Verification 참조 경로가 현재 backend 전용 문서로 올바르게 갱신되었습니다.
  - **FIX-07 (Ruby assertion placeholder 교체)**: Verification 문서 내 Ruby placeholder가 실제 재현 가능한 yaml 파싱 코드로 정확하게 대치되었습니다.

### Verification Evidence
- [Verification Document](../verification/feature-argocd-backend-manual-sync.md)의 `### Approved Fixes FIX-03~07 재검증` 섹션(L793-864)에 수록된 `rg` 교차 검증 및 `ruby` Application manifest assertion 재실행 결과(출력: `Application manifest assertions passed`, exit code 0)가 완벽히 입증되었습니다.
- `git diff --check` 및 금지 영역 변경 사항이 없음(`git diff --name-only` 출력 없음)이 성공적으로 입증되었습니다.

### New Problems Found
- 없음.

### Required Fixes Before PR
- 없음.

### Verdict
PASS
