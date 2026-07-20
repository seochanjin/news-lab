# Topic Summary 제목·기간 정합성 수정

## 작업 내용

Daily·3-day·Weekly Topic Summary 제목을 신뢰할 수 없는 LLM 입력으로 취급해 저장
전 정제하고, 3-day·Weekly API가 기존 기간 metadata로 계산한 KST 날짜 범위를
명시적으로 반환하도록 수정했다. 기존 row는 DB update 없이 API read 시점에 같은
제목 정제를 적용한다.

## 주요 변경 사항

- 공통 title sanitizer가 날짜·기간 표현을 제거하고 잔존 pattern, 길이와 의미를
  검증한다. 실패 시 keyword, 대표 기사 제목, 고정 기본 제목 순으로 결정적인
  fallback을 만든다.
- 세 Summary prompt에 날짜·연도·요일·기간·시간 범위를 제목에서 제외하는 계약을
  추가하고, Daily·3-day·Weekly 저장 직전에 sanitizer를 적용한다.
- Topic row의 기존 window metadata를 검증해 3-day와 Weekly의
  `period_start`, `period_end`를 end-exclusive ISO date로 계산한다.
- 3-day·Weekly Home/list/detail 응답은 기존 field를 유지하면서 period field를
  추가한다. 기존 title은 read-time에 정제하고 구형 Home cache payload는
  재생성한다.
- Invalid period metadata가 섞이면 Home/list는 해당 row만 warning 후 제외하고
  valid row를 유지한다. Detail은 내부 값을 노출하지 않는 고정 detail의 HTTP
  500으로 변환한다.
- Production 전체 243 row는 사람이 read-only analyzer로 확인했으며 원문 title
  노출이나 DB write 없이 period/sanitize 오류가 0건이었다.
- Backend PR #66과 GitOps image PR #67 merge 후 Argo CD
  `Synced / Healthy`, rollout 성공, Backend Pod `2/2 Ready`와 restart 0을
  확인했다. Deployment와 CronJob 4개는 동일한 immutable image를 사용한다.
  Source merge commit은 `980a237515377418fdae7fe3fb2f945c011237ce`, Argo CD
  revision은 `d8ff31929347de1e7d4f0f6941e08297a5117f17`이며 배포 image는
  `seocj/news-api:980a237515377418fdae7fe3fb2f945c011237ce`다.
- Health·version과 3-day·Weekly Home/list/detail Production API가 모두 HTTP
  200이었고, response 42건의 title·period validation 오류는 0건이었다.

## 테스트

- Invalid API·Home 경계: `40 passed, 14 subtests passed`
- Targeted: `188 passed, 68 subtests passed`
- 전체 Backend 회귀: `479 passed, 122 subtests passed`
- `git diff --check`: 통과
- DB migration, dependency, K3s manifest diff: 없음

## 확인 결과

- 새 저장 title의 sanitizer·deterministic fallback과 세 Pipeline 전달 경로를
  fake repository/provider로 검증했다.
- 3-day·Weekly list/detail/Home의 기존 field 유지, period field와 cache 하위
  호환 동작을 검증했다.
- Home/list valid+invalid 혼합 row에서 valid item 유지, Home 전부 invalid 시 빈
  payload, detail invalid metadata의 고정 500을 양쪽 API에서 검증했다.
- Production read-only 집계: 전체 243 row, sanitize 변경 204, 유지 39,
  fallback 0, period 성공 152, 계산 실패·invalid range·residual pattern·미처리
  실패 모두 0.
- Production 배포: Backend PR #66 및 GitOps image PR #67 merge, Argo CD
  `Synced / Healthy`, rollout passed, Pod `2/2 Ready`, restart 0.
- Production API: health·version과 3-day·Weekly Home/list/detail 8개 endpoint 모두
  HTTP 200. 검증한 42건에서 invalid title, residual date/period pattern, missing
  period와 invalid period 모두 0, validation exit 0.

## 비고

- DB schema·migration·backfill과 기존 row update는 없다.
- Pipeline stage·CronJob·K3s resource·Redis key/TTL은 변경하지 않았다.
- 사람이 제공한 sanitized Production evidence를 근거로 UNIT-05와 전체
  Verification을 완료했다. DB migration, 기존 row update, Pipeline·CronJob 수동
  실행과 Secret 변경·조회는 없었다.
- Production title 원문과 credential은 기록하지 않았고 사람이 사용한 임시 API
  response 파일은 삭제됐다.
- Approved FIX-01~05를 적용했으며 CodeRabbit thread resolve는 commit·CI 확인 후
  사람이 수행할 항목으로 남아 있다.
- Frontend의 KST 기간 표시와 UTC datetime 직접 노출 제거는 별도 branch 범위다.
- 이 문서 완료 단계에서는 Backend pytest를 재실행하지 않았으며 위 테스트 수치는
  기존 Verification에 기록된 실제 실행 결과다.
