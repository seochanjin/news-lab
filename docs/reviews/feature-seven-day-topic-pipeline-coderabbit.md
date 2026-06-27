# CodeRabbit Review: 최근 7일 기사·토픽 파이프라인 확장

## Review Summary

CodeRabbit는 Weekly Topic pipeline의 전체 구조는 유지 가능하지만, Public API에
노출되는 Topic 상태와 내부 결과 모델의 무결성, Weekly DB schema 제약이
애플리케이션 계약보다 느슨한 문제를 확인했다.

주요 문제는 다음과 같다.

- `/weekly-topics/home`이 publish 가능한 Topic 상태를 필터링하지 않는다.
- 주간 window 검증이 날짜만 비교해 정오~정오와 같은 잘못된 7일 범위를 허용한다.
- 원문 확보 결과의 상태 bucket이 서로 겹칠 수 있다.
- 최종 run status와 저장·실패 Topic 수가 모순될 수 있다.
- Weekly DB가 JSON 형식, 최소 기사·source 수, rank와 역할 관계를 충분히 강제하지 않는다.
- 원문 loader 결과가 일부만 반환될 경우 기존에 전달된 원문이 사라질 수 있다.
- CronJob에 불필요한 Kubernetes service account token이 자동 mount될 수 있다.

공개된 코멘트 외에 숨겨진 conversation 3건은 현재 내용이 제공되지 않아 이
문서에는 포함하지 않았다.

---

## Problems Found

### CR-01: `/weekly-topics/home`에 draft 또는 실패 Topic이 노출될 수 있음

**심각도:** Major
**파일:** `app/routers/weekly_topics.py`

현재 최신 window를 선택할 때는 `weekly_topic_runs.status`만 다음과 같이
검사한다.

```sql
r.status in ('success', 'partial_success')
```

하지만 해당 run에 포함된 개별 `weekly_topics.status`는 검사하지 않는다.

따라서 성공 또는 부분 성공 run에 다음과 같은 Topic row가 존재하면 Public 홈
응답에 포함될 수 있다.

- `draft`
- `failed`
- 기타 publish 대상이 아닌 상태

최신 window를 선택하는 CTE와 실제 Topic 목록을 반환하는 본 쿼리 모두에서
publish 가능한 Topic 상태를 필터링해야 한다.

검토할 수정 방향:

```sql
where r.status in ('success', 'partial_success')
  and t.status = 'ready'
```

실제 publishable 상태 이름은 repository와 기존 3일 Topic 정책을 확인해
`ready` 또는 현재 프로젝트가 사용하는 상태로 통일해야 한다.

---

### CR-02: Weekly window가 서울 기준 자정인지 검증하지 않음

**심각도:** Major
**파일:** `app/services/weekly_topic_pipeline/models.py`

현재 검증은 다음만 확인한다.

- `window_start`의 서울 날짜가 `week_start`와 일치하는지
- `window_end`의 서울 날짜가 7일 뒤인지

이 방식은 다음 잘못된 범위도 통과시킨다.

```text
월요일 12:00 KST
~
다음 월요일 12:00 KST
```

날짜와 기간은 맞지만 Weekly 계약인 월요일 자정부터 다음 월요일 자정까지가
아니다.

이 경우 월요일 오전 기사가 누락되고 다음 월요일 오전 기사가 잘못 포함될 수
있다.

다음을 추가 검증해야 한다.

- `local_start`가 월요일 `00:00:00`
- `local_end`가 다음 월요일 `00:00:00`
- 필요하다면 microsecond도 0
- `window_end - window_start`가 정확한 7일 범위인지 확인

Timezone-aware datetime을 서울 시간으로 변환한 뒤 `time()`을 검사하는 방식이
적절하다.

---

### CR-03: 원문 확보 상태 bucket이 서로 중복될 수 있음

**심각도:** Major
**파일:** `app/services/weekly_topic_pipeline/models.py`

현재 각 목록 내부의 중복만 확인한다.

```text
reused_article_ids
extracted_article_ids
failed_article_ids
missing_article_ids
```

하지만 목록 사이의 중복은 허용된다.

예:

```text
article 10
→ reused_article_ids에도 존재
→ failed_article_ids에도 존재
```

또는:

```text
article 20
→ article_raw_texts에는 원문 존재
→ missing_article_ids에도 존재
```

이 경우 통계와 실제 Summary 입력이 서로 모순된다.

필요한 검증:

- 네 상태 bucket은 상호 배타적이어야 한다.
- `article_raw_texts`에 있는 article은 `failed` 또는 `missing`에 존재하면 안 된다.
- `reused` 또는 `extracted` article은 원문 map에 존재해야 한다.
- 필요하다면 처리 대상 전체 집합과 상태 bucket의 합집합 관계도 검증한다.

---

### CR-04: 최종 run status와 Topic 처리 결과가 모순될 수 있음

**심각도:** Major
**파일:** `app/services/weekly_topic_pipeline/models.py`
**동일 문제:** CodeRabbit가 표시한 다른 최종 결과 모델에도 적용

현재 다음 개별 count 일치만 검증한다.

- generated count와 Topic 목록 크기
- failed count와 failure 목록 크기
- saved count와 저장 ID 목록 크기
- saved count가 generated count 이하인지

하지만 다음 모순이 허용된다.

```text
run_status = success
failed_topic_count > 0
```

```text
run_status = failed
saved_topic_count > 0
```

```text
run_status = partial_success
saved_topic_count = 0
```

```text
run_status = partial_success
failed_topic_count = 0
```

Run status는 Public home에서 최신 publishable window를 선택하는 데 사용되므로
이 모순은 API 노출과 운영 판단에 직접 영향을 준다.

권장 계약:

```text
success
→ 실패 Topic 없음
→ 선택 Topic이 있다면 모두 성공적으로 저장

partial_success
→ 저장 Topic 1개 이상
→ 실패 Topic 1개 이상

failed
→ 저장 Topic 없음
→ 실행 또는 모든 Topic 처리 실패
```

정상 빈 결과의 status가 `success`인지 별도 상태인지 현재 계약에 맞춰 함께
검증해야 한다.

---

### CR-05: JSONB 컬럼이 배열인지 DB에서 보장하지 않음

**심각도:** Major
**파일:** `db/migrations/008_create_weekly_topic_tables.sql`

다음 컬럼은 애플리케이션과 API에서 list로 사용된다.

```sql
key_points jsonb
keywords jsonb
```

그러나 DB는 object, string, number도 허용한다.

예:

```json
{ "keyword": "AI" }
```

```json
"AI"
```

이런 값이 저장되면 API serialization 또는 소비자 계약이 깨질 수 있다.

권장 제약:

```sql
check (jsonb_typeof(key_points) = 'array')
check (jsonb_typeof(keywords) = 'array')
```

기존 default인 빈 배열과도 일치한다.

---

### CR-06: Weekly 최소 기사·source 계약이 DB에서 강제되지 않음

**심각도:** Major
**파일:** `db/migrations/008_create_weekly_topic_tables.sql`

애플리케이션 모델은 다음을 요구한다.

```text
article_count >= 5
source_count >= 2
source_count <= article_count
```

하지만 DB는 현재 0 이상만 검사한다.

```sql
article_count >= 0
source_count >= 0
```

repository 외의 경로나 향후 운영 SQL을 통해 다음과 같은 잘못된 Topic이
저장될 수 있다.

```text
article_count = 2
source_count = 5
```

권장 제약:

```sql
check (article_count >= 5)
check (source_count >= 2)
check (source_count <= article_count)
```

단, `draft` Topic을 불완전한 상태로 먼저 저장하는 흐름이 있다면 status별
제약이나 persistence 순서를 함께 검토해야 한다. 현재 repository가 완성된 Topic만
저장한다면 직접 제약해도 된다.

---

### CR-07: 기사 rank와 대표 기사 역할 계약이 DB에서 강제되지 않음

**심각도:** Major
**파일:** `db/migrations/008_create_weekly_topic_tables.sql`

현재 DB는 Topic 내 동일 article 중복만 방지한다.

```sql
unique (weekly_topic_id, article_id)
```

하지만 다음은 허용된다.

- 한 Topic에서 여러 article이 같은 rank 사용
- `is_representative = true`인데 `is_summary_evidence = false`
- 서비스 모델이 요구하는 역할 관계와 다른 row 저장

동일 rank가 존재하면 상세 API의 기사 순서가 불안정해질 수 있다.

권장 제약:

```sql
unique (weekly_topic_id, rank)
```

```sql
check (
    not is_representative
    or is_summary_evidence
)
```

대표 기사 정확히 1개, Summary 근거 최대 5개와 같은 집합 단위 제약은 단순
CHECK로 강제하기 어렵다. 이 부분은 repository validation과 테스트에서 계속
보호해야 한다.

---

### CR-08: loader가 반환한 원문으로 기존 원문 map을 덮어씀

**심각도:** Minor
**파일:** `app/services/weekly_topic_pipeline/raw_acquisition_stage.py`

현재 `raw_texts` 인자로 이미 전달된 원문이 있어도 `raw_text_loader`가 존재하면
loader 결과로 전체 map을 교체한다.

```python
article_raw_texts = _selected_raw_texts(raw_texts, related_ids)

if raw_text_loader is not None:
    article_raw_texts = _selected_raw_texts(
        raw_text_loader(related_ids),
        related_ids,
    )
```

loader가 stale하거나 일부 기사만 반환하면 기존에 사용 가능했던 원문이
사라진다.

예:

```text
preloaded raw_texts: article 1, 2
loader result: article 2만 반환
결과: article 1 원문 유실
```

기존 map과 loader 결과를 merge하고, 어느 쪽을 우선할지 명시해야 한다.

권장 방향:

```python
loaded = _selected_raw_texts(raw_text_loader(related_ids), related_ids)
article_raw_texts = {
    **article_raw_texts,
    **loaded,
}
```

loader가 최신 source라면 위처럼 loader를 우선하고, 기존 인자 우선이 의도라면
병합 순서를 반대로 한다.

CodeRabbit가 표시한 다른 유사 구간에도 동일하게 적용해야 한다.

---

### CR-09: Task 문서 오타

**심각도:** Minor
**파일:** `docs/tasks/feature-seven-day-topic-pipeline.md`

다음 오타를 수정한다.

```text
시용 날짜 범위
```

```text
표시용 날짜 범위
```

현재 사용자가 붙여준 최신 문서에는 이미 `표시용`으로 보이므로, PR branch에
실제로 오타가 남아 있는지 확인한 뒤 수정한다.

---

### CR-10: CronJob의 service account token 자동 mount

**심각도:** Minor
**파일:** `k8s/news-weekly-topic-pipeline-cronjob.yaml`

Weekly CronJob은 Kubernetes API를 호출하지 않고 다음 외부 자원만 사용한다.

- DATABASE_URL
- Summary API key
- 일반 네트워크

그런데 기본 설정에서는 Pod에 service account token이 자동 mount될 수 있다.

불필요한 Kubernetes API credential 노출을 줄이기 위해 Pod spec에 다음을
추가하는 것이 권장된다.

```yaml
automountServiceAccountToken: false
```

추가 위치는 Job Pod template의 `spec` 아래다.

```yaml
spec:
  automountServiceAccountToken: false
  restartPolicy: Never
```

CodeRabbit는 `runAsNonRoot`, `readOnlyRootFilesystem`도 언급했지만, 이는 현재
Docker image 호환성 확인이 필요한 별도 image-hardening 작업으로 보고 이번
Quick fix에서는 service account token 비활성화만 적용하는 것이 적절하다.

---

## Required Fixes Before PR

다음 항목은 PR merge 전에 수정하는 것이 적절하다.

### FIX-01: Public 홈 API Topic 상태 필터

- 최신 window CTE에서 publishable Topic status를 적용한다.
- 실제 반환 Topic query에도 동일한 status 필터를 적용한다.
- 성공 run에 draft 또는 failed Topic이 섞여 있어도 홈 응답에서 제외되는
  테스트를 추가한다.

### FIX-02: Weekly window 서울 자정 경계 검증

- `window_start`가 서울 기준 월요일 00:00인지 검증한다.
- `window_end`가 서울 기준 다음 월요일 00:00인지 검증한다.
- 월요일 12:00부터 다음 월요일 12:00까지의 window가 거부되는 테스트를 추가한다.
- UTC 변환 후에도 정상 KST 자정 window가 통과하는 테스트를 유지한다.

### FIX-03: Raw acquisition 상태 상호 배타성 검증

- reused, extracted, failed, missing 목록 사이 교집합을 거부한다.
- 원문 map과 failed/missing 상태의 모순을 거부한다.
- 정상 상태와 각 모순 상태의 단위 테스트를 추가한다.

### FIX-04: Run status와 처리 count 정합성 검증

- `success`, `partial_success`, `failed`와 saved/failed count 관계를 강제한다.
- 정상 빈 결과 정책을 명시적으로 처리한다.
- 동일 계약이 필요한 다른 최종 결과 모델에도 적용한다.
- 모순 상태별 회귀 테스트를 추가한다.

### FIX-05: Weekly JSONB 배열 제약

Migration에 다음 제약을 추가한다.

```sql
check (jsonb_typeof(key_points) = 'array')
check (jsonb_typeof(keywords) = 'array')
```

Migration 정적 테스트를 갱신한다.

### FIX-06: Weekly Topic 기사·source 수 DB 제약

Migration에 애플리케이션 계약과 일치하는 제약을 추가한다.

```sql
check (article_count >= 5)
check (source_count >= 2)
check (source_count <= article_count)
```

Repository 및 migration 테스트를 갱신한다.

### FIX-07: Topic 기사 rank와 역할 DB 제약

Migration에 다음 제약을 추가한다.

```sql
unique (weekly_topic_id, rank)
```

```sql
check (
    not is_representative
    or is_summary_evidence
)
```

중복 rank와 모순된 역할이 거부되는 migration 정적 테스트 또는 DB 계약
테스트를 추가한다.

---

## Optional Improvements

### OPT-01: 기존 원문과 loader 결과 병합

`raw_acquisition_stage.py`에서 기존 `raw_texts`와 loader 반환값을 병합한다.

기능상 실제 원문이 유실될 수 있으므로 가능하면 이번 PR에 포함하는 것이 좋지만,
CodeRabbit 분류는 Minor다.

병합 우선순위를 코드와 docstring에 명시하고 다음을 테스트한다.

- 기존 원문만 존재
- loader 원문만 존재
- 두 곳 모두 존재
- loader가 일부 기사만 반환
- loader가 빈 결과 반환

### OPT-02: Task 문서 오타 수정

`시용`이 실제 branch에 남아 있다면 `표시용`으로 수정한다.

### OPT-03: CronJob service account token 비활성화

다음을 추가한다.

```yaml
automountServiceAccountToken: false
```

Manifest 테스트에서도 해당 값이 `false`인지 검증한다.

### OPT-04: DB와 서비스 상태 계약 추가 정리

CodeRabbit가 직접 요구한 범위를 넘어 다음도 후속 검토할 수 있다.

- `weekly_topics.status` 허용값 CHECK
- `similarity` 범위 CHECK
- Weekly 날짜와 정확한 7일 범위 DB CHECK
- 대표 기사 정확히 1개 보장 방식
- Summary evidence 최대 5개 보장 방식

집합 단위 제약은 DB CHECK로 단순히 구현하기 어려우므로 repository validation과
테스트를 유지하는 편이 현실적이다.

---

## Suggested Test Commands

CodeRabbit Fix 관련 집중 테스트:

```bash
python -m pytest \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  tests/test_weekly_topics_api.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

Weekly 실행 진입점 포함 테스트:

```bash
python -m pytest \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  tests/test_weekly_topics_api.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py \
  -v
```

기존 3일 Topic 회귀:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

전체 회귀:

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

정적 검사:

```bash
python -m compileall app scripts tests
git diff --check
```

Migration 변경 확인:

```bash
rg -n \
  "jsonb_typeof|article_count|source_count|weekly_topic_id, rank|is_representative" \
  db/migrations/008_create_weekly_topic_tables.sql \
  tests/test_weekly_topic_repository.py
```

Public home 상태 필터 확인:

```bash
rg -n \
  "weekly_topics|status|latest_window" \
  app/routers/weekly_topics.py \
  tests/test_weekly_topics_api.py
```

CronJob token mount 확인:

```bash
rg -n \
  "automountServiceAccountToken" \
  k8s/news-weekly-topic-pipeline-cronjob.yaml \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

---

## Risk Notes

### Public 노출 위험

CR-01을 수정하지 않으면 성공 run에 속한 draft 또는 failed Topic이
`/weekly-topics/home`을 통해 공개될 수 있다.

이는 가장 직접적인 사용자 노출 문제다.

### 날짜 범위 오류 위험

CR-02를 수정하지 않으면 월요일~일요일이라는 날짜 표시는 맞지만 실제 조회
시간대가 정오~정오처럼 틀어진 주간이 저장될 수 있다.

이 경우 일부 기사가 누락되고 다음 주 기사가 섞일 수 있다.

### 통계 및 상태 불일치 위험

CR-03과 CR-04를 수정하지 않으면 다음 데이터가 동시에 존재할 수 있다.

- 성공하면서 실패 Topic이 있는 run
- 실패하면서 저장 Topic이 있는 run
- 원문이 있으면서 missing인 기사
- reused이면서 failed인 기사

운영 로그, API publish 여부와 장애 분석을 신뢰하기 어려워진다.

### DB 우회 저장 위험

CR-05부터 CR-07까지 수정하지 않으면 애플리케이션 dataclass를 거치지 않는
SQL, 관리 도구 또는 향후 코드 경로에서 잘못된 데이터가 저장될 수 있다.

현재 repository 경로만 사용한다면 즉시 장애가 발생할 가능성은 낮지만, DB가
서비스 계약을 충분히 보호하지 못한다.

### Migration 적용 전 주의

`008_create_weekly_topic_tables.sql`은 아직 production DB에 적용되지 않았으므로
지금 제약을 보강하는 것이 가장 안전하다.

이미 적용된 이후라면 기존 row가 새 CHECK나 UNIQUE 조건을 위반하지 않는지 먼저
조회한 뒤 별도 migration으로 추가해야 한다.

### 기존 원문 유실 위험

CR-08은 loader가 항상 완전한 결과를 반환하면 드러나지 않는다. 하지만 partial
loader 결과가 발생하면 이미 보유한 원문을 잃고 Summary 근거 수가 줄어들 수
있다.

### Kubernetes credential 노출

CR-10은 즉각적인 취약점이라기보다 최소 권한 원칙 문제다. Weekly Job이
Kubernetes API를 사용하지 않으므로 token 자동 mount를 비활성화하는 것이
안전하다.
