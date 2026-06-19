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

Root endpoint `GET /`는 주요 endpoint 링크를 반환한다.

## API 역할

- `/articles`는 수집된 기사 metadata를 조회한다.
- `/collector/*`는 RSS collector 실행 상태와 이력을 조회한다.
- `/raw-articles`는 원문 추출 결과를 조회한다.
- `/extractor/*`는 원문 extractor 실행 상태와 이력을 조회한다.
- `/topics`는 주제 archive와 detail을 제공한다.
- `/topics/home`은 home 화면용 bounded topic card payload를 제공한다.

이 문서는 현재 구현의 영역만 요약한다. Request parameter, response schema,
status code의 source of truth는 router 구현이다. Contract 변경은 별도 task로
다룬다.

## 구현 규칙

새 router는 `app/routers/`에 추가하고 `app/main.py`에 등록한다. DB query는
SQLAlchemy `text()`와 bind parameter를 사용해 user input을 SQL 문자열에 직접
삽입하지 않는다.
