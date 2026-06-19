# Antigravity Review: Embedding 기반 topic grouping MVP

## Review Summary

본 리뷰는 `feature/embedding-topic-grouping` 브랜치에 구현된 임베딩 기반 토픽 그룹화 MVP 기능의 설계와 비용/비기능 안전 장치 작동 여부에 대한 검증 결과입니다. 이번 차수에서는 결정론적 로컬 해시 임베딩([app/utils/article_embeddings.py](~/news-lab/app/utils/article_embeddings.py))과 중요도 우선의 seed-based greedy clustering 알고리즘([app/utils/topic_grouping.py](~/news-lab/app/utils/topic_grouping.py)), 그리고 외부 API 차단 및 파이프라인 출력을 확인하는 집계 스크립트([scripts/analyze_topic_groups.py](~/news-lab/scripts/analyze_topic_groups.py))가 신뢰성 있게 구축되었습니다.

## Requirement Coverage

[docs/tasks/feature-embedding-topic-grouping.md](~/news-lab/docs/tasks/feature-embedding-topic-grouping.md)의 모든 기획적 요구조건이 충족되었습니다.

- **임베딩 텍스트 결합**: 기사 제목, 요약문, 출처명, 카테고리 후보 필드가 정규화되어 결합 입력값으로 가공됩니다.
- **코사인 유사도 계산**: 벡터 간 정규화를 포함하는 코사인 유사도 헬퍼가 추가되었습니다.
- **중요도 기반 시드 선정**: 29차 중요도 점수(`importance_score`) 내림차순을 활용해 최상위 기사를 그룹의 중심점(seed)으로 삼는 greedy 클러스터링 알고리즘이 올바르게 설계되었습니다.
- **요약 지표 출력**: 토픽 후보별 기사 수, 출처 수, 카테고리/언어 분포, 유사도 평균, 대표 기사 및 중요도 기사가 JSON 형식으로 상세히 요약 출력됩니다.

## Code Quality / Maintainability

- **안정적인 비동기/순서 보장**: `OpenAIEmbeddingProvider`는 OpenAI가 대량 임베딩 반환 시 순서를 보장하지 않을 수 있는 점을 고려하여 `index` 필드 기준 정렬 처리를 구현해 배치 순서 어긋남 버그를 사전에 방지했습니다.
- **다형성 보장**: `EmbeddingProvider` 프로토콜 인터페이스를 통해 로컬 해시 모델과 OpenAI 모델이 분리되어 런타임 결합도를 낮췄습니다.
- **정교한 수학적 검증**: 코사인 유사도 및 해시 단위 구문 예외 상황(벡터 차원 불일치 등)에 대한 사전 대응 코드가 명확합니다.

## Security Review

- **SQL Injection 방지**: 스크립트의 조회 쿼리가 절대 문자열 결합(interpolation)을 사용하지 않으며, 미리 정의된 상수 `text()` 템플릿에 `window_hours` 및 `max_articles` 매개변수를 완전히 바인딩하여 안전합니다.
- **자격 증명 오염 방지**: 외부 API용 자격 증명(`OPENAI_EMBEDDING_API_KEY`)을 환경 변수에서 로딩하도록 구현하였으며, 소스 코드 내부 하드코딩 흔적은 없습니다.
- **최소 권한의 법칙**: DB 연결 즉시 `set transaction read only`를 명시 실행하여 dry-run 성격에 맞게 데이터 무결성을 보호합니다.

## Operational Risk

- **비용 안전 장치 (Cost-safety)**: 기본 실행 시 외부 API 호출이 차단된 로컬 해싱 모델(`deterministic-hash-v1`)을 강제하며, OpenAI 임베딩 호출에는 다음 세 가지 안전 조건이 모두 필수 요구됩니다:
  1. `--use-embedding-provider` 플래그 명시 지정
  2. `OPENAI_EMBEDDING_API_KEY` 환경 변수 적재
  3. 명시적인 `--max-articles` 인자 지정 (최대 200건으로 상한 제한)
- **비용 예상 리포트**: 실제 호출 발생 직전 예상 토큰 수와 예상 비용($)을 stdout에 자동 리포팅하는 방어 레이어가 정상 작동합니다.

## Scope Control

- **스콥 준수**: LLM 기반의 한국어 요약, 주요 포인트 추출, 키워드 추출, 프론트엔드 라우트 바인딩 및 자동 크론잡 스케줄링 등의 아웃오브스콥 영역은 코드와 설정에서 배제되어 통제 상태가 우수합니다.
- **변경 통제**: Kubernetes manifest, DB DDL 마이그레이션이 발생하지 않고 읽기 전용 상태를 엄수했습니다.

## Verification Review

- 검증 로그([docs/verification/feature-embedding-topic-grouping.md](~/news-lab/docs/verification/feature-embedding-topic-grouping.md))상에서 33개의 전체 단위 테스트 통과 및 DNS 제한 조건 아래 정상 동작을 확인한 이력이 정밀하게 수록되어 있습니다.
- 로컬 해싱 임베딩 결과물(100건 중 98개 그룹 도출 등)은 파이썬 파이프라인 형태 검증용 목적으로만 올바르게 규정되었으며, 임의의 품질 평가 수단으로 왜곡되어 사용되지 않았습니다.

## Documentation Review

- PR draft 양식이 일치하며 Devlog draft는 향후 스키마 설계 계획(`article_embeddings`, `topics`, `topic_articles` 데이터 구조 모델링 등)을 후보 초안으로 명확히 구획하여 향후 마이그레이션 적용 차수를 고려할 수 있게 문서화했습니다.

## Problems Found

- 발견된 결함이나 취약점이 없습니다.

## Required Fixes Before PR

- 없음.

## Optional Improvements

- **배치 처리(Batching)**: 현재 `OpenAIEmbeddingProvider`는 최대 200건의 기사 임베딩 요청을 한 번의 HTTP POST에 실어 처리합니다. 향후 아웃오브스콥 상한(200건 이상)을 해제하거나 확장 적용 시, API 제한 크기를 넘어서지 않도록 청크(chunk) 단위 분할 배치 호출 로직을 설계하는 방향을 추천합니다.

## Suggested Test Commands

PR 제출 전 아래 로컬 테스트 명령어로 파이프라인 정상 유무를 확인하십시오.

```bash
# 전체 단위 테스트 실행
.venv/bin/python -m unittest discover -s tests -v

# 구문 컴파일 오류 체크
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py

# 로컬 해싱 기반 24시간 발행 윈도우 토픽 후보 집계 검증 (드라이런)
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
```

## Verdict

- **PASS**: 모든 비용 통제 조건, SQL Injection 차단 조건 및 마이그레이션 미지행 규칙을 준수하여 합격으로 처리합니다.
