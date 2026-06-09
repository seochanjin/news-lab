# Approved Fixes: Lightweight article classification MVP

## Candidate Fixes Pending Human Approval

### Candidate 1. Category keyword와 importance weight 설정 외부화

Antigravity review에서 현재 `CATEGORY_KEYWORDS`, importance 관련 keyword,
source category weight가 `app/utils/article_classification.py`의 상수로
정의되어 있어, 향후 분류 체계가 복잡해질 경우 설정 파일로 분리하는
방안이 optional improvement로 제안되었다.

제안 범위:

- category keyword mapping을 별도 config module 또는 structured config로
  분리
- breaking/high-impact keyword와 source category weight를 동일한 config
  경계로 이동
- config validation과 deterministic ordering을 유지
- 기존 classification 결과가 의도치 않게 변경되지 않도록 regression
  test 추가

판단 초안:

- **Pending human approval**
- 이번 task의 acceptance criteria를 충족하기 위한 blocking fix는 아니다.
- 현재 category와 weight 규모에서는 코드 상수가 규칙을 한 위치에서
  명확하게 보여주며, 별도 JSON parsing이나 config validation 복잡도를
  추가하지 않는다.
- 향후 keyword tuning이 잦아지거나 비개발자가 규칙을 관리해야 할 때
  별도 후속 task로 분리하는 것이 적절하다.

## Approved Fixes

- None.
- Human operator가 명시적으로 승인한 fix는 아직 없다.
- Review output만으로는 수정 승인이 성립하지 않으므로 candidate fix를
  코드에 적용하지 않는다.

## Rejected or Deferred Suggestions

- Rejected suggestion은 없다.
- Candidate 1은 인간 승인 전까지 deferred가 아니라 pending approval
  상태로 유지한다.
- Antigravity review의 Suggested Test Commands는 fix 제안이 아니므로
  approved/rejected 항목으로 분류하지 않는다.
- CodeRabbit review 문서에는 구체적인 required fix 또는 optional
  improvement가 기록되어 있지 않다.

## Applied Changes

- None.
- 이 fix drafting 단계에서는 코드, 테스트, DB, API, K8s manifest를
  변경하지 않았다.
- DB migration, Supabase SQL, production command, push, merge를 실행하지
  않았다.

## Verification Required

Candidate 1이 인간 operator에 의해 승인되어 별도 구현되는 경우 다음
검증이 필요하다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 0
git status --short
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

추가 검증 기준:

- 외부화 전후 동일 fixture에 대해 category와 importance 결과가 동일해야
  한다.
- 잘못된 config가 조용히 잘못된 classification을 만들지 않도록 validation
  동작을 확인해야 한다.
- classification dry-run은 계속 DB read-only로 동작해야 한다.
- production verification은 human-provided 실제 로그가 있기 전까지
  pending으로 유지한다.
