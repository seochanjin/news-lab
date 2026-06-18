# backend api.newslab.ai.kr 도메인/TLS 전환

## 작업 목적

기존 backend API 도메인 `api.dev-scj.site`를 중단하지 않고 신규 운영
도메인 `api.newslab.ai.kr`를 추가해, cert-manager 기반 HTTPS 발급과 점진적
도메인 전환이 가능한 상태를 만드는 것이 목적이다.

## 기존 문제

- Backend Ingress는 `api.dev-scj.site` 단일 host와 `news-api-tls` 단일 TLS
  Secret만 선언하고 있었다.
- frontend는 `newslab.ai.kr` 도메인 체계를 사용하지만 backend는 기존 도메인
  하나만 제공하고 있었다.
- 신규 backend 도메인 적용 전후에 필요한 DNS, Certificate, ACME, HTTPS
  검증 절차가 Runbook에 정리되어 있지 않았다.

## 변경 내용

- `news-api-ingress`에 `api.newslab.ai.kr` host rule 추가
- 신규 도메인용 별도 TLS Secret `news-api-newslab-tls` 선언
- 기존 `api.dev-scj.site` rule과 `news-api-tls` 유지
- 기존 `cert-manager.io/cluster-issuer: letsencrypt-prod` annotation 유지
- 두 도메인을 동일 `news-api` Service port `80`으로 연결
- Architecture에 backend domain/TLS 구조와 frontend 후속 전환 경계 기록
- Runbook에 human-controlled DNS, dry-run, apply, Certificate/ACME, HTTPS
  검증 절차 기록

## 구현 상세

Ingress의 TLS 설정은 host별 Secret을 분리했다.

```text
api.dev-scj.site    -> news-api-tls
api.newslab.ai.kr   -> news-api-newslab-tls
```

기존 도메인은 제거하지 않아 신규 인증서 발급이나 frontend 전환 과정에서
기존 API 접근 경로를 유지한다. 신규 host rule은 기존 host와 동일한 `/`
Prefix와 `news-api:80` backend를 사용하므로 FastAPI application code나 API
schema 변경이 필요하지 않다.

Architecture에는 backend API의 두 host와 TLS Secret 관계를 기록했다.
Runbook에는 DNS 확인부터 server-side dry-run, manifest apply,
Certificate/ACME 조회, 신규·기존 health endpoint 확인까지의 절차를
human-controlled 작업으로 정리했다.

## 대안 검토

- **기존 `api.dev-scj.site`를 신규 도메인으로 즉시 교체**
  - 기존 frontend와 운영 확인 경로가 바로 영향을 받으므로 제외했다.
  - 신규 DNS/TLS 검증이 끝날 때까지 두 host를 병행하는 편이 rollback 범위가
    작다.

- **기존 `news-api-tls`에 두 도메인을 함께 넣는 다중 SAN 인증서 사용**
  - 하나의 Secret으로 관리할 수 있지만 신규 인증서 재발급 과정이 기존
    도메인의 인증서 lifecycle과 결합된다.
  - task에서 권장한 host별 별도 Secret 정책을 선택했다.

- **신규 도메인 추가와 frontend API base URL 전환을 한 작업에서 수행**
  - backend TLS 문제와 frontend 설정 문제를 동시에 발생시킬 수 있어
    제외했다.
  - 신규 backend endpoint의 운영 검증 후 별도 작업으로 전환한다.

- **별도 Ingress resource 생성**
  - host별 객체 분리는 가능하지만 현재 repository는 Deployment, Service,
    Ingress를 `k8s/news-api.yaml`에서 함께 관리한다.
  - 동일 Service와 동일 Traefik 설정을 사용하는 이번 범위에서는 기존
    Ingress에 host/TLS 항목을 추가하는 편이 변경이 작다.

## 선택한 접근과 근거

단일 다중 SAN 인증서 대신 host별 TLS Secret을 사용했다. 이 방식은 기존
`news-api-tls`의 lifecycle을 유지하면서 신규 인증서 발급 실패가 기존
인증서 Secret을 대체하지 않도록 변경 범위를 분리한다.

frontend API base URL 변경은 신규 backend DNS/TLS/health 검증 이후 별도
작업으로 남겼다. backend 노출과 frontend 소비 경로를 한 번에 바꾸지 않아
문제 발생 시 원인과 rollback 범위를 명확히 유지할 수 있다.

기존 `news-api-ingress`와 `news-api` Service를 재사용해 application code,
API schema, DB 및 image workflow를 건드리지 않았다. 실제 DNS, apply,
Certificate 발급 및 HTTPS 검증은 repository 변경과 분리해 운영자가
수동으로 수행하도록 유지했다.

## 트레이드오프

- 두 도메인을 병행하므로 TLS Secret과 Certificate 운영 대상이 하나
  늘어난다.
- 신규 인증서 발급 실패가 기존 인증서 Secret을 직접 대체하지 않지만,
  Ingress 한 객체에 두 host가 있으므로 manifest 변경 검토는 함께 필요하다.
- frontend가 아직 기존 backend 도메인을 사용하므로 이번 변경만으로
  사용자 트래픽이 신규 도메인으로 전환되지는 않는다.
- 실제 K3s apply 전에는 manifest의 정적 구조만 확인할 수 있고,
  cert-manager의 ACME 처리와 외부 HTTPS 동작은 검증할 수 없다.
- 기존 도메인을 유지해 전환 위험은 낮추지만, 장기적으로 도메인과 인증서
  정리 작업이 별도로 필요하다.

## 테스트

`docs/verification/feature-backend-api-newslab-domain.md`에 기록된 실제 정적
검증 결과:

- 전체 `k8s/*.yaml` YAML stream parsing: 통과
- `k8s/news-api.yaml` parsing 결과:
  `Deployment, Service, Ingress`
- Ingress focused assertion: 통과
  - ClusterIssuer annotation: `letsencrypt-prod`
  - `api.dev-scj.site` → `news-api-tls`
  - `api.newslab.ai.kr` → `news-api-newslab-tls`
  - 두 host 모두 `news-api` Service port `80`으로 연결
- `git diff --check`: 통과
- verification, PR, devlog Markdown focused whitespace 검사: 통과
- application code, scripts, tests, DB, Dockerfile, GitHub Actions, frontend,
  `.env`, `.env.*` 보호 범위 diff/status: 변경 없음
- security grep에서 기존 안전한 참조만 확인됐으며 신규 credential 또는
  secret 값은 발견되지 않음

Source task 파일을 포함한 첫 untracked Markdown whitespace 검사는 기존
Markdown hard-break trailing space 때문에 exit code `3`을 반환했다. Task
파일은 수정하지 않았으며, 생성한 verification, PR, devlog 파일만 대상으로
한 focused 검사는 통과했다.

## 운영 반영

- Codex는 DNS 확인, kubectl preflight/dry-run/apply, Certificate/ACME 조회,
  production curl을 실행하지 않았다.
- 실제 운영 반영과 검증은 human-controlled pending 상태다.
- Human-provided production verification log는 제공되지 않았다.
- 다음 항목은 pending이다.
  - `api.newslab.ai.kr` A record가 `152.67.211.33`인지 확인
  - AAAA record가 없는지 확인
  - `letsencrypt-prod`와 기존 Ingress preflight
  - `k8s/news-api.yaml` server-side dry-run 및 실제 apply
  - Ingress의 두 host/TLS Secret mapping 확인
  - `news-api-newslab-tls` Secret과 Certificate `Ready=True` 확인
  - ACME Order valid 및 Challenge 상태 확인
  - 신규/기존 `/health` HTTP 200과 반복 요청 안정성 확인

승인되어 적용된 review fix는 없다. PR merge, production deployment,
K3s rollout, TLS 발급 및 HTTPS 운영 검증 완료를 주장하지 않는다.

## README 업데이트 판단

README 변경은 필요하지 않다고 판단했다. 이번 작업은 FastAPI 사용법, API
schema 또는 로컬 개발 절차를 바꾸는 기능 변경이 아니라 K3s Ingress의
도메인/TLS 운영 설정 변경이다.

구조적 설명은 `docs/ARCHITECTURE.md`, 실제 적용과 검증 절차는
`docs/RUNBOOK.md`에 기록하는 것이 기존 문서 역할과 맞다.

## 확인 결과

- Repository manifest에는 기존/신규 backend host가 함께 선언되어 있다.
- 기존 도메인의 TLS Secret은 유지되고 신규 도메인은 별도 Secret을 사용한다.
- Backend application code, API behavior, DB, Docker image workflow는
  변경되지 않았다.
- Runbook에 적용 전제조건과 적용 후 검증 절차가 추가됐다.
- Production HTTPS 성공 여부는 아직 확인되지 않았다.

## 이번 단계의 의미

Backend를 `newslab.ai.kr` 도메인 체계로 옮기기 위한 첫 단계로, 기존 경로를
보존하면서 신규 도메인과 인증서를 독립적으로 검증할 수 있게 했다. 운영자가
신규 TLS와 health endpoint를 확인한 뒤 frontend API base URL을 별도
작업에서 안전하게 전환할 수 있다.

## 포트폴리오용 요약

K3s와 Traefik으로 운영되는 FastAPI backend에 신규 운영 도메인을 추가했다.
기존 `api.dev-scj.site`를 유지하면서 `api.newslab.ai.kr` host rule을
동일 Service에 연결하고, cert-manager의 `letsencrypt-prod`를 사용하는
별도 TLS Secret으로 인증서 lifecycle을 분리했다.

단순 manifest 수정에 그치지 않고 Architecture에 도메인/TLS 구조를
문서화하고, Runbook에 DNS preflight, server-side dry-run, Certificate/ACME
상태, 기존·신규 HTTPS health endpoint의 반복 검증 절차를 추가했다.
Application, DB, Docker 및 frontend 범위를 건드리지 않고 인프라 변경과
후속 frontend 전환을 단계적으로 분리한 작업이다.

## 다음 단계 후보

- Human DNS A/AAAA 확인
- Human server-side dry-run 및 K3s manifest apply
- `news-api-newslab-tls` Certificate `Ready=True`와 ACME Order 확인
- 신규/기존 `/health` HTTP 200 및 반복 요청 확인
- 검증 완료 후 frontend API base URL을 `api.newslab.ai.kr`로 전환하는 별도
  작업 진행
- 장기적으로 기존 `api.dev-scj.site` 제거 여부 별도 판단
- Backend Ingress의 HTTP → HTTPS redirect 정책 점검
- Docker image의 `latest` tag 정책 개선 검토
