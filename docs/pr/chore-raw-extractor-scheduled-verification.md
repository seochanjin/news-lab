# raw extractor CronJob scheduled run 검증

## 작업 내용

- `news-raw-extractor` CronJob의 scheduled run 동작을 production read-only command로 확인했습니다.
- 15차에서 pending으로 남긴 scheduled execution verification을 완료했습니다.

## 주요 변경 사항

- `docs/verification/chore-raw-extractor-scheduled-verification.md`에 실제 검증 로그 기록
- `docs/devlog/chore-raw-extractor-scheduled-verification.md`에 18차 작업 기록 정리

## 추가/변경된 API

- 없음

## DB 변경 사항

- 없음

## README 영향

- README 변경 없음
- 이번 작업은 기능 추가가 아니라 기존 CronJob scheduled run 검증 기록이므로 README 수정은 필요하지 않음

## 테스트

- `kubectl get cronjob news-raw-extractor`
- `kubectl get jobs | grep raw-extractor`
- `kubectl get pods | grep raw-extractor`
- `curl https://api.dev-scj.site/extractor/status`
- `curl "https://api.dev-scj.site/extractor/runs?limit=5"`
- `git diff --check`
- `git diff -- app db k8s scripts/collect_rss.py scripts/extract_raw_articles.py`

## 확인 결과

- CronJob `LAST SCHEDULE=11h`
- scheduled Job `news-raw-extractor-29678070` Complete
- scheduled Pod Completed, restart 0
- latest extractor run `id=3`, status success
- success_count=5, failed_count=0
- Supabase raw article 원문 5개 확인

## 비고

- Production write operation 없음
- manual Job 생성 없음
- K8s manifest 변경 없음
