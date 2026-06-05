# agent handoff workflow 개선

## 작업 목적

- NewsLab의 multi-agent workflow에서 매번 branch별 문서 경로와 handoff prompt를 수동으로 조립하는 부담을 줄인다.
- Codex, Gemini/Antigravity, CodeRabbit, human operator 사이의 역할 경계를 더 명확히 한다.
- 자동 실행이 아니라 사람이 복사해 쓸 prompt template을 제공해 workflow 일관성을 높인다.
- 상세 요구사항은 `docs/tasks/<safe-branch>.md`에 두고, chat prompt는 source of truth, 파일 경로, scope, 금지사항, 검증 명령 중심으로 유지하는 규칙을 문서화한다.

## 기존 문제

- 작업 branch마다 task/review/fixes/verification/PR/devlog 경로를 사람이 기억하거나 다시 작성해야 했다.
- Codex 구현, Gemini/Antigravity review, review 결과 저장, fixes draft, PR draft, devlog draft 사이의 handoff prompt가 매번 조금씩 달라질 수 있었다.
- review output과 approved fixes의 경계가 명확하지 않으면, 승인되지 않은 review suggestion이 바로 수정으로 이어질 위험이 있었다.
- verification 결과는 `docs/verification/`을 기준으로 해야 하지만, PR/devlog 작성 시 review file이나 예상 결과가 섞일 수 있었다.
- GitHub MCP나 외부 agent 자동 실행까지 도입하면 scope와 운영 안전 경계가 커지므로, 이번 단계에서는 helper가 prompt만 출력하도록 제한할 필요가 있었다.

## 변경 내용

- `scripts/agent_next_step.sh` 추가.
  - 현재 git branch를 읽는다.
  - branch name의 `/`를 `-`로 바꿔 safe branch name을 계산한다.
  - 현재 branch 기준 workflow 파일 경로를 출력한다.
  - 각 workflow 단계별 copy/paste용 prompt template을 출력한다.
- 지원 명령 추가.
  - `files`
  - `codex-implement`
  - `antigravity-review`
  - `antigravity-review-write`
  - `fixes-draft`
  - `codex-apply-fixes`
  - `pr-draft`
  - `devlog-draft`
- `docs/prompts/agent-handoff.md` 추가.
  - prompt handoff source of truth 규칙 정리.
  - branch file naming 규칙 정리.
  - production-impacting command와 외부 agent 자동 실행 금지 경계 정리.
  - Codex/Gemini/Antigravity/fixes/PR/devlog prompt 구조 정리.
- `docs/RUNBOOK.md` 업데이트.
  - helper 사용법 추가.
  - safe branch name 예시 추가.
  - helper가 실행하지 않는 작업 범위 명시.
- `docs/verification/chore-agent-handoff-workflow.md` 업데이트.
  - 실제 실행한 static/local validation 명령과 결과 기록.

## 구현 상세

- safe branch name 계산은 기존 `scripts/new_agent_task.sh`와 같은 방식인 `/` -> `-` 변환을 따른다.
- `files` 명령은 현재 branch가 `chore/agent-handoff-workflow`일 때 `chore-agent-handoff-workflow` 기반 경로를 출력한다.
- helper prompt에는 공통 규칙을 반복 포함했다.
  - task file이 source of truth.
  - task file과 chat prompt가 충돌하면 task file 우선.
  - production-impacting command 금지.
  - secrets, `.env`, kubeconfig, credentials, SSH keys, tokens 수정 금지.
  - Codex, Gemini/Antigravity, GitHub, CodeRabbit 자동 실행 금지.
  - GitHub MCP는 명시적 task 없이는 사용하지 않음.
  - review output만으로는 수정 지시가 아니며, approved fixes만 적용 가능.
- `antigravity-review-write` prompt는 writable file을 `docs/reviews/<safe-branch>-antigravity.md` 하나로 제한한다.
- `fixes-draft` prompt는 AI가 candidate fixes를 만들 수 있지만 최종 승인 주체는 human operator라고 명시한다.
- `codex-apply-fixes` prompt는 `docs/fixes/<safe-branch>-approved-fixes.md`의 approved fixes만 반영하도록 지시한다.
- `run` 또는 외부 API 호출 같은 자동화는 넣지 않았다.

## 테스트

실제 실행한 static/local validation:

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

Review prompt enhancement 이후 추가 실행:

```bash
bash -n scripts/agent_next_step.sh
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## 운영 반영

- 이 작업은 local helper script와 documentation 변경이다.
- Production verification은 해당 없음.
- `kubectl apply`, `kubectl rollout`, Supabase SQL, production `curl`, `git push`, `git merge`는 실행하지 않았다.
- Codex, Gemini/Antigravity, GitHub, CodeRabbit 자동 실행도 수행하지 않았다.
- 실제 운영 반영은 PR review, merge, 이후 human workflow에서 helper를 사용하는 단계로 남아 있다.

## 확인 결과

- `bash -n scripts/agent_next_step.sh`는 exit code 0, 출력 없음.
- `scripts/agent_next_step.sh files`는 현재 branch와 safe branch name을 정상 출력했다.

```text
Branch: chore/agent-handoff-workflow
Safe branch name: chore-agent-handoff-workflow
```

- `files` 출력에 task/review/fixes/verification/PR/devlog 경로가 포함됐다.
- 모든 helper prompt 명령은 exit code 0으로 copy/paste용 prompt template을 출력했다.
- generated prompt들은 human-controlled operation boundaries를 포함했다.
- `antigravity-review-write` prompt는 writable file을 `docs/reviews/chore-agent-handoff-workflow-antigravity.md` 하나로 제한했다.
- `fixes-draft` prompt는 candidate fixes와 human approval 경계를 명시했다.
- `codex-apply-fixes` prompt는 approved fixes만 적용하도록 명시했다.
- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py`는 exit code 0, 출력 없음.
- FastAPI app, DB, K8s manifest, collector script, extractor script 변경 없음이 확인됐다.
- Approved fixes는 없음.
- Git fallback handling for Git versions earlier than 2.22는 deferred.

## 이번 단계의 의미

- agent workflow에서 반복되던 prompt 조립 비용을 줄였다.
- branch별 workflow artifact path를 helper가 일관되게 출력하므로 human operator가 경로를 잘못 지정할 가능성을 낮췄다.
- review, fixes, implementation, PR, devlog 단계 사이의 책임 경계를 문서와 prompt template에 반영했다.
- 자동화 범위를 prompt 출력까지만 제한해 GitHub MCP, 외부 agent 실행, production command 실행으로 scope가 커지는 것을 피했다.
- 검증 결과는 `docs/verification/`에 기록된 실제 실행 명령만 사용하도록 workflow 기준을 강화했다.

## 포트폴리오용 요약

- NewsLab의 multi-agent 개발 운영을 위해 branch-aware handoff helper를 추가했다.
- helper는 현재 git branch에서 safe branch name을 계산하고, workflow artifact 경로와 단계별 prompt template을 출력한다.
- Codex/Gemini/Antigravity/CodeRabbit을 자동 실행하지 않고, human-controlled operation boundaries를 보존하는 방식으로 생산성을 개선했다.
- prompt 작성 규칙을 `docs/prompts/agent-handoff.md`에 문서화해 task file, verification log, approved fixes의 source of truth 관계를 명확히 했다.

## 다음 단계 후보

- 다음 실제 feature/chore 작업에서 `scripts/agent_next_step.sh`를 사용해 handoff prompt 품질을 확인한다.
- 사용 중 발견되는 문구 중복, 누락된 금지사항, 과도한 prompt 길이를 조정한다.
- Git version fallback이 필요한 환경이 확인되면 `git branch --show-current` 대체 로직을 검토한다.
- GitHub MCP 연동은 별도 task에서 scope, 권한, 안전 경계를 정한 뒤 검토한다.
