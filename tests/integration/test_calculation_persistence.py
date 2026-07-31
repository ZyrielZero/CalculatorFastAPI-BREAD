"""Integration tests for the Calculation model against a real Postgres.

Covers the assignment's required cases: a record persists with correct
data, the user_id foreign key is enforced, disallowed operands and
unknown types are rejected by the database itself, and deleting a user
removes their calculations through ON DELETE CASCADE.
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.calculation import CalculationCreate, CalculationRead
from app.schemas.user import UserCreate
from app.services.user_service import register_user


@pytest.fixture()
def owner(db):
    return register_user(
        db,
        UserCreate(
            username="tally_keeper",
            email="tally@example.net",
            password="Ledger-Row-88",
        ),
    )


def _persist(db, owner, payload: CalculationCreate) -> Calculation:
    calc = Calculation(
        a=payload.a, b=payload.b, type=payload.type.value, user_id=owner.id
    )
    db.add(calc)
    db.commit()
    db.refresh(calc)
    return calc


def test_calculation_row_persists_with_correct_data(db, owner):
    payload = CalculationCreate(a=37.5, b=12.5, type="sub")
    saved = _persist(db, owner, payload)

    found = db.scalar(select(Calculation).where(Calculation.id == saved.id))
    assert found is not None
    assert found.a == 37.5
    assert found.b == 12.5
    assert found.type == "sub"
    assert found.user_id == owner.id
    assert found.created_at is not None
    assert found.result == 25.0


def test_read_schema_serializes_a_stored_row(db, owner):
    saved = _persist(db, owner, CalculationCreate(a=64, b=8, type="divide"))
    view = CalculationRead.model_validate(saved)
    assert view.result == 8.0
    assert view.user_id == owner.id


def test_foreign_key_rejects_a_user_that_does_not_exist(db):
    stray = Calculation(a=2, b=3, type="add", user_id=uuid.uuid4())
    db.add(stray)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_rejects_an_unknown_type(db, owner):
    bad = Calculation(a=10, b=3, type="modulo", user_id=owner.id)
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_database_rejects_a_zero_divisor_on_divide(db, owner):
    bad = Calculation(a=10, b=0, type="divide", user_id=owner.id)
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_a_user_cascades_to_their_calculations(db, owner):
    _persist(db, owner, CalculationCreate(a=5, b=4, type="multiply"))
    _persist(db, owner, CalculationCreate(a=100, b=42, type="sub"))
    assert db.scalar(select(Calculation.id)) is not None

    user_row = db.get(User, owner.id)
    db.delete(user_row)
    db.commit()

    assert db.scalar(select(Calculation.id)) is None