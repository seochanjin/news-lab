# Approved Fixes: 3일 Topic pipeline·저장·API·CronJob 구축

## Approved Fixes

- [x] FIX-01: Dry-run에서 외부 Summary provider 호출 차단
  - `execute=False`에서는 실제 `summary_provider.summarize()`를 호출하지 않는다.
  - Dry-run에서는 OpenAI API key, 외부 네트워크 요청과 Summary API 비용이 필요하지 않아야 한다.
  - 후보 조회, clustering, 대표·관련·Summary 근거 기사 선정과 분석 통계까지만 수행한다.
  - 원문 지연 추출, Summary provider 호출과 DB 결과 교체는 `execute=True`에서만 수행한다.
  - `execute=False`에서 provider 호출 횟수가 0이고 repository 결과 교체가 발생하지 않는 테스트를 추가한다.
  - `execute=True`의 기존 Summary 생성과 저장 계약은 유지한다.

- [x] FIX-02: 후보 조회용 DB connection 수명 축소
  - read-only connection은 `load_three_day_candidates()` 실행 구간에서만 유지한다.
  - 후보와 embedding 결과를 일반 Python model로 완전히 materialize한 뒤 connection을 반환한다.
  - clustering, 원문 확보와 Summary provider 호출 중에는 후보 조회 connection을 보유하지 않는다.
  - 결과 저장 transaction은 기존 repository 경계를 통해 별도로 생성한다.
  - 원문 추출과 Summary 처리 전에 후보 조회 connection이 반환되는 구조를 테스트로 보호한다.

- [x] FIX-03: Candidate embedding 설정값 타입 검증 보강
  - `provider`, `model`, `source_text_type`에 `.strip()`을 호출하기 전에 문자열 타입을 확인한다.
  - 비문자열, 빈 문자열과 공백 문자열은 field 이름이 포함된 `ValueError`로 처리한다.
  - `None`, 숫자, list 또는 dict 입력이 `AttributeError`로 누출되지 않도록 한다.
  - 유효한 문자열 설정의 기존 동작은 유지한다.

- [x] FIX-04: 절대 window 기준 idempotency 계약으로 문서 통일
  - 3일 Topic의 중복 방지, advisory lock과 결과 교체 기준을 `(window_start, window_end)`로 명확히 한다.
  - `reference_date`는 서울 기준 표시, archive filter와 운영 조회를 위한 metadata로만 설명한다.
  - 같은 `reference_date`에도 서로 다른 절대 window가 존재할 수 있음을 문서화한다.
  - Task, 설계, Architecture, Runbook, PR과 devlog의 관련 표현을 확인해 통일한다.
  - repository가 실제로 절대 window 기준 lock·delete·insert를 사용하는지 회귀 테스트로 확인한다.

- [x] FIX-05: 부분 migration 상태에서도 실행 가능한 schema 확인 SQL로 수정
  - `docs/runbooks/database-check.md`의 constraint 조회에서 누락된 table을 직접 `::regclass`로 변환하지 않는다.
  - `to_regclass()`을 사용해 존재하는 relation만 `pg_constraint` 조회 대상으로 사용한다.
  - table 존재 여부 확인 query는 별도로 유지한다.
  - 세 table이 모두 존재해야 정상 적용 완료임을 명시한다.
  - 일부 table만 존재하는 경우 자동 drop이나 무조건 재실행하지 않고 migration 이력과 실제 object를 비교하도록 안내한다.

- [x] FIX-06: Machine-specific file URI를 repository 상대 링크로 교체
  - 문서의 `local file URI under /Users/...` 및 개인 workspace 절대 경로를 제거한다.
  - GitHub와 다른 개발 환경에서도 동작하는 repository 상대 Markdown 링크로 교체한다.
  - 문서 전체를 검색해 같은 유형의 로컬 경로가 남아 있지 않은지 확인한다.
  - 명령 예시로 의도적으로 사용된 일반 경로와 실제 개인 workspace 노출을 구분한다.

- [x] FIX-07: 공통 UTC 변환 helper 타입 힌트 추가
  - `_as_utc()`의 signature를 `datetime | None` 입력과 반환 타입으로 명시한다.
  - `None`, naive datetime과 timezone-aware datetime의 기존 처리 정책은 유지한다.
  - Daily Topic과 3일 Topic의 정렬 결과에 회귀가 없는지 확인한다.

- [x] FIX-08: 3일 Topic Home API 문구 명확화
  - `/three-day-topics/home` 설명을 “성공 또는 부분 성공한 최신 72시간 window의 경량 Topic card payload”처럼 명확한 표현으로 수정한다.
  - 최신 publishable window 한 개를 반환한다는 점을 명시한다.
  - 전체 count query와 관련 기사 detail join을 수행하지 않는 경량 API임을 유지한다.
  - API 구현이나 응답 계약은 변경하지 않는다.

- [x] FIX-09: CronJob non-root 실행 계약 확인 및 안전한 보안 설정 반영
  - Dockerfile 최종 사용자와 실제 image의 실행 UID/GID를 확인한다.
  - Python, 원문 추출 library와 외부 HTTP 처리 과정에서 필요한 쓰기 경로를 확인한다.
  - image가 지원하면 `runAsNonRoot: true`를 적용한다.
  - `readOnlyRootFilesystem: true`는 필요한 writable 경로를 확인한 뒤 적용한다.
  - `/tmp` 등 쓰기 경로가 필요하면 `emptyDir` volume과 mount를 함께 추가한다.
  - 적용할 수 없다면 구체적인 runtime 제약과 필요한 image 변경을 문서화하고 별도 container hardening 작업으로 보류한다.
  - 기존 `allowPrivilegeEscalation: false`, capability drop과 `RuntimeDefault` seccomp 설정은 유지한다.

## Rejected or Deferred Suggestions

### Deferred: 검증 없이 `readOnlyRootFilesystem: true` 즉시 적용

현재 image의 runtime 쓰기 경로를 확인하지 않고 root filesystem을 read-only로 만들면 Python, 원문 추출 library 또는 임시 파일 사용으로 CronJob이 실패할 수 있다.

Image와 실행 경로를 확인한 결과 필요한 writable path를 `emptyDir`로 분리할 수 있으면 FIX-09에 포함한다. Docker image 변경이 필요하면 기존 API 및 Daily Topic workload와 함께 별도 container hardening 작업으로 진행한다.

### Deferred: 3일 Topic DB 제약 추가 강화

다음 항목은 이번 CodeRabbit review에서 확인된 직접 결함이 아니며 현재 migration, model과 repository 테스트가 기존 계약을 보호하고 있다.

- `key_points`, `keywords`의 JSON array CHECK
- `three_day_topics.status` CHECK
- Topic 내 rank UNIQUE
- 대표 기사 partial UNIQUE index
- `finished_at >= started_at` CHECK

실제 migration 적용 전 schema 검토에서 필요성을 다시 판단한다. 추가할 경우 migration만 독립적으로 바꾸지 않고 repository와 테스트를 함께 수정한다.

### Rejected: `reference_date`를 결과 교체 key로 사용

`reference_date`는 서울 기준 달력 날짜로, 절대 실행 범위를 유일하게 식별하지 않는다.

같은 날짜에 서로 다른 `window_start`, `window_end`가 존재할 수 있으므로 결과 교체와 advisory lock의 source of truth는 `(window_start, window_end)`로 유지한다.

### Rejected: Dry-run에서 실제 Summary provider를 호출하고 저장만 생략

Dry-run은 DB write뿐 아니라 외부 API 호출, 비용과 네트워크 부수 효과도 없어야 한다.

따라서 `execute=False`에서 실제 Summary provider를 호출하는 방식은 허용하지 않는다.

## Applied Changes

- Dry-run은 후보 조회, clustering, 대표·관련·Summary 근거 기사 선정과 분석
  통계까지만 수행하도록 `build_pipeline()`을 분리했다. `execute=False`에서는
  원문 지연 추출, Summary provider 호출과 repository 결과 교체를 호출하지
  않는다.
- Dry-run에서 `--use-summary-provider` flag가 있어도
  `OPENAI_SUMMARY_API_KEY`를 요구하지 않도록 CLI gate를 조정했다. Execute mode는
  계속 `--use-summary-provider`와 API key를 요구한다.
- `load_candidates_for_context()`를 추가해 후보 조회 read-only connection을
  `load_three_day_candidates()` 구간에만 열고 materialized 결과를 반환하도록
  했다. 원문 확보, Summary provider와 저장 transaction은 이 connection을
  보유하지 않는다.
- `provider`, `model`, `source_text_type`이 문자열인지 `.strip()` 전에
  확인하고 field 이름이 포함된 `ValueError`를 발생시킨다.
- Task, 설계, Architecture, Runbook, PR, devlog에서 결과 교체와 advisory lock
  기준을 절대 `(window_start, window_end)`로 통일했다. `reference_date`는 서울
  기준 표시, archive filter와 운영 조회 metadata로 설명했다.
- `docs/runbooks/database-check.md`의 3일 Topic constraint 확인 query를
  `to_regclass()` 기반으로 바꾸고, 세 table이 모두 존재해야 정상 적용 완료임을
  명시했다.
- `docs README.md` 전체에서 개인 workspace `file` URI와 실제 사용자 절대 경로
  literal을 제거했다.
- 공통 selection helper `_as_utc()`에 `datetime | None` 입력과 반환 타입 힌트를
  추가했다.
- `/three-day-topics/home` 설명을 성공 또는 부분 성공한 최신 72시간 publishable
  window의 경량 Topic card payload로 명확히 했다. API query와 response contract는
  변경하지 않았다.
- Dockerfile 최종 `USER`가 없어 현 image는 non-root 실행을 보장하지 못하는 것을
  확인했다. CronJob은 기존 `allowPrivilegeEscalation: false`, capability drop,
  `RuntimeDefault` seccomp를 유지하고 `/tmp` `emptyDir` mount를 추가했다.
  `runAsNonRoot`와 `readOnlyRootFilesystem`은 image hardening 후 별도 적용으로
  문서화했다.
- 전체 로컬 회귀 테스트, compileall, whitespace와 문서 검색은 통과했다.
  `kubectl apply --dry-run`은 금지 command에 해당하므로 사람이 수행할 항목으로
  남겼다.

## Verification Required

### 3일 Pipeline 및 저장 회귀

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topic_repository.py \
  -v
```

확인 항목:

- Dry-run Summary provider 호출 0회
- Dry-run에서 Summary API key 불필요
- Dry-run에서 결과 교체 transaction 미실행
- Execute mode의 기존 Summary 및 저장 동작 유지
- 후보 조회 connection 조기 반환
- 72시간 context와 통계 유지
- 절대 window 기반 원자 교체 계약 유지

### 설정 검증 및 공통 Selection 회귀

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline.py \
  tests/test_daily_topic_article_selection.py \
  tests/test_run_daily_topic_pipeline.py \
  -v
```

확인 항목:

- 비문자열, 빈 문자열과 공백 설정값이 `ValueError`
- `_as_utc()`의 기존 시간 변환 동작 유지
- Daily Topic 기사 선정 및 정렬 회귀 없음

### API 및 CronJob 검증

```bash
python -m pytest \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

CronJob 보안 설정을 변경했다면 다음을 테스트한다.

- `runAsNonRoot`
- `readOnlyRootFilesystem` 적용 여부
- 필요한 `emptyDir` 및 volume mount
- capability drop과 seccomp 유지
- 기존 schedule, command, Secret, resource와 deadline 유지

### 전체 회귀

```bash
python -m pytest
python -m unittest discover -s tests
python -m compileall app scripts tests
git diff --check
```

### 문서 정합성

```bash
rg -n \
  'file://''/|/Users/seo''chanjin|reference_date.*id''empot|id''empot.*reference_date' \
  docs README.md
```

개인 workspace URI와 `reference_date`를 결과 교체 key처럼 설명하는 문구가 없어야 한다.

```bash
rg -n \
  'to_regclass|::regclass|three_day_topic_runs|three_day_topics|three_day_topic_articles' \
  docs/runbooks/database-check.md
```

부분 적용 검사 query에서 존재하지 않을 수 있는 relation을 직접 `::regclass`로 변환하지 않아야 한다.

### Kubernetes client-side dry-run

사람이 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

기대 결과:

```text
cronjob.batch/news-three-day-topic-pipeline created (dry run)
```

### Kubernetes server-side dry-run

최종 manifest 확정 후 사람이 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

실제 migration 적용, K3s apply, 수동 Job 생성과 production API 확인은 Codex가 수행하지 않는다.
