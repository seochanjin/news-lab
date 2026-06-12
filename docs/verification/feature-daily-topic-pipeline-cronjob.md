# Verification: Daily Topic Pipeline CronJob 자동화

## Verification Scope

- Daily topic pipeline CronJob manifest 정적 검증
- 04:00 KST schedule과 Job 안전 설정 검증
- 30분 active deadline과 Python unbuffered command 검증
- 자동 `--execute` command의 bounded 운영값 검증
- Daily topic pipeline 단계별 secret-safe progress logging 변경 검증
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
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
git diff --check
python -m unittest discover -s tests -v
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff -- app db frontend Dockerfile .github k8s/news-rss-collector-cronjob.yaml k8s/news-raw-extractor-cronjob.yaml
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
```

## Results

- Python compile: passed.
- Manifest focused tests: passed, 3 tests.
- Full unittest discovery: passed, 119 tests.
- YAML static parse check: passed with `cronjob manifest ok`.
- `git diff --check` and targeted diff check: passed.
- Initial implementation scope diff for application, DB, frontend, Dockerfile,
  GitHub Actions, existing RSS/raw extractor CronJobs, and daily pipeline
  script: empty. The approved follow-up fix intentionally modifies only the
  daily pipeline script from that list.
- Final manifest focused test, YAML parse, `git diff --check`, and scope diff
  rerun after documentation updates: passed.
- Approved-fix Python compile: passed.
- Approved-fix manifest focused tests: passed, 3 tests.
- Approved-fix full unittest discovery: passed, 119 tests.
- Approved-fix final `git diff --check`: passed.
- CodeRabbit follow-up Python compile: passed.
- CodeRabbit follow-up manifest focused tests: passed, 3 tests.
- CodeRabbit follow-up full unittest discovery: passed, 119 tests.
- CodeRabbit follow-up protected-scope diff for application, DB, frontend,
  Dockerfile, GitHub Actions, and existing RSS/raw extractor CronJobs: empty.
- CodeRabbit follow-up fetch-stage logging check confirms one raw text fetch
  start/end pair and a raw extraction state fetch start/end pair.
- Fix 6 YAML structure manifest tests: passed, 3 tests.
- Fix 6 full unittest discovery: passed, 119 tests.
- Fix 6 final `git diff --check`: passed.
- Fix 6 tests parse the CronJob manifest and directly assert nested deadline,
  command prefix, bounded arguments, Secret references, and safety settings.
- The repository has no separate test dependency pattern, so `PyYAML` was added
  as the minimal parser dependency in the existing `requirements.txt`.
- Before Fix 6, the committed manifest test used standard-library text
  assertions because PyYAML was not declared in repository dependencies.
  Fix 6 superseded that approach by declaring PyYAML and parsing the manifest
  for direct nested structure assertions.
- Manifest tests confirm:
  - name `news-daily-topic-pipeline`;
  - schedule `0 4 * * *` and `Asia/Seoul`;
  - `concurrencyPolicy: Forbid`, `restartPolicy: Never`, `backoffLimit: 1`;
  - `activeDeadlineSeconds: 1800`;
  - unbuffered command order:
    `python -u scripts/run_daily_topic_pipeline.py`;
  - required bounded pipeline arguments and explicit `--execute`;
  - existing `seocj/news-api:latest`, node selector, resource/security pattern;
  - `news-api-secret` references for `DATABASE_URL`,
    `OPENAI_EMBEDDING_API_KEY`, and `OPENAI_SUMMARY_API_KEY`.

## Manual or Production Verification

- Human-provided pre-fix production observation:
  - CronJob applied and scheduled at `04:00 Asia/Seoul`.
  - Job Pod started and Secret env references resolved.
  - `scripts/run_daily_topic_pipeline.py` existed in the image.
  - Job remained `Running` for more than 5 hours.
  - `kubectl logs` returned no output.
  - No new `/topics` rows were observed.
  - Human operator deleted the stuck Job.
- Post-fix production verification was not run by Codex.
- The updated CronJob manifest was not applied by Codex.
- No provider call, DB write, production curl, or kubectl command was run by
  Codex while applying the approved fixes.

## Pending Verification

- Human-controlled `kubectl apply` of
  `k8s/news-daily-topic-pipeline-cronjob.yaml`.
- Human-controlled manual or scheduled Job verification that logs identify the
  last completed stage and the Job succeeds or fails after 30 minutes.
- Human-controlled production `/topics` read verification after a successful
  Job.
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
