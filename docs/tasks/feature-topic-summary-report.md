# Task: Raw text 기반 topic summary report MVP

## Goal

34차까지 구현한 raw extraction target 실행 흐름 이후, `raw_articles.raw_text`가 확보된 topic 후보를 대상으로 사람이 읽을 수 있는 한국어 topic summary report를 생성한다.

이번 작업의 목적은 topic summary를 DB에 저장하거나 API로 제공하는 것이 아니다.  
35차는 topic summary 생성 가능성을 검증하는 report MVP 단계다.

기본 실행은 deterministic/mock summary로 동작하며, 실제 LLM provider 호출은 `--use-summary-provider` 옵션이 명시된 경우에만 허용한다.

실제 provider 테스트는 다음 정책을 따른다.

- 1차 실제 테스트 모델: `gpt-5-nano`
- 품질 비교 필요 시 후보 모델: `gpt-5-mini`
- provider model은 `OPENAI_SUMMARY_MODEL` 환경변수에서 읽는다.
- `OPENAI_SUMMARY_MODEL`이 없으면 기본값은 `gpt-5-nano`다.
- provider 호출에는 `OPENAI_SUMMARY_API_KEY`가 필요하다.

## Scope

### In scope

- 기존 topic grouping / representative candidate / raw extraction target 흐름 재사용
- `raw_articles.raw_text`가 있는 article만 summary input으로 사용
- raw text가 없는 topic은 summary 대상에서 제외하거나 `insufficient_raw_text`로 report에 표시
- topic별 summary input 구성
- deterministic/mock summary provider 구현
- OpenAI summary provider opt-in 구현
- `OPENAI_SUMMARY_API_KEY` / `OPENAI_SUMMARY_MODEL` 환경변수 지원
- provider 호출 시 `--use-summary-provider` 명시 요구
- provider 호출 시 작은 실행 범위 제한
  - `--max-topics`
  - `--max-articles-per-topic`
  - `--max-raw-chars-per-article`
- topic summary JSON output 생성
- topic summary markdown report 생성
- report에 사용 article/source/raw_text_length 표시
- report에 provider mode, model, DB write 여부, raw extraction 여부 표시
- unit test 추가
- verification/devlog/PR 문서 작성

### Summary output fields

topic summary output은 최소 다음 필드를 포함한다.

- `topic_candidate_id`
- `title_ko`
- `summary_ko`
- `key_points`
- `keywords`
- `confidence`
- `source_count`
- `article_count`
- `used_articles`
- `provider`
- `model`

### Provider policy

기본 실행은 deterministic/mock summary다.

- 기본 실행에서는 API key가 필요 없다.
- 기본 실행에서는 OpenAI provider를 호출하지 않는다.
- `--use-summary-provider`가 있을 때만 실제 provider를 호출한다.
- provider 호출 시 `OPENAI_SUMMARY_API_KEY`가 없으면 실패해야 한다.
- provider model은 `OPENAI_SUMMARY_MODEL`에서 읽는다.
- model 기본값은 `gpt-5-nano`다.
- `gpt-5-mini`는 품질 비교용으로 사용 가능해야 한다.
- provider 호출은 작은 범위에서만 허용한다.
- provider 호출 결과는 DB에 저장하지 않고 report로만 남긴다.

### Out of scope

- raw extraction 실행
- `--execute` 기반 raw extraction 호출
- DB write
- topic summary DB 저장
- topics/topic_articles schema 추가
- DB migration
- `/topics` API 추가
- frontend 변경
- Kubernetes manifest 변경
- CronJob 변경
- Docker image build/push
- K3s rollout
- production deployment
- production curl verification
- Batch API 연동
- Prompt caching 최적화
- 자동 운영 스케줄링

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
- raw extractor 실행 정책
- raw extraction target 선정 정책의 기본 의미
- `.env`
- kubeconfig
- credentials
- SSH key
- token
- secret

Codex는 다음 명령을 실행하지 않는다.

- raw extraction `--execute`
- kubectl apply/delete/rollout
- helm upgrade
- docker build/push
- git push
- git merge
- Supabase SQL 실행
- production curl verification
- DB migration
- manual SQL

## Expected files

예상 추가/변경 파일은 다음과 같다.

### New files

- `scripts/generate_topic_summary_report.py`
  - raw text 기반 topic summary report CLI
  - 기본 deterministic/mock summary
  - opt-in OpenAI summary provider
  - JSON output 및 markdown report 생성

- `app/utils/topic_summary.py`
  - summary input 구성
  - deterministic/mock summary 생성
  - provider response parsing
  - markdown report rendering helper

- `tests/test_topic_summary.py`
  - summary input 구성 검증
  - raw_text 없는 article/topic 처리 검증
  - deterministic/mock summary 검증
  - provider response parsing 검증

- `tests/test_generate_topic_summary_report.py`
  - CLI option validation
  - provider guard 검증
  - default mode에서 provider 미호출 검증
  - report generation 검증

- `docs/reports/feature-topic-summary-report-deterministic.md`
  - deterministic/mock summary report

- `docs/reports/feature-topic-summary-report-provider-nano.md`
  - human-approved `gpt-5-nano` 실행 결과 report
  - Codex가 자동 실행하지 않는다.

- `docs/reports/feature-topic-summary-report-provider-mini.md`
  - 품질 비교용 `gpt-5-mini` 실행 결과 report
  - 필요 시 human approval 후 생성한다.

- `docs/verification/feature-topic-summary-report.md`
- `docs/devlog/feature-topic-summary-report.md`
- `docs/pr/feature-topic-summary-report.md`
- `docs/reviews/feature-topic-summary-report-antigravity.md`
- `docs/reviews/feature-topic-summary-report-coderabbit.md`
- `docs/fixes/feature-topic-summary-report-approved-fixes.md`

### Possible minimal changes

필요한 경우에만 최소 변경한다.

- `scripts/analyze_raw_extraction_targets.py`
  - summary input 재사용을 위한 helper 분리가 필요할 경우
- `app/utils/raw_extraction_targets.py`
  - topic/article 구조 재사용 helper가 필요할 경우

## DB changes

DB schema 변경 없음.

기본 deterministic/mock 실행에서는 DB write가 없어야 한다.

허용되는 DB 동작:

- `articles` 조회
- `sources` 조회
- `raw_articles` 조회
- topic grouping을 위한 read-only 조회

금지되는 DB 동작:

- insert
- update
- delete
- migration
- topic summary 저장
- topics/topic_articles 저장
- raw extraction 실행
- extraction_runs 기록

provider 실행 시에도 DB write는 수행하지 않는다.  
provider 결과는 JSON/markdown report로만 남긴다.

## API changes

API 변경 없음.

- 신규 FastAPI route 없음
- 기존 endpoint 응답 구조 변경 없음
- `/articles` 변경 없음
- `/raw-articles` 변경 없음
- `/collector/*` 변경 없음
- `/extractor/*` 변경 없음
- `/topics` API 추가 없음
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
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py
```

Focused unittest:

```bash
.venv/bin/python -m unittest \
  tests.test_topic_summary \
  tests.test_generate_topic_summary_report \
  -v
```

Full unittest:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

CLI help:

```bash
.venv/bin/python scripts/generate_topic_summary_report.py --help
```

Deterministic/mock report:

```bash
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

Provider guard 검증:

```bash
OPENAI_SUMMARY_API_KEY= \
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 1 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 1000 \
  --use-summary-provider
```

기대 결과:

- `--use-summary-provider`가 있으나 `OPENAI_SUMMARY_API_KEY`가 없으므로 실패해야 한다.
- 실제 provider 호출이 발생하면 안 된다.

Human-approved nano provider test:

```bash
OPENAI_SUMMARY_MODEL=gpt-5-nano \
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 2 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --use-summary-provider \
  --report-path docs/reports/feature-topic-summary-report-provider-nano.md
```

Human-approved mini comparison test:

```bash
OPENAI_SUMMARY_MODEL=gpt-5-mini \
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 2 \
  --max-articles-per-topic 1 \
  --max-raw-chars-per-article 3000 \
  --use-summary-provider \
  --report-path docs/reports/feature-topic-summary-report-provider-mini.md
```

주의:

- provider test는 Codex가 자동 실행하지 않는다.
- provider test는 human approval 이후 수동 실행한다.
- provider test 결과는 실제 실행 로그가 있을 때만 verification에 기록한다.

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db tests docs
git status --short -- app/routers app/main.py db k8s frontend Dockerfile .github
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

- CLI help가 정상 동작한다.
- 기본 실행은 deterministic/mock summary다.
- 기본 실행에서는 OpenAI/LLM provider를 호출하지 않는다.
- 기본 실행에서는 API key가 필요하지 않다.
- 기본 실행에서는 DB write가 발생하지 않는다.
- 기본 실행에서는 raw extraction이 실행되지 않는다.
- `raw_articles.raw_text`가 있는 article만 summary input으로 사용한다.
- raw_text가 없는 topic은 제외하거나 `insufficient_raw_text`로 report에 표시한다.
- summary output은 `title_ko`, `summary_ko`, `key_points`, `keywords`, `confidence`를 포함한다.
- report에는 사용한 article/source/raw_text_length가 표시된다.
- report에는 provider mode와 model이 표시된다.
- report에는 `db_write_performed=false`가 표시된다.
- report에는 `raw_extraction_performed=false`가 표시된다.
- provider 호출은 `--use-summary-provider`가 있을 때만 가능하다.
- provider 호출 시 `OPENAI_SUMMARY_API_KEY`가 필요하다.
- provider model은 `OPENAI_SUMMARY_MODEL`을 따른다.
- provider model 기본값은 `gpt-5-nano`다.
- `gpt-5-mini` provider 비교 실행이 가능해야 한다.
- provider 실행은 작은 범위 제한을 적용한다.
- provider 결과는 DB에 저장하지 않고 report로만 남긴다.
- API, DB schema, K8s, CronJob, frontend 변경이 없다.
- topic summary DB 저장은 하지 않는다.
- `/topics` API는 추가하지 않는다.
- production verification, deployment, rollout은 수행하지 않는다.
- verification 문서에는 실제 실행한 명령과 결과만 기록한다.

## Notes

35차는 topic summary 저장/API 단계가 아니다.

이번 작업은 raw text 기반 topic summary 생성 가능성을 검증하는 report MVP다.  
summary 품질이 충분한지 확인한 뒤, 후속 차수에서 DB 저장과 `/topics` API를 검토한다.

실제 provider 테스트는 다음 순서로 수행한다.

1. `gpt-5-nano`로 1차 테스트
2. 품질 부족 또는 비교 필요 시 `gpt-5-mini`로 동일 조건 재실행
3. 두 report를 비교해 운영 후보 모델을 결정

35차에서는 비용과 실행 범위를 엄격히 제한한다.
