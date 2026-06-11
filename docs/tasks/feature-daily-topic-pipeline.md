# Task: 수동 daily topic pipeline MVP

## Goal

최근 24시간 동안 수집된 기사들을 기준으로, 하나의 수동 실행 daily topic pipeline을 만든다.

목표 흐름은 다음과 같다.

```text
최근 24시간 기사 조회
→ 메모리 기반 embedding topic grouping
→ topic별 raw extraction target 선정
→ 필요한 기사만 raw extraction
→ raw_text 기반 gpt-5-nano topic summary 생성
→ topics/topic_articles 저장 plan 생성
→ human-approved --execute에서만 DB 저장
→ /topics API로 조회 가능한 provider summary 확보
```

이번 작업의 핵심은 기존의 분리된 분석/추출/요약 저장 흐름을 하나의 수동 실행 파이프라인으로 연결하는 것이다.  
CronJob 자동화는 이번 범위가 아니며, 39차 작업에서 다룬다.

## Scope

- 최근 24시간 기사 기준 daily topic pipeline 구현
- 가능한 경우 새 스크립트 추가:
  - `scripts/run_daily_topic_pipeline.py`
- 기존 유틸/스크립트 재사용:
  - `app/utils/article_embeddings.py`
  - `app/utils/topic_grouping.py`
  - `app/utils/topic_representatives.py`
  - `scripts/analyze_topic_groups.py`
  - `scripts/analyze_raw_extraction_targets.py`
  - `scripts/run_raw_extraction_targets.py`
  - `scripts/generate_topic_summary_report.py`
  - `scripts/save_topic_summaries.py`
- 메모리 기반 embedding 생성 및 topic grouping
- topic별 representative/supporting article 선정
- selected article에 대해서만 raw extraction 실행
- raw_text가 확보된 기사만 summary input으로 사용
- `gpt-5-nano` provider summary 생성 옵션 지원
- 기본 실행은 dry-run
- `--execute` 옵션이 있을 때만 DB write 수행
- `topics`, `topic_articles` 저장 plan 생성
- 가능하면 `topic_articles.similarity_score` 저장 반영
- report 생성
- 기존 `news-raw-extractor` CronJob suspend 운영 절차 문서화
- 39차 CronJob 자동화에서 재사용 가능한 명령 형태로 구성

권장 dry-run 명령 예시는 다음과 같다.

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.70 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-070.md
```

Compare the wider `0.70` grouping with the initial operating candidate `0.72`:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.72 \
  --max-topics 3 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run-072.md
```

권장 execute 명령 예시는 다음과 같다.

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.78 \
  --max-topics 5 \
  --max-reference-topics 10 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --execute \
  --report-path docs/reports/feature-daily-topic-pipeline-execute.md
```

단, Codex/agent는 provider 호출 및 `--execute` 실행을 하지 않는다.  
실제 provider 호출과 DB write는 human-approved 단계로만 수행한다.

## Do not change

- CronJob 자동화 구현 금지
- 새 K8s CronJob manifest 추가 금지
- `news-raw-extractor` 코드 삭제 금지
- 기존 raw extractor CronJob manifest 삭제 금지
- DB migration 추가 금지
- `article_embeddings` 테이블 추가 금지
- `topic_candidates` 또는 `topic_candidate_articles` 테이블 추가 금지
- embedding vector DB 저장 금지
- topic candidate 중간 결과 DB 저장 금지
- 3일/7일 trend summary 구현 금지
- gpt-5-mini 비교 구현 금지
- fallback/retry/factuality gate 고도화 금지
- frontend 변경 금지
- Raspberry Pi worker 관련 변경 금지
- secrets, `.env`, kubeconfig, credentials, SSH keys, tokens 수정 금지
- production-impacting command 실행 금지
- `kubectl apply/delete/patch/rollout` 실행 금지
- Supabase SQL 직접 실행 금지
- `git push`, `git merge`, PR merge 금지
- provider 대량 호출 금지
- human approval 없는 `--execute` 실행 금지

## Expected files

Expected new or modified files:

```text
scripts/run_daily_topic_pipeline.py
tests/test_run_daily_topic_pipeline.py
docs/tasks/feature-daily-topic-pipeline.md
docs/verification/feature-daily-topic-pipeline.md
docs/pr/feature-daily-topic-pipeline.md
docs/devlog/feature-daily-topic-pipeline.md
docs/RUNBOOK.md
```

Optional, only if needed:

```text
scripts/generate_topic_summary_report.py
scripts/save_topic_summaries.py
app/utils/topic_representatives.py
app/utils/raw_extraction_targets.py
tests/test_save_topic_summaries.py
tests/test_topic_representatives.py
```

Do not create DB migration files for this task.

## DB changes

No schema changes.

Allowed DB behavior:

- Read recent `articles`
- Read existing raw text tables used by the current codebase
- Generate save plan for `topics`
- Generate save plan for `topic_articles`
- Write to `topics` and `topic_articles` only when `--execute` is explicitly passed

Not allowed:

- New tables
- New columns
- DB migrations
- embedding vector storage
- topic candidate intermediate storage
- raw SQL migration execution
- Supabase SQL execution by agent

## API changes

No API route changes are expected.

The existing production read path remains:

```http
GET /topics?page=1&page_size=10
GET /topics/{topic_id}
```

The pipeline should produce data that can be read through the existing `/topics` API.

Do not modify API response shape unless strictly necessary.  
If API changes become necessary, stop and explain before implementing.

## Test commands

Run only local, non-production-impacting commands.

Required:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m unittest discover -s tests -v
git diff --check
```

Recommended targeted tests if files exist:

```bash
python -m unittest tests.test_run_daily_topic_pipeline -v
python -m unittest tests.test_save_topic_summaries -v
```

Dry-run command may be documented but should not be executed by Codex if it triggers provider calls.

Provider and DB write commands are human-approved only:

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.78 \
  --max-topics 5 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --report-path docs/reports/feature-daily-topic-pipeline-dry-run.md
```

```bash
.venv/bin/python scripts/run_daily_topic_pipeline.py \
  --window-hours 24 \
  --max-articles 300 \
  --similarity-threshold 0.78 \
  --max-topics 5 \
  --max-articles-per-topic 3 \
  --max-raw-chars-per-article 3000 \
  --use-embedding-provider \
  --use-summary-provider \
  --summary-model gpt-5-nano \
  --execute \
  --report-path docs/reports/feature-daily-topic-pipeline-execute.md
```

Production read verification is human-run only unless explicitly allowed:

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/<topic_id>"
```

Existing raw extractor CronJob suspend is human-run only:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl patch cronjob news-raw-extractor \
  -n default \
  -p '{"spec":{"suspend":true}}'
```

Verification check:

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob news-raw-extractor -n default
```

## Acceptance criteria

- A manual daily topic pipeline can be run from one command.
- The pipeline uses recent 24-hour articles as input.
- Embedding vectors are used only in memory.
- No embedding vectors are saved to DB.
- No topic candidate intermediate tables are introduced.
- The pipeline can group similar articles into topic candidates.
- The pipeline can select representative/supporting articles per topic.
- The pipeline can run raw extraction only for selected articles.
- The pipeline can generate topic summaries with `gpt-5-nano` when explicitly enabled.
- The default mode is dry-run and does not write to DB.
- `--execute` is required for DB write.
- Save plan targets only `topics` and `topic_articles`.
- If available, `similarity_score` is preserved into `topic_articles`.
- Report includes:
  - window hours
  - article count
  - topic candidate count
  - selected topic count
  - selected article ids
  - article_count/source_count per topic
  - similarity scores where available
  - raw extraction success/failure count
  - summary provider/model
  - DB write performed 여부
- Existing `/topics` API can read the saved provider summary after human-approved execute.
- Raw text is not exposed through API.
- Existing raw extractor CronJob is not deleted; suspend procedure is documented only.
- Local tests pass.
- Verification document records only commands actually run and their actual results.

## Notes

This task intentionally favors speed and simplicity.

For 24-hour daily summaries with fewer than roughly 300 articles per day, in-memory embedding grouping is acceptable.  
Embedding DB storage is deferred until 3-day/7-day trend summaries, search/recommendation, or repeated reprocessing becomes necessary.

The preferred 38~40 plan is:

```text
38차: manual daily topic pipeline MVP
39차: daily topic pipeline CronJob automation
40차: frontend topic summary connection
```

Existing `news-raw-extractor` should remain in the repository for now.  
Operationally, it may be suspended after the new daily topic pipeline is verified, but the suspend action must be performed manually by the human operator.
