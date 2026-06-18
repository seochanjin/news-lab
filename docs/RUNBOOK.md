# NewsLab Runbook

이 문서는 현재 통합 Runbook 역할을 한다. 문서가 더 커지면 routine check, K3s operations, CronJobs, troubleshooting을 `docs/runbooks/` 하위 문서로 분리한다.

This document contains operational commands for local development and K3s production operations.

Production-impacting commands must be run manually by the human operator.

## Routine Operation Check

Use this procedure to decide whether the NewsLab cluster, monitoring stack,
API, RSS collector, and raw extractor are operating normally.

All commands in this section are read-only unless explicitly marked otherwise.
The human operator must open the Tailscale SSH tunnel described below before
running `kubectl` commands. Do not record credentials, kubeconfig contents,
private addresses, or unredacted application data in operation logs.

### Quick Health Check

Run these checks in order. Continue to the detailed section for any failed or
unexpected result.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/extractor/status
```

Normal baseline:

- Every expected node is `Ready`.
- Required application and monitoring Pods are `Running` or completed Job Pods
  are `Completed`; restart counts are not unexpectedly increasing.
- Node and Pod CPU/memory usage has no sustained saturation or sudden increase.
- `news-api` Deployment has `2/2` available replicas.
- Both CronJobs exist, are not suspended, and have recent successful Jobs:
  - `news-rss-collector`: `03:00 Asia/Seoul`
  - `news-raw-extractor`: `03:30 Asia/Seoul`
- `/health` succeeds, and collector/extractor status responses show an expected
  recent run without an unexplained failure or long-running state.

### Cluster Checks

Check node readiness, placement, Pod status, resource usage, and recent events:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get events -A \
  --sort-by=.lastTimestamp
```

Investigate when:

- A node is not `Ready`, or a previously running Pod is not `Running`.
- Pod restart counts increase between checks.
- CPU or memory remains near a resource limit, or usage differs sharply from
  the recent Grafana trend.
- Recent events include repeated scheduling, image pull, mount, probe, eviction,
  or OOM failures.

Use `describe` and logs for the affected object:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe node <node-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe pod -n <namespace> <pod-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n <namespace> <pod-name> \
  --all-containers --tail=200
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n <namespace> <pod-name> \
  --all-containers --previous --tail=200
```

`--previous` is useful only when a container has restarted. Redact sensitive or
article data before saving logs.

### Monitoring Checks

Check the monitoring components in the `monitoring` namespace:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get events -n monitoring \
  --sort-by=.lastTimestamp
```

Normal baseline:

- Grafana, Prometheus, Prometheus Operator, and kube-state-metrics Pods are
  `Running`.
- A node-exporter Pod is `Running` on every expected node.
- Restart counts are stable, and Grafana/Prometheus memory remains below the
  configured `512Mi` limits.

Open Grafana through a local port-forward. Credential retrieval and login are
human operator actions; never record the credential value.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward \
  -n monitoring svc/monitoring-grafana 3000:80
```

Then open `http://127.0.0.1:3000` and review the bundled dashboards. Dashboard
names may vary slightly with the installed kube-prometheus-stack version.

| Dashboard                                         | Check                                     | Investigate when                                                                        |
| ------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------- |
| Kubernetes / Compute Resources / Cluster          | Overall CPU, memory, and workload count   | Sustained saturation, unexpected workload drop, or a sharp change from the recent trend |
| Kubernetes / Compute Resources / Node (Pods)      | Per-node and per-Pod CPU/memory           | A node is missing, a Pod approaches its limit, or usage is concentrated unexpectedly    |
| Kubernetes / Compute Resources / Namespace (Pods) | `default` and `monitoring` workload usage | A namespace has unexpected growth or repeated restarts                                  |
| Node Exporter / Nodes                             | Node CPU, memory, filesystem, and network | Missing node metrics, filesystem pressure, or sustained resource pressure               |

Prometheus retention is `1d` and storage is ephemeral. Missing older history
does not by itself indicate an outage; missing current targets or recent
metrics does.

### Application Checks

Check Kubernetes objects that route traffic to `news-api`:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get service news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate \
  news-api-tls news-api-newslab-tls
```

Run the external read-only API checks only when the human operator chooses to
perform production verification:

```bash
curl -i https://api.dev-scj.site/health
curl -i https://api.newslab.ai.kr/health
curl https://api.dev-scj.site/version
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/extractor/status
```

Normal baseline:

- `news-api` Deployment is `2/2` available and its Pods are `Running`.
- Service and Ingress exist.
- Both `news-api-tls` and `news-api-newslab-tls` certificates are ready after
  the new domain has been applied.
- `/health` returns a successful HTTP response for both
  `api.dev-scj.site` and `api.newslab.ai.kr`.
- Collector and extractor status responses show the latest known run. Compare
  timestamps with the configured CronJob schedules before deciding a run is
  stale.

### CronJob Checks

Check schedule, suspension, last schedule, Jobs, Pods, and recent run APIs:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob \
  news-rss-collector news-raw-extractor
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs \
  --sort-by=.metadata.creationTimestamp
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-rss-collector
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-raw-extractor
curl "https://api.dev-scj.site/collector/runs?limit=5"
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

Normal baseline:

- `SUSPEND` is `False`, `ACTIVE` is normally `0`, and `LAST SCHEDULE` advances
  after the configured daily schedule.
- Recent scheduled Jobs are `Complete`; failed Jobs are investigated even when
  a later retry succeeded.
- Collector/extractor run history timestamps and statuses agree with the
  corresponding Job.

Inspect a failed Job without creating, deleting, or rerunning it:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe job <job-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l job-name=<job-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs job/<job-name> --tail=200
```

### First-Response Troubleshooting

Use read-only evidence first. Any label change, manifest apply, Pod deletion,
rollout, node restart, or manual Job creation requires an explicit human
operator decision.

#### Node NotReady

1. Run `kubectl describe node <node-name>` and review conditions, taints, and
   recent events.
2. Check whether Pods on that node are unavailable and whether other nodes have
   enough capacity.
3. Compare the node's last Grafana metrics with the other nodes.
4. Have the human operator inspect K3s, host resource, network, and Tailscale
   status on the affected node before choosing a restart or rejoin action.

#### Pod Pending

1. Run `kubectl describe pod -n <namespace> <pod-name>` and read scheduling
   events.
2. Check node readiness, allocatable resources, labels, taints, and the Pod's
   node selector.
3. Confirm whether the cause is capacity, placement, image pull, mount, or
   missing configuration.
4. Require human approval before changing labels, taints, resources, or
   manifests.

#### Pod CrashLoopBackOff

1. Run `kubectl describe pod` and both current and `--previous` container logs.
2. Check exit code, restart count, recent events, image, and configuration
   references without exposing secret values.
3. Compare with recent deployment or image changes.
4. Require human approval before rollback, rollout, or Pod deletion.

#### OOMKilled

1. Confirm `Reason: OOMKilled` and the exit code using `kubectl describe pod`.
2. Check current `kubectl top pod` values and the recent Grafana memory trend.
3. Compare observed usage with the container request and limit.
4. Require human approval before changing resource values or restarting the
   workload.

#### news-api Unavailable

1. Check Deployment replicas, API Pods, Service, Ingress, certificate, and
   recent events.
2. Check API Pod logs and whether `/health` fails from the external endpoint.
3. Distinguish Pod/application failure from Service, Ingress, certificate, DNS,
   or external network failure.
4. Require human approval before rollout, manifest, certificate, DNS, or
   network changes.

#### CronJob Failure

1. Check CronJob schedule/suspension, the failed Job description, its Pod, and
   logs.
2. Compare the Job time and result with `/collector/runs` or `/extractor/runs`.
3. Determine whether the failure is scheduling, image pull, configuration,
   database access, or script execution.
4. Require human approval before creating a manual Job, deleting a Job, or
   changing the CronJob.

#### Grafana or Prometheus Unavailable

1. Check monitoring Pods, Services, events, resource usage, and restart counts.
2. Describe and inspect logs for the affected Grafana, Prometheus, operator, or
   sidecar container.
3. If Grafana alone is unavailable, use `kubectl top` and object status while
   investigating. If Prometheus is unavailable, expect Grafana metrics gaps.
4. Require human approval before a restart, Helm change, resource change, or
   reinstall.

### Routine Check Record

Copy this checklist into an operation record. Record the check time, operator,
actual command results, and links to sanitized evidence. Do not mark production
verification complete without actual operator-provided results.

```text
NewsLab routine operation check
- Checked at:
- Operator:
- Cluster access available: [ ] yes [ ] no
- Nodes Ready: [ ] yes [ ] no
- Unexpected Pod state/restarts: [ ] none [ ] found
- Node/Pod resource pressure: [ ] none [ ] found
- Monitoring Pods and node-exporters healthy: [ ] yes [ ] no
- Grafana current metrics visible: [ ] yes [ ] no [ ] not checked
- news-api Deployment 2/2 available: [ ] yes [ ] no
- /health successful: [ ] yes [ ] no [ ] not checked
- RSS collector latest scheduled run healthy: [ ] yes [ ] no
- Raw extractor latest scheduled run healthy: [ ] yes [ ] no
- Recent warning events or failed Jobs: [ ] none [ ] found
- Follow-up owner/action:
- Sanitized evidence:
```

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

Print the current branch's workflow file paths:

```bash
scripts/agent_next_step.sh files
```

Print reusable handoff prompts for each workflow step:

```bash
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh fixes-draft
scripts/agent_next_step.sh codex-apply-fixes
scripts/agent_next_step.sh pr-draft
scripts/agent_next_step.sh devlog-draft
```

The helper derives the safe branch name from the current git branch. For example, `feature/raw-extractor-cronjob` becomes `feature-raw-extractor-cronjob`.

The helper only prints file paths and prompt templates for the human operator to copy. It does not run Codex, Gemini/Antigravity, GitHub, CodeRabbit, `kubectl`, Supabase SQL, production verification, `git push`, or `git merge`.

Standard prompt handoff rules are documented in:

```text
docs/prompts/agent-handoff.md
```

For each task, evaluate README and portfolio documentation impact before drafting the PR or devlog:

- Record alternatives considered, chosen approach, rationale, and tradeoffs in the devlog.
- Decide whether README updates are needed.
- If README changes are not needed, briefly record why in the devlog or PR draft.
- README updates are not mandatory for every internal workflow task, but the decision should be explicit.

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
ssh -i <oracle-ssh-private-key-path> \
  -N -L 6443:127.0.0.1:6443 \
  ubuntu@<tailscale-node-name>
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

## Backend API Domain and TLS Transition

The backend Ingress keeps the existing `api.dev-scj.site` host and adds
`api.newslab.ai.kr`. Both hosts route to the same `news-api` Service, but each
host uses a separate TLS Secret:

```text
api.dev-scj.site    -> news-api-tls
api.newslab.ai.kr   -> news-api-newslab-tls
ClusterIssuer       -> letsencrypt-prod
```

Changing the frontend API base URL is not part of this transition. Perform
that change only after the new backend domain and certificate are stable.

All commands in this section are human-controlled. Confirm DNS before applying
the manifest:

```bash
dig +short api.newslab.ai.kr
dig +short AAAA api.newslab.ai.kr
```

Expected DNS:

```text
A     152.67.211.33
AAAA  no record
```

Confirm the existing issuer and Ingress, then run the server-side dry-run:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get clusterissuer letsencrypt-prod
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress \
  news-api-ingress -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server \
  -f k8s/news-api.yaml
```

Apply the manifest only after the preflight checks pass:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-api.yaml
```

Verify the Ingress, certificate, ACME resources, and TLS Secret without
printing Secret data:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress \
  news-api-ingress -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress \
  news-api-ingress -o yaml | \
  rg -n "api.dev-scj.site|api.newslab.ai.kr|news-api-tls|news-api-newslab-tls|cluster-issuer"
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe certificate \
  news-api-newslab-tls
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get order,challenge
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret \
  news-api-newslab-tls
```

After `news-api-newslab-tls` reports `Ready=True`, verify both hosts:

```bash
curl -I https://api.newslab.ai.kr/health
curl -sS https://api.newslab.ai.kr/health
curl -I https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/health
```

Run repeated health checks to catch intermittent routing or TLS failures:

```bash
for i in {1..20}; do
  echo "---- new domain $i ----"
  curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" \
    https://api.newslab.ai.kr/health
done

for i in {1..20}; do
  echo "---- existing domain $i ----"
  curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" \
    https://api.dev-scj.site/health
done
```

Record the actual apply, Certificate, ACME, and HTTPS results in the task's
verification document. Do not mark production verification complete from the
manifest change alone.

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

## Daily Topic Pipeline Threshold Comparison

The following provider dry-runs are human-approved manual verification commands.
They do not include `--execute`, but they call embedding and summary providers.
Use `0.70` to inspect wider grouping and `0.72` as the initial operating
candidate. `0.78` remains a conservative comparison value.

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-070.md
```

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.72 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-072.md
```

## Daily Topic Pipeline CronJob

The `news-daily-topic-pipeline` CronJob runs at `04:00 Asia/Seoul`, after the
RSS collector and raw extractor schedules. It includes `--execute`, provider
flags, and bounded topic/article limits. Each Job has a 30-minute active
deadline and runs Python in unbuffered mode. Applying, manually running,
disabling, or deleting this CronJob is a human-controlled production operation.

Apply the CronJob after review:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply \
  -f k8s/news-daily-topic-pipeline-cronjob.yaml
```

Check the CronJob:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob \
  news-daily-topic-pipeline -n default
```

Create a manual verification Job:

```bash
JOB_NAME=news-daily-topic-pipeline-manual-$(date +%Y%m%d%H%M%S)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-daily-topic-pipeline \
  $JOB_NAME \
  -n default
```

Check the manual Job and logs:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get job $JOB_NAME -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default job/$JOB_NAME
```

The logs identify the last started and completed pipeline stage using
secret-safe counts and selected article IDs. If a Job exceeds 30 minutes,
Kubernetes marks it failed; inspect the Job description and logs to identify
the last completed stage:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe job $JOB_NAME -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default job/$JOB_NAME
```

After reviewing the logs, verify the existing read API with a real topic ID:

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/home"
curl -sS "https://api.dev-scj.site/topics/<integer-topic-id>"
```

Use timing checks when comparing the archive API and the home payload API:

```bash
curl -sS -o /dev/null -w 'topics page_size=10: %{time_total}s\n' \
  'https://api.dev-scj.site/topics?page=1&page_size=10'
curl -sS -o /dev/null -w 'topics home: %{time_total}s\n' \
  'https://api.dev-scj.site/topics/home'
```

`/topics/home` is intended for the frontend home screen. It returns a bounded
topic card payload and does not replace `/topics` for archive browsing or
`/topics/{id}` for detail views.

Clean up the manual Job:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME -n default
```

Disable or re-enable the schedule without deleting the manifest:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob \
  news-daily-topic-pipeline \
  -n default \
  -p '{"spec":{"suspend":true}}'

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob \
  news-daily-topic-pipeline \
  -n default \
  -p '{"spec":{"suspend":false}}'
```

Rollback by disabling the schedule first. Delete the CronJob only when the
human operator explicitly decides to remove the automation:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete cronjob \
  news-daily-topic-pipeline -n default
```

The existing `news-raw-extractor` CronJob remains unchanged. Suspending it is a
separate human decision after daily pipeline scheduled-run verification.

## Raw Extractor CronJob

Human-controlled operation.

Suspend the existing raw extractor CronJob only after the daily topic pipeline
has been verified and the human operator decides to stop broad scheduled raw
extraction:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob news-raw-extractor \
  -n default \
  -p '{"spec":{"suspend":true}}'
```

Verify the suspend state:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor -n default
```

This is a human-controlled operation. Do not delete the existing CronJob
manifest or raw extractor code.

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
