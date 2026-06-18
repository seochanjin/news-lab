# Approved Fixes: backend api.newslab.ai.kr 도메인/TLS 전환

## Approved Fixes

- CodeRabbit review에서 지적한 PR scope 표현을 수정한다.
  - 기존 문장은 변경 범위를 `k8s/news-api.yaml`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 중심으로만 설명해 실제 PR에 포함된 workflow 문서 범위가 축소되어 보일 수 있었다.
  - 기능 변경 파일과 작업 기록/검증/리뷰 문서를 구분해서 설명하도록 수정한다.
- CodeRabbit review에서 지적한 YAML parsing command를 수정한다.
  - 기존 Ruby `YAML.load_stream` 기반 command를 Python `yaml.safe_load_all` 기반 command로 교체한다.
  - `k8s/news-api.yaml`처럼 하나의 YAML 파일 안에 여러 Kubernetes resource가 `---`로 포함된 구조를 안전하게 검증할 수 있도록 한다.

## Rejected or Deferred Suggestions

- 없음.

이번 review에서 반려하거나 후속 작업으로 미룬 제안은 없다.

## Applied Changes

- `docs/reviews/feature-backend-api-newslab-domain-antigravity.md`
  - Scope Control 문장을 실제 PR 변경 범위에 맞게 수정했다.
  - 기능 변경은 `k8s/news-api.yaml`에 제한되었고, 운영 절차와 검증 근거를 남기기 위해 task, verification, PR, devlog, fixes, review 문서가 함께 추가 또는 수정되었음을 명확히 구분했다.
- `docs/tasks/feature-backend-api-newslab-domain.md`
  - YAML manifest 검증 command를 Ruby `YAML.load_stream`에서 Python `yaml.safe_load_all` 기반 command로 교체했다.
- `docs/reviews/feature-backend-api-newslab-domain-coderabbit.md`
  - CodeRabbit review 내용이 별도 문서로 기록되었다.

## Verification Required

PR merge 이전에 다음 정적 검증을 다시 수행한다.

- `git diff --check`
- Python `yaml.safe_load_all` 기반 YAML parsing command
- 변경 범위 확인
- secret scan
- backend application code, DB, Supabase SQL, Dockerfile, frontend 관련 파일이 변경되지 않았는지 확인

PR merge 이후 사람이 다음 운영 검증을 수행해야 한다.

- `api.newslab.ai.kr` DNS A record 확인
- `api.newslab.ai.kr` AAAA record 없음 확인
- server-side dry-run
- 실제 K3s apply
- `news-api-newslab-tls` Certificate 생성 및 `Ready=True` 확인
- ACME Order `valid` 확인
- `news-api-newslab-tls` Secret 생성 확인
- `https://api.newslab.ai.kr/health` 정상 응답 확인
- 기존 `https://api.dev-scj.site/health` 정상 유지 확인
- 신규/기존 API health endpoint 반복 curl 안정성 확인
