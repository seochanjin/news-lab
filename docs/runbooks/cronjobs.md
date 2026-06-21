# CronJob 운영

[Runbook index로 돌아가기](../RUNBOOK.md)

## 현재 schedule

| CronJob | Schedule | Entry point |
| --- | --- | --- |
| `news-rss-collector` | `03:00 Asia/Seoul` | `scripts/collect_rss.py` |
| `news-daily-topic-pipeline` | `04:00 Asia/Seoul` | `scripts/run_daily_topic_pipeline.py` |

Manifest의 값이 source of truth다. Schedule 변경은 별도 task와 사람의 apply가
필요하다.

`news-raw-extractor`는 repository 배포 대상에서 제거됐다. 기존 cluster object
삭제와 manifest 반영은 human operator가 수행한다.

## Read-only 상태 확인

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs \
  --sort-by=.metadata.creationTimestamp
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-rss-collector
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-daily-topic-pipeline
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
- Collector 이력과 topic 생성 결과가 각 Job 시각과 상태에 부합한다.

## Daily topic embedding reuse 확인

Daily topic pipeline은 기존 실행 단위와 `04:00 Asia/Seoul` schedule을 유지하며
`article_embeddings`를 clustering 입력으로 재사용한다. Topic 선정 뒤 selected
article만 원문 확보 대상으로 삼고, 기존 `raw_articles.raw_text`는 재사용한다.

사람이 안전한 환경 변수 주입과 DB write 영향을 확인한 뒤 동일 조건으로 두 번
실행한다.

```bash
python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --execute
```

각 실행의 JSON result 또는 log에서 다음 값을 기록한다.

```text
candidate_articles
embedding_created
embedding_updated
embedding_reused
embedding_failed
clustering_input_count
topic_count
raw_reused_count
raw_extracted_count
raw_failed_count
raw_missing_count
pipeline_date
business_timezone
pipeline_elapsed_seconds
```

첫 실행은 기존 저장 상태에 따라 created/updated/reused가 섞일 수 있다. 동일
조건의 두 번째 실행에서는 기사 입력이 바뀌지 않았다면 `embedding_reused`가
증가하고 provider 신규 호출 대상은 감소해야 한다.

확인 기준:

- `candidate_articles = embedding_created + embedding_updated +
  embedding_reused + embedding_failed`
- `clustering_input_count = candidate_articles - embedding_failed`
- 실패 article ID와 짧은 오류 요약만 log에 있고 credential과 전체 원문이 없음
- 정상 vector가 2건 미만이면 `topic_count=0`이고 topic DB save를 수행하지 않음
- 기존 topic clustering threshold와 summary/save 계약이 유지됨
- `pipeline_date`와 저장된 `topics.topic_date`가 `Asia/Seoul` 기준으로 일치함

실패 시 embedding failure가 일부 article에 한정됐는지, 정상 vector 수가 최소
조건을 충족했는지, topic save 단계까지 진행했는지를 구분한다. 운영 article의
제목이나 요약을 검증 목적으로 수정하지 않는다.

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
판단한다. Repository에서 제거된 기존 raw extractor CronJob object의 삭제 또는
복구는 사람이 manifest version과 영향 범위를 확인한 뒤 결정한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob \
  <cronjob-name> -p '{"spec":{"suspend":true}}'
```

실행 전 현재까지 완료한 검증, 변경 이유, 확인할 결과, 실패 시 대응을 task
verification에 기록한다.
