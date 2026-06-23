# 3일 Topic pipeline·저장·API·CronJob 구축

## 작업 목적

Daily Topic의 24시간 결과와 별개로, 최근 72시간 기사와 이미 저장된 article
embedding을 사용해 3일 주요 이슈를 생성·저장·조회하는 backend 경로를 만든다.

## 기존 문제

- Daily Topic 결과만으로는 72시간 흐름을 다시 clustering할 수 없다.
- 기존 Topic table은 1일 결과 계약이므로 3일 결과와 실행 이력을 안전하게
  분리할 저장 구조가 없었다.
- 동일 window 재실행 중 실패하면 기존 성공 결과를 보존하는 원자 교체 계약과
  독립 API, CronJob이 필요했다.

## 변경 내용

- `ThreeDayPipelineContext`가 서울 기준의 명시적인 72시간 window를 한 번
  결정하고 모든 단계에 전달한다.
- 기존 `article_embeddings` 중 metadata와 source hash가 일치하는 vector만
  재사용하며 누락 기사는 제외·집계한다.
- 기간 독립적인 clustering/기사 선정 helper를 Daily와 공유하고 3일 설정은
  별도로 유지한다.
- Summary 근거 기사만 원문 확보와 72시간 전용 prompt 입력으로 사용하며 Topic별
  실패를 격리한다.
- 전용 migration/repository가 run 이력과 활성 Topic set을 분리하고 동일 window
  결과를 transaction 안에서 교체한다.
- archive/home/detail API와 `05:00 Asia/Seoul` CronJob manifest를 추가했다.
- README, Architecture, Runbook과 설계 문서에 운영 수동 절차와 선택 근거를
  반영했다.

## 테스트

실제 실행 결과와 실패 이력은
`docs/verification/feature-three-day-topic-pipeline.md`에 기록한다. 집중 테스트,
Daily 회귀, 전체 pytest/unittest, compileall과 whitespace 검증을 대상으로 한다.

- 3일 pipeline 집중: 20 passed
- 3일 API: 6 passed
- 3일 CronJob manifest: 3 passed
- Daily pipeline/CronJob 회귀: 23 passed
- 전체 pytest: 261 passed
- 전체 unittest: 261 passed
- compileall과 `git diff --check`: passed

## 운영 반영

Agent는 migration, Kubernetes apply, 수동 Job과 production API 확인을 수행하지
않았다. Human operator는 migration schema 확인 후 manifest client/server
dry-run, apply, 수동 Job log와 API 순서로 검증해야 한다.

## 확인 결과

허용된 로컬 검증은 모두 통과했다. 세부 command, 실행 시간과 의도된 stderr는
Verification 문서가 source of truth다. 운영 검증 log가 제공되기 전에는 배포
또는 production 완료로 보지 않는다.

## 이번 단계의 의미

Daily 결과를 재집계하지 않고 기사 embedding에서 직접 72시간 이슈를 만드는
독립 경로를 확보했다. 실행 감사 이력은 누적하되 활성 결과만 교체해 재현성과
가용성을 함께 유지한다.

## 다음 단계

- Human operator의 migration 및 K3s 반영
- 실제 72시간 데이터에서 Topic 품질, 누락 embedding 비율과 실행 시간을 관찰
- 관찰 결과에 따른 3일 전용 threshold와 상한 조정은 별도 task로 수행
