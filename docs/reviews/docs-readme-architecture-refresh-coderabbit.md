# CodeRabbit Review: README 및 아키텍처 문서 현행화

## Review Summary

CodeRabbit이 PR #62에서 총 4개의 finding을 남겼다.

- Major 2건
- Minor 2건
- 모두 문서 변경 범위 안에서 수정 가능한 quick win
- Application code, Kubernetes manifest, workflow, DB 또는 Production 변경은 필요하지 않음

가장 중요한 문제는 production health check가 HTTP 4xx/5xx를 실패로 처리하지 않는 점과 Verification 문서의 최종 상태가 `passed`와 `pending`으로 충돌하는 점이다.

나머지 두 건은 Runbook의 CronJob 검증 범위를 더 정확하게 제한하는 문제와 Markdown lint 경고다.

## Problems Found

### 1. Backend CronJob 확인 명령이 namespace 전체를 조회함

대상 파일:

```
docs/runbooks/backend-deploy.md
```

현재 Runbook은 다음과 같이 namespace 안의 모든 CronJob을 출력한다.

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get cronjob
```

이 명령은 unrelated CronJob도 함께 출력하므로 네 Backend CronJob 중 하나가 누락되거나 잘못된 image를 사용해도 사람이 전체 목록을 보고 놓칠 수 있다.

검증 대상은 다음 네 workload로 한정해야 한다.

```
news-rss-collector
news-daily-topic-pipeline
news-three-day-topic-pipeline
news-weekly-topic-pipeline
```

판단: valid finding. Minor지만 운영 Runbook의 검증 정확도를 높이므로 수정한다.

### 2. Production health check가 HTTP 4xx/5xx를 실패로 처리하지 않음

대상 파일:

```
docs/runbooks/backend-deploy.md
```

현재 명령:

```bash
curl -sS https://api.newslab.ai.kr/health
```

`curl -sS`는 네트워크 연결 실패에는 non-zero로 종료하지만 HTTP 404, 500과 같은 응답에는 성공 코드로 종료할 수 있다.

따라서 endpoint가 500을 반환해도 Verification에서 command 자체가 성공한 것으로 잘못 기록될 수 있다.

다음과 같이 HTTP failure handling을 추가해야 한다.

```bash
curl --fail --silent --show-error https://api.newslab.ai.kr/health
```

또는 응답 body를 유지해야 하면 다음을 사용할 수 있다.

```bash
curl --fail-with-body --silent --show-error https://api.newslab.ai.kr/health
```

판단: valid finding. Major이며 PR merge 전에 반드시 수정한다.

### 3. Task 문서의 fenced code block에 language identifier가 없음

대상 파일:

```
docs/tasks/docs-readme-architecture-refresh.md
```

Task 문서의 흐름도와 file list code block 일부가 다음처럼 language identifier 없이 작성되어 있다.

```

```

User

→ Public DNS

→ Oracle Public IP

```

```

Markdownlint MD040 규칙은 fenced code block에 language identifier를 요구한다.

흐름도와 file list는 모두 `text`를 사용하면 된다.

```

```

User

→ Public DNS

→ Oracle Public IP

```

```

판단: valid finding. Functional bug는 아니지만 lint 경고이며 수정 비용이 작으므로 함께 반영한다.

### 4. Verification 최종 상태가 `passed`와 `pending`으로 충돌함

대상 파일:

```
docs/verification/docs-readme-architecture-refresh.md
```

문서 상단의 canonical status는 다음과 같다.

```
passed
```

하지만 UNIT-06 시점의 중간 로그에는 다음 내용이 남아 있다.

```
UNIT-07 remains pending and was not started.
Overall Verification Status remains pending.
```

현재 문서는 시간순 실행 기록을 그대로 보존하면서 최종 reconciliation 결과를 위에 추가한 구조라서, 독자는 어떤 상태가 최종 상태인지 혼동할 수 있다.

UNIT-06의 중간 블록을 삭제할 필요는 없지만 다음처럼 historical snapshot임을 명확히 표시해야 한다.

```
Historical UNIT-06 Snapshot

이 섹션은 UNIT-07 완료 전의 중간 상태다.
최종 canonical status는 문서 상단의 passed와 UNIT-07 결과를 기준으로 한다.
```

판단: valid finding. Major이며 Verification의 신뢰성에 직접 영향을 주므로 PR merge 전에 반드시 수정한다.

## Required Fixes Before PR

- [ ] `docs/runbooks/backend-deploy.md`의 두 CronJob 조회 명령을 네 Backend CronJob 명시 조회로 변경
- [ ] production `/health` curl에 `--fail --silent --show-error` 또는 `--fail-with-body` 적용
- [ ] `docs/tasks/docs-readme-architecture-refresh.md`의 unlabeled fenced code block 6개에 `text` language identifier 추가
- [ ] `docs/verification/docs-readme-architecture-refresh.md`의 UNIT-06 pending 블록을 historical snapshot으로 명시하고 최종 canonical status를 `passed` 하나로 정리
- [ ] 수정 후 CodeRabbit Review artifact와 Approved Fixes 문서에 4개 finding의 승인 및 반영 결과 기록
- [ ] 수정 commit push 후 CodeRabbit 재검토 결과 확인

## Optional Improvements

- Runbook의 Backend workload 이름을 여러 명령에서 반복할 경우 shell variable 또는 공통 예시로 묶는 방법을 검토할 수 있다. 이번 PR에서는 문서 가독성을 위해 explicit name 나열을 유지해도 된다.
- Verification 문서는 1,000줄 이상으로 길어졌으므로 후속 작업에서 최종 결과와 단계별 historical log를 분리할 수 있다. 이번 PR에서는 상태 충돌만 최소 수정한다.
- `curl` 기반 운영 확인 명령은 다른 Runbook에도 `-sS`만 남아 있는지 별도 검색할 수 있다. 이번 finding의 직접 범위는 `backend-deploy.md`다.

## Suggested Test Commands

### CronJob 명시 조회 확인

```bash
rg -n \
  'kubectl get cronjob|news-rss-collector|news-daily-topic-pipeline|news-three-day-topic-pipeline|news-weekly-topic-pipeline' \
  docs/runbooks/backend-deploy.md
```

확인 조건:

- namespace 전체 조회만 하는 명령이 남아 있지 않음
- 네 Backend CronJob 이름이 모두 명시됨

### Health check failure 처리 확인

```bash
rg -n \
  'curl .*api\.newslab\.ai\.kr/health' \
  docs/runbooks/backend-deploy.md
```

확인 조건:

- `--fail` 또는 `--fail-with-body` 포함
- `--silent`와 `--show-error` 포함

### Fenced code language 확인

```bash
markdownlint-cli2 docs/tasks/docs-readme-architecture-refresh.md
```

설치되지 않았다면 다음 검색으로 unlabeled fence를 수동 확인한다.

````bash
python - <<'PY'
from pathlib import Path

path = Path('docs/tasks/docs-readme-architecture-refresh.md')
lines = path.read_text(encoding='utf-8').splitlines()

unlabeled = [
    index
    for index, line in enumerate(lines, start=1)
    if line.strip() == '```'
]

if unlabeled:
    raise SystemExit(f'unlabeled fences: {unlabeled}')

print('all opening fences are labeled or closing fences only')
PY
````

### Verification canonical status 확인

```bash
rg -n \
  'Verification Status|Overall Verification Status|pending|Historical UNIT-06|canonical' \
  docs/verification/docs-readme-architecture-refresh.md
```

확인 조건:

- 최종 canonical status는 `passed`
- 과거 `pending` 문장은 historical snapshot으로 명확히 한정됨
- 현재 전체 상태처럼 읽히는 conflicting statement가 없음

### 최종 문서 범위와 whitespace 확인

```bash
git diff --check
```

```bash
git diff --name-only -- \
  app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml
```

기대 결과: 출력 없음.

## Risk Notes

- CronJob 이름을 잘못 입력하면 Runbook 명령이 일부 workload를 누락할 수 있으므로 실제 manifest의 `metadata.name`과 대조해야 한다.
- `curl --fail`은 HTTP error body를 기본적으로 숨길 수 있다. 장애 분석 시 body가 필요하면 `--fail-with-body`가 더 적합하다.
- Verification의 중간 `pending` 기록을 단순 삭제하면 작업 진행 이력이 사라진다. 삭제보다 historical snapshot 라벨을 추가하는 방식이 적절하다.
- Markdown fence 수정은 내용 변경이 아니라 lint 정합성 변경이므로 flow text와 file list 자체를 함께 편집하지 않는다.
- 이번 수정은 문서 전용이며 production command, Argo CD Sync, Kubernetes 변경이나 새 production verification을 요구하지 않는다.
