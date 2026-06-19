# Antigravity Review: Topic 대표 기사 후보 선정 MVP

## Review Summary

이 리뷰는 [feature/topic-representative-candidates](~/news-lab) 브랜치에 구현된 Topic 대표 기사 후보 선정 MVP 기능의 품질, 안정성 및 요구사항 충족 여부를 검증합니다.

구현된 시스템은 [topic_grouping.py](~/news-lab/app/utils/topic_grouping.py)의 임베딩 기반 토픽 그룹화 결과를 바탕으로, 대표 기사 선정을 위한 7가지 다중 신호(importance, topic seed, similarity, source diversity, title/summary information, published recency, category) 기반 scoring 정책을 설계 및 구현하였습니다. 또한, sequential greedy 선택 방식을 통해 동일 매체 중복 노출을 감점(source diversity)하는 품질 중심의 대표 후보 추천 정책을 실현하고 있으며, 사용자 및 운영자가 검토할 수 있는 마크다운 보고서(report) 자동 생성 기능을 제공합니다.

전체 코드 변경 사항 및 추가 파일들은 설계 및 안전성 가이드를 충실히 준수하고 있으며, 운영 위험 요소(Production Impact) 없이 완전한 Read-only 형태로 구현되었음을 확인하였습니다.

## Requirement Coverage

[feature-topic-representative-candidates.md](~/news-lab/docs/tasks/feature-topic-representative-candidates.md)에 정의된 모든 요구사항이 완벽하게 충족되었음을 확인하였습니다.

- **대표 후보 선정 로직 구현**: [topic_representatives.py](~/news-lab/app/utils/topic_representatives.py)에 대표 기사 후보 선정 헬퍼 함수가 작성되었으며, 토픽당 최대 3개(`max_candidates_per_topic`)까지 순위별로 기사를 선정합니다.
- **다중 신호 기반 채점 정책**: `importance_score` 단일 기준에 의존하지 않고, 요구사항에 정의된 7가지 신호가 `COMPONENT_WEIGHTS`에 가중치(합계 1.0)로 정확히 반영되었습니다.
- **매체 다양성(Source Diversity) 보장**: 순차 선택 과정에서 이미 선택된 매체(`source`)에서 발행된 기사는 다양성 점수를 `1.0`에서 `0.25`로 감점하여 중복 매체 노출을 제한합니다.
- **기본 및 Fallback 임계값(Threshold) 지원**: 기본 임계값 `0.70`과 보수적 Fallback 임계값 `0.72`를 명령행 인수로 자유롭게 설정하여 비교 분석할 수 있습니다.
- **상세 보고서 생성**: 토픽 후보 ID, 기사 수, 매체 수, 카테고리/언어 분포, 선정 기사 여부 및 순위, 기사 메타데이터(제목, 매체, 중요도, 유사도, 발행일), 상세 점수 성분 및 선정 사유가 포함된 마크다운 보고서를 정상적으로 빌드합니다.
- **안전 게이트 및 Read-only**: 실제 OpenAI API 호출을 제어하는 `--use-embedding-provider` 옵션 게이트와 테스트용 결정론적 임베딩 제공자(`DeterministicHashEmbeddingProvider`) 연동이 정상 작동합니다.

## Code Quality / Maintainability

구현된 코드의 논리 구조와 유지보수성은 매우 훌륭합니다.

- **모듈성**: 비즈니스 로직([topic_representatives.py](~/news-lab/app/utils/topic_representatives.py)), 명령행 인터페이스([analyze_topic_representatives.py](~/news-lab/scripts/analyze_topic_representatives.py)), 그리고 기존 그룹화 유틸([topic_grouping.py](~/news-lab/app/utils/topic_grouping.py))이 단일 책임 원칙에 따라 깔끔하게 분리되어 있습니다.
- **타입 안정성**: 함수 시그니처 전반에 Python 타입 어노테이션이 작성되어 정적 분석 및 가독성을 높였습니다.
- **점수 일관성**: 가중치의 합이 1.0이 되도록 컴포넌트 딕셔너리가 설계되었으며, `float` 정밀도 문제를 최소화하기 위해 소수점 4자리 반올림(`round(..., 4)`) 처리가 일관되게 적용되었습니다.
- **견고성**: 최신성 점수(`recency_score`) 계산 시 `published_at` 시각이 누락된 경우 `created_at`으로 자동 Fallback하는 안전 장치가 마련되어 신뢰성을 확보하였습니다.

## Security Review

코드베이스 상에 비밀키 유출 등 보안 취약점은 식별되지 않았습니다.

- **비밀키 노출 방지**: OpenAI API 호출에 필요한 인증 정보(`OPENAI_EMBEDDING_API_KEY`)를 코드 내에 하드코딩하지 않고, `os.environ` 및 `.env` 로드를 통해 주입받도록 안전하게 처리되었습니다.
- **API 게이트 차단**: `--use-embedding-provider` 사용 시 API Key 존재 여부를 사전 확인하여 에러로 즉각 처리하고, 미지정 시에는 로컬 결정론적 해시 연동을 강제해 키 누락에 따른 예외 상황을 원천 차단합니다.
- **로그 안정성**: 보고서, 로그, 테스트 파일 등에 민감한 키 값이나 개인 정보가 전혀 노출되지 않았습니다.

## Operational Risk

이 브랜치가 가지는 운영 위험은 **없음 (Zero)** 수준으로 판단됩니다.

- **완벽한 Read-only 작동**: DB 연결 세션 시작 시 `connection.execute(text("set transaction read only"))`를 명시적으로 실행하여 데이터베이스 쓰기(INSERT/UPDATE/DELETE) 발생 가능성을 차단하였습니다.
- **운영 인프라 비침해**: DB 스키마 마이그레이션이 발생하지 않으며, API 라우터 등록 및 Kubernetes 매니페스트 변경 사항이 없어 현재 실행 중인 K3s 서비스에 미치는 위험이 전무합니다.

## Scope Control

작업 범위가 사전에 지정된 범위 내로 엄격하게 통제되었습니다.

- **불필요한 변경 차단**: `git status` 기준 변경 사항은 [topic_grouping.py](~/news-lab/app/utils/topic_grouping.py)의 시드 여부 및 본문 요약 필드 추가에 한정되며, 그 외에는 신규 생성 파일로만 구성되어 있어 기존 로직에 영향을 주지 않는 범위 제어가 모범적으로 이루어졌습니다.

## Verification Review

[feature-topic-representative-candidates.md](~/news-lab/docs/verification/feature-topic-representative-candidates.md) 검증 로그에 기재된 검증 프로세스의 무결성을 재검토하였습니다.

- **기록의 진실성**: 검증 로그에 명시된 단위 테스트 실행(54개 테스트 패스), CLI 도움말 정상 작동, 결정론적 임베딩 기반 리포트 생성 등이 모두 실제 실행 결과를 기반으로 왜곡 없이 일관되게 작성되었음을 확인하였습니다.
- **환경 차이 기록**: 개발 환경의 차이로 인해 실행하지 못한 `pytest`에 대해 거짓으로 통과했다고 주장하지 않고, 실행 불가 사실(`command not found`)을 있는 그대로 정직하게 누락(Pending) 처리한 점은 검증 무결성 측면에서 매우 우수합니다.

## Report Quality Review

생성된 리포트 파일들을 통해 산출물의 품질을 정밀 비교하였습니다.

- **비교 분석의 투명성**: 임계값 `0.70` 보고서([feature-topic-representative-candidates.md](~/news-lab/docs/reports/feature-topic-representative-candidates.md))와 `0.72` 보고서([feature-topic-representative-candidates-threshold-072.md](~/news-lab/docs/reports/feature-topic-representative-candidates-threshold-072.md)) 간의 그룹화 차이가 직관적으로 이해됩니다. 예를 들어, `0.70`에서 두 기사로 묶여 있던 World Cup 관련 토픽(`topic-0035`)이 임계값을 `0.72`로 상향함에 따라 두 기사 간의 코사인 유사도(`0.7175`)가 미달되어 싱글톤(단일 기사 토픽)으로 나뉘고 상세 목록에서 자동 배제되는 클러스터링의 수학적 경계선 현상이 올바르게 리포트에 반영되어 있습니다.
- **채점 인트라 범위 준수**: 채점 지표인 `candidate_score`가 토픽 내부의 대표 후보 선정용으로만 한정 사용(Intra-topic)되어야 하며, 전체 토픽 간의 절대적 중요도 비교 점수로 오용되어선 안 된다는 제한 사항과 전체 기사 추출 우선순위 수립은 후속 정책 설계 차수로 위임한다는 정책적 명시가 문서 및 코드([topic_representatives.py:L223-L225](~/news-lab/app/utils/topic_representatives.py#L223-L225))에 뚜렷하게 선언되었습니다.
- **가독성 향상**: [feature-topic-representative-candidates-with-singletons.md](~/news-lab/docs/reports/feature-topic-representative-candidates-with-singletons.md)를 통해 싱글톤 토픽까지 포함하는 전체 출력을 선택 옵션(`--include-singletons`)으로 밀어내고, 기본 보고서들은 2개 이상의 기사를 가지는 복수 기사 토픽(Multi-article topics)에 집중함으로써 검토자의 인지 부하를 획기적으로 경감시켰습니다.

## Documentation Review

작업 관련 산출물 문서 간의 일관성이 높습니다.

- [feature-topic-representative-candidates.md](~/news-lab/docs/tasks/feature-topic-representative-candidates.md)(요구사항 문서), [feature-topic-representative-candidates.md](~/news-lab/docs/verification/feature-topic-representative-candidates.md)(검증 로그), [feature-topic-representative-candidates.md](~/news-lab/docs/pr/feature-topic-representative-candidates.md)(PR 설명서), [feature-topic-representative-candidates.md](~/news-lab/docs/devlog/feature-topic-representative-candidates.md)(개발로그) 간에 지표 정보(기사 100건 분석 시의 토픽/대표 후보 개수 등)가 오차 없이 정교하게 맵핑되어 있습니다.

## Problems Found

심각한 버그나 결함은 식별되지 않았으나, 재현성 및 운영상 혼선을 방지하기 위해 다음 사항을 기록합니다.

1. **검증 스크립트 실행 경로와 템플릿 리포트의 불일치**:
   - 검증 문서에 명시된 기본 결정론적 리포트 생성 명령(예: `report-path docs/reports/feature-topic-representative-candidates.md`)을 그대로 실행하면, 실제 OpenAI 임베딩 결과를 기반으로 생성되어 저장되어 있던 현재의 리포트가 결정론적 로컬 해시 임베딩 결과(토픽 수 96개, 복수 기사 토픽 3개)로 덮어씌워지게 됩니다.
   - 현재 저장소의 `docs/reports/feature-topic-representative-candidates.md`와 `docs/reports/feature-topic-representative-candidates-threshold-072.md`는 실제 OpenAI API 호출 결과(토픽 수 85개, 복수 기사 토픽 10개)가 영구적으로 보존되어 있는 상태입니다.
   - 따라서 검증 과정에서 해당 명령어 실행 시 고품질의 OpenAI 분석 데이터가 덮어써져 손실될 우려가 존재합니다.

## Required Fixes Before PR

- **없음 (None)**: PR 승인 및 머지를 가로막는 결함이나 설계 위반 사항은 존재하지 않습니다.

## Optional Improvements

1. **보고서 출력 경로 이원화 또는 보존 조치**:
   - 검증 문서의 CLI 실행 예시 혹은 기본 경로를 이원화하여, 개발자 로컬 검증 명령이 실제 고품질 OpenAI 데이터 보고서를 덮어쓰지 않도록 개선하는 것이 권장됩니다.
   - 예: 테스트 실행 경로를 `docs/reports/feature-topic-representative-candidates-deterministic.md` 형태로 분리하거나 별도 아티팩트로 명명하여 분리 관리할 수 있습니다.
2. **정렬 비교 가독성 보완 (`_ranking_key`)**:
   - [topic_representatives.py](~/news-lab/app/utils/topic_representatives.py)의 `winner = min(scored, key=_ranking_key)` 로직에서 역순 정렬을 위해 음수 기호(`-`)를 채점 지표들에 붙이고 `min`을 활용하는 기법은 수학적으로 정확하나 가독성을 저해할 소지가 있습니다. `max(..., key=...)` 형태나 직관적인 내림차순 정렬 형태로의 표현 교체를 차후 리팩토링 시 고려해볼 수 있습니다.

## Suggested Test Commands

개발 및 운영 환경에서 영향도 없이 안전하게 이 브랜치를 추가 검증해볼 수 있는 Read-only 명령어 목록입니다.

```bash
# Python 컴파일 오류 여부 확인
.venv/bin/python -m py_compile app/utils/topic_representatives.py scripts/analyze_topic_representatives.py

# 단위 테스트 전체 탐색 실행 (54개 전체 성공 여부 검증)
.venv/bin/python -m unittest discover -s tests -v

# 도움말 인터페이스 검증
.venv/bin/python scripts/analyze_topic_representatives.py --help

# 임베딩 비용 분석을 위한 OpenAI dry-run (실제 임베딩 생성이 아닌 토큰 측정 용도)
.venv/bin/python scripts/analyze_topic_representatives.py \
  --window-hours 24 \
  --max-articles 100 \
  --use-embedding-provider \
  --similarity-threshold 0.70 \
  --report-path docs/reports/temp_test_report.md \
  --dry-run
```

## Verdict

**PASS** (승인 및 머지 가능)
이 브랜치는 요구사항 명세서를 완벽하게 충족하며, 예외 설계 및 코드 무결성이 매우 높고 운영 부하 및 리스크가 전혀 없는 완성도 높은 MVP 상태입니다.
