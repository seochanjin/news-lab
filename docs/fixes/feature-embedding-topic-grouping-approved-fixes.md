# Approved Fixes: Embedding 기반 topic grouping MVP

## Approved Fixes

- None.
- Antigravity review에서 PR 제출 전 반드시 수정해야 할 required fix는 발견되지 않았다.
- Human operator가 명시적으로 승인한 코드 수정 항목은 없다.
- Review output만으로는 optional suggestion 적용 승인이 성립하지 않으므로, batching 개선은 이번 PR에 적용하지 않는다.

## Rejected or Deferred Suggestions

### Deferred 1. OpenAI embedding provider batching/chunking

Antigravity review에서 현재 `OpenAIEmbeddingProvider`가 최대 200건의 article embedding 요청을 한 번의 HTTP POST로 처리한다는 점을 바탕으로, 향후 상한을 늘리거나 운영 규모가 커질 경우 chunk 단위 batch 호출 로직을 설계하는 optional improvement가 제안되었다.

판단:

- **Deferred**
- 이번 task의 acceptance criteria를 충족하기 위한 blocking fix는 아니다.
- 현재 script는 실제 provider 호출 시 `--max-articles`를 명시적으로 요구하고, 상한을 200건으로 제한한다.
- 30차 MVP의 목적은 대량 embedding 운영이 아니라 topic grouping pipeline과 safety gate 검증이다.
- chunking/batching은 향후 `article_embeddings` 저장 구조 또는 topic pipeline CronJob 운영화 단계에서 함께 검토하는 것이 적절하다.

후속 검토 방향:

- provider별 request size limit 확인
- article 수 증가 시 chunk size 정책 설계
- partial failure/retry 정책 설계
- embedding input hash 기반 중복 호출 방지
- batch별 cost estimate와 execution summary 기록
- DB 저장 구조 도입 시 already embedded article 재사용 정책 검토

## Applied Changes

- None.
- 이 fix drafting 단계에서는 코드, 테스트, DB, API, K8s manifest를 변경하지 않았다.
- DB migration, Supabase SQL, production command, push, merge를 실행하지 않았다.
- Optional batching/chunking suggestion은 이번 PR에 적용하지 않았다.

## Verification Required

추가 code fix가 없으므로 별도 fix verification은 필요하지 않다.

PR 제출 전 기존 verification 명령의 최종 상태만 확인한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py
.venv/bin/python scripts/analyze_topic_groups.py --help
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

필요 시 dry-run 대표 명령을 한 번 더 확인한다.

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
```

검증 기준:

- 단위 테스트가 통과해야 한다.
- Python compile이 통과해야 한다.
- CLI help가 정상 출력되어야 한다.
- K8s manifest 변경이 없어야 한다.
- DB migration이 없어야 한다.
- DB write path가 없어야 한다.
- 기본 실행에서 OpenAI embedding provider를 호출하지 않아야 한다.
- 실제 provider 호출은 `--use-embedding-provider`, `OPENAI_EMBEDDING_API_KEY`, 명시적 `--max-articles`가 모두 있을 때만 가능해야 한다.
- production-impacting command는 실행하지 않는다.
