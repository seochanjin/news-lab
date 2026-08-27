# Task: 대표 기사 원문 부재로 인한 Topic 폐기 수정

## Goal

`three_day`·`weekly` Topic Pipeline에서 **대표 기사(rank 1)의 원문이 없다는 이유만으로
Topic 전체를 폐기하는 동작**을 수정한다. 다른 근거 기사의 원문이 남아 있으면 Topic을 살린다.

이번 작업의 원칙은 다음과 같다.

```
원문이 하나도 없다        → Topic 폐기 (기존 방어 유지)
대표 기사 원문만 없다      → 원문이 있는 다음 순위를 대표로 승격
```

LLM에 전달하는 `used_articles`는 **변경하지 않는다.** 원래도 원문이 있는 기사만
근거로 들어갔다. 바뀌는 것은 `representative_article_id` 라벨뿐이므로
"근거 없이 요약하지 않는다"는 기존 계약은 그대로 유지된다.

- **branch:** `fix/topic-representative-fallback`
- **시간 상한:** 1일
- **범위 밖:** `daily` pipeline(해당 검증 없음), DB 정규화, 추출기 parser 개선

## 배경 — 조사로 확인한 사실

80차에서 구성한 Grafana Dashboard가 `three_day`의 `partial_success` 비율 38.3%를
드러냈다. Kubernetes Job의 exit code는 0이므로 이전에는 관측되지 않던 값이다.

### 1. 38.3%는 Topic 단위 실패율이 증폭된 값이다

모든 run이 정확히 Topic 5개를 선정하며(`--max-topics 5`), 하나만 실패해도
run 전체가 `partial_success`가 된다.

```
Topic 단위 실패율    30 / 335 = 9.0%
예측 run partial     1 - (1 - 0.090)^5 = 37.4%
실측 run partial     26 / 67 = 38.8%
```

이항분포(n=5, p=0.090) 예측과 실측 분포가 거의 일치한다.

| 실패 Topic 수 | 예측 | 실측 |
| --- | --- | --- |
| 0 | 41.9 | 41 |
| 1 | 20.6 | 22 |
| 2 | 4.1 | 4 |
| 3+ | 0.4 | 0 |

**실패가 특정 시기나 특정 run에 몰려 있지 않고 무작위로 흩어져 있다는 뜻이다.**
따라서 "특정 배치가 깨졌다" 계열의 가설은 기각된다.

8월 Topic 실패율이 11.1%로 7월(6.9%)보다 높지만 z = 1.27로 유의하지 않다(p ≈ 0.20).
표본 크기에서 오는 흔들림이므로 별도 원인으로 추적하지 않는다.

### 2. 원문 추출 실패는 한 source에 집중되어 있다

| source | total | failed | failed_pct |
| --- | --- | --- | --- |
| Hacker News | 12 | 5 | 41.7 |
| Al Jazeera | 160 | 49 | 30.6 |
| The Guardian World | 241 | 6 | 2.5 |
| DW English | 186 | 0 | 0.0 |
| BBC World | 188 | 0 | 0.0 |
| TechCrunch / Wired / Ars Technica | 111 | 0 | 0.0 |

전체 실패 60건 중 49건이 Al Jazeera이며, 그중 **45건이 `/video/` URL**이다.

### 3. 추출기는 정상 동작했다

실패 URL을 실제로 조회한 결과 `/video/newsfeed/` 페이지는 영상 플레이어와
2문장 캡션(약 300자)만 있고 기사 본문이 없다.
`extract_raw_articles.py`의 `len(raw_text) < 300` 판정은 **올바른 판단이었다.**

즉 문제는 parser가 아니라 **본문이 없는 영상 포스트가 기사로 수집되고,
그것이 대표 기사로 선정될 수 있다**는 데 있다.

### 4. 실패 사유가 DB에 남지 않는다

`scripts/run_three_day_topic_pipeline.py`의 `_completion_from_analysis`가
`error_message`를 전달하지 않아 `partial_success` run의 사유가 항상 NULL이다.
Topic별 사유는 `LOGGER.warning`으로만 남고 Pod가 정리되면 사라진다.

```sql
-- status = partial_success, runs = 26, with_error_message = 0
```

이 원인 하나를 특정하는 데 SQL 6회가 필요했던 이유다.

## Scope

### UNIT-01. 대표 기사 폴백

대상: `app/services/three_day_topic_pipeline/summary_persistence_stage.py`,
`app/services/weekly_topic_pipeline/summary_persistence_stage.py`

- `representative_article_id` 결정 시 `representative_candidate_rank` 오름차순으로
  순회하며 **`used_articles`에 포함된 첫 기사**를 선택한다.
- `used_articles`가 비어 있으면 기존대로 `insufficient raw text`로 실패시킨다.
- `used_articles`가 비어 있지 않은데 대표를 찾지 못하는 경우는 발생할 수 없다.
  기존의 `representative article raw text is required` 분기는 방어로 남긴다.
- `used_articles`의 구성과 정렬은 변경하지 않는다.
- `summary_input_hash` 계산 대상(`used_articles`)이 바뀌지 않으므로
  기존 hash 계약은 영향받지 않는다.

### UNIT-02. 실패 사유 영속화

대상: `scripts/run_three_day_topic_pipeline.py`,
`scripts/run_weekly_topic_pipeline.py`

- `_completion_from_analysis`가 Topic 실패 사유를 요약해 `error_message`에 전달한다.
- 사유별 건수를 집계한 형태로 기록한다. 1000자 상한을 지킨다.
- `status = 'success'`이면 `error_message`는 None을 유지한다.

### UNIT-03. 대표 후보에서 추출 실패 기사 제외 (조건부)

UNIT-01·02 완료 후 재평가한다. UNIT-01로 충분하면 후속 작업 후보로 넘긴다.

## Out of scope

- `daily` pipeline — `_validate_summary_input`에 해당하는 검증이 없다
- 추출기 parser 개선 — 영상 포스트는 parser로 해결할 대상이 아니다
- Hacker News 추출 실패 — 외부 도메인이 매번 달라 단일 parser로 덮을 수 없다
- DB schema 정규화
- Al Jazeera 일반 기사 4건의 실패 원인
- Grafana Dashboard panel 재배치

## Checklist

- [x] UNIT-01 구현
- [x] UNIT-01 단위 test
- [ ] UNIT-02 구현
- [ ] UNIT-02 단위 test
- [ ] 전체 test 통과
- [ ] verification 문서 작성
- [ ] 운영 반영 후 지표 재확인 (사람 수행)

## 완료 판정

운영 반영 후 Grafana `NewsLab Business Metrics`에서 다음을 확인한다.

- `three_day` Topic 저장 성공률이 91.3%에서 상승
- `three_day` 부분 실패 비율이 38.3%에서 하락
- `partial_success` run의 `error_message`가 채워지기 시작

예상치는 Topic 실패율 1~2%, run 부분 실패 5~10%다.
**예상과 다르면 예상이 틀린 것이므로 원인을 다시 조사한다.**
