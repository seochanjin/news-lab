# 홈 Topics 경량 API 설계 및 MVP

## 작업 목적

홈 첫 화면이 범용 `/topics` archive API의 pagination/count/metadata 응답을
기다리지 않도록, 홈 card에 필요한 최소 Topics payload를 제공하는 read-only
MVP API를 추가한다.

이번 단계의 목표는 Redis, DB snapshot, static JSON, frontend revalidate를 바로
도입하는 것이 아니다. 먼저 홈 전용 lightweight API를 분리해, 홈이 범용 archive
API를 그대로 사용하는 구조보다 더 작은 payload와 더 단순한 query path를 가질 수
있는지 확인한다.

## 기존 문제

- 홈(`/`)은 원문 기사 preview와 Articles API 조회 제거 이후에도 주요 이슈 표시를
  위해 `/topics?page=1&page_size=10`을 사용하고 있었다.
- task에 제공된 운영 측정 기준으로 `/topics?page=1&page_size=10`은 약
  0.71s~1.00s, 10회 반복 평균 약 0.87s였다.
- 이 수치는 backend 장애 수준은 아니지만 홈 첫 화면에서는 loading으로 체감될 수
  있다.
- 기존 `/topics`는 archive API라 `count(*)`, pagination metadata,
  provider/model/status/timestamps 등 홈에 불필요한 응답을 포함한다.
- 기존 `/topics/{topic_id}`는 detail API라 `topic_articles`, `articles`,
  `sources` join으로 connected article list를 반환한다. 홈 첫 viewport에는 이
  detail payload가 필요하지 않다.

## 변경 내용

- `GET /topics/home` 추가.
- `topics` 테이블에서 최대 10개 topic card payload만 직접 조회.
- 기존 `/topics`, `/topics/{topic_id}`는 변경하지 않음.
- `/topics/home` route를 `/topics/{topic_id}`보다 먼저 선언해 route shadowing을
  방지.
- `tests/test_topics_api.py`에 route 등록, response shape, empty response, query
  shape 검증 추가.
- `docs/ARCHITECTURE.md`에 Topics API와 `/topics/home` 역할 추가.
- `docs/RUNBOOK.md`에 `/topics/home` read-only 확인 및 timing command 후보 추가.
- `docs/design/home-topics-snapshot-cache-strategy.md`에 후속
  cache/snapshot/revalidate 전략 기록.
- `docs/verification/feature-home-topics-snapshot-design.md`에 실제 실행한 검증
  command와 결과 기록.
- `docs/fixes/feature-home-topics-snapshot-design-approved-fixes.md`에 approved
  fixes 상태 기록.

## 구현 상세

신규 endpoint:

```text
GET /topics/home
```

응답 field:

- `generated_at`
- `topic_date`
- `items[].id`
- `items[].topic_date`
- `items[].title_ko`
- `items[].summary_ko`
- `items[].keywords`
- `items[].article_count`
- `items[].source_count`

Query 특징:

- `topics` 테이블만 조회한다.
- `limit :limit` bind parameter를 사용한다.
- fixed limit은 10개다.
- 정렬은 `topic_date desc, article_count desc, source_count desc, id desc`다.
- `count(*)`를 실행하지 않는다.
- `topic_articles`, `articles`, `sources`를 join하지 않는다.
- provider/model/status/debug/detail article field를 반환하지 않는다.
- 결과가 없으면 `topic_date: null`, `items: []`를 반환한다.

기존 API 분석 결과:

- `GET /topics`는 `status`, `date_from`, `date_to`, `keyword` filter를 받고,
  `select count(*) from topics ...`로 pagination total을 계산한다.
- `GET /topics` item은 provider/model/status/timestamps 등 archive metadata를
  포함한다.
- `GET /topics/{topic_id}`는 topic detail을 읽은 뒤 `topic_articles`,
  `articles`, `sources` join으로 connected article list를 반환한다.
- 홈 첫 viewport에는 topic card field만 필요하므로 archive pagination metadata와
  detail article join은 제외했다.

## 대안 검토

### 기존 `/topics` 계속 사용

구현 변경이 없고 frontend도 그대로 둘 수 있다. 하지만 홈이 계속 archive API의
pagination/count/metadata 응답을 기다리게 된다. 이번 작업의 목적이 홈 payload
분리 가능성 확인이므로 선택하지 않았다.

### `/topics/home`이 내부에서 기존 `/topics` handler를 wrapper로 호출

구현 중복은 줄일 수 있다. 다만 기존 archive API의 `count(*)`, pagination
metadata, provider/model/status payload를 그대로 끌고 오기 쉬워 lightweight API의
목적이 약해진다. 이번 MVP에서는 직접 query를 선택했다.

### Redis cache 즉시 도입

API replica 간 공유 cache를 만들 수 있다. 하지만 Redis 운영 구성, fallback,
cache invalidation, 배포 변경이 필요하고 이번 차수의 scope를 넘어선다. Redis는
목적이 아니라 사용자 요청 시점의 무거운 조회/조합을 줄이기 위한 수단이므로 후속
작업으로 남겼다.

### DB snapshot table 즉시 도입

`home_topic_snapshots` 같은 table에 generated payload를 저장하면 durable fallback과
history를 얻을 수 있다. 하지만 DB schema 변경과 migration이 필요하며 이번 task에서
명시적으로 금지되어 있다.

### Static JSON 또는 frontend revalidate 즉시 도입

홈을 거의 정적 payload처럼 제공할 수 있다. 다만 artifact hosting, invalidation,
frontend 변경이 필요하다. 이번 PR은 backend read-only API 분리에 집중했다.

### Pydantic response_model 추가

Swagger 문서화 품질과 schema 명확성이 좋아질 수 있다. 현재 topics router는 plain
dictionary 반환 style을 사용하고 있고, 이번 변경은 작고 reviewable한 MVP가
목표라서 response shape는 unit test로 보호했다. API schema 정리 차수에서 다시
검토한다.

## 선택한 접근과 근거

선택한 접근은 `app/routers/topics.py` 안에 `GET /topics/home`을 추가하고,
`topics` 테이블을 직접 조회하는 read-only endpoint를 만드는 것이다.

근거:

- 기존 FastAPI router 구조를 유지한다.
- DB schema와 production infrastructure를 변경하지 않는다.
- 홈에 필요한 field만 반환해 payload를 줄인다.
- archive API의 total count query를 피한다.
- detail API의 connected article join을 피한다.
- 기존 `/topics`, `/topics/{topic_id}` contract를 건드리지 않는다.
- 후속 cache/snapshot 구조로 확장할 수 있는 별도 API surface를 확보한다.

## 트레이드오프

- 아직 Redis, DB snapshot, static JSON, frontend revalidate가 없으므로
  `/topics/home`도 여전히 DB read를 수행한다.
- fixed limit 10은 홈 MVP에는 단순하지만, 나중에 홈 UI 요구가 바뀌면 조정 기준이
  필요하다.
- `generated_at`은 현재 응답 생성 시각이며, Daily Topic Pipeline snapshot 생성
  시각은 아니다. 후속 snapshot/cache 구현 시 의미를 재정의하거나 별도 source
  metadata를 추가할 수 있다.
- `status = 'published'` filter는 아직 도입하지 않았다. 현재 topic publish workflow가
  없고 운영 topic이 draft 중심이라, 지금 적용하면 홈 topic이 비어질 수 있다.
- composite index는 추가하지 않았다. topic row가 늘거나 운영 응답 시간이 증가하면
  `topic_date desc, article_count desc, source_count desc, id desc` 정렬용 index를
  별도 DB 작업으로 검토한다.

## 테스트

`docs/verification/feature-home-topics-snapshot-design.md`에 기록된 실제 실행
결과만 적는다.

```bash
python -m unittest tests.test_topics_api -v
```

- 결과: 6 tests passed

```bash
python -m py_compile app/routers/topics.py tests/test_topics_api.py
```

- 결과: passed

```bash
python -m unittest discover -s tests -v
```

- 결과: 121 tests passed

```bash
git diff --check
```

- 결과: passed

참고:

- 최초 focused test 실행에서는 신규 test가 detail topic fixture를 재사용해
  실패했다.
- home payload fixture를 lightweight query 결과에 맞게 분리한 뒤 rerun에서
  통과했다.
- full unittest 실행 중 argparse usage/error 로그가 출력되었지만, 이는 실패
  case를 검증하는 기존 테스트의 stderr 출력이며 최종 결과는 OK였다.

## 운영 반영

운영 반영은 수행하지 않았다.

- PR merge: pending
- image build: pending
- K3s rollout: pending
- production `/topics/home` curl verification: pending
- frontend home의 `/topics/home` 전환: pending

실행하지 않은 작업:

- `git push`
- `git merge`
- `kubectl apply`
- `kubectl rollout`
- Supabase SQL
- DB write
- production deploy
- 신규 production curl verification

Production timing 값은 task source of truth에 제공된 pre-task 측정치만
verification에 기록했다.

## README 업데이트 판단

README는 수정하지 않았다.

판단 근거:

- 설치 방법 변경 없음.
- dependency 변경 없음.
- 로컬 실행 방식 변경 없음.
- public setup flow 변경 없음.
- 신규 API 설명은 repository 운영/아키텍처 문맥에 더 가까워
  `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`에 반영했다.

## 확인 결과

- 현재 `/topics`, `/topics/{topic_id}` 구조 분석을 verification에 기록했다.
- 제공된 운영 `/topics` 응답 시간 측정값을 verification에 기록했다.
  - `/topics?page=1&page_size=10`: 약 0.71s~1.00s
  - 10회 반복 평균: 약 0.87s
- `/topics/home`은 기존 `/topics` wrapper가 아니라 직접 lightweight query를
  사용한다.
- `/topics/home`은 홈 첫 화면에 필요한 field만 반환한다.
- `/topics/home`은 total count query와 `topic_articles` join을 사용하지 않는다.
- 기존 `/topics`, `/topics/{topic_id}` response schema는 변경하지 않았다.
- DB schema, Supabase SQL, Redis, K3s manifest, Dockerfile, GitHub Actions,
  frontend code, secret, `.env*`는 변경하지 않았다.
- Approved fixes 문서 기준으로 blocking fix는 없었고, approved fixes 단계에서
  추가 code change는 없었다.
- Production deploy, K3s rollout, production verification은 완료되지 않았다.

## 이번 단계의 의미

이번 작업은 홈 성능 문제를 단순히 cache 도입 문제로 보지 않고, 먼저 API boundary와
payload 책임을 분리한 단계다.

홈은 "오늘의 주요 이슈"를 빠르게 보여주는 화면이고, `/topics`는 전체 주요 이슈
archive다. 두 화면의 정보 요구가 다르므로 backend API도 분리했다.

장기 목표는 다음 흐름이다.

```text
Daily Topic Pipeline 완료
→ home topics payload 사전 생성
→ Redis/DB snapshot/static JSON/revalidate 중 적절한 조합으로 갱신
→ 사용자 요청 시점에는 이미 준비된 작은 payload 제공
```

이번 차수는 그 구조로 가기 위한 backend API surface와 설계 문서를 만든 단계다.

## 포트폴리오용 요약

NewsLab 홈 화면의 초기 로딩 부담을 줄이기 위해 범용 Topics archive API와 홈 전용
payload API를 분리했다. 기존 `/topics`가 pagination count와 archive metadata를
반환하던 구조에서, 홈 첫 화면에 필요한 topic card field만 반환하는
`GET /topics/home` read-only endpoint를 추가했다.

기존 API contract와 DB schema는 유지하면서 unit test로 route 등록, response shape,
query 경량화 조건을 검증했다. 또한 Redis나 DB snapshot을 성급히 도입하지 않고,
Daily Topic Pipeline 완료 시점에 home payload를 사전 생성하는 cache/snapshot 전략을
문서화했다.

## 다음 단계 후보

- 47차 후보: frontend home을 `/topics/home`으로 전환하고 loading 체감 확인.
- `/topics/home` 자체도 충분히 빠르지 않으면 47차를 cache/snapshot MVP로 바꾸고
  frontend 전환을 48차로 미룬다.
- 48차 후보: Daily Topic Pipeline 완료 후 home payload cache/snapshot 갱신 MVP.
- Topic row 증가 또는 운영 응답 시간 증가 시 home query composite index 검토.
- Topic moderation/publish workflow 도입 시 `/topics`, `/topics/home`, `/search`의
  status filtering 정책 정리.
- API schema 정리 차수에서 `/topics`, `/topics/{id}`, `/topics/home`의 Pydantic
  response model 도입 여부 검토.
- 49차 이후: embedding 저장 구조 검토로 복귀.
