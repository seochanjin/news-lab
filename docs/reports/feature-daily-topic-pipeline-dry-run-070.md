# Daily topic pipeline report

## Summary

- Dry-run: `true`
- Execute requested: `false`
- Window hours: 24
- Article count: 115
- Topic candidate count: 105
- Selected topic count: 3
- Reference topic count: 10
- Selected article IDs: `[944, 945, 974, 952, 993, 898, 989]`
- Topic ordering: `article_count desc, source_count desc, average similarity desc, latest published_at desc, topic_candidate_id asc`
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `false`
- Raw extraction success/failure: 0 / 0
- DB write performed: `false`

## Selected Topics

### topic-0001

- Article count: 6
- Source count: 4
- Selected article IDs: `[944, 945, 974]`
- Similarity scores: `{944: 1.0, 945: 0.7079, 974: 0.7781}`

#### Selected Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 944 | 1.0000 | The Guardian World | 2026-06-10 17:14:59+00:00 | Middle East crisis live: US going to hit Iran ‘hard’ again today, says Trump | https://www.theguardian.com/world/live/2026/jun/10/iran-war-updates-missile-strikes-trump-us-retaliation-middle-east-crisis-war-live |
| supporting | 945 | 0.7079 | The Guardian World | 2026-06-10 17:00:33+00:00 | Trump, ever the unreliable narrator, is unable to force reality to match his preferred story on Iran | https://www.theguardian.com/us-news/2026/jun/10/trump-iran-war-analysis |
| supporting | 974 | 0.7781 | DW English |  | Middle East: US to hit Iran 'hard,' Trump says | https://www.dw.com/en/middle-east-us-to-hit-iran-hard-trump-says/live-77482934?maca=en-rss-en-all-1573-rdf |

#### Generated Summary

- Status: `ready`
- title_ko: 트럼프, 이란에 ‘강력한 타격’ 재차 예고… 양국 교전 재개
- summary_ko: 도널드 트럼프 미국 대통령이 이란에 대해 수요일에 다시 ‘강하게 타격하겠다’고 밝히자 미국은 이란에 대한 타격을 재개했다. 이란은 압박에 굴복하지 않겠다며 반격에 나섰고, 미국은 호르무즈 해협 인근의 기지와 방어시설을 겨냥한 타격을 수행했다. 이란의 반격으로 미군 기지에 대한 타격이 보고됐으며, 미국은 호르무즈 차단과 해상 작전을 지속했다. 이란은 다수의 타깃 타격을 주장했고, 미국 측은 대부분의 미사일·드론이 요격됐다고 밝혔다. 한편 인도 정부는 Settebello 공격으로 3명의 선원이 실종되고 21명이 구조됐다고 전했다.
- key_points:
  - 트럼프가 이란에 대해 ‘다시 강하게 타격하겠다’고 발언
  - 미국이 이란에 대한 타격을 재개
  - 이란은 압박에 반발하며 반격
  - IRGC가 미국 기지 21곳 타격 주장
  - 미국은 호르무즈 인근 타격 및 해상 작전 지속
  - 대다수 미사일·드론은 요격됐다고 미국 측 발표
  - Settebello 공격으로 인도 선원 3명 실종, 21명 구조
- keywords: `미국-이란 갈등, 트럼프, 강경 타격, 호르무즈 해협, IRGC, 미사일, 드론, Settebello, 인도 선원 실종, 해상 차단, 교전 확산`

### topic-0054

- Article count: 2
- Source count: 2
- Selected article IDs: `[952, 993]`
- Similarity scores: `{952: 1.0, 993: 0.8137}`

#### Selected Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 952 | 1.0000 | Al Jazeera | 2026-06-10 16:30:54+00:00 | Mass shooting with at least 10 attackers in Johannesburg | https://www.aljazeera.com/video/newsfeed/2026/6/10/mass-shooting-with-at-least-10-attackers-in-johannesburg?traffic_source=rss |
| supporting | 993 | 0.8137 | DW English |  | South Africa: Mass shooting kills 12 near Johannesburg | https://www.dw.com/en/south-africa-mass-shooting-kills-12-near-johannesburg/a-77483899?maca=en-rss-en-all-1573-rdf |

#### Generated Summary

- Status: `insufficient_raw_text`
- title_ko: 
- summary_ko: 
- key_points:
- keywords: ``

### topic-0038

- Article count: 2
- Source count: 2
- Selected article IDs: `[898, 989]`
- Similarity scores: `{898: 1.0, 989: 0.7975}`

#### Selected Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 898 | 1.0000 | BBC World | 2026-06-10 15:31:15+00:00 | Pakistan launches deadly air strikes in Afghanistan, reigniting tensions | https://www.bbc.com/news/articles/cvg57nk373lo?at_medium=RSS&at_campaign=rss |
| supporting | 989 | 0.7975 | DW English |  | Pakistan carries out new deadly strikes on Afghanistan | https://www.dw.com/en/pakistan-carries-out-new-deadly-strikes-on-afghanistan/a-77483466?maca=en-rss-en-all-1573-rdf |

#### Generated Summary

- Status: `insufficient_raw_text`
- title_ko: 
- summary_ko: 
- key_points:
- keywords: ``

## Reference Candidates

These candidates were outside `--max-topics` and are shown only for human review.
They are not raw extraction, summary provider, or DB save targets.

### topic-0022

- Article count: 2
- Source count: 2
- Reason: outside max-topics
- Article IDs: `[975, 924]`
- Similarity scores: `{975: 1.0, 924: 0.7937}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 975 | 1.0000 | DW English |  | Cuba: Amid blockade, Pentagon chief issues military warning | https://www.dw.com/en/cuba-amid-blockade-pentagon-chief-issues-military-warning/a-77494837?maca=en-rss-en-all-1573-rdf |
| supporting | 924 | 0.7937 | The Guardian World | 2026-06-10 16:38:40+00:00 | Hegseth warns Cuba against acquiring weapons in visit to Guantánamo Bay | https://www.theguardian.com/us-news/2026/jun/10/hegseth-warns-cuba-weapons-guantanamo-bay |

### topic-0026

- Article count: 2
- Source count: 2
- Reason: outside max-topics
- Article IDs: `[956, 891]`
- Similarity scores: `{956: 1.0, 891: 0.7896}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 956 | 1.0000 | Al Jazeera | 2026-06-10 15:38:38+00:00 | Bill Gates appears before Congress to testify over Epstein files | https://www.aljazeera.com/video/newsfeed/2026/6/10/bill-gates-appears-before-congress-to-testify-over-epstein-files?traffic_source=rss |
| supporting | 891 | 0.7896 | BBC World | 2026-06-10 14:14:16+00:00 | Three questions Bill Gates could face as he testifies to Congress on Epstein | https://www.bbc.com/news/articles/crr892qp255o?at_medium=RSS&at_campaign=rss |

### topic-0008

- Article count: 2
- Source count: 2
- Reason: outside max-topics
- Article IDs: `[946, 964]`
- Similarity scores: `{946: 1.0, 964: 0.7488}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 946 | 1.0000 | The Guardian World | 2026-06-10 14:05:23+00:00 | Video shows family’s car slowing before Israeli troops shot dead Palestinian baby | https://www.theguardian.com/world/2026/jun/10/palestinian-baby-shot-dead-israeli-troops-occupied-west-bank-new-footage |
| supporting | 964 | 0.7488 | Al Jazeera | 2026-06-10 12:44:39+00:00 | 7-month-old baby shot by Israeli soldier in Hebron | https://www.aljazeera.com/video/newsfeed/2026/6/10/7-month-old-baby-shot-by-israeli-soldier-in-hebron?traffic_source=rss |

### topic-0011

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[979]`
- Similarity scores: `{979: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 979 | 1.0000 | DW English |  | Germany news: Recession looms as Iran war chokes growth | https://www.dw.com/en/germany-news-recession-looms-as-iran-war-chokes-growth/live-77487978?maca=en-rss-en-all-1573-rdf |

### topic-0012

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[983]`
- Similarity scores: `{983: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 983 | 1.0000 | DW English |  | Neo-Nazi lost an east German election, but extremism remains | https://www.dw.com/en/neo-nazi-lost-an-east-german-election-but-extremism-remains/a-77487377?maca=en-rss-en-all-1573-rdf |

### topic-0017

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[990]`
- Similarity scores: `{990: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 990 | 1.0000 | DW English |  | War in Ukraine: Kyiv strikes key Russian supply lines | https://www.dw.com/en/war-in-ukraine-kyiv-strikes-key-russian-supply-lines/a-77480640?maca=en-rss-en-all-1573-rdf |

### topic-0042

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[982]`
- Similarity scores: `{982: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 982 | 1.0000 | DW English |  | India news: Modi becomes longest-serving elected PM | https://www.dw.com/en/india-news-modi-becomes-longest-serving-elected-pm/live-77484563?maca=en-rss-en-all-1573-rdf |

### topic-0043

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[984]`
- Similarity scores: `{984: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 984 | 1.0000 | DW English |  | The strongest El Nino in more than a century may be coming | https://www.dw.com/en/the-strongest-el-nino-in-more-than-a-century-may-be-coming/a-77469489?maca=en-rss-en-all-1573-rdf |

### topic-0044

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[994]`
- Similarity scores: `{994: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 994 | 1.0000 | DW English |  | NASA picks first European astronaut for Artemis mission | https://www.dw.com/en/nasa-picks-first-european-astronaut-for-artemis-mission/a-77482632?maca=en-rss-en-all-1573-rdf |

### topic-0066

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[976]`
- Similarity scores: `{976: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 976 | 1.0000 | DW English |  | World Cup 2026: How an old song from Bosnia went viral | https://www.dw.com/en/world-cup-2026-how-an-old-song-from-bosnia-went-viral/a-77491463?maca=en-rss-en-all-1573-rdf |

## Safety

- Embedding vectors and topic candidate intermediate results are memory-only.
- Actual raw extraction and DB writes require explicit `--execute`.
- Provider calls require explicit provider flags and API keys.
