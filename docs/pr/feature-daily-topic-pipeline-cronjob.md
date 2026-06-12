# Daily Topic Pipeline CronJob 실행 제한 및 로그 보강

## 작업 내용

- 수동 검증된 daily topic pipeline을 매일 `04:00 Asia/Seoul`에 실행하는 Kubernetes CronJob manifest를 추가했습니다.
- 첫 scheduled run에서 Job이 5시간 이상 `Running` 상태로 남고 `kubectl logs` 출력이 비어 있는 문제가 관찰되어, 후속 approved fix로 실행 제한과 로그 가시성을 보강했습니다.
- 자동 운영 command는 검증된 제한값과 명시적 `--execute`를 유지합니다.
- RUNBOOK에 적용, 조회, manual Job, 로그, cleanup, disable/rollback 절차를 human-controlled 명령으로 문서화했습니다.

## 주요 변경 사항

- `k8s/news-daily-topic-pipeline-cronjob.yaml`
  - 이름: `news-daily-topic-pipeline`
  - schedule/timezone: `0 4 * * *`, `Asia/Seoul`
  - `concurrencyPolicy: Forbid`, `restartPolicy: Never`, `backoffLimit: 1`
  - `activeDeadlineSeconds: 1800` 추가
    - Job이 30분 이상 완료되지 않으면 실패 처리
  - command를 `python -u scripts/run_daily_topic_pipeline.py`로 변경
    - Python stdout/stderr unbuffered logging 적용
  - 기존 `seocj/news-api:latest`, app node selector, resource/security pattern 재사용
  - `news-api-secret`의 DB/provider key reference 재사용
  - threshold 0.70, max topics 3, reference topics 10 등 bounded command와 `--execute` 유지

- `scripts/run_daily_topic_pipeline.py`
  - secret-safe progress logging 추가
  - pipeline start/completion/failure 로그 추가
  - article fetch, raw state/text fetch, embedding, topic candidate generation, raw extraction, summary provider, DB write 단계 로그 추가
  - exception 발생 시 traceback logging 후 exception 재발생
  - API key, `DATABASE_URL`, raw article full text, credential 값은 로그에 출력하지 않음

- `tests/test_daily_topic_pipeline_cronjob_manifest.py`
  - schedule, 안전 설정, 전체 command, Secret reference 패턴 정적 검증
  - `activeDeadlineSeconds: 1800` 검증 추가
  - `python -u scripts/run_daily_topic_pipeline.py` command 순서 검증 추가

- `docs/RUNBOOK.md`
  - apply/get/manual Job/logs/cleanup/disable/re-enable/delete 절차 추가
  - 30분 active deadline과 로그 확인 기준 문서화

- `docs/fixes/feature-daily-topic-pipeline-cronjob-approved-fixes.md`
  - 첫 scheduled run에서 관찰된 장시간 Running 문제 기록
  - 승인된 Fix 1-5 반영
    - 실행 시간 제한
    - Python unbuffered logging
    - manifest test 보강
    - daily pipeline 단계별 progress logging
    - PR/task/review 문서 불일치 정리

## 추가/변경된 API

- 없음.
- 기존 `/topics` API를 그대로 사용합니다.

## DB 변경 사항

- DB schema, migration, 신규 테이블 및 컬럼 변경은 없습니다.
- CronJob이 실제 적용되면 기존 `topics`, `topic_articles`에만 저장합니다.
- 이번 코드 변경 자체는 DB schema나 저장 구조를 변경하지 않습니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 이번 변경은 사용자-facing 기능 설명보다 CronJob 운영 안정성 및 관찰성 보강에 해당합니다.
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
- Protected-scope diff: empty.

## 확인 결과

- Manifest에 task의 schedule, 안전 설정, bounded `--execute` command가 포함됨을 정적으로 확인했습니다.
- `activeDeadlineSeconds: 1800`과 `python -u` command가 포함됨을 확인했습니다.
- 기존 RSS/raw extractor CronJob과 application, DB schema, API, frontend, Dockerfile, GitHub Actions는 변경하지 않았습니다.
- 운영 관찰 후 승인된 fix에 따라 `scripts/run_daily_topic_pipeline.py`에는 secret-safe progress logging을 추가했습니다.
- Secret 값은 확인하거나 기록하지 않았습니다.

## 비고

- Approved fixes 문서에 승인된 Fix 1-5를 적용했습니다.
- 이번 fix는 hang 원인을 확정하는 변경이 아니라, 장시간 Running 방지와 로그 가시성 확보를 위한 운영 안전장치입니다.
- post-fix K3s apply, manual Job, scheduled run, production `/topics` 검증은 pending입니다.
- `news-api-secret`에 필요한 key 이름이 존재하는지 확인하는 작업은 Secret 값을 노출하지 않는 human-controlled 항목입니다.
- 기존 `news-raw-extractor` CronJob suspend는 human decision pending입니다.
- PR merge, deployment, rollout 완료를 주장하지 않습니다.
- Kubectl, Supabase SQL, provider call, DB write, production curl, push, merge는 Codex가 실행하지 않았습니다.

## 리뷰 요청 포인트

- `activeDeadlineSeconds: 1800` 위치가 batch/v1 CronJob spec상 적절한지
- `python -u` command 변경이 기존 argument 순서를 깨지 않는지
- progress logging이 secret-safe한지
- manifest test가 timeout/unbuffered command를 충분히 검증하는지
- 추가로 필요한 CronJob 운영 안전장치가 있는지
