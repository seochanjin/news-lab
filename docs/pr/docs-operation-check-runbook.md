# NewsLab 운영 점검 Runbook 정리

## 작업 내용

- NewsLab 운영자가 K3s cluster, monitoring stack, `news-api`, RSS
  collector, raw extractor의 현재 상태를 순서대로 판단할 수 있도록
  `docs/RUNBOOK.md`에 표준 운영 점검 절차를 정리했습니다.
- 운영 점검은 read-only 진단을 기본으로 하고, label/manifest 변경, Pod
  삭제, rollout, restart, manual Job 생성 등 변경성 대응은 human operator
  판단과 승인 대상으로 분리했습니다.

## 주요 변경 사항

- 빠른 상태 판단을 위한 quick health check 흐름과 정상 baseline을
  추가했습니다.
- Cluster, monitoring, application, CronJob 점검 절차를 분리했습니다.
- Grafana bundled dashboard별 확인 항목과 이상 판단 기준을 정리했습니다.
- `kubectl get/top/describe/logs`, `/health`, collector/extractor status API를
  이용한 read-only 진단 명령을 추가했습니다.
- Node NotReady, Pod Pending, Pod CrashLoopBackOff, OOMKilled, `news-api`
  unavailable, CronJob failure, Grafana/Prometheus unavailable 상황의 1차
  대응 순서를 추가했습니다.
- 정기 운영 점검 결과와 sanitized evidence를 기록할 수 있는 짧은
  checklist를 추가했습니다.

## 추가/변경된 API

- 없음.
- FastAPI route, response schema, application behavior를 변경하지
  않았습니다.

## DB 변경 사항

- 없음.
- DB schema, migration, Supabase SQL을 변경하거나 실행하지 않았습니다.

## README 영향

- README는 변경하지 않았습니다.
- 이번 작업은 operator-facing 운영 상세 절차를 기존 `docs/RUNBOOK.md`에
  정리하는 작업이며, root README의 프로젝트 소개와 로컬 실행 안내 범위를
  변경하지 않습니다.
- Approved fixes 문서에 따라 README의 Runbook 링크 추가는 deferred
  상태입니다.

## 테스트

`docs/verification/docs-operation-check-runbook.md`에 기록된 정적 검사:

```bash
git diff --check
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
git grep -n -E "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+"
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key"

ruby -e 'files=%w[docs/RUNBOOK.md docs/tasks/docs-operation-check-runbook.md docs/verification/docs-operation-check-runbook.md docs/pr/docs-operation-check-runbook.md docs/devlog/docs-operation-check-runbook.md]; bad=[]; files.each{|f| File.readlines(f).each_with_index{|line,i| bad << "#{f}:#{i+1}" if line.match?(/[ \t]+$/)}}; abort bad.join("\n") unless bad.empty?; puts "Workflow docs whitespace: OK"'

rg -n -i "100\.[0-9]+\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|192\.168\.[0-9]+\.[0-9]+|K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key" docs/RUNBOOK.md docs/tasks/docs-operation-check-runbook.md docs/verification/docs-operation-check-runbook.md docs/pr/docs-operation-check-runbook.md docs/devlog/docs-operation-check-runbook.md

rg -n "Quick Health Check|Cluster Checks|Monitoring Checks|Application Checks|CronJob Checks|Node NotReady|Pod Pending|Pod CrashLoopBackOff|OOMKilled|news-api Unavailable|CronJob Failure|Grafana or Prometheus Unavailable|Routine Check Record" docs/RUNBOOK.md
```

## 확인 결과

- `git diff --check`: 출력 없음, exit code `0`.
- Application source, DB, K3s manifest, collector/extractor script scope diff:
  출력 없음, exit code `0`.
- Private IP pattern 검사: 매치 없음.
- Credential pattern 검사: 기존 repository의 안전한 secret expression,
  검사 명령 문자열, redacted placeholder, Python `engine.begin()` false
  positive만 매치했으며 credential 값은 발견되지 않았습니다.
- Untracked workflow 문서를 포함한 whitespace 검사:
  `Workflow docs whitespace: OK`.
- Untracked workflow 문서를 포함한 `rg` 검사에서도 private IP와 credential
  값이 발견되지 않았습니다.
- Required quick check, category checks, seven common failure sections,
  routine checklist heading이 모두 확인되었습니다.
- Production read-only check와 Grafana UI 확인은 수행하지 않았습니다.

## 비고

- 이번 작업은 documentation-only입니다.
- Approved fixes는 없으며 fix-specific verification도 없습니다.
- FastAPI application source, DB, K3s manifest, collector/extractor runtime
  script, Alertmanager, Loki, PVC, external notification을 변경하지
  않았습니다.
- Agent는 production `kubectl`, production `curl`, Grafana 접속,
  `kubectl apply`, `kubectl rollout`, git push, git merge를 실행하지
  않았습니다.
- Human operator의 실제 production read-only 점검과 Grafana dashboard
  확인은 pending입니다.
- Production 상태, deployment, rollout, PR merge 완료를 주장하지
  않습니다.
