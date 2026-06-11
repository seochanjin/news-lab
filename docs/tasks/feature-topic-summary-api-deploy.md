# Task: Topic summary API 운영 배포 및 production read verification

## Goal

36차에서 구현한 topic summary DB 저장 및 `/topics` read API를 운영 K3s 환경에 반영하고, production API에서 정상 조회되는지 검증한다.

이번 작업의 목표는 새로운 기능을 추가하는 것이 아니라, 이미 local/Supabase 환경에서 검증한 다음 기능이 운영 API에서도 안전하게 동작하는지 확인하는 것이다.

- `GET /topics`
- `GET /topics/{topic_id}`
- `topics`, `topic_articles` 기반 조회
- related article metadata 조회
- raw text 미노출

이번 작업은 38차 CronJob 자동화 전에 수행하는 production read verification 단계다.

## Scope

이번 작업 범위는 다음과 같다.

### 1. 운영 배포 준비 확인

- 36차에서 merge된 topic summary API 코드가 main branch에 반영되어 있는지 확인한다.
- GitHub Actions image build/push 상태를 확인한다.
- 운영 K3s가 사용할 image tag 또는 rollout 대상이 올바른지 확인한다.
- DB migration은 이미 human operator가 Supabase SQL Editor에서 적용한 상태를 전제로 한다.
- 추가 DB migration은 수행하지 않는다.

### 2. K3s rollout 확인

운영 배포는 human-controlled operation으로 수행한다.

확인 대상:

- `news-api` Deployment rollout
- `news-api` Pod 상태
- Service/Ingress 상태
- image tag 또는 rollout revision
- application logs에서 startup error 여부

예상 확인 명령은 verification에 실제 실행 결과로 기록한다.

### 3. Production API read verification

운영 API에서 다음 read-only endpoint를 확인한다.

- `GET https://api.dev-scj.site/health`
- `GET https://api.dev-scj.site/version`
- `GET https://api.dev-scj.site/topics?page=1&page_size=10`
- `GET https://api.dev-scj.site/topics/1`

검증 포인트:

- `/health` 정상 응답
- `/version` 정상 응답
- `/topics`에서 저장된 topic summary 조회 가능
- `/topics/{topic_id}`에서 related article metadata 조회 가능
- `/topics`, `/topics/{topic_id}` 응답에 `raw_text` 미포함
- 404 behavior 확인 가능하면 확인
- production DB write 없음
- raw extraction 실행 없음
- provider call 없음

### 4. 문서 업데이트

운영 read API가 확인되면 문서에 반영한다.

업데이트 후보:

- `docs/verification/feature-topic-summary-api-deploy.md`
- `docs/devlog/feature-topic-summary-api-deploy.md`
- `docs/pr/feature-topic-summary-api-deploy.md`
- `docs/reviews/feature-topic-summary-api-deploy-antigravity.md`
- `docs/fixes/feature-topic-summary-api-deploy-approved-fixes.md`
- `README.md`
- `docs/RUNBOOK.md`
- `docs/ARCHITECTURE.md`

README/RUNBOOK/ARCHITECTURE 업데이트는 이번 작업에서 `/topics` API가 production application surface로 확인된 경우에만 수행한다.

## Do not change

이번 작업에서 다음은 변경하지 않는다.

- DB schema 변경 금지
- 신규 migration 추가 금지
- Supabase SQL 실행 금지
- topic summary save CLI `--execute` 실행 금지
- raw extraction 실행 금지
- provider call 실행 금지
- CronJob 추가/수정 금지
- frontend 변경 금지
- factuality/quality gate 구현 금지
- provider fallback/retry 구현 금지
- 대량 topic 저장 금지
- `gpt-5-mini` 자동 사용 금지
- K8s manifest 변경 금지
- Dockerfile 변경 금지
- GitHub Actions workflow 변경 금지
- secrets, `.env`, kubeconfig, SSH key, token, credential 변경 금지
- production DB write 금지
- production API에 raw text 노출 금지

K3s rollout, production curl verification, PR merge는 human-controlled operation이다.  
Codex나 review agent는 이를 직접 실행하지 않는다.

## Expected files

예상 추가/변경 파일:

```text
docs/tasks/feature-topic-summary-api-deploy.md
docs/verification/feature-topic-summary-api-deploy.md
docs/devlog/feature-topic-summary-api-deploy.md
docs/pr/feature-topic-summary-api-deploy.md
docs/reviews/feature-topic-summary-api-deploy-antigravity.md
docs/fixes/feature-topic-summary-api-deploy-approved-fixes.md
README.md
docs/RUNBOOK.md
docs/ARCHITECTURE.md
```

실제 변경 파일은 구현 결과에 따라 조정한다.

이번 작업은 기본적으로 운영 반영 검증과 문서화 작업이다.  
코드 변경은 원칙적으로 필요하지 않다. 단, production deployment 과정에서 문서와 실제 동작이 불일치하는 작은 오류가 발견되면 별도 approved fix로 처리한다.

## DB changes

이번 작업에서는 DB schema를 변경하지 않는다.

전제 조건:

- 36차에서 추가한 `topics`, `topic_articles` migration SQL이 Supabase에 human operator에 의해 이미 적용되어 있다.
- 최소 1개의 deterministic topic summary와 related article link가 저장되어 있다.
- production API는 기존 `DATABASE_URL`을 통해 같은 Supabase DB를 조회한다.

금지 사항:

- 신규 migration 작성 금지
- Supabase SQL 실행 금지
- manual SQL 실행 금지
- save CLI `--execute` 실행 금지
- production DB write 금지

DB 관련 확인은 read-only 조회 또는 production API 응답 검증으로 제한한다.

## API changes

이번 작업에서는 새 API를 추가하지 않는다.

검증 대상 API:

### GET `/topics`

저장된 topic summary 목록을 pagination으로 조회한다.

검증할 응답 요소:

- `items`
- `page`
- `page_size`
- `total`
- `has_next`
- topic item fields:
  - `id`
  - `topic_date`
  - `title_ko`
  - `summary_ko`
  - `keywords`
  - `source_count`
  - `article_count`
  - `provider`
  - `model`
  - `status`
  - `created_at`
  - `updated_at`

### GET `/topics/{topic_id}`

단일 topic summary와 related article metadata를 조회한다.

검증할 응답 요소:

- topic fields
- `key_points`
- `keywords`
- `summary_input_hash`
- `articles`
  - `article_id`
  - `title`
  - `url`
  - `source`
  - `published_at`
  - `role`
  - `similarity_score`

두 API 응답에 `raw_text`가 포함되면 안 된다.

## Test commands

Codex 또는 local verification에서 실행 가능한 명령:

### Local/static checks

```bash
git status --short --branch
git diff --stat
git diff --check
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### Scope checks

```bash
git diff -- k8s
git diff -- .github
git diff -- frontend
git diff -- Dockerfile
git diff -- db
```

### Security checks

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

```bash
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app scripts tests docs db
```

### Human-controlled K3s verification

다음 명령은 human operator가 직접 실행하고 결과를 verification 문서에 기록한다.

```bash
kubectl --kubeconfig ~/.kube/oci-k3s.yaml get pods -n default
kubectl --kubeconfig ~/.kube/oci-k3s.yaml rollout status deployment/news-api -n default
kubectl --kubeconfig ~/.kube/oci-k3s.yaml get svc,ingress -n default
kubectl --kubeconfig ~/.kube/oci-k3s.yaml logs -n default deployment/news-api --tail=100
```

실제 namespace 또는 deployment 이름이 다르면 기존 RUNBOOK 기준을 따른다.

### Human-controlled production API verification

다음 명령은 human operator가 직접 실행하고 결과를 verification 문서에 기록한다.

```bash
curl -sS https://api.dev-scj.site/health
curl -sS https://api.dev-scj.site/version
curl -sS "https://api.dev-scj.site/topics?page=1&page_size=10"
curl -sS "https://api.dev-scj.site/topics/1"
```

raw text 미노출 확인:

```bash
curl -sS "https://api.dev-scj.site/topics/1" | grep -i raw_text
```

예상 결과:

- `grep` 결과 없음
- 또는 command exit code가 no match임을 verification에 기록

404 확인이 필요하면 다음을 실행한다.

```bash
curl -i -sS "https://api.dev-scj.site/topics/999999999"
```

예상 결과:

- HTTP 404

## Acceptance criteria

완료 기준은 다음과 같다.

- 36차 topic summary API 코드가 운영 배포 대상에 포함되어 있다.
- `news-api` Deployment rollout이 정상 완료되었다.
- production `news-api` Pod가 정상 상태다.
- production `/health`가 정상 응답한다.
- production `/version`이 정상 응답한다.
- production `/topics?page=1&page_size=10`이 정상 응답한다.
- production `/topics/{topic_id}`가 정상 응답한다.
- `/topics` 목록에서 저장된 topic summary가 조회된다.
- `/topics/{topic_id}` 상세에서 related article metadata가 조회된다.
- production API 응답에 `raw_text`가 포함되지 않는다.
- production DB write가 발생하지 않았다.
- raw extraction이 실행되지 않았다.
- provider call이 실행되지 않았다.
- K8s manifest, CronJob, Dockerfile, GitHub Actions, frontend, DB schema 변경이 없다.
- README/RUNBOOK/ARCHITECTURE가 production 확인 결과에 맞게 업데이트되었거나, 업데이트하지 않은 경우 이유가 devlog에 기록되어 있다.
- verification 문서에 실제 human-run command와 결과가 기록되어 있다.
- production deployment/verification을 수행한 경우, “Codex가 수행했다”고 기록하지 않는다.

## Notes

- 이 작업은 36차의 DB 저장 및 read API 구현 후속 단계다.
- 38차 CronJob 자동화 전에 production read path가 정상인지 확인하는 것이 목적이다.
- 이번 작업에서 summary 자동 저장은 하지 않는다.
- 이번 작업에서 provider 기반 save는 하지 않는다.
- 이번 작업에서 raw extraction은 하지 않는다.
- production verification은 read-only로 제한한다.
- production deployment와 K3s rollout은 반드시 human-controlled operation으로 수행한다.
- `/topics` production read verification이 완료되면, 다음 단계에서 CronJob 자동화를 설계할 수 있다.
- README/RUNBOOK/ARCHITECTURE는 이번 검증 결과를 기준으로 필요한 범위만 업데이트한다.
