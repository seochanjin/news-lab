# Topic summary API 운영 배포 및 production read verification

## 작업 목적

36차에서 구현하고 local/Supabase 환경에서 검증한 topic summary read API가
운영 K3s 환경에서도 정상 동작하는지 확인하는 작업이다.

새 기능을 추가하는 대신 `GET /topics`, `GET /topics/{topic_id}`의 production
read path, related article metadata, raw text 미노출, missing topic 404를
운영 evidence로 확인하는 데 목적이 있다.

## 기존 문제

- Local API에서는 `/topics` 목록과 상세 조회가 정상 동작했지만 production
  application surface에 반영되었는지 확인되지 않았다.
- 초기 verification 명령은 `news` namespace를 가정했지만 실제 `news-api`
  Deployment는 `default` namespace에 있었다.
- Production K3s resource와 `/health`, `/version`은 정상 상태였지만, restart
  전 `/topics`, `/topics/1`은 `404 Not Found`를 반환했다.
- 이는 DB query 오류가 아니라 running Pod가 이전 image/application version을
  제공하는 rollout/image refresh 문제로 판단되었다.

## 변경 내용

- Documentation-only deployment verification workflow를 작성했다.
- Local/static validation 결과와 human-controlled K3s/production verification
  evidence를 verification 문서에 기록했다.
- 실제 namespace를 발견한 뒤 `default` namespace 기준으로 운영 상태를
  확인했다.
- Human operator의 rollout restart 전후 production API 결과를 기록했다.
- 애플리케이션 코드, API endpoint, DB schema, K8s manifest는 변경하지 않았다.
- Approved fix는 없었다.

## 구현 상세

### Local/static verification

- 전체 unittest와 문서 diff 검사를 수행했다.
- K8s, GitHub Actions, frontend, Dockerfile, DB 변경이 없음을 확인했다.
- Security grep으로 credential 값이 추가되지 않았음을 확인했다.

### Namespace 및 K3s 상태 확인

- 초기 `news` namespace 확인은 namespace 미존재로 실패했다.
- Human operator가 전체 Deployment를 조회해 `news-api`가 `default`
  namespace에 있음을 확인했다.
- Restart 전 Deployment는 `2/2` available 상태였고 기존 Pod 2개는
  `1/1 Running`, restart 0 상태였다.
- Service, Traefik Ingress, application startup log도 정상 상태였다.

### Production read verification과 rollout restart

- Restart 전 `/health`, `/version`은 정상 응답했다.
- Restart 전 `/topics`, `/topics/1`은 `404 Not Found`를 반환했다.
- Human operator가 `news-api` Deployment를 rollout restart했다.
- Restart 후 새 ReplicaSet의 Pod 2개가 `1/1 Running`, restart 0 상태가 되었다.
- Restart 후 `/topics` 목록과 `/topics/1` 상세 조회가 정상 동작했다.
- 상세 응답에서 related article metadata를 확인했고 `raw_text`는 노출되지
  않았다.
- 존재하지 않는 topic은 HTTP 404와 `Topic not found`를 반환했다.

## 대안 검토

### 애플리케이션 코드 수정

Local API와 DB 조회는 이미 검증되었고 restart 전 production에서 route 자체가
404를 반환했으므로 코드 문제로 보지 않았다. 승인되지 않은 코드 변경 없이
배포 상태를 먼저 확인하는 접근을 선택했다.

### K8s manifest 또는 image tag 수정

Task 범위에서 K8s manifest와 deployment 설정 변경은 금지되어 있다. 기존
`seocj/news-api:latest` Deployment를 human-controlled rollout restart로
새로고침했다.

### Production 확인 없이 정상 상태로 기록

운영 evidence가 없는 완료 주장은 배제했다. 실제 human-provided kubectl 및
curl logs가 verification에 기록된 뒤에만 production read verification
완료를 기록했다.

## 선택한 접근과 근거

운영 문제를 application behavior 변경으로 해결하지 않고, read-only
verification으로 현재 상태를 먼저 분리했다.

Restart 전후 API 결과를 비교해 이전 Pod가 오래된 application version을
제공하고 있다는 가설을 확인했다. 이후 human operator가 rollout restart를
수행하고 같은 endpoint를 다시 확인함으로써 배포 반영 여부를 검증했다.

이 접근은 production DB write, migration, raw extraction, provider call 없이
운영 read path만 확인할 수 있다.

## 트레이드오프

- `latest` image와 rollout restart 방식은 어떤 build가 배포되었는지
  traceability가 약하다.
- Main branch 및 GitHub Actions image build/push 상태는 별도 확인이 필요할 수
  있다.
- README/RUNBOOK/ARCHITECTURE를 이번 작업에서 갱신하지 않아 architecture
  문서의 API 목록은 production surface 최신 상태와 차이가 남아 있다.
- Production verification은 실제 데이터 1건 기준이며 대량 조회나 성능은
  검증하지 않았다.

## 테스트

`docs/verification/feature-topic-summary-api-deploy.md`에 기록된 결과:

- Full unittest discovery: 108 tests passed.
- `git diff --check`: passed.
- K8s, GitHub Actions, frontend, Dockerfile, DB scope checks: no diff.
- Security grep: 기존 safe references와 test-only values만 매치되었으며
  credential 값은 발견되지 않았다.
- Human-controlled K3s verification:
  - Deployment/Pod/Service/Ingress/log 상태: passed
  - Restart 후 새 Pod 2개: `1/1 Running`, restart 0
- Human-controlled production read verification:
  - `/health`, `/version`: passed
  - Restart 전 `/topics`, `/topics/1`: 404
  - Restart 후 `/topics`, `/topics/1`: passed
  - Raw text 미노출: passed
  - Missing topic HTTP 404: passed

## 운영 반영

- K3s rollout restart: human operator 수행 완료
- Production topic list/detail read verification: human operator 수행 완료
- Production raw text 미노출 및 missing topic 404 확인: 완료
- Production DB write: 수행하지 않음
- Supabase SQL/manual SQL: 수행하지 않음
- Save CLI `--execute`: 수행하지 않음
- Raw extraction/provider call: 수행하지 않음
- PR merge: pending

## README 업데이트 판단

README, RUNBOOK, ARCHITECTURE는 이번 작업에서 변경하지 않았다.

Production `/topics` read API가 확인되었으므로 운영 surface 문서 업데이트의
근거는 확보되었다. 다만 이번 branch의 핵심 범위는 deployment verification
evidence 정리였고, 현재 architecture 문서도 topic summary API 이전 상태여서
부분적인 한 줄 수정 대신 후속 문서 정합성 작업으로 분리하는 것이 적절하다고
판단했다.

## 확인 결과

- 실제 `news-api` namespace는 `default`임을 확인했다.
- Restart 전 K3s resource는 healthy였지만 production `/topics` route는
  반영되지 않은 상태였다.
- Human-controlled rollout restart 후 새 Pod가 정상 상태로 전환되었다.
- Production `/topics`에서 저장된 deterministic summary를 조회했다.
- Production `/topics/1`에서 related article metadata를 조회했다.
- Production topic detail 응답에 `raw_text`가 포함되지 않았다.
- 존재하지 않는 topic은 HTTP 404를 반환했다.
- 코드, API, DB schema, K8s manifest, CronJob, Dockerfile, GitHub Actions,
  frontend는 변경하지 않았다.

## 이번 단계의 의미

Topic summary 기능이 local/Supabase 검증을 넘어 production read application
surface에서 동작함을 확인했다.

또한 healthy Pod와 최신 application behavior가 동일하지 않을 수 있음을
실제 사례로 확인했다. Resource health 확인과 endpoint-level verification을
함께 수행해야 배포 완료를 판단할 수 있다는 운영 기준을 남겼다.

## 포트폴리오용 요약

FastAPI topic summary read API의 K3s production 배포 상태를 검증했다. 기존
Pod가 healthy 상태였지만 신규 `/topics` route를 제공하지 않는 문제를
restart 전후 endpoint 비교로 진단했고, human-controlled rollout restart 후
topic 목록/상세, related article metadata, raw text 미노출, 404 동작을
확인했다. 코드나 DB write 없이 deployment evidence와 application-level
verification을 연결했다.

## 다음 단계 후보

- Main branch 및 GitHub Actions image build/push 상태 확인으로 release
  traceability 보강
- Immutable image tag 또는 digest 기반 배포 전략 검토
- README/RUNBOOK/ARCHITECTURE에 production `/topics` surface와 검증 절차 반영
- Topic summary 자동 저장 CronJob 설계 전 운영 안전 조건 정의
- Production read monitoring 및 smoke check 자동화 검토
- Human-controlled PR merge
