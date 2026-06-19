# Task: 저장된 article embedding을 daily topic pipeline에 연결

## Goal

기존 daily topic pipeline이 매 실행마다 embedding을 새로 생성하지 않고, 55차에서 구현한 `article_embeddings` 저장·재사용 기능을 사용하도록 변경한다.

처리 흐름:

```text
Daily topic 후보 기사 조회
→ 기사별 source text와 hash 생성
→ 기존 article_embeddings 확인
→ hash가 같으면 저장 vector 재사용
→ 없거나 hash가 변경됐으면 embedding 생성·저장
→ 확보한 vector로 기존 clustering 수행
→ topic 및 topic_articles 저장
```

동일한 입력으로 pipeline을 다시 실행했을 때 embedding provider 호출이 반복되지 않아야 한다.

이번 작업에서는 기존 daily pipeline의 실행 단위, CronJob과 schedule을 유지한다. Pipeline 분리는 실제 적용 결과를 확인한 뒤 후속 작업에서 결정한다.

## Scope

### 1. 현재 pipeline 조사

구현 전에 실제 repository를 기준으로 다음을 확인한다.

- Daily topic pipeline 진입 script와 주요 함수
- 후보 기사 조회 조건
- 현재 embedding 생성 위치
- 사용 중인 provider, model과 dimension
- Embedding 결과가 clustering에 전달되는 자료형
- Article metadata와 vector의 매핑 방식
- Clustering 최소 입력 조건
- Topic 및 `topic_articles` 저장 흐름
- Pipeline 결과와 log 형식
- 관련 tests와 fake provider 구조
- 현재 CronJob command와 schedule

Task 설명과 실제 코드가 다르면 repository 구조를 우선한다.

### 2. Embedding 저장·재사용 연결

Daily pipeline에서 55차의 공통 article embedding 저장 모듈을 사용한다.

필수 동작:

- 기존 `title_summary` 입력, 정규화와 hash 규칙을 그대로 사용한다.
- 동일한 article, provider, model, dimension과 source type의 기존 row를 확인한다.
- Hash가 같으면 provider를 호출하지 않고 저장 vector를 사용한다.
- Row가 없으면 embedding을 생성하고 저장한다.
- Hash가 변경됐으면 embedding을 다시 생성하고 atomic upsert로 갱신한다.
- 저장 DB에서 읽은 vector를 기존 clustering 입력 형식으로 변환한다.
- 저장·재사용 로직을 pipeline 내부에 복제하지 않는다.

Embedding 상태는 다음으로 구분한다.

```text
created
updated
reused
failed
```

향후 실행 단위 분리를 고려해 후보 조회, embedding 확보, clustering과 topic 저장의 함수 책임은 구분하되 과도한 구조 개편은 하지 않는다.

### 3. 실패 처리와 clustering 연결

개별 article embedding 실패가 전체 pipeline을 즉시 중단시키지 않도록 한다.

- 실패하거나 dimension이 맞지 않는 article은 clustering 입력에서 제외한다.
- 정상 처리된 article은 계속 진행한다.
- 실패 article ID와 안전한 오류 요약만 기록한다.
- Secret, connection string, API key와 전체 원문은 log에 남기지 않는다.
- 정상 vector 수가 clustering 최소 조건보다 적으면 clustering과 topic 저장을 건너뛴다.
- 실패 article을 제외한 뒤에도 article metadata와 vector 순서가 일치해야 한다.
- 서로 다른 provider, model, dimension과 source type의 vector를 섞지 않는다.

기존 clustering 알고리즘, threshold와 topic 저장 계약은 변경하지 않는다.

### 4. 실행 통계와 문서

Pipeline 결과 또는 log에 다음 값을 포함한다.

```text
candidate_articles
embedding_created
embedding_updated
embedding_reused
embedding_failed
clustering_input_count
topic_count
pipeline_elapsed_seconds
```

기존 출력 형식이 있다면 기존 필드를 제거하지 않고 필요한 값만 추가한다.

다음을 현재 문서 구조에 맞게 갱신한다.

- Pipeline architecture
- 관련 runbook
- Verification
- Devlog
- PR draft

실제 명령과 결과는 verification에 기록한다.

적용 후 분리를 선택한 이유, 실행 시간과 reuse 수치, 후속 분리 판단 근거는 devlog에 기록한다.

README는 공개 API, 설치 절차 또는 사용자 기능이 변경되는 경우에만 수정한다.

## Do not change

- Daily pipeline의 실행 단위, CronJob command, schedule과 K3s manifest를 변경하지 않는다.
- Docker build/push, Kubernetes apply/delete/rollout/restart를 수행하지 않는다.
- 기존 embedding schema, migration, provider, model, dimension, source type과 정규화 규칙을 변경하지 않는다.
- Clustering 알고리즘, threshold와 topic summary 정책을 변경하지 않는다.
- ANN index, 신규 run table, queue, retry framework, distributed lock과 병렬 처리를 추가하지 않는다.
- Public API와 frontend를 변경하지 않는다.
- 기존 SQL 전체 ORM 전환이나 대규모 SQL refactoring을 수행하지 않는다.
- Secret, `.env`, kubeconfig와 실제 credential을 agent가 읽거나 수정하지 않는다.
- 운영 Supabase 데이터를 agent가 임의로 변경하거나 삭제하지 않는다.
- `git push`, merge와 PR merge를 수행하지 않는다.

## Expected files

실제 repository 구조를 우선한다.

예상 변경 영역:

```text
기존 daily topic pipeline script 또는 module
app/utils/article_embedding_storage.py
관련 pipeline 및 embedding tests
docs/architecture/pipeline.md
필요한 경우 docs/architecture/database.md
관련 runbook
docs/verification/feature-daily-pipeline-embedding-reuse.md
docs/devlog/feature-daily-pipeline-embedding-reuse.md
docs/pr/feature-daily-pipeline-embedding-reuse.md
```

## DB changes

Schema와 migration 변경 없음.

기존 항목을 사용한다.

```text
articles
article_embeddings
topics
topic_articles
```

추가 schema가 필요하다고 판단되면 구현하지 말고 blocker 또는 후속 제안으로 기록한다.

## API changes

Public API 변경 없음.

Pipeline 내부 결과와 CLI log에 embedding 통계 필드를 추가할 수 있다.

기존 자동화가 출력 형식에 의존하는 경우 기존 필드를 유지한다.

## Test commands

관련 범위 test를 먼저 실행하고 전체 회귀 test를 실행한다.

최소 검증:

```bash
python -m compileall app scripts tests
python -m unittest discover -s tests
git diff --check
git status --short --branch
git diff --name-only
git diff --stat
```

다음을 단위 테스트로 확인한다.

- 기존 hash가 같으면 provider 미호출 및 `reused`
- Row가 없으면 embedding 생성 및 저장
- Hash가 변경되면 embedding 갱신
- 다른 model 또는 source type row를 잘못 재사용하지 않음
- Dimension 불일치 article 제외
- Provider 실패 article 제외 후 정상 article 계속 처리
- Article metadata와 vector 순서 유지
- `created`, `updated`, `reused`, `failed` 집계
- `clustering_input_count` 계산
- 최소 입력 미달 시 clustering 건너뜀
- 기존 clustering과 topic 저장 test 회귀 없음

외부 API와 운영 Supabase를 unit test에서 직접 호출하지 않는다.

Fake provider와 기존 test fixture를 사용한다.

실제 수동 실행 command는 repository 조사 후 verification에 기록한다.

## Acceptance criteria

- [x] 기존 daily topic pipeline의 embedding 생성과 clustering 연결 위치를 확인했다.
- [x] 55차 article embedding 공통 모듈을 pipeline에서 재사용한다.
- [x] 기존 embedding 계약에 따라 신규 생성, hash 변경 갱신과 동일 hash 재사용이 동작한다.
- [x] 저장 로직을 pipeline 내부에 복제하지 않았다.
- [x] 실패 또는 비호환 article은 제외되고 정상 article 처리는 계속된다.
- [x] 실패 article 제외 후에도 metadata와 vector 매핑이 유지된다.
- [x] 기존 clustering 알고리즘, threshold와 topic 저장 동작을 유지한다.
- [x] 후보·embedding 상태·clustering 입력·topic 수·실행 시간이 결과에 기록된다.
- [x] 관련 unit test와 전체 회귀 test가 통과한다.
- [ ] 실제 수동 실행에서 topic 생성 결과를 확인했다.
  - 사람이 수행 필요
- [ ] 동일 조건 재실행에서 embedding reuse 증가를 확인했다.
  - 사람이 수행 필요
- [x] CronJob, K3s manifest, DB schema, Public API와 frontend를 변경하지 않았다.
- [x] Architecture, runbook, verification, devlog와 PR draft를 갱신했다.
- [x] 실제 credential과 전체 원문을 log 또는 문서에 기록하지 않았다.

## Notes

이번 작업의 순서:

```text
현재 pipeline 조사
→ 저장 embedding 연결
→ 로컬 test
→ 사람이 pipeline 수동 실행
→ 동일 조건 재실행
→ scheduled daily 실행 관찰
→ 후속 분리 필요성 판단
```

사람은 환경변수를 안전하게 주입한 뒤 pipeline을 두 번 실행하고 다음 값을 verification에 기록한다.

```text
candidate_articles
embedding_created
embedding_updated
embedding_reused
embedding_failed
clustering_input_count
topic_count
pipeline_elapsed_seconds
```

후속 pipeline 분리는 다음 근거를 보고 판단한다.

- Embedding 단계의 실행 시간과 API 호출 비중
- Embedding과 summary의 실패·재시도 정책 차이
- 한 단계 실패로 전체 pipeline을 재실행하는 비용
- 단계별 실행 주기와 resource 분리 필요성

작업은 WIP 1로 진행한다.

```text
조사
→ 변경
→ 문서화
→ 검증
→ verification 기록
→ checklist 갱신
```
