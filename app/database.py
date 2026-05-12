import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401 — register models

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured (create_all).")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
