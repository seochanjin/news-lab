# 홈 Topics 경량 API 설계 및 MVP

## 작업 내용

홈 첫 화면이 범용 `/topics` archive API의 pagination/count/metadata 응답을
기다리지 않도록, 홈 전용 read-only Topics API MVP를 추가했습니다.

이번 PR의 목표는 Redis, DB snapshot, static JSON, frontend revalidate를 바로
구현하는 것이 아니라, 홈에서 필요한 최소 payload만 제공하는 backend API
분리와 후속 cache/snapshot 전략 문서화입니다.

## 주요 변경 사항

- `app/routers/topics.py`
  - `GET /topics/home` endpoint 추가
  - `topics` 테이블에서 홈 card 필드만 직접 조회
  - `count(*)`, pagination metadata, provider/model/status/debug fields,
    `topic_articles` join 제외
  - `/topics/home` route를 `/topics/{topic_id}`보다 먼저 선언해 route
    shadowing 방지
- `tests/test_topics_api.py`
  - `/topics/home` route 등록 확인
  - lightweight payload shape 확인
  - empty response가 `topic_date: null`, `items: []`로 반환되는지 확인
  - home query가 `count(*)`, `topic_articles`, provider/model field를
    사용하지 않는지 확인
- `docs/ARCHITECTURE.md`
  - Topics router와 Daily topic flow 추가
  - `/topics`, `/topics/home`, `/topics/{topic_id}` 역할 차이 문서화
- `docs/RUNBOOK.md`
  - `/topics/home` read-only 확인 및 timing command 후보 추가
- `docs/design/home-topics-snapshot-cache-strategy.md`
  - Next.js revalidate, FastAPI in-memory TTL, Redis, DB snapshot, static JSON,
    Redis + DB fallback, CronJob cache warming 후보 비교
  - Daily Topic Pipeline 완료 시점에 home payload를 사전 생성하는 장기 방향
    기록
- `docs/verification/feature-home-topics-snapshot-design.md`
  - 실제 실행한 검증 command와 결과 기록
- `docs/fixes/feature-home-topics-snapshot-design-approved-fixes.md`
  - approved fixes 상태 기록

Approved fixes 문서 기준으로 이번 PR에 반드시 반영해야 할 blocking fix는
없었고, approved fixes 단계에서 추가 code change는 없었습니다.

## 추가/변경된 API

추가 API:

```text
GET /topics/home
```

응답 형태:

```json
{
  "generated_at": "2026-06-16T00:00:00+00:00",
  "topic_date": "2026-06-16",
  "items": [
    {
      "id": 12,
      "topic_date": "2026-06-16",
      "title_ko": "...",
      "summary_ko": "...",
      "keywords": ["..."],
      "article_count": 7,
      "source_count": 3
    }
  ]
}
```

특징:

- 최대 10개 topic card item 반환
- `topics` 테이블 기반 read-only SELECT
- `topic_date desc, article_count desc, source_count desc, id desc` 정렬
- 결과가 없으면 `topic_date: null`, `items: []`
- total count query 없음
- connected article/detail payload 없음

변경하지 않은 API:

- `GET /topics`
- `GET /topics/{topic_id}`
- `GET /articles`
- 기타 기존 API

## DB 변경 사항

DB schema 변경은 없습니다.

- migration 추가 없음
- Supabase SQL 실행 없음
- table/column/index 추가 없음
- data backfill 없음
- DB write query 없음

Composite index 후보는 review에서 개선 제안으로 언급되었지만, 이번 task의
scope가 read-only API와 문서화이며 DB schema 변경이 금지되어 있어 후속 작업으로
defer했습니다.

## README 영향

README 변경은 없습니다.

이번 변경은 설치 방법, dependency, 로컬 실행 방식, public setup flow를 바꾸지
않습니다. 신규 API 설명은 `docs/ARCHITECTURE.md`와 `docs/RUNBOOK.md`에
반영했습니다.

## 테스트

`docs/verification/feature-home-topics-snapshot-design.md`에 기록된 실제 실행
결과입니다.

```bash
python -m unittest tests.test_topics_api -v
```

- 결과: passed, 6 tests

```bash
python -m py_compile app/routers/topics.py tests/test_topics_api.py
```

- 결과: passed

```bash
python -m unittest discover -s tests -v
```

- 결과: passed, 121 tests

```bash
git diff --check
```

- 결과: passed

참고:

- 최초 focused test 실행 중 신규 test fixture가 detail topic fixture를 재사용해
  실패했습니다.
- home payload fixture를 lightweight query 결과에 맞게 분리한 뒤 rerun에서
  통과했습니다.
- full unittest 실행 중 일부 argparse usage/error 로그가 출력될 수 있으나,
  이는 실패 케이스를 검증하는 기존 테스트의 stderr 출력이며 최종 결과는 OK로
  기록되어 있습니다.

## 확인 결과

- 현재 `/topics`, `/topics/{topic_id}` 구조를 분석해 verification에 기록했습니다.
- 제공된 운영 `/topics` 응답 시간 측정값을 verification에 기록했습니다.
  - `/topics?page=1&page_size=10`: 약 0.71s~1.00s
  - 10회 반복 평균: 약 0.87s
- `/topics/home`은 기존 `/topics` wrapper가 아니라 직접 lightweight query를
  사용합니다.
- `/topics/home`은 홈 첫 화면에 필요한 field만 반환합니다.
- 기존 `/topics`, `/topics/{topic_id}` response schema는 변경하지 않았습니다.
- DB schema, Supabase SQL, Redis, K3s manifest, Dockerfile, GitHub Actions,
  frontend code, secret, `.env*`는 변경하지 않았습니다.
- Production deploy, K3s rollout, production `/topics/home` verification은
  수행하지 않았습니다.

## 비고

- Production timing 값은 task source of truth에 제공된 pre-task 측정치이며,
  이번 PR draft 작성 과정에서 새 production curl은 실행하지 않았습니다.
- Local HTTP verification against `uvicorn`은 live `DATABASE_URL` target이
  필요하므로 실행하지 않았고, handler는 fake connection 기반 unit test로
  검증했습니다.
- Production `/topics/home` 확인은 PR merge, image build, K3s rollout 이후
  human operator가 별도로 수행해야 합니다.
- 후속 후보:
  - 47차: frontend home을 `/topics/home`으로 전환하고 loading 체감 확인
  - `/topics/home` 자체도 충분히 빠르지 않으면 47차를 cache/snapshot MVP로 전환
  - 48차: Daily Topic Pipeline 완료 후 home payload cache/snapshot 갱신 MVP
  - 49차 이후: embedding 저장 구조 검토로 복귀
