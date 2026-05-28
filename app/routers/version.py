import socket
from fastapi import APIRouter

router = APIRouter(tags=["version"])

@router.get("/version")
def version():
    return {
        "app": "news-api",
        "project": "NewsLab",
        "version": "0.2.0",
        "hostname": socket.gethostname(),
    }