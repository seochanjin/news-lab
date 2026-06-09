# Task: Lightweight article classification MVP

## Goal

NewsLab에 저장된 multi-source article metadata를 기준으로 lightweight article classification과 importance signal 후보를 분석한다.

이번 작업의 목적은 LLM이나 embedding 없이 rule 기반으로 article의 기본 category, language 후보, keyword 기반 importance signal을 계산하고, 향후 topic grouping과 topic ranking에 사용할 수 있는 저비용 classification 기준을 마련하는 것이다.

이번 차수에서는 classification 결과를 DB에 바로 저장하지 않는다. 현재 articles 데이터를 read-only로 조회하고 dry-run 분석 결과를 verification/devlog에 기록한다.

## Scope

이번 작업 범위는 다음으로 제한한다.

- source 기반 기본 category 확인
- title/summary 기반 lightweight category rule mapping 추가
- language detection 방식 검토 또는 lightweight helper 추가
- keyword count 기반 importance signal 후보 계산
- 현재 DB의 articles 데이터를 대상으로 classification dry-run 분석 script 추가
- 분석 script에서 window 기준을 지정할 수 있게 한다.
  - 24h
  - 72h
  - 168h
  - all
- 분석 기준 timestamp를 명확히 분리한다.
  - product/topic 기준: published_at
  - collection/operation 기준: created_at
  - published_at이 없으면 created_at fallback
- category별 article count를 출력한다.
- language별 article count를 출력한다.
- source category와 rule-based category가 다른 article 후보를 출력한다.
- importance signal 상위 article 후보를 출력한다.
- DB 반영이 필요할 경우 column/migration 제안만 문서화한다.
- 분석 결과를 verification/devlog에 기록한다.

초기 category 후보는 다음을 기준으로 한다.

- tech
- world
- business
- politics
- security
- ai
- climate
- sports
- unknown

초기 importance signal 후보는 다음을 기준으로 한다.

- title keyword match count
- summary keyword match count
- source category
- article recency
- breaking/live/update 관련 keyword
- geopolitical/conflict/election/market/AI/security 관련 keyword

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
- article row update
- source row update

이번 차수에서는 DB schema migration을 자동 실행하지 않는다.

Codex는 Supabase SQL을 실행하지 않는다.
DB schema 변경이 필요하다고 판단되면 SQL 초안과 migration 필요성을 문서로만 제안한다.

## Expected files

예상 변경 파일은 repository 구조에 따라 조정한다.

- classification helper
  - 예: app/utils/article_classification.py
  - 또는 repository에 더 적합한 위치
- classification analysis script
  - 예: scripts/analyze_article_classification.py
- 필요 시 관련 테스트 파일
  - 예: tests/test_article_classification.py
- docs/tasks/feature-lightweight-article-classification.md
- docs/verification/feature-lightweight-article-classification.md
- docs/pr/feature-lightweight-article-classification.md
- docs/devlog/feature-lightweight-article-classification.md
- docs/reviews/feature-lightweight-article-classification-antigravity.md
- docs/fixes/feature-lightweight-article-classification-approved-fixes.md

## DB changes

이번 차수에서는 DB schema를 변경하지 않는다.

이번 작업은 현재 articles.title, articles.summary, articles.category, articles.published_at, articles.created_at, articles.source_id와 sources 데이터를 읽어 dry-run 분석하는 것을 우선한다.

이번 차수에서 DB에 바로 추가하지 않는 후보:

- articles.detected_language
- articles.rule_category
- articles.importance_score
- articles.importance_signals
- articles.classified_at

다만 분석 결과를 기반으로 후속 차수에서 다음 DB 변경을 검토한다.

- articles.detected_language column 추가
- articles.rule_category column 추가
- articles.importance_score column 추가
- articles.importance_signals JSONB column 추가
- 기존 articles backfill
- category/language index 추가 여부

## API changes

이번 차수에서 신규 API는 추가하지 않는다.

기존 API 응답 구조를 변경하지 않는다.

확인 대상 API:

- /articles
- /collector/status
- /collector/runs

classification 후보 분석은 API가 아니라 script 기반으로 수행한다.

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
.venv/bin/python -m py_compile scripts/analyze_article_classification.py
```

classification helper가 추가된 경우:

```bash
.venv/bin/python -m py_compile app/utils/article_classification.py
```

테스트가 추가된 경우:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

classification analysis 실행 예시:

```bash
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --max-examples 5
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 5
.venv/bin/python scripts/analyze_article_classification.py --window-hours 168 --max-examples 5
```

필요 시 전체 article 기준 dry-run:

```bash
.venv/bin/python scripts/analyze_article_classification.py --all --max-examples 5
```

created_at 기준 운영 분석:

```bash
.venv/bin/python scripts/analyze_article_classification.py --window-hours 24 --time-basis created --max-examples 5
```

API read-only 확인이 필요한 경우:

```bash
curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
curl http://127.0.0.1:8000/collector/status
curl "http://127.0.0.1:8000/collector/runs?limit=5"
```

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db tests
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

테스트 runner가 존재하면 실행한다.

```bash
pytest
```

단, pytest가 설치되어 있지 않다면 verification에 pending으로 기록한다.

## Acceptance criteria

- Lightweight article classification helper가 추가되어 있다.
- Source category를 article의 기본 category로 유지하는 정책이 문서화되어 있다.
- Rule-based category mapping이 deterministic하게 동작한다.
- Rule-based category는 source category를 즉시 덮어쓰지 않는다.
- Title과 summary 기반 keyword rule이 적용된다.
- Language detection 또는 language fallback 정책이 구현되어 있다.
- Language detection이 불확실하면 unknown 또는 source language fallback을 사용한다.
- Importance signal 후보가 계산된다.
- Importance signal은 최종 ranking이 아니라 topic grouping 전 후보 signal로 취급된다.
- Classification analysis script가 현재 DB articles를 read-only로 조회한다.
- Script는 24h / 72h / 168h / all window 분석을 지원한다.
- Script는 published_at 기준 분석을 우선하고, published_at이 없으면 created_at을 fallback으로 사용한다.
- Script는 created_at 기준 운영 분석도 지원한다.
- Script는 category별 count를 출력한다.
- Script는 language별 count를 출력한다.
- Script는 source category와 rule category가 다른 후보를 출력한다.
- Script는 importance signal 상위 후보를 출력한다.
- 분석 결과가 verification/devlog에 기록되어 있다.
- DB migration은 실행하지 않는다.
- DB write는 수행하지 않는다.
- K8s manifest는 변경하지 않는다.
- production-impacting command는 실행하지 않는다.
- LLM, embedding, topic grouping, AI summary는 구현하지 않는다.
- secret, token, private IP, kubeconfig, .env 값은 기록하지 않는다.

## Notes

27차에서 multi-source RSS collection이 적용되어 Supabase DB에 여러 source article metadata가 저장되었다.

28차에서는 URL/title normalization과 duplicate candidate analysis를 구현했다.

29차에서는 topic grouping 전에 article metadata에 대해 lightweight classification signal을 계산한다.

이번 classification은 최종 분류 확정값이 아니라 topic grouping과 topic ranking 전에 사용할 수 있는 후보 signal이다.

source category는 기본 category로 유지한다.
rule-based category는 title과 summary의 keyword rule을 기반으로 계산하되, source category를 바로 덮어쓰지 않는다.

source category와 rule-based category가 다를 수 있으며, 이번 차수에서는 이를 conflict가 아니라 분석 후보로 본다.

수집일과 기사 발행일은 분리해서 본다.

- created_at: NewsLab이 article을 수집/저장한 시각
- published_at: 언론사가 article을 발행한 시각

제품 기준의 “오늘의 뉴스 흐름”은 published_at 기준이 더 적합하다.

운영 기준의 “오늘 몇 개가 새로 들어왔는가”는 created_at 기준이 더 적합하다.

MVP에서는 최근 24시간을 기본 window로 보되, article 수가 부족하면 72시간 또는 168시간 window를 fallback으로 검토한다.

이번 차수에서는 LLM, embedding, topic grouping, AI summary를 사용하지 않는다
