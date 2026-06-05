# agent handoff workflow 개선

## 작업 내용

- NewsLab multi-agent workflow에서 branch별 파일 경로와 handoff prompt를 매번 수동으로 조립하지 않도록 local helper를 추가했습니다.
- 현재 git branch에서 safe branch name을 계산하고, task/review/fixes/verification/PR/devlog 파일 경로를 출력하도록 했습니다.
- Codex, Gemini/Antigravity review, review write, fixes draft, approved fixes 적용, PR draft, devlog draft 단계별 copy/paste용 prompt template을 출력하도록 했습니다.
- agent handoff prompt 작성 규칙을 별도 문서로 정리하고 Runbook에 helper 사용법을 추가했습니다.
- 실제 실행한 static/local validation 결과를 verification 문서에 기록했습니다.

## 주요 변경 사항

- `scripts/agent_next_step.sh` 추가
  - 현재 branch를 `git branch --show-current`로 확인
  - `/`를 `-`로 바꿔 safe branch name 계산
  - `files` 명령으로 현재 branch 기준 workflow 파일 경로 출력
  - `codex-implement`, `antigravity-review`, `antigravity-review-write`, `fixes-draft`, `codex-apply-fixes`, `pr-draft`, `devlog-draft` prompt template 출력
  - helper는 prompt만 출력하며 Codex, Gemini/Antigravity, GitHub, CodeRabbit, Kubernetes, Supabase, production API를 실행하지 않음
- `docs/prompts/agent-handoff.md` 추가
  - 긴 요구사항은 `docs/tasks/<safe-branch>.md`에 두는 규칙 문서화
  - chat prompt는 source of truth, 파일 경로, scope, constraints, validation 중심으로 작성하는 규칙 문서화
  - review output만으로는 수정 지시가 아니며, approved fixes만 적용 가능하다는 handoff 경계 문서화
  - Codex implementation, Gemini/Antigravity review, review write, fixes draft, apply fixes, PR draft, devlog draft prompt 구조 정리
- `docs/RUNBOOK.md` 변경
  - `scripts/agent_next_step.sh files` 사용법 추가
  - 각 handoff prompt 출력 명령 추가
  - helper가 safe branch name을 계산하는 방식과 자동 실행하지 않는 작업 범위 명시
- `docs/verification/chore-agent-handoff-workflow.md` 변경
  - 실제 실행한 static/local validation 명령과 결과 기록
  - production verification이 해당 없는 작업임을 기록

## 추가/변경된 API

- 없음.
- FastAPI route 또는 API response는 변경하지 않았습니다.

## DB 변경 사항

- 없음.
- DB schema 또는 migration은 변경하지 않았습니다.
- Supabase SQL은 실행하지 않았습니다.

## 테스트

- 완료:

```bash
bash -n scripts/agent_next_step.sh
```

```bash
scripts/agent_next_step.sh files
```

```bash
scripts/agent_next_step.sh codex-implement
```

```bash
scripts/agent_next_step.sh antigravity-review
```

```bash
scripts/agent_next_step.sh antigravity-review-write
```

```bash
scripts/agent_next_step.sh fixes-draft
```

```bash
scripts/agent_next_step.sh codex-apply-fixes
```

```bash
scripts/agent_next_step.sh pr-draft
```

```bash
scripts/agent_next_step.sh devlog-draft
```

```bash
git diff --check
```

```bash
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

- Review prompt enhancement 이후 추가 확인:

```bash
bash -n scripts/agent_next_step.sh
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## 확인 결과

- `bash -n scripts/agent_next_step.sh`는 exit code 0, 출력 없음.
- `scripts/agent_next_step.sh files`는 현재 branch와 safe branch name을 출력했습니다.

```text
Branch: chore/agent-handoff-workflow
Safe branch name: chore-agent-handoff-workflow
```

- `files` 출력에 다음 workflow 경로가 포함됐습니다.
  - `docs/tasks/chore-agent-handoff-workflow.md`
  - `docs/reviews/chore-agent-handoff-workflow-antigravity.md`
  - `docs/reviews/chore-agent-handoff-workflow-coderabbit.md`
  - `docs/fixes/chore-agent-handoff-workflow-approved-fixes.md`
  - `docs/verification/chore-agent-handoff-workflow.md`
  - `docs/pr/chore-agent-handoff-workflow.md`
  - `docs/devlog/chore-agent-handoff-workflow.md`
- 모든 helper prompt 명령은 exit code 0으로 copy/paste용 prompt template을 출력했습니다.
- 생성된 prompt에는 human-controlled operation boundaries가 포함됐습니다.
- `antigravity-review-write` prompt는 writable file을 `docs/reviews/chore-agent-handoff-workflow-antigravity.md` 하나로 제한했습니다.
- `fixes-draft` prompt는 AI가 candidate fixes를 만들 수 있지만 최종 승인 주체는 human operator라고 명시했습니다.
- `codex-apply-fixes` prompt는 `docs/fixes/chore-agent-handoff-workflow-approved-fixes.md`의 approved fixes만 적용하라고 명시했습니다.
- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py`는 exit code 0, 출력 없음.
- FastAPI app, DB, K8s manifest, collector script, extractor script 변경 없음이 확인됐습니다.
- Production verification은 이 helper/documentation 작업에는 해당 없음으로 기록했습니다.

## 비고

- Approved fixes: 없음.
- Gemini / Antigravity review에서 PR 전 필수 수정 사항은 없었습니다.
- Git fallback handling for Git versions earlier than 2.22는 deferred입니다.
- PR merge, production deployment, K3s rollout, production verification은 완료로 주장하지 않습니다.
- `kubectl`, rollout, Supabase SQL, production `curl`, `git push`, `git merge`는 실행하지 않았습니다.
- GitHub MCP integration과 agent 자동 실행은 이번 작업 범위에서 제외했습니다.
