# Antigravity Review: 최근 7일 기사·토픽 파이프라인 확장

## Review Summary
`feature/seven-day-topic-pipeline` 브랜치는 Weekly Topic Pipeline의 전체 설계 및 구현, 데이터베이스 마이그레이션, SQLAlchemy 레포지토리, 목록/상세/홈 API, K3s CronJob 매니페스트, 테스트 코드 작성을 완수했습니다. 검토 결과, 요구사항과 수용 조건(Acceptance Criteria)을 완벽히 만족하며, 기존 Daily 및 3일 Topic 파이프라인에 회귀 결함을 주지 않고 완전히 분리된 전용 테이블과 API, 배치를 통해 독립적으로 동작함을 확인했습니다. 

## Requirement Coverage
- **주간 범위 및 시간대**: Asia/Seoul 기준 완료 주간(월요일 00:00부터 다음 월요일 00:00 미만)을 정확히 결정하고, 파이프라인 context를 통해 후보 조회부터 저장까지 단일 윈도우를 주입하여 일관성을 보장합니다.
- **수동 재처리 지원**: `--week-start` CLI 인자로 YYYY-MM-DD 형식의 월요일 날짜를 엄격히 검증하여 특정 완료 주간의 수동 재처리를 지원합니다.
- **기존 Embedding 재사용**: 신규 embedding provider API를 호출하지 않으며, 기존 `article_embeddings`에 저장된 vector만 read-only로 재사용합니다. embedding 누락 기사는 누락 사유별 통계를 카운트하여 기록하고 제외합니다.
- **재클러스터링 및 기사 선정**: Daily 및 3일 토픽의 저장 결과를 재집계하지 않고, 기사 임베딩 후보로 직접 clustering을 진행합니다. 최소 기사 수 5개 이상, 최소 출처(source) 수 2개 이상 조건이 군집 후보 필터링 시 엄격히 적용됩니다.
- **대표 및 요약 근거 기사 구분**: 대표성 점수를 기준으로 관련 기사를 정렬하며, 요약 근거 기사는 출처 다양성을 극대화하고 중복(URL, 공백 정규화 제목)을 제거하는 결정론적인 알고리즘을 통해 최대 5개까지 선정합니다.
- **원문 대체 및 실패 격리**: 원문이 없는 요약 근거 기사는 지연 추출을 수행하며, 지연 추출 실패 시 동일 군집의 다음 순위 관련 기사 원문으로 자동 대체합니다. 요약 생성 실패가 다른 토픽을 방해하지 않는 실패 격리가 구현되었습니다.
- **원자적 교체 및 Idempotency**: execute 모드에서 성공 토픽이 있거나 정상 빈 결과일 때 window advisory lock 내에서 기존 window 결과를 삭제하고 신규 결과를 삽입하는 원자적 트랜잭션을 적용합니다. 
- **API 및 K3s CronJob**: 목록, 상세, 홈 API가 정상 제공되며 `/weekly-topics/home` 라우트가 동적 라우트보다 먼저 등록되도록 순서를 보장합니다. CronJob은 매주 월요일 00:30 Asia/Seoul 스케줄로 set up 되었으며, embedding key 없이 database url과 summary key만 안전하게 주입받습니다.

## Code Quality / Maintainability
- Daily/3일/Weekly 파이프라인에서 공유할 수 있는 기사 후보 및 임베딩 검증 로직이 `app/services/topic_pipeline/candidate_stage.py` 및 `selection.py` 공통 모듈로 적절히 추출되었으며, 기존 3일 토픽 파이프라인도 이 공통 모듈을 사용하도록 리팩터링되었습니다.
- 새로 추가되거나 대폭 수정된 모든 Python 파일(`models.py`, `context.py`, `repository.py`, `summary_persistence_stage.py` 등) 및 테스트 코드에 실제 역할과 검증 목적을 명확히 하는 한글 docstring이 완벽히 작성되었습니다.

## Security Review
- 모든 DB 쿼리 생성 시 SQLAlchemy `text()`와 bind parameter를 사용하여 SQL Injection 위험성을 방지했습니다.
- Secret 값(`.env`, DATABASE_URL 등)의 하드코딩이나 파일 직접 노출이 없으며, CronJob 매니페스트에서도 secretKeyRef를 통해 안전하게 주입됩니다. container spec에 `allowPrivilegeEscalation: false` 및 `seccompProfile: RuntimeDefault`를 지정하여 보안 모범 사양을 준수했습니다.

## Operational Risk
- 동일 윈도우에 대한 재실행이나 중복 실행으로 결과가 누적되지 않도록 advisory lock 및 트랜잭션 rollback 정책을 설계하여 동시성 레이스 컨디션을 차단했습니다.
- 특정 토픽의 외부 요약 API 오류나 네트워크 실패 시에도 실패 격리를 통해 파이프라인 전체가 실패하지 않고 `partial_success`로 저장되는 구조를 가져 운영 복원력이 높습니다.

## Scope Control
- frontend 저장소나 build/push CI 변경 시도가 없으며, 수정이 제한된 config나 DB 등 외부 components의 production direct apply가 배제되어 scope 내에서 안전하게 변경이 완료되었습니다.

## Verification Review
- `docs/verification/feature-seven-day-topic-pipeline.md`에 모든 테스트 실행 로그(pytest, unittest, compileall, git diff --check)와 verification status 가 통과 상태로 온전하게 기록되어 있습니다.
- kubectl apply client-side dry-run은 안전 규칙에 따라 스킵되었으며, 대신 `tests/test_weekly_topic_pipeline_cronjob_manifest.py`에서 YAML 구조와 argument 파싱을 테스트 코드를 통해 강력히 검증하여 우회 통제를 훌륭히 완수했습니다.

## Documentation Review
- `docs/design/weekly-topic-pipeline.md`에 DB 대안 설계, 트레이드오프 및 선택 근거가 상세히 문서화되어 있습니다.
- `README.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` 등에 7일 Topic 파이프라인, CronJob, API 최초 적용 절차가 올바르게 반영 및 링크화되었습니다.

## Problems Found
- 없음 (None)

## Required Fixes Before PR
- 없음 (None)

## Optional Improvements
- 주간 Summary 프롬프트 버전(`weekly-flow-v1`)의 요약 성능에 대해 실제 프로덕션 기사 및 텍스트 데이터가 누적되는 시점에 품질 모니터링을 진행하는 것을 권장합니다.
- `WeeklyTopicRepository`에서 advisory lock 키 생성 시 `hashtextextended`를 사용하여 문자열을 해싱합니다. 해시 충돌 확률이 극히 희박하나 완벽히 충돌을 배제하기 위해 정수 고유 범위 키 매핑을 고려해볼 수 있으나 현 구조도 충분히 신뢰 가능합니다.

## Suggested Test Commands
- `python -m pytest tests/test_weekly_topic_pipeline.py tests/test_weekly_topic_repository.py tests/test_weekly_topics_api.py tests/test_weekly_topic_pipeline_cronjob_manifest.py -v`
- `python -m pytest`
- `python -m compileall app scripts tests`
- `git diff --check`

## Verdict
PASS

## Re-review 1
### Existing Problems Status
- **최초 리뷰 지적 사항**: 최초 리뷰 시 발견된 문제점(`Problems Found`)이 없었으므로 검토할 기존 문제가 없었습니다.

### Approved Fixes Verification
`docs/fixes/feature-seven-day-topic-pipeline-approved-fixes.md`에 승인된 12개 수정사항(`FIX-01` ~ `FIX-12`)이 실제 구현 및 데이터베이스 명세, 그리고 테스트 코드에 완벽히 적용되었습니다.
- **FIX-01**: `/weekly-topics/home` 조회 시 publishable Topic 상태인 `ready` 필터를 CTE와 본 쿼리에 모두 정상 적용했습니다.
- **FIX-02**: `models.py`에서 서울 기준 월요일 자정 윈도우 시작/종료 여부(시, 분, 초, 마이크로초 = 0) 검증을 추가해 shifted 윈도우 유입을 강력하게 차단했습니다.
- **FIX-03**: `WeeklyRawAcquisitionResult` 포스트 이닛에서 reused, extracted, failed, missing 버킷 간의 상호 배타성과 원문 존재 상태 간의 정합성을 논리적으로 강제했습니다.
- **FIX-04**: `WeeklyTopicProcessingResult`에서 최종 run 상태(`success`, `partial_success`, `failed`)와 내부 저장/실패 토픽 카운트 간의 모순을 거부하는 비즈니스 규칙 검증을 추가했습니다.
- **FIX-05**: `raw_acquisition_stage.py`에 `_merge_selected_raw_texts`를 추가하여 기존 원문과 loader 조회 원문이 병합되도록 하고, loader 조회 값을 우선해 유실을 차단했습니다.
- **FIX-06**: `008_create_weekly_topic_tables.sql` 마이그레이션에 `key_points` 및 `keywords` 컬럼이 JSON array인지 확인하는 `jsonb_typeof() = 'array'` CHECK 제약을 추가했습니다.
- **FIX-07**: `weekly_topics` 테이블의 `article_count >= 5`, `source_count >= 2`, `source_count <= article_count` CHECK 제약을 추가하여 DB 레벨 계약을 강화했습니다.
- **FIX-08**: `weekly_topic_articles` 테이블에 `(weekly_topic_id, rank)` UNIQUE 제약 및 대표 기사의 Summary 근거 포함 의무화 CHECK 제약을 강화했습니다.
- **FIX-09**: `weekly_topics.status`에 `status in ('draft', 'ready', 'failed')` CHECK를 적용하고, 서비스 저장 상태(`ready`)와 홈 API 간의 공개 계약을 일치시켰습니다.
- **FIX-10**: task 문서의 오타(`시용` -> `표시용`) 정리와 타 문서들의 날짜 범위 표현을 정비했습니다.
- **FIX-11**: CronJob YAML에 `automountServiceAccountToken: false`를 적용하고 관련 manifest 유효성 테스트를 보강했습니다.
- **FIX-12**: `similarity` 범위 CHECK(`-1 <= similarity <= 1`) 및 `finished_at >= started_at` 시간 관계 CHECK 등을 마이그레이션과 모델에 각각 추가 반영했습니다.

### Verification Evidence
- **추가 검증 내역**: [docs/verification/feature-seven-day-topic-pipeline.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/verification/feature-seven-day-topic-pipeline.md)에 12개 Approved Fixes를 추가 적용한 후 실행한 모든 테스트 로그가 온전히 업데이트되었습니다.
- **테스트 통과**: 407개 테스트 전체 패스, compileall 성공 및 whitespace 검증(`git diff --check`) 통과가 입증되었습니다.

### New Problems Found
- 없음 (None)

### Required Fixes Before PR
- 없음 (None)

### Verdict
PASS
