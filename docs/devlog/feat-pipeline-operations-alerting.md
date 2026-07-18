# Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## 작업 목적

75차에서 확인한 Production Prometheus metric과 PromQL을 실제 운영 알림으로
연결하는 작업이다. 목표는 Alert manifest를 추가하는 데 그치지 않고 다음 전달
경로를 끝까지 확인하는 것이었다.

```text
PrometheusRule
→ Prometheus evaluation
→ Alertmanager route
→ native Telegram receiver
→ Telegram 개인 채팅 firing 수신
→ Telegram 개인 채팅 resolved 수신
```

운영 Alert는 Pipeline 정기 실행 지연, 정기 Job 실패, Node NotReady 3종으로
제한했다. application code, Pipeline business logic, DB와 custom metric은 변경하지
않았다.

## 기존 문제

- Repository Monitoring values에서 Alertmanager가 비활성 상태였다.
- Production에는 Alertmanager CR·Pod와 NewsLab custom `PrometheusRule`이 없었고,
  Prometheus에서 외부 Alertmanager endpoint도 설정되지 않았다.
- Dashboard로 상태를 조회할 수는 있었지만 정기 실행 지연, 실패 Job과 Node
  NotReady를 운영자가 능동적으로 전달받는 경로는 없었다.
- 초기 설계는 generic webhook receiver를 전제로 했으나 실제 운영 채널이 Telegram
  개인 채팅으로 확정됐다. webhook bridge를 추가하면 별도 서비스 운영과 장애
  지점이 생기는 문제가 있었다.
- 전달 테스트를 안전하게 종료하려면 Alert expression이 빈 벡터가 되어야 한다.
  `vector(0)`만 사용하면 값 0인 시계열이 계속 반환되어 resolved 전환이 되지 않는다.

## 변경 내용

- `kube-prometheus-stack` values에서 Alertmanager를 활성화했다.
- matcher 없는 root `null` receiver 아래에 `alert_scope="news-lab"` child route 한
  개를 두고 native Telegram receiver로 연결했다.
- 외부 receiver는 Telegram 한 개만 사용하고 `send_resolved: true`와
  `parse_mode: HTML`을 명시했다.
- 운영 Secret은 `monitoring/news-lab-alertmanager-telegram`의 `bot-token`,
  `chat-id` key로 정의하고 `bot_token_file`, `chat_id_file`로 읽도록 했다.
  Secret manifest와 실제 값은 Repository에 추가하지 않았다.
- `release=monitoring` label을 가진 실제 Alert 3종과 별도 전달 test Rule을 추가했다.
- Architecture index, Alerting 설계와 Monitoring runbook에 route, Secret lifecycle,
  Silence, 전달 실패, rollback과 검증 절차를 문서화했다.

## 구현 상세

### Alertmanager route

root route는 모든 Alert를 받아야 하므로 matcher를 두지 않았다. root receiver는
외부 전송을 하지 않는 `null` sink이고, `alert_scope="news-lab"` matcher가 있는
child route만 `news-lab-telegram` receiver로 전달한다. chart 기본 Alert나 다른
rule은 전용 label이 없으면 Telegram으로 전달되지 않는다.

알림 grouping은 `alertname`, `severity`를 사용한다. `group_wait: 30s`,
`group_interval: 5m`, `repeat_interval: 12h`로 구성했다. `parse_mode`는 Alertmanager
Telegram 기본 rendering과 같은 `HTML`을 명시해 version 변경 시에도 render 계약을
검토할 수 있게 했다.

### Secret 경계

values에는 Secret resource 이름, key 이름과 mount file path만 둔다.

- Bot token file:
  `/etc/alertmanager/secrets/news-lab-alertmanager-telegram/bot-token`
- Chat ID file:
  `/etc/alertmanager/secrets/news-lab-alertmanager-telegram/chat-id`

credential 생성·회전·삭제와 접근 통제는 사람의 운영 책임이다. 전체 Alertmanager
configuration을 별도 Secret이나 `AlertmanagerConfig` CR로 분리하지 않고 chart가
관리하는 configuration과 별도 credential Secret mount를 조합했다.

### 실제 Alert 3종

1. `PipelineScheduleDelayed`
   - Daily: 마지막 schedule 후 `26h` 초과
   - Weekly: 마지막 schedule 후 `8d` 초과
   - `for: 30m`, severity `warning`
   - 결과에 `cadence=daily|weekly` label을 추가한다.
2. `PipelineScheduledJobFailed`
   - 숫자 suffix `-[0-9]+`와 CronJob owner join을 모두 요구한다.
   - 수동 prewarm Job은 제외된다.
   - `for: 10m`, severity `warning`
3. `NewsLabNodeNotReady`
   - `arm-master-node`, `arm-worker-node`, `pi-worker-node`만 대상으로 한다.
   - `Ready=true == 0`이 10분 지속되면 firing한다.
   - severity `critical`

세 Alert 모두 `alert_scope=news-lab`을 사용해 전용 child route에만 진입한다.

### 전달 test Rule

Repository test manifest는 `vector(1)`, `for: 1m`으로 firing을 만든다. 이 파일은
기본 Kustomization에서 제외해 사람의 명시적 적용 없이는 생성되지 않는다.

resolved 검증에서는 운영용 임시 expression을 `vector(0) > 0`으로 바꿨다. 이
표현식은 빈 벡터를 반환하므로 Alert가 inactive로 전환된다. 확인 후 test Rule을
삭제하고 Kubernetes API와 Prometheus Rules API 양쪽에서 제거를 검증했다.

## 대안 검토

### Generic webhook과 native Telegram

- Generic webhook은 채널 교체가 쉽지만 webhook bridge를 별도로 배포·운영해야 한다.
- Native Telegram은 Alertmanager가 직접 전달하므로 중간 서비스와 장애 지점이
  줄어든다.

### root receiver 직접 전송과 label 기반 child route

- root receiver를 Telegram에 직접 연결하면 chart 기본 Alert까지 모두 외부로
  전달되어 알림 범위가 과도해진다.
- root `null` sink와 NewsLab label child route를 분리하면 이번 작업의 Alert만
  전달할 수 있다.

### 전체 configuration Secret과 credential file mount

- 전체 configuration을 existing Secret으로 관리하면 credential과 route 구조가
  Git review 경계 밖으로 이동한다.
- chart configuration은 Git에 두고 실제 credential만 별도 Secret file로 읽으면
  구조 검토와 Secret lifecycle을 분리할 수 있다.

### 실제 장애 유도와 test Alert

- Node 중단, CronJob suspend나 실패 Job 생성은 Production 영향이 크다.
- 별도 `vector(1)` test Alert는 실제 업무 장애 없이 evaluation·route·receiver를
  검증할 수 있다.

## 선택한 접근과 근거

- webhook bridge 없이 Alertmanager native Telegram receiver를 선택했다.
- root `null` sink와 `alert_scope="news-lab"` child route로 외부 전달 범위를
  최소화했다.
- credential은 file mount로 주입해 Git에는 실제 값이 남지 않도록 했다.
- 기존 kube-state-metrics를 사용해 custom application metric이나 DB query를
  도입하지 않았다.
- Daily와 Weekly 실행 주기가 다르므로 stale threshold를 분리했다.
- 정기 Job 실패는 canonical 숫자 suffix와 CronJob owner를 함께 확인해 prewarm을
  제외했다.
- 안전한 end-to-end 검증을 위해 기본 Kustomization에서 분리된 test Rule을
  사람이 명시적으로 적용·제거했다.

## 트레이드오프

- `kube_cronjob_status_last_schedule_time` series 자체가 사라진 상태는 지연 Alert가
  감지하지 못한다.
- Kubernetes Job 성공·실패만으로 업무 수준의 `partial_success`는 구분할 수 없다.
- 실패 Job은 `failedJobsHistoryLimit: 3` 범위에서 object가 남아 있는 동안 Alert가
  유지되고 `repeat_interval: 12h`에 따라 반복될 수 있다.
- Telegram Secret이 없거나 key가 잘못되면 Pod mount 또는 configuration load가
  실패하므로 Helm 반영 전 사람의 key 존재 확인이 필요하다.
- test Rule은 Repository에 남지만 기본 Kustomization에서 제외된다. 전달 재검증
  때 명시적으로 적용하고 반드시 제거해야 한다.
- 기존 chart 기본 `kube-apiserver-burnrate.rules`의 evaluation timeout은 이번
  범위에서 해결하지 않았다.

## 테스트

Verification에 기록된 최종 결과는 다음과 같다.

- Monitoring YAML parse: `5 passed`
- `kubectl kustomize k8s/monitoring/rules`
  - rendered resource `1`개
  - 실제 Alert 3종만 포함
  - `NewsLabAlertDeliveryTest` 미포함
- Helm chart `86.2.0` local render assertion: 통과
  - matcher 없는 root route
  - NewsLab child route와 native Telegram receiver 각 1개
  - `send_resolved: true`, Secret file path 확인
  - literal Telegram credential과 webhook configuration 없음
- Alertmanager `v0.32.2` `amtool check-config`: `SUCCESS`
- Production과 동일한 Prometheus `v3.12.0` `promtool check rules`
  - 실제 운영 Rule: `3 rules found`
  - 전달 test Rule: `1 rules found`
  - `--lint=all --lint-fatal`, exit code `0`
- 최종 전체 pytest: `445 passed, 91 subtests passed in 14.64s`
- local Markdown link/fence, trailing whitespace와 민감정보 패턴 검사: 통과
- `git diff --check`: 출력 없음
- FastAPI, Pipeline, DB와 dependency tracked diff: 없음

## 운영 반영

사람이 승인된 운영 절차로 Monitoring Helm release를 revision `3`에서 `4`로
upgrade했다. chart는 `kube-prometheus-stack-86.2.0`, app version은 `v0.91.0`이고
revision `4` status는 `deployed`다.

Alertmanager `v0.32.2`는 replica `1/1`, reconciled·available 상태이며 Pod는
`2/2 Running`, restart `0`이다. StatefulSet rollout과 Service 생성도 확인됐다.
Prometheus는 Alertmanager API v2 endpoint에 연결됐다.

사람이 실제 Rule 3종과 별도 test Rule을 적용했다. Prometheus API에서 test Alert
firing을 확인하고 Telegram firing 메시지를 수신했다. 임시 expression을
`vector(0) > 0`으로 바꾼 뒤 `health=ok`, `state=inactive`와 Telegram resolved
메시지를 확인했다. test Rule을 삭제한 뒤 Kubernetes API `NotFound`와 Prometheus
Rules API 제거 상태를 확인했다.

Agent는 Production command를 재실행하지 않았고 Secret 값, Telegram bot token과
chat ID를 조회하거나 기록하지 않았다.

## README 업데이트 판단

README 업데이트는 필요하지 않다.

- 이번 작업은 public API 사용법, local application 실행이나 DB schema가 아니라
  Monitoring Alerting과 운영 절차 변경이다.
- Architecture index에서 Alerting 설계로 연결하고 Runbook index가 기존 Monitoring
  runbook으로 연결하므로 상세 정보의 진입점이 이미 마련돼 있다.
- README가 설명하는 backend 상위 구조와 사용자-facing contract는 바뀌지 않았다.

## 확인 결과

- Production `monitoring/news-lab-pipeline-alerts`의 세 실제 Alert는 모두
  `health=ok`, `state=inactive`, `lastError` 없음이다.
- Telegram firing과 resolved 메시지를 실제 수신했다.
- test Rule 제거 후 최종 Production에는 `news-lab-pipeline-alerts`만 유지된다.
- NewsLab Rule의 parse·load·evaluation과 Telegram 전달 경로에서 오류가 확인되지
  않았다.
- Verification Status와 UNIT-01~06은 모두 `passed`이고 Pending Verification은 없다.

기존 chart 기본 `kube-apiserver-burnrate.rules`에서는 최근 관찰 중 간헐적인
evaluation timeout이 확인됐다. 현재 관찰 대상 Rule은 `health=ok`, `lastError`
없음이며 정확한 원인은 확정하지 않았다. 이 현상은 NewsLab Alert 3종이나 Telegram
전달 실패가 아니므로 비차단 관찰로 분류했다. 이번 작업에서는 기본 Rule,
retention, query timeout, Prometheus resource와 storage를 변경하지 않았다.

## 이번 단계의 의미

Dashboard로 상태를 찾아보는 수동 관찰에서 한 단계 나아가, 정기 실행 지연·정기
Job 실패·Node NotReady를 운영 채널로 능동 전달하는 경로를 만들었다. 특히
Prometheus evaluation, Alertmanager routing, native Telegram receiver, 실제 개인
채팅 수신과 resolved까지 한 흐름으로 검증했다.

동시에 root sink, label route, Secret file mount와 human-controlled test artifact로
운영 안전 경계를 분리했다. 기능 구현뿐 아니라 credential 비노출, test cleanup과
실패 대응까지 같은 작업 단위에서 문서화하고 검증했다.

## 포트폴리오용 요약

- kube-prometheus-stack `86.2.0`에서 Alertmanager `v0.32.2`를 활성화하고 native
  Telegram receiver와 file-based Secret 주입 구조를 설계했다.
- kube-state-metrics 기반 Pipeline Alert 3종을 구현하고 Kustomize, Helm,
  promtool, amtool과 전체 pytest로 정적·회귀 검증했다.
- 사람이 수행한 Production 적용에서 실제 Telegram firing·resolved 전달과 test
  Rule cleanup까지 확인해 end-to-end 운영 검증을 완료했다.

## 다음 단계 후보

- 기존 `kube-apiserver-burnrate.rules` evaluation timeout을 별도 운영 개선 Task로
  조사한다. retention, query timeout, Rule 평가 시간과 Prometheus CPU·메모리·
  스토리지 상태를 함께 확인하되 원인 분석 전 설정 변경을 먼저 하지 않는다.
- CronJob metric series 자체가 사라지는 경우를 탐지할 필요가 있는지 별도 Alert
  요구사항으로 검토한다.
- 실제 운영 알림량을 관찰한 뒤 threshold, grouping, repeat interval과 Silence
  정책의 조정 필요성을 별도 Task에서 평가한다.
- Task Notes에 따라 다음 프로젝트 차수인 DB Backup/Restore 훈련을 진행할 수 있다.

Approved Fixes 문서에는 적용 대상으로 승인된 finding이 없다. Review 파일은 fix
승인이나 Verification 통과 근거로 사용하지 않았다. PR commit, push와 merge는
수행하지 않았다.
