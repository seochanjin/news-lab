# NewsLab Backend Runbook

이 문서는 backend 운영 절차의 진입점이다. Production-impacting command는
사람이 직접 판단하고 실행한다.

## 빠른 상태 확인

Tailscale SSH tunnel과 kubeconfig를 준비한 사람이 다음 read-only command를
순서대로 실행한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get nodes
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -A
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs
curl https://api.dev-scj.site/health
curl https://api.dev-scj.site/collector/status
curl https://api.dev-scj.site/extractor/status
curl https://api.dev-scj.site/topics/home
curl https://api.dev-scj.site/three-day-topics/home
curl https://api.dev-scj.site/weekly-topics/home
```

Production API `curl`도 task 또는 human operator가 허용한 경우에만 agent
verification과 구분해 실행한다.

## Backend 배포와 rollback 기준

Backend `news-api` 배포 image는 `seocj/news-api:<full-git-sha>` 형식의 immutable
tag를 운영 manifest에 기록한다. GitHub Actions가 image build에 성공하면 manifest
update bot PR을 생성하고, 사람이 PR diff를 검토해 merge한다. Argo CD는 Manual
Sync 정책을 유지하므로 사람이 `OutOfSync`와 diff를 확인한 뒤 Sync를 승인한다.

Rollback은 이전 정상 full SHA로 manifest를 바꾸는 PR과 Argo CD Manual Sync로
수행한다. `kubectl rollout restart`만으로 image version을 변경하지 않으며,
`latest`는 운영 manifest와 rollback 기준으로 사용하지 않는다. Auto sync,
automatic prune, automatic self-heal은 적용하지 않는다.

Daily·3-day·Weekly Home Redis cache 반영 시에도 같은 GitOps 경계를 따른다.
사람이 manifest diff에서 `news-redis` Deployment/Service와 `news-api` 및 세
Pipeline CronJob의 `REDIS_URL`, 기간별 TTL, `REDIS_TIMEOUT_SECONDS` 변경만
포함됐는지 확인한 뒤 Argo CD Manual Sync를 승인한다. 현재 TTL은 Daily·3-day
`108000`초, Weekly `691200`초다.

Redis 장애 검증은 사람이 승인한 운영 창에서만 수행한다. 정상 상태의 cache hit
로그를 확인한 뒤 Redis 중단, 세 Home API의 PostgreSQL fallback 정상 응답,
Redis 복구, miss 후 재저장과 이후 hit 로그를 순서대로 확인한다. 기간별 key와
Pipeline prewarm 검증은 [CronJob 운영](runbooks/cronjobs.md)을 따른다.

## 장애 발생 시 첫 확인 순서

1. Node readiness와 Pod 상태·restart count를 확인한다.
2. 최근 event와 영향받은 object의 `describe`를 확인한다.
3. 현재 log와 restart가 있었다면 `--previous` log를 확인한다.
4. Service, Ingress, Certificate, CronJob, Job 상태를 영향 범위에 따라 확인한다.
5. 변경 명령을 실행하기 전에 수집한 증거와 예상 영향을 기록한다.
6. Apply, delete, patch, rollout, restart, migration은 사람이 결정한다.

## 세부 Runbook

- [일상 운영 점검](runbooks/routine-check.md)
- [Backend 배포와 domain/TLS 확인](runbooks/backend-deploy.md)
- [CronJob 운영](runbooks/cronjobs.md)
- [Database와 local read check](runbooks/database-check.md)
- [장애 초기 대응](runbooks/troubleshooting.md)
- [Argo CD Manual Sync 계획](runbooks/argocd-manual-sync-plan.md)

## Human-controlled operation

다음 작업은 자동 실행하지 않는다.

- PR merge와 main branch merge 결정
- Supabase SQL과 migration 실행
- Kubernetes manifest apply
- K3s rollout, restart, object 변경·삭제
- Weekly Topic production migration, 수동 Job과 API 최종 확인
- Secret 생성 또는 변경
- Production verification
- Redis 중단과 복구를 포함한 production 장애 주입
- OCI security rule, DNS, domain, TLS 변경

Agent의 상세 금지 범위는
[금지 및 사람 통제 작업](agent/forbidden-commands.md)을 따른다.
