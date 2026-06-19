# Backend 배포와 Domain/TLS 확인

[Runbook index로 돌아가기](../RUNBOOK.md)

이 문서의 변경 command는 모두 사람이 실행한다. Agent는 command를 제안하거나
결과를 정리할 수 있지만 apply, rollout, DNS/TLS 변경과 production verification을
자동 실행하지 않는다.

## 배포 전 확인

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get clusterissuer letsencrypt-prod
```

Manifest 변경 task라면 사람이 server-side dry-run 결과를 확인한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server \
  -f k8s/news-api.yaml
```

## Manifest apply

사람이 review와 preflight를 마친 뒤 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-api.yaml
```

Apply 직후에는 object 존재만 확인하며 production 동작 완료로 간주하지 않는다.

## Image rollout

새 image가 이미 registry에 준비되었다는 전제에서 사람이 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout restart deployment/news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
```

Running image 확인:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api \
  -o=jsonpath='{.spec.template.spec.containers[0].image}'
```

## Domain과 certificate

사람이 DNS를 확인한다.

```bash
dig +short api.newslab.ai.kr
dig +short AAAA api.newslab.ai.kr
```

Ingress와 certificate는 secret data를 출력하지 않고 확인한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress \
  news-api-ingress -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe certificate \
  news-api-newslab-tls
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get order,challenge
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret \
  news-api-newslab-tls
```

Certificate가 `Ready=True`인 뒤 사람이 두 host를 확인한다.

```bash
curl -I https://api.newslab.ai.kr/health
curl -sS https://api.newslab.ai.kr/health
curl -I https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/health
```

## 실패 시 중단과 확인

- Rollout 실패: Deployment와 Pod event, current/previous log를 확인한다.
- Certificate 실패: Certificate, Order, Challenge와 DNS 결과를 확인한다.
- 한 host만 실패: Ingress host/TLS mapping과 DNS를 비교한다.
- Application 오류: Service endpoint와 Pod log를 확인한다.

Rollback 또는 재적용은 원인을 확인한 뒤 사람이 결정한다. 실제 apply, rollout,
certificate, HTTPS 결과를 해당 task의 verification 문서에 기록한다.
