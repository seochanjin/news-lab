# Topic 대표 후보 기반 raw extraction 대상 선정

## 작업 목적

- representative candidate 결과에서 후속 raw extraction 대상으로 먼저
  검토할 article을 선정한다.
- 실제 원문 요청이나 DB write 전에 정책 결과를 JSON과 markdown으로
  검토할 수 있게 한다.

## 기존 문제

- representative candidate rank는 topic 내부 대표성만 설명하며, raw text
  존재 여부나 실패 이력을 고려하지 않는다.
- candidate score를 topic 간 extraction priority로 오용할 위험이 있었다.
- 실제 extraction 전에 topic당 몇 개를 추출할지 비교할 read-only
  산출물이 없었다.

## 변경 내용

- raw 상태와 representative rank를 결합하는 target selection helper 추가.
- read-only 분석 CLI 및 기본 1개/비교 2개 target report 추가.
- target 정책과 CLI safety gate를 검증하는 unit test 추가.
- 승인 fix를 적용해 입력 순서와 무관한 rank 우선 target 선정을 보장했다.
- deterministic/max2 report가 실제 extraction 승인 목록으로 오해되지
  않도록 상단 warning을 추가했다.

## 구현 상세

- `app/utils/raw_extraction_targets.py`
  - multi-article topic에서 pending/not-extracted 대표 후보만 target으로
    선정한다.
  - raw text가 있으면 `already_extracted`, failed 이력이 있으면 `failed`,
    limit 초과 후보는 `backup`, 대표 후보 밖 article은 `skipped`로
    표시한다.
  - target 판정 전에 rank가 있는 article을 rank 오름차순으로 정렬하고,
    rank가 없는 article은 뒤로 배치하며 article id를 tie-breaker로
    사용한다.
  - topic 정렬은 multi-article, source count, article count, 최신순이며
    candidate score를 topic 간 정렬에 사용하지 않는다.
  - deterministic report에는 검증용/비승인 경고를, max2 report에는 복수
    target 정책 비교용/비승인 경고를 표시한다.
- `scripts/analyze_raw_extraction_targets.py`
  - 기존 조회, classification, deterministic embedding, grouping,
    representative selection을 재사용한다.
  - 선택된 article ID의 raw 상태만 bind parameter로 조회하고 transaction을
    read-only로 설정한다.
  - 실제 extraction 및 DB write 여부를 JSON/report에 false로 명시한다.

## 대안 검토

- candidate rank 1만 무조건 extraction 대상으로 지정:
  raw text가 이미 있거나 failed 상태일 수 있어 제외했다.
- candidate score로 모든 topic을 전역 정렬:
  score가 topic 내부 비교용이므로 정책 의미가 달라 제외했다.
- 실제 extractor에 target policy를 바로 연결:
  정책 human review 전 DB write와 외부 요청을 발생시키므로 후속 단계로
  미뤘다.
- CLI report 출력 경로를 `docs/reports/` 하위로 제한:
  현재 핵심 결함과 직접 관련이 없고 production 영향도 없어 승인 fix에서
  보류했다.
- deterministic report를 실제 extraction 승인 목록으로 사용:
  topic 품질이 낮을 수 있어 human-approved embedding provider 결과와
  human review가 필요하므로 제외했다.

## 선택한 접근과 근거

- 기존 grouping/scoring 결과 위에 독립적인 target policy layer를
  추가했다. 기존 정책을 변경하지 않고 extraction readiness만 검토할 수
  있다.
- raw 상태를 별도 read-only query로 조회했다. 기존 article query와
  scoring contract를 유지하면서 원문 존재/실패 상태만 결합할 수 있다.
- topic당 최대 target 수를 1~3으로 제한하고 1개와 2개 report를 비교했다.
  초기 비용을 제한하면서 summary 품질에 필요한 원문 수를 human review할
  수 있다.
- article 입력 순서를 신뢰하지 않고 rank 기준으로 다시 정렬한다.
  upstream 자료 구조가 변경되더라도 rank 1 후보가 먼저 평가되는 정책
  불변식을 유지할 수 있다.
- report 상단에 검증 산출물의 한계를 명시한다. Read-only 실행 결과가
  후속 실제 extraction 승인을 의미하지 않도록 운영 판단 경계를 분리한다.

## 트레이드오프

- 현재 topic ordering은 source/article count와 최신성만 사용하는 MVP다.
- failed article은 자동 재시도하지 않으므로 필요 시 사람이 별도 retry
  정책을 승인해야 한다.
- deterministic grouping 품질에 target 결과가 의존한다.
- 현재 실제 샘플의 multi-article 후보에는 already-extracted/failed 사례가
  없어 해당 분기는 unit test로만 확인했다.
- rank 우선 정렬은 eligible rank 1을 먼저 평가하지만, rank 1이
  already-extracted/failed이면 다음 eligible rank가 target이 된다.
- max2 report는 비교 가능한 정보를 늘리지만 실제 extraction 비용과
  summary 품질 간 최종 정책은 확정하지 않는다.
- report path 제한은 보류되어 사용자가 임의 경로를 지정할 수 있다.

## 테스트

- 승인 fix 적용 후 Python compile: 통과.
- 승인 fix focused unittest: 최종 `13 passed`.
- Full unittest discovery: 최종 `67 passed`.
- 뒤섞인 rank 입력 테스트:
  - rank 1: `target`
  - rank 2: `backup`
  - rank 없음: `skipped`
- CLI help: 통과.
- deterministic read-only report:
  - topic당 최대 1개: target 2개
  - topic당 최대 2개: target 4개
- deterministic/max2 warning 검사: 통과.
- `git diff --check`: 통과.
- K8s 및 보호 범위 변경 없음.
- credential-pattern 검사에서 실제 credential 값 발견 없음.
- `pytest`: executable 미설치로 pending.
- 승인 fix focused unittest 최초 실행은 기존 테스트가 fix 이전 입력 순서를
  기대해 `1 failed, 12 passed`였으며, 승인된 rank 우선 기대값으로 수정한
  뒤 통과했다.

## 운영 반영

- 운영 반영하지 않았다.
- 실제 raw extraction, DB write, summary 생성, OpenAI provider 호출,
  production verification, Kubernetes command, rollout, deployment, push,
  merge를 수행하지 않았다.
- PR merge 및 production 반영 상태는 pending이다.

## README 업데이트 판단

- README는 변경하지 않았다.
- 내부 read-only 분석 단계이며 API와 운영 절차 변경이 없어 README 갱신이
  필요하지 않다고 판단했다.

## 확인 결과

- 24시간/100건/threshold 0.72 deterministic 분석에서 topic 96개,
  multi-article topic 2개를 확인했다.
- 기본 1개 정책은 target 2개, 비교 2개 정책은 target 4개를 선정했다.
- 두 report 모두 target/backup/skipped 상태, candidate rank/score, raw
  status, 결정 사유를 표시한다.
- 입력 article 순서가 뒤섞여도 rank 1 eligible 후보가 먼저 target으로
  평가된다.
- 기본 deterministic report는 검증용/비승인 경고를, max2 report는
  비교용/비승인 경고를 표시하고 Human review status를 `Pending`으로
  유지한다.
- DB write와 raw extraction이 수행되지 않았음을 결과에 명시했다.
- `.env`, K8s, DB schema, API routers, frontend, raw extractor,
  grouping/scoring 정책 변경이 없음을 확인했다.

## 이번 단계의 의미

- topic 대표 후보를 실제 원문 확보 단계와 연결하기 전에, raw 상태와 비용
  제한을 반영한 검토 가능한 target policy를 분리했다.
- 후속 실제 extraction 및 topic summary 생성 전에 사람이 대상과
  topic당 원문 수를 결정할 수 있다.
- read-only 분석 결과와 실제 운영 승인 사이의 경계를 report 자체에
  명시해 잘못된 extraction 실행 위험을 줄였다.

## 포트폴리오용 요약

- NewsLab의 topic representative candidate 결과에 raw extraction 상태를
  결합하는 read-only target selection MVP를 구현했다.
- 상태 기반 안전 정책, topic당 target limit, 설명 가능한 decision reason,
  rank 기반 deterministic selection, JSON/markdown 산출물과 67개
  unittest로 실제 extraction 전 검토 단계를 마련했다.
- deterministic 검증 report에 비승인 경고를 추가해 분석 결과와 운영
  실행 결정을 분리했다.

## 다음 단계 후보

- 사람이 topic당 1개/2개 정책과 target 적합성을 검토한다.
- human approval 후 실제 embedding provider 결과와 deterministic 결과를
  비교한다.
- failed article 재시도 정책과 실제 extraction 실행 방식을 별도
  승인한다.
- human approval 후 target 원문을 확보하고 topic title/summary 생성을
  설계한다.
- 필요 시 후속 CLI hardening 작업에서 report path 제한을 검토한다.
- `pytest`, PR merge, rollout, deployment, production verification는
  pending이다.
