# Task: raw extractor CronJob scheduled run 검증

## Goal

PR merge 이후 production K3s cluster에 적용된 `news-raw-extractor` CronJob이 manual Job이 아닌 정기 schedule에 의해 자동 실행되는지 확인한다.

이번 작업의 목표는 15차에서 pending으로 남긴 scheduled run verification을 닫는 것이다.

## Scope

- `news-raw-extractor` CronJob 상태 확인
- scheduled Job 생성 여부 확인
- scheduled Job pod 상태 및 logs 확인 가능하면 기록
- `/extractor/status` 확인
- `/extractor/runs?limit=5` 확인
- Supabase/raw_articles 또는 API 결과 기준으로 원문 저장 여부 확인
- 실제 확인 결과를 `docs/verification/chore-raw-extractor-scheduled-verification.md`에 기록
- devlog에 scheduled run 검증 결과 기록

## Do not change

- FastAPI app code
- DB schema / migration
- K8s manifest
- collector script
- extractor script
- secrets, `.env`, kubeconfig, credentials
- GitHub Actions workflow
- production deployment setting

## Expected files

- `docs/tasks/chore-raw-extractor-scheduled-verification.md`
- `docs/verification/chore-raw-extractor-scheduled-verification.md`
- `docs/devlog/chore-raw-extractor-scheduled-verification.md`
- `docs/pr/chore-raw-extractor-scheduled-verification.md`
- `docs/fixes/chore-raw-extractor-scheduled-verification-approved-fixes.md`
- `docs/reviews/chore-raw-extractor-scheduled-verification-antigravity.md`
- `docs/reviews/chore-raw-extractor-scheduled-verification-coderabbit.md`

## DB changes

None.

## API changes

None.

## Test commands

Production read-only verification commands only:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get jobs | grep raw-extractor
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods | grep raw-extractor
curl https://api.dev-scj.site/extractor/status
curl "https://api.dev-scj.site/extractor/runs?limit=5"
```

Static/local documentation validation:

```bash
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## Acceptance criteria

- CronJob news-raw-extractor exists.
- CronJob schedule is still 30 3 \* \* \*.
- CronJob timezone is still Asia/Seoul.
- LAST SCHEDULE is no longer <none> after the scheduled time has passed.
- A scheduled raw extractor Job is found or API run history confirms the scheduled run.
- /extractor/status reports latest successful run.
- /extractor/runs?limit=5 includes the scheduled run.
- Supabase/raw_articles 확인 결과 원문 5개 저장이 확인된다.
- No app, DB, K8s manifest, collector script, or extractor script change is made.
- Production verification results are recorded only from actual human-run commands/logs.

## Notes

- This task closes the pending scheduled verification from the raw extractor CronJob work.
- Manual Job verification was already completed in the previous task.
- This task should not create a new manual Job unless scheduled run evidence is missing and the human explicitly decides to re-test manually.
- README update is not required unless the verification changes the public project status summary.
- Devlog should include alternatives considered, chosen approach, tradeoffs, and README update decision.
