# Task: Raw extraction target 기반 제한 실행 CLI

## Goal

33차에서 구현한 raw extraction target selection 결과를 기반으로, 선정된 target article을 실제 raw extractor 실행 대상으로 연결하는 제한 실행 CLI를 구현한다.

이번 작업의 핵심은 실제 원문 추출을 무조건 자동화하는 것이 아니다.  
기본 실행은 dry-run으로 유지하고, human operator가 명시적으로 승인한 경우에만 제한된 개수의 target article에 대해 실제 raw extraction을 수행할 수 있게 한다.

34차는 35차 topic summary MVP로 넘어가기 위한 원문 확보 준비 단계다.

이번 작업에서 달성할 목표는 다음과 같다.

- 33차 target selection 결과를 재사용한다.
- `extraction_target_status=target`인 article만 실행 후보로 사용한다.
- 기본 실행에서는 실제 raw extraction을 수행하지 않고 execution plan만 생성한다.
- 실제 실행은 `--execute`와 `--limit`가 명시된 경우에만 가능하게 한다.
- 이미 추출된 article, failed article, backup/skipped article은 실행 대상에서 제외한다.
- 실행 계획과 결과를 JSON 및 markdown report로 검토할 수 있게 한다.

## Scope

### In scope

- 33차 raw extraction target selection 흐름 재사용
- 기존 topic grouping / representative candidate / raw extraction target helper 재사용
- target status가 `target`인 article만 실행 후보로 사용
- 기본 dry-run execution plan 생성
- `--execute` 옵션이 있을 때만 실제 raw extraction 실행 가능
- `--execute` 실행 시 `--limit` 필수
- `--limit`는 작은 값으로 제한
- already_extracted article skip
- failed article 자동 retry 금지
- backup/skipped article 실행 금지
- 실행 대상 article id, title, source, topic id, raw status, decision reason 출력
- 실제 실행 결과 JSON/markdown report 생성
- CLI option validation test 추가
- execution candidate filtering test 추가
- dry-run safety test 추가
- verification/devlog/PR 문서 작성

### Execution policy

기본 실행은 항상 dry-run이다.

- `--execute`가 없으면 실제 raw extraction을 수행하지 않는다.
- dry-run에서는 실행 계획만 출력한다.
- dry-run report에는 `raw_extraction_performed=false`, `db_write_performed=false`를 명시한다.
- dry-run에서는 기존 raw extractor를 호출하지 않는다.

실제 실행 조건은 다음과 같다.

- `--execute`가 명시되어야 한다.
- `--limit`가 명시되어야 한다.
- `--limit`는 `1~5` 범위만 허용한다.
- 실행 대상은 `extraction_target_status=target`인 article만 허용한다.
- `already_extracted`, `failed`, `backup`, `skipped` article은 실행하지 않는다.
- 실행 전 실행 대상 목록을 JSON/markdown에 남긴다.
- 실제 실행 결과는 성공/실패/skip 상태를 report에 남긴다.

Codex는 이번 작업의 검증 과정에서 `--execute`를 실행하지 않는다.  
실제 `--execute` 실행은 human operator가 별도 승인한 뒤 수동으로 수행한다.

### Raw extraction integration policy

기존 raw extractor 구현을 우선 재사용한다.

구현 전 다음을 먼저 확인한다.

- 기존 `scripts/extract_raw_articles.py` 구조
- 특정 article id만 추출할 수 있는지
- limit 제어가 가능한지
- 이미 추출된 article skip 정책
- failed 상태 처리 정책
- extraction_runs 기록 방식
- raw_articles insert/update 방식

필요한 경우 기존 extractor에 최소한의 옵션을 추가한다.

허용 가능한 옵션 예시:

- `--article-ids`
- `--limit`
- `--dry-run`
- `--skip-failed`
- `--skip-existing`

단, 기존 CronJob 기본 동작이 바뀌면 안 된다.

### Out of scope

- topic summary 생성
- LLM 요약 호출
- topics/topic_articles DB schema 추가
- DB migration
- `/topics` API 추가
- frontend 변경
- Kubernetes manifest 변경
- CronJob 변경
- Docker image build/push
- K3s rollout
- production deployment
- production curl verification
- 대량 raw extraction
- failed article 자동 retry
- raw extraction 결과를 topic summary에 연결
- summary 저장
- provider 기반 topic summary 생성

## Do not change

이번 작업에서 다음 항목은 변경하지 않는다.

- DB schema
- migration 파일
- FastAPI router
- API response schema
- frontend
- Kubernetes manifest
- CronJob manifest
- Docker build/push workflow
- deployment/rollout script
- topic grouping similarity algorithm
- representative candidate score weight
- raw extraction target 선정 정책의 기본 의미
- OpenAI embedding provider 기본 동작
- topic summary 관련 코드
- `.env`
- kubeconfig
- credentials
- SSH key
- token
- secret

기존 `scripts/extract_raw_articles.py`는 필요한 경우에만 최소 변경한다.  
변경하더라도 기존 CronJob이 기존 방식으로 실행될 때의 기본 동작을 깨면 안 된다.

Codex는 다음 명령을 실행하지 않는다.

- `kubectl apply`
- `kubectl delete`
- `kubectl rollout`
- `helm upgrade`
- `docker build`
- `docker push`
- `git push`
- `git merge`
- Supabase SQL 실행
- production curl verification
- `--execute`를 포함한 실제 raw extraction 실행 명령

## Expected files

예상 추가/변경 파일은 다음과 같다.

### New files

- `scripts/run_raw_extraction_targets.py`
  - 33차 target selection 결과 기반 제한 실행 CLI
  - 기본 dry-run
  - `--execute`와 `--limit` guard
  - 실행 계획/결과 JSON 출력
  - markdown report 생성

- `tests/test_run_raw_extraction_targets.py`
  - CLI option validation
  - dry-run 기본 동작
  - `--execute` 시 `--limit` 필수 검증
  - limit 범위 검증
  - target only 실행 후보 검증
  - backup/skipped/already_extracted/failed 제외 검증

- `docs/reports/feature-raw-extraction-target-runner-dry-run.md`
  - dry-run execution plan report

- `docs/verification/feature-raw-extraction-target-runner.md`
  - 실제 실행한 검증 명령과 결과 기록

- `docs/devlog/feature-raw-extraction-target-runner.md`
  - 작업 배경, 선택한 접근, 대안, 트레이드오프 기록

- `docs/pr/feature-raw-extraction-target-runner.md`
  - PR 설명 초안

### Possible minimal changes

필요한 경우에만 최소 변경한다.

- `scripts/extract_raw_articles.py`
  - 특정 article id / limit / dry-run / skip-existing / skip-failed를 지원하기 위한 최소 옵션 추가
  - 기존 CronJob 기본 동작 유지 필수

- `app/utils/raw_extraction_targets.py`
  - 실행 대상 목록 추출 helper가 필요할 경우 최소 변경

- `scripts/analyze_raw_extraction_targets.py`
  - 기존 target selection 결과 재사용을 위한 helper 분리가 필요할 경우 최소 변경

수정하지 않는 것이 원칙인 파일:

- `k8s/*`
- `db/*`
- `app/routers/*`
- frontend 관련 파일
- deployment 관련 파일

## DB changes

DB schema 변경 없음.

### Dry-run

dry-run에서는 DB write가 없어야 한다.

허용되는 DB 동작:

- `articles` 조회
- `sources` 조회
- `raw_articles` 상태 조회
- read-only transaction 기반 execution plan 생성

금지되는 DB 동작:

- insert
- update
- delete
- migration
- extraction run 기록
- raw_articles 저장
- topic summary 저장

### Execute mode

`--execute` 실행 시에는 기존 raw extraction 저장 로직이 수행하는 DB write만 허용한다.

허용 가능한 write:

- 기존 raw extractor가 수행하는 `raw_articles` insert/update
- 기존 raw extractor가 수행하는 extraction run 기록

금지되는 write:

- DB migration
- topics/topic_articles 저장
- topic summary 저장
- representative candidates 저장
- 신규 테이블 write
- 임의의 수동 SQL 실행

단, Codex는 human operator 승인 없이 `--execute`를 실행하지 않는다.  
이번 구현 verification에서는 실제 DB write가 발생하면 안 된다.

## API changes

API 변경 없음.

- 신규 FastAPI route 없음
- 기존 endpoint 응답 구조 변경 없음
- `/articles` 변경 없음
- `/raw-articles` 변경 없음
- `/collector/*` 변경 없음
- `/extractor/*` 변경 없음
- frontend 변경 없음

이번 작업 결과는 CLI JSON output과 markdown report로 확인한다.

## Test commands

정적 확인:

```bash
git status --short --branch
git diff --stat
git diff --check
```

Python compile:

```bash
.venv/bin/python -m py_compile \
  app/utils/raw_extraction_targets.py \
  scripts/analyze_raw_extraction_targets.py \
  scripts/run_raw_extraction_targets.py
```

Focused unittest:

```bash
.venv/bin/python -m unittest \
  tests.test_raw_extraction_targets \
  tests.test_analyze_raw_extraction_targets \
  tests.test_run_raw_extraction_targets \
  -v
```

Full unittest:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

CLI help:

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py --help
```

Dry-run execution plan report:

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 2 \
  --report-path docs/reports/feature-raw-extraction-target-runner-dry-run.md
```

Execute guard 검증:

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --execute
```

기대 결과:

- `--execute`에 `--limit`가 없으므로 실패해야 한다.
- 실제 raw extraction이 실행되면 안 된다.

Limit validation 검증:

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 6
```

기대 결과:

- `--limit`는 `1~5` 범위만 허용해야 하므로 실패해야 한다.

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db tests docs
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

pytest가 설치되어 있다면 실행한다.

```bash
pytest
```

설치되어 있지 않다면 설치하지 않고 verification에 `pending`으로 기록한다.

## Acceptance criteria

- `scripts/run_raw_extraction_targets.py --help`가 정상 동작한다.
- 기본 실행은 dry-run이다.
- dry-run에서는 실제 raw extraction이 실행되지 않는다.
- dry-run에서는 DB write가 발생하지 않는다.
- `--execute` 없이 실행하면 execution plan만 생성한다.
- `--execute` 실행 시 `--limit`가 없으면 실패한다.
- `--limit`는 `1~5` 범위만 허용한다.
- 실행 후보는 `extraction_target_status=target` article만 포함한다.
- `backup`, `skipped`, `already_extracted`, `failed` article은 실행 후보에서 제외한다.
- 실행 계획 report에는 article id, title, source, topic id, raw status, decision reason이 포함된다.
- report에는 dry-run 여부와 실제 extraction 수행 여부가 표시된다.
- dry-run report에는 `raw_extraction_performed=false`, `db_write_performed=false`가 표시된다.
- Codex verification 과정에서 실제 raw extraction을 실행하지 않는다.
- Codex verification 과정에서 DB write를 수행하지 않는다.
- 기존 raw extractor의 CronJob 기본 동작을 깨지 않는다.
- API, DB schema, K8s, CronJob, frontend 변경이 없다.
- OpenAI provider를 자동 호출하지 않는다.
- topic summary를 생성하지 않는다.
- verification 문서에는 실제 실행한 명령과 결과만 기록한다.
- PR 문서에는 실제 extraction, deployment, rollout이 수행되지 않았음을 명시한다.

## Notes

34차는 35차 topic summary MVP로 넘어가기 위한 원문 확보 준비 단계다.

하지만 이번 작업에서 topic summary는 생성하지 않는다.  
이번 작업은 raw extraction target을 기존 extractor와 안전하게 연결하는 실행 경계만 만든다.

기본 실행은 dry-run으로 유지한다.  
실제 `--execute` 실행은 human operator가 별도 승인한 뒤 소량으로 수행한다.

초기 실제 실행 후보는 다음 정도로 제한하는 것이 좋다.

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 2 \
  --execute \
  --report-path docs/reports/feature-raw-extraction-target-runner-execute.md
```

단, 위 명령은 이번 구현 verification에서 실행하지 않는다.  
실제 실행 여부는 PR review와 human approval 이후 별도로 결정한다.
