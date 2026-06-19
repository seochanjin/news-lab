# CodeRabbit Review: 저장된 article embedding을 daily topic pipeline에 연결

## Review Summary

CodeRabbit review에서 article별 embedding 실패 격리 범위가 지나치게 넓다는 문제가 확인됐다.

현재 pipeline은 `embedding_acquirer(article)` 호출뿐 아니라 반환값에 대한 계약 검사까지 하나의 `try/except Exception` 안에서 처리한다.

따라서 다음과 같은 구현 계약 위반도 일반적인 기사별 embedding 실패로 기록되고 pipeline이 계속 진행된다.

- `embedding_acquirer`가 `EmbeddingResult`가 아닌 값을 반환
- 지원하지 않는 embedding status 반환
- 성공 상태이지만 embedding vector가 없는 결과 반환

이러한 오류는 외부 provider나 특정 기사 데이터로 인한 개별 실패가 아니라 pipeline과 embedding 모듈 사이의 integration contract가 깨진 것이다.

계약 위반을 article-level failure로 낮춰 처리하면 다음 문제가 발생할 수 있다.

- 구현 회귀가 즉시 드러나지 않음
- 모든 기사가 실패해도 원인이 숨겨짐
- 일부 기사만 남은 상태에서 topic이 생성됨
- 빈 결과 또는 부분 결과가 정상 실행처럼 기록됨
- 잘못된 callback 구현이 production에서 조용히 통과함

기사별 운영 실패는 계속 격리하되, 반환값 계약 위반은 fail-fast하도록 수정해야 한다.

## Problems Found

### CR-1. Embedding acquirer 계약 위반이 기사별 실패로 숨겨짐

- 심각도: Major
- 유형: Error handling / Integration contract
- 대상:
  - `scripts/run_daily_topic_pipeline.py`
  - embedding acquisition loop

현재 구조:

```python
for article in articles:
    try:
        result = embedding_acquirer(article)

        if not isinstance(result, EmbeddingResult):
            raise TypeError(...)

        if result.status not in {"created", "updated", "reused"}:
            raise ValueError(...)

        if result.embedding is None:
            raise ValueError(...)

        ...
    except Exception as error:
        stats["failed"] += 1
        failures.append(...)
```

문제점:

- Callback 반환 타입 오류가 `embedding_failed` 한 건으로 처리된다.
- 지원하지 않는 status가 pipeline contract 오류로 노출되지 않는다.
- 성공 상태에 vector가 없는 심각한 integration 오류도 pipeline이 계속 진행한다.
- Test double 또는 실제 구현의 회귀가 topic 결과 일부 누락으로만 나타날 수 있다.

구분해야 할 오류:

```text
격리 대상
- 특정 article의 provider 호출 실패
- 특정 article의 DB 조회 또는 저장 실패
- 특정 article 입력 처리 실패

Fail-fast 대상
- EmbeddingResult가 아닌 반환값
- 허용되지 않은 status
- 성공 결과에 embedding vector 없음
```

승인 수정 방향:

1. `embedding_acquirer(article)` 호출만 기사별 `try/except` 범위에 둔다.
2. 반환값 계약 검사는 `try/except` 바깥에서 수행한다.
3. 계약 위반은 `TypeError` 또는 `ValueError`로 즉시 전파한다.
4. 기사별 운영 실패의 기존 격리 동작은 유지한다.
5. 정상 결과의 article/vector 순서와 통계 집계는 유지한다.

권장 구조:

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
        raise TypeError("embedding acquirer returned an invalid result")

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

## Required Fixes Before PR

- [ ] `embedding_acquirer(article)` 호출과 반환 계약 검사를 서로 다른 오류 처리 범위로 분리한다.
- [ ] Provider 또는 DB 등 기사별 처리 예외는 기존처럼 `failed`로 집계하고 다음 article을 계속 처리한다.
- [ ] `EmbeddingResult`가 아닌 반환값은 즉시 `TypeError`를 발생시킨다.
- [ ] `created`, `updated`, `reused` 외의 status는 즉시 `ValueError`를 발생시킨다.
- [ ] Embedding vector가 없는 성공 결과는 즉시 `ValueError`를 발생시킨다.
- [ ] 계약 위반을 `embedding_failures`에 추가하지 않는다.
- [ ] 정상 article과 vector의 순서를 유지한다.
- [ ] 기존 article-level failure isolation 동작을 유지한다.
- [ ] 관련 단위 테스트와 전체 회귀 테스트를 통과한다.

## Optional Improvements

### 1. 허용 상태 상수화

현재 허용 상태 집합:

```python
{"created", "updated", "reused"}
```

이 값이 여러 위치에서 반복된다면 공통 상수로 분리할 수 있다.

예:

```python
VALID_EMBEDDING_STATUSES = frozenset(
    {"created", "updated", "reused"}
)
```

현재 한 곳에서만 사용한다면 필수 수정은 아니다.

### 2. 기사별 격리 예외 범위 축소

현재 `embedding_acquirer` 호출에서 발생하는 모든 `Exception`을 기사별 실패로 처리한다.

향후 오류 유형이 명확해지면 다음처럼 운영 오류만 명시적으로 잡는 방식을 검토할 수 있다.

- Provider API 오류
- SQLAlchemy/DBAPI 오류
- 입력 데이터 처리 오류

다만 현재 저장 모듈의 예외 계약이 세분화되어 있지 않다면 이번 작업에서 무리하게 좁히지 않는다.

### 3. 실패율 임계치

현재는 정상 embedding이 최소 2건 이상이면 일부 실패가 있어도 clustering을 진행한다.

향후 다음 정책을 별도 작업에서 검토할 수 있다.

```text
embedding 실패율이 일정 비율 이상
→ pipeline 전체 실패 또는 경고
```

이번 CodeRabbit 수정 범위에는 포함하지 않는다.

## Suggested Test Commands

### 관련 단위 테스트

```bash
python -m unittest \
  tests.test_run_daily_topic_pipeline \
  tests.test_article_embedding_storage \
  tests.test_daily_topic_pipeline_cronjob_manifest
```

필수 테스트 사례:

- `embedding_acquirer`가 provider 오류를 발생시키면 해당 article만 `failed`
- 실패 article 이후 정상 article은 계속 처리
- 반환값이 `EmbeddingResult`가 아니면 `TypeError`
- 지원하지 않는 status면 `ValueError`
- Embedding vector가 없으면 `ValueError`
- 계약 위반은 `embedding_failures`로 낮춰 처리되지 않음
- 정상 결과의 article/vector 순서 유지
- `created`, `updated`, `reused`, `failed` 통계 유지
- 정상 vector 2건 미만 시 clustering 건너뜀

### 전체 회귀 테스트

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
```

### 변경 범위 확인

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

금지 영역 diff는 없어야 한다.

## Risk Notes

이 문제는 외부 provider의 일시적 실패보다 integration regression을 숨긴다는 점에서 위험하다.

예를 들어 callback 구현이 잘못되어 모든 article에 `None`을 반환해도 현재 구조에서는 다음처럼 처리될 수 있다.

```text
candidate_articles=40
embedding_failed=40
clustering_input_count=0
```

Pipeline이 최소 입력 가드로 종료되더라도 실제 원인은 callback 계약 위반인데 단순 기사 실패처럼 보인다.

일부만 잘못된 결과를 반환하면 더 위험하다.

```text
candidate_articles=40
embedding_failed=10
clustering_input_count=30
topic 생성 계속
```

이 경우 integration 결함이 있는 상태에서 부분 topic 결과가 저장될 수 있다.

수정 후에는 다음 정책이 명확해진다.

```text
기사별 운영 실패
→ 격리하고 계속 진행

프로그램 반환 계약 위반
→ 즉시 실패하고 원인 노출
```

수정 범위는 embedding acquisition loop와 관련 테스트에 한정한다.

다음은 변경하지 않는다.

- Article embedding 저장 계약
- Provider, model과 dimension
- Clustering 알고리즘과 threshold
- Topic 저장 방식
- CronJob command와 schedule
- K3s manifest
- DB schema와 migration
- Public API와 frontend
