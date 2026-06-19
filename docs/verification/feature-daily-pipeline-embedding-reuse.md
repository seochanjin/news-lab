# Verification: 저장된 article embedding을 daily topic pipeline에 연결

## Verification Scope

- Daily topic pipeline의 후보 조회, embedding, clustering, topic 저장과 CronJob
  실행 계약 조사
- 저장된 pgvector를 clustering vector로 복원하는 공통 embedding 모듈 검증

## Commands Run

Command:
`python -m unittest tests.test_article_embedding_storage tests.test_article_embeddings`

Result:
공통 article embedding 관련 20 tests가 통과했다.

Status: passed

Notes:
저장 vector 복원, 동일 hash reuse, 저장 vector dimension 검증, 비영속 생성,
atomic upsert와 기존 provider 동작을 포함한다. 최초 실행에서는 test fake가
변경된 select projection을 인식하지 못해 2건이 실패했고 fake query 판정을
수정한 뒤 재실행해 통과했다.

Command:
`python -m unittest tests.test_run_daily_topic_pipeline tests.test_article_embedding_storage tests.test_daily_topic_pipeline_cronjob_manifest`

Result:
관련 pipeline, embedding storage와 CronJob contract 27 tests가 통과했다.

Status: passed

Notes:
Stored embedding reuse 시 provider 미호출, 기사별 created/reused/failed 집계,
provider/dimension 실패 격리, metadata/vector 순서 유지, 최소 2건 미달 시
clustering/topic save 건너뜀과 기존 CronJob command/schedule 회귀를 포함한다.
기존 argparse validation test의 예상 error output과 실패 격리 warning log가
출력됐지만 최종 결과는 `OK`다.

Command:
`python -m compileall scripts/run_daily_topic_pipeline.py app/utils/article_embedding_storage.py tests/test_run_daily_topic_pipeline.py`

Result:
대상 application, pipeline script와 test compile이 exit code 0으로 완료됐다.

Status: passed

Command:
`python -m compileall app scripts tests; python -m unittest discover -s tests`

Result:
전체 application/script/test compile이 완료됐고 142 tests가 통과했다.

Status: passed

Notes:
기존 argparse validation test의 예상 error output과 새 article-level failure
격리 warning이 출력됐지만 최종 test result는 `OK`다.

Command:
`git diff --check; git status --short --branch; git diff --name-only; git diff --stat; git diff -- k8s db/migrations app/routers app/main.py requirements.txt`

Result:
`git diff --check`는 출력 없이 통과했다. Branch는
`feature/daily-pipeline-embedding-reuse`이고 변경은 storage utility, daily
pipeline, 관련 tests, pipeline architecture/runbook과 workflow 문서에
한정됐다. 금지 영역 diff는 출력되지 않았다.

Status: passed

Notes:
신규 workflow 문서는 untracked 상태라 `git diff --name-only/stat` 출력에는
포함되지 않는다. K3s manifest, DB migration, Public API와 dependency 변경은
없다.

Command:
`python -m unittest tests.test_run_daily_topic_pipeline tests.test_article_embedding_storage tests.test_daily_topic_pipeline_cronjob_manifest; python -m unittest discover -s tests`

Result:
통계의 `updated` 상태 검증을 보완한 뒤 관련 27 tests와 전체 142 tests가 다시
통과했다.

Status: passed

Command:
`python scripts/run_daily_topic_pipeline.py --window-hours 24 --max-articles 300 --similarity-threshold 0.70 --max-topics 3 --max-reference-topics 10 --max-articles-per-topic 3 --max-raw-chars-per-article 3000 --use-embedding-provider --use-summary-provider --summary-model gpt-5-nano --execute`

Status: human-required

Notes:
Production DB write와 external provider 호출이 발생하므로 실행하지 않았다.
사람이 안전한 credential 주입 후 동일 조건으로 두 번 실행하고 통계와 topic
결과를 제공해야 한다.

Command:
`rg -n '[[:blank:]]+$' <task 관련 변경 file>; git diff --check; git status --short --branch; git diff --name-only; git diff --stat; rg -n '^## ' docs/pr/feature-daily-pipeline-embedding-reuse.md docs/devlog/feature-daily-pipeline-embedding-reuse.md`

Result:
Trailing whitespace 검색과 `git diff --check`는 출력 없이 통과했다. Branch와
task 범위 변경 파일을 확인했고 PR/devlog 필수 section이 모두 존재했다.

Status: passed

Notes:
Git 추적 전 workflow scaffold는 `git diff --name-only/stat`에 포함되지 않지만
`git status --short --branch`에서 별도로 확인했다.

## Results

- Pipeline entry point는 `scripts/run_daily_topic_pipeline.py`다.
- 후보 기사는 최근 24시간의 `articles`를 published time 기준으로 최대 300건
  조회하며 CronJob은 OpenAI embedding provider를 사용한다.
- 기존 embedding은 `prepare_articles()`가 만든 article 순서대로 provider에
  일괄 요청되고 같은 순서의 vector가 `group_articles()`에 전달됐다.
- Clustering은 seed-based greedy grouping이며 기존 threshold, representative
  selection과 topic save contract는 유지 대상이다.
- CronJob command는 `--use-embedding-provider`, `--use-summary-provider`,
  `--execute`를 사용하고 schedule은 `04:00 Asia/Seoul`이다.
- 공통 storage 모듈은 `title_summary` hash가 같은 저장 row의
  `embedding::text`를 clustering용 float tuple로 복원할 수 있다.
- Pipeline은 저장 embedding acquirer가 반환한 정상 article/vector만 같은
  순서로 clustering에 전달한다.
- 개별 embedding 실패는 안전한 article ID/error summary로 기록되고 나머지
  article 처리는 계속된다.
- 정상 vector가 2건 미만이면 clustering, summary와 topic DB save를 건너뛴다.
- Pipeline 결과와 report에 후보 수, embedding 상태별 수, clustering 입력 수,
  topic 수와 elapsed seconds가 추가됐다.

## Manual or Production Verification

- 실제 pipeline 수동 첫 실행과 topic 생성 확인: 사람이 수행 필요
- 동일 조건 두 번째 실행의 embedding reuse 증가 확인: 사람이 수행 필요
- Scheduled daily 실행 관찰: 운영 반영 후 확인 필요

## Pending Verification

- 실제 pipeline 수동 실행과 동일 조건 reuse 확인: 사람이 수행 필요

## Evidence Notes

- CronJob과 K3s manifest는 조사만 했으며 수정하지 않았다.
- Secret, `.env`, kubeconfig와 credential은 읽거나 수정하지 않았다.
- Production pipeline, kubectl, rollout과 production curl은 실행하지 않았다.

## Production E2E Verification

### First execution

동일한 production configuration으로 daily topic pipeline을 실행했다.

결과:

```text
candidate_articles=45
embedding_created=42
embedding_updated=0
embedding_reused=3
embedding_failed=0
clustering_input_count=45
topic_candidate_count=40
topic_count=3
pipeline_elapsed_seconds=135.851984
```

상태: 통과

확인 내용:

- 기존 embedding 3건을 재사용했다.
- 신규 기사 embedding 42건을 생성하고 저장했다.
- Embedding 실패 없이 후보 기사 45건 전체가 clustering에 전달됐다.
- Topic 3건과 연결 기사 6건을 저장했다.
- Raw extraction 3건과 summary 생성 3건이 성공했다.

### Interrupted second attempt

동일 조건 재실행 중 `get_raw_texts()` DB 응답 대기가 장시간 지속되어 사용자가 중단했다.

상태: interrupted

확인 내용:

- `raw text fetch` 단계에서 중단됐다.
- Embedding, summary와 topic DB write 단계에는 도달하지 않았다.
- 중단 후 `pg_stat_activity`에서 장기 transaction이나 lock 대기는 확인되지 않았다.
- 일시적인 DB 또는 network 지연으로 판단하고 다시 실행했다.

### Successful second execution

동일한 production configuration으로 pipeline을 다시 실행했다.

결과:

```text
candidate_articles=38
embedding_created=0
embedding_updated=0
embedding_reused=38
embedding_failed=0
clustering_input_count=38
topic_candidate_count=34
topic_count=3
pipeline_elapsed_seconds=87.256793
```

상태: 통과

확인 내용:

- 후보 기사 38건 모두 저장된 embedding을 재사용했다.
- 신규 embedding 생성과 기존 embedding 갱신이 발생하지 않았다.
- Embedding 실패 없이 38건 전체가 clustering 입력으로 사용됐다.
- 추가 raw extraction 없이 기존 본문을 사용했다.
- Summary 3건을 생성했다.
- Topic 3건과 연결 기사 6건을 저장했다.
- Pipeline이 `daily topic pipeline completion` 로그와 함께 정상 종료됐다.
- 저장 결과의 topic ID는 `21`, `22`, `23`으로 확인됐다.

### Production E2E verdict

다음 저장·재사용 흐름을 실제 Supabase와 external provider 환경에서 확인했다.

```text
첫 실행
→ 기존 embedding 재사용
→ 없는 embedding 생성 및 저장
→ clustering
→ summary
→ topic 저장

동일 조건 재실행
→ 신규 생성 없음
→ 갱신 없음
→ 저장 embedding 전체 재사용
→ clustering
→ summary
→ topic 저장
```

56차의 production E2E verification은 통과했다.
