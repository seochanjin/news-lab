# CodeRabbit Review: Lightweight article classification MVP

## Review Summary

CodeRabbit review에서 scripts/analyze_article_classification.py의 get_articles() SQL query construction 방식에 대한 major issue가 확인되었다.

현재 get_articles()는 timestamp_expression, where_sql 같은 SQL fragment를 만든 뒤 text(f"""...""")에 문자열 보간으로 삽입한다.

CLI의 parse_args()에서는 --time-basis 값을 published 또는 created로 제한하고 있지만, get_articles() 함수 자체는 직접 호출될 수 있다. 따라서 함수 내부에서도 SQL fragment interpolation에 의존하지 않고 안전한 query template 선택 방식으로 동작해야 한다.

이번 issue는 production runtime path나 DB write에는 영향을 주지 않는다. 다만 SQL construction 안전성과 유지보수성을 위해 PR 전 수정하는 것이 적절하다.

## Problems Found

Problem 1. get_articles() SQL fragment interpolation

대상 파일:

- scripts/analyze_article_classification.py

문제 위치:

- get_articles()
- timestamp_expression
- where_sql
- text(f"""...""")
- order by {timestamp_expression}

현재 구조는 대략 다음 방식이다.

```python
timestamp_expression = (
    "coalesce(a.published_at, a.created_at)"
    if time_basis == "published"
    else "a.created_at"
)

where_sql = ""

if not all_articles:
    where_sql = (
        f"where {timestamp_expression} >= "
        "now() - (:window_hours * interval '1 hour')"
    )

query = text(f"""
    ...
    {timestamp_expression} as analysis_time
    ...
    {where_sql}
    order by {timestamp_expression} desc nulls last, a.id desc
""")
```

문제는 SQL 값이 아니라 SQL 구조 일부가 문자열 보간으로 조립된다는 점이다.

현재 CLI에서는 time_basis가 제한되어 있으므로 즉시 사용자 입력 기반 SQL injection으로 보기는 어렵다. 그러나 get_articles()가 함수로 분리되어 있기 때문에 다른 코드나 테스트에서 직접 호출될 수 있고, 함수 내부에서 안전한 SQL template 선택을 보장하지 않는다.

## Required Fixes Before PR

Fix 1. get_articles() SQL query construction을 고정 template 선택 방식으로 변경

get_articles()에서 SQL fragment를 f-string으로 조립하지 않도록 수정한다.

수정 기준:

- text(f"""...""")로 SQL fragment를 삽입하지 않는다.
- timestamp_expression과 where_sql을 문자열로 조립하지 않는다.
- time_basis와 all_articles 조합에 따라 고정된 SQLAlchemy text() query template을 선택한다.
- window_hours 같은 값만 bind parameter로 전달한다.
- time_basis가 예상 값이 아니면 ValueError를 발생시킨다.
- 기존 CLI 동작과 JSON 출력 구조는 유지한다.
- set transaction read only 동작은 유지한다.
- DB write, DB migration, API 변경, K8s 변경은 하지 않는다.

예상 방향:

- published + window
- published + all
- created + window
- created + all

위 네 가지 query template을 명시적으로 분리하거나, 동등하게 안전한 allowlist 기반 template 선택 방식을 사용한다.

예시 구조:

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

created 기준 query와 all query도 같은 방식으로 고정 template을 사용한다.

## Optional Improvements

Optional 1. 유사 SQL construction 패턴은 별도 리팩토링 차수에서 일괄 점검

이번 PR에서는 scripts/analyze_article_classification.py의 CodeRabbit 지적 범위만 수정한다.

다만 repository 전반에 text(f"""...""") 또는 SQL fragment interpolation 패턴이 존재할 수 있으므로, 별도 후속 차수에서 전체 SQL query construction을 점검한다.

후속 검토 방향:

- text(f"""...""") 사용처 조사
- 동적 SQL fragment interpolation 사용처 조사
- 사용자 입력과 연결될 수 있는 column/order/filter fragment 점검
- 고정 query template + bind parameter 방식으로 정리
- 필요한 경우 allowlist 기반 query 선택으로 제한

## Suggested Test Commands

수정 후 다음 명령을 실행한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py tests/test_article_classification.py
.venv/bin/python scripts/analyze_article_classification.py --help
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 168 --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --all --max-examples 0
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --time-basis created --max-examples 0
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

보안 grep도 재확인한다.

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

## Risk Notes

- 이번 issue는 production API runtime path의 직접 취약점은 아니다.
- 분석 script는 read-only transaction으로 실행되며 DB write를 수행하지 않는다.
- 그러나 SQL construction 방식은 PR 전 수정하는 것이 적절하다.
- 수정 범위는 scripts/analyze_article_classification.py의 query construction에 한정한다.
- DB schema, K8s manifest, API router, collector, raw extractor는 변경하지 않는다.
