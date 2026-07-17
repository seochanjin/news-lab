# Task: Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## Goal

현재 설치된 `kube-prometheus-stack`의 Repository 설정과 Production 수집 상태를 조사하고, 이미 수집 중인 Kubernetes metric만 사용해 NewsLab Pipeline 운영 상태를 확인할 수 있는 Grafana Dashboard 1차 버전을 구성한다.

대상 Pipeline은 다음 네 CronJob이다.

```text
news-rss-collector
news-daily-topic-pipeline
news-three-day-topic-pipeline
news-weekly-topic-pipeline
```

다음 순서로 진행한다.

```text
Repository Monitoring 설정 조사
→ Production Prometheus target과 storage 상태 확인
→ CronJob·Job·Pod·Node metric과 label inventory 작성
→ 실제 Prometheus에서 PromQL 검증
→ NewsLab Pipeline Operations Dashboard 구성
→ Kubernetes metric만으로 확인할 수 없는 업무 metric 목록 확정
→ 76차 Alerting에서 사용할 후보 query와 조건 정리
```

이번 Task의 핵심 완료 기준은 예제 PromQL을 추측으로 추가하는 것이 아니라, 현재 Cluster에서 실제로 노출되는 metric과 label을 확인한 뒤 유효한 query만 Dashboard에 반영하는 것이다.

Dashboard는 다음 질문에 답할 수 있어야 한다.

- 네 CronJob이 최근 언제 schedule되었는가?
- CronJob이 suspend 상태인가?
- 현재 실행 중인 Job이 있는가?
- 최근 Job이 성공했는가, 실패했는가?
- 선택 기간 동안 Job 실패가 몇 번 발생했는가?
- Pipeline Pod의 CPU·Memory 사용량은 어느 정도인가?
- Pod restart, Pending, scheduling 실패가 발생했는가?
- 세 Node가 Ready 상태이며 CPU·Memory 여유가 있는가?

## Scope

- `k8s/monitoring/kube-prometheus-stack-values.yaml`과 관련 Architecture, Runbook, Verification 문서를 조사한다.
- 현재 Grafana Dashboard provisioning 방식이 존재하는지 확인한다.
- 기존 Dashboard JSON, ConfigMap, Grafana sidecar, `dashboardProviders`와 values 기반 Dashboard 설정 존재 여부를 확인한다.
- Prometheus chart version, retention, replica, resource request/limit, nodeSelector와 storage 설정을 확인한다.
- Prometheus가 PVC를 사용하는지, ephemeral storage를 사용하는지 실제 Repository 설정과 Production object에서 각각 확인한다.
- Prometheus, kube-state-metrics, node-exporter, kubelet/cAdvisor 등 Dashboard에 필요한 target의 실제 `UP/DOWN` 상태를 확인한다.
- Production 확인 명령은 read-only로 제한하고 사람이 직접 실행하거나 제공한 sanitized 결과만 문서화한다.
- `kube-state-metrics`가 노출하는 CronJob과 Job metric 이름 및 label을 실제 Prometheus에서 확인한다.
- 다음 metric 계열의 존재 여부를 확인하되, 존재한다고 가정하지 않는다.

```text
kube_cronjob_*
kube_job_*
kube_pod_*
kube_node_*
container_cpu_usage_seconds_total
container_memory_working_set_bytes
node_cpu_seconds_total
node_memory_*
node_filesystem_*
```

- 각 query에서 실제로 사용할 다음 label의 존재와 값을 확인한다.

```text
namespace
cronjob
job_name
job
owner_name
owner_kind
pod
container
node
condition
status
phase
reason
```

- Job 이름의 생성 suffix에 직접 의존하기보다 `CronJob → Job owner` 관계를 사용할 수 있는지 우선 검토한다.
- `default` namespace와 네 NewsLab CronJob을 명시적으로 제한하는 PromQL을 작성한다.
- RSS·Daily·3-day·Weekly를 구분할 수 있는 Dashboard variable 또는 고정 panel 구성을 선택한다.
- Grafana Dashboard 이름은 `NewsLab Pipeline Operations`를 기본값으로 한다.
- Dashboard의 기본 시간 범위와 timezone 표시 방식을 명시한다.
- Dashboard에 최소한 다음 panel group을 구성한다.

```text
1. Pipeline Overview
- CronJob 최근 schedule 시각
- 가능한 경우 최근 successful 시각
- CronJob suspend 상태
- 현재 active Job 수

2. Job Status
- 최근 Job 성공·실패 상태
- 선택 기간 내 실패 횟수
- 현재 실행 중인 Job
- 최근 생성된 Job 목록 또는 상태 Timeline

3. Pipeline Pod Resources
- CPU 사용량
- Memory working set
- Container restart 증가량
- Pending Pod
- Unschedulable 또는 scheduling 실패 상태
- 확인 가능한 경우 Container waiting reason

4. Cluster Nodes
- Node Ready 상태
- Node CPU 사용률
- Node Memory 사용률
- Node별 Pod 수
- 실제 metric이 확인된 경우 filesystem 여유 공간
```

- metric이 없거나 현재 stack 설정에서 수집되지 않는 panel은 임의의 대체 query로 숨기지 않고, 제외 이유를 문서에 기록한다.
- Dashboard JSON 또는 현재 Repository provisioning 방식에 맞는 최소 artifact를 추가한다.
- 기존 provisioning 방식이 없다면 Dashboard JSON과 수동 import 절차를 우선 제공하고, 새로운 범용 Dashboard 배포 framework를 만들지 않는다.
- Dashboard panel별 PromQL, unit, legend, threshold와 `No data` 의미를 문서화한다.
- Kubernetes metric만으로 확인할 수 없는 NewsLab 업무 상태를 명시한다.

```text
Pipeline partial_success
DB run table의 last success와 상세 status
candidate count
embedding created/reused/missing count
saved topic count
failed topic count
Pipeline stage별 duration
Summary provider 오류 수
```

- 위 업무 metric은 후속 Task 후보로만 기록하고 이번 Task에서 구현하지 않는다.
- 76차 Alerting에서 사용할 수 있는 CronJob, Node, Pod restart query 후보와 관찰 결과를 정리한다.
- Architecture, Runbook, Verification, PR과 devlog에 실제 조사 결과, Dashboard 범위와 한계를 기록한다.

## Do not change

- FastAPI `/metrics` endpoint 추가
- 애플리케이션 custom metric 구현
- DB run table을 조회하는 exporter 또는 sidecar 추가
- Prometheus Pushgateway 추가
- OpenTelemetry, Loki, Tempo 도입
- Alertmanager 활성화 또는 설정 변경
- `PrometheusRule`과 운영 Alert Rule 추가
- Telegram, email, Slack 등 알림 채널 구성
- Prometheus retention `1d` 변경
- Prometheus PVC, `storageSpec`, StorageClass와 장기 storage 추가
- Approved Fix 7의 Grafana CPU limit `300m → 200m` Production baseline 정합화
  외 Grafana, Prometheus와 kube-state-metrics의 resource request/limit 변경
- Monitoring workload의 nodeSelector와 toleration 변경
- Helm chart version upgrade
- Production Helm release upgrade 또는 재설치
- Grafana public Ingress, SSO, anonymous access와 외부 공개
- Backend application business logic
- RSS 수집, Embedding, Topic Selection, Extraction과 Summary logic
- CronJob schedule, timezone, command, concurrencyPolicy, deadline, retry 정책
- Kubernetes Deployment, Service, Ingress, Secret과 application resource 설정
- PostgreSQL schema, migration, Supabase SQL과 운영 데이터
- Frontend repository와 UI
- Argo CD Manual Sync 정책
- 사람이 승인해야 하는 다음 작업의 자동 실행
  - PR merge
  - `kubectl apply/delete/patch/edit/rollout`
  - `helm upgrade/install/uninstall`
  - Argo CD Sync
  - DB migration
  - Secret 변경
  - Production 장애 주입

## Expected files

작업 전에 실제 Repository 구조와 Grafana provisioning 방식을 확인하고 최소 범위로 수정한다.

현재 확인된 Monitoring 기준 파일:

```text
k8s/monitoring/kube-prometheus-stack-values.yaml
docs/verification/infra-monitoring-baseline.md
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

예상 Dashboard artifact:

```text
k8s/monitoring/dashboards/news-lab-pipeline-operations.json
```

현재 provisioning 방식에 따라 다음 중 필요한 파일만 추가 또는 수정한다.

```text
k8s/monitoring/*dashboard*.yaml
k8s/monitoring/*configmap*.yaml
k8s/monitoring/kube-prometheus-stack-values.yaml
```

기존 provisioning 방식이 없고 수동 import 방식을 선택하면 불필요한 ConfigMap과 values 변경을 만들지 않는다.

예상 검증 또는 Test 파일:

```text
tests/test_monitoring_dashboard.py
scripts/validate_monitoring_dashboard.*
```

별도 Test 파일이 필요하지 않으면 JSON parse, PromQL API query와 Helm render 검증 명령을 Verification에 기록한다.

예상 문서 파일:

```text
docs/design/pipeline-operations-dashboard.md
docs/runbooks/monitoring.md
docs/tasks/feat-pipeline-operations-dashboard.md
docs/reviews/feat-pipeline-operations-dashboard-coderabbit.md
docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md
docs/verification/feat-pipeline-operations-dashboard.md
docs/pr/feat-pipeline-operations-dashboard.md
docs/devlog/feat-pipeline-operations-dashboard.md
```

실제 task script가 생성한 filename과 기존 문서 구조를 우선한다. 같은 목적의 Dashboard, ConfigMap, validation script와 Runbook을 중복 생성하지 않는다.

구현 전에 다음 항목을 조사한다.

- 현재 `kube-prometheus-stack` chart version과 설치 command 기록
- Grafana sidecar와 Dashboard provider 활성화 여부
- 기존 Dashboard artifact와 ConfigMap label 규칙
- Prometheus service 이름과 안전한 local access 방식
- Prometheus target 목록과 scrape 상태
- `kube-state-metrics` version과 CronJob/Job metric 노출 상태
- kubelet/cAdvisor와 node-exporter target 상태
- 네 CronJob의 namespace와 정확한 object name
- Job owner label 또는 metric join에 사용할 실제 label
- Prometheus retention, storage와 PVC 상태
- Dashboard를 Repository에서 배포할지 JSON import artifact로 관리할지

## DB changes

없음.

- migration file 추가 없음
- table, column, index와 constraint 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음
- DB run table query 추가 없음
- Dashboard가 PostgreSQL 또는 Supabase에 직접 연결하지 않음

Kubernetes metric으로 알 수 없는 업무 상태는 이번 Task에서 DB query로 우회하지 않고 후속 custom metric 또는 exporter 후보로 기록한다.

## API changes

없음.

- 신규 endpoint 없음
- FastAPI `/metrics` 추가 없음
- 기존 endpoint path 변경 없음
- request/response schema 변경 없음
- 인증과 권한 정책 변경 없음
- Dashboard가 Production API를 polling해 metric처럼 사용하지 않음

Production read-only 회귀 확인이 필요한 경우 기존 `/health`와 Home API를 사용하되, Dashboard datasource는 Prometheus만 사용한다.

## Test commands

### Repository Monitoring 구조 조사

```bash
find k8s docs tests scripts \
  \( -iname '*prometheus*' \
  -o -iname '*grafana*' \
  -o -iname '*monitoring*' \
  -o -iname '*dashboard*' \) \
  -print
```

```bash
rg -n \
  "kube-prometheus-stack|retention|storageSpec|grafana|dashboardProviders|sidecar|ServiceMonitor|PodMonitor|PrometheusRule|Alertmanager" \
  k8s docs
```

```bash
rg -n \
  "kind: CronJob|name: news-rss-collector|name: news-daily-topic-pipeline|name: news-three-day-topic-pipeline|name: news-weekly-topic-pipeline" \
  k8s
```

### 변경 범위 확인

```bash
git branch --show-current
git status --short
git diff --stat
git diff --name-only
```

### Values와 YAML parse 확인

```bash
ruby -e '
require "yaml"
Dir["k8s/monitoring/**/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
```

### Dashboard JSON parse 확인

실제 Dashboard JSON 경로를 확정한 뒤 실행한다.

```bash
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json \
  >/dev/null
```

확인 조건:

- JSON syntax 오류 없음
- Dashboard title이 `NewsLab Pipeline Operations`
- datasource UID 또는 datasource variable 사용 방식이 현재 Grafana 환경과 호환됨
- panel ID 중복 없음
- panel query에 placeholder나 검증되지 않은 metric이 남지 않음

### Helm render 확인

Monitoring values 또는 provisioning manifest를 변경한 경우 실행한다.

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/news-lab-monitoring-rendered.yaml
```

실제 설치 chart version이 다르면 Production과 Repository 기록을 확인한 뒤 동일한 version을 사용한다.

### Production read-only object 조사

다음 명령은 사람이 연결 상태를 확인한 뒤 실행하고 sanitized 결과를 Verification에 기록한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get pods,svc -n monitoring -o wide

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheus,servicemonitor,podmonitor,prometheusrule -A

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get cronjob,job,pod -n default -o wide

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get pvc -A

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get nodes -L observability,workload

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheus -A -o yaml
```

확인 항목:

- Monitoring Pod와 target component 상태
- Prometheus retention
- `storageSpec`와 PVC 존재 여부
- ServiceMonitor와 PodMonitor selector 범위
- 네 CronJob의 schedule, suspend와 active 상태
- 최근 Job 이름과 owner 관계
- Node label과 Ready 상태

### Prometheus local access

실제 Prometheus service 이름을 먼저 확인한 뒤 사람이 안전한 local port-forward를 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl port-forward \
  -n monitoring \
  svc/<PROMETHEUS_SERVICE> \
  9090:9090
```

다른 terminal에서 확인한다.

```bash
curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/api/v1/targets
curl -fsS http://127.0.0.1:9090/api/v1/label/__name__/values
```

Credential, internal IP와 전체 target response는 문서에 원문 그대로 저장하지 않는다.

### Metric inventory 확인

다음 metric 이름은 후보이며 실제 존재 여부와 label을 확인한 뒤 사용한다.

```text
kube_cronjob_status_last_schedule_time
kube_cronjob_status_last_successful_time
kube_cronjob_spec_suspend
kube_cronjob_status_active
kube_job_status_succeeded
kube_job_status_failed
kube_job_status_active
kube_job_created
kube_job_owner
kube_pod_container_status_restarts_total
kube_pod_status_phase
kube_pod_status_scheduled
kube_node_status_condition
container_cpu_usage_seconds_total
container_memory_working_set_bytes
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_memory_MemTotal_bytes
```

Prometheus query API 예시:

```bash
PROMQL='kube_cronjob_spec_suspend{namespace="default"}'

curl -fsSG \
  --data-urlencode "query=${PROMQL}" \
  http://127.0.0.1:9090/api/v1/query
```

각 Dashboard query를 같은 방식으로 실행해 다음을 확인한다.

- query status가 `success`
- 예상 label이 존재
- 네 CronJob 또는 세 Node가 의도대로 구분됨
- unrelated namespace와 workload가 포함되지 않음
- empty result라면 metric 부재인지 현재 event 부재인지 구분해 기록

### Targeted Test

Validation test 또는 script를 추가한 경우 실제 경로에 맞게 실행한다.

```bash
PYTHONPATH=. pytest -q -k "monitoring or dashboard or prometheus"
```

최소 검증 항목:

- Dashboard JSON parse
- 필수 Dashboard title과 panel group 존재
- 네 CronJob 이름 또는 variable filter 반영
- 금지된 업무 metric과 DB datasource 미사용
- Alertmanager와 `PrometheusRule` 신규 변경 없음
- retention과 storage 설정 변경 없음

### 전체 Test

애플리케이션 코드를 변경하지 않더라도 Repository 회귀 확인이 필요한 경우 실행한다.

```bash
PYTHONPATH=. pytest -q
```

### 정적 검증

```bash
git diff --check
```

```bash
rg -n \
  "partial_success|candidate_count|embedding_count|saved_topic_count|failed_topic_count" \
  k8s/monitoring
```

Kubernetes metric Dashboard에 존재하지 않는 업무 metric 이름을 가짜 PromQL로 추가하지 않았는지 확인한다.

```bash
git diff --name-only -- \
  app scripts db migrations requirements.txt
```

기대 결과: application, Pipeline, DB와 dependency 변경 없음.

### Production Grafana 확인

사람이 local port-forward 또는 기존 operator access path를 사용한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl port-forward \
  -n monitoring \
  svc/monitoring-grafana \
  3000:80
```

확인 항목:

- Dashboard가 import 또는 provisioning됨
- Panel query 오류 없음
- 네 CronJob이 구분돼 표시됨
- Job, Pod와 Node panel이 실제 데이터 또는 설명 가능한 `No data` 상태를 표시함
- Dashboard refresh 후 지속적으로 query 성공
- 기존 Grafana Dashboard와 datasource에 회귀 없음

Dashboard import, ConfigMap 적용 또는 Helm upgrade가 필요한 경우 사람이 diff를 검토하고 별도 승인 후 수행한다. Agent는 Production mutation을 실행하지 않는다.

## Acceptance criteria

- 현재 `kube-prometheus-stack` values와 관련 운영 문서가 조사돼 있다.
- 실제 Production Prometheus object에서 retention, storage, PVC와 replica 상태를 확인했다.
- Prometheus, kube-state-metrics, node-exporter와 필요한 kubelet/cAdvisor target 상태가 기록돼 있다.
- CronJob, Job, Pod와 Node에 사용할 실제 metric 이름과 label inventory가 작성돼 있다.
- 존재하지 않거나 수집되지 않는 metric을 존재한다고 기록하지 않는다.
- Dashboard에 사용하는 모든 PromQL이 실제 Prometheus query API에서 syntax 검증됐다.
- Dashboard query가 `default` namespace와 NewsLab workload 범위로 제한된다.
- `NewsLab Pipeline Operations` Dashboard artifact가 Repository에 존재한다.
- RSS·Daily·3-day·Weekly CronJob의 최근 schedule 시각을 확인할 수 있다.
- 실제 metric이 제공되는 경우 최근 successful 시각을 확인할 수 있다. 제공되지 않으면 대체 근거와 한계를 문서화한다.
- CronJob suspend와 active Job 상태를 확인할 수 있다.
- 최근 Job 성공·실패와 선택 기간 내 실패 횟수를 확인할 수 있다.
- Pipeline Pod CPU·Memory와 restart 증가량을 확인할 수 있다.
- Pending, Unschedulable 또는 scheduling 실패 상태를 현재 metric이 허용하는 범위에서 확인할 수 있다.
- 세 Node의 Ready, CPU와 Memory 상태를 확인할 수 있다.
- filesystem panel은 실제 node-exporter metric과 mount filter가 검증된 경우에만 포함한다.
- panel별 unit, legend, query 의미와 `No data` 해석이 문서화돼 있다.
- Dashboard JSON이 parse되고 provisioning 또는 import 절차가 재현 가능하다.
- Production Grafana에서 panel query 오류 없이 Dashboard가 표시된다.
- Kubernetes metric으로 확인할 수 없는 `partial_success`와 Pipeline 업무 metric 목록이 별도로 기록돼 있다.
- 76차 Alerting 후보인 CronJob 이상, Node NotReady와 Pod restart query가 실제 metric을 기준으로 정리돼 있다.
- Alertmanager, `PrometheusRule`, 알림 채널, retention과 storage는 변경되지 않는다.
- FastAPI, DB, Frontend, Pipeline logic과 CronJob schedule에 변경이 없다.
- Production mutation은 사람이 승인하고 수행하며, 실행하지 않은 검증은 통과로 기록하지 않는다.
- Architecture, Runbook, Verification, PR과 devlog가 실제 조사 결과와 Dashboard 한계를 반영한다.

## Notes

- 이번 Task는 Kubernetes 운영 metric을 조사하고 시각화하는 단계다. NewsLab custom business metric 구현 단계가 아니다.
- Kubernetes Job 성공은 애플리케이션의 `success`, `partial_success`, `failed` 업무 상태와 동일하지 않을 수 있다.
- Weekly Pipeline이 일부 Topic 저장에 성공한 뒤 `partial_success`로 종료해도 Kubernetes Job exit code 정책에 따라 성공 또는 실패로만 보일 수 있다. 이 차이는 Dashboard 한계로 명시한다.
- UNIT-02에서 `kube_cronjob_status_last_successful_time` 노출을 확인했지만 prewarm
  Job 성공도 반영되므로 정기 실행 최근 성공 시각에는 사용하지 않는다.
- UNIT-02에서 owner 관계만으로는 prewarm Job이 제외되지 않음을 확인했다. 정기
  Job은 숫자 suffix canonical filter와 owner metric join을 함께 사용한다.
- UNIT-03에서 정기 Pipeline Pod 9개와 Pod/Node resource·status query를 실제
  Prometheus에서 검증했다. 24시간 range panel의 `No data`는 0이나 정상으로
  해석하지 않으며 retention `1d`와 마지막 실행 시각을 함께 확인한다.
- Node legend는 `node_uname_info.nodename`을 사용하지 않고
  `kube_node_info.internal_ip`과 node-exporter `instance`를 join해 Kubernetes
  node 이름을 사용한다.
- Prometheus retention `1d`와 persistent storage 부재가 확인되면 장기 추세, 월간 성공률과 SLO 측정에 적합하지 않음을 기록한다. 이번 Task에서 변경하지 않는다.
- Dashboard에서 `No data`를 정상 또는 성공으로 해석하지 않는다. metric 부재, event 부재, scrape 장애를 구분한다.
- Grafana timezone은 운영자가 날짜 경계를 오해하지 않도록 Dashboard 또는 문서에서 명시한다.
- Dashboard를 풍부하게 만들기 위해 검증되지 않은 panel을 추가하지 않는다. 운영 질문에 직접 답하는 최소 panel을 우선한다.
- Alert threshold와 notification route는 76차 범위다. 이번 Task에서는 query 후보와 현재 관찰값만 정리한다.
- Production read-only 조사에서도 credential, Secret, private IP, 전체 target metadata와 민감한 label 값은 문서에 저장하지 않는다.
- 모든 `kubectl` 명령은 다음 prefix를 사용한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl ...
```

- `kubectl apply`, Helm upgrade, Dashboard import와 Grafana 변경은 사람이 diff와 영향 범위를 확인한 뒤 수행한다.
- 승인 Fix 1에 따라 stat/table panel의 활성 Prometheus target 20개는
  `instant=true`, `range=false`를 사용한다. PromQL 내부 기간 집계와 Dashboard
  기본 범위는 변경하지 않는다.
- 승인 Fix 2에 따라 CronJob schedule과 정기 Job completion timestamp를 표시하는
  세 panel은 최종 PromQL 결과에 `1000 *`을 적용해 Unix seconds를 Grafana
  DateTime milliseconds로 변환한다.
- empty result가 정상일 수 있는 active/Pending/scheduling false/waiting panel에
  `or vector(0)`을 추가하지 않는다. 빨간 경고 없는 일반 `No data`와
  query/datasource 오류를 나타내는 빨간 경고 `No data`를 구분한다.

## Implementation Units

- [x] UNIT-01: Repository Monitoring 구성, Dashboard provisioning 방식과 Production read-only baseline 조사
- [x] UNIT-02: CronJob·Job metric inventory, label 관계와 Pipeline PromQL 검증
- [x] UNIT-03: Pod·Container·Node metric inventory와 Resource·Scheduling PromQL 검증
- [x] UNIT-04: `NewsLab Pipeline Operations` Dashboard JSON과 최소 provisioning 또는 import artifact 구성
- [x] UNIT-05: Dashboard validation, Helm/YAML/JSON parse, 전체 회귀와 문서 정합성 검증
- [x] UNIT-06: 사람이 수행한 Production Grafana 확인 결과 반영과 76차 Alerting 후보·업무 metric 공백 확정
  - 76차 Alerting 후보와 Kubernetes metric으로 확인할 수 없는 업무 metric 공백 확정
  - Approved Fix 4의 Grafana data proxy timeout `120s` repository 설정과 Helm
    chart `86.2.0` render 검증 완료
  - Approved Fix 5의 Dashboard 자동 refresh `15m` 적용과 local render 검증 완료
  - Approved Fix 6의 CPU·Memory·Restart 원본 metric canonical 정기 Pod 조기
    필터와 local render 검증 완료
  - 수정 후 Production Prometheus target `20/20`과 개별 query 성능 재측정 완료
  - 네 query 동시 성능 재측정 3회 모두 통과, 최대 `79.418s`로 권장 `90s` gate 충족
  - Approved Fix 7의 Grafana CPU limit을 Production Helm Revision 1·2 baseline인
    `200m`으로 정합화하고 chart `86.2.0` render 검증 완료
  - Approved Fix 8의 Secret 노출 대응 절차 문서화 완료; 운영자가 기존 admin
    password를 회전하고 임시 patch 파일과 shell password 변수를 제거했으며
    Secret 값은 읽거나 기록하지 않음
  - 운영자 evidence로 Dashboard ConfigMap 적용, Helm Revision 3 배포, Grafana
    rollout, timeout `120s`, resources baseline과 health 확인 완료
  - Production Grafana에서 Dashboard 로드, 4개 row와 20개 query panel, 실제
    2026년 KST timestamp, 일반 `No data`, Node 3대와 빨간 query warning 미재발 확인
