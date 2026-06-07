# Verification: NewsLab 운영 점검 Runbook 정리

## Verification Scope

- `docs/RUNBOOK.md`에 추가한 운영 점검 절차의 문서 정합성 확인.
- Application source, DB, K3s manifest, collector/extractor script가 변경되지
  않았는지 확인.
- Private IP와 credential 값이 문서에 추가되지 않았는지 확인.

## Commands Run

```bash
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key"

ruby -e 'files=%w[docs/RUNBOOK.md docs/tasks/docs-operation-check-runbook.md docs/verification/docs-operation-check-runbook.md docs/pr/docs-operation-check-runbook.md docs/devlog/docs-operation-check-runbook.md]; bad=[]; files.each{|f| File.readlines(f).each_with_index{|line,i| bad << "#{f}:#{i+1}" if line.match?(/[ \t]+$/)}}; abort bad.join("\n") unless bad.empty?; puts "Workflow docs whitespace: OK"'

rg -n -i "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key" docs/RUNBOOK.md docs/tasks/docs-operation-check-runbook.md docs/verification/docs-operation-check-runbook.md docs/pr/docs-operation-check-runbook.md docs/devlog/docs-operation-check-runbook.md

rg -n "Quick Health Check|Cluster Checks|Monitoring Checks|Application Checks|CronJob Checks|Node NotReady|Pod Pending|Pod CrashLoopBackOff|OOMKilled|news-api Unavailable|CronJob Failure|Grafana or Prometheus Unavailable|Routine Check Record" docs/RUNBOOK.md
```

## Results

- `git diff --check`: exit code `0`, 출력 없음.
- Scope diff check: exit code `0`, 출력 없음.
- Private IP pattern check: exit code `1`, 출력 없음. 매치가 발견되지 않음.
- Credential pattern check: exit code `0`. 기존 repository의 안전한 secret
  expression, 검사 명령 문자열, redacted placeholder, Python
  `engine.begin()` false positive만 매치했으며 credential 값은 발견되지
  않음.
- Workflow docs whitespace check: `Workflow docs whitespace: OK`.
- Untracked workflow 파일을 포함한 `rg` 검사: private IP 매치 없음.
  Credential 패턴은 task/verification/PR에 기록한 검사 명령 문자열과
  verification의 `engine.begin()` 설명만 매치했으며 credential 값은
  발견되지 않음.
- Acceptance section check: required quick check, category checks, seven common
  failure sections, and routine checklist headings가 모두 매치됨.

## Manual or Production Verification

- 수행하지 않음.
- Agent는 production `kubectl`, production `curl`, Grafana 접속,
  `kubectl apply`, `kubectl rollout`, git push, git merge를 실행하지 않음.

## Pending Verification

- Human operator가 필요 시 Runbook의 read-only quick health check를 실제
  production 환경에서 수행하고 sanitized 결과를 별도 verification 기록에
  남겨야 함.
- Grafana bundled dashboard 이름은 설치된 kube-prometheus-stack 버전에
  따라 약간 다를 수 있으므로 실제 UI에서 확인 필요.

## Evidence Notes

- 이번 verification은 documentation static check만 포함함.
- Production 상태가 정상이라고 주장하지 않음.
- `docs/tasks/`, `docs/verification/`, `docs/pr/`, `docs/devlog/` workflow
  파일은 현재 untracked 상태이므로 `git diff --check`와 `git grep`의 검사
  대상에 포함되지 않는다. 별도 whitespace와 `rg` 검사로 이를 보완했다.
