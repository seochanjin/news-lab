# Approved Fixes: Raw text 기반 topic summary report MVP

## Approved Fixes

### 1. raw_text가 있는 topic을 우선 summary 대상으로 선택

#### Problem

Human-approved integration verification에서 34차 limited raw extraction을 실행해 `article_id=644`의 raw extraction이 성공했다.

34차 execute 결과:

- `article_id=644`
- `topic_candidate_id=topic-0086`
- extraction result: `success`
- `raw_extraction_performed=true`
- `db_write_performed=true`

그 후 35차 deterministic summary report를 다시 생성했지만, 결과는 다음과 같았다.

- `topic_count=3`
- `summarized_topic_count=0`
- `insufficient_raw_text_topic_count=3`

원인은 35차 summary report 생성 로직이 `max_topics`를 먼저 적용하기 때문이다.  
현재 흐름에서는 `topic-0001~topic-0003`만 summary 대상으로 선택되며, raw_text가 확보된 `topic-0086`은 `--max-topics 3` 범위 밖이라 summary input에 포함되지 않는다.

#### Approved fix

35차 summary report는 raw_text 기반 report이므로, raw_text가 있는 topic을 우선 summary 대상으로 선택해야 한다.

다음 방식으로 수정한다.

- 전체 topic candidate를 대상으로 raw_text availability를 먼저 평가한다.
- `status=ready`인 topic을 `insufficient_raw_text` topic보다 앞에 배치한다.
- 그 다음 `max_topics`를 적용한다.
- ready topic 정렬 기준은 다음 순서를 따른다.
  1. `status=ready` 우선
  2. used article count 내림차순
  3. source count 내림차순
  4. 기존 deterministic order 또는 `topic_candidate_id` 오름차순
- raw_text가 없는 topic은 계속 `insufficient_raw_text`로 report에 표시한다.
- raw_text 전문은 JSON/markdown report에 노출하지 않는다.
- DB write, raw extraction, provider call은 수행하지 않는다.
- API, DB schema, K8s, CronJob, frontend는 변경하지 않는다.

#### Required tests

다음 unit test를 추가한다.

- raw_text가 있는 topic이 `max_topics` 범위 밖에 있어도 ready topic으로 선택되는지 검증
- raw_text가 없는 topic은 `insufficient_raw_text`로 유지되는지 검증
- `max_topics` 적용 후 ready topic이 우선 포함되는지 검증
- report/summary output에 raw_text 전문이 노출되지 않는지 검증

## Rejected or Deferred Suggestions

없음.

이번 fix는 human-approved integration verification 중 발견된 실제 기능 gap에 대한 필수 수정이다.  
별도 rejected/deferred suggestion은 없다.

## Applied Changes

### Fix 1 적용 완료

- `build_topic_summary_inputs()`가 전체 topic candidate의 raw text availability를
  먼저 평가하도록 수정했다.
- `ready` topic을 `insufficient_raw_text` topic보다 앞에 배치한 뒤
  `max_topics`를 적용하도록 수정했다.
- ready topic은 used article count 내림차순, source count 내림차순, 기존
  deterministic order 순으로 정렬한다.
- limit 안에 자리가 남으면 `insufficient_raw_text` topic을 계속 포함한다.
- deterministic public summary에서 raw text excerpt와 raw-text-derived keyword를
  제거했다.
- public JSON/markdown output에는 raw text 필드와 원문 식별 문자열이 포함되지
  않도록 unit test를 추가했다.
- initial `max_topics` 범위 밖의 ready topic 우선 포함과 ready topic 정렬
  unit test를 추가했다.

변경 파일:

- `app/utils/topic_summary.py`
- `tests/test_topic_summary.py`
- `docs/fixes/feature-topic-summary-report-approved-fixes.md`
- `docs/verification/feature-topic-summary-report.md`

review 문서 또는 approved fix 밖의 제안은 적용하지 않았다.

### 2. provider response payload validation 강화

#### Problem

`parse_provider_response()`에서 `json.loads(output_text)` 결과가 dict/object라고 가정하고 `.keys()`를 호출한다.
하지만 provider 응답이 JSON array, string, null 등 object가 아닌 valid JSON일 경우 `AttributeError`가 발생할 수 있다.

또한 `confidence`를 `float()`로만 변환하면 `NaN`, `inf`, `-inf` 같은 non-finite 값이 통과할 수 있다.

#### Approved fix

- `json.loads(output_text)` 결과가 dict인지 먼저 검증한다.
- `title_ko`, `summary_ko`가 string인지 검증한다.
- `key_points`, `keywords`가 list인지 검증한다.
- `key_points`, `keywords`의 원소가 string인지 검증한다.
- `confidence`가 finite number인지 검증한다.
- `confidence`가 `0~1` 범위인지 검증한다.
- 잘못된 provider payload는 `ValueError`로 제어된 validation error를 발생시킨다.

#### Required tests

- provider response가 JSON object가 아닌 경우 `ValueError`
- `confidence`가 `NaN`/`inf`인 경우 `ValueError`
- `confidence`가 0~1 범위를 벗어나면 `ValueError`
- list field 안에 string이 아닌 값이 있으면 `ValueError`

### Fix 2 적용 완료

- `parse_provider_response()`가 JSON object가 아닌 provider payload를
  `ValueError`로 거부하도록 수정했다.
- text/list field 타입과 list 원소 타입을 검증하도록 수정했다.
- `confidence`가 finite number이고 `0~1` 범위인지 검증하도록 수정했다.
- non-object JSON, non-finite/out-of-range confidence, 잘못된 text/list field
  타입을 검증하는 unit test를 추가했다.
- provider scoring, topic grouping, DB write, raw extraction, API, K8s 동작은
  변경하지 않았다.

## Verification Required

fix 적용 후 다음 검증을 수행한다.

```bash id="ge5m6c"
git status --short --branch
git diff --stat
git diff --check
```

```bash id="a2hige"
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py
```

```bash id="tu5ovj"
.venv/bin/python -m unittest \
  tests.test_topic_summary \
  tests.test_generate_topic_summary_report \
  -v
```

```bash id="pjzlz6"
.venv/bin/python -m unittest discover -s tests -v
```

Deterministic report 재생성:

```bash id="zzdnik"
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

기대 결과:

- deterministic report 생성 성공
- `summarized_topic_count >= 1`
- `insufficient_raw_text_topic_count`는 남아 있을 수 있음
- report에 used article metadata와 `raw_text_length` 표시
- report/JSON에 raw_text 전문 미노출
- `db_write_performed=false`
- `raw_extraction_performed=false`
- provider call 없음

변경 범위 확인:

```bash id="7oeb1e"
git diff -- k8s
git diff -- app scripts db tests docs
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github .env
```

보안 검사:

```bash id="dz377e"
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash id="pz9qjl"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

금지 사항:

- raw extraction 추가 실행 금지
- raw extraction `--execute` 명령 실행 금지
- DB write 금지
- OpenAI/LLM provider 호출 금지
- migration/manual SQL 금지
- production curl/deployment/rollout 금지
- git push/merge 금지

검증 완료.

- Focused unittest: 15 tests passed.
- Full unittest: 90 tests passed.
- deterministic actual-data report 재생성 성공.
- summarized_topic_count=3.
- DB write 없음.
- raw extraction 없음.
- provider call 없음.
