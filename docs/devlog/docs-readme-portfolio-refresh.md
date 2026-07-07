# NewsLab README 포트폴리오 관문 개선

## 작업 목적

NewsLab README를 저장소 첫 진입점으로 재구성한다.

기존 README는 FastAPI endpoint와 초기 운영 구성 중심이어서, 실제 프로젝트가
가진 다음 맥락을 한 번에 보여주기 어려웠다.

- RSS 수집부터 Daily / Three-day / Weekly Topic으로 이어지는 데이터 pipeline
- Oracle Cloud A1과 Raspberry Pi를 함께 쓰는 3-node K3s 운영 구조
- Traefik, cert-manager, Tailscale, Supabase, Prometheus/Grafana의 역할
- GitHub Actions와 Docker Hub를 통한 ARM64 backend image 발행
- Agent가 구현과 검토를 보조하고 사람이 운영 변경을 승인하는 workflow
- Architecture, Runbook, Verification, Devlog로 누적한 운영 기록

이번 작업의 목적은 채용담당자나 면접관이 README 상단만 읽어도
`무엇을 만들었는지`, `실제로 어떤 구조로 운영하는지`, `무엇을 직접 설계하고
검증했는지`, `근거 문서는 어디인지`를 파악할 수 있게 만드는 것이다.

## 기존 문제

- README가 API endpoint 목록과 로컬 실행 안내에 치우쳐 있었다.
- 현재 서비스 도메인은 `newslab.ai.kr`, `api.newslab.ai.kr`인데 README에는
  이전 backend domain인 `api.dev-scj.site`가 current domain처럼 남아 있었다.
- Daily, Three-day, Weekly Topic pipeline의 차이와 설계 의도가 README 상단에서
  드러나지 않았다.
- K3s cluster, Traefik/cert-manager, Tailscale, observability, CI image 발행
  같은 운영 경험이 README에서 충분히 설명되지 않았다.
- 장기간 축적된 Architecture, Runbook, Verification, Devlog 문서가 있어도
  외부 방문자가 어디부터 봐야 하는지 알기 어려웠다.
- 기존 README에는 전체 아키텍처를 빠르게 파악할 수 있는 이미지가 없었다.

## 변경 내용

- `README.md`를 포트폴리오 관문 문서 구조로 재작성했다.
- README 상단에 현재 live service 주소를 정리했다.
  - Frontend: `https://newslab.ai.kr`
  - Frontend alias: `https://www.newslab.ai.kr`
  - Backend API: `https://api.newslab.ai.kr`
- README에서 이전 `api.dev-scj.site`를 현재 운영 주소로 표현하지 않도록 제거했다.
- `docs/images/newslab-architecture.png`를 추가하고 README에서 상대 경로로 연결했다.
- RSS collection, raw extraction, embedding, clustering, summary, Topic 저장과
  FastAPI 제공 흐름을 README에 요약했다.
- Oracle Cloud A1 + Raspberry Pi 기반 3-node K3s 구조와 backend `news-api`
  replica 근거를 README에 기록했다.
- Traefik, cert-manager, Tailscale, Supabase/pgvector, Prometheus/Grafana,
  kube-state-metrics, node-exporter, GitHub Actions/Docker Hub의 역할을 정리했다.
- Agent workflow와 human-controlled operation 원칙을 README에 반영했다.
- Architecture, Runbook, pipeline/design, workflow, verification 문서로 이동하는
  documentation index를 README에 추가했다.
- branch workflow artifact를 추가하거나 갱신했다.
  - `docs/tasks/docs-readme-portfolio-refresh.md`
  - `docs/verification/docs-readme-portfolio-refresh.md`
  - `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`
  - `docs/pr/docs-readme-portfolio-refresh.md`
  - `docs/devlog/docs-readme-portfolio-refresh.md`

## 구현 상세

README 정보 구조는 다음 흐름으로 잡았다.

```text
프로젝트 소개
→ Live Service
→ Architecture image
→ 주요 기능
→ Data Pipeline
→ Architecture
→ Infrastructure / Deployment
→ Observability
→ Agent Workflow
→ 주요 설계 결정
→ Documentation
→ Local Development
```

구현 시 근거로 확인한 문서는 다음과 같다.

- `docs/ARCHITECTURE.md`
- `docs/architecture/overview.md`
- `docs/architecture/pipeline.md`
- `docs/architecture/k3s-runtime.md`
- `docs/architecture/domains.md`
- `docs/RUNBOOK.md`
- `docs/runbooks/cronjobs.md`
- `k8s/news-api.yaml`
- `k8s/monitoring/kube-prometheus-stack-values.yaml`
- `.github/workflows/docker-build.yml`

README에는 실제 manifest와 문서로 확인한 사실만 적었다.

- `news-api` Deployment는 `replicas: 2`다.
- backend Ingress는 Traefik과 cert-manager를 사용하며
  `api.newslab.ai.kr` host를 포함한다.
- backend와 CronJob image는 `seocj/news-api:latest`를 참조한다.
- CronJob은 RSS collector, Daily Topic, Three-day Topic, Weekly Topic으로
  분리되어 있다.
- Docker workflow는 `linux/arm64` image를 Docker Hub로 push한다.
- Monitoring values에서는 Alertmanager가 disabled이고, Prometheus/Grafana,
  Prometheus Operator, kube-state-metrics가 `observability=true` node selector를
  사용한다.

Frontend `news-lab-web x2`는 backend repository만으로는 처음에 검증할 수
없었으므로 README에는 backend repo 단독 근거로 frontend replica를 증명하지
않는다고 명시했다. 이후 사람이 제공한 verification log에서
`news-lab-web-deployment.yaml`의 `replicas: 2`가 확인됐다.

## 대안 검토

- 기존 README에 endpoint 목록만 조금 보강하는 방식
  - 장점: 변경량이 작다.
  - 단점: task 목표인 포트폴리오 관문 문서가 되기 어렵고, pipeline과 운영 경험이
    계속 하단에 묻힌다.
- Architecture 문서를 대폭 확장하고 README에는 링크만 두는 방식
  - 장점: 상세 정보의 중복을 줄일 수 있다.
  - 단점: 외부 방문자가 README 상단에서 프로젝트 가치를 바로 이해하기 어렵다.
- 운영 수치와 성능 지표를 추가하는 방식
  - 장점: 포트폴리오 문서의 임팩트가 커 보일 수 있다.
  - 단점: 측정 시점과 근거가 없는 수치는 task에서 금지한 과장이다.
- README에 아키텍처 이미지만 크게 두고 설명을 줄이는 방식
  - 장점: 시각적으로 빠르게 구조를 보여줄 수 있다.
  - 단점: GitHub 화면에서 작은 글자가 읽기 어려울 수 있고, 이미지 안의 모든
    내용을 검증 문장으로 대체할 수 없다.

## 선택한 접근과 근거

선택한 접근은 README 자체를 독립적으로 읽히는 포트폴리오 관문으로 재작성하고,
세부 근거는 기존 architecture/runbook/verification 문서로 연결하는 방식이다.

근거는 다음과 같다.

- Task의 목표가 README 상단만으로 서비스, pipeline, 운영 구조, 설계 판단,
  근거 문서를 이해할 수 있게 만드는 것이었다.
- 프로젝트의 현재 운영 구조는 이미 `docs/architecture/`, `docs/runbooks/`,
  `k8s/`, `.github/workflows/`에 나뉘어 있으므로 README는 이를 압축해서 연결하는
  역할이 적합하다.
- 측정하지 않은 비용, 처리량, latency, availability 같은 수치를 넣지 않는 것이
  검증 가능한 포트폴리오 문서에 더 맞다.
- GitHub Actions image push와 K3s rollout을 분리해서 설명해야 실제 운영 경계와
  human approval workflow를 과장하지 않는다.

## 트레이드오프

- README가 이전보다 길어졌다. 대신 방문자가 프로젝트 가치와 운영 구조를 README
  안에서 바로 파악할 수 있다.
- 세부 endpoint 목록은 README 중심에서 밀려났다. 대신 API 자체 변경은 없고,
  README는 서비스와 운영 구조 설명에 집중한다.
- Frontend manifest는 backend repo 안에서 확인되지 않는 영역이어서 처음에는
  제한 사항으로 남겼다. 이후 사람이 제공한 frontend replica log는 verification
  근거로 기록했지만, production reachability까지 완료된 것으로 확장하지 않았다.
- Architecture image를 저장소에 추가해 binary asset이 늘었다. 대신 README 첫
  화면에서 전체 운영 구조를 더 빠르게 전달할 수 있다.
- 운영 변경과 production verification을 수행하지 않았기 때문에 전체 verification
  status는 `pending`이다. 문서 작업의 로컬 정합성은 확인했지만 실제 서비스
  접근성은 별도 사람 검증으로 남긴다.

## 테스트

- 실제 test와 verification 결과의 source of truth는
  `docs/verification/docs-readme-portfolio-refresh.md`다.
- Application code, DB schema, API contract, K3s manifest, GitHub Actions
  workflow 동작은 변경하지 않았으므로 application 전체 테스트는 실행하지 않았다.
- 실행한 주요 로컬 검증은 다음과 같다.
  - 현재/이전 도메인 패턴 검색
  - backend Deployment/Service/Ingress와 replica 확인
  - RSS/Daily/Three-day/Weekly pipeline과 CronJob 근거 확인
  - Traefik, cert-manager, Tailscale, Prometheus, Grafana,
    kube-state-metrics, node-exporter 근거 확인
  - GitHub Actions Docker build/push workflow 확인
  - `docs/images/newslab-architecture.png` 존재 확인
  - README image reference와 alt text 확인
  - README 내부 문서 링크 대상 파일 존재 확인
  - 근거 없는 비용, 처리량, latency, availability, user count, fixed test count
    문구가 없는지 확인
  - `file`과 `cmp`로 README용 image가 원본 PNG와 동일한지 확인
  - `git diff --check`
  - 변경 범위가 README와 문서/이미지 asset 중심인지 확인

검증 결과 요약:

- `git diff --check`: passed
- README old-domain current-address 제거: passed
- README 내부 링크와 이미지 경로 확인: passed
- backend `news-api replicas: 2` manifest 근거 확인: passed
- frontend `news-lab-web replicas: 2`: 사람이 제공한 verification log로 확인
- production reachability: pending

## 운영 반영

- 운영 반영은 수행하지 않았다.
- 실행하지 않은 작업:
  - production `curl`
  - DNS lookup
  - TLS certificate status check
  - `kubectl apply`
  - `kubectl rollout`
  - deployment/restart/object 변경
  - Docker push
  - GitHub Actions run
  - Supabase SQL
  - DB write
  - `git push`
  - `git merge`

이번 변경은 README와 문서/이미지 asset 중심이며, 운영 자원에는 직접 영향을 주지
않는다. Production reachability와 최종 rollout 확인은 operator-provided log가
있을 때만 완료로 기록한다.

## README 업데이트 판단

README 업데이트가 필요했다.

판단 근거:

- task의 핵심 목표가 README를 포트폴리오 관문 문서로 개선하는 것이었다.
- 기존 README는 현재 운영 도메인과 맞지 않는 이전 domain을 포함했다.
- 실제 구현된 pipeline, K3s 운영 구조, observability, CI image 발행, agent
  workflow가 README에서 충분히 드러나지 않았다.
- 외부 방문자가 세부 작업 기록을 모두 읽지 않아도 핵심 architecture/runbook과
  verification 문서로 이동할 수 있어야 했다.

README에는 검증된 운영 구조만 적고, 생산 환경 접속 완료나 운영 rollout 완료는
주장하지 않았다.

## 확인 결과

- README는 현재 서비스 주소를 `newslab.ai.kr`, `www.newslab.ai.kr`,
  `api.newslab.ai.kr`로 표시한다.
- README는 이전 `api.dev-scj.site`를 현재 운영 주소로 표시하지 않는다.
- README는 Daily, Three-day, Weekly Topic pipeline의 차이를 설명한다.
- README는 backend K3s manifest 근거로 `news-api replicas: 2`를 설명한다.
- 사람이 제공한 verification log에서 frontend `news-lab-web replicas: 2`가
  확인됐다.
- README는 GitHub Actions image push를 자동 K3s CD로 과장하지 않는다.
- README는 Alertmanager가 enabled인 것처럼 설명하지 않는다.
- README는 측정하지 않은 비용, 처리량, latency, availability, user count, test
  count를 추가하지 않는다.
- Approved fixes 문서에는 승인된 fix가 없으므로 별도 approved fix 적용은 없다.
- Verification 전체 상태는 production reachability가 남아 있어 `pending`이다.

## 이번 단계의 의미

- README가 단순한 API 목록에서 프로젝트 운영 경험을 설명하는 진입 문서로
  바뀌었다.
- NewsLab의 핵심 차별점인 multi-window Topic pipeline, hybrid K3s 운영,
  observability, human-in-the-loop 운영 원칙을 한 화면에서 설명할 수 있게 됐다.
- 운영 주장과 검증 근거를 분리해, 포트폴리오 문서라도 과장 없이 유지할 수 있는
  기준을 세웠다.
- 기존 architecture/runbook/verification/devlog 문서를 README에서 탐색 가능한
  evidence chain으로 연결했다.

## 포트폴리오용 요약

NewsLab은 RSS 기사를 수집해 원문, embedding, Topic 요약을 Supabase/PostgreSQL에
저장하고 FastAPI와 웹 서비스로 제공하는 개인 운영 뉴스 플랫폼이다. 이번 작업은
README를 외부 방문자용 관문 문서로 재구성해 Daily / Three-day / Weekly Topic
pipeline, Oracle Cloud A1 + Raspberry Pi 기반 K3s 운영, Traefik/cert-manager
TLS, Prometheus/Grafana 관측성, GitHub Actions/Docker Hub image 발행, agent
workflow와 human approval 운영 원칙을 한 번에 이해할 수 있게 만들었다.

## 다음 단계 후보

- 사람이 production reachability log를 제공하면 README live service 검증 상태를
  verification 문서에 추가한다.
- frontend manifest가 backend 운영 문서와 같은 repository 또는 문서 체계로
  편입되면 frontend runtime 근거 링크를 README에 더 직접적으로 연결한다.
- README 이미지의 작은 글자가 GitHub 화면에서 충분히 읽히지 않는다면 별도
  task로 이미지 최적화 또는 보조 diagram/text를 검토한다.
- Devlog 초안을 Notion에 옮길 때 production verification pending 상태가
  완료처럼 보이지 않도록 별도 체크박스로 분리한다.
- 향후 Argo CD, Alertmanager, semantic search 같은 계획은 구현 완료 후에만
  README current feature로 반영한다.
