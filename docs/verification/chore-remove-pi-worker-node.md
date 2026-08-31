# Verification: Raspberry Pi worker node 정리

Branch: `chore/remove-pi-worker-node`

---

## 조사

### 제거 직전 Pi에 배치된 Pod

Command:

```bash
kubectl get pods -A -o wide --field-selector spec.nodeName=pi-worker-node
```

Result:

```text
kube-system  svclb-traefik-6146a7ed-74z4q                2/2  Running  4 (27d ago)  85d  10.42.4.10
monitoring   monitoring-prometheus-node-exporter-6sg75   1/1  Running  2 (27d ago)  85d  100.92.105.106
```

Status: passed — **Pod 2개, 둘 다 모든 노드에 배치되는 DaemonSet이다.**
이 노드에만 존재해야 하는 workload는 없다.

`svclb-traefik`은 k3s ServiceLB가 모든 노드에 두는 Pod로 해당 노드를 LoadBalancer
endpoint 후보로 만든다. 그러나 Pi는 가정용 NAT 뒤에 있고 공개 트래픽은 Public DNS와
Oracle Public IP를 거쳐 진입하므로 이 endpoint는 실제로 사용된 적이 없다.

> **최초 task·ADR 초안에는 "node-exporter 하나뿐"이라고 적었으나 실측은 2개였다.**
> 결론(전용 workload 없음)은 같지만 사실이 틀렸으므로 세 문서를 모두 교정했다.

### Dashboard 영향 조사

`k8s/monitoring/dashboards/news-lab-pipeline-operations.json`의 Cluster Nodes row는
노드명을 하드코딩하지 않는다.

```text
Node Ready              kube_node_status_condition{condition="Ready",status="true"} == 1
Node CPU Usage          node_cpu_seconds_total 기반, instance→node label join
Running Pods by Node    sum by(node) (...)
```

`grep -c "pi-worker-node"` 결과 0.

Status: passed — **Dashboard 수정은 불필요하다.** 노드가 빠지면 자동으로 2개만 표시된다.
로드맵의 "Cluster Nodes row 3노드 → 2노드" 항목은 실제로는 해당 사항이 없다.

---

## UNIT-01. Monitoring 설정 정리

### 구현 범위

- `k8s/monitoring/kube-prometheus-stack-values.yaml`
  — node-exporter의 `node-role=news-edge-worker` toleration 제거
- `k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`
  — `NewsLabNodeNotReady`의 node regex에서 `pi-worker-node` 제거

### 검증

Command:

```bash
python3 -c "import yaml; ..."   # YAML parse + toleration/regex assertion
grep -rn "pi-worker-node|news-edge-worker" k8s/ | wc -l
```

Result:

```text
YAML OK: k8s/monitoring/kube-prometheus-stack-values.yaml
YAML OK: k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
node-exporter tolerations: 2
  - node-role.kubernetes.io/control-plane
  - node-role.kubernetes.io/master
pi-worker-node 참조 없음 확인
manifest 내 Pi 참조: 0
```

Status: passed

---

## UNIT-02. 현재 상태 문서 현행화

- `README.md` — 3-node → 2-node, node-exporter toleration, 설계 결정 항목,
  문서 탐색의 링크 분류를 "운영 근거"에서 "과거 구성 이력"으로 이동
- `docs/ARCHITECTURE.md` — 노드 목록
- `docs/architecture/k3s-runtime.md` — 노드 표, node-exporter 배치, Tailscale 서술

**과거 기록은 수정하지 않았다.** `docs/verification/infra-pi-worker-join.md`,
`docs/fixes/infra-pi-worker-join-approved-fixes.md`,
`docs/design/pipeline-operations-dashboard.md`는 그 시점의 사실을 기록한 문서다.
지우면 19차 구성 경험이 이력에서 사라진다.

Status: passed — 링크 4건 유효성 확인 완료.

---

## UNIT-03. ADR

`docs/adr/0001-remove-pi-worker-node.md` 신규. `docs/adr/`의 첫 문서다.

명시한 것:

- **79차 장애는 Pi가 원인이 아니며 Pi를 제거해도 그 위험은 남는다.**
  `--flannel-iface tailscale0`은 Oracle node 사이 통신과 operator 경로에 계속
  사용되므로 유지한다. 따라서 이 결정의 근거를 "장애 위험 감소"로 서술하지 않는다.
- 일반화 경계. "Raspberry Pi는 서버로 부적합하다"가 아니라
  **"노드는 거기 있어야만 하는 이유가 있을 때 추가한다"**이다.
  물리적 위치가 요구사항인 영역에서 ARM SBC는 정당한 선택이다.
- 매각 전 재이미징이 필수인 이유. Pi에 k3s node token, Tailscale node key, SSH key가
  남아 있다. 79차에서 join token 회전을 보류한 근거가 "API server는 Tailscale
  내부에서만 접근 가능하다"였는데, Tailscale 상태 파일이 남은 기기를 타인에게
  넘기면 그 전제가 깨진다.

Status: passed

---

## 노드 제거 (사람 수행)

Command:

```bash
kubectl drain pi-worker-node --ignore-daemonsets
kubectl delete node pi-worker-node
kubectl get nodes
kubectl get pods -n monitoring -o wide | grep node-exporter
```

Result:

```text
node/pi-worker-node cordoned
Warning: ignoring DaemonSet-managed Pods: kube-system/svclb-traefik-...,
         monitoring/monitoring-prometheus-node-exporter-...
node/pi-worker-node drained
node "pi-worker-node" deleted

NAME              STATUS   ROLES           AGE   VERSION
arm-master-node   Ready    control-plane   98d   v1.35.5+k3s1
arm-worker-node   Ready    worker          85d   v1.35.5+k3s1

monitoring-prometheus-node-exporter-ks26g   1/1  Running  0  85d  arm-worker-node
monitoring-prometheus-node-exporter-qvdmd   1/1  Running  0  85d  arm-master-node
```

Status: passed — 노드 2개, node-exporter 2개.

Notes:

- `delete node` 직후에는 삭제된 노드의 node-exporter Pod 객체가 남아 있었다.
  Pod GC 컨트롤러가 수 분 내에 정리했다. **강제 삭제는 사용하지 않았다.**
- 노드가 재등록되지 않았다.

---

## Pi에서 k3s agent 제거 (사람 수행)

Command:

```bash
sudo /usr/local/bin/k3s-agent-uninstall.sh
```

Result (요약):

```text
systemctl stop k3s-agent.service
killtree ...                              containerd task 정리
do_unmount_and_remove /run/k3s            containerd mount 해제
do_unmount_and_remove /var/lib/kubelet/*
ip link delete cni0
ip link delete flannel.1                  Cannot find device "flannel.1"
tailscale set --advertise-routes=         광고 route 해제
iptables-save | grep -v KUBE-/CNI-/flannel | iptables-restore
systemctl disable k3s-agent               Removed multi-user.target.wants 링크
rm -f /etc/systemd/system/k3s-agent.service{,.env}
rm -rf /etc/rancher/k3s /run/k3s /run/flannel
rm -rf /var/lib/rancher/k3s /var/lib/kubelet
rm -f /usr/local/bin/{k3s,kubectl,crictl,ctr,k3s-killall.sh}
```

Status: passed — service가 disable되고 binary와 상태 디렉터리가 제거됐다.
**노드는 재등록되지 않는다.**

Notes:

- `Cannot find device "flannel.1"`은 오류가 아니다. 이미 존재하지 않는 인터페이스를
  지우려 한 것이며 uninstall script의 정상 경로다.
- script가 `tailscale set --advertise-routes=`를 실행해 광고 route를 해제했다.
  **Tailscale 자체는 로그인 상태로 남아 있다.**
- `/etc/rancher/k3s`는 제거됐으나 node token이 있는 `/etc/rancher/node/`는 script
  대상이 아닐 수 있다. 매각 전 재이미징으로 처리한다.

---

## 매각 범위와 자격증명 처리

**보드만 매각하고 저장 매체(SD/USB)는 보관한다.**

따라서 매각 전 재이미징은 불필요하다. k3s node token, Tailscale node key, SSH key는
모두 저장 매체 안에 있고 그 매체는 양도하지 않는다. Raspberry Pi 5 보드의
비휘발성 저장소는 부트로더 EEPROM뿐이며 부팅 설정만 보관한다.

> 최초 절차 초안은 저장 매체를 함께 양도하는 것으로 가정해 재이미징을 필수로
> 기재했다. 매각 범위를 확인하지 않고 세운 전제였다. 실제 범위에 맞춰 정정한다.
> 저장 매체를 함께 양도하는 경우에는 재이미징이 여전히 필수다.

---

## Monitoring 설정 운영 적용 (사람 수행)

### chart 버전 고정

Command:

```bash
helm list -n monitoring
```

Result:

```text
monitoring  monitoring  4  deployed  kube-prometheus-stack-86.2.0  v0.91.0
```

**`--version 86.2.0`을 명시해 upgrade했다.** 버전을 생략하면 저장소의 최신 chart를
받아오므로, toleration 두 줄을 지우려던 작업이 kube-prometheus-stack 전체 버전
업그레이드가 된다. CRD 변경 시 Prometheus·Grafana·Alertmanager가 모두 영향을 받는다.

### dry-run 검증

Command:

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --dry-run=server --hide-secret > /tmp/monitoring-dry.yaml

grep -c "news-edge-worker" /tmp/monitoring-dry.yaml
grep -A 12 "^      tolerations:" /tmp/monitoring-dry.yaml | head -20
```

Result:

```text
0

      tolerations:
        - effect: NoSchedule
          key: node-role.kubernetes.io/control-plane
          operator: Exists
        - effect: NoSchedule
          key: node-role.kubernetes.io/master
          operator: Exists
```

Status: passed — 렌더링 결과에 `news-edge-worker` 참조가 없고, control-plane과
master toleration 2개는 유지된다. **후자가 사라지면 master 노드에서 node-exporter가
동작하지 않아 노드 지표가 하나 비게 되므로 함께 확인했다.**

### 적용

Command:

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
kubectl apply -f k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
kubectl get pods -n monitoring -o wide | grep node-exporter
rm -f /tmp/monitoring-dry.yaml
```

Result:

```text
Release "monitoring" has been upgraded. Happy Helming!
STATUS: deployed
REVISION: 5

prometheusrule.monitoring.coreos.com/news-lab-pipeline-alerts configured

monitoring-prometheus-node-exporter-8jwpb  1/1  Running  0  36s  arm-master-node
monitoring-prometheus-node-exporter-m8ct8  1/1  Running  0  38s  arm-worker-node
```

Status: passed

Notes:

- chart 버전이 86.2.0으로 유지됐다(REVISION만 4 → 5).
- toleration 변경으로 node-exporter Pod 2개가 재생성됐다(age 36s, 38s).
- **임시 dry-run 파일을 삭제했다.** 75차에서 helm manifest diff 과정에 Grafana
  admin password가 노출된 이후 Runbook에 정한 절차다. `--hide-secret`을 사용했지만
  절차는 그대로 지킨다.

---

## 미수행 (사람 수행 필요)
- ~~Tailscale 제거~~ — admin 콘솔에서 머신 삭제 완료.
  기기측 `tailscale logout`은 수행하지 않았으나 저장 매체를 보관하므로 불필요하다.
- 적용 후 Grafana `NewsLab Pipeline Operations`의 Cluster Nodes row가 2노드로
  표시되는지 확인
