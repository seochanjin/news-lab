# Approved Fixes: Topic summary DB 저장 및 조회 API MVP

## Approved Fixes

### 1. `ON CONFLICT` 대상 컬럼을 migration unique constraint와 일치시킨다

#### Problem

Antigravity review에서 `topics` 테이블의 unique constraint와 save CLI의 upsert query가 불일치하는 문제가 발견되었다.

현재 migration SQL은 topic summary의 provider/model별 저장 가능성을 고려해 다음 unique constraint를 사용한다.

```sql
unique (summary_input_hash, provider, model)
```

하지만 `scripts/save_topic_summaries.py`의 `UPSERT_TOPIC_QUERY`는 다음 conflict target을 사용한다.

```sql
on conflict (summary_input_hash) do update set
```

PostgreSQL에서 `ON CONFLICT` target은 실제 unique 또는 exclusion constraint와 일치해야 한다.  
따라서 현재 상태로 `--execute` 저장을 수행하면 다음 유형의 런타임 오류가 발생할 수 있다.

```text
there is no unique or exclusion constraint matching the ON CONFLICT specification
```

#### Approved fix

`UPSERT_TOPIC_QUERY`의 conflict target을 migration SQL의 unique constraint와 일치하도록 수정한다.

변경 전:

```sql
on conflict (summary_input_hash) do update set
```

변경 후:

```sql
on conflict (summary_input_hash, provider, model) do update set
```

#### Rationale

`unique(summary_input_hash)`는 같은 summary input에 대해 deterministic, `gpt-5-nano`, `gpt-5-mini` 결과를 각각 저장하는 사용 사례를 막는다.

36차 MVP에서는 `summary_input_hash`, `provider`, `model` 조합을 unique key로 두는 편이 적절하다.  
따라서 migration SQL은 유지하고, save CLI query를 수정한다.

---

### 2. Migration unit test의 unique constraint 기대값을 실제 schema와 일치시킨다

#### Problem

Antigravity review에서 `tests/test_topic_summary_migration.py`의 assertion이 현재 migration SQL과 불일치하는 문제가 발견되었다.

현재 test는 다음 문자열을 기대한다.

```python
self.assertIn("unique (summary_input_hash)", sql)
```

하지만 migration SQL은 다음 constraint를 사용한다.

```sql
unique (summary_input_hash, provider, model)
```

이로 인해 migration SQL 자체는 의도한 방향이지만, test expectation이 outdated 상태가 되어 테스트가 실패한다.

#### Approved fix

`tests/test_topic_summary_migration.py`의 unique constraint assertion을 실제 schema와 일치하도록 수정한다.

변경 전:

```python
self.assertIn("unique (summary_input_hash)", sql)
```

변경 후:

```python
self.assertIn("unique (summary_input_hash, provider, model)", sql)
```

#### Rationale

migration SQL의 복합 unique constraint는 provider/model별 summary 저장을 허용하기 위한 의도된 설계다.  
따라서 test를 단일 hash unique 기준이 아니라 복합 unique 기준으로 갱신한다.

---

### 3. Save CLI SQL mismatch를 test에서 더 잘 잡도록 보강한다

#### Problem

현재 `tests/test_save_topic_summaries.py`는 fake connection으로 persistence path를 검증한다.  
이 방식은 DB write 호출 여부와 payload 구조를 확인하는 데는 유용하지만, 실제 PostgreSQL constraint와 `ON CONFLICT` target의 정합성까지 검증하지는 못한다.

#### Approved fix

save CLI test에 다음 검증을 추가한다.

- `UPSERT_TOPIC_QUERY` 문자열에 `on conflict (summary_input_hash, provider, model)`이 포함되는지 확인
- migration SQL의 unique constraint와 save CLI conflict target이 같은 컬럼 조합을 사용하는지 확인

#### Rationale

실제 DB integration test 없이도 migration SQL과 upsert query의 핵심 정합성을 unit test에서 방어한다.
과도한 SQL parser 구현은 이번 범위에 포함하지 않는다.

---

### 4. `summary_input_hash`를 article 순서에 독립적으로 만든다

#### Problem

CodeRabbit review에서 `build_summary_input_hash()`가 `used_articles`의 현재 순서에 의존한다는 지적이 있었다.

현재 hash payload는 `topic_input["used_articles"]` 순서대로 구성된다.
따라서 논리적으로 같은 topic input이라도 article 순서만 바뀌면 서로 다른 hash가 생성된다.

예를 들어 다음 두 입력은 논리적으로 같은 article 집합을 나타낼 수 있다.

```text
[article_1, article_2]
[article_2, article_1]
```

하지만 현재 구현에서는 서로 다른 `summary_input_hash`가 생성될 수 있다.

이 경우 DB unique key인 `unique(summary_input_hash, provider, model)`이 같은 입력의 중복 저장을 제대로 막지 못할 수 있다.

#### Approved fix

`build_summary_input_hash(topic_input)`에서 hash payload를 만들기 전에 article payload를 deterministic하게 정렬한다.

정렬 기준은 다음을 사용한다.

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

#### Required tests

다음 테스트를 추가한다.

- 같은 article/raw_text 집합이 다른 순서로 들어와도 같은 `summary_input_hash`를 생성한다.
- raw_text가 달라지면 기존처럼 다른 `summary_input_hash`를 생성한다.
- article_id가 달라지면 다른 `summary_input_hash`를 생성한다.

#### Rationale

`summary_input_hash`는 DB deduplication의 핵심 key다.
따라서 list order가 아니라 실제 summary input의 논리적 내용에 의해 결정되어야 한다.

---

### 5. Provider generation을 DB write transaction 밖에서 수행한다

#### Problem

CodeRabbit review에서 `scripts/save_topic_summaries.py`의 execute branch가 `engine.begin()`으로 write transaction을 연 뒤 `_generate_with_connection()`을 호출한다는 지적이 있었다.

현재 구조는 다음과 같은 흐름이다.

```python
if args.execute:
    with engine.begin() as connection:
        result = _generate_with_connection(connection, args)
        plan = execute_save_plan(build_save_plan(result, args), connection)
```

`_generate_with_connection()`은 topic grouping과 summary generation을 수행한다.
이 과정에서 `--use-summary-provider`가 사용되면 OpenAI provider HTTP call이 발생할 수 있다.

그 결과 provider call 같은 느리거나 실패 가능한 network I/O가 DB write transaction 안에서 수행될 수 있다.
이는 다음 문제를 만들 수 있다.

- 불필요하게 긴 DB transaction
- network failure로 인한 transaction 장시간 점유
- lock/connection resource 낭비
- 실제 write 수행 전 단계에서 rollback 범위가 과도하게 커짐

#### Approved fix

summary generation과 save plan 생성은 write transaction 밖에서 수행한다.

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

구현 시 다음 원칙을 지킨다.

- Summary generation은 read-only connection 또는 non-write path에서 수행한다.
- DB write transaction은 `execute_save_plan()` 호출 범위로 최소화한다.
- `--execute`가 없는 경우 기존처럼 read-only dry-run을 유지한다.
- `--execute`가 있는 경우에도 provider generation은 write transaction 밖에서 수행한다.
- DB write는 여전히 `--execute`가 명시된 경우에만 가능해야 한다.
- raw extraction은 실행하지 않는다.

#### Required tests

다음 테스트를 추가하거나 기존 테스트를 보강한다.

- `--execute` branch에서 generation이 write transaction 안에서 호출되지 않음을 검증한다.
- `execute_save_plan()`만 write transaction 안에서 호출되는 구조를 검증한다.
- dry-run에서는 DB write가 발생하지 않음을 기존처럼 유지한다.
- provider call 자체는 실행하지 않고 mock/fake provider 또는 deterministic provider로 검증한다.

#### Rationale

DB transaction은 가능한 짧게 유지해야 한다.
Generation, provider call, save plan 생성은 write가 아니므로 write transaction 밖에서 처리하는 것이 더 안전하다.

---

## Rejected or Deferred Suggestions

### 1. dry-run report 물리 생성 요구는 human DB environment 준비 이후로 보류한다

#### Review finding

Antigravity review는 `DATABASE_URL` 누락으로 `docs/reports/feature-topic-summary-api-save-dry-run.md` 파일이 생성되지 않은 점을 blocking 항목으로 지적했다.

#### Decision

이 항목은 코드 수정 사항으로 처리하지 않고, pending verification으로 유지한다.

#### Rationale

save CLI dry-run report 생성은 실제 DB 조회 환경이 필요하다.  
Codex verification 환경에는 `DATABASE_URL`이 주입되어 있지 않았고, Supabase migration SQL도 아직 human approval로 적용되지 않았다.

따라서 이 실패는 다음과 같이 분류한다.

```text
코드 결함: 아님
환경/수동 검증 미완료: 맞음
```

36차 task의 DB migration policy에 따라 Codex는 Supabase SQL을 직접 실행하지 않는다.  
실제 Supabase migration 적용과 DATABASE_URL이 명시적으로 준비된 환경에서 dry-run report를 재생성하는 것은 human verification 단계로 보류한다.

#### Required follow-up verification

Supabase migration SQL을 human operator가 수동 적용한 뒤, approved environment에서 다음을 수행한다.

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-api-save-dry-run.md
```

성공 시 `docs/verification/feature-topic-summary-api.md`에 실제 실행 결과를 기록한다.

---

### 2. 실제 Supabase migration 적용은 Codex fix 적용 범위에서 제외한다

Supabase SQL Editor에서 `db/migrations/005_create_topics_tables.sql`을 실행하는 작업은 human-controlled operation이다.

Codex는 SQL 파일을 수정할 수 있지만, Supabase SQL 실행은 수행하지 않는다.

---

### 3. 실제 `--execute` save verification은 Codex fix 적용 범위에서 제외한다

`--execute`는 실제 DB write를 수행한다.  
따라서 migration SQL 검토 및 Supabase 적용 이후 human approval을 받은 뒤 제한적으로 수행한다.

Codex fix에서는 unit test와 mock execute path 검증까지만 허용한다.

---

### 4. Provider-based save verification은 후속 검증으로 보류한다

`--use-summary-provider`를 통한 provider-based save는 실제 provider call과 비용을 발생시킨다.
이번 fix 범위에서는 provider call을 실행하지 않는다.

provider-based save verification은 별도 human approval 이후 제한된 topic 수로 수행한다.

## Applied Changes

- `scripts/save_topic_summaries.py`
  - `ON CONFLICT` target을 `(summary_input_hash, provider, model)`로 수정
- `tests/test_topic_summary_migration.py`
  - unique constraint assertion을 복합 unique 기준으로 수정
- `tests/test_save_topic_summaries.py`
  - save upsert query가 composite conflict target을 사용하는지 확인하는 unit test 추가
- migration SQL의 `unique(summary_input_hash, provider, model)`은 유지
- dry-run report 생성 실패와 Supabase migration/실제 DB write 검증은 pending human verification으로 유지

- `app/utils/topic_summary.py`
  - hash payload를 `article_id`, `raw_text` 기준으로 정렬해 동일 article/raw_text 집합의 순서가 달라도 같은 `summary_input_hash`를 생성하도록 수정
- `scripts/save_topic_summaries.py`
  - read-only connection에서 summary generation을 완료하고 save plan을 생성한 뒤, `--execute`일 때만 `execute_save_plan()`을 write transaction에서 실행하도록 수정
- `tests/test_save_topic_summaries.py`
  - equivalent article/raw_text set 순서 변경, raw_text 변경, article_id 변경에 대한 hash 테스트 보강
  - execute 경로의 generation/save plan이 write transaction 밖에서 실행되고 `execute_save_plan()`만 write transaction 안에서 실행되는지 검증
  - dry-run이 write transaction을 열지 않는지 검증

## Verification Required

Approved fixes 적용 후 다음 검증을 수행한다.

### Python compile

```bash
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py \
  scripts/save_topic_summaries.py \
  app/routers/topics.py \
  app/main.py
```

### Focused tests

```bash
.venv/bin/python -m unittest \
  tests.test_topic_summary_migration \
  tests.test_save_topic_summaries \
  tests.test_topics_api \
  tests.test_topic_summary \
  -v
```

### Full unittest

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### CLI help

```bash
.venv/bin/python scripts/save_topic_summaries.py --help
```

### Diff check

```bash
git diff --check
```

If unrelated trailing whitespace exists in previous review artifacts, also run a targeted check for changed implementation/test files.

```bash
git diff --check -- \
  app/utils/topic_summary.py \
  scripts/save_topic_summaries.py \
  tests/test_topic_summary.py \
  tests/test_save_topic_summaries.py \
  tests/test_topic_summary_migration.py \
  docs/verification/feature-topic-summary-api.md \
  docs/fixes/feature-topic-summary-api-approved-fixes.md
```

### Scope checks

```bash
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
```

### Security checks

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

## Not Required During Codex Fix Verification

The following must not be performed by Codex during approved fix implementation.

- Supabase SQL execution
- manual SQL execution
- save CLI `--execute`
- DB write against real Supabase
- raw extraction
- provider call
- production curl verification
- K3s rollout
- deployment
- git push
- git merge

## Final Acceptance for This Fix

- `UPSERT_TOPIC_QUERY` conflict target matches `unique(summary_input_hash, provider, model)`.
- Migration unit test expects the composite unique constraint.
- Save CLI unit test checks the composite conflict target.
- `summary_input_hash` is order-insensitive for equivalent article/raw_text sets.
- `summary_input_hash` still changes when article_id or raw_text changes.
- Summary generation and provider call path are outside the DB write transaction.
- DB write transaction is limited to `execute_save_plan()`.
- Focused and full unit tests pass.
- No Supabase SQL was executed by Codex.
- No real DB write was performed by Codex.
- No provider call or raw extraction was performed by Codex.
- Pending human verification items remain clearly documented.
