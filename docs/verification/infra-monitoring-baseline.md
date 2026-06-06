# Verification: K3s 모니터링 기본 구성

## Verification Scope

- Agent가 로컬 저장소에서 Helm values 정적 검증과 manifest 렌더링을 수행했다.
- Agent는 K3s cluster에 접근하거나 node label, namespace, Helm release를 변경하지 않았다.
- Production 설치와 설치 후 상태 확인은 human operator가 수행했으며, 제공된 sanitized 결과를 이 문서에 기록했다.

## Commands Run

### Helm client and repository checks

Commands:

```bash
helm version --short
helm repo list
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm search repo prometheus-community/kube-prometheus-stack --versions | sed -n '1,8p'
```

Results:

```text
Helm version: v4.2.0+g0646808
Initial repository list: no repositories to show
prometheus-community repository add: succeeded
prometheus-community repository update: succeeded
Latest kube-prometheus-stack chart found: 86.2.0
```

### Values YAML parse check

Command:

```bash
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'
```

Result:

```text
YAML parse: OK
```

### Helm manifest render check

Command:

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml && echo 'helm template: OK'
```

Result:

```text
helm template: OK
```

The rendered output was written only to `/tmp` and was not committed.

### Rendered manifest assertions

Command:

```bash
ruby -ryaml -e 'docs=YAML.load_stream(File.read(ARGV[0])).compact; find=->(kind,name){docs.find{|d| d["kind"]==kind && d.dig("metadata","name")==name}}; raise "Alertmanager rendered" if docs.any?{|d| d["kind"]=="Alertmanager"}; %w[monitoring-grafana monitoring-kube-state-metrics monitoring-kube-prometheus-operator].each{|name| d=find.call("Deployment",name) or raise "missing #{name}"; raise "bad nodeSelector #{name}" unless d.dig("spec","template","spec","nodeSelector","observability")=="true"}; g=find.call("Deployment","monitoring-grafana"); gc=g.dig("spec","template","spec","containers").find{|c| c["name"]=="grafana"}; raise "bad Grafana resources" unless gc.dig("resources","requests","memory")=="256Mi" && gc.dig("resources","limits","memory")=="512Mi"; p=find.call("Prometheus","monitoring-kube-prometheus-prometheus") or raise "missing Prometheus"; raise "bad Prometheus settings" unless p.dig("spec","retention")=="1d" && p.dig("spec","nodeSelector","observability")=="true" && p.dig("spec","resources","requests","memory")=="256Mi" && p.dig("spec","resources","limits","memory")=="512Mi"; n=find.call("DaemonSet","monitoring-prometheus-node-exporter") or raise "missing node-exporter"; raise "missing Pi toleration" unless n.dig("spec","template","spec","tolerations").any?{|t| t["key"]=="node-role" && t["value"]=="news-edge-worker"}; puts "Rendered manifest assertions: OK"' /tmp/infra-monitoring-baseline-rendered.yaml
```

Result:

```text
Rendered manifest assertions: OK
```

The assertions confirmed:

- No `Alertmanager` custom resource was rendered.
- Grafana, kube-state-metrics, Prometheus Operator, and Prometheus select `observability=true`.
- Prometheus retention is `1d`.
- Prometheus and Grafana memory request/limit values were rendered as configured.
- node-exporter includes the `node-role=news-edge-worker:NoSchedule` Pi toleration.

### Application and database scope check

Command:

```bash
git diff -- app db scripts/collect_rss.py scripts/extract_raw_articles.py
```

Result:

```text
No output. Exit code 0.
```

### Static checks

Commands:

```bash
git diff --check
git grep -n -i -E 'K3S_TOKEN|node-token|password|private key|BEGIN|ssh-key'
rg -n -i 'K3S_TOKEN|node-token|adminPassword|BEGIN (RSA|OPENSSH|PRIVATE)|ssh-(rsa|ed25519)' \
  k8s/monitoring \
  docs/verification/infra-monitoring-baseline.md \
  docs/pr/infra-monitoring-baseline.md \
  docs/devlog/infra-monitoring-baseline.md \
  docs/tasks/infra-monitoring-baseline.md
rg -n '[[:blank:]]+$' \
  k8s/monitoring/kube-prometheus-stack-values.yaml \
  docs/verification/infra-monitoring-baseline.md \
  docs/pr/infra-monitoring-baseline.md \
  docs/devlog/infra-monitoring-baseline.md
```

Results:

- `git diff --check`: no output, exit code 0.
- `git grep`: existing repository references only, including a GitHub Actions secret expression, a redacted `<NODE_TOKEN>`, and Python `engine.begin()` false positives.
- Targeted new-file credential scan: only the task document's static-check command matched; no credential value matched.
- Trailing whitespace scan: no output.

## Results

- `k8s/monitoring/kube-prometheus-stack-values.yaml` parses successfully.
- kube-prometheus-stack chart `86.2.0` renders successfully with the values file.
- Rendered manifest assertions for Alertmanager disablement, core placement, retention, and Pi toleration passed.
- Application source, DB files, and data-writing scripts were not modified.
- Production verification results below were provided by the human operator.

## Approved Fix Verification

The following commands were run after applying the approved fixes.

### YAML and pinned Helm render

Commands:

```bash
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml
```

Results:

```text
YAML parse: OK
helm template: OK
```

### Current rendered manifest assertions

Command:

```bash
ruby -ryaml -e 'docs=YAML.load_stream(File.read(ARGV[0])).compact; find=->(kind,name){docs.find{|d| d["kind"]==kind && d.dig("metadata","name")==name}}; raise "Alertmanager rendered" if docs.any?{|d| d["kind"]=="Alertmanager"}; %w[monitoring-grafana monitoring-kube-state-metrics monitoring-kube-prometheus-operator].each{|name| d=find.call("Deployment",name) or raise "missing #{name}"; raise "bad nodeSelector #{name}" unless d.dig("spec","template","spec","nodeSelector","observability")=="true"}; g=find.call("Deployment","monitoring-grafana"); gc=g.dig("spec","template","spec","containers").find{|c| c["name"]=="grafana"}; raise "bad Grafana resources" unless gc.dig("resources","requests","memory")=="256Mi" && gc.dig("resources","limits","memory")=="512Mi"; p=find.call("Prometheus","monitoring-kube-prometheus-prometheus") or raise "missing Prometheus"; raise "bad Prometheus settings" unless p.dig("spec","retention")=="1d" && p.dig("spec","nodeSelector","observability")=="true" && p.dig("spec","resources","requests","memory")=="256Mi" && p.dig("spec","resources","limits","memory")=="512Mi"; n=find.call("DaemonSet","monitoring-prometheus-node-exporter") or raise "missing node-exporter"; raise "missing Pi toleration" unless n.dig("spec","template","spec","tolerations").any?{|t| t["key"]=="node-role" && t["value"]=="news-edge-worker"}; puts "Rendered manifest assertions: OK"' /tmp/infra-monitoring-baseline-rendered.yaml
```

Result:

```text
Rendered manifest assertions: OK
```

### Scope and static checks

Commands and results:

- `git diff -- app db scripts/collect_rss.py scripts/extract_raw_articles.py`: no output, exit code 0.
- `git grep -n -E '100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+'`: no output, exit code 1 because no IP pattern matched.
- `git grep -n -i -E 'K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key'`: matched existing safe references, redacted placeholders, verification command text, and Python `engine.begin()` false positives; no credential value was found.
- `git diff --check`: exit code 2 because `docs/reviews/infra-monitoring-baseline-antigravity.md` contains two pre-existing trailing-whitespace findings. The review artifact was not modified because review output is outside the approved fix scope.
- `git diff --check -- k8s/monitoring/kube-prometheus-stack-values.yaml docs/verification/infra-monitoring-baseline.md docs/pr/infra-monitoring-baseline.md docs/devlog/infra-monitoring-baseline.md docs/fixes/infra-monitoring-baseline-approved-fixes.md`: no output, exit code 0.

## Manual or Production Verification

Status: Completed by human operator for the recorded installation and post-install checks.

Recorded install command shape:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl label node arm-worker-node observability=true --overwrite

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create namespace monitoring --dry-run=client -o yaml | \
  KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f -

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --kubeconfig ~/.kube/oci-k3s.yaml \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
```

Recorded post-install check commands:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
```

Safe local Grafana access:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward \
  -n monitoring svc/monitoring-grafana 3000:80
```

Then open `http://127.0.0.1:3000`. Grafana credential retrieval is a local operator action; no credential value is recorded in this repository.

## Pending Verification

- Grafana shows node-level CPU and memory metrics for all three nodes.
- Read-only external API regression checks succeed if the human operator chooses to run them.

## Evidence Notes

- No `kubectl`, Helm install/upgrade, production `curl`, rollout, push, or merge command was run by the agent.
- Production verification claims below are limited to sanitized results provided by the human operator.

## Production Verification Results

Monitoring stack was installed into the `monitoring` namespace.

Final monitoring Pod status:

- `monitoring-grafana`: `3/3 Running` on `arm-worker-node`
- `monitoring-kube-prometheus-operator`: `1/1 Running` on `arm-worker-node`
- `monitoring-kube-state-metrics`: `1/1 Running` on `arm-worker-node`
- `prometheus-monitoring-kube-prometheus-prometheus-0`: `2/2 Running` on `arm-worker-node`
- `monitoring-prometheus-node-exporter`: `1/1 Running` on all three nodes:
  - `arm-master-node`
  - `arm-worker-node`
  - `pi-worker-node`

`news-api` remained available:

```text
news-api   2/2   2   2
```

Post-install resource check:

```text
arm-master-node   CPU 85m   Memory 1532Mi
arm-worker-node   CPU 62m   Memory 1377Mi
pi-worker-node    CPU 32m   Memory 491Mi
```

The monitoring stack increased resource usage but did not disrupt news-api.

### Grafana container-level resource check

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pod -n monitoring \
  monitoring-grafana-84749cf497-lnrqh \
  --containers
```

Result:

```text
grafana                  150Mi
grafana-sc-dashboard      75Mi
grafana-sc-datasources    74Mi
```

The Grafana container stayed below the updated 512Mi memory limit.

### Final monitoring Pod status

- monitoring-grafana: 3/3 Running, restart count 0
- monitoring-kube-prometheus-operator: 1/1 Running, restart count 0
- monitoring-kube-state-metrics: 1/1 Running, restart count 0
- prometheus-monitoring-kube-prometheus-prometheus-0: 2/2 Running, restart count 0
- monitoring-prometheus-node-exporter: running on all three nodes

Application regression check

news-api remained available:

```text
news-api   2/2   2   2
```
