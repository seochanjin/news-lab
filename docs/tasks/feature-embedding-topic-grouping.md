# Task: Embedding 기반 topic grouping MVP

## Goal

NewsLab에 저장된 multi-source article metadata를 기준으로 embedding 기반 topic grouping MVP를 구현한다.

이번 작업의 목적은 27차에서 수집한 multi-source article metadata, 28차 URL/title normalization 결과, 29차 lightweight classification/importance signal을 바탕으로, 의미적으로 유사한 article을 topic 후보로 묶을 수 있는지 검증하는 것이다.

이번 차수에서는 topic summary, frontend 연동, CronJob 자동화, production rollout을 수행하지 않는다.

## Scope

이번 작업 범위는 다음으로 제한한다.

- topic grouping 입력 article 조회 기준 정의
  - 기본: `published_at` 기준
  - fallback: `created_at`
  - 지원 window: 24h, 72h, 168h, all
- article embedding input text 정의
  - title
  - RSS summary
  - source name
  - source/rule category 후보
- embedding generation interface 추가
- embedding provider를 명확히 분리한다.
  - 실제 provider 사용 여부는 환경 변수와 명시 옵션으로 제어한다.
  - API key가 없으면 실행 전 명확한 error를 낸다.
- cosine similarity 계산 helper 추가
- seed-based greedy clustering MVP 구현
- topic candidate analysis script 추가
  - 예: `scripts/analyze_topic_groups.py`
- dry-run mode를 기본값으로 유지한다.
- topic 후보를 JSON으로 출력한다.
- topic별 다음 정보를 출력한다.
  - topic candidate id
  - article count
  - source count
  - category 분포
  - language 분포
  - 대표 article 후보
  - average similarity
  - max importance article
- 29차 importance signal을 대표 article 후보 선정에 참고한다.
- article_embeddings / topics / topic_articles DB 구조 필요성을 문서화한다.
- 분석 결과를 verification/devlog에 기록한다.

## Do not change

이번 차수에서는 다음을 변경하지 않는다.

- topic_summary_ko generation
- key_points generation
- keywords generation using LLM
- article raw_text extraction policy
- raw extractor CronJob
- RSS collector CronJob
- frontend code
- K8s manifests
- CronJob schedule
- production rollout
- Supabase SQL migration execution
- DB provider
- Oracle DB / NoSQL integration
- article/source row update
- automatic DB write of topics
- automatic DB write of embeddings
- summary/completion/chat model 호출

Codex는 Supabase SQL을 실행하지 않는다.

DB schema 변경이 필요하다고 판단되면 SQL 초안과 migration 필요성을 문서로만 제안한다.

## Expected files

예상 변경 파일은 repository 구조에 따라 조정한다.

- embedding helper
  - 예: `app/utils/article_embeddings.py`
- topic grouping helper
  - 예: `app/utils/topic_grouping.py`
- topic grouping analysis script
  - 예: `scripts/analyze_topic_groups.py`
- 필요 시 관련 테스트 파일
  - 예: `tests/test_topic_grouping.py`
  - 예: `tests/test_article_embeddings.py`
- `docs/tasks/feature-embedding-topic-grouping.md`
- `docs/verification/feature-embedding-topic-grouping.md`
- `docs/pr/feature-embedding-topic-grouping.md`
- `docs/devlog/feature-embedding-topic-grouping.md`
- `docs/reviews/feature-embedding-topic-grouping-antigravity.md`
- `docs/fixes/feature-embedding-topic-grouping-approved-fixes.md`

## DB changes

이번 차수에서는 DB schema를 변경하지 않는다.

이번 작업은 현재 articles/sources 데이터를 read-only로 조회하고, embedding/topic grouping 결과를 dry-run JSON으로 출력하는 것을 우선한다.

이번 차수에서 DB에 바로 추가하지 않는 후보:

- `article_embeddings`
- `topics`
- `topic_articles`
- `topic_runs`
- `topic_grouping_runs`

다만 분석 결과를 기반으로 후속 차수에서 다음 DB 변경을 검토한다.

### Candidate table: article_embeddings

- `id`
- `article_id`
- `embedding_model`
- `embedding_vector`
- `embedding_input_hash`
- `created_at`

### Candidate table: topics

- `id`
- `topic_date`
- `window_hours`
- `representative_article_id`
- `title_candidate`
- `category`
- `language`
- `article_count`
- `source_count`
- `importance_score`
- `created_at`

### Candidate table: topic_articles

- `id`
- `topic_id`
- `article_id`
- `similarity_score`
- `is_representative`
- `created_at`

DB migration은 사람이 승인한 별도 차수 또는 approved fix에서만 수행한다.

## API changes

이번 차수에서 신규 API는 추가하지 않는다.

기존 API 응답 구조를 변경하지 않는다.

Topic 관련 API는 이번 차수에서 추가하지 않는다.

후속 차수에서 검토할 API:

- `/topics`
- `/topics/{topic_id}`

이번 차수의 topic grouping 결과는 API가 아니라 script JSON 출력으로 확인한다.

## Test commands

정적 검증:

```bash
git status --short
git diff --stat
git diff --check
```

Python compile 검증:

```bash
.venv/bin/python -m py_compile scripts/analyze_topic_groups.py
```

helper가 추가된 경우:

```bash
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py
```

테스트가 추가된 경우:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

topic grouping dry-run 예시:

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 72 --max-articles 150 --dry-run
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 168 --max-articles 200 --dry-run
```

실제 embedding provider를 사용하는 경우에는 명시 옵션을 요구한다.

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --use-embedding-provider --dry-run
```

API key가 없으면 명확히 실패해야 한다.

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

API key 없이도 helper와 clustering 로직을 검증할 수 있도록 deterministic fake embedding 또는 fixture embedding을 테스트에서 사용한다.

## Acceptance criteria

- Embedding input text 생성 helper가 추가되어 있다.
- Embedding provider interface가 분리되어 있다.
- API key가 필요한 provider는 명시 옵션 없이 자동 실행되지 않는다.
- Cosine similarity helper가 추가되어 있다.
- Seed-based greedy clustering MVP가 구현되어 있다.
- Topic grouping analysis script가 현재 DB articles를 read-only로 조회한다.
- Script는 24h / 72h / 168h / all window 분석을 지원한다.
- Script는 published_at 기준 분석을 우선하고, published_at이 없으면 created_at을 fallback으로 사용한다.
- Script는 created_at 기준 운영 분석도 지원한다.
- Script는 dry-run을 기본값으로 한다.
- Script는 max article limit을 지원한다.
- Script는 topic candidate groups를 JSON으로 출력한다.
- Script는 topic별 article count, source count, category 분포, language 분포를 출력한다.
- Script는 representative article 후보를 출력한다.
- Script는 similarity score를 출력한다.
- 29차 importance signal을 대표 article 후보 선정에 참고한다.
- 분석 결과가 verification/devlog에 기록되어 있다.
- DB migration은 실행하지 않는다.
- DB write는 수행하지 않는다.
- K8s manifest는 변경하지 않는다.
- production-impacting command는 실행하지 않는다.
- topic summary, AI summary, key_points 생성은 구현하지 않는다.
- frontend API 연동은 구현하지 않는다.
- secret, token, private IP, kubeconfig, .env 값은 기록하지 않는다.

## Notes

27차에서 multi-source RSS collection이 적용되어 Supabase DB에 여러 source article metadata가 저장되었다.

28차에서는 URL/title normalization과 duplicate candidate analysis를 구현했다.

29차에서는 lightweight classification과 importance signal 후보를 구현했다.

30차에서는 처음으로 의미 기반 article grouping을 검증한다.

이번 topic grouping은 최종 topic feed가 아니라 MVP 후보 생성이다.

수집일과 기사 발행일은 분리해서 본다.

- created_at: NewsLab이 article을 수집/저장한 시각
- published_at: 언론사가 article을 발행한 시각

제품 기준의 “오늘의 뉴스 흐름”은 published_at 기준이 더 적합하다.

운영 기준의 “오늘 몇 개가 새로 들어왔는가”는 created_at 기준이 더 적합하다.

MVP에서는 최근 24시간을 기본 window로 보되, article 수가 부족하면 72시간 또는 168시간 window를 fallback으로 검토한다.

이번 차수에서는 topic summary와 frontend 연동을 하지 않는다.

Embedding 비용이 발생할 수 있으므로 실제 provider 호출은 명시 옵션과 article limit을 요구한다.

- 실제 embedding provider 호출 전 예상 article 수, 예상 token 수, 예상 비용을 stdout에 출력한다.
- `--use-embedding-provider`를 사용하더라도 `--max-articles`가 없거나 너무 크면 실행을 거부한다.
- 기본 embedding model은 `OPENAI_EMBEDDING_MODEL` 환경변수로 설정하며, 없으면 `text-embedding-3-small`을 사용한다.

실제 OpenAI embedding provider를 사용할 경우 다음 환경변수를 사용한다.

- `OPENAI_EMBEDDING_API_KEY`
- `OPENAI_EMBEDDING_MODEL`
