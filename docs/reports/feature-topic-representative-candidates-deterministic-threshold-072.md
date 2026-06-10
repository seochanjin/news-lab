# Topic representative candidate review

## Summary

- Human review status: **Pending**
- Analyzed article count: 100
- Topic candidate count: 96
- Multi-article topic count: 2
- Singleton topic count: 94
- Report detail topic count: 2
- Singleton topic details included: `False`
- Representative candidate count: 99
- Similarity threshold: 0.72
- Embedding provider/model: `deterministic` / `deterministic-hash-v1`
- DB write performed: `false`

## Scoring Policy

- Candidate score compares representative candidates within the same topic.
- Candidate score must not be used as an importance score across topics.
- Overall raw extraction priority requires a separate follow-up policy.

- `importance` weight: 0.20
- `topic_seed` weight: 0.15
- `similarity` weight: 0.20
- `source_diversity` weight: 0.10
- `information` weight: 0.15
- `recency` weight: 0.15
- `category` weight: 0.05

## Topic Candidates

### topic-0014

- Article count: 2
- Source count: 1
- Category distribution: `{'politics': 1, 'sports': 1}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | EU plans to ban Russian soldiers from bloc in fresh sanctions on Moscow | The Guardian World | world | politics | 7 | 1.0000 | 2026-06-09 15:12:38+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8511 |
| yes | 2 | Is the pope a Real Madrid fan? Leo’s admission upsets Barcelona faithful | The Guardian World | world | sports | 4 | 0.7380 | 2026-06-09 15:55:15+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.5458 |

#### Candidate Details

- **Article 725 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1326, recency=0.1485, category=0.0500`
- **Article 725 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 725 recency time:** 2026-06-09 15:12:38+00:00 (`published_at`)
- **Article 725 human review status:** Pending
- **Article 724 components:** `importance=0.0400, topic_seed=0.0000, similarity=0.1476, source_diversity=0.0250, information=0.1332, recency=0.1500, category=0.0500`
- **Article 724 selection reason:** Selected for recency, topic similarity, title/summary information.
- **Article 724 recency time:** 2026-06-09 15:55:15+00:00 (`published_at`)
- **Article 724 human review status:** Pending

### topic-0086

- Article count: 4
- Source count: 1
- Category distribution: `{'tech': 4}`
- Language distribution: `{'en': 4}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Claude Fable 5 | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 16:58:01+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.6852 |
| yes | 2 | System Card: Claude Fable 5 and Claude Mythos 5 [pdf] | Hacker News | tech | unknown | 2 | 0.8356 | 2026-06-09 16:58:13+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4507 |
| yes | 3 | Using Optical Aberrations to Distinguish Real Astronomical Transients | Hacker News | tech | unknown | 2 | 0.7456 | 2026-06-09 15:12:30+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4387 |
| no |  | The LD_DEBUG environment variable (2012) | Hacker News | tech | unknown | 2 | 0.7660 | 2026-06-09 17:29:05+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4301 |

#### Candidate Details

- **Article 644 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0288, recency=0.1489, category=0.0375`
- **Article 644 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 644 recency time:** 2026-06-09 16:58:01+00:00 (`published_at`)
- **Article 644 human review status:** Pending
- **Article 646 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1671, source_diversity=0.0250, information=0.0522, recency=0.1489, category=0.0375`
- **Article 646 selection reason:** Selected for topic similarity, recency, title/summary information.
- **Article 646 recency time:** 2026-06-09 16:58:13+00:00 (`published_at`)
- **Article 646 human review status:** Pending
- **Article 668 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1491, source_diversity=0.0250, information=0.0618, recency=0.1453, category=0.0375`
- **Article 668 selection reason:** Selected for topic similarity, recency, title/summary information.
- **Article 668 recency time:** 2026-06-09 15:12:30+00:00 (`published_at`)
- **Article 668 human review status:** Pending
- **Article 655 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1532, source_diversity=0.0250, information=0.0444, recency=0.1500, category=0.0375`
- **Article 655 selection reason:** Not selected within the candidate limit.
- **Article 655 recency time:** 2026-06-09 17:29:05+00:00 (`published_at`)
- **Article 655 human review status:** Pending

## Human Review Notes

- Candidate suitability: Pending
- Source diversity suitability: Pending
- Candidate count suitability: Pending
