"""Unit tests for CalculationCreate and CalculationRead. No database."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.calculation_factory import CalculationType
from app.models.calculation import Calculation
from app.schemas.calculation import CalculationCreate, CalculationRead


@pytest.mark.parametrize("kind", ["add", "sub", "multiply", "divide"])
def test_create_accepts_every_known_type(kind):
    payload = CalculationCreate(a=12.5, b=2.5, type=kind)
    assert payload.type is CalculationType(kind)


@pytest.mark.parametrize("kind", ["Add", "SUB", "Multiply", "DIVIDE"])
def test_create_normalizes_mixed_case_type_strings(kind):
    payload = CalculationCreate(a=9, b=3, type=kind)
    assert payload.type is CalculationType(kind.lower())


def test_create_accepts_the_enum_directly():
    payload = CalculationCreate(a=6, b=7, type=CalculationType.MULTIPLY)
    assert payload.type is CalculationType.MULTIPLY


def test_create_rejects_unknown_type():
    with pytest.raises(ValidationError):
        CalculationCreate(a=4, b=2, type="modulo")


def test_create_rejects_zero_divisor_on_divide():
    with pytest.raises(ValidationError, match="nonzero"):
        CalculationCreate(a=18, b=0, type="divide")


def test_zero_b_is_fine_when_not_dividing():
    payload = CalculationCreate(a=18, b=0, type="multiply")
    assert payload.b == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_create_rejects_non_finite_operands(bad):
    with pytest.raises(ValidationError):
        CalculationCreate(a=bad, b=1, type="add")


def test_create_rejects_non_numeric_operands():
    with pytest.raises(ValidationError):
        CalculationCreate(a="eleven", b=2, type="add")


def test_read_serializes_from_the_model_including_computed_result():
    calc = Calculation(
        id=uuid.uuid4(),
        a=45,
        b=6,
        type="divide",
        user_id=uuid.uuid4(),
    )
    calc.created_at = datetime.now(timezone.utc)
    view = CalculationRead.model_validate(calc)
    assert view.result == 7.5
    assert view.type is CalculationType.DIVIDE
    assert view.id == calc.id
    assert view.user_id == calc.user_id