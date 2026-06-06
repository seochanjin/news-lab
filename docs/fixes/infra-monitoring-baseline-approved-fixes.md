# Approved Fixes: K3s 모니터링 기본 구성

## Approved Fixes

### 1. Grafana resource values consistency fix

Approve fixing all documentation and verification references to match the deployed values file.

Canonical Grafana resource values:

```yaml
requests:
  cpu: 50m
  memory: 256Mi
limits:
  cpu: 300m
  memory: 512Mi
```

Reason:

- Initial Grafana memory limit `256Mi` caused `OOMKilled` during UI access.
- The limit was increased to `512Mi`.
- The new Grafana Pod stayed `3/3 Running` with restart count `0`.
- Container-level metrics showed the `grafana` container using about `150Mi`, while sidecar containers used about `75Mi` each.

Files to align:

- `k8s/monitoring/kube-prometheus-stack-values.yaml`
- `docs/verification/infra-monitoring-baseline.md`
- `docs/pr/infra-monitoring-baseline.md`
- `docs/devlog/infra-monitoring-baseline.md`

### 2. Prometheus retention consistency fix

Approve fixing all documentation references to match the deployed values file.

Canonical Prometheus retention value:

```yaml
retention: 1d
```

Reason:

- This task intentionally uses short retention for a lightweight monitoring baseline.
- `3d` references in PR/devlog are stale and should be corrected to `1d`.

Files to align:

- `docs/verification/infra-monitoring-baseline.md`
- `docs/pr/infra-monitoring-baseline.md`
- `docs/devlog/infra-monitoring-baseline.md`

### 3. Rendered manifest assertion fix

Approve updating the verification assertion command so it checks the current intended values.

Expected assertion values:

- Alertmanager custom resource is not rendered.
- Grafana, kube-state-metrics, Prometheus Operator, and Prometheus select `observability=true`.
- Grafana memory request is `256Mi`.
- Grafana memory limit is `512Mi`.
- Prometheus retention is `1d`.
- Prometheus memory request is `256Mi`.
- Prometheus memory limit is `512Mi`.
- node-exporter includes the Pi worker toleration for `node-role=news-edge-worker:NoSchedule`.

Reason:

- The previous assertion text expected older Grafana values and no longer matched the actual values file after the OOM fix.

### 4. Production verification status fix

Approve normalizing the production verification section.

Required final state:

- Production installation and post-install verification should be marked as completed only for commands actually run by the human operator.
- Earlier “Pending human operator execution” text should be replaced or moved so it does not contradict completed installation evidence.
- Production results should include only sanitized outputs and node names, not raw Tailscale/private LAN IP addresses.
- Grafana credential retrieval should be recorded only as a local action; credential values must not be recorded.

Reason:

- The monitoring stack was actually installed and verified after the initial pending section was written.
- The verification document must reflect the final timeline honestly.

### 5. Helm chart version pinning

Approve adding `--version 86.2.0` to documented Helm install/upgrade commands.

Reason:

- The rendered verification used kube-prometheus-stack chart `86.2.0`.
- Pinning the chart version prevents future installs from silently using a different chart version.

Example command shape:

```bash
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --kubeconfig ~/.kube/oci-k3s.yaml \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
```

## Rejected or Deferred Suggestions

### Add PVC for Prometheus storage

Deferred.

Reason:

- This task is a lightweight monitoring baseline.
- Prometheus data persistence is useful, but PVC/storage policy should be handled in a later task after baseline stability is confirmed.
- Current short retention and ephemeral storage are accepted tradeoffs.

### Enable Alertmanager

Rejected for this task.

Reason:

- Alertmanager and external notification channels are explicitly out of scope.
- Alerting should be handled in a later observability task.

### Add Pi temperature metric

Deferred.

Reason:

- Pi temperature monitoring is useful but not required for the current CPU/memory monitoring baseline.
- This should be handled separately using node-exporter textfile collector or a small custom exporter.

## Applied Changes

Applied by the implementation agent.

1. Grafana resource values consistency fix
   - Updated `k8s/monitoring/kube-prometheus-stack-values.yaml` to the approved Grafana values:
     - request: `50m`, `256Mi`
     - limit: `300m`, `512Mi`
   - Aligned verification, PR draft, and devlog references.
2. Prometheus retention consistency fix
   - Aligned verification, PR draft, and devlog references to `1d`.
3. Rendered manifest assertion fix
   - Updated the verification assertion to check Grafana `256Mi` request and `512Mi` limit, Prometheus `1d` retention and approved memory values, core placement, Alertmanager disablement, and Pi toleration.
4. Production verification status fix
   - Removed the contradictory pending installation status.
   - Kept only sanitized human-provided production results as completed evidence.
   - Left Grafana dashboard metric confirmation and optional external API checks pending because no direct evidence was provided.
5. Helm chart version pinning
   - Added `--version 86.2.0` to documented Helm render and install/upgrade commands.

No rejected or deferred suggestion was applied.

## Verification Required

After applying the fixes, run:

```bash
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'
```

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml
```

```bash
ruby -ryaml -e 'docs=YAML.load_stream(File.read(ARGV[0])).compact; find=->(kind,name){docs.find{|d| d["kind"]==kind && d.dig("metadata","name")==name}}; raise "Alertmanager rendered" if docs.any?{|d| d["kind"]=="Alertmanager"}; %w[monitoring-grafana monitoring-kube-state-metrics monitoring-kube-prometheus-operator].each{|name| d=find.call("Deployment",name) or raise "missing #{name}"; raise "bad nodeSelector #{name}" unless d.dig("spec","template","spec","nodeSelector","observability")=="true"}; g=find.call("Deployment","monitoring-grafana"); gc=g.dig("spec","template","spec","containers").find{|c| c["name"]=="grafana"}; raise "bad Grafana resources" unless gc.dig("resources","requests","memory")=="256Mi" && gc.dig("resources","limits","memory")=="512Mi"; p=find.call("Prometheus","monitoring-kube-prometheus-prometheus") or raise "missing Prometheus"; raise "bad Prometheus settings" unless p.dig("spec","retention")=="1d" && p.dig("spec","nodeSelector","observability")=="true" && p.dig("spec","resources","requests","memory")=="256Mi" && p.dig("spec","resources","limits","memory")=="512Mi"; n=find.call("DaemonSet","monitoring-prometheus-node-exporter") or raise "missing node-exporter"; raise "missing Pi toleration" unless n.dig("spec","template","spec","tolerations").any?{|t| t["key"]=="node-role" && t["value"]=="news-edge-worker"}; puts "Rendered manifest assertions: OK"' /tmp/infra-monitoring-baseline-rendered.yaml
```

```bash
git diff --check
```

```bash
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
```

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key"
```
