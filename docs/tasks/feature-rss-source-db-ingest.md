# Task: 다중 RSS source 수집 및 DB 저장 MVP

## Goal

NewsLab RSS collector를 TechCrunch 중심 구조에서 다중 RSS source 수집 구조로 확장하고, 검증된 RSS feed에서 article metadata를 Supabase DB에 저장한다.

이번 작업의 목적은 28차 중복 제거와 30차 topic grouping을 위한 실제 article 후보 데이터를 확보하는 것이다.

NewsLab은 단순 최신 기사 목록 서비스가 아니라 “오늘의 뉴스 흐름”을 정리하는 topic digest service를 목표로 한다. 따라서 27차에서는 여러 source에서 하루 기준 article metadata를 충분히 확보할 수 있는 수집 기반을 만든다.

이번 차수의 성공 기준은 topic grouping이나 요약을 구현하는 것이 아니라, 여러 RSS source에서 article metadata가 실제 DB에 저장되고, source별 수집 결과를 확인할 수 있는 것이다.

## Scope

이번 작업 범위는 다음으로 제한한다.

- RSS source registry 또는 config를 추가한다.
- source metadata를 정의한다.
  - name
  - feed_url
  - category
  - country
  - language
  - enabled
  - trust_level
- collector가 enabled RSS source를 순회하도록 수정한다.
- source별 feed fetch / parse / insert 처리를 수행한다.
- source 하나가 실패해도 나머지 source 수집은 계속 진행되도록 한다.
- source별 수집 결과를 확인할 수 있게 한다.
  - parsed_count
  - inserted_count
  - skipped_count
  - error_count
- 기존 TechCrunch 수집 동작을 유지한다.
- 기존 article insert 및 중복 방지 동작을 유지한다.
- local collector 실행으로 Supabase DB에 article metadata가 저장되는 것을 확인한다.
- `/articles`, `/sources`, `/collector/status`, `/collector/runs` read-only 확인을 수행한다.
- source 증가로 raw extractor가 과도하게 실행될 위험이 있는지 현재 `scripts/extract_raw_articles.py`의 limit/status 조건을 확인하고 문서화한다.
- 27차 기준으로 하루 100~300개 article metadata 수집 가능성을 판단할 수 있도록 source별 parsed / inserted / skipped count를 기록한다.

초기 enabled source 후보는 다음을 기준으로 한다.

| name               | feed_url                                        | category | country | language | trust_level |
| ------------------ | ----------------------------------------------- | -------- | ------- | -------- | ----------- |
| TechCrunch         | https://techcrunch.com/feed/                    | tech     | US      | en       | medium      |
| Ars Technica       | https://feeds.arstechnica.com/arstechnica/index | tech     | US      | en       | medium      |
| Wired              | https://www.wired.com/feed/rss                  | tech     | US      | en       | medium      |
| Hacker News        | https://news.ycombinator.com/rss                | tech     | US      | en       | medium      |
| BBC World          | https://feeds.bbci.co.uk/news/world/rss.xml     | world    | GB      | en       | high        |
| The Guardian World | https://www.theguardian.com/world/rss           | world    | GB      | en       | high        |
| Al Jazeera         | https://www.aljazeera.com/xml/rss/all.xml       | world    | GLOBAL  | en       | medium      |
| DW English         | https://rss.dw.com/rdf/rss-en-all               | world    | DE      | en       | medium      |

다음 source는 27차에서 조사 또는 probe 후보로 남긴다. 실제 enabled 여부는 fetch 안정성, item 수, URL 품질, 중복 위험을 확인한 뒤 결정한다.

- CNBC
- MarketWatch
- The Verge
- MIT Technology Review
- Google News RSS
- Reuters
- AP News
- 국내 언론 RSS 후보
- NewsAPI
- GDELT

Google News RSS는 aggregator 성격이 있으므로 27차에서 바로 기본 enabled source로 넣기보다, 28차 normalized_url / duplicate handling 설계와 함께 검토한다.

## Do not change

이번 차수에서는 다음을 변경하지 않는다.

- topic grouping 구현
- embedding 생성
- keyword extraction
- AI summary 생성
- article_summary_ko 생성
- topic_summary_ko 생성
- raw article extraction 확장
- raw article extraction 정책 변경
- frontend code
- K8s manifests
- CronJob schedule
- Docker image tag 정책
- GitHub Actions workflow
- production rollout
- DB provider
- Oracle DB / Oracle NoSQL / MongoDB 연동
- Supabase SQL migration 실행
- DB schema migration 실행

현재 K3s에는 다음 workload가 있다.

- Deployment: `news-api`
- Service: `news-api`
- Ingress: `news-api-ingress`
- CronJob: `news-rss-collector`
- CronJob: `news-raw-extractor`

`news-rss-collector` CronJob은 매일 03:00 Asia/Seoul에 다음 command를 실행한다.

```bash
python scripts/collect_rss.py
```

`news-raw-extractor` CronJob은 매일 03:30 Asia/Seoul에 다음 command를 실행한다.

```bash
python scripts/extract_raw_articles.py
```

두 CronJob 모두 `DATABASE_URL`을 `news-api-secret`에서 주입받는다.

이번 차수에서는 K8s manifest를 변경하지 않는다. collector 코드가 변경되더라도 production 반영, Docker build/push, rollout, manual CronJob 실행은 사람이 별도로 판단한다.

## Expected files

예상 변경 파일은 실제 repository 구조에 따라 조정한다.

주요 변경 후보:

- `scripts/collect_rss.py`
- RSS source registry/config 파일
  - 예: `app/config/rss_sources.py`
  - 또는 repository 구조에 더 적합한 위치
- 관련 테스트 파일이 이미 있다면 테스트 파일
- `docs/tasks/feature-rss-source-db-ingest.md`
- `docs/verification/feature-rss-source-db-ingest.md`
- `docs/pr/feature-rss-source-db-ingest.md`
- `docs/devlog/feature-rss-source-db-ingest.md`
- `docs/reviews/feature-rss-source-db-ingest-antigravity.md`
- `docs/fixes/feature-rss-source-db-ingest-approved-fixes.md`

필요 시 최소 범위에서 문서 업데이트를 수행할 수 있다.

- `README.md`
- `docs/RUNBOOK.md`
- `AGENTS.md`

단, README / RUNBOOK / AGENTS 업데이트는 실제 변경 내용과 운영 영향이 있을 때만 수행한다.

## DB changes

이번 차수에서는 DB provider를 변경하지 않는다.

현재 Supabase PostgreSQL을 primary DB로 유지한다.

이번 차수에서 저장하는 것은 article metadata 중심이다.

저장 대상:

- title
- url
- source
- category
- rss_summary 또는 summary
- published_at
- tags
- created_at

이번 차수에서 저장하지 않는 것:

- raw_text 대량 저장
- embeddings
- article_summary_ko
- topic_summary_ko
- topic keyword table
- topic grouping result

DB schema migration은 기본적으로 수행하지 않는다.

가능한 경우 기존 schema 안에서 다음을 처리한다.

- source row 조회 또는 생성
- source_id 매핑
- article metadata insert
- 기존 중복 방지 로직 유지

만약 다중 source 저장을 위해 schema 변경이 반드시 필요하다면, Codex가 임의로 migration을 실행하지 않는다. 필요한 변경 사항, 이유, 영향 범위, SQL 초안을 문서로 제안하고 사람이 승인한 뒤 별도 차수 또는 fix로 진행한다.

Supabase 무료 DB 용량을 고려해 27차에서는 raw_text, embedding, AI summary를 대량 저장하지 않는다.

## API changes

이번 차수에서 신규 API는 추가하지 않는다.

기존 API의 응답 구조를 깨지 않는다.

확인 대상 API:

- `/health`
- `/sources`
- `/articles`
- `/collector/status`
- `/collector/runs`

기대 사항:

- `/articles`에서 여러 source의 article metadata가 조회된다.
- `/sources`에서 source 목록 또는 source 관련 정보가 기존 구조에 맞게 확인된다.
- `/collector/status` 또는 `/collector/runs`에서 collector 실행 결과를 확인할 수 있다.
- 기존 frontend가 사용하는 `/articles` 응답 구조는 유지한다.

이번 차수에서 다음 API는 추가하지 않는다.

- `/topics`
- `/topics/{topic_id}`
- `/keywords`
- `/summaries`
- `/topic-groups`

topic 관련 API는 30차 이후 topic grouping 구현 단계에서 검토한다.

## Test commands

로컬 실행 기준 검증 후보:

```bash
git status --short
git diff --stat
git diff --check
```

collector 실행:

```bash
python scripts/collect_rss.py
```

로컬 API 서버 실행:

```bash
uvicorn app.main:app --reload
```

로컬 API 확인:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/sources
curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
curl http://127.0.0.1:8000/collector/status
curl "http://127.0.0.1:8000/collector/runs?limit=5"
```

raw extractor 현재 처리 조건 확인:

```bash
git grep -n "limit\|status\|raw\|extract" scripts/extract_raw_articles.py app db
```

변경 범위 확인:

```bash
git diff -- k8s
git diff -- app scripts db
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```

테스트가 존재한다면 실행한다.

```bash
pytest
```

production 확인은 이번 task의 필수 검증이 아니다.

production 확인이 필요하면 사람이 별도로 판단하고, read-only 명령과 production-impacting 명령을 구분해 기록한다.

## Acceptance criteria

- RSS source registry 또는 config가 추가되어 있다.
- 최소 8개 이상의 enabled RSS source 후보가 정의되어 있다.
- 가능하면 10~12개 source까지 확장 가능하도록 구조가 잡혀 있다.
- collector가 enabled RSS source를 순회한다.
- source 하나가 실패해도 나머지 source 수집은 계속 진행된다.
- source별 parsed_count / inserted_count / skipped_count / error_count를 확인할 수 있다.
- 기존 TechCrunch 수집 동작은 유지된다.
- 기존 article insert 및 중복 방지 동작은 유지된다.
- article metadata가 Supabase DB에 저장되는 것을 local collector 실행으로 확인한다.
- `/articles`에서 여러 source의 article이 조회되는 것을 확인한다.
- `/collector/status` 또는 `/collector/runs`에서 collector 실행 결과를 확인한다.
- 하루 100~300개 article metadata 수집 가능성을 판단할 수 있는 source별 count 근거가 남아 있다.
- raw extractor가 source 증가 후 과도하게 실행될 위험이 있는지 현재 동작을 확인하고 문서화한다.
- K8s manifest는 변경하지 않는다.
- 신규 topic API는 추가하지 않는다.
- topic grouping, embedding, AI summary, raw extraction 확장은 구현하지 않는다.
- DB schema migration은 사람이 명시적으로 승인하지 않는 한 수행하지 않는다.
- production-impacting command는 실행하지 않는다.
- 실제 secret, token, private IP, kubeconfig, `.env` 값은 문서나 코드에 기록하지 않는다.

## Notes

NewsLab의 기본 제품 단위는 “오늘의 뉴스 흐름”이다.

따라서 이후 topic grouping, keyword ranking, topic summary의 기본 집계 단위는 Asia/Seoul 기준 하루 또는 최근 24시간으로 한다.

MVP에서는 Asia/Seoul 기준 `topic_date` 하루 단위로 article metadata를 모으고, 해당 날짜의 기사들을 기준으로 중복 제거와 topic grouping을 수행하는 방향을 우선한다.

2~3일 누적 데이터는 기본 topic ranking 기준이 아니라, ongoing topic, rising topic, yesterday comparison을 위한 보조 signal로 사용한다.

27차에서 중요한 것은 단순히 source 목록을 늘리는 것이 아니라, 여러 source에서 실제 article metadata가 DB에 저장되고, 다음 차수에서 중복 제거와 topic grouping을 검증할 수 있는 데이터가 확보되는 것이다.

현재 운영 구조에서는 RSS collector가 03:00에 실행되고 raw extractor가 03:30에 실행된다. source 수가 늘어나면 raw extractor가 갑자기 더 많은 article을 처리하려고 할 수 있으므로, raw extractor의 limit/status 조건을 확인해야 한다.

Google News RSS는 수집량을 빠르게 늘릴 수 있는 후보지만, aggregator 성격이 있어 URL 정규화와 중복 제거 설계에 영향을 준다. 따라서 27차에서는 바로 기본 enabled source로 넣기보다 probe/deferred source로 기록하고, 28차 normalized_url 설계와 함께 검토한다.

이번 차수에서 production rollout은 자동 수행하지 않는다. Docker image build/push, K3s rollout, manual CronJob 실행, production collector 결과 확인은 사람이 별도로 판단한다.
