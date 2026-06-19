\# Approved Fixes: 저장된 article embedding을 daily topic pipeline에 연결

## Approved Fixes

### 1. Embedding acquirer 계약 위반을 fail-fast 처리

CodeRabbit review에서 embedding acquisition loop의 `try/except Exception` 범위가 지나치게 넓다는 문제가 확인됐다.

현재 구현은 다음 두 종류의 오류를 모두 article-level failure로 처리한다.

```text
기사별 운영 실패
- Provider 호출 실패
- DB 조회 또는 저장 실패
- 특정 article 처리 실패

Pipeline 계약 위반
- EmbeddingResult가 아닌 반환값
- 지원하지 않는 status
- Embedding vector가 없는 성공 결과
```

기사별 운영 실패는 나머지 article 처리를 계속하기 위해 격리하는 것이 맞다.

반면 pipeline 계약 위반은 callback 구현 또는 integration의 결함이므로 `failed` 통계로 낮춰 처리하지 않고 즉시 예외를 발생시켜야 한다.

승인된 수정:

- [x] `embedding_acquirer(article)` 호출만 기사별 `try/except`로 감싼다.
- [x] Acquirer 호출 중 발생한 예외는 기존처럼 해당 article의 `failed`로 기록한다.
- [x] 실패 article 처리 후 명시적으로 `continue`한다.
- [x] 반환값 검사는 `try/except` 바깥으로 이동한다.
- [x] 반환값이 `EmbeddingResult`가 아니면 `TypeError`를 발생시킨다.
- [x] Status가 `created`, `updated`, `reused` 중 하나가 아니면 `ValueError`를 발생시킨다.
- [x] Embedding vector가 없으면 `ValueError`를 발생시킨다.
- [x] 계약 위반은 `embedding_failures` 목록이나 `failed` 집계에 포함하지 않는다.
- [x] 정상 결과에 대해서만 article, vector와 상태 통계를 추가한다.
- [x] 기존 실패 격리, 순서 유지와 최소 clustering 입력 가드를 유지한다.

권장 구현:

```python
for article in articles:
    try:
        result = embedding_acquirer(article)
    except Exception as error:
        stats["failed"] += 1
        failure = {
            "article_id": article.get("id"),
            "error": _safe_embedding_error(error),
        }
        failures.append(failure)
        LOGGER.warning(
            "article embedding failed: article_id=%s error=%s",
            failure["article_id"],
            failure["error"],
        )
        continue

    if not isinstance(result, EmbeddingResult):
        raise TypeError(
            "embedding acquirer returned an invalid result"
        )

    if result.status not in {"created", "updated", "reused"}:
        raise ValueError(
            f"unsupported embedding status: {result.status}"
        )

    if result.embedding is None:
        raise ValueError(
            "embedding result does not include a vector"
        )

    clustering_articles.append(article)
    embeddings.append(result.embedding)
    stats[result.status] += 1
```

### 테스트 보완

다음 계약 위반 테스트를 추가하거나 기존 테스트를 보완한다.

- [x] Acquirer가 `EmbeddingResult` 외의 객체를 반환하면 `TypeError`
- [x] Acquirer가 허용되지 않은 status를 반환하면 `ValueError`
- [x] Acquirer가 vector 없는 성공 결과를 반환하면 `ValueError`
- [x] 위 계약 위반은 article failure로 기록되지 않음
- [x] Provider 예외는 여전히 article-level failure로 격리됨
- [x] Provider 실패 이후 정상 article은 계속 처리됨
- [x] 정상 article과 vector 순서가 유지됨
- [x] 기존 집계 및 최소 입력 가드 테스트가 유지됨

## Rejected or Deferred Suggestions

### 1. Embedding 예외 유형 전면 세분화

Deferred.

이상적으로는 `embedding_acquirer`가 발생시킬 수 있는 운영 오류를 명시적인 예외 계층으로 구분할 수 있다.

예:

```text
EmbeddingProviderError
EmbeddingStorageError
EmbeddingInputError
```

그러나 현재 저장 모듈의 예외 계약을 전면 변경하면 이번 CodeRabbit 지적보다 범위가 커진다.

이번 수정에서는 다음 경계만 명확히 한다.

```text
Acquirer 호출 중 발생한 오류
→ article-level failure

Acquirer 반환값 계약 오류
→ pipeline fail-fast
```

예외 계층 세분화는 provider 및 batch 처리 구조를 정리할 때 별도 작업으로 검토한다.

### 2. 실패율 기반 pipeline 중단 정책

Deferred.

현재 정책은 일부 article embedding이 실패하더라도 정상 vector가 최소 2건 이상이면 clustering을 계속한다.

향후 다음 기준을 추가할 수 있다.

- 전체 후보 대비 embedding 실패율
- 연속 provider 실패 횟수
- 최소 정상 처리 비율
- Provider outage 판단

이번 작업의 목적은 계약 위반을 숨기지 않는 것이므로 실패율 정책은 변경하지 않는다.

### 3. 허용 embedding status 공통 상수화

Optional / Deferred.

`created`, `updated`, `reused` 집합이 여러 모듈에서 반복되면 공통 상수화할 수 있다.

현재 한 위치에서만 검사한다면 별도 추상화 없이 유지해도 된다.

### 4. 운영 E2E 재실행

Deferred unless runtime path changed.

이번 수정은 정상 `EmbeddingResult`의 처리 흐름이나 저장·재사용 로직을 변경하지 않고, 잘못된 callback 반환값의 오류 처리 방식만 변경한다.

기존 production E2E에서는 다음이 이미 확인됐다.

```text
첫 실행
candidate_articles=45
embedding_created=42
embedding_reused=3
embedding_failed=0
topic_count=3

동일 조건 재실행
candidate_articles=38
embedding_created=0
embedding_updated=0
embedding_reused=38
embedding_failed=0
topic_count=3
```

관련 단위 테스트와 전체 회귀가 통과하면 운영 provider를 다시 호출하는 E2E는 필수로 요구하지 않는다.

다만 구현 과정에서 정상 반환 처리 경로까지 변경됐다면 소량 수동 실행을 다시 검토한다.

## Applied Changes

적용 상태:

- Approved Fix 1
  - 상태: 적용 및 로컬 검증 완료
- 계약 위반 단위 테스트
  - 상태: 적용 및 로컬 검증 완료
- 전체 회귀 검증
  - 상태: 적용 및 로컬 검증 완료

- Approved Fix 1 적용
  - `embedding_acquirer(article)` 호출만 article-level 예외 격리 범위에 남겼다.
  - 반환 타입, status와 vector 계약 검사를 예외 격리 범위 밖으로 이동했다.
  - 계약 위반이 즉시 `TypeError` 또는 `ValueError`로 전파되도록 수정했다.
  - Provider 및 개별 article 오류의 기존 격리 동작은 유지했다.

- 테스트 보완
  - 잘못된 반환 타입 fail-fast 검증 추가
  - 잘못된 status fail-fast 검증 추가
  - vector 없는 결과 fail-fast 검증 추가
  - article-level provider failure 회귀 검증 유지

- 회귀 검증
  - 관련 30 tests 통과
  - 전체 145 tests 통과
  - compileall 통과
  - git diff check 통과
  - 금지 영역 diff 없음

운영 E2E는 재실행하지 않았다. 이번 변경은 정상 `EmbeddingResult` 처리 경로가
아니라 잘못된 callback 반환 계약의 오류 전파 경계만 변경하며, 기존 production
E2E 결과는 verification 문서에 기록되어 있다.

## Verification Required

### 1. 관련 단위 테스트

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

확인 기준:

- Acquirer의 실제 처리 예외는 해당 article의 `failed`로 집계된다.
- 실패한 article 이후 정상 article 처리가 계속된다.
- 잘못된 반환 타입은 `TypeError`로 즉시 전파된다.
- 지원하지 않는 status는 `ValueError`로 즉시 전파된다.
- Vector 없는 성공 결과는 `ValueError`로 즉시 전파된다.
- 계약 위반은 `embedding_failures` 또는 `failed` 통계로 변환되지 않는다.
- 정상 article/vector 순서가 유지된다.
- `created`, `updated`, `reused`, `failed` 집계가 유지된다.
- 정상 vector 2건 미만 시 기존 가드가 유지된다.
- CronJob command와 schedule contract가 유지된다.

### 2. 전체 회귀 검증

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

확인 기준:

- Python compile 통과
- 전체 unittest 통과
- Whitespace 오류 없음
- `.env`와 credential이 변경에 포함되지 않음

### 3. 변경 범위 확인

```bash
git diff --name-only
git diff --stat
git diff -- \
  k8s \
  db/migrations \
  app/routers \
  app/main.py \
  requirements.txt
```

확인 기준:

- 변경은 daily pipeline과 관련 tests 및 review 문서에 한정된다.
- K3s manifest 변경 없음
- DB migration 변경 없음
- Public API 변경 없음
- Dependency 변경 없음

### 4. 기존 Production E2E 근거 유지

기존 production 검증 결과:

```text
첫 실행
candidate_articles=45
embedding_created=42
embedding_updated=0
embedding_reused=3
embedding_failed=0
clustering_input_count=45
topic_count=3
pipeline_elapsed_seconds=135.851984
```

```text
동일 조건 재실행
candidate_articles=38
embedding_created=0
embedding_updated=0
embedding_reused=38
embedding_failed=0
clustering_input_count=38
topic_count=3
pipeline_elapsed_seconds=87.256793
```

이번 수정 후 다음이 유지되는지 단위 테스트로 확인한다.

- 정상 `EmbeddingResult` 처리 경로
- Stored embedding reuse
- Clustering 입력
- Topic 저장 이전 분석 결과
- 상태 집계

정상 runtime 경로를 변경하지 않았다면 외부 provider를 사용하는 운영 E2E 재실행은 선택 사항이다.

### 5. Antigravity 재검토

Codex 적용 후 기존 Antigravity review 문서에 `Re-review 1`을 추가한다.

확인 항목:

- CodeRabbit CR-1 해결 여부
- Article-level 운영 실패 격리 유지
- 반환 계약 위반 fail-fast 여부
- 신규 테스트 근거
- Scope 밖 변경 없음
- 미해결 PR blocker 없음

권장 재검토 구조:

```md
## Re-review 1

### Existing Problems Status

### Approved Fixes Verification

### Verification Evidence

### New Problems Found

### Required Fixes Before PR

### Verdict
```

### 6. 최종 완료 조건

다음 조건을 모두 충족하면 PR 진행 가능하다.

- Embedding acquirer 반환 계약 검사가 article-level 예외 격리 범위 밖에 있음
- 잘못된 반환 타입이 fail-fast함
- 잘못된 status가 fail-fast함
- Vector 없는 결과가 fail-fast함
- Provider와 개별 article 오류는 계속 격리됨
- 정상 결과 통계와 순서가 유지됨
- 관련 테스트 통과
- 전체 회귀 테스트 통과
- Antigravity 재검토 완료
- 미해결 Required Fix 없음
