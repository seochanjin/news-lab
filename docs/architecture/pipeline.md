# 수집·추출·주제 Pipeline

[Architecture index로 돌아가기](../ARCHITECTURE.md)

## RSS collection

```text
RSS source registry / sources
→ scripts/collect_rss.py
→ articles
→ crawl_runs
→ /articles, /collector/status, /collector/runs
```

K3s의 `news-rss-collector` CronJob은 `03:00 Asia/Seoul`에 실행되도록
manifest에 정의되어 있다.

## Raw article extraction

```text
articles.url
→ scripts/extract_raw_articles.py
→ HTML fetch와 BeautifulSoup extraction
→ raw_articles
→ extraction_runs
→ /raw-articles, /extractor/status, /extractor/runs
```

K3s의 `news-raw-extractor` CronJob은 `03:30 Asia/Seoul`에 실행되도록
manifest에 정의되어 있다.

## Daily topic pipeline

```text
article candidate
→ grouping / representative selection
→ 필요한 raw article 처리
→ summary 생성
→ topics / topic_articles
→ /topics, /topics/home, /topics/{topic_id}
```

진입점은 `scripts/run_daily_topic_pipeline.py`다.
`news-daily-topic-pipeline` CronJob은 `04:00 Asia/Seoul`에 실행되도록
manifest에 정의되어 있다.

Provider 호출과 DB write 여부는 script option에 따라 달라진다. Agent는
task에서 허용한 dry-run만 실행하며, DB write나 운영 CronJob 실행은 자동으로
수행하지 않는다. 운영 절차는 [CronJob runbook](../runbooks/cronjobs.md)을
참고한다.

## Article embedding batch

Article embedding은 daily topic pipeline과 분리된 수동 소량 batch다.

```text
articles.title + articles.summary
→ whitespace normalization
→ SHA-256 source hash
→ article_embeddings lookup
→ same hash: reuse
→ missing or changed hash: OpenAI embedding 생성
→ 1536 dimension 검증
→ article_embeddings insert/update
```

진입점은 `scripts/embed_articles.py`다. 기본 limit은 10이고 최대 100으로
제한한다. `--article-id`는 특정 기사만 선택하며 반복 지정할 수 있다.
`--dry-run`은 기사 선택만 수행하고 embedding provider와 DB write를 호출하지
않는다.

Stored vector similarity는 application 내부 함수가 pgvector cosine distance
operator를 사용해 조회한다. 비교 범위는 같은 provider, model, dimension,
source text type으로 제한하며 public API endpoint는 제공하지 않는다.

이 batch는 현재 CronJob 또는 `scripts/run_daily_topic_pipeline.py`에 연결하지
않는다.
