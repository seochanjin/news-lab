# K3s 모니터링 기본 구성

## 작업 내용

- NewsLab hybrid K3s cluster의 node/pod CPU·memory 상태를 확인하기 위한 kube-prometheus-stack monitoring baseline을 추가했습니다.
- Prometheus, Grafana, kube-state-metrics, node-exporter를 최소 리소스 구성으로 사용합니다.
- Monitoring core workload는 Oracle ARM worker에 배치하고 Raspberry Pi worker는 monitoring target으로 포함합니다.

## 주요 변경 사항

- `k8s/monitoring/kube-prometheus-stack-values.yaml` 추가.
- Alertmanager 비활성화.
- Prometheus retention을 `1d`로 설정.
- Prometheus resources:
  - request: `100m`, `256Mi`
  - limit: `500m`, `512Mi`
- Grafana resources:
  - request: `50m`, `256Mi`
  - limit: `300m`, `512Mi`
- Grafana, Prometheus, Prometheus Operator, kube-state-metrics에 `observability=true` nodeSelector 설정.
- node-exporter에 Pi worker의 `node-role=news-edge-worker:NoSchedule` 및 control-plane/master toleration 설정.
- Grafana는 외부에 노출하지 않고 local `kubectl port-forward`로 접근.
- Helm render/install 명령의 kube-prometheus-stack chart 버전을 `86.2.0`으로 고정.
- Human-approved fixes에 따라 Grafana OOM 이후 resource 값, Prometheus retention, rendered assertion, production verification 상태를 정합성 있게 수정.

## 추가/변경된 API

- 없음.
- FastAPI route, response schema, application behavior를 변경하지 않았습니다.

## DB 변경 사항

- 없음.
- DB schema, migration, Supabase SQL을 변경하거나 실행하지 않았습니다.

## README 영향

- README는 변경하지 않았습니다.
- 이번 작업의 상세 구성과 운영 검증 결과는 task, verification, devlog 문서에 기록하는 것이 적합하다고 판단했습니다.

## 테스트

Agent가 수행한 로컬 검증:

```bash
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'

helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 86.2.0 \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml
```

- YAML parse 성공.
- kube-prometheus-stack chart `86.2.0` pinned render 성공.
- Rendered manifest assertion 성공:
  - Alertmanager custom resource 미생성
  - Monitoring core `observability=true` 배치
  - Prometheus retention `1d`
  - Grafana/Prometheus memory request·limit
  - Pi worker node-exporter toleration
- `git diff -- app db scripts/collect_rss.py scripts/extract_raw_articles.py`: 출력 없음, exit code 0.
- Private/Tailscale IP pattern 검사: 매치 없음.
- Credential 검사: 기존 안전한 참조, redacted placeholder, 검사 명령 문자열, `engine.begin()` false positive만 매치했으며 credential 값은 발견되지 않음.
- 승인 대상 파일 범위의 `git diff --check`: 출력 없음, exit code 0.
- 전체 `git diff --check`: 기존 `docs/reviews/infra-monitoring-baseline-antigravity.md`의 trailing whitespace 2건으로 exit code 2. Review artifact는 approved fix 범위가 아니므로 수정하지 않았습니다.

## 확인 결과

Human operator가 제공한 sanitized production verification 결과:

- Monitoring stack이 `monitoring` namespace에 설치됨.
- Grafana, Prometheus, Prometheus Operator, kube-state-metrics가 `arm-worker-node`에서 Running.
- node-exporter가 `arm-master-node`, `arm-worker-node`, `pi-worker-node`에서 Running.
- 초기 Grafana memory limit `256Mi`에서 UI 접근 중 OOMKilled가 발생했으며, resource 조정 후 Grafana는 `3/3 Running`, restart count `0`.
- Grafana container memory 약 `150Mi`, sidecar container memory 각각 약 `75Mi`.
- `news-api`는 `2/2` available 상태를 유지.

Pending verification:

- Grafana dashboard에서 세 노드의 CPU/memory metrics 직접 확인.
- 선택적 external API regression checks.

## 비고

- Agent는 `kubectl apply`, Helm install/upgrade, rollout, production curl, git push, git merge를 실행하지 않았습니다.
- PR merge 완료를 주장하지 않습니다.
- Production 확인 결과는 human operator가 제공한 sanitized 로그 범위에서만 기록했습니다.
- Grafana credential 값, kubeconfig 내용, node token, 실제 IP 주소는 기록하지 않았습니다.
- Alertmanager, external notification, Loki, Pi temperature metric, Prometheus PVC는 이번 작업 범위에서 제외하거나 deferred 상태로 유지했습니다.
