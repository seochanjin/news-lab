# Monitoring과 Dashboard 확인

[Runbook index로 돌아가기](../RUNBOOK.md)

이 절차는 사람이 Tailscale/SSH tunnel과 kubeconfig 접근을 준비한 뒤 Production
Monitoring baseline, Dashboard와 Alertmanager provisioning을 확인할 때 사용한다.
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
- Argo CD diff에서 retention, storage, resource와 의도하지 않은 Alertmanager
  변경이 없는지 확인한다.
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

## 5. Alertmanager Secret 준비와 관리

Alertmanager 외부 전송은 `alert_scope="news-lab"` label을 가진 Alert만
`news-lab-telegram` native Telegram receiver로 보낸다. bot token과 개인 채팅 ID는
Repository나 Helm values가 아니라 `monitoring/news-lab-alertmanager-telegram`
Secret의 `bot-token`, `chat-id` key로 관리한다. 상세 구조는
[Pipeline Operations Alerting 설계](../design/pipeline-operations-alerting.md)를
따른다.

다음 Secret 생성·변경 command는 모두 human-controlled다. 운영자는 먼저 승인된
Telegram bot token과 개인 chat ID를 운영 credential manager에서 준비하고, 각각
한 값만 든 권한 제한 파일을 Git working tree와 일반 `/tmp` 밖에 만든다. 실제
token이나 chat ID를 command 인자, shell history, 문서, ticket, Verification 또는
Helm values에 넣지 않는다. 아래 경로 placeholder는 운영자가 관리하는 안전한 파일
경로로 바꾼다.

```bash
umask 077
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl create secret generic news-lab-alertmanager-telegram \
  --namespace monitoring \
  --from-file=bot-token=/path/to/operator-managed-bot-token-file \
  --from-file=chat-id=/path/to/operator-managed-chat-id-file \
  --dry-run=client -o yaml | \
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f -
```

Helm 변경 전에 다음 read-only command로 resource 이름과 두 key 존재만 확인한다.
`-o yaml`, `-o json`, `jsonpath`로 `.data` 값을 출력하거나 Base64를 decode하지
않는다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret \
  -n monitoring news-lab-alertmanager-telegram \
  -o go-template='name={{.metadata.name}}{{"\n"}}{{if index .data "bot-token"}}bot-token-key=present{{"\n"}}{{end}}{{if index .data "chat-id"}}chat-id-key=present{{"\n"}}{{end}}'
```

예상 sanitized 결과는 Secret 이름, `bot-token-key=present`와
`chat-id-key=present`이며 실제 값은 포함하지 않는다. key가 없거나
이름·namespace가 다르면 Helm 반영을 중단하고 Secret 입력을 바로잡는다.

Secret과 values diff를 사람이 승인한 뒤에만 Task에 적힌
`helm upgrade --dry-run=server --hide-secret`을 먼저 수행한다. raw render나
`--hide-secret` 없는 diff는 저장·공유하지 않는다. 실제 Helm upgrade, rollout과
test alert 적용은 별도의 human-controlled 단계이며 UNIT-05 전에는 완료로 기록하지
않는다. 실제 sanitized 적용·전달 evidence가 제공된 뒤에만 완료로 기록한다.

### 회전, 전달 실패와 rollback

bot token 또는 chat ID 회전은 같은 이름과 key로 Secret을 갱신한 뒤 사람이
Alertmanager의 configuration reload 또는 rollout 상태를 확인하고 test alert의
firing과 resolved 알림을 개인 채팅에서 모두 수신해야 완료다. 기존 값은 새 값 검증
전까지 운영 credential manager의 rollback 값으로 보존하되 Repository나
Verification에 복사하지 않는다.

알림이 수신되지 않으면 다음 순서로 점검한다.

1. Alert에 `alert_scope="news-lab"` label이 있는지 확인한다.
2. Secret 이름과 `bot-token`, `chat-id` key 존재, Alertmanager Pod의 mount 상태를
   값 출력 없이 확인한다.
3. Alertmanager configuration status와 log에서 parse, file read와 Telegram API
   delivery 오류를 확인하고 token과 chat ID는 sanitize한다.
4. firing만 오거나 resolved만 누락되면 receiver render의
   `send_resolved: true`와 test alert 해제 상태를 확인한다.
5. 새 credential 또는 chat ID 문제라면 기존 승인 값으로 같은 Secret을 다시 만들고,
   사람이 reload 또는 rollout과 firing·resolved 전달을 재검증한다.

Secret 파일과 shell session 정리는 운영 credential 정책에 따라 사람이 수행한다.
Secret 삭제, `kubectl apply`, Helm upgrade와 rollout을 Agent가 실행하지 않는다.

### Silence 운영 원칙

Silence는 계획된 점검이나 이미 대응 중인 Alert의 중복 전달을 제한할 때만 사람이
생성한다. `alert_scope="news-lab"`만으로 넓게 묶지 않고 가능하면 `alertname`,
`namespace` 등 대상 matcher를 함께 지정하며, 종료 시각과 사유·담당자를 남긴다.
무기한 Silence와 chart 기본 Alert 전체를 가리는 matcher는 사용하지 않는다.

생성 전에는 현재 firing Alert와 matcher 영향 범위를 확인하고, 생성 후에는 의도한
Alert만 silenced인지 확인한다. 점검이 끝나면 만료 또는 삭제 상태를 확인하고 실제
Rule이 정상 상태인지 다시 조회한다. Silence 생성·삭제와 운영 API 호출은 모두
human-controlled이며 sanitized 결과만 Verification에 기록한다.

### 전달 test rule 경계

전달 테스트용 Repository artifact는
`k8s/monitoring/rules/news-lab-alert-delivery-test.yaml`이다. 이 파일은
`vector(1)` 기반이며 정상 운영 rule Kustomization에서 제외되어 있다. 운영자는
승인된 운영 검증에서만 test rule을 별도로 적용하고 1분 이상 지속된 firing 수신을
확인한다. 이어서 운영용 임시 사본의 expression을 `vector(0) > 0`으로 바꿔
적용하고 resolved 수신을 확인한다. `vector(0)`만 사용하면 값이 0인 시계열이
계속 반환되어 firing 상태가 유지된다. Repository 원본은 firing 검증용
`vector(1)`을 유지한다.

firing과 resolved evidence를 확보한 뒤 test `PrometheusRule` object를 제거하고,
`news-lab-pipeline-alerts`의 실제 Alert 3종만 남았는지 확인한다. 적용·수정·삭제
command는 human-controlled이며, 실제 수행 결과와 sanitized Alert 이름·상태만
Verification에 기록한다.

### 76차 Production 검증 완료 baseline

사람이 Monitoring Helm revision `4`와 Alertmanager `v0.32.2`를 반영하고 실제
NewsLab Rule 3종이 `health=ok`, `state=inactive`, `lastError` 없음임을 확인했다.
별도 test Rule로 Telegram firing 메시지를 수신한 뒤 `vector(0) > 0`으로 전환해
resolved 메시지를 수신했고, test Rule 제거 후 Kubernetes API `NotFound`와
Prometheus Rules API 제거 상태를 확인했다. 최종 Production에는
`news-lab-pipeline-alerts`만 유지한다.

Alertmanager 전달과 NewsLab Rule에서는 오류가 확인되지 않았다. Prometheus의 기존
`kube-apiserver-burnrate.rules`에서는 간헐적인 evaluation timeout이 있었지만 현재
관찰 대상 Rule은 `health=ok`, `lastError` 없음이다. 정확한 원인은 76차에서 확정하지
않았으며, 기본 Rule timeout을 조정하거나 Rule을 비활성화하지 않는다. 후속 운영
개선에서는 retention, query timeout, Rule 평가 시간과 Prometheus CPU·메모리·스토리지
상태를 함께 조사한다.
