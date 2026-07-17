# Monitoring과 Dashboard 확인

[Runbook index로 돌아가기](../RUNBOOK.md)

이 절차는 사람이 Tailscale/SSH tunnel과 kubeconfig 접근을 준비한 뒤 Production
Monitoring baseline과 Dashboard provisioning을 read-only로 확인할 때 사용한다.
출력에는 credential, private address, kubeconfig 내용과 전체 target metadata를
남기지 않는다.

## 1. Production object baseline

다음은 조회 명령이며 object를 변경하지 않는다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods,svc -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl get prometheus,servicemonitor,podmonitor,prometheusrule -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pvc -A
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl get nodes -L observability,workload
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get prometheus -A -o yaml
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl get cronjob,job,pod -n default -o wide
```

확인하고 sanitized 결과만 Verification에 옮긴다.

- 설치 release/chart version과 Monitoring Pod readiness
- Prometheus replica, `1d` retention, storage/PVC 상태
- ServiceMonitor와 PodMonitor 존재 범위
- 세 node의 label과 Ready 상태
- 네 NewsLab CronJob의 schedule, suspend, active와 최근 Job owner

Repository에는 Prometheus `storageSpec` override가 없으므로 Production object와
PVC 조회가 다르면 drift로 기록하고 변경하지 않는다.

## 2. Prometheus target 확인

실제 Prometheus Service 이름을 먼저 확인한다. 아래 port-forward는 사람이 local
terminal에서 실행하고, 종료할 때 `Ctrl-C`로 중단한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward \
  -n monitoring svc/<PROMETHEUS_SERVICE> 9090:9090
```

다른 terminal에서 read-only endpoint를 확인한다.

```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/api/v1/targets
```

Prometheus, kube-state-metrics, node-exporter와 kubelet/cAdvisor target의 health를
요약한다. 전체 target response, internal address와 불필요한 label은 문서에
복사하지 않는다. DOWN target은 Dashboard의 `No data`와 metric 부재를 구분하는
근거로 기록한다.

## 3. Grafana provisioning 기준

Chart `86.2.0`의 현재 render는 `grafana_dashboard: "1"` label을 가진 ConfigMap을
Grafana dashboard sidecar가 감시한다. Repository Dashboard를 반영할 때는 다음을
사람이 확인한다.

- Dashboard JSON과 ConfigMap diff가 승인된 범위인지 확인한다.
- ConfigMap이 `monitoring` namespace와 기존 label 규칙을 사용하는지 확인한다.
- Argo CD diff에서 retention, storage, resource, Alertmanager 변경이 없는지
  확인한다.
- 사람이 현재 Application 포함 범위와 별도 provisioning diff를 확인한 후에만
  Production에 반영한다.

Agent는 `kubectl apply`, Helm upgrade와 Argo CD Sync를 실행하지 않는다. 문제가
발생하면 새 Dashboard ConfigMap 변경을 되돌리는 Git revert PR을 준비하고,
사람이 diff 검토와 승인된 provisioning 경로로 복원한다. 기존 chart Dashboard와
datasource는 삭제하거나 재설정하지 않는다.

### Dashboard artifact render와 사람 통제 반영

Repository 검토 단계에서는 다음 local read-only render만 실행한다.

```bash
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-rendered.yaml
```

render 결과에서 namespace `monitoring`, ConfigMap 이름
`news-lab-pipeline-operations-dashboard`, label `grafana_dashboard: "1"`과 JSON
key를 확인한다. datasource UID는 chart가 생성하는 `prometheus`다.
Helm render에서는 Grafana ConfigMap의 `[dataproxy] timeout = 120`과 기존
Grafana request `50m`/`256Mi`, limit `200m`/`512Mi` 및 기존 Prometheus replica
`1`, retention `1d`, storage 미설정을 함께 확인한다. Grafana CPU limit `200m`은
Production Helm Revision 1·2와 일치해야 하며 `300m`으로 render되면 적용을
중단한다.

현재 Argo CD Application은 `k8s/`를 recursive하게 읽지 않으므로 이 하위
Kustomization을 자동 배포하지 않는다. 다음 변경 명령은 human-controlled이며
Dashboard JSON 전체 query 검증, diff 승인과 operator tunnel 준비 후에만 사람이
실행한다. Grafana timeout은 Dashboard ConfigMap과 별도의 Helm release values
변경이므로 사람이 두 diff를 모두 검토한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl diff -k k8s/monitoring/dashboards

KUBECONFIG=~/.kube/oci-k3s.yaml \
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --dry-run=server \
  --hide-secret \
  --debug \
  >/tmp/monitoring-upgrade-dry-run.txt 2>&1
```

raw `helm get manifest`와 client-side `helm template`의 Secret 리소스를 일반 diff
파일로 비교하지 않는다. `--hide-secret`이 없는 dry-run도 사용하지 않는다. 검토
결과에서 Grafana admin Secret 또는 Secret checksum의 비의도적 변경, Grafana CPU
limit `300m`, Prometheus/Alertmanager/Ingress/Service 변경이 보이면 적용을
중단한다.

기존 raw manifest diff에서 Grafana `admin-password` Base64 값이 출력됐으므로
Base64를 디코딩하거나 문서에 복사하지 않고 노출된 password로 취급한다. 승인된
diff 이후에도 다음은 모두 human-controlled 작업이다.

- 운영 Secret 관리 경로에서 Grafana admin password 회전
- Secret 값이 포함됐을 수 있는 local 임시 manifest/diff 파일 삭제
- Dashboard ConfigMap 적용과 Helm upgrade
- Grafana rollout, 새 password 로그인과 `/api/health` 확인

운영자는 실제 Secret 값이나 Base64를 Verification에 제공하지 않는다. 임시 파일
삭제 대상은 다음이며 Agent는 이 명령을 실행하지 않는다.

```bash
rm -f /tmp/monitoring-manifest-before.yaml
rm -f /tmp/monitoring-helm.diff
rm -f /tmp/monitoring-upgrade-dry-run.txt
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply -k k8s/monitoring/dashboards

KUBECONFIG=~/.kube/oci-k3s.yaml \
helm upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl rollout status deployment/monitoring-grafana -n monitoring
```

반영 후에는 ConfigMap 존재를 read-only로 확인하고 Grafana port-forward에서
Dashboard title, 네 Pipeline 구분, panel query 오류와 기존 dashboard 회귀를
확인한다. 실제 결과만 Verification에 기록한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get configmap \
  -n monitoring news-lab-pipeline-operations-dashboard
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl port-forward \
  -n monitoring svc/monitoring-grafana 3000:80
curl -fsS http://127.0.0.1:3000/api/health
```

문제가 생기면 Dashboard/values 변경을 되돌리는 Git revert PR을 만들고 사람이
승인된 반영 경로로 이전 desired state를 복원한다. datasource와 기존 chart
dashboard ConfigMap은 삭제하거나 재설정하지 않는다.

## 4. Grafana UI 확인 결과 제공

운영자는 Dashboard 반영 후 credential과 private address를 제외하고 다음
결과를 Verification에 제공한다.

- ConfigMap 이름과 `grafana_dashboard: "1"` label
- Dashboard title/UID, `Asia/Seoul`, 기본 24h, 자동 refresh `15m`
- Grafana `/etc/grafana/grafana.ini`의 `[dataproxy] timeout = 120`
- Grafana admin password 회전 완료, 새 password 로그인과 `/api/health` 정상
- 네 CronJob 구분과 prewarm Job 제외
- 20개 target query error와 설명 가능한 `No data` panel
- 20개 target이 Instant 전용으로 실행되고 Range query가 중복 실행되지 않음
- 빨간 경고 없는 일반 `No data`와 query/datasource 오류인 빨간 경고
  `No data`를 구분하고 후자는 Inspect 결과 확인
- CronJob schedule과 정기 Job completion 세 panel이 1970년이 아니라 실제
  2026년 KST 시각을 표시
- title, legend, unit, threshold 표시
- refresh 후 query 성공과 기존 dashboard/datasource 회귀

ConfigMap 적용 성공만으로 UI 검증을 통과 처리하지 않으며, sanitized
text 결과나 screenshot을 근거로 각 항목을 구분해 남긴다.

## 5. 76차 Alerting 인계 경계

CronJob schedule/suspend/failed Job, Node Ready와 Pipeline Pod restart query를
Alerting 후보로 인계한다. Alertmanager, `PrometheusRule`, notification route,
threshold과 `for` 기간은 이 Task에서 변경하지 않는다. 일간과 주간
CronJob은 stale threshold를 분리하고 `1d` retention과 Job object 정리 한계를
반영한다. 정확한 query와 관찰값은
[Dashboard 설계](../design/pipeline-operations-dashboard.md#76차-alerting-후보)를 따른다.
