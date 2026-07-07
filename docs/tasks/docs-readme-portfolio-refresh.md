# Task: NewsLab README 포트폴리오 관문 개선

## Goal

현재 NewsLab README는 API endpoint와 초기 개발 정보 중심으로 작성되어 있어, 실제 프로젝트가 갖춘 다음 내용을 충분히 보여주지 못한다.

- Daily / Three-day / Weekly Topic pipeline
- Oracle Cloud ARM과 Raspberry Pi로 구성한 3노드 K3s 클러스터
- Backend와 Frontend의 다중 replica 운영
- Traefik과 cert-manager를 통한 외부 트래픽 및 TLS 처리
- Prometheus와 Grafana 기반 관측성
- GitHub Actions와 Docker Hub를 이용한 이미지 발행
- Agent가 구현과 검토를 보조하고 사람이 운영 변경을 승인하는 workflow
- 장기간 운영하며 축적한 Architecture, Runbook, Verification, Devlog 문서

또한 현재 서비스는 `newslab.ai.kr`과 `api.newslab.ai.kr`을 사용하지만, README 일부에는 이전 도메인과 과거 운영 상태가 남아 있을 가능성이 있다.

이번 작업의 목표는 README를 채용담당자와 면접관이 저장소에 진입했을 때 확인하는 **포트폴리오 관문 문서**로 재구성하는 것이다.

README 상단을 확인하는 것만으로 다음 내용을 파악할 수 있어야 한다.

```
NewsLab이 어떤 서비스인지
→ 실제 서비스가 운영되고 있는지
→ 뉴스가 어떤 pipeline을 통해 Topic으로 생성되는지
→ 어떤 인프라에서 운영되는지
→ 프로젝트에서 어떤 기술적 판단과 운영 경험을 얻었는지
→ 상세 근거 문서는 어디에서 확인할 수 있는지
```

README에 작성하는 내용은 실제 코드, K3s manifest, GitHub Actions, 운영 문서와 교차 검증한다.

측정하지 않았거나 근거가 없는 성능, 비용, 처리량과 운영 수치는 추가하지 않는다.

## Scope

- 기존 `README.md`의 구조와 내용을 조사한다.
- README에 남아 있는 이전 도메인과 오래된 운영 정보를 확인한다.
- 현재 운영 주소를 정확히 반영한다.

```
Frontend
https://newslab.ai.kr
https://www.newslab.ai.kr

Backend
https://api.newslab.ai.kr
```

- README 상단에 NewsLab의 목적을 설명하는 간결한 소개를 작성한다.
- 실제 서비스로 이동할 수 있는 링크를 상단에 배치한다.
- NewsLab 전체 아키텍처 이미지를 저장소에 추가하고 README에 연결한다.
- 이미지의 내용이 현재 운영 구조와 일치하는지 확인한다.
- 주요 사용자 기능을 정리한다.
- RSS 수집부터 Topic 제공까지의 데이터 pipeline을 정리한다.
- Daily / Three-day / Weekly Topic의 역할을 설명한다.
- 주요 기술 스택을 역할별로 정리한다.
- 현재 K3s 클러스터 구성을 설명한다.
- Backend와 Frontend Deployment 및 replica 수를 실제 manifest와 대조한다.
- Traefik, cert-manager, Tailscale, Supabase의 역할을 설명한다.
- Prometheus와 Grafana 기반 관측성 구성을 설명한다.
- GitHub Actions와 Docker Hub 이미지 발행 흐름을 설명한다.
- Agent workflow와 Human approval 운영 원칙을 간결하게 설명한다.
- 프로젝트에서 선택한 주요 설계 판단과 trade-off를 정리한다.
- Architecture, Runbook, Task, Verification, Review, Devlog 문서로 이동할 수 있는 문서 인덱스를 추가한다.
- 외부 방문자가 우선 확인할 만한 핵심 운영 기록을 선별해 연결한다.
- README의 링크, 이미지 경로, Markdown 형식과 사실 정합성을 검증한다.

README의 권장 정보 구조는 다음을 기준으로 검토한다.

```
프로젝트 소개
→ Live Service
→ 대표 화면 또는 아키텍처
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

실제 저장소의 기존 README와 문서 구조를 조사한 뒤 중복되거나 불필요한 Section은 조정할 수 있다.

## Do not change

- FastAPI Application 코드
- Router
- Service
- Repository
- ORM Model
- Database query
- RSS Collector
- Raw article extraction
- Embedding 생성 로직
- Clustering 알고리즘
- 대표 기사 및 관련 기사 선정 정책
- Daily Topic pipeline
- Three-day Topic pipeline
- Weekly Topic pipeline
- AI 요약 로직
- Prompt
- Provider 및 Model 설정
- Frontend Application 코드
- K3s Deployment 동작
- K3s Service 동작
- K3s Ingress 동작
- Traefik 설정
- cert-manager 설정
- GitHub Actions workflow 동작
- Docker build 및 image 발행 방식
- Dockerfile
- 환경 변수
- Secret
- Supabase 설정
- DB Schema
- Migration
- 기존 Public API 계약
- 운영 환경의 Resource
- Production Deployment

문서 조사 과정에서 코드, manifest 또는 운영 설정의 별도 문제가 발견되더라도 이번 작업에서 함께 수정하지 않는다.

다음 내용은 근거가 확인되지 않으면 README에 작성하지 않는다.

- 월 운영 비용이 정확히 0원이라는 주장
- 일일 평균 기사 처리량
- 누적 기사 수
- 누적 Topic 수
- 실패율
- 평균 응답 시간
- p95 또는 p99 응답 시간
- pipeline 평균 처리 시간
- 테스트 개수
- 장애 복구 시간
- 가용성 수치
- 사용자 수

README에 수치를 작성해야 한다면 측정 기준, 측정 시점과 근거를 확인한 뒤 사용한다.

테스트 개수처럼 지속적으로 변하는 값은 고정 수치로 작성하지 않는 것을 우선한다.

## Expected files

실제 Repository 구조를 먼저 조사한 뒤 필요한 파일만 수정하거나 추가한다.

예상 주요 변경 파일:

```
README.md
docs/images/newslab-architecture.png
```

아키텍처 이미지 저장 경로는 기존 이미지 자산 구조를 조사한 뒤 확정한다.

기존 규칙과 충돌하지 않는다면 다음 경로를 우선 사용한다.

```
docs/images/newslab-architecture.png
```

필요한 경우에만 다음 문서를 수정한다.

```
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

다만 이번 작업의 목적은 README 개선이므로, 기존 문서 링크가 깨졌거나 README와 명백히 충돌하는 경우가 아니라면 상세 문서를 광범위하게 다시 작성하지 않는다.

작업용 자동 생성 문서는 기존 `scripts/new_agent_task.sh` 계약을 따른다.

```
docs/tasks/
docs/reviews/
docs/fixes/
docs/verification/
docs/pr/
docs/devlog/
```

README에서 사용할 이미지 파일은 의미를 알 수 없는 UUID 또는 임시 이름으로 저장하지 않는다.

## DB changes

없음.

- Database Migration 없음
- Schema 변경 없음
- Table 변경 없음
- Column 변경 없음
- Constraint 변경 없음
- Index 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음
- 데이터 조회를 위한 별도 Script 실행 없음

README에 DB 구조를 설명할 경우 기존 schema와 문서를 근거로 작성한다.

## API changes

없음.

- 새로운 FastAPI endpoint 추가 없음
- 기존 endpoint 변경 없음
- Request schema 변경 없음
- Response schema 변경 없음
- Public API 계약 변경 없음
- API version 변경 없음
- API 배포 없음

README에 API 주소와 주요 endpoint를 설명할 수 있지만 API 자체는 변경하지 않는다.

## Test commands

이번 작업은 문서와 이미지 자산 변경이므로 Application 전체 테스트 실행을 기본 필수 조건으로 두지 않는다.

먼저 README와 현재 운영 상태의 정합성을 조사한다.

이전 도메인과 현재 도메인 확인:

```bash
rg -n \
  "api\.dev-scj\.site|dev-scj\.site|newslab\.site|newslab\.ai\.kr|api\.newslab\.ai\.kr" \
  README.md docs k8s app scripts .github
```

K3s Deployment, Service, Ingress와 replica 확인:

```bash
rg -n \
  "kind: Deployment|kind: Service|kind: Ingress|replicas:|name: news-api|name: news-lab-web" \
  k8s
```

Topic pipeline과 CronJob 명칭 확인:

```bash
rg -n \
  "CronJob|daily|three.day|three_day|weekly|RSS|collector|topic.pipeline" \
  README.md docs k8s app scripts .github
```

관측성과 네트워크 구성 확인:

```bash
rg -n \
  "Prometheus|Grafana|kube-state-metrics|node-exporter|Traefik|cert-manager|Tailscale" \
  README.md docs k8s
```

GitHub Actions와 image registry 구성 확인:

```bash
find .github/workflows -maxdepth 1 -type f -print | sort
```

```bash
rg -n \
  "docker|Docker Hub|buildx|push|ARM64|linux/arm64" \
  .github README.md docs
```

기존 이미지 자산 확인:

```bash
find . -type f \( \
  -iname "*.png" -o \
  -iname "*.jpg" -o \
  -iname "*.jpeg" -o \
  -iname "*.webp" -o \
  -iname "*.svg" \
\) | sort
```

추가한 아키텍처 이미지 존재 여부 확인:

```bash
test -f docs/images/newslab-architecture.png
```

README 이미지 참조 확인:

```bash
rg -n \
  "newslab-architecture\.png|!\.*Architecture|!\[.*아키텍처" \
  README.md
```

README에 작성한 내부 문서 링크의 대상 파일이 실제로 존재하는지 확인한다.

필요하면 다음과 같은 방식으로 개별 확인한다.

```bash
test -f docs/ARCHITECTURE.md
test -f docs/RUNBOOK.md
```

Markdown과 공백 오류 확인:

```bash
git diff --check
```

변경 범위 확인:

```bash
git status --short
```

```bash
git diff -- README.md docs/images docs/ARCHITECTURE.md docs/RUNBOOK.md
```

오래된 도메인이 현재 운영 주소처럼 README에 남아 있지 않은지 최종 확인한다.

```bash
rg -n \
  "api\.dev-scj\.site|dev-scj\.site|newslab\.site" \
  README.md
```

이전 도메인을 마이그레이션 이력이나 과거 장애 설명으로 의도적으로 언급하는 경우에는 현재 주소로 오해되지 않도록 문맥을 명확히 작성한다.

README에 Application의 구체적인 테스트 결과나 테스트 개수를 새로 주장하는 경우에만 실제 테스트를 실행한다.

기존 후보:

```bash
python -m compileall app scripts tests
```

```bash
python -m unittest discover -s tests
```

Repository가 현재 pytest를 표준으로 사용한다면 기존 Convention에 맞춰 다음 명령을 사용할 수 있다.

```bash
python -m pytest
```

실행하지 않은 명령은 Verification에 성공으로 기록하지 않는다.

## Acceptance criteria

- README 상단에서 NewsLab이 어떤 서비스인지 한 문장으로 이해할 수 있다.
- README 상단에서 실제 서비스 주소를 확인할 수 있다.
- Frontend 주소가 현재 운영 도메인과 일치한다.
- Backend 주소가 현재 운영 도메인과 일치한다.
- 이전 `api.dev-scj.site`가 현재 운영 주소로 표현되지 않는다.
- README의 프로젝트 설명이 단순한 API endpoint 목록에 머물지 않는다.
- 주요 사용자 기능이 정리되어 있다.
- 오늘의 Topic, 최근 3일 Topic과 지난주 Topic이 설명되어 있다.
- RSS 수집부터 Topic 제공까지의 데이터 흐름을 확인할 수 있다.
- Embedding, clustering, 기사 선정, 원문 확보와 AI 요약의 역할이 과장 없이 설명되어 있다.
- Daily / Three-day / Weekly pipeline의 구분이 명확하다.
- 전체 아키텍처 이미지가 저장소 내부의 명확한 경로에 저장되어 있다.
- README에서 아키텍처 이미지가 정상적인 상대 경로로 참조된다.
- 이미지 대체 텍스트가 의미 있게 작성되어 있다.
- 아키텍처 이미지의 도메인, 노드, Deployment, 외부 시스템과 운영 경로가 현재 상태와 일치한다.
- Oracle Cloud ARM과 Raspberry Pi로 구성된 3노드 K3s 클러스터가 설명되어 있다.
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`의 역할이 과장 없이 설명되어 있다.
- `news-api` replica 수가 실제 manifest와 일치한다.
- `news-lab-web` replica 수가 실제 manifest와 일치한다.
- Traefik의 Ingress Controller 역할이 설명되어 있다.
- cert-manager와 Let's Encrypt의 TLS 인증서 발급 관계가 설명되어 있다.
- Tailscale이 외부 Public ingress가 아니라 운영자 접근과 노드 연결에 사용된다는 점이 혼동 없이 설명되어 있다.
- Supabase PostgreSQL과 pgvector의 역할이 설명되어 있다.
- Prometheus와 Grafana 기반 관측성 구성이 실제 배포 상태와 일치한다.
- node-exporter와 kube-state-metrics를 언급하는 경우 실제 구성과 일치한다.
- GitHub Actions와 Docker Hub의 image build·push 흐름이 실제 workflow와 일치한다.
- 현재 수동 rollout 또는 사람 승인 절차를 완전 자동 CD처럼 표현하지 않는다.
- Agent가 구현과 검토를 보조하고 고위험 운영 변경은 사람이 수행한다는 원칙이 설명되어 있다.
- Human-in-the-loop 운영 원칙을 자동화 부족을 숨기기 위한 표현으로 과장하지 않는다.
- 주요 설계 결정 또는 운영 trade-off를 최소한 한 개 이상 설명한다.
- Architecture와 Runbook 문서로 이동할 수 있다.
- Task, Verification, Review와 Devlog 기록의 목적을 확인할 수 있다.
- 외부 방문자가 60개 이상의 작업 기록을 순서대로 모두 읽지 않아도 주요 근거 문서로 이동할 수 있다.
- README에 연결한 내부 파일이 실제로 존재한다.
- 깨진 이미지 경로가 없다.
- 깨진 상대 링크가 없다.
- 측정하지 않은 성능 수치가 추가되지 않는다.
- 확인하지 않은 비용 수치가 추가되지 않는다.
- 확인하지 않은 처리량 수치가 추가되지 않는다.
- 테스트 개수를 고정 수치로 작성한 경우 실제 결과로 검증되어 있다.
- Application 코드가 변경되지 않는다.
- DB와 API가 변경되지 않는다.
- K3s manifest의 동작이 변경되지 않는다.
- GitHub Actions workflow의 동작이 변경되지 않는다.
- Production deploy를 수행하지 않는다.
- `git diff --check`가 통과한다.
- 변경 범위가 README, 이미지와 필요한 최소 문서에 한정된다.
- 실제 조사 결과, 실행 명령과 검증 결과는 Verification에 기록된다.
- Task 문서에는 계획만 유지된다.

## Notes

- README는 이력서나 포트폴리오에서 GitHub 저장소로 이동한 방문자가 가장 먼저 확인하는 문서로 간주한다.
- README는 내부 개발 일지가 아니라 외부 방문자를 위한 프로젝트 진입 문서로 작성한다.
- README 상단은 약 30초 안에 다음 질문에 답할 수 있는 구조를 목표로 한다.

```
무엇을 만든 프로젝트인가?
실제로 동작하는가?
어떤 기술적 문제가 있는가?
어떤 구조로 운영되는가?
작성자는 무엇을 직접 설계하고 운영했는가?
근거는 어디에서 확인할 수 있는가?
```

- 기술 이름을 길게 나열하기보다 기술이 실제로 어떤 역할을 수행하는지 설명한다.
- 포트폴리오 문장을 그대로 복사하지 않고 GitHub README에 맞게 압축한다.
- README에 모든 작업 차수를 나열하지 않는다.
- 상세 구현 과정과 운영 기록은 `docs/`로 연결한다.
- 대표적인 Architecture, 장애 대응, pipeline 개선과 Agent workflow 기록만 선별한다.
- Architecture 이미지는 다음 파일을 사용한다.

```
docs/images/newslab-architecture.png
```

- README 이미지 참조는 다음 형식을 우선한다.

```markdown
![NewsLab 전체 아키텍처
```

- 업로드된 원본 이미지의 임시 파일명이나 UUID를 README 경로로 사용하지 않는다.
- 이미지 원본을 저장소 경로에 복사할 때 내용이나 해상도를 임의로 변경하지 않는다.
- 별도의 이미지 수정이 필요하면 이번 README 작업과 분리할지 먼저 판단한다.
- Architecture 이미지의 작은 글자가 GitHub 화면에서 읽기 어려운 경우 전체 이미지 아래에 핵심 구성 요소를 텍스트로 함께 설명한다.
- README에서 아키텍처를 이미지 하나에만 의존하지 않는다.
- 서비스 링크가 외부에서 접근되지 않는 상태라면 운영 중이라고 단정하지 않고 현재 상태를 확인한다.
- 도메인, TLS와 API 응답의 실제 운영 검증은 사람이 수행한다.
- Agent는 Production 상태를 추측하지 않는다.
- 과거 도메인을 기록 목적으로 남길 경우 `이전 운영 주소`임을 명확히 표시한다.
- 현재 Alertmanager가 구성되지 않았다면 완전한 alerting 체계가 있는 것처럼 표현하지 않는다.
- Prometheus와 Grafana가 있다는 이유만으로 자동 장애 대응이 구현됐다고 표현하지 않는다.
- GitHub Actions가 image를 발행하더라도 K3s rollout이 사람에 의해 수행된다면 이를 자동 CD로 표현하지 않는다.
- 향후 Argo CD, Alertmanager, Operations Agent와 semantic search를 추가할 계획이 있더라도 현재 구현된 기능처럼 작성하지 않는다.
- README 조사 중 발견한 별도 개선 사항은 이번 범위에 포함하지 않고 후속 작업 후보로 기록한다.
- README나 Architecture 문서에 포함된 공개 정보에 Secret, 내부 credential, private token과 민감한 접속 정보가 포함되지 않도록 확인한다.
- Tailscale IP, kubeconfig 경로와 내부 운영 명령은 공개 README에 반드시 필요한 수준만 작성한다.
- 실제 운영 검증 결과는 Verification에 기록하되 Task에는 추가하지 않는다.
- `UNIT-01 분석 결과`와 같은 조사 내용을 Task 하단에 추가하지 않는다.

## Implementation Units

- [x] UNIT-01: 기존 README, 운영 도메인, K3s manifest, CI, 관측성 문서와 이미지 자산 조사
- [x] UNIT-02: README 정보 구조 재작성과 NewsLab 전체 아키텍처 이미지 추가
- [x] UNIT-03: 도메인·인프라·파이프라인 사실 정합성, 내부 링크, 이미지 경로와 변경 범위 검증 (사람이 수행 필요: frontend `news-lab-web` replica manifest 근거 또는 이미지 수정 판단)
