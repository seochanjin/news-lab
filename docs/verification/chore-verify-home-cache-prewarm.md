# Verification: Pipeline 기반 Home Cache Prewarming 운영 검증

## Verification Status

passed

Daily·3-day·Weekly Pipeline 기반 Home Cache Prewarming 운영 검증을 모두 완료했다.

## Verification Scope

- Daily Pipeline이 Home API 요청 없이 `topics:home:v1`을 prewarm하는지 Production 환경에서 검증
- Pipeline Job 완료 여부 확인
- Home API 호출 전 Redis key 존재 여부와 TTL 확인
- Pipeline 로그에서 `event=prewarm` 확인
- Home API 호출 후 TTL이 초기화되지 않고 감소하는지 확인
- Daily·3-day·Weekly Pipeline 모두 동일한 절차로 Production 검증 완료

## Commands Run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get cronjob news-daily-topic-pipeline \
  -n default \
  -o wide
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get pods \
  -n default |
grep news-redis
```

```bash
REDIS_POD=$(
  KUBECONFIG=~/.kube/oci-k3s.yaml \
  kubectl get pods \
    -n default \
    -o name |
  grep '^pod/news-redis-' |
  head -n 1 |
  cut -d/ -f2
)
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl exec \
  -n default \
  "$REDIS_POD" \
  -- redis-cli DEL topics:home:v1
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl exec \
  -n default \
  "$REDIS_POD" \
  -- redis-cli EXISTS topics:home:v1
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl exec \
  -n default \
  "$REDIS_POD" \
  -- redis-cli TTL topics:home:v1
```

```bash
RUN_ID=$(date +%Y%m%d%H%M%S)
DAILY_JOB="news-daily-topic-pipeline-prewarm-${RUN_ID}"

KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl create job \
  --from=cronjob/news-daily-topic-pipeline \
  "$DAILY_JOB" \
  -n default
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl wait \
  --for=condition=complete \
  "job/$DAILY_JOB" \
  -n default \
  --timeout=1800s
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl logs \
  -n default \
  "job/$DAILY_JOB" |
grep -E 'prewarm|cache|db_write_performed|bypass'
```

```bash
curl -sS https://api.newslab.ai.kr/topics/home > /tmp/daily-home.json
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl exec \
  -n default \
  "$REDIS_POD" \
  -- redis-cli TTL topics:home:v1
```

## Results

### Daily Pipeline

- CronJob `news-daily-topic-pipeline`: 정상
- Production image: `seocj/news-api:d18f695854cb82c6a8d2ecd5833a88eb45a6ade2`
- Redis Pod: `Running`, restart 0
- 검증 전 기존 key 상태:
  - `EXISTS topics:home:v1` → `1`
  - `TTL topics:home:v1` → `73084`
- key 삭제 후:
  - `DEL topics:home:v1` → `1`
  - `EXISTS topics:home:v1` → `0`
  - `TTL topics:home:v1` → `-2`
- 수동 Job:
  - `news-daily-topic-pipeline-prewarm-20260715134942`
  - `condition=complete` 성공
- Pipeline 실행 결과:
  - `db_write_performed=true`
  - `saved_topic_count=3`
  - `home_topics_cache event=prewarm key=topics:home:v1 ttl_seconds=108000`
- Home API 호출 전 Redis 확인:
  - `EXISTS topics:home:v1` → `1`
  - `TTL topics:home:v1` → `107913`
- `GET /topics/home` 응답 성공
- API 호출 후 TTL:
  - `107816`
- TTL이 `108000`으로 초기화되지 않고 `107913 → 107816`으로 감소함

**Daily Pipeline-driven prewarm: passed**

### 3-day Pipeline

- 검증 전 기존 key 상태:
  - `EXISTS three-day-topics:home:v1` → `1`
  - `TTL three-day-topics:home:v1` → `75771`
- key 삭제 후:
  - `DEL three-day-topics:home:v1` → `1`
  - `EXISTS three-day-topics:home:v1` → `0`
  - `TTL three-day-topics:home:v1` → `-2`
- 수동 Job:
  - `news-three-day-topic-pipeline-prewarm-20260715140441`
  - `condition=complete` 성공
- Pipeline 실행 결과:
  - `saved_topic_count=5`
  - `failed_topic_count=0`
  - `run_status=success`
  - `home_topics_cache event=prewarm key=three-day-topics:home:v1 ttl_seconds=108000`
- Home API 호출 전 Redis 확인:
  - `EXISTS three-day-topics:home:v1` → `1`
  - `TTL three-day-topics:home:v1` → `107755`
- `GET /three-day-topics/home` 응답 성공
- API 호출 후 TTL:
  - `107642`
- TTL이 `108000`으로 초기화되지 않고 `107755 → 107642`로 감소함

**3-day Pipeline-driven prewarm: passed**

### Weekly Pipeline

- CronJob `news-weekly-topic-pipeline`: 정상
- Production image: `seocj/news-api:d18f695854cb82c6a8d2ecd5833a88eb45a6ade2`
- 검증 전 기존 key 상태:
  - `EXISTS weekly-topics:home:v1` → `1`
  - `TTL weekly-topics:home:v1` → `640641`
- key 삭제 후:
  - `DEL weekly-topics:home:v1` → `1`
  - `EXISTS weekly-topics:home:v1` → `0`
  - `TTL weekly-topics:home:v1` → `-2`
- 수동 Job:
  - `news-weekly-topic-pipeline-prewarm-20260715142651`
  - `condition=complete` 성공
- Pipeline 실행 결과:
  - `saved_topic_count=3`
  - `failed_topic_count=2`
  - `run_status=partial_success`
  - 실패 2건은 OpenAI API 응답 `ReadTimeout`으로 발생
  - `home_topics_cache event=prewarm key=weekly-topics:home:v1 ttl_seconds=691200`
- Home API 호출 전 Redis 확인:
  - 최초 `kubectl exec` 1회에서 Kubernetes API Server TLS handshake timeout 발생
  - 즉시 재시도 후 `EXISTS weekly-topics:home:v1` → `1`
  - `TTL weekly-topics:home:v1` → `689599`
- `GET /weekly-topics/home` 응답 성공
- API 호출 후 TTL:
  - `689411`
- TTL이 `691200`으로 초기화되지 않고 `689599 → 689411`로 감소함

**Weekly Pipeline run: partial_success**

**Weekly Pipeline-driven prewarm: passed**

## Manual or Production Verification

Production 환경에서 사람이 직접 수행한 운영 검증이다.

검증 과정에서 Redis key를 명시적으로 삭제한 뒤 Daily Pipeline Job을 수동 실행했고, Home API를 호출하기 전에 Redis key가 생성된 것을 확인했다. 이후 처음으로 Home API를 호출한 뒤 TTL이 초기화되지 않고 감소하는 것도 확인했다.

따라서 Daily·3-day·Weekly Pipeline에 대해서 다음 경로가 실제 Production 환경에서 성립함을 확인했다.

```
Daily Pipeline
→ PostgreSQL DB write 성공
→ Pipeline prewarm 실행
→ topics:home:v1 생성
→ Home API 호출 전 Redis에 이미 존재
→ 첫 Home API 요청은 기존 prewarmed cache 사용

3-day Pipeline
→ Topic 5개 저장 성공
→ Pipeline prewarm 실행
→ three-day-topics:home:v1 생성
→ Home API 호출 전 Redis에 이미 존재
→ 첫 Home API 요청은 기존 prewarmed cache 사용

Weekly Pipeline
→ 5개 후보 중 3개 Topic 저장 성공, 2개 OpenAI ReadTimeout
→ run_status=partial_success
→ 저장 가능한 결과를 기반으로 Pipeline prewarm 실행
→ weekly-topics:home:v1 생성
→ Home API 호출 전 Redis에 이미 존재
→ 첫 Home API 요청은 기존 prewarmed cache 사용
```

## Pending Verification

없음.

Daily·3-day·Weekly 세 Pipeline에 대한 Production 운영 검증을 모두 완료했다.

## Evidence Notes

- Daily Pipeline Job 시작: `2026-07-15 04:49:55 UTC`
- DB write 완료 후 prewarm 로그: `2026-07-15 04:52:26.820 UTC`
- prewarm 로그:
  - `home_topics_cache event=prewarm key=topics:home:v1 ttl_seconds=108000`
- API 응답의 `generated_at`:
  - `2026-07-15T04:52:26.679173+00:00`
- Pipeline 직후 TTL: `107913`
- 첫 Home API 호출 후 TTL: `107816`
- API 로그에서 별도의 `event=hit` 출력은 확인되지 않았지만, TTL이 재설정되지 않고 감소했으므로 기존 prewarmed key를 사용한 것으로 판단한다.

### 3-day Evidence

- 3-day Pipeline Job 시작: `2026-07-15 05:04:52 UTC`
- prewarm 로그: `2026-07-15 05:09:37.500 UTC`
- prewarm 로그:
  - `home_topics_cache event=prewarm key=three-day-topics:home:v1 ttl_seconds=108000`
- Pipeline 결과:
  - `saved_topic_count=5`
  - `failed_topic_count=0`
  - `run_status=success`
- API 응답의 `generated_at`:
  - `2026-07-15T05:09:37.355686+00:00`
- Pipeline 직후 TTL: `107755`
- 첫 Home API 호출 후 TTL: `107642`
- TTL이 재설정되지 않고 감소했으므로 기존 prewarmed key가 사용된 것으로 판단한다.

### Weekly Evidence

- Weekly Pipeline Job 시작: `2026-07-15 05:27:00 UTC`
- Topic 처리 중 OpenAI API `ReadTimeout` 2건 발생:
  - `topic-0126`
  - `topic-0005`
- Pipeline 결과:
  - `saved_topic_count=3`
  - `failed_topic_count=2`
  - `run_status=partial_success`
- prewarm 로그: `2026-07-15 05:35:21.127 UTC`
- prewarm 로그:
  - `home_topics_cache event=prewarm key=weekly-topics:home:v1 ttl_seconds=691200`
- Pipeline 완료 후 Home API 호출 전:
  - `EXISTS weekly-topics:home:v1` → `1`
  - `TTL weekly-topics:home:v1` → `689599`
- API 응답의 `generated_at`:
  - `2026-07-15T05:35:20.955068+00:00`
- 첫 Home API 호출 후 TTL:
  - `689411`
- TTL이 `689599 → 689411`로 감소했으므로 기존 prewarmed key가 사용된 것으로 판단한다.
- Redis 확인 직전 `kubectl exec`에서 `net/http: TLS handshake timeout`이 1회 발생했으나, 즉시 재시도에 성공했다. 이는 Redis 또는 prewarm 실패가 아니라 Kubernetes API Server 연결 경로의 일시적 handshake timeout으로 기록한다.

현재 상태:

```
Daily Pipeline-driven prewarm: passed
3-day Pipeline-driven prewarm: passed
Weekly Pipeline-driven prewarm: passed
Overall Verification Status: passed
```
