# Raw extraction target 기반 제한 실행 CLI

## 작업 목적

NewsLab의 raw article extraction 흐름은 `articles.url`을 읽어 원문을 추출하고,
결과를 `raw_articles`와 `extraction_runs`에 기록한다. 기존 extractor는 일반
pending article을 처리하는 운영 경로이므로, topic 대표 후보 중 선정된 raw
extraction target만 소량 실행하려면 별도의 승인 경계가 필요했다.

이번 작업의 목적은 이전 단계에서 선정한 `extraction_target_status=target`
article을 기존 extractor와 연결하되, 기본 실행에서는 실제 원문 추출이나 DB
write가 발생하지 않는 dry-run-first 제한 실행 CLI를 만드는 것이다.

## 기존 문제

- raw extraction target 선정 결과는 분석 report로 검토할 수 있었지만, 실제
  extractor에 전달할 실행 계획과 명시적인 승인 경계가 없었다.
- 기존 `scripts/extract_raw_articles.py`는 일반 pending article을 직접 처리하므로
  선정된 target ID만 실행하는 opt-in 경로가 없었다.
- 분석 결과를 바로 실행에 연결하면 backup, skipped, already extracted, failed
  article이 의도치 않게 처리되거나 대량 실행될 위험이 있었다.
- 실제 실행 전에 대상 article과 실행 여부를 사람이 검토할 report가 필요했다.

## 변경 내용

- 기본 dry-run인 `scripts/run_raw_extraction_targets.py`를 추가했다.
- 기존 raw extraction target selection 결과를 재사용해 target-only execution
  plan을 생성하도록 구현했다.
- `--execute` 사용 시 명시적인 `--limit`를 요구하고 허용 범위를 `1~5`로
  제한했다.
- 기존 extractor에 selected article ID 전용 opt-in extraction helper를
  추가했다.
- execution plan과 결과를 JSON 및 markdown report로 출력하도록 구현했다.
- CLI validation, 후보 필터링, dry-run safety, mock execute 연결 테스트를
  추가했다.
- approved fix 문서에는 적용할 fix가 없으며, review 결과를 근거로 추가 코드
  수정은 수행하지 않았다.

## 구현 상세

### Dry-run runner

- runner는 기존 `analyze_raw_extraction_targets.py`의 분석 흐름을 재사용한다.
- `extraction_target_status=target`인 article만 execution candidate로 변환한다.
- `backup`, `skipped`, `already_extracted`, `failed` 상태는 실행 후보에서
  제외한다.
- 기본 실행에서는 read-only transaction으로 article과 raw extraction 상태를
  조회하고 execution plan만 생성한다.
- dry-run report에는 article ID, title, source, topic ID, raw status, decision
  reason을 포함한다.
- report에 `dry_run`, `execute_requested`, `raw_extraction_performed`,
  `db_write_performed`를 명시해 실행 여부를 확인할 수 있게 했다.

### Opt-in extractor integration

- 기존 extractor에 selected article ID 목록을 받는 opt-in 함수를 추가했다.
- selected-ID 조회는 미추출 article 또는 raw text가 비어 있는 pending article만
  허용한다.
- 이미 추출된 article과 failed article은 자동으로 제외한다.
- 실제 execute-mode가 호출될 경우 기존 extractor의 fetch/save 및
  `extraction_runs` 기록 방식을 재사용한다.
- 기존 `extract()` 진입점과 K3s raw extractor CronJob의 기본 실행 의미는
  변경하지 않았다.

### Safety boundary

- `--execute` 없이 extractor를 호출하지 않는다.
- `--execute` 사용 시 `--limit`가 없으면 실패하도록 구현했다.
- limit은 `1~5` 범위만 허용한다.
- execute integration은 실제 실행이 아닌 mock executor로만 검증했다.
- OpenAI/embedding/summary provider 옵션을 추가하거나 호출하지 않았다.

## 대안 검토

### 기존 extractor 기본 동작을 target 기반으로 변경

기존 CronJob의 대상 선정 의미가 바뀌고 운영 범위가 달라질 위험이 있어
선택하지 않았다.

### runner에서 extraction과 save 로직을 별도로 구현

HTML fetch, `raw_articles` 저장, `extraction_runs` 기록 로직이 중복되고 기존
extractor와 정책이 달라질 수 있어 선택하지 않았다.

### target 분석 결과를 DB에 저장한 뒤 실행

실행 상태 관리에는 유리하지만 신규 schema와 DB write가 필요해 이번 task
scope를 벗어나므로 선택하지 않았다.

### 구현 검증 중 실제 소량 extraction 실행

실제 동작 확인에는 도움이 되지만 human approval 없는 DB write와 원문 추출이
발생하므로 선택하지 않았다. execute 경로는 mock/unit test로만 검증했다.

## 선택한 접근과 근거

- 분석 정책은 기존 helper를 재사용하고 실행 경계만 별도 runner에 배치했다.
  이를 통해 target 선정 정책과 raw extraction 저장 책임을 분리했다.
- 실제 write 경로는 기존 extractor helper를 재사용하는 opt-in 함수로
  제한했다. 기존 CronJob 기본 동작을 유지하면서 선택된 ID만 처리할 수 있다.
- dry-run을 기본값으로 두고 explicit execute와 작은 limit을 함께 요구했다.
  운영 write를 human review 이후로 미루면서 실행 대상을 사전에 확인할 수 있다.
- execution plan을 JSON과 markdown으로 모두 출력해 자동 처리와 사람 검토를
  함께 지원했다.

## 트레이드오프

- selected-ID 실행 경로도 실제 실행 시 기존 extractor처럼 article별
  transaction과 extraction run 기록을 사용하므로 완전한 단일 transaction은
  아니다.
- 실제 웹사이트 응답, 원문 추출 품질, DB write 결과는 human-approved 실행
  전까지 검증되지 않는다.
- 분석 시점과 실제 실행 시점 사이에 article 상태가 변경될 수 있다. 다만 실제
  selected-ID 조회에서 현재 raw 상태를 다시 확인해 기존/failed article을
  제외한다.
- 실행 report 생성 후 실제 execute 단계에서 예외가 발생할 경우 운영자가
  report와 extraction run 상태를 함께 확인해야 한다.

## 테스트

`docs/verification/feature-raw-extraction-target-runner.md`에 기록된 실제 결과는
다음과 같다.

- Python compile: passed.
- Focused unittest: 21 tests passed.
- Full unittest: 75 tests passed.
- CLI help: passed.
- `--limit 6` validation: 허용 범위 초과 오류 확인.
- Read-only dry-run report 생성: passed.
  - 100개 article 분석
  - target candidate 2건
  - execution candidate 2건
  - `dry_run=true`
  - `execute_requested=false`
  - `raw_extraction_performed=false`
  - `db_write_performed=false`
- `git diff --check`: passed.
- K8s 및 보호 범위 변경 없음 확인.
- Security checks: 신규 credential 값 노출 없음 확인.
- `pytest`: pending. 설치되어 있지 않아 실행하지 않았다.

첫 sandboxed dry-run 시도는 외부 DNS 제한으로 DB 접근 전에 실패했다. 이후
read-only rerun에서 report 생성을 확인했다.

## 운영 반영

- 실제 raw extraction은 수행하지 않았다.
- `raw_articles` 또는 `extraction_runs` DB write는 수행하지 않았다.
- `--execute`가 포함된 shell 명령은 실행하지 않았다.
- OpenAI, embedding, summary, 기타 LLM provider는 호출하지 않았다.
- production curl verification, deployment, K3s rollout, migration, manual SQL,
  git push, git merge는 수행하지 않았다.
- 실제 execute-mode 검증과 운영 반영은 human review 및 명시적 승인 이후
  pending이다.
- PR merge와 production verification도 pending이다.

## README 업데이트 판단

README 변경은 필요하지 않다고 판단했다.

이번 변경은 human-controlled 내부 runner와 workflow 문서에 한정된다. 기존
FastAPI API, DB schema, K3s manifest, CronJob command, frontend, 운영 기본
동작은 변경하지 않았다. 실제 execute-mode 운영 절차가 승인되고 반복 운영
경로로 확정되면 README 또는 RUNBOOK 반영을 별도 검토할 수 있다.

## 확인 결과

- 기본 실행이 dry-run이며 기존 raw extractor를 호출하지 않는 것을 확인했다.
- execution plan에 target 상태 article만 포함되는 것을 unit test와 dry-run
  report로 확인했다.
- execute/limit guard와 selected-ID extractor 연결은 parser unit test와 mock
  executor로 확인했다.
- report에 실행 대상 정보와 extraction/write 미수행 상태가 포함된다.
- 기존 extractor의 기본 `extract()` 진입점과 CronJob 실행 의미는 유지된다.
- API, DB schema, K8s, CronJob, frontend, Docker workflow는 변경하지 않았다.
- topic summary 생성은 포함하지 않았다.

## 이번 단계의 의미

raw extraction target 선정 결과를 실제 원문 확보 단계와 연결하면서도, 실행
권한과 DB write를 human approval 뒤로 유지하는 운영 경계를 마련했다.

이 단계는 topic summary MVP로 넘어가기 전에 필요한 원문을 소량 확보할 수
있는 준비 작업이다. 분석 결과를 곧바로 대량 실행으로 연결하지 않고, dry-run
report와 작은 limit을 통해 검토 가능한 실행 흐름을 만든 점이 핵심이다.

## 포트폴리오용 요약

뉴스 topic 대표 후보 중 raw extraction target만 제한적으로 실행할 수 있는
dry-run-first CLI를 설계했다. 기존 target selection과 raw extractor를
재사용하면서 target-only 필터, explicit execute/limit guard, selected-ID
opt-in 경로, JSON/markdown execution report를 추가했다. 실제 write 경로는
mock으로 검증하고 운영 실행은 사람 승인 뒤로 분리해 기존 CronJob 동작과
데이터 안전성을 유지했다.

## 다음 단계 후보

- human review 후 `--limit 1~5` 범위의 실제 execute-mode 실행 여부 결정
- human-provided 실행 로그 기반 success/failed/skipped 결과 확인
- 실제 원문 추출 품질과 execution report 보완점 검토
- 반복 운영이 확정되면 RUNBOOK 또는 README에 승인된 실행 절차 문서화
- 확보된 원문을 사용하는 topic summary MVP 검토
