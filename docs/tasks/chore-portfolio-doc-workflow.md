# Task: README/포트폴리오 문서화 workflow 개선

## Goal

Improve the NewsLab agent workflow so future worklogs and PR drafts include portfolio-oriented documentation decisions.

The current workflow records implementation, review, approved fixes, and verification. However, portfolio-quality documentation also needs to capture alternatives considered, why the chosen approach was selected, tradeoffs, and whether README updates are needed.

## Scope

- Update worklog/devlog prompt rules to include:
  - alternatives considered
  - chosen approach and rationale
  - tradeoffs
  - README update decision
  - portfolio-facing summary
- Update PR draft prompt rules if needed to mention README impact.
- Update `docs/prompts/agent-handoff.md` to include portfolio documentation handoff rules.
- Update `scripts/agent_next_step.sh devlog-draft` output to include the new devlog sections.
- Update `docs/RUNBOOK.md` with guidance for README/portfolio documentation checks.
- Record static/local verification results in `docs/verification/chore-portfolio-doc-workflow.md`.

## Do not change

- Do not modify FastAPI app behavior.
- Do not modify DB schema or migrations.
- Do not modify K8s manifests.
- Do not modify collector or extractor runtime scripts.
- Do not modify secrets, `.env`, kubeconfig, credentials, SSH keys, or tokens.
- Do not run `kubectl apply`.
- Do not run `kubectl rollout`.
- Do not execute Supabase SQL.
- Do not use GitHub MCP.
- Do not push or merge.

- Do not claim production verification is complete.

## Expected files

Likely files:

- `docs/prompts/worklog-draft.md`
- `docs/prompts/pr-draft.md`
- `docs/prompts/agent-handoff.md`
- `scripts/agent_next_step.sh`
- `docs/RUNBOOK.md`
- `docs/tasks/chore-portfolio-doc-workflow.md`
- `docs/verification/chore-portfolio-doc-workflow.md`
- `docs/pr/chore-portfolio-doc-workflow.md`
- `docs/devlog/chore-portfolio-doc-workflow.md`

## DB changes

None.

## API changes

None.

## Test commands

Agent may run only static/local validation:

```bash
bash -n scripts/agent_next_step.sh
scripts/agent_next_step.sh devlog-draft
scripts/agent_next_step.sh pr-draft
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## Acceptance criteria

- Future devlog drafts include sections for:
  - alternatives considered
  - chosen approach and rationale
  - tradeoffs
  - README update decision
  - portfolio-facing summary
- Future PR drafts mention README impact when relevant.
- agent_next_step.sh devlog-draft prints the updated devlog section requirements.
- docs/prompts/agent-handoff.md documents the portfolio documentation handoff rule.
- docs/RUNBOOK.md explains that tasks should evaluate README/portfolio documentation impact.
- Static/local validation is recorded in docs/verification/chore-portfolio-doc-workflow.md.
- No app, DB, K8s, collector, extractor, secret, credential, or production files are modified.

## Notes

This task is a workflow/documentation improvement. It should not implement a new product feature.

The purpose is to ensure future NewsLab work is recorded not only as implementation history, but also as portfolio-quality engineering decision documentation.

## Alternatives Considered

### Alternative A: Manually add alternatives after writing each devlog

- Pros: Flexible.
- Cons: Easy to forget, and the quality of worklogs may vary by task.

### Alternative B: Require README updates for every task

- Pros: README stays consistently updated.
- Cons: Too strict for internal workflow tasks that do not affect user-facing usage or architecture.

### Alternative C: Add README impact and alternatives review to workflow prompts

- Pros: Every task evaluates documentation impact, while README changes are made only when relevant.
- Cons: Devlog prompts become slightly longer.

## Selected Approach

Use Alternative C.

Future workflow prompts should ask agents to evaluate README impact, alternatives considered, chosen approach, and tradeoffs. README updates should not be mandatory for every task, but the decision should be recorded.
