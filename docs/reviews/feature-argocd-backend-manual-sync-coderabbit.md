# CodeRabbit Review: Argo CD 최소 설치 및 Backend Manual Sync 검증

## Review Summary

문서와 manifest의 전체 방향은 Task의 Manual Sync 및 scope 제한 원칙과
일치한다. 다만 review/verification artifact의 정확성과 재현성에 다섯 가지
수정이 필요하다.

## Problems Found

1. Antigravity review가 실제 증거가 있는 `/health` 외에 `/version`까지 검증
   완료로 기술했다.
2. Antigravity review의 `../docs/...` 링크는 `docs/reviews/` 기준으로
   `docs/docs/...`를 가리켜 깨진다.
3. 이 CodeRabbit artifact가 빈 템플릿이라 실제 review 결과와 verdict를
   보존하지 못한다.
4. Task가 현재 Backend 작업의 Verification 대신 이전 baseline Verification을
   직접 참조한다.
5. Verification의 Ruby assertion command가 placeholder라 같은 검증을 재실행할
   수 없다.

## Required Fixes Before PR

- [x] Production API 완료 주장을 실제 `/health` 증거로 한정한다.
- [x] Antigravity review의 `../docs/` 링크를 `../` 기준의 올바른 상대 경로로
  수정한다.
- [x] CodeRabbit review artifact에 findings, required fixes, optional
  improvements, suggested commands와 verdict를 기록한다.
- [x] Task의 Verification 참조를 Backend 전용 문서로 교체한다.
- [x] Ruby placeholder를 실행 가능한 전체 assertion command로 교체하고
  재실행 결과를 Verification에 기록한다.

## Optional Improvements

- Private repository로 전환할 때 credential 저장, rotation과 최소 권한 정책을
  별도 runbook/task로 작성한다.
- Frontend Application, immutable image tag와 Automated Sync는 현재 변경에
  섞지 않고 후속 task로 유지한다.

## Suggested Test Commands

```bash
rg -n \
  "/version|/health|\.\./docs/|feature-argocd-manual-sync-baseline|<k8s/argocd/news-api-application.yaml field assertions>|Verdict|Problems Found|Required Fixes Before PR" \
  docs/reviews/feature-argocd-backend-manual-sync-antigravity.md \
  docs/reviews/feature-argocd-backend-manual-sync-coderabbit.md \
  docs/tasks/feature-argocd-backend-manual-sync.md \
  docs/verification/feature-argocd-backend-manual-sync.md
```

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

## Risk Notes

- `/version`은 실제 실행 증거가 없으므로 완료로 주장하지 않는다.
- 이 fix는 문서 정확성과 로컬 manifest assertion만 변경하며 cluster resource를
  변경하지 않는다.

## Verdict

CHANGES REQUIRED

Required Fixes는 repository에 반영했지만 CodeRabbit 재검토는 자동 실행하지
않았다. 외부 재검토가 통과하기 전에는 Verdict를 `PASS`로 변경하지 않는다.
