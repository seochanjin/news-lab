# Task: NewsLab 정기 수집·분석 중지 준비

## Goal

뉴스랩의 정기 수집·분석을 중지하는 설정을 main 대상 PR로 준비한다.
공용 노드 경보와 GameProbe 운영은 유지하고, 운영 적용과 PR 병합은 사람이 한다.

## Scope

- CronJob 4개에 `spec.suspend: true`를 명시한다.
- `PipelineScheduleDelayed`, `PipelineScheduledJobFailed` 규칙을 제거한다.
- 같은 PrometheusRule의 `NewsLabNodeNotReady`는 식·조건·라벨을 그대로 유지한다.
- 적용 순서, 확인 방법, 재개 시 주의점을 verification 문서에 기록한다.

## Do not change

- API·웹·Redis·exporter Deployment와 이미지 버전
- CronJob schedule, timeZone, command, retry, resource, Secret 참조
- 공용 K3s·Argo CD·Grafana·Prometheus·Alertmanager와 알림 수신 경로
- API 키·Secret·DB·DNS·GameProbe·프론트 저장소
- 기존 `docs/reports/baseline-2026-08.md` 미추적 파일
- 운영 리소스 적용·변경 및 PR 병합

## Expected files

- `k8s/monitoring/rules/news-lab-pipeline-alerts.yaml`
- `k8s/news-rss-collector-cronjob.yaml`
- `k8s/news-daily-topic-pipeline-cronjob.yaml`
- `k8s/news-three-day-topic-pipeline-cronjob.yaml`
- `k8s/news-weekly-topic-pipeline-cronjob.yaml`
- `docs/tasks/codex-suspend-newslab-pipelines.md`
- `docs/verification/codex-suspend-newslab-pipelines.md`

## DB changes

없음.

## API changes

없음. 기존 조회 API와 웹은 계속 실행된다.

## Test commands

- `git diff --check`
- Python 표준 라이브러리와 macOS Ruby YAML parser를 사용한 읽기 전용 비교:
  YAML 5개 파싱, CronJob의 suspend 이외 변경 없음, 경보 2개만 제거,
  공용 노드 경보 전체 보존을 base commit과 비교한다.
  실제 실행 코드는 verification 문서에 기록한다.
- `git diff --stat`, `git diff --name-only`, `git status --short --branch`
- GitHub PR 대상·변경 파일·head SHA 읽기 전용 확인

## Acceptance criteria

- [x] CronJob 4개의 suspend가 boolean true이며 나머지 배포 설정이 동일하다.
- [x] 수집·분석 경보 2개만 제거되고 공용 노드 경보가 동일하다.
- [x] YAML 파싱과 차이 검증이 통과한다.
- [x] 병합 후 사람의 적용 순서·검증·복구 절차가 기록되어 있다.
- [x] main 대상 PR로 검토할 변경과 검증 기록을 준비하고, 병합·운영 적용은 수행하지 않는다.

## Notes

- 2026-11-01 사용자가 코드 변경 및 main 대상 PR 생성을 요청했다.
  이 범위의 브랜치 생성·커밋·push·PR 생성은 요청에 포함되며 병합은 포함되지 않는다.
- 기존 main task 포인터가 가리키는 기능 작업은 이번 작업이 아니다.
  해당 문서나 완료 이력은 변경하지 않는다.
- Argo CD news-api는 수동 Sync이며 k8s 하위 폴더를 재귀 탐색하지 않는다.
  따라서 monitoring/rules 파일은 별도 적용 후 CronJob 변경을 Sync해야 한다.
- suspend는 새 예약 실행만 중지한다. 실행 중 Job 및 수동 Job 실행을 막지 않는다.
- startingDeadlineSeconds가 미지정되어 재개 시 놓친 예약이 즉시 실행되거나
  누락 횟수 제한에 걸릴 수 있다. 재개 전에 정책을 검토한다.

## Implementation Units

없음
