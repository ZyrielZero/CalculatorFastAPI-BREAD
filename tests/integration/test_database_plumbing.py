from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import build_engine, get_db
from app.database_init import drop_db, init_db


def test_build_engine_honors_explicit_url():
    engine = build_engine("sqlite://")
    assert engine.url.drivername == "sqlite"


def test_get_db_yields_a_working_session_and_closes():
    generator = get_db()
    session = next(generator)
    assert isinstance(session, Session)
    assert session.execute(text("SELECT 1")).scalar() == 1
    generator.close()  # runs the finally block


def test_init_and_drop_db_manage_the_users_table():
    drop_db()
    init_db()
    from app.database import engine

    assert inspect(engine).has_table("users")