# Approved Fixes: Home API 부하 측정 및 Redis Cache 적용

## Approved Fixes

이번 fix는 Redis 기능을 확장하는 작업이 아니라, Task 70의 immutable image 정책과 현재 테스트·문서 사이의 정합성을 복구하는 작업이다.

Redis 변경 전 기준 commit `15c686ef`의 별도 worktree에서도 동일한 세 CronJob manifest test가 실패했다.

```
406 passed
3 failed
78 subtests passed
```

세 실패는 모두 실제 manifest가 `seocj/news-api:<40자리 full Git SHA>`를 사용하는 반면 테스트가 `seocj/news-api:latest`를 고정 기대해서 발생했다. 따라서 Redis 구현으로 생긴 회귀가 아니라 immutable image 전환 이후 남아 있던 stale test expectation으로 확정한다.

- [x] FIX-01: Daily Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-02: Three-day Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-03: Weekly Topic Pipeline CronJob image assertion을 immutable SHA 정책에 맞게 수정
- [x] FIX-04: 특정 현재 SHA를 하드코딩하지 않고 full Git SHA 형식과 workload image 정합성을 검증
- [x] FIX-05: Task의 Implementation Units를 parser 호환 형식으로 정리
- [x] FIX-06: Verification에 기준 worktree 재현 결과와 fix 이후 전체 test 결과를 반영

FIX-01~FIX-03의 기존 assertion:

```python
self.assertEqual(self.container["image"], "seocj/news-api:latest")
```

수정 원칙:

```python
self.assertRegex(
    self.container["image"],
    r"^seocj/news-api:[0-9a-f]{40}$",
)
```

가능하면 각 CronJob image가 Backend Deployment 또는 동일한 기준 manifest의 image와 일치하는지도 함께 검증한다. 단, 현재 SHA 값 자체를 test에 하드코딩하지 않는다.

FIX-05 적용 후 `Implementation Units`는 하위 bullet 없이 다음 형식만 유지한다.

```markdown
## Implementation Units

- [x] UNIT-01: 현재 조회 구조와 Cache 적합성 조사
- [ ] UNIT-02: Redis 적용 전 Baseline 부하 테스트
- [x] UNIT-03: Cache 정책 설계
- [x] UNIT-04: Redis와 Cache-aside 구현
- [ ] UNIT-05: Unit/Integration Test
- [ ] UNIT-06: K3s와 운영 설정 반영
- [ ] UNIT-07: Redis 적용 후 부하 테스트와 비교
- [ ] UNIT-08: Redis 장애·복구 검증 및 최종 문서화
```

UNIT-05는 전체 test suite가 `0 failed`로 확인된 뒤에만 `[x]`로 변경한다. UNIT-02, UNIT-06~UNIT-08은 이번 fix에서 완료 처리하지 않는다.

## Rejected or Deferred Suggestions

- **CronJob manifest를 다시 `latest`로 되돌리기**: 거절한다. Task 70에서 확정한 immutable full Git SHA 운영 정책을 위반한다.
- **현재 SHA `7636ee0db92d8fcbf2111688febea2e90edf54a1`를 test에 직접 하드코딩하기**: 거절한다. 다음 manifest image 갱신 PR에서 동일한 문제가 재발한다.
- **세 실패를 Redis 구현 회귀로 분류하기**: 거절한다. 기준 commit `15c686ef`에서도 동일하게 재현됐다.
- **CronJob schedule, command, Secret, securityContext 또는 resource 값을 함께 변경하기**: 거절한다. 이번 fix는 image assertion 정합성만 다룬다.
- **Redis 코드, Cache 정책 또는 K8s Redis manifest 추가 수정**: 연기한다. 해당 변경은 별도 review와 후속 UNIT에서 검토한다.
- **UNIT-02 Baseline 성능 측정과 production 배포를 이번 codex-fix에서 수행하기**: 연기한다. `k6` 실행 환경 준비와 사람 승인 후 별도로 진행한다.
- **Production 명령 실행**: 거절한다. Argo CD Sync, `kubectl apply/delete/patch/edit/rollout`, Redis 장애 주입과 production 부하 테스트는 사람이 수행한다.

## Applied Changes

- FIX-01~FIX-03: 세 CronJob manifest test의 image assertion을
  `seocj/news-api:latest` 고정 기대값에서
  `^seocj/news-api:[0-9a-f]{40}$` full Git SHA 형식 검증으로 변경했다.
- FIX-04: 세 CronJob image가 `k8s/news-api.yaml`의 Backend Deployment image와
  일치하는지 검증해 특정 현재 SHA를 test에 하드코딩하지 않도록 했다.
- FIX-05: `docs/tasks/feature-home-api-redis-cache.md`의
  `Implementation Units`를 하위 bullet 없는 parser 호환 checklist 형식으로
  정리했다. 전체 test suite가 `0 failed`로 통과해 UNIT-05만 추가 완료
  처리했고, UNIT-02와 UNIT-06~UNIT-08은 미완료로 유지했다.
- FIX-06: `docs/verification/feature-home-api-redis-cache.md`에 기준 worktree
  재현 결과와 fix 이후 대상 test 및 전체 test 결과를 기록했다.

수정 허용 범위:

```
tests/test_daily_topic_pipeline_cronjob_manifest.py
tests/test_three_day_topic_pipeline_cronjob_manifest.py
tests/test_weekly_topic_pipeline_cronjob_manifest.py
docs/tasks/feature-home-api-redis-cache.md
docs/fixes/feature-home-api-redis-cache-approved-fixes.md
docs/verification/feature-home-api-redis-cache.md
```

필요한 경우 test helper 중복 제거를 위한 기존 공통 test utility 파일은 최소 범위에서 수정할 수 있다. 신규 application module은 만들지 않는다.

다음 영역은 변경하지 않는다.

```
app/
k8s/
load-tests/
requirements.txt
db/
migrations/
frontend/
.github/workflows/
scripts/
docker-compose.yml
```

FIX 체크박스는 실제 수정과 검증이 완료된 경우에만 `[x]`로 변경한다.

## Verification Required

### 기존 stale expectation 제거 확인

```bash
rg -n 'seocj/news-api:latest' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

기대 결과: 출력 없음.

### Immutable image assertion 확인

```bash
rg -n \
  'assertRegex|[0-9a-f].*40|news-api' \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

확인 조건:

- `seocj/news-api:` repository prefix를 검증한다.
- tag가 40자리 lowercase hexadecimal SHA인지 검증한다.
- 특정 SHA 값에 test가 결합되지 않는다.
- 가능하면 Backend workload image 일치도 함께 검증한다.

### 대상 test 확인

```bash
PYTHONPATH=. pytest -q \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  tests/test_weekly_topic_pipeline_cronjob_manifest.py
```

기대 결과: `0 failed`.

### 전체 test 확인

```bash
PYTHONPATH=. pytest -q
```

기대 결과:

- `0 failed`
- 기존 Redis cache 관련 13개 test 포함 전체 suite 통과
- 실제 passed 및 subtests 수를 Verification에 기록

### Task parser 형식 확인

```bash
awk '
  /^## Implementation Units/ { in_units=1; next }
  in_units && /^## / { in_units=0 }
  in_units && NF { print }
' docs/tasks/feature-home-api-redis-cache.md
```

확인 조건:

- 모든 UNIT 줄이 `- [ ] UNIT-NN: 설명` 또는 `- [x] UNIT-NN: 설명` 형식이다.
- UNIT 아래에 중첩 bullet이나 설명 문단이 없다.
- UNIT-02와 UNIT-06~UNIT-08은 미완료 상태다.
- UNIT-05는 전체 test 통과 후에만 완료 상태다.

### K8s와 application code 미변경 확인

```bash
git diff --name-only -- \
  app k8s load-tests requirements.txt db migrations frontend \
  .github/workflows scripts docker-compose.yml
```

기대 결과: 이번 fix로 발생한 신규 변경 없음.

기존 Redis 구현 변경이 이미 working tree에 존재하므로, `git diff` 전체가 아니라 codex-fix 실행 전후의 추가 변경 범위를 기준으로 판단한다.

### 정적 검증

```bash
git diff --check
```

기대 결과: exit code 0.

### Verification 문서 확인

Verification에는 다음을 명시한다.

- 기준 commit: `15c686ef`
- 기준 worktree에서 `406 passed, 3 failed, 78 subtests passed`
- 세 실패가 모두 stale `latest` assertion이었음
- fix 이후 대상 test 결과
- fix 이후 전체 test 결과
- UNIT-02 성능 Baseline, K3s 반영, production 장애 검증은 계속 pending임
