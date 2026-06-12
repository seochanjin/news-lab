# Daily Topic Pipeline CronJob 자동화

## 작업 목적

수동 검증된 daily topic pipeline을 Kubernetes CronJob으로 자동화해 매일 최근
24시간 기사 기준의 “오늘의 주요 이슈”를 생성하고, 기존 `topics`와
`topic_articles`에 제한된 범위로 저장할 수 있게 만드는 것이 목적이다.

초기 자동화 이후 첫 scheduled run에서 발견된 장시간 실행과 빈 로그 문제를
바탕으로, Job 실행 시간 제한과 단계별 운영 로그도 보강했다.

## 기존 문제

- Daily topic pipeline은 실행 가능한 상태였지만 provider 호출과 DB 저장을
  사람이 직접 실행해야 했다.
- RSS collector와 raw extractor 이후 자동 실행할 schedule이 없었다.
- 자동 write 범위, 중복 실행 방지, cleanup, disable/rollback 절차를 운영
  구성으로 고정할 필요가 있었다.
- 초기 CronJob의 첫 `04:00 Asia/Seoul` scheduled run은 Pod 생성, Secret env
  reference 주입, image 내 script 존재까지 성공했지만 Job이 5시간 이상
  `Running` 상태로 남았다.
- 해당 Job의 `kubectl logs`는 비어 있었고 신규 `/topics` row도 확인되지 않아,
  마지막 진행 단계와 hang 지점을 판단할 수 없었다.

## 변경 내용

- `news-daily-topic-pipeline` CronJob manifest 추가
- `04:00 Asia/Seoul` schedule과 `concurrencyPolicy: Forbid` 설정
- 검증된 provider 및 topic/article 제한값과 자동 운영용 `--execute` 적용
- 기존 `news-api` image, Secret reference, node selector, resource/security
  pattern 재사용
- Job에 `activeDeadlineSeconds: 1800`을 추가해 실행 시간을 30분으로 제한
- CronJob command를 `python -u scripts/run_daily_topic_pipeline.py`로 변경
- daily pipeline에 secret-safe 단계별 progress logging과 exception traceback
  logging 추가
- manifest 정적 테스트에 deadline과 unbuffered command 순서 검증 추가
- RUNBOOK에 apply, manual Job, 로그 확인, cleanup, disable/rollback,
  30분 deadline 확인 절차 추가

## 구현 상세

CronJob은 기존 운영 흐름 다음 순서로 실행되도록 구성했다.

```text
03:00 KST  news-rss-collector
03:30 KST  news-raw-extractor
04:00 KST  news-daily-topic-pipeline
```

자동 실행 command는 다음 값으로 제한했다.

```text
python -u scripts/run_daily_topic_pipeline.py
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

`max-topics=3`은 실제 raw extraction, provider summary, DB write 대상을 최대
3개 topic으로 제한한다. `max-reference-topics=10`은 report 참고 후보이며
실제 extraction, summary, DB write 대상이 아니다.

`activeDeadlineSeconds: 1800`은 종료되지 않는 Job을 30분 후 실패 처리한다.
`python -u`와 단계별 progress logging은 `kubectl logs`에서 pipeline 시작,
article 조회, embedding, topic candidate 생성, raw extraction, summary,
DB write의 마지막 시작/완료 단계를 확인할 수 있게 한다.

로그에는 config의 비밀이 아닌 운영값, count, selected article ID만 포함한다.
`DATABASE_URL`, API key, raw article full text, credential, token, `.env` 내용은
기록하지 않는다. Runtime exception은 traceback을 기록한 뒤 다시 발생시켜
기존 Job 실패 의미를 유지한다.

## 대안 검토

- **애플리케이션 내부 scheduler**
  - API replica lifecycle과 결합되고 중복 실행 제어가 복잡해 제외했다.
- **GitHub Actions schedule**
  - Production DB/provider credential과 운영 경계가 GitHub Actions로
    확장되므로 제외했다.
- **기존 raw extractor CronJob 즉시 suspend**
  - Daily pipeline의 정상 scheduled run이 아직 확인되지 않아 human
    decision으로 보류했다.
- **Pipeline 내부 HTTP/provider/raw extraction timeout 즉시 추가**
  - Hang 원인이 아직 분리되지 않았으므로 우선 Kubernetes deadline과 로그
    가시성을 보강하고, 반복 시 별도 작업으로 다루기로 했다.
- **Commit SHA image tag로 전환**
  - 현재 `news-api` 운영 패턴인 `latest`와 `imagePullPolicy: Always`를
    유지하고 image tag 전략 변경은 별도 CI/CD 작업으로 보류했다.
- **더 많은 topic 저장 또는 threshold/model 변경**
  - 운영 안정성 보강 범위를 벗어나며 provider 비용과 write 범위를 늘리므로
    기존 검증값을 유지했다.
- **Manifest test에 PyYAML dependency 추가**
  - Repository에 선언되지 않은 dependency를 추가하지 않고 표준 라이브러리
    문자열 assertion을 유지했다. YAML parse는 별도 로컬 확인으로 기록했다.

## 선택한 접근과 근거

기존 K3s CronJob 패턴을 재사용하면서 daily pipeline을 독립 CronJob으로
분리했다. 이 방식은 API server lifecycle과 분리해 schedule, manual Job,
disable/rollback을 운영자가 명확히 제어할 수 있다.

첫 scheduled run에서 확인된 문제에 대해서는 원인이 확정되지 않은 상태에서
provider나 extraction 동작을 변경하지 않았다. 대신 30분 Job deadline으로
장기 실행의 운영 영향을 제한하고, unbuffered 단계별 로그로 다음 실행에서
원인 구간을 식별할 수 있도록 했다.

## 트레이드오프

- `--execute` 자동 Job이므로 성공 시 provider 호출과 기존 topic 테이블 write가
  발생한다.
- `concurrencyPolicy: Forbid`는 중복 실행을 막지만 실행 중인 Job이 있으면 다음
  schedule이 건너뛰어질 수 있다.
- 30분 deadline은 장기 hang을 제한하지만 정상 작업이 30분을 초과하면 실패
  처리된다.
- `backoffLimit: 1`은 일시 오류 재시도를 허용하지만 provider 비용이 추가될 수
  있다.
- 단계별 로그는 hang 구간을 보여주지만 내부 HTTP/provider timeout 자체를
  해결하지는 않는다.
- 기존 raw extractor와 selected extraction이 함께 운영되어 일시적으로 추출
  작업이 중복될 수 있다.
- 기존 `latest` image pattern을 유지하므로 배포 artifact의 commit 단위
  추적성은 제한적이다.

## 테스트

Verification 문서에 기록된 실제 로컬 결과:

- Python compile: 통과
- Manifest focused tests: 3개 통과
- Full unittest discovery: 119개 통과
- YAML static parse: `cronjob manifest ok`로 통과
- `git diff --check`: 통과
- Manifest test에서 schedule, timezone, safety settings, bounded command,
  Secret reference, `activeDeadlineSeconds: 1800`,
  `python -u scripts/run_daily_topic_pipeline.py` 순서를 확인

Approved fix 적용 후에도 compile, manifest focused tests, full unittest
discovery, `git diff --check`가 모두 통과했다.

## 운영 반영

Human-provided pre-fix 운영 확인 결과:

- CronJob은 `04:00 Asia/Seoul`에 scheduled trigger되었다.
- Job Pod가 시작되었고 Secret env reference가 정상 주입되었다.
- Image 내 `/app/scripts/run_daily_topic_pipeline.py` 존재가 확인되었다.
- Job은 5시간 이상 `Running` 상태였고 logs는 비어 있었다.
- 신규 `/topics` row는 확인되지 않았다.
- Stuck Job은 human operator가 삭제했다.

Approved fix가 포함된 최신 manifest의 production 적용과 검증은 pending이다.

- 수정 manifest human-controlled apply: pending
- Manual 또는 scheduled Job의 단계별 로그 확인: pending
- Job 성공 또는 30분 초과 실패 처리 확인: pending
- 성공 후 production `/topics` 확인: pending
- 다음 `04:00 Asia/Seoul` scheduled run 확인: pending
- 기존 `news-raw-extractor` suspend 결정: pending

Codex는 post-fix kubectl 명령, provider call, raw extraction, 실제 DB write,
Supabase SQL, production curl, rollout, git push, git merge를 실행하지 않았다.
PR merge 또는 post-fix production deployment 완료를 주장하지 않는다.

## README 업데이트 판단

README 변경은 필요하지 않다. 이번 변경은 사용자-facing API 사용법이 아니라
K3s batch 운영과 장애 확인 절차에 해당한다. Apply, manual Job, logs, cleanup,
disable/rollback, deadline 확인 방법은 `docs/RUNBOOK.md`에 기록하는 것이 기존
문서 역할과 맞다.

## 확인 결과

- Daily topic pipeline의 자동 실행 schedule과 bounded `--execute` command를
  manifest로 고정했다.
- 첫 scheduled run을 통해 schedule trigger, Pod 시작, Secret reference,
  script 존재는 확인되었다.
- 첫 scheduled Job completion과 DB write는 성공하지 못했으며, logs도 비어
  있었다.
- 승인된 후속 fix로 30분 deadline, unbuffered 실행, secret-safe 단계별 로그,
  manifest regression test를 추가했다.
- DB schema/migration, API route/response, frontend, Dockerfile, GitHub
  Actions, 운영 threshold/model, 기존 RSS/raw extractor CronJob, secret은
  변경하지 않았다.
- Post-fix production 동작은 아직 검증되지 않았다.

## 이번 단계의 의미

수동 daily topic pipeline을 단순히 CronJob으로 등록하는 데서 끝내지 않고,
첫 실제 scheduled run에서 드러난 장시간 실행과 관찰 불가능 문제를 운영
안전장치와 진단 로그로 보완했다.

현재 상태는 자동 실행 범위, 중복 실행 정책, 최대 실행 시간, 로그 관찰 지점,
human-controlled rollback 절차가 코드와 문서에 명시된 상태다. 다만 post-fix
production 성공 여부는 다음 human-controlled 검증으로 확정해야 한다.

## 포트폴리오용 요약

Embedding과 LLM summary를 사용하는 daily news topic pipeline을 K3s
CronJob으로 자동화했다. 검증된 provider/DB write 범위를 command로 제한하고,
`Forbid` concurrency와 30분 active deadline으로 중복 및 장기 실행 위험을
관리했다. 첫 scheduled run에서 발생한 5시간 이상 실행과 빈 로그 문제를
바탕으로 Python unbuffered 실행, secret-safe 단계별 progress logging,
traceback logging, manifest regression test, 운영 RUNBOOK을 보강했다.

## 다음 단계 후보

- Human-controlled updated CronJob apply와 manual Job 검증
- 단계별 로그로 hang 발생 구간 확인
- 다음 `04:00 Asia/Seoul` scheduled run과 `/topics` 결과 확인
- Hang 반복 시 내부 HTTP, raw extraction, OpenAI request timeout 별도 설계
- 기존 `news-raw-extractor` CronJob suspend 여부 결정
- Provider summary 품질 모니터링과 frontend 노출 전 품질 검토
- CronJob 실패 알림, 실행 시간, provider 비용 모니터링
- Commit SHA 기반 image tag 전략 검토
