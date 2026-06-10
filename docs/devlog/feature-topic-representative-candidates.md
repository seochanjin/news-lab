# Topic 대표 기사 후보 선정 MVP

## 작업 목적

- 기존 embedding 기반 topic grouping 결과에서 후속 raw extraction 대상으로
  검토할 대표 기사 후보를 topic별 최대 3개까지 선정한다.
- importance 단일 기준이 아니라 여러 signal을 명시적으로 계산하고,
  사람이 후보 적합성을 검토할 수 있는 read-only report를 만든다.
- 이번 단계에서는 후보 정책과 report 품질만 검증하고 DB 저장, raw
  extraction, topic summary 생성은 수행하지 않는다.

## 기존 문제

- 기존 topic grouping의 대표 기사는 최고 importance 기사와 동일해 topic
  seed, similarity 중심성, source diversity, 정보량, 최신성을 함께
  비교하지 못했다.
- 후보별 점수 구성요소와 선정 사유가 없어 사람이 ranking 근거를
  확인하기 어려웠다.
- singleton topic까지 모두 상세 출력하면 핵심 검토 대상인 multi-article
  topic을 찾기 어려웠다.
- `published_at`이 없을 때 `created_at`을 recency fallback으로 사용하지만
  기존 report에서는 어떤 시각을 사용했는지 확인하기 어려웠다.
- deterministic 검증 report와 OpenAI provider report가 같은 경로를
  사용할 수 있어 human-approved provider 산출물이 덮어써질 위험이 있었다.

## 변경 내용

- 대표 후보 점수를 다음 7개 component로 구성했다.
  - importance
  - topic seed
  - similarity
  - source diversity
  - title/summary information
  - recency
  - source/rule category
- 후보를 순차 선택하면서 이미 선택된 source를 감점해 source diversity를
  반영했다.
- topic별 최대 후보 수를 기본 3개로 제한하고 selected/non-selected,
  rank, score components, selection reason, human review status를 남겼다.
- 기본 threshold `0.70`과 보수 fallback `0.72`를 지원하는 read-only
  분석 CLI를 추가했다.
- 승인된 Fix 1~4를 적용했다.
  - 기본 report는 multi-article topic만 상세 출력
  - `--include-singletons` 옵션 제공
  - published/created 시각과 recency time source 표시
  - candidate score의 topic 내부 비교 범위 명시
  - deterministic report와 OpenAI provider report 경로 분리

## 구현 상세

- `app/utils/topic_grouping.py`
  - topic member serialization에 summary와 `is_topic_seed`를 포함했다.
- `app/utils/topic_representatives.py`
  - component별 normalized/weight/weighted 값을 계산하고 합산해 candidate
    score를 만든다.
  - source diversity는 이전에 선택된 source인지에 따라 다음 후보 점수에
    반영한다.
  - `published_at`이 없으면 `created_at`을 recency 계산에 사용하고,
    `recency_time_source`를 report에 표시한다.
  - markdown 기본 상세 출력은 multi-article topic으로 제한한다.
- `scripts/analyze_topic_representatives.py`
  - 기존 article 조회, 분류, deterministic embedding, grouping 흐름을
    재사용한다.
  - DB 연결 후 `set transaction read only`를 실행한다.
  - 실제 provider는 `--use-embedding-provider`, API key, 명시적 article
    limit이 모두 있어야 사용할 수 있다.
- report 산출물
  - deterministic 검증 report는 `-deterministic` 전용 경로에 저장한다.
  - 기존 대표 report 경로는 human-approved OpenAI provider 실행용으로
    예약한다.

## 대안 검토

- 최고 importance 기사만 대표 후보로 유지하는 방법:
  구현은 단순하지만 topic 중심성, source diversity, 정보량을 반영하지
  못해 제외했다.
- topic centroid 기반 ranking:
  중심성 계산에는 적합하지만 기존 seed-based grouping 흐름보다 구현
  범위가 커지고 이번 MVP의 제한된 검증 목적을 넘어 제외했다.
- 대표 후보와 run history를 DB에 저장하는 방법:
  정책이 human review 전이고 schema/versioning 결정이 필요해 후속
  단계로 미뤘다.
- raw extraction 대상을 candidate score로 자동 확정하는 방법:
  candidate score는 같은 topic 내부 순위용이므로 전체 extraction
  우선순위로 사용하는 것은 부적절해 적용하지 않았다.
- 실제 OpenAI provider를 자동 재실행하는 방법:
  비용이 발생할 수 있고 human approval이 필요해 실행하지 않았다.

## 선택한 접근과 근거

- 기존 seed-based topic grouping 결과 위에 별도 deterministic scoring
  helper를 추가했다.
  - 기존 grouping 정책을 유지하면서 대표 후보 정책만 독립적으로 검토할
    수 있다.
- component와 weight를 report에 명시적으로 노출했다.
  - 사람이 후보 ranking의 근거와 약점을 직접 확인할 수 있다.
- source diversity를 순차 선택 방식으로 반영했다.
  - 단순 정적 점수보다 실제 후보 목록에서 같은 source 반복을 줄이는
    효과를 확인할 수 있다.
- 기본 report는 multi-article topic 중심으로 제한했다.
  - singleton count는 유지하면서 human review 집중도를 높인다.
- deterministic/OpenAI report 경로를 분리했다.
  - 반복 가능한 검증 산출물이 비용 기반 provider 산출물을 덮어쓰지
    않도록 보존한다.

## 트레이드오프

- component weight는 MVP 정책 후보이며 정답으로 확정된 값이 아니다.
- seed-based grouping과 deterministic hash embedding 품질에 후보 결과가
  의존한다.
- source diversity 감점은 같은 source의 두 번째 기사가 더 적합한
  경우에도 순위를 낮출 수 있다.
- singleton topic은 seed/similarity 점수가 높아질 수 있으므로 candidate
  score를 topic 간 중요도 비교에 사용할 수 없다.
- 기본 report 가독성은 개선됐지만 singleton 세부 검토에는
  `--include-singletons` report가 별도로 필요하다.
- 실제 provider 비교와 raw extraction 전체 우선순위 정책은 아직
  pending이다.

## 테스트

- Python compile: 통과.
- Focused unittest: `15 passed`.
- Full unittest discovery: `54 passed`.
- CLI help: 통과.
- deterministic report 생성:
  - threshold `0.70`: 통과
  - threshold `0.72`: 통과
  - `--include-singletons`: 통과
- `git diff --check`: 통과.
- K8s 변경 범위 확인: 변경 없음.
- Credential-pattern 검사: 실제 credential 값 발견 없음.
- `pytest`: executable이 설치되어 있지 않아 미실행/pending.

## 운영 반영

- 운영 반영하지 않았다.
- Production verification, Supabase SQL, migration, raw extraction,
  Kubernetes command, rollout, deployment를 수행하지 않았다.
- 실제 OpenAI embedding provider는 호출하지 않았다.
- Git push, merge, PR merge를 수행하지 않았다.

## README 업데이트 판단

- README는 변경하지 않았다.
- 이번 작업은 내부 분석 helper, CLI, tests, workflow 문서, 검토 report에
  한정되며 사용자-facing API나 운영 절차를 변경하지 않아 README 갱신이
  필요하지 않다고 판단했다.

## 확인 결과

- Threshold `0.70` deterministic report:
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics / detail topics: 3 / 3
  - representative candidates: 100
  - DB write performed: false
- Threshold `0.72` deterministic report:
  - analyzed articles: 100
  - topic candidates: 96
  - multi-article topics / detail topics: 2 / 2
  - representative candidates: 99
  - DB write performed: false
- Singleton 포함 report는 topic detail 96개를 출력했다.
- 기본 report에서 singleton은 count로만 확인하고 multi-article topic에
  집중할 수 있다.
- report에서 published/created 시각, recency 기준, score components,
  selection reason, selected/non-selected 상태를 확인할 수 있다.
- deterministic report는 전용 경로에 생성되어 OpenAI provider report
  경로를 덮어쓰지 않았다.

## 이번 단계의 의미

- topic grouping 결과를 실제 raw extraction 대상으로 연결하기 전에,
  대표 후보 선정 기준을 설명 가능한 deterministic 정책으로 만들었다.
- importance만 높은 기사 대신 topic 중심성, source diversity, 정보량,
  최신성을 함께 검토할 수 있게 했다.
- DB 저장과 실제 extraction을 분리해 정책 품질을 먼저 human review할 수
  있는 안전한 중간 단계를 마련했다.

## 포트폴리오용 요약

- NewsLab의 embedding 기반 topic grouping 결과 위에 설명 가능한 대표
  기사 후보 ranking MVP를 구현했다.
- 7개 signal을 component별로 계산하고 source diversity를 고려해 topic별
  최대 3개 후보를 선정했다.
- read-only CLI와 human-review markdown report를 제공하고, singleton
  필터링, recency 근거 표시, deterministic/provider 산출물 분리로 검토
  가능성과 재현성을 높였다.
- 실제 데이터 100건 기준 deterministic 분석과 54개 unittest를 통과했고,
  DB write나 production-impacting 작업 없이 정책을 검증했다.

## 다음 단계 후보

- 사람이 후보 적합성, source diversity weight, topic별 후보 수를 검토한다.
- human approval 후 실제 OpenAI provider 기반 report와 deterministic
  결과를 비교한다.
- topic 간 raw extraction 전체 우선순위 정책을 별도로 정의한다.
- 대표 후보 저장 여부, selection run history, score versioning을
  설계한다.
- 승인된 대표 후보를 raw extraction 대상으로 연결할지 후속 차수에서
  결정한다.
