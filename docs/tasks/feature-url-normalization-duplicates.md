# Task: URL 정규화와 중복 후보 분석 MVP

## Goal

NewsLab에 저장된 multi-source article 데이터를 기준으로 URL 정규화 규칙을 만들고, tracking parameter 제거 및 중복 후보 분석을 수행한다.

이번 작업의 목적은 27차에서 수집된 여러 source article metadata를 바탕으로, 28차 이후 normalized_url 기반 중복 방지 정책을 수립할 근거를 만드는 것이다.

이번 차수는 LLM, embedding, topic grouping을 사용하지 않는다. URL 정규화와 중복 후보 분석은 deterministic rule 기반으로 처리한다.

## Scope

이번 작업 범위는 다음으로 제한한다.

- URL normalization 함수 추가
- tracking query parameter 제거 rule 정의
- domain별 불필요 query parameter 제거 rule 정의
- title normalization 함수 추가
- title_hash 생성 로직 검토 또는 helper 추가
- 현재 DB의 articles 데이터를 대상으로 duplicate candidate dry-run 분석 script 추가
- 분석 script에서 window 기준을 지정할 수 있게 한다.
  - 24h
  - 72h
  - 168h
- 분석 기준 timestamp를 명확히 분리한다.
  - product/topic 기준: `published_at`
  - collection/operation 기준: `created_at`
  - `published_at`이 없으면 `created_at` fallback
- normalized_url 기준 중복 후보를 출력한다.
- title_hash 또는 normalized title 기준 유사 중복 후보를 출력한다.
- 분석 결과를 verification/devlog에 기록한다.
- normalized_url, title_hash, duplicate_of_article_id를 DB에 반영할지에 대한 후속 정책을 문서화한다.

## Do not change

이번 차수에서는 다음을 변경하지 않는다.

- LLM integration
- embedding generation
- topic grouping implementation
- AI summary generation
- raw article extraction policy
- raw article extraction schedule
- frontend code
- K8s manifests
- CronJob schedule
- production rollout
- Supabase SQL migration execution
- DB provider
- Oracle DB / NoSQL integration
- Google News RSS enabled source 추가

이번 차수에서는 DB schema migration을 자동 실행하지 않는다.

Codex는 Supabase SQL을 실행하지 않는다.
DB schema 변경이 필요하다고 판단되면 SQL 초안과 migration 필요성을 문서로만 제안한다.

- read-only duplicate analysis script
- no DB migration execution
- no K8s changes
- no production rollout
- no LLM/embedding/topic grouping
- no DB writes

## Expected files

예상 변경 파일은 repository 구조에 따라 조정한다.

- URL normalization helper
  - 예: `app/utils/url_normalization.py`
  - 또는 repository에 더 적합한 위치
- duplicate analysis script
  - 예: `scripts/analyze_article_duplicates.py`
- 필요 시 관련 테스트 파일
- `docs/tasks/feature-url-normalization-duplicates.md`
- `docs/verification/feature-url-normalization-duplicates.md`
- `docs/pr/feature-url-normalization-duplicates.md`
- `docs/devlog/feature-url-normalization-duplicates.md`
- `docs/reviews/feature-url-normalization-duplicates-antigravity.md`
- `docs/fixes/feature-url-normalization-duplicates-approved-fixes.md`

## DB changes

이번 차수에서는 DB schema를 변경하지 않는다.

이번 작업은 현재 `articles.url`, `articles.title`, `articles.summary`, `articles.published_at`, `articles.created_at`, `articles.source_id` 데이터를 읽어 dry-run 분석하는 것을 우선한다.

이번 차수에서 DB에 바로 추가하지 않는 후보:

- `articles.normalized_url`
- `articles.title_hash`
- `articles.duplicate_of_article_id`
- normalized_url unique index

다만 분석 결과를 기반으로 후속 차수에서 다음 DB 변경을 검토한다.

- `articles.normalized_url` column 추가
- 기존 articles backfill
- normalized_url index 추가
- unique constraint 또는 partial unique index 검토
- `articles.duplicate_of_article_id` column 추가
- `articles.title_hash` column 추가

## API changes

이번 차수에서 신규 API는 추가하지 않는다.
기존 API 응답 구조를 변경하지 않는다.
확인 대상 API:

- `/articles`
- `/collector/status`
- `/collector/runs`

중복 후보 분석은 API가 아니라 script 기반으로 수행한다.
topic 관련 API는 이번 차수에서 추가하지 않는다.

## Test commands

정적 검증:

```bash
git status --short
git diff --stat
git diff --check
```

Python compile 검증:

```bash
.venv/bin/python -m py_compile scripts/analyze_article_duplicates.py
```

URL normalization helper가 추가된 경우:

```bash
.venv/bin/python -m py_compile app/utils/url_normalization.py
```

duplicate analysis 실행 예시:

```bash
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 24
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 72
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 168
```

필요 시 전체 article 기준 dry-run:

```bash
.venv/bin/python scripts/analyze_article_duplicates.py --all
```

API read-only 확인:

```bash
curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
curl http://127.0.0.1:8000/collector/status
curl "http://127.0.0.1:8000/collector/runs?limit=5"
```

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

테스트가 존재하면 실행한다.

```bash
pytest
```

단, pytest가 설치되어 있지 않다면 verification에 pending으로 기록한다.

## Acceptance criteria

- URL normalization 함수가 추가되어 있다.
- 일반 tracking parameter가 제거된다.
- domain별 RSS/tracking parameter 제거 rule이 반영되어 있다.
  - 예: utm\_\*
  - 예: fbclid
  - 예: gclid
  - 예: at_medium
  - 예: at_campaign
  - 예: traffic_source
- URL scheme/host/path/query 정규화 기준이 문서화되어 있다.
- duplicate analysis script가 현재 DB articles를 read-only로 조회한다.
- script는 24h / 72h / 168h window 분석을 지원한다.
- script는 published_at 기준 분석을 우선하고, published_at이 없으면 created_at을 fallback으로 사용한다.
- script는 normalized_url 기준 중복 후보를 출력한다.
- script는 normalized title 또는 title_hash 기준 후보를 출력한다.
- 분석 결과가 verification/devlog에 기록되어 있다.
- DB migration은 실행하지 않는다.
- K8s manifest는 변경하지 않는다.
- production-impacting command는 실행하지 않는다.
- LLM, embedding, topic grouping, AI summary는 구현하지 않는다.
- secret, token, private IP, kubeconfig, .env 값은 기록하지 않는다.

## Notes

전 단계에서 multi-source RSS collection이 적용되어 Supabase DB에 여러 source article metadata가 저장되었다.

이번 단계에서는 이 데이터를 기준으로 중복 후보를 확인한다.

수집일과 기사 발행일은 분리해서 본다.

- created_at: NewsLab이 article을 수집/저장한 시각
- published_at: 언론사가 article을 발행한 시각

제품 기준의 “오늘의 뉴스 흐름”은 published_at 기준이 더 적합하다.

운영 기준의 “오늘 몇 개가 새로 들어왔는가”는 created_at 기준이 더 적합하다.

MVP에서는 최근 24시간을 기본 window로 보되, article 수가 부족하면 72시간 또는 168시간 window를 fallback으로 검토한다.

Google News RSS는 aggregator source이므로 URL 정규화와 중복 제거 정책이 정리된 뒤 enabled 여부를 다시 검토한다.
