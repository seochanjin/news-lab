# Approved Fixes: Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## Approved Fixes

### 1. 모든 Prometheus target을 Instant 전용으로 변경

Dashboard의 활성 Prometheus target 20개는 모두 `stat` 또는 `table` panel이며, 각 PromQL이 현재 시점의 상태나 query 내부의 기간 집계를 반환하도록 구성돼 있다.

기존 `instant=true`, `range=true` 설정은 Grafana에서 Instant와 Range query를 모두 실행하게 하므로 다음과 같이 변경했다.

```json
{
  "instant": true,
  "range": false
}
```

변경 대상은 활성 Prometheus target 20개 전체다.

다음은 유지한다.

- panel title, panel ID, row 구조
- Dashboard UID와 datasource UID
- PromQL 기간 집계 범위
- timezone `Asia/Seoul`

### 2. Unix timestamp 초 단위를 Grafana DateTime 밀리초 단위로 변환

다음 metric은 Unix timestamp를 초 단위로 반환한다.

- `kube_cronjob_status_last_schedule_time`
- `kube_job_status_completion_time`

Grafana DateTime unit은 값을 밀리초로 해석하므로 다음 세 panel의 최종 PromQL 결과에 `1000 *`을 적용했다.

- `CronJob Last Schedule`
- `Last Successful Regular Job`
- `Regular Job Completion Time`

예시:

```
1000 * kube_cronjob_status_last_schedule_time{
  namespace="default",
  cronjob=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"
}
```

Production Grafana에서 기존 `1970-01-22` 대신 실제 2026년 KST 시각이 표시되는 것을 확인했다.

### 3. 정상적인 empty result와 query error를 구분하는 정책 유지

다음 panel은 현재 해당 이상 상태가 없으면 empty vector와 일반 `No data`가 나올 수 있다.

- `Currently Active Regular Jobs`
- `Pending Pipeline Pods`
- `Scheduling Failed / False`
- `Container Waiting Reason`

이 panel에 일괄적으로 `or vector(0)`을 추가하지 않는다. Prometheus scrape 장애, metric 부재, owner join 불일치를 정상값 `0`으로 숨길 수 있기 때문이다.

다음 기준을 유지한다.

- 빨간 경고 아이콘이 없는 `No data`: 현재 조건에 일치하는 series가 없는지 확인
- 빨간 경고 아이콘이 있는 `No data`: query 또는 datasource 오류로 취급하고 Inspect와 로그 확인

### 4. Grafana data proxy timeout을 120초로 증가

Production Grafana에서 다음 로그를 확인했다.

```
method=POST path=/api/ds/query status=400
 duration=30.006s status_source=downstream
```

같은 요청이 `30.004s`에도 종료됐다. Grafana container의 환경변수, `grafana.ini`, datasource provisioning에는 별도 timeout 설정이 없었다.

Prometheus runtime 설정은 다음과 같다.

```
query.timeout=2m
query.max-samples=50000000
```

따라서 Prometheus의 2분 제한보다 먼저 Grafana data proxy 기본 30초 제한이 요청을 종료하는 것으로 판단한다.

`k8s/monitoring/kube-prometheus-stack-values.yaml`에 다음 설정을 추가한다.

```yaml
grafana:
  grafana.ini:
    dataproxy:
      timeout: 120
```

요구사항:

- 기존 `grafana` values와 충돌하지 않도록 현재 구조에 병합한다.
- Helm chart `86.2.0` render에서 Grafana 설정에 timeout `120`이 포함되는지 assertion한다.
- Agent는 Helm upgrade, rollout, Argo CD Sync를 실행하지 않는다.
- 실제 Production Helm 반영과 Grafana Pod 재기동 확인은 사람이 수행한다.

### 5. Dashboard 자동 새로고침을 5분에서 15분으로 완화

이 Dashboard는 초 단위 실시간 서비스가 아니라 하루 단위 CronJob과 최근 24시간 resource peak를 확인하는 운영 화면이다.

현재 5분 자동 새로고침은 계산량이 큰 24시간 query를 반복 실행해 Prometheus 경합을 증가시킨다.

Dashboard JSON의 자동 refresh를 다음과 같이 변경한다.

```json
{
  "refresh": "15m"
}
```

다음은 유지한다.

- 기본 시간 범위 `now-24h`
- timezone `Asia/Seoul`
- 사용자가 수동으로 Refresh할 수 있는 기능

### 6. Pipeline resource query에 정기 Pod selector를 앞단부터 적용

개별 query 실행 시간은 다음과 같았다.

```
Failures in Selected Range       12.403s
Peak CPU (24h, 5m rate)          27.354s
Peak Memory Working Set (24h)    21.178s
Container Restart Increase       13.680s
```

같은 네 query를 동시에 실행하면 다음까지 증가했다.

```
Peak Memory Working Set (24h)    51.743s
Failures in Selected Range       69.557s
Container Restart Increase       94.156s
Peak CPU (24h, 5m rate)         106.702s
Total wall time                 106.706s
```

PromQL 문법이나 metric 부재가 아니라 동시 실행 시 Prometheus 연산 경합이 발생하는 상태다.

현재 CPU, Memory, Restart query는 `default` namespace의 넓은 container series를 읽은 뒤 owner join으로 Pipeline Pod만 남긴다. 원본 metric selector에 정기 Pipeline Pod regex를 추가해 처음부터 대상 series를 제한한다.

Canonical Pod selector:

```
pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*"
```

적용 대상:

- `container_cpu_usage_seconds_total`
- `container_memory_working_set_bytes`
- `kube_pod_container_status_restarts_total`

예시:

```
container_cpu_usage_seconds_total{
  namespace="default",
  pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*",
  container!="",
  container!="POD",
  image!=""
}
```

필요하면 `kube_pod_owner`에도 동일한 정기 Job/Pod 범위 제한을 추가할 수 있다. 다만 label join과 결과 cardinality는 기존 의미를 유지해야 한다.

필수 보존 조건:

- prewarm Job/Pod 제외
- CPU는 최근 24시간 최대 5분 평균
- Memory는 최근 24시간 최대 working set
- Restart는 Dashboard 선택 범위의 increase
- RSS, Daily, 3-day 결과 유지
- retention `1d`에 따른 Weekly `No data` 정책 유지

### 7. Production Helm revision과 Repository의 Grafana CPU limit drift 정합화

Repository의 최초 모니터링 values는 Grafana CPU limit을 `300m`으로 선언하고 있다.

```yaml
grafana:
  resources:
    requests:
      cpu: 50m
      memory: 256Mi
    limits:
      cpu: 300m
      memory: 512Mi
```

그러나 실제 Helm revision manifest를 확인한 결과는 다음과 같다.

```
Revision 1: Grafana CPU limit 200m
Revision 2: Grafana CPU limit 200m
```

Revision 1과 Revision 2 모두 `200m`이므로 현재 Production의 `200m`은 Helm 적용 후 수동 patch로 생긴 일시적 drift가 아니라, 최초 설치부터 유지된 실제 배포 baseline이다. Revision 2의 memory request/limit은 Repository와 동일한 `256Mi`/`512Mi`다.

전체 Repository values로 Helm upgrade하면 이번 timeout fix와 무관하게 Grafana CPU limit이 `200m → 300m`으로 변경된다. 이번 문제는 Prometheus query 연산 경합과 Grafana data proxy 30초 timeout이 원인이며, Grafana CPU 상한 증가가 필요하다는 근거는 없다.

따라서 Repository의 Grafana resource 선언을 현재 Production baseline에 맞춘다.

```yaml
grafana:
  resources:
    requests:
      cpu: 50m
      memory: 256Mi
    limits:
      cpu: 200m
      memory: 512Mi
```

요구사항:

- Grafana CPU request `50m` 유지
- Grafana CPU limit `200m`으로 Repository 정합화
- memory request `256Mi`, limit `512Mi` 유지
- Prometheus와 기타 monitoring workload resource는 변경하지 않음
- 이 변경을 query 성능 개선으로 설명하지 않음
- 목적은 전체 values 기반 Helm upgrade에서 승인되지 않은 `200m → 300m` 변경을 방지하는 것임

### 8. Helm Secret 노출 방지와 Grafana admin password 회전

기존 release manifest와 client-side `helm template` 결과를 raw diff하는 과정에서 Grafana Secret의 `admin-password` Base64 값이 diff에 출력됐다. 기존 manifest 쪽 값은 현재 Production Secret 값일 가능성이 높고, Base64는 암호화가 아니므로 해당 비밀번호는 노출된 것으로 취급한다.

이번 문서와 Repository에는 실제 Secret 값, Base64 값, 디코딩 값 중 어느 것도 기록하지 않는다.

Codex 요구사항:

- Secret 값을 읽거나 디코딩하거나 다시 출력하지 않음
- Secret 값이나 임시 manifest/diff 내용을 Repository, Notion, PR, Devlog, Verification에 복사하지 않음
- Grafana admin password를 코드나 values 파일에 평문으로 추가하지 않음
- Production Secret 변경, password 회전, Pod restart를 실행하지 않음
- Runbook과 Verification에 사람 수행 보안 조치만 기록

사람이 수행할 보안 조치:

1. 현재 Grafana admin password를 폐기하고 새로운 강한 비밀번호로 회전
2. Helm/Kubernetes의 운영 Secret 관리 경로를 사용하며 Repository와 Notion에 평문을 저장하지 않음
3. Secret 변경 후 Grafana rollout과 로그인, `/api/health`를 확인
4. 실제 Secret 값을 포함할 수 있는 로컬 임시 파일을 삭제

삭제 대상 예시:

```bash
rm -f /tmp/monitoring-manifest-before.yaml
rm -f /tmp/monitoring-helm.diff
rm -f /tmp/monitoring-upgrade-dry-run.txt
```

앞으로 Helm 검토는 다음 원칙을 따른다.

- `helm upgrade --dry-run=server --hide-secret` 사용
- raw Secret manifest를 일반 diff 파일에 저장하지 않음
- Secret checksum이나 Secret 리소스 변경이 의도치 않게 발생하면 Helm upgrade를 중단

### 9. 변경 범위 제한

이번 추가 수정에서 변경을 허용한다.

- `k8s/monitoring/dashboards/news-lab-pipeline-operations.json`
- `k8s/monitoring/kube-prometheus-stack-values.yaml`
- 관련 Design, Approved Fixes, Verification, Task, Runbook, PR, Devlog 문서

변경하지 않는다.

- FastAPI와 application 코드
- Pipeline 실행 코드
- DB, migration, dependency
- Prometheus retention, PVC, storage
- Prometheus `query.timeout`, `query.max-samples`, query concurrency
- Grafana datasource UID와 Dashboard UID
- Alertmanager, `PrometheusRule`, notification route
- custom business metric
- Production Secret과 Grafana admin password

## Rejected or Deferred Suggestions

- Empty result panel 전체에 `or vector(0)`을 추가하지 않는다.
- Weekly Pipeline CPU/Memory의 최근 24시간 `No data`를 강제로 `0`으로 표시하지 않는다.
- Prometheus retention `1d`와 persistent storage 부재는 이번 fix에서 변경하지 않는다.
- Prometheus `query.timeout=2m`을 늘리지 않는다. 느린 query의 자원 점유만 연장할 수 있다.
- `query.max-samples`와 query concurrency를 변경하지 않는다.
- Node나 Monitoring Pod resource 증가는 실제 saturation 근거가 없어 보류한다. Grafana CPU limit은 증가시키지 않고 Production Helm baseline인 `200m`으로 Repository drift만 정합화한다.
- kube-apiserver burn-rate 기본 rule 변경 또는 비활성화는 이번 범위에서 제외한다.
- Recording rule 추가는 이번 최적화와 timeout 완화 후에도 동시 query가 느릴 때 후속 작업으로 분리한다.
- Alerting threshold, `for`, Alertmanager route와 `PrometheusRule` 구현은 76차 후속 범위로 유지한다.
- Kubernetes metric으로 확인할 수 없는 업무 metric은 이번 fix에서 추가하지 않는다.
- Grafana UI에서만 임시로 설정을 수정하고 Repository에 반영하지 않는다.

## Applied Changes

현재 상태: Approved Fix 1~8의 repository 변경, local/read-only 검증과 운영자 Production 적용·UI 검증을 완료했다. 수정 후 네 query 동시 실행은 3회 모두 통과했고, Grafana CPU limit은 Production `200m` baseline에 맞춰 Repository와 배포 상태를 정합화했다. 운영자는 기존 Grafana admin password를 회전하고 임시 patch 파일과 shell password 변수를 제거했다. 실제 Secret 값은 기록하지 않는다.

- [x] 활성 Prometheus target 20개를 `instant=true`, `range=false`로 변경
- [x] 세 timestamp panel의 최종 결과에 `1000 *` 적용
- [x] Dashboard JSON parse와 target assertion 통과
- [x] Kustomize ConfigMap render 통과
- [x] Production Prometheus에서 최신 수정 target 20개 API 재검증: `20 passed / 0 failed`
- [x] Production Grafana에서 timestamp가 실제 2026년 KST로 표시됨을 확인
- [x] Node panel과 기본 Pipeline 상태 panel 정상 표시 확인
- [x] Grafana `/api/ds/query`가 약 30초에서 `status=400`으로 종료되는 로그 확인
- [x] Grafana data proxy timeout `120` repository 설정과 chart `86.2.0` render 확인
- [x] Dashboard 자동 refresh `15m` 적용과 JSON/Kustomize 검증
- [x] CPU, Memory, Restart query의 정기 Pipeline Pod 조기 필터 적용
- [x] 수정 후 JSON/Kustomize/Helm/pytest 검증
- [x] 수정 후 Production Prometheus target 검증: `20 passed / 0 failed`
- [x] 수정 후 네 query 동시 실행 성능 3회 재측정
  - Round 1 최대 `79.418s`, total `79.420s`
  - Round 2 최대 `47.378s`, total `47.382s`
  - Round 3 최대 `50.882s`, total `50.885s`
  - 3회 모두 `Concurrent validation: PASSED`
  - 모든 query `120초` 미만, 가장 느린 결과도 권장 gate `90초` 이하
- [x] Helm Revision 1과 2의 Grafana CPU limit이 모두 `200m`임을 확인
- [x] Repository baseline이 `300m`이고 전체 values upgrade 시 `200m → 300m` drift가 발생함을 확인
- [x] Repository Grafana CPU limit을 Production baseline `200m`으로 정합화
- [x] 관련 Design, Fixes, Task, Verification, Runbook, PR, Devlog에 resource drift와 Secret 노출 대응 반영
- [x] 운영자가 Dashboard ConfigMap을 적용하고 chart `86.2.0`, Revision 3 Helm release가 `deployed`임을 확인
- [x] 운영자가 Grafana admin password를 회전하고 임시 patch 파일과 shell password 변수를 제거
- [x] Grafana rollout, timeout `120`, resources baseline과 API health 확인
- [x] refresh `15m`, 실제 2026년 KST timestamp, 일반 `No data`와 UI 빨간 query warning 미재발 확인
- [x] UNIT-06과 전체 Verification 완료 처리

Codex는 Repository 수정과 local/read-only 검증만 수행한다. Production Secret 변경, password 회전, Helm upgrade, rollout, git push/merge를 실행하지 않는다.

## Verification Required

### Repository 정적 검증

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null

jq -e '
  [
    .. | objects
    | select(.targets? | type == "array")
    | .targets[]
    | select(.expr? != null)
  ] as $targets
  | ($targets | length) == 20
  and all($targets[]; .instant == true and .range == false)
' "$DASHBOARD"

jq -e '.refresh == "15m"' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml

git diff --check
```

추가 assertion:

- 세 timestamp panel에 `1000 *` 유지
- CPU, Memory, Restart 원본 metric selector에 canonical 정기 Pod regex 존재
- Dashboard UID, datasource UID, 4개 row, 20개 target 유지
- CPU `5m` rate와 resource query `24h` window 유지

### Helm render 검증

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-rendered.yaml
```

Rendered Grafana 설정에서 다음을 assertion한다.

```
dataproxy timeout = 120
Grafana CPU request = 50m
Grafana CPU limit = 200m
Grafana memory request = 256Mi
Grafana memory limit = 512Mi
```

기존 설정도 유지해야 한다.

- Prometheus replica `1`
- retention `1d`
- persistent storage 미설정
- Grafana dashboard sidecar label `grafana_dashboard=1`
- Alertmanager 미생성

### Local 회귀 검증

```bash
PYTHONPATH=. pytest -q

git diff --name-only -- \
  app scripts db migrations requirements.txt
```

기대 결과:

- 전체 pytest 통과
- application, Pipeline, DB, migration, dependency diff 없음

### Production Prometheus read-only 기능 검증

수정된 Dashboard의 활성 target 20개를 `/api/v1/query`에서 다시 실행한다.

완료 기준:

```
Targets: 20
Passed: 20
Failed: 0
```

결과 cardinality:

- CronJob query: 4개 Pipeline
- retained regular Job query: 9개, prewarm 제외
- 최근 24시간 CPU/Memory: RSS, Daily, 3-day 3개
- Restart: 정기 Pod 9개
- Node query: 3개 Node
- active/Pending/scheduling false/waiting reason은 `0` result 가능

### Query 성능 재측정

동일한 네 query를 개별과 4개 동시 실행으로 다시 측정한다.

필수 기준:

- 모든 query `status=success`
- 결과 cardinality가 기존과 동일
- 동시 실행 query 각각 `120초` 미만
- 권장 gate: 가장 느린 동시 query `90초` 이하로 Grafana timeout 대비 최소 30초 여유 확보

권장 gate를 충족하지 못하면 timeout을 추가로 늘리지 않고 recording rule 또는 query 재설계를 후속 작업으로 등록한다.

### Production 적용 전 diff

Dashboard ConfigMap:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl diff -k k8s/monitoring/dashboards
```

Helm release는 Secret을 출력하지 않는 server-side dry-run으로 검토한다.

```bash
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

예상 변경:

- Dashboard ConfigMap의 refresh와 PromQL selector
- Grafana 설정의 data proxy timeout `120`
- timeout 설정 변경에 따른 Grafana Pod template config checksum/rollout
- Grafana CPU request `50m`, limit `200m` 유지
- Grafana memory request `256Mi`, limit `512Mi` 유지

허용하지 않는 변경:

- Grafana admin Secret 교체 또는 Secret checksum의 비의도 변경
- Grafana CPU limit `300m` 적용
- Prometheus retention, storage, PVC, query timeout, resource 변경
- Alertmanager, Ingress, Service, replica 변경

raw `helm get manifest`와 client-side `helm template`의 Secret 값을 직접 diff하지 않는다. 예상하지 않은 변경이 있으면 적용하지 않는다.

### 사람이 수행할 Production 적용

Agent가 실행하지 않는다.

사람이 승인 후 다음을 수행한다.

- 민감한 임시 manifest/diff 파일 삭제
- Grafana admin password를 운영 Secret 관리 경로에서 회전
- Dashboard ConfigMap 재적용
- Helm release upgrade
- Grafana Pod rollout 완료 확인
- 새 password 로그인과 Grafana API health 확인

실제 Secret, Base64 값, password는 명령 출력·문서·Notion·PR에 남기지 않는다.

### 사람이 수행할 Production Grafana 검증

- `NewsLab Pipeline Operations` Dashboard 정상 로드
- 기본 시간 범위 `Last 24 hours`, timezone KST 유지
- 자동 refresh `15m` 확인
- `Failures in Selected Range`, CPU, Memory, Restart panel의 빨간 경고 아이콘 없음
- CPU와 Memory 값이 수동 새로고침을 반복해도 안정적으로 표시
- 세 timestamp panel이 실제 2026년 KST로 표시
- Pending, Scheduling false, Waiting reason의 일반 `No data`는 현재 이상 상태 부재와 일치
- RSS, Daily, 3-day, Weekly 네 Pipeline 표시
- prewarm Job/Pod 미포함
- Node panel에 `arm-master-node`, `arm-worker-node`, `pi-worker-node` 표시
- datasource error와 panel query error 없음

최소 반복 검증:

1. Dashboard 최초 로드 완료 대기
2. 수동 Refresh 2회
3. 각 Refresh 요청이 120초 안에 종료
4. 빨간 query warning이 재발하지 않는지 확인
5. 가능하면 자동 refresh `15m` 1회 확인

### 완료 상태 처리

- 위 Production Grafana 사람 검증 전에는 UNIT-06과 전체 Verification을 완료 처리하지 않는다.
- 사람이 Grafana password 회전, Helm 적용, rollout, Production UI 검증 결과를 제공한 뒤 UNIT-06을 `[x]`, Verification Status를 `passed`로 변경한다.
- Production 장애 주입은 수행하지 않는다.
