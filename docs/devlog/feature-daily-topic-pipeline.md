# 수동 Daily Topic Pipeline MVP

## 작업 목적

최근 24시간 동안 수집된 기사를 기준으로 topic grouping, 필요한 원문 추출,
topic summary 생성, 기존 `/topics` API에서 조회할 수 있는 저장 결과까지 하나의
수동 실행 흐름으로 연결하는 것이 목적이었다.

자동화에 앞서 사람이 결과를 검토하고 제한된 범위에서 실행할 수 있도록 기본
동작은 dry-run으로 유지했다. 실제 raw extraction과 DB write는 명시적인
`--execute`에서만 수행하도록 경계를 설정했다.

## 기존 문제

- Topic grouping, representative 선정, raw extraction target 분석, summary
  생성, 저장 계획이 각각 분리된 스크립트로 존재했다.
- 하루 단위 topic summary를 만들려면 여러 명령과 중간 결과를 사람이 직접
  연결해야 했다.
- `--max-topics`로 어떤 topic이 선택되는지 우선순위가 명확하지 않았다.
- 기존 report는 article ID와 similarity 위주라 grouping 품질을 사람이
  판단하기 어려웠다.
- 요약 대상 밖 후보가 사라져, threshold와 선택 정책을 함께 검토하기 어려웠다.
- 운영 자동화 전에 provider 비용, raw extraction 범위, DB write 범위를 제한한
  수동 검증 경로가 필요했다.

## 변경 내용

- `scripts/run_daily_topic_pipeline.py`를 추가해 기존 분석/추출/요약/저장 모듈을
  하나의 수동 pipeline으로 연결했다.
- 최근 24시간 기사만 입력으로 사용하고 embedding vector와 topic candidate
  중간 결과는 메모리에서만 처리한다.
- selected topic을 다음 순서로 정렬한 후 `--max-topics`를 적용한다.
  1. article count 내림차순
  2. source count 내림차순
  3. 평균 similarity 내림차순
  4. 최신 기사 시각 내림차순
  5. topic candidate ID 오름차순
- `--max-reference-topics`를 추가해 요약 대상 밖 후보를 report-only 정보로
  남겼다.
- report에 selected/reference 기사 metadata와 generated summary를 추가했다.
- 실제 기사 URL을 report에 표시하도록 기존 read-only 기사 조회에 `a.url`을
  포함했다.
- RUNBOOK에 0.70/0.72 threshold 비교와 기존 raw extractor CronJob suspend
  수동 절차를 기록했다.

## 구현 상세

Pipeline 흐름은 다음과 같다.

```text
최근 24시간 기사 조회
→ embedding 생성 및 메모리 기반 grouping
→ representative/supporting article 선정
→ topic 우선순위 정렬
→ selected topics / reference candidates 분리
→ selected topics의 raw extraction target 계산
→ raw_text 기반 summary input 생성
→ topics/topic_articles save plan 생성
→ --execute에서만 extraction 및 DB write
```

기본 dry-run에서도 grouping, summary, save plan을 확인할 수 있지만 extraction과
DB write는 수행하지 않는다. Provider 호출도 별도 provider flag와 API key가
있어야 가능하다.

Reference candidates는 사람이 grouping 후보를 검토하기 위한 공개 가능한
metadata만 가진다. 이 후보들은 raw extraction, summary provider, save plan,
DB write 경로에 전달되지 않는다.

Report에는 role, article ID, similarity, source, published time, title, URL,
summary 결과를 표시한다. Raw text는 public result, markdown report, 기존
`/topics` API에 노출하지 않는다.

## 대안 검토

- **Embedding과 topic candidate를 DB에 저장**
  - 3일/7일 trend, 재처리, 검색에는 유리하지만 하루 약 300개 이하 기사 대상
    MVP에는 schema와 운영 복잡도가 커진다.
  - `article_embeddings`, `topic_candidates`,
    `topic_candidate_articles` 테이블 추가는 보류했다.
- **각 기존 스크립트를 운영자가 순서대로 실행**
  - 코드 변경은 적지만 실행 경계와 결과 연결이 불명확하고 실수 가능성이 높다.
- **즉시 CronJob 자동화**
  - 아직 threshold와 provider summary 품질을 확인하는 단계이므로 자동 실행은
    이르다고 판단했다.
- **Reference candidates도 요약하거나 저장**
  - 검토 범위를 넓힐 수 있지만 provider 비용, raw extraction, DB write 범위가
    `--max-topics`를 넘어가므로 제외했다.
- **gpt-5-mini 비교 및 fallback/factuality gate 추가**
  - MVP 검증 범위를 넘으므로 후속 품질 개선 작업으로 보류했다.

## 선택한 접근과 근거

기존 검증된 유틸과 스크립트를 재사용하는 얇은 orchestration script를
선택했다. 새로운 저장 구조 없이 기존 `topics`, `topic_articles`와 `/topics`
read path를 그대로 활용할 수 있고, 각 단계의 기존 단위 테스트와 안전장치를
재사용할 수 있기 때문이다.

24시간 단위 처리량에서는 embedding과 topic candidate를 메모리에서 처리하는
방식이 충분하다. 중간 결과 저장보다 기본 dry-run, 명시적 provider flag,
`--execute` gate를 통해 비용과 write 범위를 통제하는 것을 우선했다.

0.70과 0.72를 실제 provider dry-run으로 비교한 결과, 0.70은 “오늘의 주요
이슈”처럼 넓은 묶음에 적합했고 0.72는 “같은 사건 기사 묶음”에 더 가까운
보수적 결과를 보였다.

## 트레이드오프

- 메모리 기반 처리로 구조는 단순하지만 장기 trend 분석과 반복 처리 최적화에는
  적합하지 않다.
- `--max-topics`로 provider 비용과 DB write 범위를 제한하는 대신 일부 의미
  있는 후보는 저장되지 않는다. 이를 reference report로 보완했다.
- Reference candidates에 singleton이 포함될 수 있어 report noise가 생길 수
  있다.
- Raw text가 없는 selected topic은 `insufficient_raw_text`로 남아 실제 저장
  가능한 summary 수가 줄어들 수 있다.
- Provider summary에서 일부 한국어 품질 문제와 혼합 언어 표현이 관찰됐다.
  Frontend 노출 전 품질 검토가 필요하다.
- 수동 실행은 안전하지만 정기 운영에는 사람 개입이 필요하다.

## 테스트

Verification 문서에 기록된 실제 로컬 검증 결과:

- Python compile: 통과
- Final focused pipeline tests: 8개 통과
- Save topic summary tests: 8개 통과
- Pipeline/analyze/save combined focused tests: 25개 통과
- Full unittest discovery: 116개 통과
- `git diff --check`: 통과
- DB migration, K8s, GitHub Actions, frontend, Dockerfile, API router scope
  diff: 변경 없음

초기 approved-fix focused test에서는 report URL 누락으로 1개 테스트가
실패했다. 기존 read-only article query projection에 `a.url`을 추가한 후
focused 및 전체 테스트가 통과했다.

## 운영 반영

Human-approved provider dry-run이 수행됐다.

- Threshold 0.70: 기사 115개, topic candidate 105개, selected 3개,
  reference 10개
- Threshold 0.72: 기사 115개, topic candidate 107개, selected 3개,
  reference 10개

Human-approved threshold 0.70 `--execute`가 1회 수행됐다.

- 기사 114개, topic candidate 104개, selected 3개
- Raw extraction 성공/실패: 3/2
- Summary 상태: ready 2개, `insufficient_raw_text` 1개
- 명시적인 execute 경로에서 실제 DB write 수행

Human-provided production `/topics` 조회 로그에서 새 `openai` /
`gpt-5-nano` summary가 조회됐고, topic detail에 raw text가 노출되지 않았으며
존재하지 않는 topic ID는 HTTP 404를 반환했다.

Supabase SQL과 migration은 실행하지 않았다. Kubectl 명령, 배포, K3s rollout,
git push, git merge, PR merge 완료 로그는 없다. 기존 `news-raw-extractor`
CronJob suspend 여부는 human decision pending이다.

## README 업데이트 판단

README 업데이트는 필요하지 않다고 판단했다.

이번 변경은 사용자용 빠른 시작보다 운영자용 수동 pipeline과 검증 절차에
가깝다. Threshold 비교 명령, provider 호출 주의사항, raw extractor CronJob
suspend 절차는 `docs/RUNBOOK.md`에 기록하는 편이 현재 문서 구조와 책임에
맞는다.

## 확인 결과

- 최근 24시간 기사 기준 수동 pipeline이 하나의 명령 형태로 연결됐다.
- 기본 dry-run과 명시적 `--execute` write 경계가 유지된다.
- Selected topic 우선순위와 `--max-topics` 적용 방식이 명확해졌다.
- Reference candidates는 report에 남지만 extraction, summary, save 대상이
  아니다.
- Report와 production topic detail에서 raw text가 노출되지 않는다.
- Provider 기반 summary가 기존 `/topics` API를 통해 조회됨을 human-provided
  production logs로 확인했다.
- DB schema, API route/response shape, K8s manifest, CronJob 자동화, frontend는
  변경하지 않았다.
- PR merge, 배포, K3s rollout 완료 여부는 pending이다.

## 이번 단계의 의미

분리되어 있던 NewsLab의 기사 분석, 원문 추출, 요약, 저장 흐름이 처음으로
제한된 write 경계를 가진 하루 단위 운영 pipeline으로 연결됐다.

단순히 요약 스크립트를 추가한 것이 아니라, 실제 provider 결과를 threshold별로
비교하고, human-approved execute 후 기존 production read API에서 저장 결과와
raw text 비노출까지 확인했다. 다음 자동화 작업에서 재사용할 수 있는 실행
계약과 검증 기준을 마련한 단계다.

## 포트폴리오용 요약

최근 24시간 뉴스 기사를 대상으로 embedding 기반 topic grouping,
representative article 선정, 선택적 raw extraction, LLM summary 생성,
PostgreSQL 저장을 하나의 수동 pipeline으로 통합했다. 기본 dry-run과 명시적
execute gate로 provider 비용과 DB write를 통제하고, 주요 topic 정렬 및
reference-only 후보 분리를 통해 사람이 결과를 검토할 수 있게 했다.

0.70/0.72 similarity threshold를 실제 provider 결과로 비교하고,
human-approved execute 후 production `/topics` API에서 OpenAI summary 조회와
raw text 비노출을 검증했다. 중간 embedding/topic candidate 테이블을 추가하지
않고 기존 시스템을 재사용해 작은 변경으로 end-to-end 흐름을 완성했다.

## 다음 단계 후보

- Daily topic pipeline CronJob 자동화
- 기존 `news-raw-extractor` CronJob suspend 여부 결정
- `/topics` 기반 frontend 연결 및 UI 품질 검토
- Provider summary의 한국어 품질 개선과 factuality 검토
- `insufficient_raw_text` 비율과 raw extraction 실패 원인 분석
- Reference candidate singleton noise 감소 정책 검토
- 3일/7일 trend가 필요해질 때 embedding/topic candidate 저장 구조 재검토
