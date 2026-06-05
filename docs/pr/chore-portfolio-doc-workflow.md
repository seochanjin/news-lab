# README/포트폴리오 문서화 workflow 개선

## 작업 내용

- future worklog/devlog가 구현 내역뿐 아니라 portfolio-quality engineering decision documentation을 남기도록 prompt 규칙을 확장했습니다.
- devlog prompt에 대안 검토, 선택한 접근과 근거, 트레이드오프, README 업데이트 판단 섹션을 추가했습니다.
- PR draft prompt에 README 영향 섹션을 추가했습니다.
- `agent-handoff` 규칙에 README/portfolio documentation handoff 기준을 추가했습니다.
- `scripts/agent_next_step.sh`의 `devlog-draft`, `pr-draft` 출력이 새 섹션 요구사항을 포함하도록 업데이트했습니다.
- Runbook에 작업마다 README/portfolio documentation impact를 평가하라는 안내를 추가했습니다.
- 실제 실행한 static/local validation 결과를 verification 문서에 기록했습니다.

## 주요 변경 사항

- `docs/prompts/worklog-draft.md`
  - `## 대안 검토`
  - `## 선택한 접근과 근거`
  - `## 트레이드오프`
  - `## README 업데이트 판단`
  - alternatives/rationale/tradeoffs/README decision 기록 규칙 추가
- `docs/prompts/pr-draft.md`
  - `## README 영향` 섹션 추가
  - README 변경이 필요 없을 때도 간단히 이유를 적도록 규칙 추가
- `docs/prompts/agent-handoff.md`
  - PR/devlog handoff 규칙에 README 영향 판단 추가
  - `Portfolio Documentation Handoff` 섹션 추가
  - README 업데이트는 모든 작업에 필수는 아니지만 판단은 기록하도록 명시
- `scripts/agent_next_step.sh`
  - `devlog-draft` 출력에 새 portfolio documentation 섹션 추가
  - `pr-draft` 출력에 `## README 영향` 추가
- `docs/RUNBOOK.md`
  - PR/devlog 작성 전에 README/portfolio documentation impact를 평가하는 안내 추가
- `docs/verification/chore-portfolio-doc-workflow.md`
  - 실제 실행한 static/local validation 명령과 결과 기록

## 추가/변경된 API

- 없음.
- FastAPI app behavior, route, response는 변경하지 않았습니다.

## DB 변경 사항

- 없음.
- DB schema와 migration은 변경하지 않았습니다.
- Supabase SQL은 실행하지 않았습니다.

## README 영향

- README 파일 자체는 변경하지 않았습니다.
- 이번 작업은 README를 매번 수정하도록 강제하지 않고, future PR/devlog에서 README 영향 여부와 판단 근거를 기록하도록 workflow prompt를 개선합니다.
- 내부 workflow/documentation 개선이므로 현재 README 내용 변경은 필요하지 않다고 판단했습니다.

## 테스트

완료된 static/local validation:

```bash
bash -n scripts/agent_next_step.sh
```

```bash
scripts/agent_next_step.sh devlog-draft
```

```bash
scripts/agent_next_step.sh pr-draft
```

```bash
git diff --check
```

```bash
git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py
```

## 확인 결과

- `bash -n scripts/agent_next_step.sh`는 exit code 0, 출력 없음.
- `scripts/agent_next_step.sh devlog-draft`는 현재 branch 기준 devlog prompt를 출력했습니다.
- `devlog-draft` 출력에 다음 새 섹션이 포함됐습니다.
  - `## 대안 검토`
  - `## 선택한 접근과 근거`
  - `## 트레이드오프`
  - `## README 업데이트 판단`
  - `## 포트폴리오용 요약`
- `scripts/agent_next_step.sh pr-draft`는 현재 branch 기준 PR draft prompt를 출력했습니다.
- `pr-draft` 출력에 `## README 영향`이 포함됐습니다.
- 생성된 prompt는 human-controlled operation boundaries를 유지했습니다.
- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py`는 exit code 0, 출력 없음.
- FastAPI app, DB, K8s manifest, collector script, extractor script 변경 없음이 확인됐습니다.
- Production verification은 이 workflow/documentation task에는 해당 없음으로 기록했습니다.

## 비고

- Approved fixes: 없음.
- Antigravity review에서 PR 전 필수 수정 사항은 없었습니다.
- CodeRabbit review file은 현재 template만 있고 findings는 없습니다.
- 이번 작업은 task의 Alternative C를 따릅니다: README impact와 alternatives review를 workflow prompt에 추가하되, README 업데이트를 모든 작업에 강제하지 않습니다.
- PR merge, production deployment, K3s rollout, production verification 완료를 주장하지 않습니다.
- `kubectl`, rollout, Supabase SQL, production `curl`, `git push`, `git merge`는 실행하지 않았습니다.
- GitHub MCP integration과 외부 agent 자동 실행은 하지 않았습니다.
