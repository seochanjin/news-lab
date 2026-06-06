# Task: K3s 모니터링 기본 구성

## Goal

NewsLab hybrid K3s cluster의 master, Oracle ARM worker, Raspberry Pi worker 상태를 Grafana에서 확인할 수 있도록 Prometheus/Grafana 기반 monitoring baseline을 구성한다.

이번 작업의 목표는 완성형 관측성 시스템이 아니라, 최소 리소스로 node/pod CPU·memory 상태를 볼 수 있는 기본 모니터링 환경을 만드는 것이다.

## Scope

- Prometheus/Grafana 최소 구성을 검토하고 설치한다.
- Alertmanager는 이번 단계에서 제외한다.
- Prometheus retention은 짧게 설정한다.
- Prometheus/Grafana resource request/limit을 낮게 설정한다.
- Monitoring stack 본체는 Raspberry Pi가 아니라 Oracle ARM worker에 배치한다.
- Raspberry Pi worker는 monitoring target으로 포함한다.
- node-exporter, kube-state-metrics를 통해 node/pod 상태를 확인한다.
- Grafana 접속 방법을 기록한다.
- 설치 후 news-api가 계속 2/2 Running인지 확인한다.

## Do not change

- Do not modify application source code.
- Do not modify DB schema or Supabase SQL.
- Do not modify existing news-api, extractor, collector manifests unless explicitly required.
- Do not expose secrets, kubeconfig, tokens, SSH keys, `.env`, Grafana password, or credentials.
- Do not deploy Alertmanager in this task.
- Do not configure external notification channels in this task.

## Expected files

- k8s/monitoring/kube-prometheus-stack-values.yaml
  - kube-prometheus-stack 최소 설치 values 파일
  - Alertmanager 비활성화
  - Prometheus 짧은 retention 설정
  - Prometheus/Grafana resource request/limit 설정
  - Prometheus/Grafana를 observability=true node에 배치
  - Pi worker taint를 허용하기 위한 node-exporter toleration 설정
- docs/verification/infra-monitoring-baseline.md
  - 실제 실행한 설치/검증 명령과 결과 기록
- docs/pr/infra-monitoring-baseline.md
  - PR 설명 초안
- docs/devlog/infra-monitoring-baseline.md
  - 작업 기록 및 대안 검토
- docs/fixes/infra-monitoring-baseline-approved-fixes.md
  - review 후 승인된 fixes 기록
- docs/reviews/infra-monitoring-baseline-antigravity.md
  - Antigravity review 결과 기록
- docs/reviews/infra-monitoring-baseline-coderabbit.md
  - CodeRabbit review 결과 기록

## DB changes

- None.
- Supabase SQL, DB schema, migration은 변경하지 않는다.

## API changes

- None.
- FastAPI route, response schema, application behavior는 변경하지 않는다.
- 기존 news-api는 monitoring 설치 후에도 2/2 Running 상태를 유지해야 한다.

## Test commands

Baseline checks before installation:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
```

Node label check:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl label node arm-worker-node observability=true --overwrite
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get node arm-worker-node --show-labels
```

Helm checks:

```bash
helm version
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm search repo prometheus-community/kube-prometheus-stack
```

Manifest review before install:

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
```

Install or upgrade:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create namespace monitoring --dry-run=client -o yaml | \
  KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f -

helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
```

Post-install verification:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
```

Grafana local access check:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

External API regression checks:

```bash
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/extractor/status
```

Static checks:

```bash
git diff --check
git diff -- app db scripts/collect_rss.py scripts/extract_raw_articles.py
git grep -n -i -E "K3S_TOKEN|node-token|password|private key|BEGIN|ssh-key"
```

## Acceptance criteria

- Monitoring namespace exists.
- Prometheus and Grafana Pods are Running.
- Monitoring stack core Pods are scheduled on `arm-worker-node`, not `pi-worker-node`.
- `kubectl top nodes` or equivalent metrics check works.
- Grafana can be accessed through a safe local method such as port-forward.
- Grafana shows node-level CPU/memory metrics for:
  - arm-master-node
  - arm-worker-node
  - pi-worker-node
- `news-api` remains `2/2` available after installation.
- Verification log records only commands actually run.
- Actual Tailscale IPs, node tokens, Grafana password, kubeconfig content, and SSH key paths are not committed.

## Notes

- This task is production-impacting because it installs monitoring components into the live K3s cluster.
- Keep the first installation small. Long-term retention, Alertmanager, Loki/log collection, external notification channels, and Pi temperature metrics are deferred.
- Prometheus stores time-series data locally inside its storage volume. Grafana only visualizes data from Prometheus.
- metrics-server is used for lightweight kubectl top checks and is not a long-term metrics database.
- kube-state-metrics exposes Kubernetes object state such as Deployment replica status, Pod phase, Job status, and Node condition.
- node-exporter should run on each node to expose CPU, memory, disk, and network metrics. Since pi-worker-node has a NoSchedule taint, node-exporter needs a toleration to run there.
- Prometheus/Grafana core Pods should be scheduled on arm-worker-node, not pi-worker-node.
- Grafana credentials must not be committed. Use a generated/admin password from Kubernetes Secret only when needed for local login.
- If monitoring installation causes news-api instability or excessive resource usage, reduce retention/resources or uninstall the stack and record the result.
