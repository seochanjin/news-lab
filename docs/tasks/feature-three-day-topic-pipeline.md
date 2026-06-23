# Task: 3일 Topic pipeline·저장·API·CronJob 구축

## Goal

기존 Daily Topic pipeline과 1일 Topic 운영 구조를 유지하면서, 최근 72시간 동안 수집된 기사와 기존 `article_embeddings` 데이터를 활용해 3일 단위 주요 이슈를 생성하는 별도 pipeline을 구축한다.

3일 Topic은 Daily Topic 결과를 다시 집계하는 방식이 아니라, 최근 72시간 기사 후보를 직접 조회하고 이미 저장된 article embedding을 재사용해 다시 clustering한다.

선정된 3일 Topic은 기존 `topics`, `topic_articles`와 분리된 전용 테이블에 저장하며, 목록·상세·홈 API와 K3s CronJob을 통해 독립적으로 조회하고 실행할 수 있어야 한다.

이번 작업의 최종 흐름은 다음과 같다.

```text
기존 Daily Topic pipeline
→ 기사 embedding 저장 유지

최근 72시간 기사 조회
→ 기존 article_embeddings 재사용
→ 3일 기준 재클러스터링
→ 대표 기사 및 관련 기사 선정
→ 요약 근거 기사 선정
→ selected 기사 원문 확보
→ 3일 흐름 요약 생성
→ three_day_topics 계열 테이블 저장
→ 3일 Topic API 제공
→ 전용 CronJob 정기 실행
```

## Scope

- 최근 72시간의 기사 후보를 조회하는 3일 Topic 전용 실행 컨텍스트를 추가한다.
- 조회 시간 범위는 `Asia/Seoul` 기준의 공통 `window_start`, `window_end`로 계산한다.
- 실행 과정 전체에서 동일한 시간 범위를 사용하도록 컨텍스트를 한 번만 결정해 주입한다.
- 기사 시간 기준은 기존 기사 데이터 구조를 검토해 `published_at`을 우선 사용하고, 필요한 경우 기존 정책과 일치하는 fallback을 적용한다.
- 기존 `article_embeddings`에 저장된 embedding만 사용한다.
- 3일 Topic pipeline에서는 신규 embedding provider 호출을 수행하지 않는다.
- embedding이 없는 기사는 실행 실패로 만들지 않고 제외하며 누락 건수를 실행 결과와 로그에 기록한다.
- 최근 72시간 기사 embedding을 사용해 3일 기준으로 다시 clustering한다.
- 기존 Daily Topic의 clustering, 대표 기사 선정, 관련 기사 선정 로직을 가능한 범위에서 재사용하거나 공통 처리 계층으로 추출한다.
- 공통 로직 추출 시 기존 Daily Topic의 입력·출력·정책·테스트 계약을 유지한다.
- 3일 Topic의 최대 후보 기사 수, 최대 Topic 수, clustering threshold, 관련 기사 수와 요약 근거 기사 수를 독립적인 설정으로 관리한다.
- 관련 기사 전체와 요약에 실제 사용한 근거 기사를 분리해 저장한다.
- Topic으로 선정된 기사에 대해서만 기존 원문을 우선 조회하고, 필요한 경우 지연 원문 추출을 수행한다.
- 3일 흐름에 맞는 별도 summary prompt 또는 prompt version을 사용한다.
- 요약은 단일 시점의 사건 설명보다 최근 72시간 동안의 변화, 진행 상황과 여러 출처의 공통 내용을 설명해야 한다.
- Topic 하나의 원문 확보 또는 요약이 실패해도 다른 Topic 처리는 계속하는 실패 격리 정책을 적용한다.
- 3일 Topic 전용 저장 구조와 실행 이력 구조를 추가한다.
- 동일한 기준일 또는 동일한 window 범위로 재실행할 때 중복 데이터가 누적되지 않도록 idempotency 정책을 적용한다.
- 기존 성공 결과를 먼저 삭제한 뒤 pipeline 중간 실패로 결과가 사라지지 않도록 저장·교체 순서를 설계한다.
- 3일 Topic 목록·상세·홈 API를 추가한다.
- 3일 Topic pipeline을 정기 실행하는 K3s CronJob manifest를 추가한다.
- CronJob은 기존 Secret, ConfigMap, image와 실행 환경을 가능한 범위에서 재사용한다.
- 로컬 단위 테스트, 전체 회귀 테스트, manifest 검증과 수동 실행 절차를 문서화한다.
- 실제 DB migration 적용, K3s apply, 수동 Job 실행과 운영 API 확인은 사람이 수행할 수 있도록 명령과 확인 기준을 제공한다.
- README와 Architecture, Runbook, verification, PR, devlog 문서를 작업 결과에 맞게 갱신한다.
- 설계 대안, 선택 근거와 트레이드오프를 문서에 기록한다.

## Do not change

- 기존 Daily Topic pipeline의 운영 의미와 실행 결과를 변경하지 않는다.
- 기존 `scripts/run_daily_topic_pipeline.py`의 외부 실행 계약을 깨지 않는다.
- 기존 `app/services/daily_topic_pipeline/`의 public 함수·결과 모델·통계 의미를 불필요하게 변경하지 않는다.
- 기존 `topics` 테이블 구조와 저장 데이터를 3일 Topic 용도로 사용하지 않는다.
- 기존 `topic_articles` 테이블 구조와 저장 데이터를 3일 Topic 용도로 사용하지 않는다.
- 기존 `topics`, `topic_articles`, `article_embeddings`, `article_texts`, `article_summaries` 데이터를 삭제하거나 변환하지 않는다.
- 기존 `/topics`, `/topics/{topic_id}`, `/topics/home` API contract를 변경하지 않는다.
- 기존 Daily Topic CronJob schedule, command와 argument를 변경하지 않는다.
- 기존 RSS 수집 및 기사 저장 흐름을 변경하지 않는다.
- 기존 embedding 생성 정책이나 embedding model을 변경하지 않는다.
- 3일 Topic pipeline에서 embedding API를 새로 호출하지 않는다.
- 7일 Topic 테이블, pipeline, API와 CronJob을 이번 작업에 포함하지 않는다.
- frontend 저장소와 화면을 변경하지 않는다.
- Redis, cache server, snapshot file과 별도 message queue를 도입하지 않는다.
- production Secret 값을 변경하지 않는다.
- GitHub Actions의 image build/push 정책을 변경하지 않는다.
- 실제 migration 적용, Supabase SQL 실행, K3s apply, rollout, CronJob 실행과 production 배포를 Agent가 수행하지 않는다.
- 기존 application SQL 전반의 interpolation 또는 query construction 리팩터링을 이번 작업에 포함하지 않는다.

## Expected files

실제 저장소 구조를 먼저 확인한 뒤 필요한 파일만 추가·수정한다.

예상 신규 파일:

```text
db/migrations/*_create_three_day_topic_tables.sql

scripts/run_three_day_topic_pipeline.py

app/services/three_day_topic_pipeline/__init__.py
app/services/three_day_topic_pipeline/context.py
app/services/three_day_topic_pipeline/models.py
app/services/three_day_topic_pipeline/candidate_stage.py
app/services/three_day_topic_pipeline/topic_selection_stage.py
app/services/three_day_topic_pipeline/raw_acquisition_stage.py
app/services/three_day_topic_pipeline/summary_persistence_stage.py

app/routers/three_day_topics.py

k8s/news-three-day-topic-pipeline-cronjob.yaml

tests/test_run_three_day_topic_pipeline.py
tests/test_three_day_topic_pipeline.py
tests/test_three_day_topics_api.py
tests/test_three_day_topic_pipeline_cronjob_manifest.py
```

공통 로직 추출이 필요할 경우 예상 수정 파일:

```text
app/services/daily_topic_pipeline/*
app/services/topic_pipeline/*
app/routers/__init__.py
app/main.py
```

단, 공통 모듈의 실제 경로와 이름은 기존 repository 구조를 검토한 뒤 결정한다. Daily Topic 코드를 3일 Topic 디렉터리로 단순 복사하지 않고, 재사용 가치가 명확한 순수 처리 로직만 공통화한다.

예상 문서 파일:

```text
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/design/three-day-topic-pipeline.md
docs/tasks/<current-task>.md
docs/verification/<current-task>.md
docs/reviews/<current-task>-antigravity.md
docs/reviews/<current-task>-coderabbit.md
docs/fixes/<current-task>-approved-fixes.md
docs/pr/<current-task>.md
docs/devlog/<current-task>.md
```

## DB changes

3일 Topic은 기존 1일 Topic 테이블과 분리된 전용 테이블에 저장한다.

예상 테이블:

```text
three_day_topics
three_day_topic_articles
three_day_topic_runs
```

### `three_day_topics`

최소 저장 정보:

```text
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
status
provider
model
prompt_version
summary_input_hash
created_at
updated_at
```

검토할 제약과 인덱스:

```text
- 동일한 기준일 또는 동일한 window 범위의 결과 중복 방지
- 최신 3일 Topic 조회를 위한 reference_date/window_end 정렬 인덱스
- status 기반 조회가 필요할 경우 status 포함 인덱스
```

### `three_day_topic_articles`

최소 저장 정보:

```text
three_day_topic_id
article_id
rank
similarity
is_representative
is_summary_evidence
created_at
```

필수 제약:

```text
UNIQUE (three_day_topic_id, article_id)
```

관계 정책:

```text
- three_day_topic_id는 three_day_topics를 참조한다.
- article_id는 기존 articles를 참조한다.
- 대표 기사는 관련 기사 집합에 포함된다.
- 요약 근거 기사는 관련 기사 집합의 부분집합이다.
```

### `three_day_topic_runs`

최소 실행 이력:

```text
id
reference_date
window_start
window_end
status
candidate_count
embedding_count
missing_embedding_count
cluster_count
selected_topic_count
saved_topic_count
failed_topic_count
error_message
started_at
finished_at
created_at
```

실행 상태와 통계 이름은 기존 Daily Topic pipeline의 의미와 가능한 한 일치시킨다.

### 재실행 정책

- 동일한 `reference_date` 또는 동일한 `window_start`, `window_end` 실행은 중복 결과를 누적하지 않는다.
- pipeline 중간 실패로 기존 성공 결과가 먼저 제거되지 않아야 한다.
- 결과 교체가 필요한 경우 transaction 안에서 기존 window 결과와 신규 결과를 안전하게 교체한다.
- 실행 실패 이력은 `three_day_topic_runs`에 남긴다.
- 일부 Topic 실패 시 성공한 Topic 저장 여부와 전체 run 상태 정책을 문서화하고 테스트한다.

Migration은 SQL 파일로 추가하되 실제 DB 적용은 사람이 수행한다.

## API changes

3일 Topic 전용 API를 추가한다.

권장 endpoint:

```text
GET /three-day-topics
GET /three-day-topics/home
GET /three-day-topics/{topic_id}
```

정적 route인 `/three-day-topics/home`은 동적 route인 `/three-day-topics/{topic_id}`보다 먼저 등록한다.

### `GET /three-day-topics`

목적:

```text
3일 Topic archive 목록 조회
```

검토할 query parameter:

```text
page
page_size
reference_date
date_from
date_to
keyword
status
```

최소 응답 정보:

```text
page
page_size
total
has_next
items
```

각 item 최소 필드:

```text
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
status
created_at
updated_at
```

### `GET /three-day-topics/home`

목적:

```text
프론트 첫 화면에서 사용할 최신 3일 Topic card payload 제공
```

최소 응답:

```text
generated_at
reference_date
window_start
window_end
items
```

각 item 최소 필드:

```text
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
```

홈 API는 다음을 피한다.

```text
- 전체 pagination count
- 관련 기사 detail join
- provider/model/debug metadata
- 불필요한 archive field
```

결과가 없으면 정상적인 빈 응답을 반환한다.

```json
{
  "generated_at": "...",
  "reference_date": null,
  "window_start": null,
  "window_end": null,
  "items": []
}
```

### `GET /three-day-topics/{topic_id}`

목적:

```text
단일 3일 Topic과 연결 기사 조회
```

최소 Topic 정보:

```text
id
reference_date
window_start
window_end
title_ko
summary_ko
keywords
article_count
source_count
status
provider
model
prompt_version
created_at
updated_at
```

연결 기사 최소 정보:

```text
article_id
title
url
published_at
source
rank
similarity
is_representative
is_summary_evidence
```

존재하지 않는 Topic은 기존 API style과 일치하는 404 응답을 반환한다.

`app/main.py` 또는 router 등록 파일 수정 시 기존 router 등록과 application startup에 회귀가 없어야 한다.

## Test commands

작업 중 UNIT별 관련 테스트를 먼저 수행하고 최종적으로 전체 회귀 테스트를 실행한다.

예상 집중 테스트:

```bash
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  -v
```

```bash
python -m pytest tests/test_three_day_topics_api.py -v
```

```bash
python -m pytest \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v
```

Daily Topic 회귀 테스트:

```bash
python -m pytest \
  tests/test_run_daily_topic_pipeline.py \
  tests/test_daily_topic_pipeline_cronjob_manifest.py \
  -v
```

전체 테스트:

```bash
python -m pytest
```

```bash
python -m unittest discover -s tests
```

Compile 검증:

```bash
python -m compileall app scripts tests
```

Whitespace 및 scope 확인:

```bash
git diff --check
```

```bash
git diff -- \
  app/services/daily_topic_pipeline \
  scripts/run_daily_topic_pipeline.py \
  k8s/news-daily-topic-pipeline-cronjob.yaml
```

Migration 확인:

```bash
rg -n \
  "three_day_topics|three_day_topic_articles|three_day_topic_runs" \
  db/migrations app scripts tests
```

API route 확인:

```bash
rg -n \
  "three-day-topics|three_day_topics" \
  app tests docs
```

CronJob manifest 확인:

```bash
kubectl apply --dry-run=client \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

K3s server-side dry-run과 실제 적용은 사람이 수행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply --dry-run=server \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

실제 운영 검증이 승인된 뒤 사용할 수동 명령 예시:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl apply \
  -f k8s/news-three-day-topic-pipeline-cronjob.yaml
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl create job \
  --from=cronjob/news-three-day-topic-pipeline \
  news-three-day-topic-pipeline-manual-$(date +%Y%m%d%H%M%S)
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl get jobs,pods -o wide
```

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml \
kubectl logs job/<manual-job-name>
```

## Acceptance criteria

- 기존 Daily Topic pipeline과 CronJob이 변경 전과 동일하게 동작한다.
- 기존 `topics`, `topic_articles` 테이블과 API contract가 변경되지 않는다.
- 3일 Topic pipeline이 최근 72시간 기사 후보를 명시적인 `window_start`, `window_end` 기준으로 조회한다.
- pipeline 전체 단계가 동일한 시간 범위를 사용한다.
- 기존 `article_embeddings`만 재사용하며 신규 embedding API를 호출하지 않는다.
- embedding이 없는 기사는 제외되고 누락 통계가 기록된다.
- Daily Topic 결과를 재집계하지 않고 기사 embedding을 직접 재클러스터링한다.
- 3일 Topic 정책은 Daily Topic 정책과 독립적인 설정값으로 관리된다.
- 관련 기사와 요약 근거 기사가 분리된다.
- 원문 확보와 요약은 선정된 기사에 대해서만 수행된다.
- Topic 하나의 실패가 다른 Topic 처리를 중단시키지 않는다.
- 3일 흐름에 맞는 summary prompt 또는 prompt version이 적용된다.
- `three_day_topics`, `three_day_topic_articles`, `three_day_topic_runs` migration이 추가된다.
- 동일 기준일 또는 동일 window로 재실행해도 Topic 결과가 중복 누적되지 않는다.
- pipeline 실패 시 기존 성공 결과가 불완전하게 삭제되지 않는다.
- 실행 통계와 오류가 `three_day_topic_runs`에 기록된다.
- `GET /three-day-topics`가 archive 목록을 반환한다.
- `GET /three-day-topics/home`이 최소 card payload를 반환한다.
- `GET /three-day-topics/{topic_id}`가 관련 기사와 대표·요약 근거 역할을 반환한다.
- 빈 데이터와 존재하지 않는 Topic의 응답이 테스트로 보호된다.
- 정적 `/home` route가 동적 `/{topic_id}` route에 가려지지 않는다.
- 3일 Topic CronJob manifest가 추가되고 client-side dry-run을 통과한다.
- CronJob은 `concurrencyPolicy: Forbid`, 적절한 history limit, resource 설정과 실행 제한 시간을 가진다.
- CronJob은 명시적인 3일 Topic 실행 진입점을 사용한다.
- 7일 Topic과 frontend 기능은 포함되지 않는다.
- Python 변경 파일에 프로젝트 문서화 정책에 맞는 한글 docstring이 작성된다.
- 관련 집중 테스트, Daily Topic 회귀 테스트, 전체 pytest, unittest와 compileall이 통과한다.
- `git diff --check`가 통과한다.
- Verification 문서에는 실제 실행한 명령과 결과만 기록한다.
- DB migration 적용과 K3s 운영 반영을 수행하지 않았다면 완료된 것처럼 기록하지 않는다.
- README, Architecture, Runbook과 devlog에 설계 대안, 선택 근거, 트레이드오프 및 운영 절차가 반영된다.

## Notes

- 현재 Daily Topic pipeline은 계속 기사 embedding 생성과 1일 Topic 생성을 담당한다.
- 3일 Topic pipeline은 Daily Topic의 `topics` 결과를 읽지 않고, 기사와 `article_embeddings`를 직접 조회한다.
- Daily Topic이 생성한 embedding뿐 아니라 동일 테이블에 유효하게 저장된 기존 embedding은 3일 후보로 사용할 수 있다.
- 최근 72시간의 정확한 경계는 실행 시각을 기준으로 계산하되, `Asia/Seoul` timezone과 재현 가능한 명시적 `window_end` 주입 방식을 우선한다.
- 운영 CronJob의 실행 시각은 RSS 수집과 Daily Topic pipeline이 충분히 완료된 이후로 설정한다.
- 3일 pipeline 자체는 embedding을 생성하지 않으므로 Daily Topic 실행과 반드시 같은 process에 묶을 필요는 없다.
- 3일과 7일 저장 테이블은 분리한다.
- 이번 작업에서는 3일 전용 테이블만 추가하며, 7일 테이블은 다음 작업에서 별도로 추가한다.
- 테이블과 repository는 기간별로 분리하되 clustering, 기사 선정, 원문 확보와 summary provider 같은 순수 처리 로직은 가능한 범위에서 재사용한다.
- 공통화가 기존 Daily Topic의 동작을 흔들 가능성이 높다면 이번 작업에서는 최소한의 안전한 추출만 수행하고 과도한 리팩터링은 피한다.
- 59차에서 도입한 관련 기사 수와 요약 근거 기사 수 분리 정책을 3일 Topic에도 적용한다.
- 3일 Topic은 단순히 기사 수가 많은 cluster를 저장하는 것이 아니라 출처 다양성, 대표성, 시간 흐름을 고려할 수 있도록 기존 선정 정책과 기간 특성을 함께 검토한다.
- 초기 구현에서는 기존 clustering threshold를 출발점으로 사용할 수 있으나, 72시간 데이터 결과를 검증한 뒤 별도 설정으로 조정 가능해야 한다.
- 실제 migration 적용과 K3s CronJob 반영은 고위험 수동 작업이다.
- 모든 운영 Kubernetes 명령에는 다음 kubeconfig를 명시한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml
```

## Implementation Units

- [x] UNIT-01: 기존 Daily Topic·embedding 구조 분석 및 3일 Topic 저장·실행 계약 설계
- [x] UNIT-02: 3일 Topic 전용 DB migration과 repository 기반 구현
- [x] UNIT-03: 최근 72시간 후보 조회 및 기존 article embedding 재사용 구현
- [x] UNIT-04: 3일 Topic 재클러스터링·대표/관련/요약 근거 기사 선정 구현
- [x] UNIT-05: 선택 기사 원문 확보·3일 요약 생성·실패 격리·저장 구현
- [x] UNIT-06: 3일 Topic 목록·홈·상세 API 구현
- [x] UNIT-07: 3일 Topic CronJob manifest와 실행 진입점 구현
- [x] UNIT-08: 전체 회귀 검증·운영 수동 절차·README 및 설계 문서 정리
