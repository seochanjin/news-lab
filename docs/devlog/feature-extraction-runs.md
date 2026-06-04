# 본문 추출 실행 이력 저장

## 작업 목적

- raw article extractor의 실행 단위 이력을 DB에 저장하고 API로 조회할 수 있게 한다.
- RSS collector의 `crawl_runs`와 유사한 운영 관측 지점을 extractor에도 추가한다.

## 기존 문제

- `raw_articles`는 기사별 추출 결과만 저장한다.
- extractor를 언제 실행했는지, 전체 성공/실패 카운트가 얼마인지, 실행 자체가 실패했는지 확인할 실행 이력 테이블이 없었다.

## 변경 내용

- `db/migrations/004_create_extraction_runs.sql`
  - `extraction_runs` 테이블 생성 SQL 추가
- `scripts/extract_raw_articles.py`
  - `create_extraction_run()` 추가
  - `finish_extraction_run()` 추가
  - 실행 시작 시 `running` 레코드 생성
  - 정상 종료 시 `success_count`, `failed_count`, `status=success` 저장
  - 예상 밖 예외 발생 시 `status=failed`, `error_message` 저장 후 예외 재발생
- `app/routers/extractor.py`
  - `GET /extractor/status`
  - `GET /extractor/runs`
  - `GET /extractor/runs?status=success`
  - `GET /extractor/runs?status=failed`
- `app/main.py`
  - extractor 라우터 등록

## 테스트

- 이번 작업에서는 Supabase SQL을 실행하지 않았다.
- 이번 작업에서는 `scripts/extract_raw_articles.py`를 실행하지 않았다.
- 이번 작업에서는 kubectl 명령을 실행하지 않았다.
- 코드 문법 검증:

```bash
python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(), filename=p) for p in ['app/main.py', 'app/routers/extractor.py', 'scripts/extract_raw_articles.py']]"
```

수동 마이그레이션 이후 로컬 API 확인 명령:

```bash
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/extractor/runs
curl "http://127.0.0.1:8000/extractor/runs?status=success"
curl "http://127.0.0.1:8000/extractor/runs?status=failed"
```

## 운영 반영

- Supabase SQL migration 적용은 사람이 직접 수행해야 한다.
- K3s rollout/restart는 사람이 직접 수행해야 한다.
- production verification은 사람이 직접 수행해야 한다.

## 확인 결과

- extractor 실행 이력 저장을 위한 코드와 API가 추가되었다.
- RSS collector behavior, Kubernetes manifests, secrets, env files는 변경하지 않았다.

## 이번 단계의 의미

- raw article extractor도 collector처럼 실행 단위 관측이 가능해진다.
- 이후 extractor CronJob을 추가할 때 실행 성공/실패를 API로 확인할 기반이 생긴다.

## 다음 단계

- 사람이 `004_create_extraction_runs.sql`을 Supabase에 적용한다.
- 로컬 또는 운영 환경에서 extractor를 실행해 `extraction_runs` 기록 생성을 확인한다.
- `/extractor/status`, `/extractor/runs` 응답을 확인한다.
