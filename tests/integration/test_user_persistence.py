import pytest
from sqlalchemy import select

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import DuplicateUserError, register_user

PAYLOAD = UserCreate(
    username="ridge_line", email="ridge@example.net", password="Summit-Push-41"
)


def test_register_persists_a_row(db):
    user = register_user(db, PAYLOAD)
    found = db.scalar(select(User).where(User.username == "ridge_line"))
    assert found is not None
    assert found.id == user.id


def test_stored_hash_is_bcrypt_not_plaintext(db):
    register_user(db, PAYLOAD)
    row = db.scalar(select(User).where(User.username == "ridge_line"))
    assert row.password_hash.startswith("$2b$")
    assert "Summit-Push-41" not in row.password_hash


def test_created_at_is_stamped_by_the_database(db):
    user = register_user(db, PAYLOAD)
    assert user.created_at is not None
    assert user.created_at.tzinfo is not None


def test_duplicate_username_raises(db):
    register_user(db, PAYLOAD)
    clone = UserCreate(
        username="ridge_line", email="other@example.net", password="Summit-Push-41"
    )
    with pytest.raises(DuplicateUserError):
        register_user(db, clone)


def test_duplicate_email_raises(db):
    register_user(db, PAYLOAD)
    clone = UserCreate(
        username="other_name", email="ridge@example.net", password="Summit-Push-41"
    )
    with pytest.raises(DuplicateUserError):
        register_user(db, clone)


def test_failed_duplicate_leaves_session_usable(db):
    register_user(db, PAYLOAD)
    with pytest.raises(DuplicateUserError):
        register_user(db, PAYLOAD)
    # rollback happened inside the service; the session must still work
    assert db.scalar(select(User).where(User.username == "ridge_line")) is not None