# NewsLab README 포트폴리오 관문 개선

## 작업 내용

- README를 API endpoint 중심 문서에서 외부 방문자용 포트폴리오 관문 문서로 재구성했다.
- 현재 서비스 주소, 데이터 pipeline, K3s 운영 구조, 관측성, GitHub Actions/Docker Hub 이미지 발행 흐름, Agent workflow, 주요 설계 결정을 README 상단 흐름에서 확인할 수 있게 정리했다.
- NewsLab 전체 아키텍처 이미지를 `docs/images/newslab-architecture.png`로 추가하고 README에서 상대 경로로 연결했다.
- 작업 source of truth, verification, review/fix/pr/devlog workflow 문서를 branch 전용 경로에 추가했다.

## 주요 변경 사항

- `README.md`
  - 현재 서비스 URL을 `https://newslab.ai.kr`, `https://www.newslab.ai.kr`, `https://api.newslab.ai.kr`로 정리했다.
  - 이전 `api.dev-scj.site`를 현재 운영 주소로 표현하던 내용을 제거했다.
  - Daily / Three-day / Weekly Topic pipeline 차이와 RSS 수집부터 FastAPI 제공까지의 데이터 흐름을 설명했다.
  - Oracle Cloud A1 + Raspberry Pi 기반 3-node K3s 운영 구조, Traefik, cert-manager, Tailscale, Supabase/pgvector, Prometheus/Grafana 역할을 정리했다.
  - GitHub Actions가 `linux/arm64` backend image를 Docker Hub로 발행하지만 K3s rollout은 자동 CD로 주장하지 않도록 명시했다.
  - Architecture, Runbook, pipeline/design, workflow, verification 문서 링크를 추가했다.
- `docs/images/newslab-architecture.png`
  - 기존 원본 이미지 `images/image.png`와 동일한 PNG를 README용 저장소 경로로 복사했다.
- `docs/tasks/main.md`
  - 현재 task를 `docs-readme-portfolio-refresh.md`로 갱신했다.
- workflow artifact
  - `docs/tasks/docs-readme-portfolio-refresh.md`
  - `docs/verification/docs-readme-portfolio-refresh.md`
  - `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`
  - `docs/reviews/docs-readme-portfolio-refresh-antigravity.md`
  - `docs/reviews/docs-readme-portfolio-refresh-coderabbit.md`
  - `docs/devlog/docs-readme-portfolio-refresh.md`
  - `docs/pr/docs-readme-portfolio-refresh.md`

Approved fixes source of truth인 `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`에는 승인된 fix 항목이 없어 별도 fix 적용은 없었다.

## 추가/변경된 API

없음.

- FastAPI endpoint 추가/변경 없음
- Request/response schema 변경 없음
- Public API 계약 변경 없음
- API 배포 없음

README에는 현재 Backend API 주소를 문서화했지만 API 동작은 변경하지 않았다.

## DB 변경 사항

없음.

- DB migration 없음
- Schema/table/column/index/constraint 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음

## README 영향

- README 영향 있음.
- 이번 PR의 핵심 변경은 README를 프로젝트 소개, live service, 아키텍처 이미지, 주요 기능, data pipeline, infrastructure/deployment, observability, agent workflow, design decision, documentation, local development 흐름으로 재작성한 것이다.
- README의 운영 주장과 수치는 기존 코드, K3s manifest, GitHub Actions workflow, architecture/runbook/verification 문서에 근거한 내용으로 제한했다.
- 측정하지 않은 비용, 처리량, latency, availability, user count, 고정 test count는 추가하지 않았다.

## 테스트

- `docs/verification/docs-readme-portfolio-refresh.md` 기준으로 다음 로컬 검증을 수행했다.
- `rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site|newslab\.ai\.kr|api\.newslab\.ai\.kr" README.md docs k8s app scripts .github`
  - README는 현재 서비스 URL만 current address로 표시하고, 이전 도메인은 README current address에서 제거됨.
- `rg -n "kind: Deployment|kind: Service|kind: Ingress|replicas:|name: news-api|name: news-lab-web" k8s`
  - backend `news-api` Deployment/Service/Ingress와 `replicas: 2` 확인.
- `rg -n "CronJob|daily|three.day|three_day|weekly|RSS|collector|topic.pipeline" README.md docs k8s app scripts .github`
  - README pipeline 설명과 RSS/Daily/Three-day/Weekly CronJob 및 entrypoint 근거 확인.
- `rg -n "Prometheus|Grafana|kube-state-metrics|node-exporter|Traefik|cert-manager|Tailscale" README.md docs k8s`
  - README 설명과 static config/document evidence 정합성 확인.
- `find .github/workflows -maxdepth 1 -type f -print | sort`
  - `.github/workflows/docker-build.yml` 확인.
- `rg -n "docker|Docker Hub|buildx|push|ARM64|linux/arm64" .github README.md docs`
  - Docker Hub image build/push와 `linux/arm64` workflow 설명 정합성 확인.
- `test -f docs/images/newslab-architecture.png`
  - README용 architecture image 존재 확인.
- `rg -n "newslab-architecture\.png|!\.*Architecture|!\[.*아키텍처" README.md`
  - README image reference와 alt text 확인.
- `test -f ...`
  - README-linked internal documentation targets 존재 확인.
- `rg -n "0원|cost|비용|일일 평균|누적|실패율|평균 응답|p95|p99|처리량|가용성|사용자 수|테스트 [0-9]+|[0-9]+ tests|availability|latency" README.md`
  - 근거 없는 비용/성능/처리량/가용성/user count/test count 주장 없음 확인.
- `file docs/images/newslab-architecture.png images/image.png`
  - 두 이미지가 PNG, `2414 x 1300`, 8-bit RGBA, non-interlaced임을 확인.
- `cmp -s images/image.png docs/images/newslab-architecture.png && echo identical`
  - README용 이미지가 원본과 동일함을 확인.
- `git diff --check`
  - whitespace error 없음.
- `git diff --name-only -- README.md docs/ARCHITECTURE.md docs/RUNBOOK.md app scripts k8s .github db requirements.txt Dockerfile docker-compose.yml`
  - application code, scripts, DB, K3s manifest, GitHub Actions workflow, Dockerfile, requirements 변경 없음 확인.

Application 전체 테스트는 실행하지 않았다. 이번 작업은 문서와 이미지 자산 변경이며 application code, DB, API, pipeline 로직 변경이 없다.

## 확인 결과

- README는 더 이상 이전 도메인을 현재 운영 주소로 표시하지 않는다.
- README 내부 문서 링크와 architecture image 경로가 로컬에서 확인됐다.
- `news-api` backend replica 수는 backend repo의 `k8s/news-api.yaml` 근거와 일치한다.
- 사람이 제공한 frontend manifest 확인 로그에서 `news-lab-web-deployment.yaml`의 `replicas: 2`가 확인됐다.
- Architecture image는 `newslab.ai.kr`, Traefik/Ingress/TLS/Service/Pod path, Oracle Cloud A1 + Raspberry Pi 3-node K3s cluster, Tailscale, Docker Hub/GitHub Actions, Supabase PostgreSQL + pgvector, cert-manager/Let's Encrypt, monitoring components를 포함한다.
- Production `curl`, DNS lookup, TLS check, `kubectl`, rollout, deployment, Docker push, GitHub Actions run, Supabase SQL, DB write, `git push`, `git merge`는 실행하지 않았다.
- `docs/verification/docs-readme-portfolio-refresh.md`의 전체 verification status는 production reachability 확인이 남아 있어 `pending`이다.

## 비고

- PR merge 완료를 주장하지 않는다.
- Production deployment, K3s rollout, production verification 완료를 주장하지 않는다.
- Public reachability for `https://newslab.ai.kr`, `https://www.newslab.ai.kr`, `https://api.newslab.ai.kr`는 operator-provided production verification log가 제공되기 전까지 pending이다.
- Review 파일은 verification 통과 근거로 사용하지 않았다.
