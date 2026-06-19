# Backend Domain과 TLS

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 현재 routing

Traefik `news-api-ingress`가 두 host를 동일한 `news-api` Service로 전달한다.

| Host | TLS Secret |
| --- | --- |
| `api.dev-scj.site` | `news-api-tls` |
| `api.newslab.ai.kr` | `news-api-newslab-tls` |

cert-manager의 ClusterIssuer는 `letsencrypt-prod`다. 두 host는 transition 동안
함께 유지된다.

## 변경 경계

DNS, OCI security rule, Ingress apply, certificate 발급 확인, frontend API base
URL 전환은 각각 사람 통제 작업이다. Manifest에 host가 존재한다는 사실만으로
DNS와 HTTPS production verification이 완료되었다고 판단하지 않는다.

확인 절차와 rollback 판단은
[Backend deploy runbook](../runbooks/backend-deploy.md)을 참고한다.
