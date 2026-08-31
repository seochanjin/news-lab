# Task: Raspberry Pi worker node 정리

## Goal

`pi-worker-node`를 K3s cluster에서 제거하고, 저장소의 현재 상태 문서와 monitoring
설정을 2-node 구성에 맞게 현행화한다. Pi 하드웨어는 매각한다.

**이 작업의 성격은 기능 추가가 아니라 정리다.** 따라서 제거 자체보다 **왜 제거하는지를
기록으로 남기는 것**이 산출물이다. 기록이 없으면 "노드를 늘렸다가 없앴다"가 되고,
기록이 있으면 "효용 대비 운영 부하를 측정해 정리했다"가 된다.

- **branch:** `chore/remove-pi-worker-node`
- **시간 상한:** 반나절
- **범위 밖:** `flannel-iface: tailscale0` 구성 변경, ARM 노드 재구성

## 배경 — 제거 판단의 근거

19차에서 Raspberry Pi를 hybrid worker로 join했다. 공인 IP 없이 이기종 노드를 묶기
위해 Tailscale 위에 flannel VXLAN을 얹는 구성을 표준화했고, taint/toleration,
kubelet log proxy, remotedialer, 재join 후 label 손실 문제를 해결했다.

그러나 **이 노드에만 배치된 workload가 없다.** 제거 직전 실측에서 Pod 2개가
있었고 둘 다 모든 노드에 배치되는 DaemonSet이다(`svclb-traefik`, `node-exporter`).

```text
node-role=news-edge-worker:NoSchedule  taint
→ 이를 tolerate하는 것은 DaemonSet 2개뿐
→ 노드가 존재해야만 하는 이유를 만드는 workload는 없다
```

`svclb-traefik`은 해당 노드를 LoadBalancer endpoint 후보로 만들지만, Pi는 가정용
NAT 뒤에 있어 실제로 사용된 적이 없다.

얻는 것은 자기 자신에 대한 monitoring이고, 지는 것은 **홈 네트워크 의존**이다.
공유기 재부팅, ISP 장애, 정전이 cluster 구성 요소의 가용성에 들어온다.
통제 밖의 변수를 지면서 얻는 것이 없다.

### 79차 장애와의 관계 — 오해하지 않기 위해 기록한다

79차의 25시간 전면 장애는 **`arm-worker-node`에서 `tailscaled` 재시작으로 flannel
VXLAN이 붕괴한 것**이었다. Pi가 원인이 아니다.

그리고 **Pi를 제거해도 그 위험은 남는다.** `--flannel-iface tailscale0`은 Oracle 노드
두 대 사이 통신과 operator 접근 경로에도 사용되므로 유지한다. 79차에서 적용한
systemd `PartOf` 의존 선언이 그 방어책이며 이번 작업과 무관하다.

**따라서 이 작업의 근거는 "장애 위험 감소"가 아니라 "효용 없는 운영 변수 제거"다.**

### 왜 다른 용도로 쓰지 않는가

오라클 ARM 4 OCPU / 24GB를 이미 운영 중이다. 24시간 상시 실행이 필요한 것은
전부 그쪽이 낫다. Pi가 유일하게 우위인 영역은 **물리적으로 집에 있어야만 하는
workload**(홈 네트워크 DNS, 물리 센서, USB 동글)인데 현재 해당 사항이 없다.

용도가 없는 상태에서 용도를 만들어 붙이는 것은 이번에 제거하는 이유
("workload 없이 노드를 추가했다")를 더 작은 규모로 반복하는 것이다.

## Scope

### UNIT-01. Monitoring 설정 정리

- `k8s/monitoring/kube-prometheus-stack-values.yaml`
  — node-exporter의 `node-role=news-edge-worker` toleration 제거
- `k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`
  — `NewsLabNodeNotReady` alert의 node regex에서 `pi-worker-node` 제거

**Dashboard는 수정하지 않는다.** `news-lab-pipeline-operations.json`의 Cluster Nodes
panel은 노드명을 하드코딩하지 않고 `kube_node_*`를 그대로 사용하므로 노드가 빠지면
자동으로 2개만 표시된다. 확인 완료.

### UNIT-02. 현재 상태 문서 현행화

- `README.md` — 3-node → 2-node, node-exporter toleration 서술, 설계 결정 항목
- `docs/ARCHITECTURE.md` — 노드 목록
- `docs/architecture/k3s-runtime.md` — 노드 표, node-exporter 배치, Tailscale 서술

**과거 기록은 수정하지 않는다.** `docs/verification/infra-pi-worker-join.md`,
`docs/fixes/infra-pi-worker-join-approved-fixes.md`,
`docs/design/pipeline-operations-dashboard.md`는 그 시점의 사실을 기록한 문서다.
19차 경험은 과거형으로 유효하며 지우면 오히려 이력이 사라진다.

### UNIT-03. ADR 작성

- `docs/adr/0001-remove-pi-worker-node.md` 신규

`docs/adr/`는 현재 비어 있다. AGENTS.md의 workflow artifact 표에 정의된 경로이므로
이번이 첫 ADR이 된다. 형식은 Context / Decision / Consequences로 둔다.

## 사람이 수행 (순서 중요)

```text
1. 배치된 workload 확인
   kubectl get pods -A -o wide --field-selector spec.nodeName=pi-worker-node

2. drain
   kubectl drain pi-worker-node --ignore-daemonsets

3. Pi에서 k3s agent 제거          ← delete node보다 먼저 한다
   sudo /usr/local/bin/k3s-agent-uninstall.sh

4. node 삭제
   kubectl delete node pi-worker-node

5. Tailscale 제거 (기기와 콘솔 양쪽)
   sudo tailscale logout
   + Tailscale admin 콘솔에서 머신 삭제

6. 저장 매체 재이미징            ← 매각 전 필수

7. UNIT-01 설정 적용 (Helm, PrometheusRule)
```

**3번이 4번보다 먼저인 이유**: `kubectl delete node` 후에도 Pi에서 k3s-agent가 살아
있으면 노드가 자동으로 다시 등록된다.

**6번을 건너뛰면 안 되는 이유**: Pi에 k3s node token(`/etc/rancher/node/`),
Tailscale node key(`/var/lib/tailscale/tailscaled.state`), SSH key가 남아 있다.
79차에서 join token 회전을 보류한 근거가 "API server는 Tailscale 내부에서만
접근 가능하다"였는데, **Tailscale 상태 파일이 그대로 남은 기기를 타인에게 넘기면
그 전제가 깨진다.** 재이미징하면 회전은 불필요하다.

**2~4번 사이에 `NewsLabNodeNotReady` alert(critical, Telegram)가 발생할 수 있다.**
`for: 10m`이므로 빠르게 진행하면 발생하지 않는다. 발생해도 정상이다.

## Checklist

- [x] UNIT-01 구현
- [x] UNIT-02 구현
- [x] UNIT-03 ADR 작성
- [x] 노드 제거 (사람 수행)
- [x] Pi에서 k3s-agent 제거 (사람 수행)
- [x] Helm render 검증 및 운영 적용 (사람 수행)
- [x] Tailscale 제거 (admin 콘솔에서 머신 삭제)
- [x] monitoring 설정 운영 적용 및 확인 (사람 수행)

## 완료 판정

```bash
kubectl get nodes                    # 2개
kubectl get pods -n monitoring -o wide | grep node-exporter   # 2개
```

Grafana `NewsLab Pipeline Operations`의 Cluster Nodes row가 2노드로 표시되고
`NewsLabNodeNotReady` alert가 발생하지 않는다.
