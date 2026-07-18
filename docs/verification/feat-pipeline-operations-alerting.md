# Verification: Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## Verification Status

passed

## Verification Scope

- UNIT-01의 Repository Monitoring values, chart `86.2.0` Alertmanager render 구조,
  Prometheus rule selector와 namespace selector를 local read-only 방식으로 조사했다.
- 사람이 제공한 sanitized Production read-only 결과로 현재 Alertmanager,
  PrometheusRule, Prometheus selector와 AlertmanagerConfig baseline을 확인했다.
- UNIT-02에서 Alertmanager 활성화와 NewsLab label route를 반영했고, 최초 generic
  webhook receiver 설계는 Production 적용 전에 native Telegram receiver로
  교체했다.
- UNIT-03에서 실제 Alert 3종, 기본 Kustomization과 별도 전달 test rule artifact를
  구현하고 threshold, `for`, Job 보존 및 테스트 운영 경계를 문서화했다.
- UNIT-04에서 Monitoring YAML, 기본 Kustomize, chart `86.2.0` Helm render와 전체
  pytest를 검증했다. 사람이 Production과 동일한 Prometheus `v3.12.0` 이미지의
  `promtool`로 실제 Alert 3종과 전달 test Alert 1종도 검증했다.
- UNIT-05 진입 시 Production Alertmanager, PrometheusRule과 Prometheus alerting
  endpoint를 read-only로 재조회했으나 Agent 환경에서 local Kubernetes API
  tunnel에 접근할 수 없었다. 이후 사람이 Production 적용과 전달 검증을 완료했다.
- 실제 Secret, Telegram credential·chat ID, Pipeline 동작과 Production object는
  Agent가 조회하거나 변경하지 않았다.

## Commands Run

### UNIT-01 branch와 Repository inventory

Command:

```bash
git branch --show-current
git status --short
rg --files k8s docs | \
  rg '(monitor|prometheus|grafana|pipeline|alert|observ)'
find k8s/monitoring -maxdepth 3 -type f -print
```

Result:

```text
branch: feat/pipeline-operations-alerting
Monitoring values: k8s/monitoring/kube-prometheus-stack-values.yaml
Dashboard Kustomize artifacts: k8s/monitoring/dashboards/
Custom Alerting design/rule artifacts before UNIT-01: none
Working tree: existing task/review/fix/PR/devlog/verification drafts present
```

Status: passed

Notes:

- 기존 dirty working tree는 보존했고 UNIT-01과 무관한 파일을 수정하지 않았다.

### UNIT-01 chart version, defaults와 current render

Command:

```bash
helm version --short
helm repo list
helm show chart prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | rg '^(version|appVersion):'
helm show values prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | ruby -ryaml -e '
v = YAML.safe_load(STDIN.read, aliases: true)
alertmanager = v.fetch("alertmanager")
spec = alertmanager.fetch("alertmanagerSpec")
prometheus = v.fetch("prometheus").fetch("prometheusSpec")
puts "alertmanager.enabled=#{alertmanager["enabled"].inspect}"
puts "route.receiver=#{alertmanager.dig("config", "route", "receiver").inspect}"
puts "receivers=#{alertmanager.fetch("config").fetch("receivers").map { |r| r["name"] }.inspect}"
puts "configSecret=#{spec["configSecret"].inspect}"
puts "useExistingSecret=#{spec["useExistingSecret"].inspect}"
puts "secrets=#{spec["secrets"].inspect}"
puts "ruleSelector=#{prometheus["ruleSelector"].inspect}"
puts "ruleSelectorNilUsesHelmValues=#{prometheus["ruleSelectorNilUsesHelmValues"].inspect}"
puts "ruleNamespaceSelector=#{prometheus["ruleNamespaceSelector"].inspect}"
'
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml | \
  ruby -ryaml -e '
docs = YAML.load_stream(STDIN.read).compact
prometheus = docs.find { |doc| doc["kind"] == "Prometheus" }
rules = docs.select { |doc| doc["kind"] == "PrometheusRule" }
abort "Alertmanager rendered" if docs.any? { |doc| doc["kind"] == "Alertmanager" }
abort "unexpected alerting" unless prometheus.dig("spec", "alerting").nil?
expected = {"matchLabels" => {"release" => "monitoring"}}
abort "unexpected rule selector" unless prometheus.dig("spec", "ruleSelector") == expected
abort "unexpected rule namespace selector" unless prometheus.dig("spec", "ruleNamespaceSelector") == {}
abort "unexpected rule count: #{rules.length}" unless rules.length == 35
puts "Current monitoring render assertions: OK"
'
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --set alertmanager.enabled=true | \
  ruby -ryaml -e '
docs = YAML.load_stream(STDIN.read).compact
alertmanager = docs.find { |doc| doc["kind"] == "Alertmanager" }
prometheus = docs.find { |doc| doc["kind"] == "Prometheus" }
secret = docs.find do |doc|
  doc["kind"] == "Secret" &&
    doc.dig("metadata", "name") == "alertmanager-monitoring-kube-prometheus-alertmanager"
end
abort "missing Alertmanager" unless alertmanager
abort "unexpected Alertmanager name" unless alertmanager.dig("metadata", "name") == "monitoring-kube-prometheus-alertmanager"
abort "unexpected explicit configSecret" unless alertmanager.dig("spec", "configSecret").nil?
abort "missing configuration key" unless secret.fetch("data").key?("alertmanager.yaml")
endpoint = prometheus.dig("spec", "alerting", "alertmanagers").fetch(0)
expected = {
  "namespace" => "monitoring",
  "name" => "monitoring-kube-prometheus-alertmanager",
  "port" => "http-web",
  "pathPrefix" => "/",
  "apiVersion" => "v2"
}
abort "unexpected endpoint: #{endpoint}" unless endpoint == expected
puts "Enabled Alertmanager render assertions: OK"
'
```

Result:

```text
Helm: v4.2.0+g0646808
Chart: kube-prometheus-stack 86.2.0
Chart appVersion: v0.91.0
Repository render Alertmanager count: 0
Repository render Prometheus alerting: nil
Repository render PrometheusRule count: 35
Repository render rule selector: matchLabels release=monitoring
Repository render rule namespace selector: {}
Enabled render Alertmanager: monitoring-kube-prometheus-alertmanager
Enabled render configuration Secret:
  alertmanager-monitoring-kube-prometheus-alertmanager
Enabled render configuration key: alertmanager.yaml
Enabled render Prometheus Alertmanager endpoint:
  monitoring/monitoring-kube-prometheus-alertmanager:http-web, API v2
Chart default receiver: null
Chart default useExistingSecret: false
```

Status: passed

Notes:

- enabled render는 `--set`을 사용한 local 조사이며 Repository values를 수정하지
  않았다.
- Secret은 resource 이름과 key 구조만 확인했고 credential이나 실제 Production
  Secret을 조회하지 않았다.

### UNIT-01 chart CRD selector와 Secret semantics

Command:

```bash
helm show crds prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | \
  ruby -ryaml -e '
docs = YAML.load_stream(STDIN.read).compact
extract = lambda do |kind, fields|
  crd = docs.find do |doc|
    doc["kind"] == "CustomResourceDefinition" &&
      doc.dig("spec", "names", "kind") == kind
  end
  abort "missing #{kind} CRD" unless crd
  schema = crd.dig("spec", "versions").find { |v| v["served"] }
    .dig("schema", "openAPIV3Schema", "properties", "spec", "properties")
  fields.each do |field|
    description = schema.dig(field, "description").to_s.gsub(/\s+/, " ").strip
    puts "#{kind}.spec.#{field}: #{description}"
  end
end
extract.call("Prometheus", %w[ruleSelector ruleNamespaceSelector alerting])
extract.call(
  "Alertmanager",
  %w[configSecret alertmanagerConfigSelector alertmanagerConfigNamespaceSelector secrets]
)
'
```

Result:

```text
Prometheus ruleSelector: empty matches all objects; null matches none
Prometheus ruleNamespaceSelector: empty matches all namespaces;
  null matches only the current namespace
Alertmanager configSecret: empty uses alertmanager-<alertmanager-name>;
  configuration key is alertmanager.yaml
```

Status: passed

### UNIT-01 Production read-only baseline 과거 시도

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get alertmanager,pods -n monitoring

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheusrules -A -L release

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheus -n monitoring \
  -o jsonpath='{range .items[*]}name={.metadata.name}{"\n"}ruleSelector={.spec.ruleSelector}{"\n"}ruleNamespaceSelector={.spec.ruleNamespaceSelector}{"\n"}alertingEndpoints={range .spec.alerting.alertmanagers[*]}{.namespace}/{.name}:{.port}{" "}{end}{"\n"}{end}'

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get alertmanagerconfigs -A

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl explain prometheus.spec.ruleNamespaceSelector

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl explain prometheus.spec.ruleSelector
```

Result:

```text
Unable to connect to the server: dial tcp 127.0.0.1:6443:
connect: operation not permitted
```

Status: failed

Notes:

- kubeconfig가 가리키는 local Kubernetes API tunnel에 현재 실행 환경이 접근하지
  못해 모든 Production 조회가 실패했다.
- 실패를 live baseline으로 해석하지 않았고 과거 evidence로 현재 상태를
  추정하지 않았다.
- Secret get/decode와 production-impacting command는 실행하지 않았다.

### UNIT-01 Production live read-only baseline

Command:

```text
Human operator가 Kubernetes API tunnel과 cluster-info를 확인하고 Production
Alerting object를 read-only로 조회했다. Agent는 운영 command를 재실행하지 않았다.
```

Result:

```text
Kubernetes API tunnel and cluster-info: 정상
monitoring Alertmanager CR: 없음
monitoring Alertmanager Pod: 없음
monitoring Prometheus Pod: Running
monitoring Prometheus Operator Pod: Running
monitoring PrometheusRule count: 35
queried PrometheusRule namespace: monitoring
queried PrometheusRule label: release=monitoring
NewsLab custom PrometheusRule: 없음
Prometheus ruleSelector: {"matchLabels":{"release":"monitoring"}}
Prometheus ruleNamespaceSelector: {}
Prometheus alertingEndpoints: 없음
AlertmanagerConfig: 없음
active route and receiver: Alertmanager 미활성 상태이므로 해당 없음
Alertmanager configuration Secret: Alertmanager 미활성 상태이므로 해당 없음
```

Status: passed

Notes:

- 이 결과는 2026-07-18에 사람이 제공한 sanitized evidence를 그대로 요약했다.
- Secret 값과 endpoint 값은 확인하거나 추정하지 않았고 문서에 기록하지 않았다.
- 앞선 tunnel 접근 실패는 Agent 실행 환경의 과거 시도로 보존하며, 사람이 제공한
  live 결과를 현재 Production baseline으로 사용한다.

### UNIT-01 live evidence 반영 정합성 검증

Command:

```bash
rg -n 'UNIT-01 Status: `passed`|\[x\] UNIT-01:|\[ \] UNIT-02:' \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md

# Pending Verification의 UNIT-01 항목 부재 확인
# 대상 문서 trailing whitespace와 Markdown fence 짝 확인
# 대상 문서 credential value pattern 부재 확인

git diff --check
git status --short
```

Result:

```text
UNIT-01 Status: passed: found
Task UNIT-01 checkbox: checked
Task UNIT-02 checkbox: unchecked
Pending Verification UNIT-01 entry: absent
Target whitespace: OK
Markdown fences: OK
Credential value scan: OK
git diff --check: no output
```

Status: passed

Notes:

- 문서 정합성 검증만 수행했으며 UNIT-02 구현이나 운영 조회는 수행하지 않았다.

### UNIT-01 local 문서·render 최종 검증

Command:

```bash
python3 - <<'PY'
"""UNIT-03 Alert manifest의 구조와 핵심 PromQL 계약을 정적으로 검증한다."""
from pathlib import Path
import yaml

for path in Path("k8s/monitoring").rglob("*.yaml"):
    with path.open(encoding="utf-8") as stream:
        list(yaml.safe_load_all(stream))
    print(f"OK {path}")
PY

# 위 chart section의 current와 enabled Helm render assertion을 재실행

test -f docs/ARCHITECTURE.md
test -f docs/design/pipeline-operations-alerting.md
ruby -e '
files = %w[docs/ARCHITECTURE.md docs/design/pipeline-operations-alerting.md]
files.each do |file|
  File.read(file).scan(/\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)/).flatten.each do |target|
    next if target.match?(%r{\Ahttps?://})
    path = File.expand_path(target, File.dirname(file))
    abort "missing link target: #{file} -> #{target}" unless File.exist?(path)
  end
end
puts "Local Markdown links: OK"
'
rg -n 'Pipeline Operations Alerting 설계' \
  docs/ARCHITECTURE.md \
  docs/design/pipeline-operations-alerting.md
rg -n 'UNIT-01 Status: `blocked`|\[ \] UNIT-01:' \
  docs/tasks/feat-pipeline-operations-alerting.md

if rg -n '[[:blank:]]+$' \
  docs/ARCHITECTURE.md \
  docs/design/pipeline-operations-alerting.md \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md; then
  exit 1
else
  echo 'Target whitespace: OK'
fi

for file in \
  docs/ARCHITECTURE.md \
  docs/design/pipeline-operations-alerting.md \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md; do
  count=$(rg -c '^```' "$file" || true)
  if (( count % 2 != 0 )); then
    exit 1
  fi
done

if rg -n -i \
  'B[E]GIN (RSA|OPENSSH|PRIVATE)|webhook[_-]?u[r]l:[[:space:]]*https?://|passw[o]rd:[[:space:]]*[^<]' \
  docs/design/pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md; then
  exit 1
else
  echo 'Target credential value scan: OK'
fi

git diff --check
git diff --name-only -- app scripts db requirements.txt k8s
git diff --stat
git diff --name-only
git status --short
```

Result:

```text
Monitoring YAML parse: 2 passed
Current monitoring render assertions: OK
Enabled Alertmanager render assertions: OK
Local Markdown links and fences: OK
Architecture index link and UNIT-01 blocked/unchecked state: found
Target whitespace: OK
Target credential value scan: OK
git diff --check: no output
Application/Pipeline/DB/dependency/Kubernetes scope diff: no output
Tracked diff: docs/ARCHITECTURE.md and pre-existing docs/tasks/main.md
```

Status: passed

Notes:

- `git diff --stat`와 `git diff --name-only`는 untracked task artifact를 포함하지
  않으므로 `git status --short`로 함께 확인했다.
- 첫 credential scan은 Verification에 기록한 literal 정규식 자체를 탐지해
  실패했다. 같은 민감값을 탐지하지만 command text는 탐지하지 않는 bracket
  expression으로 바꿔 재실행했고 출력 없이 통과했다.
- `docs/tasks/main.md` 변경과 기존 PR/devlog/review/fix 초안은 UNIT-01 시작 전부터
  존재했으며 수정하지 않았다.
- 전체 pytest는 Task의 UNIT-04 전체 회귀 범위이므로 UNIT-01에서 실행하지 않았다.

### UNIT-02 chart와 Alertmanager configuration 계약 조사

이 section은 Production 적용 전에 폐기한 최초 generic webhook 설계의 historical
evidence다. 현재 native Telegram receiver 계약은 뒤의 receiver 변경 검증을
source of truth로 사용한다.

Command:

```bash
command -v amtool || true
command -v promtool || true
helm show values prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | \
  sed -n '/^alertmanager:/,/^grafana:/p'
helm show crds prometheus-community/kube-prometheus-stack \
  --version 86.2.0 | \
  rg -n -C 3 'urlFile|url_file|urlSecret|webhookConfigs|matchers:|Route'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --set alertmanager.enabled=true \
  --set 'alertmanager.alertmanagerSpec.secrets[0]=news-lab-alertmanager-webhook' | \
ruby -ryaml -e '<Alertmanager spec and configuration Secret key assertions>'
```

Result:

```text
amtool: not installed
promtool: not installed
Chart Alertmanager image: prometheus/alertmanager:v0.32.2
alertmanagerSpec.secrets mount root: /etc/alertmanager/secrets/
Rendered Alertmanager spec.secrets:
  news-lab-alertmanager-webhook
Rendered chart-managed configuration Secret key: alertmanager.yaml
```

Status: passed

Notes:

- 공식 Alertmanager configuration 계약에서 root route는 matcher 없이 모든 Alert를
  받아야 하고, generic webhook은 mutually exclusive한 `url` 또는 `url_file`을
  지원함을 확인했다.
- 따라서 root `null` sink와 NewsLab label child route를 분리하고 실제 endpoint는
  mounted Secret의 `url_file`로 읽는 구조를 선택했다.
- local chart render만 수행했으며 Production Secret이나 object는 조회·변경하지
  않았다.

### UNIT-02 values·문서와 Helm render 정적 검증

이 section의 webhook render 결과는 최초 설계의 historical evidence이며 현재
configuration을 나타내지 않는다.

Command:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

for path in Path('k8s/monitoring').rglob('*.yaml'):
    with path.open(encoding='utf-8') as stream:
        list(yaml.safe_load_all(stream))
    print(f'OK {path}')
PY

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml | \
ruby -ryaml -rbase64 -e '<Alertmanager render assertions>'

ruby -e '<local Markdown link assertions>'

# values, design과 runbook의 credential value pattern 부재 확인
git diff --check
```

Result:

```text
Monitoring YAML parse: 2 passed
Alertmanager render assertions: OK
External receiver count: 1
NewsLab child route count: 1
Credential source: mounted Secret file
Local Markdown links: OK
Target credential value scan: OK
git diff --check: no output
```

Status: passed

Notes:

- render assertion은 Alertmanager CR 활성화, `observability=true` placement,
  Prometheus API v2 endpoint, Secret mount 이름, matcher 없는 root route,
  `alert_scope="news-lab"` child route 한 개, 외부 webhook receiver 한 개,
  `send_resolved: true`와 정확한 `url_file` path를 확인했다.
- configuration의 receiver entry는 필수 root `null` sink와 외부 receiver 두 개지만,
  endpoint로 전송하는 receiver는 한 개다.
- chart-managed configuration Secret을 local render에서만 decode해 구조를 검사했고
  실제 endpoint나 Production Secret 값은 존재하지 않았다.
- `amtool`이 없어 독립 Alertmanager parser 검증은 수행하지 않았다. UNIT-04의 전체
  render와 UNIT-05의 Production configuration/log 확인은 계속 남아 있다.
- `PrometheusRule`, Kustomize artifact와 Python 파일은 UNIT-02에서 변경하지 않았다.
- 전체 pytest와 rule 검증은 Task가 지정한 UNIT-04 전체 회귀 범위이므로 실행하지
  않았다.

### UNIT-02 final scope와 checklist 정합성 검증

Command:

```bash
# Monitoring YAML parse와 Alertmanager final render assertions 재실행
# local Markdown link, fence, trailing whitespace와 credential value scan 재실행
rg -n 'UNIT-02 Status: passed|\[x\] UNIT-02:|\[ \] UNIT-03:' \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md
# Pending Verification의 UNIT-02 항목 부재 확인
git diff --check
git diff --name-only -- app scripts db requirements.txt
git diff --name-only -- k8s
git diff --stat
git diff --name-only
git status --short
```

Result:

```text
Monitoring YAML parse: 2 passed
Alertmanager final render assertions: OK
Local Markdown links and fences: OK
Target whitespace: OK
Target credential value scan: OK
Task UNIT-02 checkbox: checked
Task UNIT-03 checkbox: unchecked
UNIT-02 Status: passed: found
Pending Verification UNIT-02 entry: absent
git diff --check: no output
Application/Pipeline/DB/dependency scope diff: no output
Kubernetes scope diff: k8s/monitoring/kube-prometheus-stack-values.yaml only
```

Status: passed

Notes:

- tracked `docs/ARCHITECTURE.md`와 `docs/tasks/main.md` 변경 및 다른 untracked workflow
  초안은 UNIT-02 시작 전부터 존재했고 이 UNIT에서 수정하지 않았다.
- UNIT-03 이후 artifact를 구현하거나 완료 처리하지 않았다.

### UNIT-02 final render 축약 assertion 재실행

이 section의 `url_file` 결과는 최초 설계의 historical evidence이며 현재
configuration을 나타내지 않는다.

Command:

```bash
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml | \
ruby -ryaml -rbase64 -e '<condensed render assertions>'
git diff --check
```

Result:

```text
First attempt: NoMethodError for Array#filter_map
Corrected select/map attempt: Alertmanager compatibility render assertion: OK
git diff --check: no output
```

Status: passed

Notes:

- 첫 축약 assertion은 local Ruby version이 `filter_map`을 지원하지 않아 검사
  harness에서 실패했다. values render나 Alertmanager configuration 실패가 아니다.
- 같은 receiver 추출을 호환되는 `select`와 `map`으로 바꿔 Secret mount, root route,
  child route 수, `send_resolved`, `url_file`과 literal `url` 부재를 재검사해 통과했다.

### UNIT-03 Alert artifact와 정적 계약 검증

Command:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

rules_dir = Path("k8s/monitoring/rules")
paths = [
    rules_dir / "kustomization.yaml",
    rules_dir / "news-lab-pipeline-alerts.yaml",
    rules_dir / "news-lab-alert-delivery-test.yaml",
]
docs = {}
for path in paths:
    with path.open(encoding="utf-8") as stream:
        docs[path.name] = yaml.safe_load(stream)
    print(f"YAML OK: {path}")

kustomization = docs["kustomization.yaml"]
assert kustomization["resources"] == ["news-lab-pipeline-alerts.yaml"]
actual = docs["news-lab-pipeline-alerts.yaml"]
assert actual["metadata"]["namespace"] == "monitoring"
assert actual["metadata"]["labels"] == {"release": "monitoring"}
rules = actual["spec"]["groups"][0]["rules"]
assert [rule["alert"] for rule in rules] == [
    "PipelineScheduleDelayed",
    "PipelineScheduledJobFailed",
    "NewsLabNodeNotReady",
]
assert all(rule["labels"]["alert_scope"] == "news-lab" for rule in rules)

schedule, failed, node = rules
assert schedule["for"] == "30m"
assert "> 26 * 60 * 60" in schedule["expr"]
assert "> 8 * 24 * 60 * 60" in schedule["expr"]
assert '"cadence", "daily"' in schedule["expr"]
assert '"cadence", "weekly"' in schedule["expr"]
assert failed["for"] == "10m"
assert failed["labels"]["severity"] == "warning"
assert "-[0-9]+" in failed["expr"]
assert "group_left (owner_name)" in failed["expr"]
assert 'owner_kind="CronJob"' in failed["expr"]
assert "prewarm" not in failed["expr"]
assert node["for"] == "10m"
assert node["labels"]["severity"] == "critical"
for name in ("arm-master-node", "arm-worker-node", "pi-worker-node"):
    assert name in node["expr"]
assert 'condition="Ready"' in node["expr"]
assert 'status="true"' in node["expr"]
assert "== 0" in node["expr"]

test_rule = docs["news-lab-alert-delivery-test.yaml"]
assert test_rule["metadata"]["labels"] == {"release": "monitoring"}
test_alert = test_rule["spec"]["groups"][0]["rules"][0]
assert test_alert["alert"] == "NewsLabAlertDeliveryTest"
assert test_alert["expr"] == "vector(1)"
assert test_alert["for"] == "1m"
assert test_alert["labels"]["alert_scope"] == "news-lab"
print("UNIT-03 rule contract assertions: OK")
PY

ruby -e '
files = %w[docs/design/pipeline-operations-alerting.md docs/runbooks/monitoring.md]
files.each do |file|
  File.read(file).scan(/\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)/).flatten.each do |target|
    next if target.match?(%r{\Ahttps?://})
    path = File.expand_path(target, File.dirname(file))
    abort "missing link target: #{file} -> #{target}" unless File.exist?(path)
  end
end
puts "Local Markdown links: OK"
'
if rg -n '[[:blank:]]+$' k8s/monitoring/rules \
  docs/design/pipeline-operations-alerting.md \
  docs/runbooks/monitoring.md \
  docs/tasks/feat-pipeline-operations-alerting.md; then
  exit 1
else
  echo 'UNIT-03 target whitespace: OK'
fi
for file in \
  docs/design/pipeline-operations-alerting.md \
  docs/runbooks/monitoring.md \
  docs/tasks/feat-pipeline-operations-alerting.md; do
  count=$(rg -c '^```' "$file" || true)
  if (( count % 2 != 0 )); then
    echo "odd fence count: $file"
    exit 1
  fi
done
echo 'Markdown fences: OK'
git diff --check
git diff --name-only -- app scripts db requirements.txt
git status --short
```

Result:

```text
YAML OK: k8s/monitoring/rules/kustomization.yaml
YAML OK: k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
YAML OK: k8s/monitoring/rules/news-lab-alert-delivery-test.yaml
UNIT-03 rule contract assertions: OK
Local Markdown links: OK
UNIT-03 target whitespace: OK
Markdown fences: OK
git diff --check: no output
FastAPI/Pipeline/DB/dependency diff: no output
```

Status: passed

Notes:

- `PipelineScheduleDelayed` 한 Alert 안에서 Daily `26h`와 Weekly `8d` threshold를
  분리했고 결과에 `cadence` label을 추가했다.
- 정기 Job 실패는 숫자 suffix와 CronJob owner join을 모두 요구하므로 prewarm
  Job이 제외된다. Node Alert는 지정된 세 Node만 대상으로 한다.
- test rule은 `vector(1)` 기반 별도 artifact이며 정상 운영 Kustomization에서
  제외했다.
- `promtool`, `kubectl kustomize`, Helm render와 전체 pytest는 UNIT-04 검증
  범위이므로 실행하지 않았다. Production 적용과 전달 테스트도 수행하지 않았다.

### UNIT-03 final checklist와 scope 정합성 검증

Command:

```bash
# Python assertion으로 다음 상태를 확인
# - Verification에 UNIT-03 Status: passed 존재
# - Pending Verification에 UNIT-03 부재, UNIT-04 존재
# - Task의 UNIT-03 checked, UNIT-04 unchecked

python3 - <<'PY'
from pathlib import Path
import yaml

for path in Path("k8s/monitoring").rglob("*.yaml"):
    with path.open(encoding="utf-8") as stream:
        list(yaml.safe_load_all(stream))
    print(f"OK {path}")
PY

# UNIT-03 대상의 credential value pattern과 trailing whitespace 부재 확인
git diff --check
git diff --name-only -- app scripts db requirements.txt
git diff --stat
git diff --name-only
git status --short
```

Result:

```text
UNIT-03 checklist and Verification state: OK
Monitoring YAML parse: 5 passed
UNIT-03 credential value scan: OK
UNIT-03 final whitespace: OK
git diff --check: no output
FastAPI/Pipeline/DB/dependency diff: no output
Tracked diff includes pre-existing UNIT-01/02 and workflow changes.
Untracked UNIT-03 artifact: k8s/monitoring/rules/
```

Status: passed

Notes:

- `git diff --stat`와 `git diff --name-only`는 untracked 파일을 표시하지 않으므로
  `git status --short`로 rule 디렉터리와 workflow artifact를 함께 확인했다.
- `docs/ARCHITECTURE.md`, `docs/tasks/main.md`, Alertmanager values 및 다른 untracked
  workflow 초안은 UNIT-03 시작 전 변경을 보존했다.
- UNIT-03은 기존 Alertmanager values를 수정하지 않았고 application, Pipeline,
  DB, CronJob, Dashboard JSON과 dependency 변경도 없었다.

### UNIT-04 YAML과 Kustomize render 검증

Command:

```bash
python3 - <<'PY'
"""Monitoring YAML 전체가 안전하게 역직렬화되는지 확인한다."""
from pathlib import Path

import yaml

for path in Path("k8s/monitoring").rglob("*.yaml"):
    with path.open(encoding="utf-8") as stream:
        list(yaml.safe_load_all(stream))
    print(f"OK {path}")
PY

kubectl kustomize k8s/monitoring/rules \
  > /tmp/news-lab-rules-rendered.yaml

ruby -ryaml -e '<Kustomize resource, Alert 3종과 test rule 제외 assertion>'
```

Result:

```text
Monitoring YAML parse: 5 passed
Kustomize resource count: 1
Rendered Alert:
  PipelineScheduleDelayed
  PipelineScheduledJobFailed
  NewsLabNodeNotReady
NewsLabAlertDeliveryTest in default render: absent
Kustomize render assertions: OK
```

Status: passed

Notes:

- 별도 전달 test rule은 기본 Kustomization에 포함되지 않은 상태를 유지했다.
- `/tmp` render artifact만 생성했으며 Production object를 조회하거나 변경하지
  않았다.

### UNIT-04 Helm chart `86.2.0` render 검증

이 section은 receiver 변경 전 Helm render의 historical evidence다. 현재 Telegram
render 결과는 뒤의 receiver 변경 검증을 source of truth로 사용한다.

Command:

```bash
helm template monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/monitoring-rendered.yaml

ruby -ryaml -rbase64 -e '<Alertmanager와 Prometheus render assertion>'
```

Result:

```text
Helm 86.2.0 render assertions: OK
Rendered resources: 121
Alertmanager count: 1
Chart PrometheusRule count: 35
External webhook receiver count: 1
```

Status: passed

Notes:

- assertion은 Alertmanager Secret mount, matcher 없는 root sink,
  `alert_scope="news-lab"` child route 한 개, 외부 receiver 한 개,
  `send_resolved: true`, `url_file`, literal `url` 부재와 Prometheus API v2 endpoint를
  확인했다.
- chart-managed configuration Secret의 placeholder configuration만 local render에서
  decode했다. 실제 credential이나 endpoint 값은 존재하지 않았고 Production
  Secret은 조회하지 않았다.

### UNIT-04 PrometheusRule `promtool` 과거 Agent 환경 시도

Command:

```bash
command -v promtool
promtool check rules \
  k8s/monitoring/rules/news-lab-pipeline-alerts.yaml

docker image inspect quay.io/prometheus/prometheus:v3.12.0-distroless
docker info --format '{{.ServerVersion}}'

find /opt/homebrew /usr/local /Users/seochanjin/.cache \
  /Users/seochanjin/Library/Caches -type f -name promtool
```

Result:

```text
promtool: command not found, exit 127
Docker daemon: permission denied while connecting to the Docker API socket
Local promtool search result: none
Alternative container runtime: none
```

Status: failed

Notes:

- Task가 허용한 chart image 또는 임시 container fallback도 현재 sandbox에서 Docker
  daemon socket에 접근할 수 없어 실행하지 못했다.
- Production workload를 이용한 우회 검증이나 package 설치는 수행하지 않았다.
- 이 시점에는 `promtool check rules`를 실행할 수 없어 UNIT-04를 환경 제약
  blocker로 유지했다. 이후 사람이 수행한 최종 성공 검증은 다음 section에
  기록한다.

### UNIT-04 PrometheusRule `promtool` 최종 검증

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get statefulset \
  prometheus-monitoring-kube-prometheus-prometheus \
  -n monitoring \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="prometheus")].image}{"\n"}'

docker run --rm \
  --entrypoint /bin/promtool \
  -v /private/tmp/news-lab-pipeline-alerts.rules.yaml:/rules/pipeline.rules.yaml:ro \
  -v /private/tmp/news-lab-alert-delivery-test.rules.yaml:/rules/delivery-test.rules.yaml:ro \
  quay.io/prometheus/prometheus:v3.12.0-distroless \
  check rules \
  --lint=all \
  --lint-fatal \
  /rules/pipeline.rules.yaml \
  /rules/delivery-test.rules.yaml
```

Result:

```text
Production Prometheus image:
  quay.io/prometheus/prometheus:v3.12.0-distroless

Generated temporary rule files from each PrometheusRule CR spec.groups:
  /tmp/news-lab-pipeline-alerts.rules.yaml
  /tmp/news-lab-alert-delivery-test.rules.yaml

Checking /rules/pipeline.rules.yaml
  SUCCESS: 3 rules found

Checking /rules/delivery-test.rules.yaml
  SUCCESS: 1 rules found

Exit code: 0
```

Status: passed

Notes:

- 2026-07-18에 사람이 Production Prometheus 이미지를 read-only로 확인하고,
  Repository의 두 `PrometheusRule` CR에서 `spec.groups`를 임시 rule 파일로 추출해
  검증한 sanitized evidence다.
- 운영 Alert 3종과 전달 test Alert 1종은 Prometheus `v3.12.0` 기준으로 문법,
  PromQL parse, rule format와 fatal lint error가 없음을 확인했다.
- 임시 파일만 생성했으며 원본 Repository 파일, Production object, Helm release와
  Secret은 변경하지 않았다. Production 적용과 Alert 전달 검증도 수행하지 않았다.

### UNIT-04 전체 pytest와 scope 회귀

Command:

```bash
PYTHONPATH=. pytest -q
git diff --check
git diff --name-only -- app scripts db requirements.txt
git diff --name-only -- k8s
git diff --stat
git diff --name-only
git status --short
```

Result:

```text
445 passed, 91 subtests passed in 15.12s
git diff --check: no output
FastAPI/Pipeline/DB/dependency diff: no output
Kubernetes tracked diff:
  k8s/monitoring/kube-prometheus-stack-values.yaml
Untracked Kubernetes artifact:
  k8s/monitoring/rules/
```

Status: passed

Notes:

- 기존 dirty working tree를 보존했고 UNIT-04에서는 manifest나 Python 구현을
  변경하지 않았다.
- `docs/ARCHITECTURE.md`, `docs/tasks/main.md`, Alertmanager values와 UNIT-01~03
  workflow artifact는 UNIT-04 시작 전에 존재한 변경이다.
- CronJob, Dashboard JSON, application, Pipeline, DB와 dependency 변경은 없다.

### UNIT-04 checklist와 Verification 정합성 검증

Command:

```bash
# Python assertion으로 다음 상태를 확인
# - 성공한 Kustomize, Helm, pytest와 diff criteria는 checked
# - 이 검증 시점에는 promtool criterion과 UNIT-04가 unchecked
# - 이 검증 시점에는 Verification의 UNIT-04가 blocked이고 UNIT-05 Status는 없음

# Task와 Verification의 Markdown fence 및 trailing whitespace 확인
git diff --check
git diff --name-only -- app scripts db requirements.txt
git status --short
```

Result:

```text
UNIT-04 checklist and Verification state: OK
Markdown fences: OK
UNIT-04 documentation whitespace: OK
git diff --check: no output
FastAPI/Pipeline/DB/dependency diff: no output
```

Status: passed

Notes:

- 성공한 개별 acceptance criteria만 완료 처리했다.
- 이 검증 시점에는 `promtool` 환경 제약으로 UNIT-04 checklist를 미완료 상태로
  유지했다. 이후 사람의 최종 성공 검증으로 blocker를 해소했다.
- 후속 UNIT을 구현하거나 완료 처리하지 않았다.

### UNIT-04 최종 문서 정합성 검증

Command:

```bash
# Task와 Verification의 Markdown fence 짝 확인
# Task와 Verification의 trailing whitespace 확인
# Task와 Verification의 credential value pattern 부재 확인
git diff --check
git status --short
```

Result:

```text
Markdown fences: OK
Target trailing whitespace: OK
Credential value scan: OK
git diff --check: OK
git status --short: 기존 task 범위의 tracked/untracked 변경 표시
```

Status: passed

Notes:

- 문서만 갱신했으며 구현 manifest, Alert expression, Alertmanager values와 test
  artifact는 수정하지 않았다.
- UNIT-05 Production 적용 및 전달 검증은 시작하지 않았다.

### UNIT-05 Production 적용 전 read-only 상태 재조회

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get alertmanager,pods -n monitoring

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheusrules -A -L release

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheus -n monitoring \
  -o jsonpath='{range .items[*]}name={.metadata.name}{"\n"}ruleSelector={.spec.ruleSelector}{"\n"}ruleNamespaceSelector={.spec.ruleNamespaceSelector}{"\n"}alertingEndpoints={range .spec.alerting.alertmanagers[*]}{.namespace}/{.name}:{.port}{" "}{end}{"\n"}{end}'
```

Result:

```text
Unable to connect to the server: dial tcp 127.0.0.1:6443:
connect: operation not permitted
```

Status: failed

Notes:

- 세 read-only 조회가 모두 같은 local Kubernetes API tunnel 접근 제한으로
  실패했다.
- 이 결과를 Production object의 부재나 적용 실패로 해석하지 않았다.
- Secret 조회·변경, Helm upgrade, `kubectl apply/patch/delete/rollout`과 test
  alert 전달은 수행하지 않았다.
- 이 시점에는 사람이 수행한 Secret 구성·적용과 sanitized firing·resolved evidence가
  없어 UNIT-05를 `human-required`로 유지했다. 이후 성공 evidence는 아래에 기록했다.

### Production 적용 중단 후 native Telegram receiver 변경 검증

Command:

```bash
ruby -ryaml -e '<Monitoring YAML parse>'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/monitoring-telegram-rendered.yaml

ruby -ryaml -rbase64 -e '<Alertmanager Telegram render assertions>'

docker run --rm \
  --entrypoint /bin/amtool \
  -v /private/tmp/news-lab-alertmanager-telegram.yaml:/config/alertmanager.yaml:ro \
  quay.io/prometheus/alertmanager:v0.32.2 \
  check-config /config/alertmanager.yaml

# local Markdown link와 fence, trailing whitespace 확인
# credential value와 active values/design/runbook/task/PR/devlog의 폐기 receiver 참조 부재 확인
git diff --check
git diff --name-only -- app scripts db requirements.txt k8s/monitoring/rules
git status --short
```

Result:

```text
Monitoring YAML parse: 5 passed
Helm 86.2.0 Telegram render assertions: OK
Rendered resources: 121
Alertmanager Secret mount: news-lab-alertmanager-telegram
Root route: matcher-free null receiver
NewsLab child route count: 1
Native Telegram receiver count: 1
Telegram parse mode: HTML
webhook configuration: absent
Literal bot token/chat ID: absent
amtool v0.32.2 check-config: SUCCESS
Local Markdown links: OK
Markdown fences: OK
Target trailing whitespace: OK
Credential value scan: OK
Active implementation/docs legacy receiver references: absent
git diff --check: OK
FastAPI/Pipeline/DB/dependency/rule tracked diff: no output
```

Status: passed

Notes:

- system Python의 PyYAML import는 `ModuleNotFoundError`로 실패해 같은 대상 5개를
  Ruby YAML parser로 재검증했고 모두 통과했다.
- sandbox의 Docker socket 접근은 거부됐지만 승인된 Docker 실행으로 Alertmanager
  `v0.32.2` 이미지를 받아 렌더된 configuration의 `amtool check-config`를 통과했다.
- render assertion은 `news-lab-alertmanager-telegram` Secret mount, matcher 없는
  root `null` route, NewsLab child route 한 개, native Telegram receiver 한 개,
  `send_resolved: true`, 두 file path, `parse_mode: HTML`, webhook configuration과
  literal credential 부재를 확인했다.
- Alert rule과 test Alert artifact는 수정하지 않았으므로 이전 `promtool` 성공
  evidence를 유지하고 재실행하지 않았다. Monitoring values와 문서만 바뀌어 전체
  pytest도 재실행하지 않았다.
- 이 local 검증에서 Agent는 Production Secret 생성, Helm upgrade, Kubernetes
  object 변경과 실제 Telegram 전송을 수행하지 않았다. 당시 UNIT-05는 미완료였고,
  이후 사람이 완료했다.

### UNIT-05 human-operated Production 적용과 Telegram 전달 검증

Command:

```text
Human operator가 승인된 운영 절차로 다음을 수행했다.
- monitoring Helm release를 --wait --timeout 10m 조건으로 upgrade
- 실제 NewsLab PrometheusRule 적용
- 별도 전달 test PrometheusRule 적용과 firing 확인
- test expression을 vector(0) > 0으로 변경해 resolved 확인
- test PrometheusRule 삭제
- Kubernetes와 Prometheus API 및 관련 log를 read-only로 확인

Agent는 위 Production command를 재실행하지 않았다.
```

Result:

```text
Helm release: monitoring
Namespace: monitoring
Chart: kube-prometheus-stack-86.2.0
App version: v0.91.0
Revision: 3 -> 4
Revision 4 status: deployed
helm upgrade --wait --timeout 10m: success

Alertmanager CR: monitoring-kube-prometheus-alertmanager
Alertmanager version: v0.32.2
replicas/ready: 1/1
reconciled: True
available: True
paused: false
Pod: 2/2 Running, restart 0
StatefulSet rollout: complete
Service: created

Prometheus Alertmanager endpoint:
  monitoring/monitoring-kube-prometheus-alertmanager:http-web
Alertmanager API version: v2

PrometheusRule: monitoring/news-lab-pipeline-alerts
Label: release=monitoring
PipelineScheduleDelayed: health=ok, state=inactive, lastError 없음
PipelineScheduledJobFailed: health=ok, state=inactive, lastError 없음
NewsLabNodeNotReady: health=ok, state=inactive, lastError 없음

Temporary PrometheusRule: news-lab-alert-delivery-test
NewsLabAlertDeliveryTest firing: Prometheus API에서 확인
Telegram firing message: received
Resolved expression: vector(0) > 0
Resolved state: health=ok, state=inactive
Telegram resolved message: received
Test PrometheusRule deletion: complete
Kubernetes API after deletion: NotFound
Prometheus Rules API after deletion: absent
Final custom Production rule: news-lab-pipeline-alerts only

Alertmanager recent log telegram/notify/error/fail search: no output
Prometheus configuration reload INFO: confirmed
NewsLab Rule parse/load/evaluation/Alertmanager delivery error: none
```

Status: passed

Notes:

- 이 section은 사람이 제공한 sanitized Production evidence를 그대로 요약했다.
  Secret 값, Telegram bot token과 chat ID는 제공받거나 기록하지 않았다.
- `vector(0)`은 값 0인 시계열을 반환하므로 Alert를 resolved로 만들지 못한다.
  실제 resolved 전환에는 빈 벡터를 반환하는 `vector(0) > 0`을 사용했다.
- Alertmanager log 검색 결과만으로 성공을 판정하지 않고 실제 Telegram firing과
  resolved 메시지 수신을 전달 성공 evidence로 사용했다.

### UNIT-05 비차단 관찰: chart 기본 burnrate Rule evaluation timeout

Command:

```text
Human operator가 최근 2시간의 Prometheus log와 Rules API를 read-only로 확인했다.
Agent는 Production 조회나 설정 변경을 수행하지 않았다.
```

Result:

```text
Observed group: kube-apiserver-burnrate.rules
Intermittent timeout observations:
  apiserver_request:burnrate1d read
  apiserver_request:burnrate3d read
  apiserver_request:burnrate1d write
Error forms:
  query timed out in expression evaluation
  expanding series: context deadline exceeded

Current apiserver_request:burnrate3d read:
  health=ok, lastError 없음, evaluationTime 약 71.45초
Current apiserver_request:burnrate3d write:
  health=ok, lastError 없음, evaluationTime 약 38.01초
Previous evaluation times observed: 약 119.33초, 약 55.18초
```

Status: passed

Notes:

- 이 timeout은 NewsLab Alert 3종의 health나 Telegram 전달 실패가 아니므로 UNIT-05
  완료를 막지 않는 운영 관찰로 분류한다.
- 현재 관찰 대상 Rule은 `health=ok`이고 `lastError`가 비어 있다. 정확한 원인은
  이번 작업에서 확정하지 않았다.
- 후속 운영 개선에서는 retention, query timeout, Rule 평가 시간과 Prometheus
  CPU·메모리·스토리지 상태를 함께 조사할 수 있다.
- 76차에서는 기존 chart 기본 Rule의 timeout 설정, 활성 상태, Prometheus resource,
  retention과 storage를 변경하지 않았다.

### UNIT-06 최종 local render와 regression 검증

Command:

```bash
ruby -ryaml -e '<Monitoring YAML parse>'
kubectl kustomize k8s/monitoring/rules \
  > /tmp/news-lab-rules-final.yaml
ruby -ryaml -e '<실제 Alert 3종과 test Alert 제외 assertion>'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/monitoring-final-rendered.yaml
ruby -ryaml -rbase64 -e '<native Telegram render assertions>'

docker run --rm \
  --entrypoint /bin/amtool \
  -v /private/tmp/news-lab-alertmanager-final.yaml:/config/alertmanager.yaml:ro \
  quay.io/prometheus/alertmanager:v0.32.2 \
  check-config /config/alertmanager.yaml

PYTHONPATH=. pytest -q
```

Result:

```text
Monitoring YAML parse: 5 passed
Kustomize resources: 1
Production alerts:
  PipelineScheduleDelayed
  PipelineScheduledJobFailed
  NewsLabNodeNotReady
NewsLabAlertDeliveryTest: absent
Helm 86.2.0 render assertions: OK
Alertmanager native Telegram configuration: OK
Literal Telegram credentials: absent
amtool v0.32.2 check-config: SUCCESS
pytest: 445 passed, 91 subtests passed in 14.64s
```

Status: passed

Notes:

- test manifest의 기본 expression은 firing 검증용 `vector(1)`을 유지하고 기본
  Kustomization에서는 제외된다.
- Production command, Secret 조회·변경과 chart 기본 Rule 설정 변경은 수행하지
  않았다.

### UNIT-06 최종 문서·scope 정합성 검증

Command:

```bash
# Architecture/Runbook index와 76차 문서의 local Markdown link 및 fence 확인
# 76차 values, rule과 문서의 trailing whitespace 확인
# Secret, Telegram credential과 private key value pattern 부재 확인
# Task checklist, Verification Status, UNIT-05/06과 Pending Verification 확인

rg -n 'vector\(0\)|vector\(1\)' \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/verification/feat-pipeline-operations-alerting.md \
  docs/runbooks/monitoring.md \
  docs/design/pipeline-operations-alerting.md \
  k8s/monitoring/rules/news-lab-alert-delivery-test.yaml

git diff --check
git diff --name-only -- app scripts db requirements.txt
git status --short
```

Result:

```text
Local Markdown links and fences: OK
Target trailing whitespace: OK
Credential value scan: OK
Task and Verification final state: OK
Resolved procedure: vector(0) > 0 only
Test manifest expression: vector(1)
git diff --check: OK
FastAPI/Pipeline/DB/dependency tracked diff: none
git status --short: 기존 76차 tracked/untracked 변경 표시
```

Status: passed

Notes:

- `vector(0)`은 잘못된 사용을 경고하는 설명에만 남아 있고, resolved 절차는 모두
  `vector(0) > 0`이다.
- Secret resource·key 이름과 file path만 기록했으며 실제 값은 기록하지 않았다.
- Alert Rule, chart 기본 Rule, application, Pipeline, DB와 dependency는 UNIT-06에서
  수정하지 않았다.

### Approved FIX-01 Task fence 검증

Command:

```bash
rg -n '^```$' docs/tasks/feat-pipeline-operations-alerting.md
npx --yes markdownlint-cli2 \
  docs/tasks/feat-pipeline-operations-alerting.md
```

Result:

```text
rg: closing fence 8개 출력
markdownlint-cli2: MD040 없음
markdownlint-cli2: 기존 MD013 line-length 6건만 출력, exit 1
```

Status: passed

Notes:

- 전달 경로와 Expected files의 두 opening fence에 `text` identifier를 추가했다.
- 승인 문서의 `rg '^```$'` 명령은 opening fence뿐 아니라 정상적인 closing
  fence도 찾으므로 출력 없음 조건을 완료 판정으로 사용하지 않았다.
- FIX-01 범위인 `MD040`은 해소됐다. 승인되지 않은 기존 `MD013` 6건은 수정하지
  않았다.

### Approved FIX-02 두 PrometheusRule artifact 검증

Command:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

sources = {
    Path('k8s/monitoring/rules/news-lab-pipeline-alerts.yaml'):
        Path('/tmp/news-lab-pipeline-alerts.rules.yaml'),
    Path('k8s/monitoring/rules/news-lab-alert-delivery-test.yaml'):
        Path('/tmp/news-lab-alert-delivery-test.rules.yaml'),
}

for source, target in sources.items():
    with source.open(encoding='utf-8') as stream:
        manifest = yaml.safe_load(stream)
    with target.open('w', encoding='utf-8') as stream:
        yaml.safe_dump(
            {'groups': manifest['spec']['groups']},
            stream,
            sort_keys=False,
            allow_unicode=True,
        )
    print(target)
PY

.venv/bin/python - <<'PY'
from pathlib import Path
import yaml

sources = {
    Path('k8s/monitoring/rules/news-lab-pipeline-alerts.yaml'):
        Path('/tmp/news-lab-pipeline-alerts.rules.yaml'),
    Path('k8s/monitoring/rules/news-lab-alert-delivery-test.yaml'):
        Path('/tmp/news-lab-alert-delivery-test.rules.yaml'),
}

for source, target in sources.items():
    with source.open(encoding='utf-8') as stream:
        manifest = yaml.safe_load(stream)
    with target.open('w', encoding='utf-8') as stream:
        yaml.safe_dump(
            {'groups': manifest['spec']['groups']},
            stream,
            sort_keys=False,
            allow_unicode=True,
        )
    print(target)
PY

docker run --rm \
  --entrypoint /bin/promtool \
  -v /tmp/news-lab-pipeline-alerts.rules.yaml:/rules/pipeline.rules.yaml:ro \
  -v /tmp/news-lab-alert-delivery-test.rules.yaml:/rules/delivery-test.rules.yaml:ro \
  quay.io/prometheus/prometheus:v3.12.0-distroless \
  check rules \
  --lint=all \
  --lint-fatal \
  /rules/pipeline.rules.yaml \
  /rules/delivery-test.rules.yaml

kubectl kustomize k8s/monitoring/rules |
rg 'alert:|NewsLabAlertDeliveryTest'

rg -n 'expr: vector\(1\)' \
  k8s/monitoring/rules/news-lab-alert-delivery-test.yaml

git diff --name-only -- k8s/monitoring/rules

rm -f \
  /tmp/news-lab-pipeline-alerts.rules.yaml \
  /tmp/news-lab-alert-delivery-test.rules.yaml
```

Result:

```text
system python3 extraction: ModuleNotFoundError: No module named 'yaml'
.venv/bin/python extraction: 2 temporary native rule files generated
Checking /rules/pipeline.rules.yaml
  SUCCESS: 3 rules found
Checking /rules/delivery-test.rules.yaml
  SUCCESS: 1 rules found
Kustomize alerts: PipelineScheduleDelayed, PipelineScheduledJobFailed,
  NewsLabNodeNotReady
NewsLabAlertDeliveryTest in Kustomize: absent
test manifest expression: vector(1)
k8s/monitoring/rules tracked diff: none
temporary native rule files: removed
```

Status: passed

Notes:

- 시스템 `python3`에는 PyYAML이 없어 첫 추출이 실패했으며, 같은 script를
  Repository `.venv` Python으로 재실행해 검증을 완료했다.
- Production workload와 Alert Rule manifest는 변경하지 않았다.

### Approved FIX-03 Review와 Approved Fixes artifact 검증

Command:

```bash
npx --yes markdownlint-cli2 \
  docs/reviews/feat-pipeline-operations-alerting-coderabbit.md \
  docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md
```

Result:

```text
MD040: 없음
기존 MD013 line-length: 26건
exit code: 1
```

Status: passed

Notes:

- 실제 CodeRabbit 결과, 승인·거절 결정, 적용 변경과 검증 절차를 지정 section에
  기록했다.
- 새 artifact의 모든 fenced code block에 language identifier가 있다.
- FIX-03 범위인 artifact 작성과 `MD040` 검증은 완료됐다. 승인되지 않은 기존
  `MD013` line-length는 수정하지 않았다.

### Approved FIX-04 PR review 상태 정합성 검증

Command:

```bash
rg -n \
  'CodeRabbit|finding|Production 재적용|thread|승인된 finding 없음' \
  docs/pr/feat-pipeline-operations-alerting.md

npx --yes markdownlint-cli2 \
  docs/pr/feat-pipeline-operations-alerting.md
```

Result:

```text
CodeRabbit minor actionable finding 2개 승인·반영 문구: present
승인된 finding 없음 문구: absent
문서-only 변경과 Production 재적용·재검증 미수행 문구: present
inline thread 후속 확인 문구: present
markdownlint-cli2: 0 issues
```

Status: passed

Notes:

- Alertmanager·Rule·Telegram 구현 변경이나 Production 완료를 새로 주장하지
  않았다.
- Review artifact는 Verification 통과 근거로 사용하지 않았다.

### Approved Fixes 최종 회귀와 scope 검증

Command:

```bash
PYTHONPATH=. pytest -q

npx --yes markdownlint-cli2 \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/reviews/feat-pipeline-operations-alerting-coderabbit.md \
  docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md

kubectl kustomize k8s/monitoring/rules |
rg 'alert:|NewsLabAlertDeliveryTest'

git diff --name-only
git diff --name-only -- \
  k8s/monitoring/kube-prometheus-stack-values.yaml \
  k8s/monitoring/rules app scripts db requirements.txt
git diff --check

# 승인 문서 5개의 trailing whitespace와 fence pairing 확인
# git diff의 Telegram token, private key와 literal chat ID pattern 확인
git status --short --branch
```

Result:

```text
pytest: 445 passed, 91 subtests passed in 14.87s
markdownlint-cli2: MD040 없음, 기존 MD013 32건, exit 1
Kustomize alerts: 실제 Alert 3종만 포함, NewsLabAlertDeliveryTest 없음
changed files: 승인된 문서와 Verification 기록 5개
runtime/Alert Rule scope tracked diff: none
git diff --check: OK
trailing whitespace: none
Markdown fences: paired
credential value pattern: none
branch: feat/pipeline-operations-alerting
```

Status: passed

Notes:

- Markdown lint의 exit 1은 승인 범위 밖 기존 `MD013` line-length 32건 때문이다.
  이번 승인 finding인 `MD040`은 세 대상 문서 모두 해소됐다.
- CodeRabbit inline thread 확인·resolve는 commit 이후 작업이라 실행하지 않았다.
- Production command, Secret 조회·변경, commit, push와 merge는 수행하지 않았다.

## Results

- UNIT-01 조사 시점 Repository values에서 Alertmanager는 비활성이고, 당시 render에는
  `Alertmanager` CR과 Prometheus `alerting` 설정이 없다.
- Prometheus는 `release=monitoring` rule을 모든 namespace에서 탐색하도록
  render된다.
- chart `86.2.0`의 Alertmanager 활성 render가 사용하는 CR, configuration Secret,
  key와 Prometheus endpoint 구조를 확인했다.
- UNIT-01 조사 시점 Repository에는 custom `PrometheusRule`, route·receiver와
  Alertmanager Secret artifact가 없었다.
- Production에는 Alertmanager CR·Pod, AlertmanagerConfig, Alertmanager endpoint와
  NewsLab custom `PrometheusRule`이 없고, Prometheus와 Operator Pod는 Running이다.
- Production의 기본 `PrometheusRule` 35개는 `monitoring` namespace와
  `release=monitoring` label을 사용하며, Prometheus selector는 Repository render와
  일치한다.
- Repository values에서 Alertmanager를 활성화했고, root sink 아래
  `alert_scope="news-lab"` route만 native Telegram receiver로 전달한다.
- Telegram receiver는 `monitoring/news-lab-alertmanager-telegram` Secret의
  `bot-token`, `chat-id` key를 file mount로 읽으며 실제 값이나 Secret manifest는
  Repository에 없다.
- Monitoring runbook에 사람이 수행할 Secret 준비·key 존재 확인·회전·전달 실패와
  rollback 경계를 기록했다.
- receiver의 `parse_mode`는 Alertmanager 기본 Telegram rendering과 같은 `HTML`을
  명시해 render에서 메시지 해석 방식이 고정되도록 했다.
- `release=monitoring`인 실제 `PrometheusRule`에 지연, 정기 Job 실패와 Node
  NotReady Alert를 구현했고 모두 `alert_scope=news-lab` route label을 사용한다.
- Daily/Weekly 지연 threshold를 분리하고 정기 Job 숫자 suffix filter, owner join,
  세 Node selector와 각 `for`·severity를 정적 검증했다.
- `vector(1)` 전달 test rule은 별도 파일로 제공하되 기본 Kustomization에서는
  제외해 사람의 명시적 적용 없이는 firing하지 않도록 했다.
- 사람이 Production과 동일한 Prometheus `v3.12.0`의 `promtool`을 사용해 운영
  Alert 3종과 전달 test Alert 1종을 `--lint=all --lint-fatal`로 검증했으며 exit
  code는 0이었다.
- 사람이 Monitoring Helm revision `4`, Alertmanager `v0.32.2`와 실제 NewsLab Rule
  3종을 Production에 반영했고 세 Rule의 `health=ok`, `state=inactive`, `lastError`
  없음을 확인했다.
- test Alert의 firing과 `vector(0) > 0` 전환 뒤 resolved Telegram 메시지를 실제
  수신했으며 test Rule 제거 후 실제 Rule 3종만 남았다.
- NewsLab Rule과 Telegram 전달 경로에서는 오류가 없었다. 기존 chart 기본
  `kube-apiserver-burnrate.rules`의 간헐적인 evaluation timeout은 별도 비차단
  관찰로 기록했다.
- 승인된 CodeRabbit minor finding 2개에 따라 Task fence와 promtool 절차를
  정정하고 Review·Approved Fixes·PR artifact를 실제 적용 상태로 갱신했다.
- 승인 fix 적용 후 전체 pytest와 문서·scope 검증을 다시 수행했으며 runtime과
  Alert Rule manifest는 변경하지 않았다.

UNIT-01 Status: passed

UNIT-02 Status: passed

UNIT-03 Status: passed

UNIT-04 Status: passed

UNIT-05 Status: passed

UNIT-06 Status: passed

## Manual or Production Verification

Status: passed

UNIT-01 Production read-only baseline은 사람이 제공한 sanitized evidence로
완료했다. UNIT-05 진입 시 Agent의 read-only 재조회는 local Kubernetes API tunnel
접근 제한으로 실패했지만, 이후 사람이 Production 적용과 firing·resolved 전달을
완료하고 sanitized evidence를 제공했다. Secret 값, bot token, chat ID, private
address와 kubeconfig 내용은 제공받거나 문서에 기록하지 않았다.

## Pending Verification

없음.

## Evidence Notes

- 이전 Dashboard Verification의 chart `86.2.0` Helm Revision 3 배포 기록은 과거
  evidence이며 현재 Alertmanager와 rule object 조회를 대체하지 않는다.
- Agent는 `kubectl apply/patch/delete/rollout`, Helm upgrade, Secret 조회·변경,
  git push와 merge를 실행하지 않았다.
- UNIT-03에서 FastAPI, Pipeline, DB, CronJob, Dashboard JSON, values와 dependency를
  수정하지 않았다.
- UNIT-04의 YAML, Kustomize, Helm, pytest와 최종 human-operated `promtool` 검증이
  모두 통과했다.
- UNIT-05의 Production read-only 재조회는 실행했으나 Agent 환경의 local API tunnel
  접근 제한으로 실패했다.
- UNIT-05의 Production 변경과 firing·resolved 전달 검증은 사람이 수행했고,
  sanitized 운영 evidence만 문서에 반영했다.
- generic webhook receiver는 Production 적용 전에 폐기했고 native Telegram
  receiver로 변경했다. 이 변경 자체를 UNIT-05 완료 evidence로 사용하지 않는다.
- Approved FIX-01~04는 모두 적용·검증했다. Markdown lint의 기존 `MD013`은 승인
  범위 밖이라 유지했고, CodeRabbit thread 확인·resolve는 commit 이후 후속으로
  남겼다.
