# Task: Topic 대표 기사 후보 선정 MVP

## Goal

31차에서 검증한 실제 embedding 기반 topic grouping 결과를 바탕으로, topic별 raw extraction 대상이 될 대표 기사 후보를 read-only로 선정한다.

이번 작업의 목적은 topic group 안에서 어떤 article을 대표 후보로 삼을지 판단할 수 있는 scoring/ranking 기준을 만들고, 사람이 검토할 수 있는 markdown report를 생성하는 것이다.

이번 차수에서는 raw article extraction을 실행하지 않는다.

이번 차수에서는 topic summary를 생성하지 않는다.

이번 차수에서는 topic, article embedding, topic_articles, representative candidate를 DB에 저장하지 않는다.

32차는 대표 기사 후보 선정 정책과 report 검증 단계다.

## Scope

- 기존 topic grouping 분석 결과를 기반으로 topic별 representative article candidate를 선정한다.
- 기본 similarity threshold 후보는 0.70을 사용한다.
- 보수적 fallback threshold로 0.72를 사용할 수 있게 한다.
- topic별 대표 기사 후보는 기본적으로 최대 3개까지 선정한다.
- 대표 후보 선정 기준을 명시적으로 계산한다.
- 후보 선정 기준에는 다음 signal을 포함한다.
  - importance_score
  - topic seed 여부
  - topic 내 similarity score
  - source diversity
  - title/summary 정보량
  - published_at 최신성
  - source category / rule category
- 후보별 선정 사유를 report에 출력한다.
- report에는 topic별 다음 정보를 포함한다.
  - topic candidate id
  - article count
  - source count
  - category distribution
  - language distribution
  - representative candidate rank
  - article title
  - source
  - source category
  - rule category
  - importance score
  - similarity score
  - published_at
  - candidate score
  - candidate score components
  - selection reason
  - human review status
- 전체 summary에는 다음 정보를 포함한다.
  - analyzed article count
  - topic candidate count
  - multi-article topic count
  - representative candidate count
  - threshold
  - provider/model
  - DB write 여부
- 31차 report와 구분되는 별도 report를 생성한다.
  - 예: docs/reports/feature-topic-representative-candidates.md
- 대표 후보 선정 결과는 사람이 검토할 수 있는 markdown 형태로 남긴다.
- 결과는 read-only로 유지한다.
- 실제 OpenAI embedding provider를 다시 호출할 수는 있지만, 호출은 human operator가 명시적으로 승인한 범위에서만 수행한다.
- 기본 구현과 테스트는 fake/deterministic embedding 또는 mock provider 기반으로 검증한다.

## Do not change

이번 차수에서는 다음을 변경하지 않는다.

- DB schema
- DB migration
- article_embeddings 저장
- topics 저장
- topic_articles 저장
- representative candidate 저장
- article/source row update
- raw article extraction 실행
- raw extractor CronJob
- RSS collector CronJob
- topic summary generation
- key points generation
- keywords generation
- LLM/chat/summary API call
- frontend code
- API router
- K8s manifests
- CronJob schedule
- production rollout
- provider batching/chunking 운영화

Codex는 Supabase SQL을 실행하지 않는다.

Codex는 production-impacting command를 실행하지 않는다.

## Expected files

예상 변경 파일은 repository 구조에 따라 조정한다.

- 대표 후보 선정 helper
  - 예: app/utils/topic_representatives.py
- 기존 분석 script 개선 또는 신규 script
  - 예: scripts/analyze_topic_representatives.py
  - 또는 scripts/analyze_topic_groups.py 확장
- 테스트
  - 예: tests/test_topic_representatives.py
  - 필요 시 tests/test_analyze_topic_representatives.py
- report
  - docs/reports/feature-topic-representative-candidates.md
- verification
  - docs/verification/feature-topic-representative-candidates.md
- reviews
  - docs/reviews/feature-topic-representative-candidates-antigravity.md
  - docs/reviews/feature-topic-representative-candidates-coderabbit.md
- fixes
  - docs/fixes/feature-topic-representative-candidates-approved-fixes.md
- PR document
  - docs/pr/feature-topic-representative-candidates.md
- devlog
  - docs/devlog/feature-topic-representative-candidates.md

## DB changes

이번 차수에서는 DB schema를 변경하지 않는다.

이번 작업은 현재 articles / sources 데이터를 read-only로 조회하고, topic grouping 결과에서 대표 기사 후보를 계산하는 분석 단계다.

이번 차수에서 DB에 추가하지 않는다.

- article_embeddings
- topics
- topic_articles
- topic_representatives
- topic_runs
- topic_grouping_runs

후속 차수에서 다음을 검토한다.

- representative candidate 저장 여부
- representative selection run history
- selected article의 raw extraction 대상화
- representative selection score versioning
- source diversity policy 저장 방식

## API changes

이번 차수에서 신규 API는 추가하지 않는다.

기존 API 응답 구조를 변경하지 않는다.

Topic 관련 API는 이번 차수에서 추가하지 않는다.

이번 차수의 결과는 API가 아니라 script output과 markdown report로 확인한다.

## Test commands

정적 검증:

```bash
git status --short --branch
git diff --stat
git diff --check
```

Python compile 검증:

```bash
.venv/bin/python -m py_compile app/utils/topic_representatives.py scripts/analyze_topic_representatives.py
```

테스트:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

CLI help:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py --help
```

기본 deterministic/read-only report 생성:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.70 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates.md \
  --dry-run
```

보수 threshold 확인:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates-threshold-072.md \
  --dry-run
```

실제 OpenAI embedding provider를 다시 사용할 경우, human operator의 명시적 승인 후 제한 실행한다.

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --use-embedding-provider \
  --similarity-threshold 0.70 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates.md \
  --dry-run
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

신규 파일 대상 보안 검사:

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

테스트 runner가 존재하면 실행한다.

```bash
pytest
```

단, pytest가 설치되어 있지 않다면 verification에 pending으로 기록한다.

## Acceptance criteria

- topic별 대표 기사 후보를 최대 3개까지 선정할 수 있다.
- 대표 후보 선정은 read-only로 수행된다.
- 대표 후보 선정 결과는 markdown report로 생성된다.
- report에는 candidate score와 score component가 포함된다.
- report에는 candidate selection reason이 포함된다.
- report에는 topic별 article title, source, category, rule category, importance score, similarity score, published_at이 포함된다.
- report에는 selected candidate와 non-selected article을 구분할 수 있다.
- source diversity를 고려한다.
- importance score만으로 대표 후보를 단정하지 않는다.
- seed article, similarity 중심성, source diversity, 정보량, 최신성 중 최소 3개 이상의 signal을 scoring에 반영한다.
- 기본 threshold 후보 0.70을 사용할 수 있다.
- 보수 fallback threshold 0.72를 사용할 수 있다.
- 실제 provider 호출은 opt-in safety gate 뒤에서만 가능하다.
- 실제 provider 호출 없이도 deterministic/mock 기반 test가 통과한다.
- DB migration은 실행하지 않는다.
- DB write는 수행하지 않는다.
- K8s manifest는 변경하지 않는다.
- production-impacting command는 실행하지 않는다.
- raw article extraction은 실행하지 않는다.
- topic summary, AI summary, key_points 생성은 구현하지 않는다.
- frontend/API 연동은 구현하지 않는다.
- secret, token, private IP, kubeconfig, .env 값은 기록하지 않는다.

## Notes

27차에서 multi-source RSS collection이 적용되어 여러 source article metadata가 저장되었다.

28차에서는 URL/title normalization과 exact duplicate candidate analysis를 구현했다.

29차에서는 lightweight classification과 importance signal 후보를 구현했다.

30차에서는 embedding input, provider interface, cosine similarity, seed-based greedy clustering을 구현했다.

31차에서는 실제 OpenAI embedding provider를 제한 실행하여 semantic grouping 품질을 검증했다. 샘플 기준 0.70을 기본 threshold 후보, 0.72를 보수 fallback 후보로 남겼다.

32차에서는 topic group 안에서 raw extraction 대상으로 삼을 대표 기사 후보를 고르는 정책을 만든다.

이번 차수의 핵심 질문은 다음이다.

- topic group 안에서 어떤 article이 대표 후보로 적절한가?
- importance score가 높은 article과 similarity 중심 article이 다를 때 어떤 기준을 우선할 것인가?
- 같은 source article이 여러 개 있을 때 source diversity를 어떻게 반영할 것인가?
- title/summary 정보량이 부족한 article을 후보에서 낮출 수 있는가?
- raw extraction 대상으로 1개만 고를지, 2~3개 후보를 남길지 판단할 수 있는가?

이번 차수는 raw extraction 실행이 아니다.

이번 차수는 topic summary 생성이 아니다.

이번 차수는 DB 저장이 아니다.

대표 후보 선정 결과는 후속 raw extraction 대상 선정의 입력으로 사용한다.
