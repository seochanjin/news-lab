# README 및 아키텍처 문서 현행화

## 작업 내용

NewsLab의 README와 Architecture/Runbook 진입 문서를 현재 운영 구조에 맞게
현행화하는 문서 전용 변경입니다. 대표 아키텍처 이미지를 R1 자산으로 교체하고,
immutable image 기반 승인형 GitOps, Redis Home Cache, hybrid K3s topology와
운영 경계를 실제 manifest·workflow·기존 운영 검증에 맞춰 정리했습니다.

## 주요 변경 사항

- README를 프로젝트 소개, 데이터 흐름, 요청 경로, Cache, K3s, 배포,
  관측성과 문서 탐색을 한 번에 이해할 수 있는 진입점으로 갱신했습니다.
- `docs/images/newslab-architecture_R1.png`를 README와 Architecture index에
  연결했습니다. 이미지는 사용자가 제공했으며 이번 작업에서 편집하지 않았습니다.
- Frontend와 Backend의 Ingress·Service·Pod 경계를 분리하고 public ingress와
  Tailscale operator/hybrid-node 경로를 구분했습니다.
- PostgreSQL/Supabase를 Source of Truth로, Redis를 삭제 가능한 fail-open
  cache로 설명하고 Daily·3-day·Weekly prewarm key와 TTL을 반영했습니다.
- Backend full Git SHA image build, manifest PR, 사람 merge 검토, Argo CD diff와
  Manual Sync로 이어지는 승인형 GitOps 절차를 문서화했습니다.
- `arm-master-node`, `arm-worker-node`, `pi-worker-node`의 역할과 application,
  monitoring placement를 현재 manifest와 기존 운영 검증 범위에 맞춰 정리했습니다.
- Architecture의 Weekly Pipeline/table 설명과 Runbook의 Weekly Home 점검 및
  full-SHA 배포·rollback 절차를 보완했습니다.
- Review 문서에 finding이 없어 Approved Fixes에는 `없음`을 기록했습니다.

## 테스트

Source of truth는
`docs/verification/docs-readme-architecture-refresh.md`이며 최종 상태는
`passed`입니다.

- 대표 이미지 존재와 README/Architecture 참조 확인: passed
- 오래된 대표 이미지 경로 제거와 current-state full SHA 정책 확인: passed
- Redis key, TTL, fail-open과 Pipeline prewarm 정합성 확인: passed
- 네 CronJob schedule과 `Asia/Seoul` time zone 정합성 확인: passed
- README와 Architecture index의 Markdown 상대 링크 확인: passed
- 금지 영역 변경 검색: 출력 없음
- `git diff --check`: passed

Application test suite는 실행하지 않았습니다. Application code, API, DB,
pipeline, Kubernetes manifest와 workflow 동작을 변경하지 않는 문서 전용
Task이므로 통과로 기록하지 않습니다.

## 확인 결과

- README, Architecture와 Runbook의 현재 운영 설명이 repository manifest와
  workflow의 용어·값에 맞게 정리됐습니다.
- `seocj/news-api:latest` 검색 결과는 명시된 전환 전 baseline 이력에만 남아
  있으며 현재 desired state 설명에는 사용되지 않습니다.
- Frontend 저장소 밖의 runtime과 live node/DNS/cache 상태는 이 저장소에서
  새로 증명한 것처럼 표현하지 않았습니다.
- Application, scripts, Kubernetes, workflow, DB, migration, dependency와
  Secret은 변경하지 않았습니다.

## 비고

- Production command나 새 production verification은 수행하지 않았습니다.
- PR merge, Argo CD Manual Sync, rollout, deployment, Supabase SQL, Docker push,
  `git push`와 `git merge` 완료를 주장하지 않습니다.
- 운영 상태에 관한 기존 Verification은 기록 시점의 근거로만 사용했습니다.
