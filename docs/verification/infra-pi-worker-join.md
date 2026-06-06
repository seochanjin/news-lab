# Verification: Raspberry Pi worker K3s join 검증

## Verification Scope

- Production K3s cluster operation.
- Raspberry Pi worker join.
- Hybrid node networking standardization to Tailscale InternalIP.
- Node scheduling and kubelet log proxy verification.
- Existing News API recovery verification.

## Commands Run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl run pi-worker-test \
  --image=busybox:1.36 \
  --restart=Never \
  --overrides='{"spec":{"nodeSelector":{"hardware":"raspberry-pi"},"containers":[{"name":"pi-worker-test","image":"busybox:1.36","command":["sh","-c","hostname && uname -a && sleep 60"]}]}}'

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs pi-worker-test

sudo cat /etc/rancher/k3s/config.yaml
sudo systemctl restart k3s
sudo k3s kubectl get nodes -o wide

sudo /usr/local/bin/k3s-agent-uninstall.sh

curl -sfL https://get.k3s.io | \
  K3S_URL=https://100.79.184.11:6443 \
  K3S_TOKEN='<NODE_TOKEN>' \
  INSTALL_K3S_EXEC='agent --node-name arm-worker-node --node-ip 100.117.78.65 --flannel-iface tailscale0 --node-label node-role=oracle-arm-worker --node-label network=tailscale --node-label location=oci' \
  sh -

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl label node arm-worker-node node-role.kubernetes.io/worker= --overwrite
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl label node pi-worker-node node-role.kubernetes.io/worker= --overwrite
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl label node arm-worker-node workload=app --overwrite

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl run arm-worker-test \
  --image=busybox:1.36 \
  --restart=Never \
  --overrides='{"spec":{"nodeSelector":{"node-role":"oracle-arm-worker"},"containers":[{"name":"arm-worker-test","image":"busybox:1.36","command":["sh","-c","hostname && uname -a && sleep 30"]}]}}'

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs arm-worker-test

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl taint node pi-worker-node \
  node-role=news-edge-worker:NoSchedule

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete pod -n cert-manager \
  -l app.kubernetes.io/instance=cert-manager

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/extractor/status
```

## Results

### Final node state

```text
arm-master-node   Ready   control-plane   INTERNAL-IP 100.79.184.11
arm-worker-node   Ready   worker          INTERNAL-IP 100.117.78.65
pi-worker-node    Ready   worker          INTERNAL-IP 100.92.105.106
```

### Pi worker test

pi-worker-test was scheduled to pi-worker-node and kubectl logs succeeded.

```text
pi-worker-test
Linux pi-worker-test 6.8.0-1053-raspi ... aarch64 GNU/Linux
```

### Oracle ARM worker test

arm-worker-test was scheduled to arm-worker-node and kubectl logs succeeded.

```text
arm-worker-test
Linux arm-worker-test 6.17.0-1014-oracle ... aarch64 GNU/Linux
```

### News API scheduling recovery

After arm-worker-node was rejoined, news-api Pods were initially Pending.

Root cause:

```text
news-api Deployment has nodeSelector workload=app.
arm-worker-node lost the workload=app label during rejoin.
```

Fix:

```bash
kubectl label node arm-worker-node workload=app --overwrite
```

Result:

```text
news-api   2/2   2   2
```

### Pi taint

pi-worker-node has the following taint:

```text
node-role=news-edge-worker:NoSchedule
```

This prevents general workloads from being scheduled onto the Pi unless they explicitly tolerate the taint.

### Cert-manager placement

cert-manager Pods were recreated after the Pi taint was added. Final state:

```text
cert-manager              Running   arm-master-node
cert-manager-cainjector   Running   arm-worker-node
cert-manager-webhook      Running   arm-worker-node
```

### External API verification

```bash
curl https://api.dev-scj.site/health
```

Result:

```json
{
  "status": "ok",
  "service": "news-api",
  "hostname": "news-api-6df6794796-zqwbk"
}
```

```bash
curl https://api.dev-scj.site/extractor/status
```

Result:

```json
{
  "status": "success",
  "latest_run": {
    "id": 3,
    "status": "success",
    "success_count": 5,
    "failed_count": 0
  }
}
```

### Issues Found

Initial Pi kubelet log access failure

The Pi worker initially joined with home LAN IP 192.168.1.121, causing kubectl logs to fail because the Oracle control plane could not reach the home LAN address.

Remotedialer attempted OCI private IP

After rejoining the Pi with Tailscale IP, the K3s remotedialer still attempted to connect to 10.0.0.107:6443, which is not reachable from the home network.

The master was updated to use Tailscale IP and tailscale0, after which the Pi agent connected to:

```text
wss://100.79.184.11:6443/v1-k3s/connect
```

Lost workload label after worker rejoin

arm-worker-node lost the manually applied workload=app label after rejoin, causing news-api Pods to remain Pending. The label was restored.

## Manual or Production Verification

## Pending Verification

- Long-running stability of Pi worker over home network.
- Behavior after Pi reboot or temporary home network disconnect.
- Whether cert-manager/system workloads should be explicitly pinned to Oracle nodes using affinity or nodeSelector.
- Whether Pi should run selected batch workloads with explicit tolerations.

## Evidence Notes

- K3s node token was used only during node join and must not be recorded in Git, Notion, PR, or verification logs.
- No application code or DB schema was changed.
