# Topic summary DB 저장 및 조회 API MVP

## 작업 내용

- raw text 기반 topic summary report MVP를 DB 저장 및 read API 단계로
  확장했습니다.
- `topics`, `topic_articles` 저장 구조와 기본 dry-run save CLI를 추가했습니다.
- 저장된 topic summary를 조회하는 `/topics`, `/topics/{topic_id}` API를
  추가했습니다.
- API와 저장 report에는 raw text 전문을 노출하지 않습니다.

## 주요 변경 사항

- `db/migrations/005_create_topics_tables.sql`
  - topic summary와 근거 article 연결을 위한 테이블, FK, unique constraint,
    조회 index를 정의합니다.
  - 동일 input의 provider/model별 결과를 저장할 수 있도록
    `unique(summary_input_hash, provider, model)`을 사용합니다.
- `scripts/save_topic_summaries.py`
  - 기존 summary 생성 helper를 재사용해 save plan과 markdown report를
    생성합니다.
  - 기본 실행은 read-only dry-run이며 `--execute`가 명시된 경우에만
    transaction 안에서 topic과 article link를 저장합니다.
  - approved fix로 upsert conflict target을 migration의 composite unique
    constraint와 일치시켰습니다.
- `app/utils/topic_summary.py`
  - 실제 bounded summary input을 기반으로 `summary_input_hash`를 생성합니다.
- `app/routers/topics.py`, `app/main.py`
  - topic 목록 및 상세 read-only router를 추가하고 FastAPI app에
    등록했습니다.
- 테스트
  - migration 구조, dry-run/save plan, mocked persistence, composite conflict
    target, pagination/detail/404/raw text 미노출을 검증합니다.

## 추가/변경된 API

- `GET /topics`
  - `page`, `page_size`, `status`, `date_from`, `date_to`, `keyword` 필터를
    지원하는 pagination 목록 API입니다.
  - `items`, `page`, `page_size`, `total`, `has_next`를 반환합니다.
- `GET /topics/{topic_id}`
  - topic summary와 관련 article metadata를 반환합니다.
  - 존재하지 않는 topic은 `404`를 반환합니다.
- API 응답에는 `raw_text`가 포함되지 않습니다.
- 기존 API response 구조는 변경하지 않았습니다.

## DB 변경 사항

- migration SQL에 `topics`, `topic_articles` 테이블을 추가했습니다.
- 주요 constraint:
  - `unique(summary_input_hash, provider, model)`
  - `unique(topic_id, article_id)`
  - `topic_articles.topic_id -> topics.id`
  - `topic_articles.article_id -> articles.id`
- Human operator가 Supabase SQL Editor에서 migration을 수동 적용했고,
  verification 문서에 table/constraint/index 확인 결과가 기록되어 있습니다.
- Human-approved limited execute에서 deterministic topic 1개와 관련 article
  link 1개가 저장되었습니다.

## README 영향

- README는 변경하지 않았습니다.
- `/topics` API가 추가되었지만 production deployment와 공개 운영 검증이 아직
  완료되지 않았으므로, 운영 surface가 확정된 뒤 README/RUNBOOK 업데이트를
  별도 검토합니다.

## 테스트

- 초기 구현 검증:
  - Python compile: passed
  - focused summary/save/API tests: 30 tests passed
  - full unittest: 105 tests passed
- Approved fix 검증:
  - Python compile: passed
  - focused migration/save/topics API tests: 11 tests passed
  - full unittest: 106 tests passed
  - save CLI help: passed
  - 전체 및 targeted `git diff --check`: passed
- Scope/security:
  - K8s, GitHub Actions, frontend, Dockerfile 변경 없음
  - credential 값 노출 없음

## 확인 결과

- Approved fix 적용 후 `UPSERT_TOPIC_QUERY`와 migration 모두
  `(summary_input_hash, provider, model)` composite key를 사용합니다.
- Human-approved Supabase verification:
  - migration 적용 및 expected table/constraint/index 확인
  - dry-run 성공: DB write 및 raw extraction 없음
  - limited execute 성공: topic 1개, related article link 1개 저장
- Human-approved local API verification:
  - `/health`, `/topics`, `/topics/1` 정상 응답
  - topic 목록/detail에서 저장된 deterministic summary와 article metadata 확인
  - `/topics`, `/topics/1` 응답에 raw text 미포함 확인
- Raw extraction과 provider 호출은 수행하지 않았습니다.

## 비고

- Supabase migration 및 limited execute는 human-approved verification으로
  수행되었으며 Codex가 실행하지 않았습니다.
- Production deployment, K3s rollout, production HTTP verification, PR merge는
  수행되지 않았으며 pending입니다.
- Optional provider-based save verification은 deferred 상태입니다.
