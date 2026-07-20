# Topic Summary 제목·기간 정합성 수정

## 작업 목적

Topic Summary 제목에서 LLM이 섞어 넣은 날짜·기간 문구를 제거하고, 화면이 제목을
해석하지 않아도 정확한 기간을 표시할 수 있는 Backend API 계약을 제공한다.

## 기존 문제

Daily·3-day·Weekly prompt와 parser는 제목의 날짜·기간 표현을 막지 않았고 저장
경로도 provider의 `title_ko`를 그대로 사용했다. 3-day·Weekly API에는 raw window
datetime은 있었지만 KST 날짜 기준의 공통 end-exclusive period field가 없었다.

## 변경 내용

- 공통 sanitizer가 상대 기간, 숫자 날짜, 요일·시간 범위를 제거한 뒤 길이,
  의미와 residual pattern을 검증한다.
- 정제 실패 시 LLM 재호출 없이 keyword, 대표 기사 제목, 고정 기본 제목 순서의
  deterministic fallback을 사용한다.
- 세 prompt에 날짜·기간 제외 계약을 추가하고 새 Summary 저장 전에 sanitizer를
  통과시킨다.
- 기존 Topic window metadata만으로 3-day·Weekly의 KST `period_start`와
  end-exclusive `period_end`를 계산한다. title과 `created_at`에서는 역산하지
  않는다.
- 기존 row는 DB에서 바꾸지 않고 list/detail/Home serialization 시 제목을
  정제한다. period field가 없는 구형 cache payload는 miss로 처리한다.

## 테스트

- 관련 targeted suite: `180 passed, 68 subtests passed`
- 전체 Backend 회귀: `471 passed, 122 subtests passed`
- Repository whitespace와 금지 범위 검사: 통과

## 운영 반영

DB migration, data migration과 backfill은 필요하지 않다. Production 전체 243 row의
read-only analyzer는 사람이 실행했고 DB write와 title 원문 노출 없이 모든 오류
지표가 0임을 확인했다. 애플리케이션 배포와 API smoke verification은 기존
immutable image·manifest PR·Argo CD Manual Sync 절차에 따라 사람이 수행해야 한다.

## 확인 결과

로컬에서는 새 저장 경로, 기존 row read-time 정제, period 계산, API 하위 호환과
Home cache 재생성을 검증했다. Production period 대상 152 row도 사람이 제공한
집계에서 모두 계산에 성공했다. 다만 새 코드가 배포된 운영 API 응답 증거는 아직
없으므로 전체 Verification은 `pending`이다.

## 이번 단계의 의미

제목은 표시 문자열, 기간은 기존 Pipeline window에서 계산되는 결정적 데이터로
책임을 분리했다. Frontend는 제목을 parsing하지 않고 새 period field만으로 KST
범위를 표시할 수 있다.

## 다음 단계

사람이 Production 배포 후 3-day·Weekly Home/list/detail 응답의 기존 field 유지,
ISO date period와 정제된 title을 확인하고 sanitized 결과를 Verification에
기록한다. 그 전에는 UNIT-05를 완료 처리하지 않는다. 이후 Frontend 변경은 별도
branch에서 진행한다.
