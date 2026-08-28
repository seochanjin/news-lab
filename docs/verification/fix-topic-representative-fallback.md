# Verification: 대표 기사 원문 부재로 인한 Topic 폐기 수정

Branch: `fix/topic-representative-fallback`

---

## 조사 (Production DB, 사람이 실행)

### ① 실패 사유가 DB에 남지 않는다

Command (Supabase SQL Editor):

```sql
select status, count(*) as runs, count(error_message) as with_error_message,
       sum(failed_topic_count) as failed_topics
from three_day_topic_runs group by status order by runs desc;
```

Result:

```text
success          41 runs   with_error_message 0   failed_topics 0
partial_success  26 runs   with_error_message 0   failed_topics 30
```

Status: passed — `partial_success` 26건 전부 `error_message`가 NULL이다.
`_completion_from_analysis`가 값을 전달하지 않기 때문이다. UNIT-02 대상.

### ② 38.3%는 Topic 단위 실패율의 증폭값이다

Result (월별):

| month | success | partial | selected | saved | failed_topics |
| --- | --- | --- | --- | --- | --- |
| 2026-06 | 5 | 3 | 40 | 36 | 4 |
| 2026-07 | 22 | 10 | 160 | 149 | 11 |
| 2026-08 | 14 | 13 | 135 | 120 | 15 |

```text
Topic 단위 실패율   30 / 335 = 9.0%
예측 run partial    1 - (1 - 0.090)^5 = 37.4%
실측 run partial    26 / 67 = 38.8%
```

이항분포(n=5, p=0.090) 예측 대비 실측:

| 실패 Topic 수 | 예측 | 실측 |
| --- | --- | --- |
| 0 | 41.9 | 41 |
| 1 | 20.6 | 22 |
| 2 | 4.1 | 4 |
| 3+ | 0.4 | 0 |

Status: passed — 실패가 무작위 독립임이 확인됐다. 특정 배치·시기 가설은 기각.

8월 Topic 실패율 11.1%와 7월 6.9%의 차이는 z = 1.27(p ≈ 0.20)로 유의하지 않다.
별도 원인으로 추적하지 않는다.

### ③ 추출 실패는 한 source에 집중되어 있다

Result:

| source | total | failed | failed_pct |
| --- | --- | --- | --- |
| Hacker News | 12 | 5 | 41.7 |
| Al Jazeera | 160 | 49 | 30.6 |
| The Guardian World | 241 | 6 | 2.5 |
| DW English | 186 | 0 | 0.0 |
| BBC World | 188 | 0 | 0.0 |
| TechCrunch / Wired / Ars Technica | 111 | 0 | 0.0 |

전체 실패 60건 중 59건이 `extracted text is too short`, 1건이 WSJ 401이다.

Al Jazeera 실패 49건의 URL 유형:

```text
video    45
article   4
```

Status: passed

### ④ 추출기는 정상 동작했다

실패 URL `https://www.aljazeera.com/video/newsfeed/2026/8/18/tropical-storm-lala-...`를
직접 조회한 결과 영상 플레이어와 2문장 캡션(약 280\~320자)만 존재하고 기사 본문이 없다.

`extract_raw_articles.py`의 `len(raw_text) < 300` 판정은 올바른 동작이었다.

Status: passed — parser 수정은 불필요하다. **문제는 본문이 없는 영상 포스트가
기사로 수집되고 대표 기사로 선정될 수 있다는 데 있다.**

---

## UNIT-01. 대표 기사 폴백

### 구현 범위

- `app/services/topic_pipeline/selection.py`
  — `pick_summary_representative_article_id()` 신규
- `app/services/topic_pipeline/__init__.py` — export 추가
- `app/services/three_day_topic_pipeline/summary_persistence_stage.py`
  — `build_three_day_summary_input`이 새 함수를 사용
- `app/services/weekly_topic_pipeline/summary_persistence_stage.py`
  — `build_weekly_summary_input`이 새 함수를 사용
- `tests/test_topic_summary_representative_selection.py` 신규 (9 케이스)

### 설계 판단

개념 두 개가 한 값에 섞여 있었다.

| 개념 | 기준 | 원문 필요 |
| --- | --- | --- |
| `is_representative` (topic_articles 저장) | clustering 대표, 기사 유사도 | 무관 |
| `representative_article_id` (Summary 입력) | 요약 근거의 대표 | 필요 |

후자가 전자의 rank 1을 원문 확인 없이 사용했다. **`is_representative`는 변경하지
않았다.** clustering 대표는 유사도 기준으로 그대로 두고, Summary 대표만 분리했다.

`used_articles`의 구성과 정렬은 변경하지 않았다. 따라서 LLM에 전달되는 근거와
`summary_input_hash` 계약은 영향받지 않는다.

`weekly`에는 이미 근거 기사 폴백(`_summary_evidence_articles_with_fallback`)이
있었으나 대표 기사에는 적용되지 않은 상태였다. 이번에 양쪽이 일치하게 됐다.

### 고정한 동작

```text
rank 1의 원문이 있다           → rank 1을 그대로 사용 (기존 동작 유지)
rank 1의 원문이 없다           → 원문이 있는 다음 rank로 승격
rank 있는 기사에 원문이 없다    → 원문이 있는 첫 used_article 사용
원문이 하나도 없다             → None. 호출부가 insufficient raw text로 실패
```

기존 `representative article raw text is required` 분기는 도달 불가가 되지만
방어로 남겨뒀다.

### 단위 test

Command:

```bash
python -m pytest -q tests/test_topic_summary_representative_selection.py
```

Result:

```text
9 passed in 0.17s
```

Status: passed

### 전체 test

Command:

```bash
python -m pytest -q
```

Result:

```text
488 passed, 122 subtests passed in 4.01s
```

Status: passed (기존 479 + 신규 9)

### 환경 제약

최초 실행에서 3건이 실패했다.

```text
FAILED tests/test_three_day_topics_api.py::...::test_routes_are_registered_...
FAILED tests/test_topics_api.py::...::test_topics_routes_are_registered
FAILED tests/test_weekly_topics_api.py::...::test_routes_are_registered_...
AttributeError: '_IncludedRouter' object has no attribute 'path'
```

원인은 이번 변경이 아니라 **검증용으로 새로 만든 venv가 FastAPI 0.141.1을
설치했기 때문**이다. `requirements.txt`에 fastapi 버전 핀이 없다.
`fastapi==0.115.6`으로 맞춘 뒤 3건 모두 통과했고, 이후 모든 측정은 0.115.6 기준이다.

세 test는 `app.routes` introspection만 수행하며 이번 변경 대상 모듈을 import하지
않는다. 후속 작업 후보로 분류한다(본 task 범위 밖).

### 미수행

- 운영 반영 후 지표 재확인 — 사람 수행
- 실제 Production 데이터로 폴백이 발동하는 Topic 확인 — 운영 반영 후 가능

---

## UNIT-02. 실패 사유 영속화

### 구현 범위

- `app/services/topic_pipeline/failures.py`
  — `summarize_topic_failure_reasons()` 신규
- `app/services/topic_pipeline/__init__.py` — export 추가
- `scripts/run_three_day_topic_pipeline.py`,
  `scripts/run_weekly_topic_pipeline.py`
  — `_build_analysis`가 `topic_failure_reasons`를 산출하고
    `_completion_from_analysis`가 이를 `error_message`로 전달
- `tests/test_topic_failure_summary.py` 신규 (8 케이스)
- `tests/test_run_three_day_topic_pipeline.py`,
  `tests/test_run_weekly_topic_pipeline.py` — 케이스 갱신·추가

### 설계 판단

**개별 사유를 모두 남기지 않고 사유별 건수만 집계한다.** run 이력 table의
`error_message`는 1000자 상한이 있고, 필요한 정보는 "어떤 유형이 지배적인가"이지
"어느 Topic이 실패했는가"가 아니다. Topic 단위 추적이 필요해지면 별도 table을
만들어야 하며 이번 범위가 아니다.

**성공한 run은 `error_message`를 None으로 유지한다.** 빈 문자열로 채우면
"사유가 없다"와 "사유를 기록하지 않았다"를 구분할 수 없다. 이번 조사에서
NULL 26건이 후자였고, 그 구분이 원인 추적의 출발점이었다.

`_completion_from_analysis`는 `analysis["topic_failure_reasons"]`를
`.get()` 없이 직접 읽는다. `_build_analysis`가 키를 빠뜨리면 즉시 실패해야 한다.
`.get()`으로 무르게 두면 사유가 다시 조용히 사라진다.

### 고정한 동작

```text
실패 없음                → None
같은 사유 여러 건         → "사유 xN" 으로 묶는다
사유 여러 유형           → 건수 내림차순, "; " 로 연결
사유 문자열이 길다        → 200자로 자른다 (provider 응답 본문 방어)
전체가 1000자를 넘는다    → 건수 많은 유형부터 남기고 "(+N more)" 표시
사유 하나가 상한을 넘는다  → 잘라서라도 남긴다
줄바꿈·연속 공백         → 한 칸으로 정규화
```

### 실제 출력 확인

Command:

```bash
python -c "from app.services.topic_pipeline import summarize_topic_failure_reasons; ..."
```

Result:

```text
'ValueError: representative article raw text is required x2; ValueError: insufficient raw text x1'
length: 96
none on success: None
```

Status: passed

### 단위 test

Command:

```bash
python -m pytest -q tests/test_topic_failure_summary.py
```

Result:

```text
8 passed in 0.02s
```

Status: passed

### 기존 test 갱신

`test_completion_uses_actual_analysis_counts`가 `analysis` dict를 직접 구성하므로
새 키가 없어 `KeyError`로 실패했다. `.get()`으로 무르게 만들지 않고 **test를
갱신했다.** 이번 변경의 계약이 그 키이기 때문이다.

`test_completion_keeps_error_message_none_on_success`를 두 runner test에 추가했다.

### 전체 test

Command:

```bash
python -m pytest -q
```

Result:

```text
498 passed, 122 subtests passed in 3.53s
```

Status: passed (UNIT-01 시점 488 + 신규 8 + 갱신 2)

### 미수행

- 운영 반영 후 `partial_success` run의 `error_message`가 실제로 채워지는지 확인
  — 사람 수행

---

## 남은 작업 (사람 수행)

- 운영 반영 후 Grafana `NewsLab Business Metrics` 재확인
  - `three_day` Topic 저장 성공률 91.3%에서 상승
  - `three_day` 부분 실패 비율 38.3%에서 하락
- 예상치는 Topic 실패율 1\~2%, run 부분 실패 5\~10%.
  **예상과 다르면 예상이 틀린 것이므로 원인을 다시 조사한다.**

## 후속 작업 후보 (본 task 범위 밖)

- `requirements.txt` 의존성 버전 핀 부재 — 다음 이미지 빌드가 breaking 버전을
  가져올 수 있다
- `Makefile`의 `test`/`lint` target이 "No automated tests configured yet"으로
  남아 있다. 실제로는 488개 test가 있다
- Al Jazeera 일반 기사 4건의 추출 실패 원인
- Hacker News 추출 실패 — 외부 도메인이 매번 달라 단일 parser로 덮을 수 없다
- 대표 후보 선정 단계에서 `extraction_status = 'failed'` 기사 제외 (UNIT-03 후보)
- DB schema 정규화
