# Antigravity Review: backend api.newslab.ai.kr 도메인/TLS 전환

## Review Summary

본 변경 사항은 `feature/backend-api-newslab-domain` 브랜치에 구현된 backend API 도메인 및 TLS 인증서 전환 설정을 검토한 결과입니다. 변경 사항은 Ingress 설정 확장과 관련 문서 업데이트로 구성되어 있으며, 기존의 `api.dev-scj.site` 도메인을 안전하게 유지하면서 신규 운영 도메인인 `api.newslab.ai.kr`을 성공적으로 추가하고 있습니다. 전체적인 변경 사항의 범위 제어가 매우 우수하며, 코드 품질 및 배포 안전성이 확보된 상태입니다.

## Requirement Coverage

`docs/tasks/feature-backend-api-newslab-domain.md`에 정의된 요구사항에 대한 구현 커버리지를 검토한 결과, 100% 충족함을 확인했습니다:
- **기존 도메인 유지**: `api.dev-scj.site` 호스트 및 TLS 설정이 손상 없이 유지되고 있습니다.
- **신규 도메인 추가**: `api.newslab.ai.kr` 호스트가 Ingress 규칙에 올바르게 추가되었습니다.
- **ClusterIssuer 사용**: 기존 `letsencrypt-prod` ClusterIssuer 어노테이션이 유지되어 신규 도메인도 이를 통해 인증서를 발급받도록 구성되었습니다.
- **TLS Secret 분리**: 기존 `news-api-tls`와 신규 `news-api-newslab-tls` Secret을 분리하여 인증서 라이프사이클을 독립적으로 격리했습니다.
- **운영 단계 검증 문서화**: 신규 도메인 접속 및 헬스 체크 검증 절차가 런북에 상세히 기술되었습니다.

## Code Quality / Maintainability

- **Kubernetes 매니페스트 구조**: `k8s/news-api.yaml` 파일 내의 Ingress 명세가 가독성 높고 표준 사양에 부합하게 선언되었습니다. 두 호스트가 동일한 backend 서비스(`news-api:80`)로 매핑되는 과정이 중복 없이 깔끔하게 작성되었습니다.
- **인증서 격리**: 단일 멀티 도메인(SAN) 인증서 대신 개별 TLS Secret 정책을 채택함으로써, 신규 도메인 인증서 발급 과정의 문제가 기존 도메인의 운영 안정성에 영향을 미치지 않도록 설계되었습니다.

## Security Review

- **비밀 데이터 비노출**: 매니페스트에는 실제 비밀번호나 비공개 키가 포함되어 있지 않으며, Kubernetes Secret 참조명만 사용하고 있습니다.
- **비밀 검사 수행**: 정적 비밀 검사(`git grep`)를 통해 의도치 않은 인증 키나 `.env` 설정 등이 커밋 범위에 노출되지 않았음을 확인했습니다.
- **권한 제어**: 추가된 라우팅과 TLS 설정은 최소 권한 원칙을 따르며, 불필요한 시스템 접근 권한 상승을 유발하지 않습니다.

## Operational Risk

- **무중단 운영**: 기존 접속 경로인 `api.dev-scj.site` 및 관련 TLS 설정에 변경을 가하지 않았으므로, 배포 및 인증서 발급 단계에서 기존 API 소비자에 대한 서비스 중단 위험이 발생하지 않습니다.
- **인증서 발급 실패 격리**: `api.newslab.ai.kr` 인증서 발급 중 레이트 리밋이나 DNS ACME 챌린지 실패가 발생하더라도 기존 `news-api-tls` 연결에는 영향이 없습니다.
- **통제 범위 명시**: 런북에 수동 DNS 확인, `apply --dry-run=server` 검증, 배포 후 인증서 상태 추적 및 반복 curl 점검 방법이 구체적으로 문서화되어 있어, 작업자의 실수나 오동작 위험을 크게 줄였습니다.

## Scope Control

- **범위 제어 상태**: 변경된 파일은 매니페스트 `k8s/news-api.yaml` 1개 파일과 문서 파일(`docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`)로 제한되어 있습니다.
- **불필요한 변경 없음**: FastAPI 애플리케이션 코드, API 스키마, 데이터베이스 마이그레이션(SQL), Dockerfile, 프론트엔드 코드 등 금지된 범위의 변경이 전혀 발생하지 않았습니다.

## Verification Review

- **정적 검증 적절성**: 에이전트 환경에서 실행한 정적 검증(`git diff --check`, Ruby YAML 구문 검증, 정적 YAML 의미 분석 등)이 정밀하게 설계 및 실행되었습니다.
- **검증의 기록성**: 검증 단계의 상세 명령어와 결과가 `docs/verification/feature-backend-api-newslab-domain.md` 파일에 누락 없이 투명하게 기록되었습니다.
- **제어 경계 준수**: 에이전트는 실제 클러스터 상태 변경을 유발하는 명령어(`kubectl apply`, 실 운영 DNS 조회, 프로덕션 curl 등)를 실행하지 않고 사람의 검증 영역으로 안전하게 유보했습니다.

## Documentation Review

- **아키텍처 가이드 반영**: `docs/ARCHITECTURE.md`에 백엔드 다중 도메인 공존 및 TLS Secret 분리 구조가 올바르게 업데이트되었습니다. 또한 프론트엔드 API 엔드포인트 전환은 안전성을 확인한 후 후속 단계에서 수행한다는 경계가 명확히 명시되었습니다.
- **런북 가이드 구체성**: `docs/RUNBOOK.md`에 도메인 추가와 관련된 작업 순서와 예상 결과가 매우 직관적으로 작성되어 있어 현장 대응에 유용합니다.

## Problems Found

- 발견된 결함이나 개선이 필요한 오류가 존재하지 않습니다. 

## Required Fixes Before PR

- **없음**. (정적 검사 및 YAML 파싱 검사를 통과하여 PR 진행에 결격 사유가 없습니다.)

## Optional Improvements

- **없음**. (현재 구현 수준 및 문서화 상태가 요구사항 수준을 넘어 매우 안정적입니다.)

## Suggested Test Commands

운영자가 프로덕션 환경에서 수동 배포 전후로 실행할 것을 권장하는 검증 명령어 세트입니다:

1. **DNS 사전 검증**
   ```bash
   dig +short api.newslab.ai.kr
   dig +short AAAA api.newslab.ai.kr
   ```
   *기대 결과: A 레코드는 `152.67.211.33`을 가리키고, AAAA 레코드는 조회되지 않아야 함.*

2. **Letsencrypt ClusterIssuer 사전 점검**
   ```bash
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get clusterissuer letsencrypt-prod
   ```

3. **서버 사이드 드라이런 실행**
   ```bash
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server -f k8s/news-api.yaml
   ```

4. **실제 매니페스트 반영**
   ```bash
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-api.yaml
   ```

5. **리소스 및 인증서 발급 모니터링**
   ```bash
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress -o wide
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate news-api-newslab-tls
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe certificate news-api-newslab-tls
   KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get order,challenge
   ```

6. **HTTPS 접속 및 반복 호출 안정성 검증**
   ```bash
   # 신규 도메인 검증
   curl -I https://api.newslab.ai.kr/health
   for i in {1..20}; do curl -sS -o /dev/null -w "%{http_code}\n" https://api.newslab.ai.kr/health; done

   # 기존 도메인 유지 검증
   curl -I https://api.dev-scj.site/health
   for i in {1..20}; do curl -sS -o /dev/null -w "%{http_code}\n" https://api.dev-scj.site/health; done
   ```

## Verdict

- **APPROVED** (요구사항 충족 완료, 사이드 이펙트 우려 없음, 즉시 PR 검토 및 배포 승인 가능)
