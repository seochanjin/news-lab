# Raspberry Pi worker K3s join 검증

## 작업 목적

이번 작업의 목적은 집에 있는 Raspberry Pi를 NewsLab K3s 클러스터의 worker node로 추가하고, 실제 운영 가능한 수준인지 검증하는 것이었다.

처음 목표는 단순히 Raspberry Pi를 worker node로 join하고 `Ready` 상태를 확인하는 것이었다. 하지만 진행 중 `kubectl logs`가 실패하면서, 단순 node join만으로는 운영 검증이 충분하지 않다는 것을 확인했다.

따라서 작업 범위를 확장해 Oracle Cloud ARM 노드와 Raspberry Pi home-lab 노드가 모두 Tailscale 기반으로 통신하도록 K3s node `InternalIP`와 flannel interface를 정리했다.

최종 목표는 다음 상태를 만드는 것이었다.

```text
arm-master-node   InternalIP: 100.79.184.11
arm-worker-node   InternalIP: 100.117.78.65
pi-worker-node    InternalIP: 100.92.105.106
```

즉, Oracle Cloud 내부 private IP와 집 LAN IP가 섞이는 구조를 피하고, 모든 K3s node 간 통신 기준을 Tailscale로 통일하는 것이 이번 작업의 핵심이었다.

## 기존 문제

기존 NewsLab K3s 클러스터는 Oracle Cloud ARM 인스턴스 2대로 구성되어 있었다.

```text
arm-master-node   10.0.0.107
arm-worker-node   10.0.0.173
```

이때는 두 노드가 같은 OCI VCN 안에 있었기 때문에 private IP 기반 통신에 문제가 없었다.

하지만 Raspberry Pi는 집 네트워크에 있는 장비이므로 OCI private subnet인 `10.0.0.0/24`에 직접 접근할 수 없다. 처음 Raspberry Pi를 worker로 join했을 때 node 자체는 `Ready`가 되었지만, 테스트 Pod의 로그 조회가 실패했다.

초기 실패 원인은 Pi node의 `InternalIP`가 집 LAN IP인 `192.168.1.121`로 잡힌 것이었다. Oracle master 입장에서는 이 주소로 Pi kubelet `10250` 포트에 접근할 수 없었다.

이후 Pi를 Tailscale IP 기준으로 재join해 `InternalIP`를 `100.92.105.106`으로 변경했지만, K3s agent 로그에서 master의 기존 OCI private IP인 `10.0.0.107:6443`으로 remotedialer proxy 연결을 계속 시도하는 문제가 남아 있었다.

```text
Failed to connect to proxy
dial tcp 10.0.0.107:6443: connect: connection timed out
```

즉, Raspberry Pi worker join은 표면적으로 성공했지만, K3s 내부 통신 경로가 OCI private IP와 Tailscale IP 사이에서 섞여 운영에 필요한 `kubectl logs` 검증이 실패하는 상태였다.

## 변경 내용

먼저 Raspberry Pi의 네트워크 상태를 확인했다. Pi는 Ubuntu Server가 설치된 상태였고, Wi-Fi로 접속 중이었다. 이후 Ethernet 케이블을 연결해 `eth0`에 DHCP 주소가 정상 할당되는지 확인했다.

```text
eth0   192.168.1.121/24
wlan0  192.168.1.120/24
```

라우팅 우선순위는 Ethernet이 더 높게 잡혔다.

```text
default via 192.168.1.1 dev eth0 metric 100
default via 192.168.1.1 dev wlan0 metric 600
```

이후 Raspberry Pi에 Tailscale을 설치하고 tailnet에 연결했다.

```text
pi-worker-node Tailscale IP: 100.92.105.106
```

Raspberry Pi를 K3s worker로 join할 때는 node name, node IP, flannel interface를 Tailscale 기준으로 지정했다.

```text
--node-name pi-worker-node
--node-ip 100.92.105.106
--flannel-iface tailscale0
```

그 결과 Pi node는 다음과 같이 등록되었다.

```text
pi-worker-node   Ready   InternalIP: 100.92.105.106
```

하지만 이 상태에서도 master가 기존 OCI private IP를 계속 사용하려는 문제가 있었기 때문에, master node의 K3s 설정도 Tailscale 기준으로 변경했다.

master에 `/etc/rancher/k3s/config.yaml`을 생성했다.

```yaml
node-ip: 100.79.184.11
flannel-iface: tailscale0
tls-san:
  - 100.79.184.11
  - arm-master-node
```

재시작 후 master의 `InternalIP`가 Tailscale IP로 변경되었다.

```text
arm-master-node   InternalIP: 100.79.184.11
```

이후 Pi의 K3s agent 로그에서 기존 `10.0.0.107:6443` 경로가 제거되고, Tailscale IP 기준으로 remotedialer proxy가 연결되는 것을 확인했다.

```text
Connected to proxy url="wss://100.79.184.11:6443/v1-k3s/connect"
Removing server from load balancer: 10.0.0.107:6443
Stopped tunnel to 10.0.0.107:6443
```

다음으로 Oracle ARM worker도 동일한 기준으로 재join했다.

변경 전:

```text
arm-worker-node   InternalIP: 10.0.0.173
```

변경 후:

```text
arm-worker-node   InternalIP: 100.117.78.65
```

worker 재join 이후 role label을 복구했다.

```bash
kubectl label node arm-worker-node node-role.kubernetes.io/worker= --overwrite
kubectl label node pi-worker-node node-role.kubernetes.io/worker= --overwrite
```

또한 `arm-worker-node` 재join 과정에서 기존에 수동으로 붙어 있던 `workload=app` label이 사라져 `news-api` Pod가 `Pending` 상태가 되었다. `news-api` Deployment에는 다음 nodeSelector가 설정되어 있었다.

```yaml
nodeSelector:
  workload: app
```

따라서 `arm-worker-node`에 label을 다시 붙였다.

```bash
kubectl label node arm-worker-node workload=app --overwrite
```

Raspberry Pi에는 일반 workload가 실수로 배치되지 않도록 `NoSchedule` taint를 적용했다.

```bash
kubectl taint node pi-worker-node node-role=news-edge-worker:NoSchedule
```

적용 결과:

```text
Taints: node-role=news-edge-worker:NoSchedule
```

마지막으로 Pi에 올라가 있던 cert-manager Pod들을 삭제해 재스케줄링을 유도했다. 최종적으로 cert-manager는 Oracle master/worker 쪽으로 이동했다.

```text
cert-manager              arm-master-node
cert-manager-cainjector   arm-worker-node
cert-manager-webhook      arm-worker-node
```

## 테스트

먼저 최종 node 상태를 확인했다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide
```

최종 결과:

```text
arm-master-node   Ready   control-plane   100.79.184.11
arm-worker-node   Ready   worker          100.117.78.65
pi-worker-node    Ready   worker          100.92.105.106
```

Pi worker에 테스트 Pod를 생성하고 로그 조회를 확인했다.

```bash
kubectl run pi-worker-test ...
kubectl logs pi-worker-test
```

결과:

```text
pi-worker-test
Linux pi-worker-test 6.8.0-1053-raspi ... aarch64 GNU/Linux
```

Oracle ARM worker에도 테스트 Pod를 생성하고 로그 조회를 확인했다.

```bash
kubectl run arm-worker-test ...
kubectl logs arm-worker-test
```

결과:

```text
arm-worker-test
Linux arm-worker-test 6.17.0-1014-oracle ... aarch64 GNU/Linux
```

`news-api` Deployment 상태도 확인했다.

```bash
kubectl get deploy news-api
kubectl get pods -l app=news-api -o wide
```

결과:

```text
news-api   2/2   2   2

news-api-...   Running   arm-worker-node
news-api-...   Running   arm-worker-node
```

외부 API도 확인했다.

```bash
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/extractor/status
```

결과:

```json
{
  "status": "ok",
  "service": "news-api",
  "hostname": "news-api-6df6794796-zqwbk"
}
```

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

마지막으로 전체 Pod 상태를 확인했다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
```

주요 Pod들은 모두 `Running` 상태였다.

```text
cert-manager              Running
cert-manager-cainjector   Running
cert-manager-webhook      Running
news-api                  2 Pods Running
coredns                   Running
metrics-server            Running
traefik                   Running
```

## 운영 반영

이번 작업은 실제 운영 중인 NewsLab K3s 클러스터에 반영되었다.

최종 node 구성은 다음과 같다.

```text
arm-master-node
- role: control-plane
- InternalIP: 100.79.184.11
- flannel interface: tailscale0

arm-worker-node
- role: worker
- InternalIP: 100.117.78.65
- flannel interface: tailscale0
- workload=app
- news-api 실행 위치

pi-worker-node
- role: worker
- InternalIP: 100.92.105.106
- flannel interface: tailscale0
- hardware=raspberry-pi
- location=home-lab
- node-role=news-edge-worker
- taint: node-role=news-edge-worker:NoSchedule
```

운영 API인 `news-api`는 Oracle ARM worker에 유지했다. Pi는 아직 집 네트워크, 전원, 장기 안정성 검증이 필요하므로 일반 workload가 자동 배치되지 않도록 제한했다.

이번 작업 중 K3s node token을 사용했지만, token 값은 Git, Notion, PR, verification log에 기록하지 않았다.

## 확인 결과

최종적으로 모든 K3s node의 `InternalIP`가 Tailscale IP 기준으로 통일되었다.

```text
arm-master-node   100.79.184.11
arm-worker-node   100.117.78.65
pi-worker-node    100.92.105.106
```

Pi worker와 Oracle ARM worker 모두 테스트 Pod 실행 및 `kubectl logs` 조회가 성공했다. 이는 K3s API server에서 각 worker node의 kubelet으로 접근하는 경로가 정상화되었다는 의미다.

`arm-worker-node` 재join 후 `news-api`가 `Pending` 상태가 되었지만, 원인은 `workload=app` label 누락으로 확인되었다. label 복구 후 `news-api`는 다시 `2/2` Running 상태가 되었고, 외부 API도 정상 응답했다.

```text
curl https://api.dev-scj.site/health
→ {"status":"ok","service":"news-api",...}

curl https://api.dev-scj.site/extractor/status
→ {"status":"success",...}
```

Pi worker에는 `NoSchedule` taint가 적용되어 일반 Pod가 실수로 올라가지 않도록 했다. 이후 cert-manager Pod들도 Pi에서 빠져 Oracle master/worker 쪽으로 이동했다.

따라서 이번 작업은 Raspberry Pi worker join뿐 아니라 하이브리드 K3s 클러스터의 네트워크 기준을 Tailscale로 통일하고, 기존 서비스 복구까지 검증한 상태로 완료되었다.

## 이번 단계의 의미

이번 단계는 NewsLab이 단순한 Oracle Cloud 내부 클러스터에서 벗어나, 실제 집에 있는 Raspberry Pi까지 포함하는 하이브리드 K3s 클러스터로 확장된 지점이다.

단순히 노드를 하나 더 붙인 것이 아니라, 다음과 같은 실제 운영 문제를 직접 경험하고 해결했다.

```text
- home-lab worker node join
- LAN IP와 cloud private IP가 섞일 때 발생하는 kubelet log proxy 문제
- K3s remotedialer proxy 연결 실패
- node-ip / flannel-iface 설정
- Tailscale 기반 node-to-node networking
- worker 재join 후 수동 label 손실
- Deployment nodeSelector와 node label 관계
- taint를 통한 edge node workload 제한
- 운영 변경 후 외부 API 복구 검증
```

이번 작업은 포트폴리오 관점에서도 의미가 크다. 단순히 Kubernetes manifest를 작성한 것이 아니라, 실제 운영 중인 클러스터에 home-lab 장비를 추가하고, 네트워크 문제를 디버깅하고, 기존 서비스가 다시 정상 동작하는지 확인했기 때문이다.

또한 앞으로 Raspberry Pi나 외부 ARM node를 추가할 때 사용할 수 있는 기준도 생겼다.

```text
K3s node-to-node communication = Tailscale
운영 API workload = Oracle ARM worker
home-lab Pi worker = edge/test/batch workload 후보
Pi workload 배치 = 명시적 toleration 필요
```

## 다음 단계

다음 단계에서는 Raspberry Pi worker를 단순히 붙여 둔 상태에서 끝내지 않고, 실제 workload를 어떻게 활용할지 검증할 필요가 있다.

우선순위 후보는 다음과 같다.

```text
1. Raspberry Pi worker 장기 안정성 확인
   - 재부팅 후 자동 재join 여부
   - Ethernet/Wi-Fi 전환 상황
   - Tailscale 재연결 동작
   - 장시간 Ready 유지 여부

2. Pi worker에 batch workload 배치 테스트
   - raw extractor
   - crawler 보조 작업
   - summary/classification worker 후보
   - toleration을 명시한 Job/CronJob 실행

3. system workload placement 정책 정리
   - cert-manager
   - Traefik ServiceLB
   - metrics-server
   - system Pod가 어느 노드에 떠야 하는지 기준화

4. 모니터링 구성
   - node 상태
   - Pod restart
   - CronJob 실패
   - CPU/memory/disk
   - Pi worker 연결 끊김 알림

5. public-facing news frontend 개발
   - 기사 목록
   - 기사 상세
   - 카테고리
   - 검색
   - 외부 사용자가 볼 수 있는 최소 UI
```

다음 회차에서는 너무 세부적인 내부 개선보다, 실제 사용자가 볼 수 있는 뉴스 서비스로 이어지는 방향을 우선순위에 두는 것이 좋다.
