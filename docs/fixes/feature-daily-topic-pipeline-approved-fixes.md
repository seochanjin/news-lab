# Approved Fixes: 수동 daily topic pipeline MVP

## Approved Fixes

### Fix 1: Daily pipeline report에 selected article metadata 추가

#### Background

현재 provider dry-run report는 topic별 `article_id`와 `similarity_score`만 표시한다.  
이 정보만으로는 사람이 실제로 같은 이슈끼리 묶였는지 판단하기 어렵다.

#### Approved Change

- `scripts/run_daily_topic_pipeline.py`의 report output에 selected article metadata를 추가한다.
- 각 selected topic에 대해 다음 정보를 표시한다.
  - role
  - article_id
  - similarity_score
  - source name
  - published_at
  - title
  - url
- 가능하면 generated summary도 report에 함께 표시한다.
  - title_ko
  - summary_ko
  - key_points
  - keywords
- raw_text는 report에 노출하지 않는다.

#### Expected Report Shape

```md
### topic-0001

- Article count: 4
- Source count: 3
- Selected article IDs: `[944, 974, 947]`
- Similarity scores: `{944: 1.0, 974: 0.7781, 947: 0.7799}`

#### Selected Articles

| role           | article_id | similarity | source | published_at | title | url |
| -------------- | ---------: | ---------: | ------ | ------------ | ----- | --- |
| representative |        944 |        1.0 | ...    | ...          | ...   | ... |
| supporting     |        974 |     0.7781 | ...    | ...          | ...   | ... |
| supporting     |        947 |     0.7799 | ...    | ...          | ...   | ... |

#### Generated Summary

- title_ko: ...
- summary_ko: ...
- key_points:
  - ...
- keywords: ...
```

---

### Fix 2: selected topic 정렬 기준을 article_count/source_count 우선으로 명확화

#### Background

`--max-topics`는 요약 대상으로 선택할 topic 최대 개수다.  
현재 선택 순서가 명확하지 않으면, 사람이 기대하는 “많이 묶인 주요 topic 상위 N개”가 아니라 임의 순서의 topic이 선택될 수 있다.

#### Approved Change

- selected topic 후보 정렬 기준을 명확히 한다.
- 기본 정렬 기준은 다음 우선순위를 따른다.
  1. `article_count` 내림차순
  2. `source_count` 내림차순
  3. 평균 또는 대표 similarity score 내림차순
  4. 최신 published_at 내림차순
  5. topic_candidate_id 오름차순 또는 deterministic tie-breaker
- `--max-topics N`은 이 정렬 결과의 상위 N개 topic만 summary 대상으로 선택한다.
- 정렬 기준은 report에 기록한다.

#### Expected Behavior

예를 들어 `--max-topics 5`이면:

```text
전체 topic candidates
→ article_count/source_count 기준으로 정렬
→ 상위 5개만 gpt-5-nano 요약 대상
```

---

### Fix 3: max-topics 밖의 후보를 reference candidates로 report에 남기기

#### Background

`--max-topics` 밖의 후보 topic은 요약 대상에서는 제외되지만, 사람이 검토할 수 있도록 참고 정보로 남길 필요가 있다.  
특히 프론트 또는 운영 판단에서는 “요약된 topic 외에 어떤 후보가 있었는지”가 중요하다.

#### Approved Change

- `--max-topics`로 선택되지 않은 나머지 topic 후보 중 의미 있는 후보를 report의 `Reference Candidates` 섹션에 표시한다.
- reference candidates는 AI 요약 대상이 아니다.
- reference candidates는 DB 저장 대상이 아니다.
- reference candidates는 raw extraction 대상이 아니다.
- reference candidates에는 raw_text를 포함하지 않는다.
- 표시 정보:
  - topic_candidate_id
  - article_count
  - source_count
  - selected/reference article ids
  - article title/source/url
  - similarity scores where available
- reference candidate 표시 개수를 제한하는 CLI 옵션을 추가할 수 있다.
  - 예: `--max-reference-topics 10`
- 기본값은 10개 이하로 제한한다.

#### Expected Report Shape

```md
## Reference Candidates

These candidates were not summarized because they were outside `--max-topics`.
They are shown only for human review.

### topic-0012

- Article count: 2
- Source count: 2
- Reason: outside max-topics
- Article IDs: `[... ]`

| article_id | similarity | source | published_at | title | url |
| ---------: | ---------: | ------ | ------------ | ----- | --- |
|        ... |        ... | ...    | ...          | ...   | ... |
```

---

### Fix 4: documented dry-run threshold를 0.70 기준으로도 검증 가능하게 정리

#### Background

0.72 dry-run 결과에서는 selected topic 5개가 모두 `article_count >= 2`였고, supporting article similarity도 대체로 0.78 이상이었다.  
다만 grouping 폭을 확인하기 위해 0.70 기준의 추가 dry-run도 사람이 수행할 수 있어야 한다.

#### Approved Change

- task/verification/runbook 예시에서 `--similarity-threshold 0.70`과 `0.72`를 비교 가능한 값으로 문서화한다.
- 기본 추천값은 다음과 같이 정리한다.
  - `0.70`: 조금 더 넓게 묶는 검증용
  - `0.72`: 초기 운영 후보 기본값
  - `0.78`: 보수적 검증값, article_count=1 증가 가능
- 코드 기본값 변경이 필요하다면 task 목적에 맞춰 `0.72`를 유지하거나, CLI에서 명시 입력하도록 한다.
- 이번 fix에서 provider 호출은 실행하지 않는다. 0.70 dry-run은 human-approved manual verification으로 남긴다.

## Rejected or Deferred Suggestions

- `article_embeddings` 테이블 추가는 보류한다.
  - 이유: 현재 목표는 24시간 daily summary이며, embedding vector는 메모리 처리로 충분하다.
  - 3일/7일 trend, 유사 기사 검색, 재처리 비용 최적화가 필요할 때 재검토한다.

- `topic_candidates`, `topic_candidate_articles` 테이블 추가는 보류한다.
  - 이유: 38차는 manual daily pipeline MVP이며, 중간 결과 저장 없이 최종 `topics/topic_articles` 저장만 검증한다.

- CronJob 자동화는 보류한다.
  - 이유: 39차에서 daily topic pipeline CronJob으로 다룬다.

- frontend 변경은 보류한다.
  - 이유: 40차에서 `/topics` 기반 화면 연결로 다룬다.

- gpt-5-mini 비교, fallback, factuality gate는 보류한다.
  - 이유: 먼저 gpt-5-nano 기반 daily topic summary가 프론트에 보여줄 만한지 확인한다.

- 기존 `news-raw-extractor` 코드/manifest 삭제는 보류한다.
  - 이유: repository에는 남겨두고, 운영상 suspend 여부만 human-controlled step으로 판단한다.

## Applied Changes

- Fix 1 적용:
  - selected topic report에 role, article_id, similarity, source, published_at, title, URL을 포함하는 article metadata table을 추가했다.
  - 생성된 summary의 status, title_ko, summary_ko, key_points, keywords를 함께 표시한다.
  - 실제 read-only 기사 조회 결과에 URL이 포함되도록 `scripts/analyze_topic_groups.py`의 SELECT projection에 `a.url`을 추가했다.
  - raw_text는 public pipeline result와 markdown report에 포함하지 않는다.

- Fix 2 적용:
  - selected topic을 다음 기준으로 명시적으로 정렬한다.
    1. article_count desc
    2. source_count desc
    3. average similarity desc
    4. latest published_at desc
    5. topic_candidate_id asc
  - `--max-topics`는 정렬 완료 후 summary 대상으로 선택할 최대 topic 개수로 유지했다.
  - 정렬 정책을 report summary에 기록한다.

- Fix 3 적용:
  - `--max-reference-topics` 옵션을 추가하고 기본값/최댓값을 10으로 제한했다.
  - `--max-topics` 밖 후보를 `Reference Candidates` 섹션에 표시한다.
  - reference candidates는 raw extraction, summary provider, save plan, DB write 경로에 전달하지 않는다.
  - reference candidates는 사람이 grouping 후보를 검토하기 위한 report-only 정보로 유지한다.

- Fix 4 적용:
  - task와 RUNBOOK에 provider 기반 0.70/0.72 dry-run 비교 명령을 별도 report 경로와 함께 문서화했다.
  - 0.70은 “오늘의 주요 이슈”처럼 넓게 묶는 후보값으로, 0.72는 조금 더 보수적인 후보값으로 비교할 수 있게 했다.
  - provider dry-run은 human-approved manual verification으로 실행되었고, `--execute` DB write는 아직 실행하지 않았다.

실제 변경 파일:

```text
scripts/run_daily_topic_pipeline.py
scripts/analyze_topic_groups.py
tests/test_run_daily_topic_pipeline.py
tests/test_analyze_topic_groups.py
docs/RUNBOOK.md
docs/tasks/feature-daily-topic-pipeline.md
docs/fixes/feature-daily-topic-pipeline-approved-fixes.md
docs/verification/feature-daily-topic-pipeline.md
```

## Verification Required

Codex가 실행 가능한 로컬 검증:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest tests.test_run_daily_topic_pipeline -v
python -m unittest tests.test_save_topic_summaries -v
python -m unittest discover -s tests -v
git diff --check
```

Human-approved manual verification 완료:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-070.md
```

비교용 human-approved manual verification 완료:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.72 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-072.md
```

Human-approved manual verification pending:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --execute \
  --report-path docs/reports/feature-daily-topic-pipeline-execute-070.md
```

검증 기준:

- selected topic은 article_count/source_count 기준으로 정렬된다.
- `--max-topics 3`이면 상위 3개 topic만 summary 대상이 된다.
- max-topics 밖의 후보는 `Reference Candidates`에 표시된다.
- reference candidates는 raw extraction, summary provider, DB save 대상이 아니다.
- selected article metadata가 report에 표시된다.
- raw_text는 report/API에 노출되지 않는다.
- 0.70 dry-run은 “오늘의 주요 이슈” 형태로 넓게 묶는 후보로 확인되었다.
- 0.72 dry-run은 조금 더 보수적으로 묶는 후보로 확인되었다.
- `--execute` 저장 검증은 아직 미수행 상태다.
