# Topic 대표 후보 기반 raw extraction 대상 선정

## 작업 내용

- 기존 topic grouping과 representative candidate 결과를 재사용해 실제 raw
  extraction 전에 검토할 target을 read-only로 선정한다.
- topic당 target 최대 수를 1~3으로 제한하고 기본 1개 및 비교용 2개
  markdown report와 CLI JSON output을 생성한다.
- 실제 raw extraction, DB write, topic summary 생성은 수행하지 않는다.

## 주요 변경 사항

- representative rank와 raw 상태를 결합해 `target`, `backup`, `skipped`,
  `already_extracted`, `failed` 상태와 선정/제외 사유를 계산한다.
- topic 내부 article을 representative rank 오름차순으로 정렬하고 rank가
  없는 article은 뒤로 배치해 입력 순서와 무관한 target 선정을 보장한다.
- multi-article topic을 우선하고 source count, article count, 최신순으로
  topic을 정렬한다. Candidate score는 topic 내부 ranking에만 사용한다.
- `raw_articles` 상태는 bind parameter를 사용한 read-only query로
  조회하며 실제 extractor는 호출하지 않는다.
- provider 실행은 기존 opt-in, API key, article limit safety gate를
  유지한다.
- deterministic report에는 검증용이며 실제 extraction 승인 목록이
  아니라는 경고를 표시한다. Max2 report에는 복수 target 정책 비교용이며
  실행 승인이 아니라는 경고를 추가한다.

## 추가/변경된 API

- 신규 API 없음.
- 기존 FastAPI route 및 응답 구조 변경 없음.
- 결과는 CLI JSON output과 markdown report로 확인한다.

## DB 변경 사항

- DB schema 및 migration 변경 없음.
- `articles`, `sources`, `raw_articles` 상태만 read-only transaction으로
  조회한다.
- insert/update/delete 및 extraction run 기록을 수행하지 않는다.

## README 영향

- README 변경 없음.
- 내부 분석 CLI와 검토 report 추가이며 사용자-facing API나 운영 절차는
  변경하지 않았다.

## 테스트

- 승인 fix 적용 후 Python compile: 통과.
- 승인 fix focused unittest: 최종 `13 passed`.
- Full unittest discovery: 최종 `67 passed`.
- 뒤섞인 rank 입력 테스트: rank 1 `target`, rank 2 `backup`, rank 없는
  article `skipped` 확인.
- CLI help: 통과.
- Deterministic read-only report 생성:
  - `max_targets_per_topic=1`: 통과, target 2개
  - `max_targets_per_topic=2`: 통과, target 4개
- Report warning 검사: 통과.
- `git diff --check`: 통과.
- K8s 변경 없음.
- `pytest`: executable 미설치로 pending.

## 확인 결과

- 분석 article 100건에서 topic 96개, multi-article topic 2개를 확인했다.
- 기본 정책은 multi-article topic별 최대 1개, 비교 정책은 최대 2개
  target을 선정했다.
- 입력 article 순서가 뒤섞여도 representative rank가 낮은 eligible
  후보부터 target 한도를 사용한다.
- report에 rank, candidate score, raw status, target/backup/skipped 상태와
  결정 사유가 표시된다.
- 기본 deterministic report와 max2 비교 report에 검증용/비승인 경고가
  표시되며 Human review status는 `Pending`이다.
- `db_write_performed=false`, `raw_extraction_performed=false`를 확인했다.
- `.env`, K8s, DB schema, API routers, frontend, raw extractor,
  grouping/scoring 정책 변경이 없음을 확인했다.
- 실제 OpenAI provider, raw extraction, DB write, production verification는
  실행하지 않았다.

## 비고

- 승인 fix focused unittest 최초 실행은 기존 테스트가 fix 이전 입력 순서를
  기대해 `1 failed, 12 passed`였고, 승인된 rank 우선 순서로 기대값을
  수정한 뒤 `13 passed`를 확인했다.
- 현재 샘플의 multi-article 후보에는 existing raw/failed 상태가 없었고,
  해당 상태 제외 정책은 unit test로 검증했다.
- Rejected/deferred 항목인 report path 제한 개선은 적용하지 않았다.
- topic당 1개와 2개 중 최종 정책 선택 및 실제 extraction 실행은 human
  review 후 후속 단계다.
- `pytest`, 실제 provider 비교, 실제 extraction, summary 생성, PR merge,
  deployment, rollout, production verification는 pending이다.
