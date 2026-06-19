# 금지 및 사람 통제 작업

[Backend agent workflow로 돌아가기](backend-workflow.md)

## Agent가 자동 실행하지 않는 command

```text
git push
git merge
gh pr merge
kubectl apply
kubectl delete
kubectl patch
kubectl edit
kubectl rollout restart
helm install
helm upgrade
helm uninstall
docker push
production DB migration
Supabase 운영 SQL
```

동등한 production-impacting command도 같은 기준을 적용한다.

## 사람이 통제하는 작업

- PR merge와 main branch merge 결정
- Kubernetes manifest apply
- K3s rollout, restart, object 생성·변경·삭제
- Supabase SQL과 migration 실행
- DB write가 발생하는 production script와 manual Job
- Secret과 ConfigMap 값 생성 또는 변경
- Production API와 scheduled workload 최종 verification
- OCI security rule, DNS, domain, TLS 변경

## 민감정보

다음을 수정하거나 값으로 기록하지 않는다.

- `.env`, `.env.*`
- kubeconfig
- `DATABASE_URL` 실제 값
- API key, token, password
- SSH/private key
- Docker registry credential
- Kubernetes Secret data

환경 변수명, Secret resource명, placeholder는 정책과 구조 설명에 사용할 수 있다.

## 문서에 command를 적는 조건

사람이 수행할 고위험 command를 runbook에 기록할 때:

1. Human-controlled command임을 명시한다.
2. Read-only 검증 command와 변경 command를 구분한다.
3. 실행 전 조건과 실행 후 확인 결과를 제공한다.
4. 실패 시 rollback 또는 troubleshooting 경로를 제공한다.
5. 실제 실행 결과처럼 작성하지 않는다.

## 허용 가능한 진단

Task에서 금지하지 않았다면 `git status`, `git diff`, file search, local static
check와 read-only object 조회를 사용할 수 있다. Production `kubectl get`,
`describe`, `logs`, `curl`은 접근 자체가 운영 verification이므로 현재 task 또는
human operator가 명시적으로 허용한 경우에만 실행한다.
