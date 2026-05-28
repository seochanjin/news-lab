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

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
