# Task: NewsLab 운영 점검 Runbook 정리

## Goal

NewsLab 운영자가 K3s cluster, monitoring stack, news-api, RSS collector, raw extractor 상태를 빠르게 점검할 수 있도록 운영 점검 Runbook을 정리한다.

이번 작업의 목표는 새로운 기능 구현이 아니라, 이미 구축한 Grafana/Prometheus, kubectl, API endpoint를 이용해 운영자가 “현재 NewsLab이 정상인지” 판단할 수 있는 표준 점검 절차를 문서화하는 것이다.

## Scope

- Grafana에서 확인할 dashboard와 기준 정리
- `kubectl get/top/describe/logs` 기반 기본 점검 명령 정리
- `news-api` health check 확인 방법 정리
- raw extractor status API 확인 방법 정리
- RSS collector / raw extractor CronJob 상태 확인 방법 정리
- node/pod 이상 상황별 1차 대응 순서 정리
- 운영 점검 결과를 기록할 체크리스트 작성
- README 반영 필요 여부 판단

## Do not change

- Do not modify application source code.
- Do not modify DB schema or Supabase SQL.
- Do not modify K3s manifests unless only documentation references are needed.
- Do not reinstall Prometheus/Grafana.
- Do not add Alertmanager, Loki, PVC, or external notification channels.
- Do not expose secrets, kubeconfig, tokens, SSH keys, `.env`, Grafana password, or credentials.
- Do not run production-impacting commands unless the human operator explicitly chooses to run read-only checks.

## Expected files

- `docs/RUNBOOK.md`
- `docs/tasks/docs-operation-check-runbook.md`
- `docs/verification/docs-operation-check-runbook.md`
- `docs/pr/docs-operation-check-runbook.md`
- `docs/devlog/docs-operation-check-runbook.md`
- `docs/fixes/docs-operation-check-runbook-approved-fixes.md`
- `docs/reviews/docs-operation-check-runbook-antigravity.md`
- `docs/reviews/docs-operation-check-runbook-coderabbit.md`

## DB changes

- None.
- Supabase SQL, DB schema, migration은 변경하지 않는다.

## API changes

- None.
- FastAPI route, response schema, application behavior는 변경하지 않는다.

## Test commands

Static checks:

```bash
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key"
```

Optional read-only checks if the human operator explicitly runs them:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/extractor/status
```

## Acceptance criteria

- Runbook includes a clear quick health check flow.
- Runbook separates:
  - cluster checks
  - monitoring checks
  - application checks
  - CronJob checks
  - first-response troubleshooting
- Runbook includes first-response steps for common failures:
  - Node NotReady
  - Pod Pending
  - Pod CrashLoopBackOff
  - OOMKilled
  - news-api unavailable
  - CronJob failure
  - Grafana/Prometheus unavailable
- Runbook includes a short checklist format for routine operation checks.
- No secrets, tokens, raw kubeconfig, Grafana password, or private IPs are committed.
- Verification log records only commands actually run.

## Notes

- This task is documentation-only.
- Production read-only checks may be useful, but results must be recorded only if actually run by the human operator.
- Do not claim production verification unless command output is provided.
