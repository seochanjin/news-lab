# Raspberry Pi worker K3s join 검증

## 작업 내용

- Raspberry Pi worker node를 NewsLab K3s cluster에 추가했습니다.

- Oracle Cloud node와 home-lab Raspberry Pi node가 혼합된 구조에서 K3s node InternalIP와 flannel interface를 Tailscale 기준으로 통일했습니다.

- `arm-master-node`, `arm-worker-node`, `pi-worker-node`가 모두 Tailscale IP를 Kubernetes InternalIP로 사용하도록 정리했습니다.

- Pi worker에 `NoSchedule` taint를 추가해 일반 workload가 실수로 배치되지 않도록 했습니다.

- `news-api` scheduling issue를 복구하고 외부 API 동작을 확인했습니다.

## 주요 변경 사항

- `arm-master-node`
  - InternalIP: `10.x.x.x` → `100.x.x.x`
  - `flannel-iface: tailscale0` 적용
- `arm-worker-node`
  - InternalIP: `10.x.x.x` → `100.x.x.x`
  - Tailscale IP 기준으로 K3s agent 재조인
  - `workload=app` label 복구
- `pi-worker-node`
  - InternalIP: `100.x.x.x`
  - `flannel-iface: tailscale0`
  - `node-role=news-edge-worker:NoSchedule` taint 추가

## 테스트

- `kubectl get nodes -o wide`
- Pi worker test Pod 생성 및 `kubectl logs`
- Oracle ARM worker test Pod 생성 및 `kubectl logs`
- `kubectl get pods -A -o wide`
- `kubectl get svc -A`
- `kubectl get ingress -A`
- `curl https://api.dev-scj.site/health`
- `curl https://api.dev-scj.site/extractor/status`

## 확인 결과

- 모든 K3s node의 InternalIP가 Tailscale IP 기준으로 통일됐습니다.
- Pi worker와 Oracle worker에서 test Pod 실행 및 logs 조회가 성공했습니다.
- `news-api` Deployment는 `2/2` available 상태로 복구됐습니다.
- 외부 API health check가 성공했습니다.
- extractor status API가 정상 응답했습니다.

## 비고

- K3s node token, kubeconfig, SSH key, secret 값은 기록하지 않았습니다.
- `news-api` Pending 원인은 `arm-worker-node` 재조인 후 `workload=app` label이 사라진 것이었고, label 복구로 해결했습니다.
- Pi worker는 edge/test/batch 용도로 제한하기 위해 taint를 적용했습니다.
