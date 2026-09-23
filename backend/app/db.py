import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./money.db")
if os.getenv("APP_ENV") == "production" and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("Production requires a persistent PostgreSQL DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
