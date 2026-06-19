# Verification: backend agent workflow 문서 경량화 및 WIP 1 검증 체계 정리

## Verification Scope

- `AGENTS.md`, architecture/runbook index와 세부 문서, agent workflow 문서
- Workflow artifact인 task, verification, PR draft, devlog
- Markdown 상대 링크, 문서 범위, 고위험 명령 문맥, 민감정보 pattern
- Backend application, DB, migration, Kubernetes manifest, Docker, workflow는
  변경하지 않음

## Commands Run

### 작업 전 조사

```bash
git status --short --branch
wc -l docs/ARCHITECTURE.md docs/RUNBOOK.md AGENTS.md
rg -n '^#{1,4} ' docs/ARCHITECTURE.md docs/RUNBOOK.md
find docs -maxdepth 2 -type f | sort
```

결과:

- Branch: `feature/backend-agent-workflow-docs`
- 작업 시작 시 이 task의 workflow scaffold file만 untracked 상태였음
- 기존 줄 수: `AGENTS.md` 166, `docs/ARCHITECTURE.md` 332,
  `docs/RUNBOOK.md` 1015
- Architecture는 component/data/API가 한 파일에 있었고, Runbook은 routine
  check, agent workflow, local operation, deployment, CronJob, Git workflow가
  한 파일에 혼재했음

### 구현 대조

```bash
find app/routers scripts db/migrations k8s -maxdepth 2 -type f | sort
rg -n 'APIRouter|@router\.(get|post|put|patch|delete)' app/routers/*.py
rg -n 'kind:|name: news-|schedule:|timeZone:|nodeSelector:|workload:|host:|secretName:|cluster-issuer|image:' k8s/*.yaml
rg -n 'CREATE TABLE|ALTER TABLE|CREATE INDEX|topics|topic_articles|sources|articles|crawl_runs|raw_articles|extraction_runs' db/migrations app scripts
```

결과:

- 실제 router, migration, script, manifest를 기준으로 API, table, CronJob,
  domain/TLS 문서를 작성함
- CronJob schedule `03:00`, `03:30`, `04:00 Asia/Seoul`과 두 API host를
  manifest에서 확인함

### 문서 구조와 범위

```bash
wc -l AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md \
  docs/architecture/*.md docs/runbooks/*.md docs/agent/*.md
rg -n '^#|^##|^###' \
  AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md \
  docs/architecture docs/runbooks docs/agent
find docs/architecture docs/runbooks docs/agent -maxdepth 1 -type f | sort
```

결과:

- `AGENTS.md` 106줄, architecture index 45줄, runbook index 54줄
- Architecture 6개, runbook 5개, agent workflow 5개 세부 문서 생성
- 현재 기준 문서는 한국어를 기본으로 작성함

### Markdown link

```bash
rg -n '\]\(' \
  AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md \
  docs/architecture docs/runbooks docs/agent
python -c 'from pathlib import Path; import re,sys; roots=[Path("AGENTS.md"),Path("docs/ARCHITECTURE.md"),Path("docs/RUNBOOK.md")]+list(Path("docs/architecture").glob("*.md"))+list(Path("docs/runbooks").glob("*.md"))+list(Path("docs/agent").glob("*.md")); bad=[]
for p in roots:
 s=p.read_text()
 for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)",s):
  if "://" in target or target.startswith("#"): continue
  dest=(p.parent/target.split("#",1)[0]).resolve()
  if not dest.exists(): bad.append((str(p),target))
print("checked",len(roots),"files"); print("broken",len(bad)); [print(f"{p}: {t}") for p,t in bad]; sys.exit(1 if bad else 0)'
```

결과:

- 19개 대상 Markdown file 검사
- Broken relative link 0개

### Workflow와 운영 기준

```bash
rg -n \
  'api\.newslab\.ai\.kr|api\.dev-scj\.site|news-api|news-rss-collector|news-raw-extractor|news-daily-topic-pipeline|workload=app|workload: app|Tailscale|Supabase' \
  AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md docs/architecture docs/runbooks
rg -n \
  'WIP 1|작업 단위|checklist|체크리스트|Gate 1|Gate 2|Gate 3|Gate 4|Gate 5|end-to-end|사람이 수행' \
  AGENTS.md docs/agent docs/tasks/feature-backend-agent-workflow-docs.md
rg -n \
  'git push|git merge|kubectl apply|kubectl delete|kubectl patch|kubectl edit|kubectl rollout restart|helm upgrade|docker push|migration|Supabase 운영 SQL' \
  AGENTS.md docs/ARCHITECTURE.md docs/RUNBOOK.md \
  docs/architecture docs/runbooks docs/agent
```

결과:

- WIP 1, 작업 단위 완료 조건, Gate 1~5, checklist 규칙 확인
- 고위험 command는 금지 목록 또는 human-controlled runbook 문맥에만 존재
- 현재 schedule, host, resource 명칭에서 충돌 없음

### 민감정보 pattern

```bash
git grep -n -i -E \
  'API_KEY|TOKEN|PASSWORD|PRIVATE KEY|BEGIN PRIVATE|DATABASE_URL=|SECRET=' \
  -- \
  ':!package-lock.json' \
  ':!docs/tasks/**' \
  ':!docs/reviews/**' \
  ':!docs/fixes/**' \
  ':!docs/verification/**' \
  ':!docs/pr/**' \
  ':!docs/devlog/**'
```

결과:

- 실제 credential 값은 발견되지 않음
- 기존 source와 manifest의 환경 변수명, Secret reference, test placeholder,
  정책 문구만 검색됨

### 최종 diff

```bash
git status --short --branch
git diff --name-only
git diff --stat
git diff --check
```

결과:

- `git diff --check` 통과
- Tracked diff와 untracked file 상태를 함께 확인했으며 변경은 문서 범위에 한정
- Application source, migration, `k8s/*.yaml`, Dockerfile, GitHub Actions,
  frontend 변경 없음

## Results

- Architecture와 Runbook index에서 책임별 세부 문서로 이동하는 경로를 확인함
- 세부 문서에서 index 또는 인접 문서로 돌아가는 경로를 확인함
- Agent가 task → workflow → 역할별 문서 → 필요한 architecture/runbook →
  verification/forbidden 문서 순서로 읽도록 정의함
- Documentation-only acceptance criteria 충족

## Manual or Production Verification

- 수행하지 않음
- 이 task는 production apply, rollout, DB write, production API 확인을 요구하지
  않음

## Pending Verification

- PR 생성 및 merge
- 실제 다음 task에서 새 읽기 순서와 WIP 1 gate를 적용한 운영성 확인
- Production verification은 이 문서 작업의 범위 밖

## Evidence Notes

- 최초 Antigravity review 원문은 유지했다.
- Approved Fixes 적용 후 동일 review 파일에 `Re-review 1`을 추가했다.
- 별도 rereview artifact는 생성하지 않았다.
- Approved Fixes 적용 결과와 재검토 결과는 실제 diff 및 verification 기록을 기준으로 확인했다.
- 후속 자동화 후보는 devlog에 기록했다.

## Approved Fixes 적용 검증

### 변경 전 상태와 대상 확인

```bash
git status --short --branch
sed -n '1,420p' scripts/agent_next_step.sh
for command in files codex-implement antigravity-review antigravity-review-write fixes-draft codex-apply-fixes pr-draft devlog-draft; do
  echo "COMMAND $command"
  scripts/agent_next_step.sh "$command"
done
rg -n 'agent_next_step|codex-implement|antigravity-review-write|Re-review|rereview' \
  tests scripts docs
```

결과:

- Branch가 `feature/backend-agent-workflow-docs`임을 확인함
- 기존 helper는 8개 command를 유지했지만 신규 `docs/agent/*`, WIP 1,
  Approved Fixes 검증, 단일 review 파일 재검토 규칙이 생성 prompt에 부족했음
- 별도 자동 test는 없고 기존 verification에서 shell 문법과 command 출력
  확인 방식을 사용한 것을 확인함

### 최초 shell 검증 실패와 수정

```bash
ls -l scripts/agent_next_step.sh
bash -n scripts/agent_next_step.sh
scripts/agent_next_step.sh --help
scripts/agent_next_step.sh files
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh codex-apply-fixes
```

최초 결과:

- `bash -n scripts/agent_next_step.sh`는 통과함
- Script 재작성 과정에서 executable bit가 제거되어 직접 실행 command는
  exit code 126, `permission denied`로 실패함

수정:

```bash
chmod +x scripts/agent_next_step.sh
```

결과:

- Executable mode를 복원함

### Shell 문법, 도움말, 핵심 prompt 재검증

```bash
ls -l scripts/agent_next_step.sh
bash -n scripts/agent_next_step.sh
scripts/agent_next_step.sh --help
scripts/agent_next_step.sh files
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh codex-apply-fixes
```

결과:

- 모든 command exit code 0
- Script mode는 executable
- 기존 8개 command 유지, 별도 rereview command 없음
- 도움말과 prompt가 한국어 기준으로 출력됨
- `files`가 backend workflow 5개 문서, architecture/runbook index, 최초 review와
  Re-review의 단일 파일 사용을 출력함
- Codex prompt가 WIP 1, 작업 단위 완료 순서, checklist, 문제 분류,
  end-to-end와 human-controlled verification을 출력함
- Antigravity prompt가 task/fixes/verification/기존 review/diff 대조와
  최초 review·재검토 모드를 출력함
- Review write prompt가 writable file 하나, 기존 원문 보존, `Re-review N`
  append, 기존 문제 상태와 새 문제 구분을 출력함
- Approved fixes prompt가 승인 항목만 적용하고 검증 완료 항목만 체크하며
  실제 command 결과를 verification에 기록하도록 출력함

### 기존 command 회귀 검증

```bash
scripts/agent_next_step.sh fixes-draft
scripts/agent_next_step.sh pr-draft
scripts/agent_next_step.sh devlog-draft
```

결과:

- 모든 command exit code 0
- 현재 branch safe name 기반 경로 유지
- 공통 고위험 command 제한 유지
- 기존 역할과 필수 section 유지
- 출력 문구 한국어화 확인

### 별도 rereview artifact와 민감정보 확인

```bash
rg -n \
  'antigravity-rereview|antigravity-rereview-write|rereview\.md' \
  scripts/agent_next_step.sh || true
git grep -n -i -E \
  'API_KEY|TOKEN|PASSWORD|PRIVATE KEY|BEGIN PRIVATE|DATABASE_URL=|SECRET=' \
  -- \
  scripts/agent_next_step.sh \
  docs/agent \
  docs/fixes/feature-backend-agent-workflow-docs-approved-fixes.md
```

결과:

- 별도 rereview command 또는 artifact path 없음
- 실제 credential 값 없음
- 민감정보 검색은 Secret 수정 금지 정책 문구만 반환함

### Antigravity 재검토

- 생성된 review prompt를 사용해 Antigravity 재검토를 수행했다.
- 최초 review 원문을 유지한 상태에서 동일 파일에 `Re-review 1`을 추가했다.
- Approved Fixes 적용 여부, verification evidence, 신규 문제 및 scope creep을 확인했다.
- 재검토 결과는 `APPROVED`였다.

### 미수행 검증

- Production verification:
  이 approved fixes는 local helper/document 변경이므로 수행하지 않음

### 최종 Gate

```bash
bash -n scripts/agent_next_step.sh
git diff --check
git status --short --branch
git diff --name-only
git diff --stat
sed -n '1,/^## Rejected or Deferred Suggestions/p' \
  docs/fixes/feature-backend-agent-workflow-docs-approved-fixes.md |
  rg -n -- '- \[ \]' || true
git diff --summary -- scripts/agent_next_step.sh
git diff -- scripts/agent_next_step.sh
rg -n \
  'WIP 1|조사 → 변경 → 문서화 → 검증|완료하지 않은 checklist|end-to-end|Re-review N|APPROVED WITH NOTES|현재 git diff|docs/verification/.+-|docs/fixes/.+-approved-fixes' \
  scripts/agent_next_step.sh \
  docs/agent/codex-instructions.md \
  docs/agent/antigravity-review.md
scripts/agent_next_step.sh files >/tmp/agent-next-files.txt
scripts/agent_next_step.sh codex-implement >/tmp/agent-next-codex.txt
scripts/agent_next_step.sh antigravity-review >/tmp/agent-next-review.txt
scripts/agent_next_step.sh antigravity-review-write >/tmp/agent-next-review-write.txt
scripts/agent_next_step.sh codex-apply-fixes >/tmp/agent-next-apply.txt
wc -l \
  /tmp/agent-next-files.txt \
  /tmp/agent-next-codex.txt \
  /tmp/agent-next-review.txt \
  /tmp/agent-next-review-write.txt \
  /tmp/agent-next-apply.txt
```

결과:

- `bash -n`과 `git diff --check` 통과
- `scripts/agent_next_step.sh` mode `100755` 유지
- Approved Fixes의 실제 checklist 항목은 모두 완료 처리됨
  - 검색 결과의 unchecked 표기는 checklist 처리 규칙 설명과 Markdown 예시뿐임
- WIP 1, end-to-end, verification/fixes 대조, `Re-review N`, 최종 verdict 규칙이
  script와 agent 지침에 존재함
- 핵심 prompt 5개를 `/tmp`에 출력했고 총 346줄, 모든 command exit code 0
- 변경은 승인된 helper와 backend workflow/document artifact 범위에 한정됨
- Backend application, DB/migration, Kubernetes manifest, Dockerfile,
  GitHub Actions, frontend 변경 없음
