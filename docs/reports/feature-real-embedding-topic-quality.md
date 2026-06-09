# Real embedding topic quality review

## Review Status

- Human review:
  - Same-event grouping quality: Pass for sampled OpenAI embedding topics.
  - Cross-event over-grouping: No severe over-grouping observed at threshold 0.70/0.72. Threshold 0.65 may include broader issue-level grouping.
  - Representative article suitability: Mostly acceptable.
  - Recommended threshold: 0.70 as default candidate, 0.72 as conservative fallback.
  - Ready for representative article stage: Yes, with continued human review in the next representative-selection step.
- Embedding model: `text-embedding-3-small`
- Real provider used: `True`
- Article count: 68
- Time basis: `published`
- Window hours: 24
- DB write performed: `false`

## Provider Estimate

- Estimated tokens: 5896
- Estimated cost USD: 0.000118

## Threshold Summary

| Threshold | Topic Candidates | Multi-article Topics | Singleton Topics | Singleton Ratio |
| --------- | ---------------: | -------------------: | ---------------: | --------------: |
| 0.65      |               61 |                    7 |               54 |          0.8852 |
| 0.70      |               63 |                    4 |               59 |          0.9365 |
| 0.72      |               64 |                    4 |               60 |          0.9375 |
| 0.75      |               65 |                    3 |               62 |          0.9538 |
| 0.80      |               66 |                    2 |               64 |          0.9697 |

## Deterministic Hash Comparison

| Threshold | Topic Candidates | Multi-article Topics | Singleton Ratio |
| --------- | ---------------: | -------------------: | --------------: |
| 0.65      |               63 |                    5 |          0.9206 |
| 0.70      |               66 |                    2 |          0.9697 |
| 0.72      |               66 |                    2 |          0.9697 |
| 0.75      |               67 |                    1 |          0.9851 |
| 0.80      |               68 |                    0 |          1.0000 |

## Multi-article Topic Candidates

### Threshold 0.65

- Multi-article topic candidates: 7

#### topic-0001

- Article count: 2
- Source count: 1
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8315
- Representative article: Will Iran give up on ceasefire talks as strait of Hormuz blockade continues?
- Max importance article: Will Iran give up on ceasefire talks as strait of Hormuz blockade continues?

| Title                                                                        | Source             | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------------------------- | ------------------ | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Will Iran give up on ceasefire talks as strait of Hormuz blockade continues? | The Guardian World | world           | world         |         30 | 2026-06-08 14:04:20+00:00 |        1.0 |
| Iran war: who is fighting and why?                                           | The Guardian World | world           | world         |         27 | 2026-06-08 14:54:38+00:00 |     0.6631 |

#### topic-0002

- Article count: 2
- Source count: 1
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.842
- Representative article: Apple’s long-awaited AI Siri overhaul is finally here
- Max importance article: Apple’s long-awaited AI Siri overhaul is finally here

| Title                                                                                             | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Apple’s long-awaited AI Siri overhaul is finally here                                             | TechCrunch | tech            | ai            |         13 | 2026-06-08 17:56:21+00:00 |        1.0 |
| WWDC 2026: What to expect, from Siri’s highly anticipated revamp to Apple Intelligence and iOS 27 | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:34:59+00:00 |      0.684 |

#### topic-0004

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8306
- Representative article: ‘Strategic doctrine’: Iran hails military shift after Beirut raid response
- Max importance article: ‘Strategic doctrine’: Iran hails military shift after Beirut raid response

| Title                                                                        | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| ‘Strategic doctrine’: Iran hails military shift after Beirut raid response   | Al Jazeera | world           | world         |         11 | 2026-06-08 16:06:47+00:00 |        1.0 |
| Iran's strike on Israel suggests the regime's sense of resilience is growing | BBC World  | world           | unknown       |          3 | 2026-06-08 14:11:22+00:00 |     0.6612 |

#### topic-0009

- Article count: 2
- Source count: 2
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8539
- Representative article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more
- Max importance article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more

| Title                                                                           | Source      | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------- | ----------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more | TechCrunch  | tech            | ai            |          8 | 2026-06-08 17:42:26+00:00 |        1.0 |
| Apple WWDC 2026 Livestream                                                      | Hacker News | tech            | unknown       |          2 | 2026-06-08 17:14:24+00:00 |     0.7078 |

#### topic-0029

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8663
- Representative article: Iran and Israel say they have halted strikes after first exchange of fire since truce
- Max importance article: Iran and Israel say they have halted strikes after first exchange of fire since truce

| Title                                                                                 | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Iran and Israel say they have halted strikes after first exchange of fire since truce | BBC World  | world           | unknown       |          3 | 2026-06-08 17:11:32+00:00 |        1.0 |
| Middle East updates: Iran, Israel both declare pause in attacks                       | DW English | world           | unknown       |          3 |                           |     0.7325 |

#### topic-0030

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9277
- Representative article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon
- Max importance article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon

| Title                                                      | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Jailed crypto founder Sam Bankman-Fried seeks Trump pardon | BBC World  | world           | unknown       |          3 | 2026-06-08 17:18:21+00:00 |        1.0 |
| Sam Bankman-Fried applies for a pardon from Trump          | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:04:21+00:00 |     0.8554 |

#### topic-0041

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8802
- Representative article: Meta to take legal action against Israeli spyware company NSO
- Max importance article: Meta to take legal action against Israeli spyware company NSO

| Title                                                                                       | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Meta to take legal action against Israeli spyware company NSO                               | Al Jazeera | world           | unknown       |          3 | 2026-06-08 14:05:28+00:00 |        1.0 |
| WhatsApp says it caught new spyware attacks linked to NSO Group in violation of court order | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:37:31+00:00 |     0.7605 |

### Threshold 0.70

- Multi-article topic candidates: 4

#### topic-0010

- Article count: 3
- Source count: 2
- Category distribution: `{'ai': 1, 'tech': 2}`
- Language distribution: `{'en': 3}`
- Average similarity: 0.8576
- Representative article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more
- Max importance article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more

| Title                                                                                             | Source      | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------------- | ----------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more                   | TechCrunch  | tech            | ai            |          8 | 2026-06-08 17:42:26+00:00 |        1.0 |
| WWDC 2026: What to expect, from Siri’s highly anticipated revamp to Apple Intelligence and iOS 27 | TechCrunch  | tech            | unknown       |          2 | 2026-06-08 15:34:59+00:00 |     0.8649 |
| Apple WWDC 2026 Livestream                                                                        | Hacker News | tech            | unknown       |          2 | 2026-06-08 17:14:24+00:00 |     0.7078 |

#### topic-0030

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8663
- Representative article: Iran and Israel say they have halted strikes after first exchange of fire since truce
- Max importance article: Iran and Israel say they have halted strikes after first exchange of fire since truce

| Title                                                                                 | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Iran and Israel say they have halted strikes after first exchange of fire since truce | BBC World  | world           | unknown       |          3 | 2026-06-08 17:11:32+00:00 |        1.0 |
| Middle East updates: Iran, Israel both declare pause in attacks                       | DW English | world           | unknown       |          3 |                           |     0.7325 |

#### topic-0032

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9277
- Representative article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon
- Max importance article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon

| Title                                                      | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Jailed crypto founder Sam Bankman-Fried seeks Trump pardon | BBC World  | world           | unknown       |          3 | 2026-06-08 17:18:21+00:00 |        1.0 |
| Sam Bankman-Fried applies for a pardon from Trump          | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:04:21+00:00 |     0.8554 |

#### topic-0043

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8802
- Representative article: Meta to take legal action against Israeli spyware company NSO
- Max importance article: Meta to take legal action against Israeli spyware company NSO

| Title                                                                                       | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Meta to take legal action against Israeli spyware company NSO                               | Al Jazeera | world           | unknown       |          3 | 2026-06-08 14:05:28+00:00 |        1.0 |
| WhatsApp says it caught new spyware attacks linked to NSO Group in violation of court order | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:37:31+00:00 |     0.7605 |

### Threshold 0.72

- Multi-article topic candidates: 4

#### topic-0010

- Article count: 2
- Source count: 1
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9324
- Representative article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more
- Max importance article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more

| Title                                                                                             | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more                   | TechCrunch | tech            | ai            |          8 | 2026-06-08 17:42:26+00:00 |        1.0 |
| WWDC 2026: What to expect, from Siri’s highly anticipated revamp to Apple Intelligence and iOS 27 | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:34:59+00:00 |     0.8649 |

#### topic-0030

- Article count: 2
- Source count: 2
- Category distribution: `{'world': 2}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8663
- Representative article: Iran and Israel say they have halted strikes after first exchange of fire since truce
- Max importance article: Iran and Israel say they have halted strikes after first exchange of fire since truce

| Title                                                                                 | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Iran and Israel say they have halted strikes after first exchange of fire since truce | BBC World  | world           | unknown       |          3 | 2026-06-08 17:11:32+00:00 |        1.0 |
| Middle East updates: Iran, Israel both declare pause in attacks                       | DW English | world           | unknown       |          3 |                           |     0.7325 |

#### topic-0032

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9277
- Representative article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon
- Max importance article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon

| Title                                                      | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Jailed crypto founder Sam Bankman-Fried seeks Trump pardon | BBC World  | world           | unknown       |          3 | 2026-06-08 17:18:21+00:00 |        1.0 |
| Sam Bankman-Fried applies for a pardon from Trump          | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:04:21+00:00 |     0.8554 |

#### topic-0043

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8802
- Representative article: Meta to take legal action against Israeli spyware company NSO
- Max importance article: Meta to take legal action against Israeli spyware company NSO

| Title                                                                                       | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Meta to take legal action against Israeli spyware company NSO                               | Al Jazeera | world           | unknown       |          3 | 2026-06-08 14:05:28+00:00 |        1.0 |
| WhatsApp says it caught new spyware attacks linked to NSO Group in violation of court order | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:37:31+00:00 |     0.7605 |

### Threshold 0.75

- Multi-article topic candidates: 3

#### topic-0010

- Article count: 2
- Source count: 1
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9324
- Representative article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more
- Max importance article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more

| Title                                                                                             | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more                   | TechCrunch | tech            | ai            |          8 | 2026-06-08 17:42:26+00:00 |        1.0 |
| WWDC 2026: What to expect, from Siri’s highly anticipated revamp to Apple Intelligence and iOS 27 | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:34:59+00:00 |     0.8649 |

#### topic-0032

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9277
- Representative article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon
- Max importance article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon

| Title                                                      | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Jailed crypto founder Sam Bankman-Fried seeks Trump pardon | BBC World  | world           | unknown       |          3 | 2026-06-08 17:18:21+00:00 |        1.0 |
| Sam Bankman-Fried applies for a pardon from Trump          | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:04:21+00:00 |     0.8554 |

#### topic-0043

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.8802
- Representative article: Meta to take legal action against Israeli spyware company NSO
- Max importance article: Meta to take legal action against Israeli spyware company NSO

| Title                                                                                       | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Meta to take legal action against Israeli spyware company NSO                               | Al Jazeera | world           | unknown       |          3 | 2026-06-08 14:05:28+00:00 |        1.0 |
| WhatsApp says it caught new spyware attacks linked to NSO Group in violation of court order | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:37:31+00:00 |     0.7605 |

### Threshold 0.80

- Multi-article topic candidates: 2

#### topic-0010

- Article count: 2
- Source count: 1
- Category distribution: `{'ai': 1, 'tech': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9324
- Representative article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more
- Max importance article: WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more

| Title                                                                                             | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ------------------------------------------------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| WWDC 2026: Everything announced on Siri AI, iOS 27, Apple Intelligence and more                   | TechCrunch | tech            | ai            |          8 | 2026-06-08 17:42:26+00:00 |        1.0 |
| WWDC 2026: What to expect, from Siri’s highly anticipated revamp to Apple Intelligence and iOS 27 | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:34:59+00:00 |     0.8649 |

#### topic-0032

- Article count: 2
- Source count: 2
- Category distribution: `{'tech': 1, 'world': 1}`
- Language distribution: `{'en': 2}`
- Average similarity: 0.9277
- Representative article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon
- Max importance article: Jailed crypto founder Sam Bankman-Fried seeks Trump pardon

| Title                                                      | Source     | Source Category | Rule Category | Importance | Published At              | Similarity |
| ---------------------------------------------------------- | ---------- | --------------- | ------------- | ---------: | ------------------------- | ---------: |
| Jailed crypto founder Sam Bankman-Fried seeks Trump pardon | BBC World  | world           | unknown       |          3 | 2026-06-08 17:18:21+00:00 |        1.0 |
| Sam Bankman-Fried applies for a pardon from Trump          | TechCrunch | tech            | unknown       |          2 | 2026-06-08 15:04:21+00:00 |     0.8554 |

## Human Review Notes

- Same-event grouping quality: 샘플 기준 통과. 실제 OpenAI embedding 결과에서 WWDC / Siri / Apple Intelligence, Iran / Israel pause, Sam Bankman-Fried pardon request, Meta / WhatsApp / NSO spyware 후보가 의미 있게 묶였다.
- Cross-event over-grouping: 0.70과 0.72 threshold 기준에서는 심각한 오묶음이 확인되지 않았다. 다만 0.65는 같은 사건보다 넓은 이슈 단위로 묶일 가능성이 있어 기본값으로는 보수적으로 접근하는 것이 적절하다.
- Representative article suitability: 샘플 기준 대체로 적절하다. 다만 대표 기사 선정은 32차 대표 기사 후보 선정 단계에서 계속 human review 대상으로 유지한다.
- Recommended threshold: 기본 후보 threshold는 0.70, 보수적 fallback은 0.72로 둔다.
- Ready for representative article stage: 조건부로 가능하다. 31차 샘플 검증 결과는 32차 대표 기사 후보 선정 단계로 넘어가기에 충분하지만, 후속 단계에서도 사람이 검토하는 절차를 유지한다.
