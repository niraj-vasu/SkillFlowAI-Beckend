import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from .config import settings


def _resolve_database_url() -> str:
    """Pick the database URL and normalize it for SQLAlchemy + psycopg (v3).

    Priority: explicit DATABASE_URL, then Vercel Postgres' auto-injected POSTGRES_URL,
    then the config default (local SQLite). Vercel/Neon hand out `postgres://…` URLs,
    which SQLAlchemy needs rewritten to the `postgresql+psycopg://` driver form.
    """
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or settings.database_url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _resolve_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Serverless (Vercel): don't hold pooled connections across function invocations,
    # and check the connection is alive before using it.
    engine = create_engine(DATABASE_URL, poolclass=NullPool, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
