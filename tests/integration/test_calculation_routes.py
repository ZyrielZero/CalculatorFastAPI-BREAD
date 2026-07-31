"""Route-level integration tests for the /calculations BREAD surface.

Two registered users drive these tests so ownership isolation is
verified from both sides: every by-id route must treat another user's
row exactly like a missing one.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

ALICE = {"username": "alice_ops", "email": "alice@example.net", "password": "Vector-Sum-11"}
BOB = {"username": "bob_ops", "email": "bob@example.net", "password": "Scalar-Mul-22"}


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


def _auth_headers(client, creds):
    client.post("/users/register", json=creds)
    token = client.post(
        "/users/login",
        data={"username": creds["username"], "password": creds["password"]},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def alice(client):
    return _auth_headers(client, ALICE)


@pytest.fixture()
def bob(client):
    return _auth_headers(client, BOB)


def test_add_returns_201_with_computed_result(client, alice):
    response = client.post(
        "/calculations", json={"a": 6, "b": 7, "type": "multiply"}, headers=alice
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result"] == 42.0
    assert body["type"] == "multiply"


def test_browse_lists_only_own_rows(client, alice, bob):
    client.post("/calculations", json={"a": 1, "b": 2, "type": "add"}, headers=alice)
    client.post("/calculations", json={"a": 3, "b": 4, "type": "add"}, headers=alice)
    client.post("/calculations", json={"a": 9, "b": 9, "type": "sub"}, headers=bob)

    mine = client.get("/calculations", headers=alice).json()
    assert len(mine) == 2
    assert {row["result"] for row in mine} == {3.0, 7.0}


def test_read_returns_own_row(client, alice):
    created = client.post(
        "/calculations", json={"a": 10, "b": 4, "type": "sub"}, headers=alice
    ).json()
    response = client.get(f"/calculations/{created['id']}", headers=alice)
    assert response.status_code == 200
    assert response.json()["result"] == 6.0


def test_read_foreign_and_missing_ids_are_identical_404s(client, alice, bob):
    foreign = client.post(
        "/calculations", json={"a": 1, "b": 1, "type": "add"}, headers=bob
    ).json()["id"]
    missing = uuid.uuid4()

    foreign_resp = client.get(f"/calculations/{foreign}", headers=alice)
    missing_resp = client.get(f"/calculations/{missing}", headers=alice)
    assert foreign_resp.status_code == missing_resp.status_code == 404
    assert foreign_resp.json() == missing_resp.json()


def test_edit_replaces_fields_and_recomputes(client, alice):
    created = client.post(
        "/calculations", json={"a": 6, "b": 7, "type": "multiply"}, headers=alice
    ).json()
    response = client.put(
        f"/calculations/{created['id']}",
        json={"a": 84, "b": 2, "type": "divide"},
        headers=alice,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "divide"
    assert body["result"] == 42.0


def test_edit_rejects_zero_divisor(client, alice):
    created = client.post(
        "/calculations", json={"a": 8, "b": 2, "type": "divide"}, headers=alice
    ).json()
    response = client.put(
        f"/calculations/{created['id']}",
        json={"a": 8, "b": 0, "type": "divide"},
        headers=alice,
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_edit_foreign_row_is_404(client, alice, bob):
    foreign = client.post(
        "/calculations", json={"a": 5, "b": 5, "type": "add"}, headers=bob
    ).json()["id"]
    response = client.put(
        f"/calculations/{foreign}",
        json={"a": 1, "b": 1, "type": "add"},
        headers=alice,
    )
    assert response.status_code == 404


def test_delete_returns_204_and_row_is_gone(client, alice):
    created = client.post(
        "/calculations", json={"a": 2, "b": 2, "type": "add"}, headers=alice
    ).json()
    assert (
        client.delete(f"/calculations/{created['id']}", headers=alice).status_code
        == 204
    )
    assert client.get(f"/calculations/{created['id']}", headers=alice).status_code == 404


def test_delete_foreign_row_is_404_and_row_survives(client, alice, bob):
    foreign = client.post(
        "/calculations", json={"a": 3, "b": 3, "type": "multiply"}, headers=bob
    ).json()["id"]
    assert client.delete(f"/calculations/{foreign}", headers=alice).status_code == 404
    assert client.get(f"/calculations/{foreign}", headers=bob).status_code == 200


def test_all_routes_require_authentication(client):
    some_id = uuid.uuid4()
    assert client.get("/calculations").status_code == 401
    assert (
        client.post("/calculations", json={"a": 1, "b": 1, "type": "add"}).status_code
        == 401
    )
    assert client.get(f"/calculations/{some_id}").status_code == 401
    assert (
        client.put(
            f"/calculations/{some_id}", json={"a": 1, "b": 1, "type": "add"}
        ).status_code
        == 401
    )
    assert client.delete(f"/calculations/{some_id}").status_code == 401


def test_add_invalid_type_returns_400(client, alice):
    response = client.post(
        "/calculations", json={"a": 1, "b": 1, "type": "modulo"}, headers=alice
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_add_missing_operand_returns_400(client, alice):
    response = client.post("/calculations", json={"a": 1, "type": "add"}, headers=alice)
    assert response.status_code == 400


def test_type_is_case_insensitive_on_create(client, alice):
    response = client.post(
        "/calculations", json={"a": 2, "b": 3, "type": "Add"}, headers=alice
    )
    assert response.status_code == 201
    assert response.json()["type"] == "add"


def test_result_recomputes_from_stored_operands_on_read(client, alice):
    create_resp = client.post(
        "/calculations", json={"a": 100, "b": 25, "type": "divide"}, headers=alice
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    fetch_resp = client.get(f"/calculations/{created['id']}", headers=alice)
    assert fetch_resp.status_code == 200, fetch_resp.text
    assert fetch_resp.json()["result"] == 4.0