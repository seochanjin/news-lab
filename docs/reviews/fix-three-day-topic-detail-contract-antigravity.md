# Antigravity Review: 3일 Topic 상세 API key_points 응답 계약 수정

## Review Summary
본 작업은 3일 Topic 상세 API(`GET /three-day-topics/{topic_id}`) 응답에서 `key_points` 필드가 누락되는 결함을 해결하는 건입니다. 변경 사항은 API 라우터의 SQL SELECT 쿼리 수정 및 데이터 응답 정규화(`NULL` 또는 빈 배열에 대해 `[]` 반환), 그리고 관련 API contract test 보강으로 제한됩니다. Task 요구사항 및 지침을 철저하게 준수하고 있으며, 결함이나 위험 요인은 발견되지 않았으므로 최종 Verdict는 `PASS`입니다.

## Requirement Coverage
- **상세 API 응답 필드 추가**: `GET /three-day-topics/{topic_id}` 상세 응답 시 `key_points` 필드가 항상 포함됩니다.
- **타입 및 정규화 계약**: 응답 타입은 `list[str]`이며, DB 상의 값이 `NULL`이거나 빈 배열인 경우 모두 빈 배열 `[]`을 반환하도록 `topic.get("key_points") or []` 정규화 처리가 적용되었습니다.
- **순서 유지**: DB에 저장된 핵심 포인트 배열의 순서가 변경 없이 그대로 응답에 반영됩니다.
- **기존 필드 유지**: 기존 상세 응답 필드들과 `articles` 배열 구조, 정렬 로직 등은 모두 안전하게 보존되었습니다.

## Code Quality / Maintainability
- **최소 범위 수정**: 별도의 대규모 리팩터링 없이 문제 원인이 되었던 라우터와 테스트 케이스만 정밀하게 수정되었습니다.
- **한글 Docstring 규칙 준수**: 
  - `app/routers/three_day_topics.py` 내의 [get_three_day_topic](file:///Users/seochanjin/workspace/NewsLab/news-lab/app/routers/three_day_topics.py#L142-L146)
  - `tests/test_three_day_topics_api.py` 내의 [detail_topic_row](file:///Users/seochanjin/workspace/NewsLab/news-lab/tests/test_three_day_topics_api.py#L117-L121) 및 신규 테스트 메서드들
  - 위 대상들에 대해 실제 역할과 검증 목적을 설명하는 한글 docstring이 정상적으로 기술되었습니다.

## Security Review
- **SQL Injection 방지**: Raw query 수행 시 SQLAlchemy의 `text()`와 bind parameter (`:topic_id`)를 올바르게 사용하여 취약점을 방지했습니다.
- **민감 정보 노출 없음**: `.env` 파일, DB credential, API token 등 민감 키의 유출이나 변경 이력은 전혀 감지되지 않았습니다.

## Operational Risk
- **DB Schema 미변경**: `three_day_topics` DB schema나 migration 파일의 추가/변경이 없으므로 운영 DB에 미치는 리스크가 없습니다.
- **Pipeline 안정성**: 3일 Topic 생성/저장 pipeline을 변경하지 않았으므로 수집/분석 주기 작동에 주는 영향이 없습니다.

## Scope Control
- **금지 파일 변경 없음**: `k8s/` manifest, `Dockerfile`, `.github` actions, `requirements.txt` 등 어떠한 인프라 및 종속성 관련 파일도 변경되지 않았습니다.
- **기타 API 보호**: Daily 및 Weekly Topic API/pipeline과의 상호 간섭이 없으며, 3일 Topic 목록/홈 API 계약도 기존 상태를 완벽히 유지하고 있습니다.

## Verification Review
- **정직한 결과 기록**: `docs/verification/fix-three-day-topic-detail-contract.md`에 실제 실행한 명령과 그 결과가 매우 투명하게 기록되었습니다. (예: `app/schemas` 경로 부재로 인한 grep 실패 건도 정직하게 실패로 기재됨)
- **로컬 검증 통과**: 전체 pytest(409 passed), unittest(409 passed), python compileall 검증이 정상적으로 통과되었습니다.
- **운영 검증 보류**: 실제 운영 환경 배포/검증(K3s rollout, production DB 직접 수정 등)은 수행하지 않고 미수행/사람 수행 필요 상태로 안전하게 보류하였습니다.

## Documentation Review
- **Source of Truth 일치**: Task 및 Verification 문서에 UNIT-01, UNIT-02, UNIT-03의 완료 상황과 검증 결과가 상세히 추적되어 기록되었습니다.
- **PR 및 Devlog 일치**: 작성 예정인 PR draft 및 devlog 문서 또한 현재의 변경 범위와 완벽히 정합합니다.

## Problems Found
- 없음.

## Required Fixes Before PR
- 없음.

## Optional Improvements
- 없음.

## Suggested Test Commands
본 변경 사항을 로컬 환경에서 다시 한 번 독립적으로 검증하기 위해 다음의 테스트 명령어를 권장합니다.

```bash
# 3일 Topic API 집중 테스트
python -m pytest tests/test_three_day_topics_api.py -v

# 3일 Topic 회귀 테스트
python -m pytest \
  tests/test_run_three_day_topic_pipeline.py \
  tests/test_three_day_topic_pipeline.py \
  tests/test_three_day_topics_api.py \
  tests/test_three_day_topic_pipeline_cronjob_manifest.py \
  -v

# 전체 pytest 회귀 테스트
python -m pytest
```

## Verdict
PASS
