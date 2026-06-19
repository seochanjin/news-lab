# CronJob 운영

[Runbook index로 돌아가기](../RUNBOOK.md)

## 현재 schedule

| CronJob | Schedule | Entry point |
| --- | --- | --- |
| `news-rss-collector` | `03:00 Asia/Seoul` | `scripts/collect_rss.py` |
| `news-raw-extractor` | `03:30 Asia/Seoul` | `scripts/extract_raw_articles.py` |
| `news-daily-topic-pipeline` | `04:00 Asia/Seoul` | `scripts/run_daily_topic_pipeline.py` |

Manifest의 값이 source of truth다. Schedule 변경은 별도 task와 사람의 apply가
필요하다.

## Read-only 상태 확인

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs \
  --sort-by=.metadata.creationTimestamp
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-rss-collector
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-raw-extractor
```

Human operator가 API 확인을 허용한 경우:

```bash
curl "https://api.dev-scj.site/collector/runs?limit=5"
curl "https://api.dev-scj.site/extractor/runs?limit=5"
curl "https://api.dev-scj.site/topics?page=1&page_size=10"
curl "https://api.dev-scj.site/topics/home"
```

정상 기준:

- `SUSPEND`가 의도한 값이고 평소 `ACTIVE`는 `0`이다.
- `LAST SCHEDULE`이 각 schedule 이후 갱신된다.
- 최근 scheduled Job이 `Complete`다.
- 실패한 Job은 이후 성공 여부와 무관하게 원인을 확인한다.
- Collector/extractor API 이력이 Job 시각과 상태에 부합한다.

## 실패한 Job 조사

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe job <job-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l job-name=<job-name>
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs job/<job-name> --tail=200
```

Scheduling, image pull, configuration, DB access, provider, script stage 중 어디서
실패했는지 구분한다. Log를 저장할 때 credential과 기사 원문을 제거한다.

## 수동 Job

다음 command는 DB write 또는 provider 호출을 일으킬 수 있는 사람 통제 작업이다.
현재 task가 요구하고 human operator가 승인한 경우에만 실행한다.

```bash
JOB_NAME=<cronjob-name>-manual-$(date +%Y%m%d%H%M%S)
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/<cronjob-name> "$JOB_NAME"
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs job/"$JOB_NAME"
```

확인이 끝난 수동 Job 삭제도 사람이 결정한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job "$JOB_NAME"
```

## Suspend와 rollback

CronJob suspend, re-enable, delete, manifest apply는 사람이 수행한다. Daily topic
pipeline의 문제가 다른 workload에 영향을 준다면 우선 schedule suspend 여부를
판단하고 기존 raw extractor 변경은 별도 결정으로 유지한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob \
  <cronjob-name> -p '{"spec":{"suspend":true}}'
```

실행 전 현재까지 완료한 검증, 변경 이유, 확인할 결과, 실패 시 대응을 task
verification에 기록한다.
