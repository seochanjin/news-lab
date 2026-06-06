# Task: Raspberry Pi worker join and hybrid K3s network standardization

## Purpose

Add a Raspberry Pi worker node to the NewsLab K3s cluster and standardize hybrid node networking so that Oracle Cloud nodes and home-lab nodes communicate through Tailscale.

## Background

The cluster originally used OCI private IPs for Oracle nodes:

- `arm-master-node`: `10.x.x.x`
- `arm-worker-node`: `10.x.x.x`

When the Raspberry Pi worker was added from a home network, the cluster became a hybrid environment. The first Pi join succeeded, but kubelet log access failed because node/control-plane traffic tried to use addresses that were not consistently reachable across networks.

## Scope

- Join Raspberry Pi as a K3s worker node.
- Configure Pi worker node to use its Tailscale IP as Kubernetes InternalIP.
- Configure K3s master to use Tailscale IP and `tailscale0`.
- Rejoin Oracle ARM worker with Tailscale IP and `tailscale0`.
- Restore node labels required by existing workloads.
- Add a taint to Pi worker so general workloads are not scheduled there by accident.
- Verify test Pods, `kubectl logs`, existing `news-api`, Ingress, and extractor status.

## Do Not Change

- Do not modify application source code.
- Do not modify DB schema or Supabase SQL.
- Do not modify Kubernetes manifests unless a later follow-up task requires persistence.
- Do not expose K3s node token, kubeconfig, SSH keys, `.env`, or secrets in Git/Notion/logs.

## Alternatives Considered

### Alternative A: Stop after Pi worker becomes Ready

- Pros: Smallest change.
- Cons: `kubectl logs` and operational verification remained broken.

### Alternative B: Add Tailscale subnet route for OCI private subnet

- Pros: Minimal fix for Pi access to `10.x.x.x:6443`.
- Cons: Mixed node networking remains: OCI nodes use VCN IPs, Pi uses Tailscale IP.

### Alternative C: Standardize all K3s node IPs and flannel interface on Tailscale

- Pros: Clean long-term hybrid cluster model.
- Pros: Easier to add more ARM/Pi/home-lab nodes later.
- Cons: Requires touching master and worker node networking.

## Chosen Approach

Alternative C was selected.

The goal shifted from simply joining a Pi worker to standardizing the hybrid K3s cluster networking model. Since the project is intended to be operated long-term and more external/home-lab nodes may be added later, using Tailscale as the common node network is more consistent than keeping mixed OCI private IP and home LAN IP behavior.

## Acceptance Criteria

- `kubectl get nodes -o wide` shows all nodes with Tailscale InternalIP.
- `pi-worker-node` is `Ready`.
- `arm-worker-node` is `Ready`.
- `kubectl logs` works for test Pods on Pi and Oracle worker.
- `news-api` Deployment returns to `2/2` available.
- External API checks succeed:
  - `curl https://api.dev-scj.site/health`
  - `curl https://api.dev-scj.site/extractor/status`
- Pi worker has a `NoSchedule` taint for edge/test workloads.
