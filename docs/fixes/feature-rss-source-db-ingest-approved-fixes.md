# Approved Fixes: 다중 RSS source 수집 및 DB 저장 MVP

## Approved Fixes

### Antigravity review approved fixes

Antigravity review에서 docs/ARCHITECTURE.md와 27차 task 문서 사이에 raw extractor CronJob 상태 불일치가 확인되었다.

현재 27차 task와 실제 K3s 운영 구조에서는 다음 CronJob이 존재하는 것으로 정리되어 있다.

- news-rss-collector
- news-raw-extractor

하지만 docs/ARCHITECTURE.md에는 raw article extraction CronJob이 Not Yet Implemented 항목에 남아 있는 것으로 리뷰되었다.

이번 fix에서는 docs/ARCHITECTURE.md에서 raw article extraction CronJob 상태를 실제 운영 구조와 맞게 수정한다.

수정 기준:

- news-raw-extractor CronJob이 이미 존재하는 운영 workload임을 반영한다.
- raw extractor가 매일 03:30 Asia/Seoul에 실행되는 구조라면 해당 내용을 문서에 반영한다.
- raw extractor는 python scripts/extract_raw_articles.py를 실행한다는 점을 문서화한다.
- news-rss-collector CronJob은 매일 03:00 Asia/Seoul에 실행되는 구조로 유지한다.
- 이번 fix는 문서 정합성 수정만 수행한다.
- K8s manifest, collector code, extractor code, DB migration은 변경하지 않는다.

### CodeRabbit review approved fixes

- Replace local file URI links with repository-relative paths or plain repository paths.
- Remove data-writing collector execution from default review verification commands.
- Validate `RSS_MAX_ENTRIES_PER_SOURCE` before use.
- Fix collector inserted/skipped counters so they are only applied after a successful source transaction commit.
- Clean up repetitive approved-fix bullet wording where practical.

## Rejected or Deferred Suggestions

### Antigravity deferred suggesions

Deferred 1. Article 단위 transaction isolation 개선

Antigravity review에서 현재 collector가 source 단위 transaction을 사용하기 때문에, 특정 source 안에서 단일 article insert가 database error를 발생시키면 해당 source feed의 성공 insert까지 rollback될 수 있다는 점이 개선 후보로 제안되었다.

이번 27차에서는 해당 개선을 보류한다.

보류 이유:

- 이번 task의 핵심 목표는 다중 RSS source 수집과 DB 저장 MVP를 검증하는 것이다.
- local verification에서 8개 source 모두 error_count 0으로 성공했다.
- source 단위 transaction은 현재 MVP 기준으로 동작이 단순하고 rollback 경계가 명확하다.
- entry-level transaction isolation은 collector error handling 정책을 더 세분화하는 작업이므로 후속 개선으로 분리하는 것이 적절하다.
- 28차 중복 제거 또는 collector 안정화 차수에서 재검토한다.

후속 검토 방향:

- article entry 단위 insert 실패를 source 전체 rollback 없이 skip 처리할지 검토한다.
- failed entry count를 source-level telemetry에 반영할지 검토한다.
- DB constraint error, malformed URL, published_at parsing failure를 어떻게 분리할지 검토한다.

### CodeRabbit deferred suggestions

- Add dedicated unit tests for environment parsing: deferred unless the current test structure supports it cleanly.

## Applied Changes

### Applied from Antigravity review

Codex가 다음 범위 안에서만 변경했다.

- docs/ARCHITECTURE.md

적용 내용:

- `news-rss-collector` CronJob이 매일 03:00 Asia/Seoul에 `python scripts/collect_rss.py`를 실행한다는 내용을 문서화했다.
- `news-raw-extractor` CronJob이 매일 03:30 Asia/Seoul에 `python scripts/extract_raw_articles.py`를 실행한다는 내용을 문서화했다.
- `Raw article extraction CronJob`을 Not Yet Implemented 항목에서 제거했다.

이번 fix에서 다음 파일은 변경하지 않는다.

- scripts/collect_rss.py
- app/config/rss_sources.py
- scripts/extract_raw_articles.py
- app/
- db/migrations/
- k8s/
- frontend files
- GitHub Actions workflow

### Applied from CodeRabbit review

- Replaced feature RSS review docs' local file URI links with repository-relative or plain repository paths.
- Moved data-writing collector execution out of default review verification commands and labeled it as human-approved data-writing verification.
- Added positive integer validation for `RSS_MAX_ENTRIES_PER_SOURCE`; invalid or non-positive values fall back to the default with a warning.
- Updated collector counters so per-source inserted/skipped counts are promoted to global counts only after the source transaction commits successfully.
- Cleaned up repetitive approved-fix bullet spacing and wording where practical.

## Verification Required

Codex 적용 후 사람이 다음 명령으로 확인한다.

```bash
git status --short
git diff --stat
git diff --check
git diff -- docs/ARCHITECTURE.md
git diff -- k8s
git diff -- app scripts db
```

기대 결과:

- docs/ARCHITECTURE.md만 문서 정합성 목적으로 수정되어 있어야 한다.
- git diff -- k8s에서 출력이 없어야 한다.
- scripts/collect_rss.py, app/config/rss_sources.py의 기존 구현은 이번 fix에서 불필요하게 변경되지 않아야 한다.
- DB migration이 추가되거나 수정되지 않아야 한다.
- production-impacting 변경이 없어야 한다.

필요 시 read-only 문서 확인:

```bash
grep -n "raw extractor\|raw article\|CronJob\|news-raw-extractor\|news-rss-collector" docs/ARCHITECTURE.md
```
