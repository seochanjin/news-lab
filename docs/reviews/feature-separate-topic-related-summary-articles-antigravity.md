# Antigravity Review: Topic 관련 기사 보존과 Summary 근거 기사 분리

## Review Summary

본 작업은 Daily topic pipeline에서 기존에 저장 대상 기사 수와 요약 생성용 원문 확보 기사 수를 동시에 제한하던 `max_articles_per_topic` 설정을 다음 두 가지 역할로 분리하는 기능 개선을 다룹니다.

- **Topic 관련 기사**: Topic 관계를 보존해 `topic_articles`에 저장할 기사 집합 (Daily 기본값 20건)
- **Summary 근거 기사**: 원문 확보 및 Summary 생성의 입력에 활용할 기사 집합 (Daily 기본값 3건)

구현 코드 분석 결과, 설정 분리, 단계별 결과 모델 분리, 결정론적 기사 및 대표 기사 선정, 원문 확보/Summary 입력 분리, 그리고 관련 기사 전체 저장 등의 요구사항이 API 및 DB 스키마 회귀 없이 안전하게 설계 및 작성되었습니다. 로컬 검증에서 201개의 모든 테스트가 통과하였으며 변경 금지 영역에 대한 수정이 없음을 확인했습니다.

## Requirement Coverage

- **설정 분리**: `max_related_articles_per_topic` (기본값 20) 및 `max_summary_articles_per_topic` (기본값 3) 설정이 분리되었습니다. 초기 CLI 인자 파싱 단계에서 `1 <= max_summary_articles_per_topic <= max_related_articles_per_topic` 조건이 안전하게 검증됩니다.
- **기존 인자 호환성**: `--max-articles-per-topic`은 deprecated alias로 남아 단독 사용 시 두 상한에 동일 값을 적용하도록 설계되었고, 신규 옵션과 혼용 시 에러를 유발해 안정성을 높였습니다.
- **단계 결과 모델 분리**: `TopicSelectionResult` 데이터 클래스 내에 `related_article_ids` 및 `summary_article_ids`가 각각 분리되어 정의되었습니다. `__post_init__` 검증 로직을 통해 `summary_articles ⊆ related_articles` 와 `representative_articles ⊆ summary_articles` 관계가 데이터 모델 레이어에서 강제됩니다.
- **기사 집합 선정 로직**: Topic 대표 기사를 최우선 보존하며, 중복 URL 및 normalized title을 결정론적으로 제외하고 source 다양성을 극대화하도록 `_summary_article_ids_for_topic`이 올바르게 설계되었습니다.
- **원문 확보 및 요약 입력 제한**: Raw acquisition 및 Summary 생성 단계에서 관련 기사 전체 대신 `summary_article_ids`에 해당하는 기사 목록만 남긴 복사본(`_summary_article_topics`)을 넘겨, 요약에 쓰이지 않는 관련 기사로 인한 불필요한 원문 추출과 summary provider 입력을 확실하게 차단합니다.
- **관련 기사 전체 저장**: 최종 저장 계획 빌드 시 `_apply_related_articles`를 주입하여, 요약 생성에 성공한 Topic에 대해서는 대표 기사(`representative`) 및 서브 기사(`supporting`) 관계를 유지하면서 관련 기사 전체를 `topic_articles`에 맵핑해 저장하도록 구현되었습니다.
- **통계 수치 분리**: 통계 및 Markdown 보고서에 관련 기사 수, Summary 근거 기사 수, 원문 확보 대상 수 및 저장된 `topic_articles` 수 등이 상세하게 분리 반영되었습니다.
- **API 스키마 및 회귀**: API의 endpoint나 response schema는 보존되었으나, 집계 및 기사 목록이 관련 기사 전체를 반영하도록 수정되었으며 `tests/test_topics_api.py`를 통해 구조적 계약이 깨지지 않음을 완벽히 확인했습니다.

## Code Quality / Maintainability

- **한글 Docstring 원칙 준수**: 새로 생성되거나 수정한 모든 Python 모듈, 클래스, 함수, 그리고 신규 테스트 클래스와 함수에 한글 docstring이 누락 없이 작성되어, 각 구성 요소의 역할과 검증 목적을 명확히 파악할 수 있습니다.
- **비즈니스 로직 결합성**: 데이터 모델 단에서의 집합 제약 검증(`TopicSelectionResult.__post_init__`)과 CLI 파싱 제약 검증이 체계적으로 분리되어 코드 품질과 가독성이 훌륭합니다.

## Security Review

- pipeline 실행 시 환경 변수 노출이나 민감 정보 로깅 패턴이 발생하지 않습니다.
- K3s manifest(`news-daily-topic-pipeline-cronjob.yaml`)의 command 인수만 안전하게 수정되었으며, 기존의 최소 권한 pod securityContext 및 Secret 참조 패턴을 그대로 유지하고 있습니다.

## Operational Risk

- API endpoint 경로, response schema, DB table 스키마 및 migration이 없으므로 운영 환경에서의 API/DB 관련 장애 요인이 전혀 없습니다.
- deprecated alias 지원 정책을 통해 일시적인 manifest 불일치 시에도 안정적인 실행을 지원합니다.

## Scope Control

- `db/migrations/`, `app/routers/`, `app/main.py` 등 명시된 변경 금지 영역에 대한 수정이 전혀 없습니다.
- pgvector, ANN 검색 튜닝, clustering 알고리즘 변경 등 scope 외의 부가적인 refactoring이나 기능 추가(Scope Creep)가 철저히 통제되었습니다.

## Verification Review

- `docs/verification/feature-separate-topic-related-summary-articles.md` 문서에는 UNIT-01부터 UNIT-04까지의 테스트 명령어, 컴파일 검증, 변경 금지 영역 diff 체크, 그리고 정합성 검토 결과가 객체 지향적인 검증 기포에 입각하여 상세히 작성되어 있습니다.
- Antigravity가 로컬 workspace에서 `pytest`, `unittest`, `compileall`, `git diff --check` 명령어를 통해 재검증한 결과, **201건의 테스트 케이스가 전부 성공**하였으며 정적 에러나 syntax 에러가 없음이 실증적으로 증명되었습니다.
- Kubernetes apply 및 production 서비스 확인 등은 사람이 직접 수행해야 할 항목으로 분류되어 안전하게 이관되었습니다.

## Documentation Review

- `docs/architecture/backend-api.md`, `docs/architecture/pipeline.md`, `docs/runbooks/cronjobs.md` 가 수정된 비즈니스 사양에 맞추어 정확하게 업데이트되었으며, 실제 CLI 파라미터 분리에 맞게 실행 예시가 동기화되었습니다.

## Problems Found

- 발견된 결함이나 문제점이 없습니다.

## Required Fixes Before PR

- [ ] 없음 (문제가 발견되지 않았습니다)

## Optional Improvements

- 없음 (현재 구현 및 테스트 구성이 요구사항 대비 충분히 깔끔하고 효율적입니다)

## Suggested Test Commands

로컬 개발 환경에서 회귀 여부를 재검증할 때 아래 명령어들을 권장합니다.

```bash
# 전체 테스트 실행
python -m pytest

# unittest 호환 테스트 실행
python -m unittest discover -s tests

# 정적 컴파일 분석
python -m compileall app scripts tests

# 변경 금지 영역 수정 여부 및 포맷팅 검증
git diff --check
git diff -- db/migrations app/routers app/main.py
```

## Verdict

**APPROVED**

(모든 수용 조건(Acceptance Criteria)을 완전하게 충족하며, 코드 수준의 방어적 validation 및 테스트 구성이 뛰어나고, 변경 금지 영역과 하위 호환성 역시 철저히 준수되어 추가적인 수정 없이 PR 진행을 승인합니다.)

## Re-review 1

### Existing Problems Status

- **최초 리뷰 발견 문제**: 최초 리뷰(Initial Review) 시 발견된 결함이나 PR 블로커 수준의 문제가 없었으므로, 해당 사항이 없습니다. (**적용 대상 아님**)

### Approved Fixes Verification

- **중복 비교 로직 분리 및 대소문자 보존 (Approved Fix #1)**: [docs/fixes/feature-separate-topic-related-summary-articles-approved-fixes.md](../docs/fixes/feature-separate-topic-related-summary-articles-approved-fixes.md)에 승인된 피드백이 완벽히 반영되었습니다.
  - `topic_selection_stage.py` 내의 `_normalize_duplicate_value` 함수가 `_normalize_duplicate_url` 및 `_normalize_duplicate_title`로 분리되었습니다.
  - URL 정규화는 `strip()`만 적용해 path와 query의 대소문자를 정상 보존하며, 제목 정규화는 기존의 공백 정규화 및 `casefold()` 방식을 유지합니다.
  - `test_daily_topic_article_selection.py`에 path와 query의 대소문자가 다른 URL을 가진 기사가 중복으로 제외되지 않고 개별 Summary 기사로 유지되는지 확인하는 `test_summary_selection_preserves_case_sensitive_url_path_and_query` 테스트 케이스가 성공적으로 추가되었습니다.
  - 판정: **해결됨**

### Verification Evidence

- [docs/verification/feature-separate-topic-related-summary-articles.md](../docs/verification/feature-separate-topic-related-summary-articles.md)에 승인된 Fix에 대한 단위 테스트 및 전체 회귀 테스트 검증 내역이 정상적으로 기록되었습니다.
- Antigravity가 로컬 환경에서 직접 테스트들을 수행하여 신규 테스트를 포함한 202건의 테스트가 모두 성공적으로 작동함을 재검증했습니다.
  - `pytest`: 202 passed
  - `unittest`: Ran 202 tests OK
  - `compileall`: exit code 0
  - `git diff --check`: exit code 0
  - 변경 금지 영역(`db/migrations`, `app/routers`, `app/main.py`): 변경 사항 없음

### New Problems Found

- **없음**: 새로 수정한 소스 코드와 신규 추가된 테스트 메서드 모두 한글 docstring 규칙을 명확히 준수하고 있으며, 추가적인 결함이나 scope creep이 발견되지 않았습니다.

### Required Fixes Before PR

- **없음**

### Verdict

**APPROVED**

(승인된 피드백 사항이 실질적으로 반영되었고 이에 대한 회귀 테스트 및 검증 증적이 명확하게 확보되어 정상적으로 승인합니다.)
