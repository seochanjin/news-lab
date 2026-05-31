import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "prepare_threshold": None,
    },
)


def get_connection():
    with engine.connect() as connection:
        yield connection
