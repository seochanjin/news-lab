# Backend 배포와 Domain/TLS 확인

[Runbook index로 돌아가기](../RUNBOOK.md)

이 문서의 변경 command는 모두 사람이 실행한다. Agent는 command를 제안하거나
결과를 정리할 수 있지만 apply, rollout, DNS/TLS 변경과 production verification을
자동 실행하지 않는다.

## 승인형 GitOps 배포 전제

Backend application code PR이 `main`에 merge되면 GitHub Actions가
`linux/arm64`용 `seocj/news-api:<full-git-sha>` image를 build/push한다. Build가
성공한 뒤 같은 workflow가 `Deployment/news-api`와 네 Backend CronJob의 image를
동일한 full Git SHA로 갱신하는 manifest PR을 만든다. Image push만으로 cluster
rollout이 시작되지는 않는다.

사람은 manifest PR에서 다음을 확인한 뒤 merge한다.

- 변경 대상이 `k8s/news-api.yaml`과 네 Backend CronJob manifest인지
- 다섯 workload가 같은 40자리 lowercase Git SHA image를 사용하는지
- image 외 schedule, command, selector, Secret reference와 resource 설정이
  의도치 않게 바뀌지 않았는지

`latest`는 registry에 보조 tag로 발행되지만 운영 manifest와 rollback 기준으로
사용하지 않는다. Manifest PR merge, Argo CD Sync와 production verification은
모두 사람이 승인하고 실행한다.

## Argo CD diff와 Manual Sync

Manifest PR merge 후 Argo CD `news-api` Application이 `OutOfSync`를 감지하면
사람이 다음 read-only 조회로 revision, health와 diff를 확인한다.

```bash
argocd app get news-api
argocd app diff news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
```

Diff가 승인된 manifest image 변경과 일치하고 예상하지 않은 resource 생성·삭제,
selector, Service, Ingress, schedule, command 또는 Secret 변경이 없을 때만 사람이
다음 변경 명령을 실행한다.

```bash
argocd app sync news-api
```

`news-api` Application에는 automated sync, automatic prune와 automatic
self-heal을 설정하지 않는다. 예상하지 않은 diff나 `Degraded` 상태가 있으면
Sync를 실행하지 않고 현재 revision, diff, resource health와 event를 보존한 뒤
[Argo CD Manual Sync 계획](argocd-manual-sync-plan.md)의 중단 기준을 따른다.

## Sync 후 rollout과 image 검증

Manual Sync 직후 사람이 rollout, 실제 workload image와 application health를
순서대로 확인한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -l app=news-api -o wide
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deployment news-api \
  -o=jsonpath='{.spec.template.spec.containers[0].image}'
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob \
  -o=custom-columns='NAME:.metadata.name,IMAGE:.spec.jobTemplate.spec.template.spec.containers[0].image'
argocd app get news-api
curl -sS https://api.newslab.ai.kr/health
```

Deployment와 네 CronJob image가 승인한 full SHA와 일치하고, Argo CD가
`Synced`/`Healthy`이며 production health가 정상일 때만 배포 검증을 완료로
기록한다. Agent는 사람이 제공한 실제 log 없이 이 단계를 완료로 표시하지 않는다.

## Rollback

Rollback은 `latest` 재사용이나 `kubectl rollout restart`가 아니라 이전 정상
full SHA를 다섯 workload manifest에 반영하는 PR로 시작한다. 사람이 PR diff를
검토해 merge한 뒤 위와 같은 Argo CD diff 승인, Manual Sync, rollout, workload
image와 production health 검증을 반복한다. 실패 원인을 확인하기 전에 live
resource를 직접 patch하거나 삭제하지 않는다.

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
