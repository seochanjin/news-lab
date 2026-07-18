# Pipeline Operations Alerting 설계

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 현재 UNIT 경계

이 문서는 Pipeline 운영 Alerting의 근거를 UNIT별로 누적한다. UNIT-01에서는
Repository Monitoring 설정과 chart `86.2.0` render 구조를 조사했고, Production
read-only baseline은 사람이 제공한 sanitized evidence로 확인했다. UNIT-02에서는
Alertmanager 활성화와 receiver·route, Secret 주입 구조를 Repository values에
반영했다. 최초 generic receiver 설계는 Production 적용 전에 폐기하고 native
Telegram receiver로 교체했다.

UNIT-03에서는 핵심 Alert 3종과 별도 test alert artifact를 추가했다. UNIT-05의
Production Secret 구성, Helm·rule 반영과 실제 Telegram firing·resolved 전달은
사람이 수행했고, UNIT-06에서 sanitized evidence와 최종 문서 상태를 정합화했다.

## UNIT-01 Repository Monitoring baseline

Repository의 Monitoring core 설정은
`k8s/monitoring/kube-prometheus-stack-values.yaml`이고 chart version은 `86.2.0`으로
고정한다. Dashboard는 `k8s/monitoring/dashboards/`의 별도 Kustomize artifact다.
Alert rule 디렉터리와 custom `PrometheusRule` manifest는 아직 없다.

| 항목 | UNIT-01 조사 시점 Repository 또는 local render 기준 |
| --- | --- |
| Alertmanager | values에서 `enabled: false`; `Alertmanager` CR과 Prometheus의 `alerting` 설정이 render되지 않음 |
| PrometheusRule | chart 기본 rule 35개만 render됨; custom rule 없음 |
| Rule selector | `matchLabels.release: monitoring` |
| Rule namespace selector | `{}`; chart CRD 정의상 모든 namespace에서 rule 탐색 |
| Required custom rule label | `release: monitoring` |
| Prometheus placement | `observability: "true"` |
| Prometheus retention/storage | `1d`; `storageSpec` override 없음 |
| Provisioning 경로 | `k8s/`를 읽는 Backend Argo CD Application은 `recurse: false`라서 `k8s/monitoring/`을 배포하지 않음 |

Prometheus의 실제 rule selector는 chart 기본값의
`ruleSelectorNilUsesHelmValues: true` 때문에 Helm release label인
`release: monitoring`으로 render된다. namespace selector는 빈 label selector이므로
모든 namespace를 감시한다. 따라서 후속 custom rule은 `monitoring` namespace에
두는 것을 기본 경로로 삼되, 발견 조건에는 namespace보다
`release: monitoring` label이 필수다.

Monitoring values와 Dashboard provisioning은 Backend workload Argo CD
Application에 포함되지 않는다. Alertmanager와 chart values 변경은 기존 Monitoring
Helm release 경로에서 사람이 diff를 검토하고 반영해야 하며, custom rule의 실제
provisioning 경로는 후속 UNIT에서 Repository의 기존 별도 Kustomize 방식을 따라
확정한다.

## UNIT-01 chart 86.2.0 Alertmanager render baseline

Chart 자체의 기본값은 Alertmanager 활성화지만 UNIT-01 조사 시점 Repository
values는 이를 비활성화했다. 당시 values에 `--set alertmanager.enabled=true`만
더한 local render로 활성화 시 생성 구조를 확인했다.

| 항목 | chart `86.2.0` render 결과 |
| --- | --- |
| Alertmanager CR | `monitoring-kube-prometheus-alertmanager` |
| Configuration Secret | `alertmanager-monitoring-kube-prometheus-alertmanager` |
| Configuration key | `alertmanager.yaml` |
| `spec.configSecret` | 미지정; Operator 기본 규칙인 `alertmanager-<Alertmanager 이름>` 사용 |
| Prometheus 전달 대상 | `monitoring/monitoring-kube-prometheus-alertmanager:http-web`, API v2 |
| Chart config 입력 | `alertmanager.config` 또는 `alertmanager.stringConfig` |
| Existing Secret 기본값 | `alertmanagerSpec.useExistingSecret: false` |
| 추가 mounted Secret 기본값 | `alertmanagerSpec.secrets: []` |
| 기본 route·receiver | receiver 이름 `null` 하나; 실제 외부 전달 없음 |

`alertmanager.config`에는 `global`, `inhibit_rules`, `route`, `receivers`, `templates`
구조가 있고 chart가 이를 위 Secret의 `alertmanager.yaml`로 render한다. 단순히
`enabled`만 바꾸면 기본 `null` receiver가 알림을 버리므로 운영 알림이 전달되지
않는다. 실제 receiver 한 개, NewsLab 전용 route 한 개와 `send_resolved: true`를
함께 설계해야 한다.

UNIT-01 시점의 Repository에는 Alertmanager route, 실제 receiver, endpoint 또는
credential, Alertmanager용 Secret manifest가 없었다. UNIT-02는 route와 receiver
구조만 values에 반영하며 Secret manifest나 실제 값은 추가하지 않는다.

## Alertmanager route와 receiver 설계

Repository values는 Alertmanager를 활성화하고 다음 최소 routing tree를 구성한다.

```text
모든 Alert
→ root route / null sink
→ alert_scope="news-lab"인 Alert만 child route와 대조
→ news-lab-telegram native Telegram receiver
```

Alertmanager의 [공식 configuration 계약](https://prometheus.io/docs/alerting/latest/configuration/)상
root route는 모든 Alert를 받아야 하므로 matcher를 가질 수 없다.
따라서 외부 전송을 하지 않는 필수 `null` sink를 root receiver로 두고,
`alert_scope = "news-lab"` matcher를 가진 child route 한 개만 외부 receiver로
연결한다. 이때 receiver entry는 root용 sink와 외부용 두 개지만, 실제 endpoint로
전송하는 운영 receiver는 `news-lab-telegram` 하나뿐이다. chart 기본 rule이나
다른 팀 rule은 전용 label이 없으면 외부로 전송되지 않는다.

외부 receiver는 Alertmanager native `telegram_configs` 한 채널로 고정하며
webhook bridge를 두지 않는다. `group_by`는 `alertname`과
`severity`, `group_wait`는 `30s`, `group_interval`은 `5m`, `repeat_interval`은
`12h`다. UNIT-03의 세 실제 Alert와 test alert는 모두
`alert_scope: news-lab` label을 가져야 이 route에 진입한다. receiver의
`send_resolved: true`는 firing 이후 resolved 전달 검증을 가능하게 한다.

`parse_mode`는 Alertmanager의 기본 Telegram rendering과 같은 `HTML`을 values에
명시한다. 기본값에 암묵적으로 의존하지 않고 render 결과에서 메시지 해석 방식을
검토할 수 있게 고정하는 선택이며, 별도 custom message template은 추가하지 않는다.

## Secret 주입과 소유권 경계

Telegram credential과 destination identifier는 `monitoring` namespace의 사람이
관리하는 Opaque Secret `news-lab-alertmanager-telegram`의 `bot-token`과 `chat-id`
key에 저장한다. Secret manifest와 실제 값은 Git에 두지 않는다. values는
`alertmanagerSpec.secrets`에 Secret 이름만 등록하고, Operator가 Alertmanager
Pod에 mount한 다음 native Telegram receiver가 두 파일을 읽는다.

| 항목 | 고정 계약 |
| --- | --- |
| Secret namespace | `monitoring` |
| Secret name | `news-lab-alertmanager-telegram` |
| Secret keys | `bot-token`, `chat-id` |
| Bot token file | `/etc/alertmanager/secrets/news-lab-alertmanager-telegram/bot-token` |
| Chat ID file | `/etc/alertmanager/secrets/news-lab-alertmanager-telegram/chat-id` |
| Repository 보관 정보 | resource 이름, key 이름과 mount 경로만 |
| 사람 책임 | Telegram bot·개인 채팅 준비, Secret 생성·회전·삭제와 접근 통제 |

Alertmanager configuration 자체는 chart가 생성하는
`alertmanager-monitoring-kube-prometheus-alertmanager` Secret에 들어가지만,
여기에는 실제 token이나 chat ID 대신 위 file path만 render된다. `useExistingSecret`이나
`configSecret`으로 전체 configuration을 별도 관리하지 않으며,
`AlertmanagerConfig` CR도 도입하지 않는다. 이렇게 configuration 구조는 Git에서
review하면서 credential lifecycle은 운영 Secret으로 분리한다.

Alertmanager Pod는 기존 Monitoring core와 같은 `observability: "true"` node에
배치한다. Secret이 없거나 key가 다르면 mount 또는 configuration load가 실패할 수
있으므로, 사람은 Helm 반영 전에 Secret의 이름과 key 존재만 확인하고 실제 값은
출력하지 않는다. credential 회전 뒤에는 firing·resolved test alert 전달로 새 값을
확인하며, 실패하면 route label, mount 상태와 Alertmanager log를 sanitized 형태로
점검한다.

## Pipeline schedule baseline

후속 stale alert 기준에 사용할 Repository CronJob schedule은 모두 namespace가
생략되어 `default`를 사용하고 timezone은 `Asia/Seoul`이다.

| 계열 | CronJob | Schedule |
| --- | --- | --- |
| Daily | `news-rss-collector` | 매일 `03:00` |
| Daily | `news-daily-topic-pipeline` | 매일 `04:00` |
| Daily | `news-three-day-topic-pipeline` | 매일 `05:00` |
| Weekly | `news-weekly-topic-pipeline` | 매주 월요일 `00:30` |

세 Daily 계열과 Weekly 계열은 실행 주기가 다르므로 하나의 stale threshold로
합치지 않는다. schedule과 timezone 자체는 변경하지 않는다.

## UNIT-03 핵심 Alert 3종

`k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`은 `monitoring` namespace와
`release: monitoring` label을 사용한다. 세 Alert 모두
`alert_scope: news-lab` label을 가져 UNIT-02의 전용 route로만 전달된다.

| Alert | 조건 | `for` | Severity | 근거 |
| --- | --- | --- | --- | --- |
| `PipelineScheduleDelayed` | Daily는 마지막 schedule 후 `26h` 초과, Weekly는 `8d` 초과 | `30m` | `warning` | Daily는 다음 실행 예정 시각에서 2시간, Weekly는 다음 월요일 00:30에서 24시간의 시작 지연을 허용하고 30분 지속 시 알림 |
| `PipelineScheduledJobFailed` | 숫자 suffix 정기 Job의 `kube_job_status_failed > 0`과 CronJob owner가 모두 일치 | `10m` | `warning` | 일시적인 scrape 변동을 제외하면서 보존된 실패 Job을 운영자가 확인할 시간을 확보 |
| `NewsLabNodeNotReady` | 지정한 세 Node의 `Ready=true` condition이 `0` | `10m` | `critical` | 짧은 상태 전환은 제외하되 Pipeline과 Monitoring 가용성에 영향을 주는 Node 장애는 높은 심각도로 전달 |

지연 rule은 Alert 이름은 하나로 유지하면서 PromQL 분기를 Daily와 Weekly로
분리하고 결과에 `cadence` label을 추가한다. `Asia/Seoul` CronJob controller가
schedule 시각을 계산하지만 metric은 Unix timestamp이므로 `time()`과의 차이는
timezone 변환 없이 초 단위로 비교한다. 이 Alert는 metric series가 존재하는
CronJob의 지연을 감지하며, CronJob 또는 kube-state-metrics series 자체가 사라진
상태까지 대신 감지하지는 않는다.

정기 Job 실패는 Dashboard에서 검증한 canonical 숫자 suffix
`-[0-9]+`를 Job 이름 끝에 요구한다. 따라서 `*-prewarm-*` 수동 Job은 같은 CronJob
owner를 가져도 제외된다. `max by (namespace, job_name)`은 환경에 따라 `reason`
label이 추가된 failed series를 Job 한 개로 정규화하고, `kube_job_owner` join으로
네 대상 CronJob의 controller 생성 Job만 남긴다.

네 CronJob의 `failedJobsHistoryLimit`는 모두 `3`이다. 실패 object가 보존되는 동안
Alert도 firing 상태를 유지하고 Alertmanager의 `repeat_interval: 12h`에 따라 반복
전달될 수 있다. 이후 성공 Job이 생겨도 이전 실패 Job이 남아 있으면 자동으로
resolved되지 않으며, controller가 해당 실패 Job을 history limit에 따라 제거해
query 결과가 사라져야 resolved된다. Kubernetes Job 성공·실패만으로 업무 수준의
`partial_success`는 판별하지 못한다.

## UNIT-03 전달 테스트 artifact

`k8s/monitoring/rules/news-lab-alert-delivery-test.yaml`은 `vector(1)`과 `for: 1m`을
사용하는 별도 `PrometheusRule`이다. 실제 운영 rule만 render하는
`k8s/monitoring/rules/kustomization.yaml`에서는 의도적으로 제외했다. 따라서
운영자가 명시적으로 test file을 적용해야만 firing하며 일반 Kustomize 반영으로
상시 test alert가 생성되지 않는다.

사람은 test rule을 별도로 적용해 firing 수신을 확인한 뒤, 같은 임시 rule의
expression을 `vector(0) > 0`으로 바꿔 적용해 resolved 수신을 확인한다.
`vector(0)`만 사용하면 값이 0인 시계열 자체는 계속 반환되어 Alert expression이
활성인 채로 남으므로 resolved 전환에 사용할 수 없다. 검증이 끝나면 test rule
object를 제거하고 실제 세 Alert만 남았는지 확인한다. 이 변경과 삭제는 모두
human-controlled이며 Agent는 수행하지 않는다.

## UNIT-05 Production 전달 검증 결과

사람이 chart `86.2.0`을 Monitoring Helm revision `4`로 반영하고 Alertmanager
`v0.32.2`, 실제 NewsLab Rule 3종과 native Telegram 전달 경로를 검증했다.

- Alertmanager CR은 reconciled·available 상태이고 replica `1/1`, Pod `2/2`
  Running, restart `0`이며 StatefulSet rollout과 Service 생성을 확인했다.
- Prometheus는 Alertmanager API v2 endpoint
  `monitoring/monitoring-kube-prometheus-alertmanager:http-web`에 연결됐다.
- `news-lab-pipeline-alerts`의 세 Rule은 모두 `health=ok`, `state=inactive`,
  `lastError` 없음으로 확인됐다.
- 별도 test Rule의 firing과 `vector(0) > 0` 전환 뒤 resolved Telegram 메시지를
  실제 수신했다.
- test Rule을 제거한 뒤 Kubernetes API의 `NotFound`와 Prometheus Rules API의
  제거 상태를 확인해 최종 Production에는 실제 Rule 3종만 남겼다.

NewsLab Rule과 Telegram 전달 경로의 parse, load, evaluation과 delivery 오류는
확인되지 않았다. 다만 기존 chart 기본 `kube-apiserver-burnrate.rules`에서는
간헐적인 evaluation timeout이 관찰됐다. 현재 관찰 대상 Rule은 `health=ok`이고
`lastError`는 비어 있지만 정확한 원인은 확정하지 않았다. 이 비차단 관찰 때문에
이번 작업에서 기본 Rule, retention, query timeout이나 Prometheus resource를
변경하지 않는다.

## UNIT-01 Production Alerting baseline

2026-07-18에 사람이 Kubernetes API tunnel과 cluster-info가 정상임을 확인하고
제공한 sanitized read-only evidence는 다음과 같다.

| 항목 | Production live baseline |
| --- | --- |
| Alertmanager | `monitoring` namespace에 CR과 Pod 없음 |
| Prometheus | Prometheus와 Prometheus Operator Pod Running |
| PrometheusRule | `monitoring` namespace에 35개; 조회된 rule은 `release=monitoring` label 사용 |
| NewsLab custom rule | 없음 |
| Rule selector | `{"matchLabels":{"release":"monitoring"}}` |
| Rule namespace selector | `{}` |
| Alertmanager endpoint | 없음 |
| AlertmanagerConfig | 없음 |
| 활성 route·receiver와 configuration Secret | Alertmanager 미활성 상태이므로 해당 없음 |

Agent의 local tunnel 접근 실패는 과거 실행 이력으로 Verification에 보존했다.
현재 baseline은 위 사람이 제공한 live 결과를 기준으로 하며, 확인하지 않은 Secret
값이나 endpoint 값은 추정하거나 기록하지 않았다.

## 최종 범위

- 기본 Kustomization은 승인된 실제 Alert 3종만 포함한다.
- 전달 test manifest는 firing용 `vector(1)`을 유지하되 기본 Kustomization에서는
  제외한다.
- 기존 chart 기본 burnrate Rule timeout은 후속 운영 개선 후보이며 76차에서
  설정 변경, 비활성화나 resource 조정을 하지 않는다.
