# Approved Fixes: 홈 Topics 경량 API 설계 및 MVP

## Approved Fixes

Antigravity review 결과, 이번 PR에 반드시 반영해야 할 blocking fix는 확인되지 않았다.

```text
Required Fixes Before PR: None
Verdict: PASS
```

따라서 이번 approved fixes 문서에서는 추가 적용할 필수 수정 사항을 두지 않는다.

## Rejected or Deferred Suggestions

다음 항목은 유효한 개선 제안이지만, 이번 작업의 목표인 `/topics/home` 경량 API MVP 범위를 넘어서므로 후속 작업으로 미룬다.

### 1. Composite Index 추가

Antigravity는 `/topics/home` query가 다음 정렬을 사용하므로, topic row가 많아질 경우 composite index를 고려할 수 있다고 제안했다.

```sql
create index if not exists idx_topics_home_sort
on topics (topic_date desc, article_count desc, source_count desc, id desc);
```

이번 차수에서는 DB schema 변경과 Supabase SQL 실행이 명시적으로 금지되어 있으므로 적용하지 않는다.

Deferred reason:

```text
- DB schema 변경 필요
- Supabase SQL 실행 필요
- 이번 차수의 scope는 read-only API 추가와 문서화
- 현재 topic row 규모에서는 즉시 blocking issue로 보기 어려움
```

후속 후보:

```text
Home Topics API 운영 응답 시간이 증가하거나 topic row 수가 충분히 늘어난 뒤,
DB index 검토 차수에서 composite index를 함께 검토한다.
```

### 2. `status = 'published'` 필터 준비

Antigravity는 향후 topic 승인/공개 workflow가 생기면 `/topics/home`이 `draft` topic을 계속 노출할 수 있다고 지적했다.

현재 Daily Topic Pipeline에서 생성되는 topic은 사용자-facing MVP 기준으로 `draft` 상태를 사용하고 있으며, 별도의 `published` 전환 workflow가 아직 없다.  
따라서 이번 차수에서 `status = 'published'` 필터를 적용하면 현재 홈 topic이 비어버릴 수 있다.

Deferred reason:

```text
- 아직 published 전환 workflow가 없음
- 현재 운영 데이터는 draft topic 중심
- 이번 차수는 기존 topic 표시 정책을 변경하지 않음
- 공개/승인 상태 정책은 별도 product decision 필요
```

후속 후보:

```text
Topic moderation/publish workflow를 도입하는 차수에서
/topics, /topics/home, /search의 status filtering 정책을 함께 정리한다.
```

### 3. Pydantic response_model 추가

Antigravity는 `/topics/home`에 Pydantic response model을 추가하면 Swagger 문서화 품질이 좋아질 수 있다고 제안했다.

현재 topics router의 기존 style과 구현 흐름을 유지하기 위해 이번 차수에서는 plain dictionary 반환 방식을 사용한다.

Deferred reason:

```text
- 기존 topics router style과 일관성 유지
- API schema 정리 범위가 별도 작업으로 커질 수 있음
- 현재 unit test로 response shape를 보호하고 있음
```

후속 후보:

```text
API schema 문서화 정리 차수에서 /topics, /topics/{id}, /topics/home의
Pydantic response_model 도입 여부를 함께 검토한다.
```

## Applied Changes

이번 approved fixes 단계에서 추가로 적용한 code change는 없다.

Antigravity review 전에 이미 구현된 주요 변경 사항은 다음과 같다.

```text
- GET /topics/home read-only endpoint 추가
- 홈 첫 화면에 필요한 최소 topic card payload 반환
- provider/model/confidence/debug/detail article 필드 제외
- total count query 제거
- topic_articles/articles/sources join 없이 topics 테이블 기반 조회
- 기존 GET /topics, GET /topics/{topic_id} 보호 test 유지
- /topics/home route를 /topics/{topic_id}보다 먼저 선언하여 route shadowing 방지
- docs/ARCHITECTURE.md에 신규 endpoint 역할 반영
- docs/RUNBOOK.md에 endpoint 확인 command 후보 추가
- docs/design/home-topics-snapshot-cache-strategy.md에 후속 cache/snapshot 전략 기록
```

## Verification Required

Approved fixes 단계에서 추가 code change는 없으므로, 기존 검증 command를 재실행하여 상태가 유지되는지 확인한다.

필수 확인:

```bash
python -m unittest tests.test_topics_api -v
python -m unittest discover -s tests -v
python -m py_compile app/routers/topics.py tests/test_topics_api.py
git diff --check
git status --short --branch
```

선택 확인:

```bash
git diff -- app/routers/topics.py tests/test_topics_api.py docs/ARCHITECTURE.md docs/RUNBOOK.md docs/design/home-topics-snapshot-cache-strategy.md
```

확인 관점:

```text
- /topics/home route가 /topics/{topic_id}보다 먼저 선언되어 있는지
- /topics/home이 read-only SELECT만 수행하는지
- 기존 /topics, /topics/{topic_id} route behavior가 test로 보호되는지
- response에 provider/model/confidence/debug/detail article 필드가 포함되지 않는지
- DB schema, Supabase SQL, K3s manifest, Dockerfile, GitHub Actions, secret, .env 변경이 없는지
```

Production verification은 이번 단계에서 수행하지 않는다.  
`/topics/home` 운영 확인은 PR merge, image build, K3s rollout 이후 human operator가 별도로 수행한다.

Approved fixes 확인 단계에서 다음 검증을 재실행했다.

- python -m unittest tests.test_topics_api -v: 6 tests passed
- python -m unittest discover -s tests -v: 121 tests passed
- python -m py_compile app/routers/topics.py tests/test_topics_api.py: passed
- git diff --check: passed
- git status --short --branch: tracked changes and workflow/design docs only

unittest 실행 중 argparse error usage 로그가 출력되었지만,
이는 실패 케이스를 검증하는 기존 테스트의 stderr 출력이며 최종 결과는 OK였다.
