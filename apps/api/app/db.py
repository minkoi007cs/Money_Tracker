import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./money.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
if (os.getenv("APP_ENV") == "production" or os.getenv("VERCEL") == "1") and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("Production requires a persistent PostgreSQL DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
    **({"poolclass": NullPool} if os.getenv("APP_ENV") == "production" else {}),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    with SessionLocal() as db:
        yield db
