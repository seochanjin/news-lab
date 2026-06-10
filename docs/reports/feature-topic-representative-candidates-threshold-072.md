# Topic representative candidate review

## Summary

- Human review status: **Pending**
- Analyzed article count: 100
- Topic candidate count: 86
- Multi-article topic count: 9
- Singleton topic count: 77
- Report detail topic count: 9
- Singleton topic details included: `False`
- Representative candidate count: 99
- Similarity threshold: 0.72
- Embedding provider/model: `openai` / `text-embedding-3-small`
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

### topic-0004

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Israeli attack on Tyre in Lebanon kills eight as evacuation ordered for Christian quarter | The Guardian World | world | unknown | 9 | 1.0000 | 2026-06-09 15:58:09+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8671 |
| yes | 2 | Israeli air strikes hit Lebanese city of Tyre despite Iranian warning to stop attacks | BBC World | world | unknown | 3 | 0.7215 | 2026-06-09 17:47:41+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.5476 |

#### Candidate Details

- **Article 729 components:** `importance=0.0900, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1434, recency=0.1462, category=0.0375`
- **Article 729 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 729 recency time:** 2026-06-09 15:58:09+00:00 (`published_at`)
- **Article 729 human review status:** Pending
- **Article 675 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1443, source_diversity=0.1000, information=0.0858, recency=0.1500, category=0.0375`
- **Article 675 selection reason:** Selected for recency, topic similarity, source diversity.
- **Article 675 recency time:** 2026-06-09 17:47:41+00:00 (`published_at`)
- **Article 675 human review status:** Pending

### topic-0014

- Article count: 2
- Source count: 2
- Category distribution: `{'politics': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | EU plans to ban Russian soldiers from bloc in fresh sanctions on Moscow | The Guardian World | world | politics | 7 | 1.0000 | 2026-06-09 15:12:38+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.8468 |
| yes | 2 | EU proposes entry ban for Russian Ukraine combatants in new sanctions package | DW English | world | unknown | 3 | 0.8132 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.5923 |

#### Candidate Details

- **Article 725 components:** `importance=0.0700, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1326, recency=0.1442, category=0.0500`
- **Article 725 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 725 recency time:** 2026-06-09 15:12:38+00:00 (`published_at`)
- **Article 725 human review status:** Pending
- **Article 761 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1626, source_diversity=0.1000, information=0.1122, recency=0.1500, category=0.0375`
- **Article 761 selection reason:** Selected for topic similarity, recency, title/summary information.
- **Article 761 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 761 human review status:** Pending

### topic-0026

- Article count: 2
- Source count: 2
- Category distribution: `{'security': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Anthropic’s Claude Fable 5 is a version of Mythos the public can access today | TechCrunch | tech | security | 5 | 1.0000 | 2026-06-09 17:00:00+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.8050 |
| yes | 2 | Anthropic Offers Mythos Upgrade for Cyber Partners and a ‘Safe’ Version for the Rest of You | Wired | tech | unknown | 2 | 0.8344 | 2026-06-09 17:00:46+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.5731 |

#### Candidate Details

- **Article 575 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.1050, recency=0.1500, category=0.0500`
- **Article 575 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 575 recency time:** 2026-06-09 17:00:00+00:00 (`published_at`)
- **Article 575 human review status:** Pending
- **Article 616 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1669, source_diversity=0.1000, information=0.0987, recency=0.1500, category=0.0375`
- **Article 616 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 616 recency time:** 2026-06-09 17:00:46+00:00 (`published_at`)
- **Article 616 human review status:** Pending

### topic-0028

- Article count: 3
- Source count: 2
- Category distribution: `{'tech': 3}`
- Language distribution: `{'en': 3}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | The Top New Features in Apple’s iOS 27 and iPadOS 27 | Wired | tech | unknown | 5 | 1.0000 | 2026-06-09 17:03:37+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.7618 |
| yes | 2 | iOS 27 features we didn’t see onstage | TechCrunch | tech | unknown | 2 | 0.7869 | 2026-06-09 15:06:12+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.5207 |
| yes | 3 | MacOS 27 Golden Gate: Top New Features | Wired | tech | unknown | 2 | 0.7375 | 2026-06-09 17:33:21+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.4475 |

#### Candidate Details

- **Article 615 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0753, recency=0.1490, category=0.0375`
- **Article 615 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 615 recency time:** 2026-06-09 17:03:37+00:00 (`published_at`)
- **Article 615 human review status:** Pending
- **Article 580 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1574, source_diversity=0.1000, information=0.0609, recency=0.1449, category=0.0375`
- **Article 580 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 580 recency time:** 2026-06-09 15:06:12+00:00 (`published_at`)
- **Article 580 human review status:** Pending
- **Article 614 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1475, source_diversity=0.0250, information=0.0675, recency=0.1500, category=0.0375`
- **Article 614 selection reason:** Selected for recency, topic similarity, title/summary information.
- **Article 614 recency time:** 2026-06-09 17:33:21+00:00 (`published_at`)
- **Article 614 human review status:** Pending

### topic-0030

- Article count: 4
- Source count: 4
- Category distribution: `{'politics': 2, 'world': 2}`
- Language distribution: `{'en': 4}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Man reportedly shot at Kenya protest against US Ebola quarantine centre | BBC World | world | politics | 5 | 1.0000 | 2026-06-09 15:08:50+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7774 |
| yes | 2 | Man shot dead during protest against proposed US Ebola quarantine facility in Kenya | The Guardian World | world | unknown | 3 | 0.8269 | 2026-06-09 17:13:20+00:00 | 2026-06-09 18:00:45.660093+00:00 | published_at | 0.6210 |
| yes | 3 | Kenya: Protester shot dead at rally against US Ebola center | DW English | world | politics | 4 | 0.8542 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.5987 |
| no |  | Kenya’s police crack down on protest against US Ebola centre in Nanyuki | Al Jazeera | world | unknown | 3 | 0.7890 | 2026-06-09 16:16:44+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.5497 |

#### Candidate Details

- **Article 677 components:** `importance=0.0500, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0834, recency=0.1440, category=0.0500`
- **Article 677 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 677 recency time:** 2026-06-09 15:08:50+00:00 (`published_at`)
- **Article 677 human review status:** Pending
- **Article 704 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1654, source_diversity=0.1000, information=0.1398, recency=0.1483, category=0.0375`
- **Article 704 selection reason:** Selected for topic similarity, recency, title/summary information.
- **Article 704 recency time:** 2026-06-09 17:13:20+00:00 (`published_at`)
- **Article 704 human review status:** Pending
- **Article 777 components:** `importance=0.0400, topic_seed=0.0000, similarity=0.1708, source_diversity=0.1000, information=0.0879, recency=0.1500, category=0.0500`
- **Article 777 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 777 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 777 human review status:** Pending
- **Article 737 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1578, source_diversity=0.1000, information=0.0780, recency=0.1464, category=0.0375`
- **Article 737 selection reason:** Not selected within the candidate limit.
- **Article 737 recency time:** 2026-06-09 16:16:44+00:00 (`published_at`)
- **Article 737 human review status:** Pending

### topic-0033

- Article count: 3
- Source count: 3
- Category distribution: `{'politics': 1, 'world': 2}`
- Language distribution: `{'en': 3}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Trump says Iran shot down US helicopter over Hormuz, vows to respond | Al Jazeera | world | politics | 4 | 1.0000 | 2026-06-09 16:54:15+00:00 | 2026-06-09 18:00:51.123812+00:00 | published_at | 0.7639 |
| yes | 2 | Middle East: Trump accuses Iran of shooting down helicopter | DW English | world | unknown | 3 | 0.7579 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.5606 |
| yes | 3 | Trump says Iran shot down US helicopter and vows to respond | BBC World | world | unknown | 3 | 0.8093 | 2026-06-09 17:32:15+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.5480 |

#### Candidate Details

- **Article 736 components:** `importance=0.0400, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0762, recency=0.1477, category=0.0500`
- **Article 736 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 736 recency time:** 2026-06-09 16:54:15+00:00 (`published_at`)
- **Article 736 human review status:** Pending
- **Article 773 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1516, source_diversity=0.1000, information=0.0915, recency=0.1500, category=0.0375`
- **Article 773 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 773 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 773 human review status:** Pending
- **Article 674 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1619, source_diversity=0.1000, information=0.0696, recency=0.1490, category=0.0375`
- **Article 674 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 674 recency time:** 2026-06-09 17:32:15+00:00 (`published_at`)
- **Article 674 human review status:** Pending

### topic-0043

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Scrapping of Franco-German fighter jet leaves allies at odds on defence future | BBC World | world | unknown | 3 | 1.0000 | 2026-06-09 14:54:36+00:00 | 2026-06-09 18:00:39.836012+00:00 | published_at | 0.7357 |
| yes | 2 | Franco-German fighter jet project collapses after industry dispute | DW English | world | unknown | 3 | 0.7695 |  | 2026-06-09 18:00:55.862488+00:00 | created_at | 0.5542 |

#### Candidate Details

- **Article 680 components:** `importance=0.0300, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0747, recency=0.1435, category=0.0375`
- **Article 680 selection reason:** Selected for topic similarity, topic seed, recency.
- **Article 680 recency time:** 2026-06-09 14:54:36+00:00 (`published_at`)
- **Article 680 human review status:** Pending
- **Article 780 components:** `importance=0.0300, topic_seed=0.0000, similarity=0.1539, source_diversity=0.1000, information=0.0828, recency=0.1500, category=0.0375`
- **Article 780 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 780 recency time:** 2026-06-09 18:00:55.862488+00:00 (`created_at`)
- **Article 780 human review status:** Pending

### topic-0064

- Article count: 3
- Source count: 3
- Category distribution: `{'tech': 3}`
- Language distribution: `{'en': 3}`
- Representative candidate count: 3
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Rivian starts deliveries of its all-important R2 SUV | TechCrunch | tech | unknown | 2 | 1.0000 | 2026-06-09 16:46:08+00:00 | 2026-06-09 18:00:20.029782+00:00 | published_at | 0.7181 |
| yes | 2 | Rivian R2 2026: Specs, Price, Availability | Wired | tech | unknown | 2 | 0.7322 | 2026-06-09 13:00:00+00:00 | 2026-06-09 18:00:28.067530+00:00 | published_at | 0.5276 |
| yes | 3 | First Drive: The 2027 Rivian R2 entirely changes the EV game | Ars Technica | tech | unknown | 2 | 0.7333 | 2026-06-09 13:00:46+00:00 | 2026-06-09 18:00:23.975652+00:00 | published_at | 0.5028 |

#### Candidate Details

- **Article 576 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0606, recency=0.1500, category=0.0375`
- **Article 576 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 576 recency time:** 2026-06-09 16:46:08+00:00 (`published_at`)
- **Article 576 human review status:** Pending
- **Article 618 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1464, source_diversity=0.1000, information=0.0816, recency=0.1421, category=0.0375`
- **Article 618 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 618 recency time:** 2026-06-09 13:00:00+00:00 (`published_at`)
- **Article 618 human review status:** Pending
- **Article 600 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1467, source_diversity=0.1000, information=0.0564, recency=0.1422, category=0.0375`
- **Article 600 selection reason:** Selected for topic similarity, recency, source diversity.
- **Article 600 recency time:** 2026-06-09 13:00:46+00:00 (`published_at`)
- **Article 600 human review status:** Pending

### topic-0074

- Article count: 2
- Source count: 1
- Category distribution: `{'tech': 2}`
- Language distribution: `{'en': 2}`
- Representative candidate count: 2
- Human review status: **Pending**

| Selected | Rank | Title | Source | Source Category | Rule Category | Importance | Similarity | Published At | Created At | Recency Time Source | Candidate Score |
| --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| yes | 1 | Claude Fable 5 | Hacker News | tech | unknown | 2 | 1.0000 | 2026-06-09 16:58:01+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.6863 |
| yes | 2 | System Card: Claude Fable 5 and Claude Mythos 5 [pdf] | Hacker News | tech | unknown | 2 | 0.8117 | 2026-06-09 16:58:13+00:00 | 2026-06-09 18:00:34.086685+00:00 | published_at | 0.4470 |

#### Candidate Details

- **Article 644 components:** `importance=0.0200, topic_seed=0.1500, similarity=0.2000, source_diversity=0.1000, information=0.0288, recency=0.1500, category=0.0375`
- **Article 644 selection reason:** Selected for topic similarity, recency, topic seed.
- **Article 644 recency time:** 2026-06-09 16:58:01+00:00 (`published_at`)
- **Article 644 human review status:** Pending
- **Article 646 components:** `importance=0.0200, topic_seed=0.0000, similarity=0.1623, source_diversity=0.0250, information=0.0522, recency=0.1500, category=0.0375`
- **Article 646 selection reason:** Selected for topic similarity, recency, title/summary information.
- **Article 646 recency time:** 2026-06-09 16:58:13+00:00 (`published_at`)
- **Article 646 human review status:** Pending

## Human Review Notes

- Candidate suitability: Pending
- Source diversity suitability: Pending
- Candidate count suitability: Pending
