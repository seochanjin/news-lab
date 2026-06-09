# Antigravity Review: URL 정규화와 중복 후보 분석 MVP

## Review Summary

본 리뷰는 `feature/url-normalization-duplicates` 브랜치에 구현된 URL 정규화 규칙 및 중복 후보 분석 MVP 기능에 대한 검증 결과입니다. 이번 차수에서는 수집된 RSS 기사 메타데이터의 중복을 분석하기 위해 결정론적(deterministic) 룰 기반의 URL/제목 정규화 도구([app/utils/url_normalization.py](~/news-lab/app/utils/url_normalization.py))와 데이터베이스 조회용 읽기 전용 분석 스크립트([scripts/analyze_article_duplicates.py](~/news-lab/scripts/analyze_article_duplicates.py))가 정상적으로 설계 및 구현되었습니다. 비파괴적이고 안전한 아키텍처 원칙을 준수하며, 운영 영향도가 전혀 없는 상태로 검증이 완료되었습니다.

## Requirement Coverage

[docs/tasks/feature-url-normalization-duplicates.md](~/news-lab/docs/tasks/feature-url-normalization-duplicates.md)에 기술된 모든 요구사항이 성공적으로 반영되었습니다.

- **URL 정규화 및 트래킹 파라미터 제거**: `utm_*`, `fbclid`, `gclid`, `at_medium`, `at_campaign`, `traffic_source` 등의 공통 파라미터와 특정 언론사 도메인(BBC, DW, Wired 등) 전용 파라미터가 정상적으로 필터링됩니다.
- **제목 정규화 및 해시 기능**: NFKC 유니코드 정규화, 소문자화, 구두점 및 공백 제거 후 SHA-256 해시를 산출하는 `make_title_hash`가 추가되었습니다.
- **시간대별/기준별 분석 옵션**: `--window-hours` (24h, 72h, 168h) 및 `--all` 플래그가 지원되며, `--time-basis` 옵션으로 발행 시각(`coalesce(published_at, created_at)`) 및 수집 시각(`created_at`)을 구분하여 분석할 수 있습니다.
- **결과 출력 및 기록**: 정규화된 URL 혹은 제목 해시를 기준으로 중복 후보 기사들을 집계하여 JSON으로 출력하며, 분석 결과가 검증 문서([docs/verification/feature-url-normalization-duplicates.md](~/news-lab/docs/verification/feature-url-normalization-duplicates.md)) 및 작업 로그([docs/devlog/feature-url-normalization-duplicates.md](~/news-lab/docs/devlog/feature-url-normalization-duplicates.md))에 누락 없이 기록되었습니다.

## Code Quality / Maintainability

- **안전한 모듈 설계**: Python 표준 라이브러리(`urllib.parse`, `hashlib`, `unicodedata`)를 적극 활용하여 외부 종속성을 줄였습니다.
- **정교한 예외 처리**: `urlsplit` 파싱 과정에서 발생할 수 있는 `ValueError`를 적절하게 캐치하고 비정상적인 URL에 대해 `None`을 안전하게 반환합니다.
- **테스트 커버리지**: URL/제목 정규화 기능에 대한 풍부한 케이스와 스크립트의 분석 로직 검증을 위한 모의 객체 테스트가 작성되어 신뢰성이 높습니다.
- **코드 스타일**: SQLAlchemy의 `text()` 함수를 이용한 바인드 매개변수 처리가 가독성 있게 구조화되었습니다.

## Security Review

- **SQL Injection 방지**: 스크립트 작성 시 사용자가 입력한 값(`window_hours`)은 bind parameter (`:window_hours`) 형식으로 처리되어 SQL Injection 위험을 완전히 차단했습니다. 동적으로 주입되는 시간 기준 칼럼명은 내부 지정 상숫값(`coalesce(published_at, created_at)` 또는 `created_at`)으로만 제한되어 안전합니다.
- **자격 증명 유출 여부**: `.env` 파일이나 DB 패스워드 등의 자격 증명이 소스 코드 내에 하드코딩되지 않았으며, `dotenv`를 통해 주입받도록 안전하게 구현되었습니다.
- **최소 권한 원칙**: DB 커넥션 획득 직후 `set transaction read only`를 명시적으로 실행하여 오작동으로 인한 데이터 변경을 원천적으로 차단했습니다.

## Operational Risk

- **실제 영향도**: 제로(0).
- DB 스키마 마이그레이션(DDL) 및 데이터 수정(DML) 작업을 수행하지 않으며, API 라우터나 기존 수집/추출 크론잡의 작동 로직을 전혀 변경하지 않는 순수 분석용 스크립트이기 때문에 운영 중인 시스템에 부정적인 영향을 미칠 가능성이 없습니다.

## Scope Control

- **요구사항 준수**: LLM, 임베딩, 토픽 그룹화, 요약 생성 등 아웃오브스콥 항목들이 완벽히 제외되었습니다.
- **변경 파일 제어**: 요구사항에 명시된 파일 이외의 인프라 설정(Kubernetes Manifests 등)이나 다른 비즈니스 로직 소스 코드는 전혀 수정되지 않고 범위가 잘 제어되었습니다.

## Verification Review

- 검증 문서([docs/verification/feature-url-normalization-duplicates.md](~/news-lab/docs/verification/feature-url-normalization-duplicates.md))에 기록된 내용에 따르면, 단위 테스트 9개 통과 및 컴파일 에러 없음이 확인되었습니다.
- 네트워크 접근 승인 하에 실행된 DB 분석 결과(최근 수집/발행된 180~376건의 기사 분석)가 구체적인 기사 카운트와 함께 기록되어 검증 투명성이 확보되었습니다.

## Documentation Review

- PR draft와 Devlog draft가 검증 기록([docs/verification/feature-url-normalization-duplicates.md](~/news-lab/docs/verification/feature-url-normalization-duplicates.md))의 사실관계를 정확히 참조하고 있습니다.
- 향후 차수에서 도입할 데이터베이스 스키마(예: `normalized_url`, `title_hash` 추가 여부) 및 고유 인덱스 설계 방향성이 `devlog` 내에 체계적으로 문서화되었습니다.

## Problems Found

- 발견된 특이사항이나 치명적인 버그가 없습니다.

## Required Fixes Before PR

- 없음.

## Optional Improvements

- **대용량 데이터 대비 오프셋/배치 처리**: 현재 분석 스크립트는 매치되는 모든 기사를 메모리에 한 번에 올리는 구조(`mappings().all()`)를 취하고 있습니다. 현재 DB 크기(~376건)에서는 문제가 없으나, 기사가 수만 건 이상으로 증가할 경우 메모리 부족 위험이 발생할 수 있습니다. 향후에는 대용량 분석을 위해 청크(chunk) 단위 조회를 고려해 볼 수 있습니다.

## Suggested Test Commands

PR 제출 전 로컬 환경에서 다음과 같은 명령어로 동작 및 빌드 상태를 재확인할 수 있습니다.

```bash
# 단위 테스트 전체 검증
.venv/bin/python -m unittest discover -s tests -v

# 구문 분석 및 컴파일 검증
.venv/bin/python -m py_compile app/utils/url_normalization.py scripts/analyze_article_duplicates.py

# 최근 72시간 기준 발행 시각 중복 분석 dry-run 실행
.venv/bin/python scripts/analyze_article_duplicates.py --window-hours 72 --max-groups 5
```

## Verdict

- **PASS**: 모든 인수 조건(Acceptance Criteria)을 만족하며, 구조가 깔끔하고 운영 안전성이 확보되어 풀 리퀘스트 생성 단계로 진행할 것을 권장합니다.
