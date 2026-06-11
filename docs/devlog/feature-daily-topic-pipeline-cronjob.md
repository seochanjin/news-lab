# Daily Topic Pipeline CronJob 자동화

## 작업 목적

수동 실행과 production read까지 검증된 daily topic pipeline을 매일 정해진
시간에 제한된 범위로 자동 실행할 수 있도록 Kubernetes CronJob 구성을
추가하는 것이 목적이다.

## 기존 문제

- Daily topic pipeline은 하나의 명령으로 실행할 수 있었지만 사람이 직접
  provider와 `--execute` 옵션을 포함해 실행해야 했다.
- 매일 생성되는 “오늘의 주요 이슈” summary를 안정적으로 갱신할 자동 운영
  schedule이 없었다.
- 자동 write 범위와 운영 중 disable/rollback 절차를 manifest와 RUNBOOK에서
  명확히 고정할 필요가 있었다.

## 변경 내용

- `news-daily-topic-pipeline` CronJob manifest 추가
- `04:00 Asia/Seoul` schedule 설정
- 기존 RSS collector 03:00, raw extractor 03:30 이후 실행 순서 유지
- 검증된 threshold 0.70과 최대 topic/article 제한값 적용
- provider flags와 자동 운영용 `--execute` 포함
- 기존 image, Secret reference, node selector, resource/security pattern 재사용
- manifest 정적 테스트 추가
- RUNBOOK에 apply부터 disable/rollback까지 human-controlled 절차 추가

## 구현 상세

CronJob은 `python scripts/run_daily_topic_pipeline.py`를 다음 제한값으로
실행한다.

```text
window-hours=24
max-articles=300
similarity-threshold=0.70
max-topics=3
max-reference-topics=10
max-articles-per-topic=3
max-raw-chars-per-article=3000
summary-model=gpt-5-nano
use-embedding-provider=true
use-summary-provider=true
execute=true
```

`max-topics=3`으로 실제 summary/DB write 범위를 제한한다.
`max-reference-topics=10`은 report용 후보 제한이며 extraction, provider summary,
DB write 대상이 아니다.

CronJob은 기존 `news-api` 이미지와 `news-api-secret` key reference를
재사용한다. Secret 값은 코드나 문서에 포함하지 않았다.

## 대안 검토

- **애플리케이션 내부 scheduler 사용**
  - API replica 수와 lifecycle에 결합되고 중복 실행 제어가 복잡해 제외했다.
- **GitHub Actions schedule 사용**
  - production DB/provider credential과 cluster 운영 경계가 GitHub Actions로
    확장되므로 제외했다.
- **기존 raw extractor CronJob 즉시 suspend**
  - Daily pipeline scheduled run 검증 전에는 운영 영향이 불확실해 human
    decision으로 남겼다.
- **더 많은 topic 자동 저장**
  - Provider 비용과 DB write 범위를 늘리므로 수동 검증된 3개 제한을 유지했다.
- **Manifest 테스트를 PyYAML 기반으로 유지**
  - 로컬 환경에는 PyYAML이 있었지만 repository dependency로 선언되어 있지
    않았다.
  - 새 dependency를 추가하지 않고 표준 라이브러리 기반 정적 assertion으로
    committed test를 구성했으며, YAML parse는 별도 로컬 검증으로 기록했다.

## 선택한 접근과 근거

기존 K3s CronJob 운영 패턴을 재사용했다. `timeZone`, `Forbid`, Job history,
backoff, node selector, resource/security context를 기존 manifest와 맞추면
운영 일관성을 유지하면서 daily pipeline만 독립적으로 disable하거나 manual
Job으로 검증할 수 있다.

## 트레이드오프

- `--execute`를 포함한 자동 Job이므로 Secret key 누락, provider 장애, summary
  품질 문제는 scheduled run 실패 또는 품질 저하로 이어질 수 있다.
- `concurrencyPolicy: Forbid`는 중복 write를 방지하지만 장시간 실행 중 다음
  schedule은 건너뛸 수 있다.
- `backoffLimit: 1`은 일시 오류 재시도를 허용하지만 provider 비용이 추가될 수
  있다.
- 기존 raw extractor와 daily pipeline의 selected extraction이 한동안 함께
  운영되어 추출 작업이 중복될 수 있다.
- CronJob은 기존 Secret key reference를 가정한다. 실제 cluster Secret에
  필요한 key 이름이 존재하는지는 값을 노출하지 않는 human verification이
  필요하다.

## 테스트

- Python compile: 통과
- Manifest focused tests: 3개 통과
- Full unittest discovery: 119개 통과
- YAML static parse: 통과
- `git diff --check`: 통과
- 기존 CronJob과 application/DB/API/frontend/Dockerfile/GitHub Actions scope
  diff: 변경 없음

## 운영 반영

이번 단계에서는 manifest와 운영 절차만 구현했다.

- K3s apply: pending
- Manual Job 실행 및 로그 확인: pending
- Production `/topics` 확인: pending
- 다음 04:00 KST scheduled run 확인: pending
- 기존 raw extractor CronJob suspend 결정: pending
- `news-api-secret` 필수 key 이름 존재 확인: pending

Kubectl, provider call, raw extraction, 실제 DB write, Supabase SQL, production
curl, deployment, rollout, push, merge는 실행하지 않았다.

## README 업데이트 판단

README 변경은 필요하지 않다. 이 변경은 사용자 기능 사용법보다 K3s 운영
절차에 해당하므로 apply, 검증, cleanup, disable/rollback 절차를 RUNBOOK에
기록했다.

## 확인 결과

- 자동 운영 command가 human-approved 수동 실행값으로 제한됨을 정적으로
  확인했다.
- Secret 값 없이 기존 Secret key reference 패턴만 재사용했다.
- 기존 RSS/raw extractor CronJob은 변경하거나 suspend하지 않았다.
- Approved fixes 문서에 승인된 code/config fix는 없으며, review에 따른
  추가 변경도 적용하지 않았다.
- Production 적용과 자동 실행 성공 여부는 human verification pending이다.

## 이번 단계의 의미

수동 daily topic pipeline을 K3s에서 독립적으로 운영할 수 있는 자동화 단위로
전환했다. 자동 write 범위, 중복 실행 방지, retry, disable/rollback 절차를
manifest와 문서로 명시해 production 적용 전 검토 가능한 상태를 만들었다.

## 포트폴리오용 요약

Embedding 기반 daily news topic pipeline을 Kubernetes CronJob으로 자동화할
수 있도록 04:00 KST schedule, bounded provider/DB write command,
concurrency/retry 정책, Secret reference, security/resource 설정을 구성했다.
Manifest 정적 테스트와 운영 RUNBOOK을 함께 추가해 적용 전 안전성과 운영
절차를 검증 가능하게 만들었다.

## 다음 단계 후보

- Human-controlled CronJob apply와 manual Job 검증
- 다음 04:00 KST scheduled run 및 `/topics` 결과 확인
- 기존 `news-raw-extractor` CronJob suspend 여부 결정
- Provider summary 품질 모니터링 및 frontend 노출 전 품질 검토
- CronJob 실패 알림과 비용/실행 시간 모니터링
