# Lightweight article classification MVP

## 작업 목적

LLM이나 embedding 없이 multi-source article metadata에서 기본 category,
language 후보, importance signal을 계산해 향후 topic grouping과 ranking
정책을 검토할 저비용 분석 기반을 만든다.

이번 단계에서는 classification 결과를 DB나 API에 바로 반영하지 않고,
현재 데이터를 read-only로 분석해 rule coverage, source category와의
mismatch, importance score 분포를 확인하는 것을 목표로 했다.

## 기존 문제

- source category 외에 title/summary 내용 기반 category 후보가 없었다.
- language와 중요도 신호를 일관되게 비교할 deterministic helper가 없었다.
- classification을 DB에 저장하기 전에 실제 분포와 mismatch 규모를 확인할
  read-only 도구가 없었다.
- 제품 관점의 발행 시각 분석과 운영 관점의 수집 시각 분석이 분리되어
  있지 않았다.
- 최종 ranking이나 DB 저장 정책을 결정하기 전에 importance signal의 실제
  점수 범위를 확인할 근거가 없었다.

## 변경 내용

- `app/utils/article_classification.py`
  - source category 정규화와 별도 rule category 계산
  - 문자 script 기반 language 감지 및 source registry fallback
  - 구성 요소가 드러나는 importance 후보 점수 계산
- `scripts/analyze_article_classification.py`
  - transaction read-only 기반 classification dry-run
  - 24h/72h/168h/all 및 published/created 기준 지원
  - category/language 분포, mismatch 후보, importance 후보 출력
  - approved fix에 따라 published/created와 window/all 조합별 고정 SQL
    template 선택 및 `window_hours` bind parameter 적용
- classification helper와 집계 동작 단위 테스트 추가
- `get_articles()`의 고정 query 선택, bind parameter, unsupported
  `time_basis` 처리를 확인하는 단위 테스트 추가

Source category는 article의 기본 category로 유지하며 rule category가 이를
덮어쓰지 않는다. Importance score도 최종 ranking이 아니라 topic 처리 전
후보 signal로만 취급한다.

승인된 SQL query construction fix만 적용했다. Keyword/weight 설정 외부화
candidate와 repository 전반 SQL 리팩토링은 적용하지 않았다.

API, DB schema, collector/extractor, frontend, K8s manifest는 변경하지
않았다.

## 구현 상세

### Rule category

- 초기 category 후보는 `tech`, `world`, `business`, `politics`,
  `security`, `ai`, `climate`, `sports`, `unknown`이다.
- title과 summary에 명시적 keyword mapping을 적용한다.
- title match는 summary match보다 높은 가중치를 적용한다.
- 동점인 경우 고정 category priority를 사용해 deterministic 결과를
  반환한다.
- match가 없으면 `unknown`을 반환하며 source category를 덮어쓰지 않는다.

### Language 후보

- 한글, 일본어, 중국어, 아랍어, 키릴 문자, 영문 문자 범위를 기반으로
  lightweight detection을 수행한다.
- 감지할 문자량이 충분하지 않으면 repository의 `RSS_SOURCES` registry에
  정의된 source language를 fallback으로 사용한다.
- 감지와 fallback 모두 불가능하면 `unknown`을 반환한다.
- 첫 read-only DB 쿼리에서 현재 `sources.language` column이 없음을
  확인했기 때문에 schema를 변경하지 않고 source name 기반 registry
  fallback을 선택했다.

### Importance signal

- title keyword match count
- summary keyword match count
- source category points
- article recency points
- breaking/live/update 관련 keyword count
- geopolitical/conflict/election/market/AI/security 관련 high-impact
  keyword count

각 구성 요소를 `importance_signals`에 함께 반환해 점수의 근거를 확인할
수 있게 했다. 이 점수는 최종 ranking이 아니라 후속 topic grouping과
ranking 정책을 검토하기 위한 후보 signal이다.

### Read-only analysis

- DB 연결 후 `set transaction read only`를 실행하고 SELECT만 수행한다.
- 기본 제품 기준은 `coalesce(published_at, created_at)`이다.
- `--time-basis created`를 사용하면 운영 분석 기준인 `created_at`만
  사용한다.
- 24h/72h/168h와 `--all`을 지원한다.
- `published + window`, `published + all`, `created + window`,
  `created + all` 네 가지 고정 SQLAlchemy `text()` template 중 하나를
  선택하며 SQL fragment를 문자열 보간하지 않는다.
- `window_hours`만 bind parameter로 전달하고, 지원하지 않는
  `time_basis`는 `ValueError`로 거부한다.
- source/rule category count, language count, mismatch 후보, top importance
  후보, importance 점수 요약을 JSON으로 출력한다.
- Verification에서는 `--max-examples 0`을 사용해 기사 제목과 후보 상세를
  로그에 남기지 않았다.

## 대안 검토

- **Source category를 rule category로 즉시 덮어쓰기**
  - 분류 결과를 바로 사용할 수 있지만, keyword rule의 false positive와
    coverage를 확인하기 전에 원본 분류 의미를 잃을 수 있어 제외했다.
- **LLM 또는 embedding 기반 classification**
  - 표현이 다양한 기사를 더 정교하게 분류할 수 있지만 비용, 비결정성,
    latency, 운영 복잡도가 증가하며 이번 task 범위를 벗어나 제외했다.
- **외부 language detection dependency 도입**
  - 정교한 감지가 가능하지만 dependency와 모델/패키지 운영 비용이
    증가해, 현재 영어 중심 source 구성에는 문자 script 기반 방식이 더
    적합하다고 판단했다.
- **`sources.language` DB column 추가**
  - DB를 source of truth로 만들 수 있지만 이번 단계는 schema 변경 금지
    범위이므로 repository source registry fallback을 사용했다.
- **classification 결과를 DB에 즉시 저장**
  - 반복 조회에는 유리하지만 rule 안정화 전 backfill과 stale 결과 관리
    문제가 생길 수 있어 read-only dry-run을 먼저 선택했다.
- **Keyword/weight를 설정 파일로 외부화**
  - 향후 tuning과 비개발자 관리에는 유리하다. 현재는 인간 승인 대기
    candidate fix이며 적용되지 않았다.
- **SQL timestamp/where fragment를 동적으로 조립**
  - query 중복을 줄일 수 있지만 함수가 직접 호출될 때 허용 값 경계가
    약해지고 SQL construction을 검토하기 어렵다. Approved Fix 1에서 네
    개의 고정 query template 선택 방식으로 교체했다.
- **Repository 전반 SQL construction 리팩토링**
  - 공통 안전성 개선에는 유리하지만 API, collector, extractor까지 검증
    범위가 확대된다. 이번 task에서는 분석 script의 approved fix만
    적용하고 별도 후속 작업으로 보류했다.

## 선택한 접근과 근거

- deterministic keyword rule을 선택했다. 동일 입력에 동일 결과를 내고
  rule별 영향과 mismatch를 설명하기 쉽다.
- source category와 rule category를 분리했다. Source category는 수집
  provenance를 보존하고, rule category는 후속 분석용 후보로 활용할 수
  있다.
- language detection은 dependency 없는 Unicode script 방식을 선택했다.
  현재 전체 분석에서 `en` 373건, `ko` 3건으로 source 구성이 제한적이기
  때문에 MVP 검증에 충분하다.
- importance score는 단일 점수뿐 아니라 구성 요소를 반환하도록 했다.
  향후 weight 조정 시 어떤 signal이 점수에 영향을 주었는지 추적하기
  위해서다.
- DB write보다 read-only dry-run을 먼저 선택했다. 실제 분포와 mismatch
  규모를 확인한 뒤 schema와 운영 정책을 결정하기 위해서다.
- SQL은 허용된 두 time basis와 window/all 조합을 고정 template으로
  명시했다. 일부 query 중복보다 함수 내부의 허용 경계와 검토 가능성을
  우선하고, 값은 bind parameter로만 전달하기 위해서다.

## 트레이드오프

- Keyword exact-match 방식은 빠르고 설명 가능하지만 동의어, 문맥,
  부정문, 표현 차이를 이해하지 못한다.
- Rule category의 `unknown` 비율이 높아 보수적이지만 false positive를
  줄이는 대신 coverage가 낮다.
- Source registry language fallback은 현재 DB schema와 호환되지만 DB와
  repository 설정이 달라질 경우 불일치 가능성이 있다.
- 문자 script 기반 language detection은 혼합 언어와 짧은 텍스트에서
  제한적이다.
- Recency가 importance score에 포함되므로 실행 시점에 따라 점수가 달라질
  수 있다. 동일 실행 내 계산은 일관되지만 장기 저장 값으로 사용하려면
  기준 시각 정책이 필요하다.
- Keyword와 weight를 코드 상수로 유지하면 규칙을 한 곳에서 읽기 쉽지만
  tuning 빈도가 높아질 경우 설정 외부화가 필요하다.
- 현재 분석 script는 전체 대상을 메모리에 올리므로 article 수가 크게
  증가하면 chunk/batch 처리가 필요하다.
- 네 개의 고정 SQL template은 select/order 구문을 일부 중복하지만,
  동적 SQL fragment 조립을 제거해 query별 동작과 허용 범위를 명확히
  확인할 수 있다.

## 테스트

- Approved Fix 1 적용 후 전체 단위 테스트 21개와 Python compile 검증
  통과
- 고정 query 선택, bound `window_hours`, unsupported `time_basis`의
  `ValueError` 처리를 확인하는 테스트 통과
- CLI help와 `git diff --check` 통과
- 신규 untracked 파일 whitespace 검사 통과
- Approved Fix 1 적용 후 published 기준 24h/72h/168h/all 및 created 기준
  24h read-only 분석 재실행 통과
- 초기 sandbox DB 시도는 DNS 제한으로 연결 전에 실패했다.
- 첫 네트워크 쿼리에서 현재 `sources.language` column 부재를 확인해,
  schema 변경 없이 repository source registry fallback으로 수정했다.
- security grep에서 실제 credential 값은 발견되지 않았다.
- `pytest`는 `.venv/bin/pytest`가 설치되어 있지 않아 pending이다.
- 실제 명령과 상세 결과는
  `docs/verification/feature-lightweight-article-classification.md` 참조

## 운영 반영

- 운영 반영 없음.
- DB migration, Supabase SQL, article/source row write를 수행하지 않았다.
- K8s manifest 변경, apply, rollout을 수행하지 않았다.
- production API curl과 production verification을 수행하지 않았다.
- PR merge, git push, git merge를 수행하지 않았다.
- human-provided production verification log는 없다.

## README 업데이트 판단

README는 변경하지 않았다.

이번 변경은 내부 classification helper와 수동 read-only 분석 script를
추가하는 작업이며 기존 FastAPI 실행 방법, 공개 API, K3s 운영 절차를
변경하지 않는다. 향후 classification이 정식 batch job, DB schema, 공개
API로 확장되면 README 또는 Runbook에 사용 방법과 운영 정책을 추가하는
것이 적절하다.

## 확인 결과

- published 기준:
  - 24h 166건: mismatch 50건, importance 평균 5.2
  - 72h 253건: mismatch 70건, importance 평균 4.68
  - 168h 347건: mismatch 102건, importance 평균 4.06
  - 전체 376건: mismatch 112건, importance 평균 3.99
- created 기준 24h 293건: mismatch 76건, importance 평균 4.81
- 전체 rule category는 `unknown` 224건으로 보수적인 규칙 특성이
  확인됐다.
- 전체 language 후보는 `en` 373건, `ko` 3건이었다.
- 전체 source category는 `tech` 208건, `world` 165건, `ai` 1건,
  `unknown` 2건이었다.
- 전체 importance 후보 점수는 최대 30, 평균 3.99였다.
- 승인된 SQL query construction fix를 적용해 `get_articles()`의 동적 SQL
  fragment interpolation을 네 개의 고정 query template 선택 방식으로
  변경했다.
- Approved Fix 1 적용 후 21개 단위 테스트와 다섯 가지 read-only
  dry-run이 통과했고, 전체 category/language 분포와 mismatch 수는
  유지됐다.
- 시간 window별 기사 수와 importance 평균의 일부 변화는 recency와 실행
  시각에 따른 것이며 classification rule 변경 결과가 아니다.
- Keyword와 importance weight 설정 외부화는 승인 대기 candidate이며
  적용되지 않았다.

## 이번 단계의 의미

분류 결과를 DB나 API에 즉시 반영하지 않고 실제 데이터 분포를 먼저
확인했다. Source category, rule category, language, importance를 독립된
후보 signal로 분리해 이후 topic grouping/ranking 정책을 단계적으로
검토할 수 있게 했다.

또한 현재 DB schema와 repository source registry의 차이를 실제 read-only
분석 과정에서 확인하고, schema 변경 없이 동작하는 fallback을 적용해 MVP
범위를 유지했다.

Approved Fix 1에서는 동적 SQL fragment 조립을 고정 query template과 bind
parameter로 교체해, read-only 분석 기능을 유지하면서 query construction의
허용 범위와 검토 가능성을 높였다.

## 포트폴리오용 요약

Multi-source RSS 기사 metadata를 대상으로 LLM이나 embedding 없이
동작하는 deterministic lightweight classification 시스템을 설계하고
구현했다. Source category를 보존하면서 title/summary keyword 기반 rule
category, Unicode script 기반 language 후보, 설명 가능한 importance
signal을 별도로 계산했다.

읽기 전용 분석 도구로 published/created 기준과 24h/72h/168h/all window를
지원하고, 실제 전체 376건에서 source/rule mismatch 112건, rule
`unknown` 224건, language `en` 373건·`ko` 3건, importance 최대 30·평균
3.99를 확인했다. Approved Fix 1을 통해 분석 query를 네 개의 고정
SQLAlchemy template과 bind parameter 방식으로 정리하고, 21개 단위
테스트와 read-only dry-run으로 기존 분석 의미가 유지됨을 확인했다. DB
schema와 운영 시스템을 변경하기 전에 실제 데이터로 rule coverage와
signal 분포를 검증하는 단계적 접근을 적용했다.

## 다음 단계 후보

- mismatch와 top importance 예시를 사람이 검토해 keyword/weight를 조정한다.
- `rule_category`, `detected_language`, `importance_score`,
  `importance_signals`, `classified_at` DB 반영 필요성을 검토한다.
- DB 반영 시 nullable column과 backfill, category/language index를 별도
  migration 차수에서 검토한다.
- article 수가 증가하면 chunk/batch 분석을 검토한다.
- human operator가 keyword/weight 설정 외부화 candidate fix의 승인 여부를
  결정한다.
- repository의 동적 SQL fragment 사용처를 별도 task에서 조사하고,
  고정 template 또는 allowlist 적용 필요성을 검토한다.
- production verification은 실제 rollout과 human-provided curl 로그가
  제공될 때까지 pending으로 유지한다.
