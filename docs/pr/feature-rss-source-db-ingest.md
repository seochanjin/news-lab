# 다중 RSS source 수집 및 DB 저장 MVP

## 작업 내용

NewsLab RSS collector를 TechCrunch 중심 수집 구조에서 registry 기반 다중 RSS source 수집 구조로 확장했습니다.

이번 작업은 28차 중복 제거와 30차 topic grouping 검증을 위한 실제 article metadata 후보 데이터를 확보하는 MVP입니다. Topic grouping, embedding, AI summary, raw extraction 확장은 구현하지 않았습니다.

## 주요 변경 사항

- `app/config/rss_sources.py`에 8개 enabled RSS source registry를 추가했습니다.
  - TechCrunch
  - Ars Technica
  - Wired
  - Hacker News
  - BBC World
  - The Guardian World
  - Al Jazeera
  - DW English
- `scripts/collect_rss.py`가 registry를 기존 `sources` 테이블에 동기화한 뒤 enabled source를 순회하도록 변경했습니다.
- source별 feed fetch / parse / insert 처리를 수행하도록 변경했습니다.
- source 하나가 실패해도 나머지 source 수집은 계속되도록 per-source error handling을 추가했습니다.
- article category를 hardcoded `tech` 대신 source category 기준으로 저장하도록 변경했습니다.
- 기존 article insert의 `on conflict (url) do nothing` 중복 방지 동작은 유지했습니다.
- collector stdout에 source별 `parsed`, `inserted`, `skipped`, `errors` count를 출력하도록 했습니다.
- `docs/ARCHITECTURE.md`에서 승인된 문서 정합성 fix를 반영했습니다.
  - `news-rss-collector`: 매일 03:00 Asia/Seoul, `python scripts/collect_rss.py`
  - `news-raw-extractor`: 매일 03:30 Asia/Seoul, `python scripts/extract_raw_articles.py`
  - `Raw article extraction CronJob`을 Not Yet Implemented 항목에서 제거

## 추가/변경된 API

신규 API는 추가하지 않았습니다.

기존 API 응답 구조는 변경하지 않았고, local read-only verification에서 다음 API를 확인했습니다.

- `GET /health`
- `GET /sources`
- `GET /articles?page=1&page_size=20`
- `GET /collector/status`
- `GET /collector/runs?limit=5`

## DB 변경 사항

DB schema migration은 추가하거나 실행하지 않았습니다.

Collector는 기존 schema 안에서 다음을 수행합니다.

- registry source row 조회 또는 생성
- 기존 `sources` 테이블에 존재하는 column만 동기화
- article metadata insert
- `url` 기준 기존 중복 방지 유지

`country`, `language`, `trust_level`은 code registry에 정의되어 있지만, matching DB column이 있을 때만 `sources`에 기록됩니다.

## README 영향

README 변경은 하지 않았습니다.

이번 변경은 collector 구현과 source registry, architecture 문서 정합성 수정에 한정되어 README 업데이트는 필요하지 않다고 판단했습니다.

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

- `pytest`: 현재 환경에 command가 없어 실행하지 못했습니다.
- `python scripts/collect_rss.py`: non-venv Python에 `feedparser`가 없어 collector 실행 전 실패했습니다.
- `.venv/bin/python scripts/collect_rss.py` initial sandbox run: restricted DNS/network로 Supabase host resolution에 실패했습니다.

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

Raw extractor risk 확인:

- 현재 `scripts/extract_raw_articles.py`는 `extract(limit: int = 5)`입니다.
- `get_target_articles()`는 `raw_articles` row가 없는 article만 선택합니다.
- source 증가로 backlog는 늘 수 있지만, 현재 코드 기준 단일 extractor run 처리량은 5개로 제한됩니다.

Approved fix 확인:

- `docs/ARCHITECTURE.md`가 `news-rss-collector`, `news-raw-extractor` CronJob 상태와 schedule/command를 반영합니다.
- `git diff -- k8s`: 출력 없음.
- Approved documentation fix 과정에서 app/script/db 추가 변경은 없었습니다.

## 비고

- K8s manifests는 변경하지 않았습니다.
- CronJob schedule은 변경하지 않았습니다.
- DB migration은 추가하거나 실행하지 않았습니다.
- Supabase SQL은 실행하지 않았습니다.
- Topic grouping, embedding, keyword extraction, AI summary, raw extraction 확장은 구현하지 않았습니다.
- Frontend는 변경하지 않았습니다.
- GitHub Actions workflow는 변경하지 않았습니다.
- Secret, `.env`, kubeconfig, credential, token은 수정하지 않았습니다.
- Production rollout, K3s rollout/restart, Docker build/push, production curl verification은 수행하지 않았습니다.
- PR merge는 완료된 것으로 주장하지 않습니다.
- Production verification은 human operator가 별도로 수행해야 합니다.
