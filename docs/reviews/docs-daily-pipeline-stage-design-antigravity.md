# Antigravity Review: Daily topic pipeline 내부 단계 분리

## Review Summary

본 변경 사항은 `docs/daily-pipeline-stage-design` 브랜치에 대응하여 `scripts/run_daily_topic_pipeline.py`에 강하게 결합되어 있던 뉴스 처리 파이프라인 흐름을 단일 책임 원칙(SRP)에 맞춰 4단계로 리팩토링하고, 기존 선행 추출 방식의 `news-raw-extractor` 크론잡을 제거하여 운영 효율성을 제고하기 위해 수행되었습니다.

- **파이프라인 단계 분리**: 임베딩 준비(`prepare_article_embeddings`), 클러스터링 및 토픽 선정(`cluster_and_select_topics`), 선택 기사 원문 확보(`acquire_selected_article_raw_texts`), 토픽 요약 생성 및 저장(`summarize_and_save_topics`) 단계로 안전하게 격리되었습니다.
- **날짜 정합성 보완**: 파이프라인 진입 시점에 `Asia/Seoul` 시간대 기준 공통 `pipeline_date`를 한 번 결정하여 데이터 삽입 및 파생 시점의 날짜 모호성을 해결하였습니다.
- **크론잡 최적화**: 기존 03:30 추출 스케줄을 제거하고 토픽으로 선정된 기사들만 필요한 시점에 한정해 원문을 확보하도록 개선하여 API 비용 및 데이터 처리를 크게 단축시켰습니다.

설계적 관심사의 분리와 운영 최적화가 유기적으로 적용된 탁월한 변경 사항입니다.

## Requirement Coverage

[docs/tasks/docs-daily-pipeline-stage-design.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/tasks/docs-daily-pipeline-stage-design.md) 요구사항을 완벽히 정합성 있게 충족하고 있습니다.

- **단계 분리 및 인터페이스 획정**:
  - 각 단계의 입력과 출력을 정의한 결과 타입(`EmbeddingStageResult`, `TopicSelectionResult`, `RawAcquisitionResult`, `TopicSaveResult`)이 구현되었습니다.
- **선택 기사 원문 추출 가이드라인**:
  - 전체 기사가 아닌 토픽에 포함된 selected article에 대해서만 `raw_articles` 유무에 따라 조건부 추출을 수행하도록 원문 수집 단계가 변경되었습니다.
- **공통 날짜 주입**:
  - `resolve_pipeline_context()` 함수를 구현하여 UTC 경계와 상관없이 파이프라인 전체 프로세스가 동일한 `pipeline_date`를 공유합니다.
- **크론잡 제거 범위**:
  - `k8s/news-raw-extractor-cronjob.yaml` 파일이 정확히 삭제되었으며, 관련 스케줄 검증 테스트 스펙 및 아키텍처/런북 설명이 안전하게 제거/갱신되었습니다.

## Code Quality / Maintainability

- **가독성 및 모듈화**: 스크립트 전반에 걸쳐 결합되어 있던 복잡한 처리 연산들이 단계별 함수 단위로 파편화되지 않고 명확하게 그룹핑되어 가독성이 높아졌습니다.
- **주석 품질**: 코드 자체를 해석하는 불필요한 노이즈 주석을 추가하지 않고, 비즈니스 흐름과 단계 간 결합 조건을 명시하는 정갈한 주석들이 작성되었습니다.
- **단위 테스트 정상화**: [tests/test_run_daily_topic_pipeline.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/tests/test_run_daily_topic_pipeline.py)에 단계별 격리 실행 테스트 및 수집 예외 케이스 4종이 보강되었으며, 전체 150건의 단위 테스트가 회귀 에러 없이 통과됨을 재검토하였습니다.

## Security Review

- **인증 정보 노출 없음**: 소스코드에 데이터베이스 커넥션 설정이나 OpenAI 토큰, 크레덴셜이 노출되지 않았고 로깅 시에도 민감정보가 완벽히 필터링되고 있습니다.

## Operational Risk

- **비용 최적화**: 03:30 선추출 크론잡이 제거됨에 따라 불필요하게 모든 유입 기사의 원문을 가져오던 리소스 낭비가 해결되었으며, 실제 토픽화된 기사(selected articles)들만 지연 추출하므로 효율적입니다.
- **동작 가드 유지**: 정상 기사 임베딩 수가 2건 미만이면 클러스터링을 건너뛰는 안전 조치 및 토픽 요약 생성의 격리 정책이 정상 보존되었습니다.

## Scope Control

- **변경 파일 제약 준수**: 03:30 크론잡 매니페스트 삭제를 제외하고는, 변경 금지 영역인 `db/migrations/`, `app/routers/`, `app/main.py`, `requirements.txt`에 수정이 발생하지 않았음을 확인하였습니다.

## Verification Review

- **검증 실질 수행**: [docs/verification/docs-daily-pipeline-stage-design.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/verification/docs-daily-pipeline-stage-design.md) 파일에 전체 테스트 통과 여부 및 정적 컴파일 실행 기록, 매니페스트 부재 체크 등에 대한 구체적인 명령어 증적이 성실히 기재되어 있습니다. 

## Documentation Review

- **문서 동기화 완결성**: [docs/ARCHITECTURE.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/ARCHITECTURE.md), [docs/architecture/k3s-runtime.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/architecture/k3s-runtime.md), [docs/architecture/pipeline.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/architecture/pipeline.md) 및 [docs/runbooks/cronjobs.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/runbooks/cronjobs.md) 문서에서 기존 03:30 스케줄을 제거하고 04:00 파이프라인에서 지연 원문 추출이 수행된다는 내용으로 설명이 일관성 있게 수정되었습니다.

## Problems Found

- **결함 사항 없음**: 정적 분석 및 컴파일, 150건의 단위 테스트 재검토를 총체적으로 진행했을 때 중대한 결함이나 모순은 발견되지 않았습니다.

## Required Fixes Before PR

- **해당 사항 없음** (PR 병합을 진행하기 위해 수정되어야 할 블로커 오류는 없습니다).

## Optional Improvements

- **단계별 로깅 상세화**: 대규모 배치 처리 시 각 단계별(예: 1단계 종료 후 2단계 진입 전) 메모리 점유 및 처리 경과 시간을 마일스톤 로그 형태로 상세히 노출해주면 향후 프로덕션 모니터링 시 문제의 단계를 즉시 진단하는 데 큰 도움이 될 것입니다.

## Suggested Test Commands

본 브랜치의 검증 동작을 다시 확인하려면 아래의 읽기 전용 커맨드들을 검토해 볼 수 있습니다:

1. **정적 분석 및 전체 단위 테스트 실행**:
   ```bash
   python -m compileall app scripts tests && python -m unittest discover -s tests
   ```
2. **배포 매니페스트 부재 및 스케줄 재확인**:
   ```bash
   python -m unittest tests.test_daily_topic_pipeline_cronjob_manifest
   ```
3. **변경 포맷 정합성 확인**:
   ```bash
   git diff --check
   ```

## Verdict

- **APPROVED**
  - 본 변경 사항은 `Acceptance Criteria`를 완벽히 만족하며, 일관성 있는 리팩토링과 문서 동기화가 성실히 이루어졌으므로 PR 제출 및 병합 절차를 추진하기에 완벽히 적절합니다.

## Re-review 1
### Existing Problems Status

- **기존 문제 1**: 해당 사항 없음. (최초 Review 시점에서 검출된 blocker 결함이 없었습니다.)
- **상태**: 해결됨 / 해당 없음

### Approved Fixes Verification

[approved-fixes.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/fixes/docs-daily-pipeline-stage-design-approved-fixes.md)에 명시된 6가지 승인된 수정(Approved Fixes) 사항의 이행 여부를 정합성 있게 대조 및 검증하였습니다:

1. **Daily topic pipeline을 역할별 패키지로 분리 (이행 완료)**:
   - 기존에 한 파일에 섞여 있던 책임들이 [embedding_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/embedding_stage.py), [topic_selection_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/topic_selection_stage.py), [raw_acquisition_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/raw_acquisition_stage.py), [summary_persistence_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/summary_persistence_stage.py) 모듈들로 성공적으로 리팩토링 및 이관되었습니다.
2. **실행 진입점의 책임 축소 (이행 완료)**:
   - [run_daily_topic_pipeline.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/scripts/run_daily_topic_pipeline.py) 파일은 파라미터 유효성 검사, 실행 context 초기화, 단계별 함수 호출 및 통계 결합 등의 조정자 역할에 집중하도록 대폭 정리되었습니다.
3. **단계별 결과 타입 분리 (이행 완료)**:
   - 각 단계간의 인터페이스 계약을 표현하는 결과 객체들(`PipelineContext`, `EmbeddingStageResult`, `TopicSelectionResult`, `RawAcquisitionResult`, `TopicSaveResult`)이 [models.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/models.py) 파일로 통합 정의되어 단방향 흐름이 보다 투명해졌습니다.
4. **파일 크기 제한 적용 (이행 완료)**:
   - 진입점 스크립트인 [run_daily_topic_pipeline.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/scripts/run_daily_topic_pipeline.py)가 381줄로 경량화되었고, 서비스 모듈 중 가장 용량이 큰 [topic_selection_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/topic_selection_stage.py)가 182줄로, 500줄 제약 조건을 안정적으로 준수합니다.
5. **기존 동작과 계약 유지 (이행 완료)**:
   - 단위 테스트(35개)와 회귀 테스트(150개)를 모두 구동한 결과, 기사 및 임베딩 준비, clustering, selected article 원문 확보 및 추출 격리 정책, 토픽별 요약 생성 및 저장에 있어 기존 비즈니스 규칙이 안전하게 유지되고 있음을 검증했습니다.
6. **Import 및 의존성 구조 검증 (이행 완료)**:
   - Stage 상위/하위 모듈 간의 순환 참조가 제거되었고, 모듈 로딩 시점에서의 무단 DB 연결이나 OpenAI API 등 외부 provider 호출이 차단되어 사이드 이펙트가 방지되었습니다.

### Verification Evidence

실제 동작 검증 및 환경 검토는 [verification.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/verification/docs-daily-pipeline-stage-design.md)의 증적 및 로컬 실행 기록을 토대로 하였습니다:

- **단위 테스트 실행**:
  - `python -m unittest tests.test_run_daily_topic_pipeline tests.test_article_embedding_storage tests.test_daily_topic_pipeline_cronjob_manifest` -> 35개 테스트 전수 통과
- **전체 회귀 테스트**:
  - `python -m compileall app scripts tests && python -m unittest discover -s tests` -> 150개 테스트 에러 없이 통과
- **정적 포맷 및 금지 구역**:
  - `git diff --check` -> 공백 에러 없음
  - `git diff -- db/migrations app/routers app/main.py requirements.txt` -> 금지된 영역 변경 사항 부재
- **파일 용량 측정**:
  - `wc -l scripts/run_daily_topic_pipeline.py app/services/daily_topic_pipeline/*.py` -> 모든 파일 500줄 이하 충족

### New Problems Found

- **결함 사항 없음**: 변경 사항 분석 및 단위 테스트 회귀 검증을 마친 결과, 리팩토링 단계에서 유입된 새로운 설계 오류나 scope creep은 식별되지 않았습니다.

### Required Fixes Before PR

- **해당 사항 없음** (병합에 방해가 되는 블로커 요인이 존재하지 않습니다.)

### Verdict

- **APPROVED**
  - 승인된 6가지 Fix 가이드라인에 입각하여 역할 분리 패키지 구조가 정교하게 구현되었으며, 150건의 전체 단위 테스트 및 변경 금지 영역 보존 계약을 모두 우수하게 통과하였기에 최종 APPROVED 판정을 내립니다.

## Re-review 2
### Existing Problems Status

- **기존 문제 1**: 해당 사항 없음. (이전 Review 및 Re-review 1 시점에서 검출된 blocker 결함이 없었습니다.)
- **상태**: 해결됨 / 해당 없음

### Approved Fixes Verification

[approved-fixes.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/fixes/docs-daily-pipeline-stage-design-approved-fixes.md)에 명시된 6가지 승인된 수정(Approved Fixes) 사항의 이행 상태가 완벽하게 유지되고 있음을 재확인했습니다:

1. **Daily topic pipeline을 역할별 패키지로 분리 (이행 완료)**:
   - 각 단계별 구현이 [embedding_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/embedding_stage.py), [topic_selection_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/topic_selection_stage.py), [raw_acquisition_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/raw_acquisition_stage.py), [summary_persistence_stage.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/summary_persistence_stage.py)에 깔끔하게 유지되고 있습니다.
2. **실행 진입점의 책임 축소 (이행 완료)**:
   - [run_daily_topic_pipeline.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/scripts/run_daily_topic_pipeline.py)가 단순 조율자 역할을 충실히 수행하고 있습니다.
3. **단계별 결과 타입 분리 (이행 완료)**:
   - 각 단계의 입력/결과 인터페이스 타입들이 [models.py](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/services/daily_topic_pipeline/models.py)에 분리 정의되어 결합도가 낮게 제어됩니다.
4. **파일 크기 제한 적용 (이행 완료)**:
   - 모든 관련 Python 소스 파일들의 줄 수가 500줄 이하 정책을 만족하고 있습니다.
5. **기존 동작과 계약 유지 (이행 완료)**:
   - 단위 테스트(35개) 및 회귀 테스트(150개)를 재구동하여 임베딩 재사용, selected article 지연 추출, summary 실패 격리, 공통 날짜 적용 등의 비즈니스 로직이 안전하게 보존됨을 재차 증명했습니다.
6. **Import 및 의존성 구조 검증 (이행 완료)**:
   - 순환 참조(circular import) 및 모듈 로드 시의 사이드 이펙트가 여전히 존재하지 않습니다.

### Verification Evidence

실제 동작 검증 및 환경 검토는 [verification.md](file:///Users/seochanjin/workspace/NewsLab/news-lab/docs/verification/docs-daily-pipeline-stage-design.md)의 증적 및 로컬 실행 기록을 토대로 하였습니다:

- **단위 테스트 실행**:
  - `python -m unittest tests.test_run_daily_topic_pipeline tests.test_article_embedding_storage tests.test_daily_topic_pipeline_cronjob_manifest` -> 35개 테스트 전수 통과
- **전체 회귀 테스트**:
  - `python -m compileall app scripts tests && python -m unittest discover -s tests` -> 150개 테스트 에러 없이 통과
- **정적 포맷 및 금지 구역**:
  - `git diff --check` -> 공백 에러 없음
  - `git diff -- db/migrations app/routers app/main.py requirements.txt` -> 금지된 영역 변경 사항 없음
- **파일 용량 측정**:
  - `wc -l scripts/run_daily_topic_pipeline.py app/services/daily_topic_pipeline/*.py` -> 모든 파일 500줄 이하 충족

### New Problems Found

- **결함 사항 없음**: 변경 사항 분석 및 단위 테스트 회귀 검증을 마친 결과, 새로 유입된 설계 오류나 scope creep은 식별되지 않았습니다.

### Required Fixes Before PR

- **해당 사항 없음** (병합에 방해가 되는 블로커 요인이 존재하지 않습니다.)

### Verdict

- **APPROVED**
  - 모든 요구사항 및 승인된 수정 가이드라인이 철저하게 충족되었으며, 150건의 단위 테스트 전체가 완벽히 성공하였기에 최종 APPROVED 판정을 유지합니다.



