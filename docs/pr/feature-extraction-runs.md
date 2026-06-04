# 본문 추출 실행 이력 저장

## 작업 내용

- raw article extractor 실행 단위 이력을 저장하는 `extraction_runs` 테이블 마이그레이션 추가
- `scripts/extract_raw_articles.py` 실행 시작/완료/실패 상태 기록 추가
- extractor 실행 이력을 읽는 FastAPI 라우터 추가
- `/extractor/status`, `/extractor/runs` API 등록

## 주요 변경 사항

- `db/migrations/004_create_extraction_runs.sql`
  - `started_at`, `finished_at`, `status`, `success_count`, `failed_count`, `error_message`, `created_at` 저장
- `scripts/extract_raw_articles.py`
  - 실행 시작 시 `status=running` 레코드 생성
  - 정상 종료 시 `status=success`와 성공/실패 카운트 저장
  - 예상 밖 예외 발생 시 `status=failed`, 카운트, `error_message` 저장
- `app/routers/extractor.py`
  - 최근 실행 목록 조회
  - 최신 실행 상태 조회
  - `status` 필터 지원
- `app/main.py`
  - extractor 라우터 등록

## 테스트

- Supabase SQL은 실행하지 않음
- data-writing script는 실행하지 않음
- kubectl 명령은 실행하지 않음
- 로컬 문법 검증:

```bash
python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(), filename=p) for p in ['app/main.py', 'app/routers/extractor.py', 'scripts/extract_raw_articles.py']]"
```

마이그레이션을 수동 실행한 뒤 확인할 명령:

```bash
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/extractor/status
curl http://127.0.0.1:8000/extractor/runs
curl "http://127.0.0.1:8000/extractor/runs?status=success"
curl "http://127.0.0.1:8000/extractor/runs?status=failed"
```

추출 실행 이력 생성을 확인하려면 사람이 승인한 뒤 아래 data-writing script를 실행:

```bash
python scripts/extract_raw_articles.py
```

## 확인 결과

- `/extractor/status`는 최신 extraction run을 반환하도록 구현됨
- `/extractor/runs`는 최근 extraction run 목록을 반환하도록 구현됨
- `/extractor/runs?status=success|failed` 필터가 bind parameter 기반으로 동작하도록 구현됨
- RSS collector 동작과 K3s manifests는 변경하지 않음

## 비고

- `004_create_extraction_runs.sql`은 수동으로 Supabase에 적용해야 함
- production rollout/restart 및 production verification은 사람 진행 필요
