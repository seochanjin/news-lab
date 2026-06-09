# CodeRabbit Review: Embedding 기반 topic grouping MVP

## Review Summary

CodeRabbit review에서 `app/utils/article_embeddings.py`의 `OpenAIEmbeddingProvider.embed()` 처리 방식에 대한 major issue가 확인되었다.

현재 구현은 `texts`가 빈 sequence인 경우에도 OpenAI embeddings endpoint로 HTTP POST를 수행할 수 있다. 또한 OpenAI 응답의 embedding 개수가 입력 text 개수와 일치하는지 검증하지 않는다.

이번 issue는 기본 dry-run 경로나 deterministic local embedding provider에는 영향을 주지 않는다. 실제 OpenAI provider는 `--use-embedding-provider`, `OPENAI_EMBEDDING_API_KEY`, 명시적 `--max-articles`가 모두 있을 때만 사용된다.

다만 외부 API 호출 경로의 비용/안전성을 더 강화하기 위해 PR 전 수정하는 것이 적절하다.

## Problems Found

### Problem 1. Empty input에서도 OpenAI embeddings endpoint를 호출할 수 있음

대상 파일:

- `app/utils/article_embeddings.py`

대상 함수:

- `OpenAIEmbeddingProvider.embed()`

현재 구현은 다음 흐름이다.

```python
def embed(self, texts: Sequence[str]) -> list[list[float]]:
    response = requests.post(
        self.endpoint,
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        json={"model": self.model, "input": list(texts)},
        timeout=self.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()["data"]
    ordered = sorted(data, key=lambda item: item["index"])
    return [item["embedding"] for item in ordered]
```

문제점:

- `texts`가 빈 sequence여도 외부 OpenAI API 호출이 발생할 수 있다.
- 빈 입력에 대한 외부 호출은 불필요한 네트워크 요청이다.
- 빈 입력에 대한 외부 호출은 비용/오류 리스크를 만든다.
- MVP의 cost-safety 원칙과 맞지 않는다.

### Problem 2. OpenAI 응답 embedding 개수 검증이 없음

현재 구현은 응답 `data`를 `index` 기준으로 정렬한 뒤 embedding list를 반환한다.

하지만 다음을 검증하지 않는다.

- 응답 `data` 개수와 입력 text 개수가 같은지
- 정렬 후 embedding 개수와 입력 text 개수가 같은지

응답 개수가 입력 개수와 다르면 article과 embedding vector의 대응 관계가 깨질 수 있다. 이 경우 topic grouping 결과가 잘못될 수 있으므로 명확한 예외를 발생시키는 것이 안전하다.

## Required Fixes Before PR

### Fix 1. `OpenAIEmbeddingProvider.embed()` empty input early return 및 응답 개수 검증

수정 기준:

- `texts`를 함수 초기에 `list(texts)`로 한 번만 변환한다.
- 변환된 input list가 비어 있으면 `requests.post`를 호출하지 않고 즉시 `[]`를 반환한다.
- OpenAI 응답의 `data` 길이가 입력 text 개수와 일치하는지 검증한다.
- 응답 개수가 일치하지 않으면 `RuntimeError` 또는 명확한 예외를 발생시킨다.
- 기존 `index` 기준 정렬 동작은 유지한다.
- 정렬 후 embedding list 개수도 입력 text 개수와 일치하는지 확인한다.
- 정상 응답에서는 기존처럼 입력 순서에 맞는 embedding list를 반환한다.

예상 구현 방향:

```python
def embed(self, texts: Sequence[str]) -> list[list[float]]:
    input_texts = list(texts)
    if not input_texts:
        return []

    response = requests.post(
        self.endpoint,
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        json={"model": self.model, "input": input_texts},
        timeout=self.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()["data"]

    if len(data) != len(input_texts):
        raise RuntimeError(
            f"Embedding response count mismatch: expected {len(input_texts)}, got {len(data)}"
        )

    ordered = sorted(data, key=lambda item: item["index"])
    embeddings = [item["embedding"] for item in ordered]

    if len(embeddings) != len(input_texts):
        raise RuntimeError(
            f"Ordered embedding count mismatch: expected {len(input_texts)}, got {len(embeddings)}"
        )

    return embeddings
```

테스트 기준:

- `OpenAIEmbeddingProvider.embed([])`는 `requests.post`를 호출하지 않고 `[]`를 반환해야 한다.
- OpenAI mock response의 `data` 개수가 입력 text 개수보다 적으면 명확한 예외가 발생해야 한다.
- OpenAI mock response의 `data` 개수가 입력 text 개수보다 많아도 명확한 예외가 발생해야 한다.
- 정상 mock response는 기존처럼 `index` 기준 정렬 후 embedding list를 반환해야 한다.

## Optional Improvements

### Optional 1. Provider batching/chunking

Antigravity review에서도 언급된 내용이다.

현재 실제 provider 호출은 `--max-articles` 상한 200건으로 제한되어 있으므로 이번 PR의 blocking issue는 아니다.

다만 향후 상한을 늘리거나 운영 CronJob으로 전환할 경우 다음 개선을 검토한다.

- provider별 request size limit 확인
- chunk size 정책 설계
- partial failure/retry 정책 설계
- batch별 cost estimate 출력
- embedding input hash 기반 중복 호출 방지
- 이미 embedding된 article 재사용 정책

이번 PR에서는 적용하지 않는다.

## Suggested Test Commands

Fix 적용 후 다음 명령을 실행한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py
.venv/bin/python scripts/analyze_topic_groups.py --help
git status --short --branch
git diff --stat
git diff --check
git diff -- k8s
git diff -- app scripts db tests
```

필요 시 대표 dry-run을 재확인한다.

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
```

보안 grep:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py tests/test_article_embeddings.py tests/test_topic_grouping.py tests/test_analyze_topic_groups.py
```

## Risk Notes

- 이번 issue는 기본 dry-run 경로의 직접 결함은 아니다.
- 기본 실행은 deterministic local embedding provider를 사용하며 OpenAI API를 호출하지 않는다.
- 실제 OpenAI provider 호출은 명시적 opt-in 경로에서만 가능하다.
- 그러나 provider 구현 자체는 빈 입력과 응답 개수 불일치를 방어해야 한다.
- 수정 범위는 `app/utils/article_embeddings.py`와 관련 단위 테스트에 한정한다.
- DB schema, API, K8s manifest, collector, raw extractor는 변경하지 않는다.
- 실제 OpenAI provider 호출은 이번 fix verification에서 수행하지 않는다.
