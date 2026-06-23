# CodeRabbit Review: 3일 Topic pipeline·저장·API·CronJob 구축

## Review Summary

CodeRabbit은 3일 Topic pipeline의 dry-run 계약, DB connection 수명, CronJob 보안 설정, 설정값 검증, 기간별 idempotency 설명과 운영 문서의 migration 확인 절차를 검토했다.

검토 결과, 다음 세 항목은 PR 전에 반드시 수정하거나 실제 실행 계약을 확인해야 하는 문제로 판단한다.

1. `execute=False` 상태에서도 Summary provider가 호출될 수 있어 dry-run 계약을 위반할 가능성
2. 후보 조회용 DB connection이 원문 추출과 Summary API 호출 동안 계속 유지되어 connection pool 압력을 높이는 문제
3. migration 부분 적용 상태에서 운영자가 실행하도록 안내한 `::regclass` 기반 constraint 확인 SQL이 누락 테이블 때문에 실패하는 문제

CronJob의 `runAsNonRoot`와 `readOnlyRootFilesystem` 부재도 보안상 의미 있는 지적이다. 다만 현재 Docker image의 실행 사용자와 쓰기 경로를 확인하지 않고 바로 적용하면 Job 실행을 중단시킬 수 있으므로, image runtime 계약을 확인한 뒤 안전하게 적용해야 한다.

그 외 설정값 타입 검증, repository 상대 링크, 절대 window 기반 idempotency 표현, `_as_utc()` 타입 힌트와 API 문구는 빠르게 보완 가능한 품질 개선 항목이다.

## Problems Found

### 1. Dry-run에서도 Summary provider가 호출될 가능성

`summary_persistence_stage.py`는 선택된 Topic마다 Summary 입력을 만들고 다음 호출을 수행한다.

```python
summary = summary_provider.summarize(summary_input)
```

이 단계가 `execute=False`에서도 호출된다면 기본 dry-run 명령이 외부 Summary API를 사용하게 된다.

영향:

- 예상하지 못한 외부 API 비용 발생
- API key가 없는 dry-run의 실패
- dry-run에서 외부 네트워크 부수 효과 발생
- CLI의 `--execute` 안전 계약 위반

기본 dry-run은 후보 조회와 clustering 분석까지만 수행하거나, 실제 provider를 호출하지 않는 deterministic preview provider를 사용해야 한다.

Severity: Major

### 2. 후보 조회용 DB connection의 수명이 지나치게 김

`run_three_day_topic_pipeline.py`에서 연 read-only DB connection은 후보 조회에만 전달되지만, 현재 구조상 전체 `build_pipeline()` 호출 동안 유지되는 것으로 보인다.

후보 조회 이후에는 다음과 같은 장시간 작업이 수행된다.

```text
clustering
원문 지연 추출
외부 Summary API 호출
Topic별 실패 격리
저장 계획 구성
```

이 시간 동안 사용하지 않는 pooled connection이 계속 점유되면 다음 문제가 발생할 수 있다.

- DB connection pool 압력 증가
- 다른 API 또는 CronJob의 connection 획득 지연
- 외부 API timeout 동안 불필요한 DB session 유지
- 장기 실행 배치의 connection 누수 위험 증가

DB connection 범위는 `load_three_day_candidates()` 호출만 감싸도록 축소해야 한다.

Severity: Major

### 3. CronJob이 non-root 및 read-only root filesystem을 강제하지 않음

현재 container security context에는 다음 설정이 있다.

```yaml
allowPrivilegeEscalation: false
capabilities:
  drop: ["ALL"]
seccompProfile:
  type: RuntimeDefault
```

그러나 다음 항목은 없다.

```yaml
runAsNonRoot: true
readOnlyRootFilesystem: true
```

현재 상태에서는 image 기본 사용자와 filesystem 정책에 의존한다.

보안상 non-root 실행을 강제하는 것이 바람직하지만, 적용 전에 다음을 확인해야 한다.

- `seocj/news-api:latest` image의 기본 USER
- Python이 실행 중 bytecode 또는 cache를 기록하는지
- `/tmp` 등 임시 쓰기 경로가 필요한지
- 인증서, locale 또는 library가 runtime에 파일을 생성하는지

Image가 non-root를 지원하면 `runAsNonRoot: true`를 적용한다. Root filesystem을 read-only로 만들 경우 필요한 writable 경로에는 `emptyDir` volume을 명시해야 한다.

Severity: Major, runtime compatibility 확인 필요

### 4. 설정값 검증에서 비문자열 입력이 `AttributeError`를 발생시킬 수 있음

`candidate_stage.py`의 설정 검증은 다음 값에 바로 `.strip()`을 호출한다.

```python
provider
model
source_text_type
```

호출자가 문자열이 아닌 값을 전달하면 의도한 설정 오류인 `ValueError`가 아니라 `AttributeError`가 발생한다.

이는 잘못된 configuration을 명확한 오류 계약으로 변환하지 못하는 문제다.

다음 방식으로 타입과 공백을 함께 검사하는 것이 적절하다.

```python
if not isinstance(value, str) or not value.strip():
    raise ValueError(...)
```

비문자열과 공백 문자열을 각각 검증하는 회귀 테스트를 추가해야 한다.

Severity: Minor

### 5. 공통 `_as_utc()` helper의 입력 타입이 명시되지 않음

`selection.py`의 `_as_utc()`는 `None`과 `datetime`을 모두 처리하지만 타입 힌트가 없다.

기능상 오류는 아니지만 공통 모듈로 추출된 helper이므로 다음과 같이 계약을 명시하는 편이 낫다.

```python
def _as_utc(value: datetime | None) -> datetime | None:
```

Severity: Minor

### 6. Backend API 문서 표현이 불명확함

다음 문장은 의미를 이해할 수 있지만 운영자 관점에서 다소 부자연스럽다.

```text
성공 또는 부분 성공한 최신 72시간 window 하나의 bounded Topic card payload
```

다음처럼 단순화하는 것이 명확하다.

```text
성공 또는 부분 성공한 최신 72시간 window의 경량 Topic card payload
```

Severity: Minor

### 7. Review 문서에 machine-specific `local file URI under /Users/...` 링크가 포함됨

Antigravity review 문서에 로컬 절대 경로가 포함되어 있다.

```text
local file URI under /Users/seo''chanjin/...
```

이 링크는 다른 contributor와 GitHub에서 열리지 않으며 로컬 workspace 경로를 노출한다.

Repository 상대 링크로 교체해야 한다.

예:

```markdown
[task-authoring-guide.md](../agent/task-authoring-guide.md)
```

Severity: Minor, Security/Portability

### 8. Idempotency 설명에서 `reference_date`가 dedupe key처럼 해석될 수 있음

`reference_date`는 서울 기준의 달력 날짜이며 절대 실행 범위를 유일하게 식별하지 않는다.

같은 날짜에도 서로 다른 다음 실행이 가능하다.

```text
[2026-06-20T04:00+09:00, 2026-06-23T04:00+09:00)
[2026-06-20T05:00+09:00, 2026-06-23T05:00+09:00)
```

따라서 idempotency와 교체 기준은 다음 절대 시간 범위여야 한다.

```text
(window_start, window_end)
```

`reference_date`는 조회·표시를 위한 metadata로 명시해야 한다.

Severity: Minor, Data integrity documentation

### 9. 부분 migration 상태에서 constraint 확인 SQL이 실패함

Runbook은 migration 일부 object만 생성된 상태를 운영자가 조사하도록 안내한다.

그러나 constraint 확인 query에서 다음 표현을 사용한다.

```sql
'public.three_day_topic_runs'::regclass
```

해당 테이블 중 하나라도 없으면 PostgreSQL이 cast 단계에서 오류를 발생시키므로, 부분 적용 상태를 조사하기 위한 query 자체를 실행할 수 없다.

`to_regclass()`을 사용해 존재하는 table만 대상으로 constraint를 조회해야 한다.

개념적으로 다음 형태가 적절하다.

```sql
with target_tables as (
    select to_regclass('public.three_day_topic_runs') as relation
    union all
    select to_regclass('public.three_day_topics')
    union all
    select to_regclass('public.three_day_topic_articles')
)
select
    constraint_row.conrelid::regclass as table_name,
    constraint_row.conname,
    pg_get_constraintdef(constraint_row.oid) as definition
from pg_constraint as constraint_row
where constraint_row.conrelid in (
    select relation
    from target_tables
    where relation is not null
)
order by table_name::text, constraint_row.conname;
```

Severity: Minor, Operational correctness

## Required Fixes Before PR

- [ ] `execute=False`인 dry-run에서 실제 Summary provider가 호출되지 않도록 실행 경계를 수정한다.
- [ ] dry-run에서 provider 호출 횟수가 0임을 검증하는 회귀 테스트를 추가한다.
- [ ] 후보 조회용 DB connection 범위를 `load_three_day_candidates()` 실행 구간으로 축소한다.
- [ ] 원문 추출 또는 Summary provider 처리 동안 후보 조회 connection이 열린 상태가 아님을 테스트하거나 구조적으로 보장한다.
- [ ] CronJob image가 non-root 실행을 지원하는지 확인하고 `runAsNonRoot` 적용 여부를 결정한다.
- [ ] `readOnlyRootFilesystem` 적용 시 필요한 writable 경로와 `emptyDir` volume을 함께 설계하거나, 적용할 수 없는 구체적 근거를 문서화한다.
- [ ] migration 부분 적용 상태에서도 실행 가능한 `to_regclass()` 기반 constraint 확인 query로 Runbook을 수정한다.
- [ ] 설정값 validation에서 비문자열 및 공백 문자열을 명시적인 `ValueError`로 처리하고 테스트한다.
- [ ] Review 문서의 machine-specific `local file URI under /Users/...` 링크를 repository 상대 링크로 교체한다.
- [ ] Task와 설계 문서에서 결과 교체 기준을 `(window_start, window_end)`로 명확히 하고 `reference_date`는 metadata임을 기록한다.

## Optional Improvements

- `_as_utc()`에 `datetime | None` 입력·반환 타입을 명시한다.
- `/three-day-topics/home` 설명을 “최신 72시간 window의 경량 Topic card payload”처럼 단순화한다.
- CronJob 보안 설정을 기존 Daily Topic CronJob에도 동일하게 적용할지는 별도 공통 인프라 hardening 작업으로 검토한다.
- 설정값의 타입 검증이 여러 stage에 반복된다면 공통 configuration validator로 추출하는 방안을 후속 검토한다.
- Migration의 JSONB array, Topic status와 rank uniqueness 제약 강화는 현재 repository 계약과 실제 운영 데이터 확인 후 별도 검토한다.

## Suggested Test Commands

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -v
```

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topics_api.py \
  -v
```

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_daily_topic_article_selection.py \
  -v
```

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

```bash
python -m compileall app scripts tests
```

```bash
git diff --check
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

CronJob 보안 설정 변경 후에는 다음도 사람이 수행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

## Risk Notes

- Dry-run provider 호출 문제를 수정할 때 Summary stage 전체를 건너뛰면 dry-run 분석 payload나 예상 저장 계획이 사라질 수 있다. Dry-run에서 어떤 결과까지 생성해야 하는지 CLI 계약을 먼저 고정해야 한다.
- DB connection 범위를 줄일 때 candidate row가 connection 종료 후에도 완전히 materialize된 plain model인지 확인해야 한다. Lazy iterator나 DB-backed row를 외부 단계까지 전달하면 안 된다.
- `runAsNonRoot: true`는 image가 root 사용자만 전제로 만들어졌다면 Job 시작 자체를 실패시킬 수 있다.
- `readOnlyRootFilesystem: true`는 Python, OpenSSL, temporary file 또는 library cache 쓰기를 차단할 수 있으므로 writable `emptyDir` 경로 검증이 필요하다.
- Idempotency 문서만 수정하는 것이 아니라 repository의 advisory lock과 delete 조건이 실제로 `(window_start, window_end)`를 사용하고 있는지도 함께 확인해야 한다.
- `to_regclass()` 기반 query는 누락 object를 안전하게 건너뛰지만, 누락된 table 자체가 정상이라는 의미는 아니다. 별도의 table existence query와 함께 사용해야 한다.
- Review 파일 링크 수정 시 로컬 절대 경로가 다른 문서에도 남아 있는지 repository 전체를 검색해야 한다.

## Verdict

**CHANGES REQUIRED**
