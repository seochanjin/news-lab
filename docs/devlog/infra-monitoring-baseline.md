# K3s 모니터링 기본 구성

## 작업 목적

- NewsLab hybrid K3s cluster의 `arm-master-node`, `arm-worker-node`, `pi-worker-node` 상태를 지속적으로 확인할 수 있는 최소 monitoring baseline을 구성한다.
- `kubectl top`의 순간 값 확인을 넘어 Prometheus에 metrics를 수집하고 Grafana에서 node/pod CPU·memory 상태를 볼 수 있는 기반을 만든다.
- Monitoring core workload는 Oracle ARM worker에 배치하고 Raspberry Pi worker는 monitoring target으로만 포함한다.

## 기존 문제

- 기존 cluster에는 장기 metrics 저장소와 dashboard가 없어 node/pod 리소스 상태를 지속적으로 비교하기 어려웠다.
- `metrics-server` 기반 `kubectl top`은 현재 상태 확인에는 유용하지만 추세 확인과 dashboard 시각화에는 적합하지 않았다.
- Pi worker에는 `node-role=news-edge-worker:NoSchedule` taint가 있어 기본 node-exporter 설정만으로는 Pi metrics가 누락될 수 있었다.
- Resource가 제한된 hybrid cluster에서 kube-prometheus-stack 기본 구성을 그대로 설치하면 Alertmanager, retention, resource 사용량이 baseline 목표보다 커질 수 있었다.

## 변경 내용

- `k8s/monitoring/kube-prometheus-stack-values.yaml` 추가.
- Alertmanager 비활성화.
- Prometheus retention을 `1d`로 설정.
- Prometheus resources를 request `100m/256Mi`, limit `500m/512Mi`로 설정.
- Grafana resources를 request `50m/256Mi`, limit `300m/512Mi`로 설정.
- Grafana, Prometheus, Prometheus Operator, kube-state-metrics에 `observability=true` nodeSelector 적용.
- node-exporter에 Pi worker와 control-plane/master taint toleration 적용.
- Grafana Service는 외부 노출 없이 chart 기본 `ClusterIP`를 유지하고 local port-forward 접근 방식을 사용.
- Helm render/install 명령에 kube-prometheus-stack chart `86.2.0` 버전 고정.
- Verification, approved fixes, PR draft 문서를 실제 실행 결과와 운영 확인 결과에 맞춰 정리.

## 구현 상세

- Monitoring core placement:
  - `arm-worker-node`에 `observability=true` label을 사용해 Grafana, Prometheus, Prometheus Operator, kube-state-metrics를 Oracle ARM worker에 배치한다.
  - Core workload가 Pi worker에 배치되지 않도록 Pi toleration은 node-exporter에만 적용한다.
- Node metrics:
  - node-exporter DaemonSet이 master, Oracle ARM worker, Pi worker에서 실행될 수 있도록 taint toleration을 설정했다.
  - Pi worker의 기존 `node-role=news-edge-worker:NoSchedule` taint를 명시적으로 허용했다.
- Kubernetes object 상태:
  - kube-state-metrics를 포함해 Deployment replica, Pod phase, Job, Node condition 같은 object state를 Prometheus에서 수집할 수 있도록 했다.
- Resource baseline:
  - Prometheus retention을 `1d`로 짧게 유지했다.
  - 초기 Grafana memory limit `256Mi`에서 UI 접근 중 OOMKilled가 발생했다.
  - Human-approved fix에 따라 Grafana request/limit을 `50m/256Mi`, `300m/512Mi`로 조정했다.
- 재현성:
  - 로컬 render와 documented install command에서 chart version을 `86.2.0`으로 고정했다.
- 보안과 접근:
  - Grafana는 external ingress나 notification channel을 추가하지 않았다.
  - Grafana credential retrieval은 local operator action으로만 다루고 credential 값은 문서에 기록하지 않았다.

## 대안 검토

- Prometheus와 Grafana를 직접 Kubernetes manifest로 구성:
  - RBAC, ServiceMonitor, dashboard provisioning, component 연결을 직접 유지해야 하므로 초기 구축과 향후 유지보수 비용이 커 제외했다.
- kube-prometheus-stack 기본 values 그대로 설치:
  - 빠르게 설치할 수 있지만 Alertmanager와 기본 retention/resource 설정이 현재 cluster의 최소 구성 목표에 맞지 않아 제외했다.
- Prometheus 없이 `metrics-server`와 `kubectl top`만 유지:
  - Resource 사용량은 가장 작지만 historical metrics와 Grafana dashboard를 제공하지 못해 목표를 충족하지 못한다.
- Prometheus PVC를 함께 구성:
  - Metrics persistence에는 유리하지만 storage class와 PVC 운영 정책을 함께 결정해야 해 이번 baseline에서는 deferred로 남겼다.
- Grafana 외부 공개:
  - 접근은 편해지지만 ingress, TLS, 인증 노출 범위가 커져 local port-forward 방식을 선택했다.

## 선택한 접근과 근거

- kube-prometheus-stack을 사용하고 작은 override values 파일만 유지하는 방식을 선택했다.
- 이 접근은 검증된 Prometheus Operator, Grafana dashboard, node-exporter, kube-state-metrics 연결을 재사용하면서 NewsLab cluster에 필요한 placement와 resource 제한만 명시할 수 있다.
- Alertmanager를 끄고 retention을 `1d`로 제한해 첫 monitoring 설치의 resource 부담을 줄였다.
- Core workload는 `observability=true` node에 고정하고 node-exporter만 모든 노드를 대상으로 실행해 Oracle worker와 Pi worker의 역할을 분리했다.
- Chart `86.2.0`을 pinning해 로컬 렌더링 결과와 운영 설치 명령의 재현성을 높였다.

## 트레이드오프

- Prometheus storage는 chart 기본 ephemeral storage를 사용하므로 Pod 재생성 시 과거 metrics가 유실될 수 있다.
- Retention이 `1d`라 장기 추세 분석에는 부족하지만 baseline 안정성과 resource 사용량 확인에는 적합하다.
- Grafana를 port-forward로만 접근하므로 매번 operator가 로컬 터널을 열어야 한다.
- Alertmanager와 external notification을 제외해 장애 알림 자동화는 제공하지 않는다.
- Grafana memory limit을 `512Mi`로 높여 OOM 문제를 해결했지만 초기 계획보다 worker memory 사용량이 증가했다.
- Kube-prometheus-stack chart upgrade는 pinning된 버전 변경과 별도 render/운영 검증이 필요하다.

## 테스트

Agent가 수행한 로컬 검증:

```bash
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml
```

- YAML parse 성공.
- kube-prometheus-stack chart `86.2.0` pinned render 성공.
- Rendered manifest assertion 성공:
  - Alertmanager custom resource 미생성
  - Monitoring core `observability=true` 배치
  - Prometheus retention `1d`
  - Grafana/Prometheus memory request·limit
  - Pi worker node-exporter toleration
- Application, DB, collector/extractor script scope check: 출력 없음, exit code 0.
- Private/Tailscale IP pattern 검사: 매치 없음.
- Credential 값: 발견되지 않음.
- Approved fix 대상 파일의 `git diff --check`: 출력 없음, exit code 0.
- 전체 `git diff --check`: 기존 `docs/reviews/infra-monitoring-baseline-antigravity.md`의 trailing whitespace 2건으로 exit code 2. Review artifact는 approved fix 범위가 아니므로 수정하지 않았다.

## 운영 반영

- Agent는 `kubectl apply`, Helm install/upgrade, rollout, production curl을 실행하지 않았다.
- Human operator가 제공한 sanitized verification 기록에 따르면 monitoring stack은 `monitoring` namespace에 설치되었다.
- Grafana, Prometheus, Prometheus Operator, kube-state-metrics는 `arm-worker-node`에서 Running 상태였다.
- node-exporter는 `arm-master-node`, `arm-worker-node`, `pi-worker-node`에서 Running 상태였다.
- Grafana OOM 이후 resource 값을 조정했고, 새 Grafana Pod는 `3/3 Running`, restart count `0` 상태를 유지했다.
- `news-api`는 `2/2` available 상태를 유지했다.
- PR merge 완료나 별도 K3s rollout 완료를 주장하지 않는다.

## README 업데이트 판단

- README는 수정하지 않았다.
- 이번 작업은 infrastructure baseline과 운영 검증 기록이 중심이며, 상세 설정은 task, verification, devlog 문서에서 관리하는 편이 적합하다.
- Monitoring 접근 방식이 장기 운영 표준으로 확정되거나 사용자-facing 운영 안내가 필요해질 때 README 반영을 다시 검토한다.

## 확인 결과

- Alertmanager 없이 Prometheus/Grafana baseline을 구성했다.
- Monitoring core workload가 Oracle ARM worker에서 Running인 것을 human-provided 기록으로 확인했다.
- node-exporter가 세 노드에서 Running인 것을 human-provided 기록으로 확인했다.
- Grafana container memory는 약 `150Mi`, sidecar container는 각각 약 `75Mi`로 확인되었고, 조정된 Grafana memory limit `512Mi` 아래에서 동작했다.
- Monitoring 설치와 resource 조정 후에도 `news-api`는 `2/2` available 상태를 유지했다.
- Grafana dashboard에서 세 노드 CPU/memory metrics를 직접 확인한 증거는 pending이다.
- 선택적 external API regression checks도 pending이다.

## 이번 단계의 의미

- NewsLab이 API와 batch workload 운영을 넘어 hybrid K3s cluster 자체의 resource 상태를 관찰할 수 있는 기반을 갖추었다.
- Oracle ARM worker와 Raspberry Pi worker의 역할 차이를 placement와 toleration으로 명시해 heterogeneous cluster 운영 의도를 구성 파일에 반영했다.
- 최초 설정 후 실제 OOM 문제를 관찰하고 resource 값을 조정하는 운영 피드백 루프를 문서화했다.
- Verification을 agent 로컬 검증과 human-provided production 결과로 분리해 실행 주체와 근거를 명확히 유지했다.

## 포트폴리오용 요약

- Oracle Cloud ARM 노드와 Raspberry Pi worker로 구성된 hybrid K3s cluster에 kube-prometheus-stack 기반 monitoring baseline을 설계했다.
- Prometheus, Grafana, kube-state-metrics, node-exporter를 활용해 node/pod resource 및 Kubernetes object 상태 수집 기반을 구성했다.
- Node label과 taint toleration으로 monitoring core와 edge monitoring target의 배치 정책을 분리했다.
- Alertmanager 비활성화, `1d` retention, 낮은 resource request/limit으로 제한된 cluster에 맞는 초기 구성을 적용했다.
- 운영 중 Grafana OOMKilled를 확인하고 container-level metrics를 근거로 memory limit을 조정한 뒤 안정 상태를 확인했다.
- Chart version pinning, rendered manifest assertion, credential/IP 노출 검사를 통해 배포 구성의 재현성과 안전성을 검증했다.

## 다음 단계 후보

- Grafana dashboard에서 `arm-master-node`, `arm-worker-node`, `pi-worker-node`의 CPU/memory metrics를 직접 확인하고 verification에 기록.
- 필요 시 read-only external API regression checks 수행.
- Baseline 안정성 확인 후 Prometheus PVC와 storage policy를 별도 task로 검토.
- Alertmanager와 external notification channel을 별도 observability task로 설계.
- Pi temperature metric을 node-exporter textfile collector 또는 별도 exporter로 추가 검토.
- 실제 resource 사용량을 관찰해 Prometheus/Grafana request·limit과 retention 재조정.
