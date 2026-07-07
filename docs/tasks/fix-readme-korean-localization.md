# Task: NewsLab README 한글 표기 및 용어 정합성 개선

## Goal

현재 NewsLab README는 프로젝트 내용 자체는 충분히 보강되었지만, 한글과 영어가 혼용되고 섹션 제목과 설명 문장의 상당 부분이 영어 중심으로 작성되어 있다.

이번 작업의 목표는 README의 전체 설명을 한국어 중심으로 정리하고, 기술명·고유명사·코드·명령어·파일명·API endpoint는 원문을 유지해 가독성과 전문성을 함께 확보하는 것이다.

README를 처음 확인하는 국내 채용담당자와 면접관이 별도의 해석 없이 다음 내용을 자연스럽게 이해할 수 있어야 한다.

- NewsLab이 어떤 서비스인지
- 어떤 데이터 파이프라인으로 토픽을 생성하는지
- 어떤 인프라에서 운영되는지
- 어떤 설계 판단과 운영 경험이 반영되었는지
- 상세 문서와 근거를 어디에서 확인할 수 있는지

이번 작업은 표현과 용어 정합성을 개선하는 문서 수정이며, 애플리케이션 기능·인프라 동작·API 계약은 변경하지 않는다.

## Scope

- `README.md`의 영어 중심 섹션 제목과 설명 문장을 한국어 중심으로 수정한다.
- 한글과 영어가 불규칙하게 섞인 표현을 일관된 기준으로 정리한다.
- 다음과 같은 일반 설명 용어는 한국어 표기를 우선한다.
  - Frontend → 프론트엔드
  - Backend → 백엔드
  - Architecture → 아키텍처
  - Data Pipeline → 데이터 파이프라인
  - Observability → 관측성
  - Infrastructure → 인프라
  - Deployment → 배포
  - Documentation → 문서
  - Design Decision → 설계 결정
  - Troubleshooting → 문제 해결 또는 장애 대응
  - Live Service → 운영 서비스
  - Key Features → 주요 기능
- 서비스 핵심 도메인 용어인 `Topic`은 첫 등장 시 `토픽(Topic)`으로 설명하고, 이후에는 `토픽` 표기를 우선한다.
- `Human-in-the-loop`는 최초 1회 `사람 승인 기반(Human-in-the-loop)`으로 설명하고 이후에는 문맥에 맞게 한국어 표현을 우선한다.
- 기술명과 제품명은 원문 표기를 유지한다.
  - FastAPI
  - Next.js
  - PostgreSQL
  - pgvector
  - Docker
  - K3s
  - Kubernetes
  - Traefik
  - Tailscale
  - Prometheus
  - Grafana
  - GitHub Actions
  - Docker Hub
  - Supabase
  - cert-manager
  - Let's Encrypt
- 코드, 명령어, 환경 변수, 파일 경로, 브랜치명과 API endpoint는 번역하지 않는다.
- 표의 헤더와 설명 문장은 한국어로 정리하되, 실제 리소스명과 node·Deployment 이름은 원문을 유지한다.
- 현재 README의 사실관계, 링크, 이미지 참조와 섹션 순서는 필요한 범위에서만 유지·정리한다.
- 문장 종결 방식과 용어 표기를 통일한다.
- 영어 표현을 유지해야 하는 경우 불필요한 중복 번역을 피하고, 국내 개발 문서에서 일반적으로 통용되는 표기를 사용한다.
- README 내부 링크와 이미지 경로가 수정 과정에서 깨지지 않았는지 확인한다.
- 변경 전후 diff를 검토해 내용 누락이나 사실 왜곡이 없는지 확인한다.

## Do not change

- README의 핵심 사실관계
- 운영 도메인
- 서비스 URL
- 아키텍처 이미지 파일
- 이미지 경로
- 내부 문서 링크 대상
- 데이터 파이프라인 구조
- K3s 노드 구성
- Deployment replica 수
- GitHub Actions와 Docker Hub의 이미지 발행 흐름
- Prometheus와 Grafana 구성 설명의 사실관계
- 사람 승인 기반 운영 원칙
- 주요 설계 결정의 의미
- Application 코드
- FastAPI router
- Service
- Repository
- ORM Model
- Database query
- RSS Collector
- Raw article extraction
- Embedding 생성 로직
- Clustering 로직
- Daily Topic pipeline
- Three-day Topic pipeline
- Weekly Topic pipeline
- AI 요약 로직
- Frontend Application 코드
- K3s manifest
- GitHub Actions workflow
- Dockerfile
- 환경 변수
- Secret
- DB schema
- Migration
- Public API 계약
- Production Deployment

영어 표현을 한국어로 바꾸는 과정에서 기술적 의미를 단순화하거나 과장하지 않는다.

다음 항목은 이번 작업 범위에 포함하지 않는다.

- 새로운 기능 설명 추가
- 정량 지표 추가
- 성능 수치 추가
- 비용 수치 추가
- 운영 현황 재측정
- 아키텍처 이미지 수정
- 문서 구조의 대규모 재설계
- 새로운 README 섹션 대량 추가
- 기존 상세 문서 전면 번역

## Expected files

예상 주요 변경 파일:

```
README.md
```

작업용 자동 생성 문서는 기존 `scripts/new_agent_task.sh` 계약에 따라 갱신할 수 있다.

```
docs/tasks/
docs/reviews/
docs/fixes/
docs/verification/
docs/pr/
docs/devlog/
```

다음 파일은 README 링크 정합성 문제나 명백한 용어 충돌이 확인되는 경우에만 최소 범위로 수정한다.

```
docs/ARCHITECTURE.md
docs/RUNBOOK.md
```

아키텍처 이미지는 이번 작업에서 변경하지 않는다.

```
docs/images/newslab-architecture.png
```

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

## API changes

없음.

- 새로운 endpoint 추가 없음
- 기존 endpoint 변경 없음
- Request schema 변경 없음
- Response schema 변경 없음
- Public API 계약 변경 없음
- API version 변경 없음
- API 배포 없음

## Test commands

README의 영어 중심 섹션과 혼용 표현을 확인한다.

```bash
rg -n \
  "^#{1,6} .*\b(Overview|Live Service|Key Features|Data Pipeline|Architecture|Infrastructure|Deployment|Observability|Agent Workflow|Design Decisions|Documentation|Local Development|Troubleshooting)\b" \
  README.md
```

일반 설명에서 불필요하게 남은 영어 중심 표현을 확인한다.

```bash
rg -n \
  "Frontend|Backend|Architecture|Data Pipeline|Observability|Infrastructure|Deployment|Documentation|Design Decision|Troubleshooting|Live Service|Key Features" \
  README.md
```

기술명과 고유명사가 유지됐는지 확인한다.

```bash
rg -n \
  "FastAPI|Next.js|PostgreSQL|pgvector|Docker|K3s|Kubernetes|Traefik|Tailscale|Prometheus|Grafana|GitHub Actions|Docker Hub|Supabase|cert-manager|Let's Encrypt" \
  README.md
```

운영 주소가 그대로 유지됐는지 확인한다.

```bash
rg -n \
  "https://newslab\.ai\.kr|https://www\.newslab\.ai\.kr|https://api\.newslab\.ai\.kr" \
  README.md
```

아키텍처 이미지 참조가 유지됐는지 확인한다.

```bash
rg -n \
  "docs/images/newslab-architecture\.png|NewsLab 전체 아키텍처" \
  README.md
```

오래된 도메인이 다시 포함되지 않았는지 확인한다.

```bash
rg -n \
  "api\.dev-scj\.site|dev-scj\.site|newslab\.site" \
  README.md
```

내부 문서 링크 대상이 유지됐는지 확인한다.

```bash
test -f docs/ARCHITECTURE.md
test -f docs/RUNBOOK.md
test -f docs/images/newslab-architecture.png
```

Markdown 공백과 형식 오류를 확인한다.

```bash
git diff --check
```

변경 범위를 확인한다.

```bash
git status --short
```

```bash
git diff -- README.md docs/ARCHITECTURE.md docs/RUNBOOK.md
```

애플리케이션 코드나 인프라 파일이 변경되지 않았는지 확인한다.

```bash
git diff --name-only -- app scripts k8s db .github Dockerfile docker-compose.yml requirements.txt
```

이번 작업은 문서 표현 수정이므로 Application 전체 테스트를 기본 필수 조건으로 두지 않는다.

README 수정 과정에서 코드나 동작을 함께 변경한 경우에만 저장소의 표준 테스트를 실제로 실행한다.

실행하지 않은 테스트는 Verification에 통과했다고 기록하지 않는다.

## Acceptance criteria

- README의 주요 섹션 제목이 한국어 중심으로 정리되어 있다.
- 일반 설명 문장이 한국어 중심으로 작성되어 있다.
- 한글과 영어가 불규칙하게 혼용된 표현이 줄어들었다.
- `프론트엔드`, `백엔드`, `아키텍처`, `데이터 파이프라인`, `관측성`, `인프라`, `배포`, `문서` 등의 표기가 일관된다.
- `Topic`은 최초 설명 이후 `토픽` 중심으로 사용된다.
- `Human-in-the-loop`는 최초 설명 시 한국어 의미가 함께 제시된다.
- FastAPI, Next.js, PostgreSQL, pgvector, Docker, K3s, Traefik, Tailscale, Prometheus, Grafana, GitHub Actions, Docker Hub, Supabase, cert-manager와 Let's Encrypt 등 고유 기술명은 원문을 유지한다.
- 코드, 명령어, 파일 경로, 환경 변수와 API endpoint는 번역되지 않는다.
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`, `news-api`, `news-lab-web` 등 실제 리소스명은 변경되지 않는다.
- 운영 서비스 URL이 기존과 동일하게 유지된다.
- 오래된 도메인이 다시 추가되지 않는다.
- 아키텍처 이미지 경로와 대체 텍스트가 유지된다.
- 내부 문서 링크가 깨지지 않는다.
- 기존 데이터 파이프라인, 인프라와 운영 설명의 의미가 변경되지 않는다.
- README의 사실관계가 번역 과정에서 왜곡되지 않는다.
- 기존 수동 rollout을 완전 자동 CD처럼 표현하지 않는다.
- 관측성을 자동 장애 대응이나 완전한 alerting으로 과장하지 않는다.
- 측정하지 않은 성능·비용·처리량 수치가 추가되지 않는다.
- Application 코드가 변경되지 않는다.
- DB와 API가 변경되지 않는다.
- K3s manifest와 GitHub Actions workflow가 변경되지 않는다.
- 아키텍처 이미지가 변경되지 않는다.
- 변경 범위가 README와 필요한 최소 문서에 한정된다.
- `git diff --check`가 통과한다.
- 실제 실행한 명령과 결과는 Verification에 기록된다.
- Task 문서에는 계획만 유지된다.

## Notes

- 이번 작업은 README의 내용을 새로 확장하는 작업이 아니라 언어와 용어 정합성을 개선하는 후속 수정이다.
- 모든 영어를 기계적으로 한국어로 번역하지 않는다.
- 국내 개발 문서에서 일반적으로 원문을 사용하는 기술명과 제품명은 그대로 둔다.
- 번역하면 의미가 어색해지는 기술 용어는 원문을 유지하되, 필요한 경우 최초 1회 한국어 설명을 덧붙인다.
- 섹션 제목은 가능하면 한국어로 통일한다.
- 표의 컬럼명과 설명은 한국어를 우선하되 실제 시스템 리소스명은 원문을 유지한다.
- 문체는 설명형 평서문으로 통일하고, 불필요한 영문 대문자 표기를 줄인다.
- 동일 개념에 `Backend`, `백엔드`, `Back-end`처럼 여러 표기를 혼용하지 않는다.
- `Topic`, `토픽`, `주제`를 문맥마다 바꾸지 않고 프로젝트 도메인 용어로 통일한다.
- README의 채용용 가독성을 우선하지만, 기술적 정확성을 희생하지 않는다.
- 기존 포트폴리오와 이력서에서 사용하는 프로젝트 용어와 충돌하지 않도록 확인한다.
- 상세 코드와 운영 기록은 기존 `docs/` 링크를 유지하며 README에 과도하게 복제하지 않는다.
- README 번역 과정에서 별도 기능 문제나 문서 불일치를 발견하더라도 이번 작업에서 함께 수정하지 않고 후속 작업 후보로 기록한다.
- 실제 운영 검증이나 Production 명령은 수행하지 않는다.
- Task에는 `Implementation Units` 섹션을 추가하지 않는다.

## Implementation Units

없음
