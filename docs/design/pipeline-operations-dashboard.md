# Pipeline Operations Dashboard 설계

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 현재 조사 범위

이 문서는 `NewsLab Pipeline Operations` Dashboard의 근거를 UNIT별로 누적한다.
현재 UNIT-01의 Monitoring baseline, UNIT-02의 CronJob/Job PromQL, UNIT-03의
Pod/Container/Node PromQL 검증과 UNIT-04 Dashboard artifact 구성을 완료했다.
UNIT-05의 JSON/YAML/Kustomize/Helm 정적 검증과 전체 pytest 회귀도 통과했다.
운영자가 Production Prometheus query API에서 Dashboard의 활성 target 20개를
Approved Fix 4~6 적용 후 다시 검증해 `20 passed / 0 failed`를 확인했다. 이어
Dashboard ConfigMap, chart `86.2.0` Helm Revision 3와 Grafana rollout을 적용하고
Production UI에서 4개 row, timestamp, resource/status panel, 일반 `No data`와
Node 3대를 확인했다. UNIT-01~06과 전체 Verification은 완료됐다.

## Repository Monitoring baseline

Repository의 Monitoring 설정 파일은
`k8s/monitoring/kube-prometheus-stack-values.yaml` 하나다. 설치 및 render 기록은
`kube-prometheus-stack` chart `86.2.0`을 고정한다.

| 항목 | Repository 또는 chart `86.2.0` render 기준 |
| --- | --- |
| Prometheus replica | `1` |
| Prometheus retention | `1d` |
| Prometheus storage | `storageSpec`/`storage` override 없음, PVC template 미생성 |
| Prometheus resources | request `100m`/`256Mi`, limit `500m`/`512Mi` |
| Prometheus placement | `observability: "true"` |
| Grafana resources | request `50m`/`256Mi`, limit `200m`/`512Mi` |
| Grafana placement | `observability: "true"` |
| Grafana data proxy timeout | `120s`; Prometheus의 `2m` query timeout보다 먼저 종료되던 약 `30s` proxy 제한 완화 |
| kube-state-metrics placement | `observability: "true"` |
| Prometheus Operator placement | `observability: "true"` |
| node-exporter | control-plane/master 및 `news-edge-worker` taint toleration |
| Alertmanager | 비활성화 |

`storageSpec`이 없다는 사실은 Repository desired state와 local render에서
Prometheus PVC가 생성되지 않는다는 뜻이다. 실제 Production Prometheus object와
cluster 전체 PVC 부재는 live read-only 조회로 별도 확인해야 한다. `1d` retention과
ephemeral storage 조합에서는 장기 추세, 월간 성공률과 SLO를 신뢰할 수 없다.
이번 Task에서는 retention이나 storage, Prometheus query timeout을 변경하지 않는다.
Grafana data proxy timeout만 `grafana.ini`의 `[dataproxy] timeout = 120`으로
명시하며, chart `86.2.0` render에서 해당 설정이 생성되는 것을 검증한다.

Production Helm Revision 1과 2의 Grafana CPU limit은 모두 `200m`이지만 기존
Repository 선언은 `300m`이었다. 전체 values 기반 Helm upgrade에서 이번 timeout
fix와 무관한 `200m → 300m` 변경이 섞이지 않도록 Repository limit을 실제 배포
baseline인 `200m`으로 정합화한다. CPU request `50m`과 memory request/limit
`256Mi`/`512Mi`는 유지한다. 이는 query 성능 개선이나 resource 증설이 아니라
승인되지 않은 drift 방지가 목적이다.

## Helm 검토와 Grafana Secret 경계

기존 release manifest와 client-side `helm template`의 raw diff 과정에서 Grafana
Secret의 `admin-password` Base64 값이 출력됐다. Base64는 암호화가 아니므로 해당
password는 노출된 것으로 취급한다. 실제 Secret 값, Base64 값과 디코딩 값은
Repository, Verification, PR, Devlog와 외부 문서에 기록하지 않는다.

앞으로 Production Helm 변경 범위는 `helm upgrade --dry-run=server
--hide-secret`으로 검토한다. raw `helm get manifest`와 client-side render의 Secret
리소스를 일반 diff 파일로 비교하지 않으며, admin Secret 또는 그 checksum의
비의도적 변경이 보이면 적용을 중단한다. Agent는 Secret을 읽거나 디코딩하거나
변경하지 않는다.

사람은 운영 Secret 관리 경로에서 Grafana admin password를 회전하고, 민감한
임시 manifest/diff 파일을 삭제한 뒤 Grafana rollout, 새 password 로그인과
`/api/health`를 확인해야 한다. 이 보안 조치와 Production Helm 적용은 사람이
결과를 제공하기 전까지 `human-required`다.

네 CronJob manifest에는 namespace가 생략되어 모두 `default` namespace를
사용하며 object 이름은 다음과 같다.

- `news-rss-collector`
- `news-daily-topic-pipeline`
- `news-three-day-topic-pipeline`
- `news-weekly-topic-pipeline`

## Dashboard provisioning 결정

Repository에는 custom Dashboard JSON, Dashboard ConfigMap, `dashboardProviders`
override가 없다. 다만 chart `86.2.0` 기본값과 local render에는 다음 provisioning
경로가 이미 존재한다.

- Grafana dashboard sidecar가 활성화된다.
- sidecar는 모든 namespace에서 `grafana_dashboard: "1"` label을 가진
  ConfigMap을 감시한다.
- `monitoring-grafana-config-dashboards`가 `sidecarProvider`를 제공한다.
- chart 기본 Dashboard ConfigMap 27개가 같은 label로 render된다.

Dashboard JSON은
`k8s/monitoring/dashboards/news-lab-pipeline-operations.json`을 source로 유지한다.
같은 디렉터리의 최소 `kustomization.yaml`이 JSON을
`news-lab-pipeline-operations-dashboard` ConfigMap으로 만들고 기존
`grafana_dashboard: "1"` label을 붙인다. JSON을 ConfigMap YAML에 중복 저장하지
않으며 values의 sidecar/provider도 재정의하지 않는다. 이 하위 디렉터리는 현재
Argo CD Application의 non-recursive `k8s/` 경로에 자동 포함되지 않으므로 실제
provisioning은 사람이 별도 승인 후 수행한다.

## Dashboard 계약

- title/UID: `NewsLab Pipeline Operations` / `newslab-pipeline-operations`
- datasource: chart가 생성하는 Prometheus UID `prometheus`
- 기본 시간 범위/refresh: 최근 `24h` / `15m`; 계산량이 큰 24시간 query의
  자동 실행 경합을 줄이되 수동 refresh와 시간 범위 선택은 유지
- timezone: `Asia/Seoul`
- Pipeline 구분: 고정된 네 CronJob selector와 `cronjob` 또는 `owner_name` legend
- 장기 이력: retention `1d`와 ephemeral storage 때문에 보장하지 않음
- target 실행 방식: 활성 Prometheus target 20개 모두 `instant=true`,
  `range=false`; stat/table panel은 현재 시점의 결과와 PromQL 내부 range 집계만
  사용하고 Grafana Range query를 중복 실행하지 않음
- DateTime 입력: `kube_cronjob_status_last_schedule_time`과
  `kube_job_status_completion_time`의 Unix seconds 최종 결과에 `1000 *`을 적용해
  Grafana `dateTimeAsIso`가 요구하는 milliseconds로 변환

| Group | Panel | Unit | Legend 또는 표시 | Threshold | `No data` 핵심 의미 |
| --- | --- | --- | --- | --- | --- |
| Pipeline Overview | CronJob Last Schedule | ISO 시각 | `cronjob` | 없음 | CronJob series, scrape 또는 filter 확인 |
| Pipeline Overview | Last Successful Regular Job | ISO 시각 | `owner_name` | 없음 | 성공 정기 Job/series 부재 또는 retention 경과 |
| Pipeline Overview | CronJob Suspend | short/state | `cronjob` | `1` red | 0과 다르며 metric/scrape를 확인 |
| Pipeline Overview | Active Regular Jobs | short | `owner_name` | `1` blue | 실행 없음으로 단정하지 않고 owner series 확인 |
| Job Status | Retained Succeeded/Failed, Completion Time | short/ISO 시각 | owner와 Job | failed `1` red | 삭제된 Job 이력은 표시되지 않음 |
| Job Status | Failures in Selected Range | short | `owner_name` | `1` red | 보존 중인 Job만 집계하며 장기 총 실패 수가 아님 |
| Pipeline Pod Resources | Peak CPU/Memory 24h | cores/bytes IEC | `cronjob` | 없음 | retention 경과 또는 resource series 부재 |
| Pipeline Pod Resources | Restart Increase | short | Pipeline/Pod | `1` red | 선택 기간 series와 owner join 확인 |
| Pipeline Pod Resources | Pending/Scheduling False/Waiting | short table | Pipeline/Pod/reason | 없음 | 결과 없음과 metric 자체 부재를 구분 |
| Cluster Nodes | Ready | state | `node` | Ready 외 red | node series 또는 scrape 확인 |
| Cluster Nodes | CPU/Memory | percent 0-100 | `node` | 70 orange, 90 red | node-exporter와 node mapping 확인 |
| Cluster Nodes | Running Pods | short | `node` | 없음 | kube-state-metrics와 Pod info join 확인 |
| Cluster Nodes | Root Filesystem | percent 0-100 | `node` | 75 orange, 90 red | ext4 `/` series와 node mapping 확인 |

모든 Pipeline query는 `namespace="default"`와 네 NewsLab 이름 또는 숫자 suffix
정기 Job filter를 사용한다. Node panel은 cluster의 세 Node 전체를 의도적으로
표시한다. Dashboard description도 `No data`를 정상 또는 0으로 해석하지 않도록
동일한 운영 경계를 포함한다.

UNIT-04 작성 직후에는 local tunnel 부재로 전체 query를 재검증하지 못했지만,
UNIT-05 마지막 운영자 검증에서 활성 Prometheus target 20개를 Production query
API로 모두 실행했다. 모든 query가 `status=success`였고 parse/execution error,
many-to-many matching과 duplicate series 오류는 없었다. Grafana의 `$__range`는
Dashboard 기본 범위에 맞춰 `24h`로 치환했으며 `label_replace`의 `$1`은 정규식
capture group으로 유지했다. Approved Fix 4~6 적용 후에도 같은 방식으로 `20/20`
성공과 기존 cardinality를 확인했다. 수정 후 개별 실행시간은 Failures `10.75s`,
CPU `23.04s`, Memory `12.46s`, Restart `41.92s`였다. 운영자가 네 query 동시
실행을 세 번 재측정했고 최대 `79.418s`, total `79.420s`로 필수 `120s`와 권장
`90s` gate를 모두 통과했다.

## CronJob과 Job metric 설계

Production Prometheus에서 다음 kube-state-metrics 계열은 각각 12개 series를
반환했다. 여기서 `count(...)` 결과 `12`는 Job 상태값이나 Job 성공 횟수가 아니라
현재 selector에 일치하는 metric series 수다.

| metric | 확인한 주요 label | 값의 의미 |
| --- | --- | --- |
| `kube_job_status_completion_time` | `namespace`, `job_name` | Job 완료 시각의 Unix timestamp |
| `kube_job_status_succeeded` | `namespace`, `job_name` | Job의 succeeded 수 |
| `kube_job_status_failed` | `namespace`, `job_name`, 환경에서 노출되는 경우 `reason` | Job의 failed 수 |
| `kube_job_status_active` | `namespace`, `job_name` | 현재 active Pod 수 |
| `kube_job_owner` | `namespace`, `job_name`, `owner_kind`, `owner_name` | Job과 owner object의 관계; metric value는 관계 존재를 나타내는 `1` |

`default` namespace에서 네 NewsLab CronJob을 `owner_kind="CronJob"`과
`owner_name`으로 제한해도 12개 Job이 일치했다. 이 중 3개가 수동 prewarm
Job이므로 owner 관계만으로는 정기 실행을 구분할 수 없다. prewarm Job도 동일한
CronJob owner를 가지기 때문이다. 정기 Job 9개만 선택하는 canonical filter는
CronJob controller가 생성한 숫자 suffix까지 제한하는 다음 matcher다.

```promql
job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
```

Dashboard의 정기 Job query는 이 matcher와 `namespace="default"`를 항상 함께
사용한다. owner join은 네 Pipeline 소속임을 확인하고 결과에 `owner_name`을
전달하는 용도이며, prewarm 제외 수단으로 단독 사용하지 않는다.

정기 실행의 최근 성공 시각은 다음처럼 완료 시각, 성공 상태와 owner 관계를
결합해 Pipeline별 최댓값으로 계산한다.

```promql
max by (owner_name) (
  kube_job_status_completion_time{
    namespace="default",
    job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
  }
  * on (namespace, job_name)
    (kube_job_status_succeeded{
      namespace="default",
      job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
    } == 1)
  * on (namespace, job_name) group_left(owner_name)
    kube_job_owner{
      namespace="default",
      owner_kind="CronJob",
      owner_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"
    }
)
```

Production 검증에서 filtered 정기 Job 9개는 모두
`kube_job_status_succeeded == 1`이었고, 위 join은 RSS, Daily, 3-day, Weekly 네
Pipeline 모두 결과를 반환했다.

`kube_cronjob_status_last_successful_time`은 정기 실행 성공 시각 panel에 사용하지
않는다. Weekly 정기 Job의 `completion_time`은 `1783870652`였지만 CronJob의
`lastSuccessfulTime`은 `1784093724`였다. 후자는 prewarm 실행의 성공으로
갱신됐으므로 정기 실행과 수동 실행을 구분하지 못한다.

## No data와 retention 한계

정기 실행 성공 시각 query의 `No data`는 성공을 뜻하지 않는다. 다음 원인을
구분해서 확인해야 한다.

- canonical filter에 일치하는 정기 Job 또는 성공한 Job이 없음
- Job object 정리로 kube-state-metrics series가 사라짐
- kube-state-metrics scrape 장애 또는 metric 부재
- label 변경이나 query filter 불일치
- Prometheus 재시작에 따른 ephemeral 시계열 유실

`Currently Active Regular Jobs`, `Pending Pipeline Pods`,
`Scheduling Failed / False`, `Container Waiting Reason`은 조건에 일치하는 series가
없으면 empty vector가 정상적으로 반환될 수 있다. 이 네 query에
`or vector(0)`을 추가하지 않는다. Grafana에서 빨간 경고 아이콘이 없는 일반
`No data`는 현재 조건 일치 series 부재 가능성을 확인하고, 빨간 경고 아이콘이
있는 `No data`는 query/datasource 오류로 분류해 Inspect 결과를 확인한다.

Prometheus retention은 `1d`이고 persistent storage가 없다. 따라서 range panel은
하루를 넘는 실행 이력을 완전하게 보장하지 않으며, Job object가 삭제된 series는
retention 경과 후 조회할 수 없다. 이 Dashboard는 장기 성공률, 월간 추세 또는
SLO의 근거로 사용하지 않는다.

## Pipeline Pod canonical join

Production inventory의 `count(metric)` 결과는 다음과 같다. 숫자는 상태값이나
event 횟수가 아니라 selector에 일치한 series 수다.

| Metric | Series | Metric | Series |
| --- | ---: | --- | ---: |
| `kube_pod_owner` | 43 | `kube_pod_info` | 43 |
| `kube_pod_container_info` | 49 | `kube_pod_container_status_restarts_total` | 49 |
| `kube_pod_status_phase` | 215 | `kube_pod_status_scheduled` | 129 |
| `kube_pod_status_unschedulable` | 0 | `kube_pod_status_reason` | 344 |
| `kube_pod_container_status_waiting_reason` | 0 | `container_cpu_usage_seconds_total` | 93 |
| `container_memory_working_set_bytes` | 93 | `kube_node_status_condition` | 36 |
| `node_cpu_seconds_total` | 64 | `node_memory_MemAvailable_bytes` | 3 |
| `node_memory_MemTotal_bytes` | 3 | `node_filesystem_avail_bytes` | 15 |
| `node_filesystem_size_bytes` | 15 | `node_uname_info` | 3 |

`kube_pod_owner`의 Job owner 이름을 `job_name`으로 복사한 뒤 UNIT-02의 filtered
`kube_job_owner`와 join한다. 다음 표현은 `pod`, `job_name`, `cronjob` label을 가진
정기 Pipeline Pod 9개를 반환했으며 숫자 suffix filter가 prewarm Pod를 제외했다.

```promql
label_replace(
  kube_pod_owner{namespace="default", owner_kind="Job"},
  "job_name", "$1", "owner_name", "(.+)"
)
* on (namespace, job_name) group_left(cronjob)
label_replace(
  kube_job_owner{
    namespace="default",
    owner_kind="CronJob",
    job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
  },
  "cronjob", "$1", "owner_name", "(.+)"
)
```

아래 Pod panel query에서 `PIPELINE_PODS`는 이 canonical join을 뜻한다.
`PIPELINE_PODS`와 아래 `NODE_MAP`은 문서 가독성을 위한 표기이며 PromQL identifier가
아니다. UNIT-04 Dashboard query에는 각 표현식을 inline한다. 운영자가 실행한
inline canonical query는 Verification에 기록한다.

## Pipeline Pod 상태 panel 계약

| Panel | Canonical PromQL의 핵심 | Unit | Legend | 검증 결과 |
| --- | --- | --- | --- | --- |
| Container restarts | `sum by (cronjob, pod) (increase(kube_pod_container_status_restarts_total{pod=~"CANONICAL_REGULAR_POD"}[$__range]) * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS))` | `short` | `{{cronjob}} / {{pod}}` | 정기 Pod 9개 모두 `0` |
| Pending Pod | `(kube_pod_status_phase{phase="Pending"} == 1) * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)` | `short` | `{{cronjob}} / {{pod}}` | resultCount `0` |
| Unschedulable Pod | `(kube_pod_status_unschedulable == 1) * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)` | `short` | `{{cronjob}} / {{pod}}` | metric series와 query result 모두 `0` |
| Scheduled false fallback | `(kube_pod_status_scheduled{condition="false"} == 1) * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)` | `short` | `{{cronjob}} / {{pod}}` | resultCount `0` |
| Container waiting reason | `(kube_pod_container_status_waiting_reason == 1) * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)` | `short` | `{{cronjob}} / {{pod}} / {{container}} / {{reason}}` | metric series와 query result 모두 `0` |

`kube_pod_status_phase`와 `kube_pod_status_scheduled`는 상태별 series를 함께
노출하므로 series 존재만으로 현재 상태라고 판단하지 않고 반드시 `== 1`로
활성 상태를 제한한다. `kube_pod_status_unschedulable`이 현재 노출되지 않으므로
Dashboard에서는 `scheduled{condition="false"}`를 scheduling 실패 대체 근거로
사용한다. `No data`는 정상 또는 0이 아니며 metric 부재, 대상 Pod 부재, scrape
장애와 filter 불일치를 구분한다.

## Pipeline Pod resource panel 계약

CPU panel의 canonical query는 Pod container CPU를 합산한 5분 `rate`를 만들고,
최근 24시간 subquery에서 Pipeline별 최댓값을 구한다.

CPU, Memory, Restart의 원본 metric selector에는 owner join 전에 다음 정기 Pod
regex를 적용한다. 숫자 suffix가 있는 정기 Job Pod만 조기에 제한해 prewarm Pod와
무관한 container series를 제외하며, 뒤의 `kube_pod_owner` → `kube_job_owner`
join은 소유 관계와 `cronjob` label 전달을 계속 검증한다.

```promql
pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*"
```

```promql
max by (cronjob) (
  max_over_time(
    (
      sum by (namespace, pod) (
        rate(container_cpu_usage_seconds_total{
          namespace="default",
          pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*",
          container!="", container!="POD", image!=""
        }[5m])
      )
      * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)
    )[24h:5m]
  )
)
```

- 의미: 순간 peak가 아니라 최근 24시간 안에서 가장 높았던 5분 평균 CPU
- unit: `cores`
- legend: `{{cronjob}}`
- 검증값: RSS `0.00445`, Daily `0.02937`, 3-day `0.09195` core, Weekly
  `No data`

Memory panel은 요청된 canonical 순서대로 container별 24시간 최대 working set을
먼저 구하고, 같은 Pod의 container를 합산한 뒤 Pipeline 실행 Pod 중 최댓값을
선택한다.

```promql
max by (cronjob) (
  sum by (cronjob, pod) (
    max_over_time(container_memory_working_set_bytes{
      namespace="default",
      pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*",
      container!="", container!="POD", image!=""
    }[24h])
    * on (namespace, pod) group_left(job_name, cronjob) (PIPELINE_PODS)
  )
)
```

- 의미: 최근 24시간의 container별 최대 working set을 Pod별로 합산한 값
- unit: `bytes (IEC)`
- legend: `{{cronjob}}`
- 검증값: RSS `42618880` bytes(약 `40.6 MiB`), Daily `80535552`
  bytes(약 `76.8 MiB`), 3-day `117649408` bytes(약 `112.2 MiB`), Weekly
  `No data`

Weekly의 CPU와 Memory `No data`는 0이나 정상 상태를 뜻하지 않는다. Weekly 실행
후 24시간이 지났고 Prometheus retention도 `1d`이므로 해당 range series가 조회
범위에 남아 있지 않은 결과다.

## Node panel 계약

`node_uname_info`는 3개 series를 제공하지만 Pi의 `nodename`이 Kubernetes object
이름 `pi-worker-node`가 아니라 `scj`로 노출됐다. Dashboard legend에는 이를 직접
사용하지 않는다. node-exporter `instance`의 host 부분과
`kube_node_info.internal_ip`을 `label_replace`로 맞춰 Kubernetes `node` label을
전달한다.

```promql
label_replace(
  kube_node_info,
  "instance", "$1:9100", "internal_ip", "(.+)"
)
```

아래 query의 `NODE_MAP`은 이 mapping을 뜻한다.

| Panel | Canonical PromQL | Unit | Legend | 검증 결과 |
| --- | --- | --- | --- | --- |
| Node Ready | `kube_node_status_condition{condition="Ready", status="true"} == 1` | `short` | `{{node}}` | 세 Node 모두 `1` |
| CPU usage | `100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))) * on (instance) group_left(node) (NODE_MAP)` | `percent (0-100)` | `{{node}}` | master `8.1%`, worker `53.2%`, Pi `0.8%` |
| Memory usage | `100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * on (instance) group_left(node) (NODE_MAP)` | `percent (0-100)` | `{{node}}` | master `20.3%`, worker `16.4%`, Pi `7.5%` |
| Running Pods | `sum by (node) ((kube_pod_status_phase{phase="Running"} == 1) * on (namespace, pod) group_left(node) kube_pod_info)` | `short` | `{{node}}` | master `14`, worker `13`, Pi `2` |
| Root filesystem usage | `100 * (1 - node_filesystem_avail_bytes{fstype="ext4", mountpoint="/"} / node_filesystem_size_bytes{fstype="ext4", mountpoint="/"}) * on (instance) group_left(node) (NODE_MAP)` | `percent (0-100)` | `{{node}}` | master `12.9%`, worker `21.8%`, Pi `8.7%` |

CPU는 최근 5분 idle 비율의 평균을 사용률로 변환한다. Memory는
`MemAvailable / MemTotal`을 사용한다. Running Pod 수는 `phase="Running" == 1`과
`kube_pod_info`를 join하므로 Completed Pod를 제외한다.

Filesystem inventory에서 운영 대상은 `fstype="ext4"`, `mountpoint="/"`다.
`tmpfs`, `/run`, `/run/lock`, `/boot`와 vfat EFI/firmware partition은 root
filesystem panel에서 제외한다. Filesystem도 `NODE_MAP`으로 Kubernetes node
이름을 사용한다.

## Production baseline 상태

최초 read-only 조회는 운영자 SSH tunnel 부재로 실패했지만, tunnel 준비 후
운영자가 재검증했다. Production은 chart `86.2.0`, Prometheus replica `1`,
retention `1d`, persistent storage/PVC 없음으로 Repository baseline과 일치했다.
Prometheus, kube-state-metrics, node-exporter와 kubelet/cAdvisor target은 모두
`UP`이었다. CronJob/Job metric과 owner 관계는 위 UNIT-02 결과로 확인했다.

Pod/Container/Node metric과 resource/scheduling query는 UNIT-03 운영자 검증을
완료했다. UNIT-05 local artifact 검증, 전체 회귀와 Dashboard target 20개의
Production Prometheus API 재검증도 완료했다. UNIT-06 Production 적용과 Grafana
UI 사람 검증까지 완료해 전체 Verification은 `passed`다.

## Kubernetes metric으로 확인할 수 없는 업무 metric

UNIT-06에서 다음 공백을 후속 custom metric 또는 exporter 후보로 확정했다.
Kubernetes Job은 process exit code에 따른 성공/실패만 보여 주며 아래 값은 현재
Prometheus scrape target에서 제공되지 않는다.

| 공백 | Kubernetes metric으로 대체할 수 없는 이유 |
| --- | --- |
| Pipeline `partial_success` | Job 성공/실패는 일부 Topic 저장 성공과 상세 상태를 구분하지 못함 |
| DB run table last success·상세 status | kube-state-metrics는 application DB record를 읽지 않음 |
| candidate count | Pod/Job resource metric에 선정 대상 건수가 포함되지 않음 |
| embedding created/reused/missing count | CPU/Memory는 embedding 처리 결과를 구분하지 못함 |
| saved/failed topic count | Job exit code로 Topic별 부분 저장 결과를 복원할 수 없음 |
| Pipeline stage별 duration | Job 전체 시간과 stage별 소요 시간은 다름 |
| Summary provider 오류 수 | container waiting/restart는 provider API 오류를 보여 주지 않음 |

이 Dashboard에 DB datasource, 가짜 PromQL, Pushgateway 또는 exporter를 추가하지
않는다. metric 이름, label cardinality, 수집 경로와 retention은 별도 Task에서
설계해야 한다.

## 76차 Alerting 후보

아래는 실제 노출과 join을 확인한 metric에 기반한 후보다.
`PrometheusRule`, Alertmanager, threshold, `for` 기간과 notification route는 76차에서
결정하며 이 Task에서 추가하지 않는다.

| 후보 | Query 핵심 | 관찰값 | 76차 결정 항목 |
| --- | --- | --- | --- |
| CronJob suspend | `kube_cronjob_spec_suspend{namespace="default",cronjob=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"} == 1` | 네 CronJob 모두 `0` | 의도한 중지의 silence 정책 |
| CronJob schedule 지연 | `time() - kube_cronjob_status_last_schedule_time{namespace="default",cronjob=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"}` | 네 CronJob series 확인 | 일간 3개와 주간 1개의 허용 지연을 분리 |
| 정기 Job 실패 | `kube_job_status_failed{namespace="default",job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"} > 0` 후 `kube_job_owner` join | 보존 정기 Job 9개 모두 `0` | Job 삭제·`1d` retention 전 평가 간격 |
| Node NotReady | `kube_node_status_condition{condition="Ready",status="true"} != 1` | 세 Node 모두 `1` | scrape 소실 `absent` 후보와 `for` 기간 |
| Pipeline Pod restart | `increase(kube_pod_container_status_restarts_total{namespace="default",pod=~"CANONICAL_REGULAR_POD"}[15m]) > 0` 후 정기 Pod canonical owner join | 정기 Pod 9개 restart `0`; 24h query 9개 | window, completed Pod 보존, 회복 알림 정책 |

CronJob schedule 지연은 일간 실행 세 개의 매일 03:00/04:00/05:00과 Weekly의
매주 월요일 00:30, 모두 `Asia/Seoul`을 같은 threshold로 평가하지 않는다.
`1d` retention과 ephemeral storage 때문에 장기 window query는 알림 근거로
사용하지 않는다. `15m` restart window는 76차에서 조정할 초안이다. UNIT-06의
Production Prometheus target 검증은 `20 passed / 0 failed`였고, Grafana UI에서도
빨간 query warning이 재발하지 않았다.

## 현재 UNIT 경계

- UNIT-05 완료 범위: JSON/YAML/Kustomize/Helm render, Dashboard 구조와
  namespace/datasource 제한, 금지 metric scan, 문서 정합성, 전체 pytest 회귀와
  Production Prometheus의 활성 target `20/20` query API 재검증
- UNIT-06 문서화 범위에서 Alerting 후보와 업무 metric 공백을 확정했다.
- 운영자가 Production ConfigMap과 Helm Revision 3를 적용하고 Grafana rollout,
  API health, 4개 row와 panel 표시, timestamp, 일반 `No data`, Node mapping과
  빨간 query warning 미재발을 확인했다.
- UNIT-06 checklist와 전체 Verification은 완료했다.

Elasticsearch bundled plugin 설치의 permission 오류는 Dashboard 기능에 영향을
주지 않은 후속 점검 항목이며, 이 브랜치에서는 plugin 설정을 변경하지 않는다.
