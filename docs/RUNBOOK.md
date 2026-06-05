# NewsLab Runbook

This document contains operational commands for local development and K3s production operations.

Production-impacting commands must be run manually by the human operator.

## Agent Task Workflow

Create a new agent task from `main`:

```bash
scripts/new_agent_task.sh feature/<task-name> "<task title>"
```

The script creates a feature branch and task artifacts:

- `docs/tasks/<safe-branch-name>.md`
- `docs/reviews/<safe-branch-name>-antigravity.md`
- `docs/reviews/<safe-branch-name>-coderabbit.md`
- `docs/fixes/<safe-branch-name>-approved-fixes.md`
- `docs/verification/<safe-branch-name>.md`
- `docs/pr/<safe-branch-name>.md`
- `docs/devlog/<safe-branch-name>.md`

Use the artifact directories by purpose:

- Save review results in `docs/reviews/`.
- Record only human-approved fixes in `docs/fixes/`.
- Record actual commands run and results in `docs/verification/`.
- Draft PR and devlog entries from `docs/verification/`, not from assumptions or suggested commands.

## Local API

Run the FastAPI application locally:

```bash
uvicorn app.main:app --reload
```

Local API checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/sources
curl http://127.0.0.1:8000/articles
curl http://127.0.0.1:8000/collector/status
curl http://127.0.0.1:8000/raw-articles
```

## Local RSS Collector

Run the RSS collector manually:

```bash
python scripts/collect_rss.py
```

Check collector status locally:

```bash
curl http://127.0.0.1:8000/collector/status
curl http://127.0.0.1:8000/collector/runs
curl "http://127.0.0.1:8000/collector/runs?status=success"
curl "http://127.0.0.1:8000/collector/runs?status=failed"
```

## Local Raw Article Extractor

Run the raw article extractor manually:

```bash
python scripts/extract_raw_articles.py
```

Check raw article extraction results locally:

```bash
curl http://127.0.0.1:8000/raw-articles
curl "http://127.0.0.1:8000/raw-articles?status=success"
curl "http://127.0.0.1:8000/raw-articles?status=failed"
```

Check a specific raw article result:

```bash
curl http://127.0.0.1:8000/raw-articles/<article_id>
```

Check extractor run history locally:

```bash
curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/extractor/runs
curl "http://127.0.0.1:8000/extractor/runs?status=success"
curl "http://127.0.0.1:8000/extractor/runs?status=failed"
```

## K3s Access through Tailscale SSH Tunnel

The kubeconfig uses:

```text
https://127.0.0.1:6443
```

Open an SSH tunnel to the K3s master node over Tailscale:

```bash
ssh -i ~/Documents/oracle/ssh-key-2026-05-18.key \
  -N -L 6443:127.0.0.1:6443 \
  ubuntu@arm-master-node
```

Keep this terminal open.

Then run `kubectl` commands from another terminal:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
```

## K3s Cluster Checks

Check nodes:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
```

Check pods:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -o wide
```

Check deployments:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment
```

Check services:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get service
```

Check ingress:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress
```

Check certificates:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate
```

## Production API Checks

Check production API endpoints:

```bash
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/version
curl https://api.dev-scj.site/sources
curl https://api.dev-scj.site/articles
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/raw-articles
```

Check article filters:

```bash
curl "https://api.dev-scj.site/articles?page=1&page_size=5"
curl "https://api.dev-scj.site/articles?source=TechCrunch&page=1&page_size=5"
curl "https://api.dev-scj.site/articles?category=tech&page=1&page_size=5"
curl "https://api.dev-scj.site/articles?keyword=ai&page=1&page_size=5"
```

Check collector APIs:

```bash
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/collector/runs
curl "https://api.dev-scj.site/collector/runs?status=success"
curl "https://api.dev-scj.site/collector/runs?status=failed"
```

Check raw article APIs:

```bash
curl https://api.dev-scj.site/raw-articles
curl "https://api.dev-scj.site/raw-articles?status=success"
curl "https://api.dev-scj.site/raw-articles?status=failed"
curl https://api.dev-scj.site/raw-articles/<article_id>
```

Check extractor APIs:

```bash
curl https://api.dev-scj.site/extractor/status
curl https://api.dev-scj.site/extractor/runs
curl "https://api.dev-scj.site/extractor/runs?status=success"
curl "https://api.dev-scj.site/extractor/runs?status=failed"
curl -i "https://api.dev-scj.site/extractor/runs?status=wrong"
```

## Production Rollout

Human-controlled operation.

Restart the FastAPI deployment after a new image is built and pushed:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout restart deployment/news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api
```

Check running image:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api \
  -o=jsonpath='{.spec.template.spec.containers[0].image}'
echo
```

Check pods after rollout:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -o wide
```

## Production Logs

Check logs from a running API pod:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-api \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME
```

Open a shell inside a running API pod:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-api \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl exec -it $POD_NAME -- sh
```

Check scripts included in the production image:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-api \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl exec -it $POD_NAME -- ls scripts
```

## RSS Collector CronJob

Check CronJob:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
```

Check jobs:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs
```

Create a manual RSS collector job from the CronJob:

```bash
JOB_NAME=news-rss-collector-manual-$(date +%s)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-rss-collector \
  $JOB_NAME
```

Check the manual job pod:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME
```

Check manual job logs:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME
```

Delete the manual test job:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME
```

Verify collector run history after a manual job:

```bash
curl https://api.dev-scj.site/collector/status
curl "https://api.dev-scj.site/collector/runs?limit=5"
```

## Raw Extractor CronJob

Human-controlled operation.

Apply the raw extractor CronJob manifest after review:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-raw-extractor-cronjob.yaml
```

Check CronJob:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor
```

Create a manual Job from the CronJob for verification:

```bash
JOB_NAME=news-raw-extractor-manual-$(date +%s)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-raw-extractor \
  $JOB_NAME
```

Check the manual Job pod:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME
```

Check the manual Job logs:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME
```

Check extractor API status after the manual Job finishes:

```bash
curl https://api.dev-scj.site/extractor/status
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

Delete the manual verification Job:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME
```

## Kubernetes Secret Check

Check that the API secret exists:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret news-api-secret
```

Check that the deployment references the secret:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-api \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe pod $POD_NAME | grep -A5 Environment
```

## Git Workflow

Update local main:

```bash
git checkout main
git pull origin main
```

Create a feature branch:

```bash
git switch -c feature/<task-name>
```

Check changed files:

```bash
git status
git diff
```

Commit changes:

```bash
git add .
git commit -m "<commit message>"
```

Push only when explicitly intended:

```bash
git push -u origin feature/<task-name>
```

## Human-Controlled Operations

The following operations must remain manual:

- Supabase SQL migration execution
- GitHub PR merge
- K3s rollout / restart
- Kubernetes manifest apply
- Secret creation or update
- Production verification
- OCI security rule changes
- DNS / domain / TLS changes
