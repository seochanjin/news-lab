# Task: Daily Topic Pipeline CronJob 자동화

## Goal

38차에서 수동으로 검증한 `scripts/run_daily_topic_pipeline.py`를 Kubernetes CronJob으로 자동 실행하도록 구성한다.

목표는 매일 최근 24시간 기사 기준으로 “오늘의 주요 이슈” topic summary를 생성하고, 기존 `topics` / `topic_articles` 테이블에 저장해 `/topics` API에서 조회할 수 있게 만드는 것이다.

초기 자동화 설정은 38차 human-approved execute에서 검증한 값을 기준으로 한다.

- `similarity-threshold`: `0.70`
- `max-topics`: `3`
- `max-reference-topics`: `10`
- `max-articles`: `300`
- `max-articles-per-topic`: `3`
- `max-raw-chars-per-article`: `3000`
- `summary-model`: `gpt-5-nano`

`max-topics: 3`은 실제 요약 생성 및 DB 저장 대상 topic을 최대 3개로 제한한다는 뜻이다.

`max-reference-topics: 10`은 `max-topics` 밖의 후보 topic을 report에 참고용으로 최대 10개까지 남긴다는 뜻이다. Reference candidates는 raw extraction, summary provider, DB write 대상이 아니다.

## Scope

- Daily topic pipeline CronJob manifest를 추가한다.
- CronJob은 `scripts/run_daily_topic_pipeline.py`를 실행한다.
- CronJob은 자동 운영 목적이므로 `--execute`를 포함한다.
- CronJob은 38차에서 검증한 제한값을 사용한다.
- CronJob은 기존 `news-api` 이미지와 실행 환경을 재사용한다.
- CronJob은 기존 Secret/env 주입 구조를 재사용한다.
  - `DATABASE_URL`
  - OpenAI API key 관련 env
- CronJob schedule은 기존 RSS collector와 raw extractor 실행 이후로 설정한다.
- `timeZone`은 `Asia/Seoul`로 설정한다.
- `concurrencyPolicy`는 `Forbid`로 설정한다.
- `restartPolicy`는 `Never`로 설정한다.
- `backoffLimit`은 `1`로 설정한다.
- 성공/실패 Job history limit을 설정한다.
- node selector, resource/security context는 기존 CronJob 패턴을 따른다.
- `docs/RUNBOOK.md`에 적용, 수동 실행, 로그 확인, Job cleanup, rollback/disable 절차를 추가한다.
- verification 문서에는 실제로 실행한 명령과 결과만 기록한다.
- 기존 `news-raw-extractor` CronJob suspend 여부는 문서화만 하고, 실제 suspend는 human-controlled step으로 남긴다.

## Do not change

- DB schema, migration, 신규 테이블, 신규 컬럼을 추가하지 않는다.
- `article_embeddings`, `topic_candidates`, `topic_candidate_articles` 테이블을 추가하지 않는다.
- API route와 response shape를 변경하지 않는다.
- frontend를 변경하지 않는다.
- GitHub Actions를 변경하지 않는다.
- Dockerfile을 변경하지 않는다.
- 기존 `news-rss-collector` CronJob을 삭제하거나 변경하지 않는다.
- 기존 `news-raw-extractor` CronJob을 삭제하지 않는다.
- 기존 `news-raw-extractor` CronJob suspend를 자동 실행하지 않는다.
- gpt-5-mini 비교, fallback, factuality gate를 추가하지 않는다.
- provider prompt 품질 개선은 이번 범위에 포함하지 않는다.
- secret 값, `.env`, kubeconfig, credentials, SSH key, token을 수정하지 않는다.
- Codex/agent는 `kubectl apply`, `kubectl delete`, `kubectl patch`, `kubectl rollout`을 실행하지 않는다.
- Codex/agent는 Supabase SQL, migration, production curl, git push, git merge를 실행하지 않는다.

## Expected files

예상 변경 파일:

```text
k8s/news-daily-topic-pipeline-cronjob.yaml
docs/tasks/feature-daily-topic-pipeline-cronjob.md
docs/verification/feature-daily-topic-pipeline-cronjob.md
docs/pr/feature-daily-topic-pipeline-cronjob.md
docs/devlog/feature-daily-topic-pipeline-cronjob.md
docs/RUNBOOK.md
```

필요 시 추가 가능한 파일:

```text
tests/test_daily_topic_pipeline_cronjob_manifest.py
```

## DB changes

DB schema 변경은 없다.

- 신규 테이블 없음
- 신규 컬럼 없음
- migration 없음
- Supabase SQL 실행 없음

CronJob 실행 시 실제 write 대상은 기존 테이블이다.

```text
topics
topic_articles
```

CronJob은 `scripts/run_daily_topic_pipeline.py --execute`를 실행하므로, 정상 동작 시 매일 provider 기반 topic summary가 기존 `topics` / `topic_articles`에 저장된다.

단, 이번 구현 작업에서 agent는 실제 DB write를 수행하지 않는다. 실제 CronJob 적용과 운영 검증은 human-controlled step으로 수행한다.

## API changes

API 변경은 없다.

기존 topic 조회 API를 그대로 사용한다.

```text
GET /topics?page=1&page_size=10
GET /topics/{topic_id}
```

CronJob 실행 후 저장된 topic summary는 기존 `/topics` API에서 조회되어야 한다.

raw_text는 API에 노출되면 안 된다.

## Test commands

Codex가 실행 가능한 로컬 검증:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest discover -s tests -v
git diff --check
```

manifest test를 추가한 경우:

```bash
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
```

YAML 정적 확인이 가능하면 다음을 수행한다.

```bash
python - <<'PY'
import yaml
from pathlib import Path

path = Path("k8s/news-daily-topic-pipeline-cronjob.yaml")
data = yaml.safe_load(path.read_text())
assert data["kind"] == "CronJob"
assert data["metadata"]["name"] == "news-daily-topic-pipeline"
assert data["spec"]["timeZone"] == "Asia/Seoul"
assert data["spec"]["concurrencyPolicy"] == "Forbid"
print("cronjob manifest ok")
PY
```

Human-controlled verification 후보:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-daily-topic-pipeline-cronjob.yaml
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-daily-topic-pipeline -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job --from=cronjob/news-daily-topic-pipeline news-daily-topic-pipeline-manual-$(date +%Y%m%d%H%M%S) -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default job/<manual-job-name>
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
```

위 human-controlled commands는 Codex/agent가 실행하지 않는다. 실제 실행 결과만 verification 문서에 기록한다.

## Acceptance criteria

- `k8s/news-daily-topic-pipeline-cronjob.yaml`이 추가된다.
- CronJob 이름은 `news-daily-topic-pipeline`이다.
- CronJob은 기존 `news-api` image를 사용한다.
- CronJob은 `python scripts/run_daily_topic_pipeline.py`를 실행한다.
- CronJob command에는 다음 운영값이 포함된다.
  - `--window-hours 24`
  - `--max-articles 300`
  - `--similarity-threshold 0.70`
  - `--max-topics 3`
  - `--max-reference-topics 10`
  - `--max-articles-per-topic 3`
  - `--max-raw-chars-per-article 3000`
  - `--use-embedding-provider`
  - `--use-summary-provider`
  - `--summary-model gpt-5-nano`
  - `--execute`
- CronJob은 `timeZone: Asia/Seoul`을 사용한다.
- CronJob은 `concurrencyPolicy: Forbid`를 사용한다.
- CronJob은 `restartPolicy: Never`를 사용한다.
- CronJob은 `backoffLimit: 1`을 사용한다.
- CronJob은 기존 Secret/env 주입 구조를 재사용한다.
- Secret 값은 코드나 문서에 기록하지 않는다.
- DB schema, API, frontend, GitHub Actions, Dockerfile은 변경하지 않는다.
- 기존 `news-raw-extractor` CronJob은 삭제하지 않는다.
- 기존 `news-raw-extractor` CronJob suspend는 human decision pending으로 문서화한다.
- RUNBOOK에 apply, get, manual job, logs, cleanup, disable/suspend 절차가 문서화된다.
- 로컬 테스트와 `git diff --check`가 통과한다.
- verification 문서에는 실제 실행한 명령과 결과만 기록한다.
- production verification은 human-provided logs가 있을 때만 완료로 표시한다.

## Notes

38차에서 수동 daily topic pipeline은 threshold `0.70` 기준으로 human-approved execute까지 검증되었다. Production `/topics` API에서 `openai` / `gpt-5-nano` summary가 조회되었고, raw_text가 topic detail API에 노출되지 않는 것도 확인했다.

이번 39차는 해당 수동 실행 흐름을 자동 운영 가능한 CronJob으로 등록하는 단계다.

기존 운영 흐름은 다음 순서를 기준으로 한다.

```text
03:00 KST  news-rss-collector
03:30 KST  news-raw-extractor
04:00 KST  news-daily-topic-pipeline
```

다만 daily topic pipeline은 selected article raw extraction을 자체 수행할 수 있다. 따라서 기존 `news-raw-extractor` CronJob은 향후 suspend 후보이지만, 이번 작업에서는 삭제하거나 자동 suspend하지 않는다.

초기 CronJob은 작은 범위의 자동 write로 제한한다.

```text
max-topics=3
max-articles=300
max-articles-per-topic=3
max-raw-chars-per-article=3000
summary-model=gpt-5-nano
```

`max-topics=3`은 대문에 보여줄 “오늘의 주요 이슈” 3개를 생성하기 위한 제한값이다.

`max-reference-topics=10`은 report에서 요약 대상 밖 후보를 최대 10개까지 참고용으로 남기기 위한 값이다. Reference candidates는 실제 요약/저장 대상이 아니다.

Provider summary에서 일부 한국어 품질 문제가 관찰되었다. 이는 이번 CronJob 자동화의 blocker는 아니지만, frontend 노출 전 prompt/quality review 대상으로 남긴다.
