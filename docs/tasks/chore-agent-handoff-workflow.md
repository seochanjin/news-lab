# Task: agent handoff workflow 개선

## Goal

Reduce manual copy/paste and repeated prompt construction between ChatGPT, Codex, Gemini/Antigravity, and CodeRabbit during the NewsLab agent workflow.

This task adds a local helper that prints the current branch's workflow file paths and reusable handoff prompts.

The goal is not to fully automate agents. The goal is to make the handoff between agents more consistent and easier for the human operator.

## Scope

- Add a local helper script for agent workflow handoff.
- The helper should infer the current git branch name.
- The helper should derive the safe branch name used by `new_agent_task.sh`.
  - Example: `feature/raw-extractor-cronjob` → `feature-raw-extractor-cronjob`
- The helper should print paths for:
  - task file
  - Antigravity review file
  - CodeRabbit review file
  - approved fixes file
  - verification file
  - PR draft file
  - devlog file
- The helper should print reusable prompts for:
  - Codex implementation
  - Gemini/Antigravity review
  - Gemini/Antigravity review written to `docs/reviews`
  - fixes draft creation
  - Codex applying approved fixes
  - PR draft generation
  - devlog generation
- Update `docs/RUNBOOK.md` with helper usage.
- Define standard prompt handoff rules for Codex, Gemini/Antigravity, fixes draft, PR draft, and devlog draft.
- Add the prompt handoff rules to `docs/RUNBOOK.md` or a dedicated prompt document.

## Do not change

- Do not modify FastAPI app behavior.
- Do not modify DB schema.
- Do not modify K8s manifests.
- Do not modify production scripts such as collectors or extractors.
- Do not modify secrets, `.env`, kubeconfig, or credentials.
- Do not run `kubectl apply`.
- Do not run `kubectl rollout`.
- Do not execute Supabase SQL.
- Do not integrate GitHub MCP in this task.
- Do not automatically run Codex, Gemini/Antigravity, GitHub, or CodeRabbit.
- Do not create, push, merge, or close PRs automatically.

## Expected files

Likely files:

- `scripts/agent_next_step.sh`
- `docs/RUNBOOK.md`
- `docs/verification/chore-agent-handoff-workflow.md`
- `docs/pr/chore-agent-handoff-workflow.md`
- `docs/devlog/chore-agent-handoff-workflow.md`
- `docs/prompts/agent-handoff.md`

## DB changes

None.

Do not add or modify database migrations.

## API changes

None.

Do not modify FastAPI routes or response behavior.

## Test commands

Agent may run static/local validation only:

```bash
bash -n scripts/agent_next_step.sh
```

```bash
scripts/agent_next_step.sh files
scripts/agent_next_step.sh codex-implement
scripts/agent_next_step.sh antigravity-review
scripts/agent_next_step.sh antigravity-review-write
scripts/agent_next_step.sh fixes-draft
scripts/agent_next_step.sh codex-apply-fixes
scripts/agent_next_step.sh pr-draft
scripts/agent_next_step.sh devlog-draft
```

```bash
git diff --check
```

```bash
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## Acceptance criteria

- `scripts/agent_next_step.sh` exists.
- The script can infer the current branch name.
- The script can derive the safe branch name.
- The script prints the expected task/review/fixes/verification/PR/devlog file paths.
- The script prints reusable prompts for each supported handoff step.
- The generated prompts preserve human-controlled operation boundaries.
- The Gemini/Antigravity review-write prompt restricts writable files to the target review file only.
- The fixes-draft prompt makes clear that AI may draft candidate fixes, but the human operator must approve final fixes.
- The Codex apply-fixes prompt tells Codex to apply only approved fixes.
- `docs/RUNBOOK.md` explains how to use the helper.
- Static validation passes.
- No app, DB, K8s, collector, extractor, secret, or credential files are modified.
- The project documents define a standard structure for Codex implementation prompts.
- The project documents define a standard structure for Gemini/Antigravity review prompts.
- The project documents clarify that detailed task requirements live in `docs/tasks/<branch>.md`, while chat prompts should stay focused on file paths, source of truth, constraints, and validation commands.

## Notes

This task is based on friction found during the 15차 raw extractor CronJob work.

The main pain points were:

- The human had to remember the correct branch-specific document paths.
- The human had to manually construct prompts for Codex and Gemini/Antigravity.
- Gemini/Antigravity review output had to be copied manually into `docs/reviews`.
- Review output and approved fixes needed a clearer handoff step.
- Codex should not apply review suggestions directly unless they are listed as approved fixes.

This task should improve the workflow handoff, but should not introduce full automation or GitHub MCP integration yet.
