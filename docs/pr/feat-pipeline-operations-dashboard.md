# Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## 작업 내용

- 현재 `kube-prometheus-stack`의 Repository 설정과 Production 수집 상태를
  조사하고, 네 NewsLab Pipeline과 세 Kubernetes Node를 확인하는
  `NewsLab Pipeline Operations` Dashboard를 구성했습니다.
- Production에서 노출되는 CronJob, Job, Pod, Container와 Node metric 및 label
  관계를 확인하고 실제 Prometheus에서 검증한 PromQL만 사용했습니다.
- 기존 Grafana sidecar가 감시하는 `grafana_dashboard: "1"` label 기반의 최소
  Kustomize ConfigMap provisioning artifact를 추가했습니다.
- Kubernetes metric으로 확인할 수 없는 업무 metric 7개와 76차 Alerting 후보를
  문서화했습니다.
- Approved Fix 1~8을 적용하고 local 회귀, Production Prometheus query와 운영자
  Grafana UI 검증까지 완료했습니다.

## 주요 변경 사항

- Dashboard에 Pipeline Overview, Job Status, Pipeline Pod Resources와 Cluster
  Nodes의 4개 row 및 활성 Prometheus target 20개를 구성했습니다.
- Dashboard 기본 범위를 최근 24시간, timezone을 `Asia/Seoul`, 자동 refresh를
  `15m`으로 설정했습니다.
- CronJob owner만으로 제외되지 않는 prewarm 실행은 숫자 suffix canonical
  Job/Pod filter로 제외했습니다.
- 최근 정기 성공 시각은 prewarm의 영향을 받는 CronJob
  `lastSuccessfulTime` 대신 filtered Job의 `completion_time`과 `succeeded` join으로
  계산했습니다.
- 모든 target을 Instant 전용으로 설정하고, 세 DateTime panel의 Unix seconds를
  Grafana가 기대하는 milliseconds로 변환했습니다.
- CPU·Memory·Restart 원본 metric에 정기 Pipeline Pod selector를 조기 적용해
  조회 범위를 줄였습니다. CPU panel은 순간 peak가 아니라 최근 24시간 내 최대
  5분 평균입니다.
- 정상 empty result를 `0`으로 숨기지 않고 일반 `No data`와 빨간 query error를
  구분했습니다. Weekly resource `No data`는 실행 후 24시간 초과와 Prometheus
  retention `1d` 제약에 따른 예상 결과일 수 있습니다.
- Grafana data proxy timeout을 `120s`로 설정해 기존 약 30초 query 종료 문제를
  해결했습니다.
- Grafana CPU limit을 Production baseline에 맞춰 `300m`에서 `200m`으로
  정합화했습니다. 이는 query 성능 개선이 아니라 전체 values 적용 시 비의도적
  resource drift를 방지하기 위한 변경입니다.
- Dashboard 설계, Monitoring runbook, Architecture/Runbook index, Task,
  Verification과 운영 기록을 실제 검증 결과에 맞춰 갱신했습니다.

## 추가/변경된 API

없습니다.

- FastAPI endpoint와 `/metrics`를 추가하거나 변경하지 않았습니다.
- request/response schema, 인증 및 권한 정책 변경이 없습니다.
- Dashboard datasource는 Prometheus만 사용하며 application API나 DB를 metric
  source로 사용하지 않습니다.

## DB 변경 사항

없습니다.

- schema, migration, table, column, index와 constraint 변경이 없습니다.
- Supabase SQL이나 Production 데이터 변경을 수행하지 않았습니다.
- DB run 상태는 Kubernetes metric으로 추정하지 않고 후속 custom metric 또는
  exporter 후보로 남겼습니다.

## README 영향

`README.md` 변경은 필요하지 않습니다. 이번 변경은 backend 사용법이나 공개 API가
아닌 Monitoring 운영 artifact와 절차에 한정되며, 진입점은 기존 문서 체계에 맞춰
`docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`에 연결했습니다.

## 테스트

- Monitoring YAML parse: 통과
- Dashboard JSON parse와 panel/target assertion: 통과
- Kustomize ConfigMap render와 embedded Dashboard JSON 검증: 통과
- kube-prometheus-stack chart `86.2.0` Helm render 및 Grafana sidecar/resources/
  timeout assertion: 통과
- Dashboard 구조, namespace/datasource scope, 금지 업무 metric과 DB datasource
  scan: 통과
- Alertmanager와 `PrometheusRule` 미추가 확인: 통과
- 전체 pytest: `445 passed, 91 subtests passed`
- `git diff --check`: 출력 없음
- Production Prometheus 활성 target: `20 passed / 0 failed`
- 수정 후 네 무거운 query 동시 실행 3회: 모두 query status `success`, 오류 없음,
  필수 `120s` 및 권장 `90s` gate 통과
  - Round 1 최대 `79.418s`, total wall `79.420s`
  - Round 2 최대 `47.378s`, total wall `47.382s`
  - Round 3 최대 `50.882s`, total wall `50.885s`

## 확인 결과

- 운영자가 Dashboard ConfigMap을 Production에 적용했고 chart `86.2.0`, Helm
  Revision 3가 `deployed` 상태이며 Grafana rollout이 완료됐음을 확인했습니다.
- Production Grafana에서 `NewsLab Pipeline Operations`가 4개 row와 기존 query
  panel 구조로 정상 로드됐고 빨간 query warning이 재발하지 않았습니다.
- CronJob 4개, 실제 2026년 KST timestamp, active/failure `0`, 정기 Pod별 restart
  `0`과 세 Node의 Ready/CPU/Memory/Running Pods/root filesystem이 정상
  표시됐습니다.
- 현재 active Job, Pending, scheduling false와 waiting reason panel은 빨간 경고
  없는 일반 `No data`로 표시됐습니다. 이는 query 실패가 아니라 현재 조건에
  일치하는 이상 상태가 없는 empty result입니다.
- Grafana data proxy timeout `120s`, 자동 refresh `15m`, requests
  `50m`/`256Mi`, limits `200m`/`512Mi`와 API health 정상 상태를 확인했습니다.
- 기존 `/api/ds/query status=400 duration=30s`, `context canceled`,
  `deadline exceeded` 형태의 장애는 rollout 후 재현되지 않았습니다.
- 운영자가 노출 가능성이 있던 기존 Grafana admin password를 회전하고 임시 patch
  파일과 shell password 변수를 제거했습니다. 실제 password, Base64와 Secret
  값은 이 PR 초안에 기록하지 않습니다.
- UNIT-01~06과 전체 Verification Status는 `passed`입니다.

## 비고

- Production 적용, Helm upgrade, Grafana rollout, password 회전과 UI 검증은
  운영자가 수행해 제공한 sanitized evidence를 근거로 기록했습니다. Agent는 해당
  Production 명령이나 Secret 조회·변경을 실행하지 않았습니다.
- PR merge, git push와 git merge는 수행하거나 완료로 주장하지 않습니다.
- Kubernetes Job 성공만으로 업무 수준 `partial_success`를 검증했다고 주장하지
  않습니다. custom business metric과 exporter는 추가하지 않았습니다.
- 장애 주입, Alertmanager/PrometheusRule, notification route는 구현하거나
  검증하지 않았습니다.
- Weekly CPU/Memory 데이터가 항상 존재한다고 보장하지 않습니다. 현재 retention
  `1d`와 persistent storage 부재 한계를 유지합니다.
- Grafana Elasticsearch bundled plugin 설치의 permission 오류는 Dashboard
  기능에 영향을 주지 않은 후속 점검 항목입니다.
- recording rule 기반 무거운 query 추가 최적화, Alerting 구현, custom business
  metric과 retention/PVC/storage 개선은 별도 후속 작업입니다.
