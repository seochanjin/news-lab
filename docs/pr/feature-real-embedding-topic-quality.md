# 실제 embedding 기반 topic 품질 검증

## 작업 내용

- 기존 read-only topic grouping 분석 스크립트에서 실제 OpenAI embedding과 deterministic hash embedding의 threshold별 결과를 비교할 수 있도록 확장했다.
- `0.65`, `0.70`, `0.72`, `0.75`, `0.80` threshold별 topic candidate 수, multi-article topic 수, singleton 수와 비율을 계산한다.
- 사람이 topic grouping 품질을 검토할 수 있도록 multi-article topic 상세 markdown report를 생성한다.
- 실제 provider 호출 전 article 수, 예상 token 수와 예상 비용을 출력하며, 기존 provider safety gate와 DB read-only 동작을 유지한다.

## 주요 변경 사항

- `app/utils/topic_quality.py`
  - threshold 문자열 파싱과 중복 제거, 범위 검증을 추가했다.
  - 동일한 article/embedding 집합을 여러 threshold로 비교하는 품질 지표 계산을 추가했다.
  - topic별 title, source, category, rule category, importance, published time, similarity를 포함하는 markdown report renderer를 추가했다.
- `scripts/analyze_topic_groups.py`
  - `--thresholds`, `--report-path` 옵션을 추가했다.
  - 실제 provider 모드에서는 동일 article 집합의 deterministic hash 비교 요약도 함께 생성한다.
  - 승인된 Fix 1을 적용해 argument/provider validation 전에 `load_dotenv()`를 호출한다.
  - `--use-embedding-provider`, API key, 명시적 `--max-articles`, 최대 200건 제한은 그대로 유지한다.
- `tests/test_topic_quality.py`, `tests/test_analyze_topic_groups.py`
  - threshold 비교, singleton 비율, report 필드, provider 비교, 외부 API 미호출, `.env` 로딩 및 provider gate 유지 여부를 검증한다.
- `docs/reports/feature-real-embedding-topic-quality.md`
  - 실제 OpenAI embedding 제한 실행 결과와 deterministic hash 비교 결과를 기록했다.

## 추가/변경된 API

- 신규 API는 추가하지 않았다.
- 기존 API router와 응답 구조를 변경하지 않았다.

## DB 변경 사항

- DB schema와 migration 변경은 없다.
- 분석은 기존 `articles`/`sources` 데이터를 read-only로 조회하며 DB write를 수행하지 않는다.
- `article_embeddings`, `topics`, `topic_articles` 등 topic 관련 데이터 저장은 이번 범위에 포함하지 않았다.

## README 영향

- README 변경은 필요하지 않다.
- 이번 변경은 내부 read-only 분석 스크립트와 품질 검토 report에 한정되며, 공개 API나 운영 실행 절차를 변경하지 않는다.

## 테스트

실행 및 통과:

```bash
.venv/bin/python -m py_compile app/utils/topic_quality.py scripts/analyze_topic_groups.py tests/test_topic_quality.py tests/test_analyze_topic_groups.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_groups.py --help
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

- 최종 전체 unittest suite: 42 tests passed.
- compile과 CLI help 확인을 통과했다.
- mock/fake embedding 기반 테스트에서 외부 API를 호출하지 않았다.
- `git diff --check`를 통과했고 K8s 변경은 없었다.
- `.venv/bin/pytest`는 설치되어 있지 않아 pending이다.

## 확인 결과

- published 기준 최근 24시간 deterministic baseline을 read-only로 실행했다.
  - 조회 article: 70건
  - embedding model: `deterministic-hash-v1`
  - provider 사용: `false`
  - DB write: `false`
- deterministic baseline에서 threshold별 multi-article topic 수는 `0.65: 5`, `0.70: 2`, `0.72: 2`, `0.75: 1`, `0.80: 0`으로 확인됐다.
- human-approved 실제 OpenAI embedding provider 제한 실행 기록:
  - model: `text-embedding-3-small`
  - article: 68건
  - published 기준 최근 24시간
  - 예상 token: 5,896
  - 예상 비용: USD 0.000118
  - DB write: `false`
  - 추천 threshold 후보: `0.70`
  - 보수적 fallback 후보: `0.72`
- 실제 provider 결과와 deterministic hash 결과를 포함한 검토 report를 생성했다.
- 승인된 `.env` 자동 로드 fix 적용 후 compile, 42개 unittest, CLI, static scope 및 보안 검사를 통과했다.
- fix 적용 후 실제 provider 명령은 billable 외부 API 호출 가능성이 있어 재실행하지 않았다.

## 비고

- semantic grouping 품질과 최종 threshold 확정은 계속 human review 대상이다.
- topic summary, key points, keywords, LLM summary, raw extraction, frontend 연동, API, DB 저장, K8s/CronJob 변경은 수행하지 않았다.
- `.env` 파일과 secret 값은 수정하거나 출력하지 않았다.
- production verification, K3s rollout, deployment, git push, PR merge는 수행하지 않았으며 pending이다.
