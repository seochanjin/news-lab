# NewsLab

NewsLab은 여러 RSS source의 기사를 수집하고 임베딩·클러스터링·AI 요약을
거쳐 일간·최근 3일·지난주 토픽으로 제공하는 개인 운영 뉴스 플랫폼입니다.

PostgreSQL/Supabase가 기사 원문, 임베딩, 토픽 결과와 pipeline 실행 이력의
영속 저장소이며, 이 저장소의 FastAPI backend가 조회 API를 제공합니다.
Next.js frontend와 그 배포 리소스는 별도 `news-lab-web` 저장소에서 관리합니다.

## 운영 서비스

현재 운영 중인 서비스입니다.

- NewsLab: <https://newslab.ai.kr>

![NewsLab 전체 아키텍처](docs/images/newslab-architecture_R1.png)

## 주요 기능

- RSS source registry 조회, 기사 수집과 정규화된 URL 기준 중복 방지
- 기사 metadata·원문 조회와 수집·추출 실행 상태 및 이력 제공
- 오늘의 토픽, 최근 72시간 토픽, 직전 완료 주간 토픽의 독립 생성
- 토픽별 대표 기사, 관련 기사와 AI Summary 근거 기사 분리
- 일간·3일·주간 토픽별 archive, Home card payload와 detail API 제공
- Architecture, Runbook과 Verification을 통한 설계·운영 근거 관리

## 데이터 파이프라인

NewsLab backend는 RSS 기사를 PostgreSQL/Supabase에 먼저 저장한 뒤, 기간별
후보를 embedding과 clustering으로 묶고 토픽 단위 read model로 저장합니다.
FastAPI는 pipeline을 요청 시 실행하지 않고 저장된 결과를 조회합니다.

```text
RSS feed
→ RSS collector
→ articles + crawl_runs
→ period-specific topic pipeline
  → article_embeddings 생성 또는 재사용
  → clustering / representative and related article selection
  → Summary 근거 기사만 raw_articles 확보
  → AI Summary 생성
→ topics / three_day_topics / weekly_topics와 관계·실행 이력 저장
→ FastAPI archive / Home / detail read API
→ 별도 Next.js frontend
```

- 일간 토픽은 최근 24시간 기사 후보의 embedding을 생성하거나 재사용하고,
  유사 기사 cluster에서 토픽과 Summary를 만듭니다.
- 3일 토픽은 최근 72시간 기사와 기존 `article_embeddings`만 읽어 독립적으로
  재클러스터링하며, 일간 토픽 결과를 다시 집계하지 않습니다.
- 주간 토픽은 직전 완료 주간의 기사와 기존 embedding으로 주간 흐름을
  독립 생성하며, 일간 또는 3일 토픽 결과를 집계하지 않습니다.

원문 확보와 Summary provider 호출은 모든 기사에 선행 적용하지 않고 토픽 선정
후 Summary 근거 기사에 필요한 범위로 제한합니다. 기간별 결과와 실행 이력의
구체적인 저장 계약은 [Pipeline architecture](docs/architecture/pipeline.md)와
[Database architecture](docs/architecture/database.md)에서 확인할 수 있습니다.
DB write와 provider 호출이 포함된 운영 실행은 사람이 영향 범위를 확인한 뒤
수행합니다.

## 아키텍처

사용자 요청은 별도 Next.js frontend와 이 저장소의 FastAPI backend로 나뉘며,
각 application은 독립된 Kubernetes Service와 Pod를 사용합니다. Backend
application과 scheduled pipeline은 K3s에서 실행되고 PostgreSQL/Supabase가
기사, 원문, embedding, 토픽 결과와 실행 이력을 보관합니다.

| 영역                | 역할                                                        |
| ------------------- | ----------------------------------------------------------- |
| Next.js frontend    | 사용자 화면 제공. 별도 `news-lab-web` 저장소가 관리         |
| FastAPI backend     | 저장된 source, 기사, 토픽과 실행 상태를 read API로 제공     |
| PostgreSQL/Supabase | 기사·원문·embedding·기간별 토픽과 실행 이력의 영속 저장     |
| Redis               | Home API 반복 조회를 줄이는 삭제 가능한 fail-open cache     |
| pgvector            | 기사 제목·RSS 요약 기반 embedding 저장과 재사용             |
| K3s                 | Backend API 배포 리소스와 RSS·토픽 CronJob 실행             |
| Traefik             | public HTTP(S) 요청을 application별 Service로 전달          |
| cert-manager        | Let's Encrypt ACME 기반 TLS Secret 발급·갱신 관리           |
| Tailscale           | public ingress와 분리된 operator 접근·hybrid node 통신 경로 |

이 저장소에 기록된 현재 백엔드 manifest 근거는 다음과 같습니다.

- `news-api` 배포 리소스: `replicas: 2`
- `news-api` Service: port `80` to container port `8000`
- `news-api` Ingress: Traefik + cert-manager, `api.newslab.ai.kr`
- 백엔드와 네 CronJob image: `seocj/news-api:<full-git-sha>` 형식의 동일한
  immutable tag
- CronJob node selector: `workload: app`

공개 요청은 다음 논리 경로를 따릅니다.

```text
User
→ Public DNS
→ Oracle Public IP
→ Traefik Ingress
→ Kubernetes Service
→ Application Pod
```

다이어그램의 `Service → Pod / Container`는 요청을 받은 application의
서비스와 Pod를 의미하는 논리 단계입니다. Frontend는 Frontend Service에서
Next.js Pod로, Backend는 `news-api` Service에서 FastAPI Pod로 각각
전달되며, 하나의 Service가 두 application의 Pod를 함께 선택하지
않습니다. 이 백엔드 저장소는 `news-api-ingress → news-api Service
→ FastAPI Pod`를 직접 정의합니다. Public DNS와 Oracle Public IP 연결,
Frontend application과 Kubernetes manifest는 저장소 밖의 운영 범위이므로
사람이 제공한 운영 검증 없이 현재 상태를 재증명하지 않습니다.

## Home Cache

PostgreSQL/Supabase는 토픽 결과의 Source of Truth이고 Redis는 언제든 비우거나
재생성할 수 있는 cache 계층입니다. 세 Home API는 cache-aside로 동작합니다.

```text
Home API request
→ Redis key 조회
→ hit: cached Home payload 반환
→ miss / Redis 장애 / 손상 payload: PostgreSQL 조회
→ Redis 저장 시도 후 payload 반환
```

Redis 미설정, 연결 실패, timeout 또는 읽기·쓰기 실패는 Home API와 Pipeline의
실패로 전파하지 않는 fail-open 정책을 사용합니다. FastAPI와 각 Pipeline이
PostgreSQL과 Redis에 각각 접근하며, PostgreSQL과 Redis가 서로 직접 통신하지
않습니다.

Pipeline은 PostgreSQL 저장이 성공한 뒤 Home API와 같은 payload builder로
대응 key를 prewarm합니다. 따라서 첫 Home API 요청 전에도 최신 저장 결과를
cache에서 제공할 수 있습니다.

```text
Daily Pipeline → PostgreSQL 저장 → topics:home:v1 prewarm
3-day Pipeline → PostgreSQL 저장 → three-day-topics:home:v1 prewarm
Weekly Pipeline → PostgreSQL 저장 → weekly-topics:home:v1 prewarm
```

| Home 구분 | Redis key                  | TTL                |
| --------- | -------------------------- | ------------------ |
| Daily     | `topics:home:v1`           | `108000`초(30시간) |
| 3-day     | `three-day-topics:home:v1` | `108000`초(30시간) |
| Weekly    | `weekly-topics:home:v1`    | `691200`초(8일)    |

TTL은 최신성을 결정하는 주기가 아니라 오래된 cache의 장기 잔류를 제한하는
안전장치입니다. 최신 payload 전환은 Pipeline의 post-save prewarm이 담당합니다.
세부 cache-aside와 로그 정책은
[FastAPI Architecture](docs/architecture/backend-api.md), Pipeline별 저장 이후
흐름은 [Pipeline Architecture](docs/architecture/pipeline.md)에서 확인할 수
있습니다.

## 인프라와 배포

NewsLab은 hybrid 3-node K3s cluster에서 운영됩니다.

- `arm-master-node`: Oracle Cloud A1 control-plane node
- `arm-worker-node`: application과 monitoring core workload를 담당하는 Oracle Cloud A1 worker
- `pi-worker-node`: Tailscale로 연결된 Raspberry Pi worker이며, 일반 application이 실수로 scheduling되지 않도록 taint가 설정됨

`arm-master-node`에는 일반 application workload를 배치하지 않습니다.
`arm-worker-node`는 Frontend·Backend, Redis, scheduled pipeline과 monitoring
core의 현재 application node입니다. `pi-worker-node`는
`node-role=news-edge-worker:NoSchedule` taint로 일반 application을 받지
않고 node-exporter만 실행하며, 향후 explicit toleration을 갖춘 edge/batch
workload 후보로 남겨 둡니다.

외부 운영 경로는 public request path와 분리됩니다. GitHub Actions와
Docker Hub는 ARM64 image 발행을, Argo CD는 Git desired state와 cluster의
수동 동기화를 담당합니다. FastAPI와 pipeline이 관리형
PostgreSQL/Supabase에 접근하고, cert-manager가 Let's Encrypt ACME와
연동합니다. Operator는 Tailscale SSH tunnel을 통해 K3s API에
접근하며, Tailscale은 사용자의 public ingress를 대체하지 않습니다.

정기 실행되는 백엔드 workload는 Kubernetes CronJob으로 정의되어 있습니다.

| Workload                        | 실행 시간                       | 진입점                                    |
| ------------------------------- | ------------------------------- | ----------------------------------------- |
| `news-rss-collector`            | `03:00 Asia/Seoul`              | `scripts/collect_rss.py`                  |
| `news-daily-topic-pipeline`     | `04:00 Asia/Seoul`              | `scripts/run_daily_topic_pipeline.py`     |
| `news-three-day-topic-pipeline` | `05:00 Asia/Seoul`              | `scripts/run_three_day_topic_pipeline.py` |
| `news-weekly-topic-pipeline`    | `00:30 Asia/Seoul` every Monday | `scripts/run_weekly_topic_pipeline.py`    |

Backend 배포는 image 발행과 cluster 반영 사이에 두 번의 사람 승인 gate를 둡니다.

```text
Application code PR merge
→ GitHub Actions가 ARM64 immutable full Git SHA image build/push
→ Backend Deployment와 네 CronJob의 image를 갱신하는 manifest PR 생성
→ 사람이 manifest diff 검토 후 merge
→ Argo CD가 OutOfSync 감지
→ 사람이 Argo CD diff 검토
→ Manual Sync
→ rollout, workload image와 production health 검증
```

Workflow는 `main` branch의 backend path 변경이나 manual dispatch에서
`linux/arm64` image를 build하며, 운영 manifest와 rollback 기준에는
`seocj/news-api:<full-git-sha>`를 사용합니다. 보조 `latest` image도 registry에
발행하지만 desired state로 사용하지 않습니다. Argo CD `news-api` Application은
automated sync, automatic prune, automatic self-heal 없이 `main/k8s`를 추적합니다.
따라서 image push만으로 rollout되지 않으며 manifest PR merge 후에도 사람이
diff를 승인하고 Manual Sync와 운영 검증을 수행해야 합니다. Rollback 역시 이전
정상 full SHA를 manifest에 반영하는 PR부터 같은 승인 절차를 다시 따릅니다.

## 관측성

monitoring baseline은 kube-prometheus-stack을 사용합니다.

- Prometheus, Grafana, Prometheus Operator, kube-state-metrics는 `observability=true` node를 대상으로 구성됩니다.
- node-exporter는 control-plane/master node와 Raspberry Pi worker taint에 대한 toleration을 포함합니다.
- Alertmanager는 현재 values file에서 비활성화되어 있습니다.
- Grafana 접근과 운영 상태 확인은 runbook과 operator-controlled access path를 통해 처리합니다.

현재 manifest와 기존 운영 검증에서 monitoring core는 `arm-worker-node`,
node-exporter는 세 노드에 배치되었습니다. 이는 기록 시점의 운영 근거이며 현재
live placement를 새로 검증했다는 뜻은 아닙니다. Grafana와 K3s API를 위한
operator 접근은 Tailscale 경로를 사용하고 public application ingress와
분리합니다.

## Agent workflow

이 저장소는 문서 기반 agent-assisted workflow를 사용합니다.

- Task file은 각 branch의 source of truth입니다.
- Codex는 승인된 task unit만 구현하고 실제 실행한 verification command를 기록합니다.
- Antigravity와 CodeRabbit review output은 review evidence로만 취급하며, code 변경 권한을 직접 부여하지 않습니다.
- Approved fix는 구현 전에 별도로 기록되어야 합니다.
- `kubectl apply`, rollout, Supabase SQL, `git push`, merge 같은 고위험 작업은 사람이 통제합니다.

이 workflow는 보수적으로 운영됩니다. Automation은 구현, review, evidence 수집을 보조하고, 운영에 영향을 주는 결정은 operator가 담당합니다. 사람 승인 기반(Human-in-the-loop) 운영 원칙을 적용합니다.

## 주요 설계 결정

- 일간, 3일, 주간 토픽 pipeline은 서로를 rollup하지 않는 별도 result model입니다. 각 window는 독립적인 candidate limit, clustering threshold, persistence contract를 사용할 수 있습니다.
- 3일과 주간 pipeline은 해당 job에서 새 embedding을 생성하지 않고 기존 `article_embeddings`를 재사용해 provider coupling을 줄이고 누락된 embedding을 명시적으로 드러냅니다.
- Raw article extraction은 선택된 Summary evidence가 필요할 때까지 지연해, 토픽 선정 전 광범위한 article body fetching을 피합니다.
- Raspberry Pi worker는 cluster network와 monitoring target에 포함되지만, 일반 application scheduling은 taint와 node selector로 제한합니다.
- GitHub Actions의 image 발행, manifest PR merge, Argo CD Manual Sync와 운영
  검증을 분리해 각 단계에서 사람이 변경 내용을 승인합니다.

## 문서 탐색

처음에는 [Architecture index](docs/ARCHITECTURE.md)에서 구성 요소와 책임 경계를,
[Runbook index](docs/RUNBOOK.md)에서 사람이 수행하는 운영 절차를 선택합니다.

- 서비스와 데이터: [구성 개요](docs/architecture/overview.md),
  [FastAPI 영역](docs/architecture/backend-api.md),
  [Database](docs/architecture/database.md),
  [Pipeline](docs/architecture/pipeline.md)
- Runtime과 외부 경계: [K3s runtime](docs/architecture/k3s-runtime.md),
  [Domain과 TLS](docs/architecture/domains.md)
- 기간별 설계: [3일 토픽](docs/design/three-day-topic-pipeline.md),
  [주간 토픽](docs/design/weekly-topic-pipeline.md)
- 작업 workflow: [Backend agent workflow](docs/agent/backend-workflow.md),
  [현재 Task](docs/tasks/docs-readme-architecture-refresh.md),
  [현재 Verification](docs/verification/docs-readme-architecture-refresh.md)
- 운영 근거: [Raspberry Pi worker join verification](docs/verification/infra-pi-worker-join.md),
  [Monitoring baseline verification](docs/verification/infra-monitoring-baseline.md)

`docs/tasks/`는 branch 요구사항, `docs/verification/`은 실제 실행 결과를
보관합니다. Review, 승인된 Fix, PR과 Devlog 기록은 각각 `docs/reviews/`,
`docs/fixes/`, `docs/pr/`, `docs/devlog/`에서 변경의 검토·승인·전달 근거를
추적합니다.

## 로컬 개발

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Pipeline script는 명시적인 실행 flag가 제공되지 않으면 local 또는 dry-run 중심 사용을 기본값으로 둡니다. DB write, raw extraction, provider call, 운영 CronJob 실행을 수행하는 option은 operator-controlled action으로 취급해야 합니다.

예시:

```bash
python scripts/run_three_day_topic_pipeline.py --window-end \
  2026-06-23T05:00:00+09:00
```

```bash
python scripts/run_weekly_topic_pipeline.py --week-start 2026-06-15
```
