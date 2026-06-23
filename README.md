# NewsLab

NewsLab은 개인적으로 장기 운영하며 개선하기 위해 시작한 뉴스 처리 플랫폼 프로젝트입니다.

현재는 Oracle Cloud Always Free A1 기반 K3s 클러스터 위에 FastAPI 애플리케이션을 배포하고, Traefik Ingress, cert-manager, Docker Hub, GitHub Actions를 활용해 HTTPS 기반 API 배포 흐름을 구성하고 있습니다.

## 현재 구성

- Backend: FastAPI
- Container: Docker
- Registry: Docker Hub
- Infrastructure: Oracle Cloud Always Free A1
- Orchestration: K3s
- Ingress: Traefik
- TLS: cert-manager + Let's Encrypt
- CI: GitHub Actions
- Domain: `api.dev-scj.site`

## 현재 API

- `GET /`
- `GET /health`
- `GET /version`
- `GET /sources`
- `GET /articles`
- `GET /articles/{article_id}`
- `GET /topics`
- `GET /topics/home`
- `GET /topics/{topic_id}`
- `GET /three-day-topics`
- `GET /three-day-topics/home`
- `GET /three-day-topics/{topic_id}`

3일 Topic은 최근 72시간 기사와 기존 `article_embeddings`를 직접
재클러스터링한 결과다. Daily Topic 결과를 다시 집계하지 않으며, 전용
`three_day_topics` 계열 테이블과 API를 사용한다.

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3일 Topic pipeline은 기본 dry-run으로 실행된다.

```bash
python scripts/run_three_day_topic_pipeline.py --window-end \
  2026-06-23T05:00:00+09:00
```

`--execute`는 DB write, 지연 원문 추출과 Summary provider 호출을 포함하므로
환경과 영향을 확인한 사람이 실행한다.

## 문서

- [Architecture](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)
- [3일 Topic 설계와 선택 근거](docs/design/three-day-topic-pipeline.md)
