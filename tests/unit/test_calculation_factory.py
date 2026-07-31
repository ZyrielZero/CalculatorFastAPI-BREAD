"""Unit tests for the calculation strategy factory. No database required."""

import pytest

from app.calculation_factory import (
    Addition,
    ArithmeticOperation,
    CalculationFactory,
    CalculationType,
    Division,
    Multiplication,
    Subtraction,
)


@pytest.mark.parametrize(
    ("kind", "a", "b", "expected"),
    [
        (CalculationType.ADD, 14.5, 3.25, 17.75),
        (CalculationType.SUB, 90, 27, 63),
        (CalculationType.MULTIPLY, 6.5, 4, 26.0),
        (CalculationType.DIVIDE, 91, 4, 22.75),
    ],
)
def test_each_type_computes_through_the_factory(kind, a, b, expected):
    assert CalculationFactory.compute(kind, a, b) == expected


@pytest.mark.parametrize(
    ("kind", "strategy"),
    [
        ("add", Addition),
        ("sub", Subtraction),
        ("multiply", Multiplication),
        ("divide", Division),
    ],
)
def test_plain_strings_resolve_to_the_right_strategy(kind, strategy):
    op = CalculationFactory.operation_for(kind)
    assert isinstance(op, strategy)
    assert isinstance(op, ArithmeticOperation)


def test_zero_divisor_raises_value_error():
    with pytest.raises(ValueError, match="nonzero"):
        CalculationFactory.compute(CalculationType.DIVIDE, 33, 0)


def test_unknown_type_raises_value_error():
    with pytest.raises(ValueError, match="unsupported calculation type"):
        CalculationFactory.operation_for("modulo")


def test_strategies_are_reused_not_rebuilt():
    first = CalculationFactory.operation_for(CalculationType.MULTIPLY)
    second = CalculationFactory.operation_for("multiply")
    assert first is second