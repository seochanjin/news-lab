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

### 3. Optional: save CLI SQL mismatch를 test에서 더 잘 잡도록 보강한다

#### Problem

현재 `tests/test_save_topic_summaries.py`는 fake connection으로 persistence path를 검증한다.  
이 방식은 DB write 호출 여부와 payload 구조를 확인하는 데는 유용하지만, 실제 PostgreSQL constraint와 `ON CONFLICT` target의 정합성까지 검증하지는 못한다.

#### Approved fix

가능하면 save CLI test에 다음 중 하나를 추가한다.

- `UPSERT_TOPIC_QUERY` 문자열에 `on conflict (summary_input_hash, provider, model)`이 포함되는지 확인
- migration SQL의 unique constraint와 save CLI conflict target이 같은 컬럼 조합을 사용하는지 확인

#### Rationale

실제 DB integration test 없이도 migration SQL과 upsert query의 핵심 정합성을 unit test에서 어느 정도 방어할 수 있다.

이 항목은 구현 난이도가 낮으면 함께 적용한다.  
단, 과도한 SQL parser 구현은 이번 범위에 포함하지 않는다.

## Rejected or Deferred Suggestions

### 1. dry-run report 물리 생성 요구는 human DB environment 준비 이후로 보류한다

#### Review finding

Antigravity review는 `DATABASE_URL` 누락으로 `docs/reports/feature-topic-summary-api-save-dry-run.md` 파일이 생성되지 않은 점을 blocking 항목으로 지적했다.

#### Decision

이 항목은 코드 수정 사항으로 처리하지 않고, pending verification으로 유지한다.

#### Rationale

save CLI dry-run report 생성은 실제 DB 조회 환경이 필요하다.  
현재 Codex verification 환경에는 `DATABASE_URL`이 주입되어 있지 않았고, Supabase migration SQL도 아직 human approval로 적용되지 않았다.

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

### 2. 실제 Supabase migration 적용은 이번 approved fix 적용 범위에서 제외한다

Supabase SQL Editor에서 `db/migrations/005_create_topics_tables.sql`을 실행하는 작업은 human-controlled operation이다.

Codex는 SQL 파일을 수정할 수 있지만, Supabase SQL 실행은 수행하지 않는다.

---

### 3. 실제 `--execute` save verification은 이번 approved fix 적용 범위에서 제외한다

`--execute`는 실제 DB write를 수행한다.  
따라서 migration SQL 검토 및 Supabase 적용 이후 human approval을 받은 뒤 제한적으로 수행한다.

이번 approved fix에서는 unit test와 mock execute path 검증까지만 허용한다.

## Applied Changes

- `scripts/save_topic_summaries.py`
  - `ON CONFLICT` target을 `(summary_input_hash, provider, model)`로 수정
- `tests/test_topic_summary_migration.py`
  - unique constraint assertion을 복합 unique 기준으로 수정
- `tests/test_save_topic_summaries.py`
  - save upsert query가 composite conflict target을 사용하는지 확인하는 unit
    test 추가
- migration SQL의 `unique(summary_input_hash, provider, model)`은 유지
- dry-run report 생성 실패와 Supabase migration/실제 DB write 검증은 pending
  human verification으로 유지

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
  scripts/save_topic_summaries.py \
  tests/test_topic_summary_migration.py \
  tests/test_save_topic_summaries.py \
  docs/verification/feature-topic-summary-api.md
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
- Focused and full unit tests pass.
- No Supabase SQL was executed by Codex.
- No real DB write was performed by Codex.
- Pending human verification items remain clearly documented.
