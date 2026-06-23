# 3일 Topic pipeline·저장·API·CronJob 구축

## 작업 목적

기존 Daily Topic의 24시간 결과와 별개로 최근 72시간 기사 흐름을 다시 분석하는 독립 backend 경로를 구축한다.

3일 Topic은 Daily Topic 결과를 재집계하지 않는다. 원본 기사와 이미 저장된 `article_embeddings`를 직접 조회해 다시 clustering하고, 전용 저장 구조와 API, CronJob으로 운영한다.

최종 목표 흐름은 다음과 같다.

```text
최근 72시간 기사 조회
→ 기존 article_embeddings 재사용
→ 3일 기준 재클러스터링
→ 대표·관련·Summary 근거 기사 선정
→ Summary 근거 기사 원문 확보
→ 72시간 변화 요약 생성
→ 전용 table에 원자 저장
→ archive/home/detail API
→ 전용 CronJob
```

## 기존 문제

Daily Topic은 최근 24시간의 주요 이슈를 생성하는 계약이다. Daily 결과만 다시 묶으면 1일 Topic 선정 과정에서 제외된 기사와 원래 cluster 관계를 복원할 수 없어 72시간 흐름을 제대로 재구성할 수 없다.

기존 `topics`와 `topic_articles`는 1일 결과 계약이므로 3일 결과를 함께 저장하면 기간 의미와 조회 기준이 섞인다. 또한 3일 실행에는 다음 별도 계약이 필요했다.

- 모든 단계가 공유하는 재현 가능한 72시간 window
- 신규 embedding 비용 없이 기존 vector만 사용하는 정책
- embedding 누락을 전체 실패로 만들지 않는 통계
- 72시간 변화와 진행 상황에 맞는 Summary prompt
- 일부 Topic 실패 격리
- 동일 window 재실행 시 중복 방지
- 중간 실패에도 기존 성공 결과를 보존하는 원자 교체
- 독립적인 API와 실행 이력
- Daily 이후 별도로 실행되는 CronJob

## 변경 내용

- 서울 기준 72시간 범위를 한 번 확정하는 `ThreeDayPipelineContext`를 추가했다.
- 기존 `article_embeddings`의 metadata, source hash와 vector를 검증해 호환되는 row만 재사용한다.
- embedding이 없거나 호환되지 않는 기사는 제외하고 사유와 수를 기록한다.
- 저장 embedding을 사용해 최근 72시간 기사를 직접 재클러스터링한다.
- 기간 독립적인 기사 선정 helper를 공통 package로 추출하고 Daily와 3일 pipeline이 공유한다.
- 3일 전용 threshold, 최대 Topic, 관련 기사와 Summary 근거 기사 상한을 분리했다.
- Summary 근거 기사만 원문 재사용·지연 추출과 provider 입력 대상으로 사용한다.
- `three-day-flow-v1` 전용 Summary prompt와 versioned input hash를 추가했다.
- Topic별 원문·Summary 실패를 격리하고 성공 부분집합을 저장한다.
- 3일 Topic 전용 migration, repository와 run 이력을 추가했다.
- advisory lock과 transaction을 사용해 동일 window 결과를 원자적으로 교체한다.
- archive, home, detail API를 추가했다.
- 기본 dry-run인 전용 CLI와 `05:00 Asia/Seoul` CronJob manifest를 추가했다.
- README, Architecture, Runbook과 전용 설계 문서를 갱신했다.

Approved Fixes 문서에는 승인되어 적용된 항목이 없다.

## 구현 상세

### 실행 context와 시간 범위

`ThreeDayPipelineContext`는 실행 시작 시 다음 값을 한 번 결정해 모든 단계에 전달한다.

- `reference_date`
- `business_timezone`
- `started_at_utc`
- `started_at_local`
- `window_start`
- `window_end`
- `window_hours`
- `window_source`

기본 timezone은 `Asia/Seoul`이며 범위는 `[window_start, window_end)` 반개구간이다. `window_start`는 `window_end - 72 hours`로 계산한다. 명시적 `--window-end`는 timezone-aware ISO 8601 값만 허용해 동일 window를 재현할 수 있게 했다.

기사 시간은 `coalesce(published_at, created_at)`을 사용한다. `published_at`이 없으면 수집 시각으로 fallback하며 `analysis_time desc, article_id desc`로 결정론적으로 정렬한다.

### Candidate와 embedding 재사용

Candidate stage는 context의 bound parameter만 사용해 최근 기사와 저장 embedding을 조회한다.

Embedding 사용 조건:

- article ID 일치
- provider, model, dimension과 source type 일치
- 현재 title/summary로 계산한 source hash 일치
- vector dimension 유효

조건을 충족하지 않는 기사는 전체 실행 실패가 아니라 다음 누락 사유로 분류한다.

- `missing_row`
- `incompatible_metadata`
- `stale_hash`
- `invalid_vector`

통계는 `candidate_count = embedding_count + missing_embedding_count` 관계를 유지한다. 3일 pipeline은 embedding provider를 호출하거나 embedding을 insert/update하지 않는다.

### 재클러스터링과 기사 선정

정상 vector가 2건 이상이면 기존 grouping과 대표 기사 선정 로직을 사용해 72시간 기사를 다시 clustering한다. 2건 미만이면 오류 없이 빈 결과로 진행한다.

기간과 DB table에 독립적인 정책은 `app/services/topic_pipeline/selection.py`로 분리했다.

- Topic 정렬
- 원본 URL 보강
- 관련 기사 ID 수집
- 대표 후보 순위 기반 Summary 기사 선정
- URL과 정규화 제목 중복 제거

Daily Topic은 이 helper를 호출하도록 내부 구현만 변경했다. Daily public 결과 모델, CLI, Reference Topic과 CronJob 계약은 유지했다.

3일 설정은 Daily와 분리했다. 대표 기사, Summary 근거 기사와 관련 기사는 다음 관계를 만족한다.

```text
대표 기사 ⊆ Summary 근거 기사 ⊆ 관련 기사
```

### 원문 확보와 Summary

관련 기사 전체가 아니라 Summary 근거 기사만 원문 대상으로 사용한다. 저장된 `raw_articles.raw_text`를 우선 재사용하고 execute 모드에서 원문이 없는 기사만 지연 추출한다.

기사 하나의 추출 실패는 다른 기사와 Topic 처리를 중단하지 않는다. 사용할 원문이 없는 Topic은 저장 대상에서 제외한다.

Summary는 `three-day-flow-v1` prompt를 사용한다. 단일 사건 상태보다 다음 내용을 설명하도록 구성했다.

- 72시간 동안의 변화
- 진행 순서
- 여러 출처에서 공통으로 확인된 내용
- 불확실한 내용

Input hash에는 prompt version, 기사 ID, 기사 시각과 bounded raw text를 포함한다. 실제 provider 입력에 사용된 기사만 `is_summary_evidence=true`로 저장한다.

### 저장 구조와 원자 교체

Migration `007_create_three_day_topic_tables.sql`에 다음 table을 추가했다.

- `three_day_topic_runs`
- `three_day_topics`
- `three_day_topic_articles`

Run 이력 생성·종료 transaction과 Topic 결과 교체 transaction을 분리했다.

```text
run row 생성
→ DB 밖에서 후보·clustering·원문·provider 작업
→ window advisory transaction lock
→ 기존 window Topic 삭제
→ 신규 Topic과 기사 관계 삽입
→ commit 또는 전체 rollback
→ run 상태 종료
```

동일 window의 활성 결과는 교체하지만 run 감사 이력은 누적한다. 일부 Topic이 성공하면 성공 부분집합으로 교체하고 `partial_success`를 기록한다. 모든 Topic이 실패하면 기존 결과를 유지하고 run을 `failed`로 종료한다.

후보나 cluster가 정상적으로 0건인 경우는 `success`로 보고 빈 결과로 교체할 수 있다. Insert 도중 실패하면 기존 삭제와 신규 삽입이 함께 rollback된다.

### API

다음 endpoint를 추가했다.

- `GET /three-day-topics`
- `GET /three-day-topics/home`
- `GET /three-day-topics/{topic_id}`

Archive는 bind parameter 기반 filter와 pagination을 제공한다. Home은 성공 또는 부분 성공한 최신 window 하나만 경량 payload로 반환한다. Detail은 대표 기사와 Summary 근거 여부를 포함하고 `rank`, `article_id` 순서로 기사를 반환한다.

데이터가 없을 때 home은 정상 빈 응답을 반환하며 존재하지 않는 detail은 404를 반환한다. 정적 `/home` route를 동적 `/{topic_id}`보다 먼저 등록했다.

기존 `/topics` API 계약은 변경하지 않았다.

### CLI와 CronJob

`scripts/run_three_day_topic_pipeline.py`는 기본 dry-run이다. `--execute`에서만 run 이력, 결과 교체와 필요한 원문 추출을 수행한다.

Execute 모드는 Summary provider와 key를 요구한다. Embedding provider option은 제공하지 않는다. 단계별 count와 `success`, `partial_success`, `failed` 상태를 출력한다.

CronJob `news-three-day-topic-pipeline`은 Daily Topic 이후인 `05:00 Asia/Seoul`에 실행되도록 정의했다.

- `concurrencyPolicy: Forbid`
- history limit
- resource limit
- active deadline
- backoff limit
- 기존 image와 Secret reference 재사용
- embedding key 불필요

Manifest는 repository에만 추가했으며 실제 cluster에 적용하지 않았다.

## 대안 검토

### Daily Topic 결과 재집계

1일 Topic 선정에서 제외된 기사와 cluster 관계를 복원할 수 없다. Task의 “원본 기사 embedding 직접 재클러스터링” 요구와도 충돌하므로 선택하지 않았다.

### 3일 pipeline에서 누락 embedding 생성

누락률은 줄지만 embedding 비용과 실패 의미가 Daily 생성 정책과 결합된다. 3일 pipeline의 read-only embedding 재사용 계약을 유지하고 누락을 통계로 기록했다.

### DB의 `now() - interval '72 hour'` 사용

단계별 query 시각이 달라지고 동일 실행을 재현하기 어렵다. Application에서 window를 한 번 계산해 모든 query와 저장에 주입했다.

### 기존 `topics`와 `topic_articles` 재사용

1일·3일 기간 의미와 API contract가 섞이고 기존 데이터를 건드릴 위험이 있다. 전용 table과 API를 추가했다.

### 기존 결과를 먼저 삭제한 뒤 pipeline 실행

Provider, 원문 추출 또는 insert 실패 시 기존 성공 결과가 사라진다. 외부 작업을 먼저 완료하고 짧은 transaction에서 결과를 교체하도록 했다.

### Generation을 계속 누적하고 API에서 최신 결과만 선택

Rollback은 단순하지만 동일 window 결과가 계속 누적되고 retention과 publishable generation 관리가 추가된다. Run 이력만 누적하고 활성 Topic set은 교체하는 방식을 선택했다.

### Daily stage package 전체 복사

정책 drift와 수정 중복이 커진다. 기간에 독립적인 순수 selection helper만 공통화하고 나머지는 3일 전용 stage로 분리했다.

### Redis, snapshot 또는 queue 도입

현재 요구사항은 단일 scheduled pipeline과 DB 원자 교체로 충족된다. 운영 복잡도를 늘리는 별도 infrastructure는 도입하지 않았다.

## 선택한 접근과 근거

3일 Topic을 Daily Topic의 파생 데이터가 아니라 동일 기사 저장소를 사용하는 별도 분석 product로 설계했다.

이 접근을 선택한 이유는 다음과 같다.

- 72시간 기사 관계를 원본 vector에서 다시 계산할 수 있다.
- 기존 Daily 결과와 API, table 의미를 보존한다.
- embedding 비용을 추가하지 않고 저장 vector 활용도를 높인다.
- 명시적 window로 실행을 재현할 수 있다.
- 원문·provider 작업과 DB 결과 교체를 분리해 lock 시간을 줄인다.
- advisory lock과 transaction으로 CronJob·수동 실행 경합과 중간 실패를 방어한다.
- Run 감사 이력과 현재 publishable 결과를 분리할 수 있다.
- 일부 Topic 실패를 격리해 전체 window 가용성을 유지한다.
- API와 CronJob을 별도로 운영해 1일·3일 기능을 독립적으로 조정할 수 있다.

## 트레이드오프

- Embedding이 없는 기사는 3일 분석에서 제외되므로 Daily embedding 생성 상태에 결과 coverage가 의존한다.
- Stale hash도 provider 호출 없이 제외하므로 최신 기사 내용 변경이 즉시 반영되지 않을 수 있다.
- 활성 Topic set을 교체하므로 과거 세대별 Topic 본문은 남지 않는다. 실행 감사는 run table에만 보존된다.
- 일부 성공 시 실패한 Topic은 기존 세대에서 유지되지 않고 성공 부분집합으로 전체 window가 교체된다.
- Advisory lock은 동시 교체를 방지하지만 provider 호출 전체를 직렬화하지는 않는다. 늦게 완료된 실행이 같은 window를 다시 교체할 수 있다.
- 전용 table, repository, router와 CronJob이 추가되어 운영 대상이 늘어난다.
- `is_summary_evidence`를 저장해 추적성은 높였지만 관계 table payload와 schema가 증가했다.
- 72시간 품질 점수나 시간 decay는 실제 운영 데이터 없이 도입하지 않았다. 초기에는 기존 clustering과 선정 정책을 출발점으로 사용한다.
- Migration과 CronJob 반영 전에는 API가 table 부재로 정상 운영될 수 없으므로 적용 순서를 지켜야 한다.
- 실제 provider, DB와 cluster를 사용한 end-to-end 검증은 사람 작업으로 남아 있다.

## 테스트

실제 결과의 source of truth는 `docs/verification/feature-three-day-topic-pipeline.md`다.

최종 로컬 검증:

- 3일 pipeline과 실행 진입점
  - 20 passed
- 3일 Topic API
  - 6 passed
- CronJob manifest
  - 3 passed
- 기존 Daily 실행·CronJob 회귀
  - 23 passed
- 전체 `pytest`
  - 261 passed in 8.94s
- 전체 `unittest`
  - 261 tests in 6.604s, OK
- `python -m compileall app scripts tests`
  - passed
- `git diff --check`
  - passed
- table, API route, CronJob 이름·schedule과 문서 일관성 검색
  - passed

검증 과정에서 발견하고 해결한 항목:

- UNIT-02 repository 초기 테스트 1건 실패
  - 저장 계약 수정 후 migration 회귀 포함 11건 통과
- UNIT-04 정적 검사에서 불필요한 EOF 빈 줄 발견
  - 제거 후 compileall과 diff 검사 통과
- UNIT-07 최초 CLI 집중 테스트 실패
  - 실행 계약 수정 후 3일 실행·stage 20건과 Daily 회귀 23건 통과

테스트 환경:

- 가짜 SQLAlchemy engine과 connection
- 메모리 article/vector fixture
- mock extractor와 HTTP
- 로컬 YAML parsing

따라서 실제 DB write, migration, embedding·Summary provider, 원문 추출, Kubernetes command와 production API는 검증하지 않았다.

## 운영 반영

Repository 수준 구현과 로컬 검증까지 완료했다. 운영 반영은 수행하지 않았다.

Pending 또는 human-required:

- `007_create_three_day_topic_tables.sql` review와 Supabase 적용
- 적용 전후 table, constraint와 index 확인
- Kubernetes client-side manifest dry-run
- K3s server-side admission dry-run
- CronJob manifest apply
- 수동 Job 실행
- Job log와 `three_day_topic_runs` 확인
- 저장 Topic과 기사 역할 확인
- production archive, home, detail API 확인
- 동일 window 재실행 idempotency 확인
- 다음 scheduled `05:00 Asia/Seoul` Job 확인

권장 반영 순서는 image 확인 → migration → schema 확인 → manifest dry-run → apply → 수동 Job → DB/API 확인 → scheduled Job 확인이다.

Git push, PR merge, production deployment, K3s rollout과 production verification 완료를 주장하지 않는다.

## README 업데이트 판단

README를 업데이트했다.

3일 Topic은 신규 pipeline, API와 운영 진입점을 추가하는 기능이므로 repository 사용자가 최소한 다음 내용을 찾을 수 있어야 한다.

- 3일 Topic API endpoint
- 로컬 dry-run 실행 command
- 전용 migration 존재
- 운영 반영은 사람이 수행한다는 경계

세부 설계와 운영 절차는 README에 중복하지 않고 Architecture, Runbook과 `docs/design/three-day-topic-pipeline.md`로 연결했다.

## 확인 결과

- 72시간 window가 pipeline 전체에서 동일하게 사용된다.
- `published_at` 우선, `created_at` fallback 정책이 적용된다.
- 저장 embedding만 사용하고 신규 embedding provider 호출은 없다.
- 누락·비호환 embedding이 안전하게 제외되고 집계된다.
- Daily Topic 결과를 읽지 않고 기사 embedding을 직접 재클러스터링한다.
- 대표 기사, Summary 근거 기사와 관련 기사 부분집합 계약이 검증된다.
- Summary 근거 기사만 원문 확보와 provider 입력에 사용된다.
- Topic별 실패 격리와 일부 성공 저장이 동작한다.
- 동일 window 결과가 transaction으로 원자 교체된다.
- 전부 실패하면 기존 성공 결과를 보존한다.
- Run 이력과 활성 Topic 결과가 분리된다.
- 신규 archive, home, detail API와 빈 응답·404·route 순서가 검증됐다.
- Daily Topic의 외부 CLI, CronJob manifest와 기존 `/topics` API 계약은 유지됐다.
- Python 변경 파일과 테스트에 한글 docstring이 반영됐다.
- Approved Fixes에는 승인된 적용 항목이 없다.
- Production migration과 K3s 반영은 완료되지 않았다.

## 이번 단계의 의미

NewsLab이 “오늘의 주요 이슈”뿐 아니라 며칠에 걸쳐 전개되는 흐름을 별도 backend product로 생성할 수 있게 됐다.

기존 embedding 자산을 다시 활용해 추가 embedding 비용 없이 분석 기간을 확장했다. Daily Topic을 재집계하지 않고 원본 기사 관계를 다시 계산하기 때문에 24시간 경계에서 분리된 사건도 하나의 72시간 흐름으로 묶을 수 있다.

저장 측면에서는 실행 감사 이력과 현재 publishable 결과를 분리하고, 외부 작업 완료 후 원자 교체하는 패턴을 도입했다. 이 패턴은 이후 다른 기간 Topic pipeline을 설계할 때도 재사용할 수 있다.

## 포트폴리오용 요약

기존 Daily 뉴스 Topic과 독립적으로 최근 72시간 기사를 재클러스터링하는 3일 Topic pipeline을 설계·구현했다. 저장된 article embedding만 read-only로 재사용하고 누락 vector를 격리했으며, 대표·관련·Summary 근거 기사 집합과 72시간 변화 중심 Summary를 구성했다. PostgreSQL advisory lock과 transaction 기반 동일 window 원자 교체, 실행 감사 이력, 일부 성공 처리와 실패 시 기존 결과 보존 정책을 구현했다. 전용 migration, FastAPI archive/home/detail API, K3s CronJob과 운영 문서를 추가하고 전체 261건 회귀 테스트로 기존 Daily 계약을 보호했다.

## 다음 단계 후보

- Human operator가 migration과 K3s 최초 반영 절차를 수행한다.
- 실제 72시간 데이터에서 Topic 품질, source 다양성, 누락 embedding 비율과 실행 시간을 관찰한다.
- 운영 결과를 기반으로 similarity threshold, 후보·Topic·관련 기사 상한을 별도 Task에서 조정한다.
- `partial_success` 비율과 Topic별 원문·Summary 실패 원인을 모니터링한다.
- 동일 window 수동 재실행으로 활성 결과 비중복과 run 이력 누적을 확인한다.
- 장기 운영 후 3일 Topic 세대 보존 또는 retention 요구가 생기면 별도 설계를 검토한다.
- 7일 Topic은 별도 table, pipeline, API와 CronJob Task로 진행한다.
- Frontend에서 3일 Topic을 노출하는 작업은 별도 repository Task로 진행한다.
