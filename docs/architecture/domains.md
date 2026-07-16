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

사용자에서 application까지의 공개 요청은 다음 논리 경로를 따른다.

```text
User
→ Public DNS
→ Oracle Public IP
→ Traefik Ingress
→ Kubernetes Service
→ Application Pod
```

Backend manifest가 직접 정의하는 구간은 `news-api-ingress → news-api
Service → FastAPI Pod`다. `news-api` Service는 `app: news-api` Pod만
선택한다. Frontend는 별도 저장소의 Frontend Ingress·Service를 거쳐
Next.js Pod로 전달되며, 하나의 Service가 Frontend와 Backend Pod를
함께 선택하는 구조가 아니다.

Public DNS와 Oracle Public IP 연결은 외부 인프라이다. Repository의
Ingress host는 desired route를 보여 주지만 실제 DNS resolution·public IP
연결·HTTPS 접속성을 증명하지는 않는다. Tailscale은 hybrid node
network와 operator의 K3s API 접근에 사용되며 public ingress에 포함되지
않는다.

## 변경 경계

DNS, OCI security rule, Ingress apply, certificate 발급 확인, frontend API base
URL 전환은 각각 사람 통제 작업이다. Manifest에 host가 존재한다는 사실만으로
DNS와 HTTPS production verification이 완료되었다고 판단하지 않는다.

확인 절차와 rollback 판단은
[Backend deploy runbook](../runbooks/backend-deploy.md)을 참고한다.
