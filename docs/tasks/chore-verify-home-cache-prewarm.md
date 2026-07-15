# Task: Pipeline 기반 Home Cache Prewarming 운영 검증

## Goal

Daily·3-day·Weekly Topic Pipeline이 PostgreSQL 저장 성공 후 Home API 요청 없이
대응 Redis cache key를 prewarm하는지 Production 환경에서 검증한다.

72차 운영 검증에서는 Home API 호출 후 Redis key를 확인했기 때문에,
key가 Pipeline prewarm으로 생성됐는지 API cache-aside로 생성됐는지 구분하지
못했다.

이번 작업에서는 각 cache key를 삭제한 뒤 대응 Pipeline을 실행하고,
Home API를 호출하기 전에 Redis key와 TTL이 생성되는지 확인한다.

## Scope

- Daily Pipeline prewarm 운영 검증
- 3-day Pipeline prewarm 운영 검증
- Weekly Pipeline prewarm 운영 검증
- Pipeline Job 완료 상태 및 로그 확인
- Home API 호출 전 Redis `EXISTS` / `TTL` 확인
- Home API 호출 후 TTL이 재설정되지 않고 감소하는지 확인
- 실제 운영 검증 결과 문서화

검증 순서는 다음과 같다.

1. Daily
2. 3-day
3. Weekly

각 Pipeline은 이전 단계의 검증이 완료된 뒤 하나씩 실행한다.

## Do not change

- Application code
- Redis cache 구현
- Pipeline 구현
- Kubernetes Deployment/CronJob manifest
- CronJob schedule 또는 command
- DB schema 및 migration
- Frontend
- Argo CD Application 설정
- Secret 및 credential

운영 검증 중 결함이 발견되면 이번 task에서 즉시 수정하지 않고 별도 fix task로
분리한다.

## Expected files

- `docs/tasks/chore-verify-home-cache-prewarm.md`
- `docs/verification/chore-verify-home-cache-prewarm.md`

필요한 경우 기존 72차 운영 Verification 문서의
`Pipeline-driven prewarm: pending` 상태를 실제 검증 결과에 맞게 후속 갱신한다.

## DB changes

없음.

단, 수동 Pipeline 실행 자체는 기존 Production 데이터 생성·저장 로직을 수행할 수
있으며 AI API 호출 비용이 발생할 수 있다.

DB schema 또는 migration 변경은 하지 않는다.

## API changes

없음.

기존 API를 운영 검증에만 사용한다.

- `GET /health`
- `GET /topics/home`
- `GET /three-day-topics/home`
- `GET /weekly-topics/home`

## Test commands

코드 테스트는 새로 수행하지 않는다.

72차 구현 단계에서 다음 검증을 이미 통과했다.

- 전체 테스트: `445 passed, 91 subtests passed`
- 세 cache 통합 테스트: `1 passed`
- Kubernetes YAML parse 통과
- `git diff --check` 통과

이번 작업은 Production 운영 검증 명령과 실제 결과를 Verification 문서에 기록한다.

## Acceptance criteria

각 Pipeline에 대해 다음 조건을 확인한다.

### Daily

- `topics:home:v1` 삭제 후 Daily Pipeline 실행
- Pipeline Job 성공
- Home API 호출 전에 `EXISTS=1`
- TTL이 약 `108000`초 범위
- Pipeline 로그에서 prewarm 경로 확인
- 이후 `/topics/home` 호출 성공
- API 호출 후 TTL이 초기화되지 않고 감소

### 3-day

- `three-day-topics:home:v1` 삭제 후 3-day Pipeline 실행
- Pipeline Job 성공
- publishable 결과가 생성된 경우 Home API 호출 전에 `EXISTS=1`
- TTL이 약 `108000`초 범위
- Pipeline 로그에서 prewarm 경로 확인
- 이후 `/three-day-topics/home` 호출 성공
- API 호출 후 TTL이 초기화되지 않고 감소

### Weekly

- `weekly-topics:home:v1` 삭제 후 Weekly Pipeline 실행
- Pipeline Job 성공
- publishable 결과가 생성된 경우 Home API 호출 전에 `EXISTS=1`
- TTL이 약 `691200`초 범위
- Pipeline 로그에서 prewarm 경로 확인
- 이후 `/weekly-topics/home` 호출 성공
- API 호출 후 TTL이 초기화되지 않고 감소

최종 상태를 다음과 같이 판단한다.

- Production deployment: passed
- Redis connectivity: passed
- Home API cache-aside: passed
- Pipeline-driven prewarm: passed 또는 실제 결과에 따른 명시적 실패 사유 기록

## Notes

- Production mutation이 포함된 human-controlled 운영 검증이다.
- Redis key 삭제와 Pipeline Job 실행은 사람이 직접 수행한다.
- 세 Pipeline을 동시에 실행하지 않는다.
- 각 단계의 실제 명령 출력과 로그를 다음 단계 진행 전에 확인한다.
- Redis key 삭제 후 Home API를 먼저 호출하면 prewarm 검증이 무효가 되므로
  반드시 Pipeline 실행과 key 확인이 끝날 때까지 대응 Home API를 호출하지 않는다.
- 3-day와 Weekly는 저장 가능한 publishable 결과가 없으면 key가 생성되지 않는 것이
  정상일 수 있으므로 Pipeline 실행 결과를 함께 확인한다.
- 운영 검증 중 Application 또는 Infrastructure 결함이 발견되면 별도 task로 분리한다.

## Implementation Units

없음.

이번 작업은 코드 구현이 아니라 human-controlled Production 운영 검증이다.
