# 3일 Topic pipeline·저장·API·CronJob 구축

## 작업 내용

- 최근 72시간 기사와 기존 article embedding을 직접 재클러스터링하는 3일 Topic
  pipeline을 추가한다.
- 전용 저장 구조, archive/home/detail API와 K3s CronJob manifest를 추가한다.

## 주요 변경 사항

- 서울 기준의 재현 가능한 `[window_start, window_end)` context
- embedding provider 호출 없는 저장 vector 재사용과 누락 통계
- Daily와 공유하는 기간 독립적 선정 helper 및 독립적인 3일 설정
- Topic별 원문/Summary 실패 격리와 `three-day-flow-v1` prompt
- run 이력 보존, advisory lock과 transaction 기반 동일 window 원자 교체
- `three_day_topics`, `three_day_topic_articles`, `three_day_topic_runs`
- `/three-day-topics`, `/three-day-topics/home`,
  `/three-day-topics/{topic_id}`
- `05:00 Asia/Seoul`, `concurrencyPolicy: Forbid` 전용 CronJob
- README, Architecture, Runbook과 설계·운영 절차 정리

## 테스트

최종 command와 결과는
`docs/verification/feature-three-day-topic-pipeline.md`를 source of truth로
사용한다.

- 3일 집중/API/manifest: 20 + 6 + 3 passed
- Daily 회귀: 23 passed
- 전체 pytest: 261 passed
- 전체 unittest: 261 passed
- compileall, `git diff --check`: passed

## 확인 결과

- 기존 Daily Topic 외부 CLI와 CronJob manifest는 변경하지 않았다.
- 기존 `/topics` API와 `topics`, `topic_articles` 저장 계약은 유지한다.
- 허용된 로컬 회귀 검증은 모두 통과했다.
- Production migration, Kubernetes apply와 수동 Job은 수행하지 않았다.

## 비고

- 실제 migration과 K3s 반영은 human-controlled operation이다.
- 7일 Topic과 frontend 변경은 포함하지 않는다.
