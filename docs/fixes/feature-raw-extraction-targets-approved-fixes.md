# Approved Fixes: Topic 대표 후보 기반 raw extraction 대상 선정

## Approved Fixes

Antigravity review 결과, 현재 `feature/raw-extraction-targets` 브랜치는 요구 범위와 운영 안전성은 대체로 충족하지만 PR 전 반드시 보완해야 할 문제가 확인되었다.

이번 fix에서는 아래 3개 항목을 승인한다.

### 1. Topic 내부 article 정렬 보장

현재 `app/utils/raw_extraction_targets.py`의 `_select_topic_targets()`는 `topic["articles"]` 입력 순서를 그대로 순회한다.

이 구조에서는 `representative_candidate_rank`가 낮은 후보가 먼저 순회될 경우, rank 1 후보보다 먼저 extraction target 한도를 소진할 수 있다.

승인된 수정:

- target 선정 전 topic article 목록을 `representative_candidate_rank` 기준으로 정렬한다.
- rank가 있는 article은 rank 오름차순으로 먼저 배치한다.
- rank가 `None`인 article은 뒤로 배치한다.
- 동일 rank 또는 rank 없는 article의 안정적인 정렬을 위해 article id 등 deterministic tie-breaker를 사용한다.
- target/backup/skipped 판정은 정렬된 순서를 기준으로 수행한다.

목표:

- 입력 article 순서와 무관하게 rank 1 후보가 rank 2 후보보다 먼저 target 후보로 평가되어야 한다.
- `--max-targets-per-topic 1`에서 rank 1 후보가 eligible이면 rank 1이 target이 되어야 한다.
- `--max-targets-per-topic 2`에서 rank 1, rank 2 후보가 eligible이면 두 후보가 target이 되어야 한다.

### 2. 정렬 보장 단위 테스트 추가

현재 unit test에는 representative candidate 목록이 뒤섞인 경우에도 rank 기준 target 선정이 보장되는지 검증하는 테스트가 부족하다.

승인된 수정:

- `tests/test_raw_extraction_targets.py`에 article 입력 순서가 rank 순서와 다른 케이스를 추가한다.
- 예시:
  - 입력 순서: rank 2 후보 → rank 1 후보
  - `max_targets_per_topic=1`
  - 기대 결과: rank 1 후보가 `target`, rank 2 후보가 `backup`
- 필요하다면 rank 없는 non-candidate article이 뒤로 밀리고 `skipped` 처리되는지도 함께 검증한다.
- focused unittest와 full unittest에서 새 테스트가 통과해야 한다.

목표:

- target 선정 로직이 입력 순서에 의존하지 않는다는 것을 테스트로 보장한다.

### 3. deterministic report 및 max2 비교 report 경고 문구 추가

현재 report에는 embedding provider/model이 `deterministic / deterministic-hash-v1`로 표시되지만, 해당 report가 검증용 산출물이며 실제 extraction 승인 목록이 아니라는 문구가 부족하다.

deterministic report는 topic 품질이 낮을 수 있으며, 현재 샘플에서도 관련 없는 기사들이 같은 topic으로 묶이는 사례가 확인되었다.

승인된 수정:

- `render_raw_extraction_target_report()`에서 report 상단에 warning/disclaimer 섹션을 추가한다.
- deterministic provider 사용 시 다음 내용을 명시한다.
  - 이 report는 deterministic-hash-v1 기반 검증용 산출물이다.
  - 현재 target 목록은 실제 raw extraction 승인 목록이 아니다.
  - 실제 extraction 대상 검토는 human-approved embedding provider 결과를 기준으로 수행해야 한다.
- `max_targets_per_topic > 1`인 report에는 다음 내용을 명시한다.
  - 이 report는 복수 target 정책 비교용 산출물이다.
  - max2/max3 결과가 곧바로 실제 extraction 실행 승인을 의미하지 않는다.
- report의 `Human review status`는 계속 `Pending`으로 유지한다.

목표:

- deterministic report 또는 max2 비교 report가 실제 운영 승인 목록으로 오해되지 않게 한다.
- 후속 34차에서 실제 extraction 실행 전 human approval이 필요함을 명확히 한다.

## Rejected or Deferred Suggestions

Antigravity review의 optional improvement는 이번 fix 범위에서 제외한다.

### CLI 실행 경로/출력 경로 제한 개선

리뷰에서는 `scripts/analyze_raw_extraction_targets.py` 실행 시 report path가 일반적으로 `docs/reports/` 하위로 설정되므로, 출력 경로 예외 처리를 더 정교하게 할 수 있다고 제안했다.

이번 차수에서는 다음 이유로 보류한다.

- 현재 task의 핵심 결함은 target 선정 정렬 보장과 report 오용 방지다.
- report path는 사용자가 명시적으로 지정하는 CLI 옵션이며, 현재 구현은 임의 경로를 허용해도 production 영향이 없다.
- 경로 제한 정책은 후속 CLI hardening 작업에서 별도 차수로 다루는 것이 적절하다.

따라서 이번 fix에서는 report path 제한/검증 로직을 추가하지 않는다.

## Applied Changes

적용 완료.

### Fix 1. Topic 내부 article 정렬 보장

- `_select_topic_targets()`가 target 판정 전에 article을 representative
  candidate rank 오름차순으로 정렬하도록 변경했다.
- rank가 없는 article은 rank 후보 뒤로 배치하고 article id를 deterministic
  tie-breaker로 사용한다.
- 입력 순서와 무관하게 eligible rank 1 후보가 rank 2 후보보다 먼저 target
  한도를 사용한다.

### Fix 2. 정렬 보장 단위 테스트 추가

- rank 2, rank 없는 article, rank 1 순으로 뒤섞인 입력에서 rank 1이
  `target`, rank 2가 `backup`, rank 없는 article이 `skipped`가 되는
  테스트를 추가했다.
- 기존 상태 테스트의 기대 순서를 승인된 rank 우선 정렬 결과에 맞췄다.

### Fix 3. deterministic/max2 report 경고 추가

- deterministic report 상단에 검증용 산출물, 실제 extraction 승인 목록이
  아님, human-approved embedding provider 결과 기준 검토 필요 경고를
  추가했다.
- `max_targets_per_topic > 1` report에 comparison/비교용 산출물이며 실제
  extraction 실행 승인이 아니라는 경고를 추가했다.
- 기본 report와 max2 report를 read-only deterministic 명령으로
  재생성했다.

### Intentionally Not Changed

- Rejected/deferred report path 제한 개선
- API route, DB migration/schema, Kubernetes/CronJob manifest, frontend
- raw extraction 실행 스크립트 동작 정책
- topic grouping similarity algorithm, representative score weight
- OpenAI provider 기본 동작

## Verification Required

fix 적용 후 아래 검증을 다시 수행한다.

```bash
git status --short --branch
git diff --stat
git diff --check
```

```bash
.venv/bin/python -m py_compile \
  app/utils/topic_grouping.py \
  app/utils/topic_representatives.py \
  app/utils/raw_extraction_targets.py \
  scripts/analyze_raw_extraction_targets.py
```

```bash
.venv/bin/python -m unittest \
  tests.test_raw_extraction_targets \
  tests.test_analyze_raw_extraction_targets \
  -v
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py --help
```

기본 report 재생성:

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --report-path docs/reports/feature-raw-extraction-targets.md \
  --dry-run
```

max2 비교 report 재생성:

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 2 \
  --report-path docs/reports/feature-raw-extraction-targets-max2.md \
  --dry-run
```

report warning 확인:

```bash
rg -n "검증용|승인 목록|comparison|비교용|human-approved|deterministic-hash-v1" \
  docs/reports/feature-raw-extraction-targets*.md
```

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db tests docs
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

pytest가 설치되어 있다면 실행한다.

```bash
pytest
```

설치되어 있지 않다면 설치하지 않고 verification에 `pending`으로 기록한다.

검증 결과에서 반드시 확인할 사항:

- rank가 뒤섞인 입력에서도 rank 1 후보가 먼저 target으로 선정된다.
- deterministic report에 검증용/비승인 목록 경고가 포함된다.
- max2 report에 비교용/비승인 목록 경고가 포함된다.
- DB write performed는 계속 `false`다.
- raw extraction performed는 계속 `false`다.
- OpenAI provider는 자동 호출되지 않는다.
- API, DB schema, K8s, CronJob, frontend 변경이 없다.
