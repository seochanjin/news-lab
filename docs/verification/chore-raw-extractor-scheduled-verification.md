# Verification: raw extractor CronJob scheduled run 검증

## Verification Scope

- Production K3s cluster에서 `news-raw-extractor` CronJob이 manual Job이 아니라 정기 schedule에 의해 자동 실행되었는지 확인했다.
- CronJob registration, scheduled Job, scheduled Pod, extractor run API 결과를 확인했다.
- Supabase Table Editor에서 raw article 원문 5개가 저장된 것도 별도로 확인했다.
- No Kubernetes manifest apply, rollout, Supabase SQL, data-writing script, or manual Job creation was run in this verification.
- This verification uses read-only production checks only.

## Commands Run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs | grep raw-extractor
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods | grep raw-extractor
```

```bash
curl https://api.dev-scj.site/extractor/status
```

```bash
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

## Results

### CronJob Schedule Check

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor
```

Result:

```text
NAME                 SCHEDULE     TIMEZONE     SUSPEND   ACTIVE   LAST SCHEDULE   AGE
news-raw-extractor   30 3 * * *   Asia/Seoul   False     0        11h             26h
```

Confirmed:

- CronJob exists.
- Schedule is `30 3 * * *`.
- Timezone is `Asia/Seoul`.
- `SUSPEND=False`.
- `ACTIVE=0`.
- `LAST SCHEDULE=11h`, so the CronJob has run through its scheduled trigger.

### Scheduled Job Check

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs | grep raw-extractor
```

Result:

```text
news-raw-extractor-29678070   Complete   1/1           15s        11h
```

Confirmed:

- A scheduled Job was created by the CronJob.
- Job name: `news-raw-extractor-29678070`.
- Job status: `Complete`.
- Completions: `1/1`.
- Duration: `15s`.
- Age: `11h`.

### Scheduled Pod Check

Command:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods | grep raw-extractor
```

Result:

```text
news-raw-extractor-29678070-q9ptj   0/1     Completed   0          11h
```

Confirmed:

- Scheduled Job Pod was created.
- Pod name: `news-raw-extractor-29678070-q9ptj`.
- Pod status: `Completed`.
- Restart count: `0`.
- Age: `11h`.

### Extractor Status API Check

Command:

```bash
curl https://api.dev-scj.site/extractor/status
```

Result:

```json
{
  "status": "success",
  "latest_run": {
    "id": 3,
    "started_at": "2026-06-05T18:30:06.229196+00:00",
    "finished_at": "2026-06-05T18:30:12.261014+00:00",
    "status": "success",
    "success_count": 5,
    "failed_count": 0,
    "error_message": null,
    "created_at": "2026-06-05T18:30:06.229196+00:00"
  }
}
```

Confirmed:

- Latest extractor run is `id=3`.
- Latest run status is `success`.
- `success_count=5`.
- `failed_count=0`.
- The run started at `2026-06-05T18:30:06.229196+00:00`, which corresponds to `2026-06-06 03:30:06 Asia/Seoul`.
- This matches the CronJob schedule `30 3 * * *` with timezone `Asia/Seoul`.

### Extractor Runs API Check

Command:

```bash
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

Result:

```json
{
  "count": 3,
  "runs": [
    {
      "id": 3,
      "started_at": "2026-06-05T18:30:06.229196+00:00",
      "finished_at": "2026-06-05T18:30:12.261014+00:00",
      "status": "success",
      "success_count": 5,
      "failed_count": 0,
      "error_message": null,
      "created_at": "2026-06-05T18:30:06.229196+00:00"
    },
    {
      "id": 2,
      "started_at": "2026-06-05T03:20:11.185510+00:00",
      "finished_at": "2026-06-05T03:20:17.291480+00:00",
      "status": "success",
      "success_count": 5,
      "failed_count": 0,
      "error_message": null,
      "created_at": "2026-06-05T03:20:11.185510+00:00"
    },
    {
      "id": 1,
      "started_at": "2026-06-04T09:49:23.792580+00:00",
      "finished_at": "2026-06-04T09:49:29.129705+00:00",
      "status": "success",
      "success_count": 5,
      "failed_count": 0,
      "error_message": null,
      "created_at": "2026-06-04T09:49:23.792580+00:00"
    }
  ]
}
```

Confirmed:

- `/extractor/runs?limit=5` includes scheduled run `id=3`.
- Run `id=3` is newer than the previous manual verification run `id=2`.
- Run `id=3` completed successfully with `success_count=5`, `failed_count=0`.

### Supabase Raw Article Check

Supabase Table Editor에서 raw article 원문 저장 상태를 확인했다.

Confirmed:

- Raw article original text records: `5`.
- This matches extractor run `id=3` result: `success_count=5`, `failed_count=0`.

## Manual or Production Verification

Status: Completed.

Production read-only verification was performed manually by the human operator.

No production write operation was performed during this verification.

Not run:

- `kubectl apply`
- `kubectl rollout`
- manual Job creation
- Supabase SQL
- data-writing script
- secret update
- DB migration
- deployment restart

## Pending Verification

None for scheduled run verification.

The pending scheduled execution check from the raw extractor CronJob task is now closed.

## Evidence Notes

- CronJob `LAST SCHEDULE=11h` confirms the CronJob was triggered by schedule.
- Scheduled Job `news-raw-extractor-29678070` completed successfully.
- Scheduled Pod `news-raw-extractor-29678070-q9ptj` completed with `RESTARTS=0`.
- API latest run `id=3` started at `2026-06-05T18:30:06+00:00`, which corresponds to `2026-06-06 03:30:06 Asia/Seoul`.
- This timestamp matches the configured CronJob schedule `30 3 * * *` and timezone `Asia/Seoul`.
- `/extractor/status` and `/extractor/runs?limit=5` both confirm successful scheduled extraction.
- Supabase raw article table check confirmed that 5 original text records exist.

## Static Documentation Validation

```bash
git diff --check
```

No output. Exit code 0.

```bash
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

No output. Exit code 0.

Confirmed no app, DB, K8s manifest, collector script, or extractor script changes.
