# Approved Fixes: Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## Approved Fixes

- [x] FIX-01: Task의 unlabeled fence 2개에 `text` 추가 및 MD040 검증
- [x] FIX-02: 운영 Rule과 전달 test Rule의 promtool 절차 정정 및 검증
- [x] FIX-03: Review와 Approved Fixes artifact 작성 및 문서 검증
- [x] FIX-04: PR 초안의 review 상태 정합화 및 Markdown 검증

### FIX-01. Task의 unlabeled fenced code block에 `text` identifier 추가

대상:

- `docs/tasks/feat-pipeline-operations-alerting.md`
- 전달 경로 다이어그램
- Expected files 목록

승인 이유:

- CodeRabbit의 markdownlint `MD040` finding이 현재 branch에서 재현된다.
- 두 block은 실행 코드가 아니라 구조와 파일 목록이므로 `text`가 가장 적절하다.
- 런타임 영향 없이 문서 품질을 개선하는 최소 변경이다.

승인 변경:

````text
```text
PrometheusRule
→ Prometheus evaluation
→ Alertmanager route
→ receiver
→ 실제 firing 알림 수신
→ resolved 알림 수신
```
````

Expected files 목록도 동일하게 `text` fence로 변경한다.

보존 조건:

- block 내부 문구와 파일 목록은 변경하지 않음
- 이미 `bash`, `yaml`, `text` 등이 지정된 다른 fence는 불필요하게 변경하지 않음

### FIX-02. 운영 Alert와 전달 test Alert를 모두 포함하는 promtool 절차로 Task 정정

대상:

- `docs/tasks/feat-pipeline-operations-alerting.md`
- `PrometheusRule 정적 검증` section

승인 이유:

- 현재 Task 예시는 운영 Alert 파일만 언급해 별도 test artifact의 정적 검증이 드러나지 않는다.
- 실제 최종 Verification에서는 운영 Alert 3종과 test Alert 1종을 모두 `promtool`로 검증했다.
- test Rule은 기본 Kustomization에서 제외되므로 별도 검증 절차를 명시해야 전체 전달 흐름의 artifact가 빠지지 않는다.

승인 변경:

1. `news-lab-pipeline-alerts.yaml`의 `spec.groups`를 임시 native rule 파일로 추출
2. `news-lab-alert-delivery-test.yaml`의 `spec.groups`도 별도 임시 native rule 파일로 추출
3. Production과 동일한 Prometheus `v3.12.0-distroless` 이미지 또는 호환 local `promtool`에서 두 파일을 함께 검사
4. `--lint=all --lint-fatal` 적용
5. 검증 후 임시 파일 삭제

보존 조건:

- test manifest 기본 expression은 firing 검증용 `vector(1)` 유지
- test Rule은 기본 `kustomization.yaml`에서 계속 제외
- 실제 Alert 3종의 PromQL, threshold, `for`, severity 변경 없음
- Production workload를 이용해 검증하지 않음

### FIX-03. CodeRabbit Review와 Approved Fixes artifact를 실제 review 결과로 작성

대상:

- `docs/reviews/feat-pipeline-operations-alerting-coderabbit.md`
- `docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md`

승인 이유:

- 현재 두 파일은 section heading만 있는 placeholder다.
- PR #64에는 actionable comment 2개가 존재하므로 `승인된 finding 없음` 상태와 맞지 않는다.
- review와 승인 결정 기록을 Repository에 남겨 이후 수정·검증 근거로 사용해야 한다.

승인 변경:

- CodeRabbit Review artifact에 Review Summary, Problems Found, Required Fixes Before PR, Optional Improvements, Suggested Test Commands, Risk Notes 작성
- Approved Fixes artifact에 Approved Fixes, Rejected or Deferred Suggestions, Applied Changes, Verification Required 작성
- 수정 전에는 Applied Changes를 미적용으로 표시하고, 실제 수정 후 변경 파일과 결과로 갱신

### FIX-04. PR 설명의 review 상태 정합화

대상:

- PR #64 description 또는 `docs/pr/feat-pipeline-operations-alerting.md`

승인 이유:

현재 문서에는 승인된 finding이 없다고 기록돼 있으나 CodeRabbit review 이후 actionable comment 2개가 존재한다.

승인 변경:

- CodeRabbit minor finding 2개 승인
- 변경 범위는 Task·Review·Approved Fixes·PR 문서
- Alertmanager·Rule·Telegram 구현 변경 없음
- Production 재검증 불필요

## Rejected or Deferred Suggestions

### 1. 두 PrometheusRule CRD 파일을 그대로 promtool 인자로 추가

판정: 부분 거절

CodeRabbit의 **두 artifact를 모두 검증하라**는 요구는 승인한다. 하지만 다음처럼 CRD 전체 파일 두 개를 직접 넘기는 방식은 최종 검증 방식과 맞지 않는다.

```bash
promtool check rules \
  k8s/monitoring/rules/news-lab-pipeline-alerts.yaml \
  k8s/monitoring/rules/news-lab-alert-delivery-test.yaml
```

`promtool check rules`가 검사하는 대상은 native rule file의 `groups`다. 따라서 각 `PrometheusRule`의 `spec.groups`를 임시 파일로 추출하는 방식으로 반영한다.

### 2. Alertmanager·Telegram receiver·실제 Alert 3종 수정

판정: 거절

CodeRabbit은 해당 구현에서 기능 오류를 지적하지 않았다. Production에서 firing·resolved 전달과 실제 Rule 3종의 `health=ok`, `inactive`가 이미 확인됐다. 문서 finding을 이유로 runtime 설정이나 PromQL을 변경하지 않는다.

### 3. test Rule을 기본 Kustomization에 포함

판정: 거절

검증 누락을 막기 위해 test Rule을 일반 배포에 포함하면 운영 경계가 깨진다. test Rule은 계속 명시적 human-controlled artifact로 유지하고 기본 Kustomization에서 제외한다.

### 4. CodeRabbit Finishing Touches의 unit-test 자동 생성

판정: 거절

이번 finding은 Markdown lint와 문서상 promtool 절차 문제다. application unit test를 추가하거나 별도 PR을 생성할 근거가 없다.

### 5. Production Helm·Secret·전달 테스트 재실행

판정: 거절

수정 대상은 문서뿐이다. 기존 Production evidence는 충분하며, Agent가 Secret을 조회하거나 Helm upgrade, `kubectl apply/delete`, Telegram firing·resolved 검증을 다시 수행하지 않는다.

### 6. kube-apiserver burnrate timeout 조사

판정: 별도 후속으로 보류

기존 chart 기본 `kube-apiserver-burnrate.rules`의 간헐적 evaluation timeout은 76차 비차단 관찰 사항이다. 이번 CodeRabbit finding과 무관하므로 retention, query timeout, resource, recording rule을 수정하지 않는다.

## Applied Changes

적용 완료 변경:

- `docs/tasks/feat-pipeline-operations-alerting.md`
  - 전달 경로와 Expected files fence에 `text` 추가
  - 운영 Rule과 test Rule의 `spec.groups` 추출 및 통합 promtool 검증 절차로 정정
- `docs/reviews/feat-pipeline-operations-alerting-coderabbit.md`
  - 실제 CodeRabbit actionable comment 2개와 검증·risk 내용을 지정 section에 작성
- `docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md`
  - 승인·거절·검증 결정과 fix checklist를 작성
- `docs/verification/feat-pipeline-operations-alerting.md`
  - FIX-01과 FIX-02의 실제 실행 command, 결과와 환경 제약을 기록
- `docs/pr/feat-pipeline-operations-alerting.md`
  - CodeRabbit minor finding 2개의 승인·적용 상태와 문서-only 범위를 반영

검증 결과:

- Task의 두 opening fence에 `text`를 추가했고 markdownlint에서 `MD040`이 없다.
- Prometheus `v3.12.0-distroless`의 `promtool`이 운영 Rule 3개와 test Rule 1개를
  `--lint=all --lint-fatal`로 통과했다.
- 기본 Kustomization에는 실제 Alert 3종만 포함되고 test Rule은 없다.
- test manifest의 기본 expression은 `vector(1)`이며 Alert Rule manifest tracked
  diff는 없다.
- CodeRabbit thread 확인·resolve는 commit 이후 사람 또는 별도 승인 작업으로 남긴다.
- PR 초안 markdownlint는 issue 없이 통과했다.
- 전체 pytest는 `445 passed, 91 subtests passed in 14.87s`로 통과했다.
- `git diff --check`, trailing whitespace, Markdown fence pairing과 credential value
  pattern 검사가 통과했다.
- runtime·Alert Rule scope의 tracked diff는 없고 변경 파일은 승인된 문서와 실제
  검증 기록뿐이다.
- Task·Review·Approved Fixes 전체 markdownlint에서 `MD040`은 없으며, 승인 범위
  밖의 기존 `MD013` line-length 32건만 남아 있다.
- Production command, Secret 조회·변경, commit, push와 merge는 수행하지 않았다.

## Verification Required

### 1. Markdown fence 검증

````bash
rg -n '^```$' \
  docs/tasks/feat-pipeline-operations-alerting.md
````

기대 결과:

- 출력 없음

markdownlint 사용 가능 시:

```bash
npx markdownlint-cli2 \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/reviews/feat-pipeline-operations-alerting-coderabbit.md \
  docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md
```

완료 기준:

- `MD040` 없음
- 새 review/fixes 문서의 fence도 language 지정

### 2. 운영 Rule과 전달 test Rule 추출

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
```

### 3. promtool 검증

```bash
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
```

기대 결과:

```text
Checking /rules/pipeline.rules.yaml
  SUCCESS: 3 rules found
Checking /rules/delivery-test.rules.yaml
  SUCCESS: 1 rules found
```

임시 파일 삭제:

```bash
rm -f \
  /tmp/news-lab-pipeline-alerts.rules.yaml \
  /tmp/news-lab-alert-delivery-test.rules.yaml
```

### 4. Kustomize 운영 경계 검증

```bash
kubectl kustomize k8s/monitoring/rules |
rg 'alert:|NewsLabAlertDeliveryTest'
```

완료 기준:

- `PipelineScheduleDelayed` 포함
- `PipelineScheduledJobFailed` 포함
- `NewsLabNodeNotReady` 포함
- `NewsLabAlertDeliveryTest` 미포함

### 5. 변경 범위 검증

```bash
git diff --name-only

git diff --name-only -- \
  k8s/monitoring/kube-prometheus-stack-values.yaml \
  k8s/monitoring/rules \
  app scripts db requirements.txt
```

기대 결과:

- 첫 명령에는 승인된 문서 파일만 표시
- 두 번째 명령은 출력 없음

### 6. 회귀와 whitespace 검증

```bash
PYTHONPATH=. pytest -q
git diff --check
```

기대 결과:

- 기존 전체 테스트 통과
- `git diff --check` 출력 없음

### 7. 민감정보와 Production 작업 금지 확인

확인 사항:

- Telegram Bot token과 Chat ID가 문서·diff에 없음
- Secret value 조회·decode 없음
- Helm upgrade, rollback 없음
- `kubectl apply`, patch, delete, rollout 없음
- Production firing·resolved 테스트 재실행 없음

### 8. Review thread 확인

수정 커밋 후 PR #64의 두 CodeRabbit inline thread에서 현재 diff를 확인하고 resolve한다. thread를 resolve하기 전 실제 branch에 변경이 반영됐는지 확인한다.
