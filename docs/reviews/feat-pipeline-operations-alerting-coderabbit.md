# CodeRabbit Review: Alertmanager 활성화 및 Pipeline 핵심 Alert 3종 전달 검증

## Review Summary

PR #64에 대해 CodeRabbit은 **actionable comment 2개**를 남겼다. 두 finding 모두 `Minor`, `Quick win` 등급이며, Alertmanager·PrometheusRule·Telegram receiver·Secret 주입·Production 전달 경로의 기능 오류는 지적되지 않았다.

Pre-merge check 5개도 모두 통과했다. 이번 리뷰에서 병합 전에 처리할 내용은 다음 두 가지 문서 정합성 문제다.

1. Task 문서의 language가 없는 fenced code block에 `text` identifier를 추가한다.
2. Task의 PrometheusRule 정적 검증 절차가 운영 Alert 파일만 언급하는 문제를 수정해, 운영 Alert 3종과 전달 test Alert 1종을 모두 검증하도록 문서화한다.

두 번째 finding은 **실제 검증 누락이 아니라 Task의 예시 명령이 최종 Verification evidence와 일치하지 않는 문제**다. 실제 Verification에서는 두 `PrometheusRule`의 `spec.groups`를 native rule 파일로 추출한 뒤 Production과 동일한 Prometheus `v3.12.0-distroless` 이미지의 `promtool`로 3개 운영 Rule과 1개 test Rule을 모두 검증해 통과했다.

## Problems Found

### 1. Task의 fenced code block에 language identifier가 없음

대상:

- `docs/tasks/feat-pipeline-operations-alerting.md`
- 전달 경로 다이어그램
- Expected files 목록

현재 형태:

````text
```
PrometheusRule
→ Prometheus evaluation
→ Alertmanager route
→ receiver
→ 실제 firing 알림 수신
→ resolved 알림 수신
```
````

그리고 Expected files 목록도 동일하게 language 없는 fence를 사용한다.

영향:

- markdownlint `MD040 fenced-code-language` 경고 발생
- 문서 렌더링과 syntax highlighting 품질 저하
- 런타임, PromQL, Kubernetes manifest에는 영향 없음

수정 방향:

- 두 fence 시작을 `` ```text ``로 변경
- fence 내부 내용은 변경하지 않음
- shell, YAML 등 이미 language가 지정된 다른 fence는 유지

### 2. Task의 PrometheusRule 정적 검증 절차가 test Rule을 포함하지 않음

대상:

- `docs/tasks/feat-pipeline-operations-alerting.md`
- `PrometheusRule 정적 검증` section

현재 문서 예시:

```bash
promtool check rules \
  k8s/monitoring/rules/news-lab-pipeline-alerts.yaml
```

문제:

- `news-lab-alert-delivery-test.yaml`이 별도 artifact로 존재하지만 Task 예시 명령에는 포함되지 않는다.
- test Rule은 기본 Kustomization에서 의도적으로 제외되므로 Kustomize render만으로는 검증되지 않는다.
- `promtool check rules`는 Prometheus native rule 형식의 `groups`를 검사하므로, `PrometheusRule` CRD 전체 파일을 그대로 넘기는 방식보다 각 CRD의 `spec.groups`를 임시 native rule 파일로 추출하는 절차가 정확하다.
- 최종 Verification에서는 이미 운영 Rule과 test Rule을 모두 추출해 검증했으므로 실제 품질 문제가 아니라 Task 명령과 evidence의 불일치다.

수정 방향:

1. 두 `PrometheusRule` CRD에서 `spec.groups`를 각각 임시 YAML로 추출한다.
2. Production과 동일한 Prometheus 이미지 또는 local `promtool`로 두 파일을 함께 검사한다.
3. `--lint=all --lint-fatal`을 사용해 실제 수행 evidence와 맞춘다.
4. 임시 파일을 삭제한다.

검증 대상:

- `news-lab-pipeline-alerts.yaml` → 실제 운영 Alert 3종
- `news-lab-alert-delivery-test.yaml` → 전달 test Alert 1종

### 3. Review와 Approved Fixes artifact가 placeholder 상태

대상:

- `docs/reviews/feat-pipeline-operations-alerting-coderabbit.md`
- `docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md`

두 파일은 현재 제목과 section heading만 있고 실제 내용이 없다.

영향:

- PR #64에서 수행된 review와 승인 결정의 audit evidence가 Repository 문서에 남지 않는다.
- PR 설명의 `Approved Fixes 문서에는 적용 대상으로 승인된 finding이 없다`는 문구가 현재 CodeRabbit actionable comment 2개와 맞지 않게 된다.

수정 방향:

- 이 CodeRabbit Review 내용을 review artifact에 반영한다.
- 승인된 두 finding과 적용 범위, 보류 항목, 검증 절차를 Approved Fixes artifact에 반영한다.
- 실제 적용 전에는 `Applied Changes`를 미적용 상태로 명확히 기록하고, 수정 후 결과로 갱신한다.

## Required Fixes Before PR

### FIX-01. Task의 unlabeled fence 2개에 `text` 추가

파일:

- `docs/tasks/feat-pipeline-operations-alerting.md`

필수 변경:

- 전달 경로 다이어그램 fence를 `text`로 지정
- Expected files 목록 fence를 `text`로 지정

완료 기준:

- 대상 파일에 language 없는 fence가 없음
- markdownlint `MD040` 경고 없음
- fence 내부 내용과 문서 의미는 동일

### FIX-02. 운영 Rule과 전달 test Rule을 모두 검증하도록 Task 명령 정정

파일:

- `docs/tasks/feat-pipeline-operations-alerting.md`

필수 변경:

- 운영 `PrometheusRule`만 직접 검사하는 기존 예시를 제거하거나 보완
- 두 CRD의 `spec.groups`를 임시 native rule 파일로 추출
- 두 임시 파일을 동일한 `promtool check rules` 실행에서 함께 검사
- `--lint=all --lint-fatal` 적용
- Production workload를 변경하지 않는 local/container 검증임을 유지

완료 기준:

- 운영 Alert 3종과 test Alert 1종 모두 문서상 검증 대상
- Verification의 최종 성공 evidence와 Task의 예시 절차가 일치
- test Rule이 기본 Kustomization에서 제외되는 운영 경계는 유지

### FIX-03. CodeRabbit Review와 Approved Fixes artifact 작성

파일:

- `docs/reviews/feat-pipeline-operations-alerting-coderabbit.md`
- `docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md`

필수 변경:

- 실제 PR #64 review 결과와 승인 결정을 각 지정 format에 맞게 기록
- 존재하지 않는 기능 오류나 Production evidence를 추가하지 않음
- 수정 적용 후 `Applied Changes`와 검증 결과를 실제 결과로 갱신

## Optional Improvements

### 1. PR 설명의 Approved Fixes 문구 정합화

현재 PR 설명은 승인된 finding이 없다고 기록하지만 CodeRabbit actionable comment 2개가 생성됐다. 수정 커밋 후 다음 의미로 정정하는 것이 적절하다.

- CodeRabbit minor finding 2개를 승인해 문서만 수정
- Alertmanager·Rule·Telegram 구현 변경 없음
- Production 재적용 없음

### 2. CodeRabbit review thread 정리

수정 커밋 후 두 inline thread에서 현재 diff를 확인하고 resolve한다.

### 3. Markdown fence 검사를 전체 76차 문서로 확장

이번 필수 범위는 Task의 두 fence지만, 같은 branch의 Review·Approved Fixes 문서를 새로 채운 뒤 language 없는 fence가 추가되지 않았는지 함께 검사한다.

### 4. Generic unit-test 생성 제안은 적용하지 않음

CodeRabbit의 Finishing Touches에 표시된 unit-test 생성은 일반적인 선택 기능이다. 이번 finding은 문서 lint와 검증 절차 정합성 문제이므로 새 application test나 별도 PR을 만들 필요가 없다.

## Suggested Test Commands

### Task Markdown fence 확인

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

### 두 PrometheusRule의 native rule 추출

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

### Production 동일 Prometheus 이미지로 두 artifact 검증

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

임시 파일 정리:

```bash
rm -f \
  /tmp/news-lab-pipeline-alerts.rules.yaml \
  /tmp/news-lab-alert-delivery-test.rules.yaml
```

### Kustomize 운영 경계 확인

```bash
kubectl kustomize k8s/monitoring/rules |
rg 'alert:|NewsLabAlertDeliveryTest'
```

기대 결과:

- 실제 Alert 3종만 출력
- `NewsLabAlertDeliveryTest` 미출력

### 문서와 scope 검증

````bash
rg -n \
  'news-lab-alert-delivery-test|promtool|lint-fatal|MD040|```text' \
  docs/tasks/feat-pipeline-operations-alerting.md \
  docs/reviews/feat-pipeline-operations-alerting-coderabbit.md \
  docs/fixes/feat-pipeline-operations-alerting-approved-fixes.md

git diff --check
PYTHONPATH=. pytest -q
````

## Risk Notes

- 이번 finding은 문서 lint와 검증 절차 정합성 문제다. Alertmanager, Telegram receiver, Secret, 실제 Alert 3종의 PromQL을 수정하면 scope가 불필요하게 확대된다.
- `promtool check rules`에 `PrometheusRule` CRD 전체 YAML을 그대로 전달하지 않는다. `spec.groups`를 native rule 파일로 추출해야 실제 검증과 일치한다.
- test Rule은 계속 기본 Kustomization에서 제외해야 한다. 검증 범위를 넓힌다는 이유로 운영 배포 경로에 포함하면 안 된다.
- Production Helm upgrade, Secret 변경, `kubectl apply/delete`, firing·resolved 전달 테스트를 다시 수행할 필요가 없다. 기존 sanitized evidence를 유지한다.
- fenced code block에는 내용에 맞는 language를 지정하되, fence 경계나 내부 명령을 훼손하지 않는다.
- Review와 Approved Fixes 문서에는 실제 CodeRabbit finding만 기록하고, 미확인 Production 문제를 추가하지 않는다.
