# Argo CD 최소 설치 및 Backend Manual Sync 검증

## 작업 내용

- 68차 승인형 GitOps 설계를 기준으로 Backend `news-api`의 Argo CD 최소 도입
  조건과 운영 절차를 구체화했다.
- Argo CD `v3.4.2` 공식 non-HA manifest, K3s `v1.35.5+k3s1`과 ARM64
  호환성, 설치 namespace와 접근 방식을 확정했다.
- `ClusterIssuer/letsencrypt-prod`를 shared infrastructure 소유로 유지하고
  Backend Application 관리 대상에서 제외했다.
- 사람이 최초 diff를 확인하고 Manual Sync를 승인하는 운영 경계와 실패 시
  중단 조건을 architecture 및 runbook 문서에 반영했다.
- 승인된 FIX-01~07을 적용해 Task, Verification과 workflow artifact의 완료
  상태, 링크, 검증 주장과 재현 가능한 command를 정리했다.

## 주요 변경 사항

- `k8s/argocd/news-api-application.yaml`에 선언형 `Application/news-api`를
  추가했다.
  - source: `https://github.com/seochanjin/news-lab.git`, revision `main`,
    path `k8s`
  - destination: in-cluster, namespace `default`
  - directory recursion 비활성화
  - `cluster-issuer.yaml` 제외
  - automated sync, automatic prune, automatic self-heal 비활성화
  - workload cascade 삭제를 유발하는 resources finalizer 미사용
- Architecture 문서에 설치 방식, ARM64/Kubernetes 전제, credential 및
  ownership 경계, Backend 최초 도입 결과를 기록했다.
- Runbook에 설치 전 승인 gate, Application bootstrap, 최초 diff 검토,
  Manual Sync와 최종 read-only 점검 절차를 추가했다.
- Task, Verification, Approved Fixes, PR 및 devlog workflow 문서를 갱신했다.
- 승인된 review fix를 반영했다.
  - production API 완료 주장을 실제 증거가 있는 `/health`로 한정
  - review artifact의 잘못된 상대 링크 수정
  - 빈 CodeRabbit artifact에 실제 findings와 현재 Verdict 기록
  - Task의 Verification 참조를 Backend 전용 문서로 교체
  - Ruby manifest assertion placeholder를 실행 가능한 전체 명령으로 교체

## 추가/변경된 API

없음.

- FastAPI endpoint, request/response schema와 public API 계약을 변경하지 않았다.
- 기존 production `/health` 응답만 Verification에서 확인했다.

## DB 변경 사항

없음.

- DB schema, migration, Supabase data와 production DB write를 변경하지 않았다.
- Argo CD Sync에도 DB migration을 포함하지 않았다.

## README 영향

README는 변경하지 않았다.

이번 PR은 Backend Application의 최초 Manual Sync 검증 단계다. Frontend
Application, immutable image tag와 controlled rollback 검증이 남아 있으므로
README의 현재 운영 구조를 Argo CD 기반으로 확정해서 설명하기에는 이르다는 Task
판단을 유지했다.

## 테스트

- Repository 및 manifest 정적 확인
  - branch, working tree와 최근 commit 확인
  - Backend Kubernetes resource 및 `ClusterIssuer` 존재 확인
  - Application YAML의 repository, revision, path, exclude, destination과
    Manual Sync 설정 확인
  - automated sync, prune, self-heal 및 resources finalizer 부재 확인
- 사람 통제 환경에서 Verification에 기록된 확인
  - K3s `v1.35.5+k3s1`, 세 node의 ARM64 architecture와 설치 자원 확인
  - Argo CD 핵심 Pod 7개 Ready, Deployment 6개와 StatefulSet 1개 Ready
  - `argocd-server` Service가 `ClusterIP`이고 Argo CD Ingress가 없음을 확인
  - port-forward HTTPS 접근, admin 로그인, password 변경과 초기 credential
    Secret 삭제 확인
  - generated Backend resource 7개 및 `ClusterIssuer` 제외 확인
  - 최초 diff가 Argo CD tracking annotation 추가만 포함함을 확인
  - `--prune`, `--force`, `--replace` 없는 Manual Sync와
    `Synced`/`Healthy` 상태 확인
  - Backend Deployment rollout, `2/2 Ready`, Pod restart count 0,
    Service·Ingress와 네 CronJob 상태 확인
  - production `/health` 정상 응답 확인
  - 최종 `argocd app diff` 출력 없음 및 exit code 0 확인
- 문서 및 범위 확인
  - `git diff --check`: exit code 0
  - 금지 영역 `app`, `scripts`, `db`, `.github`, Docker 및 dependency diff:
    출력 없음
  - UNIT-01~04, Verification `passed`, Pending Verification `없음`의 상태 일치
    확인
  - Antigravity artifact의 production API 완료 주장이 `/health`로 한정되고
    잘못된 `../docs/` 링크가 제거됐음을 확인
  - Task의 이전 baseline Verification 참조 및 Verification의 Ruby placeholder
    제거 확인
  - 전체 Ruby Application manifest assertion 재실행:
    `Application manifest assertions passed`, exit code 0
  - FIX-03~07 변경 범위가 review artifact 두 개, Task, Verification과
    Approved Fixes 문서로 제한됨을 확인

## 확인 결과

- Verification Status는 `passed`, Pending Verification은 `없음`이다.
- 확인 시점의 `news-api` Application은 Sync Policy `Manual`,
  `Synced to main (2ef4adb)`, `Healthy`였다.
- 관리 대상은 Backend Deployment, Service, Ingress와 네 CronJob 등 7개이며
  모두 `ORPHANED: No`였다.
- `ClusterIssuer/letsencrypt-prod`는 Application 관리 범위에 포함되지 않았다.
- 확인 시점의 Backend Deployment는 `2/2 Ready`, Backend Pod 2개는
  `Running`/restart count 0이었다.
- 네 CronJob은 `SUSPEND=False`, `ACTIVE=0`이고 최근 관련 Pod는 모두
  `Completed`였다.
- Argo CD 핵심 Pod 7개는 `1/1 Running`/restart count 0이었고 public
  Ingress는 없었다.
- Approved Fixes의 FIX-01~07을 적용하고 허용된 재검증 결과를 Verification에
  기록했다.
- `/version`, 주요 read-only API와 Prometheus/Grafana의 개별 실행 결과는
  Verification에 없으므로 이 PR에서 검증 완료로 주장하지 않는다.

## 비고

- 이 문서는 PR 초안이며 merge 완료를 의미하지 않는다. `git push`,
  `git merge`와 GitHub PR 생성은 수행하지 않았다.
- PR 작성 과정에서는 Kubernetes 변경, rollout, Sync 또는 production API
  검증을 새로 실행하지 않았다. 위 운영 결과는 Verification에 기록된 사람이
  수행한 명령과 당시 결과를 요약한 것이다.
- CodeRabbit 외부 재검토는 자동 실행하지 않았다. 관련 artifact의 현재
  Verdict는 `CHANGES REQUIRED`이며 comment resolve와 재검토는 사람 작업으로
  남아 있다.
- Argo CD는 non-HA이며 Backend image는 계속 `latest`를 사용한다. 완전한
  배포 재현성이나 고가용성을 제공한다는 의미가 아니다.
- Frontend Application, immutable SHA image tag 전환, controlled rollback,
  Tailscale 내부 접근, backup/upgrade/recovery와 Automated Sync 검토는 후속
  task로 남긴다.
- Private repository credential 연동은 현재 public repository 범위 밖이며
  승인된 fix에 포함되지 않아 추가하지 않았다.
