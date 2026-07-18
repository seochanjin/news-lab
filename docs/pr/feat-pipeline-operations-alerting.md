# Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## 작업 내용

- 기존 Monitoring Helm values에서 비활성 상태였던 Alertmanager를 활성화하고,
  `alert_scope="news-lab"` 전용 route를 native Telegram receiver에 연결했다.
- Pipeline 정기 실행 지연, 정기 Job 실패와 Node NotReady를 감지하는 실제
  `PrometheusRule` 3종을 추가했다.
- 별도 전달 test Rule로 Prometheus evaluation부터 Alertmanager와 Telegram 개인
  채팅까지 firing·resolved 전달 경로를 검증했다.
- Secret lifecycle, Silence, 전달 실패, rollback과 test Rule 운영 경계를 설계
  문서와 Monitoring runbook에 기록했다.

## 주요 변경 사항

- `k8s/monitoring/kube-prometheus-stack-values.yaml`
  - matcher 없는 root `null` receiver를 유지하고
    `alert_scope="news-lab"` child route 한 개만 외부로 전달한다.
  - 외부 receiver는 Alertmanager native `telegram_configs` 한 개다.
  - `send_resolved: true`, `parse_mode: HTML`, `bot_token_file`과
    `chat_id_file`을 사용한다.
  - `monitoring/news-lab-alertmanager-telegram` Secret의 `bot-token`, `chat-id`
    key를 file mount로 참조한다. Secret manifest와 실제 값은 Repository에 없다.
- `k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`
  - `PipelineScheduleDelayed`: Daily `26h`, Weekly `8d` 기준을 분리하고 `for: 30m`을
    적용했다.
  - `PipelineScheduledJobFailed`: 숫자 suffix와 CronJob owner join으로 정기 Job만
    감지하고 prewarm Job을 제외하며 `for: 10m`을 적용했다.
  - `NewsLabNodeNotReady`: 지정된 Node 3대의 `Ready=true == 0`을 감지하고
    `for: 10m`을 적용했다.
  - 세 Alert 모두 `release=monitoring`, `alert_scope=news-lab`을 사용한다.
- `k8s/monitoring/rules/news-lab-alert-delivery-test.yaml`
  - firing 검증용 `vector(1)` test Alert를 별도 artifact로 유지한다.
  - 기본 Kustomization에서는 제외해 일반 배포에 포함되지 않는다.
  - resolved 운영 절차는 빈 벡터를 반환하는 `vector(0) > 0`을 사용한다.
- Architecture index, Alerting 설계, Monitoring runbook, Task, Verification과 Devlog를
  현재 Repository 구조 및 실제 Production evidence와 정합화했다.

## 추가/변경된 API

없음.

- FastAPI endpoint, request/response schema와 인증·권한 정책을 변경하지 않았다.
- application `/metrics` endpoint나 custom business metric을 추가하지 않았다.

## DB 변경 사항

없음.

- schema, migration, table, column, index와 constraint 변경이 없다.
- Supabase SQL과 Production 데이터 변경을 수행하지 않았다.

## README 영향

README 변경은 필요하지 않다.

- 이번 변경은 backend API 사용법이나 local 실행 절차가 아니라 Monitoring
  Alertmanager·PrometheusRule와 운영 runbook 범위다.
- 현재 동작과 운영 절차는 Architecture index, Alerting 설계와 Monitoring runbook에
  연결했으며 README가 가리키는 상위 구조를 바꾸지 않는다.

## 테스트

- Monitoring YAML parse: `5 passed`
- `kubectl kustomize k8s/monitoring/rules`
  - rendered resource `1`개
  - 실제 Alert 3종만 포함
  - `NewsLabAlertDeliveryTest` 미포함
- Helm chart `86.2.0` local render assertion: 통과
  - Alertmanager native Telegram configuration 정상
  - matcher 없는 root route와 NewsLab child route 한 개
  - Telegram receiver 한 개, `send_resolved: true`
  - Secret file path 사용, literal Telegram credential 없음
- Alertmanager `v0.32.2` `amtool check-config`: `SUCCESS`
- Production과 동일한 Prometheus `v3.12.0` `promtool check rules`
  - 실제 운영 Rule `3 rules found`
  - 전달 test Rule `1 rules found`
  - `--lint=all --lint-fatal`, exit code `0`
- `PYTHONPATH=. pytest -q`
  - 최종 `445 passed, 91 subtests passed in 14.64s`
- local Markdown link/fence, trailing whitespace와 민감정보 패턴 검사: 통과
- `git diff --check`: 출력 없음
- FastAPI, Pipeline, DB와 dependency tracked diff: 없음

## 확인 결과

- 사람이 Monitoring Helm release를 chart `kube-prometheus-stack-86.2.0`, app version
  `v0.91.0`, revision `4`로 upgrade했고 status `deployed`를 확인했다.
- Alertmanager `v0.32.2`는 replica `1/1`, reconciled·available 상태이며 Pod는
  `2/2 Running`, restart `0`이다. StatefulSet rollout과 Service 생성도 확인됐다.
- Prometheus는
  `monitoring/monitoring-kube-prometheus-alertmanager:http-web` API v2 endpoint에
  연결됐다.
- Production `monitoring/news-lab-pipeline-alerts`의 실제 Alert 3종은 모두
  `health=ok`, `state=inactive`, `lastError` 없음이다.
- 사람이 별도 `news-lab-alert-delivery-test` Rule을 적용해 Prometheus firing과
  Telegram firing 메시지를 확인했다. 임시 expression을 `vector(0) > 0`으로 바꾼
  뒤 `health=ok`, `state=inactive`와 Telegram resolved 메시지를 확인했다.
- test Rule 삭제 후 Kubernetes API `NotFound`와 Prometheus Rules API 제거 상태를
  확인했다. 최종 Production에는 `news-lab-pipeline-alerts`만 유지된다.
- NewsLab Rule의 parse·load·evaluation과 Telegram 전달 경로에서는 오류가 확인되지
  않았다.

## 비고

- Production 적용과 firing·resolved 수신 확인은 사람이 수행했고, PR에는
  Verification에 기록된 sanitized evidence만 반영했다. Agent는 Production
  command를 재실행하거나 Secret 값을 조회하지 않았다.
- 기존 chart 기본 `kube-apiserver-burnrate.rules`에서는 간헐적인 evaluation
  timeout이 관찰됐다. 현재 관찰 대상 Rule은 `health=ok`, `lastError` 없음이며
  정확한 원인은 이번 작업에서 확정하지 않았다.
- 위 timeout은 NewsLab Alert 3종이나 Telegram 전달 실패가 아니므로 비차단 관찰로
  분류했다. 후속 운영 개선에서 retention, query timeout, Rule 평가 시간과
  Prometheus CPU·메모리·스토리지 상태를 함께 조사할 수 있다.
- 이번 변경에서 chart 기본 Rule, retention, query timeout, Prometheus resource와
  storage를 수정하거나 비활성화하지 않았다.
- CodeRabbit의 minor actionable finding 2개를 승인해 Task의 Markdown fence와
  두 Rule artifact promtool 절차, Review·Approved Fixes·PR 문서를 정정했다.
- 이 승인 fix는 문서-only 변경이며 Alertmanager, 실제 Alert 3종, 전달 test Rule과
  Telegram receiver 구현은 변경하지 않았다. Production 재적용·재검증도 수행하지
  않았다.
- Review 파일은 Verification 통과 근거로 사용하지 않았다. CodeRabbit inline
  thread 확인·resolve는 수정 commit 이후 사람 또는 별도 승인 작업으로 남긴다.
- Pending Verification은 없다. PR commit, push, merge는 수행하지 않았다.
