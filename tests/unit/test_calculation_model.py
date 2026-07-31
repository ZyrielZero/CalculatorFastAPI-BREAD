"""Unit tests for the Calculation ORM mapping. No database required —
these assert against table metadata and Python-side behavior only."""

import uuid

import pytest

from app.models.calculation import Calculation


def test_tablename():
    assert Calculation.__tablename__ == "calculations"


def test_required_columns_are_not_nullable():
    cols = Calculation.__table__.columns
    for name in ("a", "b", "type", "user_id", "created_at"):
        assert cols[name].nullable is False


def test_user_id_is_a_foreign_key_to_users():
    fks = list(Calculation.__table__.columns["user_id"].foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "users"
    assert fks[0].ondelete == "CASCADE"


def test_created_at_has_server_default():
    assert Calculation.__table__.columns["created_at"].server_default is not None


def test_table_carries_both_check_constraints():
    names = {c.name for c in Calculation.__table__.constraints if c.name}
    assert "ck_calculations_known_type" in names
    assert "ck_calculations_nonzero_divisor" in names


@pytest.mark.parametrize(
    ("kind", "a", "b", "expected"),
    [
        ("add", 8.5, 11, 19.5),
        ("sub", 40, 13.5, 26.5),
        ("multiply", 7, 9, 63),
        ("divide", 51, 4, 12.75),
    ],
)
def test_result_is_computed_through_the_factory(kind, a, b, expected):
    calc = Calculation(id=uuid.uuid4(), a=a, b=b, type=kind, user_id=uuid.uuid4())
    assert calc.result == expected


def test_repr_names_the_operation_and_operands():
    calc = Calculation(id=uuid.uuid4(), a=3, b=5, type="multiply", user_id=uuid.uuid4())
    text = repr(calc)
    assert "multiply" in text
    assert "a=3" in text
    assert "b=5" in text