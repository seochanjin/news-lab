# NewsLab

NewsLab은 RSS 뉴스를 수집해 임베딩·클러스터링·AI 요약을 수행하고,
일간·3일·주간 토픽으로 제공하는 개인 운영 뉴스 플랫폼입니다.

기사 원문, 임베딩, 토픽과 실행 이력은 PostgreSQL/Supabase에 저장하며,
FastAPI와 Next.js 기반 웹 서비스로 제공합니다.

## 운영 서비스

- 프론트엔드: <https://newslab.ai.kr>
- 프론트엔드 별칭: <https://www.newslab.ai.kr>
- 백엔드 API: <https://api.newslab.ai.kr>

운영 접속성, DNS, TLS 인증서 상태, rollout, 최종 서비스 검증은 사람이 통제하는 작업입니다. 이 저장소는 백엔드 manifest와 runbook을 기록하지만, operator가 제공한 log 없이 agent가 운영 검증 완료를 주장하지 않습니다.

![NewsLab 전체 아키텍처](docs/images/newslab-architecture.png)

## 주요 기능

- RSS source 기반 기사 수집과 중복 URL 정규화
- 기사 원문 지연 추출과 수집·추출 실행 이력 저장
- 오늘의 토픽, 최근 3일 토픽, 지난주 토픽 제공
- 토픽별 대표 기사, 관련 기사, Summary 근거 기사 분리
- 저장된 토픽 archive, home payload, detail API 제공
- 운영 판단을 남기는 아키텍처, runbook, verification, devlog 문서화

## 데이터 파이프라인

NewsLab의 백엔드 파이프라인은 RSS 수집 결과를 바로 화면에 나열하는 데서 끝나지 않고, 기사 후보를 embedding과 clustering으로 묶은 뒤 토픽 단위로 저장합니다.

```text
RSS feed
→ articles
→ article_embeddings
→ clustering / representative article selection
→ raw_articles for summary evidence
→ AI summary
→ topics / three_day_topics / weekly_topics
→ FastAPI read API
→ frontend
```

- 일간 토픽: 최근 24시간 기사 후보를 대상으로 embedding을 생성하거나 재사용하고, 유사 기사 cluster에서 토픽과 Summary를 만든다.
- 3일 토픽: 최근 72시간 기사를 대상으로 기존 `article_embeddings`만 읽어 재클러스터링한다. 일간 토픽 결과를 다시 집계하지 않는다.
- 주간 토픽: 직전 완료 주간의 기사를 대상으로 기존 embedding을 재사용해 주간 흐름을 만든다. 일간 또는 3일 토픽 결과를 집계하지 않는다.

원문 확보와 Summary provider 호출은 모든 기사에 선행 적용하지 않고, 토픽 선정 후 Summary 근거 기사에 필요한 범위로 제한한다. DB write와 provider 호출이 포함된 운영 실행은 사람이 영향 범위를 확인한 뒤 수행한다.

## 아키텍처

백엔드 application과 scheduled pipeline은 K3s에서 실행되고, PostgreSQL/Supabase가 기사, 원문, embedding, 토픽 결과와 실행 이력을 보관합니다.

| 영역                | 역할                                                             |
| ------------------- | ---------------------------------------------------------------- |
| FastAPI             | 저장된 기사, 토픽, 실행 상태를 read API로 제공                   |
| PostgreSQL/Supabase | RSS source, articles, raw_articles, topic tables, 실행 이력 저장 |
| pgvector            | 기사 제목·RSS 요약 기반 embedding 저장과 재사용                  |
| K3s                 | API 배포 리소스와 RSS/토픽 CronJob 실행                          |
| Traefik             | public HTTP(S) 요청을 Service로 전달하는 Ingress Controller      |
| cert-manager        | Let's Encrypt ACME로 TLS Secret 발급과 갱신 관리                 |
| Tailscale           | public ingress가 아니라 운영자 접근과 hybrid node 간 통신 기준   |

이 저장소에 기록된 현재 백엔드 manifest 근거는 다음과 같습니다.

- `news-api` 배포 리소스: `replicas: 2`
- `news-api` Service: port `80` to container port `8000`
- `news-api` Ingress: Traefik + cert-manager, `api.newslab.ai.kr`
- 백엔드와 CronJob image: `seocj/news-api:latest`
- CronJob node selector: `workload: app`

아키텍처 다이어그램에는 전체 운영 서비스 기준의 프론트엔드 runtime과 `news-lab-web` 배치가 포함됩니다. 프론트엔드 application과 Kubernetes manifest는 이 백엔드 저장소 밖에서 관리되므로, 이 README는 이 저장소만으로 프론트엔드 replica 수를 증명하지 않습니다.

## 인프라와 배포

NewsLab은 hybrid 3-node K3s cluster에서 운영됩니다.

- `arm-master-node`: Oracle Cloud A1 control-plane node
- `arm-worker-node`: application과 monitoring core workload를 담당하는 Oracle Cloud A1 worker
- `pi-worker-node`: Tailscale로 연결된 Raspberry Pi worker이며, 일반 application이 실수로 scheduling되지 않도록 taint가 설정됨

정기 실행되는 백엔드 workload는 Kubernetes CronJob으로 정의되어 있습니다.

| Workload                        | 실행 시간                       | 진입점                                    |
| ------------------------------- | ------------------------------- | ----------------------------------------- |
| `news-rss-collector`            | `03:00 Asia/Seoul`              | `scripts/collect_rss.py`                  |
| `news-daily-topic-pipeline`     | `04:00 Asia/Seoul`              | `scripts/run_daily_topic_pipeline.py`     |
| `news-three-day-topic-pipeline` | `05:00 Asia/Seoul`              | `scripts/run_three_day_topic_pipeline.py` |
| `news-weekly-topic-pipeline`    | `00:30 Asia/Seoul` every Monday | `scripts/run_weekly_topic_pipeline.py`    |

GitHub Actions는 `main` branch의 path 변경이나 manual workflow dispatch 시 `linux/arm64`용 백엔드 Docker image를 build하고 Docker Hub에 push합니다. Kubernetes rollout은 완전 자동 CD로 표현하지 않으며, 운영 apply, rollout, verification은 사람이 통제합니다.

## 관측성

monitoring baseline은 kube-prometheus-stack을 사용합니다.

- Prometheus, Grafana, Prometheus Operator, kube-state-metrics는 `observability=true` node를 대상으로 구성됩니다.
- node-exporter는 control-plane/master node와 Raspberry Pi worker taint에 대한 toleration을 포함합니다.
- Alertmanager는 현재 values file에서 비활성화되어 있습니다.
- Grafana 접근과 운영 상태 확인은 runbook과 operator-controlled access path를 통해 처리합니다.

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
- GitHub Actions는 image를 발행하지만, Kubernetes rollout은 image 발행과 의도적으로 분리합니다.

## 문서

- [아키텍처 index](docs/ARCHITECTURE.md)
- [Runbook index](docs/RUNBOOK.md)
- [Pipeline architecture](docs/architecture/pipeline.md)
- [K3s runtime](docs/architecture/k3s-runtime.md)
- [Domain and TLS](docs/architecture/domains.md)
- [3일 토픽 design](docs/design/three-day-topic-pipeline.md)
- [주간 토픽 design](docs/design/weekly-topic-pipeline.md)
- [Agent workflow](docs/agent/backend-workflow.md)
- [Current task](docs/tasks/docs-readme-portfolio-refresh.md)
- [Current verification](docs/verification/docs-readme-portfolio-refresh.md)
- [Raspberry Pi worker join verification](docs/verification/infra-pi-worker-join.md)
- [Monitoring baseline verification](docs/verification/infra-monitoring-baseline.md)

`docs/` 아래의 Task, Verification, Review, Fix, PR, Devlog record는 변경이 어떻게 조사, 구현, 검토, 검증되었는지 보존합니다.

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
