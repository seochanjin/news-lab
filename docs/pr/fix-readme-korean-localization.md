# NewsLab README 한글 표기 및 용어 정합성 개선

## 작업 내용

- `README.md`의 영어 중심 section heading을 한국어 중심으로 정리했습니다.
- 일반 설명 문장에서 `Frontend`, `Backend`, `Architecture`, `Data Pipeline`, `Observability`, `Documentation`, `Local Development` 등 영어 중심 표현을 한국어 표기로 정리했습니다.
- 도메인 용어 `Topic`은 최초 1회 `토픽(Topic)`으로 설명하고 이후에는 `토픽` 중심으로 정리했습니다.
- `Human-in-the-loop`은 workflow 설명에서 `사람 승인 기반(Human-in-the-loop)`으로 설명했습니다.

## 주요 변경 사항

- 운영 서비스, 데이터 파이프라인, 아키텍처, 인프라와 배포, 관측성, agent workflow, 문서, 로컬 개발 섹션의 설명 문장을 한국어 중심으로 조정했습니다.
- FastAPI, PostgreSQL, pgvector, K3s, Kubernetes, Traefik, Tailscale, Prometheus, Grafana, GitHub Actions, Docker Hub, Supabase, cert-manager, Let's Encrypt 등 기술명은 원문으로 유지했습니다.
- 운영 URL, 아키텍처 이미지 경로와 대체 텍스트, 실제 리소스명, pipeline 구조, replica 수, rollout human-control 원칙은 변경하지 않았습니다.
- 애플리케이션 코드, DB, API, K3s manifest, GitHub Actions workflow, dependency는 변경하지 않았습니다.

## 테스트

- `rg -n "^#{1,6} .*\b(Overview|Live Service|Key Features|Data Pipeline|Architecture|Infrastructure|Deployment|Observability|Agent Workflow|Design Decisions|Documentation|Local Development|Troubleshooting)\b" README.md`
- `rg -n "Frontend|Backend|Architecture|Data Pipeline|Observability|Infrastructure|Deployment|Documentation|Design Decision|Troubleshooting|Live Service|Key Features" README.md`
- `rg -n "FastAPI|Next.js|PostgreSQL|pgvector|Docker|K3s|Kubernetes|Traefik|Tailscale|Prometheus|Grafana|GitHub Actions|Docker Hub|Supabase|cert-manager|Let's Encrypt" README.md`
- `rg -n "https://newslab\.ai\.kr|https://www\.newslab\.ai\.kr|https://api\.newslab\.ai\.kr" README.md`
- `rg -n "docs/images/newslab-architecture\.png|NewsLab 전체 아키텍처" README.md`
- `rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site" README.md`
- `test -f docs/ARCHITECTURE.md`
- `test -f docs/RUNBOOK.md`
- `test -f docs/images/newslab-architecture.png`
- `git diff --check`
- `git status --short`
- `git diff -- README.md docs/ARCHITECTURE.md docs/RUNBOOK.md`
- `git diff --name-only -- app scripts k8s db .github Dockerfile docker-compose.yml requirements.txt`

## 확인 결과

- Verification status: `passed`
- 상세 실행 결과는 `docs/verification/fix-readme-korean-localization.md`에 기록했습니다.
- 오래된 도메인은 README에 포함되지 않았고, 운영 URL과 아키텍처 이미지 참조는 유지됐습니다.
- Scope 밖 애플리케이션 코드, DB, API, manifest, workflow, dependency 변경은 없습니다.

## 비고

- Production verification, rollout, deployment, Supabase SQL은 수행하지 않았습니다.
- 이번 작업은 README 문서 표현 수정입니다.
