# Daily topic pipeline report

## Summary

- Dry-run: `false`
- Execute requested: `true`
- Window hours: 24
- Article count: 114
- Topic candidate count: 104
- Selected topic count: 3
- Reference topic count: 10
- Selected article IDs: `[944, 945, 974, 952, 993, 898, 989]`
- Topic ordering: `article_count desc, source_count desc, average similarity desc, latest published_at desc, topic_candidate_id asc`
- Embedding provider/model: `openai` / `text-embedding-3-small`
- Summary provider/model: `openai` / `gpt-5-nano`
- Raw extraction performed: `true`
- Raw extraction success/failure: 3 / 2
- DB write performed: `true`

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
- title_ko: 트럼프의 신뢰성 논란 속 이란 갈등의 재점화
- summary_ko: 미국과 이란 간 갈등이 지속되는 가운데, 도널드 트럼프 대통령의 이란 합의 가능성 발언과 ‘거의 완전 승리’ 주장 사이의 모순이 신뢰성에 의문을 키우고 있다. 미국은 이란에 대한 방어적·비례적 타격을 재차 실시했고, 이란은 미군 기지와 동맹에 대한 공격으로 보복했다. 요르단의 알-아즈락 기지, 쿠웨이트, 바레인 등에서의 공격/방어 움직임과 함께 해협 인근 에너지 공급 우려도 제기되었다. 국제사회는 긴장 완화를 촉구하며 상황 악화를 막기 위한 대화를 강조했고, 유엔은 중동 위기의 확산 가능성에 경고했다.
- key_points:
  - 트럼프의 이란 합의 가능성 발언과 완패 주장 간의 모순으로 신뢰성 저하 우려 증가
  - 미국이 이란에 대해 지속적으로 타격을 가했고, 이란은 미군 기지에 대한 보복을 실시
  - 주요 군사시설과 기지가 타격 대상이 되었으며, CENTCOM의 방어적 성격의 작전 발표
  - 오만 해협 인근의 에너지 공급 등 지역 안보가 불안정해짐
  - 요르단 알-아즈락 기지, 쿠웨이트, 바레인 등에서의 전개와 교전 가능성 확대
  - 유엔은 중동의 긴장 확산 우려를 제기하며 외교적 해법의 필요성 재차 강조
- keywords: `미국-이란 갈등, 트럼프 발언, 합의 가능성, 대규모 타격, IRGC, 중동 긴장, 유엔, 호르무즈 해협, 기지 공격`

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

- Status: `ready`
- title_ko: 남아프리카 공화국 요하네스버그 인근 Jumpers 비공식 거주지에서 총격으로 12명 사망
- summary_ko: 요하네스버그 인근 Jumpers 비공식 거주지에서 무장 용의자들이 총격을 가해 12명이 사망하고 9명이 부상했다. 경찰은 화요일 저녁에 발생한 사건으로 10명 이상으로 추정되는 용의자를 수사 중이며, 용의자들은 흰색 토요타 퀀텀으로 두 개의 진입로를 통해 들어와 여러 장소에서 발포한 뒤 같은 차량으로 도주했다. 현장에서 8명의 남성 and 3명의 여성, 병원에서 1명이 추가로 사망했다. 동기는 아직 확인되지 않았으며, 이 지역이 합법 채굴 지역과 인접하다는 점에서 채굴 관련 의혹이 제기될 수 있다. 이 사건은 비공식 거주지의 폭력성과 무장 집단에 대한 치안 문제를 다시 한번 드러내며 남아프리카 공화국의 높은 살인율 맥락에서 주목된다.
- key_points:
  - 요하네스버그 인근 Jumpers 비공식 거주지에서 12명 사망, 9명 부상
  - 발생 시각: 화요일 저녁; 다수 용의자 추적 중
  - 용의자들은 흰색 토요타 퀀텀으로 두 진입로를 통해 진입, 여러 장소에서 발포 후 동일 차량으로 도주
  - 사망자 현장: 8명 남성, 3명 여성; 병원에서 1명 추가 사망
  - 동нуть은 아직 확인되지 않음
  - 지역은 합법 채굴 지역 인접; 채굴 관련 의혹 가능성
  - 사건은 비공식 거주지의 폭력과 치안 도전 재확인, 남아프리카의 높은 살인율 맥락에서 주목
- keywords: `남아프리카, 요하네스버그, 총격, 대규모 총격, Jumpers 비공식 거주지, 합법 채굴, 살인율, 경찰, 폭력 문제`

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
