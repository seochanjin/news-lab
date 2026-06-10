# Task: Topic 대표 후보 기반 raw extraction 대상 선정

## Goal

32차에서 구현한 topic별 representative candidate 결과를 기반으로, 후속 raw extraction 단계에서 어떤 article 원문을 먼저 추출할지 read-only로 선정한다.

이번 작업은 실제 raw extraction을 실행하지 않는다.  
DB write 없이 extraction target 후보를 계산하고, 사람이 검토할 수 있는 markdown report와 CLI JSON output을 생성하는 것이 목적이다.

33차의 핵심은 다음을 명확히 분리하는 것이다.

- `candidate_score`: 같은 topic 내부에서 대표 후보를 정렬하기 위한 점수
- raw extraction target policy: 대표 후보 중 실제 원문 추출 대상으로 삼을 article을 고르는 정책

이번 작업은 topic summary 생성을 위한 사전 단계다.  
최종 목표는 topic별 대표 후보 원문을 확보한 뒤, 후속 차수에서 사람이 볼 수 있는 topic title과 topic summary를 생성하는 것이다.

## Scope

### In scope

- 기존 topic grouping 흐름 재사용
- 기존 representative candidate selection 흐름 재사용
- raw extraction 상태 조회
- topic별 raw extraction target 후보 선정
- topic당 최대 target 수 정책 적용
- 기본 `--max-targets-per-topic 1` 지원
- 옵션으로 `--max-targets-per-topic 2` 비교 report 생성
- selected target / backup candidate / skipped candidate / already_extracted / failed 상태 구분
- extraction target 선정 사유와 제외 사유를 report에 표시
- markdown report 생성
- CLI JSON output 생성
- unit test 추가
- verification/devlog/PR 문서 작성

### Target policy

기본 정책은 다음과 같다.

- 기본 대상은 `article_count > 1`인 multi-article topic이다.
- 각 topic에서 representative candidate rank 1을 기본 extraction target으로 선정한다.
- `--max-targets-per-topic` 옵션으로 topic당 target 수를 조정할 수 있다.
- `--max-targets-per-topic` 기본값은 `1`이다.
- 허용값은 `1~3`이다.
- 이미 raw text가 있는 article은 기본 extraction target에서 제외하고 `already_extracted`로 표시한다.
- raw extraction failed 상태인 article은 자동 재시도하지 않고 `failed`로 표시한다.
- pending 또는 not_extracted 상태인 article만 기본 extraction target으로 선정한다.
- rank 기준으로 target limit을 넘긴 후보는 `backup` 또는 `skipped`로 표시한다.

### Topic ordering policy

topic 간 정렬은 초기 MVP에서 다음 기준을 사용한다.

- multi-article topic 우선
- `source_count` 높은 topic 우선
- `article_count` 높은 topic 우선
- 최신 topic 우선

단, 이번 차수에서 topic 간 중요도 정책을 최종 확정하지 않는다.  
topic 간 extraction priority 정책은 report 검토 후 후속 차수에서 조정할 수 있다.

### Provider policy

- 기본 검증은 deterministic embedding provider를 사용한다.
- 실제 OpenAI embedding provider는 자동 호출하지 않는다.
- `--use-embedding-provider`를 지원하더라도 human operator의 명시적 승인 후에만 실행한다.
- OpenAI provider 실행은 실제 API 호출과 비용이 발생할 수 있다.
- 이번 작업의 필수 검증에는 OpenAI provider 실행을 포함하지 않는다.

## Do not change

이번 작업에서 다음 항목은 변경하지 않는다.

- 실제 raw extraction 실행 금지
- `raw_articles` insert/update 금지
- `extraction_runs` insert/update 금지
- topic summary 생성 금지
- OpenAI 요약 호출 금지
- DB schema migration 금지
- API route 추가 금지
- frontend 변경 금지
- Kubernetes manifest 변경 금지
- CronJob 변경 금지
- production rollout 금지
- production curl verification 금지
- OpenAI embedding provider 자동 호출 금지
- representative candidate score weight 변경 금지
- topic grouping similarity algorithm 변경 금지
- embedding model 변경 금지
- secrets, `.env`, kubeconfig, credentials, SSH keys, tokens 변경 금지

## Expected files

예상 변경/추가 파일은 다음과 같다.

- `app/utils/raw_extraction_targets.py`
  - raw extraction target 선정 helper
  - target/backup/skipped/already_extracted/failed 상태 계산
  - report rendering helper

- `scripts/analyze_raw_extraction_targets.py`
  - read-only CLI
  - 기존 article 조회, embedding, topic grouping, representative candidate 흐름 재사용
  - raw extraction 상태 조회
  - markdown report 및 JSON output 생성

- `tests/test_raw_extraction_targets.py`
  - target 선정 정책 unit test
  - `max_targets_per_topic` 동작 검증
  - already extracted / failed / skipped / backup 상태 검증
  - candidate score가 topic 간 우선순위로 사용되지 않음을 검증

- `tests/test_analyze_raw_extraction_targets.py`
  - CLI option parsing 검증
  - `--max-targets-per-topic` validation 검증
  - provider safety gate 유지 검증

- `docs/reports/feature-raw-extraction-targets.md`
  - 기본 `max_targets_per_topic=1` report

- `docs/reports/feature-raw-extraction-targets-max2.md`
  - 비교용 `max_targets_per_topic=2` report

- `docs/verification/feature-raw-extraction-targets.md`
  - 실제 실행한 검증 명령과 결과만 기록

- `docs/devlog/feature-raw-extraction-targets.md`
  - 작업 배경, 선택한 접근, 대안, 트레이드오프 기록

- `docs/pr/feature-raw-extraction-targets.md`
  - PR 설명 초안

필요한 경우에만 다음 파일을 최소 변경한다.

- `app/utils/topic_grouping.py`
- `app/utils/topic_representatives.py`
- `scripts/analyze_topic_representatives.py`

단, 기존 grouping/scoring 정책 변경은 하지 않는다.

## DB changes

DB schema 변경 없음.

이번 작업은 read-only 분석 작업이다.

허용되는 DB 동작:

- `articles` 조회
- `sources` 조회
- 기존 raw extraction 상태 조회
  - 예: `raw_articles`, `article_texts` 등 현재 프로젝트에서 사용 중인 raw text 저장 테이블 조회
- read-only transaction 설정

금지되는 DB 동작:

- insert
- update
- delete
- migration
- raw extraction 실행 결과 저장
- extraction run 기록 저장
- topic 저장
- topic article 저장
- representative candidate 저장
- summary 저장

CLI는 DB write가 수행되지 않았음을 report와 JSON output에 명시해야 한다.

## API changes

API 변경 없음.

- 신규 FastAPI router 추가 없음
- 기존 endpoint 응답 구조 변경 없음
- `/articles`, `/raw-articles`, `/collector/*`, `/extractor/*` 변경 없음
- frontend 변경 없음

이번 작업 결과는 CLI JSON output과 markdown report로만 확인한다.

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
  app/utils/topic_grouping.py \
  app/utils/topic_representatives.py \
  app/utils/raw_extraction_targets.py \
  scripts/analyze_raw_extraction_targets.py
```

Focused unittest:

```bash
.venv/bin/python -m unittest \
  tests.test_topic_grouping \
  tests.test_topic_representatives \
  tests.test_raw_extraction_targets \
  tests.test_analyze_raw_extraction_targets \
  -v
```

Full unittest:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

CLI help:

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py --help
```

기본 raw extraction target report 생성:

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --report-path docs/reports/feature-raw-extraction-targets.md \
  --dry-run
```

topic당 최대 2개 target 비교 report 생성:

```bash
.venv/bin/python scripts/analyze_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 2 \
  --report-path docs/reports/feature-raw-extraction-targets-max2.md \
  --dry-run
```

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db tests docs
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

신규/수정 파일 대상 보안 검사:

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs
```

pytest가 설치되어 있다면 실행한다.

```bash
pytest
```

설치되어 있지 않다면 설치하지 않고 verification에 `pending`으로 기록한다.

## Acceptance criteria

- `scripts/analyze_raw_extraction_targets.py --help`가 정상 동작한다.
- CLI가 raw extraction target markdown report를 생성한다.
- CLI가 JSON summary output을 생성한다.
- 기본 report는 multi-article topic 중심으로 출력한다.
- `--max-targets-per-topic 1`은 topic당 최대 1개 pending extraction target만 선정한다.
- `--max-targets-per-topic 2`는 topic당 최대 2개 pending extraction target만 선정한다.
- `--max-targets-per-topic` 허용 범위는 `1~3`이다.
- 이미 raw text가 있는 article은 기본 extraction target으로 선정하지 않고 `already_extracted`로 표시한다.
- failed 상태 article은 자동 재시도하지 않고 `failed`로 표시한다.
- limit을 초과한 representative candidate는 `backup` 또는 `skipped`로 표시한다.
- report는 target reason과 skip reason을 표시한다.
- report는 candidate rank와 candidate score를 표시하되, candidate score가 topic 내부 정렬용임을 명시한다.
- report는 extraction target 정책과 candidate score를 분리해 설명한다.
- report는 DB write performed가 `false`임을 표시한다.
- 실제 raw extraction이 실행되지 않는다.
- DB write가 수행되지 않는다.
- OpenAI provider가 자동 호출되지 않는다.
- API, DB schema, K8s, CronJob, frontend 변경이 없다.
- unit test와 compile이 통과한다.
- verification 문서에는 실제 실행한 명령과 결과만 기록한다.

## Notes

이번 작업은 topic summary 생성의 직전 준비 단계다.

현재까지의 흐름은 다음과 같다.

- 30차: embedding 기반 topic grouping
- 31차: topic grouping 결과 report 안정화
- 32차: topic 내부 representative candidate 선정
- 33차: representative candidate 중 raw extraction 대상 선정
- 이후: 실제 raw extraction 실행, topic summary 생성, topic 저장/API 연결

33차에서 만든 target report는 후속 차수에서 실제 raw extraction 실행 대상을 검토하는 기준으로 사용한다.

초기 MVP에서는 topic당 1개 target을 기본으로 하되, topic summary 품질이 부족할 가능성을 고려해 topic당 2개 target report도 비교 산출한다.

다만 이번 차수에서는 어느 정책이 최종 정답인지 확정하지 않는다.  
사람이 report를 보고 topic당 1개가 충분한지, 2개 이상이 필요한지 판단한다.

중요한 제한:

- `candidate_score`는 같은 topic 내부 대표 후보 순위다.
- `candidate_score`를 topic 간 중요도나 전체 extraction priority score로 직접 사용하지 않는다.
- 실제 extraction 실행과 summary 생성은 후속 차수에서 human approval 후 진행한다.
