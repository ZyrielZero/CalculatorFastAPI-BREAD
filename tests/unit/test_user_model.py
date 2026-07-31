"""Unit tests for the User ORM mapping. No database required —
these assert against table metadata and Python-side behavior only."""

import uuid

from app.models.user import User


def test_tablename():
    assert User.__tablename__ == "users"


def test_username_and_email_are_unique():
    cols = User.__table__.columns
    assert cols["username"].unique is True
    assert cols["email"].unique is True


def test_required_columns_are_not_nullable():
    cols = User.__table__.columns
    for name in ("username", "email", "password_hash", "created_at"):
        assert cols[name].nullable is False


def test_created_at_has_server_default():
    assert User.__table__.columns["created_at"].server_default is not None


def test_last_login_is_nullable():
    assert User.__table__.columns["last_login"].nullable is True


def test_repr_shows_username_and_never_the_hash():
    u = User(
        id=uuid.uuid4(),
        username="corvid",
        email="corvid@example.net",
        password_hash="$2b$12$notarealhashnotarealhash",
    )
    assert "corvid" in repr(u)
    assert "$2b$" not in repr(u)