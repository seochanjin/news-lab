# Verification: Home Cache Prewarming 운영 이미지 갱신 및 검증

## Production Verification

### Deployment

- Argo CD Application: `news-api`
- Synced revision: `8c31ac45b7b48c1f0f715b394a17cb5e95f6fd75`
- Backend image:
  `seocj/news-api:d18f695854cb82c6a8d2ecd5833a88eb45a6ade2`
- Argo CD sync status: `Synced`
- Argo CD health status: `Healthy`
- `Deployment/news-api` rollout: passed
- API Pods: 2/2 Running, restart 0

### Redis

- `Deployment/news-redis`: 1/1 Available
- Redis Pod: Running, restart 0
- `redis-cli PING`: `PONG`

### Cache Keys

- `topics:home:v1`
  - EXISTS: 1
  - TTL: 107814
- `three-day-topics:home:v1`
  - EXISTS: 1
  - TTL: 107822
- `weekly-topics:home:v1`
  - EXISTS: 1
  - TTL: 691026

TTL 값은 각 정책값인 108000, 108000, 691200보다 실행 경과 시간만큼
감소한 정상 범위다.

### API Smoke Test

- `GET /health`: passed
- `GET /topics/home`: passed
- `GET /three-day-topics/home`: passed
- `GET /weekly-topics/home`: passed

### Job Safety Check

- Argo CD Sync 시 새 Pipeline Job이 생성되지 않았다.
- 기존 최근 Job은 모두 정규 CronJob 실행 이력이다.

### Remaining Verification

- Pipeline-driven prewarm: pending
- 이번 검증은 API 요청 후 Redis key를 확인했으므로 API cache-aside 동작은
  검증됐지만, Pipeline이 API 요청 없이 key를 생성했다는 사실까지는 증명하지
  않았다.
