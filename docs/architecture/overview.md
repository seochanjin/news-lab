# Backend 구성 개요

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 책임 경계

NewsLab backend는 다음 책임으로 나뉜다.

| 영역 | 주요 위치 | 책임 |
| --- | --- | --- |
| API | `app/main.py`, `app/routers/` | 저장된 기사·실행 이력·주제 read API |
| Database | `app/database.py`, `db/migrations/` | PostgreSQL 연결과 schema 변경 기록 |
| Collection | `scripts/collect_rss.py` | RSS source 동기화, 기사 수집, 실행 이력 |
| Extraction | `scripts/extract_raw_articles.py` | 기사 HTML에서 원문 추출, 실행 이력 |
| Topic pipeline | `scripts/run_daily_topic_pipeline.py`, `scripts/run_three_day_topic_pipeline.py`, `scripts/run_weekly_topic_pipeline.py` | 1일·3일·주간 기사 후보 처리, 주제 생성·저장 |
| Home Cache | `app/home_topics_cache.py`, `app/home_topics_payload.py` | 기간별 Home API cache-aside와 Pipeline post-save prewarm |
| Runtime | `k8s/` | API·Redis Deployment와 네 scheduled CronJob 정의 |

## 주요 데이터 흐름

```text
RSS feed
→ articles
→ article_embeddings 생성 또는 재사용
→ 기간별 clustering과 Summary 근거 기사 선택
→ 선택된 근거 기사의 raw_articles 확보와 Summary 생성
→ topics / topic_articles
  또는 three_day_topics / three_day_topic_articles
  또는 weekly_topics / weekly_topic_articles
→ PostgreSQL/Supabase에 기간별 결과 저장
→ Pipeline이 대응 Redis Home key prewarm
→ FastAPI archive / Home / detail read API
```

PostgreSQL/Supabase가 영속 Source of Truth이며 Redis는 삭제 가능한 fail-open
cache다. FastAPI와 각 Pipeline이 두 저장 계층에 각각 접근하고 PostgreSQL과
Redis가 서로 직접 통신하지 않는다. 실행 이력은 collector의 `crawl_runs`,
extractor의 `extraction_runs`, 3일 Topic의 `three_day_topic_runs`, 주간 Topic의
`weekly_topic_runs`에 저장된다.
세부 흐름은 [pipeline](pipeline.md), table 책임은 [database](database.md)를
참고한다.

## 문서 책임

현재 구조와 운영 기준은 `docs/architecture/`, `docs/runbooks/`,
`docs/agent/`가 관리한다. 과거 작업 근거는 `docs/tasks/`,
`docs/verification/`, `docs/devlog/`, `docs/reviews/`에 보존하며 현재 운영
기준 문서에 합치지 않는다.
