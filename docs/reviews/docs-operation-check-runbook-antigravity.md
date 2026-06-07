# Antigravity Review: NewsLab 운영 점검 Runbook 정리

## Review Summary

This review evaluates the changes made on the `docs/operation-check-runbook` branch. The primary purpose of this branch is to define standard operating procedures and a structured checklist for routine checks and troubleshooting of the K3s cluster, monitoring stack, news-api, and scheduled collectors/extractors in NewsLab.

All documentation changes are cleanly isolated within [docs/RUNBOOK.md](file:///Users/seochanjin/workspace/news-lab/docs/RUNBOOK.md). No source code, database migration, or Kubernetes manifests are modified.

## Requirement Coverage

The changes satisfy all requirements defined in the source of truth task file [docs/tasks/docs-operation-check-runbook.md](file:///Users/seochanjin/workspace/news-lab/docs/tasks/docs-operation-check-runbook.md):

- **Grafana dashboard metrics and investigation criteria**: Documented in detail in [docs/RUNBOOK.md](file:///Users/seochanjin/workspace/news-lab/docs/RUNBOOK.md#L116-L125).
- **Basic check commands (`kubectl get/top/describe/logs`)**: Covered across multiple check categories.
- **`news-api` Health Checks**: Included with normal baseline state and troubleshooting checks.
- **Raw Extractor Status API**: API checking commands are correctly documented.
- **CronJob status checks**: Covered for both `news-rss-collector` and `news-raw-extractor`.
- **Node/Pod troubleshooting flow (1차 대응)**: Covered 7 common failure categories as requested (Node NotReady, Pod Pending, Pod CrashLoopBackOff, OOMKilled, news-api unavailable, CronJob failure, Grafana/Prometheus unavailable).
- **Checklist format**: A short template check list is defined for routine operator logging.
- **README revision decision**: Documented in [docs/devlog/docs-operation-check-runbook.md](file:///Users/seochanjin/workspace/news-lab/docs/devlog/docs-operation-check-runbook.md) and [docs/pr/docs-operation-check-runbook.md](file:///Users/seochanjin/workspace/news-lab/docs/pr/docs-operation-check-runbook.md); the decision to defer updating the README is explicitly justified (it is an internal operator document and doesn't change core project workflows or local setup).

## Code Quality / Maintainability

- **Structure**: The new operations section has a clear, linear progression (Quick Health Check → Cluster → Monitoring → Application → CronJob → Troubleshooting → Checklist).
- **Readability**: Code blocks are properly formatted and use uppercase environment variables (`KUBECONFIG`) to separate configuration from command arguments.
- **Genericity**: All troubleshooting commands use placeholder variables (e.g., `<node-name>`, `<pod-name>`, `<namespace>`, `<job-name>`) to prevent hardcoded environments.

## Security Review

- **Credentials/Secrets**: No passwords, tokens, SSH keys, or private IP addresses are exposed.
- **Operational Guidelines**: Includes explicit warnings not to log sensitive details or private IP addresses.
- **Kubernetes Secrets**: Secret check commands in [docs/RUNBOOK.md](file:///Users/seochanjin/workspace/news-lab/docs/RUNBOOK.md#L696-L713) verify the existence of `news-api-secret` and environmental bindings without displaying the decrypted secret value itself.

## Operational Risk

- **Read-Only Diagnostics**: The instructions emphasize read-only diagnosis commands (`kubectl get`, `top`, `describe`, `logs`, `curl`) before taking any action.
- **Human-Controlled Boundaries**: Explicitly states that any mutating actions (e.g., restarting nodes, deleting pods, manual Job creation, rollout restart, manifest apply) require human operator decisions, strictly adhering to the project rules in [AGENTS.md](file:///Users/seochanjin/workspace/news-lab/AGENTS.md).

## Scope Control

- **Unexpected Modifications**: None. The changes are strictly documentation updates. No code (`app/`), database schema (`db/`), K3s configurations (`k8s/`), or RSS/Extractor scripts (`scripts/`) are modified.
- **File Alignment**: Standard workflow documents are properly aligned and tracked under `docs/`.

## Verification Review

Verification details should remain in `docs/verification/docs-operation-check-runbook.md`.

The review checked that the verification document exists and that it does not claim production-impacting execution or mutating commands.

## Documentation Review

- **Consistency**: The naming conventions, CronJob schedules, and namespace configurations defined in the new section correspond to the actual architecture documented in [docs/ARCHITECTURE.md](file:///Users/seochanjin/workspace/news-lab/docs/ARCHITECTURE.md) and [AGENTS.md](file:///Users/seochanjin/workspace/news-lab/AGENTS.md).

## Problems Found

- No critical logic errors, credential leaks, or scope creep issues are found.

## Required Fixes Before PR

- None.

## Optional Improvements

- **Future Linkage**: When a user-facing landing page or administrative dashboard is developed, consider adding a reference to this operations runbook in the root [README.md](file:///Users/seochanjin/workspace/news-lab/README.md).

## Suggested Test Commands

To verify documentation syntax and ensure no accidental credential/private IP leaks occurred:

```bash
# Check for whitespace/syntax issues in changed files
git diff --check

# Search for any unintended private IP exposure
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+" docs/RUNBOOK.md

# Search for unintended credential exposure patterns
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key" docs/RUNBOOK.md
```

## Verdict

**PASS**
The branch is ready for review and merge.
