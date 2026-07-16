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
- `news-weekly-topic-pipeline-cronjob.yaml`: weekly topic pipeline CronJob
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

## Node topology와 workload placement

| Node | 역할 | 현재 placement 기준 |
| --- | --- | --- |
| `arm-master-node` | Oracle Cloud A1 control plane | K3s control-plane component와 node-exporter. 일반 application workload는 배치하지 않음 |
| `arm-worker-node` | Oracle Cloud A1 application worker | Frontend·Backend, Redis, scheduled pipeline, monitoring core, node-exporter |
| `pi-worker-node` | Raspberry Pi edge worker | node-exporter. `node-role=news-edge-worker:NoSchedule` taint로 일반 application 미배치 |

Backend API, Redis와 네 CronJob은 `workload: app` selector를 사용한다.
Monitoring core는 `observability: "true"` selector를 사용하고, node-exporter는
control-plane과 Pi worker의 `NoSchedule` taint toleration을 갖춘다. Frontend
resource는 별도 `news-lab-web` 저장소에서 관리한다.
Traefik, cert-manager, Ingress, Service와 TLS Secret은 cluster 공통 add-on·resource로
보며 특정 application node에 고정된 구성으로 설명하지 않는다.

`pi-worker-node`는 현재 일반 application node가 아니며, 향후
explicit toleration을 명시한 edge/batch workload만 배치하는 후보다.
Manifest는 selector와 toleration을 증명하지만 live node label·taint·Pod
placement는 사람이 제공한 운영 log로만 현재 상태를 재검증한다.

## Monitoring 구조

`k8s/monitoring/kube-prometheus-stack-values.yaml`은 Prometheus, Grafana,
Prometheus Operator와 kube-state-metrics에 `observability: "true"` selector를
적용한다. 기존의 사람 제공 Production Verification에서는 이 monitoring core가
`arm-worker-node`에서 실행되었고, DaemonSet인 node-exporter는
`arm-master-node`, `arm-worker-node`, `pi-worker-node` 세 노드에 배치되었다.

node-exporter는 control-plane/master taint와
`node-role=news-edge-worker:NoSchedule` taint를 toleration하므로 application을
Pi worker에 허용하지 않고도 세 노드의 node metric을 수집할 수 있다. Prometheus
retention은 `1d`이며 Alertmanager는 현재 values에서 비활성화되어 있다.
Grafana 접근과 live metric 확인은 operator가 Tailscale 기반 접근 경로에서
수행하며, public application ingress로 Grafana를 노출하는 구조로 설명하지
않는다. Manifest는 이 desired placement를 증명하지만 현재 Pod readiness와
metric 수집 상태는 새로운 운영 log 없이 재검증된 것으로 간주하지 않는다.

## 접근 경로

Kubeconfig의 API endpoint는 local `127.0.0.1:6443`을 사용한다. Operator가
Tailscale network를 통한 SSH tunnel을 열고 별도 terminal에서 `kubectl`을
실행한다. Private address, kubeconfig 내용, SSH key 경로의 실제 값은 문서와
verification log에 기록하지 않는다.

Tailscale overlay는 Oracle node와 Raspberry Pi node 간 cluster network와
operator 접근을 위한다. 사용자 HTTPS 요청은 Tailscale이 아니라
Public DNS와 Oracle Public IP를 거쳐 Traefik Ingress로 진입한다.

## 운영 경계

Object 조회, describe, log 확인은 read-only 진단이다. Manifest apply, object
delete/patch/edit, rollout, restart, label 또는 scheduling 변경은 사람이
결정하고 실행한다. 세부 명령은 [Backend deploy runbook](../runbooks/backend-deploy.md)
과 [Troubleshooting](../runbooks/troubleshooting.md)을 참고한다.
