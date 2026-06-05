# 본문 추출 CronJob 구성

## 작업 목적

- NewsLab의 raw article extractor를 K3s CronJob으로 실행할 수 있도록 운영 manifest를 준비한다.
- 기존 수동 실행 방식인 `scripts/extract_raw_articles.py`를 재사용하고, 추출 실행 이력은 기존 `extraction_runs` 및 `/extractor/*` API로 확인하는 구조를 유지한다.
- 실제 K3s 적용과 production verification은 human-controlled operation으로 남겨 둔다.

## 기존 문제

- RSS article metadata 수집은 CronJob으로 자동화되어 있지만, 본문 추출은 수동 실행 상태였다.
- 운영자가 K3s에서 raw extractor를 적용하고 검증할 수 있는 전용 CronJob manifest와 Runbook 절차가 없었다.
- production verification 전에는 CronJob 등록, manual Job 실행, pod log, extractor API 결과를 완료로 주장할 수 없다.

## 변경 내용

- `k8s/news-raw-extractor-cronjob.yaml` 추가
  - CronJob 이름: `news-raw-extractor`
  - 스케줄: `30 3 * * *`
  - 타임존: `Asia/Seoul`
  - 실행 명령: `python scripts/extract_raw_articles.py`
  - 이미지: `seocj/news-api:latest`
  - DB 연결: 기존 `news-api-secret`의 `DATABASE_URL`
  - `concurrencyPolicy: Forbid`
  - Job history limit과 resource request/limit은 기존 RSS collector CronJob 패턴과 맞춤
- `docs/RUNBOOK.md` 업데이트
  - raw extractor CronJob 적용 명령
  - CronJob 조회 명령
  - manual Job 생성, pod 조회, log 조회, extractor API 확인, manual Job 삭제 명령 추가
- `docs/verification/feature-raw-extractor-cronjob.md` 업데이트
  - 실제 실행한 정적 검증만 완료 결과로 기록
  - K3s/production 검증은 pending으로 기록
- `docs/pr/feature-raw-extractor-cronjob.md` 작성
  - 변경 내용, 테스트, 확인 결과, pending production verification 정리

## 구현 상세

- 기존 `k8s/news-rss-collector-cronjob.yaml`의 운영 패턴을 raw extractor CronJob에 맞춰 재사용했다.
- FastAPI app 코드, DB migration, `scripts/extract_raw_articles.py`, 기존 RSS collector CronJob manifest는 변경하지 않았다.
- secrets, `.env`, kubeconfig, credentials는 수정하지 않았다.
- `kubectl apply`, `kubectl rollout`, Supabase SQL, data-writing script는 실행하지 않았다.
- approved fixes는 없었다.

## 테스트

- 실제 실행한 정적 검증:

```bash
ruby -e 'require "yaml"; ARGV.each { |file| YAML.load_file(file); puts "OK #{file}" }' k8s/news-raw-extractor-cronjob.yaml k8s/news-rss-collector-cronjob.yaml
```

```bash
git diff --check
```

```bash
git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml
```

```bash
git status --short
```

- 실행하지 않은 검증:
  - `kubectl apply`
  - CronJob registration check
  - manual Job creation
  - manual Job pod/log check
  - production `/extractor/status` check
  - production `/extractor/runs?limit=5` check
  - manual Job cleanup

## 운영 반영

- Pending.
- production/K3s 반영은 아직 수행하지 않았다.
- 운영자가 review 후 `k8s/news-raw-extractor-cronjob.yaml`을 적용해야 한다.
- 이후 manual Job을 생성하고 pod logs 및 extractor API 결과를 확인해야 한다.
- production verification 결과가 확보되면 `docs/verification/feature-raw-extractor-cronjob.md`에 실제 출력 기준으로 추가 기록해야 한다.

## 확인 결과

- YAML parse check 통과:

```text
OK k8s/news-raw-extractor-cronjob.yaml
OK k8s/news-rss-collector-cronjob.yaml
```

- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml`는 exit code 0, 출력 없음.
- FastAPI app 코드, DB 파일, scripts, 기존 RSS collector CronJob manifest는 변경되지 않았음을 정적 diff로 확인했다.
- production verification은 pending이다.
- `kubectl apply`, manual Job 생성, pod log 확인, production `curl` 검증은 완료되지 않았다.

## 이번 단계의 의미

- 본문 추출 자동화를 위한 K3s 운영 단위가 준비되었다.
- 기존 extractor 구현과 API 구조를 건드리지 않고, 배포/운영 계층에 CronJob manifest만 추가해 변경 범위를 작게 유지했다.
- 실제 데이터 쓰기와 production 검증은 운영자 승인 및 실행 이후에만 완료 처리할 수 있도록 문서상 경계를 분리했다.

## 포트폴리오용 요약

- NewsLab raw article extractor를 K3s CronJob으로 운영할 수 있도록 Kubernetes manifest와 Runbook 절차를 추가했다.
- 기존 `news-api` 이미지와 `DATABASE_URL` secret 패턴을 재사용해 운영 일관성을 유지했다.
- production-impacting command는 실행하지 않고, 정적 검증 결과와 pending 운영 검증을 분리해 기록했다.

## 다음 단계 후보

- 운영자가 `kubectl apply -f k8s/news-raw-extractor-cronjob.yaml` 실행.
- CronJob 등록 상태 확인.
- CronJob에서 manual Job 생성.
- manual Job pod logs 확인.
- `/extractor/status` 및 `/extractor/runs?limit=5`로 실행 이력 확인.
- manual Job 정리.
- production verification 결과를 `docs/verification/feature-raw-extractor-cronjob.md`에 실제 출력 기준으로 기록.
