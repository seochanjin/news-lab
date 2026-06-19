# 일상 운영 점검

[Runbook index로 돌아가기](../RUNBOOK.md)

이 절차는 사람이 production 상태를 확인할 때 사용한다. Command 결과에는
credential, private address, kubeconfig 내용, 원문 기사 데이터를 남기지 않는다.

## 1. Cluster

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get events -A \
  --sort-by=.lastTimestamp
```

확인 기준:

- 예상 node가 모두 `Ready`다.
- 필요한 Pod가 `Running`, 완료된 Job Pod가 `Completed`다.
- Restart count가 계속 증가하지 않는다.
- CPU와 memory가 limit 또는 node capacity에 지속해서 근접하지 않는다.
- Scheduling, image pull, mount, probe, eviction, OOM event가 반복되지 않는다.

## 2. Monitoring

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl top pods -n monitoring
```

Grafana, Prometheus, operator, kube-state-metrics와 각 node의 node-exporter를
확인한다. Prometheus retention은 짧고 storage는 ephemeral일 수 있으므로 오래된
history 부재보다 현재 target과 최근 metric 유무를 우선한다.

Grafana port-forward와 login은 사람이 수행하며 credential 값을 기록하지 않는다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward \
  -n monitoring svc/monitoring-grafana 3000:80
```

## 3. Application

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get service news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate \
  news-api-tls news-api-newslab-tls
```

Human operator가 production API 확인을 선택한 경우:

```bash
curl -i https://api.dev-scj.site/health
curl -i https://api.newslab.ai.kr/health
curl https://api.dev-scj.site/version
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/extractor/status
```

## 4. Scheduled workload

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs \
  --sort-by=.metadata.creationTimestamp
```

Schedule, suspend state, last schedule, active Job과 최근 실패를 확인한다. 상세 절차는
[CronJob 운영](cronjobs.md)을 따른다.

## 점검 기록

```text
NewsLab routine operation check
- Checked at:
- Operator:
- Cluster access available: [ ] yes [ ] no
- Nodes Ready: [ ] yes [ ] no
- Unexpected Pod state/restarts: [ ] none [ ] found
- Resource pressure: [ ] none [ ] found
- Monitoring healthy: [ ] yes [ ] no [ ] not checked
- news-api available: [ ] yes [ ] no
- Production /health: [ ] success [ ] failed [ ] not checked
- Collector latest run: [ ] healthy [ ] failed [ ] not checked
- Extractor latest run: [ ] healthy [ ] failed [ ] not checked
- Daily topic latest run: [ ] healthy [ ] failed [ ] not checked
- Follow-up owner/action:
- Sanitized evidence:
```

실제 operator 결과가 없으면 production verification을 완료로 표시하지 않는다.
