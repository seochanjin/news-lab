# 대표 기사 원문 부재로 인한 Topic 폐기 수정

## 작업 내용

- 80차 Grafana Dashboard가 드러낸 `three_day` 부분 실패 38.3%의 원인을 추적하고 수정했습니다.
- 대표 기사(rank 1)의 원문이 없다는 이유만으로 Topic 전체를 폐기하던 동작을 고쳤습니다.
  다른 근거 기사의 원문이 남아 있으면 Topic을 살립니다.
- `partial_success` run의 실패 사유가 DB에 전혀 남지 않던 문제를 함께 수정했습니다.

## 조사 결과

Kubernetes Job의 exit code가 0이라 6월부터 관측되지 않던 실패입니다.

**1. 38.3%는 Topic 단위 실패율이 증폭된 값입니다.**

모든 run이 Topic 5개를 선정하며 하나만 실패해도 run이 `partial_success`가 됩니다.

```text
Topic 단위 실패율   30 / 335 = 9.0%
예측 run partial    1 - (1 - 0.090)^5 = 37.4%
실측 run partial    26 / 67  = 38.8%
```

이항분포 예측(41.9 / 20.6 / 4.1 / 0.4)과 실측 분포(41 / 22 / 4 / 0)가 일치합니다.
실패가 무작위 독립이므로 특정 배치·시기 가설은 기각됩니다.

**2. 원문 추출 실패는 한 source에 집중되어 있습니다.**

| source | total | failed | failed_pct |
| --- | --- | --- | --- |
| Hacker News | 12 | 5 | 41.7 |
| Al Jazeera | 160 | 49 | 30.6 |
| The Guardian World | 241 | 6 | 2.5 |
| BBC World | 188 | 0 | 0.0 |
| DW English | 186 | 0 | 0.0 |

Al Jazeera 실패 49건 중 **45건이 `/video/` URL**입니다.

**3. 추출기는 정상 동작했습니다.**

실패 URL을 직접 조회한 결과 `/video/newsfeed/` 페이지는 영상 플레이어와 2문장 캡션
(약 300자)만 있고 기사 본문이 없습니다. `len(raw_text) < 300` 판정은 올바른 동작이므로
**parser는 수정하지 않았습니다.**

## 주요 변경 사항

### UNIT-01. 대표 기사 폴백

- `app/services/topic_pipeline/selection.py`
  — `pick_summary_representative_article_id()` 추가. rank 순서를 지키되
    Summary 근거에 포함된 첫 기사를 대표로 선택합니다.
- `app/services/three_day_topic_pipeline/summary_persistence_stage.py`,
  `app/services/weekly_topic_pipeline/summary_persistence_stage.py`
  — `build_*_summary_input`이 새 함수를 사용합니다.
  — `_build_topic_record`가 `is_representative`를 clustering rank가 아니라
    Summary 대표에서 파생합니다.

`used_articles`의 구성과 정렬은 변경하지 않았으므로 LLM에 전달되는 근거와
`summary_input_hash` 계약은 영향받지 않습니다.

원문이 하나도 없는 Topic은 기존대로 `insufficient raw text`로 실패합니다.
**"근거 없이 요약하지 않는다"는 계약은 그대로입니다.**

### UNIT-02. 실패 사유 영속화

- `app/services/topic_pipeline/failures.py`
  — `summarize_topic_failure_reasons()` 추가
- `scripts/run_three_day_topic_pipeline.py`,
  `scripts/run_weekly_topic_pipeline.py`
  — `_build_analysis`가 `topic_failure_reasons`를 산출하고
    `_completion_from_analysis`가 `error_message`로 전달합니다.

기존에는 `partial_success` 26건 전부 `error_message`가 NULL이었습니다.

```text
ValueError: representative article raw text is required x2; ValueError: insufficient raw text x1
```

유형별 건수만 집계합니다. 성공한 run은 `None`을 유지합니다.

## Review에서 수정한 blocker

`docs/reviews/fix-topic-representative-fallback-review.md` 참조.
독립 subagent 적대적 review에서 **blocker 2건**이 나왔고 이 branch에서 수정했습니다.

**BLOCKER-01** — 최초 구현은 `is_representative`를 clustering rank로 두었고,
그 판단이 틀렸습니다. 양쪽 `models.py`의 `__post_init__`이
`representative article must be summary evidence`로 둘을 이미 묶어두고 있었고,
`weekly_topic_articles`에는 DB CHECK `not is_representative or is_summary_evidence`도
있습니다. 그 결과 Topic이 LLM 호출 후 저장 직전에 폐기됐습니다.
**저장 Topic이 0건 늘어난 상태였습니다.**

**BLOCKER-02** — 신규 test 전부가 `build_*_summary_input`에서 멈춰 저장을 확인하지
않았습니다. 그래서 BLOCKER-01 위에서 `498 passed`가 나왔습니다.
저장까지 태우는 end-to-end test 3건을 추가했습니다.

## 추가/변경된 API

- 없음

## DB 변경 사항

- schema 변경 없음
- **저장 값 의미 변경 1건**: `three_day_topic_articles.is_representative`,
  `weekly_topic_articles.is_representative`가 clustering rank 1이 아니라
  Summary 근거 대표를 가리킵니다. 기존 제약을 만족하는 방향의 변경이며
  마이그레이션은 필요하지 않습니다.

## README 영향

- README 변경 없음. 기능 추가가 아니라 기존 pipeline 결함 수정입니다.

## 테스트

```bash
python -m pytest -q
# 501 passed, 122 subtests passed
```

되돌림 검증 — `is_representative` 수정만 되돌려 실행:

```text
FAILED tests/test_three_day_topic_pipeline.py::...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다
FAILED tests/test_weekly_topic_pipeline.py::...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다
2 failed, 499 passed
```

신규 test:

- `tests/test_topic_summary_representative_selection.py` (9 케이스)
- `tests/test_topic_failure_summary.py` (8 케이스)
- `tests/test_three_day_topic_pipeline.py` — end-to-end 2건
- `tests/test_weekly_topic_pipeline.py` — end-to-end 1건

갱신한 기존 test:

- `test_all_topic_failures_preserve_existing_window_results` (3일·주간)
  — "지원 기사에만 원문이 있는" 상태로 전체 실패를 만들고 있었습니다.
    그 상황이 이제 정상 저장되므로 원문이 전무한 fixture로 바꿨습니다. **검증 의도는 그대로입니다.**
- `test_completion_uses_actual_analysis_counts` (3일·주간)
  — `error_message` 확인 추가
- `test_completion_keeps_error_message_none_on_success` (3일·주간) 신규

## 운영 반영 후 확인 필요 (사람 수행)

배포 전이므로 효과는 아직 숫자로 확인되지 않았습니다.

```sql
select status, count(*), count(error_message) as with_error_message
from three_day_topic_runs
where created_at > now() - interval '2 days'
group by status;
```

`partial_success`인데 `with_error_message`가 0이면 UNIT-02가 반영되지 않은 것입니다.

이후 Grafana `NewsLab Business Metrics`에서 확인합니다.

- `three_day` Topic 저장 성공률이 91.3%에서 상승
- `three_day` 부분 실패 비율이 38.3%에서 하락

예상치는 Topic 실패율 1~2%, run 부분 실패 5~10%입니다.
**예상과 다르면 예상이 틀린 것이므로 원인을 다시 조사합니다.**

## 범위 밖 (후속 작업 후보)

- `requirements.txt` 의존성 버전 핀 부재 — 검증용 venv가 FastAPI 0.141을 설치해
  route 등록 test 3건이 깨졌습니다. `0.115.6`으로 맞춘 뒤 통과했습니다.
  다음 이미지 빌드가 같은 문제를 밟을 수 있습니다.
- `Makefile`의 `test`/`lint` target이 "No automated tests configured yet"으로 남아 있습니다.
- Al Jazeera 일반 기사 4건의 추출 실패 원인
- Hacker News 추출 실패 — 외부 도메인이 매번 달라 단일 parser로 덮을 수 없습니다
- 대표 후보 선정 단계에서 `extraction_status = 'failed'` 기사 제외 (UNIT-03 후보)
- `_build_analysis`부터 태우는 통합 test (review SHOULD-FIX-02)
- **`three_day_topic_articles`에 DB CHECK 부재** — `weekly_topic_articles`에는
  `check (not is_representative or is_summary_evidence)`가 있으나 3일 table에는 없습니다.
  현재는 Python model 계약이 막고 있어 문제가 없지만 두 table의 제약이 다릅니다.
