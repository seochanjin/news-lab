# 본문 추출 CronJob 구성

## 작업 목적

- NewsLab의 raw article extractor를 K3s CronJob으로 자동 실행할 수 있도록 운영 구성을 추가한다.
- 기존 수동 실행 방식인 `scripts/extract_raw_articles.py`를 재사용하고, 실행 이력은 기존 `extraction_runs` 및 `/extractor/*` API로 확인하는 구조를 유지한다.
- PR merge 이후 human operator가 K3s production verification을 수행한 결과까지 문서에 반영한다.

## 기존 문제

- RSS article metadata 수집은 CronJob으로 자동화되어 있었지만, 본문 추출은 수동 실행 상태였다.
- 운영자가 K3s에서 raw extractor를 배포하고 검증할 전용 CronJob manifest와 Runbook 절차가 필요했다.
- 정기 schedule 자동 실행 여부는 실제 scheduled run 이후에만 확인할 수 있으므로 별도 pending 항목으로 남겨야 했다.

## 변경 내용

- `k8s/news-raw-extractor-cronjob.yaml` 추가.
- `news-raw-extractor` CronJob 구성.
- schedule/timezone 설정: `30 3 * * *`, `Asia/Seoul`.
- 실행 명령: `python scripts/extract_raw_articles.py`.
- 기존 `seocj/news-api:latest` 이미지와 `news-api-secret`의 `DATABASE_URL` 패턴 재사용.
- `concurrencyPolicy: Forbid`, Job history limit, resource request/limit 설정.
- CodeRabbit 승인 사항에 따라 container-level `securityContext` hardening 반영.
  - `allowPrivilegeEscalation: false`
  - `capabilities.drop: ["ALL"]`
  - `seccompProfile.type: RuntimeDefault`
- `docs/RUNBOOK.md`에 raw extractor CronJob 운영 명령 추가.
- `docs/verification/feature-raw-extractor-cronjob.md`에 pre-merge static verification과 post-merge production verification 결과 정리.

## 구현 상세

- 기존 `k8s/news-rss-collector-cronjob.yaml`의 운영 패턴을 raw extractor CronJob에 맞춰 재사용했다.
- FastAPI app code, DB migration, `scripts/extract_raw_articles.py`, 기존 RSS collector CronJob manifest는 변경하지 않았다.
- secrets, `.env`, kubeconfig, credentials는 수정하지 않았다.
- `runAsNonRoot`와 `readOnlyRootFilesystem`는 이미지 user와 runtime writable path 검증 전까지 deferred로 남겼다.

## 테스트

Pre-merge static verification은 agent가 수행했다.

```bash
ruby -e 'require "yaml"; ARGV.each { |file| YAML.load_file(file); puts "OK #{file}" }' k8s/news-raw-extractor-cronjob.yaml k8s/news-rss-collector-cronjob.yaml
```

Result:

```text
OK k8s/news-raw-extractor-cronjob.yaml
OK k8s/news-rss-collector-cronjob.yaml
```

```bash
git diff --check
```

Result:

```text
No output. Exit code 0.
```

```bash
git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml
```

Result:

```text
No output. Exit code 0.
```

위 정적 검증으로 FastAPI app code, DB file, scripts, 기존 RSS collector CronJob manifest가 변경되지 않았음을 확인했다.

## 운영 반영

PR merge 이후 human operator가 K3s production verification을 직접 수행했다. Agent가 `kubectl apply`, manual Job 생성, production `curl` 검증을 실행한 것은 아니다.

운영 반영 중 home directory에서 relative path로 `kubectl apply -f k8s/news-raw-extractor-cronjob.yaml`을 먼저 실행해 다음 오류가 발생했다.

```text
error: the path "k8s/news-raw-extractor-cronjob.yaml" does not exist
```

이후 repository root로 이동했다.

```bash
cd workspace
cd news-lab
```

Repository root에서 CronJob apply가 성공했다.

```text
cronjob.batch/news-raw-extractor created
```

CronJob 등록 상태:

```text
NAME                 SCHEDULE     TIMEZONE     SUSPEND   ACTIVE   LAST SCHEDULE   AGE
news-raw-extractor   30 3 * * *   Asia/Seoul   False     0        <none>          29s
```

Later check:

```text
NAME                 SCHEDULE     TIMEZONE     SUSPEND   ACTIVE   LAST SCHEDULE   AGE
news-raw-extractor   30 3 * * *   Asia/Seoul   False     0        <none>          4m28s
```

## 확인 결과

Human operator의 manual production verification 결과:

- K3s nodes: `arm-master-node`, `arm-worker-node` 모두 `Ready`.
- CronJob apply 성공.
- CronJob schedule 확인: `30 3 * * *`.
- CronJob timezone 확인: `Asia/Seoul`.
- CronJob `SUSPEND=False`.
- Manual Job 생성 성공: `news-raw-extractor-manual-1780629604`.
- Manual Job pod: `news-raw-extractor-manual-1780629604-cszhh`.
- Pod 상태: `Running` 이후 `Completed`.
- Pod logs에서 extractor 실행 확인.
- Extractor run `id=2` 생성.
- `target articles: 5`.
- `success_count=5`.
- `failed_count=0`.
- `/extractor/status`에서 latest run `id=2`, `status=success` 확인.
- `/extractor/runs?limit=5`에서 run `id=2` 포함 확인.
- Manual Job cleanup 완료.
- cleanup 이후 `kubectl get jobs | grep raw-extractor` 출력 없음.

Manual Job log summary:

```text
extraction run started: 2
target articles: 5
success: 5
failed: 0
```

API result summary:

```text
/extractor/status latest_run.id=2 status=success success_count=5 failed_count=0
/extractor/runs?limit=5 includes run id=2
```

## 이번 단계의 의미

- 본문 추출 자동화를 위한 K3s CronJob이 production cluster에 적용되었다.
- CronJob에서 생성한 manual Job이 실제 운영 컨테이너에서 `scripts/extract_raw_articles.py`를 실행할 수 있음을 확인했다.
- 실행 결과가 `extraction_runs`에 기록되고 `/extractor/status`, `/extractor/runs?limit=5`에서 조회되는 운영 경로를 확인했다.
- 문서상 pre-merge static verification과 post-merge production verification을 분리해 검증 책임과 실행 주체를 명확히 했다.

## 포트폴리오용 요약

- NewsLab raw article extractor를 K3s CronJob으로 운영할 수 있도록 Kubernetes manifest와 Runbook 절차를 추가했다.
- 기존 `news-api` 이미지와 `DATABASE_URL` secret 패턴을 재사용해 운영 일관성을 유지했다.
- PR merge 이후 human operator가 production에서 CronJob apply, manual Job 실행, pod logs, extractor API 결과, cleanup까지 검증했다.
- 정기 schedule 자동 실행 확인은 다음 `03:30 Asia/Seoul` run 이후 검증할 pending 항목으로 남겼다.

## 다음 단계 후보

- 다음 `03:30 Asia/Seoul` 정기 schedule에서 `news-raw-extractor`가 자동 실행되는지 확인.
- scheduled run 이후 `/extractor/status`와 `/extractor/runs?limit=5`에서 새 run이 기록되는지 확인.
- 운영 이미지 user와 runtime writable path를 확인한 뒤 `runAsNonRoot`, `readOnlyRootFilesystem` 적용 가능성 검토.
