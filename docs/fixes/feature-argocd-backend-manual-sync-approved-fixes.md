# Approved Fixes: Argo CD 최소 설치 및 Backend Manual Sync 검증

## Approved Fixes

- [x] FIX-01: Task checklist와 Verification 완료 상태를 일치시킨다.
  - `docs/tasks/feature-argocd-backend-manual-sync.md`의 `UNIT-04`를 `[x]`로 변경한다.
  - UNIT-04 본문에 사람이 cluster 접근 가능한 환경에서 최종 운영 상태를 직접 확인했다는 사실을 반영한다.
  - Agent sandbox의 K3s API 접근 실패는 과거 환경 제약으로 남기되, 이후 사람 검증으로 pending 조건이 해소되었음을 명시한다.
  - `docs/verification/feature-argocd-backend-manual-sync.md`의 `Verification Status: passed`, `Pending Verification: 없음`과 Task checklist가 동일한 완료 상태를 나타내도록 정리한다.
- [x] FIX-02: 승인된 fix 적용 및 재검증 증거를 문서에 기록한다.
  - `docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md`를 승인된 fix의 source of truth로 사용한다.
  - fix 적용 후 `Applied Changes`와 `Verification Required` 항목을 실제 결과로 갱신한다.
  - Antigravity re-review 전에 Task, Verification, Approved Fixes 세 문서가 모두 같은 상태인지 확인한다.

## Rejected or Deferred Suggestions

- private repository 전환 시 Argo CD repository credential 연동 가이드 추가 제안은 이번 fix에서 적용하지 않는다.
  - 현재 repository는 public이므로 이번 PR의 필수 수정 사항이 아니다.
  - private 전환 시 Secret 저장 방식, credential rotation, 최소 권한 정책을 포함한 별도 후속 task로 진행한다.
- Frontend Argo CD Application 도입은 이번 fix 범위에서 제외한다.
- immutable image tag 전환과 CI 기반 manifest tag 갱신 자동화는 별도 후속 task로 유지한다.
- Automated Sync, automatic prune, self-heal, public Argo CD Ingress, SSO와 HA 구성은 이번 fix 범위에 포함하지 않는다.

## Applied Changes

- [x] FIX-01에 따라
  `docs/tasks/feature-argocd-backend-manual-sync.md`의 `UNIT-04` 완료 상태를
  유지하고, 사람이 cluster 접근 가능한 환경에서 최종 운영 상태를 확인해
  pending 조건을 해소한 사실을 기록했다.
- [x] Agent sandbox의 K3s API 접근 실패를 과거 환경 제약으로 분류하고, 이후
  사람이 동일 kubeconfig로 확인한 운영 검증과의 관계를 명확히 했다.
- [x] Task의 UNIT-01~04, Verification의 `passed`와
  `Pending Verification: 없음`이 같은 완료 상태를 나타내도록 정리했다.
- [x] FIX-02에 따라 승인 fix 적용 범위와 재검증 결과를 Verification 문서에
  기록하고 FIX-01, FIX-02를 완료 처리했다.

## Verification Required

fix 적용 후 다음 명령을 실행한다.

```bash
rg -n \
  "UNIT-01|UNIT-02|UNIT-03|UNIT-04|Verification Status|Pending Verification" \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md \
  docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md
```

기대 결과:

- UNIT-01~04가 모두 `[x]`
- Verification Status가 `passed`
- Pending Verification이 `없음`
- Approved Fixes의 FIX-01, FIX-02가 적용 후 `[x]`
- 사람 검증으로 UNIT-04 pending 조건이 해소되었다는 설명이 Task와 Verification에 존재

문서 형식 검증:

```bash
git diff --check
```

금지 영역 변경 여부 확인:

```bash
git diff --name-only -- \
  app scripts db .github Dockerfile requirements.txt docker-compose.yml
```

기대 결과:

```
출력 없음
```

변경 파일 확인:

```bash
git status --short
git diff --stat
git diff -- \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md \
  docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md
```

최종 운영 상태는 이미 사람이 확인했으므로 이번 fix에서는 추가 write operation을 수행하지 않는다. 필요한 경우 다음 read-only 명령만 재실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl config current-context
argocd app get news-api --server localhost:8080 --insecure --refresh
argocd app diff news-api --server localhost:8080 --insecure
echo $?
```

모든 검증을 통과한 뒤 Antigravity re-review를 다시 실행한다.
