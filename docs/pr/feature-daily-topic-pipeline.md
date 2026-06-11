# 수동 daily topic pipeline MVP

## 작업 내용

- 최근 24시간 기사를 대상으로 topic grouping부터 raw extraction, summary 생성,
  `topics`/`topic_articles` 저장 계획까지 연결하는 수동 daily pipeline을 추가했습니다.
- 기본 실행은 dry-run이며, 실제 raw extraction과 DB write는 명시적인
  `--execute`에서만 수행됩니다.
- embedding vector와 topic candidate 중간 결과는 메모리에서만 처리합니다.

## 주요 변경 사항

- `scripts/run_daily_topic_pipeline.py`
  - 기존 grouping, representative 선정, raw extraction target, summary, save
    모듈을 하나의 실행 흐름으로 연결했습니다.
  - selected topic을 `article_count`, `source_count`, 평균 similarity, 최신 기사
    시각, topic ID 순서로 정렬한 뒤 `--max-topics`를 적용합니다.
  - `--max-reference-topics`를 추가해 summary 대상 밖 후보를 report-only
    `Reference Candidates`로 남깁니다.
  - reference candidates는 raw extraction, summary provider, save plan, DB
    write 대상에서 제외합니다.
  - report에 selected/reference 기사 metadata와 generated summary를 표시하며
    raw text는 노출하지 않습니다.
- `scripts/analyze_topic_groups.py`
  - daily pipeline report에서 기사 URL을 표시할 수 있도록 기존 read-only
    기사 조회 projection에 `a.url`을 추가했습니다.
- `docs/RUNBOOK.md`
  - 0.70/0.72 provider dry-run 비교 절차와 기존 raw extractor CronJob suspend
    수동 절차를 문서화했습니다.
- 승인된 Fix 1-4와 실제 검증 결과를 fixes/verification 문서에 반영했습니다.

## 추가/변경된 API

- 추가 또는 변경된 API route와 response shape는 없습니다.
- 기존 조회 경로를 그대로 사용합니다.
  - `GET /topics?page=1&page_size=10`
  - `GET /topics/{topic_id}`

## DB 변경 사항

- DB schema, migration, 신규 테이블 및 신규 컬럼 변경은 없습니다.
- embedding vector와 topic candidate 중간 결과는 DB에 저장하지 않습니다.
- 실제 저장 대상은 기존 `topics`, `topic_articles`입니다.
- 검증 문서에 기록된 human-approved 0.70 `--execute`에서만 실제 raw
  extraction 및 DB write가 수행되었습니다.
- Supabase SQL과 migration은 실행하지 않았습니다.

## README 영향

- README 변경은 필요하지 않습니다.
- 수동 실행, threshold 비교, raw extractor CronJob suspend 절차는
  `docs/RUNBOOK.md`에 기록했습니다.

## 테스트

실행 및 통과:

```bash
python -m py_compile scripts/run_daily_topic_pipeline.py
python -m py_compile scripts/run_daily_topic_pipeline.py scripts/analyze_topic_groups.py
python -m unittest tests.test_run_daily_topic_pipeline -v
python -m unittest tests.test_save_topic_summaries -v
python -m unittest tests.test_run_daily_topic_pipeline tests.test_analyze_topic_groups tests.test_save_topic_summaries -v
python -m unittest discover -s tests -v
git diff --check
```

- Final focused pipeline tests: 8 passed.
- Save topic summary tests: 8 passed.
- Combined focused tests: 25 passed.
- Full unittest discovery: 116 passed.
- `git diff --check`: passed.
- Scope diff에서 DB migration, K8s, GitHub Actions, frontend, Dockerfile, API
  router 변경이 없음을 확인했습니다.

## 확인 결과

- 기본 dry-run, provider/API key gate, mocked execute 경계를 확인했습니다.
- selected topic 정렬과 `--max-topics` 적용 순서를 확인했습니다.
- reference candidates가 extraction, summary, save 경로에 진입하지 않음을
  확인했습니다.
- report에 기사 metadata와 generated summary가 표시되고 raw text가
  노출되지 않음을 확인했습니다.
- Human-approved provider dry-run:
  - 0.70: 115개 기사, 105개 후보, selected 3개, reference 10개
  - 0.72: 115개 기사, 107개 후보, selected 3개, reference 10개
- Human-approved 0.70 `--execute`:
  - selected topic 3개
  - raw extraction 성공/실패 3/2
  - provider summary 2개 저장, 1개 `insufficient_raw_text`
  - DB write 수행 확인
- Human-provided production `/topics` 확인 로그에서:
  - 새 `openai` / `gpt-5-nano` summary가 조회됨
  - topic detail에 raw text가 노출되지 않음
  - 존재하지 않는 topic ID가 HTTP 404를 반환함

## 비고

- PR merge, 배포, K3s rollout은 완료로 표시하지 않습니다.
- kubectl 명령, Supabase SQL, migration, git push, git merge는 실행하지
  않았습니다.
- 기존 `news-raw-extractor` CronJob suspend 여부는 human decision pending입니다.
- CronJob 자동화와 frontend 연결은 후속 작업 범위입니다.
- Provider summary에서 일부 한국어 품질 문제가 관찰되어 frontend 노출 전
  품질 검토가 필요합니다.
