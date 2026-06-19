# Database와 Local Read Check

[Runbook index로 돌아가기](../RUNBOOK.md)

## 원칙

- Agent는 Supabase SQL과 production migration을 실행하지 않는다.
- Credential과 `DATABASE_URL` 값을 출력하거나 기록하지 않는다.
- Collector, extractor, daily pipeline은 DB write 가능성이 있으므로 명시적 승인
  없이 실행하지 않는다.
- Read API 확인과 schema file 검토를 DB 상태 변경과 구분한다.

## Local API

환경 변수가 이미 안전하게 준비된 local environment에서 실행한다.

```bash
uvicorn app.main:app --reload
```

다른 terminal에서 read endpoint를 확인한다.

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/version
curl http://127.0.0.1:8000/sources
curl http://127.0.0.1:8000/articles
curl http://127.0.0.1:8000/collector/status
curl http://127.0.0.1:8000/raw-articles
curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/topics
curl http://127.0.0.1:8000/topics/home
```

Local API도 실제 configured DB를 읽을 수 있으므로 response 원문이나 민감한
application data를 verification 문서에 그대로 복사하지 않는다.

## Schema 확인

Repository에서 관리하는 변경 이력:

```bash
find db/migrations -maxdepth 1 -type f | sort
rg -n "create table|alter table|create index" db/migrations
```

Migration file 작성은 가능하지만 실행은 사람이 수행한다. 실행 전 migration
내용, 예상 변경, rollback 또는 복구 계획을 review한다.

## DB write script

다음 command는 문서 예시이며 자동 실행 대상이 아니다.

```bash
python scripts/collect_rss.py
python scripts/extract_raw_articles.py
python scripts/run_daily_topic_pipeline.py --execute
```

실행 승인을 요청할 때 생성·변경될 table과 예상 범위를 먼저 설명한다.
