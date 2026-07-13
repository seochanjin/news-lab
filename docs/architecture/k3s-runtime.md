# K3s Runtime

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 구성

Backend workload는 Oracle Cloud A1 node의 K3s cluster에서 실행된다.
Repository의 Kubernetes 정의는 `k8s/`에 있다.

- `news-api.yaml`: Deployment, Service, Ingress
- `redis.yaml`: `/topics/home` cache-aside용 Redis Deployment, Service
- `news-rss-collector-cronjob.yaml`: RSS collector CronJob
- `news-daily-topic-pipeline-cronjob.yaml`: daily topic pipeline CronJob
- `news-three-day-topic-pipeline-cronjob.yaml`: three-day topic pipeline CronJob
- `cluster-issuer.yaml`: cert-manager ClusterIssuer
- `monitoring/`: kube-prometheus-stack 설정

Daily topic pipeline은 topic을 먼저 선정한 뒤 selected article의 원문만 확보한다.
Three-day topic pipeline은 Daily 이후 기존 article embedding을 재사용해 최근
72시간 기사를 독립적으로 재클러스터링한다.
별도 `news-raw-extractor` CronJob은 배포 대상에 포함하지 않는다.

API와 CronJob manifest는 `workload: app` node selector를 사용하고
`seocj/news-api:<full-git-sha>` image를 참조한다. `latest`는 운영 manifest와
rollback 기준으로 사용하지 않는다.

Redis는 PostgreSQL source of truth 앞의 삭제 가능한 성능 최적화 계층이다.
`news-redis`는 persistence 없이 실행되며 cache 데이터 유실 시 API가
PostgreSQL에서 payload를 다시 생성한다. Redis object 생성과 변경은 manifest
merge 후 Argo CD Manual Sync로 사람이 수행한다.

## 접근 경로

Kubeconfig의 API endpoint는 local `127.0.0.1:6443`을 사용한다. Operator가
Tailscale network를 통한 SSH tunnel을 열고 별도 terminal에서 `kubectl`을
실행한다. Private address, kubeconfig 내용, SSH key 경로의 실제 값은 문서와
verification log에 기록하지 않는다.

## 운영 경계

Object 조회, describe, log 확인은 read-only 진단이다. Manifest apply, object
delete/patch/edit, rollout, restart, label 또는 scheduling 변경은 사람이
결정하고 실행한다. 세부 명령은 [Backend deploy runbook](../runbooks/backend-deploy.md)
과 [Troubleshooting](../runbooks/troubleshooting.md)을 참고한다.
