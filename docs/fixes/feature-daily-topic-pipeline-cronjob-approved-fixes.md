# Approved Fixes: Daily Topic Pipeline CronJob 자동화

## Approved Fixes

None.

Antigravity review 결과, PR 제출 전 반드시 수정해야 하는 blocking issue는 발견되지 않았다.

## Rejected or Deferred Suggestions

- Commit SHA image tag 전환은 보류한다.
  - 현재 `news-api` Deployment도 `seocj/news-api:latest`와 `imagePullPolicy: Always` 패턴을 사용하고 있다.
  - 이번 작업은 기존 운영 image pattern을 재사용하는 CronJob 자동화가 목적이므로 image tag 전략 변경은 범위 밖이다.
  - 향후 CI/CD 안정화 단계에서 commit SHA 기반 image tag를 검토한다.

- `news-raw-extractor` CronJob suspend는 보류한다.
  - 이번 작업에서는 신규 `news-daily-topic-pipeline` CronJob manifest만 추가한다.
  - 기존 raw extractor suspend 여부는 실제 CronJob 적용, manual Job 검증, scheduled run 검증 이후 human decision으로 판단한다.

- PR/Devlog 문서 상세화는 code fix가 아니라 merge 전 문서 마무리 작업으로 처리한다.
  - Antigravity review에서는 `docs/devlog/feature-daily-topic-pipeline-cronjob.md`와 `docs/pr/feature-daily-topic-pipeline-cronjob.md` 상세화를 optional improvement로 제안했다.
  - 필수 수정 사항은 아니지만 PR 제출 전 문서 품질을 위해 별도로 작성한다.

## Applied Changes

None.

Review 결과에 따른 code/config 변경은 없다.

## Verification Required

추가 code fix가 없으므로 기존 verification 결과를 유지한다.

이미 기록된 검증:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
```

검증 결과:

- Python compile: passed.
- Manifest focused tests: passed, 3 tests.
- Full unittest discovery: passed, 119 tests.
- YAML static parse check: passed.
- `git diff --check`: passed.
- Scope diff에서 application, DB, frontend, Dockerfile, GitHub Actions, 기존 RSS/raw extractor CronJobs, daily pipeline script 변경 없음 확인.

남은 manual verification:

- `news-api-secret`에 필요한 key 이름이 존재하는지 human-controlled 확인
  - `DATABASE_URL`
  - `OPENAI_EMBEDDING_API_KEY`
  - `OPENAI_SUMMARY_API_KEY`
- human-controlled `kubectl apply`
- human-controlled manual Job 생성
- Job logs 확인
- production `/topics` read 확인
- 다음 scheduled `04:00 Asia/Seoul` 자동 실행 확인
- 기존 `news-raw-extractor` CronJob suspend 여부 결정
