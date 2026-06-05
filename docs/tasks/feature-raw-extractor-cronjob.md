# Task: 본문 추출 CronJob 구성

## Goal

Run `scripts/extract_raw_articles.py` automatically in K3s using a Kubernetes CronJob.

The raw article extractor currently runs manually. The extractor already records execution history in `extraction_runs`, and the result can be checked through `/extractor/status` and `/extractor/runs`.

This task adds a K3s CronJob manifest for the raw article extractor.

## Scope

- Add a Kubernetes CronJob manifest for raw article extraction.
- Use the existing application image.
- Run `python scripts/extract_raw_articles.py`.
- Reuse the existing DB secret/environment configuration pattern from the API or RSS collector.
- Use the same working directory and command style as the existing RSS collector CronJob.
- Set a safe schedule and timezone.
- Allow manual Job creation from the CronJob for verification.
- Update `docs/RUNBOOK.md` with raw extractor CronJob commands.
- Update `docs/verification/feature-raw-extractor-cronjob.md` with only commands actually run and results.

## Do not change

- Do not modify FastAPI app behavior.
- Do not modify DB schema.
- Do not modify `scripts/extract_raw_articles.py` unless strictly required.
- Do not modify RSS collector CronJob behavior.
- Do not modify secrets or credentials.
- Do not run `kubectl apply`.
- Do not run `kubectl rollout`.
- Do not execute Supabase SQL.
- Do not push or merge.
- Do not claim production verification is complete unless the human provides logs.
- Do not write expected production results as if they were actually verified.

## Expected files

Likely files:

- `k8s/news-raw-extractor-cronjob.yaml`
- `docs/RUNBOOK.md`
- `docs/verification/feature-raw-extractor-cronjob.md`
- `docs/pr/feature-raw-extractor-cronjob.md`
- `docs/devlog/feature-raw-extractor-cronjob.md`

## Kubernetes changes

Add a CronJob manifest.

Suggested name:

- `news-raw-extractor`

Suggested command:

- `python scripts/extract_raw_articles.py`

Suggested schedule:

- `30 3 * * *`

Suggested timezone:

- `Asia/Seoul`

Reason:

- RSS collector currently runs around 03:00.
- Raw article extraction should run after RSS collection has had time to insert articles.
- 03:30 gives a simple 30-minute buffer.

CronJob requirements:

- Use `apiVersion: batch/v1`.
- Use `kind: CronJob`.
- Set `concurrencyPolicy: Forbid`.
- Set reasonable `successfulJobsHistoryLimit` and `failedJobsHistoryLimit`.
- Use the existing image pattern from the API or RSS collector.
- Reuse the existing `DATABASE_URL` secret/environment configuration pattern.
- Use `timeZone: Asia/Seoul` if supported by the current Kubernetes/CronJob API version.
- If `timeZone` is unsupported, do not force a workaround. Document the limitation and keep the schedule behavior explicit.
- The existing RSS collector CronJob manifest may be used as a reference, but it must not be modified unless the change is explicitly required and approved.

## DB changes

None.

Do not add or modify database migrations.

## API changes

None.

Do not modify FastAPI routes or response behavior.

## Test commands

Agent must not run production commands.

Human will run these after reviewing the manifest:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-raw-extractor-cronjob.yaml

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob

JOB_NAME=news-raw-extractor-manual-$(date +%s)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-raw-extractor \
  $JOB_NAME

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME

POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME

curl https://api.dev-scj.site/extractor/status
curl "https://api.dev-scj.site/extractor/runs?limit=5"

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME
```

## Verification rules

- `docs/verification/feature-raw-extractor-cronjob.md` may include pending commands.
- Completed results must only be written after the human provides actual output.
- Production verification must remain pending until the human applies the manifest and provides logs.
- Do not infer success from static manifest creation alone.

## Acceptance criteria

- CronJob manifest exists.
- CronJob uses the existing news-api image or the same image pattern used by existing jobs.
- CronJob can access `DATABASE_URL` through the existing secret pattern.
- Manual Job can be created from the CronJob.
- Manual Job pod runs `scripts/extract_raw_articles.py`.
- Pod logs show extraction started and completed.
- `/extractor/status` shows the latest run.
- `/extractor/runs?limit=5` includes the manual run.
- RSS collector behavior is unchanged.
- FastAPI app code is unchanged unless explicitly required.
- No secrets are modified.
- Production verification is recorded in `docs/verification/feature-raw-extractor-cronjob.md`.

## Notes

This task should use the execution history added in 13차.

The goal is not to build a new extractor. The goal is to schedule the existing extractor safely in K3s.
