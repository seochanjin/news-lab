# 실제 embedding 기반 topic 품질 검증

## 작업 목적

30차에서 deterministic hash embedding으로 검증한 topic grouping pipeline을 실제 OpenAI embedding provider로 제한 실행해 semantic grouping 품질을 확인한다.

대표 기사 선정이나 topic 저장 단계로 넘어가기 전에 여러 similarity threshold의 과묶음·과분리 경향을 비교하고, 사람이 검토할 수 있는 근거를 남기는 것이 목적이다.

## 기존 문제

- 기존 분석은 한 번에 하나의 similarity threshold만 확인할 수 있어 threshold별 품질 차이를 비교하기 어려웠다.
- Topic candidate 수뿐 아니라 multi-article topic 수와 singleton 비율을 함께 확인하는 지표가 없었다.
- Multi-article topic에 포함된 기사 제목, 출처, category, importance, similarity를 사람이 검토할 수 있는 별도 report가 없었다.
- Deterministic hash embedding은 pipeline 동작 확인에는 유용하지만 semantic 유사도를 반영하지 않아 실제 topic 품질 근거로 사용하기 어려웠다.
- 실제 provider 실행 시 프로젝트 `.env`를 자동으로 로드하지 않아, 별도 shell 설정 없이는 API key safety gate를 통과할 수 없는 사용성 문제가 있었다.

## 변경 내용

- `app/utils/topic_quality.py`
  - threshold 문자열 파싱, 중복 제거, 범위 검증을 추가했다.
  - threshold별 topic 수, multi-article topic 수, singleton 수와 비율을 계산한다.
  - topic/article 상세와 human review 항목을 포함한 markdown report를 생성한다.
- `scripts/analyze_topic_groups.py`
  - `--thresholds`, `--report-path` 옵션을 추가했다.
  - 실제 provider 모드에서 동일 article 집합의 deterministic hash 결과를 함께 비교한다.
  - provider 호출 전 예상 article 수, token 수와 비용을 출력한다.
  - 승인된 Fix 1로 argument/provider validation 전에 `load_dotenv()`를 호출한다.
- `tests/test_topic_quality.py`, `tests/test_analyze_topic_groups.py`
  - threshold 지표, report 내용, deterministic 비교, provider gate, `.env` 로딩을 검증한다.
- `docs/reports/feature-real-embedding-topic-quality.md`
  - 실제 OpenAI embedding과 deterministic hash의 threshold별 결과 및 multi-article topic 상세를 기록했다.

## 구현 상세

- 하나의 embedding 결과를 모든 threshold에 재사용해 threshold 비교 시 불필요한 provider 재호출을 피했다.
- 비교 threshold는 `0.65`, `0.70`, `0.72`, `0.75`, `0.80`을 사용한다.
- Report에는 topic candidate ID, article/source 수, category/language 분포, 대표 기사, 최대 importance 기사, 평균 similarity와 article별 상세를 포함한다.
- Provider safety gate는 그대로 유지했다.
  - `--use-embedding-provider` 명시
  - `OPENAI_EMBEDDING_API_KEY` 존재
  - 명시적 `--max-articles`
  - 최대 200건 상한
- 분석 DB transaction은 read-only이며 결과를 DB에 저장하지 않는다.
- `.env` 자동 로딩은 validation 전에 수행하지만 `.env` 파일이나 secret 값은 수정하거나 출력하지 않는다.

## 대안 검토

- **단일 threshold 유지:** 구현은 단순하지만 `0.72`의 적절성과 과묶음·과분리 경향을 비교할 근거가 부족해 제외했다.
- **Threshold마다 provider를 재호출:** 각 실행을 독립적으로 만들 수 있지만 동일 입력에 반복 비용이 발생하므로 제외했다.
- **Deterministic hash 결과만 사용:** 외부 비용 없이 pipeline을 검증할 수 있지만 semantic 품질을 판단할 수 없어 실제 provider 제한 실행과 병행했다.
- **Topic과 embedding을 즉시 DB에 저장:** 후속 API와 운영 자동화에 유리하지만 품질 기준이 확정되지 않은 상태에서 schema와 저장 정책을 고정하게 되므로 이번 범위에서 제외했다.
- **자동 점수로 최종 threshold 확정:** 지표 비교는 가능하지만 실제 같은 사건 여부와 대표 기사 적합성은 사람 판단이 필요해 자동 확정하지 않았다.

## 선택한 접근과 근거

기존 read-only 분석 스크립트를 확장하고, 한 번 생성한 embedding으로 여러 threshold를 비교하는 방식을 선택했다.

이 방식은 기존 provider safety gate와 grouping 로직을 재사용하면서도 실제 provider 비용을 제한한다. 또한 동일 article 집합에서 실제 embedding과 deterministic hash 결과를 함께 출력하므로 semantic embedding의 개선 정도를 사람이 직접 비교할 수 있다.

DB 저장과 운영 자동화는 품질 기준이 확정된 이후로 미뤘다. 이번 단계에서는 재현 가능한 script output, verification 기록, human-reviewable report를 품질 판단 근거로 삼았다.

## 트레이드오프

- Seed-based greedy grouping과 threshold 비교는 단순하고 해석하기 쉽지만, 기사 순서와 seed 선택에 영향을 받을 수 있다.
- 낮은 threshold는 관련 이슈를 폭넓게 묶지만 서로 다른 사건을 과하게 묶을 가능성이 있다.
- 높은 threshold는 오탐을 줄이는 대신 같은 사건 기사도 singleton으로 분리할 가능성이 있다.
- 실제 provider 제한 실행은 semantic 품질 근거를 제공하지만 비용과 외부 API 의존성이 있으므로 자동 반복 실행하지 않았다.
- Markdown report는 사람이 검토하기 쉽지만 품질 판단 결과를 구조화해 장기 추적하거나 자동 비교하는 기능은 아직 없다.

## 테스트

Verification에 기록된 실제 실행 결과:

- Python compile 통과.
- 최종 전체 unittest suite: **42 tests passed**.
- CLI help 통과, 기존 옵션과 `--thresholds`, `--report-path` 확인.
- Fake/deterministic embedding과 mock provider 테스트에서 외부 API 미호출 확인.
- API key가 없을 때 provider 실행이 DB 접근 전에 명확히 실패함을 확인.
- `.env` 자동 로딩 호출과 key-missing provider gate 유지 여부를 mock 기반으로 확인.
- `git diff --check` 통과.
- K8s 변경 없음.
- 보안 검사에서 credential 값 미검출.
- `.venv/bin/pytest`는 설치되어 있지 않아 **pending**.

승인된 Fix 1 적용 후 실제 provider 명령은 billable 외부 API 호출 가능성이 있어 재실행하지 않았다.

## 운영 반영

- 운영 배포 및 production verification: **pending**
- K3s manifest apply 및 rollout: 수행하지 않음
- Supabase SQL, DB migration 및 DB write: 수행하지 않음
- Raw extraction 및 CronJob 실행/변경: 수행하지 않음
- Git push 및 PR merge: 수행하지 않음

Human-approved 실제 provider 실행은 품질 분석을 위한 제한된 read-only 실행이며 production 배포 완료를 의미하지 않는다.

## README 업데이트 판단

README는 변경하지 않았다.

이번 변경은 내부 read-only 분석 스크립트와 품질 검토 report에 한정된다. 공개 API, DB schema, 배포 방식, 일반 운영 명령이 변경되지 않았으므로 현재 README에 반영할 사용자-facing 변경은 없다.

## 확인 결과

- Published 기준 최근 24시간 deterministic baseline:
  - 조회 article: 70건
  - embedding model: `deterministic-hash-v1`
  - DB write: `false`
  - `0.65`: topic 65개, multi-article 5개, singleton 비율 0.9231
  - `0.70`: topic 68개, multi-article 2개, singleton 비율 0.9706
  - `0.72`: topic 68개, multi-article 2개, singleton 비율 0.9706
  - `0.75`: topic 69개, multi-article 1개, singleton 비율 0.9855
  - `0.80`: topic 70개, multi-article 0개, singleton 비율 1.0
- Human-approved 실제 OpenAI embedding provider 제한 실행:
  - model: `text-embedding-3-small`
  - article: 68건
  - time basis/window: `published`, 24시간
  - 예상 token: 5,896
  - 예상 비용: USD 0.000118
  - DB write: `false`
  - 추천 threshold 후보: `0.70`
  - 보수적 fallback 후보: `0.72`
- Deterministic baseline에는 unrelated article 과묶음 후보가 포함되어 semantic 품질 근거로 사용할 수 없음을 확인했다.
- 실제 provider 결과와 deterministic hash 결과를 포함한 markdown report를 생성했다.
- 최종 threshold 확정과 전체 grouping 품질 판단은 계속 human review 대상으로 남긴다.

## 이번 단계의 의미

Pipeline 동작 검증에 머물렀던 deterministic embedding 단계에서 실제 semantic embedding 품질을 제한된 비용으로 검토하는 단계로 진행했다.

동일 article 집합과 여러 threshold를 비교할 수 있는 지표와 report를 확보했으며, 현재 샘플에서는 `0.70`을 기본 후보, `0.72`를 보수적 후보로 후속 검토할 근거를 만들었다. 동시에 DB 저장과 운영 자동화를 분리해 품질 기준이 확정되기 전에 운영 구조를 고정하는 위험을 피했다.

## 포트폴리오용 요약

뉴스 article metadata를 대상으로 실제 OpenAI embedding과 deterministic baseline을 비교하는 read-only topic 품질 분석 도구를 구현했다. 한 번 생성한 embedding을 여러 similarity threshold에 재사용해 topic 수, multi-article 후보, singleton 비율을 계산하고, 사람이 같은 사건 묶음과 대표 기사를 검토할 수 있는 markdown report를 생성했다. Provider opt-in, API key, article 상한, 비용 사전 추정과 DB read-only 조건을 유지해 외부 API 비용과 데이터 변경 위험을 통제했다.

## 다음 단계 후보

- Multi-article 후보의 same-event grouping, 과묶음, 대표 기사 적합성을 추가 human review한다.
- 기본 threshold `0.70`과 보수적 fallback `0.72` 중 운영 후보를 확정한다.
- 대표 기사 선정 기준과 후보 생성 단계를 설계한다.
- Embedding input hash 기반 cache와 모델별 embedding 저장 정책을 검토한다.
- Topic grouping run history와 threshold/model별 품질 비교 기록 방식을 설계한다.
- 품질 기준 확정 후에만 `article_embeddings`, `topics`, `topic_articles` 저장과 topic API를 검토한다.
