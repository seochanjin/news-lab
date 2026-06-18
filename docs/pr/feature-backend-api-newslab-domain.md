# backend api.newslab.ai.kr 도메인/TLS 전환

## 작업 내용

- 기존 backend API 도메인 `api.dev-scj.site`를 유지하면서 신규 운영 도메인
  `api.newslab.ai.kr`를 추가할 수 있도록 K3s Ingress TLS 설정을
  확장했습니다.
- 신규 도메인은 기존 인증서와 분리된 `news-api-newslab-tls` Secret을
  사용하도록 선언했습니다.
- Architecture와 Runbook에 두 도메인의 공존 구조와 사람이 수행할
  적용·인증서·HTTPS 검증 절차를 문서화했습니다.

## 주요 변경 사항

- `k8s/news-api.yaml`
  - `api.newslab.ai.kr` TLS host 및 Ingress rule 추가
  - 신규 TLS Secret 이름으로 `news-api-newslab-tls` 선언
  - 기존 `api.dev-scj.site` rule과 `news-api-tls` 유지
  - `cert-manager.io/cluster-issuer: letsencrypt-prod` annotation 유지
  - 두 host 모두 기존 `news-api` Service의 port `80`으로 연결

- `docs/ARCHITECTURE.md`
  - backend API host와 TLS Secret의 분리 구조 문서화
  - frontend API base URL 전환은 후속 작업임을 명시

- `docs/RUNBOOK.md`
  - DNS, ClusterIssuer, server-side dry-run, manifest apply,
    Certificate/ACME 및 HTTPS 확인 절차 추가
  - 신규/기존 health endpoint의 반복 확인 절차 추가
  - 실제 적용과 운영 검증이 human-controlled임을 명시

## 추가/변경된 API

- FastAPI route, HTTP method, request/response schema 및 status code 변경은
  없습니다.
- 기존 endpoint를 제공하는 동일 backend Service에 접근 가능한 host만
  추가됩니다.

```text
기존: https://api.dev-scj.site
추가: https://api.newslab.ai.kr
```

## DB 변경 사항

- 없음.
- DB schema, migration, Supabase SQL 및 데이터 변경을 수행하지 않았습니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 이번 변경은 backend application 사용법이나 API schema 변경이 아니라 K3s
  Ingress 도메인/TLS 운영 설정 변경이므로 Architecture와 Runbook에
  반영했습니다.

## 테스트

`docs/verification/feature-backend-api-newslab-domain.md`에 기록된 정적 검증
결과:

- 전체 `k8s/*.yaml` YAML stream parsing: 통과
- `k8s/news-api.yaml` parsing 결과:
  `Deployment, Service, Ingress`
- Ingress focused assertion: 통과
  - ClusterIssuer annotation: `letsencrypt-prod`
  - `api.dev-scj.site` → `news-api-tls`
  - `api.newslab.ai.kr` → `news-api-newslab-tls`
  - 두 host 모두 `news-api` Service port `80`으로 연결
- `git diff --check`: 통과
- verification, PR, devlog Markdown whitespace 검사: 통과
- application code, scripts, tests, DB, Dockerfile, GitHub Actions, frontend,
  `.env`, `.env.*` 보호 범위 diff/status: 변경 없음
- security grep: 기존의 안전한 참조만 확인되었으며 신규 credential 또는
  secret 값 없음

## 확인 결과

- 기존 `api.dev-scj.site` host/rule과 `news-api-tls` 설정이 유지됐습니다.
- 신규 `api.newslab.ai.kr` host/rule과 별도 TLS Secret
  `news-api-newslab-tls`가 manifest에 선언됐습니다.
- Backend application code, DB, Docker image workflow 및 frontend API base
  URL은 변경되지 않았습니다.
- 적용 전제조건과 적용 후 Certificate/ACME/HTTPS 확인 절차가 Runbook에
  추가됐습니다.
- 승인되어 적용된 review fix는 없습니다.

## 비고

- 다음 항목은 사람이 수행할 pending 운영 검증입니다.
  - DNS A record `152.67.211.33` 및 AAAA record 없음 확인
  - `letsencrypt-prod`와 기존 Ingress preflight
  - `k8s/news-api.yaml` server-side dry-run 및 실제 apply
  - 두 Ingress host/TLS Secret mapping 확인
  - `news-api-newslab-tls` Secret 생성과 Certificate `Ready=True` 확인
  - ACME Order valid 및 Challenge 상태 확인
  - 신규/기존 `/health` HTTP 200과 반복 요청 안정성 확인
- frontend API base URL 전환은 신규 backend 도메인 검증 후 별도 작업으로
  진행합니다.
- DNS lookup, kubectl, production curl, git push 및 git merge는 실행하지
  않았습니다.
- Production deployment, K3s rollout, TLS 발급, HTTPS 운영 검증 및 PR merge
  완료를 주장하지 않습니다.
