# Review: 대표 기사 원문 부재로 인한 Topic 폐기 수정

Branch: `fix/topic-representative-fallback`
Reviewer: Claude Code (독립 subagent 적대적 review + 사람 확인)
Scope: UNIT-01, UNIT-02 구현 전체

---

## 요약

**blocker 2건, should-fix 2건, nit 3건.** blocker 2건은 이 review에서 수정했다.

review 방식은 "구현자가 아닌 관점에서 버그를 찾는다"였다. 구현 의도를 설명받지 않은
상태에서 diff와 코드만 읽고 반례를 만들도록 했다. 결과적으로 **UNIT-01은 review 전까지
의도한 효과가 전혀 없는 상태였다.**

---

## BLOCKER-01. UNIT-01이 목표한 버그를 고치지 못했다 (수정함)

### 지적

`_build_topic_record`가 `is_representative`를 여전히
`representative_candidate_rank == 1`로 계산하고 있었다. 그런데 두 값 사이에 계약이 있다.

- `app/services/three_day_topic_pipeline/models.py:300`
  — `representative article must be summary evidence`
- `app/services/weekly_topic_pipeline/models.py:395` — 동일
- `db/migrations/008_create_weekly_topic_tables.sql:79`
  — `check (not is_representative or is_summary_evidence)`

즉 **기존 계약이 이미 "대표는 반드시 Summary 근거여야 한다"고 못박고 있었다.**

DB CHECK는 `weekly_topic_articles`에만 있고 `three_day_topic_articles`에는 없다.
3일 pipeline은 Python model 계약만으로 막힌다. **두 table의 제약이 다르다는 점 자체가
별도 후속 후보다.**

### 재현

```text
topic articles: id 1(rank 1), id 2(rank 2)
article_raw_texts: {2: 'raw two'}     # rank 1의 원문이 없다

summary representative : 2            # UNIT-01은 정상 동작
record FAILED : ValueError representative article must be summary evidence
```

Topic이 `_validate_summary_input`은 통과하고 **LLM 호출까지 마친 뒤** 저장 직전에 죽었다.

### review 전 실제 효과

| 상황 | 수정 전 | UNIT-01 적용 후 (review 전) |
| --- | --- | --- |
| rank 1에 원문 있음 | 성공 | 성공 (동일) |
| **rank 1에 원문 없음, 다른 기사엔 있음** | LLM 호출 전 실패 | **LLM 호출 후 실패** |
| 원문 전무 | 실패 | 실패 (동일) |

**저장되는 Topic이 하나도 늘지 않는다.** 오히려 폐기될 Topic마다 OpenAI 호출이
한 번씩 추가되고, 오류 메시지가 원인을 가리키지 않는 문자열로 바뀐다.

### 근본 원인 — 잘못된 설계 판단

verification 문서에 이렇게 적어뒀었다.

> **`is_representative`는 변경하지 않았다.** clustering 대표는 유사도 기준으로
> 그대로 두고, Summary 대표만 분리했다.

**이 판단이 틀렸다.** 두 개념을 분리해도 된다고 판단했지만 model 계약과 DB CHECK가
이미 둘을 묶어두고 있었다. **기존 계약을 확인하지 않고 "분리하는 게 맞다"는 판단을
먼저 내린 것**이 원인이다.

### 조치

`_build_topic_record`가 `summary_input["representative_article_id"]`에서
`is_representative`를 파생하도록 수정했다. 양쪽 pipeline 모두 적용.

```python
representative_article_id = summary_input["representative_article_id"]
...
is_representative=int(article["id"]) == representative_article_id,
```

`rank`는 clustering 순서 그대로 유지한다. 바뀌는 것은 대표 표시뿐이다.

---

## BLOCKER-02. 새 test가 blocker를 잡을 수 없었다 (수정함)

### 지적

`tests/test_topic_summary_representative_selection.py`의 모든 케이스가
`build_*_summary_input`에서 멈춘다. `summarize_and_persist_*_topics`를 호출하는 test가
없으므로 **"Topic이 실제로 저장되는가"를 확인하는 test가 하나도 없었다.**

주장한 동작 변화가 "폐기되던 Topic이 저장된다"인데, 저장을 보지 않는 test만 있었다.
그래서 저장 Topic이 0건 늘어난 변경 위에서 `498 passed`가 나왔다.

핵심 line을 되돌렸을 때 8건이 실패하므로 test가 tautological하지는 않다.
**계층을 잘못 골랐다.**

### 조치

저장까지 태우는 end-to-end test를 양쪽 pipeline에 추가했다.

- `tests/test_three_day_topic_pipeline.py`
  — `test_대표_기사_원문이_없어도_Topic이_실제로_저장된다`
  — `test_원문이_하나도_없는_Topic은_여전히_폐기된다`
- `tests/test_weekly_topic_pipeline.py`
  — `test_대표_기사_원문이_없어도_Topic이_실제로_저장된다`

`is_representative` 수정만 되돌려 확인했다.

```text
FAILED tests/test_three_day_topic_pipeline.py::...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다
FAILED tests/test_weekly_topic_pipeline.py::...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다
2 failed, 499 passed
```

**의도한 지점을 정확히 잡는다.**

---

## SHOULD-FIX-01. rank 없는 기사 폴백은 도달 불가이며 위험했다 (수정함)

### 지적

`selection.py`의 마지막 분기가 `used_articles[0]["article_id"]`를 반환했다.

도달 불가다. `summary_topic_article_ids` → `_summary_article_ids_for_topic`이
`representative_candidate_rank is not None`으로 이미 거른다. weekly는
`_summary_evidence_articles_with_fallback`에서 한 번 더 거른다.

그리고 **도달했다면 반드시 깨진다.** `_build_topic_record`의 `related_articles`는
rank 있는 기사만 담으므로 대표가 목록에 없게 되고
`topic must have exactly one representative article`에 걸린다.

test `test_rank가_없는_기사만_원문을_가지면_그_기사를_쓴다`가 **불가능하면서 동시에
깨지는 동작**을 고정하고 있었다.

### 조치

해당 분기를 `return None`으로 바꾸고 이유를 주석으로 남겼다. test도 반환값이
None임을 확인하도록 갱신했다. docstring의 반환 계약도 실제 동작과 맞췄다.

---

## SHOULD-FIX-02. `test_completion_keeps_error_message_none_on_success`가 증명하는 게 없다 (미수정)

### 지적

`analysis` dict를 손으로 만들면서 `"topic_failure_reasons": None`을 직접 넣고
`completion.error_message is None`을 확인한다. `_completion_from_analysis`의 한 줄
대입을 다시 쓴 것에 가깝다.

`_build_analysis`가 성공 run에서 `None`을 만든다는 사실은 확인하지 않는다.
`summarize_topic_failure_reasons`가 빈 문자열을 반환해도 이 test는 통과한다.

### 판단

**수정하지 않는다.** `summarize_topic_failure_reasons([])`가 None을 반환한다는 것은
`tests/test_topic_failure_summary.py::test_실패가_없으면_None을_반환한다`가 직접
확인한다. `_build_analysis`부터 태우는 통합 test는 pipeline stage 전체 mock이
필요해 비용 대비 이득이 낮다.

**후속 작업 후보로 기록한다.** BLOCKER-02와 같은 계열의 지적이므로 가볍게 넘기지 않는다.

---

## NIT-01. `failures.py`의 주석이 사실과 다르다 (수정 보류)

`app/services/topic_pipeline/failures.py`의 마지막 주석이
"생략 표시의 자릿수가 늘어나 상한을 1~2자 넘길 수 있으므로"라고 적혀 있으나 거짓이다.
루프 안 guard가 계산하는 `remaining`이 최종값과 같으므로 자릿수는 늘지 않는다.

review에서 무작위 20만 회 실행으로 확인했다. 길이 위반 0건, 잘린 `(+N more)` 0건.
`models.py:279`의 1000자 검증은 이 함수로 유발할 수 없다.

**슬라이스 자체는 남긴다.** 방어로서 비용이 0이다. 주석 문구만 다음 수정 때 고친다.

## NIT-02. 첫 사유 초과 경로가 건수를 잃는다 (수정 보류)

`max_length`가 매우 작을 때만 도달하며(기본값 1000에서는 불가) 건수 없이 사유만 남는다.
`test_사유_하나가_상한을_넘어도_잘라서_남긴다`가 `max_length=20`으로만 도달한다.
운영 경로가 아니므로 그대로 둔다.

## NIT-03. 한글 docstring 누락 (수정함)

`CLAUDE.md`의 "새 Python module·class·function·test에는 한글 docstring을 쓴다" 규칙을
새 test file의 helper와 `setUp`에서 지키지 않았다. 전부 추가했다.

---

## 지적이 없었던 항목

review에서 명시적으로 확인하고 문제를 찾지 못한 영역이다.

| 항목 | 결과 |
| --- | --- |
| `summary_input_hash` 계약 | 변경 없음. hash 입력은 `prompt_version`과 `used_articles`뿐이며 `representative_article_id`는 원래도 포함되지 않았다 |
| `used_articles` 구성·정렬 | diff 이전과 동일 |
| API 노출 불일치 | 불가능. model 계약과 DB CHECK가 `is_representative=true, is_summary_evidence=false` 행을 막는다 |
| `processing_result.failures` 부재 경로 | 없음. `failures`는 default 없는 필수 field이며 dry-run 분기도 `failures=[]`를 넘긴다 |
| `analysis["topic_failure_reasons"]` 호출부 | 생산 2곳, 소비 2곳, test 4곳 전부 갱신됨 |
| `daily` pipeline 영향 | 없음. diff 0, 변경된 함수를 import하지 않는다 |
| import cycle·잔여 변수 | 없음 |
| rank 타입 견고성 | 문자열 rank 혼재 시 `TypeError`가 나지만 `topic_representatives.py`가 int 또는 None만 기록한다. 기존 코드에도 같은 정렬 key가 있으므로 regression 아님 |

`representative article raw text is required` 분기는 이제 도달 불가다. 방어로 남긴다.

---

## 이 review에서 배운 것

**기존 계약을 확인하기 전에 설계 판단을 내렸다.** "두 개념은 분리되어야 한다"는
판단 자체는 합리적이었지만, model `__post_init__`과 DB CHECK가 이미 둘을 묶어두고
있다는 사실을 읽지 않은 상태에서 내렸다. 그 결과 수정이 아무 효과가 없었다.

**검증 계층을 잘못 골랐다.** "대표가 바뀐다"를 확인했지 "Topic이 저장된다"를 확인하지
않았다. 주장하는 동작 변화가 무엇인지에서 test 계층이 나와야 한다.

두 실수 모두 test가 초록불이어도 드러나지 않았다. **`498 passed`는 아무것도
보장하지 않았다.**
