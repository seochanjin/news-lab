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

Raw extraction helper와 기존 `raw_articles`, `extraction_runs` 구조는 유지한다.
Scheduled 선추출 CronJob은 운영 흐름에서 제거하고, Daily topic pipeline이
topic 선정 후 selected article 가운데 저장 원문이 없는 기사만 추출한다.

## Daily topic pipeline

```text
article candidate
→ article_embeddings hash 확인
→ 저장 vector 재사용 또는 embedding 생성·저장
→ 유사 기사 clustering / Topic 관련 기사 최대 20건 선정
→ 관련 기사 중 Summary 근거 기사 최대 3건 선정
→ Summary 근거 기사의 저장 원문 재사용 또는 신규 추출
→ Summary 근거 기사 원문으로 topic summary 생성
→ topics / 관련 기사 전체의 topic_articles
→ /topics, /topics/home, /topics/{topic_id}
```

진입점은 `scripts/run_daily_topic_pipeline.py`다.
`news-daily-topic-pipeline` CronJob은 `04:00 Asia/Seoul`에 실행되도록
manifest에 정의되어 있다.

Pipeline 시작 시 `Asia/Seoul` 기준 `pipeline_date`를 한 번 결정한다. 기사 후보,
embedding, topic 선정, 원문 확보, summary/save 단계는 같은 실행 컨텍스트를
전달받으며 최종 `topics.topic_date`도 이 날짜를 사용한다.

내부 단계의 책임은 다음과 같다.

1. 기사 후보 및 embedding 준비
2. 유사 기사 clustering 및 topic 선정
3. Summary 근거 기사 원문 확보
4. Summary 생성 및 관련 기사 전체 저장

실행 진입점은 CLI, 실행 context, runtime dependency와 단계 호출 순서만
조정한다. 단계 구현과 결과 계약은 다음 package에 분리되어 있다.

```text
app/services/daily_topic_pipeline/
├── context.py
├── models.py
├── embedding_stage.py
├── topic_selection_stage.py
├── raw_acquisition_stage.py
├── summary_persistence_stage.py
├── runtime.py
└── reporting.py
```

`context.py`와 `models.py`는 stage module을 import하지 않는다. 각 stage는 공통
context와 결과 타입에만 의존하며, 단계 사이 결과는 같은 Python process에서
객체로 전달한다.

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

Daily 기본 상한은 Topic 관련 기사 20건과 Summary 근거 기사 3건이다. Summary
근거 기사는 항상 관련 기사의 부분집합이며 대표 기사를 포함한다. 원문 조회와
신규 추출, Summary provider 입력은 근거 기사에만 적용한다. 저장 단계는 Summary
생성에 성공한 Topic의 관련 기사 전체를 기존 순서와 대표·supporting 역할로
`topic_articles`에 연결한다.

## Three-day topic pipeline

```text
최근 72시간 articles
→ 기존 article_embeddings 호환성·source hash 확인
→ 저장 vector가 있는 기사만 재클러스터링
→ 대표/관련/Summary 근거 기사 선정
→ Summary 근거 기사의 저장 원문 재사용 또는 지연 추출
→ 72시간 변화와 공통 사실을 설명하는 Summary 생성
→ three_day_topics / three_day_topic_articles 원자 교체
→ three_day_topic_runs 실행 이력
→ /three-day-topics, /three-day-topics/home,
  /three-day-topics/{topic_id}
```

진입점은 `scripts/run_three_day_topic_pipeline.py`다.
`news-three-day-topic-pipeline` CronJob은 Daily pipeline 이후인
`05:00 Asia/Seoul`에 실행되도록 manifest에 정의되어 있다.

Pipeline 시작 시 timezone-aware `window_end`를 한 번 확정하고
`window_start = window_end - 72 hours`로 계산한다. 모든 단계와 저장 row는 같은
`[window_start, window_end)` 반개구간을 사용한다. 기사 시각은
`coalesce(published_at, created_at)`이며 후보는 최신순 상한을 적용한다.

3일 pipeline은 기존 `article_embeddings`를 읽기만 한다. Provider/model,
dimension, source type과 현재 title/summary hash가 일치하지 않거나 vector가
유효하지 않은 기사는 제외하고 `missing_embedding_count`에 반영한다. 신규
embedding provider 호출과 embedding insert/update는 수행하지 않는다.

재클러스터링과 기사 선정은 기간에 독립적인 순수 helper를 Daily와 공유하지만,
후보 수, threshold, Topic 수, 관련 기사 수와 Summary 근거 기사 수는 3일 전용
설정이다. 대표 기사는 Summary 근거 기사에 포함되고, Summary 근거 기사는 관련
기사의 부분집합이다.

원문 확보와 Summary 실패는 Topic 단위로 격리한다. 일부 Topic만 성공하면 성공
부분집합을 저장하고 run을 `partial_success`로 기록한다. 전부 실패하면 기존
window 결과를 유지한다. 외부 작업 완료 후 advisory transaction lock 안에서
기존 window 결과 삭제와 신규 결과 삽입을 함께 수행하므로 insert 실패 시 기존
결과가 rollback으로 보존된다.

CLI 기본값은 dry-run이다. `--execute`에서만 run 이력 생성, 지연 원문 추출,
Summary provider 호출과 결과 교체가 발생한다. 세부 계약과 대안은
[3일 Topic 설계 문서](../design/three-day-topic-pipeline.md), 운영 절차는
[CronJob runbook](../runbooks/cronjobs.md)을 참고한다.

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
