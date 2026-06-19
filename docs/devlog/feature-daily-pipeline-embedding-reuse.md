# 저장된 article embedding을 daily topic pipeline에 연결

## 작업 목적

Daily topic pipeline이 동일 기사 입력의 embedding을 매번 다시 생성하지 않고
Supabase `article_embeddings`에 저장된 vector를 재사용하도록 연결한다.

이번 단계에서는 기존 실행 단위와 CronJob schedule을 유지한다. Embedding 단계를
별도 pipeline으로 분리할지는 실제 실행 시간, reuse 비율과 실패 양상을 확인한
뒤 판단한다.

## 기존 문제

기존 pipeline은 후보 기사 전체를 실행마다 provider에 전달한 뒤 memory-only
vector를 clustering에 사용했다. 같은 제목·RSS 요약과 model 계약이어도 provider
호출이 반복됐고, 개별 article embedding 실패가 전체 embedding batch와 pipeline
실패로 이어질 수 있었다.

저장 기능은 독립 batch에서 사용할 수 있었지만 daily topic pipeline은 이를
사용하지 않았다. 따라서 저장된 vector와 source hash가 있어도 scheduled 실행의
비용과 실패 범위를 줄이지 못했다.

## 변경 내용

- 공통 article embedding storage 모듈이 저장 pgvector를 clustering tuple로
  복원하도록 확장
- Daily pipeline에 기사별 embedding acquisition 단계 연결
- created/updated/reused/failed 집계와 안전한 실패 기록 추가
- 실패 article 제외 후 정상 metadata/vector 순서를 유지
- 정상 vector 2건 미만 clustering/topic save gate 추가
- pipeline 결과와 report에 후보·embedding·clustering·topic·elapsed 통계 추가
- architecture와 CronJob 수동 검증 runbook 갱신
- CronJob command, schedule, manifest와 기존 topic 저장 계약 유지

## 구현 상세

CronJob은 기존과 동일하게 OpenAI `text-embedding-3-small`, 1536 dimension,
`title_summary` source type을 사용한다. Pipeline은 공통 storage 함수에 article과
provider를 전달한다.

같은 hash는 DB의 `embedding::text`를 float tuple로 변환해 `reused`로 반환한다.
Row가 없거나 hash가 변경되면 provider를 호출하고 atomic upsert 결과를
`created` 또는 `updated`로 집계한다.

각 article은 독립적으로 처리한다. 실패한 article은 ID와 200자 이하의 정규화된
오류 요약만 남기고 clustering 입력에서 제외한다. 정상 article과 vector는 같은
loop에서 함께 append해 순서를 보존한다.

기존 `group_articles()`, similarity threshold, representative selection,
summary와 topic save 코드는 변경하지 않았다. 정상 vector가 2건보다 적으면
이 단계들을 빈 결과로 통과시키고 topic save executor를 호출하지 않는다.

Pipeline JSON/report의 기존 field는 유지하고 다음 통계를 추가했다.

- `candidate_articles`
- `embedding_created`
- `embedding_updated`
- `embedding_reused`
- `embedding_failed`
- `clustering_input_count`
- `topic_count`
- `pipeline_elapsed_seconds`

Dry-run에서 저장 row가 없거나 hash가 변경된 경우 provider vector는 memory에서
생성하지만 DB에는 저장하지 않는다. Execute mode에서는 article별 transaction으로
atomic upsert를 수행한다.

## 대안 검토

- Pipeline 내부에 별도 저장 SQL 구현: 계약 중복 위험 때문에 제외했다.
- 후보 전체 provider batch 유지: 빠르지만 article별 reuse와 실패 격리가 어려워
  저장 모듈 기반 개별 acquisition을 선택했다.
- Pipeline 단계 분리: 실행 시간과 실패 분포 evidence가 없어 기존 실행 단위를
  유지했다.
- 전체 실행을 하나의 DB transaction으로 처리: article 하나의 실패가 전체
  embedding 저장을 rollback할 수 있어 제외했다.
- Retry framework, queue와 distributed lock: 현재 task 범위를 넘어 제외했다.
- Clustering 알고리즘 변경: embedding 재사용 연결과 무관하므로 유지했다.

## 선택한 접근과 근거

기존 pipeline 함수에 injectable `embedding_acquirer` 경계를 추가했다. Unit
test에서는 DB/API 없이 상태별 fake 결과를 주입할 수 있고, 운영 경로에서는
기존 engine과 provider를 사용해 공통 storage 함수에 연결된다.

Hash 동일 fast path는 provider를 호출하지 않는다. 기사별 transaction과 실패
격리는 일부 provider/DB 문제가 정상 기사까지 막지 않도록 한다. Metadata와
vector를 동시에 필터링해 clustering index mapping을 보존한다.

기존 함수 구조를 대규모로 재편하지 않고 `embedding_acquirer` 경계와
`acquire_pipeline_embeddings()` 책임만 추가했다. 후보 조회, embedding 확보,
clustering, summary와 topic 저장 단계를 구분하면서 기존 caller와 test fixture를
최대한 유지하기 위한 선택이다.

## 트레이드오프

- 기사별 provider 호출은 batch API보다 느릴 수 있지만 저장 reuse와 부분 실패
  격리를 우선했다.
- Atomic upsert는 DB race를 막지만 동시 worker의 provider 중복 호출까지 막지는
  않는다.
- 정상 vector 1건은 clustering하지 않으므로 singleton topic은 생성되지 않는다.
- Dry-run provider 모드는 신규/변경 vector를 memory에서 생성하지만 저장하지
  않는다.
- Pipeline 분리를 미뤄 embedding과 summary 실패 시 전체 실행 재시도 비용은
  남아 있다.
- Article별 DB connection/transaction은 실패 격리에 유리하지만 후보 수가
  많으면 connection overhead가 발생할 수 있다.
- 오류 요약은 200자로 제한하므로 상세 provider 진단은 원본 exception/외부
  observability에서 별도로 확인해야 한다.

## 테스트

- 공통 storage/provider 20 tests 통과
- Pipeline/storage/CronJob 관련 27 tests 통과
- Stored reuse provider 미호출, 신규 생성, failure/dimension 제외, 순서 유지,
  통계와 최소 입력 gate 확인
- 전체 142 tests와 compile/diff check 통과
- Branch, 변경 파일과 K3s/DB migration/Public API/dependency 금지 영역 diff
  확인 통과
- 실제 수동 pipeline 2회 실행: 사람이 수행 필요

초기 storage test 실행에서는 변경된 select projection을 fake connection이
인식하지 못해 2건이 실패했다. Fake query 판정을 현재 SQL에 맞게 수정한 뒤 관련
20 tests가 통과했다. 이 실패와 재실행 결과는 verification에 기록했다.

## 운영 반영

미수행. CronJob command, schedule과 K3s manifest는 변경하지 않았다.
Production DB write와 provider 호출이 발생하는 수동 pipeline 실행은 사람이
수행해야 한다.

사람이 기존 CronJob과 같은 option으로 pipeline을 두 번 실행하고 각 결과의
다음 값을 기록해야 한다.

```text
candidate_articles
embedding_created
embedding_updated
embedding_reused
embedding_failed
clustering_input_count
topic_count
pipeline_elapsed_seconds
```

첫 실행에서 topic 생성 결과를 확인하고, 동일 조건 두 번째 실행에서
`embedding_reused` 증가와 신규 provider 대상 감소를 확인해야 한다. Scheduled
daily 실행 관찰도 운영 반영 후 pending이다.

## README 업데이트 판단

README는 변경하지 않는다. Public API, 설치 절차와 사용자 기능 변경이 없고,
내부 pipeline 흐름과 운영 확인 절차는 architecture/runbook이 적절한 위치다.

## 확인 결과

로컬 unit test에서 저장 vector reuse 시 provider 미호출, 기사별 상태 집계,
실패 article 제외 후 정상 처리 지속, metadata/vector 순서 유지와 topic save
skip을 확인했다.

운영 환경의 topic 생성 결과, 동일 조건 두 번째 실행의 reuse 증가와 실제 elapsed
seconds는 아직 확인하지 않았다.

Approved Fixes 문서에는 승인·적용 항목이 없다. Review 파일은 verification
통과나 수정 승인 근거로 사용하지 않았다.

## 이번 단계의 의미

Article embedding 저장 기능을 독립 batch에 머물지 않고 실제 daily topic
clustering 입력에 연결했다. 동일 입력 반복 비용을 줄이고 일부 article 실패를
pipeline 전체 실패와 분리할 기반을 마련했다.

동시에 실행 단위를 분리하지 않고 통계부터 추가해, 향후 분리 여부를 추측이 아닌
실제 elapsed time, provider 호출 비중과 실패 정책 차이로 판단할 수 있게 했다.

## 포트폴리오용 요약

PostgreSQL pgvector에 저장된 기사 embedding을 daily clustering pipeline에
연결하고, content hash 기반 reuse, atomic upsert, article-level failure
isolation과 실행 통계를 구현했다. 기존 clustering/topic save 계약을 유지하면서
metadata-vector 정합성과 최소 입력 safety gate를 검증했으며 전체 142개 회귀
테스트를 통과했다.

## 다음 단계 후보

- 사람이 pipeline을 동일 조건으로 2회 실행해 topic 생성과 reuse 증가 확인
- Scheduled daily 실행의 elapsed time과 provider 호출 감소 관찰
- 별도 test PostgreSQL에서 pipeline storage 통합 검증
- Embedding 단계 실행 시간과 API 호출 비중 측정
- Embedding과 summary의 실패·재시도 정책 차이 분석
- 전체 pipeline 재실행 비용과 단계별 주기를 근거로 분리 여부 결정
- Human final diff 확인 후 push와 PR 진행
