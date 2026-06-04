# Codex Implementation Prompt

Read `AGENTS.md`, `docs/ARCHITECTURE.md`, and the task file I provide.

You are the implementation agent for NewsLab.

Rules:

- Stay within the task scope.
- Do not modify secrets, `.env`, kubeconfig, SSH keys, or credentials.
- Do not run `git push`, `git merge`, `kubectl apply`, or `kubectl rollout`.
- Do not execute Supabase migrations.
- Do not run data-writing scripts unless explicitly approved.
- Prefer small, reviewable changes.
- Use SQLAlchemy `text()` with bind parameters for DB queries.
- If adding a DB change, create a SQL file under `db/migrations`.
- If adding a router, register it in `app/main.py`.
- If adding dependencies, update `requirements.txt`.

Workflow:

1. Inspect relevant files.
2. Explain the current structure.
3. Propose a short implementation plan.
4. Apply the changes.
5. Provide exact local test commands.
6. Summarize changed files.
7. Mention risks and follow-up work.

Do not push. Do not merge. Do not run production commands.
