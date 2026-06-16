# Verification: 홈 Topics 경량 API 설계 및 MVP

## Verification Scope

- Backend implementation for `GET /topics/home`.
- Existing `GET /topics` and `GET /topics/{topic_id}` behavior protected by
  focused route tests.
- Documentation for current API analysis and follow-up cache/snapshot strategy.
- No production deployment, production `/topics/home` check, Supabase SQL, DB
  write, kubectl apply, kubectl rollout, git push, or git merge.

## Commands Run

```bash
pwd && rg --files -g 'AGENTS.md' -g 'docs/RUNBOOK.md' -g 'docs/prompts/codex-implement.md' -g 'docs/tasks/feature-home-topics-snapshot-design.md' -g 'docs/verification/feature-home-topics-snapshot-design.md' -g 'docs/pr/feature-home-topics-snapshot-design.md' -g 'docs/devlog/feature-home-topics-snapshot-design.md'
git status --short --branch
sed -n '1,240p' AGENTS.md
sed -n '1,260p' docs/RUNBOOK.md
sed -n '1,260p' docs/prompts/codex-implement.md
sed -n '1,680p' docs/tasks/feature-home-topics-snapshot-design.md
sed -n '1,260p' docs/ARCHITECTURE.md
sed -n '1,220p' app/routers/topics.py
sed -n '1,120p' app/main.py
sed -n '1,180p' app/database.py
sed -n '1,220p' tests/test_topics_api.py
python -m unittest tests.test_topics_api -v
python -m py_compile app/routers/topics.py tests/test_topics_api.py
python -m unittest discover -s tests -v
git diff --check
git diff --name-only
git status --short --branch
```

## Results

- `python -m unittest tests.test_topics_api -v`: passed, 6 tests.
- `python -m py_compile app/routers/topics.py tests/test_topics_api.py`: passed.
- `python -m unittest discover -s tests -v`: passed, 121 tests.
- `git diff --check`: passed.
- `git diff --name-only`: implementation/test changes at the time of the check:
  - `app/routers/topics.py`
  - `tests/test_topics_api.py`
- Final `git status --short --branch` showed tracked modifications to
  `app/routers/topics.py`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, and
  `tests/test_topics_api.py`, plus untracked workflow/design docs for this
  branch.

An initial focused test run failed because the new test reused the detail topic
fixture, which included fields not selected by `/topics/home`. The test fixture
was corrected to model the lightweight query result, and the rerun passed.

## Manual or Production Verification

- Production timing values below are the pre-task measurements provided in the
  task source of truth. I did not run new production curl verification during
  this implementation.

```text
/topics?page=1&page_size=10: 1.004652s
/topics?page=1&page_size=50: 0.902372s
/topics/7: 0.793147s

/topics?page=1&page_size=10 10회 반복:
1. 0.965516s
2. 0.881402s
3. 0.709049s
4. 0.793458s
5. 0.897315s
6. 0.868379s
7. 0.927151s
8. 0.897393s
9. 0.813286s
10. 0.996598s
```

- Observed range for `/topics?page=1&page_size=10`: about 0.71s to 1.00s.
- Average for the 10 repeated `/topics?page=1&page_size=10` samples: about
  0.87s.
- `page_size=50` was not materially slower than `page_size=10` in the provided
  single samples.
- Topic detail was in the same general range as list responses in the provided
  sample.
- For a home first viewport, about 0.7s to 1.0s can still be visible as loading
  even if it is not a severe backend outage.

## Pending Verification

- Local HTTP verification against `uvicorn` was not run because it would require
  a live `DATABASE_URL` target. The handler was verified with unit tests using a
  fake connection.
- Production `/topics/home` verification is pending deployment by the human
  operator.
- Frontend home switch to `/topics/home` is pending a later task.

## Evidence Notes

### Current Topics API analysis

- Route handler location: `app/routers/topics.py`, registered from
  `app/main.py`.
- `GET /topics`:
  - Builds optional filters for `status`, `date_from`, `date_to`, and
    `keyword`.
  - Runs `select count(*) from topics ...` for pagination.
  - Reads from `topics` only.
  - Returns `items`, `page`, `page_size`, `total`, and `has_next`.
  - Item fields include `id`, `topic_date`, `title_ko`, `summary_ko`,
    `keywords`, `source_count`, `article_count`, `provider`, `model`, `status`,
    `created_at`, and `updated_at`.
  - Existing ordering is `topic_date desc, id desc`.
- `GET /topics/{topic_id}`:
  - Reads one topic from `topics`.
  - Joins `topic_articles`, `articles`, and `sources` to return connected
    articles.
  - Returns detail fields such as `topic_candidate_id`, `key_points`,
    `confidence`, `summary_input_hash`, provider/model/status/timestamps, and
    `articles`.
- Home first viewport needs only topic card fields: `id`, `topic_date`,
  `title_ko`, `summary_ko`, `keywords`, `article_count`, and `source_count`.
- Home first viewport does not need archive pagination metadata, total count,
  provider/model/status/debug fields, connected articles, representative article
  details, or raw article text.

### `/topics/home` MVP

- `GET /topics/home` reads directly from `topics`.
- It returns at most 10 items.
- It does not call `GET /topics` as a wrapper.
- It does not run a total count query.
- It does not join `topic_articles`.
- It does not change DB schema or write data.
- It is ordered by `topic_date desc, article_count desc, source_count desc,
  id desc` so current dates stay first and larger multi-source topics are
  prioritized inside the same date.
