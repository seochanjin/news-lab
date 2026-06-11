# Daily Topic Pipeline CronJob 자동화

## 작업 내용

- 수동 검증된 daily topic pipeline을 매일 `04:00 Asia/Seoul`에 실행하는
  Kubernetes CronJob manifest를 추가했습니다.
- 자동 운영 command는 검증된 제한값과 명시적 `--execute`를 사용합니다.
- RUNBOOK에 적용, 조회, manual Job, 로그, cleanup, disable/rollback 절차를
  human-controlled 명령으로 문서화했습니다.

## 주요 변경 사항

- `k8s/news-daily-topic-pipeline-cronjob.yaml`
  - 이름: `news-daily-topic-pipeline`
  - schedule/timezone: `0 4 * * *`, `Asia/Seoul`
  - `concurrencyPolicy: Forbid`, `restartPolicy: Never`, `backoffLimit: 1`
  - 기존 `seocj/news-api:latest`, app node selector, resource/security pattern
    재사용
  - `news-api-secret`의 DB/provider key reference 재사용
  - threshold 0.70, max topics 3, reference topics 10 등 bounded command와
    `--execute` 포함
- `tests/test_daily_topic_pipeline_cronjob_manifest.py`
  - schedule, 안전 설정, 전체 command, Secret reference 패턴 정적 검증
- `docs/RUNBOOK.md`
  - apply/get/manual Job/logs/cleanup/disable/re-enable/delete 절차 추가

## 추가/변경된 API

- 없음.
- 기존 `/topics` API를 그대로 사용합니다.

## DB 변경 사항

- DB schema, migration, 신규 테이블 및 컬럼 변경은 없습니다.
- CronJob이 실제 적용되면 기존 `topics`, `topic_articles`에만 저장합니다.
- 이번 구현/검증에서 실제 DB write는 수행하지 않았습니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 운영 절차는 `docs/RUNBOOK.md`에 기록했습니다.

## 테스트

실행한 로컬 검증:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py
python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest -v
python -m unittest discover -s tests -v
git diff --check
```

- Python compile: passed.
- Manifest focused tests: 3 passed.
- Full unittest discovery: 119 passed.
- YAML static parse check: passed.
- `git diff --check`: passed.
- 금지 범위 scope diff: empty.

## 확인 결과

- Manifest에 task의 schedule, 안전 설정, bounded `--execute` command가
  포함됨을 정적으로 확인했습니다.
- 기존 RSS/raw extractor CronJob과 application, DB, API, frontend,
  Dockerfile, GitHub Actions, pipeline script는 변경하지 않았습니다.
- Secret 값은 확인하거나 기록하지 않았습니다.

## 비고

- Approved fixes 문서에 승인된 code/config fix는 없습니다.
- K3s apply, manual Job, scheduled run, production `/topics` 검증은 pending입니다.
- `news-api-secret`에 필요한 key 이름이 존재하는지 확인하는 작업은 Secret 값을
  노출하지 않는 human-controlled pending 항목입니다.
- 기존 `news-raw-extractor` CronJob suspend는 human decision pending입니다.
- PR merge, deployment, rollout 완료를 주장하지 않습니다.
- Kubectl, Supabase SQL, provider call, DB write, production curl, push, merge는
  실행하지 않았습니다.
