# README 및 아키텍처 문서 현행화

## 작업 목적

70~73차에서 구현·운영 검증한 immutable Backend 배포, Redis Home Cache,
Pipeline-driven prewarm과 hybrid K3s 구조를 프로젝트 진입 문서에 반영하는 것이
목적이었다. README는 처음 보는 독자가 서비스의 기능과 운영 구조를 빠르게
이해하게 하고, 상세 설계와 절차는 Architecture와 Runbook으로 연결하도록 했다.

## 기존 문제

- README가 이전 대표 이미지와 `latest` 기반 Backend 설명을 사용했다.
- full Git SHA image build 이후 manifest PR과 Argo CD Manual Sync로 이어지는
  승인 chain이 README에 드러나지 않았다.
- Redis cache-aside, fail-open, 세 기간별 prewarm key와 TTL이 진입 문서에서
  충분히 설명되지 않았다.
- public ingress와 Tailscale, Frontend와 Backend Service 경계가 명확하지 않았다.
- Architecture 개요에서 Weekly Pipeline/table 일부가 누락됐고 Backend deploy
  Runbook은 direct apply와 rollout restart 중심의 과거 절차를 포함했다.

## 변경 내용

- README의 프로젝트 소개, 기능, pipeline, 시스템 구성과 문서 탐색 구조를
  현재 서비스 기준으로 다시 정리했다.
- 사용자 제공 `newslab-architecture_R1.png`를 대표 이미지로 연결했다.
- 공개 요청을 `User → Public DNS → Oracle Public IP → Traefik Ingress →
  Kubernetes Service → Application Pod`로 설명하되 Frontend와 Backend의
  Service/Pod를 분리했다.
- PostgreSQL/Supabase와 Redis의 책임, cache-aside miss/fallback, Pipeline
  post-save prewarm과 TTL을 README와 Architecture에 반영했다.
- GitHub Actions의 ARM64 full-SHA image, 다섯 workload manifest PR, 사람 검토,
  Argo CD OutOfSync/diff와 Manual Sync 배포·rollback 절차를 문서화했다.
- 세 K3s node 역할, monitoring core와 node-exporter placement, public ingress와
  Tailscale의 경계를 정리했다.
- Database/overview에 Weekly 결과와 실행 이력을 보완하고 Runbook 점검 범위를
  세 Home API로 맞췄다.

## 테스트

Verification source of truth는
`docs/verification/docs-readme-architecture-refresh.md`다.

- 대표 이미지 파일과 참조 경로 확인
- current-state image policy와 역사적 `latest` 문맥 구분
- Redis key `topics:home:v1`, `three-day-topics:home:v1`,
  `weekly-topics:home:v1` 및 TTL `108000`, `108000`, `691200` 대조
- RSS/Daily/3-day/Weekly CronJob schedule과 time zone 대조
- README와 Architecture index의 Markdown 상대 링크 검사
- 금지 영역 diff와 `git diff --check` 확인

모든 허용된 최종 문서 검증은 통과했다. Application test suite는 문서 전용
변경이므로 실행하지 않았고 통과로 기록하지 않았다.

## 운영 반영

운영 반영은 수행하지 않았다. 기존 production Verification은 immutable GitOps,
Pipeline prewarm, node placement와 monitoring의 기록 시점 근거로만 참조했다.
새로운 DNS, rollout, live Pod placement, Redis 상태와 endpoint health는 확인하거나
완료로 주장하지 않았다.

## 확인 결과

- README와 Architecture/Runbook이 현재 manifest·workflow와 일치한다.
- 새 대표 이미지 경로와 내부 문서 링크가 모두 존재한다.
- PostgreSQL/Supabase Source of Truth, Redis fail-open cache, 세 prewarm 흐름과
  TTL이 구현·manifest와 일치한다.
- 배포 설명은 `latest`가 아니라 full Git SHA manifest PR과 Manual Sync를
  desired state로 사용한다.
- application, API, DB, pipeline, Kubernetes와 workflow 동작 변경은 없다.

## 이번 단계의 의미

NewsLab의 진입 문서가 단순 기능 소개를 넘어 데이터 생성·저장·조회, cache,
hybrid runtime과 승인형 배포의 책임 경계를 현재 운영 기준으로 연결하게 됐다.
동시에 repository가 증명하는 desired state와 사람이 제공해야 하는 live-state
검증을 분리해 문서의 운영 주장을 과장하지 않도록 했다.

## 다음 단계

- PR diff 검토와 merge 여부 결정은 사람이 수행한다.
- 문서에 기록된 live-state 사실을 다시 확인할 필요가 생기면 별도 Task와
  human-provided production log로 검증한다.
- 이번 UNIT 종료 후 후속 UNIT은 없다. 운영 변경을 자동 실행하지 않는다.
