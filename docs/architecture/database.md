# Database 구조

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## 연결과 migration

Application은 PostgreSQL/Supabase를 사용한다. 연결 설정은
`app/database.py`가 담당하며 credential 값은 문서에 기록하지 않는다.
Repository에서 관리하는 schema 변경은 `db/migrations/`의 SQL file이다.
Migration 실행은 사람이 수행한다.

## 현재 주요 table

| Table | 책임 |
| --- | --- |
| `sources` | RSS source metadata와 feed 설정 |
| `articles` | 수집된 기사 metadata |
| `crawl_runs` | RSS collector 실행 이력 |
| `raw_articles` | 기사 원문 추출 결과 |
| `extraction_runs` | raw extractor 실행 이력 |
| `topics` | 생성된 주제와 요약 metadata |
| `topic_articles` | topic과 article 연결 |

`sources`와 `articles`의 초기 schema는 repository 밖에서 시작되었고, 현재
repository migration은 `sources.feed_url`, 실행 이력, raw article, topic
table의 변경을 기록한다. 전체 production schema를 이 문서만으로 재구성한다고
가정하지 않는다.

## 관계

```text
sources 1 ── N articles
articles 1 ── 0..1 raw_articles
topics N ── N articles (topic_articles)
```

`crawl_runs`와 `extraction_runs`는 batch 실행 단위의 상태와 count, 오류 정보를
보존한다.

## 변경 원칙

- Schema 변경은 별도 migration file로 작성한다.
- Supabase SQL은 agent가 실행하지 않는다.
- Production data를 확인하거나 수정하는 command는 task의 명시적 허용과 사람
  판단이 필요하다.
- Embedding 저장 구조는 현재 확정하지 않았으며 후속 설계 task에서 다룬다.
