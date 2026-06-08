# 다중 RSS source 수집 및 DB 저장 MVP

## 작업 목적

NewsLab RSS collector를 TechCrunch 중심 구조에서 다중 RSS source 수집 구조로 확장해, 28차 중복 제거와 30차 topic grouping을 검증할 실제 article metadata 후보 데이터를 확보한다.

이번 단계의 목표는 topic grouping이나 요약 구현이 아니라, 여러 RSS source에서 하루 기준 article metadata를 충분히 수집하고 source별 수집 결과를 확인할 수 있는 기반을 만드는 것이다.

## 기존 문제

- 기존 collector는 enabled RSS feed를 읽을 수 있었지만, 코드 차원의 source registry가 없어 다중 source 후보를 일관되게 관리하기 어려웠다.
- article insert 시 category가 `tech`로 고정되어 world source 확장에 맞지 않았다.
- source별 `parsed / inserted / skipped / error` count를 한 번에 확인하기 어려웠다.
- feed 하나가 실패하면 collector 전체 흐름에 영향을 줄 수 있었다.
- source 수가 늘어나면 raw extractor가 과도하게 실행될 수 있는지 확인할 근거가 필요했다.
- `docs/ARCHITECTURE.md`에는 raw article extraction CronJob 상태가 실제 운영 구조와 다르게 남아 있었다.

## 변경 내용

- `app/config/rss_sources.py`를 추가해 8개 enabled RSS source registry를 정의했다.
  - TechCrunch
  - Ars Technica
  - Wired
  - Hacker News
  - BBC World
  - The Guardian World
  - Al Jazeera
  - DW English
- `scripts/collect_rss.py`를 registry 기반 다중 source collector로 확장했다.
- collector가 registry를 기존 `sources` 테이블에 동기화한 뒤 enabled source를 순회하도록 했다.
- source별 feed fetch / parse / insert 흐름을 수행하도록 했다.
- source 하나가 실패해도 나머지 source 수집은 계속되도록 per-source error handling을 추가했다.
- article category를 source category 기준으로 저장하도록 변경했다.
- 기존 `on conflict (url) do nothing` 중복 방지 동작은 유지했다.
- collector stdout에 source별 `parsed`, `inserted`, `skipped`, `errors` count를 출력하도록 했다.
- 승인된 fix로 `docs/ARCHITECTURE.md`의 CronJob 상태를 실제 운영 구조와 맞췄다.
  - `news-rss-collector`: 매일 03:00 Asia/Seoul, `python scripts/collect_rss.py`
  - `news-raw-extractor`: 매일 03:30 Asia/Seoul, `python scripts/extract_raw_articles.py`
  - `Raw article extraction CronJob`을 Not Yet Implemented 항목에서 제거

## 구현 상세

Source registry는 `app/config/rss_sources.py`에 두었다. 각 source는 `name`, `feed_url`, `url`, `category`, `country`, `language`, `enabled`, `trust_level`을 가진다.

Collector는 시작 시 `sync_source_registry()`를 실행해 registry source를 `sources` 테이블에 반영한다. DB schema migration을 추가하지 않는 것이 task 범위였기 때문에, `information_schema.columns`로 현재 `sources` 테이블에 존재하는 column만 확인하고 해당 column만 insert/update한다.

`get_enabled_sources()`는 enabled source와 `feed_url`을 읽고, source category를 article insert에 전달한다. 기존 TechCrunch 수집과 `url` conflict 기반 중복 방지 동작은 유지했다.

한 source 처리 중 예외가 발생하면 해당 source result의 `error_count`를 증가시키고 다음 source로 넘어간다. 전체 run은 source error가 없으면 `success`, source error가 있으면 `partial_success`로 마무리한다.

Raw extractor는 코드 변경 없이 현재 동작만 확인했다. `scripts/extract_raw_articles.py`는 `extract(limit: int = 5)`이고, `get_target_articles()`는 `raw_articles` row가 없는 article만 선택한다.

## 대안 검토

- DB schema migration으로 `sources.country`, `sources.language`, `sources.trust_level`을 추가하는 방안
  - 이번 task에서는 DB schema migration 실행과 schema 변경을 기본적으로 하지 않는 것이 원칙이므로 선택하지 않았다.
- 신규 API로 source별 collector telemetry를 제공하는 방안
  - 이번 task에서는 신규 API를 추가하지 않는 것이 scope였기 때문에 선택하지 않았다.
- Google News RSS 같은 aggregator source를 바로 enabled source로 추가하는 방안
  - aggregator URL 정규화와 중복 제거 설계에 영향을 주므로 28차 normalized URL / duplicate handling 단계로 미뤘다.
- Article entry 단위 transaction isolation 개선
  - approved fixes 문서에서 후속 개선으로 deferred 처리했다. 이번 MVP에서는 source 단위 transaction을 유지했다.

## 선택한 접근과 근거

Registry 기반 collector 확장을 선택했다. 이유는 source 후보를 코드에서 명확히 관리할 수 있고, 기존 `sources` 테이블과 `articles` insert 구조를 유지하면서 다중 source 수집을 검증할 수 있기 때문이다.

DB schema 변경 없이 현재 존재하는 column만 동기화하는 방식을 선택했다. 이유는 Supabase SQL migration과 DB schema migration을 사람이 승인해야 하는 안전 규칙을 지키면서도 MVP 수집 검증을 진행할 수 있기 때문이다.

신규 API를 추가하지 않고 기존 `/sources`, `/articles`, `/collector/status`, `/collector/runs`로 검증했다. 이유는 기존 API 응답 구조를 깨지 않고 collector 결과와 article metadata 저장 여부를 확인할 수 있었기 때문이다.

## 트레이드오프

- Source별 detailed telemetry는 stdout과 aggregate `crawl_runs` 중심이다. 별도 per-source run table은 만들지 않았다.
- `country`, `language`, `trust_level`은 registry에는 정의되지만, DB에 matching column이 없으면 저장되지 않는다.
- Source 단위 transaction을 유지했기 때문에 특정 source 안의 단일 article DB error가 해당 source insert 결과에 영향을 줄 수 있다. 이 개선은 후속 collector 안정화 단계에서 재검토한다.
- Google News RSS를 제외해 단기 수집량을 더 키울 수 있는 선택지는 미뤘지만, URL normalization과 duplicate handling 설계 전까지 aggregator 영향은 피했다.

## 테스트

검증 source of truth: `docs/verification/feature-rss-source-db-ingest.md`

실행 및 확인된 명령:

```bash
.venv/bin/python -m py_compile scripts/collect_rss.py app/config/rss_sources.py
git diff --check
git diff -- k8s
git diff -- app scripts db
git grep -n "limit\|status\|raw\|extract" scripts/extract_raw_articles.py app db
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\.env"
.venv/bin/python scripts/collect_rss.py
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/sources
curl "http://127.0.0.1:8000/articles?page=1&page_size=20"
curl http://127.0.0.1:8000/collector/status
curl "http://127.0.0.1:8000/collector/runs?limit=5"
```

Approved fix 검증:

```bash
git diff -- docs/ARCHITECTURE.md
git diff -- k8s
git diff -- app scripts db
grep -n "raw extractor\|raw article\|CronJob\|news-raw-extractor\|news-rss-collector" docs/ARCHITECTURE.md
```

미완료 또는 실패한 항목:

- `pytest`: 현재 환경에 command가 없어 실행하지 못했다.
- `python scripts/collect_rss.py`: non-venv Python에 `feedparser`가 없어 collector 실행 전 실패했다.
- `.venv/bin/python scripts/collect_rss.py` initial sandbox run: restricted DNS/network로 Supabase host resolution에 실패했다.

## 운영 반영

운영 반영은 수행하지 않았다.

수행하지 않은 작업:

- Docker image build/push
- K3s rollout/restart
- Kubernetes manifest apply
- Supabase SQL migration execution
- Manual CronJob execution in production
- Production curl verification
- Git push / git merge / PR merge

Production 반영과 검증은 human operator가 별도로 판단하고 수행해야 한다.

## README 업데이트 판단

README는 업데이트하지 않았다.

이번 변경은 collector 구현, source registry 추가, architecture 문서 정합성 수정에 한정된다. 사용자-facing 사용법이나 API contract가 바뀌지 않았고, 신규 API나 신규 운영 절차를 README에 추가해야 하는 수준의 변경은 아니라고 판단했다.

## 확인 결과

Collector local run 결과:

- Crawl run ID: `11`
- Status: `success`
- `inserted_count`: `190`
- `skipped_count`: `20`
- `error_count`: `0`

Source별 결과:

| Source | Parsed | Inserted | Skipped | Errors |
| --- | ---: | ---: | ---: | ---: |
| TechCrunch | 20 | 1 | 19 | 0 |
| Ars Technica | 20 | 20 | 0 | 0 |
| Wired | 30 | 30 | 0 | 0 |
| Hacker News | 30 | 30 | 0 | 0 |
| BBC World | 25 | 24 | 1 | 0 |
| The Guardian World | 30 | 30 | 0 | 0 |
| Al Jazeera | 25 | 25 | 0 | 0 |
| DW English | 30 | 30 | 0 | 0 |

Local API 확인:

- `/health`: `status=ok`
- `/sources`: `count=10`, registry 기반 8개 source enabled 확인
- `/articles?page=1&page_size=20`: `count=20`, `total=273`, 여러 source article metadata 확인
- `/collector/status`: latest run `id=11`, `status=success`, `inserted_count=190`, `skipped_count=20`
- `/collector/runs?limit=5`: run `11`이 최신 run으로 조회됨

Raw extractor 확인:

- 현재 `extract(limit: int = 5)`이다.
- `raw_articles` row가 없는 article만 target으로 선택한다.
- source 증가로 backlog는 늘 수 있지만, 현재 코드 기준 단일 extractor run 처리량은 5개로 제한된다.

Approved fix 확인:

- `docs/ARCHITECTURE.md`가 `news-rss-collector`, `news-raw-extractor` CronJob 상태와 schedule/command를 반영한다.
- `git diff -- k8s`: 출력 없음.
- Approved documentation fix 과정에서 app/script/db 추가 변경은 없었다.

## 이번 단계의 의미

NewsLab의 기본 제품 단위인 “오늘의 뉴스 흐름”을 만들기 위한 article 후보 데이터 기반을 확보했다.

이번 run에서 8개 source 기준 parsed 210건, inserted 190건이 확인되어 하루 100-300개 article metadata 수집 가능성을 판단할 근거가 생겼다. 다음 단계에서 normalized URL, duplicate handling, topic grouping을 검증할 실제 데이터가 마련되었다.

## 포트폴리오용 요약

RSS collector를 단일 source 중심 구조에서 registry 기반 다중 source 수집 구조로 확장했다. 8개 RSS source를 대상으로 source별 fetch, parse, insert, skip, error count를 기록했고, local collector run에서 article metadata 190건 저장을 검증했다. 신규 API나 DB schema migration 없이 기존 FastAPI/Supabase 구조를 유지하면서 다음 단계의 중복 제거와 topic grouping 실험을 위한 데이터 기반을 만들었다.

## 다음 단계 후보

- 28차 normalized URL 설계 및 duplicate handling 구현
- Google News RSS 같은 aggregator source의 enabled 여부 재검토
- Article entry 단위 transaction isolation 개선 검토
- Source별 collector telemetry를 DB에 저장할지 검토
- Raw extractor backlog 관리 정책 검토
- Production 반영 여부에 대한 human operator 결정
- Production read-only verification은 rollout 이후 human-provided logs 기준으로 별도 기록
