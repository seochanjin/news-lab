# Task: Topic Summary 제목·기간 정합성 수정

## Goal

3-day·Weekly Topic Summary에서 LLM이 생성한 제목에 날짜·기간 표현이 섞여 저장되는 문제를 수정한다.

이번 Backend 작업의 원칙은 다음과 같다.

```
결정적 데이터인 날짜·기간
→ 기존 Topic 생성 시각과 Pipeline 기간 계약으로 계산
→ DB에 별도 저장하지 않음
→ API가 명시적으로 전달

LLM이 생성한 제목
→ 신뢰할 수 없는 입력
→ 저장 전 sanitize·validate
→ 실패 시 deterministic fallback
```

날짜와 기간은 LLM title에서 파싱하거나 역산하지 않는다. 기존 Topic의 생성 시각과 3-day·Weekly Pipeline의 기간 계약을 기준으로 Backend가 결정적으로 계산한다. 기존 run relation에 더 명확한 기준 정보가 있다면 이를 우선 사용하되, 새로운 DB field는 추가하지 않는다.

이번 작업은 78차 최종 정합성 수정의 Backend 단계다. Frontend의 KST 기간 표시와 UTC ISO datetime 노출 제거는 Backend API 계약과 Production 데이터가 확정된 뒤 별도 Frontend 브랜치에서 진행한다.

- **Backend branch:** `fix/topic-summary-title-period-consistency`
- **시간 상한:** Backend·Frontend 전체 1일
- **완료 후 방향:** 문서 정합화 후 프로젝트 동결

## Scope

### Repository baseline 조사

다음 흐름을 먼저 확인한다.

```
Pipeline period 계산
→ run record 저장
→ LLM prompt 호출
→ Summary title parse
→ Topic DB 저장
→ API serialization
```

확인 대상:

- Daily·3-day·Weekly Summary 생성 함수와 prompt
- LLM 응답에서 title을 추출하는 parser
- Topic title 저장 경로
- `three_day_topics`, `weekly_topics`의 기존 `created_at`과 run relation
- 3-day·Weekly 기간을 기존 데이터만으로 결정적으로 계산할 수 있는지
- 3-day·Weekly Home/list/detail API response schema
- 기존 Production title에 존재하는 날짜·기간 패턴
- 현재 Backend test command와 migration 관례

### Title sanitize와 validation

공통 title sanitizer를 구현한다.

```
LLM title
→ 기본 문자열 정규화
→ 날짜·기간 deny-list 제거
→ 공백·구두점 정리
→ residual pattern 검증
→ deterministic fallback
```

처리 대상 예시:

- `3일차 기록`, `최근 3일`, `72시간 기록`
- `7월 12일~7월 15일`
- `2026-07-12`, `2026.07.12`
- `(월~일)`, `(월요일~일요일)`
- 제목 앞뒤 또는 괄호에 붙은 기간 표현

일반 숫자는 무조건 삭제하지 않는다. `AI 3대 기업`, `GPT-5`처럼 내용에 필요한 숫자는 보존한다.

다음 조건은 sanitize 실패로 판단한다.

- 빈 문자열 또는 의미 없는 문자열
- 허용 길이 위반
- 날짜·기간 pattern 잔존
- 구두점·특수문자만 남음

Fallback은 LLM을 재호출하지 않고 대표 keyword 또는 대표 기사 제목을 기반으로 결정적으로 생성한다. 최종 fallback에도 날짜·기간 표현을 포함하지 않는다.

### LLM prompt 계약

Summary prompt에 다음 계약을 추가한다.

```
제목에는 날짜, 연도, 월, 일, 요일, 기간과 시간 범위를 포함하지 않는다.
제목은 뉴스 내용과 핵심 주제만 표현한다.
```

Prompt 준수만 신뢰하지 않고 저장 전 sanitizer를 반드시 통과시킨다.

### Period 계산·API 계약

3-day·Weekly Topic의 기존 생성 시각과 Pipeline 기간 계약을 사용해 기간을 계산한다. 기간 field는 DB에 저장하지 않고 API serialization 단계에서 생성한다.

```
period_start
→ 기간에 포함되는 첫 번째 KST 날짜
→ ISO date YYYY-MM-DD

period_end
→ 기간에 포함되지 않는 첫 번째 KST 날짜
→ end-exclusive
→ ISO date YYYY-MM-DD
```

범위 의미는 `[period_start, period_end)`다.

예:

```
period_start = 2026-07-12
period_end   = 2026-07-15

포함 날짜
→ 7월 12일
→ 7월 13일
→ 7월 14일
```

`period_label`은 canonical data가 아니며 API에서 계산 가능한 표시용 field로만 검토한다. 시간 상한을 위협하면 제외한다.

### 기존 데이터 처리

기존 Topic row와 schema는 변경하지 않는다.

기존 title은 API response를 만들 때 동일한 sanitizer를 적용해 사용자 화면에 날짜·기간 노이즈가 노출되지 않게 한다. 새로 생성되는 Summary title은 저장 전에 sanitizer를 통과시킨다.

기존 데이터 검증에서는 write 없이 다음을 확인한다.

- 전체 대상 row
- sanitize 결과가 변경되는 row
- 변경 없이 유지되는 row
- fallback이 필요한 row
- sanitize 후 날짜·기간 pattern이 남는 row
- period 계산 성공·실패 row
- invalid period row

기존 DB title을 일괄 update하는 backfill이나 period migration은 수행하지 않는다.

### 새 저장 경로와 API

새 Summary 저장 순서는 다음과 같다.

```
LLM Summary 생성
→ title sanitize·validate
→ 필요 시 fallback
→ sanitized title을 기존 title column에 저장
→ API serialization에서 period_start·period_end 계산
```

3-day·Weekly Home/list/detail response에는 기존 field를 유지하면서 다음 field를 추가한다.

```json
{
  "title": "AI 반도체 투자 경쟁",
  "period_start": "2026-07-12",
  "period_end": "2026-07-15"
}
```

기존 endpoint와 field를 삭제하거나 rename하지 않는다.

### Daily 적용 범위

UNIT baseline 조사에서 Daily title에도 같은 문제가 확인되면 동일 sanitizer를 재사용한다. Daily schema 변경이나 Topic model 전체 통합은 하지 않는다.

## Do not change

- Topic grouping algorithm
- Summary body 생성 방식
- 대표 기사 선정 방식
- Embedding 생성·저장 방식
- Pipeline stage 구조와 실행 순서
- CronJob command, schedule, timezone, retry와 concurrency 정책
- K3s Deployment·Job·CronJob resource
- Redis key, TTL과 Home Cache prewarming 구조
- Alert와 Monitoring rule
- LLM provider, model, temperature와 token 설정
- API endpoint 경로
- 기존 API field 삭제 또는 rename
- 인증·권한 정책
- 날짜 parsing dependency 추가
- Topic model 공통 상속 구조 도입
- Repository 전반의 date utility 리팩터링
- DB schema·migration·backfill 추가
- 기존 title에서 period를 역산하는 처리
- 기존 Production title 일괄 update
- Frontend code
- Production DB에 Agent가 직접 write
- Secret 조회·출력·변경
- Agent의 Production rollout, git push와 merge

## Expected files

정확한 path는 Repository baseline 조사 후 확정한다.

```
app/.../topic summary prompt
app/.../topic title sanitizer
app/.../three-day pipeline
app/.../weekly pipeline
app/.../daily pipeline              # 동일 문제 확인 시 sanitizer 재사용만
app/.../API schemas 또는 serializers
app/.../period 계산 utility
tests/...title sanitizer
tests/...period calculation
tests/...topic API
tests/...pipeline save
docs/tasks/fix-topic-summary-title-period-consistency.md
docs/verification/fix-topic-summary-title-period-consistency.md
```

실제 필요가 없는 design·review·fix 문서는 미리 만들지 않는다.

## DB changes

없음.

- `three_day_topics`, `weekly_topics`에 `period_start`, `period_end` column을 추가하지 않는다.
- Schema migration, data migration과 backfill script를 만들지 않는다.
- 기존 `created_at`, Pipeline 기간 계약과 필요 시 기존 run relation을 사용해 API serialization 단계에서 기간을 계산한다.
- 기존 Topic title은 DB에서 일괄 수정하지 않고 API response 단계에서 sanitize한다.
- 새 Summary title만 저장 전에 sanitize해 기존 title column에 기록한다.

## API changes

기존 소비자 하위 호환을 유지하는 field 추가 수준의 변경이다.

추가 대상:

```
period_start
period_end
period_label  # 시간과 현재 API 구조를 검토한 뒤 선택
```

계약:

- 기존 endpoint와 response field 유지
- `period_start`, `period_end`는 ISO date 형식
- `period_end`는 end-exclusive
- title text는 period field에 영향을 주지 않음
- raw datetime field가 기존 계약에 필요하면 삭제하지 않음

Frontend는 후속 브랜치에서 새 period field를 사용해 KST 범위를 표시한다.

## Test commands

실제 test path는 Repository 조사 후 확정한다.

### Targeted tests

```bash
PYTHONPATH=. pytest -q \
  tests/test_topic_title.py \
  tests/test_topic_period.py \
  tests/test_topic_summary.py \
  tests/test_save_topic_summaries.py \
  tests/test_daily_topic_summary_persistence.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  tests/test_three_day_topics_api.py \
  tests/test_weekly_topic_pipeline.py \
  tests/test_weekly_topic_repository.py \
  tests/test_weekly_topics_api.py \
  tests/test_topics_api.py \
  tests/test_home_cache_integration.py \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_run_weekly_topic_pipeline.py \
  tests/test_analyze_topic_title_periods.py
```

필수 case:

- 날짜 없는 정상 title 유지
- `3일차 기록`, `72시간 기록` 제거
- 숫자 날짜 범위와 요일 범위 제거
- 괄호형 기간 제거
- 일반 숫자가 포함된 content title 보존
- sanitize 후 빈 문자열 fallback
- residual pattern fallback
- keyword 또는 대표 기사 기반 fallback
- period start/end 계산
- end-exclusive 의미와 KST 경계
- 기존 API field 유지
- API period field 추가
- 새 Pipeline 저장 시 sanitized title 사용
- title 문자열이 period field에 영향을 주지 않음

### 전체 회귀

```bash
PYTHONPATH=. pytest -q
```

### 기존 데이터 read-only 검증

Production 또는 sanitized fixture를 대상으로 write 없이 다음을 확인한다.

```
period calculation failure = 0
invalid period = 0
residual date pattern after sanitize = 0
unhandled sanitize failure = 0
```

기존 DB row를 update하는 migration command는 실행하지 않는다.

### Repository 검사

```bash
git diff --check
git status --short
git diff --stat
git diff --name-only
```

Pipeline stage, CronJob, K3s, Redis, Monitoring, dependency와 lock file에 의도하지 않은 변경이 없어야 한다.

## Acceptance criteria

- [x] 새 Summary title은 저장 전 sanitizer를 통과하며 날짜·기간 pattern이 남지 않고 실패 시 deterministic fallback을 사용한다.
- [x] 3-day·Weekly의 `period_start`, `period_end`는 기존 생성 시각과 Pipeline 기간 계약을 기준으로 API에서 계산되며 기존 title에서 역산하지 않는다.
- [x] 기존 데이터 read-only 검증에서 period 계산 실패, invalid range와 미처리 sanitize 실패가 0건이고 DB schema·data migration은 수행하지 않는다.
- [x] 기존 API field를 유지하면서 3-day·Weekly response에 period field를 추가한다.
- [x] Targeted test와 전체 Backend 회귀 검증이 통과하고 Pipeline stage, CronJob, K3s resource에는 변경이 없다.
- [ ] Production 배포·API smoke verification은 사람이 수행하고, DB migration이나 기존 row update가 없음을 sanitized evidence와 함께 Verification에 기록한다.

## Notes

- 78차는 계획된 마지막 기능·정합성 수정 차수다.
- Backend를 먼저 완료하고 API 계약과 Production data를 확인한 뒤 Frontend를 별도 브랜치에서 진행한다.
- Frontend 후속 범위는 KST 기간 표시 통일과 UTC ISO datetime 직접 노출 제거로 제한한다.
- 전체 작업 상한은 Backend와 Frontend를 합쳐 1일이다.
- 초과 조짐이 있으면 Daily sanitizer, `period_label`과 공통 formatter abstraction 순서로 범위를 줄인다.
- 3-day·Weekly deterministic period 계산, 새 title sanitize, 기존 데이터 read-time sanitize와 API period field는 제거하지 않는다.
- Prompt 준수 여부를 신뢰하지 않는다. 저장 전 code-level sanitize를 완료 조건으로 사용한다.
- 78차 이후에는 포트폴리오·README·Architecture·Runbook·Notion 정합화 후 프로젝트를 동결한다.
- 79차는 Production 장애, 보안 문제, 데이터 손상 위험, 명백한 사용자 화면 오류 또는 취업 제출물의 사실 오류에만 허용한다.

## UNIT-01 Baseline

### 제목 생성과 저장 흐름

| 구분 | Prompt·parser | 저장 경로 | 현재 제목 검증 |
| --- | --- | --- | --- |
| Daily | `app/utils/topic_summary.py`의 `_provider_prompt()` → `parse_provider_response()` | `app/services/daily_topic_pipeline/summary_persistence_stage.py` → `scripts/save_topic_summaries.py`의 `build_save_plan()`·`execute_save_plan()` → `topics.title_ko` | parser가 JSON field와 type·confidence 범위만 검증하며 날짜·기간은 허용한다. Deterministic provider도 대표 기사 제목을 그대로 포함한다. |
| 3-day | `app/services/three_day_topic_pipeline/summary_persistence_stage.py`의 `build_three_day_summary_prompt()` → 공통 `parse_provider_response()` | `_build_topic_record()` → `ThreeDayTopicRepository.replace_window_topics()` → `three_day_topics.title_ko` | `summary["title_ko"]`를 변환 없이 record와 insert bind parameter로 전달한다. |
| Weekly | `app/services/weekly_topic_pipeline/summary_persistence_stage.py`의 `build_weekly_summary_prompt()` → 공통 `parse_provider_response()` | `_build_topic_record()` → `WeeklyTopicRepository.replace_window_topics()` → `weekly_topics.title_ko` | `summary["title_ko"]`를 변환 없이 record와 insert bind parameter로 전달한다. |

세 prompt 모두 현재 제목에서 날짜·연도·요일·기간을 제외하라는 계약이 없다.
따라서 Daily에도 같은 입력 신뢰 경계가 존재하며 UNIT-02에서는 공통 sanitizer를
재사용하되 Daily schema나 Topic model 구조는 변경하지 않는다.

### 기간과 run relation

- 3-day context는 `resolve_three_day_pipeline_context()`에서 실행 시작 instant 또는
  명시 `window_end`를 UTC로 정규화하고 정확히 72시간을 뺀
  `[window_start, window_end)`를 만든다. `reference_date`는 `window_end`의 KST
  날짜다.
- Weekly context는 KST 월요일 00:00부터 다음 월요일 00:00 미만인 완료 주간을
  만들며 `week_start`는 포함 첫 날짜, 기존 `week_end`는 포함 마지막 일요일이다.
- 두 pipeline 모두 동일 context의 기간을 run row와 Topic row에 함께 저장하고,
  Topic의 `run_id`가 해당 run을 참조한다. `created_at`도 양쪽 Topic row에 있지만
  DB insert 시각이므로 명시 window보다 약한 근거다.
- Home 조회는 Topic과 성공·부분 성공 run을 join해 최신 publishable window를
  고르지만 archive와 detail은 Topic row만 읽는다. 새 DB field 없이 Topic row의
  window와 run relation의 일치 여부를 검증할 수 있다.

Weekly의 날짜형 period는 기존 값만으로 손실 없이
`period_start = week_start`, `period_end = week_end + 1 day`로 계산할 수 있다.
3-day도 KST로 변환한 window 경계에서 결정적으로 날짜를 만들 수 있으나, 기본
window는 05:00 같은 실행 시각에 끝날 수 있다. 이 경우 정확한 72시간 window가
KST calendar date 네 개에 걸치므로, “window가 실제로 닿는 모든 날짜”와
“`reference_date` 직전 3개 날짜”는 서로 다른 계약이다. UNIT-03에서 이 차이를
테스트로 고정해야 하며 title 또는 `created_at`에서 기간을 역산해서는 안 된다.

### API serialization baseline

| API | 현재 반환 경로와 기간 관련 field |
| --- | --- |
| Daily list/home/detail | `app/routers/topics.py`, `app/home_topics_payload.py`; `topic_date`를 반환하고 별도 period field는 없다. |
| 3-day list/detail | `app/routers/three_day_topics.py`; `reference_date`, UTC datetime `window_start`, `window_end`를 Topic row dict로 직접 반환한다. |
| 3-day home | `fetch_three_day_home_topics_from_database()`; 최상위와 각 item에 `reference_date`, `window_start`, `window_end`가 있고 run join은 최신 window 선택에만 사용한다. |
| Weekly list/detail | `app/routers/weekly_topics.py`; `week_start`, 포함 마지막 날인 `week_end`, UTC datetime `window_start`, `window_end`를 직접 반환한다. |
| Weekly home | `fetch_weekly_home_topics_from_database()`; 최상위와 각 item에 같은 기간 metadata가 있고 성공 run 및 `ready` Topic을 join/filter한다. |

명시적인 Pydantic response model이나 별도 serializer는 없고 SQL mapping을 dict로
바꾸는 방식이다. 따라서 후속 API 변경은 router list/detail과 공유 Home payload
builder 양쪽에 적용해야 하며 기존 field를 유지해야 한다. Redis Home cache는 이
builder 결과를 보관하므로 payload 변경 시 cache serialization 회귀도 확인한다.

### 기존 데이터와 검증 경로

- Repository 안에는 Production 3-day·Weekly title 전체 또는 sanitized snapshot이
  없다. Task에 제시된 `3일차 기록`, `최근 3일`, `72시간 기록`, 숫자 날짜 범위와
  요일 범위는 요구사항 예시이며 실제 row별 빈도 증거로 간주하지 않는다.
- Production DB/API 조회는 사람 주도 검증 범위이므로 UNIT-01에서 실행하지 않았다.
  전체 row count와 pattern별 count는 UNIT-04의 read-only sanitized evidence가
  제공될 때 기록한다.
- 현재 직접 관련된 회귀 파일은 `tests/test_topic_summary.py`,
  `tests/test_daily_topic_summary_persistence.py`,
  `tests/test_three_day_topic_pipeline.py`,
  `tests/test_three_day_topic_repository.py`,
  `tests/test_three_day_topics_api.py`,
  `tests/test_weekly_topic_pipeline.py`,
  `tests/test_weekly_topic_repository.py`, `tests/test_weekly_topics_api.py`다.
- Migration은 순번 SQL인 `db/migrations/007_create_three_day_topic_tables.sql`과
  `008_create_weekly_topic_tables.sql`에 run·Topic window와 FK를 정의한다. 이번
  Task는 schema·migration·backfill을 추가하지 않는다.

## UNIT-02 Implementation

### 제목 신뢰 경계

- `app/utils/topic_title.py`에 Daily·3-day·Weekly가 함께 사용하는 제목 sanitizer를
  추가했다. Unicode·공백 정규화 후 상대 기간, 숫자 날짜·연도·월, 요일·시간
  범위와 기간 단위를 제거하고 빈 괄호·구분자·가장자리 구두점을 정리한다.
- 정제 결과는 최대 120자, 문자 또는 숫자를 포함한 의미 있는 문자열, 날짜·기간
  pattern 부재를 검증한다. `기록`, `요약`, `흐름`처럼 기간 제거 뒤 정보가 없는
  label만 남은 결과도 실패로 처리한다.
- fallback은 provider keyword 순서, 대표 기사를 우선한 기사 제목 순서, 고정
  `주요 뉴스 이슈` 순으로 각 후보를 동일하게 sanitize·validate한다. LLM을 다시
  호출하거나 무작위 값을 사용하지 않는다.
- 기간 단위가 아닌 `AI 3대 기업`, `GPT-5`, `1주택`, `3년물` 같은 내용 숫자는
  보존한다.

### Prompt와 저장 경로

- 세 Summary prompt에 날짜·연도·월·일·요일·기간·시간 범위를 제목에서
  제외하고 뉴스 내용과 핵심 주제만 표현한다는 계약을 추가했다.
- 계약 변경을 hash/audit metadata에 반영하도록 3-day prompt version을
  `three-day-flow-v2`, Weekly를 `weekly-flow-v2`로 올렸다.
- Daily는 `build_save_plan()`, 3-day·Weekly는 repository record 생성 시점에
  sanitizer를 적용해 새 `title_ko`가 저장 parameter에 들어가기 전에 검증되게
  했다.
- 기존 row의 read-time sanitize, period 계산과 API response 변경은 후속 UNIT
  범위로 남겼으며 이번 UNIT에서 구현하지 않았다.

## UNIT-03 Implementation

### Period 계산 계약

- `app/utils/topic_period.py`에 DB 접근이나 새 field 저장 없이 Topic row의 기존
  기간 metadata를 검증하고 KST date를 계산하는 순수 utility를 추가했다.
- 3-day는 `window_start`와 `window_end`가 timezone-aware이며 정확히 72시간인지,
  `reference_date`가 `window_end`의 KST 날짜와 같은지 확인한다. API 날짜 범위는
  두 absolute window 경계의 KST 날짜를 사용한다. 따라서 기본 05시 실행처럼
  비자정 window도 `period_start = KST window_start 날짜`,
  `period_end = KST window_end 날짜`로 고정하며, 실제 window가 닿는 날짜를
  모두 열거해 4일 범위로 넓히지 않는다.
- Weekly는 기존 `week_start`, 포함 마지막 날인 `week_end`와 정확한 7일 KST
  자정 window가 일치하는지 확인하고 `period_start = week_start`,
  `period_end = week_end + 1 day`를 반환한다.
- 명시적인 Topic window와 기준 날짜가 insert 시각인 `created_at`보다 강한
  근거이므로 period 계산은 title과 `created_at`에 의존하지 않는다. 유효하지
  않은 기존 row는 조용히 추정하지 않고 `ValueError`로 드러내 UNIT-04의
  read-only 검증에서 집계할 수 있게 했다.

### 하위 호환 API 응답

- 3-day·Weekly list와 detail의 각 Topic에 `period_start`, `period_end`를 추가하고
  기존 response field와 endpoint를 그대로 유지했다.
- 두 Home payload의 최상위 metadata와 각 item에도 같은 period field를 추가했다.
  Topic이 없는 Home 응답은 기존 null metadata 계약과 같이 두 field를 `null`로
  반환한다.
- FastAPI JSON encoding에서 두 `date` 값은 `YYYY-MM-DD` 문자열이 된다. 별도
  `period_label`은 canonical field가 아니며 시간 상한을 고려해 추가하지 않았다.
- Home cache validator가 period field 없는 이전 payload를 miss로 처리하게 해
  DB builder에서 새 응답을 재생성한다. Redis key, TTL과 prewarm 구조는 바꾸지
  않았다.
- 기존 title의 read-time sanitize와 Production row 검증은 UNIT-04 범위로 남겼다.

## UNIT-04 Implementation

### 기존 title의 read-time 신뢰 경계

- Daily·3-day·Weekly의 list, detail과 Home DB payload가 기존 `title_ko`를
  공통 sanitizer로 복사 정제한 뒤 반환한다. 기존 DB row는 수정하지 않으며
  fallback에는 row의 keyword 순서를 사용한다.
- 날짜·기간 제목이 남아 있는 기존 Redis Home payload는 cache hit로 반환하지
  않고 miss 처리해 DB builder가 정제된 payload를 다시 만들게 했다. Redis key,
  TTL과 prewarm 흐름은 변경하지 않았다.
- UNIT-01에서 Daily에도 같은 title 신뢰 문제가 확인됐으므로 공통 sanitizer를
  재사용했다. Daily schema와 period 계약은 변경하지 않았다.

### 전체 row read-only 검증 경로

- `scripts/analyze_topic_title_periods.py`는 Daily·3-day·Weekly Topic 전체 row의
  제목 변경·유지·fallback·잔존 pattern과 3-day·Weekly period 성공·실패·invalid
  건수를 집계한다.
- DB mode는 첫 SQL로 `set transaction read only`를 실행하고 `select`만 사용한다.
  결과에는 원본 title, keyword와 row별 값을 넣지 않으며 schema·data write를
  수행하지 않는다. 운영자가 제공한 sanitized JSON fixture도 같은 집계 경로로
  검증할 수 있다.
- 로컬 synthetic fixture에서는 전체 3 row 중 제목 변경 2, 유지 1, fallback 1,
  period 성공 2였고 residual pattern, 미처리 sanitize 실패, period 실패와 invalid
  period는 모두 0이었다.
- 사람이 Production 전체 243 row를 대상으로 analyzer의 read-only 검증을
  수행했다. Period 계산 실패, invalid period, residual date pattern과 미처리
  sanitize 실패는 모두 0건이었고 DB write와 title 값 노출은 없었다.

## UNIT-05 Progress

- 확정된 targeted suite는 `180 passed, 68 subtests passed`, 전체 Backend 회귀는
  `471 passed, 122 subtests passed`로 통과했다.
- Repository 검사에서 whitespace 오류와 `db/migrations/`, `requirements.txt`,
  `k8s/` 변경이 없음을 확인했다.
- PR·devlog 초안과 Verification을 실제 로컬 결과에 맞춰 정리했다.
- Production 배포와 3-day·Weekly Home/list/detail API smoke verification은
  사람이 수행해야 하므로 UNIT-05와 전체 Verification은 아직 완료하지 않는다.

## Implementation Units

- [x] UNIT-01: Topic Summary 제목 생성·저장, Pipeline 기간 계산, run relation과 API 응답 경로 baseline 조사
- [x] UNIT-02: 제목 sanitizer·validation·deterministic fallback 구현 및 LLM prompt의 날짜·기간 제외 계약 반영
- [x] UNIT-03: 기존 생성 시각·Pipeline 기간 계약 기반 period 계산과 하위 호환 API 응답 구현
- [x] UNIT-04: 기존 데이터 read-time title sanitize와 period 계산의 read-only 검증
- [ ] UNIT-05: Backend targeted·전체 회귀 테스트, 사람 주도 Production 배포·API 검증과 최종 문서화
