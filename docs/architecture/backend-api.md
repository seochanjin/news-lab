# FastAPI와 API 영역

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## Application 구성

`app/main.py`가 FastAPI application을 생성하고 `app/routers/`의 router를
등록한다. 현재 등록된 router는 다음과 같다.

- `health.py`: `GET /health`
- `version.py`: `GET /version`
- `sources.py`: `GET /sources`
- `articles.py`: `GET /articles`, `GET /articles/{article_id}`
- `collector.py`: `GET /collector/runs`, `GET /collector/status`
- `extractor.py`: `GET /extractor/runs`, `GET /extractor/status`
- `raw_articles.py`: `GET /raw-articles`,
  `GET /raw-articles/{article_id}`
- `topics.py`: `GET /topics`, `GET /topics/home`,
  `GET /topics/{topic_id}`
- `three_day_topics.py`: `GET /three-day-topics`,
  `GET /three-day-topics/home`, `GET /three-day-topics/{topic_id}`
- `weekly_topics.py`: `GET /weekly-topics`, `GET /weekly-topics/home`,
  `GET /weekly-topics/{topic_id}`

Root endpoint `GET /`는 주요 endpoint 링크를 반환한다.

## API 역할

- `/articles`는 수집된 기사 metadata를 조회한다.
- `/collector/*`는 RSS collector 실행 상태와 이력을 조회한다.
- `/raw-articles`는 원문 추출 결과를 조회한다.
- `/extractor/*`는 원문 extractor 실행 상태와 이력을 조회한다.
- `/topics`는 주제 archive와 detail을 제공한다.
- `/topics/home`은 home 화면용 bounded topic card payload를 제공하며 Redis
  cache-aside를 사용해 반복 조회 시 PostgreSQL 조회를 건너뛴다.
- `/three-day-topics`는 3일 Topic archive와 detail을 제공한다.
- `/three-day-topics/home`은 성공 또는 부분 성공한 최신 72시간 publishable
  window 하나의 bounded Topic card payload를 제공하며 Redis cache-aside를
  사용한다.
- `/weekly-topics/home`은 성공 또는 부분 성공한 최신 완료 주간의 publishable
  window 하나의 bounded Topic card payload를 제공하며 Redis cache-aside를
  사용한다.

Topic 저장 시 `article_count`와 `source_count`는 Summary 근거 기사만이 아니라
저장된 관련 기사 전체를 기준으로 계산한다. `/topics/home`은 저장된 집계값을
card field로 반환하고, `/topics/{topic_id}`는 `topic_articles` 관계 순서대로
대표 기사와 supporting 기사 전체를 반환한다. Endpoint와 response field 이름 및
타입은 이 집계 기준 변경으로 달라지지 않는다.

`/topics/home`의 Redis cache key는 `topics:home:v1`, `/three-day-topics/home`의
Redis cache key는 `three-day-topics:home:v1`, `/weekly-topics/home`의 Redis cache
key는 `weekly-topics:home:v1`이다. Daily와 3-day key의 기본 TTL은 108,000초
(30시간), Weekly key의 기본 TTL은 691,200초(8일)다. TTL은 최신성 기준이 아니라
stale cache의 장기 잔류를 막는 안전장치로 사용하며, 최신성은 각 Pipeline이
PostgreSQL 저장 성공 이후 같은 Home payload builder로 대응 Redis key를 overwrite
하는 방식으로 관리한다. Redis는 source of truth가 아니며 Redis 미설정, 연결
실패, timeout, payload 손상은 PostgreSQL fallback으로 처리한다. Cache 상태는
response body가 아니라 `home_topics_cache event=hit|miss|store|prewarm|bypass`
로그로 구분한다.

3일 Topic API는 기존 `topics` 계열을 읽지 않는다. Archive는
`reference_date`, 날짜 범위, keyword와 status filter를 지원하고, detail은
`three_day_topic_articles`의 `rank`, `article_id` 순서로 대표 기사와 Summary
근거 여부를 함께 반환한다. Home API는 전체 count나 관련 기사 join 없이 최신
publishable window의 경량 card field만 조회한다.

Weekly Topic API도 기존 `topics`와 3일 Topic 계열을 읽지 않는다. Archive는 완료
주간과 keyword/status filter를 지원하고, Home API는 전체 count나 관련 기사 join
없이 최신 publishable 주간 window의 경량 card field만 조회한다.

이 문서는 현재 구현의 영역만 요약한다. Request parameter, response schema,
status code의 source of truth는 router 구현이다. Contract 변경은 별도 task로
다룬다.

## 구현 규칙

새 router는 `app/routers/`에 추가하고 `app/main.py`에 등록한다. DB query는
SQLAlchemy `text()`와 bind parameter를 사용해 user input을 SQL 문자열에 직접
삽입하지 않는다.
