# Task: Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## Goal

75차에서 검증한 Production Prometheus metric과 PromQL을 기반으로 Alertmanager를 활성화하고, NewsLab 운영에 필요한 핵심 Alert 3종을 `PrometheusRule`로 구성한다.

최종 목표는 rule manifest를 추가하는 데서 끝나지 않고 다음 전달 경로를 Production에서 직접 검증하는 것이다.

```
PrometheusRule
→ Prometheus evaluation
→ Alertmanager route
→ receiver
→ 실제 firing 알림 수신
→ resolved 알림 수신
```

핵심 Alert 3종은 다음으로 고정한다.

1. Pipeline 정기 실행 지연
2. 정기 Job 실패
3. Node NotReady

## Scope

### Baseline 조사

- Repository의 현재 `kube-prometheus-stack` values 확인
- Production Alertmanager 활성 상태 확인
- 현재 `PrometheusRule` 목록과 rule selector 확인
- Prometheus가 감시하는 namespace와 label 확인
- Alertmanager route·receiver·Secret 관리 경로 확인
- chart `86.2.0` 기준 Alertmanager 설정 render 구조 확인

### Alertmanager 활성화

- 현재 비활성 상태라면 Repository values에서 Alertmanager 활성화
- receiver는 한 개만 구성
- route는 NewsLab Alert 전용 label 기준으로 최소 구성
- Alertmanager native `telegram_configs`로 Telegram 개인 채팅에 전달
- `bot_token_file`과 `chat_id_file`로 운영 Secret을 참조
- `send_resolved: true` 적용
- 실제 bot token과 chat ID는 Repository에 저장하지 않음
- 운영 Secret은 사람이 별도 관리

### 핵심 Alert 3종

#### 1. Pipeline 정기 실행 지연

- Daily 계열과 Weekly 계열의 실행 주기를 구분
- Daily 계열: RSS, Daily, 3-day Pipeline
- Weekly 계열: Weekly Pipeline
- 75차에서 확인한 `kube_cronjob_status_last_schedule_time` 기반 query 사용
- timezone과 CronJob schedule을 고려해 threshold와 `for` 근거 문서화

#### 2. 정기 Job 실패

- 숫자 suffix canonical filter를 사용해 prewarm Job 제외
- `kube_job_status_failed`와 필요한 owner join 사용
- 실패 Job object 보존 기간과 반복 알림 가능성 문서화

#### 3. Node NotReady

- `arm-master-node`, `arm-worker-node`, `pi-worker-node` 대상
- `kube_node_status_condition{condition="Ready",status="true"}` 기반으로 구성
- 일시적 상태 전환을 제외하도록 적절한 `for` 적용

### 전달 검증

- 실제 장애 유도 대신 임시 test alert 사용 가능
- test alert는 `vector(1)` 기반으로 별도 rule 또는 임시 manifest로 구성
- firing 알림 수신 확인
- resolved 알림 수신 확인
- test rule 제거 후 실제 3종 rule만 남김
- 실제 3종 rule이 현재 정상 상태에서 `inactive`인지 확인
- NewsLab Rule과 Telegram 전달 경로에 parse·evaluation·delivery error가 없는지 확인
- 기존 chart 기본 Rule 오류는 NewsLab 전달 결과와 분리해 비차단 관찰로 기록

### 문서화

- Alert 설계 문서
- Monitoring runbook
- Verification
- PR 문서
- Devlog
- Task checklist

## Do not change

- FastAPI application code
- Pipeline business logic
- `/metrics` endpoint 추가 또는 변경
- custom business metric 구현
- DB schema, migration, Supabase SQL과 운영 데이터
- Redis 설정과 Home Cache 동작
- CronJob schedule, timezone, command와 retry 정책
- Grafana Dashboard JSON과 기존 20개 panel query
- Grafana data proxy timeout과 resource 설정
- Prometheus retention `1d`
- Prometheus PVC, storageSpec, StorageClass와 장기 storage
- Prometheus `query.timeout`, max samples, query concurrency
- recording rule
- Alert 3종 외 추가 운영 Alert
- 여러 receiver 또는 여러 알림 채널
- Production 장애 주입
- Node drain, reboot, shutdown
- CronJob suspend
- 실패 Job 강제 생성
- Pod 강제 삭제
- Agent의 Production Secret 조회·디코딩·변경
- Agent의 `kubectl apply`, patch, delete, rollout
- Agent의 Helm upgrade, rollback
- Agent의 git push, PR merge

## Expected files

예상 변경 파일은 Repository 구조 조사 후 확정하되, 기본 후보는 다음과 같다.

```
k8s/monitoring/kube-prometheus-stack-values.yaml
k8s/monitoring/rules/kustomization.yaml
k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
k8s/monitoring/rules/news-lab-alert-delivery-test.yaml

docs/design/pipeline-operations-alerting.md
docs/runbooks/monitoring.md
docs/tasks/feat-pipeline-operations-alerting.md
docs/verification/feat-pipeline-operations-alerting.md
docs/pr/feat-pipeline-operations-alerting.md
docs/devlog/feat-pipeline-operations-alerting.md
docs/reviews/feat-pipeline-operations-alerting-antigravity.md
docs/reviews/feat-pipeline-operations-alerting-coderabbit.md
docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md
```

실제 Repository provisioning 방식이 다르면 새 범용 framework를 만들지 않고 기존 monitoring 구조에 맞는 최소 artifact만 추가한다.

Test alert 파일은 Production 전달 검증 후 제거할 수 있다. 최종 PR에 유지할지는 검증 및 review 결과에 따라 결정한다.

## DB changes

없음.

- schema 변경 없음
- migration 없음
- table, column, index와 constraint 변경 없음
- Production 데이터 변경 없음
- DB run status를 Alert source로 사용하지 않음

## API changes

없음.

- FastAPI endpoint 변경 없음
- request/response schema 변경 없음
- 인증·권한 정책 변경 없음
- `/metrics` endpoint 추가 없음
- application API를 Alert source로 사용하지 않음

## Test commands

Repository와 Production 구조 조사 후 명령은 실제 경로에 맞춰 조정한다.

### YAML 및 Kustomize

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

for path in Path('k8s/monitoring').rglob('*.yaml'):
    with path.open(encoding='utf-8') as f:
        list(yaml.safe_load_all(f))
    print(f'OK {path}')
PY

kubectl kustomize k8s/monitoring/rules
```

### PrometheusRule 정적 검증

```bash
promtool check rules \
  k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
```

`promtool` 사용 환경이 없으면 chart image 또는 임시 container를 사용하되 Production workload를 변경하지 않는다.

### Helm render

```bash
helm template monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/monitoring-rendered.yaml
```

Secret이 render 또는 diff에 노출되지 않도록 raw output 보관과 공유에 주의한다. 운영 dry-run은 사람이 다음 원칙으로 수행한다.

```bash
helm upgrade monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  --dry-run=server \
  --hide-secret
```

### 전체 회귀

```bash
PYTHONPATH=. pytest -q
git diff --check
git status --short
```

### Production read-only 검증

모든 cluster 명령은 다음 kubeconfig를 명시한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get prometheusrules -A

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get alertmanager,pods -n monitoring

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl logs -n monitoring \
  deploy/monitoring-kube-prometheus-operator \
  --since=30m
```

실제 resource 이름은 Production 조회 결과에 따라 수정한다.

## Acceptance criteria

- [x] Repository와 Production의 Alertmanager baseline을 조사하고 문서화
- [x] PrometheusRule selector, namespace와 required label 확인
- [x] Alertmanager 활성화 설정을 Repository에 반영
- [x] receiver 1개와 route 1개를 최소 구성
- [x] `send_resolved: true` 적용
- [x] 실제 bot token과 chat ID를 Repository와 문서에 기록하지 않음
- [x] Pipeline 정기 실행 지연 Alert 구현
- [x] 정기 Job 실패 Alert 구현
- [x] Node NotReady Alert 구현
- [x] 세 Alert의 threshold, `for`, severity 근거 문서화
- [x] prewarm Job이 정기 Job 실패 Alert에서 제외됨
- [x] Daily 계열과 Weekly 실행 지연 기준이 분리됨
- [x] `promtool check rules` 통과
- [x] Kustomize render 통과
- [x] Helm chart `86.2.0` render 통과
- [x] 전체 pytest 통과
- [x] `git diff --check` 출력 없음
- [x] 사람이 Production Secret을 구성
- [x] 사람이 Alertmanager와 PrometheusRule을 Production에 적용
- [x] Prometheus에서 rule group loaded 확인
- [x] 세 실제 Alert의 rule health 정상 확인
- [x] 현재 정상 상태에서 세 실제 Alert가 `inactive`임을 확인
- [x] test alert의 firing 알림 실제 수신
- [x] test alert 해제 후 resolved 알림 실제 수신
- [x] test rule 제거 또는 최종 상태 명시
- [x] NewsLab Rule과 Telegram 전달 경로에 parse·evaluation·delivery 오류 없음
- [x] Monitoring runbook에 수신 실패, silence와 Secret 관리 절차 반영
- [x] Verification Status를 실제 evidence에 따라 `passed`로 확정

## Notes

- 76차는 Alert rule과 실제 전달 검증을 한 차수에서 완료한다.
- 77차는 DB Backup/Restore 훈련으로 유지한다.
- custom business metric, retention/PVC, recording rule과 추가 Alert는 이번 프로젝트 종료 범위가 아니다.
- Kubernetes Job 성공은 업무 수준 `partial_success`를 설명하지 못한다. 해당 한계는 75차와 동일하게 유지한다.
- 실제 receiver는 native Telegram 한 개로 고정하며 webhook bridge를 사용하지 않는다.
- receiver 선택과 credential 준비가 완료되지 않으면 구현을 완료로 표시하지 않는다.
- 테스트는 실제 Node 중단이나 Production Pipeline 실패 유도가 아니라 임시 test alert로 수행한다.
- resolved 알림 수신까지 확인해야 전달 경로 검증을 완료한 것으로 본다.
- Agent는 Secret 값을 읽거나 출력하지 않는다.
- Production 변경과 장애 가능 작업은 사람이 diff를 검토한 뒤 수행한다.

## Manual or Production Verification

Status: `passed`

Implementation Unit의 Repository 구현과 로컬 검증이 끝난 뒤 사람이 승인하고 직접 수행한다.

- Production Alertmanager용 Telegram `bot-token`과 `chat-id` Secret 구성
- 실제 Secret 값이 shell history, 임시 파일, Git diff와 문서에 남지 않았는지 확인
- `--dry-run=server --hide-secret` 기반 Helm 변경 범위 검토
- Alertmanager 활성화와 route·receiver render 결과 확인
- Monitoring Helm release upgrade
- Alertmanager와 Prometheus rollout 및 Pod 상태 확인
- `PrometheusRule` 적용
- Prometheus Rules 화면 또는 API에서 rule group loaded 확인
- 세 실제 Alert의 rule health와 현재 `inactive` 상태 확인
- 임시 test alert를 사용한 firing 알림 실제 수신
- test alert expression을 `vector(0) > 0`으로 바꾼 뒤 resolved 알림 실제 수신
- test rule과 임시 artifact 제거
- NewsLab Rule과 Telegram 전달 경로의 parse, evaluation과 delivery 오류 없음 확인
- 기존 chart 기본 Rule 오류가 있으면 NewsLab 결과와 분리해 기록

사람이 제공한 sanitized 운영 결과만 Verification, PR과 Devlog에 기록한다. Agent는 Production Secret 조회·디코딩·변경, Helm upgrade, `kubectl apply/patch/delete/rollout`과 실제 전달 테스트를 수행하지 않는다.

## Implementation Units

- [x] UNIT-01: Repository Monitoring 설정과 Production Alerting baseline 조사
- [x] UNIT-02: Alertmanager receiver·route와 Secret 주입 구조 설계
- [x] UNIT-03: Pipeline 핵심 Alert 3종과 전달 테스트 artifact 구현
- [x] UNIT-04: Rule·Kustomize·Helm render와 전체 회귀 검증
- [x] UNIT-05: Production 적용 및 firing·resolved 전달 검증
- [x] UNIT-06: 운영 evidence 기반 문서 정합화와 최종 Verification
