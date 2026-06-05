# Verification: 본문 추출 CronJob 구성

## 검증 범위

- Pre-merge static verification: agent가 로컬 저장소에서 수행.
- Post-merge production verification: PR merge 이후 human operator가 K3s production 환경에서 직접 수행.
- Supabase SQL, DB migration, FastAPI rollout 검증은 이 작업 범위에 포함하지 않음.
- 다음 `03:30 Asia/Seoul` 정기 schedule 자동 실행 확인은 아직 pending.

## Pre-Merge Static Verification

Agent가 PR merge 전에 수행한 정적 검증이다.

### YAML parse check

Command:

```bash
ruby -e 'require "yaml"; ARGV.each { |file| YAML.load_file(file); puts "OK #{file}" }' k8s/news-raw-extractor-cronjob.yaml k8s/news-rss-collector-cronjob.yaml
```

Result:

```text
OK k8s/news-raw-extractor-cronjob.yaml
OK k8s/news-rss-collector-cronjob.yaml
```

### Diff whitespace check

Command:

```bash
git diff --check
```

Result:

```text
No output. Exit code 0.
```

### Scope check

Command:

```bash
git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml
```

Result:

```text
No output. Exit code 0.
```

Meaning:

- FastAPI app code 변경 없음.
- DB file 변경 없음.
- `scripts/extract_raw_articles.py` 변경 없음.
- 기존 `k8s/news-rss-collector-cronjob.yaml` 변경 없음.

## Post-Merge Production Verification

Status: Completed for manual production verification.

Performed by: human operator.

Agent는 아래 `kubectl apply`, manual Job 생성, production `curl` 검증 명령을 실행하지 않았다. 이 섹션은 human operator가 제공한 실제 운영 검증 로그를 기록한 것이다.

### 1. K3s node 확인

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
```

Result:

```text
NAME              STATUS   ROLES           AGE   VERSION
arm-master-node   Ready    control-plane   11d   v1.35.5+k3s1
arm-worker-node   Ready    worker          11d   v1.35.5+k3s1
```

### 2. Initial relative path error

처음에는 home directory에서 실행해 relative path 오류가 발생했다.

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-raw-extractor-cronjob.yaml
```

Result:

```text
error: the path "k8s/news-raw-extractor-cronjob.yaml" does not exist
```

Resolution:

```bash
cd workspace
cd news-lab
```

### 3. CronJob apply

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-raw-extractor-cronjob.yaml
```

Result:

```text
cronjob.batch/news-raw-extractor created
```

### 4. CronJob 확인

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor
```

Result:

```text
NAME                 SCHEDULE     TIMEZONE     SUSPEND   ACTIVE   LAST SCHEDULE   AGE
news-raw-extractor   30 3 * * *   Asia/Seoul   False     0        <none>          29s
```

Later result:

```text
NAME                 SCHEDULE     TIMEZONE     SUSPEND   ACTIVE   LAST SCHEDULE   AGE
news-raw-extractor   30 3 * * *   Asia/Seoul   False     0        <none>          4m28s
```

### 5. Manual Job 생성

Command:

```bash
JOB_NAME=news-raw-extractor-manual-$(date +%s)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-raw-extractor \
  $JOB_NAME
```

Result:

```text
job.batch/news-raw-extractor-manual-1780629604 created
```

### 6. Manual Job pod 확인

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME
```

Result:

```text
NAME                                         READY   STATUS    RESTARTS   AGE
news-raw-extractor-manual-1780629604-cszhh   1/1     Running   0          6s
```

Watch result:

```text
NAME                                         READY   STATUS      RESTARTS   AGE
news-raw-extractor-manual-1780629604-cszhh   0/1     Completed   0          19s
```

### 7. Manual Job logs

Command:

```bash
POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME
```

Result:

```text
extraction run started: 2
target articles: 5
extracting article_id=109: Meta’s Oversight Board says account bans lack due process, transparency
success article_id=109, length=6980
extracting article_id=110: Meta rolls out a new AI creator assistant on Facebook
success article_id=110, length=3484
extracting article_id=111: What to expect from WWDC 2026: Siri’s highly anticipated revamp and Apple Intelligence updates
success article_id=111, length=4423
extracting article_id=112: A burglar used a Waymo to steal yoga clothes in San Francisco — and got away with it
success article_id=112, length=1851
extracting article_id=113: Cash App launches a wand for tap-and-pay
success article_id=113, length=3326
done
success: 5
failed: 0
```

### 8. `/extractor/status` 확인

Command:

```bash
curl https://api.dev-scj.site/extractor/status
```

Result:

```json
{"status":"success","latest_run":{"id":2,"started_at":"2026-06-05T03:20:11.185510+00:00","finished_at":"2026-06-05T03:20:17.291480+00:00","status":"success","success_count":5,"failed_count":0,"error_message":null,"created_at":"2026-06-05T03:20:11.185510+00:00"}}
```

### 9. `/extractor/runs?limit=5` 확인

Command:

```bash
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

Result:

```json
{"count":2,"runs":[{"id":2,"started_at":"2026-06-05T03:20:11.185510+00:00","finished_at":"2026-06-05T03:20:17.291480+00:00","status":"success","success_count":5,"failed_count":0,"error_message":null,"created_at":"2026-06-05T03:20:11.185510+00:00"},{"id":1,"started_at":"2026-06-04T09:49:23.792580+00:00","finished_at":"2026-06-04T09:49:29.129705+00:00","status":"success","success_count":5,"failed_count":0,"error_message":null,"created_at":"2026-06-04T09:49:23.792580+00:00"}]}
```

### 10. Manual Job 삭제

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME
```

Result:

```text
job.batch "news-raw-extractor-manual-1780629604" deleted from default namespace
```

### 11. Job cleanup 확인

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs
```

Result:

```text
NAME                          STATUS     COMPLETIONS   DURATION   AGE
news-rss-collector-29673720   Complete   1/1           13s        2d9h
news-rss-collector-29675160   Complete   1/1           11s        33h
news-rss-collector-29676600   Complete   1/1           26s        9h
```

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs | grep raw-extractor
```

Result:

```text
No output.
```

## 최종 확인 결과

- CronJob apply 성공: `cronjob.batch/news-raw-extractor created`.
- CronJob schedule 확인: `30 3 * * *`.
- CronJob timezone 확인: `Asia/Seoul`.
- CronJob `SUSPEND` 상태 확인: `False`.
- CronJob 기반 manual Job 생성 성공: `news-raw-extractor-manual-1780629604`.
- Manual Job pod 상태 확인: `Running` 이후 `Completed`.
- Pod logs에서 extractor 실행 확인.
- Extractor run `id=2` 생성 확인.
- `target articles: 5`.
- `success_count=5`.
- `failed_count=0`.
- `/extractor/status`에서 latest run `id=2`, `status=success` 확인.
- `/extractor/runs?limit=5`에서 run `id=2` 포함 확인.
- Manual Job cleanup 완료.
- cleanup 이후 `kubectl get jobs | grep raw-extractor` 출력 없음.

## Pending Verification

- 다음 `03:30 Asia/Seoul` 정기 schedule에서 CronJob이 자동 실행되는지 확인 필요.
