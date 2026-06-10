# Raw extraction target review

## Warning

- 이 report는 `deterministic-hash-v1` 기반 검증용 산출물이다.
- 현재 target 목록은 실제 raw extraction 승인 목록이 아니다.
- 실제 extraction 대상 검토는 human-approved embedding provider 결과를 기준으로 수행해야 한다.
- 이 report는 복수 target 정책 comparison/비교용 산출물이다.
- max2/max3 결과는 실제 raw extraction 실행 승인을 의미하지 않는다.

## Summary

- Human review status: **Pending**
- Analyzed article count: 100
- Topic candidate count: 96
- Multi-article topic count: 2
- Report detail topic count: 2
- Extraction target count: 4
- Max targets per topic: 2
- Similarity threshold: 0.72
- Embedding provider/model: `deterministic` / `deterministic-hash-v1`
- DB write performed: `false`
- Raw extraction performed: `false`

## Target Policy

- Candidate score ranks representative candidates within the same topic.
- Candidate score is not used to prioritize topics against each other.
- Multi-article topics are ordered by source count, article count, then recency.
- Only `pending` or `not_extracted` representative candidates can become targets.
- Existing raw text is marked `already_extracted`; failed extraction is not retried.

## Topic Targets

### topic-0086

- Article count: 4
- Source count: 1
- Extraction target count: 2
- Target status counts: `{'backup': 1, 'skipped': 1, 'target': 2}`

| Target Status | Rank | Title | Source | Raw Status | Candidate Score |
| --- | ---: | --- | --- | --- | ---: |
| target | 1 | Claude Fable 5 | Hacker News | not_extracted | 0.6852 |
| target | 2 | System Card: Claude Fable 5 and Claude Mythos 5 [pdf] | Hacker News | not_extracted | 0.4507 |
| backup | 3 | Using Optical Aberrations to Distinguish Real Astronomical Transients | Hacker News | not_extracted | 0.4387 |
| skipped |  | The LD_DEBUG environment variable (2012) | Hacker News | not_extracted | 0.4301 |

#### Target Decisions

- **Article 644 (target):** Selected representative candidate rank 1; raw status is `not_extracted`.
- **Article 646 (target):** Selected representative candidate rank 2; raw status is `not_extracted`.
- **Article 668 (backup):** Eligible representative candidate rank 3 exceeds the topic target limit of 2.
- **Article 655 (skipped):** Article is outside the representative candidate limit.

### topic-0014

- Article count: 2
- Source count: 1
- Extraction target count: 2
- Target status counts: `{'target': 2}`

| Target Status | Rank | Title | Source | Raw Status | Candidate Score |
| --- | ---: | --- | --- | --- | ---: |
| target | 1 | EU plans to ban Russian soldiers from bloc in fresh sanctions on Moscow | The Guardian World | not_extracted | 0.8511 |
| target | 2 | Is the pope a Real Madrid fan? Leo’s admission upsets Barcelona faithful | The Guardian World | not_extracted | 0.5458 |

#### Target Decisions

- **Article 725 (target):** Selected representative candidate rank 1; raw status is `not_extracted`.
- **Article 724 (target):** Selected representative candidate rank 2; raw status is `not_extracted`.

## Human Review Notes

- Target suitability: Pending
- Topic ordering suitability: Pending
- Max targets per topic suitability: Pending
