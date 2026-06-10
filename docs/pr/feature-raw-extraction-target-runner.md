# Raw extraction target 기반 제한 실행 CLI

## 작업 내용

- raw extraction target 분석 결과를 기존 raw extractor와 연결하는 제한 실행
  CLI를 추가했습니다.
- 기본 동작은 dry-run이며, 실제 추출 대신 execution plan을 JSON과 markdown
  report로 출력합니다.
- 실제 실행 경로는 human approval 이후 `--execute`와 명시적인 `--limit`가
  함께 제공된 경우에만 사용할 수 있도록 분리했습니다.

## 주요 변경 사항

- `scripts/run_raw_extraction_targets.py`
  - 기존 raw extraction target selection 흐름을 재사용합니다.
  - `extraction_target_status=target`인 article만 실행 후보에 포함합니다.
  - `backup`, `skipped`, `already_extracted`, `failed` article은 실행 후보에서
    제외합니다.
  - `--execute` 사용 시 `--limit`를 필수로 요구하고 허용 범위를 `1~5`로
    제한합니다.
  - 후보의 article ID, title, source, topic ID, raw status, decision reason과
    extraction/write 수행 여부를 report에 기록합니다.
- `scripts/extract_raw_articles.py`
  - selected article ID만 처리하는 opt-in extraction helper를 추가했습니다.
  - 이미 추출된 article과 failed article은 selected-ID 실행 대상에서
    제외합니다.
  - 기존 `extract()` 진입점과 CronJob 기본 실행 의미는 변경하지 않았습니다.
- `tests/test_run_raw_extraction_targets.py`
  - dry-run 기본 동작, execute/limit guard, target-only 후보 필터링,
    mock executor 기반 execute 연결을 검증합니다.
- approved fix는 없습니다. 승인된 fix 문서에 기록된 대로 review 결과를 근거로
  추가 코드 수정은 수행하지 않았습니다.

## 추가/변경된 API

- 없음.
- FastAPI route와 기존 endpoint response schema는 변경하지 않았습니다.

## DB 변경 사항

- DB schema 및 migration 변경 없음.
- dry-run 검증에서는 `articles`, `sources`, `raw_articles` 상태를 read-only로
  조회했으며 DB write는 수행하지 않았습니다.
- execute-mode 구현은 기존 extractor의 `raw_articles` 저장과
  `extraction_runs` 기록 로직을 재사용하지만, 실제 execute-mode는 검증 중
  실행하지 않았습니다.

## README 영향

- README 변경 없음.
- 이번 변경은 human-controlled 내부 CLI와 workflow 문서 범위이며 기존 API와
  운영 기본 동작을 변경하지 않아 README 업데이트가 필요하지 않다고
  판단했습니다.

## 테스트

- Python compile: passed.
- Focused unittest: 21 tests passed.
- Full unittest: 75 tests passed.
- CLI help: passed.
- `--limit 6` validation: 허용 범위 초과로 실패하는 것을 확인했습니다.
- Read-only dry-run report 생성: passed.
  - 100개 article 분석
  - target/execution candidate 2건
  - `dry_run=true`
  - `execute_requested=false`
  - `raw_extraction_performed=false`
  - `db_write_performed=false`
- `git diff --check`: passed.
- K8s 및 보호 범위 변경 없음 확인.
- Security checks: 신규 credential 값 노출 없음 확인.
- `pytest`: pending. 설치되어 있지 않아 실행하지 않았습니다.

## 확인 결과

- 기본 실행은 dry-run이며 기존 raw extractor를 호출하지 않습니다.
- 실행 계획에는 `target` 상태 article만 포함됩니다.
- execute/limit guard와 execute integration은 parser unit test 및 mock
  executor로만 검증했습니다.
- 실제 raw extraction과 DB write는 수행하지 않았습니다.
- OpenAI, embedding, summary, LLM provider는 호출하지 않았습니다.
- API, DB schema, K8s manifest, CronJob, frontend, Docker workflow는
  변경하지 않았습니다.
- topic summary 생성은 포함하지 않았습니다.

## 비고

- `--execute`가 포함된 shell 명령은 실행하지 않았습니다.
- 실제 제한 실행은 human review와 명시적 승인 이후 pending입니다.
- production verification, deployment, K3s rollout, PR merge는 수행하지
  않았으며 pending입니다.
- 첫 dry-run 시도는 sandbox DNS 제한으로 DB 접근 전에 실패했으며, 이후
  read-only rerun에서 report 생성을 확인했습니다.
