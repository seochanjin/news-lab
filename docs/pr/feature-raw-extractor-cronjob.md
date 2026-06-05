# 본문 추출 CronJob 구성

## 작업 내용

- K3s에서 기존 본문 추출 스크립트 `scripts/extract_raw_articles.py`를 주기 실행하기 위한 CronJob manifest를 추가했습니다.
- 운영자가 manifest 적용 후 수동 Job을 만들어 검증할 수 있도록 Runbook에 raw extractor CronJob 운영 명령을 추가했습니다.
- 실제 실행한 정적 검증 결과와 아직 실행하지 않은 production verification 항목을 verification 문서에 분리해 기록했습니다.

## 주요 변경 사항

- `k8s/news-raw-extractor-cronjob.yaml` 추가
  - `apiVersion: batch/v1`
  - `kind: CronJob`
  - CronJob 이름: `news-raw-extractor`
  - 스케줄: `30 3 * * *`
  - 타임존: `Asia/Seoul`
  - `concurrencyPolicy: Forbid`
  - `successfulJobsHistoryLimit: 3`
  - `failedJobsHistoryLimit: 3`
  - `backoffLimit: 1`
  - 기존 RSS collector CronJob과 동일한 이미지 패턴 사용: `seocj/news-api:latest`
  - 기존 secret 패턴 재사용: `news-api-secret`의 `DATABASE_URL`
  - 실행 명령: `python scripts/extract_raw_articles.py`
  - 기존 app workload nodeSelector 및 resource request/limit 패턴 유지
- `docs/RUNBOOK.md` 변경
  - raw extractor CronJob 적용 명령
  - CronJob 조회 명령
  - CronJob 기반 manual Job 생성 명령
  - manual Job pod/log 조회 명령
  - `/extractor/status`, `/extractor/runs?limit=5` 확인 명령
  - manual Job 삭제 명령
- `docs/verification/feature-raw-extractor-cronjob.md` 변경
  - 실제 실행한 정적 검증 명령과 결과 기록
  - production/K3s 검증은 pending으로 기록

## 추가/변경된 API

- 없음.
- FastAPI app 코드는 변경하지 않았습니다.

## DB 변경 사항

- 없음.
- DB migration은 추가하지 않았습니다.
- Supabase SQL은 실행하지 않았습니다.

## 테스트

- 완료:

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

- Pending production verification:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl apply -f k8s/news-raw-extractor-cronjob.yaml

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob

JOB_NAME=news-raw-extractor-manual-$(date +%s)

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl create job \
  --from=cronjob/news-raw-extractor \
  $JOB_NAME

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME

POD_NAME=$(KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods \
  -l job-name=$JOB_NAME \
  -o jsonpath='{.items[0].metadata.name}')

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs $POD_NAME

curl https://api.dev-scj.site/extractor/status
curl "https://api.dev-scj.site/extractor/runs?limit=5"

KUBECONFIG=~/.kube/oci-k3s.yaml kubectl delete job $JOB_NAME
```

## 확인 결과

- YAML parse check 통과:

```text
OK k8s/news-raw-extractor-cronjob.yaml
OK k8s/news-rss-collector-cronjob.yaml
```

- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db scripts k8s/news-rss-collector-cronjob.yaml`는 exit code 0, 출력 없음.
- FastAPI app 코드, DB 파일, scripts, 기존 RSS collector CronJob manifest는 변경하지 않았습니다.
- Production verification은 아직 pending입니다.
- `kubectl apply`, manual Job 생성, pod log 확인, production `curl` 검증은 아직 실행하지 않았습니다.

## 비고

- Approved fixes: 없음.
- PR merge, K3s apply, K3s rollout, production verification은 완료로 주장하지 않습니다.
- 실제 K3s 적용과 운영 검증은 human-controlled operation으로 남아 있습니다.
