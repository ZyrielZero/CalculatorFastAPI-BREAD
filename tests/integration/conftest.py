import pytest
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401  — register models on Base.metadata


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def _clean_tables(db):
    # calculations holds a foreign key into users, so Postgres refuses a
    # bare TRUNCATE on users alone; truncating both in one statement
    # resolves the dependency without CASCADE surprises.
    db.execute(text("TRUNCATE TABLE calculations, users"))
    db.commit()
    yield