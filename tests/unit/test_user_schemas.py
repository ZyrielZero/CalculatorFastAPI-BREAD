import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.user import User
from app.schemas.user import Token, UserCreate, UserRead

VALID = {"username": "night_owl", "email": "owl@example.net", "password": "Talon-Grip-88"}


def test_valid_payload_passes():
    parsed = UserCreate(**VALID)
    assert parsed.username == "night_owl"


@pytest.mark.parametrize("bad_email", ["owl", "owl@", "@example.net", "owl at example.net"])
def test_invalid_email_rejected(bad_email):
    with pytest.raises(ValidationError):
        UserCreate(**{**VALID, "email": bad_email})


@pytest.mark.parametrize(
    "bad_password",
    [
        "Short-7",        # under 8 chars
        "no-capitals-9",  # single case
        "NO-LOWERS-9",    # single case
        "No-Digits-Here", # missing digit
        "x" * 73,         # over ceiling
    ],
)
def test_password_policy_rejects(bad_password):
    with pytest.raises(ValidationError):
        UserCreate(**{**VALID, "password": bad_password})


@pytest.mark.parametrize("bad_username", ["ab", "night owl", "owl@home", "-dash-", "a" * 41])
def test_username_constraints(bad_username):
    with pytest.raises(ValidationError):
        UserCreate(**{**VALID, "username": bad_username})


def _orm_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="night_owl",
        email="owl@example.net",
        password_hash="$2b$12$fakedhashforserializationtest",
        is_active=True,
        last_login=None,
        created_at=datetime.now(timezone.utc),
    )


def test_userread_maps_from_orm_object():
    read = UserRead.model_validate(_orm_user())
    assert read.username == "night_owl"
    assert read.is_active is True


def test_userread_cannot_leak_password_hash():
    dumped = UserRead.model_validate(_orm_user()).model_dump()
    assert "password_hash" not in dumped
    assert "$2b$" not in str(dumped)


def test_token_defaults_to_bearer():
    token = Token(access_token="abc", user=UserRead.model_validate(_orm_user()))
    assert token.token_type == "bearer"