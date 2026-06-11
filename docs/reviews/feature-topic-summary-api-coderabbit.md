# CodeRabbit Review: Topic summary DB 저장 및 조회 API MVP

## Review Summary

CodeRabbit review에서 `feature/topic-summary-api` 브랜치에 대해 2건의 주요 지적이 확인되었다.

1. `summary_input_hash`가 `used_articles` 순서에 의존한다.
2. `--execute` branch에서 summary generation, 특히 optional provider HTTP call이 DB write transaction 내부에서 실행될 수 있다.

두 지적 모두 실제 운영 안정성과 DB 저장 정합성에 영향을 줄 수 있으므로 PR 전에 수정하는 것이 적절하다.

이번 review에서 발견된 문제는 기존 Antigravity approved fixes와 별개의 추가 개선 사항이다.  
따라서 직접 코드에 반영하지 않고, `docs/fixes/feature-topic-summary-api-approved-fixes.md`에 human-approved fix로 기록한 뒤 적용한다.

## Problems Found

### 1. `summary_input_hash`가 article 순서에 의존함

`app/utils/topic_summary.py`의 `build_summary_input_hash()`는 현재 `topic_input["used_articles"]` 순서대로 payload를 구성한다.

현재 구조에서는 같은 article/raw_text 집합이라도 list 순서가 바뀌면 다른 hash가 생성될 수 있다.

예:

```text
[article_1, article_2]
[article_2, article_1]
```

논리적으로는 같은 summary input일 수 있지만, 현재 구현에서는 서로 다른 `summary_input_hash`가 생성될 수 있다.

이 hash는 `topics` 테이블의 deduplication key에 사용된다.

```sql
unique (summary_input_hash, provider, model)
```

따라서 hash가 순서에 민감하면 같은 입력의 중복 저장을 안정적으로 막지 못할 수 있다.

### 2. Summary generation이 DB write transaction 내부에서 실행될 수 있음

`scripts/save_topic_summaries.py`의 execute branch는 `engine.begin()`으로 write transaction을 연 뒤 `_generate_with_connection()`을 호출한다.

현재 흐름은 다음과 같다.

```python
if args.execute:
    with engine.begin() as connection:
        result = _generate_with_connection(connection, args)
        plan = execute_save_plan(build_save_plan(result, args), connection)
```

`_generate_with_connection()`은 topic grouping, summary input 구성, summary generation을 수행한다.  
`--use-summary-provider`가 사용될 경우 provider HTTP call도 이 흐름 안에서 발생할 수 있다.

이 경우 느리거나 실패 가능한 network I/O가 DB write transaction 안에서 수행될 수 있다.

리스크:

- DB transaction이 불필요하게 길어짐
- provider call 지연/실패 시 write transaction이 장시간 열림
- DB connection/lock 리소스 낭비 가능성 증가
- 실제 write가 발생하기 전 단계까지 transaction scope가 과도하게 커짐

## Required Fixes Before PR

### 1. `summary_input_hash`를 article 순서에 독립적으로 만든다

`build_summary_input_hash(topic_input)`에서 hash payload를 만들기 전에 article payload를 deterministic하게 정렬한다.

권장 정렬 기준:

1. `article_id`
2. `raw_text`

구현 방향:

```python
payload = sorted(
    (
        {
            "article_id": article["article_id"],
            "raw_text": article["raw_text"],
        }
        for article in topic_input["used_articles"]
    ),
    key=lambda item: (item["article_id"], item["raw_text"]),
)
```

그 후 기존처럼 `json.dumps(..., sort_keys=True, separators=(",", ":"))`와 `sha256`을 사용한다.

필수 테스트:

- 같은 article/raw_text 집합이 다른 순서로 들어와도 같은 `summary_input_hash`를 생성한다.
- raw_text가 달라지면 다른 `summary_input_hash`를 생성한다.
- article_id가 달라지면 다른 `summary_input_hash`를 생성한다.

### 2. Summary generation과 save plan 생성을 DB write transaction 밖으로 이동한다

`--execute` branch에서도 summary generation은 write transaction 밖에서 수행해야 한다.

권장 흐름:

```python
result = _generate_with_connection(read_connection, args)
save_plan = build_save_plan(result, args)

if args.execute:
    with engine.begin() as write_connection:
        plan = execute_save_plan(save_plan, write_connection)
else:
    plan = save_plan
```

수정 원칙:

- Summary generation은 read-only connection 또는 non-write path에서 수행한다.
- DB write transaction은 `execute_save_plan()` 호출 범위로 최소화한다.
- `--execute`가 없는 경우 기존처럼 read-only dry-run을 유지한다.
- `--execute`가 있는 경우에도 provider generation은 write transaction 밖에서 수행한다.
- DB write는 여전히 `--execute`가 명시된 경우에만 가능해야 한다.
- raw extraction은 실행하지 않는다.

필수 테스트:

- `--execute` branch에서 generation이 write transaction 안에서 호출되지 않음을 검증한다.
- `execute_save_plan()`만 write transaction 안에서 호출되는 구조를 검증한다.
- dry-run에서는 DB write가 발생하지 않음을 기존처럼 유지한다.
- provider call 자체는 실행하지 않고 deterministic provider 또는 mock/fake path로 검증한다.

## Optional Improvements

이번 CodeRabbit review에서 별도 optional improvement로 분리할 항목은 없다.

두 지적 모두 DB deduplication과 write transaction safety에 직접 관련되므로 Required Fix로 처리한다.

후속 작업으로는 다음을 검토할 수 있다.

- provider-based save verification
- summary 저장 실패 사유를 별도 report/log로 구조화
- summary run metadata 테이블 분리
- topic summary publish/draft lifecycle 정리
- provider fallback/retry 정책 설계

위 항목들은 이번 PR의 필수 수정 범위가 아니다.

## Suggested Test Commands

Approved fixes 적용 후 다음 검증을 수행한다.

```bash
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py \
  scripts/save_topic_summaries.py \
  app/routers/topics.py \
  app/main.py
```

```bash
.venv/bin/python -m unittest \
  tests.test_topic_summary \
  tests.test_save_topic_summaries \
  tests.test_topic_summary_migration \
  tests.test_topics_api \
  -v
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
.venv/bin/python scripts/save_topic_summaries.py --help
```

```bash
git diff --check
```

필요 시 변경 파일 대상 targeted diff check:

```bash
git diff --check -- \
  app/utils/topic_summary.py \
  scripts/save_topic_summaries.py \
  tests/test_topic_summary.py \
  tests/test_save_topic_summaries.py \
  docs/verification/feature-topic-summary-api.md \
  docs/fixes/feature-topic-summary-api-approved-fixes.md \
  docs/reviews/feature-topic-summary-api-coderabbit.md
```

Scope checks:

```bash
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
```

Security checks:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

금지 사항:

- Supabase SQL 실행 금지
- manual SQL 실행 금지
- save CLI `--execute` 실행 금지
- real DB write 금지
- raw extraction 실행 금지
- provider call 실행 금지
- production curl verification 금지
- K3s rollout/deployment 금지
- git push/merge 금지

## Risk Notes

`summary_input_hash`는 topic summary deduplication의 핵심 key다.  
따라서 같은 논리적 입력이 article 순서만 다르다는 이유로 서로 다른 hash를 만들면 DB 중복 방지 정책이 약해진다.

또한 provider generation이나 network I/O가 write transaction 내부에서 수행되면 DB transaction이 불필요하게 길어진다.  
이번 CLI는 default dry-run과 explicit `--execute` guard를 갖고 있지만, `--execute` 시에도 write transaction 범위는 최소화해야 한다.

이번 fix는 API schema, DB migration, K8s, CronJob, Docker, frontend를 변경하지 않고 코드 구조와 테스트를 보강하는 범위로 제한한다.
