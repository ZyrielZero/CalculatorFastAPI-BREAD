import pytest

from app.auth.dependencies import get_current_active_user, get_current_user
from app.auth.tokens import issue_access_token, read_token_subject
from app.schemas.user import UserCreate
from app.services.user_service import authenticate_user, register_user
from fastapi import HTTPException

PAYLOAD = UserCreate(
    username="deep_field", email="field@example.net", password="Photon-Count-93"
)


@pytest.fixture()
def registered(db):
    return register_user(db, PAYLOAD)


def test_authenticate_returns_token_with_matching_subject(db, registered):
    token = authenticate_user(db, "deep_field", "Photon-Count-93")
    assert token is not None
    assert read_token_subject(token.access_token) == registered.id


def test_authenticate_response_omits_hash(db, registered):
    token = authenticate_user(db, "deep_field", "Photon-Count-93")
    assert "password_hash" not in token.user.model_dump()


def test_authenticate_stamps_last_login(db, registered):
    assert registered.last_login is None
    authenticate_user(db, "deep_field", "Photon-Count-93")
    db.refresh(registered)
    assert registered.last_login is not None


def test_wrong_password_and_unknown_user_are_indistinguishable(db, registered):
    assert authenticate_user(db, "deep_field", "Wrong-Answer-1") is None
    assert authenticate_user(db, "nobody_here", "Photon-Count-93") is None


def test_inactive_user_cannot_authenticate(db, registered):
    registered.is_active = False
    db.commit()
    assert authenticate_user(db, "deep_field", "Photon-Count-93") is None


def test_get_current_user_resolves_a_valid_token(db, registered):
    token = issue_access_token(registered.id)
    current = get_current_user(db=db, token=token)
    assert current.username == "deep_field"


def test_get_current_user_rejects_garbage_token(db):
    with pytest.raises(HTTPException) as excinfo:
        get_current_user(db=db, token="not.a.jwt")
    assert excinfo.value.status_code == 401


def test_get_current_user_rejects_token_for_deleted_user(db, registered):
    token = issue_access_token(registered.id)
    db.delete(registered)
    db.commit()
    with pytest.raises(HTTPException):
        get_current_user(db=db, token=token)


def test_inactive_user_is_forbidden_not_unauthorized(db, registered):
    token = issue_access_token(registered.id)
    current = get_current_user(db=db, token=token)
    registered.is_active = False
    db.commit()
    stale = current.model_copy(update={"is_active": False})
    with pytest.raises(HTTPException) as excinfo:
        get_current_active_user(current_user=stale)
    assert excinfo.value.status_code == 403
    
    
def test_active_user_passes_through_active_gate(db, registered):
    token = issue_access_token(registered.id)
    current = get_current_user(db=db, token=token)
    result = get_current_active_user(current_user=current)
    assert result is current