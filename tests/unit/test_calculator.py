# tests/unit/test_calculator.py
"""Unit tests for app.operations.

Each arithmetic function is exercised through a parametrized table covering
sign combinations, int/float mixing, zero identities, and magnitude extremes.
The divide-by-zero contract is pinned down to its exact error message, since
main.py forwards that text to the client.
"""

import pytest
from typing import Union
from app.operations import add, subtract, multiply, divide

Number = Union[int, float]


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (7, 11, 18),
        (-4, -9, -13),
        (1.25, 2.75, 4.0),
        (-6.5, 10, 3.5),
        (0, 42, 42),
        (10**12, 10**12, 2 * 10**12),
    ],
    ids=[
        "positive_ints",
        "negative_ints",
        "positive_floats",
        "mixed_float_and_int",
        "zero_identity",
        "large_magnitudes",
    ],
)
def test_add(a: Number, b: Number, expected: Number) -> None:
    """add returns the sum across sign, type, and magnitude combinations."""
    result = add(a, b)
    assert result == expected, f"add({a}, {b}) returned {result}, expected {expected}"


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (14, 5, 9),
        (-8, -3, -5),
        (9.75, 0.25, 9.5),
        (3, 10, -7),
        (0, 0, 0),
    ],
    ids=[
        "positive_ints",
        "negative_ints",
        "positive_floats",
        "result_goes_negative",
        "zeros",
    ],
)
def test_subtract(a: Number, b: Number, expected: Number) -> None:
    """subtract returns a - b, including results that cross zero."""
    result = subtract(a, b)
    assert result == expected, f"subtract({a}, {b}) returned {result}, expected {expected}"


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (6, 7, 42),
        (-3, 9, -27),
        (-4, -2.5, 10.0),
        (0.5, 0.5, 0.25),
        (123456, 0, 0),
        (1, 8.25, 8.25),
    ],
    ids=[
        "positive_ints",
        "mixed_signs",
        "two_negatives",
        "fraction_squared",
        "zero_annihilates",
        "one_identity",
    ],
)
def test_multiply(a: Number, b: Number, expected: Number) -> None:
    """multiply returns the product, honoring zero and identity elements."""
    result = multiply(a, b)
    assert result == expected, f"multiply({a}, {b}) returned {result}, expected {expected}"


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (42, 6, 7.0),
        (-15, 3, -5.0),
        (-9, -4, 2.25),
        (1, 8, 0.125),
        (0, 5, 0.0),
        (7, 2, 3.5),
    ],
    ids=[
        "even_division",
        "negative_numerator",
        "two_negatives",
        "fractional_result",
        "zero_numerator",
        "non_terminating_input",
    ],
)
def test_divide(a: Number, b: Number, expected: float) -> None:
    """divide always returns a float quotient, regardless of input types."""
    result = divide(a, b)
    assert result == expected, f"divide({a}, {b}) returned {result}, expected {expected}"
    assert isinstance(result, float), f"divide({a}, {b}) returned {type(result).__name__}, expected float"


@pytest.mark.parametrize("a", [3, -3, 0, 2.5], ids=["positive", "negative", "zero", "float"])
def test_divide_by_zero(a: Number) -> None:
    """A zero divisor raises ValueError with the exact client-facing message."""
    with pytest.raises(ValueError, match="Cannot divide by zero!"):
        divide(a, 0)
