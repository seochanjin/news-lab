# Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## 작업 목적

현재 `kube-prometheus-stack`의 Repository 설정과 Production에서 실제 수집되는
Kubernetes metric을 근거로, 네 NewsLab Pipeline과 세 Node의 운영 상태를 한
화면에서 확인하는 `NewsLab Pipeline Operations` Dashboard를 구성하는 작업이다.

추측한 metric이나 DB 조회를 섞지 않고 실제 Prometheus에서 metric, label,
cardinality와 PromQL을 검증한 뒤 Dashboard에 반영하는 것을 완료 기준으로 삼았다.

## 기존 문제

- Repository values만으로는 chart 기본 Grafana sidecar, Production retention,
  storage/PVC와 target 상태를 구분하기 어려웠다.
- CronJob owner 관계만 사용하면 같은 owner를 가진 prewarm Job 3개가 정기 Job
  결과에 포함됐다.
- `kube_cronjob_status_last_successful_time`은 prewarm 성공에도 갱신돼 정기 실행의
  최근 성공 시각으로 사용할 수 없었다.
- Unix seconds를 Grafana DateTime에 그대로 전달해 실제 시각 대신 1970년대 값이
  표시되는 문제가 있었다.
- CPU·Memory·Restart query가 넓은 container series를 먼저 읽고 뒤에서 owner
  join을 수행해 동시 실행 시 최대 `106.702s`까지 느려졌다.
- Grafana data proxy가 약 30초에 query를 종료해 Prometheus가 정상 계산 중이어도
  빨간 query warning과 `status=400`이 발생했다.
- 정상적인 empty result와 query 오류가 모두 `No data`로 보일 수 있어 운영자가
  의미를 구분할 기준이 필요했다.
- Kubernetes metric만으로는 `partial_success`, DB run status와 Pipeline 내부
  처리 건수·단계별 duration을 설명할 수 없었다.

## 변경 내용

- chart `86.2.0` 기준 Grafana sidecar/provider, Prometheus replica `1`, retention
  `1d`, PVC template 부재와 Monitoring placement를 조사하고 문서화했다.
- 4개 row와 활성 Prometheus target 20개로 구성된 Dashboard JSON을 추가했다.
- 기존 sidecar가 감시하는 `grafana_dashboard: "1"` label을 사용하는 최소
  Kustomize ConfigMap generator를 추가했다.
- 정기 Job과 Pod를 숫자 suffix canonical filter로 제한해 prewarm 실행을
  제외했다.
- filtered Job `completion_time`, `succeeded`와 owner join으로 최근 정기 성공
  시각을 계산했다.
- 모든 target을 Instant 전용으로 고정하고 DateTime panel 세 개의 seconds 값을
  milliseconds로 변환했다.
- CPU·Memory·Restart 원본 metric에 정기 Pipeline Pod selector를 조기 적용했다.
- Dashboard 자동 refresh를 `15m`, Grafana data proxy timeout을 `120s`로
  설정했다.
- Grafana CPU limit을 Production baseline과 같은 `200m`으로 정합화해 전체 values
  적용 시 의도하지 않은 resource drift를 방지했다.
- Dashboard 설계, Monitoring runbook과 Architecture/Runbook index를 연결하고
  No data, retention과 업무 metric 한계를 기록했다.

## 구현 상세

### 정기 Job과 prewarm 구분

Production의 `kube_job_owner` 대상 Job 12개 중 3개는 prewarm Job이었다. 이들도
`owner_kind="CronJob"`과 같은 `owner_name`을 가지므로 owner join만으로 제외할 수
없었다. 정기 실행에는 다음 숫자 suffix filter를 사용했다.

```promql
job_name=~"news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)-[0-9]+"
```

Pod query는 `kube_pod_owner → kube_job_owner` join으로 `pod`, `job_name`,
`cronjob` label을 전달하고 같은 canonical 정기 범위를 유지했다. Production에서
정기 Job과 Pod가 각각 9개였고 prewarm이 제외됨을 확인했다.

### Dashboard query 의미

- CPU: 순간 peak가 아니라 최근 24시간 내 Pipeline별 최대 5분 평균, unit `cores`
- Memory: container별 `max_over_time(...[24h])` 후 Pod별 합산, unit bytes IEC
- Restart: Dashboard 선택 범위의 정기 Pod별 증가량
- Running Pods: `phase="Running" == 1`과 `kube_pod_info` join으로 Completed Pod 제외
- Filesystem: ext4 root mount만 포함하고 Kubernetes Node 이름으로 mapping
- DateTime: metric의 Unix seconds 최종 결과에 `1000 *` 적용

현재 active Job, Pending, scheduling false와 waiting reason은 조건에 맞는 series가
없으면 일반 `No data`가 정상적으로 나올 수 있다. `or vector(0)`으로 이를 숨기지
않으며 빨간 query warning이 있는 datasource/query 오류와 구분한다.

### query 실행과 Grafana 설정

활성 target 20개는 stat/table panel의 현재 결과 또는 PromQL 내부 기간 집계만
필요하므로 `instant=true`, `range=false`로 설정했다. CPU·Memory·Restart selector는
owner join 전에 정기 Pod regex를 적용해 원본 series 범위를 줄였다.

Prometheus runtime query timeout `2m`은 유지하고, 먼저 요청을 끊던 Grafana data
proxy timeout만 `120s`로 늘렸다. 계산량이 큰 24시간 query의 반복 경합을 줄이기
위해 자동 refresh는 `5m` 대신 `15m`을 사용했다.

## 대안 검토

- CronJob owner join만 사용: prewarm도 같은 owner를 가져 제외할 수 없어 채택하지
  않았다.
- `kube_cronjob_status_last_successful_time` 사용: Weekly 값이 prewarm 성공으로
  갱신된 실제 차이를 확인해 정기 성공 시각 panel에는 사용하지 않았다.
- empty result 전체에 `or vector(0)` 추가: scrape 장애나 label mismatch까지 정상
  `0`으로 숨길 수 있어 적용하지 않았다.
- 수동 JSON import 또는 새로운 범용 provisioning framework: 기존 chart sidecar
  경로가 이미 있어 최소 Kustomize ConfigMap generator를 선택했다.
- Prometheus `query.timeout`, max samples, concurrency 증가: 느린 query의 자원
  점유를 늘릴 수 있고 현재 병목 근거와 맞지 않아 변경하지 않았다.
- Grafana CPU limit 증설: saturation 근거가 없고 Production은 처음부터 `200m`을
  사용해 증설 대신 Repository drift만 정합화했다.
- recording rule 도입: selector 최적화와 timeout 완화 후 성능 gate를 통과했으므로
  후속 최적화로 분리했다.
- DB datasource 또는 임의 custom metric 추가: Kubernetes metric만 사용한다는
  범위를 벗어나며 검증되지 않은 업무 의미를 만들 수 있어 제외했다.

## 선택한 접근과 근거

기존 Grafana sidecar와 Prometheus datasource를 그대로 사용하고, Production에서
검증한 canonical owner join과 숫자 suffix filter를 Dashboard JSON에 직접
반영했다. 별도 exporter나 provisioning framework 없이 review 가능한 artifact 두
개(JSON과 Kustomization)만 추가할 수 있기 때문이다.

성능 문제는 원본 metric selector를 조기에 좁히고 Instant query 중복을 제거한 뒤
Grafana proxy timeout을 Prometheus 제한과 같은 `120s` 범위로 맞췄다. 수정 후
네 무거운 query의 동시 실행이 3회 모두 필수 `120s`와 권장 `90s` gate를 통과해
선택 근거를 Production 결과로 확인했다.

## 트레이드오프

- 숫자 suffix filter는 현재 CronJob controller naming과 명확히 맞지만 이름 규칙이
  바뀌면 query도 함께 갱신해야 한다.
- refresh `15m`은 Prometheus 경합을 줄이는 대신 화면 최신성이 5분 설정보다
  느리다. 하루 단위 CronJob 운영 화면이라는 성격을 우선했다.
- retention `1d`와 persistent storage 부재로 장기 성공률, 월간 추세와 SLO를
  보장하지 않는다.
- Weekly CPU/Memory는 최근 실행이 24시간 밖이면 `No data`가 될 수 있으며 이를
  `0`이나 정상 상태로 단정하지 않는다.
- kube-state-metrics는 보존 중인 Kubernetes object 상태만 제공하므로 삭제된 Job
  이력과 업무 수준 `partial_success`를 복원할 수 없다.
- ConfigMap 하위 Kustomization은 현재 non-recursive Argo CD Application에 자동
  포함되지 않아 사람 통제 Production 적용 경로를 유지한다.

## 테스트

- Monitoring YAML parse: 통과
- Dashboard JSON parse와 target/panel assertion: 통과
- Kustomize ConfigMap render와 embedded JSON 검증: 통과
- kube-prometheus-stack chart `86.2.0` Helm render와
  sidecar/resources/timeout assertion: 통과
- Dashboard namespace/datasource scope, 금지 업무 metric·DB datasource scan:
  통과
- Alertmanager와 `PrometheusRule` 미추가 확인: 통과
- 전체 pytest: `445 passed, 91 subtests passed`
- `git diff --check`: 출력 없음
- Production Prometheus 활성 target: `20 passed / 0 failed`
- 수정 후 네 무거운 query 동시 실행 3회: 모두 status `success`, 오류 없음,
  필수 `120s` 및 권장 `90s` gate 통과
  - Round 1 최대 `79.418s`, total wall `79.420s`
  - Round 2 최대 `47.378s`, total wall `47.382s`
  - Round 3 최대 `50.882s`, total wall `50.885s`

## 운영 반영

운영자가 제공한 sanitized evidence에 따르면 Dashboard ConfigMap 적용, chart
`86.2.0` Helm Revision 3 배포와 Grafana rollout이 성공했다. 실제 Grafana에는
data proxy timeout `120s`, 자동 refresh `15m`, requests `50m`/`256Mi`, limits
`200m`/`512Mi`가 적용됐고 API health가 정상이었다.

운영자는 노출 가능성이 있던 기존 Grafana admin password를 회전하고 임시 patch
파일과 shell password 변수를 제거했다. 실제 password, Base64와 Secret 값은 이
문서에 기록하지 않는다. Agent는 apply, Helm upgrade, rollout, Secret 조회·변경을
실행하지 않았다.

## README 업데이트 판단

`README.md`는 변경하지 않았다. 공개 API, application 실행법이나 개발자 onboarding
흐름은 달라지지 않았고, 이번 변경의 대상은 Monitoring 운영 artifact와 절차다.
대신 기존 문서 구조에 맞춰 `docs/ARCHITECTURE.md`에서 Dashboard 설계를,
`docs/RUNBOOK.md`에서 Monitoring runbook을 찾을 수 있도록 연결했다.

## 확인 결과

- `NewsLab Pipeline Operations`가 Production Grafana에서 4개 row와 기존 query
  panel 구조로 정상 로드됐다.
- CronJob 4개와 실제 2026년 KST schedule/completion timestamp가 표시됐다.
- active/failure는 `0`, 보존된 정기 Pod의 restart는 모두 `0`으로 표시됐다.
- Daily/RSS/3-day CPU는 약 `0.0294`/`0.00445`/`0.0919` cores, Memory는
  `76.8`/`40.6`/`112` MiB로 확인됐다.
- expected empty-result panel은 빨간 경고 없는 일반 `No data`였고, query warning은
  재발하지 않았다.
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`가 모두 Ready였으며 Node
  이름 mapping과 CPU/Memory/Running Pods/root filesystem 표시가 정상이었다.
- 기존 약 30초 `/api/ds/query status=400`, `context canceled`,
  `deadline exceeded` 형태는 rollout 후 재현되지 않았다.
- UNIT-01~06과 전체 Verification Status는 `passed`다.

## 이번 단계의 의미

Kubernetes object 상태와 cAdvisor/node-exporter resource metric을 실제 운영
cardinality에 맞춰 결합해 Pipeline 운영 화면을 만들었다. 특히 prewarm과 정기
실행을 분리하고, No data를 오류 없이 정상으로 포장하지 않는 관찰 가능성 경계를
확립했다.

동시에 Dashboard가 답할 수 없는 업무 상태를 명시해 Kubernetes 성공/실패와
NewsLab의 `partial_success`를 혼동하지 않도록 했다. 이 결과는 Dashboard 1차
운영 기준이자 76차 Alerting·custom telemetry 설계의 입력이다.

## 포트폴리오용 요약

K3s의 kube-prometheus-stack 환경에서 CronJob 기반 데이터 Pipeline 운영
Dashboard를 설계·구현했다. 실제 Production metric inventory와 label cardinality를
검증해 CronJob→Job→Pod 관계를 PromQL로 모델링하고, prewarm 실행을 canonical
filter로 분리했다. 20개 query를 Production에서 전수 검증했으며 selector 조기
필터, Instant query와 Grafana timeout/refresh 조정으로 동시 query 3회 모두 90초
권장 gate를 통과시켰다. Dashboard provisioning, Secret 경계와 사람 통제 운영
절차까지 문서화하고 Production UI 검증으로 마무리했다.

## 다음 단계 후보

- Grafana Elasticsearch bundled plugin 설치 permission 오류 점검
- Prometheus recording rule 기반 무거운 query 추가 최적화
- Alertmanager/PrometheusRule, threshold, `for`와 notification route 설계·구현
- `partial_success`, DB run status, candidate/embedding/topic count, stage duration와
  summary provider 오류를 위한 custom business metric 추가
- Prometheus retention/PVC/storage 개선

위 항목은 이번 Dashboard 1차 완료를 막지 않는 별도 후속 작업이다. 장애 주입,
Alerting 구현과 custom business metric 검증은 이번 브랜치에서 수행하지 않았다.
PR merge, git push와 git merge도 완료로 주장하지 않는다.
