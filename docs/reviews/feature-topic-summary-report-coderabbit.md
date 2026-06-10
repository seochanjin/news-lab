# CodeRabbit Review: Raw text 기반 topic summary report MVP

## Review Summary

CodeRabbit review에서 `feature/topic-summary-report` 브랜치에 대해 2건의 코멘트가 확인되었다.

1. `app/utils/topic_summary.py`의 provider response parsing 경계 검증 강화 필요
2. `docs/reviews/feature-topic-summary-report-antigravity.md`의 markdown emphasis spacing 수정 필요

첫 번째 항목은 외부 provider 응답을 파싱하는 경계에서 발생할 수 있는 validation 문제로, PR 전 수정하는 것이 적절하다고 판단했다.  
두 번째 항목은 문서 markdown formatting 문제로, 기능 동작에는 영향이 없지만 함께 수정하는 것이 적절하다.

## Problems Found

### 1. Provider payload validation hardening 필요

CodeRabbit은 `parse_provider_response()`에서 `json.loads(output_text)` 결과를 JSON object라고 가정하고 `.keys()`를 호출하는 점을 지적했다.

현재 구조에서는 provider 응답이 다음과 같은 valid JSON이지만 object가 아닌 형태일 경우 `AttributeError`가 발생할 수 있다.

- JSON array
- JSON string
- JSON null
- JSON number

이 경우 의도한 validation error가 아니라 내부 Python error로 실패한다.

또한 `confidence` 값을 `float()`로만 변환하면 다음과 같은 non-finite 값이 통과할 수 있다.

- `NaN`
- `inf`
- `-inf`

Provider 응답은 외부 입력 경계이므로 controlled validation error를 발생시키는 방식으로 방어하는 것이 적절하다.

### 2. Markdown emphasis spacing 문제

CodeRabbit은 `docs/reviews/feature-topic-summary-report-antigravity.md`에서 markdown emphasis marker 뒤에 불필요한 공백이 있는 문제를 지적했다.

예:

```md
** deterministic/mock 요약 우선**
```

수정 방향:

```md
**deterministic/mock 요약 우선**
```

이 항목은 기능상 문제는 아니지만 문서 formatting 품질을 위해 수정한다.

## Required Fixes Before PR

### 1. Provider response payload validation 강화

`parse_provider_response()`에서 다음 검증을 추가한다.

- `json.loads(output_text)` 결과가 `dict`인지 확인한다.
- `title_ko`, `summary_ko`가 string인지 확인한다.
- `key_points`, `keywords`가 list인지 확인한다.
- `key_points`, `keywords` 내부 원소가 모두 string인지 확인한다.
- `confidence`가 finite number인지 확인한다.
- `confidence`가 `0~1` 범위인지 확인한다.
- 잘못된 provider payload는 `ValueError`로 제어된 validation error를 발생시킨다.

추가할 테스트:

- provider response가 JSON object가 아닌 경우 `ValueError`
- `title_ko` 또는 `summary_ko`가 string이 아닌 경우 `ValueError`
- `key_points` 또는 `keywords`가 list가 아닌 경우 `ValueError`
- `key_points` 또는 `keywords` 내부 원소가 string이 아닌 경우 `ValueError`
- `confidence`가 `NaN`, `inf`, `-inf`인 경우 `ValueError`
- `confidence`가 `0~1` 범위를 벗어나는 경우 `ValueError`

### 2. Markdown emphasis spacing 수정

`docs/reviews/feature-topic-summary-report-antigravity.md`의 emphasis spacing을 수정한다.

- `** deterministic/mock 요약 우선**`
- `**deterministic/mock 요약 우선**`

## Optional Improvements

이번 CodeRabbit review에서 별도 optional improvement는 확인하지 않았다.

다만 후속 품질 개선 후보는 다음과 같다.

- provider prompt factuality guard 강화
- provider output quality gate 설계
- `gpt-5-mini` 자동 fallback/retry 정책 검토
- confidence 값을 verified confidence로 오해하지 않도록 field naming 또는 문서 보강
- provider 호출 비용 기록 및 summary run metadata 설계

위 항목들은 이번 PR의 필수 수정 범위가 아니며, 후속 리팩토링/업그레이드 단계에서 검토한다.

## Suggested Test Commands

Provider validation fix 적용 후 다음 검증을 수행한다.

```bash
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py
```

```bash
.venv/bin/python -m unittest \
  tests.test_topic_summary \
  tests.test_generate_topic_summary_report \
  -v
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
git diff --check
```

변경 범위 확인:

```bash
git diff -- k8s
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github .env
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

금지 사항:

- provider 실제 호출 금지
- `OPENAI_SUMMARY_API_KEY`가 필요한 명령 실행 금지
- raw extraction 실행 금지
- DB write 금지
- migration/manual SQL 금지
- K8s/CronJob/API/frontend 변경 금지

## Risk Notes

Provider response parsing은 외부 입력 경계이므로 방어적 validation이 필요하다.  
이번 수정은 summary provider payload의 안정성을 높이는 변경이며, API/DB/K8s/CronJob/frontend에는 영향을 주지 않는다.

`confidence`는 provider가 반환한 자체 평가값이며, 사실 검증이 완료된 신뢰도는 아니다.  
사용자-facing DB/API로 승격하기 전에는 별도의 factuality check 또는 quality gate가 필요하다.

이번 review에서 확인된 문제는 PR 전 approved fixes로 반영하는 것이 적절하다.
