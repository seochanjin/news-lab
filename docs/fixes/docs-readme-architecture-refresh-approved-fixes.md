# Approved Fixes: README 및 아키텍처 문서 현행화

## Approved Fixes

- `docs/runbooks/backend-deploy.md`의 CronJob 확인 명령을 namespace 전체 조회에서 네 Backend CronJob 명시 조회로 변경한다.
- `docs/runbooks/backend-deploy.md`의 production `/health` 확인 명령에 HTTP 4xx/5xx 실패 처리를 추가한다.
- `docs/tasks/docs-readme-architecture-refresh.md`의 언어 미지정 fenced code block 6개에 `text` 식별자를 추가한다.
- `docs/verification/docs-readme-architecture-refresh.md`의 최종 `passed`와 UNIT-06 중간 `pending` 기록 충돌을 해소하고, UNIT-06 블록을 historical snapshot으로 명시한다.

## Rejected or Deferred Suggestions

- 없음. CodeRabbit의 4개 finding은 모두 현재 PR에서 유효하며 문서 범위 안에서 수정한다.

## Applied Changes

- 아직 적용 전이다. 위 4개 항목을 최소 범위로 수정한 뒤 실제 변경 파일과 결과를 기록한다.

## Verification Required

- Backend deploy Runbook에서 네 CronJob 이름이 명시적으로 조회되는지 확인한다.
- `/health` 명령이 HTTP 4xx/5xx에서 non-zero exit status를 반환하도록 `--fail` 또는 `--fail-with-body`를 사용하는지 확인한다.
- Task 문서의 fenced code block에 language identifier가 모두 지정되어 markdownlint MD040 위반이 제거됐는지 확인한다.
- Verification 문서에서 최종 canonical status가 `passed` 하나로 유지되고 UNIT-06의 `pending` 기록이 historical snapshot으로 구분되는지 확인한다.
- `git diff --check`를 다시 실행한다.
- 문서 범위 외 변경이 없는지 확인한다.
