# CronJob 운영

[Runbook index로 돌아가기](../RUNBOOK.md)

## 현재 schedule

| CronJob | Schedule | Entry point |
| --- | --- | --- |
| `news-rss-collector` | `03:00 Asia/Seoul` | `scripts/collect_rss.py` |
| `news-daily-topic-pipeline` | `04:00 Asia/Seoul` | `scripts/run_daily_topic_pipeline.py` |
| `news-three-day-topic-pipeline` | `05:00 Asia/Seoul` | `scripts/run_three_day_topic_pipeline.py` |

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
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l app=news-three-day-topic-pipeline
```

Human operator가 API 확인을 허용한 경우:

```bash
curl "https://api.dev-scj.site/collector/runs?limit=5"
curl "https://api.dev-scj.site/extractor/runs?limit=5"
curl "https://api.dev-scj.site/topics?page=1&page_size=10"
curl "https://api.dev-scj.site/topics/home"
curl "https://api.dev-scj.site/three-day-topics?page=1&page_size=10"
curl "https://api.dev-scj.site/three-day-topics/home"
```

정상 기준:

- `SUSPEND`가 의도한 값이고 평소 `ACTIVE`는 `0`이다.
- `LAST SCHEDULE`이 각 schedule 이후 갱신된다.
- 최근 scheduled Job이 `Complete`다.
- 실패한 Job은 이후 성공 여부와 무관하게 원인을 확인한다.
- Collector 이력과 topic 생성 결과가 각 Job 시각과 상태에 부합한다.

## 3일 Topic 최초 반영 순서

아래 작업은 모두 사람이 실행한다. Migration과 manifest가 아직 적용되지 않은
상태에서 CronJob 또는 `--execute`를 먼저 실행하지 않는다.

1. 배포 image에 3일 pipeline 코드와 API router가 포함됐는지 확인한다.
2. `db/migrations/007_create_three_day_topic_tables.sql`을 review하고 DB에
   적용한다.
3. [Database runbook](database-check.md)의 read-only query로 table,
   constraint와 index를 확인한다.
4. Kubernetes client/server-side dry-run으로 manifest schema와 cluster
   admission 결과를 확인한다.
5. CronJob manifest를 적용하고 schedule, command, Secret reference와 suspend
   상태를 확인한다.
6. 한 번의 수동 Job을 만들고 log, run row, 저장 결과와 API를 확인한다.
7. 검증이 끝난 뒤 다음 `05:00 Asia/Seoul` scheduled Job을 확인한다.

Local manifest 검토:

```bash
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

Cluster admission 검토:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

실제 적용:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

적용 후 read-only 확인:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob \
  news-three-day-topic-pipeline -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob \
  news-three-day-topic-pipeline -o yaml
```

확인 기준:

- `schedule: 0 5 * * *`, `timeZone: Asia/Seoul`이다.
- `concurrencyPolicy: Forbid`, history limit, deadline와 backoff가 manifest와
  일치한다.
- command가 `scripts/run_three_day_topic_pipeline.py`, 72시간 인자와
  `--execute`를 사용한다.
- `DATABASE_URL`, `OPENAI_SUMMARY_API_KEY`만 기존 Secret에서 참조하고 embedding
  key를 요구하지 않는다.

## 3일 Topic 수동 Job과 확인

이 절차는 DB write, 지연 원문 추출과 Summary provider 호출을 포함하는 사람 통제
작업이다.

```bash
JOB_NAME=news-three-day-topic-pipeline-manual-$(date +%Y%m%d%H%M%S)
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-three-day-topic-pipeline "$JOB_NAME"
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get job,pod \
  -l job-name="$JOB_NAME" -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs job/"$JOB_NAME"
```

Log와 `three_day_topic_runs`에서 다음 값을 확인한다.

```text
reference_date
window_start
window_end
candidate_count
embedding_count
missing_embedding_count
cluster_count
selected_topic_count
saved_topic_count
failed_topic_count
run_status
run_id
pipeline_elapsed_seconds
```

확인 기준:

- `window_end - window_start = 72 hours`이고 모든 저장 Topic이 같은 window를
  사용한다.
- `candidate_count = embedding_count + missing_embedding_count`다.
- embedding 누락은 기사 제외로 기록되고 신규 embedding 생성 log가 없다.
- `success` 또는 `partial_success` run의 `saved_topic_count`가 실제 Topic 수와
  일치한다.
- Topic 상세의 대표 기사는 관련 기사와 Summary 근거 기사에 포함된다.
- credential, embedding vector 전체와 기사 원문이 log에 노출되지 않는다.

Human operator가 production API 확인을 선택한 경우:

```bash
curl "https://api.dev-scj.site/three-day-topics?page=1&page_size=10"
curl "https://api.dev-scj.site/three-day-topics/home"
curl "https://api.dev-scj.site/three-day-topics/<topic-id>"
```

Archive, home과 detail의 window가 일치하고 detail의 관련 기사 rank와
`is_representative`, `is_summary_evidence`가 저장 계약에 부합하는지 확인한다.

동일 window idempotency를 확인하려면 manifest command를 그대로 복사해
timezone-aware `--window-end`를 추가한 별도 수동 실행 계획을 review한다. 같은
window 재실행 전후 활성 Topic set이 누적되지 않고 run 이력만 추가되는지
확인한다. 운영 재실행은 provider 호출과 결과 교체를 동반하므로 자동화하지
않는다.

## Daily topic embedding reuse 확인

Daily topic pipeline은 기존 실행 단위와 `04:00 Asia/Seoul` schedule을 유지하며
`article_embeddings`를 clustering 입력으로 재사용한다. Topic별 관련 기사는
최대 20건까지 저장 대상으로 유지하고, 그중 Summary 근거 기사 최대 3건만 원문
확보와 Summary provider 입력 대상으로 삼는다. 기존 `raw_articles.raw_text`는
우선 재사용한다.

사람이 안전한 환경 변수 주입과 DB write 영향을 확인한 뒤 동일 조건으로 두 번
실행한다.

```bash
python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-related-articles-per-topic 20 \
  --max-summary-articles-per-topic 3 \
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
related_article_count
summary_article_count
raw_acquisition_target_count
raw_reused_count
raw_extracted_count
raw_failed_count
raw_missing_count
saved_topic_article_count
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
- `summary_article_count <= related_article_count`
- `raw_acquisition_target_count = summary_article_count`
- 저장된 Topic의 `article_count`와 API 관련 기사 목록이 관련 기사 전체를 반영함
- 저장된 Topic의 `source_count`가 관련 기사 전체의 source 기준과 일치함
- Topic 상세 응답의 첫 대표 기사와 이후 supporting 기사 순서가 유지됨
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

3일 Topic 반영 실패 시 새 실행을 먼저 중단한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob \
  news-three-day-topic-pipeline -p '{"spec":{"suspend":true}}'
```

- Job 또는 provider 문제면 CronJob을 suspend하고 log와
  `three_day_topic_runs.error_message`를 확인한다.
- API 문제면 이전 application image로 rollback할지 사람이 판단한다.
- Migration은 additive이므로 실행 중단을 위해 table을 즉시 삭제할 필요가 없다.
- table 제거가 필요하면 Topic과 run 이력 보존 여부를 먼저 결정하고
  `three_day_topic_articles`, `three_day_topics`, `three_day_topic_runs` 순서의
  별도 rollback SQL을 review한다. 자동 실행하지 않는다.

실행 전 현재까지 완료한 검증, 변경 이유, 확인할 결과, 실패 시 대응을 task
verification에 기록한다.
