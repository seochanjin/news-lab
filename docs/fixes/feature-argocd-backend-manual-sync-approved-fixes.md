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
- [x] FIX-03: Antigravity review의 production API 검증 범위를 실제 증거와 일치시킨다.
  - `docs/reviews/feature-argocd-backend-manual-sync-antigravity.md`의 `/health`, `/version` 검증 완료 문구를 `/health` 검증 완료로 축소한다.
  - `/version`을 실제로 실행한 증거가 없다면 검증 완료로 주장하지 않는다.
- [x] FIX-04: Antigravity review 문서의 잘못된 상대 경로를 수정한다.
  - `docs/reviews/` 기준 `../docs/...`는 `docs/docs/...`로 해석되므로 모두 `../...`로 변경한다.
  - Task, Verification, Fixes 등 동일 파일 내 다른 링크에도 같은 규칙을 적용한다.
- [x] FIX-05: CodeRabbit review artifact를 실제 review 결과로 채운다.
  - `docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md`의 빈 템플릿을 유지하지 않는다.
  - 이번 CodeRabbit 지적 사항, Required Fixes, Optional Improvements, Suggested Test Commands와 현재 Verdict를 명시한다.
  - fix 적용 후 재검토 결과가 통과하면 최종 Verdict를 `PASS`로 갱신한다.
- [x] FIX-06: Task 문서의 Verification 참조 경로를 현재 backend 전용 문서로 교체한다.
  - `docs/tasks/feature-argocd-backend-manual-sync.md`의 기존 `docs/verification/feature-argocd-manual-sync-baseline.md` 참조를 `docs/verification/feature-argocd-backend-manual-sync.md`로 변경한다.
  - baseline 문서도 여전히 필요하다면 두 문서의 용도를 구분해 함께 명시한다.
- [x] FIX-07: Verification 문서의 Ruby placeholder command를 실제 실행 가능한 명령으로 교체한다.
  - `ruby -e '<k8s/argocd/news-api-application.yaml field assertions>'` placeholder를 제거한다.
  - 실제 사용한 assertion command 전체를 기록해 재현 가능성과 감사 가능성을 확보한다.
  - 다음과 같은 실행 가능한 형태를 사용할 수 있다.

```bash
ruby -ryaml -e '
manifest = YAML.load_file("k8s/argocd/news-api-application.yaml")

raise "kind mismatch" unless manifest["kind"] == "Application"
raise "repoURL mismatch" unless manifest.dig("spec", "source", "repoURL") == "https://github.com/seochanjin/news-lab.git"
raise "targetRevision mismatch" unless manifest.dig("spec", "source", "targetRevision") == "main"
raise "path mismatch" unless manifest.dig("spec", "source", "path") == "k8s"
raise "recurse mismatch" unless manifest.dig("spec", "source", "directory", "recurse") == false
raise "exclude mismatch" unless manifest.dig("spec", "source", "directory", "exclude") == "cluster-issuer.yaml"
raise "destination server mismatch" unless manifest.dig("spec", "destination", "server") == "https://kubernetes.default.svc"
raise "destination namespace mismatch" unless manifest.dig("spec", "destination", "namespace") == "default"
raise "syncPolicy must be absent" if manifest.dig("spec", "syncPolicy")

puts "Application manifest assertions passed"
'
```

## Rejected or Deferred Suggestions

- private repository 전환 시 Argo CD repository credential 연동 가이드 추가 제안은 이번 fix에서 적용하지 않는다.
  - 현재 repository는 public이므로 이번 PR의 필수 수정 사항이 아니다.
  - private 전환 시 Secret 저장 방식, credential rotation, 최소 권한 정책을 포함한 별도 후속 task로 진행한다.
- Frontend Argo CD Application 도입은 이번 fix 범위에서 제외한다.
- immutable image tag 전환과 CI 기반 manifest tag 갱신 자동화는 별도 후속 task로 유지한다.
- Automated Sync, automatic prune, self-heal, public Argo CD Ingress, SSO와 HA 구성은 이번 fix 범위에 포함하지 않는다.

## Applied Changes

- [x] FIX-01에 따라 `docs/tasks/feature-argocd-backend-manual-sync.md`의 `UNIT-04` 완료 상태를 유지하고, 사람이 cluster 접근 가능한 환경에서 최종 운영 상태를 확인해 pending 조건을 해소한 사실을 기록했다.
- [x] Agent sandbox의 K3s API 접근 실패를 과거 환경 제약으로 분류하고, 이후 사람이 동일 kubeconfig로 확인한 운영 검증과의 관계를 명확히 했다.
- [x] Task의 UNIT-01~04, Verification의 `passed`와 `Pending Verification: 없음`이 같은 완료 상태를 나타내도록 정리했다.
- [x] FIX-02에 따라 승인 fix 적용 범위와 재검증 결과를 Verification 문서에 기록하고 FIX-01, FIX-02를 완료 처리했다.
- [x] FIX-03에 따라 Antigravity review의 production API 완료 주장을 실제 증거가 있는 `/health`로 한정했다.
- [x] FIX-04에 따라 Antigravity review의 모든 `../docs/` 링크를 `docs/reviews/` 기준의 올바른 `../` 상대 경로로 수정했다.
- [x] FIX-05에 따라 CodeRabbit review artifact에 실제 findings, required fixes, optional improvements, suggested commands와 현재 Verdict를 기록했다. 외부 재검토는 실행하지 않았으므로 Verdict는 `CHANGES REQUIRED`를 유지했다.
- [x] FIX-06에 따라 Task의 Verification 참조를 Backend 전용 문서로 교체했다.
- [x] FIX-07에 따라 Verification의 Ruby placeholder를 실행 가능한 전체 assertion command로 교체하고 재실행 통과 결과를 기록했다.

## Verification Required

fix 적용 후 다음 명령을 실행한다.

```bash
rg -n \
  "/version|/health|\.\./docs/|feature-argocd-manual-sync-baseline|<k8s/argocd/news-api-application.yaml field assertions>|Verdict|Problems Found|Required Fixes Before PR" \
  docs/reviews/feature-argocd-backend-manual-sync-antigravity.md \
  docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md
```

기대 결과:

- Antigravity review의 production API 검증 주장이 `/health`로 한정됨
- Antigravity review에 `../docs/` 경로가 남아 있지 않음
- CodeRabbit review 문서가 빈 템플릿이 아님
- Task 문서가 backend 전용 Verification 문서를 참조함
- Verification 문서에 Ruby placeholder가 남아 있지 않음
- Ruby assertion command가 실제 실행 가능한 전체 명령으로 기록됨

Ruby assertion 재실행:

```bash
ruby -ryaml -e '
manifest = YAML.load_file("k8s/argocd/news-api-application.yaml")
raise "kind mismatch" unless manifest["kind"] == "Application"
raise "repoURL mismatch" unless manifest.dig("spec", "source", "repoURL") == "https://github.com/seochanjin/news-lab.git"
raise "targetRevision mismatch" unless manifest.dig("spec", "source", "targetRevision") == "main"
raise "path mismatch" unless manifest.dig("spec", "source", "path") == "k8s"
raise "recurse mismatch" unless manifest.dig("spec", "source", "directory", "recurse") == false
raise "exclude mismatch" unless manifest.dig("spec", "source", "directory", "exclude") == "cluster-issuer.yaml"
raise "destination server mismatch" unless manifest.dig("spec", "destination", "server") == "https://kubernetes.default.svc"
raise "destination namespace mismatch" unless manifest.dig("spec", "destination", "namespace") == "default"
raise "syncPolicy must be absent" if manifest.dig("spec", "syncPolicy")
puts "Application manifest assertions passed"
'
```

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
  docs/reviews/feature-argocd-backend-manual-sync-antigravity.md \
  docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md \
  docs/fixes/feature-argocd-backend-manual-sync-approved-fixes.md
```

모든 검증을 통과한 뒤 CodeRabbit comment를 resolve하고 Antigravity re-review를 다시 실행한다.
