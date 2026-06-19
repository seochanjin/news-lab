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
→ article_embeddings hash 확인
→ 저장 vector 재사용 또는 embedding 생성·저장
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

OpenAI embedding provider를 사용하는 daily pipeline은 기사별
`title_summary` source hash를 공통 article embedding storage 모듈에서 확인한다.
같은 provider/model/dimension/source type과 hash의 row가 있으면 저장 vector를
clustering 입력으로 재사용한다. Row가 없거나 hash가 변경되면 provider vector를
생성하고 atomic upsert로 저장한다.

개별 article embedding 실패 또는 dimension 불일치는 해당 article만 clustering
입력에서 제외한다. 정상 article과 vector의 순서를 함께 유지하며, 정상 vector가
2건 미만이면 clustering, summary와 topic 저장을 건너뛴다. Pipeline 결과에는
후보 수, embedding 생성·갱신·재사용·실패 수, clustering 입력 수, topic 수와
전체 elapsed seconds를 포함한다.

## Article embedding batch

Article embedding은 독립 수동 batch에서도 생성·재사용 상태를 확인할 수 있다.

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

Daily topic pipeline과 독립 batch는 같은 normalization, source hash, provider,
model, dimension과 source type 계약을 공유한다. 독립 batch는 소량 운영 확인과
복구 진단 경로로 유지한다.
