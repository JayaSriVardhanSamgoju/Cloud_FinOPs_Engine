from sqlalchemy import create_engine

DATABASE_URL = (
    "postgresql://admin:admin123@127.0.0.1:5433/cloudpulse_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20
)