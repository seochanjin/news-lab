# Antigravity Review: Raw extraction target 기반 제한 실행 CLI

## Review Summary

이 리뷰는 [feature/raw-extraction-target-runner](~/news-lab) 브랜치에 구현된 Raw Extraction Target 기반 제한 실행 CLI 기능의 품질, 안정성 및 요구사항 충족 여부를 검증합니다.

구현된 시스템은 33차의 대표 타겟 선정 결과를 바탕으로, 실제 원문 추출기([extract_raw_articles.py](~/news-lab/scripts/extract_raw_articles.py))와 안전하게 연동되는 제한 실행 CLI([run_raw_extraction_targets.py](~/news-lab/scripts/run_raw_extraction_targets.py))를 추가하였습니다. 기본 실행을 안전하게 dry-run으로 격리하고, 운영자의 명시적 승인 하에 소수(1~5개)의 타겟만 제한적으로 실제 원문 추출을 연동할 수 있도록 설계되었습니다.

정밀 검증 결과, 기존 CronJob의 기본 실행 엔트리포인트를 완벽하게 보존하면서 신규 선택 추출 로직을 안전한 Opt-in 구조로 결합하였으며, 요구사항에 명시된 예외 케이스 처리와 안전 게이트가 빈틈없이 구현되었음을 확인하여 **PASS** 판정을 내립니다.

## Requirement Coverage

[feature-raw-extraction-target-runner.md](~/news-lab/docs/tasks/feature-raw-extraction-target-runner.md)에 정의된 모든 설계 요건이 정상적으로 충족되었습니다.

- **기본 dry-run 동작 및 가드**: `--execute`가 제공되지 않는 한 실제 추출기 실행 및 DB 쓰기가 차단됩니다.
- **제한 조건(Limit & Execute) 강제**: 실제 실행을 의미하는 `--execute` 사용 시 `--limit` 입력이 필수이며, 허용치 범위는 `1~5`로 엄격히 제한됩니다. (유효 범위를 벗어나면 CLI 파서가 차단합니다.)
- **타겟 필터링 완벽 적용**: 오직 `extraction_target_status=target`인 기사만 추출 후보로 승격되며, `backup`, `skipped`, `already_extracted`, `failed` 기사는 실행 후보에서 물리적으로 제외됩니다.
- **리포트 내 필드 준수**: 실행 계획 보고서에 기사 ID, 제목, 매체, 토픽 ID, 원문 상태 및 결정 사유가 누락 없이 표현됩니다.
- **보고서 수치 일관성**: dry-run 보고서 상에 `dry_run=true`, `execute_requested=false`, `raw_extraction_performed=false`, `db_write_performed=false`가 정확히 기록됩니다.

## Code Quality / Maintainability

구현된 연동 코드와 신규 스크립트는 높은 수준의 구조적 안정성을 유지하고 있습니다.

- **기존 동작의 비파괴 보존**: [extract_raw_articles.py](~/news-lab/scripts/extract_raw_articles.py)의 기존 CronJob 호출 엔트리포인트(`extract()`) 및 기본 구동 흐름을 일절 훼손하지 않고, 선택적 ID 리스트 추출 API(`extract_selected_article_ids()`)만 추가 정의하여 영향도를 완벽하게 제어했습니다.
- **순서 및 Limit 준수**: `get_selected_articles()` 쿼리에서 입력받은 `article_ids` 순서를 리스트 컴프리헨션을 이용해 그대로 유지하도록 처리하였고, Limit 범위 슬라이싱 처리가 올바르게 작용합니다.
- **안전한 스킵 정책**: 이미 본문 텍스트가 채워져 있는 기사, 이전에 추출 실패한 기사, 유효하지 않은 URL 혹은 `example.com` 등의 테스트 URL은 SQL 쿼리 레벨에서 사전 필터링되어 중복 시도 및 리소스를 낭비하지 않습니다.
- **단위 테스트 품질**: [test_run_raw_extraction_targets.py](~/news-lab/tests/test_run_raw_extraction_targets.py)에서 Mock을 통한 실행기 연동 및 CLI 파서 유효성 에러 등을 상세히 검증하고 있어 회귀 결함을 강력하게 방어합니다.

## Security Review

- **인증 파일 및 비밀 정보 보호**: 기존 API 주입 패턴을 준수하며, 신규 유입된 환경 변수나 하드코딩된 토큰 정보는 식별되지 않았습니다.
- **OpenAI 차단 보증**: 이 브랜치의 로직은 요약(LLM)이나 임베딩(OpenAI) 호출과 무관하므로 `args.use_embedding_provider = False`를 하드코딩하여 API Key 노출 및 무단 호출 가능성을 차단했습니다.

## Operational Risk

- **DB 격리 보장**: dry-run 상태에서는 오직 Read-only 트랜잭션만 열리므로 데이터 오염 리스크가 없습니다.
- **원문 추출 이력 구조 준수**: 실제 `--execute` 실행 시에도 오직 기존 추출기의 데이터 지속성 레이어(`raw_articles` 테이블의 INSERT/UPDATE 및 `extraction_runs` 실행 로그 기록)만 사용하도록 연동되어 기존 분석 지표를 해치지 않습니다.
- **보고서 경고 표기 개선**: 보고서 최상단에 `## Warning` 헤더를 통해 이것이 실행 계획서일 뿐 실행 승인 상태가 아님을 인지할 수 있는 Operator Warning 문구가 뚜렷하게 삽입되어 오용 리스크를 완화시켰습니다.

## Scope Control

- **범위 엄격 제한**: Kubernetes 매니페스트, CronJob 스케줄러, Supabase 마이그레이션 파일 등의 변경 사항이 전혀 없어 배포 충돌 요소를 원천 차단하였습니다.

## Verification Review

[feature-raw-extraction-target-runner.md](~/news-lab/docs/verification/feature-raw-extraction-target-runner.md)의 실행 명령과 단위 테스트 실행을 대조 확인하였습니다.

- **안전 검증 준수**: 검증자가 실제 `--execute` 명령을 포함한 프로덕션 영향 명령을 임의 실행하지 않고 Mock 및 CLI Validation 테스트로만 안전하게 검증 결과를 통과시켰음이 확인되었습니다.
- **단위 테스트 커버리지**: 단위 테스트 전체 자동 실행(75개 통과) 결과가 로그와 정확히 일치하며 신뢰할 수 있습니다.

## Documentation Review

- [feature-raw-extraction-target-runner.md](~/news-lab/docs/tasks/feature-raw-extraction-target-runner.md)(요구사항 명세서), [feature-raw-extraction-target-runner-dry-run.md](~/news-lab/docs/reports/feature-raw-extraction-target-runner-dry-run.md)(계획서), [feature-raw-extraction-target-runner.md](~/news-lab/docs/verification/feature-raw-extraction-target-runner.md)(검증 로그), [feature-raw-extraction-target-runner.md](~/news-lab/docs/pr/feature-raw-extraction-target-runner.md)(PR 초안) 간에 기재된 내용의 정밀도와 일관성이 완벽하게 부합합니다.

## Problems Found

- **없음 (None)**: 코드 결함, 로직 오류, 보안 우려 혹은 운영상 잠재적 결함이 식별되지 않았습니다.

## Required Fixes Before PR

- **없음 (None)**

## Optional Improvements

- **없음 (None)**: 설계가 요구사항 명세 대비 완결성 있게 마무리되었습니다.

## Suggested Test Commands

안전하게 dry-run 모드로 CLI 및 컴파일 상태를 자체 확인해 볼 수 있는 명령어 세트입니다.

```bash
# Python 정적 컴파일 오류 여부 확인
.venv/bin/python -m py_compile \
  app/utils/raw_extraction_targets.py \
  scripts/analyze_raw_extraction_targets.py \
  scripts/run_raw_extraction_targets.py

# 단위 테스트 전체 실행 (75개 테스트 전체 성공 보장)
.venv/bin/python -m unittest discover -s tests -v

# CLI 도움말 정상 여부 확인
.venv/bin/python scripts/run_raw_extraction_targets.py --help

# 기본 dry-run 실행 및 신규 리포트 생성 검증
.venv/bin/python scripts/run_raw_extraction_targets.py \
  --window-hours 24 \
  --max-articles 100 \
  --similarity-threshold 0.72 \
  --max-candidates-per-topic 3 \
  --max-targets-per-topic 1 \
  --limit 2 \
  --report-path docs/reports/feature-raw-extraction-target-runner-dry-run.md
```

## Verdict

**PASS**
(브랜치는 모든 도메인 안전 수칙과 기능 사양을 위반 없이 준수하며, 안전성이 검증되어 바로 승인 및 머지가 가능한 상태입니다.)
