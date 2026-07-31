"""Route-level integration tests for /users/register and /users/login.

These exercise the full HTTP stack — routing, Pydantic validation, the
service layer, and Postgres — through TestClient, then verify the
resulting rows directly in the database.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models.user import User
from main import app

REGISTER = {
    "username": "route_runner",
    "email": "runner@example.net",
    "password": "Marathon-Pace-42",
}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_register_returns_201_with_user_read_shape(client, db):
    response = client.post("/users/register", json=REGISTER)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "route_runner"
    assert body["email"] == "runner@example.net"
    assert "password" not in body and "password_hash" not in body


def test_register_persists_hashed_password_in_db(client, db):
    client.post("/users/register", json=REGISTER)
    row = db.scalar(select(User).where(User.username == "route_runner"))
    assert row is not None
    assert row.password_hash != REGISTER["password"]
    assert row.password_hash.startswith("$2b$")


def test_register_duplicate_returns_409(client, db):
    assert client.post("/users/register", json=REGISTER).status_code == 201
    assert client.post("/users/register", json=REGISTER).status_code == 409


def test_register_invalid_payload_returns_400(client, db):
    weak = dict(REGISTER, password="alllowercase1")
    response = client.post("/users/register", json=weak)
    assert response.status_code == 400
    assert "error" in response.json()


def test_login_returns_bearer_token(client, db):
    client.post("/users/register", json=REGISTER)
    response = client.post(
        "/users/login",
        data={"username": REGISTER["username"], "password": REGISTER["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "route_runner"


def test_login_wrong_password_and_unknown_user_are_identical_401s(client, db):
    client.post("/users/register", json=REGISTER)
    wrong_pass = client.post(
        "/users/login",
        data={"username": REGISTER["username"], "password": "Wrong-Guess-99"},
    )
    no_user = client.post(
        "/users/login",
        data={"username": "ghost_account", "password": "Wrong-Guess-99"},
    )
    assert wrong_pass.status_code == no_user.status_code == 401
    assert wrong_pass.json() == no_user.json()


def test_login_stamps_last_login_in_db(client, db):
    client.post("/users/register", json=REGISTER)
    client.post(
        "/users/login",
        data={"username": REGISTER["username"], "password": REGISTER["password"]},
    )
    row = db.scalar(select(User).where(User.username == "route_runner"))
    assert row.last_login is not None
    
def test_register_page_serves_template(client):
    """GET /register renders the registration form with the fields the
    client-side script and e2e tests target by id."""
    response = client.get("/register")
    assert response.status_code == 200
    for element_id in ('id="username"', 'id="email"', 'id="password"', 'id="confirm"'):
        assert element_id in response.text


def test_login_page_serves_template(client):
    """GET /login renders the login form."""
    response = client.get("/login")
    assert response.status_code == 200
    assert 'id="identifier"' in response.text
    assert 'id="password"' in response.text


def test_login_accepts_email_as_identifier(client, db):
    """The login form field is labeled username-or-email; the service
    matches either column, so the registered email must authenticate."""
    client.post("/users/register", json=REGISTER)
    response = client.post(
        "/users/login",
        data={"username": REGISTER["email"], "password": REGISTER["password"]},
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

def test_spec_path_register_alias_creates_user(client, db):
    """POST /register — the path the assignment names — behaves exactly
    like POST /users/register, including the duplicate 409."""
    response = client.post("/register", json=REGISTER)
    assert response.status_code == 201
    assert response.json()["username"] == REGISTER["username"]
    assert client.post("/register", json=REGISTER).status_code == 409


def test_spec_path_login_alias_returns_token(client, db):
    """POST /login mirrors POST /users/login for both outcomes."""
    client.post("/register", json=REGISTER)
    ok = client.post(
        "/login",
        data={"username": REGISTER["username"], "password": REGISTER["password"]},
    )
    assert ok.status_code == 200
    assert ok.json()["token_type"] == "bearer"

    bad = client.post(
        "/login",
        data={"username": REGISTER["username"], "password": "Wrong-Password-1"},
    )
    assert bad.status_code == 401
