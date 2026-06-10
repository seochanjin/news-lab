# Topic 대표 기사 후보 선정 MVP

## 작업 내용

- 기존 seed-based topic grouping 결과를 기반으로 topic별 대표 기사 후보를
  최대 3개까지 read-only로 선정한다.
- importance 단일 기준이 아닌 여러 signal의 candidate score와 선정 사유를
  계산하고 사람이 검토할 수 있는 markdown report를 생성한다.
- 기본 similarity threshold `0.70`과 보수적 fallback `0.72`를 지원한다.

## 주요 변경 사항

- 대표 후보 scoring에 importance, topic seed, similarity, source diversity,
  title/summary 정보량, 최신성, source/rule category signal을 반영했다.
- source diversity를 고려해 후보를 순차 선택하고 selected/non-selected,
  rank, score components, selection reason, human review status를 출력한다.
- topic grouping member 결과에 summary와 topic seed 여부를 포함했다.
- read-only 분석 CLI를 추가하고 실제 embedding provider는 명시적 opt-in,
  API key, article limit safety gate 뒤에서만 사용할 수 있게 유지했다.
- 승인된 Fix 1~3을 적용해 기본 report는 multi-article topic만 상세 출력하고,
  `--include-singletons` 옵션과 recency 기준 시각, candidate score 사용 범위
  설명을 추가했다.
- 승인된 Fix 4를 적용해 deterministic 검증 report를 `-deterministic`
  전용 경로에 생성하고 OpenAI provider report 경로와 분리했다.

## 추가/변경된 API

- 신규 API 없음.
- 기존 FastAPI router와 API 응답 구조 변경 없음.
- 결과는 CLI JSON output과 markdown report로 확인한다.

## DB 변경 사항

- DB schema 및 migration 변경 없음.
- `articles`와 `sources`를 read-only transaction으로 조회한다.
- topic, embedding, topic article, representative candidate 저장 및
  article/source row update를 수행하지 않는다.

## README 영향

- README 변경 없음.
- 이번 작업은 분석 helper, CLI, tests, workflow 문서와 report에 한정되어
  README 갱신이 필요하지 않다.

## 테스트

- Python compile:
  `.venv/bin/python -m py_compile app/utils/topic_grouping.py app/utils/topic_representatives.py scripts/analyze_topic_representatives.py`
- Focused unittest:
  `.venv/bin/python -m unittest tests.test_topic_grouping tests.test_topic_representatives tests.test_analyze_topic_representatives -v`
- Full unittest:
  `.venv/bin/python -m unittest discover -s tests -v`
- CLI help:
  `.venv/bin/python scripts/analyze_topic_representatives.py --help`
- Deterministic report 생성:
  threshold `0.70`, threshold `0.72`, `--include-singletons`
- Static scope 검사:
  `git status`, `git diff --stat`, `git diff --check`, K8s 및 변경 범위 확인
- Credential-pattern 검사:
  `git grep`, `rg`

## 확인 결과

- Python compile: 통과.
- Focused unittest: `15 passed`.
- Full unittest: `54 passed`.
- CLI help: 통과.
- Threshold `0.70` deterministic report:
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics / report detail topics: 3 / 3
  - representative candidates: 100
  - DB write performed: false
- Threshold `0.72` deterministic report:
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics / report detail topics: 2 / 2
  - representative candidates: 99
  - DB write performed: false
- Singleton 포함 deterministic report: topic detail 96개 출력 확인.
- Deterministic report는 `-deterministic` 경로에 생성되어 OpenAI provider
  report 경로를 덮어쓰지 않았다.
- `git diff --check`: 통과.
- K8s 변경 없음.
- Security 검사에서 실제 credential 값은 발견되지 않았다.
- `pytest`: executable이 설치되어 있지 않아 미실행/pending.

## 비고

- 실제 OpenAI embedding provider는 호출하지 않았다.
  `--use-embedding-provider`는 실제 API 호출과 비용이 발생할 수 있어
  human operator의 명시적 승인 후에만 실행한다.
- Production verification, Supabase SQL, migration, raw extraction, summary,
  Kubernetes command, rollout, deployment, push, merge는 수행하지 않았다.
- 후보 적합성, source diversity 가중치, 후보 수에 대한 human review와
  실제 provider 비교는 pending이다.
- 테스트 및 검증 결과의 source of truth는
  `docs/verification/feature-topic-representative-candidates.md`이다.
