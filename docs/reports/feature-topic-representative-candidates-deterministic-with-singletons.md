# Topic representative candidate review

## Summary

- Human review status: **Pending**
- Analyzed article count: 100
- Topic candidate count: 96
- Multi-article topic count: 3
- Singleton topic count: 93
- Report detail topic count: 96
- Singleton topic details included: `True`
- Representative candidate count: 100
- Similarity threshold: 0.70
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

### topic-0001

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | 'Conflict Trends': Civil wars, international fights hit high | DW English | world | world | 14 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8785 |

#### Candidate Details

- **Article 778 components:** `importance=0.1400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0885, recency=0.1500, category=0.0500`
- **Article 778 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 778 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 778 human review status:** Pending

### topic-0002

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Florida shaken by 6.1-magnitude earthquake off coast of Cuba | The Guardian World | world | world | 12 | 1.0000 | 2026-06-09 16:30:08+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8960 |

#### Candidate Details

- **Article 710 components:** `importance=0.1200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1260, recency=0.1500, category=0.0500`
- **Article 710 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 710 recency time:** 2026-06-09 16:30:08+00:00 (`published_at`)
- **Article 710 human review status:** Pending

### topic-0003

- Article count: 1
- Source count: 1
- Category distribution: `{'sports': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Rich countries do better in women’s football but understanding why matters, not just for the Matildas | The Guardian World | world | sports | 12 | 1.0000 | 2026-06-09 15:00:05+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.9200 |

#### Candidate Details

- **Article 719 components:** `importance=0.1200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1500, recency=0.1500, category=0.0500`
- **Article 719 selection reason:** Selected for topic similarity, title/summary information, recency.
- **Article 719 recency time:** 2026-06-09 15:00:05+00:00 (`published_at`)
- **Article 719 human review status:** Pending

### topic-0004

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Israeli attack on Tyre in Lebanon kills eight as evacuation ordered for Christian quarter | The Guardian World | world | unknown | 9 | 1.0000 | 2026-06-09 15:58:09+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8709 |

#### Candidate Details

- **Article 729 components:** `importance=0.0900, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1434, recency=0.1500, category=0.0375`
- **Article 729 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 729 recency time:** 2026-06-09 15:58:09+00:00 (`published_at`)
- **Article 729 human review status:** Pending

### topic-0005

- Article count: 1
- Source count: 1
- Category distribution: `{'ai': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Why Anthropic has the edge over OpenAI in IPO race | DW English | world | ai | 9 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8318 |

#### Candidate Details

- **Article 771 components:** `importance=0.0900, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0918, recency=0.1500, category=0.0500`
- **Article 771 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 771 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 771 human review status:** Pending

### topic-0006

- Article count: 1
- Source count: 1
- Category distribution: `{'security': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | CISA gives US federal agencies three days to fix a VPN bug under attack by a ransomware gang | TechCrunch | tech | security | 8 | 1.0000 | 2026-06-09 17:40:08+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.8266 |

#### Candidate Details

- **Article 574 components:** `importance=0.0800, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0966, recency=0.1500, category=0.0500`
- **Article 574 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 574 recency time:** 2026-06-09 17:40:08+00:00 (`published_at`)
- **Article 574 human review status:** Pending

### topic-0007

- Article count: 1
- Source count: 1
- Category distribution: `{'ai': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple says its AI is still private, even when it's running on Google's servers | Ars Technica | tech | ai | 8 | 1.0000 | 2026-06-09 13:05:49+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.8008 |

#### Candidate Details

- **Article 599 components:** `importance=0.0800, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0708, recency=0.1500, category=0.0500`
- **Article 599 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 599 recency time:** 2026-06-09 13:05:49+00:00 (`published_at`)
- **Article 599 human review status:** Pending

### topic-0008

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Jersey teenage politician congratulated by Trump says he is not a fan | The Guardian World | world | politics | 8 | 1.0000 | 2026-06-09 14:00:52+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8614 |

#### Candidate Details

- **Article 726 components:** `importance=0.0800, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1314, recency=0.1500, category=0.0500`
- **Article 726 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 726 recency time:** 2026-06-09 14:00:52+00:00 (`published_at`)
- **Article 726 human review status:** Pending

### topic-0009

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Iranians struggle to buy food as war drives up prices | DW English | world | world | 8 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8218 |

#### Candidate Details

- **Article 770 components:** `importance=0.0800, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0918, recency=0.1500, category=0.0500`
- **Article 770 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 770 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 770 human review status:** Pending

### topic-0010

- Article count: 1
- Source count: 1
- Category distribution: `{'ai': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Sandstone raises $30M to bring AI to in-house legal teams | TechCrunch | tech | ai | 7 | 1.0000 | 2026-06-09 13:47:25+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7764 |

#### Candidate Details

- **Article 583 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0564, recency=0.1500, category=0.0500`
- **Article 583 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 583 recency time:** 2026-06-09 13:47:25+00:00 (`published_at`)
- **Article 583 human review status:** Pending

### topic-0011

- Article count: 1
- Source count: 1
- Category distribution: `{'ai': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Where is the AI jobs crisis? | Hacker News | tech | ai | 7 | 1.0000 | 2026-06-09 17:29:17+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7572 |

#### Candidate Details

- **Article 652 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0372, recency=0.1500, category=0.0500`
- **Article 652 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 652 recency time:** 2026-06-09 17:29:17+00:00 (`published_at`)
- **Article 652 human review status:** Pending

### topic-0012

- Article count: 2
- Source count: 1
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | 'Sloppenheimer:' Amazon Employees Mock the Company's AI on Slack | Hacker News | tech | ai | 7 | 1.0000 | 2026-06-09 15:59:41+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7757 |
| yes | 2 | The LD_DEBUG environment variable (2012) | Hacker News | tech | unknown | 2 | 0.7035 | 2026-06-09 17:29:05+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4176 |

#### Candidate Details

- **Article 657 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0588, recency=0.1469, category=0.0500`
- **Article 657 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 657 recency time:** 2026-06-09 15:59:41+00:00 (`published_at`)
- **Article 657 human review status:** Pending
- **Article 655 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1407, source_diversity=0.0250, information=0.0444, recency=0.1500, category=0.0375`
- **Article 655 selection reason:** Selected for recency, topic similarity, title/summary information.
- **Article 655 recency time:** 2026-06-09 17:29:05+00:00 (`published_at`)
- **Article 655 human review status:** Pending

### topic-0013

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Documents reveal concerns over US company’s proposed gas fracking in WA’s Kimberley region | The Guardian World | world | politics | 7 | 1.0000 | 2026-06-09 15:00:03+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8640 |

#### Candidate Details

- **Article 720 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1440, recency=0.1500, category=0.0500`
- **Article 720 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 720 recency time:** 2026-06-09 15:00:03+00:00 (`published_at`)
- **Article 720 human review status:** Pending

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

### topic-0015

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Italy’s foreign minister slams Israel’s Ben-Gvir over ‘flip-flop’ comments | Al Jazeera | world | politics | 7 | 1.0000 | 2026-06-09 12:00:18+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.8001 |

#### Candidate Details

- **Article 751 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0801, recency=0.1500, category=0.0500`
- **Article 751 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 751 recency time:** 2026-06-09 12:00:18+00:00 (`published_at`)
- **Article 751 human review status:** Pending

### topic-0016

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Murder of Lyhanna, 11, enrages France and turns up heat on government | BBC World | world | politics | 6 | 1.0000 | 2026-06-09 14:27:37+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7829 |

#### Candidate Details

- **Article 678 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0729, recency=0.1500, category=0.0500`
- **Article 678 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 678 recency time:** 2026-06-09 14:27:37+00:00 (`published_at`)
- **Article 678 human review status:** Pending

### topic-0017

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | ‘Osprey cam’ streams life of nesting seabirds perched at tip of 55 metre-long Queensland rainforest canopy crane | The Guardian World | world | unknown | 6 | 1.0000 | 2026-06-09 15:00:02+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8475 |

#### Candidate Details

- **Article 721 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1500, recency=0.1500, category=0.0375`
- **Article 721 selection reason:** Selected for topic similarity, title/summary information, recency.
- **Article 721 recency time:** 2026-06-09 15:00:02+00:00 (`published_at`)
- **Article 721 human review status:** Pending

### topic-0018

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | After Nagorno-Karabakh, Armenians vote for peace over nationalism | Al Jazeera | world | politics | 6 | 1.0000 | 2026-06-09 17:04:00+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7757 |

#### Candidate Details

- **Article 735 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0657, recency=0.1500, category=0.0500`
- **Article 735 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 735 recency time:** 2026-06-09 17:04:00+00:00 (`published_at`)
- **Article 735 human review status:** Pending

### topic-0019

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Six countries sanction enablers of settler violence in occupied West Bank | Al Jazeera | world | world | 6 | 1.0000 | 2026-06-09 15:07:32+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7886 |

#### Candidate Details

- **Article 739 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0786, recency=0.1500, category=0.0500`
- **Article 739 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 739 recency time:** 2026-06-09 15:07:32+00:00 (`published_at`)
- **Article 739 human review status:** Pending

### topic-0020

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | UK government ‘concerned’ by abuse claims against West Ham co-owner | Al Jazeera | world | politics | 6 | 1.0000 | 2026-06-09 13:33:43+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7889 |

#### Candidate Details

- **Article 745 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0789, recency=0.1500, category=0.0500`
- **Article 745 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 745 recency time:** 2026-06-09 13:33:43+00:00 (`published_at`)
- **Article 745 human review status:** Pending

### topic-0021

- Article count: 1
- Source count: 1
- Category distribution: `{'climate': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Venezuelans flood capital Caracas streets, demanding free elections | Al Jazeera | world | climate | 6 | 1.0000 | 2026-06-09 12:30:10+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7787 |

#### Candidate Details

- **Article 748 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0687, recency=0.1500, category=0.0500`
- **Article 748 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 748 recency time:** 2026-06-09 12:30:10+00:00 (`published_at`)
- **Article 748 human review status:** Pending

### topic-0022

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Will Israel's troops take over more of southern Lebanon? | DW English | world | world | 6 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8003 |

#### Candidate Details

- **Article 759 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0903, recency=0.1500, category=0.0500`
- **Article 759 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 759 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 759 human review status:** Pending

### topic-0023

- Article count: 1
- Source count: 1
- Category distribution: `{'business': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | EU: Youth involvement in synthetic opioids smuggling rises | DW English | world | business | 6 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7943 |

#### Candidate Details

- **Article 762 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0843, recency=0.1500, category=0.0500`
- **Article 762 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 762 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 762 human review status:** Pending

### topic-0024

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | US-Israel: What are the allegations of espionage all about? | DW English | world | world | 6 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8087 |

#### Candidate Details

- **Article 766 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0987, recency=0.1500, category=0.0500`
- **Article 766 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 766 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 766 human review status:** Pending

### topic-0025

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Will Mexico's World Cup party be spoiled by teacher protest? | DW English | world | world | 6 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.8000 |

#### Candidate Details

- **Article 781 components:** `importance=0.0600, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0900, recency=0.1500, category=0.0500`
- **Article 781 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 781 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 781 human review status:** Pending

### topic-0026

- Article count: 1
- Source count: 1
- Category distribution: `{'security': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Anthropic’s Claude Fable 5 is a version of Mythos the public can access today | TechCrunch | tech | security | 5 | 1.0000 | 2026-06-09 17:00:00+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.8050 |

#### Candidate Details

- **Article 575 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1050, recency=0.1500, category=0.0500`
- **Article 575 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 575 recency time:** 2026-06-09 17:00:00+00:00 (`published_at`)
- **Article 575 human review status:** Pending

### topic-0027

- Article count: 1
- Source count: 1
- Category distribution: `{'security': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | High-severity vulnerability in Linux caused by a single errant character | Ars Technica | tech | security | 5 | 1.0000 | 2026-06-09 15:12:43+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7618 |

#### Candidate Details

- **Article 596 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0618, recency=0.1500, category=0.0500`
- **Article 596 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 596 recency time:** 2026-06-09 15:12:43+00:00 (`published_at`)
- **Article 596 human review status:** Pending

### topic-0028

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | The Top New Features in Apple’s iOS 27 and iPadOS 27 | Wired | tech | unknown | 5 | 1.0000 | 2026-06-09 17:03:37+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.7628 |

#### Candidate Details

- **Article 615 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0753, recency=0.1500, category=0.0375`
- **Article 615 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 615 recency time:** 2026-06-09 17:03:37+00:00 (`published_at`)
- **Article 615 human review status:** Pending

### topic-0029

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Longevity Startup Doses First Human in Bid to Reverse Age-Related Sight Loss | Wired | tech | tech | 5 | 1.0000 | 2026-06-09 13:23:53+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.8032 |

#### Candidate Details

- **Article 617 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1032, recency=0.1500, category=0.0500`
- **Article 617 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 617 recency time:** 2026-06-09 13:23:53+00:00 (`published_at`)
- **Article 617 human review status:** Pending

### topic-0030

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Man reportedly shot at Kenya protest against US Ebola quarantine centre | BBC World | world | politics | 5 | 1.0000 | 2026-06-09 15:08:50+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7834 |

#### Candidate Details

- **Article 677 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0834, recency=0.1500, category=0.0500`
- **Article 677 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 677 recency time:** 2026-06-09 15:08:50+00:00 (`published_at`)
- **Article 677 human review status:** Pending

### topic-0031

- Article count: 1
- Source count: 1
- Category distribution: `{'sports': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Fifa working to resolve revoked Iran tickets | BBC World | world | sports | 4 | 1.0000 | 2026-06-09 17:50:37+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7767 |

#### Candidate Details

- **Article 684 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0867, recency=0.1500, category=0.0500`
- **Article 684 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 684 recency time:** 2026-06-09 17:50:37+00:00 (`published_at`)
- **Article 684 human review status:** Pending

### topic-0032

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Trump says Iran shot down US helicopter over Hormuz, vows to respond | Al Jazeera | world | politics | 4 | 1.0000 | 2026-06-09 16:54:15+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7662 |

#### Candidate Details

- **Article 736 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0762, recency=0.1500, category=0.0500`
- **Article 736 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 736 recency time:** 2026-06-09 16:54:15+00:00 (`published_at`)
- **Article 736 human review status:** Pending

### topic-0033

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Trump says in ‘final throes’ of peace deal but at least 8 killed in Lebanon | Al Jazeera | world | politics | 4 | 1.0000 | 2026-06-09 13:41:52+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7695 |

#### Candidate Details

- **Article 743 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0795, recency=0.1500, category=0.0500`
- **Article 743 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 743 recency time:** 2026-06-09 13:41:52+00:00 (`published_at`)
- **Article 743 human review status:** Pending

### topic-0034

- Article count: 1
- Source count: 1
- Category distribution: `{'sports': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | World Cup opening ceremony: Who’s performing, when it starts, how to watch | Al Jazeera | world | sports | 4 | 1.0000 | 2026-06-09 12:33:42+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7689 |

#### Candidate Details

- **Article 747 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0789, recency=0.1500, category=0.0500`
- **Article 747 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 747 recency time:** 2026-06-09 12:33:42+00:00 (`published_at`)
- **Article 747 human review status:** Pending

### topic-0035

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | South Africa migration crisis: Ramaphosa's plan faces doubt | DW English | world | politics | 4 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7872 |

#### Candidate Details

- **Article 763 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0972, recency=0.1500, category=0.0500`
- **Article 763 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 763 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 763 human review status:** Pending

### topic-0036

- Article count: 1
- Source count: 1
- Category distribution: `{'sports': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Germany upbeat as final World Cup preparations begin | DW English | world | sports | 4 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7857 |

#### Candidate Details

- **Article 767 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0957, recency=0.1500, category=0.0500`
- **Article 767 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 767 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 767 human review status:** Pending

### topic-0037

- Article count: 1
- Source count: 1
- Category distribution: `{'climate': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | The most powerful El Nino in a century could be on its way | DW English | world | climate | 4 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7884 |

#### Candidate Details

- **Article 772 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0984, recency=0.1500, category=0.0500`
- **Article 772 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 772 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 772 human review status:** Pending

### topic-0038

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Kenya: Protester shot dead at rally against US Ebola center | DW English | world | politics | 4 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7779 |

#### Candidate Details

- **Article 777 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0879, recency=0.1500, category=0.0500`
- **Article 777 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 777 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 777 human review status:** Pending

### topic-0039

- Article count: 1
- Source count: 1
- Category distribution: `{'politics': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Why the 2026 World Cup is so controversial | DW English | world | politics | 4 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7782 |

#### Candidate Details

- **Article 783 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0882, recency=0.1500, category=0.0500`
- **Article 783 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 783 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 783 human review status:** Pending

### topic-0040

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple’s foldable iPhone could be just around the corner | TechCrunch | tech | tech | 3 | 1.0000 | 2026-06-09 16:22:56+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7430 |

#### Candidate Details

- **Article 577 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0630, recency=0.1500, category=0.0500`
- **Article 577 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 577 recency time:** 2026-06-09 16:22:56+00:00 (`published_at`)
- **Article 577 human review status:** Pending

### topic-0041

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Lovable says it has hit $500M in annualized revenue, with 1 million new projects a week | TechCrunch | tech | tech | 3 | 1.0000 | 2026-06-09 13:00:00+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7766 |

#### Candidate Details

- **Article 584 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0966, recency=0.1500, category=0.0500`
- **Article 584 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 584 recency time:** 2026-06-09 13:00:00+00:00 (`published_at`)
- **Article 584 human review status:** Pending

### topic-0042

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Trump says Iran shot down US helicopter and vows to respond | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 17:32:15+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7371 |

#### Candidate Details

- **Article 674 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0696, recency=0.1500, category=0.0375`
- **Article 674 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 674 recency time:** 2026-06-09 17:32:15+00:00 (`published_at`)
- **Article 674 human review status:** Pending

### topic-0043

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Israeli air strikes hit Lebanese city of Tyre despite Iranian warning to stop attacks | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 17:47:41+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7533 |

#### Candidate Details

- **Article 675 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0858, recency=0.1500, category=0.0375`
- **Article 675 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 675 recency time:** 2026-06-09 17:47:41+00:00 (`published_at`)
- **Article 675 human review status:** Pending

### topic-0044

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Two reportedly killed as women take part in rare protest in Afghanistan | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 16:44:23+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7425 |

#### Candidate Details

- **Article 679 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0750, recency=0.1500, category=0.0375`
- **Article 679 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 679 recency time:** 2026-06-09 16:44:23+00:00 (`published_at`)
- **Article 679 human review status:** Pending

### topic-0045

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Scrapping of Franco-German fighter jet leaves allies at odds on defence future | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 14:54:36+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7422 |

#### Candidate Details

- **Article 680 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0747, recency=0.1500, category=0.0375`
- **Article 680 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 680 recency time:** 2026-06-09 14:54:36+00:00 (`published_at`)
- **Article 680 human review status:** Pending

### topic-0046

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | 'Please send help': Crew's distress call after ship hit by US missile | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 13:42:26+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7446 |

#### Candidate Details

- **Article 689 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0771, recency=0.1500, category=0.0375`
- **Article 689 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 689 recency time:** 2026-06-09 13:42:26+00:00 (`published_at`)
- **Article 689 human review status:** Pending

### topic-0047

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Man shot dead during protest against proposed US Ebola quarantine facility in Kenya | The Guardian World | world | unknown | 3 | 1.0000 | 2026-06-09 17:13:20+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8073 |

#### Candidate Details

- **Article 704 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1398, recency=0.1500, category=0.0375`
- **Article 704 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 704 recency time:** 2026-06-09 17:13:20+00:00 (`published_at`)
- **Article 704 human review status:** Pending

### topic-0048

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Former Air Canada pilot charged after allegedly flying without proper license for 16 years | The Guardian World | world | unknown | 3 | 1.0000 | 2026-06-09 17:10:30+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8115 |

#### Candidate Details

- **Article 709 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1440, recency=0.1500, category=0.0375`
- **Article 709 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 709 recency time:** 2026-06-09 17:10:30+00:00 (`published_at`)
- **Article 709 human review status:** Pending

### topic-0049

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Mexico prepares for World Cup opening match amid protests | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 17:51:30+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7353 |

#### Candidate Details

- **Article 734 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0678, recency=0.1500, category=0.0375`
- **Article 734 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 734 recency time:** 2026-06-09 17:51:30+00:00 (`published_at`)
- **Article 734 human review status:** Pending

### topic-0050

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Kenya’s police crack down on protest against US Ebola centre in Nanyuki | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 16:16:44+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7455 |

#### Candidate Details

- **Article 737 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0780, recency=0.1500, category=0.0375`
- **Article 737 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 737 recency time:** 2026-06-09 16:16:44+00:00 (`published_at`)
- **Article 737 human review status:** Pending

### topic-0051

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Nigeria plays Portugal in international World Cup friendly: All to know | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 16:07:24+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7449 |

#### Candidate Details

- **Article 738 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0774, recency=0.1500, category=0.0375`
- **Article 738 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 738 recency time:** 2026-06-09 16:07:24+00:00 (`published_at`)
- **Article 738 human review status:** Pending

### topic-0052

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Did Netanyahu really ‘defy’ Trump in bombing Iran? | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 14:48:48+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7254 |

#### Candidate Details

- **Article 740 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0579, recency=0.1500, category=0.0375`
- **Article 740 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 740 recency time:** 2026-06-09 14:48:48+00:00 (`published_at`)
- **Article 740 human review status:** Pending

### topic-0053

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Deadly protests in Pakistan-administered Kashmir: What’s going on? | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 13:58:09+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7380 |

#### Candidate Details

- **Article 741 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0705, recency=0.1500, category=0.0375`
- **Article 741 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 741 recency time:** 2026-06-09 13:58:09+00:00 (`published_at`)
- **Article 741 human review status:** Pending

### topic-0054

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Modi is using a cannon to kill a cockroach | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 13:56:35+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7254 |

#### Candidate Details

- **Article 742 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0579, recency=0.1500, category=0.0375`
- **Article 742 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 742 recency time:** 2026-06-09 13:56:35+00:00 (`published_at`)
- **Article 742 human review status:** Pending

### topic-0055

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Shackled, bleeding, raped: Palestinians describe abuse in Israel’s prisons | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 13:34:16+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7416 |

#### Candidate Details

- **Article 744 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0741, recency=0.1500, category=0.0375`
- **Article 744 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 744 recency time:** 2026-06-09 13:34:16+00:00 (`published_at`)
- **Article 744 human review status:** Pending

### topic-0056

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Why are Nigeria-South Africa tensions rising amid xenophobic attacks? | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 13:14:37+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7410 |

#### Candidate Details

- **Article 746 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0735, recency=0.1500, category=0.0375`
- **Article 746 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 746 recency time:** 2026-06-09 13:14:37+00:00 (`published_at`)
- **Article 746 human review status:** Pending

### topic-0057

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Mamdani scores goal at World Cup presser | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 12:21:13+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7203 |

#### Candidate Details

- **Article 749 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0528, recency=0.1500, category=0.0375`
- **Article 749 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 749 recency time:** 2026-06-09 12:21:13+00:00 (`published_at`)
- **Article 749 human review status:** Pending

### topic-0058

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Video captures Russian attack in Ukraine’s Zaporizhzhia | Al Jazeera | world | unknown | 3 | 1.0000 | 2026-06-09 12:05:19+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7332 |

#### Candidate Details

- **Article 750 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0657, recency=0.1500, category=0.0375`
- **Article 750 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 750 recency time:** 2026-06-09 12:05:19+00:00 (`published_at`)
- **Article 750 human review status:** Pending

### topic-0059

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Northern Ireland: Police urge calm after 'sickening' Belfast stabbing | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7710 |

#### Candidate Details

- **Article 760 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1035, recency=0.1500, category=0.0375`
- **Article 760 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 760 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 760 human review status:** Pending

### topic-0060

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | EU proposes entry ban for Russian Ukraine combatants in new sanctions package | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7797 |

#### Candidate Details

- **Article 761 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1122, recency=0.1500, category=0.0375`
- **Article 761 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 761 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 761 human review status:** Pending

### topic-0061

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Leipzig Bachfest 2026: Bach's music as hit parade | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7536 |

#### Candidate Details

- **Article 764 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0861, recency=0.1500, category=0.0375`
- **Article 764 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 764 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 764 human review status:** Pending

### topic-0062

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Peace Report: Are modern warlords ruling the world? | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7578 |

#### Candidate Details

- **Article 765 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0903, recency=0.1500, category=0.0375`
- **Article 765 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 765 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 765 human review status:** Pending

### topic-0063

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | India slams Pakistan at UN over 'Fitna al Hindustan' label | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7527 |

#### Candidate Details

- **Article 768 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0852, recency=0.1500, category=0.0375`
- **Article 768 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 768 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 768 human review status:** Pending

### topic-0064

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Japanese city captures black bear after multi-day hunt | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7626 |

#### Candidate Details

- **Article 769 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0951, recency=0.1500, category=0.0375`
- **Article 769 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 769 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 769 human review status:** Pending

### topic-0065

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Middle East: Trump accuses Iran of shooting down helicopter | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7590 |

#### Candidate Details

- **Article 773 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0915, recency=0.1500, category=0.0375`
- **Article 773 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 773 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 773 human review status:** Pending

### topic-0066

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Philippines: Large Mindanao quake displaced roughly 20,000 | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7662 |

#### Candidate Details

- **Article 774 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0987, recency=0.1500, category=0.0375`
- **Article 774 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 774 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 774 human review status:** Pending

### topic-0067

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Will Ebola have an impact on the World Cup? | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7587 |

#### Candidate Details

- **Article 775 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0912, recency=0.1500, category=0.0375`
- **Article 775 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 775 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 775 human review status:** Pending

### topic-0068

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Germany news: Smaller cities top out happiness rankings | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7578 |

#### Candidate Details

- **Article 776 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0903, recency=0.1500, category=0.0375`
- **Article 776 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 776 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 776 human review status:** Pending

### topic-0069

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Somali referee denied US entry, dropped from FIFA World Cup 2026 | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7545 |

#### Candidate Details

- **Article 779 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0870, recency=0.1500, category=0.0375`
- **Article 779 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 779 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 779 human review status:** Pending

### topic-0070

- Article count: 1
- Source count: 1
- Category distribution: `{'world': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Franco-German fighter jet project collapses after industry dispute | DW English | world | unknown | 3 | 1.0000 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.7503 |

#### Candidate Details

- **Article 780 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0828, recency=0.1500, category=0.0375`
- **Article 780 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 780 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 780 human review status:** Pending

### topic-0071

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Rivian starts deliveries of its all-important R2 SUV | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 16:46:08+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7181 |

#### Candidate Details

- **Article 576 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0606, recency=0.1500, category=0.0375`
- **Article 576 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 576 recency time:** 2026-06-09 16:46:08+00:00 (`published_at`)
- **Article 576 human review status:** Pending

### topic-0072

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | It’s not FAANG anymore. It’s MANGOS. | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 16:09:14+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7412 |

#### Candidate Details

- **Article 578 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0837, recency=0.1500, category=0.0375`
- **Article 578 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 578 recency time:** 2026-06-09 16:09:14+00:00 (`published_at`)
- **Article 578 human review status:** Pending

### topic-0073

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple says it may remove some apps from the App Store if they don’t attract users | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 15:23:40+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7367 |

#### Candidate Details

- **Article 579 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0792, recency=0.1500, category=0.0375`
- **Article 579 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 579 recency time:** 2026-06-09 15:23:40+00:00 (`published_at`)
- **Article 579 human review status:** Pending

### topic-0074

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | iOS 27 features we didn’t see onstage | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 15:06:12+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7184 |

#### Candidate Details

- **Article 580 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0609, recency=0.1500, category=0.0375`
- **Article 580 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 580 recency time:** 2026-06-09 15:06:12+00:00 (`published_at`)
- **Article 580 human review status:** Pending

### topic-0075

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple brings streaming-style subscription bundles to the App Store | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 14:55:36+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7352 |

#### Candidate Details

- **Article 581 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0777, recency=0.1500, category=0.0375`
- **Article 581 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 581 recency time:** 2026-06-09 14:55:36+00:00 (`published_at`)
- **Article 581 human review status:** Pending

### topic-0076

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple’s App Store rolls out personalized recommendations | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 14:30:17+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7112 |

#### Candidate Details

- **Article 582 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0537, recency=0.1500, category=0.0375`
- **Article 582 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 582 recency time:** 2026-06-09 14:30:17+00:00 (`published_at`)
- **Article 582 human review status:** Pending

### topic-0077

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | How an e-scooter founder raised $5 million to build space data centers | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 12:00:00+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7319 |

#### Candidate Details

- **Article 585 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0744, recency=0.1500, category=0.0375`
- **Article 585 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 585 recency time:** 2026-06-09 12:00:00+00:00 (`published_at`)
- **Article 585 human review status:** Pending

### topic-0078

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | One day after discovery, Meta pulls facial recognition code from its smart glasses | Ars Technica | tech | unknown | 2 | 1.0000 | 2026-06-09 16:31:10+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7208 |

#### Candidate Details

- **Article 594 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0633, recency=0.1500, category=0.0375`
- **Article 594 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 594 recency time:** 2026-06-09 16:31:10+00:00 (`published_at`)
- **Article 594 human review status:** Pending

### topic-0079

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Drone boat picked up downed US Army helicopter pilots—a first for sea rescues | Ars Technica | tech | unknown | 2 | 1.0000 | 2026-06-09 15:44:36+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7274 |

#### Candidate Details

- **Article 595 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0699, recency=0.1500, category=0.0375`
- **Article 595 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 595 recency time:** 2026-06-09 15:44:36+00:00 (`published_at`)
- **Article 595 human review status:** Pending

### topic-0080

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Gold isn’t inert, it just has bodyguards protecting it | Ars Technica | tech | unknown | 2 | 1.0000 | 2026-06-09 14:23:59+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7106 |

#### Candidate Details

- **Article 597 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0531, recency=0.1500, category=0.0375`
- **Article 597 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 597 recency time:** 2026-06-09 14:23:59+00:00 (`published_at`)
- **Article 597 human review status:** Pending

### topic-0081

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Here's Audi's next Q7 SUV and US-only SQ7, now with an RS V8 | Ars Technica | tech | unknown | 2 | 1.0000 | 2026-06-09 14:00:20+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7187 |

#### Candidate Details

- **Article 598 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0612, recency=0.1500, category=0.0375`
- **Article 598 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 598 recency time:** 2026-06-09 14:00:20+00:00 (`published_at`)
- **Article 598 human review status:** Pending

### topic-0082

- Article count: 3
- Source count: 2
- Category distribution: `{'tech': 3}`
- Language distribution: `{'en': 3}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | First Drive: The 2027 Rivian R2 entirely changes the EV game | Ars Technica | tech | unknown | 2 | 1.0000 | 2026-06-09 13:00:46+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.7057 |
| yes | 2 | System Card: Claude Fable 5 and Claude Mythos 5 [pdf] | Hacker News | tech | unknown | 2 | 0.7011 | 2026-06-09 16:58:13+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4999 |
| yes | 3 | Claude Fable 5 | Hacker News | tech | unknown | 2 | 0.7160 | 2026-06-09 16:58:01+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4045 |

#### Candidate Details

- **Article 600 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0564, recency=0.1418, category=0.0375`
- **Article 600 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 600 recency time:** 2026-06-09 13:00:46+00:00 (`published_at`)
- **Article 600 human review status:** Pending
- **Article 646 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1402, source_diversity=0.1000, information=0.0522, recency=0.1500, category=0.0375`
- **Article 646 selection reason:** Selected for recency, topic similarity, source diversity.
- **Article 646 recency time:** 2026-06-09 16:58:13+00:00 (`published_at`)
- **Article 646 human review status:** Pending
- **Article 644 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1432, source_diversity=0.0250, information=0.0288, recency=0.1500, category=0.0375`
- **Article 644 selection reason:** Selected for recency, topic similarity, category signal.
- **Article 644 recency time:** 2026-06-09 16:58:01+00:00 (`published_at`)
- **Article 644 human review status:** Pending

### topic-0083

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | MacOS 27 Golden Gate: Top New Features | Wired | tech | unknown | 2 | 1.0000 | 2026-06-09 17:33:21+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.7250 |

#### Candidate Details

- **Article 614 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0675, recency=0.1500, category=0.0375`
- **Article 614 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 614 recency time:** 2026-06-09 17:33:21+00:00 (`published_at`)
- **Article 614 human review status:** Pending

### topic-0084

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Anthropic Offers Mythos Upgrade for Cyber Partners and a ‘Safe’ Version for the Rest of You | Wired | tech | unknown | 2 | 1.0000 | 2026-06-09 17:00:46+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.7562 |

#### Candidate Details

- **Article 616 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0987, recency=0.1500, category=0.0375`
- **Article 616 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 616 recency time:** 2026-06-09 17:00:46+00:00 (`published_at`)
- **Article 616 human review status:** Pending

### topic-0085

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Rivian R2 2026: Specs, Price, Availability | Wired | tech | unknown | 2 | 1.0000 | 2026-06-09 13:00:00+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.7391 |

#### Candidate Details

- **Article 618 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0816, recency=0.1500, category=0.0375`
- **Article 618 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 618 recency time:** 2026-06-09 13:00:00+00:00 (`published_at`)
- **Article 618 human review status:** Pending

### topic-0086

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Apple decided not to roll out Siri in EU after denied request for exemption | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 16:13:10+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7229 |

#### Candidate Details

- **Article 645 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0654, recency=0.1500, category=0.0375`
- **Article 645 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 645 recency time:** 2026-06-09 16:13:10+00:00 (`published_at`)
- **Article 645 human review status:** Pending

### topic-0087

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Launch HN: Transload (YC P26) – Measuring freight items with CCTV | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 16:28:28+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7169 |

#### Candidate Details

- **Article 650 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0594, recency=0.1500, category=0.0375`
- **Article 650 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 650 recency time:** 2026-06-09 16:28:28+00:00 (`published_at`)
- **Article 650 human review status:** Pending

### topic-0088

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Biff.core: system composition for Clojure web apps | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 16:12:52+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7079 |

#### Candidate Details

- **Article 651 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0504, recency=0.1500, category=0.0375`
- **Article 651 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 651 recency time:** 2026-06-09 16:12:52+00:00 (`published_at`)
- **Article 651 human review status:** Pending

### topic-0089

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Is Grep All You Need? How Agent Harnesses Reshape Agentic Search | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 13:27:03+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7163 |

#### Candidate Details

- **Article 653 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0588, recency=0.1500, category=0.0375`
- **Article 653 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 653 recency time:** 2026-06-09 13:27:03+00:00 (`published_at`)
- **Article 653 human review status:** Pending

### topic-0090

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Can LLMs Beat Classical Hyperparameter Optimization Algorithms? | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 15:01:15+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7157 |

#### Candidate Details

- **Article 654 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0582, recency=0.1500, category=0.0375`
- **Article 654 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 654 recency time:** 2026-06-09 15:01:15+00:00 (`published_at`)
- **Article 654 human review status:** Pending

### topic-0091

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Unified Controllable and Faithful Text-to-CAD Generation with LLMs | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 14:04:54+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7175 |

#### Candidate Details

- **Article 660 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0600, recency=0.1500, category=0.0375`
- **Article 660 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 660 recency time:** 2026-06-09 14:04:54+00:00 (`published_at`)
- **Article 660 human review status:** Pending

### topic-0092

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Emerge Career (YC S22) Is Hiring a Founding Growth Marketer | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 12:01:09+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7133 |

#### Candidate Details

- **Article 661 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0558, recency=0.1500, category=0.0375`
- **Article 661 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 661 recency time:** 2026-06-09 12:01:09+00:00 (`published_at`)
- **Article 661 human review status:** Pending

### topic-0093

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | FCC wants to kill burner phones by forcing telecoms to get all customers' IDs | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 15:21:46+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7241 |

#### Candidate Details

- **Article 664 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0666, recency=0.1500, category=0.0375`
- **Article 664 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 664 recency time:** 2026-06-09 15:21:46+00:00 (`published_at`)
- **Article 664 human review status:** Pending

### topic-0094

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Show HN: Learn from 30 historical figures, open source, nonprofit, self-hosted | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 11:56:25+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7247 |

#### Candidate Details

- **Article 665 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0672, recency=0.1500, category=0.0375`
- **Article 665 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 665 recency time:** 2026-06-09 11:56:25+00:00 (`published_at`)
- **Article 665 human review status:** Pending

### topic-0095

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | What it feels like to work with Mythos | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 17:17:21+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7007 |

#### Candidate Details

- **Article 666 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0432, recency=0.1500, category=0.0375`
- **Article 666 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 666 recency time:** 2026-06-09 17:17:21+00:00 (`published_at`)
- **Article 666 human review status:** Pending

### topic-0096

- Article count: 1
- Source count: 1
- Category distribution: `{'tech': 1}`
- Language distribution: `{'en': 1}`
- Representative candidate count: 1
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Using Optical Aberrations to Distinguish Real Astronomical Transients | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 15:12:30+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.7193 |

#### Candidate Details

- **Article 668 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0618, recency=0.1500, category=0.0375`
- **Article 668 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 668 recency time:** 2026-06-09 15:12:30+00:00 (`published_at`)
- **Article 668 human review status:** Pending

## Human Review Notes

- Candidate suitability: Pending
- Source diversity suitability: Pending
- Candidate count suitability: Pending
