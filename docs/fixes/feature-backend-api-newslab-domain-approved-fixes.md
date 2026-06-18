# Approved Fixes: backend api.newslab.ai.kr 도메인/TLS 전환

## Approved Fixes

None.

## Rejected or Deferred Suggestions

None.

## Applied Changes

None.

## Verification Required

PR merge 이후 사람이 다음 운영 검증을 수행해야 한다.

- api.newslab.ai.kr DNS A record 확인
- api.newslab.ai.kr AAAA record 없음 확인
- server-side dry-run
- 실제 K3s apply
- news-api-newslab-tls Certificate 생성 및 Ready=True 확인
- ACME Order valid 확인
- news-api-newslab-tls Secret 생성 확인
- https://api.newslab.ai.kr/health 정상 응답 확인
- 기존 https://api.dev-scj.site/health 정상 유지 확인
- 신규/기존 API health endpoint 반복 curl 안정성 확인
