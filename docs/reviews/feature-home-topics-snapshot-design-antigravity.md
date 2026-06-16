# Antigravity Review: 홈 Topics 경량 API 설계 및 MVP

## Review Summary
This review evaluates the implementation of the lightweight `GET /topics/home` endpoint and its accompanying documentation in the `feature/home-topics-snapshot-design` branch. The changes successfully implement a high-performing, read-only MVP for the home screen topics without introducing database schema changes, external caching systems, or altering existing functionality. The code and tests conform to the style guidelines, and the design documentation provides a clear roadmap for subsequent caching and pipeline work.

## Requirement Coverage
All core requirements specified in [feature-home-topics-snapshot-design.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/tasks/feature-home-topics-snapshot-design.md) are fully implemented:
- **Lightweight Endpoint**: The new route `GET /topics/home` is successfully added.
- **Minimized Schema**: The response matches the requested schema exactly, returning `generated_at`, `topic_date`, and `items` with only the essential topic card fields (`id`, `topic_date`, `title_ko`, `summary_ko`, `keywords`, `source_count`, `article_count`).
- **Query Optimization**: The query avoids detail joins (such as `topic_articles` or `articles`) and eliminates the pagination total count query.
- **API Preservation**: Existing `GET /topics` and `GET /topics/{id}` endpoints remain unmodified.
- **Design & Caching Documentation**: Future cache/snapshot strategies and subsequent task sequences are comprehensively documented in [home-topics-snapshot-cache-strategy.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/design/home-topics-snapshot-cache-strategy.md).

## Code Quality / Maintainability
- **Route Shadowing**: The route `/topics/home` is defined *before* `/topics/{topic_id}` in [topics.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/routers/topics.py), preventing Starlette/FastAPI from routing home requests to the detail path.
- **Clean Execution**: Database query values use parameterized binding via SQLAlchemy's `text` mappings.
- **Robust Test Coverage**: New test cases in [test_topics_api.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/tests/test_topics_api.py) verify:
  1. Router registration of `/topics/home`.
  2. Correct field exclusion and pagination omission under success conditions.
  3. Proper null handling of `topic_date` when database rows are empty.

## Security Review
- **SQL Injection Prevention**: The query dynamically binds the limit using `{"limit": HOME_TOPICS_LIMIT}` via SQLAlchemy bind parameters, eliminating injection risks.
- **Metadata Omission**: Internal pipeline metadata (such as `provider`, `model`, `confidence`, and `summary_input_hash`) are omitted from public home page payloads, reducing internal system exposure.
- **No Secret Alteration**: No `.env`, secrets, or service connection parameters were modified.

## Operational Risk
- **No DB Down-Time**: There are no database migrations, schema edits, or index changes included, meaning zero DB schema compatibility risk.
- **Read-Only Safeties**: The new endpoint is read-only. It executes no update or insert queries against PostgreSQL/Supabase.
- **No Infra Impact**: No Kubernetes manifests (`k8s/*`), Dockerfiles, or CI/CD pipelines are altered.

## Scope Control
- **Targeted Modifications**: The code changes are restricted to:
  - [topics.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/routers/topics.py) (route implementation)
  - [test_topics_api.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/tests/test_topics_api.py) (unit tests)
- **Workflow & Documentation Consistency**: Relevant documentation changes are isolated to [ARCHITECTURE.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/ARCHITECTURE.md), [RUNBOOK.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/RUNBOOK.md), and the design directory. No unrelated system files are modified.

## Verification Review
- **Verification Conformity**: The verification logs in [feature-home-topics-snapshot-design.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/verification/feature-home-topics-snapshot-design.md) accurately describe the commands executed (python syntax checks, unittest discovers, name-only check, and git diff checks).
- **Safety Transparency**: The log correctly records that local HTTP checks and production curls were bypassed because the environment lacked a live database connection and production deployment is handled manually.

## Documentation Review
- **Architecture Updates**: [ARCHITECTURE.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/ARCHITECTURE.md) has been updated with the flow of `/topics/home` and lists the endpoint correctly.
- **Runbook Additions**: [RUNBOOK.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/RUNBOOK.md) now includes curl verification examples for testing `/topics/home` in production.
- **Strategy Documentation**: [home-topics-snapshot-cache-strategy.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/design/home-topics-snapshot-cache-strategy.md) outlines valid caching choices (Redis, DB snapshots, Next.js revalidate) and maps out task priorities for future development.

## Problems Found
No blocking code bugs or design flaws were identified. However, three minor architectural considerations were noted:
1. **Lack of Index**: The query sorts by `order by topic_date desc, article_count desc, source_count desc, id desc`. The database only has an index on `topic_date desc`. As the number of topic records increases, this sort could become inefficient.
2. **Draft Filtering**: The new route selects topics regardless of their `status` column. Currently, all pipeline items default to `draft`. If a workflow is later added to transition topics from `draft` to `published`, this query will continue returning unpublished drafts.
3. **Pydantic Response Model**: Unlike many FastAPI routes, this endpoint returns a plain dictionary instead of using a Pydantic `response_model` to enforce/document the shape in Swagger UI, matching the existing topics router style.

## Required Fixes Before PR
None. The code compiles, matches the current style of the topics router, passes unit tests, and satisfies all task constraints.

## Optional Improvements
1. **Composite Index**: If the topics table size becomes large, consider adding a composite index to avoid sorting overhead:
   ```sql
   create index if not exists idx_topics_home_sort on topics (topic_date desc, article_count desc, source_count desc, id desc);
   ```
2. **Draft Filtering Prep**: Add a comment or planning note to filter by `status = 'published'` if a topic approval workflow is introduced in the future.
3. **Response Model**: Define a Pydantic schema for `/topics/home` to improve Swagger `/docs` documentation quality.

## Suggested Test Commands
To verify the router changes locally, run the following test commands:
- **Run Topics API tests**:
  ```bash
  python -m unittest tests.test_topics_api -v
  ```
- **Run complete unit test discovery suite**:
  ```bash
  python -m unittest discover -s tests -v
  ```
- **Syntax check files**:
  ```bash
  python -m py_compile app/routers/topics.py tests/test_topics_api.py
  ```
- **Check for workspace git cleanliness**:
  ```bash
  git diff --check
  ```

## Verdict
**PASS**
The implementation is safe, correct, and fully complies with all requirement constraints and code styling guidelines of NewsLab.
