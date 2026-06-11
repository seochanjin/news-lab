# Daily topic pipeline report

## Summary

- Dry-run: `true`
- Execute requested: `false`
- Window hours: 24
- Article count: 116
- Topic candidate count: 108
- Selected topic count: 5
- Selected article IDs: `[944, 974, 947, 975, 924, 898, 989, 952, 993, 956, 891]`
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `false`
- Raw extraction success/failure: 0 / 0
- DB write performed: `false`

## Selected Topics

### topic-0001

- Article count: 4
- Source count: 3
- Selected article IDs: `[944, 974, 947]`
- Similarity scores: `{944: 1.0, 974: 0.7781, 947: 0.7799}`

### topic-0023

- Article count: 2
- Source count: 2
- Selected article IDs: `[975, 924]`
- Similarity scores: `{975: 1.0, 924: 0.7937}`

### topic-0039

- Article count: 2
- Source count: 2
- Selected article IDs: `[898, 989]`
- Similarity scores: `{898: 1.0, 989: 0.7975}`

### topic-0056

- Article count: 2
- Source count: 2
- Selected article IDs: `[952, 993]`
- Similarity scores: `{952: 1.0, 993: 0.8137}`

### topic-0027

- Article count: 2
- Source count: 2
- Selected article IDs: `[956, 891]`
- Similarity scores: `{956: 1.0, 891: 0.7896}`

## Safety

- Embedding vectors and topic candidate intermediate results are memory-only.
- Actual raw extraction and DB writes require explicit `--execute`.
- Provider calls require explicit provider flags and API keys.
