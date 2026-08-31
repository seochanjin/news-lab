# Raspberry Pi worker node 정리

## 작업 내용

- `pi-worker-node`를 K3s cluster에서 제거하고 2-node 구성으로 전환했습니다.
- monitoring 설정과 현재 상태 문서를 2-node에 맞게 현행화했습니다.
- 제거 판단의 근거를 ADR로 남겼습니다. 저장소의 첫 ADR입니다.

이 작업은 기능 추가가 아니라 정리입니다. 따라서 제거 자체보다 **왜 제거하는지를
기록으로 남기는 것**이 산출물입니다.

## 제거 판단의 근거

19차에서 Pi를 hybrid worker로 join했습니다. 공인 IP 없이 이기종 노드를 묶기 위해
Tailscale 위에 flannel VXLAN을 얹는 구성을 표준화했고, taint/toleration,
kubelet log proxy, remotedialer, 재join 후 label 손실을 해결했습니다.

그러나 **이 노드에만 배치된 workload가 없습니다.** 제거 직전 실측 결과입니다.

```text
kube-system  svclb-traefik-...                    k3s ServiceLB
monitoring   monitoring-prometheus-node-exporter  node metric 수집
```

Pod 2개, 둘 다 모든 노드에 배치되는 DaemonSet입니다. `svclb-traefik`은 해당 노드를
LoadBalancer endpoint 후보로 만들지만, Pi는 가정용 NAT 뒤에 있고 공개 트래픽은
Public DNS와 Oracle Public IP를 거쳐 진입하므로 실제로 사용된 적이 없습니다.

얻는 것은 자기 자신에 대한 node metric뿐이고, 대가는 **홈 네트워크 의존**입니다.
공유기 재부팅, ISP 장애, 정전이 cluster 구성 요소의 가용성 변수로 들어옵니다.

edge/batch workload 후보로 남겨 두었으나 2개월 이상 후보가 생기지 않았습니다.
그 사이 Oracle ARM 2대(4 OCPU / 24GB)가 확보되어 상시 실행이 필요한 workload는
전부 그쪽이 우위가 됐습니다.

### 79차 장애와의 관계 — 근거로 사용하지 않습니다

79차 25시간 전면 장애는 **`arm-worker-node`에서 `tailscaled` 재시작으로 flannel
VXLAN이 붕괴한 것**이며 Pi가 원인이 아닙니다. `--flannel-iface tailscale0`은 Oracle
node 두 대 사이 통신과 operator 접근 경로에도 사용되므로 **Pi를 제거해도 그 구성과
위험은 그대로 남습니다.** 방어책은 79차의 systemd `PartOf` 의존 선언입니다.

따라서 이 PR의 근거를 "장애 위험 감소"로 서술하지 않았습니다.

## 주요 변경 사항

### Manifest

- `k8s/monitoring/kube-prometheus-stack-values.yaml`
  — node-exporter의 `node-role=news-edge-worker` toleration 제거
- `k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`
  — `NewsLabNodeNotReady`의 node regex에서 `pi-worker-node` 제거

### 문서

- `README.md` — 3-node → 2-node, node-exporter toleration 서술, 설계 결정 항목,
  문서 링크를 "운영 근거"에서 "과거 구성 이력"으로 분류 변경
- `docs/ARCHITECTURE.md`, `docs/architecture/k3s-runtime.md` — 노드 표와 배치 서술
- `docs/adr/0001-remove-pi-worker-node.md` **신규**
- `docs/tasks/`, `docs/verification/` 신규

### 수정하지 않은 것

**Dashboard** — `news-lab-pipeline-operations.json`의 Cluster Nodes panel은 노드명을
하드코딩하지 않고 `kube_node_*`를 그대로 사용합니다(`grep -c "pi-worker-node"` = 0).
노드가 빠지면 자동으로 2개만 표시되므로 변경이 불필요합니다.

**과거 기록** — `docs/verification/infra-pi-worker-join.md`,
`docs/fixes/infra-pi-worker-join-approved-fixes.md`,
`docs/design/pipeline-operations-dashboard.md`는 그 시점의 사실을 기록한 문서입니다.
19차 구성 경험은 과거형으로 유효하며 지우면 이력이 사라집니다.

**`--flannel-iface tailscale0`** — 위 사유로 유지합니다.

## 추가/변경된 API

- 없음

## DB 변경 사항

- 없음

## README 영향

- 변경 있음. cluster topology 서술이 3-node에서 2-node로 바뀝니다.

## 테스트

이 변경에는 자동 test가 없습니다. 인프라 설정과 문서 변경이며 application code를
건드리지 않습니다.

### Repository 검증

```bash
python3 -c "import yaml; ..."                       # YAML parse + assertion
grep -rn "pi-worker-node|news-edge-worker" k8s/     # 0
```

```text
YAML OK: k8s/monitoring/kube-prometheus-stack-values.yaml
YAML OK: k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
node-exporter tolerations: 2 (control-plane, master)
manifest 내 Pi 참조: 0
문서 링크 4건 유효
```

### Helm dry-run

```bash
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --dry-run=server --hide-secret > /tmp/monitoring-dry.yaml

grep -c "news-edge-worker" /tmp/monitoring-dry.yaml     # 0
grep -A 12 "^      tolerations:" /tmp/monitoring-dry.yaml
```

렌더링 결과에 `news-edge-worker`가 없고 control-plane·master toleration 2개는
유지됩니다. **후자가 사라지면 master 노드에서 node-exporter가 동작하지 않아
노드 지표가 하나 비므로 함께 확인했습니다.**

`--version 86.2.0`을 명시했습니다. 생략하면 저장소 최신 chart를 받아오므로
toleration 두 줄 제거가 stack 전체 버전 업그레이드가 됩니다.

## 운영 반영 — 이미 완료된 상태로 올립니다

**이 PR은 이례적으로 운영 반영이 끝난 뒤 올라갑니다.** 이유는 둘입니다.

1. **노드 제거가 저장소 변경보다 먼저여야 합니다.** 문서는 현재 상태를 기술해야
   하는데, 노드가 남아 있는 상태에서 "2-node"라고 쓰면 문서가 거짓이 됩니다.
2. `k8s/monitoring/`은 Argo CD Application의 `recurse: false` 범위 밖이므로
   merge해도 자동 적용되지 않습니다. 사람이 직접 적용하는 경로입니다.

### 수행 기록

```text
kubectl drain pi-worker-node --ignore-daemonsets      node/pi-worker-node drained
sudo /usr/local/bin/k3s-agent-uninstall.sh            service disable, binary 제거
kubectl delete node pi-worker-node                    node "pi-worker-node" deleted

kubectl get nodes
  arm-master-node   Ready   control-plane   98d   v1.35.5+k3s1
  arm-worker-node   Ready   worker          85d   v1.35.5+k3s1

helm upgrade ... --version 86.2.0                     STATUS: deployed, REVISION: 5
kubectl apply -f .../news-lab-pipeline-alerts.yaml    configured

kubectl get pods -n monitoring -o wide | grep node-exporter
  monitoring-prometheus-node-exporter-8jwpb  1/1  Running  36s  arm-master-node
  monitoring-prometheus-node-exporter-m8ct8  1/1  Running  38s  arm-worker-node
```

`k3s-agent-uninstall.sh`를 `delete node`보다 먼저 실행했습니다. 순서가 반대면
agent가 살아 있어 노드가 자동으로 다시 등록됩니다.

Tailscale은 admin 콘솔에서 머신을 삭제했습니다. 저장 매체는 보관하고 보드만
매각하므로 기기측 `tailscale logout`과 재이미징은 수행하지 않았습니다.
자격증명은 모두 저장 매체 안에 있고 Pi 5 보드의 비휘발성 저장소는 부트로더
EEPROM뿐입니다.

임시 dry-run 파일은 삭제했습니다. 75차에서 helm manifest diff로 Grafana admin
password가 노출된 이후 Runbook에 정한 절차입니다.

## 남은 확인 (사람 수행)

- Grafana `NewsLab Pipeline Operations`의 Cluster Nodes row가 2노드로 표시되는지

## 범위 밖

- `--flannel-iface tailscale0` 구성 변경 — 되돌리는 변경 자체가 79차와 같은 계열의
  위험을 새로 만듭니다
- Pi 하드웨어 매각 절차
