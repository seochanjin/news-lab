# Approved Fixes: Topic 대표 기사 후보 선정 MVP

## Approved Fixes

### Fix 1. 대표 후보 report를 multi-article topic 중심으로 정리

현재 deterministic report는 singleton topic까지 모두 상세 출력한다.

그 결과 article 100건 기준 topic candidate 96개가 생성되고, 대부분의 singleton topic이 representative candidate로 표시된다. 이는 구현 검증에는 유효하지만, 사람이 검토해야 하는 핵심 대상인 multi-article topic 후보를 찾기 어렵게 만든다.

이번 fix에서는 report의 기본 상세 출력 대상을 multi-article topic 중심으로 제한한다.

수정 기준:

- 기본 report 상세에는 `article_count > 1`인 topic만 출력한다.
- singleton topic은 전체 summary에서 count로만 확인할 수 있게 한다.
- 필요하면 `--include-singletons` 옵션으로 singleton topic 상세도 출력할 수 있게 한다.
- JSON output에는 기존 분석 결과를 유지해도 되지만, markdown report는 사람이 검토하기 쉬운 형태를 우선한다.
- report summary에는 다음 값을 구분해서 표시한다.
  - 전체 topic candidate count
  - multi-article topic count
  - singleton topic count
  - report detail topic count
- 이 fix는 report 가독성 개선이며, topic grouping 결과 자체를 변경하지 않는다.

### Fix 2. recency score 기준 시각을 report에 명확히 표시

현재 scoring은 `published_at`이 없을 경우 `created_at`을 fallback으로 사용해 recency score를 계산한다.

하지만 report table에는 `Published At`만 표시된다. 이 때문에 `published_at`이 비어 있는데 recency component가 높게 표시되는 article이 생겨, 사람이 report를 볼 때 score 근거를 이해하기 어렵다.

이번 fix에서는 recency score에 사용된 기준 시각을 report에 명확히 표시한다.

수정 기준:

- article별 report에 `published_at`과 `created_at`을 모두 표시한다.
- 또는 `recency_time` / `time_used_for_recency` 컬럼을 추가한다.
- `published_at`이 없어서 `created_at`을 사용한 경우에도 report에서 그 사실을 확인할 수 있어야 한다.
- scoring 로직 자체는 유지해도 된다.
- 이 fix는 score 설명 가능성 개선이며, DB 조회/저장 정책을 변경하지 않는다.

### Fix 3. candidate score의 사용 범위를 문서화

현재 singleton topic은 seed article 하나만 포함하므로 `similarity_to_seed=1.0`과 `is_topic_seed=True`를 가진다.

따라서 singleton article은 similarity, topic seed, source diversity component에서 높은 점수를 받을 수 있다. 이는 같은 topic 내부에서 후보 순위를 계산할 때는 자연스럽지만, 서로 다른 topic 간 중요도 비교 점수로 사용하면 오해가 생길 수 있다.

이번 fix에서는 candidate score의 사용 범위를 report 또는 devlog에 명확히 남긴다.

수정 기준:

- candidate score는 **같은 topic 내부에서 대표 후보 순위를 비교하기 위한 점수**라고 명시한다.
- candidate score를 서로 다른 topic 간 중요도 비교 점수로 사용하지 않는다고 명시한다.
- raw extraction 대상 전체 우선순위는 후속 차수에서 별도 정책으로 검토한다고 명시한다.

### Fix 4. deterministic report와 OpenAI provider report 출력 경로 분리

현재 verification 명령에서 deterministic report 생성 경로와 실제 OpenAI provider 기반 report 저장 경로가 동일하게 사용될 수 있다.

그 결과, 사람이 별도로 실행해 생성한 OpenAI provider 기반 report가 이후 deterministic 검증 명령 실행으로 덮어써질 수 있다. 이는 기능 동작에는 영향을 주지 않지만, report 산출물의 의미가 뒤섞여 human review와 PR 문서화 과정에서 혼선을 만들 수 있다.

이번 fix에서는 deterministic 검증용 report와 OpenAI provider 기반 최종 검토 report의 저장 경로를 분리한다.

수정 기준:

- deterministic 검증 report는 별도 파일명으로 저장한다.
  - `docs/reports/feature-topic-representative-candidates-deterministic.md`
  - `docs/reports/feature-topic-representative-candidates-deterministic-threshold-072.md`
  - `docs/reports/feature-topic-representative-candidates-deterministic-with-singletons.md`
- OpenAI provider 기반 report는 사람이 명시적으로 승인해 실행한 경우에만 기존 대표 report 경로에 저장한다.
  - `docs/reports/feature-topic-representative-candidates.md`
  - `docs/reports/feature-topic-representative-candidates-threshold-072.md`
- verification 문서의 deterministic 실행 명령이 OpenAI provider report를 덮어쓰지 않도록 수정한다.
- `--use-embedding-provider`는 실제 OpenAI embedding API 호출이며 비용이 발생할 수 있음을 문서에 명확히 남긴다.
- 이 fix는 report 산출물 보존 정책 개선이며, scoring/grouping 로직을 변경하지 않는다.

## Rejected or Deferred Suggestions

### 실제 OpenAI embedding provider 재실행 자동화

이번 fix에서 실제 provider 호출을 자동화하지 않는다.

이유:

- 실제 provider 호출은 비용이 발생할 수 있다.
- task 기준상 provider 호출은 human operator의 명시적 승인 후에만 수행한다.
- Codex는 비용 발생 API 호출을 자동 실행하지 않는 것이 맞다.

따라서 실제 provider 기반 최종 report 생성은 human operator가 별도로 실행한다.

### 대표 후보를 DB에 저장

이번 fix에서 representative candidate 저장은 하지 않는다.

이유:

- 32차는 read-only 분석/report 단계다.
- 대표 후보 정책이 아직 human review 전이다.
- DB schema, `topics`, `topic_articles`, `topic_representatives` 저장 정책은 후속 차수에서 검토한다.

### raw extraction 대상 자동 확정

이번 fix에서 raw extraction 대상 article을 확정하지 않는다.

이유:

- 이번 차수는 대표 기사 후보 선정 MVP다.
- raw extraction 실행은 후속 차수에서 다룬다.
- candidate score만으로 실제 raw extraction 대상을 자동 확정하지 않는다.

### topic summary 생성

이번 fix에서 topic summary, key points, keywords 생성은 하지 않는다.

이유:

- summary 생성은 LLM 호출과 별도 품질 기준이 필요하다.
- 32차 범위를 벗어난다.
- topic summary는 대표 기사 후보 선정과 raw extraction 이후 단계에서 검토한다.

## Applied Changes

Codex는 다음 변경을 적용한다.

- `app/utils/topic_representatives.py`
  - markdown report 기본 상세 출력 대상을 multi-article topic 중심으로 조정한다.
  - singleton topic count와 report detail topic count를 summary에 표시한다.
  - recency score에 사용된 기준 시각을 article row 또는 details에 표시한다.
  - candidate score의 사용 범위 설명을 report에 추가한다.

- `scripts/analyze_topic_representatives.py`
  - 필요 시 `--include-singletons` 옵션을 추가한다.
  - 기본 report는 singleton 상세를 제외하고 multi-article topic 상세를 출력한다.
  - JSON output은 기존 분석 결과를 유지하되, report rendering 옵션을 전달할 수 있게 한다.

- `tests/test_topic_representatives.py`
  - 기본 report가 singleton topic 상세를 제외하는지 검증한다.
  - `--include-singletons` 사용 시 singleton topic 상세가 출력되는지 검증한다.
  - recency 기준 시각이 report에 표시되는지 검증한다.
  - candidate score 사용 범위 문구가 report에 포함되는지 검증한다.

- `tests/test_analyze_topic_representatives.py`
  - `--include-singletons` CLI 옵션 parsing을 검증한다.
  - 기존 provider safety gate가 유지되는지 확인한다.

- `docs/reports/feature-topic-representative-candidates.md`
  - 수정된 report 형식으로 재생성한다.

- `docs/reports/feature-topic-representative-candidates-threshold-072.md`
  - 필요 시 수정된 report 형식으로 재생성한다.

- `docs/verification/feature-topic-representative-candidates.md`
  - fix 적용 후 실제 실행한 검증 명령과 결과만 추가한다.

- `docs/verification/feature-topic-representative-candidates.md`
  - deterministic report 생성 명령의 출력 경로를 OpenAI provider report 경로와 분리한다.
  - deterministic report가 실제 provider 기반 report를 덮어쓰지 않도록 명령 예시를 수정한다.
  - `--use-embedding-provider` 실행은 실제 OpenAI embedding API 호출이며 비용이 발생할 수 있음을 명시한다.

- `docs/reports/feature-topic-representative-candidates-deterministic.md`
  - deterministic threshold `0.70` 검증용 report로 분리한다.

- `docs/reports/feature-topic-representative-candidates-deterministic-threshold-072.md`
  - deterministic threshold `0.72` 검증용 report로 분리한다.

- `docs/reports/feature-topic-representative-candidates-deterministic-with-singletons.md`
  - singleton 포함 deterministic 검증용 report로 분리한다.

## Verification Required

기본 deterministic report 생성:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.70 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates-deterministic.md \
  --dry-run
```

보수 threshold deterministic report 생성:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates-deterministic-threshold-072.md \
  --dry-run
```

singleton 포함 deterministic report 옵션 확인:

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.70 \
  --max-candidates-per-topic 3 \
  --include-singletons \
  --report-path docs/reports/feature-topic-representative-candidates-deterministic-with-singletons.md \
  --dry-run
```

실제 OpenAI provider report 생성은 필수 검증이 아니다. 실행 시 실제 OpenAI embedding API 호출이 발생하고 비용이 발생할 수 있으므로, human operator가 명시적으로 승인한 경우에만 별도로 실행한다.

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

```bash
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --use-embedding-provider \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --report-path docs/reports/feature-topic-representative-candidates-threshold-072.md \
  --dry-run
```

## Applied Result

- Fix 1 applied.
  - 기본 markdown report는 multi-article topic만 상세 출력한다.
  - summary에 전체 topic, multi-article topic, singleton topic, report detail
    topic count를 구분해 표시한다.
  - `--include-singletons` 옵션으로 singleton topic 상세를 포함할 수 있다.
  - JSON 분석 결과와 topic grouping 결과는 유지했다.
- Fix 2 applied.
  - candidate row에 `Published At`, `Created At`, `Recency Time Source`를
    표시한다.
  - candidate details에 recency 계산에 사용된 시각과 source field를
    표시한다.
- Fix 3 applied.
  - candidate score는 같은 topic 내부 후보 비교용이며 topic 간 중요도
    비교용이 아니라는 설명을 report에 추가했다.
  - 전체 raw extraction 우선순위는 후속 정책이라는 설명을 추가했다.
- Fix 4 applied.
  - deterministic threshold `0.70`, threshold `0.72`, singleton 포함
    report를 `-deterministic` 전용 경로로 생성했다.
  - verification의 deterministic report 생성 명령과 evidence 경로를
    deterministic 전용 파일명으로 변경했다.
  - 기존 대표 report 경로는 human-approved OpenAI provider 실행용으로
    예약했으며 deterministic 검증으로 덮어쓰지 않았다.
  - 실제 OpenAI provider는 호출하지 않았다.
- Deferred/rejected suggestions는 적용하지 않았다.
- DB write, raw extraction, summary, API, K8s, 실제 embedding provider
  호출은 수행하지 않았다.
