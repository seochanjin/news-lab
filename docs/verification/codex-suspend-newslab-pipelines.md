# Verification: NewsLab 정기 수집·분석 중지 준비

## Verification Status

passed

위 상태는 로컬 설정 검증 결과다. 운영 적용 및 운영 중지 확인은 **human-required**이며,
아직 수행하지 않았다. PR 병합도 사람이 결정한다.

- 날짜: 2026-11-01 (Asia/Seoul)
- 저장소: `seochanjin/news-lab`
- 브랜치: `codex/suspend-newslab-pipelines`
- 비교 기준: `a2af5ed6311d00dad91d5adceab60b5fc46f5bc6`
- 설정 변경: CronJob 4개의 suspend 추가, 파이프라인 경보 2개 제거
- 공용 노드 경보, 배포 이미지, API·웹·DB·Secret 변경 없음

## 실제 로컬 검증

### YAML 파싱 및 기존 설정 보존

Command (저장소 루트에서 실행):

```bash
python3 - <<'PY'
import copy, json, subprocess
from pathlib import Path

base = 'a2af5ed6311d00dad91d5adceab60b5fc46f5bc6'
cronjobs = [
    'news-rss-collector',
    'news-daily-topic-pipeline',
    'news-three-day-topic-pipeline',
    'news-weekly-topic-pipeline',
]

def parse_yaml(text):
    result = subprocess.run(
        ['/usr/bin/ruby', '-ryaml', '-rjson', '-e',
         'puts JSON.generate(YAML.safe_load(STDIN.read))'],
        input=text, text=True, capture_output=True, check=True,
    )
    return json.loads(result.stdout)

def old_manifest(path):
    text = subprocess.check_output(['git', 'show', f'{base}:{path}'], text=True)
    return parse_yaml(text)

for name in cronjobs:
    path = f'k8s/{name}-cronjob.yaml'
    before = old_manifest(path)
    after = parse_yaml(Path(path).read_text())
    assert after['metadata']['name'] == name
    assert after['spec'].pop('suspend') is True
    assert after == before, f'Unexpected CronJob change: {name}'
    print(f'PASS {name}: suspend=true; all other settings unchanged')

path = 'k8s/monitoring/rules/news-lab-pipeline-alerts.yaml'
before = old_manifest(path)
after = parse_yaml(Path(path).read_text())
expected = copy.deepcopy(before)
removed = {'PipelineScheduleDelayed', 'PipelineScheduledJobFailed'}
for group in expected['spec']['groups']:
    group['rules'] = [rule for rule in group['rules'] if rule.get('alert') not in removed]
assert after == expected, 'Unexpected PrometheusRule change'
assert [rule['alert'] for group in after['spec']['groups'] for rule in group['rules']] == ['NewsLabNodeNotReady']
print('PASS PrometheusRule: only two pipeline alerts removed; complete node alert preserved')
print('PASS: five YAML manifests parsed and compared with base commit')
PY
```

Result:

```text
PASS news-rss-collector: suspend=true; all other settings unchanged
PASS news-daily-topic-pipeline: suspend=true; all other settings unchanged
PASS news-three-day-topic-pipeline: suspend=true; all other settings unchanged
PASS news-weekly-topic-pipeline: suspend=true; all other settings unchanged
PASS PrometheusRule: only two pipeline alerts removed; complete node alert preserved
PASS: five YAML manifests parsed and compared with base commit
```

Status: passed. CronJob의 예약·명령·이미지·자원·Secret 참조와 공용 경보의
식·유예시간·라벨·설명이 그대로 유지됨을 비교했다.
새로운 PromQL 식은 없으며, promtool 검증과 Kubernetes 서버 검증은 수행하지 않았다.

### 변경 범위

Command: `git diff --check`
Result: 출력 없음, exit 0.
Status: passed.

Command: `git diff --stat`, `git diff -- k8s`, `git status --short --branch`
Result: 설정 파일 5개만 변경. 이 작업의 Task 및 Verification 문서가 추가된다.
기존 미추적 `docs/reports/baseline-2026-08.md`는 포함하지 않는다.
Status: passed.

앱 코드가 바뀌지 않아 API·DB 테스트는 실행하지 않았다.
읽기 전용 동료 에이전트 검토에서 설정 변경 범위·노드 경보 보존·Argo 적용 범위에
차단사항이 없음을 확인했다.

### 문서 추가 후 최종 검사

Command: `git diff --cached --check`

첫 실행은 Markdown 줄바꿈용 뒤쪽 공백 4곳을 지적했다. 해당 공백을 제거하고
같은 검사를 다시 실행해 출력 없음, exit 0을 확인했다.
Status: passed (최초 실패 원인 수정 후 재검증).

문서 읽기 전용 검토에서도 운영 미실행 표시·적용 순서·복구 절차에 문제가 없었다.

## 병합 후 적용 — 사람이 수행, 아직 미실행

전제: PR 병합 후 병합된 main의 파일을 사용하고 OCI K3s 연결을 확인한다.
이 PR은 운영 설정을 직접 적용하지 않으며, 병합만으로 CronJob이 중지되지 않는다.
`argocd/news-api`는 현재 수동 Sync이고 `k8s` 하위 폴더를 재귀 탐색하지 않는다.

### 1. 경보 설정을 먼저 적용

아래는 **운영 변경 명령**이다. 운영 담당자가 실행한다.

```bash
KUBECONFIG="$HOME/.kube/oci-k3s.yaml" \
kubectl apply -f k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
```

아래는 **읽기 전용 확인 명령**이다.

```bash
KUBECONFIG="$HOME/.kube/oci-k3s.yaml" \
kubectl -n monitoring get prometheusrule news-lab-pipeline-alerts \
  -o jsonpath='{range .spec.groups[*].rules[*]}{.alert}{"\n"}{end}'
```

예상: `NewsLabNodeNotReady`만 남는다. Prometheus Rules 화면에서도
`PipelineScheduleDelayed`, `PipelineScheduledJobFailed`가 더 이상 평가되지 않고,
노드 경보가 유지되는지 확인한다. Alertmanager 수신 경로나 공용 서비스를 끄지 않는다.

경보 적용이 실패하면 먼저 원인을 확인한다. 예약을 긴급 중지해야 하는 상황이라면
CronJob 중지와 별개로 경보가 계속 발생할 수 있음을 운영자가 판단한다.

### 2. 뉴스랩 CronJob 변경을 수동 Sync

Argo CD의 **news-api** Application에서 diff가 이 PR의 CronJob 변경인지 확인한 뒤
수동 Sync한다. `gameprobe-backend`나 공유 인프라 Application을 변경하지 않는다.

경보 파일은 이 Sync 대상에 포함되지 않는다. 새 수집·분석 Job을 수동 생성하지 않는다.

### 3. 새 예약 중지와 진행 중 작업을 확인

다음은 **읽기 전용 확인 명령**이다.

```bash
KUBECONFIG="$HOME/.kube/oci-k3s.yaml" \
kubectl -n default get cronjobs \
  news-rss-collector news-daily-topic-pipeline \
  news-three-day-topic-pipeline news-weekly-topic-pipeline

KUBECONFIG="$HOME/.kube/oci-k3s.yaml" \
kubectl -n default get jobs
```

예상: 네 CronJob 모두 `SUSPEND=True`. 실행 중인 관련 Job이 있다면 완료를 기다리고
마지막에 `ACTIVE=0`인지 확인한다. 완료된 Job 기록은 삭제하지 않는다.
suspend는 이미 시작한 Job이나 수동으로 만든 Job을 중단하지 않는다.
Sync 일부 실패 시 네 리소스를 각각 확인하고, 실패한 리소스를 다시 적용하기 전
원인을 해결한다. 중지 완료는 네 개가 모두 suspend이고 관련 실행 Job이 없을 때다.

API·웹·Redis·exporter는 계속 실행되므로 이 PR은 뉴스랩 서비스 전체 종료가 아니다.
API 키 삭제 및 Supabase 자체 예약 작업 확인은 별도 작업이다.
GameProbe API와 기존 공용 노드 감시가 유지되는지도 운영 담당자가 확인한다.

## 복구 및 재개

아래는 절차 설명이며 자동 실행하지 않는다.

- 경보만 원복해야 하면 Git의 이전 두 파이프라인 경보 정의를 복구한 변경을 검토한 뒤,
  위와 같은 경보 파일 적용 절차를 수행한다. 노드 경보는 계속 유지한다.
- CronJob을 재개하려면 먼저 필요한 API 키·DB 연결·실행 시점을 확인한다.
  네 CronJob은 `startingDeadlineSeconds`가 미지정이므로 놓친 예약이 즉시 실행되거나
  누락 횟수 제한에 걸릴 수 있다. 자동으로 suspend를 해제하지 않는다.
- 재개 정책을 검토한 뒤 Git에서 suspend를 해제하는 변경을 승인하고 수동 Sync한다.
  예약·실패 경보도 재개 시점에 맞춰 복구한다.
- 경보 적용 성공 후 CronJob Sync가 실패해도 API·웹을 재시작할 필요는 없다.
  아직 suspend되지 않은 예약 작업은 계속 실행될 수 있으므로 상태를 확인한다.

## 운영 확인 기록

- 경보 설정 운영 적용: human-required, 미수행
- CronJob 수동 Sync: human-required, 미수행
- 관련 Job 완료 및 SUSPEND/ACTIVE 확인: human-required, 미수행
- Prometheus의 실제 경보 반영 및 GameProbe 운영 확인: human-required, 미수행
