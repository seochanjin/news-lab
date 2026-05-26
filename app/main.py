from fastapi import FastAPI
import socket

app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "news-api is running",
        "hostname": socket.gethostname()
    }

@app.get("/health")
def health():
    return {"status": "ok"}
