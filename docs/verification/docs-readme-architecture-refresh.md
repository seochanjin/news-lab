# Verification: README 및 아키텍처 문서 현행화

## Verification Status

passed

## Verification Scope

- UNIT-01 compared the current `README.md`, Architecture, Runbook, Kubernetes
  manifests, GitHub Actions workflow, cache implementation and existing
  Production Verification evidence.
- UNIT-02 connected the user-provided representative architecture image to
  README and the Architecture index, then aligned the public request path,
  hybrid K3s topology and external operation boundaries with that image.
- UNIT-03 refreshed the README project introduction, features, data flow,
  component boundaries and document navigation.
- UNIT-04 documented Redis cache-aside and fail-open behavior, the three
  Pipeline-driven Home Cache prewarm paths, their TTL policy and the durable
  PostgreSQL/Supabase boundary in README and Architecture documents.
- UNIT-05 documented the immutable-image manifest-PR and Argo CD Manual Sync
  approval chain, hybrid K3s placement, monitoring and Tailscale operations.
- UNIT-06 reconciled README, Architecture, Runbook, manifests and workflow
  terminology and confirmed that Review artifacts had no approved finding.
- UNIT-07 ran the Task's final documentation gates and completed the
  Verification, PR and Devlog artifacts. No application or infrastructure
  change and no new production verification were performed in this Task.

## Commands Run

Command:
`git branch --show-current && git status --short`

Result:
- Branch was `docs/readme-architecture-refresh`.
- Pre-existing worktree changes were present in `docs/tasks/main.md` and the
  branch task/review/fix/verification/PR/devlog artifacts, together with
  `docs/images/newslab-architecture_R1.png`. They were treated as user changes.

Status: passed

## Approved Fixes Verification

Command:
`rg -n -A4 -B2 'kubectl get cronjob|curl .*health' docs/runbooks/backend-deploy.md`

Result:
- Exit code 0. Argo CD diff와 Sync 후 image 확인 명령이
  `news-rss-collector`, `news-daily-topic-pipeline`,
  `news-three-day-topic-pipeline`, `news-weekly-topic-pipeline`을 명시한다.
- Production health HEAD/GET이 `curl --fail` 또는 `curl --fail-with-body`를 사용해
  HTTP 4xx/5xx에서 non-zero exit status를 반환하도록 문서화됐다.

Status: passed

Command:
Task fence 목록을 `rg`로 확인한 뒤, opening/closing fence를 추적하고 언어가 없는
opening fence 또는 닫히지 않은 fence에서 실패하는 `awk` 검사를 실행했다.

Result:
- 두 command 모두 exit code 0. 여섯 기존 unlabeled opening fence는 모두
  `text`로 지정됐고, 나머지 opening fence는 `bash`다.
- Unlabeled opening fence와 unclosed fence가 없다.

Status: passed

Command:
Verification status와 UNIT-06 historical 문구를 `rg`로 확인하고, 정확히
`## Verification Status`인 heading 수가 하나인지 `awk`로 검사했다.

Result:
- 두 command 모두 exit code 0. Canonical `Verification Status` heading은 하나며
  값은 `passed`다.
- UNIT-06은 UNIT-07 이전 historical snapshot으로 명시됐고 당시 `pending` 상태는
  과거형으로 구분됐다.

Status: passed

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`

Result:
- Exit code 0. Branch는 `docs/readme-architecture-refresh`다.
- 현재 worktree에는 Approved Fixes 대상 문서와 적용 전부터 존재한 CodeRabbit
  Review 변경만 있다. Review 문서는 이번 적용에서 수정하지 않았다.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- 출력 없음. Application, script, Kubernetes manifest, workflow, database,
  migration과 dependency 경로는 변경되지 않았다.

Status: passed

Command:
`git diff --check`

Result:
- Exit code 0, 출력 없음. 당시 tracked diff에 whitespace 오류가 없다.

Status: passed

### Approved Fixes Evidence Notes

- Application test suite는 documentation-only Approved Fixes 범위가 아니므로
  실행하지 않았고 통과로 기록하지 않는다.
- Python 파일을 만들거나 수정하지 않아 한글 docstring 변경 대상이 없다.
- Production API request, Kubernetes/Argo CD 변경, DB 작업, `git push`와
  `git merge`를 실행하지 않았다.

## UNIT-07 Verification

Command:
Task-provided repository consistency searches for the representative image,
immutable full Git SHA policy, Redis/cache prewarm, workload manifests and
CronJob schedules across `README.md`, `docs`, `.github/workflows`, `k8s` and
`app`.

Result:
- Exit code 0. README references
  `docs/images/newslab-architecture_R1.png`, while the Architecture index uses
  the equivalent `images/newslab-architecture_R1.png` relative path.
- Current-state README and Architecture documents use the immutable full Git
  SHA policy. The five `seocj/news-api:latest` matches are confined to the
  explicitly labeled pre-immutable baseline in
  `docs/architecture/argocd-manual-sync-design.md`.
- Daily, 3-day and Weekly keys and TTLs match implementation and manifests at
  `108000`, `108000` and `691200` seconds. PostgreSQL/Supabase remains the
  Source of Truth and Redis remains a fail-open prewarmed cache.
- RSS, Daily, 3-day and Weekly schedules match the manifests at `03:00`,
  `04:00`, `05:00` and Monday `00:30` in `Asia/Seoul`.

Status: passed

Command:
`test -f docs/images/newslab-architecture_R1.png`

Result:
- Exit code 0. The user-provided representative image exists.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`.

Status: passed

Command:
`git branch --show-current`, `git status --short`, `git diff --stat`, and
`git diff --name-only`.

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- Tracked changes are limited to README, Architecture/Runbook documents and
  `docs/tasks/main.md`. Branch workflow artifacts and the user-provided image
  are untracked and therefore are not included in ordinary `git diff` output.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. Application code, scripts, Kubernetes manifests, workflows,
  database/migration and dependency paths were not changed.

Status: passed

Command:
`git diff --check`

Result:
- Exit code 0 with no output. The tracked diff has no whitespace errors.

Status: passed

Command:
Final reconciliation of branch/status/diff scope, prohibited-path diff,
`git diff --check`, trailing whitespace across tracked and untracked Task
documents, UNIT checklist state, Verification Status and non-empty PR/Devlog
artifacts.

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- The prohibited-path diff and whitespace checks produced no findings.
- UNIT-01 through UNIT-07 are checked, Verification Status is `passed`, and
  both PR and Devlog artifacts are non-empty.

Status: passed

### UNIT-07 Results

- The final documentation checks passed and the Verification Status is
  `passed`.
- PR and Devlog drafts were completed from this Verification record.
- The Task checklist was reconciled after the final artifact and whitespace
  checks completed.

### UNIT-07 Skipped and Human-controlled Checks

- The application test suite was not run because this Task changes only
  documentation and the user-provided image reference; it is not recorded as
  passed.
- No new production verification was required or performed. Current DNS,
  rollout, workload placement, cache state and service health are not claimed
  without new human-provided logs.
- PR merge, Argo CD Manual Sync, Kubernetes changes, Docker push, Supabase SQL,
  production API requests, `git push` and `git merge` were not performed.
- No Python file was created or modified, so the Python documentation policy
  did not require docstring changes.

## UNIT-06 Verification

> Historical snapshot: 이 section은 UNIT-07 최종 검증 전에 기록한 UNIT-06
> 시점의 상태다. 문서 상단의 `Verification Status: passed`가 현재 전체 Task의
> canonical status다.

Command:
Task-provided repository consistency searches for architecture image/current
image policy, Redis prewarm/TTL and CronJob schedules across `README.md`,
Architecture, application, manifests and workflow files.

Result:
- Exit code 0. README and the Architecture index reference
  `newslab-architecture_R1.png`; the old representative path is absent.
- The only `seocj/news-api:latest` matches under current Architecture scope are
  five entries in `argocd-manual-sync-design.md`'s explicitly labeled
  pre-immutable transition baseline. Current desired-state documents use the
  full Git SHA policy.
- Daily, 3-day and Weekly cache keys and TTLs agree across README,
  Architecture, implementation and manifests: `108000`, `108000`, and
  `691200` seconds.
- RSS, Daily, 3-day and Weekly schedules agree with manifests at `03:00`,
  `04:00`, `05:00`, and Monday `00:30` in `Asia/Seoul`.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`.

Status: passed

Command:
The same read-only relative-link validation extended to `README.md`, the
Architecture and Runbook indexes, and all `docs/architecture/*.md` and
`docs/runbooks/*.md` files.

Result:
- Exit code 0 with `architecture/runbook relative links passed (16 files)`.

Status: passed

Command:
`rg -n 'full Git SHA|manifest PR|OutOfSync|Manual Sync|automated sync|latest' README.md docs/ARCHITECTURE.md docs/architecture/k3s-runtime.md docs/runbooks/backend-deploy.md .github/workflows/docker-build.yml k8s/argocd/news-api-application.yaml`, together with the targeted node placement,
monitoring and Tailscale search from the Task facts.

Result:
- Exit code 0. README, Architecture and Backend deploy Runbook use the same
  full-SHA manifest-PR, human merge review, Argo CD diff and Manual Sync chain.
- Workflow `latest` is a registry-only auxiliary tag; current manifest and
  rollback descriptions do not use it as desired state.
- Node selectors, monitoring selectors/tolerations and documentation agree on
  the three node roles. Public ingress and Tailscale operator/hybrid-node
  routing remain separate.

Status: passed

Command:
`rg -n 'run_weekly_topic_pipeline|weekly_topic_runs|weekly_topics|weekly_topic_articles|weekly-topics/home|Daily·3-day·Weekly|108000|691200' docs/architecture/overview.md docs/architecture/database.md docs/RUNBOOK.md docs/runbooks/routine-check.md docs/runbooks/cronjobs.md db/migrations/008_create_weekly_topic_tables.sql k8s`

Result:
- Exit code 0. The Architecture overview and Database Architecture now include
  the Weekly Pipeline and its three tables.
- Runbook index, routine check and detailed CronJob Runbook now cover all three
  Home APIs and the Daily/3-day/Weekly TTL policy.

Status: passed

Command:
`git branch --show-current`, `git status --short`, `git diff --stat`, and
`git diff --name-only`.

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- Tracked changes remain in documentation scope. Branch workflow artifacts and
  the user-provided image remain untracked; ordinary `git diff` does not include
  their contents.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. UNIT-06 did not modify prohibited application, script, manifest,
  workflow, database, migration or dependency paths.

Status: passed

Command:
`git diff --check`, followed by a trailing-whitespace search for the untracked
Task, Verification and Approved Fixes artifacts.

Result:
- Exit code 0 with no output. Tracked changes and the checked untracked workflow
  artifacts have no whitespace errors.

Status: passed

Command:
`rg -n '^- \[[ x]\] UNIT-0[1-7]:' docs/tasks/docs-readme-architecture-refresh.md`

Result:
- Exit code 0. UNIT-01 through UNIT-06 are checked and UNIT-07 remains
  unchecked.

Status: passed

### UNIT-06 Results

- `docs/architecture/overview.md` now includes the Weekly Pipeline, Redis Home
  Cache responsibility, all three result families and the actual
  FastAPI/Pipeline-to-storage boundary.
- `docs/architecture/database.md` now lists and explains the Weekly run, result
  and relation tables defined by migration 008.
- The Runbook index and routine check now cover all three Home APIs, cache TTLs
  and Weekly operational status without changing any operation.
- Antigravity and CodeRabbit Review artifacts contain no finding. Approved
  Fixes therefore records `없음`, and no Review output was used as direct
  authorization for a change.
- Historical pre-transition `latest` wording remains as dated design evidence;
  it is not presented as current desired state.

### UNIT-06 Manual or Production Verification

- No production command or new production verification was performed.
- Current DNS, node placement, rollout, cache state and service health were not
  claimed without human-provided logs.

### UNIT-06 Pending Verification

- UNIT-07 remains pending and was not started.
- At this UNIT-06 historical snapshot, the overall Verification Status was
  `pending`; final whole-task verification, PR/Devlog completion and task-wide
  status reconciliation belonged to UNIT-07 and are recorded above.

### UNIT-06 Evidence Notes

- No Python file was created or modified, so the Python documentation policy did
  not require docstring changes.
- No application test suite was run because UNIT-06 changes documentation only;
  it is not recorded as passed.
- No `git push`, `git merge`, `kubectl`, Argo CD Sync, Docker push, Supabase SQL,
  production API request or other production-impacting command was run.

Command:
`rg --files docs/architecture docs/runbook k8s .github/workflows | sort`

Result:
- The command returned exit code 2 because `docs/runbook` does not exist.
- The actual runbook directory is `docs/runbooks`; subsequent inspection used
  that path.

Status: failed

Notes:
- This was a path-discovery error only. It did not modify files or prevent the
  corrected repository investigation.

Command:
`rg -n 'newslab-architecture|seocj/news-api:latest|full Git SHA|Redis|prewarm|Argo CD|Manual Sync|Tailscale' README.md docs .github/workflows k8s`

Result:
- Exit code 0. The search located the old README image path and current-state
  `latest` wording, current immutable image/Manual Sync documentation, Redis and
  prewarm records, and historical documents that intentionally describe the
  pre-transition `latest` baseline.
- Output was large and truncated by the command runner, so targeted searches
  below were used for the recorded conclusions.

Status: passed

Command:
`rg -n 'kind: Deployment|kind: CronJob|image:|schedule:|nodeSelector:|workload: app' k8s`

Result:
- Exit code 0. `news-api`, `news-redis`, and all four CronJobs select
  `workload: app`.
- `news-api` and the four CronJobs use the same full Git SHA image tag in the
  checked-in manifests. Redis uses `redis:7.2-alpine`.
- The four CronJob schedules are `0 3 * * *`, `0 4 * * *`, `0 5 * * *`, and
  `30 0 * * 1`.

Status: passed

Command:
`test -f docs/images/newslab-architecture_R1.png`

Result:
- Exit code 0. The user-provided image exists.

Status: passed

Command:
`rg -n 'docs/images/newslab-architecture_R1\.png' README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 1 with no matches. The new image is not referenced yet.

Status: failed

Notes:
- This is a confirmed input to UNIT-02, not a UNIT-01 blocker.

Command:
`rg -n 'docs/images/newslab-architecture\.png|seocj/news-api:latest' README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 0. `README.md` still references
  `docs/images/newslab-architecture.png` and describes the current Backend and
  CronJob image as `seocj/news-api:latest`.
- Additional `latest` matches in
  `docs/architecture/argocd-manual-sync-design.md` are explicitly inside the
  immutable-transition baseline/history. The same document separately defines
  the current full Git SHA policy, so those historical matches are not current
  desired-state defects.

Status: passed

Command:
`rg -n 'topics:home:v1|three-day-topics:home:v1|weekly-topics:home:v1|108000|691200|fail-open|prewarm' README.md docs/ARCHITECTURE.md docs/architecture app k8s`

Result:
- Exit code 0. `app/home_topics_cache.py` defines the three keys and TTLs
  `108000`, `108000`, and `691200`; API and Pipeline manifests use the same
  values.
- `app/home_topics_payload.py` and the three Pipeline entry points show that
  FastAPI/Pipelines read PostgreSQL payloads and write Redis, with cache errors
  isolated as fail-open behavior.
- `docs/architecture/backend-api.md` already documents all three keys, TTLs,
  PostgreSQL fallback and post-save Pipeline overwrite. README and the
  Architecture index do not yet expose this relationship.

Status: passed

Command:
`rg -n '^\s*schedule:|timeZone:|news-rss-collector|news-daily-topic-pipeline|news-three-day-topic-pipeline|news-weekly-topic-pipeline' k8s README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 0. Manifest and current README/Pipeline Architecture schedules
  agree: RSS `03:00`, Daily `04:00`, 3-day `05:00`, and Weekly Monday `00:30`,
  all in `Asia/Seoul`.

Status: passed

Command:
`rg -n 'Public DNS|Oracle Public IP|Traefik Ingress|Kubernetes Service|Application Pod|Frontend Service|Backend Service|Next.js|FastAPI' README.md docs/ARCHITECTURE.md docs/architecture docs/runbooks`

Result:
- Exit code 0, but matches were limited to general FastAPI/Next.js wording.
- The required public request path and explicit Frontend/Backend Service
  separation are not currently described in these entry documents.

Status: passed

Command:
`rg -n 'Current task|Current verification|docs-readme-portfolio-refresh|newslab-architecture\.png' README.md docs/ARCHITECTURE.md docs/architecture docs/RUNBOOK.md docs/runbooks`

Result:
- Exit code 0. README still links its Current task and Current verification to
  `docs-readme-portfolio-refresh` and uses the old architecture image path.

Status: passed

Command:
`rg -n 'latest|rollout restart|full Git SHA|manifest.*PR|Manual Sync|Redis|prewarm|three-day|weekly|Tailscale|Public DNS|Oracle Public IP|Frontend|Backend' docs/RUNBOOK.md docs/runbooks README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 0. The Runbook index and Argo CD plan describe the current immutable
  manifest-PR/Manual-Sync policy.
- `docs/runbooks/backend-deploy.md` still presents direct manifest apply and
  `kubectl rollout restart` as the main image rollout procedure, which conflicts
  with the current deployment policy and requires a minimal later refresh.
- `docs/runbooks/routine-check.md` omits the Weekly Home endpoint and Weekly
  status item. `docs/runbooks/cronjobs.md` already contains all three prewarm
  procedures and their TTL expectations.

Status: passed

Command:
`rg -n 'arm-master-node|arm-worker-node|pi-worker-node|NoSchedule|workload: app|observability=true|node-role=news-edge-worker' docs/verification/infra-pi-worker-join.md docs/verification/infra-monitoring-baseline.md docs/verification/feature-argocd-backend-manual-sync.md docs/verification/feature-backend-immutable-image-gitops.md`

Result:
- Exit code 0. Existing human-provided verification records the three ARM64
  nodes, the Pi `node-role=news-edge-worker:NoSchedule` taint, Backend Pods on
  `arm-worker-node`, monitoring core on `arm-worker-node`, and node-exporter on
  all three nodes.
- These are point-in-time Production results. The repository manifests prove
  scheduling constraints, but not current live labels, taints, readiness or Pod
  placement.

Status: passed

Command:
`rg -n 'Pipeline-driven prewarm|prewarm.*passed|topics:home:v1|three-day-topics:home:v1|weekly-topics:home:v1|EXISTS|TTL' docs/verification/chore-verify-home-cache-prewarm.md docs/verification/feat-home-cache-prewarm.md`

Result:
- Exit code 0. `docs/verification/chore-verify-home-cache-prewarm.md` has overall
  status `passed` and records point-in-time Production evidence for Daily,
  3-day, and Weekly Pipeline-driven prewarm before the first Home API request.

Status: passed

Command:
`git branch --show-current`, `git status --short`, `git diff --stat`, and
`git diff --name-only`

Result:
- Branch remained `docs/readme-architecture-refresh`.
- Status still showed the pre-existing tracked `docs/tasks/main.md` change and
  the branch artifacts/image as untracked.
- Tracked diff output contained only `docs/tasks/main.md`; because the current
  Task and Verification files were already untracked at unit start, ordinary
  `git diff` does not display their content changes.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. UNIT-01 did not change any prohibited application,
  infrastructure, workflow, database or dependency path.

Status: passed

Command:
`git diff --check`

Result:
- No output. The tracked worktree diff has no whitespace errors.

Status: passed

Notes:
- Ordinary `git diff --check` does not include untracked Task/Verification
  files, so they were also checked with the trailing-whitespace search below.

Command:
`rg -n '[ \t]+$' docs/tasks/docs-readme-architecture-refresh.md docs/verification/docs-readme-architecture-refresh.md`

Result:
- Exit code 1 with no matches. Neither UNIT-01 artifact contains trailing
  whitespace.

Status: passed

Command:
`rg -n '^- \[[ x]\] UNIT-0[1-7]:' docs/tasks/docs-readme-architecture-refresh.md`

Result:
- UNIT-01 is checked. UNIT-02 through UNIT-07 remain unchecked.

Status: passed

## Results

### UNIT-01 repository facts

- Backend request routing directly proven by this repository is
  `Ingress/news-api-ingress` (Traefik) → `Service/news-api` → Pods labeled
  `app: news-api`. The Backend Service selects only the FastAPI Deployment.
- Public DNS resolution and the mapping to an Oracle public IP are external
  infrastructure facts; checked-in manifests only prove host rules and the
  in-cluster route. They require human-provided production evidence when a
  current-state verification claim is needed.
- This backend repository contains no Frontend Deployment or Service manifest.
  Existing Architecture history says those resources belong to the separate
  `news-lab-web` repository, but their current replicas, selector, image and
  placement cannot be re-proven from this repository. Updated diagrams and prose
  must keep Frontend and Backend Services distinct and qualify the Frontend
  boundary.
- `.github/workflows/docker-build.yml` builds and pushes `linux/arm64` images
  tagged with the full Git SHA and the auxiliary `latest` tag. After a successful
  build, `update-manifest` updates exactly the Backend Deployment and four
  CronJobs to the full SHA and opens a manifest PR. It does not deploy directly.
- `k8s/argocd/news-api-application.yaml` tracks `main/k8s`, excludes the shared
  ClusterIssuer, does not recurse into monitoring/Argo CD subdirectories, and has
  no automated sync policy. Current deployment documentation must retain human
  manifest review, merge, Argo CD diff review and Manual Sync boundaries.
- PostgreSQL/Supabase is the durable source of truth. Redis is a persistence-free,
  deletable cache used by FastAPI cache-aside reads and by Daily/3-day/Weekly
  Pipelines after successful PostgreSQL writes. Redis and PostgreSQL do not
  communicate directly.
- All five Backend code workloads select `workload: app`; Redis does too.
  Monitoring core selects `observability: "true"`, and node-exporter has
  tolerations for control-plane/master and the Pi edge-worker taint. Actual node
  labels, taints and placement remain live-state facts supported only by dated
  human verification.

### UNIT-01 confirmed documentation gaps

- README uses the old representative image, calls `latest` the current Backend
  image, links an older task/verification, omits the three Home Cache/prewarm
  design, and describes image publication without the manifest PR and Argo CD
  Manual Sync chain.
- README/Architecture entry documents do not show the required
  User → Public DNS → Oracle Public IP → Traefik Ingress → Kubernetes Service →
  Application Pod flow or explicitly separate Frontend and Backend Services.
- `docs/architecture/overview.md` omits the Weekly Pipeline from the responsibility
  table and does not present all current result/run tables in its summary flow.
- `docs/architecture/k3s-runtime.md` omits the Weekly CronJob from its manifest
  inventory, describes Redis as Daily-only, and lacks the hybrid three-node role
  and placement summary.
- `docs/architecture/pipeline.md` has correct pipeline schedules and storage
  flows, but its flow diagrams stop before the post-save Redis prewarm step.
- `docs/architecture/backend-api.md`, `docs/ARCHITECTURE.md`,
  `docs/runbooks/cronjobs.md`, and `docs/runbooks/argocd-manual-sync-plan.md`
  contain the strongest current cache and deployment descriptions and should be
  reused rather than duplicated inconsistently.
- `docs/runbooks/backend-deploy.md` requires a minimal update because its primary
  image rollout section conflicts with the current approved GitOps path.
  `docs/runbooks/routine-check.md` should include the Weekly Home check when the
  later consistency unit reviews Runbook gaps.
- Historical `latest` and pre-transition deployment descriptions in the Argo CD
  design/plan are clearly labeled baseline/history. They are past records, not
  current desired-state defects, and should not be removed merely because the
  final stale-string search finds them.

## Manual or Production Verification

- Not performed in UNIT-01.
- Existing human-provided Production Verification was read only as dated
  evidence. No current rollout, deployment, DNS, live cluster, cache or endpoint
  state is claimed.

## Pending Verification

- UNIT-03 through UNIT-07 remain pending and were not started.
- The remaining README/Architecture/Runbook refresh, final
  stale-current-state searches, scope diff checks and final `git diff --check`
  remain for their assigned units.
- Current public DNS/Oracle IP routing, live node placement, rollout and
  production service health require human evidence if this task later needs to
  make current Production verification claims.

## Evidence Notes

- No Python, application, pipeline, Kubernetes manifest, workflow, database,
  dependency, Secret or image file was changed in UNIT-01.
- No `git push`, `git merge`, `kubectl`, Argo CD Sync, Docker push, Supabase SQL,
  production API request or other production-impacting command was run.
- UNIT-01 is complete as an investigation unit while overall Verification Status
  remains `pending`.

## UNIT-02 Verification

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- The UNIT-02 tracked diff is limited to `README.md`, `docs/ARCHITECTURE.md`,
  `docs/architecture/domains.md`, and `docs/architecture/k3s-runtime.md`.
- The pre-existing `docs/tasks/main.md` change and untracked workflow artifacts
  and image remain present. Ordinary `git diff` does not include the untracked
  Task, Verification or image files.

Status: passed

Command:
`test -f docs/images/newslab-architecture_R1.png`

Result:
- Exit code 0. The user-provided image exists; it was inspected but not edited.

Status: passed

Command:
`rg -n 'docs/images/newslab-architecture_R1\.png|images/newslab-architecture_R1\.png' README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 0. README references
  `docs/images/newslab-architecture_R1.png`, and the Architecture index uses the
  equivalent relative path `images/newslab-architecture_R1.png`.

Status: passed

Command:
`rg -n 'docs/images/newslab-architecture\.png' README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 1 with no matches. The old representative image path is absent from
  the current README and Architecture documents in scope.

Status: passed

Command:
`rg -n 'User|Public DNS|Oracle Public IP|Traefik Ingress|Kubernetes Service|Application Pod|Frontend Service|news-api Service|Next.js Pod|FastAPI Pod|arm-master-node|arm-worker-node|pi-worker-node|NoSchedule|Tailscale|Manual Sync' README.md docs/ARCHITECTURE.md docs/architecture/k3s-runtime.md docs/architecture/domains.md`

Result:
- Exit code 0. README and Architecture describe the required public request
  sequence and explicitly split Frontend Service to Next.js Pods from Backend
  `news-api` Service to FastAPI Pods.
- The three node roles, Pi `NoSchedule` boundary, future explicit-toleration
  edge/batch boundary, public-ingress/Tailscale separation and external
  operation paths are present.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`. Both representative image
  references and the existing document links resolve locally.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. No prohibited application, script, manifest, workflow, database or
  dependency path was changed.

Status: passed

Command:
`git diff --check`

Result:
- No output. The tracked worktree diff has no whitespace errors.

Status: passed

Command:
`if rg -n '[ \t]+$' docs/tasks/docs-readme-architecture-refresh.md docs/verification/docs-readme-architecture-refresh.md; then exit 1; fi`

Result:
- Exit code 0 with no matches. The untracked Task and Verification artifacts
  have no trailing whitespace.

Status: passed

Command:
`rg -n '^- \[[ x]\] UNIT-0[1-7]:' docs/tasks/docs-readme-architecture-refresh.md`

Result:
- UNIT-01 and UNIT-02 are checked. UNIT-03 through UNIT-07 remain unchecked.

Status: passed

### UNIT-02 Results

- The new representative image is connected from both entry documents.
- Prose now distinguishes the shared logical request stages from the separate
  Frontend and Backend Ingress/Service/Pod chains.
- K3s documentation matches the image's control-plane, Oracle application
  worker and tainted Raspberry Pi roles, while qualifying live placement and
  external DNS/IP facts as requiring human-provided evidence.
- GitHub Actions/Docker Hub, Argo CD Manual Sync, managed PostgreSQL/Supabase,
  Let's Encrypt/cert-manager and operator Tailscale access are separated from
  the public user request path.

### UNIT-02 Manual or Production Verification

- Not performed and not required for this documentation-only unit.
- No current DNS, Oracle public IP, live node placement, rollout, deployment or
  service-health claim was made without new human-provided logs.

### UNIT-02 Pending Verification

- UNIT-03 through UNIT-07 remain pending and were not started.
- Overall Verification Status remains `pending`.

### UNIT-02 Evidence Notes

- No Python, application, pipeline, Kubernetes manifest, workflow, database,
  dependency, Secret or image file was changed in UNIT-02.
- No application test suite was run because UNIT-02 changes documentation only;
  it is not recorded as passed.
- No production-impacting command was run.

## UNIT-03 Verification

Command:
`rg -n 'include_router|@router\.(get|post)|APIRouter' app/main.py app/routers`

Result:
- Exit code 0. FastAPI registers source, article, collector, extractor, raw
  article, Daily Topic, 3-day Topic and Weekly Topic routers.
- The three Topic router groups each expose archive, Home and detail GET paths.

Status: passed

Command:
`rg -n 'CREATE TABLE|create table' db/migrations | head -n 160`

Result:
- Exit code 0. Migrations contain durable tables for collector/extractor runs,
  raw articles, article embeddings and independent Daily, 3-day and Weekly
  Topic results, relations and applicable run histories.

Status: passed

Command:
`rg --files docs/architecture docs/design docs/agent docs/runbooks | sort`

Result:
- Exit code 0. Every detailed Architecture, design, workflow and Runbook target
  selected for the README navigation structure exists in the repository.

Status: passed

Command:
`git show HEAD:README.md | sed -n '1,230p'`

Result:
- Exit code 0. The committed README was compared with the working README so the
  existing UNIT-02 image, request-path and topology edits could be preserved
  while changing only the UNIT-03 sections.

Status: passed

Command:
`rg -n '개인 운영 뉴스 플랫폼|PostgreSQL/Supabase|FastAPI backend|Next.js frontend|archive / Home / detail|Architecture index|Runbook index|현재 Task|현재 Verification' README.md`

Result:
- Exit code 0. README now identifies PostgreSQL/Supabase as durable storage,
  separates the FastAPI backend from the external Next.js frontend, describes
  the period-specific read flow, and links the current Architecture, Runbook,
  Task and Verification entry points.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`. All relative document and
  image targets in both entry documents resolve locally.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. No prohibited application, script, manifest, workflow, database or
  dependency path was changed.

Status: passed

Command:
`git diff --check`

Result:
- No output. The tracked worktree diff has no whitespace errors.

Status: passed

Command:
`if rg -n '[ \t]+$' README.md docs/tasks/docs-readme-architecture-refresh.md docs/verification/docs-readme-architecture-refresh.md; then exit 1; fi`

Result:
- Exit code 0 with no matches. README and the untracked Task and Verification
  artifacts have no trailing whitespace.

Status: passed

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- Tracked changes remain limited to the existing documentation scope:
  `README.md`, Architecture documents and `docs/tasks/main.md`. Branch workflow
  artifacts and the user-provided image remain untracked and therefore are not
  included in ordinary `git diff` output.

Status: passed

Command:
`rg -n '^- \[[ x]\] UNIT-0[1-7]:' docs/tasks/docs-readme-architecture-refresh.md`

Result:
- Exit code 0. UNIT-01 through UNIT-03 are checked; UNIT-04 through UNIT-07
  remain unchecked.

Status: passed

### UNIT-03 Results

- README now presents NewsLab as a period-specific news Topic service and makes
  this repository's FastAPI/backend responsibility distinct from the separate
  Next.js frontend repository.
- The feature list reflects the registered read APIs, execution histories and
  independent Daily, 3-day and Weekly Topic products.
- The data flow explains durable article collection, period-specific Topic
  processing, delayed raw acquisition for Summary evidence, result persistence
  and stored-result reads without implying request-time Pipeline execution.
- The system component table distinguishes frontend, backend, database,
  runtime, ingress, TLS and operator-network responsibilities.
- Document navigation now starts from Architecture and Runbook indexes, routes
  readers to focused detail documents, and links the current Task and
  Verification artifacts.

### UNIT-03 Manual or Production Verification

- Not performed and not required for this documentation-only unit.
- No current service accessibility, DNS, cluster, deployment, Pipeline or data
  state was asserted from a new production check.

### UNIT-03 Pending Verification

- UNIT-04 through UNIT-07 remain pending and were not started.
- Redis cache/prewarm policy belongs to UNIT-04; immutable GitOps, final node
  placement and external operations belong to UNIT-05.
- Overall Verification Status remains `pending`.

### UNIT-03 Evidence Notes

- No Python file was created or modified, so the Python documentation policy
  did not require docstring changes.
- No application test suite was run because UNIT-03 changes documentation only;
  it is not recorded as passed.
- No production-impacting command was run.

## UNIT-04 Verification

Command:
`sed -n '1,320p' app/home_topics_cache.py && sed -n '1,420p' app/home_topics_payload.py && rg -n -C 14 'prewarm|db_write_performed|saved_topic_count|run_status' scripts/run_daily_topic_pipeline.py scripts/run_three_day_topic_pipeline.py scripts/run_weekly_topic_pipeline.py`

Result:
- Exit code 0. The implementation defines `topics:home:v1`,
  `three-day-topics:home:v1`, and `weekly-topics:home:v1` with default TTLs
  108000, 108000, and 691200 seconds.
- Home payload functions read Redis first, fall back to PostgreSQL on a miss or
  cache failure, and attempt a fail-open cache store. Prewarm functions bypass
  Redis GET and rebuild the payload from PostgreSQL before overwrite.
- Daily prewarm requires an execute result with `db_write_performed`; 3-day and
  Weekly prewarm require at least one saved publishable Topic after successful
  run completion. Dry-run and no-write/no-result paths skip prewarm.

Status: passed

Command:
`rg -n 'HOME_TOPICS_CACHE_TTL_SECONDS|THREE_DAY_HOME_TOPICS_CACHE_TTL_SECONDS|WEEKLY_HOME_TOPICS_CACHE_TTL_SECONDS|REDIS_URL' k8s/news-api.yaml k8s/news-daily-topic-pipeline-cronjob.yaml k8s/news-three-day-topic-pipeline-cronjob.yaml k8s/news-weekly-topic-pipeline-cronjob.yaml`

Result:
- Exit code 0. The API manifest and period-specific Pipeline manifests provide
  the matching Redis URL and TTL environment variable names.
- Manifest values are 108000 seconds for Daily and 3-day, and 691200 seconds for
  Weekly.

Status: passed

Command:
`rg -n 'topics:home:v1|three-day-topics:home:v1|weekly-topics:home:v1|108000|691200|fail-open|prewarm' README.md docs/ARCHITECTURE.md docs/architecture app k8s`

Result:
- Exit code 0. README, the Architecture index, Pipeline Architecture and the
  existing Backend API Architecture now agree with the implementation and
  manifests on all three keys and TTLs.
- The entry documents describe PostgreSQL/Supabase as Source of Truth, Redis as
  a deletable fail-open cache, Pipeline post-save prewarm and the absence of a
  direct PostgreSQL-to-Redis communication path.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`. The newly added links to
  Backend API Architecture, Pipeline Architecture and the existing prewarm
  Production Verification resolve locally.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. UNIT-04 did not change application, script, manifest, workflow,
  database, migration or dependency paths.

Status: passed

Command:
`git diff --check`

Result:
- No output. The tracked worktree diff has no whitespace errors.

Status: passed

Command:
`if rg -n '[ \t]+$' README.md docs/ARCHITECTURE.md docs/architecture/pipeline.md docs/tasks/docs-readme-architecture-refresh.md docs/verification/docs-readme-architecture-refresh.md; then exit 1; fi`

Result:
- Exit code 0 with no matches. UNIT-04 documents and the untracked Task and
  Verification artifacts have no trailing whitespace.

Status: passed

Command:
`git branch --show-current`, `git status --short`, `git diff --stat`, and
`git diff --name-only`

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- Tracked changes remained in the documentation scope. UNIT-04 added
  `docs/architecture/pipeline.md` to the existing README/Architecture changes;
  pre-existing branch artifacts and the user-provided image remain untracked.
- Ordinary `git diff` still does not include the untracked Task and Verification
  content.

Status: passed

### UNIT-04 Results

- README now explains the Home API cache-aside request path, Redis fail-open
  behavior, all three Pipeline-to-key prewarm paths and exact TTLs.
- The Architecture index separates the durable PostgreSQL/Supabase Source of
  Truth from the disposable Redis layer and identifies FastAPI/Pipelines as the
  clients of both stores.
- Pipeline Architecture records the actual post-save conditions and skip
  behavior for Daily, 3-day and Weekly prewarm.
- The existing human-provided Production Verification is linked as dated
  evidence that all three keys existed before the first Home API request and
  retained decreasing TTLs after that request; no new live-state claim was made.

### UNIT-04 Manual or Production Verification

- No production command or new production verification was performed.
- Existing `chore-verify-home-cache-prewarm` human evidence was read only and
  explicitly retained as point-in-time evidence.

### UNIT-04 Pending Verification

- UNIT-05 through UNIT-07 remain pending and were not started.
- Immutable GitOps, final hybrid-node/monitoring/Tailscale documentation,
  cross-document consistency review and final task verification remain in their
  assigned units.
- Overall Verification Status remains `pending`.

### UNIT-04 Evidence Notes

- No Python file was created or modified, so the Python documentation policy did
  not require docstring changes.
- No application test suite was run because UNIT-04 changes documentation only;
  it is not recorded as passed.
- No `git push`, `git merge`, `kubectl`, Argo CD Sync, Docker push, Supabase SQL,
  production API request or other production-impacting command was run.

## UNIT-05 Verification

Command:
`rg -n 'image:|nodeSelector:|tolerations:|workload: app|observability|node-role=news-edge-worker|schedule:|timeZone:' k8s/news-api.yaml k8s/redis.yaml k8s/news-*-cronjob.yaml k8s/monitoring/kube-prometheus-stack-values.yaml k8s/argocd/news-api-application.yaml`, followed by targeted reads of the Argo CD Application, monitoring values, GitHub Actions workflow and existing Production Verification.

Result:
- Exit code 0. Backend Deployment, Redis and four CronJobs select
  `workload: app`; the five Backend code workloads use the same full Git SHA.
- Monitoring core selects `observability: "true"`; node-exporter tolerates the
  control-plane/master and `node-role=news-edge-worker:NoSchedule` taints.
- The Argo CD Application tracks `main/k8s` without automated sync, while the
  workflow builds `linux/arm64`, updates five workload manifests to the full
  Git SHA and opens a manifest PR after a successful build.
- Existing human-provided verification records monitoring core on
  `arm-worker-node`, node-exporter on all three nodes, the Pi worker taint, and
  successful point-in-time immutable image/Manual Sync operations.

Status: passed

Command:
`rg -n 'full Git SHA|manifest PR|OutOfSync|Manual Sync|rollback|automated sync' README.md docs/ARCHITECTURE.md docs/architecture/k3s-runtime.md docs/runbooks/backend-deploy.md .github/workflows/docker-build.yml k8s/argocd/news-api-application.yaml`

Result:
- Exit code 0. README, Architecture and the deploy Runbook now describe the
  full Git SHA image, five-workload manifest PR, human merge review, Argo CD
  `OutOfSync`/diff review, Manual Sync and full-SHA rollback path.
- The Runbook no longer presents direct apply or rollout restart as the routine
  image deployment path.

Status: passed

Command:
`rg -n 'arm-master-node|arm-worker-node|pi-worker-node|NoSchedule|workload: app|observability|node-exporter|Prometheus|Grafana|Tailscale|public ingress' README.md docs/ARCHITECTURE.md docs/architecture/k3s-runtime.md k8s`

Result:
- Exit code 0. Documentation and manifests agree on the control plane,
  application worker, tainted Pi worker, application and monitoring selectors,
  monitoring core, all-node node-exporter and Tailscale operator/hybrid-node
  role.
- README and K3s Architecture keep Tailscale separate from the public ingress
  path and qualify live placement as dated human evidence rather than a new
  production check.

Status: passed

Command:
`rg -n 'docs/images/newslab-architecture\.png|seocj/news-api:latest' README.md docs/ARCHITECTURE.md docs/architecture`

Result:
- Exit code 0 only because five matches remain in
  `docs/architecture/argocd-manual-sync-design.md` inside the explicitly labeled
  pre-immutable transition baseline.
- No README, Architecture index or K3s current desired-state description uses
  the old image path or `seocj/news-api:latest`.

Status: passed

Command:
Task-provided Python relative-link validation for `README.md` and
`docs/ARCHITECTURE.md`.

Result:
- Exit code 0 with `markdown relative links passed`.

Status: passed

Command:
`git diff --name-only -- app scripts k8s .github/workflows db migrations requirements.txt docker-compose.yml`

Result:
- No output. UNIT-05 did not change application, script, manifest, workflow,
  database, migration or dependency paths.

Status: passed

Command:
`git diff --check`

Result:
- No output. The tracked worktree diff has no whitespace errors.

Status: passed

### UNIT-05 Results

- README now presents the complete approval chain from application PR merge
  through ARM64 full-SHA image build, manifest PR, Argo CD diff/Manual Sync and
  human rollout, workload-image and production-health verification.
- K3s Architecture documents the monitoring component placement, selectors,
  tolerations, retention and disabled Alertmanager state without converting
  dated Production Verification into a current live-state claim.
- The deploy Runbook uses the approved GitOps path for deployment and rollback,
  separates read-only diff inspection from human-controlled Manual Sync, and
  defines stop conditions for unexpected changes.
- Hybrid node roles keep general application workload on `arm-worker-node`, the
  control plane free of general application workload, and the tainted Pi worker
  available only to explicitly tolerated future edge/batch work.

### UNIT-05 Manual or Production Verification

- No production command or new production verification was performed.
- Existing node, monitoring and immutable GitOps Production Verification was
  used only as dated evidence; current rollout, placement, metrics and health
  were not re-claimed.

### UNIT-05 Pending Verification

- UNIT-06 and UNIT-07 remain pending and were not started.
- Cross-document consistency review, approved Review fixes and final whole-task
  verification remain in their assigned units.
- Overall Verification Status remains `pending`.

### UNIT-05 Evidence Notes

- No Python file was created or modified, so the Python documentation policy did
  not require docstring changes.
- No application test suite was run because UNIT-05 changes documentation only;
  it is not recorded as passed.
- No `git push`, `git merge`, `kubectl`, Argo CD Sync, Docker push, Supabase SQL,
  production API request or other production-impacting command was run.

Command:
`git branch --show-current && git status --short && git diff --stat && git diff --name-only`

Result:
- Exit code 0. The branch remained `docs/readme-architecture-refresh`.
- Tracked changes remained documentation-only. UNIT-05 added
  `docs/runbooks/backend-deploy.md` to the earlier README/Architecture changes;
  branch artifacts and the user-provided image remain untracked and ordinary
  `git diff` does not include their content.

Status: passed

Command:
`rg -n '^- \[[ x]\] UNIT-0[1-7]:' docs/tasks/docs-readme-architecture-refresh.md`

Result:
- Exit code 0. UNIT-01 through UNIT-05 are checked; UNIT-06 and UNIT-07 remain
  unchecked.

Status: passed

Command:
`if rg -n '[ \t]+$' README.md docs/architecture/k3s-runtime.md docs/runbooks/backend-deploy.md docs/tasks/docs-readme-architecture-refresh.md docs/verification/docs-readme-architecture-refresh.md; then exit 1; fi`

Result:
- Exit code 0 with no matches. UNIT-05 documents and the untracked Task and
  Verification artifacts have no trailing whitespace.

Status: passed
