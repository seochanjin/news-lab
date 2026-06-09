# Approved Fixes: URL 정규화와 중복 후보 분석 MVP

## Approved Fixes

None.

Antigravity review 결과 Required Fixes Before PR는 없음으로 확인되었다.

이번 branch는 다음 조건을 만족한다.

- URL normalization helper가 deterministic rule 기반으로 구현되어 있다.
- tracking parameter 제거가 구현되어 있다.
- title normalization 및 title hash 생성 로직이 구현되어 있다.
- duplicate analysis script가 DB read-only 방식으로 동작한다.
- 24h / 72h / 168h / all window 분석을 지원한다.
- published_at 기준과 created_at 기준 분석을 구분한다.
- DB migration, DB write, K8s 변경, production rollout은 수행하지 않는다.
- LLM, embedding, topic grouping, summary 생성은 scope 밖으로 유지되었다.
- verification 결과 unit test 9개 통과, Python compile 통과, dry-run DB read-only 분석 완료가 기록되어 있다.

따라서 PR 전에 반드시 반영해야 할 blocking fix는 없다.

## Rejected or Deferred Suggestions

### Deferred 1. 대용량 데이터 대비 chunk/batch 처리

Antigravity review에서 현재 duplicate analysis script가 분석 대상 article을 메모리에 한 번에 올리는 구조라는 점이 optional improvement로 제안되었다.

이번 28차에서는 해당 개선을 보류한다.

보류 이유:

- 현재 분석 대상 article 수는 수백 건 수준이다.
- Verification 기준 전체 분석 대상은 all-time 기준 376건으로 확인되었다.
- 이번 task의 목적은 URL 정규화와 중복 후보 분석 MVP를 검증하는 것이다.
- chunk/batch 처리는 article 수가 수만 건 이상으로 증가했을 때 필요한 확장성 개선에 가깝다.
- 현재 규모에서는 운영 위험이나 기능 blocker로 보지 않는다.

후속 검토 방향:

- article 수가 수천~수만 건 이상으로 증가하면 chunk 단위 조회를 검토한다.
- yield_per, pagination, limit/offset, cursor 기반 조회 방식 중 적합한 방식을 검토한다.
- source별 또는 날짜별 duplicate report batch job으로 분리할지 검토한다.
- Pi worker 또는 batch node에서 daily duplicate analysis job으로 돌릴 수 있는지 검토한다.

## Applied Changes

None.

이번 fixes 단계에서 추가 코드 변경은 수행하지 않는다.

Antigravity review 결과 required fix가 없었으므로, 기존 구현을 그대로 유지한다.

이번 fixes 단계에서 변경하지 않는 파일:

- app/utils/url_normalization.py
- scripts/analyze_article_duplicates.py
- tests/test_url_normalization.py
- tests/test_analyze_article_duplicates.py
- db/migrations/
- k8s/
- API router files
- collector / raw extractor scripts

## Verification Required

추가 fix가 없으므로 별도 재검증은 필수 아님.

PR 전 최종 확인 용도로 다음 명령만 다시 실행한다.

```bash
git status --short
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

필요 시 기존 verification의 핵심 명령을 재확인한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/url_normalization.py scripts/analyze_article_duplicates.py tests/test_url_normalization.py tests/test_analyze_article_duplicates.py
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 72 --max-groups 5
```

주의:

- DB migration은 실행하지 않는다.
- Supabase SQL은 실행하지 않는다.
- K8s apply / rollout은 실행하지 않는다.
- production curl verification은 이번 task의 필수 검증이 아니다.
- duplicate analysis script는 read-only 분석으로만 사용한다.
