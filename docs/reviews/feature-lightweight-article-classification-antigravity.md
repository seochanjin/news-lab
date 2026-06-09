# Antigravity Review: Lightweight article classification MVP

## Review Summary

본 리뷰는 `feature/lightweight-article-classification` 브랜치에 구현된 결정론적(deterministic) 룰 기반의 기사 분류 및 중요도 점수 산출 MVP 기능에 대한 검증 결과입니다. 이번 차수에서는 LLM이나 임베딩 없이 텍스트 키워드 매칭과 언어 감지 규칙을 처리하는 헬퍼 모듈([app/utils/article_classification.py](~/news-lab/app/utils/article_classification.py)) 및 데이터베이스 대상 읽기 전용 집계 스크립트([scripts/analyze_article_classification.py](~/news-lab/scripts/analyze_article_classification.py))가 안전하게 작성 및 검증되었습니다. 비파괴적인 원칙 하에 시스템 영향도 없이 정상 설계되었음을 확인했습니다.

## Requirement Coverage

[docs/tasks/feature-lightweight-article-classification.md](~/news-lab/docs/tasks/feature-lightweight-article-classification.md)에 지정된 모든 요구사항이 정상 반영되었습니다.

- **Source Category 보존**: 소스 기본 카테고리는 보존하되, 룰 기반 카테고리(`rule_category`)를 별도의 독립된 분석 신호로 추출하여 데이터를 직접 덮어쓰지 않도록 설계되었습니다.
- **유니코드 스크립트 기반 언어 판별**: 한글, 일본어, 중국어, 아랍어, 키릴 문자 감지 규칙 및 최하위 언어 폴백 정책(`RSS_SOURCES` 기준)이 올바르게 설계되었습니다.
- **결정론적 중요도 계산**: 기사 발행/수집 경과 시간(recency), 소속 카테고리 점수, 긴급/고영향도 키워드 유무를 가중치 합산하여 중요도 신호 점수(`importance_score`)를 투명하게 연산합니다.
- **다양한 시간 윈도우 및 기준 지원**: `--window-hours` (24h, 72h, 168h, all) 옵션과 `--time-basis` (published, created) 플래그를 지원합니다.
- **결과 출력 및 기록**: 카테고리/언어별 분포수 및 소스/룰 미스매치 예시, 고중요도 기사 후보 리스트 등을 집계하여 JSON으로 상세히 출력하고 검증 문서에 기록을 남겼습니다.

## Code Quality / Maintainability

- **단어 경계(Word Boundary) 매칭**: 키워드 매칭 시 `(?<!\w) ... (?!\w)`를 활용하여 부분 문자열 매칭으로 인한 오탐(예: "date"에 "update"가 매칭되는 현상)을 방지합니다.
- **가벼운 언어 판별기**: 외부 무거운 NLP 패키지 없이 유니코드 문자 범위 정규표현식을 적용하여 빠르고 효율적인 분석 엔진을 제공합니다.
- **DB 스키마 타협 방안**: `sources` 테이블에 `language` 컬럼이 부재함을 런타임에 확인한 후, 테이블을 수정하는 대신 레포지토리 내부의 정적 설정 파일([app/config/rss_sources.py](~/news-lab/app/config/rss_sources.py))을 폴백 사전으로 활용하게 함으로써 아키텍처적 유연성을 보여주었습니다.

## Security Review

- **SQL Injection 방지**: 스크립트 작성 시 동적으로 정렬 기준이 변경되는 구문은 사전 승인된 정적 쿼리 구문으로 한정 맵핑했으며, 시간 윈도우 인자는 파라미터 바인딩(`:window_hours`)을 철저히 수행했습니다.
- **자격 증명 오염**: 민감 정보의 소스코드 내 하드코딩 흔적이 없으며, `.env`를 통한 환경 변수 관리 방식을 정상적으로 유지했습니다.
- **안전 거래 설정**: DB 커넥션 오픈 즉시 `set transaction read only`를 호출하여 기사 테이블이나 소스 테이블에 대한 의도치 않은 쓰기 행위를 철저히 방어하고 있습니다.

## Operational Risk

- **실제 영향도**: 제로(0).
- 마이그레이션이 실행되지 않고 DB 데이터 또한 업데이트하지 않으며 기존 동작 중인 스케줄러(CronJob)나 API 라우터에 전혀 관여하지 않으므로 운영 리스크가 존재하지 않습니다.

## Scope Control

- **스콥 준수**: LLM 연동, 임베딩 벡터 생성, 토픽 그룹 빌딩 등 상위 차수 도메인의 기능들은 배제되어 프로젝트 스콥이 적절히 통제되었습니다.

## Verification Review

- 검증 문서([docs/verification/feature-lightweight-article-classification.md](~/news-lab/docs/verification/feature-lightweight-article-classification.md))에 기록된 내용과 실제 소스코드의 일관성이 높습니다.
- 키워드 매칭 정규표현식 내 백슬래시 f-string 컴파일 오류 등을 조기 발견하고 이를 수정한 기록이 투명하게 반영되어 있습니다.

## Documentation Review

- PR draft와 Devlog draft에 기재된 집계 통계치(최대/평균 점수, 미스매치 건수 등)가 검증 로그상의 통계값과 완전히 일치하며 사실에 기반해 작성되었습니다.
- 향후 스키마 정의 및 배치 크기 조율을 위한 계획도 단계적으로 기재되어 있습니다.

## Problems Found

- 발견된 특이사항이나 아키텍처 위반 사항이 없습니다.

## Required Fixes Before PR

- 없음.

## Optional Improvements

- **키워드 및 가중치 외부화**: 현재 카테고리 매칭 키워드셋 및 가중치 점수들이 코드 내 상수로 강하게 연결되어 있습니다. 향후 기사 분류 체계가 복잡해지면 이를 `config.json` 등 설정 파일로 분리하는 설계를 도입하면 관리 효율성이 증대될 수 있습니다.

## Suggested Test Commands

PR 제출 전 로컬 환경에서 다음과 같은 명령어로 빌드 및 테스트 상태를 최종 점검할 수 있습니다.

```bash
# 전체 단위 테스트 실행
.venv/bin/python -m unittest discover -s tests -v

# 파이썬 구문 분석 및 컴파일 검증
.venv/bin/python -m py_compile app/utils/article_classification.py scripts/analyze_article_classification.py

# 최근 72시간 내 수집된 기사의 classification dry-run 분석 실행
.venv/bin/python scripts/analyze_article_classification.py --window-hours 72 --max-examples 5
```

## Verdict

- **PASS**: 모든 요구사항과 안전성 인수 기준을 충족하므로, 풀 리퀘스트 병합 절차를 진행할 것을 권장합니다.
