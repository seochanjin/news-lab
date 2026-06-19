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
