# Verification: 본문 추출 CronJob 구성

## Verification Scope

- Static repository-level verification only.
- No Kubernetes apply, rollout, manual Job creation, Supabase SQL, or data-writing script was run.

## Commands Run

```bash
ruby -e 'require "yaml"; ARGV.each { |file| YAML.load_file(file); puts "OK #{file}" }' k8s/news-raw-extractor-cronjob.yaml k8s/news-rss-collector-cronjob.yaml
```

```bash
git diff --check
```

```bash
git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml
```

```bash
git status --short
```

## Results

- YAML parse check passed:

```text
OK k8s/news-raw-extractor-cronjob.yaml
OK k8s/news-rss-collector-cronjob.yaml
```

- `git diff --check` completed with exit code 0 and no output.
- `git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml` completed with exit code 0 and no output, confirming this task did not modify FastAPI app code, DB files, scripts, or the existing RSS collector CronJob manifest.
- `git status --short` output:

```text
 M docs/RUNBOOK.md
?? docs/devlog/feature-raw-extractor-cronjob.md
?? docs/fixes/feature-raw-extractor-cronjob-approved-fixes.md
?? docs/pr/feature-raw-extractor-cronjob.md
?? docs/reviews/feature-raw-extractor-cronjob-antigravity.md
?? docs/reviews/feature-raw-extractor-cronjob-coderabbit.md
?? docs/tasks/feature-raw-extractor-cronjob.md
?? docs/verification/feature-raw-extractor-cronjob.md
?? k8s/news-raw-extractor-cronjob.yaml
```

- The untracked task/review/fix/PR/devlog files were already present before implementation and were not modified by this task, except for `docs/verification/feature-raw-extractor-cronjob.md`.

## Manual or Production Verification

- Pending human execution.
- Production/K3s verification has not been performed by the agent.

## Pending Verification

- Human operator should review and apply `k8s/news-raw-extractor-cronjob.yaml`.
- Suggested pending commands:

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

## Evidence Notes

- Completed command results must be added only after actual output is available.
