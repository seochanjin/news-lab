# Backend immutable image GitOps 운영 검증 최종 정리

## 작업 내용

이미 `main`에 반영된 Backend `news-api` immutable image 기반 GitOps 배포
파이프라인의 운영 검증 결과와 최종 문서를 정리하는 문서 전용 PR입니다.

이번 PR은 UNIT-05~UNIT-08 결과를 중심으로 Architecture, Runbook, Task,
Verification, PR draft, devlog를 현재 운영 상태에 맞게 갱신합니다. Agent는
production command, `kubectl`, `argocd`, `git push`, `git merge`를 실행하지
않았습니다.

## 주요 변경 사항

- `docs/ARCHITECTURE.md`
  - Backend 배포 image 기준이 full Git SHA tag임을 기록했습니다.
  - manifest update bot PR, 사람 merge, Argo CD Manual Sync 흐름을 현재 운영
    기준으로 정리했습니다.

- `docs/RUNBOOK.md`
  - Backend 배포와 rollback 기준을 문서화했습니다.
  - `latest`나 `kubectl rollout restart`만으로 image version을 변경하지 않는다는
    원칙을 명시했습니다.

- `docs/architecture/argocd-manual-sync-design.md`
  - Argo CD Manual Sync 기반 운영 기준을 최신 상태로 정리했습니다.
  - auto sync, automatic prune, automatic self-heal 미적용 원칙을 유지했습니다.

- `docs/runbooks/argocd-manual-sync-plan.md`
  - full SHA image 배포, manifest update bot PR, Manual Sync, PR 기반 rollback
    절차를 현재 운영 기준으로 갱신했습니다.

- `docs/tasks/feature-backend-immutable-image-gitops.md`
  - UNIT-07 rollback/restore 운영 검증 결과를 반영했습니다.
  - UNIT-01~UNIT-08을 완료 처리했습니다.

- `docs/verification/feature-backend-immutable-image-gitops.md`
  - Verification Status를 `passed`로 정리했습니다.
  - 최초 immutable image 배포, rollback, restore 결과와 UNIT-08 최종 로컬 검증
    결과를 기록했습니다.

- `docs/pr/feature-backend-immutable-image-gitops.md`
  - 이번 PR의 성격을 문서 전용 운영 검증 정리 PR로 수정했습니다.

- `docs/devlog/feature-backend-immutable-image-gitops.md`
  - 최종 운영 검증 결과와 남은 후속 후보를 현재 상태 기준으로 정리했습니다.

## 변경하지 않은 영역

이번 PR에서는 다음을 변경하지 않습니다.

- `.github/workflows/docker-build.yml`
- `k8s/*.yaml`
- application code
- scripts
- DB / migration
- dependency
- compose

## 운영 검증 결과

### 최초 immutable image 배포

- image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- Docker Hub image 존재 확인
- `linux/arm64` platform 확인
- Argo CD diff는 Deployment 1개와 CronJob 4개의 image 변경으로 제한
- Manual Sync 성공
- sync revision:
  `7aa397148a5d1c3d931cd9205553d1cd7f5838dc`
- Deployment rollout 성공
- Pod 2개 `Running`, `READY=true`
- CronJob 4개 동일 SHA 사용
- Argo CD `Synced`, `Healthy`
- production `/health` 정상

### Rollback

- image:
  `seocj/news-api:8760b1a6dfa523d1cef7a0c0b5fc22ee014a831f`
- sync revision:
  `1766100d4e8f5abb47b95afc200555b38c7c5bcb`
- diff는 Deployment 1개와 CronJob 4개의 image 변경으로 제한
- Manual Sync 성공
- Deployment rollout 성공
- workload image가 rollback SHA와 일치함을 확인
- Argo CD `Synced`, `Healthy`
- production `/health` 정상

### Restore

- image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- sync revision:
  `522bc4a6331dcc36fda17fbec59557c11c2682ec`
- diff는 Deployment 1개와 CronJob 4개의 image 변경으로 제한
- Manual Sync 성공
- Deployment rollout 성공
- Pod 2개와 CronJob 4개가 restored SHA를 사용하는 것을 확인
- Argo CD `Synced`, `Healthy`
- production `/health` 정상

## 최종 운영 Flow

```text
application code PR merge
→ full Git SHA image build/push
→ manifest update bot PR 생성
→ 사람이 manifest PR 검토·merge
→ Argo CD OutOfSync와 image-only diff 확인
→ Manual Sync
→ rollout과 production health 검증
→ 필요 시 이전 정상 full SHA manifest PR로 rollback/restore
```

## 추가/변경된 API

없음.

- 신규 FastAPI endpoint 없음
- 기존 endpoint path 변경 없음
- request/response schema 변경 없음
- 인증과 권한 정책 변경 없음

## DB 변경 사항

없음.

- migration file 추가 없음
- table, column, index, constraint 변경 없음
- Supabase SQL 실행 없음
- 운영 데이터 수정 없음

## README 영향

README는 변경하지 않았습니다.

최종 운영 흐름과 검증 결과는 Architecture, Runbook, Task, Verification, PR draft,
devlog에 반영했습니다. README는 backend 운영자용 상세 절차의 source of truth가
아니므로 이번 문서 전용 PR 범위에서는 수정하지 않았습니다.

## 테스트

Verification source of truth:
`docs/verification/feature-backend-immutable-image-gitops.md`

최종 상태:

- Verification Status: `passed`
- UNIT-01~UNIT-08 완료
- 현재 운영 및 manifest image:
  `seocj/news-api:7636ee0db92d8fcbf2111688febea2e90edf54a1`
- rollback 검증 image:
  `seocj/news-api:8760b1a6dfa523d1cef7a0c0b5fc22ee014a831f`

로컬 최종 검증:

- workflow YAML parse 통과
- K8s YAML parse 통과
- Backend workload image 5개가 동일 full SHA임을 확인
- K8s workload manifest에 `seocj/news-api:latest` 없음
- `git diff --check` 통과
- `git diff --name-only -- app scripts db requirements.txt docker-compose.yml`
  결과 출력 없음

## 확인 결과

- UNIT-05~UNIT-08 운영 검증 결과와 최종 문서 정리를 반영했습니다.
- 최초 immutable image 배포, rollback, restore가 모두 image-only diff, Manual
  Sync, rollout, workload image 확인, Argo CD `Synced`/`Healthy`, production
  `/health` 정상까지 확인됐습니다.
- 이번 branch의 변경 범위는 문서 파일뿐입니다.
- Application code, scripts, DB, dependency, compose file은 변경하지 않았습니다.
- 최종 review gate는 CodeRabbit review와 사람 검토입니다.
- Antigravity artifact는 과거 검토 기록으로만 유지합니다.
