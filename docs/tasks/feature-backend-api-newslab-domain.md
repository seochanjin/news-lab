# Task: backend api.newslab.ai.kr 도메인/TLS 전환

## Goal

NewsLab backend API를 기존 `api.dev-scj.site` 도메인과 함께 신규 운영 도메인 `api.newslab.ai.kr`에서도 HTTPS로 접근할 수 있도록 K3s Ingress TLS 설정을 확장한다.

이번 작업의 목표는 다음과 같다.

```text
1. 기존 backend API 도메인 api.dev-scj.site를 유지한다.
2. 신규 backend API 도메인 api.newslab.ai.kr를 Ingress host로 추가한다.
3. cert-manager letsencrypt-prod ClusterIssuer를 사용해 api.newslab.ai.kr TLS 인증서를 발급받을 수 있도록 manifest를 수정한다.
4. 기존 api.dev-scj.site의 TLS/Ingress 동작을 깨지 않는다.
5. https://api.newslab.ai.kr/health 또는 현재 backend health endpoint가 정상 응답하는지 운영 단계에서 검증할 수 있도록 문서화한다.
```

이번 작업은 backend API 도메인 추가 작업이다.  
frontend API base URL 전환은 이번 작업에 포함하지 않고, backend 신규 도메인이 안정화된 뒤 별도 작업으로 진행한다.

권장 도메인 상태는 다음과 같다.

```text
기존 backend API:
https://api.dev-scj.site

신규 backend API:
https://api.newslab.ai.kr
```

---

## Scope

이번 작업은 backend repository 안에서 다음 범위만 수행한다.

```text
- backend K3s Ingress manifest에 api.newslab.ai.kr host 추가
- api.newslab.ai.kr용 TLS Secret 선언
- cert-manager letsencrypt-prod annotation 유지 또는 확인
- 기존 api.dev-scj.site host/rule/TLS 유지
- architecture/runbook/verification 문서 업데이트
- PR 초안 작성
- 실제 실행한 정적 검증 결과 기록
```

권장 TLS 정책은 다음과 같다.

```text
- 기존 api.dev-scj.site는 기존 news-api-tls Secret 유지
- 신규 api.newslab.ai.kr는 별도 news-api-newslab-tls Secret 사용
```

예상 Ingress 구조는 다음과 같다.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: news-api-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - api.dev-scj.site
      secretName: news-api-tls
    - hosts:
        - api.newslab.ai.kr
      secretName: news-api-newslab-tls
  rules:
    - host: api.dev-scj.site
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: news-api
                port:
                  number: 80
    - host: api.newslab.ai.kr
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: news-api
                port:
                  number: 80
```

다만 실제 파일 구조가 다르면 repository의 현재 manifest 구조를 우선한다.

---

## Do not change

이번 작업에서 다음 항목은 변경하지 않는다.

```text
- Backend application code
- FastAPI route handler
- API response schema
- DB schema
- Supabase SQL
- migration file
- collector/extractor script logic
- Dockerfile
- Docker image build workflow
- Docker image tag policy
- frontend repository
- frontend API base URL
- existing api.dev-scj.site 제거
- existing news-api-tls Secret 제거
- Kubernetes Secret 값
- .env
- .env.*
```

금지 command:

```text
- git push
- git merge
- PR merge
- docker push
- kubectl apply
- kubectl delete
- kubectl rollout restart
- helm upgrade
- DB migration
- production deploy command
- production-impacting command
```

agent는 repository 파일 수정과 정적 검증까지만 수행한다.  
실제 K3s apply, rollout, Certificate 발급 확인, HTTPS 확인은 사람이 수동으로 수행한다.

---

## Expected files

예상 변경 파일은 다음과 같다.

```text
k8s/news-api.yaml
docs/ARCHITECTURE.md
docs/RUNBOOK.md
docs/tasks/feature-backend-api-newslab-domain.md
docs/verification/feature-backend-api-newslab-domain.md
docs/pr/feature-backend-api-newslab-domain.md
```

repository 구조에 따라 Ingress manifest가 분리되어 있다면 다음 파일이 대상일 수 있다.

```text
k8s/news-api-ingress.yaml
k8s/backend-ingress.yaml
k8s/*.yaml
```

작업 전 현재 backend Ingress 위치를 확인한다.

```bash
rg -n "api.dev-scj.site|news-api-ingress|news-api-tls|letsencrypt-prod" k8s docs
```

문서에는 다음 내용을 반영한다.

```text
- 기존 api.dev-scj.site는 유지
- 신규 api.newslab.ai.kr 추가
- 신규 TLS Secret은 news-api-newslab-tls 사용
- frontend API base URL 변경은 후속 작업
- 실제 apply/Certificate/HTTPS 검증은 사람이 수행
```

---

## DB changes

DB 변경은 없다.

이번 작업은 K3s Ingress host/TLS 설정 변경이다.  
다음 항목을 변경하지 않는다.

```text
- table
- column
- index
- constraint
- view
- function
- trigger
- seed data
- Supabase SQL
- migration
```

검증 문서에도 DB 변경 없음으로 기록한다.

---

## API changes

Backend API application code 변경은 없다.

이번 작업은 같은 backend Service를 신규 host `api.newslab.ai.kr`로도 노출하는 변경이다.  
API path, method, request body, response body, status code, pagination, filtering, collector/extractor behavior는 변경하지 않는다.

변경되는 것은 접근 가능한 host다.

```text
기존:
https://api.dev-scj.site

추가:
https://api.newslab.ai.kr
```

기존 endpoint는 계속 유지한다.

예상 확인 endpoint:

```text
/health
/version
/sources
/articles
/collector/status
/extractor/status
```

단, 운영 검증의 1차 기준은 health endpoint로 한다.

```text
https://api.dev-scj.site/health
https://api.newslab.ai.kr/health
```

---

## Test commands

agent가 실행 가능한 정적 검증과 사람이 수동으로 실행할 운영 검증을 구분한다.

### Agent static checks

```bash
git status --short --branch
```

```bash
rg -n "api.dev-scj.site|api.newslab.ai.kr|news-api-ingress|news-api-tls|news-api-newslab-tls|letsencrypt-prod" k8s docs
```

```bash
git diff --check
```

YAML parser가 사용 가능하면 manifest syntax를 확인한다.

```bash
ruby -e 'require "yaml"; ARGV.each { |f| docs = YAML.load_stream(File.read(f)); puts "#{f}: #{docs.map { |d| d["kind"] }.compact.join(", ")}" }' k8s/*.yaml
```

secret 값이 추가되지 않았는지 확인한다.

```bash
git grep -n -i -E "API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|BEGIN|\\.env"
```

변경 범위를 확인한다.

```bash
git diff --stat
git diff -- k8s docs
```

backend application code가 변경되지 않았는지 확인한다.  
repository 구조에 맞게 경로는 조정할 수 있다.

```bash
git diff -- app src scripts tests || true
```

### Manual preflight checks

아래 command는 사람이 수동으로 실행한다.

DNS 확인:

```bash
dig +short api.newslab.ai.kr
dig +short AAAA api.newslab.ai.kr
```

기대 결과:

```text
api.newslab.ai.kr -> 152.67.211.33
AAAA              -> 없음
```

Traefik/cert-manager 전제조건 확인:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get clusterissuer letsencrypt-prod
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress -o wide
```

### Manual server-side dry-run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server -f k8s/news-api.yaml
```

Ingress 파일이 분리되어 있다면 실제 파일명으로 조정한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply --dry-run=server -f k8s/news-api-ingress.yaml
```

### Manual apply

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-api.yaml
```

또는 실제 Ingress 파일명 기준:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-api-ingress.yaml
```

### Manual resource verification

Ingress 확인:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get ingress news-api-ingress -o yaml | rg -n "api.dev-scj.site|api.newslab.ai.kr|news-api-tls|news-api-newslab-tls|cluster-issuer"
```

Certificate 확인:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get certificate
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe certificate news-api-newslab-tls
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get order,challenge
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get secret news-api-newslab-tls
```

HTTPS 확인:

```bash
curl -I https://api.newslab.ai.kr/health
curl -sS https://api.newslab.ai.kr/health

curl -I https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/health
```

반복 요청 확인:

```bash
for i in {1..20}; do
  echo "---- $i ----"
  curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" https://api.newslab.ai.kr/health
done
```

기존 도메인 유지 확인:

```bash
for i in {1..20}; do
  echo "---- $i ----"
  curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" https://api.dev-scj.site/health
done
```

---

## Acceptance criteria

### Repository criteria

```text
- backend Ingress manifest에 api.newslab.ai.kr host rule이 추가됨
- api.newslab.ai.kr용 TLS Secret news-api-newslab-tls가 선언됨
- 기존 api.dev-scj.site host/rule/TLS 설정이 유지됨
- cert-manager.io/cluster-issuer: letsencrypt-prod annotation이 유지됨
- backend application code 변경 없음
- DB/Supabase SQL 변경 없음
- Dockerfile/Docker workflow 변경 없음
- frontend repository/API base URL 변경 없음
- .env, .env.* 변경 없음
- 실제 secret 값 추가 없음
- git diff --check 통과
- YAML parsing 통과
- verification 문서에 실제 실행한 command와 결과 기록
- 미실행 운영 검증은 pending으로 기록
```

### Production criteria

운영 반영은 사람이 수동으로 수행한다.

```text
- api.newslab.ai.kr DNS A record가 152.67.211.33을 바라봄
- api.newslab.ai.kr AAAA record가 없음
- server-side dry-run 성공
- K3s apply 성공
- news-api-ingress에 api.dev-scj.site와 api.newslab.ai.kr host가 모두 존재
- news-api-newslab-tls Secret 생성
- news-api-newslab-tls Certificate Ready=True
- ACME Order valid
- https://api.newslab.ai.kr/health HTTP 200
- https://api.dev-scj.site/health HTTP 200 유지
- 반복 curl 기준 신규/기존 health endpoint 모두 실패 없음
```

---

## Notes

이 작업은 frontend 도메인 정리 이후 backend 도메인을 `newslab.ai.kr` 체계로 맞추기 위한 단계다.

현재 frontend는 다음 도메인에서 동작한다.

```text
https://newslab.ai.kr
https://www.newslab.ai.kr
```

현재 backend는 기존 도메인을 사용한다.

```text
https://api.dev-scj.site
```

이번 작업에서는 backend에 신규 도메인만 추가한다.

```text
https://api.newslab.ai.kr
```

frontend의 API base URL은 이번 작업에서 변경하지 않는다.  
frontend가 실제로 `api.newslab.ai.kr`를 사용하도록 바꾸는 작업은 backend 신규 도메인/TLS 검증이 끝난 뒤 별도 차수로 진행한다.

권장 후속 순서:

```text
52차: backend api.newslab.ai.kr 도메인/TLS 추가
53차: frontend API base URL을 api.newslab.ai.kr로 전환
54차 이후: backend 최적화 및 기능 추가
```

기존 `api.dev-scj.site`는 52차에서 제거하지 않는다.  
신규 도메인 안정화와 frontend 전환이 완료된 뒤 제거 여부를 별도 작업으로 판단한다.

장기 후속 후보:

```text
- frontend API base URL api.newslab.ai.kr 전환
- 기존 api.dev-scj.site 제거 여부 판단
- backend Ingress HTTP → HTTPS redirect 정책 점검
- Docker image tag latest 사용 개선
- backend SQL cleanup/refactor
- backend topic pipeline 최적화
- backend 기능 추가
```
