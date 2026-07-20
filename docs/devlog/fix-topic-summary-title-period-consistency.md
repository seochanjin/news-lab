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

- 관련 targeted suite: `188 passed, 68 subtests passed`
- 전체 Backend 회귀: `479 passed, 122 subtests passed`
- Repository whitespace와 금지 범위 검사: 통과

위 테스트 결과는 구현·approved fixes 검증 때 실행한 기존 evidence다. Production
완료 문서화 단계에서는 Backend pytest를 다시 실행하지 않았다.

## 운영 반영

DB migration, data migration과 backfill은 필요하지 않다. Production 전체 243 row의
read-only analyzer는 사람이 실행했고 DB write와 title 원문 노출 없이 모든 오류
지표가 0임을 확인했다. 이후 Backend PR #66과 GitOps image PR #67 merge, Argo CD
`Synced / Healthy`와 rollout 성공을 사람이 확인했다. Backend Pod는 `2/2 Ready`,
restart 0이며 Deployment와 CronJob 4개가 같은 immutable image를 사용했다.
Source merge commit은 `980a237515377418fdae7fe3fb2f945c011237ce`, Argo CD
revision은 `d8ff31929347de1e7d4f0f6941e08297a5117f17`이며 배포 image는
`seocj/news-api:980a237515377418fdae7fe3fb2f945c011237ce`다.

Health·version과 3-day·Weekly Home/list/detail API는 모두 HTTP 200이었다. Sanitized
response 42건에서 invalid title, 잔존 날짜·기간 pattern, missing period와 invalid
period가 모두 0이고 validation exit가 0이었다. DB migration, 기존 DB row update,
Pipeline·CronJob 수동 실행과 Secret 변경·조회는 없었다. Production title 원문과
credential은 기록하지 않았고 임시 API response 파일은 삭제됐다.

## 확인 결과

로컬에서는 새 저장 경로, 기존 row read-time 정제, period 계산, API 하위 호환과
Home cache 재생성을 검증했다. Production period 대상 152 row도 사람이 제공한
집계에서 모두 계산에 성공했다. 배포 후 Production API 8개 endpoint와 response
42건의 title·period 계약도 통과해 전체 Verification은 `passed`다.

## 이번 단계의 의미

제목은 표시 문자열, 기간은 기존 Pipeline window에서 계산되는 결정적 데이터로
책임을 분리했다. Frontend는 제목을 parsing하지 않고 새 period field만으로 KST
범위를 표시할 수 있다.

## 다음 단계

Backend UNIT-01~05와 Production 검증은 완료됐다. Frontend의 KST 기간 표시와 UTC
datetime 직접 노출 제거는 별도 branch에서 진행하며, 이후 프로젝트 문서 정합화와
동결 절차를 검토한다.
