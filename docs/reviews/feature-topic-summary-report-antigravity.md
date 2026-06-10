# Antigravity Review: Raw text 기반 topic summary report MVP

## Review Summary

이 리뷰는 [feature/topic-summary-report](~/news-lab) 브랜치에 구현된 Raw text 기반 Topic Summary Report MVP 기능의 품질, 안정성 및 요구사항 충족 여부를 검증합니다.

구현된 시스템은 DB에서 원문이 이미 확보된 기사를 대상으로, deterministic 요약 및 OpenAI API 연동을 통한 한국어 주제 요약 리포트를 생성하는 기능을 구현하고 있습니다. CLI 진입점 파일인 [generate_topic_summary_report.py](~/news-lab/scripts/generate_topic_summary_report.py)와 요약 도메인 헬퍼 파일인 [topic_summary.py](~/app/utils/topic_summary.py)가 신규 생성되었습니다.

검증 결과, API 호출과 DB 쓰기를 제어하는 다중 안전장치가 사양대로 정상 구현되었으며, 인프라 변경 없이 완벽하게 Read-only 환경에서 리포트가 생성됨을 확인하여 최종 **PASS** 판정을 내립니다.

## Requirement Coverage

[feature-topic-summary-report.md](~/news-lab/docs/tasks/feature-topic-summary-report.md)에 기술된 모든 기능 요건이 충족되었습니다.

- **원문 대상 요약 추출**: 확보된 `raw_text` 기사만 요약용 입력값으로 사용하도록 선별 처리됩니다.
- **deterministic/mock 요약 우선**: 기본 CLI 실행은 어떠한 외부 LLM/OpenAI 호출 없이 로컬 deterministic 요약기([DeterministicSummaryProvider](~/news-lab/app/utils/topic_summary.py#L66))를 이용해 처리됩니다.
- **Provider Opt-in 게이트**: 실제 API 호출은 `--use-summary-provider` 옵션과 `OPENAI_SUMMARY_API_KEY` 환경변수가 주어질 때만 허용됩니다.
- **다양한 한도 제어(Limit Flags)**: `--max-topics`, `--max-articles-per-topic`, `--max-raw-chars-per-article` 인수를 지원하여 실행 비용 및 대량 처리를 안전하게 예방합니다.
- **보고서 수치 표기**: 생성된 마크다운 리포트에 DB 쓰기 여부(`db_write_performed=false`) 및 원문 추출 여부(`raw_extraction_performed=false`)가 정확히 기재됩니다.

## Approved Fix Coverage

[feature-topic-summary-report-approved-fixes.md](~/news-lab/docs/fixes/feature-topic-summary-report-approved-fixes.md)의 **Approved Fix 1**이 완벽하게 해결되어 구현에 적용되었음을 확인하였습니다.

- **원문 확보 토픽 우선순위 배치**: `max_topics` 제한을 적용하기 전에 전체 토픽 기사들의 원문 유무(`ready` 여부)를 먼저 평가하고, `ready` 상태 토픽들을 `insufficient_raw_text` 상태 토픽보다 배열 앞선으로 우선 정렬시킵니다.
- **우선 정렬 규칙 준수**: 원문 기사 수가 많은 순, 매체 수가 많은 순, 그리고 기존의 토픽 기사 ID 정렬 순서에 기초하여 안정적으로 정렬을 수행합니다.
- **단위 테스트 검증 완료**: [test_topic_summary.py](~/news-lab/tests/test_topic_summary.py)에 정렬 우선순위 및 한도 경계선 테스트들이 촘촘하게 추가되어 통과함을 검증했습니다.

## Code Quality / Maintainability

- **개인정보/기사원문 보호**: `raw_text` 전문이 보고서나 JSON 파일에 노출되지 않도록 `_public_topic_input`에서 기사 메타데이터(기사 ID, 제목, 매체, 원문 길이 등)만 반환하고 원문 내용은 제거하는 필터링 로직이 안전하게 정착되었습니다.
- **신뢰 수치 처리**: `confidence` 신뢰도를 AI 모델의 반환 결과로 처리하고, deterministic 로직에서는 기사 개수에 연동하여 소수점 둘째 자리까지 반올림 연산 처리하여 정보 오인 가능성을 줄였습니다.
- **안정적 예외 처리**: API 반환 객체 파싱 중 필수 반환 규격(`title_ko`, `summary_ko` 등)이 누락될 경우 즉각 예외를 발생시키도록 예외 처리문이 정교하게 설계되었습니다.

## Security Review

- **비밀키 노출 차단**: `OPENAI_SUMMARY_API_KEY` 인증 정보가 하드코딩되지 않고 쉘 환경 변수로부터 바인딩되며, 에러 시 로그 파일 등에 Key 문자열이 절대 유실/노출되지 않음을 확인하였습니다.
- **원문 전문 안전 격리**: 마크다운 출력 및 JSON Summary 결과 데이터에 실제 기사 내용(`raw_text`)이 유출되지 않도록 안전 필터링이 구현되었습니다.

## Operational Risk

- **DB 및 K3s 영향도 무(None)**: 이 브랜치는 DB의 마이그레이션, K8s manifest의 변동, CronJob 스케줄러 수정 등이 전혀 없어 서비스 가동 상태에 영향을 주지 않는 완전 격리 MVP입니다.
- **인공 팩트(Hallucination) 방지 지시**: LLM 호출 프롬프트(`_provider_prompt`) 상에 *"사실을 추가하지 말고"*라는 제약 명령을 강력하게 부여해, 뉴스 본문에 존재하지 않는 잘못된 도메인 사실을 생성(Hallucination)하는 리스크를 통제했습니다.
- **의사결정 혼선 방지**: 생성 보고서 하단에 *"Summary outputs are report-only and are not stored in the database."*라는 명확한 문구를 주입해, 이것이 즉시 API 사용자에게 노출되는 프로덕션 데이터가 아님을 운영자에게 뚜렷하게 경고하고 있습니다.
- **자동 폴백 배제**: `gpt-5-mini` 비교 모델 사용 시 임의의 자동 폴백(Fallback)이나 무단 복수 시도(Retry Loop)로 인한 API 과부하 및 오버차지 위험 없이 단발성 오류 투척으로 안정성있게 처리되었습니다.

## Scope Control

- **범위 제어 합격**: `git status` 기준 신규 분석 파일과 단위 테스트 추가 파일만 생성되었으며, 기존 [analyze_raw_extraction_targets.py](~/news-lab/scripts/analyze_raw_extraction_targets.py) 등과의 의존성을 해치는 코드 조각이 확인되지 않았습니다.

## Verification Review

[feature-topic-summary-report.md](~/news-lab/docs/verification/feature-topic-summary-report.md)의 실행 결과를 실증 분석했습니다.

- **실제 연동 검증 완료**: Sandbox DB 연결을 위한 `DATABASE_URL` 에러 및 Rerun을 거친 실제 로컬 결정론적 리포트 생성, 그리고 `gpt-5-nano`와 `gpt-5-mini`를 직접 호출해 취득한 실제 마크다운 보고서가 리포트 폴더에 안전하게 기록되었음이 물리적으로 확인되었습니다.
- **테스트 무결성**: 90개의 전체 단위 테스트가 로컬 환경에서 일체 오류 없이 성공하였음이 보증됩니다.

## Documentation Review

- 요구사항 명세서, PR 초안, 개발 로그, Approved Fixes문 및 검증 결과 문서 상의 연계 지표(기사 3개 검토 성공 등)가 완전히 일치하여 미래의 코드 리딩에 최적의 가독성을 부여합니다.

## Problems Found

- **없음 (None)**: 버그, 보안 취약점, 명세 이탈 내역이 발견되지 않았습니다.

## Required Fixes Before PR

- **없음 (None)**

## Optional Improvements

- **없음 (None)**

## Suggested Test Commands

```bash
# Python 정적 컴파일 오류 여부 확인
.venv/bin/python -m py_compile \
  app/utils/topic_summary.py \
  scripts/generate_topic_summary_report.py

# 단위 테스트 전체 실행 (90개 전체 통과 확인)
.venv/bin/python -m unittest discover -s tests -v

# CLI 도움말 정상 여부 확인
.venv/bin/python scripts/generate_topic_summary_report.py --help

# 로컬 결정론적 임베딩/요약 리포트 재생성 테스트
.venv/bin/python scripts/generate_topic_summary_report.py \
  --window-hours 24 \
  --max-topics 3 \
  --max-articles-per-topic 2 \
  --max-raw-chars-per-article 3000 \
  --report-path docs/reports/feature-topic-summary-report-deterministic.md
```

## Verdict

**PASS**
(브랜치는 모든 설계 표준, 데이터 보안 수칙 및 승인된 Fixes를 준수하였고, 실제 Provider 검증 리포트와 deterministic actual-data 리포트가 정상 반영되었음을 보장합니다.)
