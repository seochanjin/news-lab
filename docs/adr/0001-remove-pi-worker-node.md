# ADR 0001. Raspberry Pi worker node 제거

- 상태: 채택
- 날짜: 2026-08-31
- 관련: 19차 Pi worker join, 79차 flannel VXLAN 단절 장애

## Context

19차에서 Raspberry Pi를 K3s hybrid worker로 join했다. 공인 IP 없이 이기종 노드를
하나의 cluster로 묶기 위해 Tailscale 위에 flannel VXLAN을 얹는 구성을 표준화했고,
그 과정에서 taint/toleration, kubelet log proxy, remotedialer, 재join 후 label 손실을
해결했다.

이후 운영하며 확인된 사실은 다음과 같다.

**이 노드에만 배치된 workload가 없다.**

제거 직전 실측 결과 Pod는 2개였고 **둘 다 모든 노드에 배치되는 DaemonSet**이다.

```text
kube-system  svclb-traefik-...                  k3s ServiceLB
monitoring   monitoring-prometheus-node-exporter  node metric 수집
```

```text
node-role=news-edge-worker:NoSchedule  taint
→ 이를 tolerate하는 것은 위 DaemonSet 2개뿐
→ 노드가 존재해야만 하는 이유를 만드는 workload는 없다
```

`svclb-traefik`은 ServiceLB가 모든 노드에 두는 Pod로, 해당 노드를 LoadBalancer
endpoint 후보로 만든다. 그러나 Pi는 가정용 NAT 뒤에 있고 공개 트래픽은 Public DNS와
Oracle Public IP를 거쳐 진입하므로 **이 endpoint는 실제로 사용된 적이 없다.**

즉 얻는 것은 자기 자신에 대한 node metric뿐이고, 대가는 **홈 네트워크 의존**이다.
공유기 재부팅, ISP 장애, 정전이 cluster 구성 요소의 가용성 변수로 들어온다.
이 변수는 운영자가 통제할 수 없다.

edge/batch workload 후보로 남겨 두었으나 2개월 이상 실제 후보가 생기지 않았다.
그 사이 Oracle Cloud ARM 인스턴스 2대(총 4 OCPU / 24GB)가 확보되어, **상시 실행이
필요한 workload는 전부 그쪽이 우위**가 됐다. Pi가 유일하게 우위인 영역은 물리적으로
가정 내에 있어야만 하는 workload(홈 네트워크 DNS, 물리 센서, USB 동글)인데
현재 해당 사항이 없다.

### 79차 장애와의 관계

79차의 25시간 전면 장애는 **`arm-worker-node`에서 `tailscaled` 재시작으로 flannel
VXLAN이 붕괴한 것**이며 Pi가 원인이 아니다. `--flannel-iface tailscale0`은 Oracle
node 두 대 사이 통신과 operator 접근 경로에도 사용되므로 **Pi를 제거해도 그 구성과
위험은 그대로 남는다.** 방어책은 79차에서 적용한 systemd `PartOf` 의존 선언이다.

**따라서 이 결정의 근거를 "장애 위험 감소"로 서술하지 않는다.**

## Decision

`pi-worker-node`를 cluster에서 제거하고 하드웨어를 매각한다.
Oracle Cloud A1 2-node 구성으로 운영한다.

`--flannel-iface tailscale0` 구성은 **변경하지 않는다.** Oracle node 사이 통신과
operator 접근에 계속 사용되며, 되돌리는 변경 자체가 79차와 같은 계열의 위험을
새로 만든다.

용도가 없는 상태에서 용도를 만들어 붙이지 않는다. 그것은 이번에 제거하는 이유
(**workload 없이 노드를 추가했다**)를 더 작은 규모로 반복하는 일이다.

## Consequences

### 얻는 것

- 통제 불가능한 가용성 변수(홈 네트워크) 제거
- 노드 3개 중 1개가 실질 기능이 없는 상태 해소. 운영 대상이 실제 운영 대상만 남는다
- monitoring 설정에서 조건부 toleration과 node regex 예외 제거

### 잃는 것

- hybrid cluster 구성 자체는 더 이상 live 상태로 시연할 수 없다.
  **다만 19차 구성 경험과 그 과정의 문제 해결은 과거형으로 유효하며,
  `docs/verification/infra-pi-worker-join.md`에 기록이 남는다.**
- edge 노드가 실제로 필요해지면 다시 구성해야 한다. 절차는 위 문서에 있다.

### 되돌릴 수 있는가

되돌릴 수 있다. join 절차가 문서화돼 있고 cluster 구성 자체는 바뀌지 않는다.
다만 하드웨어를 매각하므로 물리적 되돌림에는 재구매가 필요하다.

### 판단의 일반화 — 어디까지 참인가

이 결정에서 도출되는 원칙은 **"Raspberry Pi는 서버로 부적합하다"가 아니다.**
장비가 물리적으로 현장에 있어야만 하는 영역(산업 현장 edge agent, 센서 게이트웨이,
로컬 네트워크 appliance)에서 ARM SBC는 정당한 선택이다.

정확한 원칙은 다음과 같다.

> **노드는 거기 있어야만 하는 이유가 있을 때 추가한다.**
> 물리적 위치가 요구사항이 아니라면 통제 가능한 환경에 두는 편이 낫다.

그리고 가용성을 약속해야 하는 구성 요소를 홈 네트워크에 두지 않는다.
이쪽은 79차 장애로 실측된 원칙이다.

## 수행 절차

```text
1. kubectl get pods -A -o wide --field-selector spec.nodeName=pi-worker-node
2. kubectl drain pi-worker-node --ignore-daemonsets
3. Pi에서 sudo /usr/local/bin/k3s-agent-uninstall.sh   ← 4번보다 먼저
4. kubectl delete node pi-worker-node
5. sudo tailscale logout + Tailscale admin 콘솔에서 머신 삭제
6. 저장 매체 재이미징                                   ← 매각 전 필수
7. monitoring 설정 적용 (Helm, PrometheusRule)
```

3번이 4번보다 먼저인 이유: `delete node` 후에도 k3s-agent가 살아 있으면 노드가
자동으로 다시 등록된다.

6번을 건너뛸 수 없는 이유: Pi에 k3s node token(`/etc/rancher/node/`), Tailscale
node key(`/var/lib/tailscale/tailscaled.state`), SSH key가 남아 있다. 79차에서
join token 회전을 보류한 근거가 "API server는 Tailscale 내부에서만 접근 가능하다"
였는데, **Tailscale 상태 파일이 그대로 남은 기기를 타인에게 넘기면 그 전제가
깨진다.** 재이미징하면 token 회전은 불필요하다.
