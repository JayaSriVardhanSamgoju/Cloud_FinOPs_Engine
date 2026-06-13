import os
from sqlalchemy import create_engine

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")

DATABASE_URL = (
    f"postgresql://admin:admin123@{DB_HOST}:{DB_PORT}/cloudpulse_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20
)