# Verification: NewsLab README 포트폴리오 관문 개선

## Verification Status

pending

## Verification Scope

- UNIT-01: existing README, domain references, K3s manifests, CI workflow,
  observability docs/config, and image asset inventory.
- UNIT-02: README information architecture rewrite and
  `docs/images/newslab-architecture.png` addition.
- UNIT-03: README domain, infrastructure, pipeline, internal link, image path,
  and local change-scope consistency verification.
- No application code change, DB change, API change, manifest behavior change,
  GitHub Actions behavior change, deployment, rollout, production curl,
  kubectl, Supabase SQL, git push, or git merge was performed.
- Overall task status remains `pending` because production reachability and
  frontend deployment/replica manifest evidence are human/operator or
  external-repository verification items.

## Commands Run

### UNIT-01 Repository And Required Document Intake

Command:

```bash
pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/docs-readme-portfolio-refresh.md' -g 'docs/verification/docs-readme-portfolio-refresh.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'
```

Result:

- Current directory: `../news-lab`
- Current branch: `docs/readme-portfolio-refresh`
- Required files were present:
  `AGENTS.md`, task, verification, backend workflow, Codex instructions,
  verification gates, forbidden commands, and task authoring guide.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Pre-existing working tree changes were present:
  - `M docs/tasks/main.md`
  - untracked branch workflow docs under `docs/devlog/`, `docs/fixes/`,
    `docs/pr/`, `docs/reviews/`, `docs/tasks/`, and `docs/verification/`.
    Status: passed

Command:

```bash
sed -n '1,260p' AGENTS.md
sed -n '1,260p' docs/tasks/docs-readme-portfolio-refresh.md
sed -n '261,620p' docs/tasks/docs-readme-portfolio-refresh.md
sed -n '1,260p' docs/verification/docs-readme-portfolio-refresh.md
sed -n '1,260p' docs/agent/backend-workflow.md
sed -n '1,260p' docs/agent/codex-instructions.md
sed -n '1,260p' docs/agent/verification-gates.md
sed -n '1,320p' docs/agent/forbidden-commands.md
sed -n '1,260p' docs/agent/task-authoring-guide.md
```

Result:

- Required workflow, safety, verification, task scope, acceptance criteria, and
  Python documentation policy were reviewed.
  Status: passed

### UNIT-01 Source Investigation

Command:

```bash
rg -n \
  "api\.dev-scj\.site|dev-scj\.site|newslab\.site|newslab\.ai\.kr|api\.newslab\.ai\.kr" \
  README.md docs k8s app scripts .github
```

Result:

- `README.md` still lists `Domain: api.dev-scj.site`.
- `k8s/news-api.yaml` contains both `api.dev-scj.site` and
  `api.newslab.ai.kr` Ingress/TLS entries.
- `scripts/extract_raw_articles.py` still contains a `NewsLabBot` user-agent URL
  with `api.dev-scj.site`; this was not changed because UNIT-01 is
  investigation only and scripts are outside the README rewrite unit.
- Several runbooks and historical task/review/devlog/verification documents
  mention `api.dev-scj.site`. Current README work must distinguish current
  service URLs from historical records.
- The task source of truth lists current public URLs as
  `https://newslab.ai.kr`, `https://www.newslab.ai.kr`, and
  `https://api.newslab.ai.kr`.
  Status: passed

Command:

```bash
rg -n \
  "kind: Deployment|kind: Service|kind: Ingress|replicas:|name: news-api|name: news-lab-web" \
  k8s
```

Result:

- `k8s/news-api.yaml` defines `Deployment`, `Service`, and `Ingress`.
- `news-api` Deployment has `replicas: 2`.
- `news-api` Service and Ingress route to service `news-api` on port `80`.
- No `news-lab-web` match was found in `k8s`; frontend replica count cannot be
  proven from this backend repository's K3s manifests alone.
  Status: passed

Command:

```bash
rg -n \
  "CronJob|daily|three.day|three_day|weekly|RSS|collector|topic.pipeline" \
  README.md docs k8s app scripts .github
```

Result:

- Output was large and included README, docs, k8s, app, and scripts matches.
- Confirmed manifest and script presence for `news-rss-collector`,
  `news-daily-topic-pipeline`, `news-three-day-topic-pipeline`, and
  `news-weekly-topic-pipeline`.
- Confirmed README currently describes 3-day and weekly topics but remains API
  endpoint oriented.
  Status: passed

Command:

```bash
rg -n \
  "Prometheus|Grafana|kube-state-metrics|node-exporter|Traefik|cert-manager|Tailscale" \
  README.md docs k8s
```

Result:

- README mentions Traefik and cert-manager but not the full current
  observability and hybrid networking story.
- `k8s/monitoring/kube-prometheus-stack-values.yaml` contains
  kube-prometheus-stack values for Grafana, Prometheus, kube-state-metrics, and
  node-exporter.
- Architecture/runbook/devlog/verification docs contain Tailscale, Grafana,
  Prometheus, node-exporter, kube-state-metrics, Traefik, and cert-manager
  operating context.
  Status: passed

Command:

```bash
find .github/workflows -maxdepth 1 -type f -print | sort
```

Result:

- One workflow file was found: `.github/workflows/docker-build.yml`.
  Status: passed

Command:

```bash
rg -n \
  "docker|Docker Hub|buildx|push|ARM64|linux/arm64" \
  .github README.md docs
```

Result:

- README mentions Docker Hub and GitHub Actions.
- `.github/workflows/docker-build.yml` uses `docker/setup-buildx-action@v3`,
  `docker/login-action@v3`, and `docker/build-push-action@v6`.
- Workflow builds and pushes `linux/arm64` images on `main` path changes and
  `workflow_dispatch`.
  Status: passed

Command:

```bash
find . -type f \( \
  -iname "*.png" -o \
  -iname "*.jpg" -o \
  -iname "*.jpeg" -o \
  -iname "*.webp" -o \
  -iname "*.svg" \
\) | sort
```

Result:

- At the time this command ran, no image asset files were found in the
  repository.
- `docs/images/newslab-architecture.png` did not exist.
- Later final status showed an untracked `images/image.png` file that Codex did
  not create or move. It is not the task's expected
  `docs/images/newslab-architecture.png` asset path and was left untouched.
  Status: passed

Command:

```bash
sed -n '1,180p' README.md
```

Result:

- README is currently short and API-focused.
- README top section describes NewsLab as a long-running personal news platform
  project.
- README current configuration lists backend stack and `Domain:
api.dev-scj.site`.
- README includes endpoint lists and local execution instructions for 3-day and
  weekly topic pipelines.
- README links to Architecture, Runbook, 3-day Topic design, and 7-day Topic
  design.
  Status: passed

Command:

```bash
rg --files k8s .github docs/architecture docs/runbooks docs/design | sort
```

Result:

- Confirmed available source files for README rewrite evidence:
  `.github/workflows/docker-build.yml`, architecture docs, runbooks, design
  docs, backend K3s manifests, CronJob manifests, cluster issuer, and monitoring
  values.
  Status: passed

Command:

```bash
sed -n '1,140p' k8s/news-api.yaml
sed -n '1,140p' .github/workflows/docker-build.yml
sed -n '1,180p' k8s/monitoring/kube-prometheus-stack-values.yaml
```

Result:

- `news-api` Deployment has 2 replicas, `workload: app` nodeSelector,
  `seocj/news-api:latest` image, and resource requests/limits.
- `news-api` Ingress uses Traefik and cert-manager
  `letsencrypt-prod`, with TLS secrets `news-api-tls` for
  `api.dev-scj.site` and `news-api-newslab-tls` for
  `api.newslab.ai.kr`.
- Docker workflow builds/pushes `linux/arm64` images to Docker Hub tags
  `${{ github.sha }}` and `latest`.
- Monitoring values disable Alertmanager, place Grafana, Prometheus,
  Prometheus Operator, and kube-state-metrics on `observability: "true"`, set
  Prometheus retention to `1d`, and give node-exporter tolerations for
  control-plane/master and `node-role=news-edge-worker`.
  Status: passed

Command:

```bash
sed -n '1,140p' docs/ARCHITECTURE.md
sed -n '1,180p' docs/architecture/overview.md
sed -n '1,180p' docs/architecture/k3s-runtime.md
sed -n '1,220p' docs/architecture/pipeline.md
sed -n '1,130p' docs/architecture/domains.md
```

Result:

- Architecture index states NewsLab stores RSS collection, raw extraction, and
  topic generation results in PostgreSQL/Supabase and serves them through
  FastAPI.
- Current scheduled workloads are `news-rss-collector`,
  `news-daily-topic-pipeline`, `news-three-day-topic-pipeline`, and
  `news-weekly-topic-pipeline`.
- Runtime docs state backend workloads run on Oracle Cloud A1 K3s and use
  `workload: app` node selector with `seocj/news-api:latest`.
- Pipeline docs describe RSS collection at `03:00 Asia/Seoul`, daily topic at
  `04:00 Asia/Seoul`, three-day topic at `05:00 Asia/Seoul`, and weekly topic
  at `00:30 Asia/Seoul` on Mondays.
- Domain docs state Traefik routes both `api.dev-scj.site` and
  `api.newslab.ai.kr` to the same `news-api` Service during transition and warn
  that DNS, Ingress apply, certificate confirmation, and frontend API base URL
  transition are human-controlled.
  Status: passed

Command:

```bash
rg -n "name: news-|schedule:|run_.*topic_pipeline|collect_rss|image:|nodeSelector|workload:" k8s/*.yaml
```

Result:

- Confirmed CronJob names, schedules, commands, image, and `workload: app`
  nodeSelector:
  - `news-rss-collector`: `0 3 * * *`, `python scripts/collect_rss.py`
  - `news-daily-topic-pipeline`: `0 4 * * *`,
    `scripts/run_daily_topic_pipeline.py`
  - `news-three-day-topic-pipeline`: `0 5 * * *`,
    `scripts/run_three_day_topic_pipeline.py`
  - `news-weekly-topic-pipeline`: `30 0 * * 1`,
    `scripts/run_weekly_topic_pipeline.py`
- All use `seocj/news-api:latest`.
  Status: passed

Command:

```bash
rg -n "news-lab-web|frontend|newslab\.ai\.kr|www\.newslab\.ai\.kr" README.md docs k8s .github app scripts
```

Result:

- Output was large due historical docs.
- No `news-lab-web` manifest match was found in `k8s`.
- Current frontend URLs are present in the task source of truth and historical
  backend-domain task notes, but frontend deployment manifest evidence is not
  present in this backend repository.
  Status: passed

Command:

```bash
rg -n "arm-master-node|arm-worker-node|pi-worker-node|observability=true|node-role=news-edge-worker|workload: app|workload=app|replicas:" README.md docs k8s
```

Result:

- `news-api` replicas and `workload: app` are present in `k8s/news-api.yaml`.
- Architecture and historical verification/devlog docs identify a 3-node
  cluster with `arm-master-node`, `arm-worker-node`, and `pi-worker-node`.
- Monitoring docs and values use `observability=true` for core monitoring
  placement and `node-role=news-edge-worker:NoSchedule` for Pi node-exporter
  toleration.
  Status: passed

### UNIT-01 Final Local Checks

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported.
  Status: passed

Command:

```bash
git diff -- docs/tasks/docs-readme-portfolio-refresh.md docs/verification/docs-readme-portfolio-refresh.md
```

Result:

- No output because both branch task and verification files are currently
  untracked.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Working tree status after UNIT-01:
  - `M docs/tasks/main.md`
  - untracked `docs/devlog/docs-readme-portfolio-refresh.md`
  - untracked `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`
  - untracked `docs/pr/docs-readme-portfolio-refresh.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-antigravity.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-coderabbit.md`
  - untracked `docs/tasks/docs-readme-portfolio-refresh.md`
  - untracked `docs/verification/docs-readme-portfolio-refresh.md`
  - untracked `images/`
    Status: passed

Command:

```bash
find images -maxdepth 2 -type f -print | sort
```

Result:

- `images/image.png`
- This file was not created, moved, edited, or referenced by Codex during
  UNIT-01.
  Status: passed

## Results

- UNIT-01 investigation completed.
- README rewrite source facts:
  - Current README still presents `api.dev-scj.site` as the domain and should be
    updated in a later unit to the task-specified current service URLs.
  - Backend manifest evidence supports `news-api` with 2 replicas and Traefik +
    cert-manager Ingress for `api.dev-scj.site` and `api.newslab.ai.kr`.
  - `api.dev-scj.site` remains in backend Ingress as a transition host according
    to `docs/architecture/domains.md`; README must not present it as the current
    public service URL.
  - The backend repo does not include a `news-lab-web` manifest, so frontend
    replica count requires external/frontend-repo or operator-provided evidence
    before README can state it as fact.
  - CI evidence supports GitHub Actions building and pushing Docker Hub
    `linux/arm64` images for the backend image.
  - Observability evidence supports Prometheus/Grafana with kube-state-metrics
    and node-exporter, Alertmanager disabled, Prometheus retention `1d`, and
    core monitoring placement on `observability=true`.
  - The expected architecture image
    `docs/images/newslab-architecture.png` does not exist; architecture image
    addition remains pending for UNIT-02.
  - A separate untracked `images/image.png` was observed after the initial image
    inventory. It was not created or used by Codex and is not treated as the
    README architecture asset.

## Manual or Production Verification

- Not performed.
- No production `curl`, `kubectl`, DNS lookup, certificate status check,
  rollout, deployment, GitHub Actions run, Docker push, or Supabase SQL was
  executed by Codex.
- Actual public service reachability for `https://newslab.ai.kr`,
  `https://www.newslab.ai.kr`, and `https://api.newslab.ai.kr` remains
  human-required production verification unless the task later provides
  explicit human logs.

## Pending Verification

- Human/operator evidence for frontend deployment manifest and replica count if
  README will state `news-lab-web` replica count.

## Evidence Notes

- Treat `docs/architecture/domains.md` and `k8s/news-api.yaml` as current backend
  domain/TLS manifest evidence.
- Treat `docs/architecture/pipeline.md` and CronJob manifests as source evidence
  for RSS, Daily, Three-day, and Weekly pipeline timing and entrypoints.
- Treat `k8s/monitoring/kube-prometheus-stack-values.yaml`,
  `docs/devlog/infra-monitoring-baseline.md`, and
  `docs/verification/infra-monitoring-baseline.md` as observability evidence.
- Treat historical task/review/devlog/verification mentions of `api.dev-scj.site`
  as historical evidence unless current architecture/runbook docs explicitly
  describe current transition routing.

### UNIT-02 README Rewrite And Architecture Image Addition

Command:

```bash
sed -n '1,220p' docs/agent/task-authoring-guide.md
sed -n '1,240p' README.md
find images docs/images -maxdepth 2 -type f -print 2>/dev/null | sort
file images/image.png docs/images/newslab-architecture.png 2>/dev/null
```

Result:

- Python documentation policy was reviewed. No Python files were created or
  modified in UNIT-02.
- Existing README was short and API-oriented, and still listed
  `api.dev-scj.site` as `Domain`.
- `images/image.png` existed as a PNG image, `2414 x 1300`, RGBA.
- `docs/images/newslab-architecture.png` did not exist before UNIT-02.
  Status: passed

Command:

```bash
rg -n "news-lab-web|newslab-web|frontend|Front|Next|replicas: 2|replica" README.md docs k8s .github app scripts
```

Result:

- `k8s/news-api.yaml` contains `replicas: 2` for `news-api`.
- No `news-lab-web` manifest was found in `k8s`.
- Historical docs mention frontend work and current frontend domains, but this
  backend repository does not contain frontend deployment manifest evidence.
- README therefore states `news-api` replica evidence from this repository and
  explicitly notes that frontend manifest evidence is outside this backend repo.
  Status: passed

Command:

```bash
sed -n '1,220p' docs/ARCHITECTURE.md
sed -n '1,240p' docs/architecture/overview.md
sed -n '1,260p' docs/architecture/k3s-runtime.md
sed -n '1,280p' docs/architecture/pipeline.md
sed -n '1,220p' docs/architecture/domains.md
sed -n '1,220p' docs/RUNBOOK.md
sed -n '1,220p' docs/runbooks/cronjobs.md
sed -n '1,180p' k8s/news-api.yaml
sed -n '1,120p' k8s/news-rss-collector-cronjob.yaml
sed -n '1,120p' k8s/news-daily-topic-pipeline-cronjob.yaml
sed -n '1,120p' k8s/news-three-day-topic-pipeline-cronjob.yaml
sed -n '1,120p' k8s/news-weekly-topic-pipeline-cronjob.yaml
sed -n '1,220p' k8s/monitoring/kube-prometheus-stack-values.yaml
sed -n '1,180p' .github/workflows/docker-build.yml
sed -n '1,260p' docs/architecture/database.md
rg -n "arm-master-node|arm-worker-node|pi-worker-node|3-node|3노드|Raspberry|Tailscale|observability=true|node-role=news-edge-worker" docs k8s README.md
```

Result:

- README rewrite facts were cross-checked against architecture, runbook, K3s,
  monitoring, CI, and database documents.
- Confirmed backend API and CronJob workloads, current backend domain routing,
  human-controlled production verification boundaries, CronJob schedules,
  Prometheus/Grafana baseline values, Docker Hub ARM64 image workflow, Supabase
  PostgreSQL/pgvector role, and hybrid K3s node evidence.
  Status: passed

Command:

```bash
mkdir -p docs/images && cp images/image.png docs/images/newslab-architecture.png && ls -l docs/images/newslab-architecture.png
```

Result:

- Created `docs/images/newslab-architecture.png` from the existing
  `images/image.png` source without image editing.
- Resulting file was present with size `530435` bytes.
  Status: passed

Command:

```bash
test -f docs/images/newslab-architecture.png
```

Result:

- Command exited successfully; architecture image exists at the expected path.
  Status: passed

Command:

```bash
rg -n "newslab-architecture\.png|!\[.*아키텍처|!\[.*Architecture" README.md
```

Result:

- README references the architecture image at
  `docs/images/newslab-architecture.png`.
- Image alt text is `NewsLab 전체 아키텍처`.
  Status: passed

Command:

```bash
rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site" README.md
```

Result:

- Command exited with status `1` and no output because old-domain patterns were
  not found in README after the rewrite.
  Status: passed

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Working tree status after UNIT-02 included:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked branch workflow docs under `docs/devlog/`, `docs/fixes/`,
    `docs/pr/`, `docs/reviews/`, `docs/tasks/`, and `docs/verification/`
  - untracked `docs/images/`
  - untracked `images/`
- `docs/tasks/main.md` and the pre-existing workflow docs were not modified by
  UNIT-02 except the current task and verification files required for this unit.
  Status: passed

Command:

```bash
git diff -- README.md docs/images docs/tasks/docs-readme-portfolio-refresh.md docs/verification/docs-readme-portfolio-refresh.md
```

Result:

- Diff showed README rewritten into a portfolio entry document, the UNIT-02 task
  checklist checked, and this verification record updated.
- `docs/images/newslab-architecture.png` is untracked binary content, so it does
  not appear in textual diff output.
  Status: passed

Command:

```bash
test -f docs/ARCHITECTURE.md && test -f docs/RUNBOOK.md && test -f docs/architecture/pipeline.md && test -f docs/architecture/k3s-runtime.md && test -f docs/architecture/domains.md && test -f docs/design/three-day-topic-pipeline.md && test -f docs/design/weekly-topic-pipeline.md && test -f docs/agent/backend-workflow.md && test -f docs/tasks/docs-readme-portfolio-refresh.md && test -f docs/verification/docs-readme-portfolio-refresh.md && test -f docs/verification/infra-pi-worker-join.md && test -f docs/verification/infra-monitoring-baseline.md
```

Result:

- Command exited successfully; README-linked internal documentation targets
  checked in UNIT-02 exist.
  Status: passed

Command:

```bash
git diff --name-only
```

Result:

- Tracked-file diff list:
  - `README.md`
  - `docs/tasks/main.md`
- Untracked files are not included by this command.
  Status: passed

## UNIT-02 Results

- README was rewritten as a portfolio entry document with live service links,
  architecture image, user-facing features, data pipeline, runtime architecture,
  infrastructure/deployment notes, observability, agent workflow, design
  trade-offs, documentation index, and local development section.
- `docs/images/newslab-architecture.png` was added from the existing
  `images/image.png` source asset.
- Current README no longer presents `api.dev-scj.site` or `newslab.site` as
  current service domains.
- README does not claim measured cost, traffic, latency, availability, test
  count, or production verification results.
- Application code, DB schema, API contract, K3s manifests, GitHub Actions
  workflow, Dockerfile, secret/env files, and production resources were not
  changed.

### UNIT-02 Final Sanity Checks

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported after updating the verification scope.
  Status: passed

Command:

```bash
rg -n "Verification Scope|Overall task status|UNIT-0[123]|newslab-architecture\.png|api\.dev-scj\.site|newslab\.site" docs/verification/docs-readme-portfolio-refresh.md docs/tasks/docs-readme-portfolio-refresh.md README.md
```

Result:

- README contains the architecture image reference.
- Task checklist shows UNIT-01 and UNIT-02 checked, UNIT-03 unchecked.
- Verification scope states UNIT-01 and UNIT-02 are in scope and overall status
  remains pending because UNIT-03 is not in scope.
- Matches for `api.dev-scj.site` are limited to task criteria and historical
  verification/evidence text, not README.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Working tree status at end of UNIT-02:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked `docs/devlog/docs-readme-portfolio-refresh.md`
  - untracked `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`
  - untracked `docs/images/`
  - untracked `docs/pr/docs-readme-portfolio-refresh.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-antigravity.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-coderabbit.md`
  - untracked `docs/tasks/docs-readme-portfolio-refresh.md`
  - untracked `docs/verification/docs-readme-portfolio-refresh.md`
  - untracked `images/`
    Status: passed

Command:

```bash
git diff --check
git status --short
```

Result:

- Final post-record check reported no whitespace errors.
- Working tree status remained:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked `docs/devlog/docs-readme-portfolio-refresh.md`
  - untracked `docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md`
  - untracked `docs/images/`
  - untracked `docs/pr/docs-readme-portfolio-refresh.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-antigravity.md`
  - untracked `docs/reviews/docs-readme-portfolio-refresh-coderabbit.md`
  - untracked `docs/tasks/docs-readme-portfolio-refresh.md`
  - untracked `docs/verification/docs-readme-portfolio-refresh.md`
  - untracked `images/`
    Status: passed

## UNIT-02 Manual or Production Verification

- Not performed.
- No production `curl`, DNS lookup, TLS check, `kubectl`, rollout, deployment,
  Docker push, GitHub Actions run, Supabase SQL, DB write, `git push`, or
  `git merge` was executed.
- Public reachability of `https://newslab.ai.kr`,
  `https://www.newslab.ai.kr`, and `https://api.newslab.ai.kr` remains
  human/operator verification unless logs are provided in a later unit.

### UNIT-03 Final Consistency Verification

Command:

```bash
rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site|newslab\.ai\.kr|api\.newslab\.ai\.kr" README.md docs k8s app scripts .github
```

Result:

- README lists only the current service URLs:
  `https://newslab.ai.kr`, `https://www.newslab.ai.kr`, and
  `https://api.newslab.ai.kr`.
- README references `api.newslab.ai.kr` as the current backend Ingress host.
- `api.dev-scj.site` remains in `k8s/news-api.yaml`, historical docs, runbooks,
  and `scripts/extract_raw_articles.py`; these were not changed because this
  unit does not modify manifests, scripts, or historical records.
  Status: passed

Command:

```bash
rg -n "kind: Deployment|kind: Service|kind: Ingress|replicas:|name: news-api|name: news-lab-web" k8s
```

Result:

- `k8s/news-api.yaml` defines `news-api` Deployment, Service, and Ingress.
- `news-api` Deployment has `replicas: 2`.
- No `news-lab-web` manifest exists under `k8s` in this backend repository.
  Status: human-required
  Notes:
- README states the backend `news-api` replica count from this repository and
  explicitly does not use this backend repository alone as proof of the
  frontend replica count.

Command:

```bash
rg -n "CronJob|daily|three.day|three_day|weekly|RSS|collector|topic.pipeline" README.md docs k8s app scripts .github
```

Result:

- README contains the RSS, Daily, Three-day, and Weekly Topic pipeline summary.
- K3s CronJob manifests exist for `news-rss-collector`,
  `news-daily-topic-pipeline`, `news-three-day-topic-pipeline`, and
  `news-weekly-topic-pipeline`.
- Output was large and included historical docs and code references; no
  README conflict was identified.
  Status: passed

Command:

```bash
rg -n "Prometheus|Grafana|kube-state-metrics|node-exporter|Traefik|cert-manager|Tailscale" README.md docs k8s
```

Result:

- README describes Traefik, cert-manager, Tailscale, Prometheus, Grafana,
  kube-state-metrics, and node-exporter roles.
- `k8s/news-api.yaml`, `k8s/cluster-issuer.yaml`, and
  `k8s/monitoring/kube-prometheus-stack-values.yaml` contain matching static
  configuration evidence.
- Output also includes historical monitoring review/devlog records; README uses
  the current values-file facts and does not claim Alertmanager is enabled.
  Status: passed

Command:

```bash
find .github/workflows -maxdepth 1 -type f -print | sort
```

Result:

- `.github/workflows/docker-build.yml`
  Status: passed

Command:

```bash
rg -n "docker|Docker Hub|buildx|push|ARM64|linux/arm64" .github README.md docs
```

Result:

- README states GitHub Actions builds `linux/arm64` backend images and pushes
  them to Docker Hub.
- `.github/workflows/docker-build.yml` uses Docker buildx/login/build-push
  actions, `platforms: linux/arm64`, and `push: true`.
- README does not describe Kubernetes rollout as automatic CD.
  Status: passed

Command:

```bash
find . -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.webp" -o -iname "*.svg" \) | sort
```

Result:

- Image assets found:
  - `./docs/images/newslab-architecture.png`
  - `./images/image.png`
    Status: passed

Command:

```bash
test -f docs/images/newslab-architecture.png
```

Result:

- Command exited successfully.
  Status: passed

Command:

```bash
rg -n "newslab-architecture\.png|!\.*Architecture|!\[.*아키텍처" README.md
```

Result:

- README references `docs/images/newslab-architecture.png`.
- Image alt text is `NewsLab 전체 아키텍처`.
  Status: passed

Command:

```bash
test -f docs/ARCHITECTURE.md && test -f docs/RUNBOOK.md && test -f docs/architecture/pipeline.md && test -f docs/architecture/k3s-runtime.md && test -f docs/architecture/domains.md && test -f docs/design/three-day-topic-pipeline.md && test -f docs/design/weekly-topic-pipeline.md && test -f docs/agent/backend-workflow.md && test -f docs/tasks/docs-readme-portfolio-refresh.md && test -f docs/verification/docs-readme-portfolio-refresh.md && test -f docs/verification/infra-pi-worker-join.md && test -f docs/verification/infra-monitoring-baseline.md
```

Result:

- Command exited successfully; README-linked internal documentation targets
  checked in UNIT-03 exist.
  Status: passed

Command:

```bash
rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site" README.md
```

Result:

- Command exited with status `1` and no output because old-domain patterns were
  not found in README.
  Status: passed

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Working tree status during UNIT-03:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked branch workflow docs under `docs/devlog/`, `docs/fixes/`,
    `docs/pr/`, `docs/reviews/`, `docs/tasks/`, and `docs/verification/`
  - untracked `docs/images/`
  - untracked `images/`
    Status: passed
    Notes:
- `docs/tasks/main.md` and untracked workflow docs other than the current task,
  current verification, and `docs/images/newslab-architecture.png` were not
  modified during UNIT-03.

Command:

```bash
git diff -- README.md docs/images docs/ARCHITECTURE.md docs/RUNBOOK.md
```

Result:

- Text diff shows only the README rewrite among tracked files in those paths.
- `docs/images/newslab-architecture.png` is untracked binary content and is
  confirmed separately by `test -f`, `file`, and `cmp`.
- No `docs/ARCHITECTURE.md` or `docs/RUNBOOK.md` diff was shown.
  Status: passed

Command:

```bash
rg -n "0원|cost|비용|일일 평균|누적|실패율|평균 응답|p95|p99|처리량|가용성|사용자 수|테스트 [0-9]+|[0-9]+ tests|availability|latency" README.md
```

Result:

- Command exited with status `1` and no output; README does not add unverified
  cost, traffic, latency, availability, user-count, or fixed test-count claims.
  Status: passed

Command:

```bash
rg -n "\[[^]]+\]\(([^)#][^)]+\.md)\)" README.md
```

Result:

- README Markdown links point to the documented Architecture, Runbook, pipeline,
  runtime, domain, design, agent workflow, task, and verification files.
- These targets were checked with `test -f` above.
  Status: passed

Command:

```bash
file docs/images/newslab-architecture.png images/image.png
```

Result:

- Both files are PNG images, `2414 x 1300`, 8-bit RGBA, non-interlaced.
  Status: passed

Command:

```bash
cmp -s images/image.png docs/images/newslab-architecture.png && echo identical
```

Result:

- `identical`
  Status: passed

Command:

```bash
git diff --name-only -- README.md docs/ARCHITECTURE.md docs/RUNBOOK.md app scripts k8s .github db requirements.txt Dockerfile docker-compose.yml 2>/dev/null
```

Result:

- `README.md`
  Status: passed

Command:

```text
view_image docs/images/newslab-architecture.png
```

Result:

- The diagram shows the requested operating structure: public DNS for
  `newslab.ai.kr`, Traefik/Ingress/TLS/Service/Pod path, Oracle Cloud A1 plus
  Raspberry Pi 3-node K3s cluster, `arm-master-node`, `arm-worker-node`,
  `pi-worker-node`, Tailscale overlay, CI/Image Registry, Supabase PostgreSQL +
  pgvector, Let's Encrypt/cert-manager, Operator Mac, and monitoring
  components.
- The diagram includes `news-lab-web x2`. This frontend replica marker is not
  proven by a backend-repository manifest, and README explicitly records that
  limitation.
  Status: human-required

## UNIT-03 Results

- Local README domain, Markdown link, image path, Docker workflow, backend
  manifest, CronJob, observability, and change-scope checks were completed.
- `git diff --check` passed.
- README no longer presents old domains as current service addresses.
- README does not add unverified performance, cost, traffic, availability,
  user-count, or fixed test-count claims.
- Application code, scripts, DB migrations/schema, K3s manifests, GitHub
  Actions workflow, Dockerfile, requirements, secrets, and production resources
  were not modified.
- Overall verification remains `pending` because public service reachability
  was not checked by Codex and the frontend `news-lab-web` replica count in the
  diagram requires frontend-repository manifest or operator-provided evidence.

## UNIT-03 Manual or Production Verification

- Not performed.
- No production `curl`, DNS lookup, TLS check, `kubectl`, rollout, deployment,
  Docker push, GitHub Actions run, Supabase SQL, DB write, `git push`, or
  `git merge` was executed.

### UNIT-03 Post-record Checks

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported after updating the UNIT-03 verification
  record and task checklist status.
  Status: passed

Command:

```bash
rg -n "Verification Status|Overall task status|UNIT-03|human-required|사람이 수행 필요|news-lab-web|git diff --check|git status --short" docs/verification/docs-readme-portfolio-refresh.md docs/tasks/docs-readme-portfolio-refresh.md
```

Result:

- Current verification scope includes UNIT-03.
- Verification status remains `pending`.
- Task checklist leaves UNIT-03 unchecked with a human-required frontend
  manifest/replica evidence note.
- UNIT-03 human-required notes for `news-lab-web` are present in verification.
  Status: passed

Command:

```bash
git status --short
```

Result:

- Working tree status after UNIT-03 record update:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked branch workflow docs under `docs/devlog/`, `docs/fixes/`,
    `docs/pr/`, `docs/reviews/`, `docs/tasks/`, and `docs/verification/`
  - untracked `docs/images/`
  - untracked `images/`
    Status: passed

### UNIT-03 Current Run Confirmation

Command:

```bash
pwd && git branch --show-current && rg --files -g 'AGENTS.md' -g 'docs/tasks/docs-readme-portfolio-refresh.md' -g 'docs/verification/docs-readme-portfolio-refresh.md' -g 'docs/agent/backend-workflow.md' -g 'docs/agent/codex-instructions.md' -g 'docs/agent/verification-gates.md' -g 'docs/agent/forbidden-commands.md' -g 'docs/agent/task-authoring-guide.md'
```

Result:

- Current directory was `../news-lab`.
- Current branch was `docs/readme-portfolio-refresh`.
- Required task, verification, workflow, Codex, verification gate, forbidden
  command, task authoring guide, and `AGENTS.md` files were present.
  Status: passed

Command:

```bash
sed -n '1,240p' AGENTS.md
sed -n '1,260p' docs/tasks/docs-readme-portfolio-refresh.md
sed -n '261,620p' docs/tasks/docs-readme-portfolio-refresh.md
sed -n '1,260p' docs/verification/docs-readme-portfolio-refresh.md
sed -n '1,220p' docs/agent/backend-workflow.md
sed -n '1,260p' docs/agent/codex-instructions.md
sed -n '1,260p' docs/agent/verification-gates.md
sed -n '1,320p' docs/agent/forbidden-commands.md
sed -n '1,260p' docs/agent/task-authoring-guide.md
```

Result:

- Current task source of truth, workflow, Codex role rules, verification gates,
  forbidden commands, and Python documentation policy were reviewed for
  UNIT-03.
  Status: passed

Command:

```bash
sed -n '1,240p' docs/fixes/docs-readme-portfolio-refresh-approved-fixes.md
```

Result:

- Approved Fixes file exists, but no approved fixes are listed for this task.
  Status: passed

Command:

```bash
sed -n '1,260p' README.md
```

Result:

- README includes current live service links, architecture image reference,
  data pipeline, infrastructure/deployment, observability, agent workflow,
  design decisions, documentation links, and local development sections.
- README explicitly avoids claiming production verification without
  operator-provided logs and avoids using this backend repository alone as
  proof of the frontend replica count.
  Status: passed

Command:

```bash
find docs/images images -maxdepth 2 -type f -print | sort
```

Result:

- `docs/images/newslab-architecture.png`
- `images/image.png`
  Status: passed

Command:

```bash
git diff -- README.md docs/images docs/ARCHITECTURE.md docs/RUNBOOK.md
```

Result:

- Diff shows the README rewrite among tracked files in those paths.
- No tracked diff was shown for `docs/ARCHITECTURE.md` or `docs/RUNBOOK.md`.
- `docs/images/newslab-architecture.png` is untracked binary content and was
  verified separately.
  Status: passed

Command:

```bash
rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site|newslab\.ai\.kr|api\.newslab\.ai\.kr" README.md docs k8s app scripts .github
```

Result:

- README lists only current service links:
  `https://newslab.ai.kr`, `https://www.newslab.ai.kr`, and
  `https://api.newslab.ai.kr`.
- `api.dev-scj.site` remains in backend Ingress transition config, runtime
  script user-agent text, runbooks, and historical workflow records; README no
  longer presents it as the current service address.
  Status: passed

Command:

```bash
rg -n "kind: Deployment|kind: Service|kind: Ingress|replicas:|name: news-api|name: news-lab-web" k8s
```

Result:

- `k8s/news-api.yaml` defines `news-api` Deployment, Service, and Ingress.
- `news-api` Deployment has `replicas: 2`.
- No `news-lab-web` manifest was found under `k8s`.
  Status: human-required
  Notes:
- Frontend `news-lab-web` replica evidence must come from the frontend
  repository manifest or operator-provided evidence, or the image must be
  adjusted by human decision.

Command:

```bash
rg -n "CronJob|daily|three.day|three_day|weekly|RSS|collector|topic.pipeline" README.md docs k8s app scripts .github
```

Result:

- README describes RSS, Daily, Three-day, and Weekly Topic pipeline flow.
- K3s manifests and scripts contain the corresponding RSS collector and Topic
  pipeline CronJob names and entrypoints.
- Output was large because it included historical docs and code references; no
  README conflict was identified.
  Status: passed

Command:

```bash
rg -n "Prometheus|Grafana|kube-state-metrics|node-exporter|Traefik|cert-manager|Tailscale" README.md docs k8s
```

Result:

- README describes Traefik, cert-manager, Tailscale, Prometheus, Grafana,
  kube-state-metrics, and node-exporter roles.
- Static evidence exists in `k8s/news-api.yaml`, `k8s/cluster-issuer.yaml`, and
  `k8s/monitoring/kube-prometheus-stack-values.yaml`.
  Status: passed

Command:

```bash
find .github/workflows -maxdepth 1 -type f -print | sort
```

Result:

- `.github/workflows/docker-build.yml`
  Status: passed

Command:

```bash
rg -n "docker|Docker Hub|buildx|push|ARM64|linux/arm64" .github README.md docs
```

Result:

- README states GitHub Actions builds `linux/arm64` backend images and pushes
  them to Docker Hub.
- `.github/workflows/docker-build.yml` uses buildx/login/build-push actions,
  `platforms: linux/arm64`, and `push: true`.
- README does not claim fully automated Kubernetes CD.
  Status: passed

Command:

```bash
find . -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.webp" -o -iname "*.svg" \) | sort
test -f docs/images/newslab-architecture.png
rg -n "newslab-architecture\.png|!\.*Architecture|!\[.*아키텍처" README.md
file docs/images/newslab-architecture.png images/image.png
cmp -s images/image.png docs/images/newslab-architecture.png && echo identical
```

Result:

- Image assets found: `./docs/images/newslab-architecture.png` and
  `./images/image.png`.
- `docs/images/newslab-architecture.png` exists.
- README references `docs/images/newslab-architecture.png` with alt text
  `NewsLab 전체 아키텍처`.
- Both PNG files are `2414 x 1300`, 8-bit RGBA, non-interlaced.
- `cmp` reported `identical`.
  Status: passed

Command:

```bash
test -f docs/ARCHITECTURE.md && test -f docs/RUNBOOK.md && test -f docs/architecture/pipeline.md && test -f docs/architecture/k3s-runtime.md && test -f docs/architecture/domains.md && test -f docs/design/three-day-topic-pipeline.md && test -f docs/design/weekly-topic-pipeline.md && test -f docs/agent/backend-workflow.md && test -f docs/tasks/docs-readme-portfolio-refresh.md && test -f docs/verification/docs-readme-portfolio-refresh.md && test -f docs/verification/infra-pi-worker-join.md && test -f docs/verification/infra-monitoring-baseline.md
```

Result:

- Command exited successfully; README-linked internal documentation targets
  exist.
  Status: passed

Command:

```bash
rg -n "0원|cost|비용|일일 평균|누적|실패율|평균 응답|p95|p99|처리량|가용성|사용자 수|테스트 [0-9]+|[0-9]+ tests|availability|latency" README.md
```

Result:

- Command exited with status `1` and no output because README does not add
  unverified cost, traffic, latency, availability, user-count, or fixed
  test-count claims.
  Status: passed

Command:

```bash
rg -n "\[[^]]+\]\(([^)#][^)]+\.md)\)" README.md
```

Result:

- README Markdown links point to the expected internal documentation files.
- The link targets were checked with `test -f` above.
  Status: passed

Command:

```bash
rg -n "api\.dev-scj\.site|dev-scj\.site|newslab\.site" README.md
```

Result:

- Command exited with status `1` and no output because old-domain patterns
  were not found in README.
  Status: passed

Command:

```bash
git diff --check
```

Result:

- No whitespace errors were reported.
  Status: passed

Command:

```bash
git diff --name-only -- README.md docs/ARCHITECTURE.md docs/RUNBOOK.md app scripts k8s .github db requirements.txt Dockerfile docker-compose.yml 2>/dev/null
```

Result:

- `README.md`
  Status: passed

Command:

```text
view_image docs/images/newslab-architecture.png
```

Result:

- The diagram shows the requested operating structure: public DNS for
  `newslab.ai.kr`, Traefik/Ingress/TLS/Service/Pod path, Oracle Cloud A1 plus
  Raspberry Pi 3-node K3s cluster, `arm-master-node`, `arm-worker-node`,
  `pi-worker-node`, Tailscale overlay, CI/Image Registry, Supabase PostgreSQL +
  pgvector, Let's Encrypt/cert-manager, Operator Mac, and monitoring
  components.
- The diagram includes `news-lab-web x2`. This frontend replica marker is not
  proven by a backend-repository manifest, and README explicitly records that
  limitation.
  Status: human-required

Command:

```bash
git status --short
```

Result:

- Working tree status after the current UNIT-03 confirmation:
  - `M README.md`
  - `M docs/tasks/main.md`
  - untracked branch workflow docs under `docs/devlog/`, `docs/fixes/`,
    `docs/pr/`, `docs/reviews/`, `docs/tasks/`, and `docs/verification/`
  - untracked `docs/images/`
  - untracked `images/`
    Status: passed

Notes:

- No production `curl`, DNS lookup, TLS check, `kubectl`, rollout,
  deployment, Docker push, GitHub Actions run, Supabase SQL, DB write,
  `git push`, or `git merge` was executed.
- UNIT-03 remains unchecked in the task checklist because the frontend
  `news-lab-web` replica evidence or image adjustment decision is explicitly a
  human-required item.

### Human verification: Frontend replica

Command & Result:

```bash
❯ rg -n "kind: Deployment|name: news-lab-web|replicas:" k8s
k8s/news-lab-web-redirect-https-middleware.yaml
4:  name: news-lab-web-redirect-https
6:    app.kubernetes.io/name: news-lab-web

k8s/news-lab-web-deployment.yaml
2:kind: Deployment
4:  name: news-lab-web
6:    app.kubernetes.io/name: news-lab-web
9:  replicas: 2
12:      app.kubernetes.io/name: news-lab-web
16:        app.kubernetes.io/name: news-lab-web
22:        - name: news-lab-web

k8s/news-lab-web-service.yaml
4:  name: news-lab-web
6:    app.kubernetes.io/name: news-lab-web
11:    app.kubernetes.io/name: news-lab-web

k8s/news-lab-web-ingress.yaml
4:  name: news-lab-web-ingress
6:    app.kubernetes.io/name: news-lab-web
26:                name: news-lab-web
36:                name: news-lab-web
```
