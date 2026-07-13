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
  - `news-three-day-topic-pipeline`
  - `news-weekly-topic-pipeline`
- Runtime: Oracle Cloud A1 기반 K3s
- Ingress: Traefik
- TLS: cert-manager와 `letsencrypt-prod`
- Remote operation: Tailscale SSH tunnel

운영 변경과 production verification은 사람이 수행한다.

## Backend 배포 기준

Backend `news-api` 운영 workload는 full Git SHA image tag를 사용한다. GitHub
Actions는 image build 성공 후 Kubernetes manifest image tag 갱신 branch와 PR을
생성하고, 사람이 manifest PR을 검토해 merge한다. Argo CD `news-api`
Application은 automated sync 없이 Git과 live state의 차이를 보여주며, 사람이
diff를 확인한 뒤 Manual Sync를 승인한다.

Rollback도 `latest`나 rollout restart가 아니라 이전 정상 full SHA를 manifest에
반영하는 PR, merge, Argo CD Manual Sync로 수행한다. Auto sync, automatic prune,
automatic self-heal은 적용하지 않는다.

## 세부 문서

- [전체 구성과 책임](architecture/overview.md)
- [FastAPI와 API 영역](architecture/backend-api.md)
- [Database 구조](architecture/database.md)
- [수집·추출·주제 pipeline](architecture/pipeline.md)
- [K3s runtime](architecture/k3s-runtime.md)
- [Domain과 TLS](architecture/domains.md)
- [Argo CD Manual Sync 설계](architecture/argocd-manual-sync-design.md)
- [Home API Redis Cache 설계](design/home-api-redis-cache.md)
- [3일 Topic 저장·실행 설계](design/three-day-topic-pipeline.md)
- [7일 Topic 저장·실행 설계](design/weekly-topic-pipeline.md)

운영 command는 [Runbook index](RUNBOOK.md), agent 작업 절차는
[Backend agent workflow](agent/backend-workflow.md)를 참고한다.
