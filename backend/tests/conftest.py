"""Test fixtures for database-backed tests.

Catalog tests run against a separate PostgreSQL database (never your dev data):
TEST_DATABASE_URL if set, otherwise DATABASE_URL with "_test" appended to the
database name. The schema is built with the real Alembic migrations and seeded
once; each test runs in a transaction that is rolled back afterwards.
If PostgreSQL is not reachable, these tests are skipped with a clear message.
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.db.seed import seed_catalog
from app.db.session import get_db
from app.main import app


def _test_database_url():
    url = make_url(os.environ.get("TEST_DATABASE_URL") or settings.database_url)
    if not url.database.endswith("_test"):
        url = url.set(database=f"{url.database}_test")
    return url


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = _test_database_url()
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": url.database},
            )
            if not exists:
                # The name comes from configuration (always ending in _test), not user input.
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL is not available for database tests: {exc.orig}")
    finally:
        admin.dispose()

    engine = create_engine(url)
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")
    with Session(engine) as session:
        seed_catalog(session)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    connection = db_engine.connect()
    transaction = connection.begin()
    # Commits inside the test (e.g. by the seed) only release a savepoint.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
