# Approved Fixes: Embedding 기반 topic grouping MVP

## Approved Fixes

### Fix 1. Empty embedding input 방지 및 provider 응답 개수 검증

CodeRabbit review에서 `app/utils/article_embeddings.py`의 `OpenAIEmbeddingProvider.embed()`가 `texts`가 빈 sequence인 경우에도 외부 OpenAI embeddings endpoint로 HTTP POST를 수행할 수 있다는 major issue가 확인되었다.

문제 위치:

- `app/utils/article_embeddings.py`
- `OpenAIEmbeddingProvider.embed()`

현재 구현은 다음과 같이 입력 비어 있음 여부를 확인하지 않고 요청을 보낸다.

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

- `texts`가 빈 리스트일 때도 외부 API 호출이 발생할 수 있다.
- 빈 입력에 대한 외부 호출은 비용/네트워크/오류 리스크를 만든다.
- provider 응답의 embedding 개수가 입력 text 개수와 같은지 검증하지 않는다.
- 응답 개수가 다르면 topic grouping 입력과 embedding vector가 어긋날 수 있다.

수정 기준:

- `texts`를 함수 초기에 `list(texts)`로 고정한다.
- `texts`가 비어 있으면 외부 API를 호출하지 않고 즉시 `[]`를 반환한다.
- OpenAI 응답의 `data` 길이가 입력 text 개수와 다르면 `RuntimeError` 또는 명확한 예외를 발생시킨다.
- 정렬된 embedding 결과 개수도 입력 text 개수와 일치하는지 확인한다.
- 기존 provider opt-in safety gate는 변경하지 않는다.
- 기존 model/env var 정책은 변경하지 않는다.
- classification, topic grouping, similarity threshold, JSON 출력 구조는 변경하지 않는다.
- DB schema, API, K8s manifest, collector/extractor는 변경하지 않는다.

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
- OpenAI mock response의 `data` 개수가 입력 text 개수보다 적거나 많으면 명확한 예외가 발생해야 한다.
- 정상 mock response에서는 기존처럼 `index` 기준 정렬 후 embedding list를 반환해야 한다.

## Rejected or Deferred Suggestions

### Deferred 1. OpenAI embedding provider batching/chunking

Antigravity review에서 현재 `OpenAIEmbeddingProvider`가 최대 200건의 article embedding 요청을 한 번의 HTTP POST로 처리한다는 점을 바탕으로, 향후 상한을 늘리거나 운영 규모가 커질 경우 chunk 단위 batch 호출 로직을 설계하는 optional improvement가 제안되었다.

판단:

- **Deferred**
- 이번 task의 acceptance criteria를 충족하기 위한 blocking fix는 아니다.
- 현재 script는 실제 provider 호출 시 `--max-articles`를 명시적으로 요구하고, 상한을 200건으로 제한한다.
- 30차 MVP의 목적은 대량 embedding 운영이 아니라 topic grouping pipeline과 safety gate 검증이다.
- chunking/batching은 향후 `article_embeddings` 저장 구조 또는 topic pipeline CronJob 운영화 단계에서 함께 검토하는 것이 적절하다.

후속 검토 방향:

- provider별 request size limit 확인
- article 수 증가 시 chunk size 정책 설계
- partial failure/retry 정책 설계
- embedding input hash 기반 중복 호출 방지
- batch별 cost estimate와 execution summary 기록
- DB 저장 구조 도입 시 already embedded article 재사용 정책 검토

## Applied Changes

Applied:

- `app/utils/article_embeddings.py`
  - `OpenAIEmbeddingProvider.embed()` 시작 시 입력을 list로 고정했다.
  - Empty input은 외부 HTTP 요청 없이 즉시 `[]`를 반환하도록 변경했다.
  - Provider 응답 `data` 개수가 입력 text 개수와 다르면 `RuntimeError`를
    발생시키도록 변경했다.
  - 정렬된 embedding 결과 개수도 입력 text 개수와 일치하는지 검증한다.
- `tests/test_article_embeddings.py`
  - Empty input에서 `requests.post`가 호출되지 않음을 확인하는 테스트를
    추가했다.
  - 응답 embedding이 입력보다 적거나 많은 경우 명확한 예외가 발생하는
    테스트를 추가했다.
  - 기존 정상 응답 index 정렬 테스트를 유지했다.

Not changed:

- Provider opt-in safety gate, model/env var 정책
- Classification, topic grouping, similarity threshold, JSON 출력 구조
- `scripts/analyze_topic_groups.py`, `app/utils/topic_grouping.py`
- DB schema/migration, API, K8s, collector/extractor, frontend
- Deferred batching/chunking suggestion

Not performed:

- DB migration, Supabase SQL, DB write
- Real OpenAI embedding provider call
- K8s apply/rollout, production curl verification
- Git push, git merge

## Verification Required

Fix 적용 후 다음 명령을 실행하고 실제 결과를 `docs/verification/feature-embedding-topic-grouping.md`에 기록한다.

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

필요 시 dry-run 대표 명령을 한 번 더 확인한다.

```bash
.venv/bin/python scripts/analyze_topic_groups.py --window-hours 24 --max-articles 100 --dry-run
```

보안 검사:

```bash
git grep -n -i -E "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
rg -n -i "K3S_TOKEN|node-token|admin-password|password:|private key|BEGIN|ssh-key|API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env" app/utils/article_embeddings.py app/utils/topic_grouping.py scripts/analyze_topic_groups.py tests/test_article_embeddings.py tests/test_topic_grouping.py tests/test_analyze_topic_groups.py
```

검증 기준:

- 단위 테스트가 통과해야 한다.
- Python compile이 통과해야 한다.
- CLI help가 정상 출력되어야 한다.
- `OpenAIEmbeddingProvider.embed([])`는 외부 HTTP 요청 없이 `[]`를 반환해야 한다.
- OpenAI mock response의 embedding 개수가 입력 개수와 다르면 명확한 예외가 발생해야 한다.
- 정상 OpenAI mock response는 `index` 기준으로 정렬된 embedding list를 반환해야 한다.
- K8s manifest 변경이 없어야 한다.
- DB migration이 없어야 한다.
- DB write path가 없어야 한다.
- 기본 실행에서 OpenAI embedding provider를 호출하지 않아야 한다.
- 실제 provider 호출은 `--use-embedding-provider`, `OPENAI_EMBEDDING_API_KEY`, 명시적 `--max-articles`가 모두 있을 때만 가능해야 한다.
- production-impacting command는 실행하지 않는다.
