# 저장된 article embedding을 daily topic pipeline에 연결

## 작업 내용

- Daily topic pipeline의 OpenAI embedding 단계를 기존
  `article_embeddings` 저장·재사용 흐름에 연결했다.
- 저장된 pgvector를 기존 clustering 입력 형식으로 복원하고, 신규 또는 변경된
  입력만 provider 호출과 atomic upsert 대상으로 처리한다.
- 기사별 embedding 실패 격리, clustering 최소 입력 gate와 실행 통계를
  추가했다.
- Pipeline architecture와 CronJob 수동 검증 runbook을 갱신했다.

## 주요 변경 사항

- 기존 `title_summary` normalization/hash와 atomic upsert 공통 모듈 재사용
- 같은 hash의 저장 vector는 provider 호출 없이 clustering에 전달
- 신규/변경 입력은 생성 후 저장하고 `created`/`updated`로 집계
- 실패 또는 dimension 불일치 article만 제외하고 정상 article 처리는 지속
- 실패 결과에는 article ID와 길이를 제한한 안전한 오류 요약만 포함
- 정상 vector 2건 미만이면 clustering, summary와 topic save 건너뜀
- metadata/vector 순서 유지
- 기존 JSON/report 필드를 제거하지 않고 embedding 및 pipeline 통계 추가
- CronJob command, schedule, manifest와 clustering 알고리즘은 변경하지 않음
- Approved Fixes에 적용 승인된 항목 없음

## 추가/변경된 API

Public API 변경 없음.

Pipeline JSON/report의 기존 필드는 유지하며 `analysis`에 다음 필드를 추가했다.

- `candidate_articles`
- `embedding_created`
- `embedding_updated`
- `embedding_reused`
- `embedding_failed`
- `clustering_input_count`
- `topic_count`
- `pipeline_elapsed_seconds`

## DB 변경 사항

Schema와 migration 변경 없음. 기존 `articles`, `article_embeddings`, `topics`,
`topic_articles`를 사용한다.

기존 embedding provider, model, 1536 dimension, `title_summary` source type과
unique constraint도 변경하지 않았다.

## README 영향

README 변경 없음. Public API, 설치 절차와 사용자 기능은 바뀌지 않았으며 내부
pipeline/운영 절차는 architecture와 CronJob runbook에 기록했다.

## 테스트

- 공통 embedding 관련 20 tests 통과
- Pipeline/storage/CronJob 관련 27 tests 통과
- 전체 142 tests 통과
- `python -m compileall app scripts tests`: 통과
- `git diff --check`: 통과
- Branch, 변경 파일과 금지 영역 diff 확인: 통과
- 실제 production pipeline 수동 실행: 사람이 수행 필요로 미실행

## 확인 결과

- Stored vector 복원과 동일 hash에서 provider 미호출 `reused`를 확인
- `created`, `updated`, `reused`, `failed` 상태별 집계를 확인
- 실패 article 제외 후 metadata/vector 순서 유지 확인
- Provider 및 dimension 실패 article을 제외하고 정상 article 처리 지속 확인
- 정상 vector 2건 미만 시 topic save 미호출 확인
- 기존 clustering threshold, representative selection, summary/topic save와
  CronJob command/schedule 회귀 확인
- 실제 topic 생성, 동일 조건 두 번째 실행의 reuse 증가와 실행 시간은 아직
  확인하지 않음

## 비고

- 사람이 안전한 credential을 주입한 뒤 production pipeline을 같은 조건으로
  두 번 실행하고 다음 값을 verification에 기록해야 함:
  `candidate_articles`, `embedding_created`, `embedding_updated`,
  `embedding_reused`, `embedding_failed`, `clustering_input_count`,
  `topic_count`, `pipeline_elapsed_seconds`
- Production pipeline 실행, Supabase SQL, kubectl, K3s rollout, deployment,
  git push/merge와 PR merge는 수행하지 않음
- CronJob/K3s manifest, DB schema/migration, Public API, frontend와 dependency는
  수정하지 않음
- ANN index, queue, retry framework, distributed lock과 병렬 처리는 범위 제외
