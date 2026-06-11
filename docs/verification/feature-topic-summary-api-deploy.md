# Verification: Topic summary API 운영 배포 및 production read verification

## Verification Scope

- 문서 전용 workflow 변경 확인
- 기존 test suite 회귀 확인
- K8s, GitHub Actions, frontend, Dockerfile, DB 변경 없음 확인
- credential/secret 값 미노출 확인
- human-controlled K3s rollout 및 production read verification 결과 기록
- production `/topics`, `/topics/{topic_id}` read API 반영 여부 확인
- production API raw text 미노출 확인
- 존재하지 않는 topic의 production 404 응답 확인

## Commands Run

### Local / documentation workflow verification

```bash
git status --short --branch
git diff --stat
git diff --check
.venv/bin/python -m unittest discover -s tests -v
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
git diff -- db
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

### Human-controlled namespace discovery

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy -A | grep news
```

### Human-controlled K3s verification before restart

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc,ingress -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default deployment/news-api --tail=100
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -l app=news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe deploy news-api -n default
```

### Human-controlled production read API verification before restart

```bash
curl -sS https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/version
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/1"
```

### Human-controlled rollout restart

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout restart deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -l app=news-api
```

### Human-controlled production read API verification after restart

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/1"
curl -sS "https://api.dev-scj.site/topics/1" | grep -i raw_text
curl -i -sS "https://api.dev-scj.site/topics/999999999"
```

## Local / Documentation Workflow Results

- Branch: `feature/topic-summary-api-deploy`
- `git status --short --branch`: workflow 문서가 untracked 상태임을 확인했다.
  - 기존 untracked `docs/reviews/feature-topic-summary-api-deploy-coderabbit.md`는 읽거나 수정하지 않았다.
- `git diff --stat`: tracked file diff 없음. 이번 workflow 문서는 신규 untracked 파일이다.
- `git diff --check`: passed.
- Full unittest discovery: passed, 108 tests.
- Scope checks:
  - `k8s`: no diff
  - `.github`: no diff
  - `frontend`: no diff
  - `Dockerfile`: no diff
  - `db`: no diff
- Security grep:
  - 기존 safe references, 환경변수명, 문서화된 검사 명령, test-only values, `engine.begin()` false positive가 매치되었다.
  - credential/secret 값은 발견되지 않았다.

## Human-controlled Namespace Discovery

초기 K3s verification command는 `news` namespace를 기준으로 작성되어 있었다.  
하지만 실제 cluster에는 `news` namespace가 없었고, `news-api` Deployment는 `default` namespace에 있었다.

### Initial commands with wrong namespace

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n news
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n news
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc,ingress -n news
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n news deployment/news-api --tail=100
```

### Initial results

```text
No resources found in news namespace.
Error from server (NotFound): namespaces "news" not found
No resources found in news namespace.
error: error from server (NotFound): namespaces "news" not found in namespace "news"
```

### Namespace discovery command

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy -A | grep news
```

### Result

```text
default        news-api                              2/2     2            2           17d
```

### Interpretation

- `news-api` Deployment namespace는 `news`가 아니라 `default`다.
- 이후 K3s verification은 `-n default` 기준으로 수행했다.
- 기존 task/verification command template의 namespace assumption은 `default` 기준으로 수정이 필요하다.

## Human-controlled K3s Verification Before Restart

### Commands Run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get svc,ingress -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl logs -n default deployment/news-api --tail=100
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -l app=news-api
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get deploy news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl describe deploy news-api -n default
```

### Results

- `news-api` Pods before restart:
  - `news-api-778f97dc9b-85ztt`: `1/1 Running`, restarts `0`, age `2d17h`
  - `news-api-778f97dc9b-vqnc2`: `1/1 Running`, restarts `0`, age `2d17h`
- CronJob pods were present as completed historical jobs:
  - `news-raw-extractor-*`: `Completed`
  - `news-rss-collector-*`: `Completed`
- Rollout status:
  - `deployment "news-api" successfully rolled out`
- Service:
  - `service/news-api`
  - type: `ClusterIP`
  - cluster IP: `10.43.73.26`
  - port: `80/TCP`
- Ingress:
  - `news-api-ingress`
  - class: `traefik`
  - host: `api.dev-scj.site`
  - ports: `80, 443`
- Deployment:
  - name: `news-api`
  - namespace: `default`
  - readiness: `2/2`
  - deployment revision before restart: `13`
  - image: `seocj/news-api:latest`
  - `DATABASE_URL` injected from `news-api-secret`
  - nodeSelector: `workload=app`
  - conditions:
    - `Available=True`
    - `Progressing=True`
- Application logs:
  - Uvicorn startup completed.
  - Existing endpoints such as `/health`, `/sources`, `/collector/status` returned `200 OK`.
  - No application startup error was observed in the inspected logs.

### Notes

- Some generic external-looking requests such as `/wp-includes`, `/jsonrpc`, `/metrics`, and `/favicon.ico` returned `404` or `405`.
- These were not treated as application startup failures.
- At this point, production K3s resources were healthy, but the running Pods were still serving an image/application version without the `/topics` route.

## Production API Verification Before Restart

### Commands Run

```bash
curl -sS https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/version
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/1"
```

### Results

```json
{
  "status": "ok",
  "service": "news-api",
  "hostname": "news-api-778f97dc9b-85ztt"
}
```

```json
{
  "app": "news-api",
  "project": "NewsLab",
  "version": "0.2.0",
  "hostname": "news-api-778f97dc9b-vqnc2"
}
```

```json
{ "detail": "Not Found" }
```

```json
{ "detail": "Not Found" }
```

### Interpretation

- Production `/health` 정상 응답 확인.
- Production `/version` 정상 응답 확인.
- Production `/topics` returned `404 Not Found`.
- Production `/topics/1` returned `404 Not Found`.
- This indicated that the production `news-api` Pods were still serving the previous image/application version without the `/topics` route.
- The failure was interpreted as a rollout/image refresh issue, not a DB query issue.

## Human-controlled Rollout Restart

36차 topic summary API code가 production Pod에 반영되지 않은 것으로 확인되어, human operator가 `news-api` Deployment를 restart했다.

### Commands Run

```bash
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout restart deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl rollout status deployment/news-api -n default
KUBECONFIG=~/.kube/oci-k3s.yaml kubectl get pods -n default -l app=news-api
```

### Results

```text
NAME                       READY   STATUS    RESTARTS   AGE
news-api-f7c77f565-9sz7f   1/1     Running   0          24m
news-api-f7c77f565-nk64t   1/1     Running   0          25m
```

### Interpretation

- `news-api` Pods were recreated after rollout restart.
- New ReplicaSet prefix: `news-api-f7c77f565`
- Both Pods are `1/1 Running`.
- Restarts: `0`
- This confirms the Deployment restarted successfully and new Pods are serving traffic.

## Production API Verification After Restart

### Commands Run

```bash
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
```

### Results

```json
{
  "items": [
    {
      "id": 1,
      "topic_date": "2026-06-11",
      "title_ko": "주제 요약: Trump says US will hit Iran 'hard' again today",
      "summary_ko": "이 주제는 'Trump says US will hit Iran 'hard' again today'을 중심으로 1개 기사와 1개 출처의 원문을 검토한 deterministic 요약입니다.",
      "keywords": ["trump", "says", "us", "will", "hit"],
      "source_count": 1,
      "article_count": 1,
      "provider": "deterministic",
      "model": "deterministic-summary-v1",
      "status": "draft",
      "created_at": "2026-06-11T05:49:44.717308+00:00",
      "updated_at": "2026-06-11T05:49:44.717308+00:00"
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 1,
  "has_next": false
}
```

### Interpretation

- Production `/topics?page=1&page_size=10` now returns saved topic summary data.
- This confirms the `/topics` route is available in production after rollout restart.
- Saved deterministic topic summary with `id=1` is readable from production API.
- The list response includes:
  - `id=1`
  - `topic_date=2026-06-11`
  - `provider=deterministic`
  - `model=deterministic-summary-v1`
  - `status=draft`
  - `article_count=1`
  - `source_count=1`
  - `has_next=false`
- The response does not include `raw_text`.

## Production Detail / Raw Text / 404 Verification After Restart

### Commands Run

```bash
curl -sS "https://api.dev-scj.site/topics/1"
curl -sS "https://api.dev-scj.site/topics/1" | grep -i raw_text
curl -i -sS "https://api.dev-scj.site/topics/999999999"
```

### Results

`/topics/1` returned topic detail successfully.

Key fields confirmed:

- `id=1`
- `topic_date=2026-06-11`
- `topic_candidate_id=topic-0033`
- `provider=deterministic`
- `model=deterministic-summary-v1`
- `status=draft`
- `confidence=0.6`
- `article_count=1`
- `source_count=1`
- `summary_input_hash=04761e69f112776403e53f93566eb44828cbc8768856e41d1aaf58702289c62c`

Related article metadata confirmed:

- `article_id=889`
- `title=Trump says US will hit Iran 'hard' again today`
- `source=BBC World`
- `role=representative`
- `similarity_score=null`

Raw text omission check:

```bash
curl -sS "https://api.dev-scj.site/topics/1" | grep -i raw_text
```

Result:

```text
no matches
```

This confirms that the production topic detail response does not expose `raw_text`.

Missing topic check:

```bash
curl -i -sS "https://api.dev-scj.site/topics/999999999"
```

Result:

```text
HTTP/2 404
{"detail":"Topic not found"}
```

### Interpretation

- Production `/topics/1` detail API is available after rollout restart.
- Related article metadata is returned correctly.
- Production topic detail response does not include `raw_text`.
- Missing topic returns HTTP 404 with `{"detail":"Topic not found"}`.
- Production read verification passed.

### Safety

- No production DB write was performed.
- No Supabase SQL was executed.
- No save CLI `--execute` was run.
- No raw extraction was run.
- No provider call was run.

## Final Verification Result

37차 production read verification 결과는 다음과 같다.

- K3s Deployment/Pod/Service/Ingress 상태 확인: passed.
- 기존 production `/health`, `/version` 확인: passed.
- Restart 전 `/topics`, `/topics/1` 확인: failed with `404 Not Found`.
- Human-controlled rollout restart 수행: completed.
- Restart 후 production `/topics` 목록 조회: passed.
- Restart 후 production `/topics/1` 상세 조회: passed.
- Restart 후 production raw text 미노출 확인: passed.
- Restart 후 production missing topic 404 확인: passed.
- Production DB write: not performed.
- Supabase SQL: not performed.
- raw extraction: not performed.
- provider call: not performed.

## Pending Verification

The following checks are still pending unless separately executed and recorded.

- Main branch and GitHub Actions image build/push status confirmation, if needed for release traceability.
- README/RUNBOOK/ARCHITECTURE update necessity review based on final production verification scope.

## Evidence Notes

- Human-provided production verification logs were recorded above.
- Supabase SQL, manual SQL, save CLI `--execute`, and real DB write were not performed during this 37차 verification.
- Raw extraction and provider call were not performed.
- K3s rollout restart was performed manually by human operator.
- Deployment, production curl verification, and K3s checks were performed manually by human operator.
- Git push and git merge were not performed as part of this verification document update.
