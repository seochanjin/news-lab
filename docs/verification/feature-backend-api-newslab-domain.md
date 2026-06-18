# Verification: backend api.newslab.ai.kr 도메인/TLS 전환

## Verification Scope

- `news-api-ingress`에 기존/신규 backend host가 함께 선언되는지 확인
- 각 host가 별도 TLS Secret을 사용하고 같은 `news-api` Service로 연결되는지 확인
- `letsencrypt-prod` ClusterIssuer annotation 유지 확인
- K3s manifest YAML syntax 확인
- application, DB, Docker, frontend, env, secret 값 비변경 확인
- Architecture/Runbook의 human-controlled 운영 검증 절차 확인

## Commands Run

```bash
git status --short --branch
rg -n "api.dev-scj.site|api.newslab.ai.kr|news-api-ingress|news-api-tls|news-api-newslab-tls|letsencrypt-prod" k8s docs
git diff --check
ruby -e 'require "yaml"; ARGV.each { |f| docs = YAML.load_stream(File.read(f)); puts "#{f}: #{docs.map { |d| d["kind"] }.compact.join(", ")}" }' k8s/*.yaml
git grep -n -i -E "API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|BEGIN|\\.env"
git diff --stat
git diff -- k8s docs
git diff -- app src scripts tests || true
ruby -e 'require "yaml"; ingress = YAML.load_stream(File.read("k8s/news-api.yaml")).find { |d| d["kind"] == "Ingress" }; raise "missing ingress" unless ingress; raise "issuer changed" unless ingress.dig("metadata", "annotations", "cert-manager.io/cluster-issuer") == "letsencrypt-prod"; tls = ingress.dig("spec", "tls"); rules = ingress.dig("spec", "rules"); expected_tls = {"api.dev-scj.site" => "news-api-tls", "api.newslab.ai.kr" => "news-api-newslab-tls"}; actual_tls = tls.to_h { |item| [item.fetch("hosts").fetch(0), item.fetch("secretName")] }; raise "tls mismatch: #{actual_tls}" unless actual_tls == expected_tls; expected_tls.each_key { |host| rule = rules.find { |item| item["host"] == host }; raise "missing rule #{host}" unless rule; service = rule.dig("http", "paths", 0, "backend", "service"); raise "service mismatch #{host}" unless service == {"name" => "news-api", "port" => {"number" => 80}} }; puts "news-api ingress domain/tls assertions passed"'
git diff --name-only
git diff -- app src scripts tests db Dockerfile .github || true
git status --short -- .env '.env.*' app src scripts tests db Dockerfile .github frontend
for f in docs/tasks/feature-backend-api-newslab-domain.md docs/verification/feature-backend-api-newslab-domain.md docs/pr/feature-backend-api-newslab-domain.md docs/devlog/feature-backend-api-newslab-domain.md; do git diff --no-index --check /dev/null "$f" >/dev/null; code=$?; if [ "$code" -ne 1 ]; then echo "$f: whitespace check failed with $code"; exit "$code"; fi; echo "$f: whitespace check passed"; done
for f in docs/verification/feature-backend-api-newslab-domain.md docs/pr/feature-backend-api-newslab-domain.md docs/devlog/feature-backend-api-newslab-domain.md; do git diff --no-index --check /dev/null "$f" >/dev/null; code=$?; if [ "$code" -ne 1 ]; then echo "$f: whitespace check failed with $code"; exit "$code"; fi; echo "$f: whitespace check passed"; done
git diff --check && ruby -e 'require "yaml"; ingress = YAML.load_stream(File.read("k8s/news-api.yaml")).find { |d| d["kind"] == "Ingress" }; expected = {"api.dev-scj.site" => "news-api-tls", "api.newslab.ai.kr" => "news-api-newslab-tls"}; actual = ingress.dig("spec", "tls").to_h { |item| [item.fetch("hosts").fetch(0), item.fetch("secretName")] }; raise unless actual == expected; raise unless ingress.dig("metadata", "annotations", "cert-manager.io/cluster-issuer") == "letsencrypt-prod"; raise unless ingress.dig("spec", "rules").map { |rule| rule["host"] } == expected.keys; puts "final static checks passed"'
```

## Results

- Current branch: `feature/backend-api-newslab-domain`.
- YAML stream parsing passed for all `k8s/*.yaml` files.
- `k8s/news-api.yaml` parsed as `Deployment, Service, Ingress`.
- Focused Ingress assertions passed with:
  - annotation `cert-manager.io/cluster-issuer: letsencrypt-prod`;
  - `api.dev-scj.site` → `news-api-tls`;
  - `api.newslab.ai.kr` → `news-api-newslab-tls`;
  - both host rules route to `news-api` Service port `80`.
- `git diff --check` passed.
- Tracked implementation diff is limited to:
  - `k8s/news-api.yaml`
  - `docs/ARCHITECTURE.md`
  - `docs/RUNBOOK.md`
- Protected-scope diff/status checks for application code, scripts, tests, DB,
  Dockerfile, GitHub Actions, frontend, `.env`, and `.env.*` were empty.
- Security grep matched existing safe references such as environment variable
  names, Kubernetes Secret object names, GitHub secret expressions,
  documentation command text, test-only values, and `engine.begin()` false
  positives. No credential or secret value was added by this change.
- The first untracked Markdown whitespace loop included the source task and
  returned exit code `3` because that existing task file uses Markdown
  hard-break trailing spaces. The task file was not modified.
- A focused whitespace check for the generated verification, PR, and devlog
  files passed.
- Final combined `git diff --check` and Ingress semantic assertions passed with
  `final static checks passed`.
- DB schema, migration, Supabase SQL, API route/response, Docker image workflow,
  and frontend API base URL were not changed.

## Manual or Production Verification

- Not run by Codex.
- No DNS lookup, kubectl command, manifest apply, rollout, Certificate/ACME
  query, production curl, git push, or git merge was performed.

## Pending Verification

- Human DNS verification:
  - `api.newslab.ai.kr` A record is `152.67.211.33`.
  - `api.newslab.ai.kr` has no AAAA record.
- Human `letsencrypt-prod` ClusterIssuer and existing Ingress preflight.
- Human server-side dry-run for `k8s/news-api.yaml`.
- Human-controlled `kubectl apply -f k8s/news-api.yaml`.
- Human verification that `news-api-ingress` contains both hosts and TLS
  Secret mappings.
- Human verification that `news-api-newslab-tls` exists and its Certificate is
  `Ready=True`.
- Human verification that the ACME Order is valid and no Challenge remains
  failed.
- Human HTTPS verification:
  - `https://api.newslab.ai.kr/health` returns HTTP 200.
  - `https://api.dev-scj.site/health` continues to return HTTP 200.
  - repeated checks for both hosts complete without failures.
- Frontend API base URL transition remains a separate follow-up task.

## Evidence Notes

- The manifest declares only TLS Secret names; it does not contain Secret
  values.
- The existing `api.dev-scj.site` rule and `news-api-tls` mapping remain in
  place.
- Production deployment, TLS issuance, HTTPS availability, rollout, and PR
  merge are not claimed complete.
