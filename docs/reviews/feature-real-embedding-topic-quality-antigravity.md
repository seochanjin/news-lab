# Antigravity Review: 실제 embedding 기반 topic 품질 검증

## Review Summary

Antigravity review 결과, 31차 `실제 embedding 기반 topic 품질 검증` 작업은 **PASS**로 판정되었다.

이번 작업은 30차에서 구현한 embedding topic grouping pipeline을 실제 OpenAI embedding provider로 제한 실행하고, threshold별 topic grouping 품질을 사람이 검토할 수 있는 markdown report로 생성하는 것이 목적이었다.

Review 기준에서 다음 항목들이 정상적으로 확인되었다.

- 실제 provider 호출 안전 장치 유지
- OpenAI embedding 호출과 DB write 경로 분리
- 여러 threshold 비교 시 동일 embedding 결과 재사용
- deterministic hash baseline 비교 시 외부 API 추가 호출 없음
- human-review용 report의 정보 충분성
- secret/API key 노출 없음
- SQL parameter binding 유지
- DB/API/frontend/K8s/CronJob/raw extraction/LLM summary 등 scope 외 변경 없음

최종 판정:

- Status: **PASS**
- Required fixes: **None**
- Optional suggestions: **Threshold 기준을 32차 대표 기사 선정 로직에 상속하는 것 권장**

## Problems Found

없음.

Antigravity는 다음 항목에서 문제를 발견하지 않았다.

- Provider safety gate
- DB read-only guard
- API cost control
- threshold comparison implementation
- deterministic baseline comparison
- report content completeness
- secret leakage
- SQL query safety
- scope control

## Required Fixes Before PR

없음.

모든 필수 검토 항목이 통과되었고, PR 전 반드시 수정해야 할 사항은 확인되지 않았다.

## Optional Improvements

### 1. Recommended threshold 기준 유지

실제 OpenAI embedding provider 검증 결과, 68개 article 샘플에서 다음 topic들이 의미 있게 묶였다.

- WWDC / Siri / Apple Intelligence
- Iran / Israel pause or truce
- Sam Bankman-Fried pardon request
- Meta / WhatsApp / NSO spyware issue

Human review 결과를 기준으로 다음 threshold 정책을 후속 작업에 이어가는 것을 권장한다.

- Default threshold candidate: `0.70`
- Conservative fallback threshold: `0.72`

32차 대표 기사 후보 선정 로직을 설계할 때, 31차에서 검증한 `0.70`을 기본 후보로 사용하고 `0.72`를 보수적 fallback으로 남기는 방향이 적절하다.

## Suggested Test Commands

PR 제출 전 다음 명령으로 최종 확인한다.

```bash
.venv/bin/python -m unittest discover -s tests -v
```

```bash
.venv/bin/python -m py_compile app/utils/topic_quality.py scripts/analyze_topic_groups.py
```

```bash
.venv/bin/python scripts/analyze_topic_groups.py \
  --window-hours 24 \
  --max-articles 100 \
  --thresholds 0.65,0.70,0.72,0.75,0.80 \
  --report-path docs/reports/feature-real-embedding-topic-quality.md \
  --dry-run
```

필요 시 실제 provider 검증은 명시적 human approval 후 제한 실행한다.

```bash
.venv/bin/python scripts/analyze_topic_groups.py \
  --window-hours 24 \
  --max-articles 100 \
  --use-embedding-provider \
  --thresholds 0.65,0.70,0.72,0.75,0.80 \
  --report-path docs/reports/feature-real-embedding-topic-quality.md \
  --dry-run
```

## Risk Notes

### 1. 실제 provider 호출 비용

실제 OpenAI embedding provider 호출은 비용이 발생할 수 있다.

다만 현재 구현은 다음 안전 장치를 유지한다.

- `--use-embedding-provider` 명시 필요
- `OPENAI_EMBEDDING_API_KEY` 환경변수 필요
- `--max-articles` 명시 필요
- `--max-articles` 200 초과 시 실행 중단
- API 호출 전 예상 token/cost 출력

31차 실제 검증에서는 다음 범위로 제한 실행되었다.

- Model: `text-embedding-3-small`
- Article count: `68`
- Estimated tokens: `5896`
- Estimated cost USD: `0.000118`
- DB write performed: `false`

### 2. DB write 없음

분석 script는 DB 연결 후 `set transaction read only`를 실행한다.

이번 작업에서는 다음을 수행하지 않았다.

- DB schema migration
- `article_embeddings` 저장
- `topics` 저장
- `topic_articles` 저장
- article/source row update
- Supabase SQL 실행

### 3. Scope 외 작업 없음

이번 PR은 topic 품질 검증과 report 생성으로 제한되었다.

다음 항목은 포함하지 않았다.

- raw article extraction 실행
- topic summary 생성
- LLM summary/key points/keywords 생성
- API router 추가
- frontend 변경
- K8s manifest 변경
- CronJob schedule 변경
- production rollout

### 4. Threshold는 운영 확정값이 아님

31차 결과 기준으로 `0.70`이 default candidate, `0.72`가 conservative fallback으로 적절해 보인다.

다만 이 값은 아직 운영 확정값이 아니라, 32차 대표 기사 후보 선정 단계에서 계속 human review와 함께 검증해야 한다.
