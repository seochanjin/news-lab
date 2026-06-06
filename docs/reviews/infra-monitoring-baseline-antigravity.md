# Antigravity Review: K3s 모니터링 기본 구성

## Review Summary

이번 작업을 통해 NewsLab 하이브리드 K3s 클러스터의 리소스 모니터링을 위한 `kube-prometheus-stack` 기본 설정이 작성되었습니다. Prometheus/Grafana 코어 컴포넌트를 `observability=true` 노드(Oracle ARM worker)에 배치하고, Raspberry Pi 워커 노드의 taint를 허용하는 등 요구사항에 부합하는 구성 항목들이 반영되었습니다.

그러나 실제 파일들을 대조하고 검증하는 과정에서 다음과 같은 중대한 불일치 및 오류가 확인되었습니다:

1. **검증 스크립트 실행 실패**: [docs/verification/infra-monitoring-baseline.md](file:///Users/seochanjin/workspace/news-lab/docs/verification/infra-monitoring-baseline.md)에 기록된 YAML 렌더링 검증 어설션 스크립트가 실제 Grafana 리소스 메모리 설정 값과의 차이로 인해 실패(`RuntimeError`)합니다.
2. **설정값과 문서(Devlog, PR) 간 불일치**: Grafana의 메모리 제한량(256Mi/512Mi vs 128Mi/256Mi)과 Prometheus의 Retention 기간(1d vs 3d)이 리소스 설정 파일과 문서 사이에서 서로 다르게 기술되어 있습니다.
3. **검증 로그 상태 불일치**: 검증 상태는 "Pending human operator execution"(대기 중)으로 적혀 있으나, 하단에는 가상의 혹은 조기 작성된 구체적인 "Production Verification Results"가 포함되어 있어 혼선을 줍니다.

따라서 설정 값과 문서를 동일하게 맞추고 검증 스크립트가 성공하도록 수정하기 전에는 PR 병합이 불가한 상태입니다.

---

## Requirement Coverage

[docs/tasks/infra-monitoring-baseline.md](file:///Users/seochanjin/workspace/news-lab/docs/tasks/infra-monitoring-baseline.md)의 요구사항과 비교한 결과는 다음과 같습니다:

- **Prometheus/Grafana 최소 구성**: 충족. `kube-prometheus-stack` 차트를 사용하여 Alertmanager를 비활성화하고 필요한 구성 요소만 활성화하도록 설정했습니다.
- **Alertmanager 제외**: 충족. `alertmanager.enabled: false`가 설정되어 배포 대상에서 제외되었습니다.
- **Prometheus 짧은 retention 설정**: 충족. `retention: 1d`로 설정하여 저장소 부하를 줄였습니다. (단, 문서에는 3d로 오기됨)
- **Prometheus/Grafana 리소스 request/limit 최소화**: 충족. 하이브리드 클러스터 성능에 맞춰 리소스 제한을 작게 정의했습니다. (단, 설정 파일값과 문서의 기술 값에 차이 발생)
- **코어 모니터링 스택을 Oracle ARM 워커에 배치**: 충족. Grafana, kube-state-metrics, prometheusOperator, prometheusSpec에 `observability=true` nodeSelector가 지정되었습니다.
- **Raspberry Pi 워커 노드 모니터링 포함**: 충족. node-exporter에 `node-role=news-edge-worker` NoSchedule taint에 대한 toleration이 부여되어 정상 작동할 수 있습니다.
- **Grafana 로그인/접속 방식 기록**: 충족. `kubectl port-forward`를 통한 접근 가이드가 기록되었습니다.
- **news-api 2/2 Running 유지 확인**: 미수행 상태(Pending). 검증 로그에는 결과가 적혀 있으나 실제 검증은 대기 상태입니다.

---

## Code Quality / Maintainability

- **간결한 구조**: `k8s/monitoring/kube-prometheus-stack-values.yaml` 파일은 기본 설정을 과하게 변경하지 않고 요구사항에 맞는 오버라이드 값들만 깔끔하게 명시하고 있어 관리하기 좋습니다.
- **배치 정책의 명확성**: `observability=true` 노드 라벨 선택기를 일괄 적용하여 ARM 워커 노드로 코어 컨테이너들을 제한한 점은 타당합니다.
- **설정 주석 부재**: 리소스 할당량(Limit/Request)이나 1d retention을 결정한 배경(하이브리드 환경의 디스크/메모리 보존을 위한 선택)을 values 파일 내 주석으로 짤막하게 기재해 두면 추후 유지보수 시 큰 도움이 될 것입니다.

---

## Security Review

- **비밀 정보 노출 없음**: `.env`, kubeconfig 내용, Grafana 초기 admin 비밀번호 등의 민감한 정보가 YAML 파일이나 문서에 하드코딩되지 않았습니다.
- **안전한 접근 방식**: Grafana 포트를 외부에 인그레스로 노출하지 않고, 내부 Tailscale 및 local `kubectl port-forward` 방식을 안내한 것은 보안 우수 사례에 부합합니다.
- **권한 제어**: node-exporter가 클러스터 노드 리소스 메트릭을 수집할 수 있도록 toleration만 안전하게 정의하였으며 불필요하게 넓은 권한이나 특권(Privileged) 설정이 남용되지 않았습니다.

---

## Operational Risk

- **Helm 차트 버전 고정 부재**: [docs/verification/infra-monitoring-baseline.md](file:///Users/seochanjin/workspace/news-lab/docs/verification/infra-monitoring-baseline.md) 및 [docs/tasks/infra-monitoring-baseline.md](file:///Users/seochanjin/workspace/news-lab/docs/tasks/infra-monitoring-baseline.md)에 기술된 `helm upgrade --install` 명령에 `--version 86.2.0` 옵션이 명시되어 있지 않습니다. 이로 인해 운영자가 나중에 명령을 실행할 때 원치 않는 최신 버전이 설치되어 호환성 이슈를 겪을 수 있습니다.
- **임시 저장소 기반 모니터링**: Prometheus 데이터가 Persistent Volume Claim(PVC) 없이 에페머럴 스토리지로 배포되므로 Pod 재시작 시 메트릭 유실 위험이 있습니다. 이는 Task의 baseline 목표를 위해 수용한 트레이드오프로 명시되어 있으나 운영상 유의해야 합니다.

---

## Scope Control

- **범위 준수**: 매우 우수합니다. 애플리케이션 소스 코드(`app/`), 데이터베이스 스키마 및 마이그레이션 파일(`db/`), 수집/추출 스크립트(`scripts/`) 등 모니터링 인프라와 무관한 파일의 수정을 철저히 방지했습니다.

---

## Verification Review

- **검증 어설션 스크립트 오류**:
  [docs/verification/infra-monitoring-baseline.md](file:///Users/seochanjin/workspace/news-lab/docs/verification/infra-monitoring-baseline.md)의 L71-72에 작성된 Ruby Assertion 스크립트는 Grafana의 메모리 request/limit을 `128Mi` 및 `256Mi`로 기대하지만, [k8s/monitoring/kube-prometheus-stack-values.yaml](file:///Users/seochanjin/workspace/news-lab/k8s/monitoring/kube-prometheus-stack-values.yaml)에는 `256Mi` 및 `512Mi`로 기재되어 있어 명령 수행 시 반드시 오류가 납니다. 검증 로그의 `Rendered manifest assertions: OK` 결과는 실제 렌더링 파일 검증 과정에서 검토되지 않은 잘못된 성공 기록입니다.
- **프로덕션 검증 상태의 모순**:
  L139의 `Status: Pending human operator execution`과 L186의 `No production verification is claimed`가 명시되어 있음에도 불구하고, L189의 `## Production Verification Results` 섹션에는 구체적인 Pod 상태 정보와 리소스 사용량이 기입되어 있어 실제 설치가 수행되었는지 여부를 명확히 파악할 수 없습니다.

---

## Documentation Review

문서 상호 간에 다음과 같은 정합성 오류가 존재합니다:

1. **Prometheus Retention 설정 불일치**:
   - YAML 파일: `retention: 1d` (L39)
   - 검증 스크립트: `retention == "1d"` 기대 (L71)
   - Devlog 문서: `Prometheus retention 3d 설정` (L18)
   - PR 문서: `Prometheus retention을 3d로 제한` (L11)
2. **Grafana 리소스 한계 설정 불일치**:
   - YAML 파일: requests `256Mi`, limits `512Mi`
   - Devlog 문서: requests `128Mi`, limits `256Mi`로 기록됨
   - 검증 스크립트: `128Mi` / `256Mi` 기대

---

## Problems Found

1. **Ruby 검증 어설션 오류**: YAML 렌더링에 대한 ruby 어설션 체크가 실패합니다 (`bad Grafana resources (RuntimeError)`).
2. **Grafana 리소스 정보 불일치**: YAML 설정 파일의 메모리값(`256Mi`/`512Mi`)과 Devlog, 검증 스크립트가 기대하는 메모리값(`128Mi`/`256Mi`)이 불일치합니다.
3. **Prometheus Retention 설정값 오기**: YAML 설정 파일 및 검증 스크립트(`1d`)와 Devlog, PR 문서(`3d`)가 불일치합니다.
4. **검증 결과 상태 왜곡**: 설치를 진행하지 않았다는 선언 아래에 상세한 설치 완료 Pod 결과 데이터가 명시되어 정직한 검증 규칙에 어긋납니다.
5. **Helm 설치 명령어 버전 누락**: 운영 배포 명령어에 `--version` 플래그가 누락되어 버전 일관성을 보장하기 어렵습니다.

---

## Required Fixes Before PR

PR 승인 및 병합을 위해 아래 조치들이 반드시 필요합니다. 단, 해당 조치들은 [docs/fixes/infra-monitoring-baseline-approved-fixes.md](file:///Users/seochanjin/workspace/news-lab/docs/fixes/infra-monitoring-baseline-approved-fixes.md)에 기록되고 운영자(인간)의 승인을 득한 후 수정되어야 합니다.

1. **Grafana 메모리 규격 통일**:
   - 실제 배포 리소스인 YAML 파일에 맞추어 Devlog, PR 문서, 검증 어설션 스크립트 모두 Grafana request `256Mi`, limit `512Mi`로 통일하거나 혹은 그 반대로 통일해야 합니다.
2. **Prometheus Retention 기간 통일**:
   - YAML 파일과 어설션 스크립트에 맞춰 Devlog 및 PR 문서의 retention 기간 문구를 `1d`로 수정합니다.
3. **검증 어설션 스크립트 수정**:
   - 위 규격 통일에 맞추어 검증용 루비 스크립트 내 값을 수정하여 `helm template` 검증 시 무사히 통과되도록 합니다.
4. **프로덕션 검증 섹션 정상화**:
   - 아직 배포가 진행되지 않은 상태라면 `Production Verification Results` 하위의 가짜(혹은 임시) 로그 내용을 비우거나 명시적인 Placeholder 주석으로 대체해야 합니다. 만약 실제 운영자가 설치를 마치고 기록을 원한 것이라면 `Pending` 상태를 `Completed`로 바꾸고 대조해야 합니다.
5. **Helm 명령어 차트 버전 명시**:
   - Task 및 검증 문서의 설치 명령어에 `--version 86.2.0` 옵션을 추가합니다.

---

## Optional Improvements

- `k8s/monitoring/kube-prometheus-stack-values.yaml` 파일 각 설정 블록(Grafana 리소스, Prometheus retention 등) 위에 주석으로 간략하게 하이브리드 리소스 제약을 위해 이와 같이 설정했음을 기술하면 좋습니다.

---

## Suggested Test Commands

수정 예정인 검증 어설션 스크립트가 로컬에서 안전하게 통과하는지 확인하기 위해 다음 명령어를 사용할 수 있습니다:

```bash
# 1. YAML 파일 파싱 상태 확인
ruby -e 'require "yaml"; YAML.load_file("k8s/monitoring/kube-prometheus-stack-values.yaml"); puts "YAML parse: OK"'

# 2. 임시 매니페스트 렌더링
helm template monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  -f k8s/monitoring/kube-prometheus-stack-values.yaml \
  > /tmp/infra-monitoring-baseline-rendered.yaml

# 3. 렌더링 결과에 대해 어설션 통과 여부 검증 (수정본 기준)
ruby -ryaml -e 'docs=YAML.load_stream(File.read(ARGV[0])).compact; find=->(kind,name){docs.find{|d| d["kind"]==kind && d.dig("metadata","name")==name}}; raise "Alertmanager rendered" if docs.any?{|d| d["kind"]=="Alertmanager"}; %w[monitoring-grafana monitoring-kube-state-metrics monitoring-kube-prometheus-operator].each{|name| d=find.call("Deployment",name) or raise "missing #{name}"; raise "bad nodeSelector #{name}" unless d.dig("spec","template","spec","nodeSelector","observability")=="true"}; g=find.call("Deployment","monitoring-grafana"); gc=g.dig("spec","template","spec","containers").find{|c| c["name"]=="grafana"}; raise "bad Grafana resources" unless gc.dig("resources","requests","memory")=="256Mi" && gc.dig("resources","limits","memory")=="512Mi"; p=find.call("Prometheus","monitoring-kube-prometheus-prometheus") or raise "missing Prometheus"; raise "bad Prometheus settings" unless p.dig("spec","retention")=="1d" && p.dig("spec","nodeSelector","observability")=="true" && p.dig("spec","resources","requests","memory")=="256Mi" && p.dig("spec","resources","limits","memory")=="512Mi"; n=find.call("DaemonSet","monitoring-prometheus-node-exporter") or raise "missing node-exporter"; raise "missing Pi toleration" unless n.dig("spec","template","spec","tolerations").any?{|t| t["key"]=="node-role" && t["value"]=="news-edge-worker"}; puts "Rendered manifest assertions: OK"' /tmp/infra-monitoring-baseline-rendered.yaml
```

---

## Verdict

- **FAIL / BLOCKED** (문서 정합성 불일치, 검증 스크립트 실행 오류 및 검증 로그 모순으로 인해 수정 조치 완료 후 재승인 필요)
