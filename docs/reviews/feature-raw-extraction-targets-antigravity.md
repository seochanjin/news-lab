# Antigravity Review: Topic 대표 후보 기반 raw extraction 대상 선정

## Review Summary

이 리뷰는 [feature/raw-extraction-targets](~/news-lab) 브랜치에 구현된 Topic 대표 후보 기반 Raw Extraction 대상 선정 기능의 품질, 안정성 및 요구사항 충족 여부를 검증합니다.

구현된 시스템은 32차의 대표 기사 후보 선정 결과를 기반으로 원문 추출 대상 기사를 Read-only 상태로 판별합니다. 기사 메타데이터와 기존 원문 추출 이력 상태(`raw_articles`)를 결합하여 `target`, `backup`, `skipped`, `already_extracted`, `failed` 상태를 계산하고, 토픽당 최대 기사 수(`max-targets-per-topic`)를 고려한 추출 후보를 선정합니다.

검증 결과, 데이터베이스 쓰기를 제한하고 트랜잭션을 Read-only로 안전하게 다루는 등 운영 안전성은 훌륭히 설계되어 있으나, **토픽 내부 기사의 입력 순서에 따른 선정 오작동 버그**와 **테스트 케이스 누락**, 그리고 **결정론적 보고서의 오용 위험을 경고하는 안내 문구 누락**이 발견되어 PR 머지 전 반드시 보완이 필요합니다.

## Requirement Coverage

[feature-raw-extraction-targets.md](~/news-lab/docs/tasks/feature-raw-extraction-targets.md)에 정의된 대부분의 기능 요구사항은 정상적으로 다루어지고 있습니다.

- **토픽별 Raw Extraction 대상 선정**: [raw_extraction_targets.py](~/news-lab/app/utils/raw_extraction_targets.py)에서 각 토픽의 대표 후보 순위를 기준으로 상태를 판별합니다.
- **최대 대상 제한 기능**: `--max-targets-per-topic` 인수를 통해 토픽당 타겟 개수를 제어(`1`~`3` 범위)하며, 기본값은 `1`로 정상 작동합니다.
- **안전 정책 및 상태 구분**: 이미 추출된 기사는 `already_extracted`, 실패 이력이 있는 기사는 `failed`로 분류하며 자동 재시도를 방지합니다.
- **Read-only CLI**: [analyze_raw_extraction_targets.py](~/news-lab/scripts/analyze_raw_extraction_targets.py)를 통해 DB 쓰기 없이 타겟 후보를 계산하고 마크다운 보고서와 JSON 출력을 얻을 수 있습니다.
- **토픽 정렬 정책 적용**: 복수 기사 토픽 우선, 매체 수 높은 순, 기사 수 높은 순, 최신순 순서의 가중치를 부여해 토픽을 정렬합니다.

## Code Quality / Maintainability

전반적인 코드는 깔끔하게 작성되어 있으며 타입 힌트와 주석이 상세히 기술되어 있습니다. 다만 아래에서 설명할 치명적인 정렬 무시 로직에 대한 버그와 이를 방지하기 위한 정적 보완 처리가 부족합니다.

- **입력 순서 의존성 문제**: [raw_extraction_targets.py](~/news-lab/app/utils/raw_extraction_targets.py)의 `_select_topic_targets` 함수에서 `topic["articles"]`를 순회할 때 기사들이 `representative_candidate_rank` 기준으로 정렬되어 있음을 보장하지 않고 루프를 실행하고 있습니다. 만약 입력 데이터의 정렬이 무작위일 경우, 순위가 낮은(예: rank 2) 후보가 루프를 먼저 지나가며 타겟 수 한도를 소진하여 rank 1 후보가 `backup`으로 지정되는 논리 결함이 존재합니다.
- **점수 격리 검증**: `candidate_score`를 토픽 정렬 우선순위로 오용하지 않도록 `_topic_priority_key` 함수에서 철저하게 격리 구현한 점은 매우 우수합니다.

## Security Review

- **인증 정보 노출 없음**: OpenAI API 관련 환경 변수 조회 시 하드코딩된 값 없이 안전하게 격리되어 처리됩니다.
- **권한 제어**: 분석용 임시 연동 게이트가 CLI 수준에 안전하게 격리되어 있으며 유효하지 않은 실행은 실행을 사전에 중단합니다.

## Operational Risk

- **DB 쓰기 리스크 차단**: 커넥션 진입점 부근에서 `connection.execute(text("set transaction read only"))`를 선제적으로 선언하여 후속 코드에서 물리적인 DB 쓰기 시도가 발생하더라도 원천적인 예외 처리가 작동하게 설계되었습니다.
- **검증용 샘플 보고서 오용 위험**: 현재 생성된 deterministic 보고서([feature-raw-extraction-targets.md](~/news-lab/docs/reports/feature-raw-extraction-targets.md))는 해시 충돌 기반의 임베딩 모델을 사용했기 때문에 Astronomics 관련 뉴스나 다른 관련성 없는 글들이 동일 토픽(`topic-0086`)으로 비정상적으로 그룹화되어 있습니다. 보고서 내부에 이 내용이 **순수 검증용 샘플이며 승인된 추출 목록이 아니라는 명시적인 안내**가 없어, 운영자가 이를 실제 기획 승인된 데이터로 오해하여 수동 추출을 승인할 위험이 잔존합니다.

## Scope Control

- **범위 제어 충실**: `git status` 상에 기존 라우터나 수집/추출 스케줄 등의 소스 코드 수정 흔적이 전혀 없으며, MVP 대상에 한정된 파일들로 독립성 있게 변경 사항이 구성되었습니다.

## Verification Review

[feature-raw-extraction-targets.md](~/news-lab/docs/verification/feature-raw-extraction-targets.md)의 실행 이력과 단위 테스트 통과 결과를 검증했습니다.

- **검증 기록의 한계**: `pytest`를 찾을 수 없는 환경적 제한이 있었지만, unittest discovery를 이용하여 `65 passed`라는 풍부한 테스트 커버리지를 투명하게 문서화하였습니다.
- **누락된 검증 요건**: 요구사항에서 보증하도록 요구한 "입력 순서가 섞여 있을 때의 랭킹 기반 타겟 우선 추출" 검증 및 "싱글톤 제외에 대한 정밀 테스트" 중 순서 왜곡에 대한 검증 코드가 단위 테스트에 누락되어 있습니다.

## Documentation Review

문서 자체의 연계성과 통일성은 양호하지만, deterministic 보고서 및 비교용 max2 보고서가 단순히 '추출 대상 리뷰 보고서'로 정의되어 있어 분석용 샘플 문서로서의 격리성 설명이 다소 미흡합니다.

## Problems Found

1. **정렬 순서 미보장에 따른 타겟 오추출 버그**:
   - `_select_topic_targets`에서 `topic["articles"]`를 정렬 없이 있는 그대로 루프 순회하므로, 기사 목록이 `representative_candidate_rank` 순서로 제공되지 않는 이상 오선정이 일어납니다.
2. **단위 테스트 내 정렬 보증 검증 케이스 누락**:
   - [test_raw_extraction_targets.py](~/news-lab/tests/test_raw_extraction_targets.py)에서 순위가 뒤섞인 배열을 입력값으로 전달하여 랭크 1이 타겟으로 안정적으로 검출되는지를 단정(Assert)하는 테스트 케이스가 작성되어 있지 않습니다.
3. **결정론적 샘플 보고서 안내 미흡**:
   - 보고서 상단에 `deterministic-hash-v1`로 수행되었음을 명시하긴 하였으나, 운영자가 불필요한 단어가 병합된 잘못된 토픽 구성을 보고 기획 결함으로 착각하거나 해당 목록을 승인할 수 있는 우려가 있습니다. 이것이 검증용 가짜 임베딩 샘플 보고서임을 명시하는 경고 문구가 누락되어 있습니다.

## Required Fixes Before PR

### 1. 토픽 기사 정렬 처리 ([raw_extraction_targets.py](~/news-lab/app/utils/raw_extraction_targets.py))

- 타겟 선정 루프를 돌기 전, 기사들의 `representative_candidate_rank` 순위에 근거해 `sorted` 처리를 추가하여 데이터 제공 순서가 뒤섞여 있더라도 lower rank(1, 2, 3)가 반드시 먼저 순회되도록 강제해야 합니다.
- 정렬 기준 예시: 랭크가 지정된 기사를 랭크 오름차순(1 -> 2 -> 3)으로 우선 배치하고, 랭크가 `None`인 기사는 맨 뒤에 위치하도록 키를 정립합니다.

### 2. 정렬 순서 보증 단위 테스트 추가 ([test_raw_extraction_targets.py](~/news-lab/tests/test_raw_extraction_targets.py))

- 대표 후보 목록이 섞인 입력 `[candidate(article_id=2, rank=2, ...), candidate(article_id=1, rank=1, ...)]` 상황에서도 순위 1번 기사가 `target`이 되고, 2번 기사가 `backup`이 됨을 입증하는 테스트 함수를 추가해야 합니다.

### 3. 결정론적/비교 샘플 보고서에 경고 및 성격 명시 ([app/utils/raw_extraction_targets.py](~/news-lab/app/utils/raw_extraction_targets.py))

- `render_raw_extraction_target_report` 함수를 수정하여 보고서 상단에 해당 문서는 **기술 검증을 위한 샘플/비교 산출물(Deterministic hash 모델 사용)**이며 실제 서비스 적용 대상이 아니라는 disclamier 경고 문구를 주입해야 합니다.
- 또한 `--max-targets-per-topic 2`로 빌드된 보고서에는 이것이 **복수 타겟 비교를 위한 샘플 분석 보고서**임을 명문화해야 합니다.

## Optional Improvements

- **CLI 실행 디렉토리 검사**:
  - `scripts/analyze_raw_extraction_targets.py` 실행 시 출력 파일 경로가 `docs/reports/` 폴더 하위로 설정되는 것이 일반적이므로 파일 생성 유무뿐만 아니라 경로 예외 처리를 정교하게 캡슐화하면 좋습니다.

## Suggested Test Commands

정렬 버그 수정 및 단위 테스트 보강 후 아래 명령을 통해 수정 사항을 검증할 것을 제안합니다.

```bash
# 정적 컴파일 오류 여부 확인
.venv/bin/python -m py_compile \
  app/utils/topic_grouping.py \
  app/utils/topic_representatives.py \
  app/utils/raw_extraction_targets.py \
  scripts/analyze_raw_extraction_targets.py

# 단위 테스트 재탐색 실행 (추가된 정렬 테스트 포함 66개 전체 통과 여부 검증)
.venv/bin/python -m unittest discover -s tests -v

# CLI 인터페이스 옵션 검증
.venv/bin/python scripts/analyze_raw_extraction_targets.py --help
```

## Verdict

**FAIL**
(이유: 토픽 내부 기사 정렬 버그가 있어 입력 데이터의 제공 순서에 따라 rank 2 후보가 타겟으로 오추출되는 정합성 문제가 있으며, deterministic 샘플 보고서의 성격을 규정하는 면책 경고문이 누락되어 실제 운영 승인 시의 위험이 수반됩니다. 상기 Required Fixes에 명시된 내용이 반영된 후 재심사해야 합니다.)
