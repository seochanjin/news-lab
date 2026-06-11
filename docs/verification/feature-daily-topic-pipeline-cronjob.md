# Verification: Daily Topic Pipeline CronJob 자동화

## Verification Scope

- Daily topic pipeline CronJob manifest 정적 검증
- 04:00 KST schedule과 Job 안전 설정 검증
- 자동 `--execute` command의 bounded 운영값 검증
- 기존 image, node selector, resource/security context, Secret reference 패턴 검증
- 기존 RSS/raw extractor CronJob과 application/DB/API 범위 비변경 확인
- RUNBOOK의 human-controlled 운영 절차 문서화 확인

## Commands Run

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -c 'import yaml; from pathlib import Path; data=yaml.safe_load(Path("k8s/news-daily-topic-pipeline-cronjob.yaml").read_text()); assert data["kind"] == "CronJob"; assert data["metadata"]["name"] == "news-daily-topic-pipeline"; assert data["spec"]["timeZone"] == "Asia/Seoul"; assert data["spec"]["concurrencyPolicy"] == "Forbid"; print("cronjob manifest ok")'
git diff --check -- k8s/news-daily-topic-pipeline-cronjob.yaml tests/test_daily_topic_pipeline_cronjob_manifest.py docs/RUNBOOK.md
rg -n '^PyYAML|^pyyaml|yaml' requirements.txt pyproject.toml setup.cfg 2>/dev/null || true
cat requirements.txt; rg -n "yaml" .github Dockerfile docker-compose.yml 2>/dev/null || true
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
git diff -- app db frontend Dockerfile .github k8s/news-rss-collector-cronjob.yaml k8s/news-raw-extractor-cronjob.yaml scripts/run_daily_topic_pipeline.py
git diff --check
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -c 'import yaml; from pathlib import Path; data=yaml.safe_load(Path("k8s/news-daily-topic-pipeline-cronjob.yaml").read_text()); assert data["kind"] == "CronJob"; assert data["metadata"]["name"] == "news-daily-topic-pipeline"; assert data["spec"]["timeZone"] == "Asia/Seoul"; assert data["spec"]["concurrencyPolicy"] == "Forbid"; print("cronjob manifest ok")'
git diff -- app db frontend Dockerfile .github k8s/news-rss-collector-cronjob.yaml k8s/news-raw-extractor-cronjob.yaml scripts/run_daily_topic_pipeline.py
git status --short --branch
git diff --stat
```

## Results

- Python compile: passed.
- Manifest focused tests: passed, 3 tests.
- Full unittest discovery: passed, 119 tests.
- YAML static parse check: passed with `cronjob manifest ok`.
- `git diff --check` and targeted diff check: passed.
- Scope diff for application, DB, frontend, Dockerfile, GitHub Actions,
  existing RSS/raw extractor CronJobs, and daily pipeline script: empty.
- Final manifest focused test, YAML parse, `git diff --check`, and scope diff
  rerun after documentation updates: passed.
- Initial manifest test used locally available PyYAML. Because PyYAML is not
  declared in repository dependencies, the committed unit test was changed to
  standard-library text assertions. The separate YAML parse command remains
  recorded as a local static check.
- Manifest tests confirm:
  - name `news-daily-topic-pipeline`;
  - schedule `0 4 * * *` and `Asia/Seoul`;
  - `concurrencyPolicy: Forbid`, `restartPolicy: Never`, `backoffLimit: 1`;
  - required bounded pipeline arguments and explicit `--execute`;
  - existing `seocj/news-api:latest`, node selector, resource/security pattern;
  - `news-api-secret` references for `DATABASE_URL`,
    `OPENAI_EMBEDDING_API_KEY`, and `OPENAI_SUMMARY_API_KEY`.

## Manual or Production Verification

- Not run.
- No CronJob manifest was applied to K3s.
- No manual Job was created.
- No CronJob logs or scheduled-run results were inspected.
- No production `/topics` curl verification was run for this task.

## Pending Verification

- Human verification that `news-api-secret` contains the required key names,
  without exposing secret values.
- Human-controlled `kubectl apply` of
  `k8s/news-daily-topic-pipeline-cronjob.yaml`.
- Human-controlled CronJob get, manual Job creation, logs, cleanup, and
  production `/topics` read verification.
- Next scheduled `04:00 Asia/Seoul` automatic run verification.
- Human decision on whether to suspend the existing `news-raw-extractor`
  CronJob after scheduled-run verification.

## Evidence Notes

- No secret value was printed, inspected, decoded, or modified.
- No provider call, raw extraction, real DB write, Supabase SQL, migration,
  kubectl command, production curl, deployment, rollout, git push, or git merge
  was performed.
- Production application, rollout, deployment, and CronJob application are not
  claimed complete.
