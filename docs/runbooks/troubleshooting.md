# 장애 초기 대응

[Runbook index로 돌아가기](../RUNBOOK.md)

변경 전에 read-only 증거를 수집한다. Label, manifest, resource, Pod, Job,
CronJob, node 상태를 바꾸는 command는 사람이 결정한다.

## 공통 진단

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe \
  <resource-type> <resource-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs \
  <pod-name> --all-containers --tail=200
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs \
  <pod-name> --all-containers --previous --tail=200
```

`--previous`는 container restart가 있을 때 사용한다.

## Node NotReady

1. Node condition, taint, event를 확인한다.
2. 해당 node의 Pod 영향과 다른 node capacity를 확인한다.
3. 마지막 monitoring metric을 다른 node와 비교한다.
4. K3s, host resource, network, Tailscale 상태를 사람이 확인한다.
5. Restart 또는 rejoin은 사람이 결정한다.

## Pod Pending

1. Pod scheduling event를 확인한다.
2. Node readiness, allocatable resource, label, taint, node selector를 비교한다.
3. Capacity, placement, image pull, mount, configuration 문제를 구분한다.
4. Label, taint, resource, manifest 변경 전에 승인을 받는다.

## CrashLoopBackOff 또는 OOMKilled

1. `describe`에서 exit code와 reason을 확인한다.
2. Current/previous log와 restart count를 확인한다.
3. `kubectl top`과 최근 Grafana trend를 확인한다.
4. Image와 configuration reference를 값 노출 없이 확인한다.
5. Rollback, resource 변경, restart, Pod delete는 사람이 결정한다.

## news-api unavailable

1. Deployment replica, Pod, Service, Ingress, Certificate, event를 확인한다.
2. Pod log와 Service endpoint를 확인한다.
3. Application, routing, TLS, DNS, external network 문제를 구분한다.
4. Production `/health` 확인은 human-controlled verification으로 기록한다.
5. Rollout, manifest, certificate, DNS, network 변경은 사람이 결정한다.

## CronJob failure

1. Schedule, suspend, failed Job description, Pod와 log를 확인한다.
2. Collector/extractor run API 또는 topic read API와 실행 시각을 비교한다.
3. Scheduling, image, configuration, DB, provider, script stage 실패를 구분한다.
4. Manual Job, Job delete, CronJob patch/apply는 사람이 결정한다.

## Grafana 또는 Prometheus unavailable

1. Monitoring Pod, Service, event, resource usage, restart count를 확인한다.
2. 영향받은 container의 describe와 log를 확인한다.
3. Grafana만 실패하면 `kubectl top`과 object status를 사용한다.
4. Prometheus 실패 중에는 Grafana metric gap이 예상됨을 기록한다.
5. Restart, Helm 변경, resource 변경, reinstall은 사람이 결정한다.

## 고위험 작업 전 handoff

다음을 남기고 사람에게 넘긴다.

- 현재까지 완료한 조사와 검증
- 필요한 고위험 작업과 이유
- 사람이 실행할 정확한 command
- 성공 시 확인할 결과
- 실패 시 rollback 또는 다음 troubleshooting 단계
