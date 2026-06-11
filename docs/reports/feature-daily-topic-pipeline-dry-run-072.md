# Daily topic pipeline report

## Summary

- Dry-run: `true`
- Execute requested: `false`
- Window hours: 24
- Article count: 115
- Topic candidate count: 107
- Selected topic count: 3
- Reference topic count: 10
- Selected article IDs: `[944, 974, 947, 952, 993, 898, 989]`
- Topic ordering: `article_count desc, source_count desc, average similarity desc, latest published_at desc, topic_candidate_id asc`
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

#### Selected Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 944 | 1.0000 | The Guardian World | 2026-06-10 17:14:59+00:00 | Middle East crisis live: US going to hit Iran ‘hard’ again today, says Trump | https://www.theguardian.com/world/live/2026/jun/10/iran-war-updates-missile-strikes-trump-us-retaliation-middle-east-crisis-war-live |
| supporting | 974 | 0.7781 | DW English |  | Middle East: US to hit Iran 'hard,' Trump says | https://www.dw.com/en/middle-east-us-to-hit-iran-hard-trump-says/live-77482934?maca=en-rss-en-all-1573-rdf |
| supporting | 947 | 0.7799 | The Guardian World | 2026-06-10 12:22:01+00:00 | Middle East peace talks in doubt as Iran says it needs to ‘reassess’ after overnight strikes | https://www.theguardian.com/world/2026/jun/10/middle-east-peace-talks-iran-strikes |

#### Generated Summary

- Status: `ready`
- title_ko: 트럼프, 이란에 대해 오늘도 ‘강경 타격’ 예고… 양국 교전 지속
- summary_ko: 도널드 트럼프 대통령은 미국이 이란에 대해 ‘오늘도 강하게 타격하겠다’고 밝혔다. 이는 지난 밤 양측의 교전과 미국의 이란 방어 체계·기지에 대한 타격 보도에 따른 것이다. 이란은 미국의 압박에도 맞대응을 시사했고, 미국은 호르무즈 해협 인근의 이란 기지와 방어 시스템에 타격했다. 이란 측은 미국 기지에 대한 응답을 주장했고, 미국은 오만 만에서 이란으로부터 운반되려던 석유를 싣고 가려던 선박을 타격했다. 인도 선원 실종 3명, 구조 21명 등의 상황과 함께 호르무즈 해협 차단 조치의 영향으로 이란의 포트가 타격을 받았으며, IRGC는 지역 내 미국 기지 21곳에 타격을 가했다고 밝혔다. 센트컴은 이란의 미사일‧드론 발사 중 다수가 요격됐다고 보도했다. 두 승무원은 생존해 구조됐다.
- key_points:
  - 트럼프: 미국은 이란에 ‘오늘도 강경 타격’
  - 양측은 지난 밤 교전했고, 미국은 이란 방어 시스템·기지에 타격
  - 이란은 미국 기지에 대한 응답 주장
  - 미국은 오만 만에서 이란 운반 선박 타격
  - 인도 선원 실종 3명, 구조 21명
  - 호르무즈 해협 차단으로 포트 영향
  - IRGC: 이 지역 미국 기지 21곳 타격 주장
  - 센트컴: 이란 발사물 다수 요격
- keywords: `트럼프, 이란, 강경 타격, 미군, IRGC, 호르무즈 해협, 오만 만, 석유 선박, Settebello, 인도 선원, 실종, 구조`

### topic-0056

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

### topic-0039

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

### topic-0023

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

### topic-0027

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

### topic-0009

- Article count: 2
- Source count: 2
- Reason: outside max-topics
- Article IDs: `[946, 964]`
- Similarity scores: `{946: 1.0, 964: 0.7487}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 946 | 1.0000 | The Guardian World | 2026-06-10 14:05:23+00:00 | Video shows family’s car slowing before Israeli troops shot dead Palestinian baby | https://www.theguardian.com/world/2026/jun/10/palestinian-baby-shot-dead-israeli-troops-occupied-west-bank-new-footage |
| supporting | 964 | 0.7487 | Al Jazeera | 2026-06-10 12:44:39+00:00 | 7-month-old baby shot by Israeli soldier in Hebron | https://www.aljazeera.com/video/newsfeed/2026/6/10/7-month-old-baby-shot-by-israeli-soldier-in-hebron?traffic_source=rss |

### topic-0012

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[979]`
- Similarity scores: `{979: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 979 | 1.0000 | DW English |  | Germany news: Recession looms as Iran war chokes growth | https://www.dw.com/en/germany-news-recession-looms-as-iran-war-chokes-growth/live-77487978?maca=en-rss-en-all-1573-rdf |

### topic-0013

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[983]`
- Similarity scores: `{983: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 983 | 1.0000 | DW English |  | Neo-Nazi lost an east German election, but extremism remains | https://www.dw.com/en/neo-nazi-lost-an-east-german-election-but-extremism-remains/a-77487377?maca=en-rss-en-all-1573-rdf |

### topic-0018

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[990]`
- Similarity scores: `{990: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 990 | 1.0000 | DW English |  | War in Ukraine: Kyiv strikes key Russian supply lines | https://www.dw.com/en/war-in-ukraine-kyiv-strikes-key-russian-supply-lines/a-77480640?maca=en-rss-en-all-1573-rdf |

### topic-0044

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[982]`
- Similarity scores: `{982: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 982 | 1.0000 | DW English |  | India news: Modi becomes longest-serving elected PM | https://www.dw.com/en/india-news-modi-becomes-longest-serving-elected-pm/live-77484563?maca=en-rss-en-all-1573-rdf |

### topic-0045

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[984]`
- Similarity scores: `{984: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 984 | 1.0000 | DW English |  | The strongest El Nino in more than a century may be coming | https://www.dw.com/en/the-strongest-el-nino-in-more-than-a-century-may-be-coming/a-77469489?maca=en-rss-en-all-1573-rdf |

### topic-0046

- Article count: 1
- Source count: 1
- Reason: outside max-topics
- Article IDs: `[994]`
- Similarity scores: `{994: 1.0}`

#### Reference Articles

| role | article_id | similarity | source | published_at | title | url |
| --- | ---: | ---: | --- | --- | --- | --- |
| representative | 994 | 1.0000 | DW English |  | NASA picks first European astronaut for Artemis mission | https://www.dw.com/en/nasa-picks-first-european-astronaut-for-artemis-mission/a-77482632?maca=en-rss-en-all-1573-rdf |

### topic-0068

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
