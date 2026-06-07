# NewsLab 운영 점검 Runbook 정리

## 작업 목적

- 운영자가 NewsLab의 cluster, monitoring, API, scheduled workload 상태를
  빠르게 확인하고, 이상 시 변경 작업 전에 필요한 진단 증거를 수집할 수
  있는 표준 절차를 만든다.

## 기존 문제

- 기존 Runbook은 개별 개발·운영 명령을 제공했지만, 정상 여부를 판단하는
  순서와 기준이 한 곳에 정리되어 있지 않았다.
- Cluster, monitoring, application, CronJob 점검 명령이 분산되어 있어
  일상 점검과 장애 대응에서 누락 가능성이 있었다.
- Node/Pod/API/CronJob/monitoring 장애별 첫 진단 순서와 결과 기록 양식이
  없었다.

## 변경 내용

- `docs/RUNBOOK.md` 앞부분에 `Routine Operation Check`를 추가했다.
- Quick health check 이후 cluster, monitoring, application, CronJob 상세
  점검으로 내려가는 흐름을 정의했다.
- Grafana bundled dashboard에서 확인할 CPU, memory, workload, node
  exporter 기준과 Prometheus `1d` retention/ephemeral storage 주의점을
  기록했다.
- 공통 장애 유형별로 `describe`, events, current/previous logs, metrics,
  status API를 이용한 read-only 1차 대응 순서를 정리했다.
- 정기 점검 시 사용할 checklist를 추가했다.

## 구현 상세

- Quick health check:
  - Node/Pod 상태, resource usage, CronJob/Job 상태, `/health`,
    `/collector/status`, `/extractor/status`를 순서대로 확인하도록 구성했다.
  - Node `Ready`, `news-api` `2/2`, CronJob schedule과 최근 성공 Job 등 현재
    구성에 맞는 정상 baseline을 함께 기록했다.
- Cluster checks:
  - `kubectl get`, `top`, events, `describe`, current/previous logs를 사용해
    readiness, placement, restart, scheduling, resource 문제를 조사하도록
    정리했다.
- Monitoring checks:
  - `monitoring` namespace의 Grafana, Prometheus, Prometheus Operator,
    kube-state-metrics, node-exporter 상태를 확인하도록 했다.
  - Local port-forward 접근과 bundled dashboard별 CPU, memory, workload,
    filesystem, network 확인 기준을 기록했다.
  - Prometheus의 `1d` retention과 ephemeral storage 특성을 운영 판단 시
    고려하도록 명시했다.
- Application and CronJob checks:
  - `news-api` Deployment, Pod, Service, Ingress, certificate와 read-only API
    확인 절차를 분리했다.
  - RSS collector와 raw extractor의 schedule, suspension, Jobs, Pods,
    run-history API를 함께 비교하도록 했다.
- First response:
  - Node NotReady, Pod Pending, Pod CrashLoopBackOff, OOMKilled, `news-api`
    unavailable, CronJob failure, Grafana/Prometheus unavailable에 대해
    read-only 증거 수집 순서를 정의했다.
  - 변경성 대응은 human operator가 원인과 증거를 확인한 뒤 결정하도록
    분리했다.
- Operation record:
  - 점검 시간, operator, 정상 여부, 후속 조치, sanitized evidence를 기록할
    수 있는 checklist를 추가했다.

## 대안 검토

- 별도 운영 점검 문서 신규 생성:
  - 운영 명령의 기준 문서가 분산될 수 있어 기존 `docs/RUNBOOK.md`에
    통합하는 방식을 선택했다.
- 자동 점검 script 추가:
  - 현재 task는 documentation-only이며 production 접근과 결과 판정의
    운영 책임도 분리해야 하므로 제외했다.
- 장애별 자동 복구 명령 포함:
  - 원인 확인 전 rollout, Pod 삭제, label/manifest 변경이 추가 장애를
    만들 수 있어 read-only 진단과 human-approved 대응을 분리했다.

## 선택한 접근과 근거

- 가장 짧은 quick health check를 진입점으로 두고, 이상이 발견된 영역의
  상세 점검과 장애별 대응으로 이동하도록 구성했다.
- 정상 기준은 현재 manifest와 monitoring baseline에 맞춰 `news-api`
  `2/2`, 두 CronJob의 schedule, monitoring component와 node-exporter
  상태를 사용했다.
- 운영 기록에는 결과와 sanitized evidence만 남기고 credential, kubeconfig,
  private address, unredacted application data를 남기지 않도록 명시했다.

## 트레이드오프

- Dashboard 이름은 kube-prometheus-stack 버전에 따라 약간 달라질 수 있다.
- 단일 수치 threshold를 강제하지 않고 sustained saturation과 최근 trend
  비교를 사용하므로 운영자의 판단이 필요하다.
- 자동 점검이나 자동 복구는 제공하지 않지만, production-impacting action을
  진단 절차와 분리해 안전성을 유지한다.
- 현재 통합 Runbook의 분량이 증가했다. 문서가 더 커지면 routine check,
  K3s operations, CronJobs, troubleshooting을 `docs/runbooks/` 하위 문서로
  분리할 필요가 있다.

## 테스트

- `git diff --check`: 출력 없음, exit code `0`.
- Application source, DB, K3s manifest, collector/extractor script scope diff:
  출력 없음, exit code `0`.
- Private IP pattern 검사: exit code `1`, 출력 없음. 매치가 발견되지 않았다.
- Credential pattern 검사: 기존 repository의 안전한 secret expression,
  검사 명령 문자열, redacted placeholder, Python `engine.begin()` false
  positive만 매치했으며 credential 값은 발견되지 않았다.
- Untracked workflow 문서를 포함한 whitespace 검사:
  `Workflow docs whitespace: OK`.
- Untracked workflow 문서를 포함한 `rg` 검사에서도 private IP와 credential
  값이 발견되지 않았다.
- Required quick check, category checks, seven common failure sections,
  routine checklist heading이 모두 확인되었다.
- 실제 명령과 상세 결과는
  `docs/verification/docs-operation-check-runbook.md`를 source of truth로
  사용한다.

## 운영 반영

- Agent는 production `kubectl`, production `curl`, Grafana 접속,
  `kubectl apply`, `kubectl rollout`, git push, git merge를 실행하지 않았다.
- 이번 변경은 documentation-only이며 application, DB, K3s manifest,
  collector/extractor runtime behavior를 변경하지 않았다.
- Human-provided production verification log는 없으며 production 상태 확인은
  pending이다.
- Production deployment, rollout, PR merge 완료를 주장하지 않는다.

## README 업데이트 판단

- README는 수정하지 않았다.
- 이번 작업은 운영자를 위한 상세 절차이며, 기존 README의 프로젝트 개요와
  로컬 실행 안내를 변경하지 않는다.
- Approved fixes 문서에서 README의 Runbook 링크 추가는 deferred로
  기록되었다.
- User-facing landing page, admin dashboard, public operations section이
  도입될 때 README 링크 추가를 다시 검토한다.

## 확인 결과

- Runbook에서 quick check, cluster, monitoring, application, CronJob,
  first-response troubleshooting, routine checklist를 분리했다.
- Task에 명시된 공통 장애 유형의 1차 대응 순서를 모두 포함했다.
- Application source, DB, K3s manifest, runtime script는 변경하지 않았다.
- Approved fixes는 없으며 fix-specific verification도 없다.
- Production read-only check와 Grafana UI 확인은 수행하지 않았으며
  pending이다.

## 이번 단계의 의미

- NewsLab의 운영 상태를 개별 명령 실행이 아니라 일관된 판단 흐름과 기록
  양식으로 확인할 수 있게 되었다.
- 장애 대응 전에 필요한 read-only 증거 수집 순서를 표준화했다.
- Cluster, monitoring, API, scheduled workload를 하나의 운영 판단 흐름으로
  연결해 장기 운영 시 반복 가능한 점검 기반을 마련했다.

## 포트폴리오용 요약

- K3s 기반 뉴스 처리 플랫폼의 cluster, observability, API, batch workload
  상태를 한 번에 점검할 수 있는 운영 Runbook을 설계했다.
- `kubectl get/top/describe/logs`, Grafana/Prometheus dashboard, health/status
  API를 연결해 정상 판단 기준과 장애별 read-only 진단 순서를 정의했다.
- Node NotReady, Pod Pending/CrashLoopBackOff/OOMKilled, API 장애, CronJob
  실패, monitoring 장애에 대한 first-response 절차를 표준화했다.
- Production-impacting action과 진단 단계를 분리하고, sanitized evidence
  checklist를 도입해 운영 안전성과 기록 가능성을 높였다.

## 다음 단계 후보

- Human operator가 Runbook을 사용해 실제 정기 점검을 수행하고 sanitized
  verification 기록을 남긴다.
- 실제 Grafana UI에서 bundled dashboard 이름과 현재 metrics 표시를
  확인한다.
- 실제 운영에서 반복되는 판단 기준이나 누락 항목이 확인되면 별도 task로
  Runbook을 보완한다.
- Runbook 분량이 계속 증가하면 `docs/runbooks/` 하위 문서 분리를 검토한다.
- User-facing operations 안내가 필요해질 때 README Runbook 링크를 다시
  검토한다.
