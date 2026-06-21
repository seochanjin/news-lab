# NewsLab Backend Architecture

이 문서는 backend architecture의 진입점이다. 세부 내용을 한 파일에 반복하지
않고 작업 범위에 맞는 문서만 선택해 읽는다.

## 전체 구조

NewsLab은 RSS 수집, 기사 원문 추출, 주제 생성 결과를 PostgreSQL/Supabase에
저장하고 FastAPI read API로 제공한다. application과 scheduled pipeline은
Oracle Cloud A1 node의 K3s cluster에서 실행된다.

```text
RSS source
→ collector / extractor / topic pipeline
→ PostgreSQL/Supabase
→ FastAPI
→ backend API domain
```

## 현재 운영 구성

- API application: `news-api`
- Database: PostgreSQL/Supabase
- Scheduled workload:
  - `news-rss-collector`
  - `news-daily-topic-pipeline`
- Runtime: Oracle Cloud A1 기반 K3s
- Ingress: Traefik
- TLS: cert-manager와 `letsencrypt-prod`
- Remote operation: Tailscale SSH tunnel

운영 변경과 production verification은 사람이 수행한다.

## 세부 문서

- [전체 구성과 책임](architecture/overview.md)
- [FastAPI와 API 영역](architecture/backend-api.md)
- [Database 구조](architecture/database.md)
- [수집·추출·주제 pipeline](architecture/pipeline.md)
- [K3s runtime](architecture/k3s-runtime.md)
- [Domain과 TLS](architecture/domains.md)

운영 command는 [Runbook index](RUNBOOK.md), agent 작업 절차는
[Backend agent workflow](agent/backend-workflow.md)를 참고한다.
