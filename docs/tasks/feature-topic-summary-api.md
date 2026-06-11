# Task: Topic summary DB 저장 및 조회 API MVP

## Goal

35차에서 구현한 raw text 기반 topic summary report MVP를 DB 저장 및 조회 API 단계로 확장한다.

현재 topic summary는 JSON/markdown report로만 생성되며 DB에 저장되지 않는다.  
이번 작업에서는 검증된 topic summary 결과를 저장할 수 있는 DB schema, 저장 CLI, 그리고 저장된 topic summary를 조회하는 read-only API MVP를 추가한다.

핵심 목표는 다음과 같다.

- `topics`, `topic_articles` 저장 구조를 추가한다.
- topic summary 결과를 DB에 저장할 수 있는 CLI를 추가한다.
- 저장 CLI는 기본 dry-run으로 동작하고, `--execute`가 있을 때만 DB write를 수행한다.
- 저장된 topic summary를 조회하는 API를 추가한다.
- `/topics` 목록 API와 `/topics/{topic_id}` 상세 API를 제공한다.
- API 응답에는 raw text 전문을 노출하지 않는다.
- DB migration SQL은 repo에 파일로 남기고, 실제 Supabase 적용은 human approval 후 수동 실행한다.

이번 작업은 summary 자동 운영 단계가 아니라, **DB 저장 + read API MVP**다.

## Scope

### 1. DB migration SQL 추가

`db/migrations` 아래에 `topics`, `topic_articles` 테이블 생성 SQL을 추가한다.

권장 테이블:

- `topics`
  - 하나의 topic summary 결과를 저장한다.
- `topic_articles`
  - topic summary와 근거 article의 연결 관계를 저장한다.

설계 원칙:

- `topics.id`를 stable primary key로 사용한다.
- `topic_candidate_id`는 35차 report와 연결하기 위한 trace metadata로만 사용한다.
- `topic_articles.article_id`는 기존 `articles(id)`를 참조한다.
- article title, source name, url, raw text는 `topic_articles`에 중복 저장하지 않는다.
- API에서 필요한 article/source 정보는 기존 `articles`, `sources`, `raw_articles`와 join해서 조회한다.
- `key_points`, `keywords`는 `jsonb`로 저장해도 된다.
- summary 생성 당시 기준의 `article_count`, `source_count`는 `topics`에 저장할 수 있다.
- `summary_input_hash`를 저장해 같은 입력으로 생성된 summary를 추적할 수 있게 한다.

권장 컬럼:

`topics`

- `id`
- `topic_date`
- `topic_candidate_id`
- `title_ko`
- `summary_ko`
- `key_points`
- `keywords`
- `confidence`
- `provider`
- `model`
- `status`
- `source_count`
- `article_count`
- `summary_input_hash`
- `created_at`
- `updated_at`

`topic_articles`

- `id`
- `topic_id`
- `article_id`
- `role`
- `similarity_score`
- `created_at`

### 2. Topic summary 저장 CLI 추가

신규 CLI를 추가한다.

예상 파일:

```bash
scripts/save_topic_summaries.py
```

동작 요구사항:

- 35차의 topic summary generation helper를 가능한 재사용한다.
- 기본 실행은 dry-run이다.
- `--execute`가 있을 때만 DB write를 수행한다.
- `--max-topics` 또는 동등한 limit 옵션이 있어야 한다.
- raw extraction은 실행하지 않는다.
- provider 호출은 명시적인 provider 옵션과 API key가 있을 때만 허용한다.
- 기본 저장 검증은 deterministic summary로 가능해야 한다.
- 저장 report를 생성한다.

저장 report에는 최소 다음 정보를 포함한다.

- `dry_run`
- `execute_requested`
- `db_write_performed`
- `raw_extraction_performed=false`
- provider/model
- topic count
- saved topic count
- skipped topic count
- inserted/updated topic id
- linked article count
- skipped reason

권장 실행 예시:

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-api-save-dry-run.md
```

human-approved 실제 저장 예시:

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 1 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --execute \
  --report-path docs/reports/feature-topic-summary-api-save-execute.md
```

### 3. Read-only API 추가

FastAPI에 read-only topic API를 추가한다.

추가 API:

- `GET /topics`
- `GET /topics/{topic_id}`

`GET /topics`는 저장된 topic summary 목록을 pagination 형태로 반환한다.

권장 query parameter:

- `page`
- `page_size`
- `status`
- `date_from`
- `date_to`
- `keyword`

권장 응답 필드:

- `id`
- `topic_date`
- `title_ko`
- `summary_ko`
- `keywords`
- `source_count`
- `article_count`
- `provider`
- `model`
- `status`
- `created_at`
- `updated_at`

pagination 구조는 기존 `/articles` API 스타일을 가능한 따른다.

- `items`
- `page`
- `page_size`
- `total`
- `has_next`

`GET /topics/{topic_id}`는 단일 topic summary와 관련 article metadata를 반환한다.

권장 응답 필드:

- topic 기본 필드
- `key_points`
- `keywords`
- related articles:
  - `article_id`
  - `title`
  - `url`
  - `source`
  - `published_at`
  - `role`
  - `similarity_score`

API 응답에는 `raw_text`를 포함하지 않는다.

### 4. Tests 추가

다음 테스트를 추가하거나 기존 테스트를 확장한다.

- migration SQL 파일 존재 확인
- migration SQL에 `topics`, `topic_articles`, FK, unique constraint가 포함되는지 확인
- save CLI 기본 dry-run 확인
- `--execute` 없이는 DB write가 발생하지 않는지 확인
- save report에 `db_write_performed`가 기록되는지 확인
- 저장 로직이 topic과 topic_articles를 올바르게 구성하는지 확인
- duplicate summary input 또는 `summary_input_hash` 처리 검증
- `/topics` 목록 API pagination 검증
- `/topics/{topic_id}` 상세 API 검증
- 존재하지 않는 topic id는 404 반환
- API 응답에 `raw_text`가 포함되지 않는지 확인
- 기존 테스트가 계속 통과하는지 확인

## Do not change

이번 작업에서 다음은 변경하지 않는다.

- Supabase SQL 자동 실행 금지
- production DB migration 자동 적용 금지
- manual SQL 실행 금지
- K8s manifest 변경 금지
- CronJob 추가/수정 금지
- Dockerfile 변경 금지
- GitHub Actions workflow 변경 금지
- frontend 변경 금지
- production deployment 금지
- K3s rollout 금지
- `kubectl`, `helm`, Docker push 실행 금지
- raw extraction 실행 금지
- 대량 provider 호출 금지
- `gpt-5-mini` 자동 fallback/retry 구현 금지
- factuality checker 구현 금지
- summary 자동 운영 스케줄링 금지
- `.env`, credentials, kubeconfig, SSH key, token, secret 변경 금지
- API 응답에 raw text 전문 노출 금지

## Expected files

예상 추가/변경 파일:

```text
db/migrations/202606xx_create_topics_tables.sql
scripts/save_topic_summaries.py
app/routers/topics.py
app/main.py
app/schemas/topics.py
app/repositories/topics.py
tests/test_save_topic_summaries.py
tests/test_topics_api.py
tests/test_topic_summary_migration.py
docs/tasks/feature-topic-summary-api.md
docs/verification/feature-topic-summary-api.md
docs/devlog/feature-topic-summary-api.md
docs/pr/feature-topic-summary-api.md
docs/reports/feature-topic-summary-api-save-dry-run.md
docs/reviews/feature-topic-summary-api-antigravity.md
docs/reviews/feature-topic-summary-api-coderabbit.md
docs/fixes/feature-topic-summary-api-approved-fixes.md
```

실제 프로젝트 구조에 맞지 않는 파일명은 기존 convention에 맞춰 조정한다.

## DB changes

DB migration SQL 파일을 repo에 추가한다.

예상 테이블:

- `topics`
- `topic_articles`

실제 Supabase DB 적용은 Codex가 수행하지 않는다.  
SQL 파일을 작성하고 review를 받은 뒤, human operator가 Supabase SQL Editor에서 수동 실행한다.

Migration SQL 작성 시 고려사항:

- `create table if not exists` 사용 여부 검토
- FK constraint 추가
- `topic_articles.topic_id -> topics.id`
- `topic_articles.article_id -> articles.id`
- `unique(topic_id, article_id)` 추가
- 목록 조회용 index 추가
  - `topics(topic_date desc)`
  - `topics(status)`
  - `topics(created_at desc)`
  - `topic_articles(topic_id)`
  - `topic_articles(article_id)`
- `updated_at` 갱신 방식은 간단한 MVP에서는 application update로 처리하거나 별도 trigger를 후속 검토한다.

Codex verification에서는 Supabase SQL 실행을 하지 않는다.  
migration 적용 전에는 DB integration verification이 제한될 수 있음을 문서에 남긴다.

## API changes

신규 read-only API를 추가한다.

### GET /topics

저장된 topic summary 목록을 pagination으로 조회한다.

예상 응답:

```json
{
  "items": [
    {
      "id": 1,
      "topic_date": "2026-06-11",
      "title_ko": "주제 제목",
      "summary_ko": "주제 요약",
      "keywords": ["keyword"],
      "source_count": 2,
      "article_count": 3,
      "provider": "openai",
      "model": "gpt-5-nano",
      "status": "draft",
      "created_at": "2026-06-11T00:00:00Z",
      "updated_at": "2026-06-11T00:00:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "has_next": false
}
```

### GET /topics/{topic_id}

단일 topic summary와 관련 article metadata를 조회한다.

예상 응답:

```json
{
  "id": 1,
  "topic_date": "2026-06-11",
  "title_ko": "주제 제목",
  "summary_ko": "주제 요약",
  "key_points": ["핵심 내용"],
  "keywords": ["keyword"],
  "source_count": 2,
  "article_count": 3,
  "provider": "openai",
  "model": "gpt-5-nano",
  "status": "draft",
  "articles": [
    {
      "article_id": 574,
      "title": "Article title",
      "url": "https://example.com/article",
      "source": "TechCrunch",
      "published_at": "2026-06-11T00:00:00Z",
      "role": "representative",
      "similarity_score": null
    }
  ],
  "created_at": "2026-06-11T00:00:00Z",
  "updated_at": "2026-06-11T00:00:00Z"
}
```

API response에는 raw text를 포함하지 않는다.

## Test commands

Codex가 실행할 기본 검증 명령:

```bash
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py \
  scripts/save_topic_summaries.py
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
git diff --check
```

Scope check:

```bash
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
```

Security check:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

Optional command if project environment supports it:

```bash
.venv/bin/python scripts/save_topic_summaries.py --help
```

Dry-run report command:

```bash
.venv/bin/python scripts/save_topic_summaries.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-api-save-dry-run.md
```

Do not run `--execute` unless human operator explicitly approves.

## Acceptance criteria

작업 완료 기준:

- `topics`, `topic_articles` migration SQL 파일이 repo에 추가되어 있다.
- Codex가 Supabase SQL을 직접 실행하지 않았다.
- 저장 CLI가 추가되어 있다.
- 저장 CLI 기본 실행은 dry-run이다.
- `--execute` 없이는 DB write가 발생하지 않는다.
- 저장 report에 `dry_run`, `execute_requested`, `db_write_performed`, `raw_extraction_performed=false`가 기록된다.
- `/topics` 목록 API가 추가되어 있다.
- `/topics/{topic_id}` 상세 API가 추가되어 있다.
- API 응답에는 raw text 전문이 포함되지 않는다.
- topic detail API는 관련 article metadata를 반환한다.
- 존재하지 않는 topic id는 404를 반환한다.
- 기존 `/articles`, `/sources`, `/health`, `/version` 등 기존 API 동작을 깨지 않는다.
- unit test가 통과한다.
- API/DB 변경 외 K8s, CronJob, Docker, GitHub Actions, frontend 변경이 없다.
- secrets, tokens, API key, `.env` 값이 repo나 report에 노출되지 않는다.
- production deployment, K3s rollout, PR merge는 수행하지 않는다.

## Notes

- 35차 summary report MVP의 후속 작업이다.
- 이번 차수는 summary 자동 운영이 아니라 DB 저장과 조회 API의 MVP다.
- provider 결과를 DB에 저장할 수 있는 경로는 만들 수 있지만, 대량 provider 호출이나 자동 fallback은 구현하지 않는다.
- 초기 저장 검증은 deterministic summary 기반으로 수행하는 것이 안전하다.
- provider 저장 검증이 필요하면 별도 human approval 후 `max_topics=1` 수준의 제한 실행만 허용한다.
- `gpt-5-nano`는 MVP 기본 모델 후보이며, `gpt-5-mini`는 비교/업그레이드 후보로 유지한다.
- factuality/quality gate는 후속 작업으로 분리한다.
- Supabase 적용은 SQL 파일 review 후 human operator가 SQL Editor에서 수동 실행한다.
- README 업데이트 여부는 `/topics` API를 이번 단계에서 공개 application surface로 볼지에 따라 결정한다. README를 변경하지 않는 경우 devlog에 이유를 남긴다.
