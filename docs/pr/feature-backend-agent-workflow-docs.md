# backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## 작업 내용

- `AGENTS.md`를 backend agent 작업의 짧은 진입점으로 정리했습니다.
- `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`를 index 문서로 축소하고, 세부
  내용을 책임별 하위 문서로 분리했습니다.
- Codex와 Antigravity가 공통으로 따르는 backend agent workflow를 추가했습니다.
- WIP 1, 작업 단위 완료 조건, checklist 운영 방식, verification Gate 1~5를
  명문화했습니다.
- 금지 command와 human-controlled operation을 구분했습니다.
- 승인된 review fixes에 따라 `scripts/agent_next_step.sh`의 prompt와 workflow
  안내를 신규 문서 구조에 맞게 갱신했습니다.

## 주요 변경 사항

- Architecture 문서를 다음 영역으로 분리했습니다.
  - 전체 구성
  - FastAPI/API
  - Database
  - 수집·추출·주제 pipeline
  - K3s runtime
  - Domain/TLS
- Runbook을 다음 운영 목적별로 분리했습니다.
  - 일상 운영 점검
  - Backend 배포
  - CronJob 운영
  - Database/local read check
  - 장애 초기 대응
- Agent workflow 문서를 다음 책임별로 분리했습니다.
  - 공통 workflow
  - Codex 구현 지침
  - Antigravity review 지침
  - Verification gate
  - 금지 및 사람 통제 작업
- `scripts/agent_next_step.sh`를 한국어화하고 기존 8개 command를 유지했습니다.
- Helper prompt가 신규 `docs/agent/*` 문서를 기준으로 사용하고,
  Architecture/Runbook에서는 task 관련 세부 문서만 선택하도록 변경했습니다.
- Codex prompt에 WIP 1, checklist 완료 조건, 문제 분류, end-to-end 검증과
  human-controlled verification 원칙을 반영했습니다.
- Antigravity prompt가 task checklist, Approved Fixes, current diff,
  verification evidence를 함께 대조하도록 보완했습니다.
- 최초 review와 재검토는 하나의
  `docs/reviews/<safe-branch>-antigravity.md`에 누적하고 `Re-review N`으로
  이력을 유지하도록 변경했습니다.
- Approved Fixes checklist와 Applied Changes를 실제 적용 및 검증 결과에 맞게
  갱신했습니다.

## 추가/변경된 API

없습니다.

- FastAPI router, endpoint path, request/response schema, status code를
  변경하지 않았습니다.
- 기존 API 설명은 현재 구현을 기준으로 architecture 문서에 재배치했습니다.

## DB 변경 사항

없습니다.

- DB schema, table, column, index, constraint를 변경하지 않았습니다.
- Migration file을 추가하거나 실행하지 않았습니다.
- Supabase SQL과 production data 작업을 수행하지 않았습니다.

## README 영향

README는 수정하지 않았습니다.

이번 변경은 backend 내부 agent workflow와 운영 문서의 구조를 정리하는
작업입니다. 사용자 기능, 설치 방법, 공개 API 사용법은 변경되지 않아 README
갱신이 필요하지 않다고 판단했습니다.

## 테스트

실행 결과의 source of truth는
`docs/verification/feature-backend-agent-workflow-docs.md`입니다.

- `git diff --check`: 통과
- Markdown 상대 링크 검사:
  - 19개 Markdown file 확인
  - broken link 0개
- 문서 구조 및 운영 기준 검색:
  - WIP 1과 Gate 1~5 확인
  - 고위험 command가 금지 또는 human-controlled 문맥에만 존재함을 확인
  - CronJob schedule, API host, Kubernetes resource 명칭 충돌 없음
- 민감정보 pattern 검사:
  - 실제 credential 값 없음
  - 환경 변수명, Secret reference, test placeholder, 정책 문구만 확인
- `scripts/agent_next_step.sh`:
  - `bash -n` 통과
  - executable mode `100755` 유지
  - 기존 8개 command 정상 출력
  - 별도 rereview command 또는 artifact path 없음
  - 핵심 prompt 5개 출력 검증, 총 346줄, 모두 exit code 0
- Approved Fixes 적용 후 Antigravity 재검토:
  - 최초 review 원문 보존
  - 동일 파일에 `Re-review 1` 추가
  - 최종 verdict `APPROVED`

검증 중 script 재작성으로 executable bit가 제거되어 직접 실행이 한 차례
`permission denied`로 실패했습니다. `chmod +x scripts/agent_next_step.sh`로
복원한 뒤 동일 command를 재실행해 모두 통과했습니다.

## 확인 결과

- Architecture index는 45줄, Runbook index는 54줄로 정리됐습니다.
- Agent가 task → 공통 workflow → 역할별 지침 → 관련 architecture/runbook →
  verification/forbidden 문서 순서로 필요한 context만 읽을 수 있습니다.
- Task checklist와 Approved Fixes checklist가 실제 완료 상태에 맞게
  갱신됐습니다.
- Backend application source, DB/migration, Kubernetes manifest, Dockerfile,
  GitHub Actions workflow, frontend는 변경하지 않았습니다.
- Production command, DB write, rollout, production curl verification은
  실행하지 않았습니다.

## 비고

- 현재 단계는 자동화된 agent harness가 아니라 문서 기반
  backend agent-assisted development workflow입니다.
- `scripts/agent_next_step.sh`는 agent, test, GitHub 작업을 직접 실행하지 않고
  prompt와 artifact 경로만 출력합니다.
- 기존 `docs/prompts/*`는 호환용 보조 문서로 유지했습니다. 중복 제거는 후속
  작업입니다.
- Checklist 자동 판정, 검증 command 자동 실행, Git hook 도입은 이번 범위에서
  제외했습니다.
- PR 생성과 merge는 사람이 수행해야 합니다.
- Production deployment와 production verification은 이 task의 범위 밖이며
  완료로 주장하지 않습니다.
- 현재 working tree에는 이번 task와 무관한 기존 Antigravity review 파일 4개의
  변경이 함께 보입니다. PR에 포함하기 전 아래 파일은 이번 branch 변경과
  분리하거나 제외해야 합니다.
  - `docs/reviews/feature-daily-topic-pipeline-antigravity.md`
  - `docs/reviews/feature-embedding-topic-grouping-antigravity.md`
  - `docs/reviews/feature-home-topics-snapshot-design-antigravity.md`
  - `docs/reviews/feature-topic-representative-candidates-antigravity.md`
