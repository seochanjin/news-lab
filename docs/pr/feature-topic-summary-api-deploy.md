# Topic summary API 운영 배포 및 production read verification

## 작업 내용

- 이미 구현된 `/topics`, `/topics/{topic_id}` read API의 운영 반영 상태를
  human-controlled K3s rollout과 production API 응답으로 검증했습니다.
- Restart 전 production Pod가 이전 application version을 제공해 `/topics`
  요청이 404를 반환하는 것을 확인했습니다.
- Human operator가 `news-api` Deployment를 rollout restart한 뒤 topic 목록,
  상세, related article metadata, raw text 미노출, missing topic 404를
  확인했습니다.
- 구현 변경 없이 deployment verification 결과와 운영 evidence를
  workflow 문서에 기록했습니다.

## 주요 변경 사항

- `docs/verification/feature-topic-summary-api-deploy.md`
  - local/static 검증 결과와 human-provided K3s/production verification
    evidence를 기록합니다.
- `docs/devlog/feature-topic-summary-api-deploy.md`
  - 배포 검증 목적, 안전 경계, 운영 반영 상태를 정리합니다.
- review/fixes placeholder
  - 자동 review 또는 미승인 fix를 적용하지 않은 상태를 명시합니다.
- 애플리케이션 동작, API endpoint, DB schema, K8s manifest는 변경하지 않습니다.

## 추가/변경된 API

- 없음.
- 기존 `GET /topics`, `GET /topics/{topic_id}`가 production에서 정상 조회되는
  것을 확인했습니다.
- 목록과 상세 응답에 `raw_text`가 포함되지 않으며, 존재하지 않는 topic은
  HTTP 404를 반환합니다.

## DB 변경 사항

- 없음.
- Supabase SQL, manual SQL, save CLI `--execute`, production DB write를
  수행하지 않았습니다.

## README 영향

- README, RUNBOOK, ARCHITECTURE는 변경하지 않았습니다.
- Production read verification은 완료되었으므로 README/RUNBOOK/ARCHITECTURE
  업데이트 필요성 검토가 남아 있습니다.
- 이번 PR draft 작성 범위에서는 해당 문서를 추가 변경하지 않았습니다.

## 테스트

- Local/static validation 결과는
  `docs/verification/feature-topic-summary-api-deploy.md`를 source of truth로
  사용합니다.
- Full unittest discovery: 108 tests passed.
- `git diff --check`: passed.
- K8s, GitHub Actions, frontend, Dockerfile, DB scope checks: no diff.
- Security grep: credential 값 미발견.
- Human-controlled K3s 및 production read verification:
  - Restart 전 Deployment/Pod/Service/Ingress/log 확인: passed
  - Restart 전 `/health`, `/version`: passed
  - Restart 전 `/topics`, `/topics/1`: 404, 이전 image/application version 확인
  - Human-controlled rollout restart: completed
  - Restart 후 `/topics`, `/topics/1`: passed
  - Raw text 미노출 및 missing topic HTTP 404: passed

## 확인 결과

- Human operator가 제공한 logs 기준으로 `news-api` rollout restart 후 새 Pod
  2개가 `1/1 Running`, restart 0 상태임을 확인했습니다.
- Production `/topics?page=1&page_size=10`에서 저장된 deterministic summary를
  조회했습니다.
- Production `/topics/1`에서 related article metadata를 조회했습니다.
- Production topic detail 응답에 `raw_text`가 없고, 존재하지 않는 topic은
  HTTP 404와 `Topic not found`를 반환했습니다.
- Production DB write, Supabase SQL, save CLI `--execute`, raw extraction,
  provider call은 수행되지 않았습니다.
- 코드, API, DB schema, K8s, CronJob, Dockerfile, GitHub Actions, frontend
  변경은 없습니다.

## 비고

- K3s 확인, rollout restart, production curl verification은 human operator가
  수행했으며 Codex가 실행하지 않았습니다.
- Main branch 및 GitHub Actions image build/push 상태 확인은 release
  traceability가 필요하면 pending입니다.
- Approved fix는 없으며 PR merge는 수행되지 않았습니다.
