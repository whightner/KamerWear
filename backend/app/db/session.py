"""Database engine and request-scoped sessions."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine connects lazily, so importing this module does not require a running database.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields one session per request and always closes it."""
    with SessionLocal() as session:
        yield session
