# Approved Fixes: 실제 embedding 기반 topic 품질 검증

## Approved Fixes

### Fix 1. `analyze_topic_groups.py`에서 `.env` 자동 로드

실제 OpenAI embedding provider 실행 시 `OPENAI_EMBEDDING_API_KEY`를 환경변수에서 검사하지만, 기존 구현은 `.env` 파일을 자동으로 로드하지 않았다.

이로 인해 프로젝트 루트의 `.env`에 `OPENAI_EMBEDDING_API_KEY`를 설정해도 사용자가 별도로 `source .env`를 실행하지 않으면 provider safety gate에서 중단되었다.

이번 fix에서는 `scripts/analyze_topic_groups.py`에서 argument validation 전에 `load_dotenv()`를 호출하도록 수정한다.

수정 기준:

- `python-dotenv`의 `load_dotenv()`를 사용한다.
- `.env`가 없어도 deterministic dry-run은 기존처럼 동작해야 한다.
- `.env` secret value는 stdout, report, verification, devlog에 출력하지 않는다.
- provider safety gate는 유지한다.
  - `--use-embedding-provider` 필요
  - `OPENAI_EMBEDDING_API_KEY` 필요
  - 명시적 `--max-articles` 필요
  - `--max-articles` 200 초과 거부
- DB write, API, frontend, K8s, CronJob, raw extraction은 변경하지 않는다.

## Rejected or Deferred Suggestions

없음.

## Applied Changes

- `scripts/analyze_topic_groups.py`
  - `parse_args()` 시작 시 `load_dotenv()`를 호출해 argument/provider
    validation 전에 프로젝트 `.env`를 자동 로드하도록 수정했다.
  - 기존 provider safety gate와 deterministic dry-run 동작은 유지했다.

- `tests/test_analyze_topic_groups.py`
  - `parse_args()`가 `load_dotenv()`를 호출하는 테스트를 추가했다.
  - `.env` 로딩을 mock한 상태에서 key가 없으면 provider validation이
    계속 명확히 실패하는지 확인하도록 기존 테스트를 보강했다.

Not changed:

- `.env` 파일과 secret 값
- Provider opt-in, explicit max article, 200건 상한 safety gate
- Threshold comparison, topic grouping, report output
- DB, API, frontend, K8s, CronJob, raw extraction

Not performed:

- Real OpenAI provider 재실행
- DB write/migration, Supabase SQL
- Production command, push, merge

## Verification Required

```bash
.venv/bin/python -m py_compile scripts/analyze_topic_groups.py tests/test_analyze_topic_groups.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/analyze_topic_groups.py --help
```

.env 자동 로딩 확인:

```bash
unset OPENAI_EMBEDDING_API_KEY

.venv/bin/python scripts/analyze_topic_groups.py \
  --window-hours 24 \
  --max-articles 10 \
  --use-embedding-provider \
  --thresholds 0.70 \
  --dry-run
```

단, 위 명령은 프로젝트 루트 .env에 OPENAI_EMBEDDING_API_KEY가 있을 때만 성공해야 한다.

보안 확인:

```bash
git diff -- .env
git status --short | grep env
git grep -n -i -E "API_KEY|TOKEN|SECRET|PASSWORD|PRIVATE KEY|\\.env"
```
