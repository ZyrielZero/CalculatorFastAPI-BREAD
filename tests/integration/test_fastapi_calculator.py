# tests/integration/test_fastapi_calculator.py
"""Integration tests for the FastAPI calculator endpoints.

Requests go through TestClient, so routing, Pydantic validation, the custom
exception handlers, and the operations layer are all exercised together
without a live server. Malformed payloads are asserted against the custom
RequestValidationError handler, which returns 400 with an 'error' field
rather than FastAPI's default 422 shape.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Yield a TestClient bound to the app, closed after each test."""
    with TestClient(app) as client:
        yield client


def test_homepage_serves_template(client):
    """GET / renders the calculator page from the Jinja2 template."""
    response = client.get('/')
    assert response.status_code == 200
    assert 'Hello World' in response.text


@pytest.mark.parametrize(
    "endpoint, a, b, expected",
    [
        ('/add', 19, 23, 42),
        ('/add', -1.5, 0.5, -1.0),
        ('/subtract', 100, 58, 42),
        ('/subtract', 2.5, 7.5, -5.0),
        ('/multiply', 6, -7, -42),
        ('/multiply', 0.25, 8, 2.0),
        ('/divide', 84, 2, 42.0),
        ('/divide', -1, 4, -0.25),
    ],
    ids=[
        "add_ints", "add_mixed_signs",
        "subtract_ints", "subtract_negative_result",
        "multiply_mixed_signs", "multiply_floats",
        "divide_ints", "divide_fractional",
    ],
)
def test_operation_endpoints(client, endpoint, a, b, expected):
    """Each arithmetic endpoint returns 200 and the correct result."""
    response = client.post(endpoint, json={'a': a, 'b': b})
    assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
    assert response.json()['result'] == expected


def test_divide_by_zero_returns_400(client):
    """A zero divisor surfaces as 400 with the operation's error message."""
    response = client.post('/divide', json={'a': 42, 'b': 0})
    assert response.status_code == 400
    body = response.json()
    assert 'error' in body
    assert 'Cannot divide by zero!' in body['error']


@pytest.mark.parametrize(
    "endpoint, payload",
    [
        ('/add', {'a': 'twelve', 'b': 3}),
        ('/subtract', {'a': 5}),
        ('/multiply', {}),
        ('/divide', {'a': None, 'b': 2}),
    ],
    ids=["non_numeric_string", "missing_field", "empty_payload", "null_value"],
)
def test_malformed_payloads_return_400(client, endpoint, payload):
    """Invalid bodies hit the custom validation handler: 400 + 'error' key."""
    response = client.post(endpoint, json=payload)
    assert response.status_code == 400, f"{endpoint} returned {response.status_code}"
    assert 'error' in response.json()
