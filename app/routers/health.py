import socket
from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "news-api",
        "hostname": socket.gethostname(),
    }
