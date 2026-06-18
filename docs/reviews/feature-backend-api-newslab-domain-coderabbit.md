# CodeRabbit Review: backend api.newslab.ai.kr 도메인/TLS 전환

## Review Summary

CodeRabbit review에서는 backend `api.newslab.ai.kr` 도메인/TLS 전환 작업에 대해 두 가지 minor 문서 개선 사항을 제안했다.

첫 번째는 Antigravity review 문서의 PR scope 표현이 실제 변경 범위를 다소 축소해서 설명한다는 지적이다. 기능 변경은 `k8s/news-api.yaml`에 집중되어 있지만, 실제 PR에는 task, verification, devlog, PR, fixes, review 문서도 포함된다. 따라서 기능 변경 범위와 workflow 문서 추가 범위를 구분해서 설명하는 편이 더 정확하다.

두 번째는 task 문서의 YAML parsing command가 Ruby `YAML.load_stream`을 사용하고 있어, repository의 다른 task 문서와 검증 command 스타일이 다르고 보안 측면에서도 Python `yaml.safe_load_all` 기반 command가 더 적절하다는 제안이다.

두 항목 모두 Kubernetes manifest 동작 자체의 결함은 아니며, 문서 정합성과 이후 agent workflow 안정성을 높이기 위한 minor 개선 사항으로 판단했다.

## Problems Found

### 1. PR scope 설명이 실제 변경 범위를 축소해서 보일 수 있음

기존 Antigravity review 문서의 Scope Control 설명은 변경 범위를 `k8s/news-api.yaml`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 중심으로 설명했다.

하지만 실제 PR에는 다음 workflow 문서들도 함께 포함된다.

```text
docs/tasks/feature-backend-api-newslab-domain.md
docs/verification/feature-backend-api-newslab-domain.md
docs/pr/feature-backend-api-newslab-domain.md
docs/devlog/...
docs/fixes/...
docs/reviews/...
```

따라서 이후 AI agent나 reviewer가 문서를 읽을 때 실제 PR 변경 범위를 오해할 수 있다.

### 2. YAML parsing command가 Ruby `YAML.load_stream` 기반임

기존 task 문서에는 다음 형태의 command가 포함되어 있었다.

```bash
ruby -e 'require "yaml"; ARGV.each { |f| docs = YAML.load_stream(File.read(f)); puts "#{f}: #{docs.map { |d| d["kind"] }.compact.join(", ")}" }' k8s/*.yaml
```

CodeRabbit은 repository의 다른 task 문서와의 일관성 및 안전한 YAML parsing 관점에서 Python `yaml.safe_load_all` 기반 command로 교체하는 것을 제안했다.

## Required Fixes Before PR

- Antigravity review 문서의 Scope Control 설명을 실제 PR 변경 범위에 맞게 수정한다.
  - 기능 변경은 backend Ingress manifest인 `k8s/news-api.yaml`에 제한되었음을 명시한다.
  - 운영 절차와 검증 근거를 남기기 위해 task, verification, PR, devlog, fixes, review 문서가 함께 추가 또는 수정되었음을 명시한다.
- task 문서의 YAML parsing command를 Python `yaml.safe_load_all` 기반 command로 교체한다.

권장 command:

```bash
python - <<'PY'
from pathlib import Path
import yaml

for path in sorted(Path("k8s").glob("*.yaml")):
    docs = list(yaml.safe_load_all(path.read_text()))
    kinds = [doc.get("kind") for doc in docs if isinstance(doc, dict) and doc.get("kind")]
    print(f"{path}: {', '.join(kinds)}")
PY
```

## Optional Improvements

- 없음.

이번 CodeRabbit review의 지적은 모두 문서 정합성과 검증 command 품질 개선에 해당하며, 별도 후속 개선으로 미룰 필요는 없다.

## Suggested Test Commands

수정 후 다음 command를 수행한다.

```bash
git diff --check
```

```bash
python - <<'PY'
from pathlib import Path
import yaml

for path in sorted(Path("k8s").glob("*.yaml")):
    docs = list(yaml.safe_load_all(path.read_text()))
    kinds = [doc.get("kind") for doc in docs if isinstance(doc, dict) and doc.get("kind")]
    print(f"{path}: {', '.join(kinds)}")
PY
```

```bash
git diff --stat
git diff -- docs/tasks/feature-backend-api-newslab-domain.md docs/reviews/feature-backend-api-newslab-domain-antigravity.md docs/fixes/feature-backend-api-newslab-domain-approved-fixes.md docs/reviews/feature-backend-api-newslab-domain-coderabbit.md
```

```bash
git grep -n -i -E "API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|BEGIN|\\.env"
```

## Risk Notes

- 이번 CodeRabbit 지적은 Kubernetes Ingress/TLS manifest의 기능적 결함을 의미하지 않는다.
- `api.dev-scj.site` 유지, `api.newslab.ai.kr` 추가, `news-api-newslab-tls` Secret 분리 정책에는 영향을 주지 않는다.
- backend application code, DB, Supabase SQL, Dockerfile, frontend code 변경은 필요하지 않다.
- 다만 scope 문장이 부정확하면 이후 AI agent가 실제 PR 변경 범위를 잘못 해석할 수 있으므로 수정하는 것이 좋다.
- YAML parsing command를 Python `yaml.safe_load_all`로 통일하면 이후 task 문서에서 같은 검증 패턴을 재사용하기 쉽다.
