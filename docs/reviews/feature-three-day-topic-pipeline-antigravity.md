# Antigravity Review: 3일 Topic pipeline·저장·API·CronJob 구축

## Review Summary
`feature/three-day-topic-pipeline` 브랜치의 구현 결과를 분석한 결과, 3일 Topic pipeline 구축 작업이 성공적으로 수행되었습니다. 최근 72시간 동안 수집된 기사와 기존 `article_embeddings` 데이터를 기반으로 재클러스터링하여 3일 단위 주요 이슈를 생성하는 독립적인 파이프라인과 전용 테이블(`three_day_topics`, `three_day_topic_articles`, `three_day_topic_runs`), FastAPI API 라우터(`three_day_topics.py`), 그리고 K3s CronJob manifest가 완벽히 구축되었습니다.
모든 요구사항이 충족되었으며, 261개의 로컬 단위 테스트가 모두 통과했고, compileall 및 git diff --check 검증을 통해 코드 안정성과 스타일 무결성이 검증되었습니다. 따라서 Verdict는 `APPROVED`로 판정합니다.

## Requirement Coverage
- **72시간 윈도우 및 시간 정책**: `Asia/Seoul` 시간대를 기준으로 정확히 72시간의 윈도우(`[window_start, window_end)`)를 설정하고, 파이프라인의 모든 단계에서 일관되게 동일한 윈도우를 공유하도록 구현되었습니다. 기사 조회 시 `coalesce(published_at, created_at)`를 기준으로 사용합니다.
- **임베딩 재사용**: 외부 임베딩 provider 호출을 방지하고 기존 `article_embeddings`에 저장된 임베딩만을 사용합니다. 임베딩이 누락되거나 메타데이터가 불일치하는 기사는 안전하게 제외되고 사유별로 `three_day_topic_runs`에 통계로 기록됩니다.
- **3일 독립 클러스터링**: 1일 Topic 결과를 재집계하지 않고 최근 72시간의 임베딩을 직접 재클러스터링합니다. 임계값, 최대 관련 기사 수, 요약 근거 기사 수 등 설정값은 독립적으로 관리됩니다.
- **대표 기사 및 요약 근거 분리**: 대표 기사 ⊆ 요약 근거 기사 ⊆ 관련 기사의 관계를 만족하며, URL 및 정규화된 제목 중복을 제거하여 중복된 출처나 중복 기사가 요약에 과도하게 반영되는 것을 방지합니다.
- **실패 격리 및 지연 원문 확보**: 선정된 요약 근거 기사에 대해서만 원문을 확보(저장 원문 우선, 미존재 시 지연 추출)하며, 단일 기사 또는 특정 Topic의 원문 확보/요약 실패가 다른 Topic 처리를 중단시키지 않도록 예외 격리가 구현되었습니다.
- **멱등성 및 원자적 저장**: `pg_advisory_xact_lock`을 적용하여 윈도우별 중복 실행 및 데이터 오염을 방지하고, 하나의 트랜잭션 내에서 기존 윈도우 데이터 삭제 후 벌크 삽입을 수행하여 저장 무결성을 보장합니다.
- **API 개발**: `GET /three-day-topics`, `GET /three-day-topics/home`, `GET /three-day-topics/{topic_id}`가 구현되었으며, 정적 경로인 `/home`이 동적 경로인 `/{topic_id}`보다 먼저 등록되도록 보장했습니다.
- **CronJob manifest**: `05:00 Asia/Seoul` 스케줄, `concurrencyPolicy: Forbid`, 3개 보존 이력 제한, `activeDeadlineSeconds: 1800` 등을 충족하는 CronJob yaml이 생성되었습니다.

## Code Quality / Maintainability
- 1일과 3일 파이프라인이 기사 선정 및 중복 제거 로직을 공유하기 위해 `app/services/topic_pipeline/selection.py` 공통 헬퍼 모듈을 추출하였습니다. 이 과정에서 기존 1일 파이프라인의 동작에 부수 효과가 생기지 않도록 차단하고 테스트로 보호되었습니다.
- 신규 작성된 모든 Python 모듈, 클래스, 메서드, 함수 및 테스트 함수에 한글 docstring이 작성되어 프로젝트 문서화 규칙([task-authoring-guide.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/agent/task-authoring-guide.md))을 완벽하게 준수하고 있습니다.
- SQLAlchemy 쿼리는 `text()`와 바인드 파라미터를 사용하여 SQL injection 위협을 완벽히 방어하였습니다.

## Security Review
- DB 연결 정보(`DATABASE_URL`) 및 OpenAI API Key(`OPENAI_SUMMARY_API_KEY`)는 하드코딩되거나 노출되지 않고, Kubernetes Secret(`news-api-secret`)을 통해 동적으로 주입되도록 설계되었습니다.
- API 파라미터는 FastAPI Query 및 Pydantic 데이터 타입을 이용해 엄격하게 타입을 지정 및 검증하고 있습니다.

## Operational Risk
- `pg_advisory_xact_lock`을 통해 여러 파이프라인이 동시 또는 병렬로 동일 윈도우를 재실행할 때 발생할 수 있는 데이터 경합이나 중복 저장을 차단하였습니다.
- 파이프라인 실행 중 오류가 발생하더라도, 기존 성공 데이터가 유실되지 않도록 실행 종료(finish) 시점에 원자적으로 교체 트랜잭션을 실행합니다.
- 3일 CronJob의 실행 실패 이력은 `three_day_topic_runs`에 안전하게 기록되어 운영 모니터링이 용이합니다.
- 수동 인프라 반영(K3s apply, DB SQL migration 실행 등)과 production 검증은 Antigravity가 수행하지 않고 사람 통제 작업(Human-required verification)으로 온전히 격리시켰습니다.

## Scope Control
- 7일 Topic 테이블 및 파이프라인, 그리고 프론트엔드 레포지토리와 연관 문서는 범위에서 완벽하게 제외되었습니다.
- 기존 Daily Topic 파이프라인의 운영 스케줄 및 동작 계약은 전혀 변경되지 않았으며, 1일 관련 테스트 회귀를 통해 이를 확실히 확인하였습니다.

## Verification Review
- 검증 문서 `docs/verification/feature-three-day-topic-pipeline.md`에 로컬에서 실제 수행한 테스트 명령어와 261개 테스트 통과, compileall, git diff --check 등의 실행 결과가 충실히 기록되어 있습니다.
- 실제 운영 DB 반영 및 K3s 적용은 안전 규칙에 따라 수행되지 않았으며, 검증 문서에서도 `human-required`로 표시되어 claims와 실제 증거의 완벽한 일치를 보장합니다.

## Documentation Review
- `README.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 및 각종 아키텍처 세부 문서(`pipeline.md`, `database.md`, `backend-api.md`, `k3s-runtime.md`, `overview.md`), 런북(`cronjobs.md`, `database-check.md`, `routine-check.md`)에 3일 파이프라인과 수동 반영/장애 복구 절차, 설계 대안 및 트레이드오프가 상세히 기록되어 운영 문서가 현행화되었습니다.

## Problems Found
- 발견된 결함이나 개선 필요 사항이 존재하지 않습니다. (None)

## Required Fixes Before PR
- 없음. (None)

## Optional Improvements
- 향후 뉴스 기사 수집량이 크게 증가하는 경우를 대비해, 72시간 재클러스터링 수행 시 CPU/메모리 부하 및 API 응답 시간 변화를 정기적으로 모니터링하는 것을 추천합니다.

## Suggested Test Commands
```bash
# 3일 파이프라인 및 레포지토리 집중 테스트
python -m pytest tests/test_run_three_day_topic_pipeline.py tests/test_three_day_topic_pipeline.py tests/test_three_day_topic_repository.py -v

# 3일 API 테스트
python -m pytest tests/test_three_day_topics_api.py -v

# 3일 CronJob manifest 검증 테스트
python -m pytest tests/test_three_day_topic_pipeline_cronjob_manifest.py -v

# Daily 파이프라인 회귀 테스트
python -m pytest tests/test_run_daily_topic_pipeline.py tests/test_daily_topic_pipeline_cronjob_manifest.py -v

# 전체 단위 테스트 실행
python -m pytest

# Python 전체 컴파일 검증
python -m compileall app scripts tests

# Whitespace 무결성 검증
git diff --check
```

## Verdict
- APPROVED
