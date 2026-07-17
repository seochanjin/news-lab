# Verification: Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## Verification Status

passed

## Verification Scope

- UNIT-01의 Repository Monitoring 구성, chart 기반 Grafana provisioning과 Production read-only baseline 조사를 완료했다.
- UNIT-02의 CronJob/Job metric series, label 관계와 정기 Pipeline PromQL 검증을 완료했다.
- UNIT-03의 Pod/Container/Node metric inventory, 정기 Pod join과 resource/status PromQL 검증을 완료했다.
- UNIT-04의 Dashboard JSON과 최소 Kustomize ConfigMap provisioning artifact 구성을 완료했다.
- UNIT-05의 JSON/YAML/Kustomize/Helm render, Dashboard 구조·scope, 문서 정합성,
  전체 pytest 회귀와 Production Prometheus API의 활성 target 20개 재검증을
  완료했다.
- Repository render와 Production object가 Prometheus replica, retention, storage 상태에서 일치하는지 확인했다.
- Prometheus active target의 UP/DOWN과 `lastError` 상태를 확인했다.
- UNIT-06의 76차 Alerting 후보와 Kubernetes metric으로 확인할 수 없는
  업무 metric 공백을 문서화했다.
- 운영자가 Approved Fix 4~8가 포함된 Dashboard ConfigMap과 chart `86.2.0` Helm
  Revision 3를 Production에 적용하고 Grafana rollout과 최신 UI를 확인했다.
- Approved Fix 1~8의 repository 변경과 local regression을 통과했고, query를
  변경한 Fix 4~6의 target 20개 Production Prometheus API 재검증도
  `20 passed / 0 failed`였다.
- 네 무거운 query의 수정 후 동시 성능은 운영자가 3회 재측정했고, 최대
  `79.418s`로 세 번 모두 `120s` 필수 gate와 `90s` 권장 gate를 통과했다.
- Grafana CPU limit은 Production Helm Revision 1·2의 `200m` baseline에 맞춰
  Repository를 정합화했다. query 성능 개선이 아니라 비의도적 drift 방지다.
- raw Helm manifest diff에서 Grafana admin password Base64가 출력된 이력을
  반영해 Secret 값을 기록하지 않는 검토와 회전 절차를 문서화했다. 운영자는
  기존 password를 회전하고 임시 patch 파일과 shell password 변수를 제거했다.
- Agent는 Production 변경 명령이나 Secret 조회를 실행하지 않았고, 사람이
  제공한 적용·검증 evidence만 기록했다.
- UNIT-01~06을 모두 완료해 전체 Task Verification Status를 `passed`로 변경한다.

## Commands Run

### UNIT-06 운영자 Production 적용과 Grafana UI 최종 검증

Command (운영자 제공):

```bash
kubectl apply -k k8s/monitoring/dashboards
```

Agent는 이 명령, Helm 변경, rollout, Secret 조회·변경을 실행하지 않았다. Helm과
rollout은 운영자가 제공한 sanitized 결과를 근거로 기록하며, 제공되지 않은 정확한
Helm 명령은 추정해 적지 않는다.

Result:

```text
Dashboard apply: configmap/news-lab-pipeline-operations-dashboard configured
Helm chart: 86.2.0
Helm revision: 3
Helm status: deployed
Helm description: Upgrade complete
Grafana rollout: deployment/monitoring-grafana successfully rolled out
Grafana data proxy timeout: 120
Grafana resources: requests cpu=50m memory=256Mi, limits cpu=200m memory=512Mi
Grafana health: database=ok, version=13.0.1+security-01
Prometheus targets: 20
Prometheus passed: 20
Prometheus failed: 0
```

운영자는 노출 가능성이 있던 기존 Grafana admin password를 회전하고 임시 patch
파일과 shell password 변수를 제거했다. 실제 password, Base64와 Secret 값은
조회하거나 이 문서에 기록하지 않았다.

수정 후 네 무거운 query 동시 실행 결과:

| 회차 | Peak Memory | Failures | Restart | Peak CPU | Total wall | 판정 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `17.646s` | `31.204s` | `58.069s` | `79.418s` | `79.420s` | passed |
| 2 | `14.580s` | `28.141s` | `36.984s` | `47.378s` | `47.382s` | passed |
| 3 | `8.654s` | `19.113s` | `28.191s` | `50.882s` | `50.885s` | passed |

세 회차 모두 query status가 success였고 오류가 없었다. 모든 query가 필수
`120s` 미만이었고 가장 느린 결과도 권장 gate `90s` 이하였다.

Production Grafana UI 확인 결과:

- `NewsLab Pipeline Operations`가 4개 row와 기존 query panel 구조로 정상 로드됐고
  빨간 query warning 아이콘이 없었다.
- Pipeline Overview는 CronJob 4개, 실제 2026년 KST schedule·regular success
  timestamp, suspend 상태와 active value `0`을 정상 표시했다.
- Job Status는 네 Pipeline failure `0`과 실제 2026년 KST completion timestamp를
  표시했다. 현재 active regular Job은 빨간 경고 없는 일반 `No data`였다.
- Pipeline Pod Resources는 CPU 약 `0.0294`/`0.00445`/`0.0919` cores와 Memory
  `76.8`/`40.6`/`112` MiB를 Daily/RSS/3-day에 표시했다. 보존된 정기 Pod의
  restart는 모두 `0`이었다.
- Pending, scheduling false와 waiting reason은 빨간 경고 없는 일반 `No data`였다.
  이는 현재 이상 상태가 없는 empty result이며 query 실패로 해석하지 않는다.
- Weekly resource `No data`는 실행 후 24시간 초과와 retention `1d` 제약에 따른
  예상 결과이며 항상 Weekly 데이터가 존재한다고 주장하지 않는다.
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`가 모두 Ready였고 CPU,
  Memory, Running Pods와 root filesystem 값 및 Kubernetes Node 이름 mapping이
  정상 표시됐다.
- Production ConfigMap에는 repository Dashboard의 자동 refresh `15m`가 적용됐다.
- rollout 후 기존 `/api/ds/query status=400 duration=30s`, `context canceled`,
  `deadline exceeded` 형태의 핵심 장애가 재현되지 않았다.

Grafana Elasticsearch bundled plugin 설치의 `permission denied` 오류는 Dashboard
기능에 영향을 주지 않았으며 이 검증의 blocker가 아닌 후속 점검 항목이다. 이
브랜치에서는 plugin 설정을 변경하지 않았다.

Status: passed (human-provided Production evidence)

### UNIT-06 최종 문서 closeout local validation

Command:

```bash
PYTHONPATH=. pytest -q

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json \
  k8s/monitoring/kube-prometheus-stack-values.yaml

git diff --name-only

git status --short

shasum \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json \
  k8s/monitoring/kube-prometheus-stack-values.yaml

grep -RniE \
  'UNIT-06.*\[ \]|Verification Status.*pending|동시.*미완료|Grafana UI.*미완료' \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md
```

Result:

```text
445 passed, 91 subtests passed in 13.62s
git diff --check: no output
forbidden-scope diff: k8s/monitoring/kube-prometheus-stack-values.yaml
dashboard JSON SHA-1: dbcb2912bdbcbb5950d085e48d209b44fcd0af76
monitoring values SHA-1: 840f4a6eaa6956b78aebd7552361da8d2bff3028
current UNIT-06 checklist: checked
current Verification Status: passed
```

`kube-prometheus-stack-values.yaml`의 diff와 그 밖의 기존 dirty worktree 항목은 이
문서 closeout 시작 전에 이미 존재했다. 시작 전후 SHA-1이 같으므로 이번 작업에서
Dashboard JSON이나 Monitoring values를 수정하지 않았다. `git diff --name-only`는
기존 tracked diff를, `git status --short`는 기존 untracked artifact도 함께
표시했다. grep에 잡힌 `pending`은 아래에 보존한 UNIT-02~06 당시의 과거 실행 결과와
검색 command 문자열뿐이며 현재 상태가 아니다.

Status: passed with pre-existing forbidden-scope diff noted

### Approved Fix 7: Grafana CPU limit Production baseline 정합화

Command:

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-approved-fix-7.yaml

ruby -ryaml -e '
docs = YAML.load_stream(
  File.read("/tmp/news-lab-monitoring-approved-fix-7.yaml")
).compact
grafana = docs.find do |doc|
  doc["kind"] == "Deployment" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
abort "missing Grafana Deployment" unless grafana
container = grafana.dig("spec", "template", "spec", "containers").find do |item|
  item["name"] == "grafana"
end
abort "missing Grafana container" unless container
resources = container.fetch("resources")
expected = {
  "requests" => { "cpu" => "50m", "memory" => "256Mi" },
  "limits" => { "cpu" => "200m", "memory" => "512Mi" }
}
abort "unexpected Grafana resources: #{resources}" unless resources == expected
config = docs.find do |doc|
  doc["kind"] == "ConfigMap" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
abort "missing data proxy timeout" unless
  config.dig("data", "grafana.ini").include?("[dataproxy]\ntimeout = 120")
prometheus = docs.find do |doc|
  doc["kind"] == "Prometheus" &&
    doc.dig("metadata", "name") == "monitoring-kube-prometheus-prometheus"
end
valid = prometheus.dig("spec", "replicas") == 1 &&
  prometheus.dig("spec", "retention") == "1d" &&
  !prometheus.fetch("spec").key?("storage")
abort "unexpected Prometheus baseline" unless valid
abort "Alertmanager rendered" if docs.any? { |doc| doc["kind"] == "Alertmanager" }
puts "Approved Fix 7 Helm assertions: OK"
puts "Grafana requests: cpu=50m memory=256Mi"
puts "Grafana limits: cpu=200m memory=512Mi"
puts "Grafana data proxy timeout: 120"
puts "Prometheus baseline: replicas=1 retention=1d storage=unset"
'
```

Result:

```text
Approved Fix 7 Helm assertions: OK
Grafana requests: cpu=50m memory=256Mi
Grafana limits: cpu=200m memory=512Mi
Grafana data proxy timeout: 120
Prometheus baseline: replicas=1 retention=1d storage=unset
```

Status: passed

Notes:

- Repository의 Grafana CPU limit만 `300m`에서 Production Helm Revision 1·2
  baseline인 `200m`으로 정합화했다.
- CPU request와 memory request/limit, 다른 Monitoring workload resource는
  변경하지 않았다.
- 이 변경은 query 성능 개선이 아니라 전체 values upgrade에서 비의도적
  `200m → 300m` drift를 방지하기 위한 것이다.
- `/tmp/news-lab-monitoring-approved-fix-7.yaml`은 local render이며 repository
  artifact가 아니다.

### Approved Fix 7 local regression과 변경 범위

Command:

```bash
ruby -ryaml -e '
YAML.load_stream(
  File.read("k8s/monitoring/kube-prometheus-stack-values.yaml")
)
puts "Monitoring values YAML parse: OK"
'

PYTHONPATH=. pytest -q
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt

if rg -n '[[:blank:]]+$' \
  docs/design/pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md; then
  exit 1
else
  echo 'Approved Fix 7 documentation whitespace: none'
fi
```

Result:

```text
Monitoring values YAML parse: OK
445 passed, 91 subtests passed in 15.86s
git diff --check: no output
application/Pipeline/DB/migration/dependency diff: no output
Approved Fix 7 documentation whitespace: none
```

Status: passed

### Approved Fix 8: Helm Secret 노출 대응 문서 검증

Command:

```bash
rg -n -- \
  '--dry-run=server|--hide-secret|raw `helm get manifest`|admin password|Base64|민감한 임시' \
  docs/design/pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md

if rg -n 'helm diff upgrade' docs/runbooks/monitoring.md; then
  exit 1
else
  echo 'Runbook unsafe raw helm diff command: none'
fi

git diff --check
git diff --name-only -- app scripts db migrations requirements.txt

if rg -n '[[:blank:]]+$' \
  docs/design/pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md; then
  exit 1
else
  echo 'Approved Fix 8 documentation whitespace: none'
fi
```

Result:

```text
Secret-safe Helm review and human rotation policy references: present
Runbook unsafe raw helm diff command: none
git diff --check: no output
application/Pipeline/DB/migration/dependency diff: no output
Approved Fix 8 documentation whitespace: none
```

Status: passed

Notes:

- Secret 값, Base64 값과 디코딩 값은 읽거나 출력하거나 문서에 추가하지 않았다.
- Production Secret 변경, password 회전, 임시 파일 삭제, Helm upgrade와 Grafana
  rollout은 실행하지 않았다.
- 사람은 `--dry-run=server --hide-secret` 결과에서 허용된 timeout/resource
  변경만 확인하고, admin Secret 또는 checksum의 비의도적 변경이 있으면 적용을
  중단해야 한다.

### Approved Fix 1~8 최종 repository gate

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'
POD_REGEX='pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*"'

python -m json.tool "$DASHBOARD" >/dev/null
jq -e --arg pod_regex "$POD_REGEX" '
  [.. | objects | select(.targets? | type == "array")
    | .targets[] | select(.expr? != null)] as $targets
  | ($targets | length) == 20
  and all($targets[]; .instant == true and .range == false)
  and .refresh == "15m"
  and .uid == "newslab-pipeline-operations"
  and .timezone == "Asia/Seoul"
  and .time.from == "now-24h"
  and .time.to == "now"
  and ([.panels[] | select(.type == "row")] | length) == 4
  and all(.panels[] | select(
    .title == "CronJob Last Schedule"
    or .title == "Last Successful Regular Job"
    or .title == "Regular Job Completion Time"
  ); .fieldConfig.defaults.unit == "dateTimeAsIso"
    and (.targets[0].expr | startswith("1000 * ")))
  and all(.panels[] | select(
    .title == "Peak CPU (24h, 5m rate)"
    or .title == "Peak Memory Working Set (24h)"
    or .title == "Container Restart Increase"
  ); .targets[0].expr | contains($pod_regex))
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fixes-1-8.yaml

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-approved-fixes-1-8.yaml

ruby -ryaml -e '
docs = YAML.load_stream(
  File.read("/tmp/news-lab-monitoring-approved-fixes-1-8.yaml")
).compact
grafana = docs.find do |doc|
  doc["kind"] == "Deployment" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
container = grafana.dig("spec", "template", "spec", "containers").find do |item|
  item["name"] == "grafana"
end
expected = {
  "requests" => { "cpu" => "50m", "memory" => "256Mi" },
  "limits" => { "cpu" => "200m", "memory" => "512Mi" }
}
abort "unexpected Grafana resources" unless
  container.fetch("resources") == expected
config = docs.find do |doc|
  doc["kind"] == "ConfigMap" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
abort "missing timeout" unless
  config.dig("data", "grafana.ini").include?("[dataproxy]\ntimeout = 120")
prometheus = docs.find do |doc|
  doc["kind"] == "Prometheus" &&
    doc.dig("metadata", "name") == "monitoring-kube-prometheus-prometheus"
end
valid = prometheus.dig("spec", "replicas") == 1 &&
  prometheus.dig("spec", "retention") == "1d" &&
  !prometheus.fetch("spec").key?("storage")
abort "unexpected Prometheus baseline" unless valid
sidecar = grafana.dig("spec", "template", "spec", "containers").find do |item|
  item["name"] == "grafana-sc-dashboard"
end
env = sidecar.fetch("env").to_h { |item| [item["name"], item["value"]] }
abort "wrong sidecar label" unless
  env["LABEL"] == "grafana_dashboard" && env["LABEL_VALUE"] == "1"
abort "Alertmanager rendered" if docs.any? { |doc| doc["kind"] == "Alertmanager" }
puts "Approved Fix 1-8 Helm assertions: OK"
'

PYTHONPATH=. pytest -q
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt

if rg -n '[[:blank:]]+$' \
  docs/design/pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md; then
  exit 1
else
  echo 'Approved Fix 1-8 documentation whitespace: none'
fi
```

Result:

```text
Dashboard contract assertions: true
Kustomize render: passed
Approved Fix 1-8 Helm assertions: OK
445 passed, 91 subtests passed in 12.98s
git diff --check: no output
application/Pipeline/DB/migration/dependency diff: no output
Approved Fix 1-8 documentation whitespace: none
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-approved-fixes-1-8.yaml`과
  `/tmp/news-lab-monitoring-approved-fixes-1-8.yaml`은 일시적인 local evidence며
  repository artifact가 아니다.
- Production dry-run, Secret 변경, password 회전, Helm upgrade와 rollout은
  실행하지 않았다.

### Approved Fix 6 동시 query 운영자 최종 재측정

Command: 위 `Approved Fix 수정 후 동시 query 성능 재측정 시도`에 기록된 동일한
네 query 동시 실행 절차를 운영자가 세 차례 실행했다. 이 turn에서 Production
query를 다시 실행하지 않았다.

Result:

| Round | 가장 느린 query | total wall time | 판정 |
| ---: | ---: | ---: | --- |
| 1 | `79.418s` | `79.420s` | PASSED |
| 2 | `47.378s` | `47.382s` | PASSED |
| 3 | `50.882s` | `50.885s` | PASSED |

Status: passed (human-provided)

Notes:

- 세 번 모두 네 query가 `status=success`와 기존 cardinality를 유지했다.
- 모든 query가 `120s` 미만이었고 가장 느린 결과도 권장 `90s` gate 이하였다.
- 앞의 localhost 연결 실패는 과거 port-forward 종료 이력으로만 보존하며 최신
  성능 상태를 나타내지 않는다.

### Approved Fix 6: CPU·Memory·Restart 정기 Pod 조기 필터

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'
POD_REGEX='pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*"'

python -m json.tool "$DASHBOARD" >/dev/null

jq -e --arg pod_regex "$POD_REGEX" '
  [.. | objects | select(.targets? | type == "array")
    | .targets[] | select(.expr? != null)] as $targets
  | ([.panels[] | select(
      .title == "Peak CPU (24h, 5m rate)"
      or .title == "Peak Memory Working Set (24h)"
      or .title == "Container Restart Increase"
    ) | .targets[0].expr] | length) == 3
  and all(.panels[] | select(
      .title == "Peak CPU (24h, 5m rate)"
      or .title == "Peak Memory Working Set (24h)"
      or .title == "Container Restart Increase"
    ); .targets[0].expr | contains($pod_regex))
  and ($targets | length) == 20
  and all($targets[]; .instant == true and .range == false)
  and ([.panels[] | select(.type == "row")] | length) == 4
  and .uid == "newslab-pipeline-operations"
  and .refresh == "15m"
  and ([.panels[] | select(.title == "Peak CPU (24h, 5m rate)")
    | .targets[0].expr] | all(contains("[5m]") and contains("[24h:5m]")))
  and ([.panels[] | select(.title == "Peak Memory Working Set (24h)")
    | .targets[0].expr] | all(contains("[24h]")))
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fix-6-rendered.yaml

ruby -rjson -ryaml -e '
doc = YAML.load_stream(
  File.read("/tmp/news-lab-dashboard-approved-fix-6-rendered.yaml")
).compact.fetch(0)
json = JSON.parse(
  doc.fetch("data").fetch("news-lab-pipeline-operations.json")
)
regex = %q{pod=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+-.*"}
titles = [
  "Peak CPU (24h, 5m rate)",
  "Peak Memory Working Set (24h)",
  "Container Restart Increase"
]
panels = json.fetch("panels").select { |panel| titles.include?(panel["title"]) }
valid = panels.length == 3 && panels.all? do |panel|
  panel.dig("targets", 0, "expr").include?(regex)
end
abort "early filter assertions failed" unless valid
puts "Rendered early Pod filter assertions: OK"
'
```

Result:

```text
Dashboard JSON parse: passed
CPU, Memory, Restart canonical Pod regex assertions: true
20 instant-only targets, 4 rows, UID and refresh assertions: true
CPU 5m rate/24h subquery and Memory 24h window assertions: true
Kustomize render: passed
Rendered early Pod filter assertions: OK
```

Status: passed

Notes:

- 원본 CPU, Memory, Restart metric selector에만 숫자 suffix 정기 Pod regex를
  추가했다. owner join, cardinality, legend와 prewarm 제외 계약은 유지했다.
- CPU의 최근 24시간 최대 5분 평균, Memory의 24시간 최대 working set,
  Restart의 선택 범위 의미는 변경하지 않았다.
- `/tmp/news-lab-dashboard-approved-fix-6-rendered.yaml`은 local evidence이며
  repository artifact가 아니다.

### Approved Fix 5: Dashboard 자동 refresh 15분

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null
jq -e '
  .refresh == "15m"
  and .time.from == "now-24h"
  and .time.to == "now"
  and .timezone == "Asia/Seoul"
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fix-5-rendered.yaml

ruby -rjson -ryaml -e '
doc = YAML.load_stream(
  File.read("/tmp/news-lab-dashboard-approved-fix-5-rendered.yaml")
).compact.fetch(0)
json = JSON.parse(
  doc.fetch("data").fetch("news-lab-pipeline-operations.json")
)
abort "wrong refresh" unless json["refresh"] == "15m"
puts "Rendered refresh assertion: OK"
'
```

Result:

```text
Dashboard JSON parse: passed
refresh=15m, now-24h, timezone=Asia/Seoul assertions: true
Kustomize render: passed
Rendered refresh assertion: OK
```

Status: passed

Notes:

- 자동 refresh만 `5m`에서 `15m`으로 변경했다. 기본 `now-24h`, timezone,
  수동 refresh와 timepicker 선택지는 유지했다.
- `/tmp/news-lab-dashboard-approved-fix-5-rendered.yaml`은 local evidence이며
  repository artifact가 아니다.

### Approved Fix 4: Grafana data proxy timeout 120초

Command:

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-approved-fixes.yaml

rg -n -C 4 \
  'dataproxy|timeout = 120|grafana.ini' \
  /tmp/news-lab-monitoring-approved-fixes.yaml
```

Result:

```text
Helm chart 86.2.0 render: passed
rendered monitoring-grafana ConfigMap grafana.ini:
  [dataproxy]
  timeout = 120
```

Status: passed

Notes:

- 기존 Grafana nodeSelector와 resources에 `grafana.ini.dataproxy.timeout=120`만
  병합했다.
- Prometheus retention `1d`, storage, query timeout과 resource 설정은 변경하지
  않았다.
- `/tmp/news-lab-monitoring-approved-fixes.yaml`은 local evidence이며 repository
  artifact가 아니다.
- Helm upgrade와 Grafana rollout은 실행하지 않았다.

### Approved Fix 4~6 통합 local regression

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null

jq -e '
  [.. | objects | select(.targets? | type == "array")
    | .targets[] | select(.expr? != null)] as $targets
  | ($targets | length) == 20
  and all($targets[]; .instant == true and .range == false)
  and .refresh == "15m"
  and .uid == "newslab-pipeline-operations"
  and .timezone == "Asia/Seoul"
  and .time.from == "now-24h"
  and ([.panels[] | select(.type == "row")] | length) == 4
  and all(.panels[] | select(
    .title == "CronJob Last Schedule"
    or .title == "Last Successful Regular Job"
    or .title == "Regular Job Completion Time"
  ); .fieldConfig.defaults.unit == "dateTimeAsIso"
    and (.targets[0].expr | startswith("1000 * ")))
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-rendered.yaml

ruby -ryaml -e '
docs = YAML.load_stream(
  File.read("/tmp/news-lab-monitoring-rendered.yaml")
).compact
config = docs.find do |doc|
  doc["kind"] == "ConfigMap" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
abort "missing grafana timeout" unless
  config.dig("data", "grafana.ini").include?("[dataproxy]\ntimeout = 120")
prometheus = docs.find do |doc|
  doc["kind"] == "Prometheus" &&
    doc.dig("metadata", "name") == "monitoring-kube-prometheus-prometheus"
end
valid = prometheus.dig("spec", "replicas") == 1 &&
  prometheus.dig("spec", "retention") == "1d" &&
  !prometheus.fetch("spec").key?("storage")
abort "wrong prometheus baseline" unless valid
abort "alertmanager rendered" if docs.any? { |doc| doc["kind"] == "Alertmanager" }
grafana = docs.find do |doc|
  doc["kind"] == "Deployment" &&
    doc.dig("metadata", "name") == "monitoring-grafana"
end
sidecar = grafana.dig("spec", "template", "spec", "containers").find do |container|
  container["name"] == "grafana-sc-dashboard"
end
env = sidecar.fetch("env").to_h { |item| [item["name"], item["value"]] }
abort "wrong sidecar label" unless
  env["LABEL"] == "grafana_dashboard" && env["LABEL_VALUE"] == "1"
puts "Helm baseline assertions: OK"
'

PYTHONPATH=. pytest -q

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt
```

Result:

```text
Dashboard JSON and contract assertions: true
Kustomize render: passed
Helm baseline assertions: OK
445 passed, 91 subtests passed in 14.51s
git diff --check: no output
application/Pipeline/DB/migration/dependency diff: no output
```

Status: passed

Notes:

- Helm render assertion은 Grafana `[dataproxy] timeout = 120`, Prometheus replica
  `1`, retention `1d`, storage 미설정, sidecar label과 Alertmanager 미생성을 함께
  확인했다.
- Dashboard UID/datasource, 4개 row/20개 target, Instant 전용 설정, 세 timestamp
  milliseconds 변환을 유지했다.

### Approved Fix 4~6 Production Prometheus API 재검증

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'
QUERY_FILE='/tmp/news-lab-approved-fixes-queries.tsv'
RESULT_FILE='/tmp/news-lab-approved-fixes-query-api.tsv'
RESPONSE_FILE='/tmp/news-lab-approved-fixes-query-response.json'

jq -r '
  .panels[] | select(.targets? != null) as $panel
  | .targets[] | select(.expr? != null)
  | [$panel.title, (.expr | gsub("\\$__range"; "24h"))]
  | @tsv
' "$DASHBOARD" > "$QUERY_FILE"

printf 'index\tpanel\thttp_status\tprometheus_status\tresult_count\telapsed_seconds\n' \
  > "$RESULT_FILE"

index=0
while IFS=$'\t' read -r title query; do
  index=$((index + 1))
  curl_result=$(curl -sSG --max-time 120 \
    -o "$RESPONSE_FILE" \
    -w '%{http_code}\t%{time_total}' \
    --data-urlencode "query=${query}" \
    http://127.0.0.1:9090/api/v1/query)
  http_status=${curl_result%%$'\t'*}
  elapsed=${curl_result##*$'\t'}
  prometheus_status=$(jq -r '.status // "missing"' "$RESPONSE_FILE")
  result_count=$(jq -r '
    if .status == "success" then (.data.result | length) else -1 end
  ' "$RESPONSE_FILE")
  printf '%02d\t%s\t%s\t%s\t%s\t%s\n' \
    "$index" "$title" "$http_status" "$prometheus_status" \
    "$result_count" "$elapsed" | tee -a "$RESULT_FILE"
done < "$QUERY_FILE"
```

Result:

| # | Panel | resultCount | elapsed |
| ---: | --- | ---: | ---: |
| 1 | CronJob Last Schedule | 4 | `0.083s` |
| 2 | Last Successful Regular Job | 4 | `0.166s` |
| 3 | CronJob Suspend | 4 | `0.101s` |
| 4 | Active Regular Jobs | 4 | `0.069s` |
| 5 | Retained Regular Job Succeeded | 9 | `0.062s` |
| 6 | Retained Regular Job Failed | 9 | `0.054s` |
| 7 | Failures in Selected Range | 4 | `10.753s` |
| 8 | Regular Job Completion Time | 9 | `0.055s` |
| 9 | Currently Active Regular Jobs | 0 | `0.055s` |
| 10 | Peak CPU (24h, 5m rate) | 3 | `23.041s` |
| 11 | Peak Memory Working Set (24h) | 3 | `12.461s` |
| 12 | Container Restart Increase | 9 | `41.923s` |
| 13 | Pending Pipeline Pods | 0 | `0.155s` |
| 14 | Scheduling Failed / False | 0 | `0.166s` |
| 15 | Container Waiting Reason | 0 | `0.197s` |
| 16 | Node Ready | 3 | `0.103s` |
| 17 | Node CPU Usage | 3 | `0.152s` |
| 18 | Node Memory Usage | 3 | `0.201s` |
| 19 | Running Pods by Node | 3 | `0.112s` |
| 20 | Root Filesystem Usage | 3 | `0.093s` |

```text
Targets: 20
Passed: 20
Failed: 0
```

Status: passed

Notes:

- Grafana macro `$__range`만 Dashboard 기본 범위에 맞춰 `24h`로 치환했고,
  `label_replace`의 `$1`은 정규식 capture group으로 유지했다.
- CronJob 4개, retained regular Job 9개, CPU/Memory 3개, Restart 9개와 Node
  3개 cardinality가 기존 계약과 일치했다. 숫자 suffix filter가 prewarm을
  제외했다.
- active/Pending/scheduling false/waiting reason의 `0`은 현재 일치하는 이상
  상태가 없다는 뜻이며 query 실패가 아니다.
- CPU/Memory의 Weekly `No data`는 실행 후 24시간 초과와 retention `1d`에 따른
  예상 결과다.
- 모든 응답은 HTTP `200`, Prometheus `status=success`였고 parse/execution 또는
  vector matching 오류가 없었다.
- `/tmp/news-lab-approved-fixes-query-api.tsv`와 응답 파일은 일시적인 local
  evidence이며 repository artifact가 아니다.
- 동일 스크립트의 최초 sandbox 실행은 localhost network 제한으로 `0/20`이었고,
  승인된 read-only 실행으로 위 `20/20` 결과를 확인했다.

### Approved Fix 수정 후 동시 query 성능 재측정 시도

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'
QUERY_FILE='/tmp/news-lab-approved-fixes-performance-queries.tsv'
RESULT_DIR='/tmp/news-lab-approved-fixes-performance'

mkdir -p "$RESULT_DIR"
jq -r '
  .panels[] | select(
    .title == "Failures in Selected Range"
    or .title == "Peak CPU (24h, 5m rate)"
    or .title == "Peak Memory Working Set (24h)"
    or .title == "Container Restart Increase"
  )
  | [.id, .title, (.targets[0].expr | gsub("\\$__range"; "24h"))]
  | @tsv
' "$DASHBOARD" > "$QUERY_FILE"

start_epoch=$(date +%s)
while IFS=$'\t' read -r panel_id title query; do
  (
    curl -sSG --max-time 120 \
      -o "$RESULT_DIR/${panel_id}.json" \
      -w '%{http_code}\t%{time_total}\n' \
      --data-urlencode "query=${query}" \
      http://127.0.0.1:9090/api/v1/query \
      > "$RESULT_DIR/${panel_id}.meta"
    http_status=$(cut -f1 "$RESULT_DIR/${panel_id}.meta")
    elapsed=$(cut -f2 "$RESULT_DIR/${panel_id}.meta")
    prometheus_status=$(jq -r \
      '.status // "missing"' "$RESULT_DIR/${panel_id}.json")
    result_count=$(jq -r '
      if .status == "success" then (.data.result | length) else -1 end
    ' "$RESULT_DIR/${panel_id}.json")
    printf '%s\t%s\t%s\t%s\t%s\n' \
      "$title" "$http_status" "$prometheus_status" "$result_count" "$elapsed" \
      > "$RESULT_DIR/${panel_id}.result"
  ) &
done < "$QUERY_FILE"
wait
end_epoch=$(date +%s)

printf 'panel\thttp_status\tprometheus_status\tresult_count\telapsed_seconds\n'
for result in "$RESULT_DIR"/*.result; do
  sed -n '1p' "$result"
done
printf 'Concurrent wall seconds: %d\n' "$((end_epoch - start_epoch))"
```

Result:

```text
Failures in Selected Range: curl exit 7, HTTP 000
Peak CPU (24h, 5m rate): curl exit 7, HTTP 000
Peak Memory Working Set (24h): curl exit 7, HTTP 000
Container Restart Increase: curl exit 7, HTTP 000
Concurrent wall seconds: 0
subsequent readiness: curl exit 7, localhost:9090 connection failed
```

Status: human-required

Notes:

- 20개 순차 API 검증 직후 port-forward가 종료돼 네 요청 모두 Prometheus query
  실행 전 연결 단계에서 실패했다. query 성능 실패나 `120s` 초과로 해석하지
  않는다.
- 수정 후 개별 실행시간은 앞의 20개 API 결과로 확인했으며 모두 `120s` 미만이다.
- 네 query 동시 실행과 권장 `90s` gate는 tunnel/port-forward를 준비한 사람이
  다시 측정해야 한다.

### Approved Fix Production 적용 전 diff 시도

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl --request-timeout=15s diff -k k8s/monitoring/dashboards

KUBECONFIG=~/.kube/oci-k3s.yaml \
helm diff upgrade monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml
```

Result:

```text
kubectl diff: exit 2, Kubernetes API 127.0.0.1:6443 connection refused
helm diff: exit 1, unknown command "diff" for "helm"
```

Status: human-required

Notes:

- K3s API tunnel이 없고 local Helm에 diff plugin이 없어 예상 Production diff를
  확인하지 못했다.
- `kubectl apply/delete/patch/edit/rollout`과 Helm upgrade는 실행하지 않았다.

### Approved Fix 최종 local gate

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fixes-final.yaml

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-approved-fixes-final.yaml

PYTHONPATH=. pytest -q
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt

if rg -n '[[:blank:]]+$' \
  docs/design/pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md; then
  exit 1
else
  echo 'documentation trailing whitespace: none'
fi
```

Result:

```text
Dashboard JSON parse: passed
Kustomize render: passed
Helm chart 86.2.0 render: passed
445 passed, 91 subtests passed in 16.66s
git diff --check: no output
application/Pipeline/DB/migration/dependency diff: no output
documentation trailing whitespace: none
UNIT-06 checklist: unchecked
Verification Status: pending
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-approved-fixes-final.yaml`과
  `/tmp/news-lab-monitoring-approved-fixes-final.yaml`은 repository artifact가
  아닌 일시적인 local render다.
- monitoring values의 허용된 변경은 Grafana data proxy timeout뿐이며,
  Prometheus retention/storage/query timeout과 resource는 유지했다.

### Approved Fix 1: Prometheus target Instant 전용 설정

Command:

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

jq -e '
  .uid == "newslab-pipeline-operations"
  and .timezone == "Asia/Seoul"
  and .time.from == "now-24h"
  and ([.panels[] | select(.type == "row")] | length) == 4
  and ([.panels[] | select(.targets? != null) | .targets[]
    | select(.expr? != null)] | length) == 20
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fix-1-rendered.yaml

git diff --check
```

Result:

```text
Dashboard JSON parse: passed
Prometheus target count: 20
instant=true and range=false targets: 20
Dashboard UID/timezone/time range/row/target assertions: true
Kustomize render: passed
git diff --check: no output
```

Status: passed

Notes:

- Approved Fix 1의 desired state는 조사 시점의 Dashboard JSON에 이미 존재해
  동일 값을 다시 덮어쓰지 않고 현재 상태를 검증했다.
- panel title/ID, 4개 row, Dashboard/datasource UID, PromQL 기간 집계,
  `now-24h`와 `Asia/Seoul`은 변경하지 않았다.
- `/tmp/news-lab-dashboard-approved-fix-1-rendered.yaml`은 local evidence이며
  repository artifact가 아니다.

### Approved Fix 2: DateTime timestamp milliseconds 변환

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null

jq -e '
  [
    .panels[]
    | select(
        .title == "CronJob Last Schedule"
        or .title == "Last Successful Regular Job"
        or .title == "Regular Job Completion Time"
      )
    | {
        title,
        unit: .fieldConfig.defaults.unit,
        expr: .targets[0].expr
      }
  ] as $timestamp_panels
  | ($timestamp_panels | length) == 3
  and all($timestamp_panels[];
    .unit == "dateTimeAsIso"
    and (.expr | startswith("1000 * "))
  )
' "$DASHBOARD"

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fix-2-rendered.yaml

ruby -rjson -ryaml -e '
doc = YAML.load_stream(
  File.read("/tmp/news-lab-dashboard-approved-fix-2-rendered.yaml")
).compact.fetch(0)
abort "wrong kind" unless doc["kind"] == "ConfigMap"
json = JSON.parse(
  doc.fetch("data").fetch("news-lab-pipeline-operations.json")
)
titles = [
  "CronJob Last Schedule",
  "Last Successful Regular Job",
  "Regular Job Completion Time"
]
panels = json.fetch("panels").select do |panel|
  titles.include?(panel["title"])
end
valid = panels.length == 3 && panels.all? do |panel|
  panel.dig("targets", 0, "expr").start_with?("1000 * ")
end
abort "timestamp assertions failed" unless valid
puts "Rendered timestamp assertions: OK"
'
```

Result:

```text
Dashboard JSON parse: passed
Timestamp panel count: 3
dateTimeAsIso and final 1000 * assertion: true
Kustomize render: passed
Rendered timestamp assertions: OK
```

Status: passed

Notes:

- kube-state-metrics timestamp seconds를 Grafana DateTime milliseconds로
  변환하는 Approved Fix 2만 적용했다.
- 세 panel의 title/ID/unit/legend와 owner join은 변경하지 않았다.
- `/tmp/news-lab-dashboard-approved-fix-2-rendered.yaml`은 local evidence이며
  repository artifact가 아니다.

### Approved Fix 3: empty result와 query error 구분

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

jq -e '
  [
    .panels[]
    | select(
        .title == "Currently Active Regular Jobs"
        or .title == "Pending Pipeline Pods"
        or .title == "Scheduling Failed / False"
        or .title == "Container Waiting Reason"
      )
    | {
        description,
        expr: .targets[0].expr
      }
  ] as $empty_panels
  | ($empty_panels | length) == 4
  and all($empty_panels[];
    (.expr | contains("or vector(0)") | not)
    and (.description | contains("빨간 경고 없는 No data"))
    and (.description | contains("빨간 경고 No data"))
    and (.description | contains("Inspect"))
  )
' "$DASHBOARD"
```

Result:

```text
Empty-result panel count: 4
or vector(0) query count: 0
No data warning/Inspect description assertions: true
```

Status: passed

Notes:

- 정상 empty vector를 관측 불능과 구분하기 위해 Approved Fix에서 거절한
  `or vector(0)`을 추가하지 않았다.
- 빨간 경고 없는 일반 `No data`는 조건 일치 series 부재 여부를 확인하고,
  빨간 경고 `No data`는 query/datasource 오류로 분류한다.

### Approved Fix 통합 local validation

Command:

```bash
DASHBOARD='k8s/monitoring/dashboards/news-lab-pipeline-operations.json'

python -m json.tool "$DASHBOARD" >/dev/null

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fixes-rendered.yaml

PYTHONPATH=. pytest -q

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/kube-prometheus-stack-values.yaml
```

Result:

```text
Approved Fix 1 target assertion: true
Approved Fix 2 timestamp assertion: true
Approved Fix 3 empty-result policy assertion: true
Kustomize render: passed
445 passed, 91 subtests passed in 15.09s
git diff --check: no output
application/Pipeline/DB/dependency/monitoring values diff: no output
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-approved-fixes-rendered.yaml`은 local evidence이며
  repository artifact가 아니다.
- Dashboard UID/datasource UID, 24시간 resource window, CPU 5분 rate,
  retention/storage와 금지 영역을 변경하지 않았다.

### Approved Fix Production Prometheus API 재검증 시도

Command:

```bash
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready

python -c \
  'import urllib.request; urllib.request.urlopen("http://127.0.0.1:9090/api/v1/query?query=up", timeout=5)'

PROMQL=$(jq -r \
  '.panels[] | select(.title == "CronJob Last Schedule") | .targets[0].expr' \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json)
curl -fsSG --max-time 15 \
  --data-urlencode "query=${PROMQL}" \
  http://127.0.0.1:9090/api/v1/query
```

Result:

```text
Prometheus Server is Ready.
Python validator: urllib.error.URLError, PermissionError [Errno 1]
curl validator first query: curl exit 7, localhost:9090 connection failed
Targets completed: 0/20
```

Status: human-required

Notes:

- readiness 확인 뒤 기존 Prometheus port-forward가 종료됐다. Python 오류는
  sandbox network 제한이고 curl 재시도는 종료된 port-forward 때문이었다.
- metric 부재, PromQL 오류 또는 Production Prometheus 장애를 의미하지 않는다.
- 이 절은 당시 port-forward 종료로 재검증하지 못한 이력을 보존한 것이다.
  이후 `Approved Fix 4~6 Production Prometheus API 재검증` 절에서 최신 target
  `20 passed / 0 failed`를 별도로 확인했으며, 이 과거 시도 결과를 최신 상태로
  사용하지 않는다.

### Approved Fix Production ConfigMap diff 시도

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl --request-timeout=15s diff -k k8s/monitoring/dashboards
```

Result:

```text
Unable to connect to the server:
dial tcp 127.0.0.1:6443: connect: operation not permitted
```

Status: human-required

Notes:

- 현재 세션의 K3s API tunnel에 접근할 수 없어 Production ConfigMap diff를
  확인하지 못했다.
- `kubectl apply/delete/patch/edit/rollout`과 Helm upgrade는 실행하지 않았다.
- 사람이 tunnel을 준비한 뒤 예상 변경이
  `monitoring/news-lab-pipeline-operations-dashboard` ConfigMap의 Dashboard
  JSON에만 한정되는지 확인해야 한다.

### Approved Fix 최종 문서와 변경 범위 검증

Command:

```bash
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-approved-fixes-final.yaml

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/kube-prometheus-stack-values.yaml

rg -n -C 2 \
  'Applied Fix 1|Applied Fix 2|Applied Fix 3|Production Prometheus에서 수정된 target|UNIT-06|Verification Status|human-required' \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md
```

Result:

```text
Dashboard JSON parse: passed
Kustomize render: passed
git diff --check: no output
application/Pipeline/DB/dependency/monitoring values diff: no output
Approved Fix checklist/current status references: present
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-approved-fixes-final.yaml`은 local evidence이며
  repository artifact가 아니다.
- Production 재검증과 적용/UI 확인을 완료로 표시하지 않았고 UNIT-06 및 전체
  Verification Status는 `pending`을 유지한다.

### Repository와 CronJob inventory

Command:

```bash
find k8s docs tests scripts \
  \( -iname '*prometheus*' -o -iname '*grafana*' \
  -o -iname '*monitoring*' -o -iname '*dashboard*' \) -print

rg -n \
  "kube-prometheus-stack|retention|storageSpec|grafana|dashboardProviders|sidecar|ServiceMonitor|PodMonitor|PrometheusRule|Alertmanager" \
  k8s docs

rg -n \
  "kind: CronJob|name: news-rss-collector|name: news-daily-topic-pipeline|name: news-three-day-topic-pipeline|name: news-weekly-topic-pipeline" \
  k8s
```

Result: Monitoring 설정은 `k8s/monitoring/kube-prometheus-stack-values.yaml` 하나였고 custom Dashboard artifact/ConfigMap은 없었다. 네 CronJob manifest와 이름을 확인했다.

Status: passed

### Chart version과 Grafana provisioning render

Command:

```bash
helm version --short
helm repo list
helm show values prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | \
  rg -n -C 3 \
  'dashboardProviders:|sidecar:|dashboards:|defaultDashboardsEnabled:|defaultDashboardsTimezone:'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/news-lab-monitoring-unit01-rendered.yaml
```

Result:

```
Helm client: v4.2.0+g0646808
prometheus-community repository: configured
defaultDashboardsEnabled: true
defaultDashboardsTimezone: utc
grafana.sidecar.dashboards.enabled: true
sidecar label/value: grafana_dashboard / 1
sidecar namespace: ALL
provider ConfigMap: present
chart default Dashboard ConfigMaps with sidecar label: 27
Prometheus replicas: 1
Prometheus retention: 1d
Prometheus storage: nil
```

Status: passed

Notes: Chart `86.2.0`은 기존 설치/검증 문서에 고정된 version이다. `/tmp` render 파일은 repository artifact가 아니다.

### Monitoring YAML과 CronJob namespace parse

Command:

```bash
ruby -ryaml -e \
  'Dir["k8s/monitoring/**/*.yaml"].sort.each{|p| YAML.load_stream(File.read(p)); puts "ok #{p}"}'

for f in \
  k8s/news-rss-collector-cronjob.yaml \
  k8s/news-daily-topic-pipeline-cronjob.yaml \
  k8s/news-three-day-topic-pipeline-cronjob.yaml \
  k8s/news-weekly-topic-pipeline-cronjob.yaml
do
  ruby -ryaml -e \
    'd=YAML.load_file(ARGV[0]); puts "#{d.dig("metadata","namespace") || "default"} #{d.dig("metadata","name")}"' \
    "$f"
done
```

Result: Monitoring values YAML parse에 성공했고 네 CronJob 모두 namespace가 생략되어 `default`를 사용함을 확인했다.

Status: passed

### Production read-only baseline 최초 시도

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml helm list -n monitoring --output json
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get pods,svc -n monitoring
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get prometheus -A
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get pvc -A
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get nodes -L observability,workload
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get servicemonitor,podmonitor -A
KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl --request-timeout=15s get cronjob,job,pod -n default
```

Result: 모든 조회가 다음 연결 오류로 실패했다.

```
kubernetes cluster unreachable
dial tcp 127.0.0.1:6443: connect: operation not permitted
```

Status: failed

Notes:

- kubeconfig가 사용하는 local API endpoint에 연결할 운영자 SSH tunnel이 당시 실행 환경에 없었다.
- Production object가 없거나 unhealthy하다는 결과가 아니다.
- 아래 운영자 재검증에서 tunnel 준비 후 동일 read-only 조회에 성공했다.

### Production read-only baseline 재검증

운영자가 K3s API SSH tunnel을 준비한 뒤 별도 터미널에서 read-only 조회를 실행했다.

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
KUBECONFIG=~/.kube/oci-k3s.yaml helm list -n monitoring --output json
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods,svc -n monitoring -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get prometheus -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pvc -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes -L observability,workload
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get servicemonitor,podmonitor -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob,job,pod -n default -o wide
```

Result:

- `arm-master-node`, `arm-worker-node`, `pi-worker-node`가 모두 `Ready`였다.
- Helm release `monitoring`은 revision `2`, status `deployed`였다.
- 실제 chart는 `kube-prometheus-stack-86.2.0`, app version은 `v0.91.0`이었다.
- Grafana는 `3/3 Running`, Prometheus Operator와 kube-state-metrics는 `1/1 Running`, Prometheus는 `2/2 Running`이었다.
- Monitoring core Pod의 restart count는 모두 `0`이었다.
- node-exporter는 세 Node에 각각 1개씩 Running 상태였다.
- Prometheus custom resource는 desired/ready `1/1`, `Reconciled=True`, `Available=True`였다.
- Cluster 전체에 PVC가 없었다.
- `arm-worker-node`에는 `observability=true`, `workload=app` label이 적용돼 있었다.
- ServiceMonitor 12개가 존재했고 조회 결과에 PodMonitor는 없었다.
- 네 NewsLab CronJob은 모두 `default` namespace에서 `suspend=False`, `active=0`이었다.
- RSS, Daily, 3-day, Weekly의 최근 정기 Job은 모두 `Complete` 상태였다.
- 현재 네 CronJob은 동일한 immutable full Git SHA image를 사용했다.
- Backend API 2개 Pod, Frontend 2개 Pod와 Redis 1개 Pod가 Running이며 restart count는 `0`이었다.

Status: passed

Notes:

- 최초 실패는 SSH tunnel 부재로 인한 local K3s API 연결 실패였다.
- 재검증 결과 Cluster, Monitoring workload와 최근 Pipeline 실행의 live 상태는 정상이다.
- 결과에서 kubeconfig 내용, private address와 전체 endpoint metadata는 기록하지 않았다.
- 과거 생성된 Weekly Job 일부가 이전 SHA 또는 `latest` image를 보존하는 것은 생성 당시 Pod template 기록이며 현재 CronJob desired state의 불일치가 아니다.
- 정기 CronJob Job 외에 사람이 생성한 `*-prewarm-*` Job도 존재한다. UNIT-02에서
  owner 관계만으로는 prewarm이 제외되지 않으며 숫자 suffix filter가 필요함을
  확인했다.

### Production Prometheus runtime spec

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheus \
  monitoring-kube-prometheus-prometheus \
  -n monitoring \
  -o jsonpath='replicas={.spec.replicas}{"\n"}retention={.spec.retention}{"\n"}storage={.spec.storage}{"\n"}'
```

Result:

```
replicas=1
retention=1d
storage=
```

Status: passed

Notes:

- Production Prometheus는 단일 replica다.
- retention은 `1d`다.
- `spec.storage`가 비어 있고 PVC도 없어 persistent storage가 구성되지 않았다.
- Prometheus Pod 재생성 시 기존 시계열 보존을 보장하지 않는다.
- storage와 retention 변경은 이번 Task 범위가 아니다.

### Production Prometheus active target 상태

운영자가 Prometheus Service를 localhost `9090`으로 port-forward한 뒤 API를 조회했다.

Command:

```bash
curl -fsS \
  'http://127.0.0.1:9090/api/v1/targets?state=active' |
jq -r '
  .data.activeTargets[]
  | [
      (.labels.job // "unknown"),
      .health,
      (if .lastError == "" then "-" else .lastError end)
    ]
  | @tsv
' |
sort -u
```

Result:

```
apiserver                              up  -
coredns                                up  -
kube-state-metrics                     up  -
kubelet                                up  -
monitoring-grafana                     up  -
monitoring-kube-prometheus-operator    up  -
monitoring-kube-prometheus-prometheus  up  -
node-exporter                          up  -
```

Status: passed

Notes:

- Dashboard에 필요한 kube-state-metrics, kubelet/cAdvisor와 node-exporter target이 모두 `UP`이다.
- 조회된 active target에서 `lastError`는 모두 비어 있었다.
- 전체 target metadata와 private scrape URL은 기록하지 않았다.

### UNIT-03 Prometheus local access 확인

첫 readiness 확인:

```bash
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready
```

Result:

```text
Prometheus Server is Ready.
```

Status: passed

Pod/Container/Node metric inventory를 시작한 직후 동일 endpoint를 다시 조회했다.

Command:

```bash
metrics=(
  kube_pod_owner
  kube_pod_info
  kube_pod_container_info
  kube_pod_container_status_restarts_total
  kube_pod_status_phase
  kube_pod_status_scheduled
  kube_pod_status_reason
  kube_pod_container_status_waiting_reason
  container_cpu_usage_seconds_total
  container_memory_working_set_bytes
  kube_node_status_condition
  node_cpu_seconds_total
  node_memory_MemAvailable_bytes
  node_memory_MemTotal_bytes
  node_filesystem_avail_bytes
  node_filesystem_size_bytes
)
for metric in "${metrics[@]}"; do
  response=$(curl -fsSG --max-time 10 \
    --data-urlencode "query=count(${metric})" \
    http://127.0.0.1:9090/api/v1/query) || exit 1
  status=$(jq -r '.status' <<<"$response")
  count=$(jq -r '.data.result[0].value[1] // "0"' <<<"$response")
  printf '%-52s %s %s\n' "$metric" "$status" "$count"
done
```

Result:

```text
curl: (7) Failed to connect to 127.0.0.1 port 9090: Couldn't connect to server
```

Status: failed

Prometheus port-forward를 다시 열 수 있는지 Service read-only 조회로 확인했다.

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl --request-timeout=10s get svc \
  -n monitoring monitoring-kube-prometheus-prometheus \
  -o jsonpath='{.metadata.name}{"\n"}'
```

Result:

```text
Unable to connect to the server: dial tcp 127.0.0.1:6443: connect: operation not permitted
```

Status: failed

Notes:

- 첫 readiness 응답 뒤 기존 `9090` port-forward가 종료됐다.
- K3s API local SSH tunnel에도 현재 실행 환경에서 접근할 수 없어 Agent가 새
  port-forward를 열 수 없었다.
- 이 결과는 metric 부재, target DOWN 또는 Production 장애를 의미하지 않는다.
- 당시에는 실제 series, label과 PromQL 결과를 확인하지 못했다. 아래 운영자
  재검증에서 port-forward 복구 후 UNIT-03 전체 query에 성공했으므로 이 실패
  기록은 과거 연결 이력으로 보존한다.

### UNIT-03 운영자 재검증: 연결과 metric inventory

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready

metrics=(
  kube_pod_owner
  kube_pod_info
  kube_pod_container_info
  kube_pod_container_status_restarts_total
  kube_pod_status_phase
  kube_pod_status_scheduled
  kube_pod_status_unschedulable
  kube_pod_status_reason
  kube_pod_container_status_waiting_reason
  container_cpu_usage_seconds_total
  container_memory_working_set_bytes
  kube_node_status_condition
  node_cpu_seconds_total
  node_memory_MemAvailable_bytes
  node_memory_MemTotal_bytes
  node_filesystem_avail_bytes
  node_filesystem_size_bytes
  node_uname_info
)
for metric in "${metrics[@]}"; do
  response=$(curl -fsSG --max-time 10 \
    --data-urlencode "query=count(${metric})" \
    http://127.0.0.1:9090/api/v1/query) || exit 1
  printf '%-52s %s %s\n' \
    "$metric" \
    "$(jq -r '.status' <<<"$response")" \
    "$(jq -r '.data.result[0].value[1] // "0"' <<<"$response")"
done
```

Result:

```text
Kubernetes Nodes: arm-master-node Ready, arm-worker-node Ready, pi-worker-node Ready
Prometheus Server is Ready.
kube_pod_owner                                      success 43
kube_pod_info                                       success 43
kube_pod_container_info                             success 49
kube_pod_container_status_restarts_total            success 49
kube_pod_status_phase                               success 215
kube_pod_status_scheduled                           success 129
kube_pod_status_unschedulable                       success 0
kube_pod_status_reason                              success 344
kube_pod_container_status_waiting_reason            success 0
container_cpu_usage_seconds_total                    success 93
container_memory_working_set_bytes                   success 93
kube_node_status_condition                          success 36
node_cpu_seconds_total                              success 64
node_memory_MemAvailable_bytes                      success 3
node_memory_MemTotal_bytes                          success 3
node_filesystem_avail_bytes                         success 15
node_filesystem_size_bytes                          success 15
node_uname_info                                     success 3
```

Status: passed

Notes:

- 각 숫자는 상태값, Pod/Node의 정상 여부 또는 event 횟수가 아니라
  `count(metric)`이 반환한 metric series 수다.
- `0`인 `kube_pod_status_unschedulable`과
  `kube_pod_container_status_waiting_reason`은 현재 일치 series가 없다는 뜻이며
  정상 상태값 `0`을 가진 series가 반환됐다는 뜻이 아니다.

### UNIT-03 정기 Pipeline Pod join과 상태 query

Command:

```bash
PIPELINE_PODS='label_replace(kube_pod_owner{namespace="default",owner_kind="Job"},"job_name","$1","owner_name","(.+)") * on(namespace,job_name) group_left(cronjob) label_replace(kube_job_owner{namespace="default",owner_kind="CronJob",job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"},"cronjob","$1","owner_name","(.+)")'

curl -fsSG --data-urlencode "query=${PIPELINE_PODS}" \
  http://127.0.0.1:9090/api/v1/query |
jq -r '[.data.result | length, ([.data.result[].metric.pod | contains("-prewarm-")] | any)] | @tsv'

curl -fsSG \
  --data-urlencode "query=sum by (cronjob,pod) (kube_pod_container_status_restarts_total{namespace=\"default\"} * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS}))" \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.cronjob, .metric.pod, .value[1]] | @tsv'

for query in \
  "(kube_pod_status_phase{namespace=\"default\",phase=\"Pending\"} == 1) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS})" \
  "(kube_pod_status_unschedulable{namespace=\"default\"} == 1) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS})" \
  "(kube_pod_status_scheduled{namespace=\"default\",condition=\"false\"} == 1) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS})" \
  "(kube_pod_container_status_waiting_reason{namespace=\"default\"} == 1) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS})"
do
  curl -fsSG --data-urlencode "query=${query}" \
    http://127.0.0.1:9090/api/v1/query |
  jq -r '.data.result | length'
done
```

Result:

```text
정기 Pipeline Pod: 9
prewarm Pod 포함: false
전달 label: pod, job_name, cronjob
정기 Pod restart: 9개 모두 0
Pending resultCount: 0
unschedulable resultCount: 0
scheduled condition=false resultCount: 0
waiting reason resultCount: 0
```

Status: passed

Notes:

- `kube_pod_owner → kube_job_owner` join과 숫자 suffix canonical filter가 정기
  Pipeline Pod만 선택했다.
- 상태별 metric은 `== 1`을 적용해야 현재 활성 상태만 남는다.
- unschedulable 전용 metric은 series가 없어
  `kube_pod_status_scheduled{condition="false"} == 1`도 대체 query로 검증했다.

### UNIT-03 최근 24시간 Pipeline CPU와 Memory

Command:

```bash
CPU_QUERY="max by (cronjob) (max_over_time((sum by (namespace,pod) (rate(container_cpu_usage_seconds_total{namespace=\"default\",container!=\"\",container!=\"POD\",image!=\"\"}[5m])) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS}))[24h:5m]))"
MEMORY_QUERY="max by (cronjob) (sum by (cronjob,pod) (max_over_time(container_memory_working_set_bytes{namespace=\"default\",container!=\"\",container!=\"POD\",image!=\"\"}[24h]) * on(namespace,pod) group_left(job_name,cronjob) (${PIPELINE_PODS})))"

for query in "$CPU_QUERY" "$MEMORY_QUERY"; do
  curl -fsSG --data-urlencode "query=${query}" \
    http://127.0.0.1:9090/api/v1/query |
  jq -r '.data.result[] | [.metric.cronjob, .value[1]] | @tsv'
done
```

Result:

| Pipeline        | 최근 24시간 최대 5분 평균 CPU | 최근 24시간 최대 Memory working set |
| --------------- | ----------------------------: | ----------------------------------: |
| RSS Collector   |             약 `0.00445` core |     `42618880` bytes, 약 `40.6 MiB` |
| Daily Pipeline  |             약 `0.02937` core |     `80535552` bytes, 약 `76.8 MiB` |
| 3-day Pipeline  |             약 `0.09195` core |   `117649408` bytes, 약 `112.2 MiB` |
| Weekly Pipeline |                     `No data` |                           `No data` |

Status: passed

Notes:

- CPU 값은 순간 peak가 아니라 최근 24시간 안에서 가장 높았던 5분 평균이다.
- Memory는 container별 `max_over_time(...[24h])` 후 Pod별로 합산하고 Pipeline
  실행 Pod 중 최댓값을 선택한다.
- Weekly 실행 후 24시간이 지났고 Prometheus retention이 `1d`라서 range
  series가 남지 않았다. Weekly `No data`를 0이나 정상으로 해석하지 않는다.

### UNIT-03 Node Ready, CPU, Memory와 Running Pod

Command:

```bash
NODE_MAP='label_replace(kube_node_info,"instance","$1:9100","internal_ip","(.+)")'
READY_QUERY='kube_node_status_condition{condition="Ready",status="true"} == 1'
CPU_QUERY="100 * (1 - avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))) * on(instance) group_left(node) (${NODE_MAP})"
MEMORY_QUERY="100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * on(instance) group_left(node) (${NODE_MAP})"
PODS_QUERY='sum by(node) ((kube_pod_status_phase{phase="Running"} == 1) * on(namespace,pod) group_left(node) kube_pod_info)'

for query in "$READY_QUERY" "$CPU_QUERY" "$MEMORY_QUERY" "$PODS_QUERY"; do
  curl -fsSG --data-urlencode "query=${query}" \
    http://127.0.0.1:9090/api/v1/query |
  jq -r '.data.result[] | [.metric.node, .value[1]] | @tsv'
done

curl -fsSG \
  --data-urlencode 'query=node_uname_info' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.instance, .metric.nodename] | @tsv'
```

Result:

| Node              | Ready | 최근 5분 CPU 사용률 | Memory 사용률 | Running Pod |
| ----------------- | ----: | ------------------: | ------------: | ----------: |
| `arm-master-node` |   `1` |           약 `8.1%` |    약 `20.3%` |        `14` |
| `arm-worker-node` |   `1` |          약 `53.2%` |    약 `16.4%` |        `13` |
| `pi-worker-node`  |   `1` |           약 `0.8%` |     약 `7.5%` |         `2` |

Status: passed

Notes:

- CPU는 최근 5분 `idle` 비율 기반 평균 사용률이고 Memory는
  `100 * (1 - MemAvailable / MemTotal)`이다.
- Running Pod query는 `phase="Running" == 1`과 `kube_pod_info`를 join해
  Completed Pod를 제외한다.
- `node_uname_info.nodename`은 Pi를 `scj`로 표시하므로 Dashboard label로 직접
  사용하지 않는다. `kube_node_info.internal_ip`과 node-exporter `instance`를
  `label_replace`로 join해 Kubernetes node 이름을 사용한다.

### UNIT-03 root filesystem inventory와 사용률

Command:

```bash
curl -fsSG \
  --data-urlencode 'query=count by (fstype,mountpoint) (node_filesystem_size_bytes)' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.fstype, .metric.mountpoint, .value[1]] | @tsv'

FILESYSTEM_QUERY="100 * (1 - node_filesystem_avail_bytes{fstype=\"ext4\",mountpoint=\"/\"} / node_filesystem_size_bytes{fstype=\"ext4\",mountpoint=\"/\"}) * on(instance) group_left(node) (${NODE_MAP})"
curl -fsSG --data-urlencode "query=${FILESYSTEM_QUERY}" \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.node, .value[1]] | @tsv'
```

Result:

- 운영 대상은 세 Node의 `fstype="ext4"`, `mountpoint="/"`다.
- `tmpfs`, `/run`, `/run/lock`, `/boot`와 vfat EFI/firmware partition은 제외
  대상임을 inventory에서 확인했다.

| Node              | Root filesystem 사용률 |
| ----------------- | ---------------------: |
| `arm-master-node` |             약 `12.9%` |
| `arm-worker-node` |             약 `21.8%` |
| `pi-worker-node`  |              약 `8.7%` |

Status: passed

Notes: filesystem query도 `kube_node_info` mapping을 사용해 Kubernetes node
이름을 legend로 전달한다.

### UNIT-02 Job metric series inventory

운영자가 Prometheus Service를 localhost `9090`으로 port-forward한 terminal을
유지한 상태에서 query API를 실행했다.

Command:

```bash
for metric in \
  kube_job_status_completion_time \
  kube_job_status_succeeded \
  kube_job_status_failed \
  kube_job_status_active
do
  curl -fsSG \
    --data-urlencode "query=count(${metric}{namespace=\"default\"})" \
    http://127.0.0.1:9090/api/v1/query |
  jq -r --arg metric "$metric" \
    '[$metric, .status, .data.result[0].value[1]] | @tsv'
done
```

Result:

```text
kube_job_status_completion_time  success  12
kube_job_status_succeeded        success  12
kube_job_status_failed           success  12
kube_job_status_active           success  12
```

Status: passed

Notes:

- `12`는 상태값, 성공 횟수 또는 실패 횟수가 아니라 각 selector가 반환한 metric
  series 수다.
- 검증된 공통 식별 label은 `namespace`와 `job_name`이다.
- `completion_time` 값은 Unix timestamp, `succeeded`/`failed`/`active` 값은 각
  Job의 해당 상태 수를 뜻한다.

### UNIT-02 owner 관계와 정기 Job filter

Command:

```bash
OWNER_MATCHERS='namespace="default",owner_kind="CronJob",owner_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"'
REGULAR_MATCHER='job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"'

curl -fsSG \
  --data-urlencode "query=count(kube_job_owner{${OWNER_MATCHERS}})" \
  http://127.0.0.1:9090/api/v1/query | jq -r '.data.result[0].value[1]'

curl -fsSG \
  --data-urlencode "query=count(kube_job_owner{${OWNER_MATCHERS},job_name=~\".*-prewarm-.*\"})" \
  http://127.0.0.1:9090/api/v1/query | jq -r '.data.result[0].value[1]'

curl -fsSG \
  --data-urlencode "query=count(kube_job_owner{${OWNER_MATCHERS},${REGULAR_MATCHER}})" \
  http://127.0.0.1:9090/api/v1/query | jq -r '.data.result[0].value[1]'
```

Result:

```text
Pipeline CronJob owner 대상 Job: 12
그중 prewarm Job: 3
숫자 suffix filter 적용 정기 Job: 9
```

Status: passed

Notes:

- `kube_job_owner`에서 검증한 관계 label은 `namespace`, `job_name`,
  `owner_kind`, `owner_name`이다.
- prewarm Job도 `owner_kind="CronJob"`과 동일한 Pipeline `owner_name`을
  가지므로 owner 조건만으로는 제외되지 않는다.
- canonical 정기 Job filter는 다음과 같다.

```promql
job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
```

### UNIT-02 정기 Job 성공 상태와 최근 성공 시각 join

Command:

```bash
curl -fsSG \
  --data-urlencode 'query=kube_job_status_succeeded{namespace="default",job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"} == 1' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.job_name, .value[1]] | @tsv'

curl -fsSG \
  --data-urlencode 'query=max by (owner_name) (kube_job_status_completion_time{namespace="default",job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"} * on (namespace,job_name) (kube_job_status_succeeded{namespace="default",job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"} == 1) * on (namespace,job_name) group_left(owner_name) kube_job_owner{namespace="default",owner_kind="CronJob",owner_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)"})' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[] | [.metric.owner_name, .value[1]] | @tsv'
```

Result:

- canonical filter에 일치한 정기 Job 9개가 모두 value `1`이었다.
- `completion_time + succeeded + filtered owner` join은 RSS, Daily, 3-day,
  Weekly 네 Pipeline 모두 결과를 반환했다.

Status: passed

Notes: join의 `succeeded == 1`은 성공한 Job만 남기고, `group_left(owner_name)`은
Pipeline별 집계를 위해 owner label을 completion series에 전달한다.

### UNIT-02 Weekly 정기 실행과 CronJob lastSuccessfulTime 비교

Command:

```bash
curl -fsSG \
  --data-urlencode 'query=max(kube_job_status_completion_time{namespace="default",job_name=~"news-weekly-topic-pipeline-[0-9]+"} * on (namespace,job_name) (kube_job_status_succeeded{namespace="default",job_name=~"news-weekly-topic-pipeline-[0-9]+"} == 1))' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[0].value[1]'

curl -fsSG \
  --data-urlencode 'query=kube_cronjob_status_last_successful_time{namespace="default",cronjob="news-weekly-topic-pipeline"}' \
  http://127.0.0.1:9090/api/v1/query |
jq -r '.data.result[0].value[1]'
```

Result:

```text
Weekly filtered regular Job completion_time: 1783870652
Weekly CronJob lastSuccessfulTime:             1784093724
```

Status: passed

Notes:

- 두 값의 차이와 Job inventory를 대조해 prewarm Job 성공이 CronJob
  `lastSuccessfulTime`을 갱신한 것을 확인했다.
- `kube_cronjob_status_last_successful_time`은 정기 실행 성공 시각 panel에
  사용하지 않는다.
- 정기 실행 최근 성공 시각은 숫자 suffix로 제한한 Job의 `completion_time`과
  `succeeded` 및 filtered owner join으로 계산한다.
- `No data`는 성공이 아니다. 일치하는 성공 Job 부재, Job object/series 정리,
  scrape 장애, metric 부재 또는 label/filter 불일치를 구분해야 한다.
- retention `1d`와 persistent storage 부재 때문에 하루보다 긴 실행 이력과
  삭제된 Job의 장기 시계열은 보장되지 않는다.

### UNIT-01 local validation

첫 번째 command attempt:

```bash
# YAML parse, Helm render assertion과 문서/diff 검증을 한 shell에서 실행
for path in docs/design/pipeline-operations-dashboard.md docs/runbooks/monitoring.md
do
  test -s "$path"
done
```

Result: YAML parse와 Helm render assertion은 통과했지만 zsh의 `path` 특수 변수를 반복 변수로 덮어써 이후 `rg`와 `git` command가 `command not found`로 실행되지 않았다.

Status: failed

Notes: Repository 검증 실패가 아니라 검증 command 작성 오류다. 반복 변수를 `doc_path`로 바꿔 아래 command를 다시 실행했다.

Command:

```bash
ruby -e '
require "yaml"
Dir["k8s/monitoring/**/*.yaml"].sort.each do |yaml_path|
  YAML.load_stream(File.read(yaml_path))
  puts "ok #{yaml_path}"
end
'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/news-lab-monitoring-rendered.yaml

# Rendered Prometheus retention/storage, Grafana dashboard sidecar label과
# Alertmanager 부재를 Ruby assertion으로 확인

rg -n 'pipeline-operations-dashboard\.md' docs/ARCHITECTURE.md
rg -n 'runbooks/monitoring\.md' docs/RUNBOOK.md
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt
git diff --stat
git diff --name-only
git status --short
```

Result:

```
ok k8s/monitoring/kube-prometheus-stack-values.yaml
UNIT-01 render assertions: OK
Architecture와 Runbook index link: present
git diff --check: no output
application/Pipeline/DB/dependency diff: no output
```

Status: passed

Notes:

- `git diff`는 tracked file만 표시하므로 새 문서는 `git status --short`와 별도 파일 존재 확인으로 함께 확인했다.
- 기존 사용자 변경인 `docs/tasks/main.md`와 task scaffold 문서들도 status에 유지했다.

### 새 문서 whitespace와 금지 metric scan

Command:

```bash
# UNIT-01에서 작성/수정한 Markdown을 Ruby로 순회해 trailing whitespace 확인
rg -n \
  'partial_success|candidate_count|embedding_count|saved_topic_count|failed_topic_count' \
  k8s/monitoring
git diff --check
```

Result:

```
Markdown whitespace check: OK
금지된 업무 metric 검색: no output
git diff --check: no output
```

Status: passed

### UNIT-02 문서 정합성과 변경 범위 확인

Command:

```bash
ruby -e '
paths = %w[
  docs/design/pipeline-operations-dashboard.md
  docs/verification/feat-pipeline-operations-dashboard.md
  docs/tasks/feat-pipeline-operations-dashboard.md
]
paths.each do |path|
  abort "missing #{path}" unless File.file?(path) && !File.zero?(path)
  File.readlines(path).each_with_index do |line, index|
    abort "trailing whitespace #{path}:#{index + 1}" if line.match?(/[ \t]+$/)
  end
end
puts "UNIT-02 Markdown checks: OK"
'

rg -n \
  'Verification Status|^pending$|UNIT-02:|UNIT-03:|1783870652|1784093724|kube_cronjob_status_last_successful_time|news-\(rss-collector\|daily-topic-pipeline\|three-day-topic-pipeline\|weekly-topic-pipeline\)-\[0-9\]\+' \
  docs/design/pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/tasks/feat-pipeline-operations-dashboard.md

git diff --check
git diff --name-only -- app scripts db migrations requirements.txt k8s
git status --short
```

Result:

```text
UNIT-02 Markdown checks: OK
Verification Status: pending
UNIT-02 checklist: checked
UNIT-03 checklist: unchecked
canonical filter와 두 Weekly timestamp: Design과 Verification에 present
git diff --check: no output
application/Pipeline/DB/dependency/Kubernetes diff: no output
```

Status: passed

Notes:

- `git status --short`에는 작업 시작 전부터 존재한 Architecture/Runbook/task
  scaffold 변경과 문서가 유지됐다.
- UNIT-02에서는 Design, Verification, Task만 수정했고
  `docs/runbooks/monitoring.md` 변경은 필요하지 않았다.
- Dashboard JSON/ConfigMap, monitoring values, application, DB, Pipeline 및
  dependency는 변경하지 않았다.

### UNIT-03 문서 정합성과 변경 범위 확인

Command:

```bash
ruby -e '
paths = %w[
  docs/design/pipeline-operations-dashboard.md
  docs/verification/feat-pipeline-operations-dashboard.md
  docs/tasks/feat-pipeline-operations-dashboard.md
]
paths.each do |path|
  abort "missing #{path}" unless File.file?(path) && !File.zero?(path)
  File.readlines(path).each_with_index do |line, index|
    abort "trailing whitespace #{path}:#{index + 1}" if line.match?(/[ \t]+$/)
  end
end
puts "UNIT-03 Markdown checks: OK"
'

rg -n \
  'Verification Status|^pending$|UNIT-03:|UNIT-04:|0\.00445|117649408|scj|phase="Running"|fstype="ext4"|No data|retention.*1d' \
  docs/design/pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/tasks/feat-pipeline-operations-dashboard.md

git diff --check
git diff --name-only -- app scripts db migrations requirements.txt k8s
git status --short
```

Result:

```text
UNIT-03 Markdown checks: OK
Verification Status: pending
UNIT-03 checklist: checked
UNIT-04 checklist: unchecked
Pod/Node 결과, No data와 retention 근거: present
git diff --check: no output
application/Pipeline/DB/dependency/Kubernetes diff: no output
```

Status: passed

Notes:

- `git status --short`에는 작업 시작 전부터 존재한 Architecture/Runbook/task
  scaffold 변경과 문서가 유지됐다.
- UNIT-03에서는 Design, Verification, Task만 수정했고
  `docs/runbooks/monitoring.md` 변경은 필요하지 않았다.
- Dashboard JSON/ConfigMap, monitoring values, application, DB, Pipeline 및
  dependency는 변경하지 않았다.

### UNIT-04 Production query endpoint 연결 확인

Command:

```bash
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready
KUBECONFIG="$HOME/.kube/oci-k3s.yaml" \
  kubectl get nodes --request-timeout=5s
```

Result:

```text
curl: (7) Failed to connect to 127.0.0.1 port 9090
Unable to connect to the server: dial tcp 127.0.0.1:6443: connect: operation not permitted
```

Status: failed

Notes:

- UNIT-03 운영자 검증 때 사용한 Prometheus port-forward와 K3s SSH tunnel이 현재
  실행 환경에는 열려 있지 않았다.
- 이는 metric 부재나 Production 장애를 의미하지 않는다.
- UNIT-04에서 새로 조합한 schedule/suspend와 선택 기간 failure/restart query는
  live API 재검증을 완료하지 않았으며 UNIT-05 gate로 남긴다.
- 기존 UNIT-02/03 canonical query는 당시 기록된 성공 evidence를 사용했다.

### UNIT-04 Dashboard assertion 최초 시도

Command:

```bash
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml
ruby -e '<rendered ConfigMap과 embedded JSON assertion>'
```

Result: Dashboard JSON parse, Kustomize render와 후속 scan은 성공했지만 Ruby
assertion이 `JSON` module을 require하지 않아 `embedded JSON`에서 중단됐다. 당시
shell에 `set -e`가 없어 뒤 command가 계속 실행됐으므로 이 묶음은 성공으로
간주하지 않는다.

Status: failed

Notes: artifact 결함이 아니라 검증 command 결함으로 분류하고 아래 수정한
command를 별도로 실행했다.

### UNIT-04 Dashboard JSON과 provisioning artifact 검증

Command:

```bash
set -e
set -o pipefail
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
jq -e '<title, UID, timezone, time range, panel ID, row, datasource assertions>' \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml
ruby -rjson -e '<ConfigMap namespace, name, sidecar label, embedded JSON assertions>'
rg -n \
  'partial_success|candidate_count|embedding_count|saved_topic_count|failed_topic_count|postgres|supabase' \
  k8s/monitoring/dashboards
ruby -e '
require "yaml"
Dir["k8s/monitoring/**/*.yaml"].sort.each do |path|
  YAML.load_stream(File.read(path))
  puts "ok #{path}"
end
'
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt
git diff --name-only -- k8s/monitoring/kube-prometheus-stack-values.yaml
```

Result:

```text
UNIT-04 dashboard assertions: OK
Forbidden business metric/datasource scan: OK
ok k8s/monitoring/dashboards/kustomization.yaml
ok k8s/monitoring/kube-prometheus-stack-values.yaml
Panel count: 24
Target count: 20
application/Pipeline/DB/dependency diff: no output
monitoring values diff: no output
git diff --check: no output
```

Status: passed

Notes:

- Dashboard는 네 row group, 20개 Prometheus target, 중복 없는 24개 panel ID를
  가진다.
- 기본 범위는 `now-24h`, timezone은 `Asia/Seoul`, datasource UID는
  chart render에서 확인한 `prometheus`다.
- Kustomize render는 namespace `monitoring`, stable ConfigMap 이름과
  `grafana_dashboard: "1"` label을 생성하고 JSON source를 data key로 포함했다.
- 업무 metric, PostgreSQL/Supabase datasource, monitoring values, application,
  DB, Pipeline과 dependency는 변경하지 않았다.
- Helm render, 전체 pytest와 전체 panel PromQL API 재검증은 UNIT-05 범위라 이번
  UNIT에서 실행하지 않았다.

### UNIT-04 Production provisioning

Command: 실행하지 않음.

Result: Dashboard ConfigMap apply, Argo CD Sync, Helm upgrade, Grafana import와
Production panel 확인을 수행하지 않았다.

Status: human-required

Notes: 현재 Argo CD Application은 `k8s/`를 non-recursive하게 읽으므로 하위
Kustomization이 자동 반영되지 않는다. 전체 query 검증과 diff 승인 후 사람이
runbook의 별도 provisioning 절차를 수행해야 한다.

### UNIT-04 최종 artifact, 문서와 checklist 정합성

Command:

```bash
set -e
set -o pipefail
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml
ruby -rjson -ryaml -e \
  '<대상 파일 존재/whitespace, JSON panel/query, rendered ConfigMap assertions>'
rg -n \
  '^## Verification Status$|^pending$|UNIT-04:|UNIT-05:|UNIT-06:' \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/tasks/feat-pipeline-operations-dashboard.md
rg -n \
  'partial_success|candidate_count|embedding_count|saved_topic_count|failed_topic_count|postgres|supabase' \
  k8s/monitoring/dashboards
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt
git diff --name-only -- k8s/monitoring/kube-prometheus-stack-values.yaml
git branch --show-current
git status --short
git diff --name-only
```

Result:

```text
UNIT-04 final artifact/docs assertions: OK
Verification Status: pending
UNIT-04 checklist: checked
UNIT-05 checklist: unchecked
UNIT-06 checklist: unchecked
Forbidden dashboard content scan: OK
Branch: feat/pipeline-operations-dashboard
application/Pipeline/DB/dependency diff: no output
monitoring values diff: no output
git diff --check: no output
```

Status: passed

Notes:

- 최종 assertion은 20개 target 모두, 네 row, unique panel ID, Pipeline query의
  `default` namespace 제한과 rendered ConfigMap label을 확인했다.
- `git status --short`의 기존 UNIT 문서 scaffold와 Architecture/Runbook 변경을
  유지했고 UNIT-04에서는 Dashboard 디렉터리와 관련 문서만 추가/갱신했다.
- 후속 UNIT-05/06은 실행하거나 완료 표시하지 않았다.

### UNIT-05 local 검증 도구와 Prometheus endpoint 확인

Command:

```bash
helm version --short
kubectl version --client=true
jq --version
ruby --version
pytest --version
command -v promtool
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready
```

Result:

```text
helm: v4.2.0
kubectl client: v1.34.1 / Kustomize v5.7.1
jq: 1.7.1
ruby: 2.6.10
pytest: 9.1.1
promtool: unavailable
curl: Failed to connect to 127.0.0.1 port 9090
```

Status: failed

Notes:

- local Prometheus endpoint가 열려 있지 않아 Dashboard의 20개 target을 query
  API로 재검증하지 못했다.
- `promtool`도 설치돼 있지 않아 local parser 검증으로 API 검증을 대체할 수
  없었다.
- endpoint 연결 실패는 metric 부재나 Production 장애를 의미하지 않는다.

### UNIT-05 Dashboard JSON/YAML/Kustomize/Helm render 검증

Command:

```bash
ruby -e '<k8s/monitoring/**/*.yaml YAML.load_stream>'
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
jq -e '<title, UID, timezone, time range, unique panel ID, row, datasource assertions>' \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null
kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-rendered.yaml
ruby -rjson -ryaml -e \
  '<ConfigMap namespace/name/sidecar label/embedded JSON assertions>'
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  >/tmp/news-lab-monitoring-rendered.yaml
ruby -ryaml -e \
  '<Prometheus retention/replica/storage, Grafana sidecar label, Alertmanager assertions>'
```

Result:

```text
ok k8s/monitoring/dashboards/kustomization.yaml
ok k8s/monitoring/kube-prometheus-stack-values.yaml
Dashboard JSON/Kustomize assertions: OK
Helm render assertions: OK
Panel count: 24
Target count: 20
```

Status: passed

Notes:

- Dashboard title/UID, `Asia/Seoul`, `now-24h`, 네 row, datasource UID
  `prometheus`, 24개 고유 panel ID와 20개 target을 확인했다.
- rendered ConfigMap은 namespace `monitoring`, stable name과
  `grafana_dashboard: "1"` label 및 embedded Dashboard JSON을 포함한다.
- chart render는 Prometheus retention `1d`, replica `1`, persistent storage
  미설정, Grafana dashboard sidecar label과 Alertmanager 미생성을 유지한다.

### UNIT-05 전체 pytest 회귀

Command:

```bash
PYTHONPATH=. pytest -q
```

Result:

```text
445 passed, 91 subtests passed in 16.86s
```

Status: passed

### UNIT-05 Dashboard scope와 문서 정합성

Command:

```bash
ruby -rjson -e \
  '<필수 row, unique panel ID, target 수, default namespace와 datasource assertions>'
rg -n \
  'partial_success|candidate_count|embedding_count|saved_topic_count|failed_topic_count|postgres|supabase' \
  k8s/monitoring/dashboards
rg -n 'kind:[[:space:]]*(Alertmanager|PrometheusRule)' \
  k8s/monitoring/dashboards
rg -n 'design/pipeline-operations-dashboard\.md' docs/ARCHITECTURE.md
rg -n 'runbooks/monitoring\.md' docs/RUNBOOK.md
rg -n 'k8s/monitoring/dashboards/|Monitoring runbook' \
  docs/architecture/k3s-runtime.md
ruby -e '<관련 문서 존재와 trailing whitespace assertions>'
git diff --check
git diff --name-only -- app scripts db migrations requirements.txt
git diff --name-only -- k8s/monitoring/kube-prometheus-stack-values.yaml
git branch --show-current
git status --short
```

Result:

```text
Dashboard structural/scope assertions: OK
Forbidden dashboard content scan: OK
No Alertmanager/PrometheusRule dashboard artifact: OK
Documentation whitespace/link assertions: OK
application/Pipeline/DB/dependency tracked diff: 0
monitoring values tracked diff: 0
Branch: feat/pipeline-operations-dashboard
git diff --check: no output
```

Status: passed

Notes:

- Pipeline panel target가 `namespace="default"`를 포함하고 모든 target이
  Prometheus datasource를 사용하는지 확인했다.
- 금지된 업무 metric/DB datasource와 새 Alertmanager/PrometheusRule artifact는
  없다.
- `docs/tasks/main.md`와 기존 task/review/fix scaffold를 포함한 작업 시작 전
  변경은 보존했다.
- 이 local 검증 시점에는 query API gate가 남아 checklist를 미완료로 유지했다.
  아래 운영자 재검증으로 gate를 완료했으며 UNIT-06은 실행하지 않았다.

### UNIT-05 Dashboard 전체 Prometheus query API 재검증

운영자가 K3s API tunnel과 Prometheus port-forward를 준비한 뒤 read-only endpoint로
Dashboard의 모든 활성 PromQL target을 검증했다.

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
curl -fsS http://127.0.0.1:9090/-/ready

python - <<'PY'
import json
import urllib.parse
import urllib.request

dashboard_path = (
    "k8s/monitoring/dashboards/news-lab-pipeline-operations.json"
)
evidence_path = "/tmp/unit05-prometheus-query-validation.json"

with open(dashboard_path, encoding="utf-8") as dashboard_file:
    dashboard = json.load(dashboard_file)

panels = dashboard["panels"]
rows = [panel for panel in panels if panel.get("type") == "row"]
targets = [
    {
        "panel": panel["title"],
        "panel_type": panel["type"],
        "refId": target.get("refId"),
        "expr": target["expr"],
    }
    for panel in panels
    for target in panel.get("targets", [])
    if target.get("expr") and not target.get("hide", False)
]
assert len(panels) == 24
assert len(rows) == 4
assert len(targets) == 20

evidence = []
for index, target in enumerate(targets, start=1):
    query = target["expr"].replace("$__range", "24h")
    url = "http://127.0.0.1:9090/api/v1/query?" + urllib.parse.urlencode(
        {"query": query}
    )
    with urllib.request.urlopen(url) as response:
        payload = json.load(response)
    data = payload.get("data", {})
    result_count = len(data.get("result", []))
    passed = payload.get("status") == "success"
    evidence.append(
        {
            "panel": target["panel"],
            "panel_type": target["panel_type"],
            "refId": target["refId"],
            "expr": target["expr"],
            "resolved_expr": query,
            "instant_config": True,
            "instant": {
                "status": payload.get("status"),
                "resultType": data.get("resultType"),
                "resultCount": result_count,
                "errorType": payload.get("errorType"),
                "error": payload.get("error"),
            },
            "status": "passed" if passed else "failed",
        }
    )
    state = "PASS" if passed else "FAIL"
    print(
        f"{state} {index:02d}/{len(targets)} {target['panel']} "
        f"resultCount={result_count}"
    )

with open(evidence_path, "w", encoding="utf-8") as evidence_file:
    json.dump(evidence, evidence_file, ensure_ascii=False, indent=2)

passed_count = sum(item["status"] == "passed" for item in evidence)
print(f"Targets: {len(evidence)}")
print(f"Passed: {passed_count}")
print(f"Failed: {len(evidence) - passed_count}")
PY
```

Result:

```text
arm-master-node: Ready
arm-worker-node: Ready
pi-worker-node: Ready
Prometheus Server is Ready.
Targets: 20
Passed: 20
Failed: 0
```

|   # | Panel                          | instant resultCount |
| --: | ------------------------------ | ------------------: |
|  01 | CronJob Last Schedule          |                   4 |
|  02 | Last Successful Regular Job    |                   4 |
|  03 | CronJob Suspend                |                   4 |
|  04 | Active Regular Jobs            |                   4 |
|  05 | Retained Regular Job Succeeded |                   9 |
|  06 | Retained Regular Job Failed    |                   9 |
|  07 | Failures in Selected Range     |                   4 |
|  08 | Regular Job Completion Time    |                   9 |
|  09 | Currently Active Regular Jobs  |                   0 |
|  10 | Peak CPU (24h, 5m rate)        |                   3 |
|  11 | Peak Memory Working Set (24h)  |                   3 |
|  12 | Container Restart Increase     |                   9 |
|  13 | Pending Pipeline Pods          |                   0 |
|  14 | Scheduling Failed / False      |                   0 |
|  15 | Container Waiting Reason       |                   0 |
|  16 | Node Ready                     |                   3 |
|  17 | Node CPU Usage                 |                   3 |
|  18 | Node Memory Usage              |                   3 |
|  19 | Running Pods by Node           |                   3 |
|  20 | Root Filesystem Usage          |                   3 |

Status: passed

Notes:

- 24개 panel 중 row panel은 4개이고 실제 Prometheus target panel은 20개다.
- `Failures in Selected Range`와 `Container Restart Increase`의 Grafana
  `$__range`는 기본 범위 `now-24h`에 맞춰 `24h`로 치환했다.
- `label_replace`의 `$1`은 Grafana 변수가 아니라 정규식 capture group이므로
  치환하지 않았다.
- CronJob query의 4개 결과는 네 Pipeline, 정기 Job query의 9개 결과는 보존
  중인 정기 Job 9개와 일치하며 숫자 suffix filter가 prewarm Job을 제외했다.
- `Retained Regular Job Failed`의 resultCount `9`는 실패 Job 9개가 아니라 정기
  Job 9개에 failed metric series가 존재한다는 뜻이다.
- active/Pending/scheduling false/waiting reason의 resultCount `0`은 현재 해당
  상태가 없다는 뜻이며 query 실패가 아니다.
- CPU/Memory의 resultCount `3`은 최근 24시간 안에 실행된 RSS, Daily, 3-day다.
  Weekly `No data`는 실행 후 24시간 초과와 retention `1d`에 따른 예상 결과다.
- Node query의 resultCount `3`은 실제 Kubernetes Node 3대와 일치한다.
- 모든 query가 `status=success`였고 parse/execution error, many-to-many matching과
  duplicate series 오류가 없었다.
- 현재 target panel은 stat/table이므로 별도 `query_range` 대상이 없다. range
  selector가 있는 PromQL도 instant query 시점에서 내부 range를 정상 평가했다.
- 상세 evidence는 `/tmp/unit05-prometheus-query-validation.json`에 저장됐다.
  `/tmp` 파일은 일시적인 local evidence이며 repository artifact로 추가하지 않는다.

### UNIT-05 최종 local validation 재실행

Command:

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

PYTHONPATH=. pytest -q

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/kube-prometheus-stack-values.yaml

if rg -n '[[:blank:]]+$' \
  docs/design/pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md; then
  exit 1
else
  echo 'trailing whitespace: none'
fi

jq -e \
  'length == 20 and all(.status == "passed")' \
  /tmp/unit05-prometheus-query-validation.json >/dev/null

rg -n -C 4 \
  'UNIT-05|UNIT-06|Targets: 20|Passed: 20|Failed: 0|query API|pending' \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/design/pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md
```

Result:

```text
Dashboard JSON parse: passed
Kustomize render: passed
Helm chart 86.2.0 render: passed
445 passed, 91 subtests passed in 15.04s
git diff --check: no output
application/Pipeline/DB/dependency/monitoring values diff: no output
local query evidence: 20 entries, all status=passed
UNIT-05 checklist: checked
UNIT-06 checklist: unchecked
Verification Status: pending
Targets: 20 / Passed: 20 / Failed: 0 evidence: present
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-rendered.yaml`과
  `/tmp/news-lab-monitoring-rendered.yaml`은 local render 결과이며 repository
  artifact로 추가하지 않는다.
- Dashboard JSON, PromQL, application, Pipeline, DB, dependency와
  `kube-prometheus-stack` values는 변경하지 않았다.
- UNIT-06과 Production provisioning/Grafana UI 확인은 실행하지 않았다.

### UNIT-06 Production Grafana 접근 확인

Command:

```bash
curl -fsS --max-time 5 http://127.0.0.1:9090/-/ready
curl -fsS --max-time 5 http://127.0.0.1:3000/api/health

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl --request-timeout=15s get configmap \
  -n monitoring news-lab-pipeline-operations-dashboard \
  -o jsonpath='{.metadata.name}{"\n"}{.metadata.labels.grafana_dashboard}{"\n"}'

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl --request-timeout=15s get pods,svc \
  -n monitoring -l app.kubernetes.io/name=grafana
```

Result:

```text
Prometheus localhost: connection failed, curl exit 7
Grafana localhost: connection failed, curl exit 7
ConfigMap read: Kubernetes API 127.0.0.1:6443 connection failed, exit 1
Grafana object read: Kubernetes API 127.0.0.1:6443 connection failed, exit 1
```

Status: human-required

Notes:

- 현재 세션에 K3s API SSH tunnel, Prometheus port-forward와 Grafana
  port-forward가 없었다.
- 이 결과는 ConfigMap/Grafana 오브젝트 부재나 Production 장애를
  의미하지 않는다.
- 사람이 수행한 ConfigMap 반영과 Grafana UI 확인 결과가 prompt나
  Repository에 제공되지 않아 Production 검증을 통과로 기록하지 않았다.

### UNIT-06 Alerting 후보·업무 metric 공백 문서 검증

Command:

```bash
rg -n \
  '76차 Alerting 후보|CronJob schedule 지연|Node NotReady|Pipeline Pod restart|Kubernetes metric으로 확인할 수 없는' \
  docs/design/pipeline-operations-dashboard.md \
  docs/runbooks/monitoring.md

rg -n \
  'partial_success|last success|candidate count|embedding created/reused/missing|saved/failed topic|stage별 duration|Summary provider' \
  docs/design/pipeline-operations-dashboard.md
```

Result: 76차 CronJob/Node/Pod restart 후보와 7개 업무 metric 공백 문서
heading/entry를 확인했다.

Status: passed

Notes:

- 후보는 UNIT-02/03/05에서 실제 노출과 join을 확인한 metric을
  재사용한다.
- `15m` restart window는 76차 조정 후보이며 UNIT-06 live API에서 별도
  재검증하지 못했다.
- Alertmanager, `PrometheusRule`, threshold, `for`, notification route와 custom
  metric은 구현하지 않았다.

### UNIT-06 최종 local 문서·artifact 검증

Command:

```bash
python -m json.tool \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json >/dev/null

kubectl kustomize k8s/monitoring/dashboards \
  >/tmp/news-lab-dashboard-unit06-rendered.yaml

ruby -ryaml -e \
  'YAML.load_stream(File.read("/tmp/news-lab-dashboard-unit06-rendered.yaml")); puts "render yaml ok"'

git diff --check

git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/kube-prometheus-stack-values.yaml

rg -n \
  '^## Verification Status$|^pending$|UNIT-06|human-required|20 passed / 0 failed' \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/verification/feat-pipeline-operations-dashboard.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md
```

Result:

```text
Dashboard JSON parse: passed
Kustomize render: passed
render yaml ok
git diff --check: no output
application/Pipeline/DB/dependency/monitoring values diff: no output
documentation trailing whitespace: no output
Verification Status: pending
UNIT-06 checklist: unchecked, human-required note present
Production query evidence summary: 20 passed / 0 failed present
```

Status: passed

Notes:

- `/tmp/news-lab-dashboard-unit06-rendered.yaml`은 local render며 repository
  artifact가 아니다.
- UNIT-06은 문서만 변경했고 Dashboard JSON, Kustomization, monitoring
  values, application, Pipeline, DB와 dependency는 변경하지 않았다.
- Production Grafana 사람 확인이 남아 checklist와 전체 status를
  완료 처리하지 않았다.

## Results

- Repository values, chart `86.2.0` local render와 Production Prometheus object가 모두 replica `1`, retention `1d`, persistent storage 미설정 상태로 일치한다.
- Cluster 전체에 PVC가 없으므로 Prometheus 시계열은 장기 보존되지 않으며 Pod 재생성 시 기존 시계열 유실 가능성이 있다.
- Grafana Dashboard sidecar/provider가 활성화돼 있고 `grafana_dashboard: "1"`
  label을 사용하는 ConfigMap provisioning 경로에 맞춰 custom Dashboard artifact를
  추가했다.
- Grafana, Prometheus, kube-state-metrics, kubelet/cAdvisor와 node-exporter target은 모두 `UP`이며 `lastError`가 없다.
- 세 K3s Node와 Monitoring workload는 현재 정상 상태다.
- 네 NewsLab CronJob은 suspend되지 않은 상태이며 최근 정기 Job은 모두 완료됐다.
- CronJob owner 대상 Job 12개 중 prewarm Job 3개가 같은 owner 관계를 가지며, 숫자 suffix filter로 정기 Job 9개를 구분했다.
- 정기 Job 9개는 모두 succeeded value `1`이었고, 최근 성공 시각 join은 네 Pipeline 결과를 모두 반환했다.
- Weekly CronJob `lastSuccessfulTime`이 prewarm 성공으로 갱신됨을 확인해 정기 실행 최근 성공 시각에는 filtered Job `completion_time`과 `succeeded` join을 사용한다.
- Pod owner join은 정기 Pipeline Pod 9개를 반환했고 restart는 모두 `0`이었다. Pending, unschedulable, scheduled false와 waiting reason query는 모두 resultCount `0`이었다.
- 최근 24시간 CPU/Memory query는 RSS, Daily, 3-day 결과를 반환했으며 Weekly는 실행 후 24시간 초과와 retention `1d`로 `No data`였다.
- 세 Node는 Ready value `1`이었다. Kubernetes node label로 계산한 CPU, Memory, Running Pod와 root filesystem query가 모두 세 Node 결과를 반환했다.
- Running Pod query는 Completed Pod를 제외했고 filesystem은 ext4 root mount만 포함했다.
- 과거 Job이 이전 image tag를 보존하는 것은 정상적인 실행 이력이며 현재 CronJob desired state 오류가 아니다.
- UNIT-01 Repository/Production baseline, UNIT-02 CronJob/Job 및 UNIT-03 Pod/Node PromQL 검증을 완료했다.
- UNIT-04 Dashboard JSON과 기존 sidecar label을 사용하는 최소 Kustomize
  ConfigMap generator를 추가했다.
- UNIT-05 local JSON/YAML/Kustomize/Helm render, Dashboard scope와 문서 정합성
  검증 및 전체 pytest 회귀는 통과했다.
- UNIT-05 당시 Dashboard의 활성 PromQL target 20개를 Production Prometheus
  query API에서 모두 실행해 `20 passed / 0 failed`를 확인했다.
- 숫자 suffix filter는 prewarm Job을 제외했다. 이상 상태 query의 resultCount
  `0`은 현재 해당 상태가 없다는 뜻이며 query 실패가 아니다.
- Weekly CPU/Memory `No data`는 실행 후 24시간 초과와 retention `1d`에 따른 예상
  결과다.
- UNIT-05 전체 검증을 완료했다.
- UNIT-06의 76차 Alerting 후보와 7개 업무 metric 공백을 확정했다.
- Approved Fix로 target 20개의 Instant 전용 설정, DateTime query 세 개의
  milliseconds 변환, empty-result `No data` 정책, Grafana data proxy timeout
  `120s`, 자동 refresh `15m`와 CPU·Memory·Restart 정기 Pod 조기 필터를
  repository에 반영했다.
- 수정 후 JSON/Kustomize/Helm assertion과 전체 pytest를 통과했고, 최신 target
  20개도 Production Prometheus에서 `20 passed / 0 failed`였다.
- 수정 후 개별 query는 Failures `10.75s`, CPU `23.04s`, Memory `12.46s`,
  Restart `41.92s`였다. 운영자가 동시 성능을 세 번 다시 측정해 최대
  `79.418s`로 필수 `120s`와 권장 `90s` gate를 모두 통과했다.
- Production Helm Revision 1·2에서 Grafana CPU limit `200m`을 확인했고,
  Repository의 `300m` 선언을 `200m`으로 정합화했다. 이 변경은 query 성능
  개선이 아니라 비의도적 resource drift 방지다.
- raw Helm manifest diff에서 Grafana admin password Base64가 출력된 이력을
  password 노출로 취급한다. 실제 값은 기록하지 않았고, 운영자가 기존 password를
  회전하고 임시 patch 파일과 shell password 변수를 제거했다.
- 운영자가 Dashboard ConfigMap과 Helm Revision 3를 적용하고 Grafana rollout,
  timeout `120s`, resources baseline, API health와 Production UI를 확인했다.
- 실제 2026년 KST timestamp, expected empty-result panel의 일반 `No data`, Node
  3대와 빨간 query warning 미재발을 확인했다.
- UNIT-06과 전체 Verification을 완료했으며 최종 Status는 `passed`다.

## Manual or Production Verification

Status: passed for UNIT-01 through UNIT-06 and Approved Fix 1~8 scoped checks

운영자가 K3s API SSH tunnel과 Prometheus port-forward를 준비하고 read-only object
조회, Prometheus runtime spec, active target, UNIT-02~03 query와 Approved Fix
4~6 적용 후 Dashboard target 20개의 query API 실행을 확인했다. 이어 Dashboard
ConfigMap과 Helm Revision 3를 적용하고 Grafana rollout, API health와 실제 UI를
확인했다. password 회전과 임시 자료 정리도 사람이 수행했으며 민감한 값은
evidence에 포함하지 않았다.

Agent는 다음 작업을 실행하지 않았다.

- Dashboard import 또는 provisioning 적용
- `kubectl apply/delete/patch/edit/rollout`
- Helm install/upgrade/uninstall
- Argo CD Sync
- Production SQL
- Secret 변경
- Production 장애 주입

Approved Fix 1~3이 반영된 Dashboard의 과거 운영자 확인 evidence는 보존한다.
Approved Fix 4~8가 포함된 Production 적용과 최신 Grafana UI 확인은 위 UNIT-06
운영자 evidence로 완료했다.

## Deferred / Follow-up

- Grafana Elasticsearch bundled plugin 설치 permission 오류 점검
- Prometheus recording rule을 이용한 무거운 query 추가 최적화
- Alertmanager/PrometheusRule과 notification route 구현
- custom business metric 추가
- Prometheus retention/PVC/storage 개선

위 항목은 이번 Dashboard Production 적용과 UNIT-06 완료를 막지 않는 후속
작업이다. 장애 주입, Alertmanager/PrometheusRule과 custom business metric은 이
브랜치에서 구현하거나 검증하지 않았다.

## Evidence Notes

- `docs/verification/infra-monitoring-baseline.md`의 사람이 제공한 설치 당시 Pod 상태는 과거 기록으로만 참고했고, 이번 운영자 read-only 결과를 현재 live baseline으로 별도 확인했다.
- 최초 Production 조회 실패와 tunnel 준비 후 재검증 성공을 모두 기록했다.
- credential, SSH private key 경로, kubeconfig 내용, private address, private scrape URL과 전체 target metadata는 기록하지 않았다.
- 이 문서의 Agent 실행 command는 조회와 local port-forward로 제한했다. UNIT-06
  Production 적용·rollout은 사람이 수행한 sanitized evidence다.
- Agent는 `kubectl apply/delete/patch/edit/rollout`, Helm
  install/upgrade/uninstall, Production SQL, git push/merge를 실행하지 않았다.
- 최초 UNIT-03 연결 실패는 보존했고, 이후 운영자가 같은 read-only endpoint를
  복구해 제공한 성공 결과를 별도 기록했다.
- 과거 미수행 Production Dashboard provisioning과 Grafana UI 기록은 당시
  evidence로 보존하며, 최종 완료 판정은 이후 운영자가 제공한 UNIT-06 evidence에
  근거한다.
- Grafana Secret 값, password, Base64 값과 디코딩 값은 읽거나 문서에 기록하지
  않았다.
