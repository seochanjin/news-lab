# Approved Fixes: Raw extraction target 기반 제한 실행 CLI

## Approved Fixes

없음.

Antigravity review 결과 `feature/raw-extraction-target-runner` 브랜치는 요구사항, 운영 안전성, scope control, verification integrity 측면에서 `PASS` 판정을 받았다.

리뷰에서 PR 전 필수 수정 사항은 발견되지 않았다.

확인된 주요 내용은 다음과 같다.

- 기본 동작은 dry-run으로 유지된다.
- `--execute` 없이 실제 raw extraction이 실행되지 않는다.
- dry-run에서는 DB write가 발생하지 않는다.
- `--execute` 실행 시 `--limit`가 필수이며, 허용 범위는 `1~5`로 제한된다.
- 실행 후보는 `extraction_target_status=target` article만 포함한다.
- `backup`, `skipped`, `already_extracted`, `failed` article은 실행 후보에서 제외된다.
- execute integration은 실제 실행이 아니라 mock/unit test로만 검증되었다.
- 기존 `scripts/extract_raw_articles.py`의 기본 `extract()` entrypoint와 CronJob 실행 의미는 유지된다.
- 신규 selected-ID extraction path는 opt-in 구조다.
- API, DB schema, K8s manifest, CronJob, frontend 변경은 없다.
- OpenAI, embedding, summary, LLM provider 호출은 없다.
- topic summary 생성은 포함하지 않는다.

## Rejected or Deferred Suggestions

없음.

Antigravity review에서 별도의 optional improvement 또는 deferred suggestion은 제시되지 않았다.

다만 CodeRabbit 또는 후속 리팩토링 단계에서 docstring coverage, CLI hardening, execute-mode error report 개선 같은 문서화/품질 개선 항목이 나오면 별도 차수에서 검토한다.

## Applied Changes

없음.

이번 문서는 Antigravity review 결과가 `PASS`였음을 기록하기 위한 문서다.  
리뷰 결과를 근거로 추가 코드 수정은 수행하지 않는다.

현재 구현 상태는 다음과 같다.

- `scripts/run_raw_extraction_targets.py`
  - raw extraction target 기반 execution plan 생성
  - 기본 dry-run
  - `--execute` / `--limit` guard
  - execution candidate filtering
  - markdown/JSON report 출력

- `scripts/extract_raw_articles.py`
  - 기존 `extract()` 기본 동작 유지
  - selected article id 기반 opt-in extraction helper 추가

- `tests/test_run_raw_extraction_targets.py`
  - dry-run 기본 동작
  - execute/limit guard
  - mock executor 기반 execute path
  - target-only candidate filtering 검증

- `docs/reports/feature-raw-extraction-target-runner-dry-run.md`
  - dry-run execution plan report 생성

## Verification Required

추가 fix가 없으므로 별도 재검증은 필수는 아니다.

PR 전 최종 확인용으로 아래 명령만 다시 확인한다.

```bash
git status --short --branch
git diff --stat
git diff --check
```

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
.venv/bin/python scripts/run_raw_extraction_targets.py --help
```

다음 사항은 계속 유지되어야 한다.

- 실제 raw extraction 실행 없음
- `--execute` 명령 실행 없음
- DB write 없음
- OpenAI/LLM provider 호출 없음
- K8s/CronJob/API/DB schema/frontend 변경 없음
- production verification 없음
- rollout/deployment 없음
