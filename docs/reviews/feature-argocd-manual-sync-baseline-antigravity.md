# Antigravity Review: NewsLab Argo CD 승인형 배포 구조 설계

## Review Summary

본 Review는 `feature/argocd-manual-sync-baseline` 브랜치에 대해 수행되었습니다. 기존 CI(GitHub Actions)와 수동 배포 방식(kubectl rollout restart)을 조사하고, Argo CD를 도입하기 위한 1단계로서 standalone Application 설정 및 사람 승인 기반 수동 동기화(Manual Sync)에 대한 상세 설계와 운영 계획을 수립한 문서를 검토했습니다.
설계는 K3s 매니페스트 및 리소스를 물리적으로 변경하지 않으면서도, 차기 운영 환경 이식 시 발생 가능한 경계 분할(news-api와 news-lab-web), 이미지 태그 방식 전환(latest -> Git SHA), 보안 가이드라인을 명확하게 제시하고 있습니다.

## Requirement Coverage

- **CI/CD 역할 구분**: 빌드/푸시(CI)와 desired/live state 비교 및 배포(CD)의 역할 구분이 명확히 설명되었습니다.
- **수동 배포 baseline 조사**: 백엔드(`news-lab`) 및 프론트엔드(`news-lab-web`)의 GitHub Actions 트리거 조건, 플랫폼, Docker Hub 푸시 정책, 현 매니페스트 구성이 실제 리포지토리 파일 기준으로 조사 및 기술되었습니다.
- **Application 경계 설정**: standalone Application 2개(`news-api`, `news-lab-web`)에 대해 source repo, main branch revision, k8s/ path, destination default namespace가 지정되었습니다.
- **Manual Sync 정책 수립**: 자동화 정책(`automated`, `prune`, `self-heal`)을 모두 비활성화하고 사람이 diff 확인 후 승인하여 동기화하는 구조를 명확히 설계했습니다. 또한 리소스 삭제를 포함하는 Sync는 별도 사람 승인 절차를 타도록 분리했습니다.
- **보안 및 접근 제어 설계**: `kubectl port-forward`를 1순위 접근 방안으로 채택하여 Argo CD UI/API의 퍼블릭 노출을 예방하고, Secret을 Git에 평문으로 관리하지 않는 원칙을 수립했습니다.
- **이미지 태그 전략**: `latest` 사용을 지양하고 고정 이미지 태그(full Git SHA)를 manifest에 PR 형태로 적용 및 승인하는 흐름을 기술했습니다.
- **Sync/Rollback 책임 경계**: Sync 전/후의 운영자 체크리스트와 Git revision/고정 태그 기반의 수동 롤백 절차를 설계했습니다.
- **단계별 로드맵 분리**: 차기 작업으로 설치, 백엔드/프론트엔드 등록 및 검증, 고정 태그 적용 등의 후속 단계를 명확히 분산했습니다.

## Code Quality / Maintainability

소프트웨어 실행 소스 코드 및 종속성의 변경 사항이 전혀 발생하지 않아 정적 결함 우려가 없습니다. 설계 마크다운 내 데이터 파이프라인 흐름도와 리소스 할당 표(table)의 구조가 직관적이고 가독성이 높습니다.

## Security Review

- 실제 운영 크레덴셜, 패스워드, 민감 토큰 등의 값은 설계 문서에 기재되지 않았습니다.
- Argo CD UI 접근 방식으로 퍼블릭 인그레스 대신 Tailscale 또는 포트 포워딩을 우선 설계하여 외부 침입 표면을 최소화했습니다.

## Operational Risk

- K3s 매니페스트 변경, 헬름 설치, 네임스페이스 생성 등의 작업이 물리적으로 실행되지 않고 기획/설계 문서화 단계에 머무르므로 이번 변경은 문서 중심이며 K3s 리소스 변경 명령을 실행하지 않아 직접적인 운영 변경 위험은 확인되지 않았습니다.

## Scope Control

- 변경 대상 파일이 `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/tasks/main.md`, 그리고 새로 추가된 2개의 설계/계획용 마크다운 파일로 완전 제어되었습니다.
- App of Apps, Canary Deployment, Sealed Secrets 등 고급 및 고난도 아키텍처는 설계 범위에서 명확히 배제되어 불필요한 공수 낭비(Scope Creep)가 발생하지 않았습니다.

## Verification Review

- [docs/verification/feature-argocd-manual-sync-baseline.md](../docs/verification/feature-argocd-manual-sync-baseline.md)에 현재 CI 설정 및 k8s/ 매니페스트, 프론트엔드 리포지토리의 리소스를 교차 점검하기 위해 수행한 grep, find, diff check 명령어와 실제 결과가 상세 기록되었습니다.
- 불필요한 운영 롤아웃이나 테스트 실행은 `skipped` 또는 `human-required`로 예외 없이 지정되어, 검증 결과가 `passed` 상태로 완결되었습니다.

## Documentation Review

- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) 및 [docs/RUNBOOK.md](../docs/RUNBOOK.md)의 인덱스 링크에 새로 추가된 수동 배포 설계 및 계획 페이지 경로가 오타 없이 정확하게 등록되었으며, 링크 대상 파일의 존재 여부도 정상 검증되었습니다.

## Problems Found

- 발견된 문제점(blocker)이 없습니다.

## Required Fixes Before PR

- 수정이 필요한 필수 항목이 없습니다.

## Optional Improvements

- 없음

## Suggested Test Commands

다음 명령어를 실행하여 설계 파일의 유효성과 형식을 확인할 수 있습니다.

```bash
git diff --check
test -f docs/architecture/argocd-manual-sync-design.md
test -f docs/runbooks/argocd-manual-sync-plan.md
```

## Verdict

PASS
