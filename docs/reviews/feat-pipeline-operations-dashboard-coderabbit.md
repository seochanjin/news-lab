# CodeRabbit Review: Pipeline 운영 모니터링 현황 조사 및 Grafana Dashboard 1차 구성

## Review Summary

PR #63에 대해 CodeRabbit은 **actionable comment 3개**와 **nitpick 2개**를 남겼다.

전체 평가는 기능 구현 실패나 Production 장애가 아니라, 문서 렌더링과 기록 정합성 문제다. Dashboard JSON, PromQL, Helm values 자체의 런타임 오류는 지적되지 않았다. Pre-merge check 5개도 모두 통과했다.

병합 전에 처리할 핵심은 다음 세 가지다.

1. Markdown 표 안의 PromQL 정규식 `|`를 escape해 표 렌더링을 복구한다.
2. Kubernetes metric으로 확인할 수 없는 업무 metric 개수를 `7개` 또는 `8개` 중 하나로 통일한다.
3. Task의 변경 금지 계약에 Grafana CPU limit `300m → 200m` 정합화 예외를 명시한다.

추가로 CodeRabbit review 문서를 실제 내용으로 채우고, Antigravity placeholder를 정리하며, fenced code block에 language identifier를 추가하는 것이 권장된다.

## Problems Found

### 1. Alerting 후보 Markdown 표가 깨짐

대상:

- `docs/design/pipeline-operations-dashboard.md`
- `76차 Alerting 후보` 표의 `CronJob suspend`, `CronJob schedule 지연`, `정기 Job 실패` 행

원인:

PromQL 정규식 안의 alternation pipe가 다음처럼 escape되지 않았다.

```promql
news-(rss-collector|daily-topic-pipeline|three-day-topic-pipeline|weekly-topic-pipeline)
```

Markdown 표는 `|`를 열 구분자로 해석하므로, 코드 span 안의 pipe까지 별도 column으로 판단한다. CodeRabbit의 markdownlint 결과는 4개 column을 기대했지만 7개로 분석했다.

영향:

- 문서 표가 여러 열로 분리돼 일부 내용이 누락되거나 잘못 렌더링될 수 있다.
- PromQL 실행에는 영향이 없다. 해당 위치는 설계 문서의 inline code다.

수정 방향:

```promql
news-(rss-collector\|daily-topic-pipeline\|three-day-topic-pipeline\|weekly-topic-pipeline)
```

표 구분용 pipe는 그대로 두고, inline PromQL 내부의 pipe만 `\|`로 변경한다.

### 2. 미수집 업무 metric 개수가 문서마다 다름

대상:

- `docs/tasks/feat-pipeline-operations-dashboard.md`
- `docs/pr/feat-pipeline-operations-dashboard.md`

Task에는 다음 8개 항목이 열거돼 있다.

1. Pipeline `partial_success`
2. DB run table의 last success와 상세 status
3. candidate count
4. embedding created/reused/missing count
5. saved topic count
6. failed topic count
7. Pipeline stage별 duration
8. Summary provider 오류 수

반면 PR 요약은 `업무 metric 7개`라고 기록한다.

영향:

- 구현 범위와 후속 custom metric 범위가 문서마다 다르게 보인다.
- 이후 Task에서 누락 여부를 판단할 때 혼선이 생긴다.

권장 결정:

현재 목록이 8개의 독립 항목으로 작성돼 있으므로 **PR 요약을 8개로 변경하는 방식**이 가장 단순하고 명확하다.

7개를 유지하려면 `saved topic count`와 `failed topic count`를 하나의 `topic save result count` 범주로 명시적으로 그룹화해야 한다. 단순히 숫자만 7로 유지하면 안 된다.

### 3. Task의 resource 변경 금지 규칙이 실제 구현과 충돌

대상:

- `docs/tasks/feat-pipeline-operations-dashboard.md`
- `Do not change` 목록

현재 문구:

```text
Grafana, Prometheus와 kube-state-metrics의 resource request/limit 변경
```

하지만 이 PR은 Production Helm Revision 1·2의 baseline에 맞추기 위해 Grafana CPU limit을 `300m → 200m`으로 정합화했다.

영향:

- Task 계약상 금지한 변경을 실제 구현에서 수행한 것처럼 보인다.
- Approved Fix와 Task가 서로 모순된다.
- 리뷰어가 scope 위반으로 판단할 수 있다.

수정 방향:

Grafana CPU limit 정합화만 승인된 예외로 기록한다.

```text
Grafana CPU limit의 300m → 200m Production baseline 정합화 외에,
Grafana·Prometheus·kube-state-metrics resource request/limit은 변경하지 않는다.
```

Prometheus, kube-state-metrics와 Grafana의 다른 request/limit 변경 금지는 유지한다.

### 4. Review artifact가 빈 placeholder 상태

대상:

- `docs/reviews/feat-pipeline-operations-dashboard-coderabbit.md`
- `docs/reviews/feat-pipeline-operations-dashboard-antigravity.md`

두 파일 모두 제목과 section heading만 있고 실제 review evidence가 없다.

영향:

- 리뷰를 수행한 기록처럼 보이지만 검토 결과가 없어 audit evidence로 사용할 수 없다.
- CodeRabbit이 직접 해당 placeholder를 low-value artifact로 판단했다.

수정 방향:

- CodeRabbit 파일은 이 리뷰 내용을 사용해 채운다.
- Antigravity review를 실제 수행했다면 실제 결과만 기록한다.
- Antigravity review를 수행하지 않았다면 placeholder 파일을 제거하거나 `미수행`을 명확히 기록한다. 결과를 추정해서 작성하면 안 된다.

### 5. Fenced code block에 language identifier가 없음

대상 예시:

- `docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md`
- `docs/tasks/feat-pipeline-operations-dashboard.md`

여러 code fence가 단순한 `` `로 시작한다.

영향:

- Markdown lint `MD040` 경고
- syntax highlighting과 문서 가독성 저하

수정 방향:

내용에 맞게 다음 identifier를 사용한다.

- PromQL: `promql`
- shell command: `bash`
- YAML: `yaml`
- JSON: `json`
- 일반 로그·측정값·목록: `text`

## Required Fixes Before PR

### FIX-01. Markdown 표의 inline PromQL pipe escape

파일:

- `docs/design/pipeline-operations-dashboard.md`

필수 변경:

- Alerting 후보 표의 세 PromQL 정규식 안에 있는 모든 `|`를 `\|`로 변경
- 표 자체의 column delimiter는 변경하지 않음

완료 기준:

- markdownlint `MD056 table-column-count` 경고 없음
- 표가 4개 column으로 정상 렌더링

### FIX-02. 업무 metric 개수 통일

파일:

- `docs/tasks/feat-pipeline-operations-dashboard.md`
- `docs/pr/feat-pipeline-operations-dashboard.md`

권장 변경:

- Task의 8개 열거 항목은 유지
- PR 요약의 `업무 metric 7개`를 `업무 metric 8개`로 변경
- Task의 목록 code fence에는 `text` identifier 추가

대안:

- 7개를 유지할 경우 saved/failed topic count를 하나의 그룹으로 재작성하고 두 문서에 같은 정의를 사용

### FIX-03. Grafana CPU limit 정합화 예외 명시

파일:

- `docs/tasks/feat-pipeline-operations-dashboard.md`

필수 변경:

- `Do not change` 목록에서 Grafana CPU limit `300m → 200m` 정합화가 승인된 예외임을 명시
- Grafana의 다른 resource와 Prometheus/kube-state-metrics resource 변경 금지는 유지

### FIX-04. CodeRabbit review artifact 작성

파일:

- `docs/reviews/feat-pipeline-operations-dashboard-coderabbit.md`

필수 변경:

- Review Summary
- Problems Found
- Required Fixes Before PR
- Optional Improvements
- Suggested Test Commands
- Risk Notes

각 section을 실제 PR #63 review evidence로 채운다.

## Optional Improvements

### 1. Antigravity placeholder 정리

`docs/reviews/feat-pipeline-operations-dashboard-antigravity.md`가 빈 상태다.

- 실제 Antigravity review가 있다면 그 결과를 작성
- 실제 review가 없다면 placeholder 제거 또는 미수행 상태 명시

CodeRabbit review 결과를 Antigravity 결과로 복사하면 안 된다.

### 2. Fenced code block language identifier 일괄 보완

특히 `docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md`의 다음 종류를 정리한다.

- timestamp PromQL 예시 → `promql`
- Grafana/Prometheus 로그와 성능 수치 → `text`
- canonical Pod selector와 resource query → `promql`
- Helm resource 예시 → `yaml`
- 검증 명령 → `bash`

이 작업은 런타임에는 영향을 주지 않지만 markdownlint 품질과 유지보수성을 높인다.

### 3. 리뷰 thread 정리

수정 커밋 후 각 CodeRabbit inline thread에서 현재 코드가 반영됐는지 확인한 뒤 resolve한다.

## Suggested Test Commands

### Markdown table과 문서 lint

```bash
npx markdownlint-cli2 \
  docs/design/pipeline-operations-dashboard.md \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/reviews/feat-pipeline-operations-dashboard-coderabbit.md \
  docs/reviews/feat-pipeline-operations-dashboard-antigravity.md
```

프로젝트에 markdownlint가 설치돼 있지 않으면 임시 도구 도입을 필수화하지 않고, 아래 검사를 함께 수행한다.

### 업무 metric 개수 확인

```bash
rg -n \
  '업무 metric [0-9]+개|partial_success|saved topic count|failed topic count' \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/pr/feat-pipeline-operations-dashboard.md
```

기대 결과:

- 두 문서의 count와 grouping이 동일

### resource scope 문구 확인

```bash
rg -n \
  'resource request/limit|300m|200m|Production baseline|정합화' \
  docs/tasks/feat-pipeline-operations-dashboard.md \
  docs/fixes/feat-pipeline-operations-dashboard-approved-fixes.md \
  docs/pr/feat-pipeline-operations-dashboard.md \
  docs/devlog/feat-pipeline-operations-dashboard.md
```

기대 결과:

- Grafana CPU limit 정합화만 예외
- 다른 monitoring resource 변경은 금지 상태 유지

### Markdown 표 pipe 확인

```bash
sed -n '425,436p' docs/design/pipeline-operations-dashboard.md
```

확인 사항:

- inline PromQL 내부의 alternation pipe가 `\|`
- 표의 column delimiter는 유지

### Review artifact 확인

```bash
for file in \
  docs/reviews/feat-pipeline-operations-dashboard-coderabbit.md \
  docs/reviews/feat-pipeline-operations-dashboard-antigravity.md; do
  echo "===== $file ====="
  sed -n '1,220p' "$file"
done
```

확인 사항:

- heading만 있는 빈 review file이 없음
- 실제로 수행하지 않은 review 결과를 작성하지 않음

### 기존 회귀 검증

```bash
PYTHONPATH=. pytest -q

git diff --check
```

문서 수정만 예상되므로 application, Dashboard JSON, Helm values에 새 변경이 없는지 확인한다.

```bash
git diff --name-only -- \
  app scripts db migrations requirements.txt \
  k8s/monitoring/dashboards/news-lab-pipeline-operations.json \
  k8s/monitoring/kube-prometheus-stack-values.yaml
```

기대 결과:

- 출력 없음

## Risk Notes

- 이번 CodeRabbit 지적은 대부분 문서 품질과 계약 정합성 문제다. Production Grafana와 Prometheus 기능 검증을 다시 수행할 필요는 낮다.
- PromQL pipe escape는 문서 표 안의 inline code에만 적용해야 한다. Dashboard JSON이나 실제 PromQL expression에 `\|`를 넣으면 정규식 의미가 달라질 수 있으므로 수정 범위를 혼동하면 안 된다.
- 업무 metric 개수는 숫자만 바꾸지 말고 실제 grouping과 일치시켜야 한다. 현재 구조에서는 8개로 통일하는 편이 가장 안전하다.
- Grafana CPU limit 예외 문구를 넓게 작성하면 이후 다른 resource 변경까지 승인된 것으로 해석될 수 있다. `300m → 200m` 정합화만 정확히 한정한다.
- 빈 Antigravity review를 임의로 채우는 것은 잘못된 audit evidence가 된다. 실제 review가 없다면 제거 또는 미수행 표시가 안전하다.
- Code fence language 보완은 low-risk지만, fence 경계나 내용 자체를 바꾸지 않도록 한다.
