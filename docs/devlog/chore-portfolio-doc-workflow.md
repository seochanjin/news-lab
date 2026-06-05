# README/포트폴리오 문서화 workflow 개선

## 작업 목적

- NewsLab 작업 기록이 단순 구현 로그를 넘어 portfolio-quality engineering decision documentation 역할을 하도록 workflow prompt를 개선한다.
- future worklog/devlog가 대안 검토, 선택 근거, 트레이드오프, README 업데이트 판단을 빠뜨리지 않도록 표준 섹션을 추가한다.
- README 업데이트를 모든 작업에 강제하지 않되, README 영향 여부와 판단 근거를 PR/devlog에 명시하도록 한다.
- 기존 agent workflow의 source of truth 경계인 `docs/tasks/`, `docs/fixes/`, `docs/verification/` 구조는 유지한다.

## 기존 문제

- 기존 worklog/devlog prompt는 구현 내용, 테스트, 운영 반영, 확인 결과 중심이었다.
- 포트폴리오 관점에서 중요한 “왜 이 접근을 선택했는지”, “다른 대안은 무엇이었는지”, “어떤 트레이드오프가 있었는지”가 매번 기록된다는 보장이 없었다.
- README 업데이트가 필요한 작업인지 판단하는 절차가 prompt에 명시되어 있지 않았다.
- README를 모든 작업마다 수정하도록 강제하면 내부 workflow 변경에도 불필요한 README churn이 생길 수 있었다.

## 변경 내용

- `docs/prompts/worklog-draft.md` 업데이트
  - `## 대안 검토`
  - `## 선택한 접근과 근거`
  - `## 트레이드오프`
  - `## README 업데이트 판단`
  - alternatives/rationale/tradeoffs/README decision 기록 규칙 추가
- `docs/prompts/pr-draft.md` 업데이트
  - `## README 영향` 섹션 추가
  - README 변경이 필요하지 않을 때도 짧게 이유를 적도록 규칙 추가
- `docs/prompts/agent-handoff.md` 업데이트
  - PR/devlog handoff 규칙에 README 영향 판단 추가
  - `Portfolio Documentation Handoff` 섹션 추가
  - README 업데이트는 필수가 아니지만 판단 기록은 필요하다고 명시
- `scripts/agent_next_step.sh` 업데이트
  - `devlog-draft` 출력에 새 devlog 섹션 추가
  - `pr-draft` 출력에 `## README 영향` 추가
- `docs/RUNBOOK.md` 업데이트
  - task마다 README/portfolio documentation impact를 평가하라는 안내 추가
- `docs/verification/chore-portfolio-doc-workflow.md` 업데이트
  - static/local validation 결과 기록

## 구현 상세

- 기존 workflow prompt 구조를 유지하면서 portfolio 문서화에 필요한 섹션만 추가했다.
- `agent_next_step.sh`는 계속 prompt template만 출력한다.
- Codex, Gemini/Antigravity, GitHub, CodeRabbit을 자동 실행하지 않는다.
- GitHub MCP integration은 추가하지 않았다.
- FastAPI app, DB, K8s manifest, collector/extractor runtime script는 변경하지 않았다.
- review 결과를 검토했지만 approved fixes는 없었고, 별도 review fix도 적용하지 않았다.

## 대안 검토

### Alternative A: 각 devlog 작성 후 수동으로 대안 섹션 추가

- 장점: 작업마다 자유롭게 문서 구조를 조정할 수 있다.
- 단점: 사람이 잊기 쉽고, 작업별 문서 품질이 흔들릴 수 있다.

### Alternative B: 모든 작업에서 README 업데이트 강제

- 장점: README가 항상 최신 상태로 유지될 가능성이 높다.
- 단점: 내부 workflow 변경처럼 README 영향이 작은 작업에도 불필요한 변경이 생길 수 있다.

### Alternative C: workflow prompt에 README 영향과 alternatives review를 추가

- 장점: 모든 작업이 README/portfolio 영향을 평가하지만, README 변경은 필요한 경우에만 수행할 수 있다.
- 단점: devlog와 PR prompt가 조금 더 길어진다.

## 선택한 접근과 근거

- 선택한 접근: Alternative C.
- 이유:
  - portfolio-quality documentation에 필요한 판단 항목을 workflow에 기본 내장할 수 있다.
  - README 업데이트를 모든 작업에 강제하지 않아 불필요한 문서 churn을 피할 수 있다.
  - 기존 `docs/tasks/`, `docs/verification/`, `docs/fixes/` source of truth 구조와 잘 맞는다.
  - helper script의 prompt 출력만 바꾸면 future workflow에 바로 반영된다.

## 트레이드오프

- devlog/PR prompt가 이전보다 길어진다.
- 내부 작업에도 README 영향 여부를 판단해야 하므로 작성자가 생각해야 할 항목이 늘어난다.
- 대신 작업의 의사결정 맥락이 더 안정적으로 남고, portfolio로 옮길 수 있는 설명 품질이 올라간다.
- README 업데이트를 필수화하지 않았기 때문에 README 최신성은 여전히 작업별 판단에 의존한다.

## 테스트

실제 실행한 static/local validation:

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

## 운영 반영

- 이 작업은 workflow prompt와 documentation 변경이다.
- Production verification은 해당 없음.
- `kubectl apply`, `kubectl rollout`, Supabase SQL, production `curl`, `git push`, `git merge`는 실행하지 않았다.
- GitHub MCP, Codex/Gemini/Antigravity/GitHub/CodeRabbit 자동 실행도 수행하지 않았다.

## README 업데이트 판단

- README 파일은 변경하지 않았다.
- 이번 작업은 README의 사용자-facing 사용법이나 시스템 architecture 자체를 바꾸지 않는다.
- 대신 future PR/devlog가 README 영향 여부를 판단하도록 workflow prompt와 Runbook을 개선했다.
- 따라서 현재 PR에서는 README 직접 수정이 필요하지 않다고 판단했다.

## 확인 결과

- `bash -n scripts/agent_next_step.sh`는 exit code 0, 출력 없음.
- `scripts/agent_next_step.sh devlog-draft`는 현재 branch 기준 devlog prompt를 출력했다.
- `devlog-draft` 출력에 다음 새 섹션이 포함됐다.
  - `## 대안 검토`
  - `## 선택한 접근과 근거`
  - `## 트레이드오프`
  - `## README 업데이트 판단`
  - `## 포트폴리오용 요약`
- `scripts/agent_next_step.sh pr-draft`는 현재 branch 기준 PR draft prompt를 출력했다.
- `pr-draft` 출력에 `## README 영향`이 포함됐다.
- 생성된 prompt는 human-controlled operation boundaries를 유지했다.
- `git diff --check`는 exit code 0, 출력 없음.
- `git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py`는 exit code 0, 출력 없음.
- FastAPI app, DB, K8s manifest, collector script, extractor script 변경 없음이 확인됐다.
- Approved fixes는 없음.
- Production verification은 이 workflow/documentation task에는 해당 없음.

## 이번 단계의 의미

- NewsLab의 작업 기록이 구현 이력뿐 아니라 engineering decision record로도 기능하도록 workflow를 개선했다.
- future worklog가 “무엇을 했는가”뿐 아니라 “왜 그렇게 했는가”를 더 일관되게 남기게 된다.
- README 업데이트 판단을 명시함으로써 공개 문서와 내부 작업 로그 사이의 연결이 더 분명해졌다.
- 작업별 포트폴리오 요약 품질이 담당자 기억에 덜 의존하게 되었다.

## 포트폴리오용 요약

- NewsLab agent workflow에 portfolio-oriented documentation decision 단계를 추가했다.
- devlog prompt는 대안 검토, 선택 근거, 트레이드오프, README 업데이트 판단을 포함하도록 확장했다.
- PR draft prompt는 README 영향 섹션을 포함하도록 변경했다.
- README를 모든 작업에 강제 업데이트하지 않고, 영향 여부를 명시적으로 판단하는 균형 잡힌 workflow를 선택했다.

## 다음 단계 후보

- 다음 feature/chore 작업에서 새 devlog/PR prompt를 실제로 사용해 문서 품질을 확인한다.
- prompt가 과도하게 길거나 중복된다면 섹션 설명을 다듬는다.
- README 영향 판단이 반복적으로 “없음”으로만 기록된다면 README 업데이트 기준을 더 구체화한다.
- 공개 portfolio README나 project overview 문서를 별도로 개선할 필요가 생기면 별도 task로 분리한다.
