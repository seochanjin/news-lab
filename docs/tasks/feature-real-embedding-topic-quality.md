# Task: 실제 embedding 기반 topic 품질 검증

## Goal

NewsLab의 30차 embedding topic grouping pipeline을 실제 OpenAI embedding provider로 제한 실행하여 semantic topic grouping 품질을 검증한다.

이번 작업의 목적은 deterministic hash embedding으로 검증한 pipeline이 실제 semantic embedding에서도 의미 있는 topic 후보를 생성하는지 확인하고, 후속 대표 기사 후보 선정 및 raw extraction 단계로 넘어가기 전에 threshold와 grouping 품질을 사람이 검토할 수 있는 근거를 만드는 것이다.

이번 차수에서는 DB schema 변경, topic 저장, article embedding 저장, topic summary 생성, frontend 연동, CronJob 자동화, production rollout을 수행하지 않는다.

## Scope

이번 작업 범위는 다음으로 제한한다.

- 30차 scripts/analyze_topic_groups.py 또는 별도 분석 script를 활용해 실제 OpenAI embedding provider 기반 topic grouping을 제한 실행한다.
- 실제 provider 사용 조건을 유지한다.
  - --use-embedding-provider
  - OPENAI_EMBEDDING_API_KEY
  - 명시적 --max-articles
  - 최대 200건 상한
- 기본 모델은 OPENAI_EMBEDDING_MODEL 환경변수 또는 text-embedding-3-small을 사용한다.
- 기본 분석 대상은 published 기준 최근 24h article이다.
- 분석 article 수는 50~100개를 우선 사용한다.
- threshold 후보를 비교한다.
  - 0.65
  - 0.70
  - 0.72
  - 0.75
  - 0.80
- threshold별 topic candidate 수를 출력한다.
- threshold별 multi-article topic candidate 수를 출력한다.
- threshold별 singleton topic 비율을 출력한다.
- 사람이 검토할 수 있도록 multi-article topic candidate report를 생성한다.
- report에는 topic별 다음 정보를 포함한다.
  - topic candidate id
  - article count
  - source count
  - category distribution
  - language distribution
  - representative article
  - max importance article
  - average similarity
  - article별 title
  - article별 source
  - article별 source category
  - article별 rule category
  - article별 importance score
  - article별 published_at
  - article별 similarity score
- deterministic hash provider 결과와 실제 OpenAI embedding provider 결과의 차이를 문서화한다.
- 실제 provider 호출 전 예상 article 수, token 수, 비용을 출력한다.
- 실제 provider 호출 결과와 비용 추정치를 verification/devlog에 기록한다.
- topic grouping 품질 판단은 자동 확정하지 않고 human review 대상으로 남긴다.
- 사람이 topic grouping 품질을 검토할 수 있는 별도 markdown report를 생성한다.
  - 예: `docs/reports/feature-real-embedding-topic-quality.md`
- verification 문서에는 실행 명령, 통과 여부, 비용 추정, provider 사용 여부, DB write 여부를 기록한다.
- report 문서에는 threshold별 multi-article topic 후보와 사람이 검토할 title/source/similarity 정보를 기록한다.

## Do not change

이번 차수에서는 다음을 변경하지 않는다.

- DB schema
- DB migration
- article_embeddings 저장
- topics 저장
- topic_articles 저장
- article/source/topic row write
- topic summary generation
- key points generation
- keywords generation
- LLM summary call
- raw article extraction execution
- raw extractor CronJob
- RSS collector CronJob
- frontend code
- API router
- K8s manifests
- CronJob schedule
- production rollout
- provider batching/chunking 운영화

Codex는 Supabase SQL을 실행하지 않는다.

Codex는 production-impacting command를 실행하지 않는다.

이번 차수는 실제 OpenAI embedding API를 제한적으로 호출할 수 있지만, 호출은 human operator가 명시적으로 승인한 범위에서만 수행한다.

## Expected files

예상 변경 파일은 repository 구조에 따라 조정한다.

- 기존 topic grouping analysis script 개선 또는 신규 quality report script
  - 예: scripts/analyze_topic_groups.py
  - 또는 scripts/review_topic_group_quality.py
- 필요 시 helper 추가
  - 예: app/utils/topic_quality.py
- 필요 시 테스트 추가
  - 예: tests/test_topic_quality.py
  - 예: tests/test_analyze_topic_groups.py
- docs/tasks/feature-real-embedding-topic-quality.md
- docs/verification/feature-real-embedding-topic-quality.md
- docs/reviews/feature-real-embedding-topic-quality-antigravity.md
- docs/reviews/feature-real-embedding-topic-quality-coderabbit.md
- docs/fixes/feature-real-embedding-topic-quality-approved-fixes.md
- docs/pr/feature-real-embedding-topic-quality.md
- docs/devlog/feature-real-embedding-topic-quality.md
- `docs/reports/feature-real-embedding-topic-quality.md`

## DB changes

이번 차수에서는 DB schema를 변경하지 않는다.

이번 작업은 현재 articles / sources 데이터를 read-only로 조회하고, 실제 OpenAI embedding provider를 제한 실행해 topic grouping 품질 report를 생성하는 것을 우선한다.

이번 차수에서 DB에 바로 추가하지 않는 후보:

- article_embeddings
- topics
- topic_articles
- topic_runs
- topic_grouping_runs

후속 차수에서 다음을 검토한다.

- embedding input hash 기반 cache
- article_id + embedding_model + embedding_input_hash unique policy
- topic grouping run history
- threshold/model별 품질 비교 기록 방식
- representative article 후보 저장 여부

## API changes

이번 차수에서 신규 API는 추가하지 않는다.

기존 API 응답 구조를 변경하지 않는다.

Topic 관련 API는 이번 차수에서 추가하지 않는다.

후속 차수에서 검토할 API:

- /topics
- /topics/{topic_id}

이번 차수의 결과는 API가 아니라 script output과 verification/devlog report로 확인한다.

## Test commands

정적 검증:

```bash
git status --short --branch
git diff --stat
git diff --check
```

Python compile 검증:

```bash
.venv/bin/python -m py_compile scripts/analyze_topic_groups.py
```

신규 helper나 script가 추가된 경우:

```bash
.venv/bin/python -m py_compile app/utils/topic_quality.py scripts/review_topic_group_quality.py
```

테스트가 추가된 경우:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

기본 dry-run 확인:

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
```

실제 OpenAI embedding provider 품질 검증은 human operator가 명시적으로 승인한 뒤 제한 실행한다.

예시:

```bash
.venv/bin/python scripts/analyze_topic_groups.py \
  --window-hours 24 \
  --max-articles 50 \
  --use-embedding-provider \
  --dry-run
```

threshold 비교 기능이 추가된 경우:

```bash
.venv/bin/python scripts/analyze_topic_groups.py \
  --window-hours 24 \
  --max-articles 100 \
  --use-embedding-provider \
  --thresholds 0.65,0.70,0.72,0.75,0.80 \
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

- 실제 OpenAI embedding provider를 제한 실행할 수 있다.
- 실제 provider 호출은 --use-embedding-provider, OPENAI_EMBEDDING_API_KEY, 명시적 --max-articles 없이는 수행되지 않는다.
- --max-articles 상한은 200건 이하로 유지된다.
- 실제 provider 호출 전 예상 article 수, token 수, 비용이 출력된다.
- 실제 provider 호출 결과가 verification/devlog에 기록된다.
- threshold 후보별 topic candidate 수가 출력된다.
- threshold 후보별 multi-article topic candidate 수가 출력된다.
- threshold 후보별 singleton topic 비율이 출력된다.
- multi-article topic candidate를 사람이 검토할 수 있는 report가 생성된다.
- report에는 article title, source, category, rule category, importance score, similarity score가 포함된다.
- deterministic hash provider 결과와 실제 OpenAI embedding provider 결과의 차이가 문서화된다.
- semantic grouping 품질은 자동 확정하지 않고 human review 대상으로 남긴다.
- DB migration은 실행하지 않는다.
- DB write는 수행하지 않는다.
- K8s manifest는 변경하지 않는다.
- production-impacting command는 실행하지 않는다.
- topic summary, AI summary, key_points 생성은 구현하지 않는다.
- frontend API 연동은 구현하지 않는다.
- raw article extraction은 실행하지 않는다.
- secret, token, private IP, kubeconfig, .env 값은 기록하지 않는다.
- Human-reviewable markdown report가 생성되어 있다.
- Report에는 threshold별 multi-article topic candidate가 포함되어 있다.
- Report에는 topic별 article title, source, similarity, importance score가 포함되어 있다.
- Report에는 human review status가 pending으로 남아 있다.

## Notes

27차에서 multi-source RSS collection이 적용되어 Supabase DB에 여러 source article metadata가 저장되었다.

28차에서는 URL/title normalization과 duplicate candidate analysis를 구현했다.

29차에서는 lightweight classification과 importance signal 후보를 구현했다.

30차에서는 embedding input, provider interface, cosine similarity, seed-based greedy clustering을 구현했다. 다만 30차는 deterministic local hash embedding으로 pipeline과 safety gate를 검증한 단계였고, 실제 semantic embedding 품질 검증은 수행하지 않았다.

31차에서는 실제 OpenAI embedding provider를 제한적으로 사용해 semantic topic grouping 품질을 검토한다.

이번 차수의 핵심 질문은 다음이다.

- 실제 embedding을 쓰면 같은 사건 기사들이 잘 묶이는가?
- threshold 0.72가 적절한가?
- 더 낮은 threshold는 서로 다른 사건을 과하게 묶는가?
- 더 높은 threshold는 같은 사건도 너무 많이 분리하는가?
- representative article 후보가 사람이 보기에도 적절한가?
- 32차 대표 기사 후보 선정 단계로 넘어갈 수 있는가?

이번 차수는 topic summary 생성이 아니다.

이번 차수는 raw extraction 실행이 아니다.

이번 차수는 DB 저장이 아니다.

실제 provider 호출 비용은 제한된 article 수에서는 매우 작지만, 호출 조건과 결과를 반드시 verification에 기록한다.
