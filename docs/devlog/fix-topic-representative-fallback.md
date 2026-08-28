# Devlog: 지표가 가리킨 곳을 파고 들어가니 계약이 있었다

Branch: `fix/topic-representative-fallback`

## 시작점 — 대시보드가 만든 질문

80차에서 Go exporter와 Grafana Dashboard를 붙였다. 켜자마자 나온 숫자가 이거다.

```text
three_day 부분 실패 비율   38.3%
원문 추출 실패 항목        58건
```

Kubernetes Job의 exit code는 0이다. 6월부터 두 달 반 동안 **성공으로 집계되던 실패**다.
exporter를 만든 목적이 정확히 이것이었으므로, 여기서 다른 일로 넘어가면
계측기만 만들고 쓰지 않은 셈이 된다.

## 38.3%를 잘못 읽고 있었다

먼저 한 일은 숫자를 분해한 것이다. Topic 단위로 내려보면 실패율이 다르다.

```text
Topic 단위 실패율   30 / 335 = 9.0%
run 부분 실패       26 / 67  = 38.8%
```

모든 run이 정확히 Topic 5개를 고르고(`--max-topics 5`), 하나만 실패해도 run 전체가
`partial_success`가 된다. 독립 시행을 가정하면:

```text
1 - (1 - 0.090)^5 = 37.4%
```

실측 38.8%와 거의 같다. 분포까지 맞춰봤다.

| 실패 Topic 수 | 이항분포 예측 | 실측 |
| --- | --- | --- |
| 0 | 41.9 | 41 |
| 1 | 20.6 | 22 |
| 2 | 4.1 | 4 |
| 3+ | 0.4 | 0 |

**실패가 무작위 독립이라는 뜻이다.** "특정 날짜 배치가 깨졌다" 같은 가설이 여기서
전부 죽는다. 그리고 고칠 대상이 바뀐다. run 실패율 38%가 아니라 **Topic 실패율 9%**다.
증폭은 양방향이므로 9%를 2%로 낮추면 38%는 10%가 된다.

8월 실패율이 11.1%로 7월 6.9%보다 높았지만 z = 1.27(p ≈ 0.20)로 유의하지 않다.
표본이 작아서 흔들린 것이라 추적하지 않았다. **눈에 띈다고 다 원인은 아니다.**

## 원인은 한 언론사였다

| source | total | failed | failed_pct |
| --- | --- | --- | --- |
| Hacker News | 12 | 5 | 41.7 |
| Al Jazeera | 160 | 49 | 30.6 |
| The Guardian World | 241 | 6 | 2.5 |
| BBC World | 188 | 0 | 0.0 |
| DW English | 186 | 0 | 0.0 |

BBC 188건과 DW 186건에서 실패가 0이다. **추출기는 멀쩡하다.**

Al Jazeera 실패 49건 중 45건이 `/video/` URL이었다. 실제로 페이지를 받아보니
영상 플레이어와 두 문장 캡션(약 300자)뿐이고 기사 본문이 없다.
`len(raw_text) < 300` 판정은 **정확했다.**

여기서 방향이 한 번 꺾였다. parser를 고치려던 계획을 접었다. 뽑을 본문이 없는
페이지에서 본문을 뽑을 방법은 없다. 문제는 **본문 없는 영상 포스트가 기사로 수집되고
대표 기사로 선정될 수 있다**는 쪽이었다.

## 진짜 결함 — 대표 하나 때문에 Topic 전체를 버린다

```python
representative_ids = [a["id"] for a in topic["articles"]
                      if a.get("representative_candidate_rank") == 1]
...
if representative_id not in used_ids:
    raise ValueError("representative article raw text is required")
```

rank 1만 본다. `three_day`는 Topic마다 기사 3건의 원문을 확보하는데
(`--max-summary-articles-per-topic 3`), rank 1이 영상 포스트여서 죽어도
rank 2, 3의 원문은 멀쩡히 있다. 그걸 쓰지 않고 Topic을 버리고 있었다.

`weekly`가 같은 설정 5건이라는 점도 여기서 설명된다. 여유분이 많으니 덜 죽는다
(Topic 실패율 6.2% vs 8.7%).

## 그리고 여기서 틀렸다

수정 방향을 이렇게 잡았다.

> `is_representative`(clustering 대표)와 `representative_article_id`(Summary 대표)는
> 다른 개념이다. 전자는 유사도 기준이라 원문과 무관하고, 후자는 요약의 근거이므로
> 원문이 있어야 한다. 그러니 후자만 고치고 전자는 건드리지 않는다.

논리 자체는 그럴듯했다. **그런데 기존 계약을 읽지 않고 내린 판단이었다.**

```python
# models.py
if self.is_representative and not self.is_summary_evidence:
    raise ValueError("representative article must be summary evidence")
```

```sql
-- 008_create_weekly_topic_tables.sql
check (not is_representative or is_summary_evidence)
```

**schema가 이미 둘을 묶어두고 있었다.** 대표는 반드시 근거여야 한다고.

결과는 이랬다. Topic이 `_validate_summary_input`을 통과하고, **OpenAI를 호출하고**,
저장 record를 만들다가 죽는다.

```text
summary representative : 2
record FAILED : ValueError representative article must be summary evidence
```

저장되는 Topic이 하나도 늘지 않는다. 폐기될 Topic마다 LLM 호출이 한 번씩 늘고,
오류 문자열만 원인을 덜 가리키는 것으로 바뀐다. **개선이 아니라 순수한 악화였다.**

## 그런데 test는 498개가 전부 초록이었다

이게 더 무서운 부분이다.

새로 쓴 test 9개는 전부 `build_*_summary_input`에서 멈췄다.
`summary_input["representative_article_id"]`가 2로 바뀌는 것은 확인했다.
**Topic이 저장되는지는 확인하지 않았다.**

주장한 동작 변화는 "폐기되던 Topic이 저장된다"인데, 저장을 보지 않는 test만 있었다.
핵심 line을 되돌리면 8건이 실패하니 tautological하지도 않았다.
**계층을 잘못 골랐을 뿐이다. 그리고 그 실수는 초록불로는 절대 드러나지 않는다.**

## 어떻게 잡았나 — review를 구현에서 떼어냈다

구현자 본인이 자기 코드를 다시 보는 것으로는 안 잡혔을 문제다.
같은 가정 위에서 코드를 쓰고 같은 가정 위에서 test를 짜기 때문이다.
"is_representative는 clustering 개념이니 건드리지 않는다"는 전제를 갖고 다시 읽으면,
그 전제를 깨는 코드(`models.py`의 `__post_init__`)를 봐도 그냥 지나친다.

그래서 별도 subagent에게 이렇게 시켰다.

```text
- 목표는 버그를 찾는 것이다. 승인하는 것이 아니다.
- 구현 의도를 설명하지 않는다. diff와 코드만 읽게 한다.
- 각 지적에 file:line, 재현되는 입력, 심각도를 붙이게 한다.
- 실제로 읽거나 실행해서 확인한 것만 보고하게 한다.
- "핵심 line을 되돌리면 어떤 test가 실패하는가"를 직접 해보게 한다.
```

**마지막 항목이 BLOCKER-02를 잡았다.** 되돌렸더니 8건이 실패해서 "test가 무의미하지는
않다"까지는 나왔는데, 거기서 멈추지 않고 "그런데 저장을 확인하는 test가 하나도 없다"로
넘어갔다. 나는 8건 실패를 보고 안심했을 것이다.

subagent는 blocker 2건, should-fix 2건, nit 3건을 냈다. 그중 5건을 이 branch에서
고쳤고, 2건은 판단해서 남겨뒀다(`docs/reviews/`에 근거를 적었다).
**지적을 전부 받아들이는 것도 review를 제대로 쓰는 게 아니다.**

의도를 설명하지 않은 게 핵심이었다고 본다. 설명했으면 "그 판단은 합리적이네요"로
시작했을 테고, 그러면 계약을 확인하러 가지 않았을 것이다.

## 수정

`_build_topic_record`가 Summary 대표에서 `is_representative`를 파생하게 했다.

```python
representative_article_id = summary_input["representative_article_id"]
...
is_representative=int(article["id"]) == representative_article_id,
```

`rank`는 clustering 순서 그대로 둔다. 바뀌는 것은 대표 표시뿐이다.

그리고 저장까지 태우는 test를 3건 추가했다. 검증은 되돌려서 했다.

```text
FAILED ...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다   (3일)
FAILED ...::test_대표_기사_원문이_없어도_Topic이_실제로_저장된다   (주간)
2 failed, 499 passed
```

## 기존 test 하나가 깨졌고, 그게 맞았다

`test_all_topic_failures_preserve_existing_window_results`가 실패했다.
"성공 Topic이 없으면 window를 교체하지 않는다"를 확인하는 test인데, **전체 실패를
만드는 방법으로 "지원 기사에만 원문이 있는" 상태를 썼다.** 그게 바로 이번에 고친 상황이다.

의도는 그대로 두고 fixture만 원문이 전무한 상태로 바꿨다.
**깨진 test를 지우지 않고 왜 깨졌는지 먼저 물어야 하는 이유가 이거다.**
이 test는 "고쳤다"는 사실을 반대편에서 확인해 준 셈이다.

## 실패 사유를 남기지 않고 있었다

원인 하나 찾는 데 Production SQL을 여섯 번 돌렸다. 이유가 있었다.

```python
return ThreeDayTopicRunCompletion(
    status=analysis["run_status"],
    ...
    failed_topic_count=analysis["failed_topic_count"],
)   # error_message를 넘기지 않는다
```

`partial_success` 26건의 `error_message`가 전부 NULL이었다. Topic별 사유는
`LOGGER.warning`으로만 남고 Pod가 정리되면 사라진다. **왜 실패했는지가
어디에도 남지 않는 구조였다.**

유형별 건수만 집계해 남기도록 했다.

```text
ValueError: representative article raw text is required x2; ValueError: insufficient raw text x1
```

개별 사유를 다 적지 않는다. `error_message`는 1000자 상한이고, 필요한 정보는
"어느 Topic이 죽었나"가 아니라 "어떤 유형이 지배적인가"다.

성공한 run은 `None`을 유지한다. 빈 문자열로 채우면 **"사유가 없다"와 "사유를 기록하지
않았다"를 구분할 수 없다.** 이번 조사에서 NULL 26건이 후자였고, 그 구분이 추적의
출발점이었다. 같은 함정을 다시 파지 않는다.

`analysis["topic_failure_reasons"]`는 `.get()` 없이 직접 읽는다. 기존 test 2건이
`KeyError`로 깨졌지만 test를 고쳤다. `.get()`으로 무르게 두면 `_build_analysis`가
키를 빠뜨려도 조용히 통과하고, **사유가 다시 조용히 사라지는 경로가 생긴다.**

## 남은 것

배포 전이라 효과는 아직 숫자로 없다. 예상은 Topic 실패율 1~2%, run 부분 실패 5~10%다.
**예상과 다르면 예상이 틀린 것이므로 다시 조사한다.** task 문서에 그렇게 적어뒀다.

UNIT-03(대표 후보 선정에서 추출 실패 기사 제외)은 보류했다. UNIT-01로 충분한지는
운영 숫자를 봐야 알 수 있고, 미리 만들면 필요 없는 코드가 남는다.

## 이번에 배운 것

**기존 계약을 읽기 전에 설계 판단을 내리지 않는다.** "두 개념은 분리되어야 한다"는
판단은 합리적으로 들렸지만, model `__post_init__`과 DB CHECK가 이미 둘을 묶어두고
있다는 사실 위에서는 틀린 판단이었다. 코드가 왜 그렇게 생겼는지 먼저 읽었어야 했다.

**test 계층은 "무엇이 바뀐다고 주장하는가"에서 나와야 한다.** 주장이 "Topic이
저장된다"면 저장을 봐야 한다. 중간 값이 바뀌는 것만 보면 초록불이 거짓말을 한다.

**구현자와 리뷰어를 분리해야 한다.** 같은 사람이 같은 가정 위에서 test를 짜면
사각이 그대로 남는다. `498 passed`는 아무것도 보장하지 않았다.

79차에서 *"가짜 헬스체크는 관측이 없는 것보다 나쁘다"*고 적었다. 이번 건은 그
test 버전이다. **효과 없는 수정 위의 초록불은 수정이 없는 것보다 나쁘다.**
고쳤다고 믿고 다음으로 넘어가게 만들기 때문이다.
