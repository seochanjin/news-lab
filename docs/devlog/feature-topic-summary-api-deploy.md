# Topic summary API 운영 배포 및 production read verification

## 작업 목적

이미 local/Supabase 환경에서 검증된 topic summary read API를 production에
반영하기 전, 배포 확인과 read-only 운영 검증 절차를 문서화하는 작업이다.

## 기존 문제

- `/topics`, `/topics/{topic_id}`는 local API에서 검증되었지만 production
  rollout 및 read path에 대한 실제 증거가 아직 없다.
- 운영 확인 명령과 Codex가 실행 가능한 local 검증 범위를 분리하지 않으면
  production verification 완료 여부가 불명확해질 수 있다.

## 변경 내용

- deployment verification workflow 문서를 작성했다.
- local/static checks와 human-controlled kubectl/production curl 절차를 분리했다.
- production logs가 없는 항목은 모두 pending으로 유지했다.
- review 및 approved-fixes placeholder에 자동 review/fix 미실행 상태를 기록했다.

## 구현 상세

- Verification 문서는 실제 실행한 local command만 완료 결과로 기록한다.
- Kubectl과 production curl은 예상 명령과 확인 항목만 제공하며 실행 결과로
  취급하지 않는다.
- Production read verification은 `/health`, `/version`, `/topics`,
  `/topics/{topic_id}`, 404, raw text 미노출을 포함한다.

## 대안 검토

- Codex가 kubectl과 production curl을 직접 실행하는 방법은 human-controlled
  operation 경계를 위반하므로 제외했다.
- Production 확인 전 README/RUNBOOK/ARCHITECTURE에 `/topics` 운영 완료를
  반영하는 방법은 검증되지 않은 상태를 문서화하게 되므로 제외했다.

## 선택한 접근과 근거

운영 작업과 문서 작업을 분리하고, production evidence가 없는 상태를
명시적으로 pending으로 유지했다. 이를 통해 실제 operator logs가 제공되기
전까지 배포 완료나 production 정상 동작을 잘못 주장하지 않는다.

## 트레이드오프

- 이번 단계만으로 production endpoint 동작을 보장할 수 없다.
- Human operator가 rollout 및 production read checks를 수행하고 결과를 다시
  기록해야 workflow가 완료된다.

## 테스트

- Full unittest discovery: 108 tests passed.
- `git diff --check`: passed.
- K8s, GitHub Actions, frontend, Dockerfile, DB scope checks에서 diff 없음.
- Security grep에서 credential 값 미발견.
- 실제 command와 상세 결과는 verification 문서에 기록했다.
- Kubectl, production curl, DB write, provider/raw extraction 검증은 실행하지
  않는다.

## 운영 반영

- Production deployment: pending
- K3s rollout: pending
- Production API read verification: pending
- PR merge: pending

## README 업데이트 판단

README, RUNBOOK, ARCHITECTURE는 변경하지 않았다.

Task는 `/topics` API가 production application surface로 확인된 경우에만 해당
문서 업데이트를 허용한다. 현재 human-provided production logs가 없으므로
운영 확인 전 상태를 유지한다.

## 확인 결과

- Documentation-only workflow를 작성했다.
- Production verification 완료를 주장하지 않았다.
- 애플리케이션, API, DB schema, K8s, CronJob, Dockerfile, GitHub Actions,
  frontend, secret/credential을 변경하지 않았다.

## 이번 단계의 의미

기능 구현과 운영 검증 사이에 명시적인 evidence gate를 둔다. 다음 자동화
단계로 진행하기 전에 production read path와 raw text 미노출을 human operator가
확인할 수 있는 절차를 마련했다.

## 포트폴리오용 요약

FastAPI topic summary read API의 production 배포 검증 workflow를 문서화하고,
local static checks와 human-controlled K3s rollout/production API 검증을
분리했다. 실제 운영 logs가 없는 상태에서는 완료를 주장하지 않는 evidence
기반 운영 문서화 원칙을 적용했다.

## 다음 단계

- Human operator가 K3s rollout과 Pod/Service/Ingress/log 상태 확인
- Human operator가 production `/topics` 목록/상세, 404, raw text 미노출 확인
- 실제 logs를 verification 문서에 기록
- Production 확인 이후 README/RUNBOOK/ARCHITECTURE 업데이트 재검토
- Human-controlled PR merge
