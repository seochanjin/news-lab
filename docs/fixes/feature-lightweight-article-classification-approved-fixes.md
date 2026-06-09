# Approved Fixes: Lightweight article classification MVP

## Candidate Fixes Pending Human Approval

### Candidate 1. Category keyword와 importance weight 설정 외부화

Antigravity review에서 현재 `CATEGORY_KEYWORDS`, importance 관련 keyword, source category weight가 `app/utils/article_classification.py`의 상수로 정의되어 있어, 향후 분류 체계가 복잡해질 경우 설정 파일로 분리하는 방안이 optional improvement로 제안되었다.

제안 범위:

- category keyword mapping을 별도 config module 또는 structured config로 분리
- breaking/high-impact keyword와 source category weight를 동일한 config 경계로 이동
- config validation과 deterministic ordering을 유지
- 기존 classification 결과가 의도치 않게 변경되지 않도록 regression test 추가

판단:

- **Pending human approval**
- 이번 task의 acceptance criteria를 충족하기 위한 blocking fix는 아니다.
- 현재 category와 weight 규모에서는 코드 상수가 규칙을 한 위치에서 명확하게 보여준다.
- 별도 JSON parsing이나 config validation 복잡도를 지금 추가하지 않는다.
- 향후 keyword tuning이 잦아지거나 비개발자가 규칙을 관리해야 할 때 별도 후속 task로 분리한다.

## Approved Fixes

### Fix 1. `get_articles()` SQL query construction 안전성 개선

CodeRabbit review에서 `scripts/analyze_article_classification.py`의 `get_articles()` 함수가 SQL fragment를 문자열 보간으로 조립한다는 major issue가 확인되었다.

현재 구현은 `timestamp_expression`, `where_sql` 같은 SQL fragment를 만든 뒤 `sqlalchemy.text(f"""...""")` 안에 삽입한다.

문제 위치:

- `scripts/analyze_article_classification.py`
- `get_articles()`
- `timestamp_expression`
- `where_sql`
- `text(f"""...""")`
- `order by {timestamp_expression}`

현재 CLI의 `parse_args()`는 `--time-basis` 값을 `published` 또는 `created`로 제한한다. 따라서 즉시 사용자 입력 기반 SQL injection 취약점으로 보기는 어렵다.

다만 `get_articles()` 함수 자체는 직접 호출될 수 있으므로, 함수 내부에서도 안전한 SQL construction을 보장해야 한다. PR 전 수정 대상으로 승인한다.

수정 기준:

- `text(f"""...""")`를 사용해 SQL fragment를 삽입하지 않는다.
- `timestamp_expression`과 `where_sql`을 문자열 조각으로 조립하지 않는다.
- `time_basis`와 `all_articles` 조합에 따라 고정된 SQLAlchemy `text()` query template을 선택한다.
- `window_hours` 같은 값만 bind parameter로 전달한다.
- `time_basis`가 예상 값이 아니면 `ValueError`를 발생시킨다.
- 기존 CLI 옵션과 JSON 출력 구조는 유지한다.
- 기존 classification rule, language fallback, importance score 계산은 변경하지 않는다.
- `set transaction read only` 동작은 유지한다.
- DB write, DB migration, API 변경, K8s 변경은 하지 않는다.

예상 query template 조합:

- `published + window`
- `published + all`
- `created + window`
- `created + all`

예상 구현 방향:

```python
PUBLISHED_WINDOW_QUERY = text("""
    select
        a.id,
        a.source_id,
        s.name as source,
        a.title,
        a.summary,
        a.category as source_category,
        a.published_at,
        a.created_at,
        coalesce(a.published_at, a.created_at) as analysis_time
    from articles a
    left join sources s on s.id = a.source_id
    where coalesce(a.published_at, a.created_at) >= now() - (:window_hours * interval '1 hour')
    order by coalesce(a.published_at, a.created_at) desc nulls last, a.id desc
""")
```

`created` 기준 query와 `all` query도 같은 방식으로 고정 template을 사용한다.

## Rejected or Deferred Suggestions

### Deferred 1. Repository 전반 SQL query construction 리팩토링

CodeRabbit이 지적한 SQL fragment interpolation 문제는 이번 파일 하나에만 국한되지 않을 수 있다. NewsLab backend의 다른 raw SQL 작성 구간에도 `text(f"""...""")` 또는 interpolated SQL fragment 패턴이 존재할 수 있다.

하지만 이번 29차 PR에서는 CodeRabbit이 지적한 `scripts/analyze_article_classification.py`의 `get_articles()`만 수정한다.

보류 이유:

- 이번 task의 scope는 lightweight article classification MVP다.
- repository 전체 SQL 리팩토링은 범위가 크고 회귀 위험이 있다.
- 기존 API, collector, extractor SQL을 한꺼번에 바꾸면 검증 범위가 커진다.
- SQL construction 전반 정리는 별도 refactoring 차수에서 수행하는 것이 적절하다.

후속 작업 방향:

- `text(f"""...""")` 사용처 조사
- 동적 SQL fragment interpolation 사용처 조사
- 사용자 입력과 연결될 수 있는 column/order/filter fragment 점검
- 고정 query template + bind parameter 방식으로 정리
- 동적 column/order/filter가 필요한 경우 allowlist 기반으로 제한
- 기존 API/collector/extractor 동작 변경 없이 query construction만 정리

### Deferred 2. Category keyword와 importance weight 설정 외부화

Candidate 1은 아직 인간 operator의 적용 승인을 받지 않았다.

이번 PR에서는 적용하지 않는다.

보류 이유:

- 이번 task의 blocking issue가 아니다.
- 현재 keyword/weight 규모에서는 코드 상수가 더 단순하다.
- config 외부화는 validation, ordering, regression test 설계가 함께 필요하다.
- 후속 tuning 빈도가 높아질 때 별도 task로 처리한다.

## Applied Changes

Applied:

- `scripts/analyze_article_classification.py`
  - `published + window`, `published + all`, `created + window`,
    `created + all` 조합을 위한 고정 SQLAlchemy `text()` query template을
    추가했다.
  - `get_articles()`의 `text(f"""...""")`, `timestamp_expression`,
    `where_sql` SQL fragment 조립을 제거했다.
  - `window_hours`는 계속 bind parameter로 전달한다.
  - 예상하지 않은 `time_basis`는 `ValueError`를 발생시킨다.
- `tests/test_analyze_article_classification.py`
  - 고정 query와 bound `window_hours` 사용을 확인하는 테스트를 추가했다.
  - unsupported `time_basis`가 `ValueError`를 발생시키는 테스트를
    추가했다.

Not changed:

- Classification rule, language fallback, importance score 계산
- CLI option과 JSON output 구조
- `set transaction read only`
- DB schema/migration, API, K8s, collector, extractor, frontend
- Candidate 1 keyword/weight 설정 외부화
- Production verification, push, merge

## Verification Required

Fix 적용 후 다음 명령을 실행하고 실제 결과를 `docs/verification/feature-lightweight-article-classification.md`에 기록한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py tests/test_article_classification.py
.venv/bin/python scripts/analyze_article_classification.py --help
```

DB read-only dry-run 검증:

```bash
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 168 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --all --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --time-basis created --max-examples 0
```

정적 검증:

```bash
git status --short
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

검증 기준:

- `get_articles()`에서 SQL fragment interpolation이 제거되어야 한다.
- `window_hours`는 bind parameter로 전달되어야 한다.
- `time_basis`가 예상 값이 아닐 경우 `ValueError`가 발생해야 한다.
- 기존 CLI 옵션과 JSON 출력 구조가 유지되어야 한다.
- classification 결과의 의미가 변경되지 않아야 한다.
- DB write가 없어야 한다.
- DB migration이 없어야 한다.
- K8s manifest 변경이 없어야 한다.
- production-impacting command를 실행하지 않아야 한다.
- production verification은 human-provided 실제 로그가 있기 전까지 pending으로 유지한다.
