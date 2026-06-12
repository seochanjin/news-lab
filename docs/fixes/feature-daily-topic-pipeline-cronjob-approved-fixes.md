# Approved Fixes: Daily Topic Pipeline CronJob 자동화

## Approved Fixes

Antigravity review 단계에서는 PR 제출 전 반드시 수정해야 하는 blocking issue가 발견되지 않았다.

다만 merge 이후 human-controlled 운영 반영 및 첫 scheduled run 확인 과정에서 `news-daily-topic-pipeline` Job이 장시간 `Running` 상태로 남는 문제가 관찰되었다. 이에 따라 운영 관찰 결과를 근거로 아래 후속 fix를 승인한다.

---

### Fix 1: CronJob 실행 시간 제한 추가

#### Background

`news-daily-topic-pipeline` CronJob은 첫 scheduled run에서 04:00 KST에 정상 trigger되었고 Pod 생성, Secret env 주입, image 내 script 존재까지 확인되었다.

확인된 상태:

- CronJob schedule trigger: 성공
- Pod 생성: 성공
- Secret env reference 주입: 성공
- `scripts/run_daily_topic_pipeline.py` image 내 존재 확인: 성공
- Pod 상태: `Running`
- Job 상태: 5시간 이상 `Running`
- `kubectl logs`: 출력 없음
- production `/topics`: 신규 저장 row 확인되지 않음
- stuck Job은 human-controlled 명령으로 삭제 완료

현재 manifest에는 `backoffLimit: 1`만 존재한다. `backoffLimit`은 실패 후 재시도 횟수를 제한하지만, 프로세스가 종료되지 않고 계속 실행되는 경우 Job을 시간 기준으로 실패 처리하지 않는다.

#### Approved Change

`k8s/news-daily-topic-pipeline-cronjob.yaml`의 `jobTemplate.spec`에 `activeDeadlineSeconds: 1800`을 추가한다.

예상 위치:

```yaml
jobTemplate:
  spec:
    activeDeadlineSeconds: 1800
    backoffLimit: 1
```

#### Expected Behavior

- daily topic pipeline Job이 30분 안에 완료되지 않으면 Kubernetes가 Job을 실패 처리한다.
- 장시간 hang 상태로 남아 cluster resource를 점유하거나 다음 schedule을 막는 상황을 줄인다.
- `concurrencyPolicy: Forbid`와 함께 동작해 중복 실행은 방지하되, 비정상 장기 실행 Job은 자동으로 종료된다.

---

### Fix 2: Python unbuffered logging 적용

#### Background

첫 scheduled run의 Pod는 5시간 이상 `Running` 상태였지만 `kubectl logs`에 출력이 없었다. Python stdout buffering으로 인해 pipeline 진행 상황 또는 hang 지점이 로그에 즉시 나타나지 않았을 가능성이 있다.

#### Approved Change

CronJob command를 `python` 실행에서 `python -u` 실행으로 변경한다.

현재:

```yaml
command:
  - python
  - scripts/run_daily_topic_pipeline.py
```

변경:

```yaml
command:
  - python
  - -u
  - scripts/run_daily_topic_pipeline.py
```

#### Expected Behavior

- Python stdout/stderr가 unbuffered mode로 출력된다.
- `kubectl logs`에서 pipeline 진행 상황 또는 실패 지점을 더 쉽게 확인할 수 있다.
- scheduled run 또는 manual Job 검증 시 운영 디버깅 가능성이 높아진다.

---

### Fix 3: Manifest test 보강

#### Background

기존 manifest static test는 schedule, command, Secret reference, safety setting을 검증했지만, 실행 시간 제한과 unbuffered logging 조건은 검증하지 않았다.

#### Approved Change

`tests/test_daily_topic_pipeline_cronjob_manifest.py`에 아래 조건을 추가 검증한다.

- `activeDeadlineSeconds: 1800`
- CronJob command에 `python`, `-u`, `scripts/run_daily_topic_pipeline.py` 순서가 포함됨
- 기존 bounded command 값은 유지됨
- 기존 Secret reference, resource, security, schedule 검증은 유지됨

#### Expected Behavior

- 향후 manifest 수정 시 timeout/logging 안전장치가 누락되는 것을 방지한다.

---

### Fix 4: Daily topic pipeline 단계별 progress logging 추가

#### Background

첫 scheduled run에서 Pod는 5시간 이상 `Running` 상태였지만 `kubectl logs` 출력이 비어 있었다. `python -u`를 적용하더라도 script 내부에 충분한 progress log가 없다면 hang 지점을 식별하기 어렵다.

#### Approved Change

`scripts/run_daily_topic_pipeline.py`에 secret-safe progress logging을 추가한다.

로그 범위:

- pipeline 시작/종료
- config 및 argument 요약
- article 조회 시작/종료와 대상 article count
- raw extraction state 조회 시작/종료와 state count
- raw text 조회 시작/종료와 raw text count
- embedding provider 호출 시작/종료
- topic candidate 생성 시작/종료와 candidate count
- selected topic count
- raw extraction 시작/종료와 대상 article id/count
- summary provider 호출 시작/종료
- DB write 시작/종료와 저장 topic count
- exception 발생 시 traceback 출력

로그에 포함하지 않을 것:

- `DATABASE_URL`
- `OPENAI_*_API_KEY`
- raw article full text
- credential, token, secret 값
- `.env` 전체 내용

#### Expected Behavior

- CronJob 또는 manual Job이 hang될 경우 `kubectl logs`로 마지막 진행 단계를 확인할 수 있다.
- DB 조회, provider call, raw extraction, DB write 중 어느 단계에서 멈췄는지 분리할 수 있다.
- pipeline 결과와 품질에는 영향을 주지 않는다.

---

### Fix 5: PR/task/review 문서 불일치 정리

#### Background

CodeRabbit review에서 일부 문서가 실제 PR 변경 내용과 맞지 않는다고 지적했다.

관찰된 불일치:

- PR 문서가 `scripts/run_daily_topic_pipeline.py`를 변경하지 않았다고 설명함
- PR 문서가 approved code/config fix가 없다고 설명함
- task 문서가 CronJob command를 `python scripts/run_daily_topic_pipeline.py`로 설명함
- review 문서가 `backoffLimit: 1`의 retry/cost risk를 과하게 표현함
- dependency-free test 설명과 선택적 PyYAML smoke check 설명이 섞여 있음

#### Approved Change

아래 문서를 실제 변경 내용에 맞게 수정한다.

- `docs/pr/feature-daily-topic-pipeline-cronjob.md`
  - pipeline script는 secret-safe progress logging을 위해 의도적으로 변경되었음을 명시한다.
  - approved fixes 문서에 Fix 1-5가 승인 및 적용되었음을 명시한다.
  - post-fix production verification은 pending임을 유지한다.

- `docs/tasks/feature-daily-topic-pipeline-cronjob.md`
  - command 설명을 `python -u scripts/run_daily_topic_pipeline.py`로 맞춘다.
  - 기존 bounded args는 변경하지 않는다.

- `docs/reviews/feature-daily-topic-pipeline-cronjob-antigravity.md`
  - `backoffLimit: 1`은 반복 실패 비용 리스크를 “원천 방어”하는 것이 아니라 “1회 재시도로 제한”하는 설정으로 표현한다.
  - 자동화된 committed unit test는 dependency-free text assertion이며, PyYAML parse는 선택적 로컬 smoke check임을 분리해 설명한다.

#### Expected Behavior

- task, PR, review, fixes 문서가 현재 구현 상태와 충돌하지 않는다.
- 이후 agent/reviewer가 오래된 “fix 없음 / script 변경 없음” 문장을 기준으로 오판하지 않는다.

---

## Rejected or Deferred Suggestions

- Commit SHA image tag 전환은 보류한다.
  - 현재 `news-api` Deployment도 `seocj/news-api:latest`와 `imagePullPolicy: Always` 패턴을 사용하고 있다.
  - 이번 작업은 기존 운영 image pattern을 재사용하는 CronJob 자동화가 목적이므로 image tag 전략 변경은 범위 밖이다.
  - 향후 CI/CD 안정화 단계에서 commit SHA 기반 image tag를 검토한다.

- `news-raw-extractor` CronJob suspend는 보류한다.
  - 신규 `news-daily-topic-pipeline` CronJob의 정상 manual/scheduled run을 먼저 확인해야 한다.
  - 기존 raw extractor suspend 여부는 daily topic pipeline 안정화 이후 human decision으로 판단한다.

- Pipeline 내부 HTTP timeout, raw extraction timeout, OpenAI request timeout 수정은 보류한다.
  - 이번 fix의 1차 목적은 CronJob 운영 안전장치와 로그 가시성 보강이다.
  - `activeDeadlineSeconds`와 `python -u` 적용 후에도 hang이 반복되면 script 내부 timeout을 별도 작업으로 다룬다.

- `max-topics`, `max-reference-topics`, threshold, provider model 변경은 보류한다.
  - 38차 수동 검증에서 사용한 운영값을 유지한다.
  - 이번 fix는 실행 안정성 보강이며 topic 품질/범위 조정은 별도 단계로 분리한다.

- non-root execution 적용은 보류한다.
  - 보안 hardening으로는 타당하지만, 현재 hotfix 범위는 장시간 Running 방지와 로그 가시성 확보다.
  - `runAsNonRoot`, `runAsUser`, `runAsGroup` 적용은 image file permission, runtime tmp/cache path, dependency 동작 검증이 필요하다.
  - 기존 `news-api` Deployment 보안 컨텍스트와의 일관성도 함께 검토해야 하므로 별도 hardening 작업으로 분리한다.

- Manifest test를 완전한 YAML 구조 parser 기반으로 전환하는 것은 보류한다.
  - CodeRabbit 지적처럼 substring 기반 test는 구조 검증 한계가 있다.
  - 다만 현재 repository에는 PyYAML이 dependency로 선언되어 있지 않다.
  - 이번 hotfix에서는 기존 dependency-free test 정책을 유지하고, 구조 parser 도입은 별도 테스트 개선 작업으로 분리한다.
  - 대신 command, active deadline, Secret reference, bounded args에 대한 text assertion을 유지한다.

## Applied Changes

승인된 Fix 1-5를 적용했다.

- `k8s/news-daily-topic-pipeline-cronjob.yaml`
  - `jobTemplate.spec.activeDeadlineSeconds: 1800` 추가
  - command를 `python -u scripts/run_daily_topic_pipeline.py` 순서로 변경

- `tests/test_daily_topic_pipeline_cronjob_manifest.py`
  - 30분 deadline과 unbuffered command 순서 검증 추가
  - 기존 bounded command, Secret reference, resource/security, schedule 검증 유지

- `scripts/run_daily_topic_pipeline.py`
  - pipeline, article fetch, raw extraction state fetch, raw text fetch, embedding, topic candidate, selected topic, raw extraction, summary provider, DB write 단계별 secret-safe progress logging 추가
  - 중복된 `raw text fetch start` 로그 제거
  - `raw extraction state fetch end` 로그 추가
  - runtime exception 발생 시 traceback logging 후 exception 재발생

- `docs/RUNBOOK.md`
  - 30분 active deadline, unbuffered logging, 마지막 완료 단계 확인 절차 문서화

- `docs/pr/feature-daily-topic-pipeline-cronjob.md`
  - 실제 PR 변경 내용과 맞도록 summary 수정
  - pipeline script 변경 및 approved fixes 적용 사실 반영

- `docs/tasks/feature-daily-topic-pipeline-cronjob.md`
  - CronJob command를 `python -u scripts/run_daily_topic_pipeline.py`로 정정

- `docs/reviews/feature-daily-topic-pipeline-cronjob-antigravity.md`
  - retry/cost risk 표현 완화
  - dependency-free unit test와 선택적 PyYAML smoke check 설명 분리

- `docs/verification/feature-daily-topic-pipeline-cronjob.md`
  - 실제 실행한 local validation 결과와 pending human verification 기록

DB schema/migration, API, frontend, Dockerfile, GitHub Actions, 운영값, 기존 RSS/raw extractor CronJob, secret/credential은 변경하지 않는다.

## Verification Required

### Local/Codex Validation

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
```

검증 기준:

- Manifest focused tests 통과
- Full unittest discovery 통과
- `git diff --check` 통과
- 기존 application, DB, API, frontend, Dockerfile, GitHub Actions, 기존 RSS/raw extractor CronJob 변경 없음 확인

### Human-controlled Verification

수정 manifest 적용:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply \
  -f k8s/news-daily-topic-pipeline-cronjob.yaml \
  -n default

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-daily-topic-pipeline -n default
```

Manual Job 검증:

```bash
JOB_NAME="news-daily-topic-pipeline-manual-$(date +%Y%m%d%H%M%S)"

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-daily-topic-pipeline \
  "$JOB_NAME" \
  -n default

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get job "$JOB_NAME" -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default job/$JOB_NAME
```

Production read 확인:

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
```

검증 기준:

- Job이 장시간 `Running` 상태로 방치되지 않는다.
- `kubectl logs`에 pipeline 진행 또는 실패 정보가 출력된다.
- Job이 성공하거나, 30분 초과 시 실패 처리된다.
- 성공 시 production `/topics`에서 신규 topic row 또는 expected no-op 결과를 확인한다.
- 실패 시 logs와 Job 상태를 기준으로 후속 원인을 분리한다.

## Observed Production Issue

첫 scheduled run 관찰 결과:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-daily-topic-pipeline -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs -n default | grep daily-topic
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -l job-name=news-daily-topic-pipeline-29686740
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe pod news-daily-topic-pipeline-29686740-nsnvn -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default news-daily-topic-pipeline-29686740-nsnvn
```

결과:

- CronJob `news-daily-topic-pipeline`은 04:00 KST에 trigger되었다.
- Job `news-daily-topic-pipeline-29686740`은 5시간 이상 `Running` 상태였다.
- Pod `news-daily-topic-pipeline-29686740-nsnvn`은 `Running` 및 `Ready` 상태였다.
- Secret env reference는 정상 주입되었다.
- image 내 `/app/scripts/run_daily_topic_pipeline.py` 존재를 확인했다.
- `kubectl logs` 출력은 비어 있었다.
- production `/topics`에서 신규 row는 확인되지 않았다.
- stuck Job은 human-controlled 명령으로 삭제했다.

판정:

- CronJob 등록과 schedule trigger는 성공했다.
- Job completion과 DB write는 성공하지 못했다.
- 운영 안정성을 위해 `activeDeadlineSeconds`, unbuffered logging, 단계별 progress logging 보강이 필요하다.
