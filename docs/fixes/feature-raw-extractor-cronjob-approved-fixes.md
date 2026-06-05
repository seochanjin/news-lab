# Approved Fixes: 본문 추출 CronJob 구성

## Review 1: Gemini / Antigravity

### Approved Fixes

None.

Gemini / Antigravity review found no required fixes before PR.

### Rejected or Deferred Suggestions

- Final PR/devlog completion is deferred until production verification.
- Scheduled CronJob execution verification is deferred until the next configured schedule.

### Applied Changes

None.

### Verification Required

- `kubectl apply`
- CronJob registration check
- manual Job creation
- Pod logs check
- `/extractor/status` check
- `/extractor/runs?limit=5` check
- manual Job cleanup

---

## Review 2: CodeRabbit

### Review Source

- Reviewer: CodeRabbit
- Review target: `k8s/news-raw-extractor-cronjob.yaml`

### Approved Fixes

- Add container-level `securityContext` to the raw extractor CronJob.
- Set `allowPrivilegeEscalation: false`.
- Drop all Linux capabilities with `capabilities.drop: ["ALL"]`.
- Use `seccompProfile.type: RuntimeDefault`.

### Rejected or Deferred Suggestions

- `runAsNonRoot: true` is deferred until the container image user configuration is confirmed.
- `readOnlyRootFilesystem: true` is deferred until the extractor runtime is verified not to require writable filesystem paths.

### Applied Changes

- Added container-level `securityContext` to `k8s/news-raw-extractor-cronjob.yaml`.
- Set `allowPrivilegeEscalation: false`.
- Dropped all Linux capabilities.
- Set `seccompProfile.type: RuntimeDefault`.
- Re-ran static YAML and diff checks.

### Verification Required

- YAML parse check.
- `git diff --check`.
- Confirm no FastAPI app, DB migration, secret, or RSS collector CronJob changes.
- Production verification remains pending until after merge.
